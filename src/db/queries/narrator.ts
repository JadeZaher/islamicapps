/** Narrator reads: list and search, detail, network, typeahead (sections 8, 9.1). See src/db/queries/AGENTS.md §Narrators. */
import 'server-only';
import { sql, type SQL } from 'drizzle-orm';
import { norm } from '@/lib/attribution/classify-attribution';
import { hadithAssessmentsJson, verdictsJson, type VerdictMode } from './assessment';
import type {
  NarratorDetail,
  NarratorHadithSummary,
  NarratorLexicon,
  NarratorListItem,
  NarratorNetwork,
  NetworkPeer,
  Paginated,
} from './contracts';
import { groupAssessments, mapNarratorBio, mapNarratorListItem, mapVerdicts, narratorNames, text } from './mappers';
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
  toInt,
  toIso,
  type PageRequest,
} from './sql-helpers';
import { verdictModeFor, type ReadVisibility } from './visibility';
import heldBackFile from './lexicon-held-back.json';

/** Lexicon death years withheld on public pages (built by src/scripts/db/build-lexicon-held-back.ts). */
const HELD_BACK_GAP: Record<string, string> = {
  gross_conflict: 'differs by more than ten years',
  differs_by_exactly_100: 'differs by exactly a century',
  differ_3_10_years: 'differs by three to ten years',
};
const LEXICON_HELD_BACK = new Map<string, NarratorLexicon['held_back']>();
for (const item of heldBackFile.held) {
  const list = LEXICON_HELD_BACK.get(item.narrator_id) ?? [];
  const gap = HELD_BACK_GAP[item.comparison] ?? 'differs';
  list.push({ field: 'death_year', reason: `Ibn Hajar's Taqrib al-Tahdhib gives a year that ${gap}`, taqrib_entry: item.taqrib_entry });
  LEXICON_HELD_BACK.set(item.narrator_id, list);
}

export interface NarratorFilters {
  /** Canonical verdict enum value (the action maps legacy THIQA-style codes). */
  verdict?: string;
  /** Required with `verdict` on public pages. */
  tradition?: string;
  tabaqah?: string;
}

const NETWORK_LIMIT = 50;
const NARRATOR_HADITH_LIMIT = 100;
const TYPEAHEAD_LIMIT = 20;

/** Bio predicate on alias `b`: public pages read published bios only. */
function bioGate(mode: VerdictMode): SQL {
  return mode === 'public' ? sql`b.retired_at is null and b.status = 'published'` : sql`b.retired_at is null`;
}

/** Name predicate on alias `n`, or null when the term cannot match anything. */
function namePredicate(rawTerm: string): SQL | null {
  const term = cleanTerm(rawTerm, 100);
  if (hasArabic(term)) {
    const normalized = norm(term).trim();
    return normalized.length >= 2 ? sql`n.name_ar_normalized ilike ${containsPattern(normalized)}` : null;
  }
  if (term.length < 2) return null;
  return sql`n.name_en_folded ilike lower(unaccent(${containsPattern(term)}))`;
}

