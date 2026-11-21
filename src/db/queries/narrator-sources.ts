/**
 * A narrator's record in an external source (hadith-kg, Riwayat) or the Imam register, its link candidates to the
 * lexicon, and every public chain position it is named at (standing identity or candidate), paged. Public views only.
 * See src/db/AGENTS.md §External identity and src/db/queries/AGENTS.md §Narrator sources.
 */
import 'server-only';
import { sql } from 'drizzle-orm';
import { reportReference } from '@/lib/citation/reference';
import type { HadithTraditionCode, IdentityBasis, NameLatinBasis, NarratorAuthority, Paginated } from './contracts';
import { text } from './mappers';
import { clampPage, COUNT_CAP, oneRow, paginated, type PageRequest } from './sql-helpers';

type Row = Record<string, unknown>;

/** Dataset fields that judge a narrator (rank wording, tadlis and ikhtilat flags, creed accusations) are never shown. */
const VERDICT_LIKE_FIELDS = new Set(['rank', 'rank_no', 'has_tadlis', 'has_ikhtilat', 'madhhab', 'is_bukhari', 'is_muslim']);

export interface NarratorLinkCandidate {
  narrator_id: string;
  name: string;
  name_ar: string | null;
  authority: NarratorAuthority;
  basis: string;
}

export interface NarratorSourceRecord {
  narrator_id: string;
  authority: NarratorAuthority;
  /** The dataset's own id (`authority_key`). */
  source_key: string;
  name_ar: string | null;
  name_latin: string | null;
  name_latin_basis: NameLatinBasis | null;
  placeholder_reason: string | null;
  /** Set when the source's id names a label as written in chains rather than an established person. */
  label_reason: string | null;
  licence: string;
  asserted_by: string;
  /** What the source records, verbatim, verdict-like fields removed. */
  assertions: Array<[string, string]>;
  /** Riwayat's name forms with their type and source. */
  name_forms: Array<{ form: string; type: string; source: string }>;
  name_source: string | null;
  /** Other datasets' ids the record carries (Riwayat's crosswalk), with a loaded record to link where one exists. */
  external_ids: Array<{ namespace: string; external_id: string; narrator_id: string | null }>;
  /** Machine-proposed links to the lexicon: candidates only. */
  link_candidates: NarratorLinkCandidate[];
}

function flatten(value: unknown): string | null {
  if (value === null || value === undefined || value === '') return null;
  if (Array.isArray(value)) return value.map(String).join(', ');
  if (typeof value === 'object') return Object.entries(value as Row).map(([key, count]) => `${key} ${count}`).join(', ');
  return String(value);
}

/** The record an external source keeps for this narrator; null for a lexicon narrator (it has no source profile). */
export async function getNarratorSourceRecord(narratorId: string): Promise<NarratorSourceRecord | null> {
  const row = await oneRow<{ record: Row | null }>(sql`
    select json_build_object(
      'narrator_id', n.id, 'authority', n.authority, 'source_key', n.authority_key, 'name_ar', n.name_ar,
      'name_latin', n.name_latin, 'name_latin_basis', n.name_latin_basis, 'placeholder_reason', n.placeholder_reason,
      'label_reason', p.label_reason, 'licence', p.licence, 'asserted_by', p.asserted_by, 'assertions', p.assertions,
      'external_ids', coalesce((
        select json_agg(json_build_object('namespace', e.namespace, 'external_id', e.external_id,
                                          'narrator_id', k.id) order by e.namespace, e.external_id)
        from narrator_external_ids e
        left join narrators k on k.retired_at is null
          and k.id = case e.namespace when 'kg' then 'narrator:hadith-kg:' || e.external_id
                                      when 'mids' then 'narrator:rawi:' || e.external_id end
        where e.narrator_id = n.id and e.retired_at is null), '[]'::json),
      'link_candidates', coalesce((
        select json_agg(json_build_object('narrator_id', r.id, 'name', coalesce(r.name_en, r.name), 'name_ar', r.name_ar,
                                          'authority', r.authority, 'basis', x.basis) order by r.id)
        from narrator_link_candidates x join narrators r on r.id = x.rawi_narrator_id and r.retired_at is null
        where x.external_narrator_id = n.id and x.retired_at is null), '[]'::json)
    ) as record
    from narrators n
    join narrator_source_profiles p on p.narrator_id = n.id and p.retired_at is null
    where n.id = ${narratorId} and n.retired_at is null
  `);
  const record = row?.record;
  if (!record) return null;
  const assertions = (record.assertions ?? {}) as Row;
  const dataset = (assertions.dataset_assertions ?? {}) as Row;
  const shown: Array<[string, string]> = [];
  for (const [key, value] of Object.entries(dataset)) {
    if (VERDICT_LIKE_FIELDS.has(key)) continue;
    const flat = flatten(value);
    if (flat) shown.push([key, flat]);
  }
  for (const key of ['popular_name_ar', 'known_as', 'ordinal', 'kunyas', 'tradition_label']) {
    const flat = flatten(assertions[key]);
    if (flat) shown.push([key, flat]);
  }
  const context = flatten(assertions.tradition_context_mentions ?? assertions.tradition_context_chain_positions);
  if (context) shown.push(['mentions by tradition (in the source)', context]);
  return {
    narrator_id: String(record.narrator_id),
    authority: String(record.authority) as NarratorAuthority,
    source_key: String(record.source_key),
    name_ar: text(record.name_ar),
    name_latin: text(record.name_latin),
    name_latin_basis: (text(record.name_latin_basis) as NameLatinBasis | null) ?? null,
    placeholder_reason: text(record.placeholder_reason),
    label_reason: text(record.label_reason),
    licence: String(record.licence ?? ''),
    asserted_by: String(record.asserted_by ?? ''),
    assertions: shown,
    name_forms: ((assertions.name_forms as Row[] | undefined) ?? []).map((form) => ({
      form: String(form.form ?? ''),
      type: String(form.type ?? ''),
      source: String(form.source ?? ''),
    })),
    name_source: text(assertions.name_source),
    external_ids: ((record.external_ids as Row[]) ?? []).map((item) => ({
      namespace: String(item.namespace),
      external_id: String(item.external_id),
      narrator_id: text(item.narrator_id),
    })),
    link_candidates: ((record.link_candidates as Row[]) ?? []).map(toLink),
  };
}

