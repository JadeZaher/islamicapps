/** Chain graph for one hadith, mention-keyed (sections 8 and 9.4). Public views `public_chain_links` and
 * `public_chain_mention_candidates` only. See src/db/AGENTS.md §Identity candidates. */
import 'server-only';
import { sql } from 'drizzle-orm';
import type {
  ChainEdge,
  ChainGraph,
  ChainMentionCandidate,
  ChainNode,
  HadithTraditionCode,
  IdentityBasis,
  MentionIdentity,
} from './contracts';
import { text } from './mappers';
import { oneRow } from './sql-helpers';

/** Strongest basis first: the order candidates are listed and labelled in. */
const BASIS_ORDER: IdentityBasis[] = [
  'reviewer_decision',
  'source_index_confirmed_by_text',
  'source_index',
  'name_exact',
  'name_spelling_fold',
  'name_kunya_only',
];

/** `agreed` when every candidate names one narrator, `differ` when they name several. */
export function mentionIdentity(candidates: ChainMentionCandidate[]): MentionIdentity {
  const narrators = new Set(candidates.map((candidate) => candidate.narrator_id));
  return narrators.size === 0 ? 'unidentified' : narrators.size === 1 ? 'agreed' : 'differ';
}

function toCandidates(value: unknown): ChainMentionCandidate[] {
  const rows = Array.isArray(value) ? (value as Record<string, unknown>[]) : [];
  return rows
    .map((row) => ({
      narrator_id: String(row.narrator_id),
      name_ar: text(row.name_ar),
      name_en: text(row.name_en),
      basis: String(row.basis) as IdentityBasis,
    }))
    .sort(
      (left, right) =>
        BASIS_ORDER.indexOf(left.basis) - BASIS_ORDER.indexOf(right.basis) || left.narrator_id.localeCompare(right.narrator_id),
    );
}

/**
 * Every position of every branch, identified or not, ordered by branch then position, so the isnad always reads
 * as written. Each position carries all its identity candidates with their basis; narrator fields and the verdict
 * are present only on verified links.
 */
export async function getChainGraph(hadithId: string): Promise<ChainGraph> {
  const row = await oneRow<{
    tradition: string | null;
    source_work: string | null;
    nodes: Record<string, unknown>[] | null;
  }>(sql`
    with candidates as (
      select c.mention_id,
             json_agg(json_build_object('narrator_id', c.narrator_id, 'name_ar', n.name_ar,
                                        'name_en', coalesce(n.name_en, n.name), 'basis', c.basis)) as items
      from public_chain_mention_candidates c
      join narrators n on n.id = c.narrator_id
      where c.hadith_id = ${hadithId}
      group by c.mention_id
    )
    select
      (select t.code from public_hadiths h join traditions t on t.id = h.tradition_id where h.id = ${hadithId}) as tradition,
      (select col.name from public_hadiths h join collections col on col.id = h.collection_id where h.id = ${hadithId}) as source_work,
      (
        select json_agg(json_build_object(
                 'node_id', l.id, 'chain_id', l.chain_id, 'branch', l.branch, 'position', l.position,
                 'surface_ar', l.surface_ar, 'narrator_id', l.narrator_id, 'name_ar', n.name_ar,
                 'name_en', coalesce(n.name_en, n.name), 'resolution', l.resolution, 'link_kind', l.link_kind,
                 'is_link', l.is_link, 'verdict', v.verdict, 'candidates', coalesce(k.items, '[]'::json))
               order by l.branch, l.position)
        from public_chain_links l
        left join narrators n on l.is_link and n.id = l.narrator_id
        left join candidates k on k.mention_id = l.id
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

  const nodes: ChainNode[] = (row?.nodes ?? []).map((node) => {
    const candidates = toCandidates(node.candidates);
    return {
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
      candidates,
      identity: mentionIdentity(candidates),
    };
  });

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
    source_work: row?.source_work ?? null,
    chain_schema: 'v2',
    nodes,
    edges,
  };
}
