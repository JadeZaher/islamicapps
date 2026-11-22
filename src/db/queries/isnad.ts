/** Chain graph for one hadith or a family of hadiths, mention-keyed (sections 8 and 9.4). Public reads use the public
 * views `public_chain_links` and `public_chain_mention_candidates_v2`; reviewer reads pass REVIEW_CHAIN_RELATIONS.
 * See src/db/AGENTS.md §Identity candidates and §External identity. */
import 'server-only';
import { sql, type SQL } from 'drizzle-orm';
import type {
  ChainEdge,
  ChainGraph,
  ChainMentionCandidate,
  ChainNode,
  HadithTraditionCode,
  IdentityBasis,
  NameLatinBasis,
  NarratorAuthority,
} from './contracts';
import { BASIS_ORDER, mentionIdentity } from './identity-groups';
import { text } from './mappers';
import { oneRow } from './sql-helpers';
import { hadithRelationsFor, isCuratorVisibility, PUBLIC_VISIBILITY, type ReadVisibility } from './visibility';

export { mentionIdentity } from './identity-groups';

function toCandidates(value: unknown): ChainMentionCandidate[] {
  const rows = Array.isArray(value) ? (value as Record<string, unknown>[]) : [];
  return rows
    .map((row) => ({
      narrator_id: String(row.narrator_id),
      name_ar: text(row.name_ar),
      name_en: text(row.name_en),
      basis: String(row.basis) as IdentityBasis,
      source_ref: text(row.source_ref),
      origin: text(row.origin),
      tier_basis: row.tier_basis === true,
      authority: String(row.authority) as NarratorAuthority,
      placeholder: text(row.placeholder),
      label_reason: text(row.label_reason),
      person_key: text(row.person_key) ?? String(row.narrator_id),
    }))
    .sort(
      (left, right) =>
        BASIS_ORDER.indexOf(left.basis) - BASIS_ORDER.indexOf(right.basis) || left.narrator_id.localeCompare(right.narrator_id),
    );
}

/** The two relations a chain read draws from: every mention as written, and every identity candidate. */
export interface ChainRelations {
  /** Columns of `public_chain_links`. */
  links: SQL;
  /** Columns of `public_chain_mention_candidates_v2`. */
  candidates: SQL;
}

export const PUBLIC_CHAIN_RELATIONS: ChainRelations = {
  links: sql`public_chain_links`,
  candidates: sql`public_chain_mention_candidates_v2`,
};

/**
 * Person key of narrator alias `n` (src/db/AGENTS.md §External identity): its lexicon link candidate, else for a Riwayat
 * record its one hadith-kg crosswalk id (that record's link, else that record), else itself. Same rule as the load
 * invariant (`PERSON_KEYS` in src/db/load/verify-data.ts) and the projection. Compares records; never merges them.
 */
export const PERSON_KEY_SQL = sql`coalesce(
  (select min(x.rawi_narrator_id) from narrator_link_candidates x where x.external_narrator_id = n.id and x.retired_at is null),
  (select coalesce((select min(y.rawi_narrator_id) from narrator_link_candidates y
                    where y.external_narrator_id = 'narrator:hadith-kg:' || min(e.external_id) and y.retired_at is null),
                   'narrator:hadith-kg:' || min(e.external_id))
   from narrator_external_ids e
   where e.narrator_id = n.id and e.namespace = 'kg' and e.retired_at is null and n.authority::text = 'riwayat'
   having count(distinct e.external_id) = 1
      and exists (select 1 from narrators k where k.id = 'narrator:hadith-kg:' || min(e.external_id))),
  n.id)`;

/**
 * Reviewer mode: the same two relations over every live report, whatever its publication state. The standing-identity
 * predicate is the one in `public_chain_links` (drizzle/core/0006); keep the two in step.
 */