function toLink(item: Row): NarratorLinkCandidate {
  return {
    narrator_id: String(item.narrator_id),
    name: String(item.name ?? ''),
    name_ar: text(item.name_ar),
    authority: String(item.authority) as NarratorAuthority,
    basis: String(item.basis),
  };
}

/** External records that a link candidate proposes as this lexicon narrator (shown as candidates on its page). */
export async function getExternalLinkCandidates(narratorId: string): Promise<NarratorLinkCandidate[]> {
  const row = await oneRow<{ items: Row[] | null }>(sql`
    select json_agg(json_build_object('narrator_id', e.id, 'name', coalesce(e.name_latin, e.name), 'name_ar', e.name_ar,
                                      'authority', e.authority, 'basis', x.basis) order by e.id) as items
    from narrator_link_candidates x join narrators e on e.id = x.external_narrator_id and e.retired_at is null
    where x.rawi_narrator_id = ${narratorId} and x.retired_at is null
  `);
  return (row?.items ?? []).map(toLink);
}

/** One chain position a narrator is named at. */
export interface NarratorAppearance {
  hadith_id: string;
  tradition: HadithTraditionCode;
  work: string;
  reference: string;
  branch: number;
  position: number;
  surface_ar: string;
  name_latin: string | null;
  /** The mention's standing identity is this narrator, and what set it; null when it is a candidate only. */
  standing_basis: string | null;
  /** Every basis by which a source names this narrator at the position. */
  bases: IdentityBasis[];
}

const APPEARANCE_PAGE_SIZE = 25;

/**
 * Public chain positions naming this narrator, as a standing identity or a candidate, in source order (tradition, work,
 * report, branch, position), paged with a capped total.
 */
export async function getNarratorAppearances(narratorId: string, request?: PageRequest): Promise<Paginated<NarratorAppearance>> {
  const window = clampPage({ pageSize: APPEARANCE_PAGE_SIZE, ...request });
  const row = await oneRow<{ counted: number; items: Row[] | null }>(sql`
    -- Driven from the indexed base tables (narrator_id on both); the public gate is the join to public_hadiths and the
    -- live chain, as in public_chain_links. Filtering the public views by narrator took ~20 s for an Imam (8,900 rows).
    with named as materialized (
      select c.mention_id as id from chain_mention_candidates c where c.narrator_id = ${narratorId} and c.retired_at is null
      union
      select m.id from chain_mentions m where m.narrator_id = ${narratorId} and m.retired_at is null
    ),
    ordered as materialized (
      select m.id, m.hadith_id, ch.branch, m.position, h.collection_sort_key, h.hadith_no_int
      from named x
      join chain_mentions m on m.id = x.id and m.retired_at is null
      join chains ch on ch.id = m.chain_id and ch.retired_at is null
      join public_hadiths h on h.id = m.hadith_id
    ),
    page as (
      select o.* from ordered o
      order by o.collection_sort_key, o.hadith_no_int nulls last, o.hadith_id collate "C", o.branch, o.position
      limit ${window.limit} offset ${window.offset}
    )
    select
      (select count(*)::int from (select 1 from ordered limit ${COUNT_CAP + 1}) capped) as counted,
      (select json_agg(json_build_object(
                 'hadith_id', h.id, 'tradition', t.code, 'work', col.name, 'hadith_no', h.hadith_no, 'url', h.url,
                 'volume', h.volume, 'page_ref', h.page_ref, 'book_number', b.number, 'branch', l.branch,
                 'position', l.position, 'surface_ar', l.surface_ar, 'name_latin', l.name_latin,
                 'standing_basis', case when l.is_link and l.narrator_id = ${narratorId} then l.standing_basis end,
                 'bases', coalesce((select json_agg(distinct c.basis) from chain_mention_candidates c
                                    where c.mention_id = l.id and c.narrator_id = ${narratorId} and c.retired_at is null), '[]'::json))
               order by p.collection_sort_key, p.hadith_no_int nulls last, p.hadith_id collate "C", p.branch, p.position)
       from page p
       join public_chain_links l on l.id = p.id
       join public_hadiths h on h.id = l.hadith_id
       join collections col on col.id = h.collection_id
       join traditions t on t.id = h.tradition_id
       left join books b on b.id = h.book_id) as items
  `);
  const items = (row?.items ?? []).map((item): NarratorAppearance => ({
    hadith_id: String(item.hadith_id),
    tradition: String(item.tradition) as HadithTraditionCode,
    work: String(item.work),
    reference: reportReference({
      id: String(item.hadith_id),
      hadithNo: text(item.hadith_no),
      url: text(item.url),
      volume: text(item.volume),
      pageRef: text(item.page_ref),
      bookNumber: text(item.book_number),
    }),
    branch: Number(item.branch),
    position: Number(item.position),
    surface_ar: String(item.surface_ar),
    name_latin: text(item.name_latin),
    standing_basis: text(item.standing_basis),
    bases: ((item.bases as string[]) ?? []) as IdentityBasis[],
  }));
  return paginated(items, row?.counted ?? 0, window, true);
}