/** Paginated narrator list and search with a capped count. The Prophet is excluded. */
export async function listNarrators(
  rawTerm: string | undefined,
  filters: NarratorFilters = {},
  request?: PageRequest,
  mode: VerdictMode = 'public',
): Promise<Paginated<NarratorListItem>> {
  const window = clampPage(request, mode === 'public' ? undefined : Number.MAX_SAFE_INTEGER);
  const predicates: SQL[] = [
    sql`n.retired_at is null`,
    sql`not exists (select 1 from narrator_bios pb where pb.narrator_id = n.id and pb.retired_at is null and pb.is_prophet)`,
  ];
  if (rawTerm?.trim()) {
    const name = namePredicate(rawTerm);
    if (!name) return paginated([], 0, window, true);
    predicates.push(name);
  }
  if (filters.verdict) {
    const code = resolveTraditionCode(filters.tradition);
    if (code === null || (mode === 'public' && !code)) return paginated([], 0, window, true);
    predicates.push(sql`exists (
      select 1 from narrator_assessments a
      left join traditions vt on vt.id = a.tradition_id
      where a.narrator_id = n.id and a.retired_at is null and a.verdict::text = ${filters.verdict}
        ${code ? sql`and vt.code = ${code}` : sql``}
        ${mode === 'public' ? sql`and a.status = 'published'` : sql``})`);
  }
  if (filters.tabaqah) {
    predicates.push(sql`exists (select 1 from narrator_bios b where b.narrator_id = n.id and ${bioGate(mode)}
                               and b.tabaqah_class::text = ${filters.tabaqah})`);
  }

  const row = await oneRow<{ counted: number; items: Record<string, unknown>[] }>(sql`
    with filtered as not materialized (
      select n.id, coalesce(n.name_en, n.name) as display_name from narrators n where ${andAll(predicates)}
    ),
    page as (
      select f.id, f.display_name from filtered f order by f.display_name, f.id
      limit ${window.limit} offset ${window.offset}
    )
    select
      (select count(*)::int from (select 1 from filtered limit ${COUNT_CAP + 1}) capped) as counted,
      coalesce((
        select json_agg(json_build_object(
                 'id', n.id, 'name', n.name, 'name_en', n.name_en, 'name_ar', n.name_ar,
                 'tabaqah_class', b.tabaqah_class, 'geographic_region', b.geographic_region,
                 'verdicts', ${verdictsJson(sql`n.id`, mode)})
               order by p.display_name, p.id)
        from page p
        join narrators n on n.id = p.id
        left join narrator_bios b on b.narrator_id = n.id and ${bioGate(mode)}
      ), '[]'::json) as items
  `);
  return paginated((row?.items ?? []).map(mapNarratorListItem), row?.counted ?? 0, window, true);
}

/** Up to 20 narrators for a name typeahead; a plain array (section 9.1). */
export async function searchNarratorsTypeahead(rawTerm: string): Promise<NarratorListItem[]> {
  const name = namePredicate(rawTerm);
  if (!name) return [];
  const row = await oneRow<{ items: Record<string, unknown>[] | null }>(sql`
    select json_agg(json_build_object('id', x.id, 'name', x.name, 'name_en', x.name_en, 'name_ar', x.name_ar,
                                      'verdicts', '[]'::json) order by x.display_name, x.id) as items
    from (
      select n.id, n.name, n.name_en, n.name_ar, coalesce(n.name_en, n.name) as display_name
      from narrators n
      where n.retired_at is null and ${name}
      order by coalesce(n.name_en, n.name), n.id
      limit ${TYPEAHEAD_LIMIT}
    ) x
  `);
  return (row?.items ?? []).map(mapNarratorListItem);
}

/**
 * Narrator detail in one statement: identity, verdicts, bio, locations and the first 100 hadiths through the
 * narrator with a capped total. Public mode reads published rows and `public_chain_links` only, plus the lexicon's
 * dates and places (labelled on the page; held-back values removed).
 */
