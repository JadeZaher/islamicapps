/** Public hadith reads: browse, search, detail. Public views only (rule 9). See src/db/queries/AGENTS.md §Search. */
import 'server-only';
import { sql, type SQL } from 'drizzle-orm';
import { norm } from '@/lib/attribution/classify-attribution';
import { getSourceFilterValues } from '@/lib/constants/sources';
import { hadithAssessmentsJson } from './assessment';
import type { HadithDetail, HadithListItem, Paginated } from './contracts';
import { groupAssessments, mapHadithListItem, text } from './mappers';
import {
  andAll,
  clampPage,
  cleanTerm,
  containsPattern,
  COUNT_CAP,
  hasArabic,
  oneRow,
  paginated,
  resolveTraditionCode,
  type PageRequest,
  type PageWindow,
} from './sql-helpers';
import { hadithRelationsFor, PUBLIC_VISIBILITY, type ReadVisibility } from './visibility';

export interface HadithFilters {
  tradition?: string;
  source?: string;
  chapter?: string;
}

/** Labels shared by several Imami works; they filter on `source_display_label`, never on a collection. */
const AMBIGUOUS_SOURCE_LABELS = new Set(['Al-Amālī', 'Kitāb al-Ghayba']);

/** Which relations a hadith list reads: the public views, or the live base tables in reviewer mode. */
export interface HadithRelations {
  hadiths: SQL;
  translations: SQL;
  /** Extra predicate on the hadith alias `h` (reviewer mode adds `retired_at is null`). */
  liveHadith: SQL;
  liveTranslation: SQL;
}

export const PUBLIC_RELATIONS: HadithRelations = hadithRelationsFor(PUBLIC_VISIBILITY);

/** Minimum normalized length for a trigram search (section 7.2). */
const MIN_TRIGRAM_TERM = 3;

/** The union of index-driven ID sets for a term (section 7.3), or null when no branch is usable. */
function matchedIds(term: string, relations: HadithRelations): SQL | null {
  const branches: SQL[] = [];
  if (term.length >= MIN_TRIGRAM_TERM) {
    const pattern = containsPattern(term);
    branches.push(sql`select id from ${relations.hadiths} where chapter_title_folded ilike lower(unaccent(${pattern}))`);
    branches.push(sql`select id from ${relations.hadiths} where category_folded ilike lower(unaccent(${pattern}))`);
  }
  if (/[A-Za-z0-9]/.test(term)) {
    branches.push(
      sql`select hadith_id as id from ${relations.translations}
          where language = 'en' and text_tsv @@ websearch_to_tsquery('english', ${term})`,
    );
  }
  if (hasArabic(term)) {
    const normalized = norm(term).trim();
    if (normalized.length >= MIN_TRIGRAM_TERM) {
      branches.push(sql`select id from ${relations.hadiths} where text_ar_normalized ilike ${containsPattern(normalized)}`);
    }
  }
  if (branches.length === 0) return null;
  return sql.join(branches, sql` union `);
}

/** Filter predicates on aliases `h` (hadith), `t` (tradition), `col` (collection); null means "matches nothing". */
export function filterPredicates(filters: HadithFilters): SQL[] | null {
  const predicates: SQL[] = [];
  const code = resolveTraditionCode(filters.tradition);
  if (code === null) return null;
  if (code) predicates.push(sql`t.code = ${code}`);
  const source = filters.source?.trim();
  if (source) {
    if (AMBIGUOUS_SOURCE_LABELS.has(source)) predicates.push(sql`h.source_display_label = ${source}`);
    else predicates.push(sql`col.name = any(${sql.param([...getSourceFilterValues(source)])}::text[])`);
  }
  const chapter = filters.chapter?.trim();
  if (chapter) predicates.push(sql`h.category = ${chapter}`);
  return predicates;
}

/** json_build_object of the list contract keys for alias `h` with `col`, `t` and translation `tr`. */
export const HADITH_LIST_OBJECT = sql`json_build_object(
  'id', h.id, 'record_id', h.record_id, 'chapter_title', h.chapter_title, 'chapter_no', h.chapter_no,
  'category', h.category, 'volume', h.volume, 'hadith_no', h.hadith_no, 'collection_id', h.collection_id,
  'collection_name', col.name, 'source_display_label', h.source_display_label, 'tradition', t.code,
  'text_ar', h.text_ar, 'matn_ar', h.matn_ar, 'english_text', tr.text, 'english_state', tr.state,
  'source_text_status', h.source_text_status, 'chain_status', h.chain_status, 'grading_status', h.grading_status)`;

/**
 * One statement for a list page: a capped count and the page rows, ordered by the single ordering
 * contract `collection_sort_key, hadith_no_int nulls last, id` (section 7.3).
 */