export const REVIEW_CHAIN_RELATIONS: ChainRelations = {
  links: sql`(
    select m.id, m.chain_id, m.hadith_id, c.branch, m.position, m.surface_ar, m.link_kind, m.resolution,
           (link.id is not null) as is_link, link.id as narrator_id,
           case when link.id is not null then m.confidence end as confidence,
           m.name_latin, m.name_latin_basis, m.name_latin_narrator_id,
           case when link.id is not null then m.extraction_method end as standing_basis,
           m.identity_withheld_reason
    from chain_mentions m
    join chains c on c.id = m.chain_id and c.retired_at is null
    join hadiths h on h.id = m.hadith_id and h.retired_at is null
    left join narrators link on link.id = m.narrator_id and link.retired_at is null
                            and m.resolution in ('source_index', 'human_verified', 'derived_relation_verified')
    where m.retired_at is null)`,
  candidates: sql`(
    select c.mention_id, c.hadith_id, c.narrator_id, c.basis, c.detail, c.source_ref, c.source_assertion_origin,
           (c.basis::text in ('source_index_confirmed_by_text', 'source_hadith_kg_confirmed_by_text',
                              'source_riwayat_confirmed_by_text', 'imam_kunya_convention')
            and n.placeholder_reason is null
            and coalesce(c.source_assertion_origin, '') <> 'riwayat_automatic_linking'
            and not exists (select 1 from narrator_source_profiles p
                            where p.narrator_id = n.id and p.retired_at is null and p.label_reason is not null)) as tier_basis
    from chain_mention_candidates c
    join narrators n on n.id = c.narrator_id and n.retired_at is null
    where c.retired_at is null
    union all
    select m.id, m.hadith_id, d.target_narrator_id, 'reviewer_decision'::mention_candidate_basis, d.decision_kind::text,
           null, null, true
    from chain_mentions m
    join narrator_surface_decisions d on d.id = m.decision_id and d.retired_at is null and d.target_narrator_id is not null
    join narrators n on n.id = d.target_narrator_id and n.retired_at is null
    where m.retired_at is null)`,
};

/** Chain relations for a resolved visibility (curator visibility only comes from src/lib/auth/visibility.ts). */
export function chainRelationsFor(visibility: ReadVisibility): ChainRelations {
  return isCuratorVisibility(visibility) ? REVIEW_CHAIN_RELATIONS : PUBLIC_CHAIN_RELATIONS;
}

/**
 * One JSON array of chain nodes for the reports in `hadithIds` (an SQL expression yielding a text[]), ordered by
 * report, branch, position. Each node carries all its identity candidates. Used inside a larger statement, so a page
 * section stays one round trip.
 */
export function chainNodesJson(relations: ChainRelations, hadithIds: SQL): SQL {
  return sql`(
    with candidates as (
      select c.mention_id,
             json_agg(json_build_object('narrator_id', c.narrator_id, 'name_ar', n.name_ar,
                                        'name_en', coalesce(n.name_en, n.name_latin, n.name), 'basis', c.basis,
                                        'source_ref', c.source_ref, 'origin', c.source_assertion_origin,
                                        'tier_basis', c.tier_basis, 'authority', n.authority,
                                        'placeholder', n.placeholder_reason, 'label_reason', p.label_reason,
                                        'person_key', ${PERSON_KEY_SQL})) as items
      from ${relations.candidates} c
      join narrators n on n.id = c.narrator_id
      left join narrator_source_profiles p on p.narrator_id = n.id and p.retired_at is null
      where c.hadith_id = any (${hadithIds})
      group by c.mention_id
    )
    select json_agg(json_build_object(
             'node_id', l.id, 'hadith_id', l.hadith_id, 'chain_id', l.chain_id, 'branch', l.branch,
             'position', l.position, 'surface_ar', l.surface_ar, 'narrator_id', l.narrator_id, 'name_ar', n.name_ar,
             'name_en', coalesce(n.name_en, n.name_latin, n.name), 'resolution', l.resolution, 'link_kind', l.link_kind,
             'is_link', l.is_link, 'candidates', coalesce(k.items, '[]'::json),
             'name_latin', l.name_latin, 'name_latin_basis', l.name_latin_basis,
             'name_latin_narrator_id', l.name_latin_narrator_id, 'standing_basis', l.standing_basis,
             'identity_withheld_reason', l.identity_withheld_reason)
           order by l.hadith_id, l.branch, l.position)
    from ${relations.links} l
    left join narrators n on l.is_link and n.id = l.narrator_id
    left join candidates k on k.mention_id = l.id
    where l.hadith_id = any (${hadithIds})
  )`;
}