export async function getNarratorDetail(narratorId: string, mode: VerdictMode = 'public'): Promise<NarratorDetail | null> {
  const linkedHadiths =
    mode === 'public'
      ? sql`select distinct l.hadith_id from public_chain_links l where l.narrator_id = n.id and l.is_link`
      : sql`select distinct m.hadith_id from chain_mentions m where m.narrator_id = n.id and m.retired_at is null`;
  const hadithRelation = mode === 'public' ? sql`public_hadiths` : sql`hadiths`;

  const row = await oneRow<{ detail: Record<string, unknown> }>(sql`
    select json_build_object(
      'id', n.id, 'name', n.name, 'name_en', n.name_en, 'name_ar', n.name_ar,
      'verdicts', ${verdictsJson(sql`n.id`, mode)},
      'bio', (select row_to_json(b) from narrator_bios b where b.narrator_id = n.id and ${bioGate(mode)}),
      'lexicon', ${
        mode === 'public'
          ? sql`(select json_build_object('review_state', p.review_state, 'birth_year_hijri', p.birth_year_hijri,
                   'death_year_hijri', p.death_year_hijri, 'birth_year_gregorian', p.birth_year_gregorian,
                   'death_year_gregorian', p.death_year_gregorian, 'birth_place', p.birth_place, 'death_place', p.death_place,
                   'geographic_region', p.geographic_region, 'source_locator', p.source_locator)
                 from narrator_lexicon_profiles p where p.narrator_id = n.id and p.retired_at is null)`
          : sql`(select row_to_json(p) from narrator_lexicon_profiles p where p.narrator_id = n.id and p.retired_at is null)`
      },
      'locations', coalesce((
        select json_agg(json_build_object('id', loc.id, 'name', loc.name, 'name_arabic', loc.name_arabic,
                                          'relation', nl.relation) order by nl.relation, loc.name)
        from narrator_locations nl join locations loc on loc.id = nl.location_id and loc.retired_at is null
        where nl.narrator_id = n.id and nl.retired_at is null
      ), '[]'::json),
      'hadith_count', (select count(*)::int from (${linkedHadiths} limit ${COUNT_CAP + 1}) capped),
      'hadiths', coalesce((
        select json_agg(json_build_object(
                 'id', h.id, 'chapter_title', h.chapter_title, 'category', h.category, 'hadith_no', h.hadith_no,
                 'collection_name', col.name, 'tradition', t.code,
                 'assessments', ${hadithAssessmentsJson(sql`h.id`)})
               order by h.collection_sort_key, h.hadith_no_int nulls last, h.id)
        from (
          select h.id from ${hadithRelation} h
          where h.id in (${linkedHadiths}) ${mode === 'review' ? sql`and h.retired_at is null` : sql``}
          order by h.collection_sort_key, h.hadith_no_int nulls last, h.id
          limit ${NARRATOR_HADITH_LIMIT}
        ) firsts
        join ${hadithRelation} h on h.id = firsts.id
        join collections col on col.id = h.collection_id
        join traditions t on t.id = h.tradition_id
      ), '[]'::json)
    ) as detail
    from narrators n
    where n.id = ${narratorId} and n.retired_at is null
  `);
  if (!row) return null;
  const detail = row.detail;
  const counted = Number(detail.hadith_count ?? 0);
  const hadithItems: NarratorHadithSummary[] = ((detail.hadiths as Record<string, unknown>[]) ?? []).map((hadith) => {
    const chapter = text(hadith.chapter_title);
    const category = text(hadith.category);
    return {
      id: String(hadith.id),
      title: chapter ?? category,
      primary_topic: category,
      source: String(hadith.collection_name ?? ''),
      hadith_no: text(hadith.hadith_no),
      tradition: hadith.tradition as NarratorHadithSummary['tradition'],
      assessments: groupAssessments(hadith.assessments),
    };
  });
  const lexicon = detail.lexicon as Record<string, unknown> | null;
  return {
    id: String(detail.id),
    ...narratorNames(detail),
    verdicts: mapVerdicts(detail.verdicts),
    bio: mapNarratorBio(detail.bio),
    lexicon: lexicon ? mapLexicon(String(detail.id), lexicon, mode) : null,
    hadiths: paginated(hadithItems, counted, { page: 1, pageSize: NARRATOR_HADITH_LIMIT, limit: NARRATOR_HADITH_LIMIT, offset: 0 }, true),
    locations: ((detail.locations as Record<string, unknown>[]) ?? []).map((location) => ({
      id: String(location.id),
      name: String(location.name),
      name_arabic: text(location.name_arabic),
      relation: location.relation as 'born' | 'died' | 'resided',
    })),
  };
}

/** A Hijri year the lexicon records; 0 is not a year (the Hijri count has none), so it is dropped. */
function lexiconYear(value: unknown): number | null {
  const year = toInt(value);
  return year === 0 ? null : year;
}

