/** Chain graph for one hadith, mention-keyed (sections 8 and 9.4). Public view `public_chain_links` only. */
import 'server-only';
import { sql } from 'drizzle-orm';
import type { ChainEdge, ChainGraph, ChainNode, HadithTraditionCode } from './contracts';
import { text } from './mappers';
import { oneRow } from './sql-helpers';

/**
 * Every position of every branch, resolved or not, ordered by branch then position, so the isnad always
 * reads as written. Narrator fields and the verdict are present only on verified links.
 */
export async function getChainGraph(hadithId: string): Promise<ChainGraph> {
  const row = await oneRow<{ tradition: string | null; nodes: Record<string, unknown>[] | null }>(sql`
    select
      (select t.code from public_hadiths h join traditions t on t.id = h.tradition_id where h.id = ${hadithId}) as tradition,
      (
        select json_agg(json_build_object(
                 'node_id', l.id, 'chain_id', l.chain_id, 'branch', l.branch, 'position', l.position,
                 'surface_ar', l.surface_ar, 'narrator_id', l.narrator_id, 'name_ar', n.name_ar,
                 'name_en', coalesce(n.name_en, n.name), 'resolution', l.resolution, 'link_kind', l.link_kind,
                 'is_link', l.is_link, 'verdict', v.verdict)
               order by l.branch, l.position)
        from public_chain_links l
        left join narrators n on l.is_link and n.id = l.narrator_id
        left join lateral (
          select a.verdict
          from narrator_assessments a
          join public_hadiths h on h.id = l.hadith_id
          join citations c on c.id = a.citation_id and c.retired_at is null
                          and c.review_state in ('human_verified', 'source_verified')
          where l.is_link and a.narrator_id = l.narrator_id and a.retired_at is null
            and a.status = 'published' and a.tradition_id = h.tradition_id
          order by a.kind = 'consensus_summary' desc, a.updated_at desc
          limit 1
        ) v on true
        where l.hadith_id = ${hadithId}
      ) as nodes
  `);

  const nodes: ChainNode[] = (row?.nodes ?? []).map((node) => ({
    node_id: String(node.node_id),
    chain_id: String(node.chain_id),
    branch: Number(node.branch),
    position: Number(node.position),
    surface_ar: String(node.surface_ar),
    narrator_id: node.is_link ? String(node.narrator_id) : null,
    name_ar: node.is_link ? text(node.name_ar) : null,
    name_en: node.is_link ? text(node.name_en) : null,
    resolution: String(node.resolution),
    link_kind: String(node.link_kind),
    is_link: node.is_link === true,
    verdict: node.is_link ? text(node.verdict) : null,
  }));

  // Adjacency is position + 1 within the same chain (stricter than a global NARRATED_FROM, section 8).
  const byChainPosition = new Map(nodes.map((node) => [`${node.chain_id}#${node.position}`, node]));
  const edges: ChainEdge[] = [];
  for (const node of nodes) {
    const next = byChainPosition.get(`${node.chain_id}#${node.position + 1}`);
    if (next) edges.push({ source: node.node_id, target: next.node_id, chain_id: node.chain_id });
  }

  return {
    hadith_id: hadithId,
    tradition: (row?.tradition ?? null) as HadithTraditionCode | null,
    chain_schema: 'v2',
    nodes,
    edges,
  };
}