export async function listHadithPage(
  relations: HadithRelations,
  filters: HadithFilters,
  rawTerm: string | undefined,
  window: PageWindow,
): Promise<Paginated<HadithListItem>> {
  const term = cleanTerm(rawTerm);
  const predicates = filterPredicates(filters);
  const matched = term ? matchedIds(term, relations) : undefined;
  if (predicates === null || matched === null) return paginated([], 0, window, true);

  const row = await oneRow<{ counted: number; items: Record<string, unknown>[] }>(sql`
    with filtered as not materialized (
      select h.id, h.collection_sort_key, h.hadith_no_int
      from ${relations.hadiths} h
      join traditions t on t.id = h.tradition_id
      join collections col on col.id = h.collection_id
      ${matched ? sql`join (${matched}) m on m.id = h.id` : sql``}
      where ${andAll([relations.liveHadith, ...predicates])}
    ),
    page as (
      select f.id, f.collection_sort_key, f.hadith_no_int
      from filtered f
      order by f.collection_sort_key, f.hadith_no_int nulls last, f.id
      limit ${window.limit} offset ${window.offset}
    )
    select
      (select count(*)::int from (select 1 from filtered limit ${COUNT_CAP + 1}) capped) as counted,
      coalesce((
        select json_agg(${HADITH_LIST_OBJECT} order by p.collection_sort_key, p.hadith_no_int nulls last, p.id)
        from page p
        join ${relations.hadiths} h on h.id = p.id
        join traditions t on t.id = h.tradition_id
        join collections col on col.id = h.collection_id
        left join lateral (
          select x.text, x.state from ${relations.translations} x
          where x.hadith_id = h.id and x.language = 'en' and ${relations.liveTranslation}
          limit 1
        ) tr on true
      ), '[]'::json) as items
  `);
  return paginated((row?.items ?? []).map(mapHadithListItem), row?.counted ?? 0, window, true);
}

/** Public browse and search (searchHadiths / getAllHadiths). Unknown tradition gives an empty page. */
export async function searchPublicHadiths(
  term: string | undefined,
  filters: HadithFilters = {},
  request?: PageRequest,
): Promise<Paginated<HadithListItem>> {
  return searchVisibleHadiths(term, filters, request, PUBLIC_VISIBILITY);
}

/** Browse and search under a resolved visibility (public views, or every live row in curator preview). */
export async function searchVisibleHadiths(
  term: string | undefined,
  filters: HadithFilters,
  request: PageRequest | undefined,
  visibility: ReadVisibility,
): Promise<Paginated<HadithListItem>> {
  return listHadithPage(hadithRelationsFor(visibility), filters, term, clampPage(request));
}

/** SQL for one hadith's detail object under the given relations, or no row when unknown. */
export function hadithDetailStatement(relations: HadithRelations, hadithId: string): SQL {
  return sql`
    select json_build_object(
      'list', ${HADITH_LIST_OBJECT},
      'sanad', h.sanad, 'sanad_confidence', h.sanad_confidence, 'narration_level', h.narration_level,
      'chain_type', h.chain_type, 'school', h.school, 'attributed_to', h.attributed_to, 'url', h.url,
      'page_ref', h.page_ref, 'arabic_sha256', h.arabic_sha256,
      'matn_en', tr.matn_text, 'english_source', tr.source, 'translator', tr.translator,
      'assessments', ${hadithAssessmentsJson(sql`h.id`)}
    ) as detail
    from ${relations.hadiths} h
    join traditions t on t.id = h.tradition_id
    join collections col on col.id = h.collection_id
    left join lateral (
      select x.text, x.state, x.matn_text, x.source, x.translator from ${relations.translations} x
      where x.hadith_id = h.id and x.language = 'en' and ${relations.liveTranslation}
      limit 1
    ) tr on true
    where h.id = ${hadithId} and ${relations.liveHadith}
  `;
}

/** Maps a detail row into the HadithDetail contract. */
export function mapHadithDetail(detail: Record<string, unknown>): HadithDetail {
  const list = mapHadithListItem(detail.list as Record<string, unknown>);
  const sanad = text(detail.sanad);
  const matnEn = text(detail.matn_en);
  return {
    ...list,
    sanad,
    isnad_arabic: sanad,
    chain_text_arabic: sanad,
    sanad_confidence: text(detail.sanad_confidence),
    matn_en: matnEn,
    narration_level: text(detail.narration_level),
    chain_type: text(detail.chain_type),
    school: text(detail.school),
    attributed_to: text(detail.attributed_to),
    url: text(detail.url),
    page_ref: text(detail.page_ref),
    arabic_sha256: String(detail.arabic_sha256),
    english_attribution: list.english_state
      ? { state: list.english_state, source: text(detail.english_source), translator: text(detail.translator) }
      : null,
    variations: [
      {
        id: `${list.id}::synthesized`,
        text_arabic: list.matn_ar ?? list.text_ar,
        text_english: matnEn ?? list.text_en,
        source: 'hadith_node',
      },
    ],
    assessments: groupAssessments(detail.assessments),
  };
}

/** Public hadith detail; null for an unknown or unpublished ID so the page can call notFound(). */
export async function getPublicHadith(hadithId: string): Promise<HadithDetail | null> {
  return getVisibleHadith(hadithId, PUBLIC_VISIBILITY);
}

/** Hadith detail under a resolved visibility; null when unknown or not visible to it. */
export async function getVisibleHadith(hadithId: string, visibility: ReadVisibility): Promise<HadithDetail | null> {
  const row = await oneRow<{ detail: Record<string, unknown> }>(hadithDetailStatement(hadithRelationsFor(visibility), hadithId));
  return row ? mapHadithDetail(row.detail) : null;
}