/** Lexicon dates and places; on public pages the held-back death years are removed and the prose bio is never read. */
function mapLexicon(narratorId: string, lexicon: Record<string, unknown>, mode: VerdictMode): NarratorLexicon {
  const held = mode === 'public' ? (LEXICON_HELD_BACK.get(narratorId) ?? []) : [];
  const deathHeld = held.some((item) => item.field === 'death_year');
  return {
    review_state: String(lexicon.review_state),
    birth_year_hijri: lexiconYear(lexicon.birth_year_hijri),
    death_year_hijri: deathHeld ? null : lexiconYear(lexicon.death_year_hijri),
    birth_year_gregorian: toInt(lexicon.birth_year_gregorian),
    death_year_gregorian: deathHeld ? null : toInt(lexicon.death_year_gregorian),
    birth_place: text(lexicon.birth_place),
    death_place: text(lexicon.death_place),
    geographic_region: text(lexicon.geographic_region),
    bio: mode === 'public' ? null : text(lexicon.bio),
    source_locator: text(lexicon.source_locator),
    held_back: held,
  };
}

/** Narrator detail under a resolved visibility (curator preview reads unpublished verdicts, bios and every report). */
export async function getVisibleNarrator(narratorId: string, visibility: ReadVisibility): Promise<NarratorDetail | null> {
  return getNarratorDetail(narratorId, verdictModeFor(visibility));
}

/** Teachers and students from `narrator_transmissions`, strongest first, limited and counted (section 8). */
export async function getNarratorNetwork(narratorId: string): Promise<NarratorNetwork> {
  const peers = (direction: 'teacher' | 'student'): SQL => {
    const [self, peer] = direction === 'teacher' ? [sql`nt.student_id`, sql`nt.teacher_id`] : [sql`nt.teacher_id`, sql`nt.student_id`];
    return sql`coalesce((
      select json_agg(json_build_object('id', p.id, 'name', p.name, 'name_en', p.name_en, 'name_ar', p.name_ar,
                                        'hadith_count', x.hadith_count, 'temporal_plausibility', x.temporal_plausibility)
                      order by x.hadith_count desc, p.id)
      from (select ${peer} as peer_id, nt.hadith_count, nt.temporal_plausibility
            from narrator_transmissions nt where ${self} = ${narratorId}
            order by nt.hadith_count desc, ${peer} limit ${NETWORK_LIMIT}) x
      join narrators p on p.id = x.peer_id and p.retired_at is null
    ), '[]'::json)`;
  };
  const row = await oneRow<Record<string, unknown>>(sql`
    select ${peers('teacher')} as teachers,
           ${peers('student')} as students,
           (select count(*)::int from narrator_transmissions nt where nt.student_id = ${narratorId}) as teacher_total,
           (select count(*)::int from narrator_transmissions nt where nt.teacher_id = ${narratorId}) as student_total,
           v.attribution_disclaimer, v.network_refreshed_at
    from (select 1) one
    left join dataset_versions v on v.is_current
  `);
  const mapPeers = (value: unknown, relationship: 'teacher' | 'student'): NetworkPeer[] =>
    ((value as Record<string, unknown>[]) ?? []).map((peer) => {
      const names = narratorNames(peer);
      return {
        id: String(peer.id),
        name_english: names.name_english,
        name_arabic: names.name_arabic,
        relationship,
        hadith_count: Number(peer.hadith_count),
        temporal_plausibility: String(peer.temporal_plausibility),
      };
    });
  return {
    teachers: mapPeers(row?.teachers, 'teacher'),
    students: mapPeers(row?.students, 'student'),
    teacher_total: Number(row?.teacher_total ?? 0),
    student_total: Number(row?.student_total ?? 0),
    attribution_disclaimer: text(row?.attribution_disclaimer),
    network_refreshed_at: toIso(row?.network_refreshed_at),
  };
}