/** Maps one JSON node; narrator fields only on a standing identity. `verdict` is filled by getChainGraph only. */
export function toChainNode(node: Record<string, unknown>, verdict: string | null = null): ChainNode {
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
    verdict: node.is_link ? verdict : null,
    candidates,
    identity: mentionIdentity(candidates),
    name_latin: text(node.name_latin),
    name_latin_basis: (text(node.name_latin_basis) as NameLatinBasis | null) ?? null,
    name_latin_narrator_id: text(node.name_latin_narrator_id),
    standing_basis: node.is_link ? text(node.standing_basis) : null,
    identity_withheld_reason: node.is_link ? null : text(node.identity_withheld_reason),
  };
}

/** Adjacency is position + 1 within the same chain (stricter than a global NARRATED_FROM, section 8). */
export function chainEdges(nodes: ChainNode[]): ChainEdge[] {
  const byChainPosition = new Map(nodes.map((node) => [`${node.chain_id}#${node.position}`, node]));
  const edges: ChainEdge[] = [];
  for (const node of nodes) {
    const next = byChainPosition.get(`${node.chain_id}#${node.position + 1}`);
    if (next) edges.push({ source: node.node_id, target: next.node_id, chain_id: node.chain_id });
  }
  return edges;
}

/**
 * Every position of every branch, identified or not, ordered by branch then position, so the isnad always reads
 * as written. Each position carries all its identity candidates with their basis; narrator fields and the verdict
 * are present only on a standing identity. Verdicts are read through the public views only.
 */
export async function getChainGraph(hadithId: string, visibility: ReadVisibility = PUBLIC_VISIBILITY): Promise<ChainGraph> {
  const relations = chainRelationsFor(visibility);
  const hadiths = hadithRelationsFor(visibility).hadiths;
  const row = await oneRow<{
    tradition: string | null;
    source_work: string | null;
    nodes: Record<string, unknown>[] | null;
    verdicts: Record<string, string> | null;
  }>(sql`
    select
      (select t.code from ${hadiths} h join traditions t on t.id = h.tradition_id where h.id = ${hadithId}) as tradition,
      (select col.name from ${hadiths} h join collections col on col.id = h.collection_id where h.id = ${hadithId}) as source_work,
      ${chainNodesJson(relations, sql`array[${hadithId}]::text[]`)} as nodes,
      (
        select json_object_agg(l.id, v.verdict)
        from public_chain_links l
        join public_hadiths h on h.id = l.hadith_id
        join lateral (
          select a.verdict
          from narrator_assessments a
          join citations c on c.id = a.citation_id and c.retired_at is null
                          and c.review_state in ('human_verified', 'source_verified')
          where a.narrator_id = l.narrator_id and a.retired_at is null
            and a.status = 'published' and a.tradition_id = h.tradition_id
          order by a.kind = 'consensus_summary' desc, a.updated_at desc
          limit 1
        ) v on true
        where l.hadith_id = ${hadithId} and l.is_link
      ) as verdicts
  `);

  const verdicts = row?.verdicts ?? {};
  const nodes = (row?.nodes ?? []).map((node) => toChainNode(node, text(verdicts[String(node.node_id)])));
  return {
    hadith_id: hadithId,
    tradition: (row?.tradition ?? null) as HadithTraditionCode | null,
    source_work: row?.source_work ?? null,
    chain_schema: 'v2',
    nodes,
    edges: chainEdges(nodes),
  };
}
