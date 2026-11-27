/**
 * Time and place for a narrator and for a family of chains: lifespans as ranges, generation, places, the eras and
 * events a life touches, and chronological gaps between consecutive transmitters. One statement per section;
 * interval relations are computed at read time and never stored. Public visibility gets only published, cited data;
 * curator visibility (minted only by src/lib/auth/visibility.ts) gets every live row, labelled. See src/db/queries/AGENTS.md §Time and place.
 */
import 'server-only';
import { sql, type SQL } from 'drizzle-orm';
import type {
  ChainFamilyTimeline,
  ChainIdentity,
  ChainTimeline,
  ChainTransmitter,
  DatumBasis,
  EpochEntry,
  EventEntry,
  ExternalTraditionParallelEntry,
  GenerationClaim,
  Lifespan,
  NarratorAffiliationEntry,
  NarratorEventEntry,
  NarratorResidenceEntry,
  NarratorTimeline,
  PlaceClaim,
  PlaceSnapshotEntry,
  TimelineAudience,
  TimelineCitation,
  TimelineTemporalAssertion,
  TimelineTrackCategory,
  TimelineTrackEntry,
} from './timeline-contracts';
import {
  buildLifespan,
  chronologicalGaps,
  generationFromTabaqahClass,
  historyBasis,
  lexiconPlace,
  parseLexiconGeneration,
  relationToLife,
  spanOfLifespans,
  yearClaim,
} from './timeline-rules';
import { oneRow } from './sql-helpers';
import { hadithRelationsFor, isCuratorVisibility, PUBLIC_VISIBILITY, type ReadVisibility } from './visibility';

function audienceFor(visibility: ReadVisibility): TimelineAudience {
  return isCuratorVisibility(visibility) ? 'review' : 'public';
}

/** At most this many reports are aligned on one axis. */
export const MAX_FAMILY_REPORTS = 12;

const VERIFIED_RESOLUTIONS = sql`('source_index', 'human_verified', 'derived_relation_verified')`;
const REVIEWED_CITATION = sql`('human_verified', 'source_verified')`;

let epochTableSeen: { available: boolean; checkedAt: number } | undefined;
let gridTableSeen: { available: boolean; checkedAt: number } | undefined;
const EPOCH_RECHECK_MS = 60_000;

/** Whether `epochs` exists here (it ships with a pending migration, src/db/ops/pending/). Cached once present. */
export async function epochsAvailable(): Promise<boolean> {
  if (epochTableSeen && (epochTableSeen.available || Date.now() - epochTableSeen.checkedAt < EPOCH_RECHECK_MS)) {
    return epochTableSeen.available;
  }
  const row = await oneRow<{ available: boolean }>(sql`select to_regclass('epochs') is not null as available`);
  epochTableSeen = { available: row?.available === true, checkedAt: Date.now() };
  return epochTableSeen.available;
}

/** Whether migration 0025 (`timeline_tracks`, `place_snapshots`, etc.) is present in this database. */
export async function timelinesGridAvailable(): Promise<boolean> {
  if (gridTableSeen && (gridTableSeen.available || Date.now() - gridTableSeen.checkedAt < EPOCH_RECHECK_MS)) {
    return gridTableSeen.available;
  }
  const row = await oneRow<{ available: boolean }>(sql`select to_regclass('timeline_tracks') is not null as available`);
  gridTableSeen = { available: row?.available === true, checkedAt: Date.now() };
  return gridTableSeen.available;
}

/**
 * Per-narrator facts for the given id list (a CTE body over `ids(narrator_id)`). Public: no lexicon field, a bio
 * only when published with a live reviewed citation, places only at reviewed locations.
 */
function narratorFacts(audience: TimelineAudience): SQL {
  const review = audience === 'review';
  return sql`
    select n.id as narrator_id, coalesce(n.name_en, n.name) as name_en, n.name_ar,
           ${review ? sql`p.birth_year_hijri` : sql`null::int`} as lexicon_birth,
           ${review ? sql`p.death_year_hijri` : sql`null::int`} as lexicon_death,
           ${review ? sql`p.lexicon_grade_label` : sql`null::text`} as lexicon_generation,
           ${review ? sql`p.birth_place` : sql`null::text`} as lexicon_birth_place,
           ${review ? sql`p.death_place` : sql`null::text`} as lexicon_death_place,
           b.death_year_hijri as bio_death, b.tabaqah_class::text as bio_tabaqah, b.geographic_region as bio_region,
           (b.narrator_id is not null and b.status = 'published' and bc.id is not null) as bio_cited,
           (select coalesce(json_agg(json_build_object('name', l.name, 'relation', nl.relation, 'location_id', l.id,
                                                       'verification_status', l.verification_status)
                                     order by nl.relation, l.name), '[]'::json)
            from narrator_locations nl
            join locations l on l.id = nl.location_id and l.retired_at is null
            where nl.narrator_id = n.id and nl.retired_at is null
              ${review ? sql`` : sql`and l.verification_status in ${REVIEWED_CITATION}`}) as linked_places
    from ids
    join narrators n on n.id = ids.narrator_id and n.retired_at is null
    left join narrator_lexicon_profiles p on p.narrator_id = n.id and p.retired_at is null
    left join narrator_bios b
      on b.narrator_id = n.id and b.retired_at is null
     ${review ? sql`` : sql`and b.status = 'published' and exists (
           select 1 from citations pc where pc.id = b.citation_id and pc.retired_at is null and pc.review_state in ${REVIEWED_CITATION})`}
    left join citations bc on bc.id = b.citation_id and bc.retired_at is null and bc.review_state in ${REVIEWED_CITATION}`;
}

/** Known, drawable years of the facts (0 excluded) as one [lo, hi] window, for prefiltering eras and events. */
const WINDOW = sql`
  select min(y) as lo, max(y) as hi
  from facts f, lateral (values (f.lexicon_birth), (f.lexicon_death), (f.bio_death)) v(y)
  where y is not null and y <> 0`;

function temporalAssertionsSubquery(audience: TimelineAudience, subjectColumn: 'event_id' | 'epoch_id'): SQL {
  const review = audience === 'review';
  const col = subjectColumn === 'event_id' ? sql`ta.event_id` : sql`ta.epoch_id`;
  return sql`
    coalesce((
      select json_agg(json_build_object(
        'id', ta.id,
        'predicate', ta.predicate,
        'year_min', ta.year_min,
        'year_max', ta.year_max,
        'statement_en', ta.statement_en,
        'stated_ar', ta.stated_ar,
        'review_state', ta.review_state,
        'citation', case when tc.id is not null then json_build_object(
          'id', tc.id,
          'work_title', tbw.title,
          'work_title_ar', tbw.title_ar,
          'author', tbw.author,
          'edition', nullif(concat_ws(', ', ted.editor, ted.publisher, ted.year), ''),
          'volume', tc.volume,
          'page', tc.page,
          'locator', tc.locator,
          'url', coalesce(nullif(trim(tc.url), ''), nullif(trim(ted.url), '')),
          'review_state', tc.review_state
        ) end
      ) order by ta.year_min nulls last, ta.id)
      from temporal_assertions ta
      left join citations tc on tc.id = ta.citation_id and tc.retired_at is null
        ${review ? sql`` : sql`and tc.review_state in ${REVIEWED_CITATION}`}
      left join bibliographic_works tbw on tbw.id = tc.work_id and tbw.retired_at is null
      left join editions ted on ted.id = tc.edition_id and ted.retired_at is null
      where ${col} = e.id and ta.retired_at is null
        ${review ? sql`` : sql`and ta.review_state in ${REVIEWED_CITATION}`}
    ), '[]'::json)`;
}

function eventsWithin(audience: TimelineAudience, withGrid = false): SQL {
  const review = audience === 'review';
  const source = review
    ? sql`(select e.*, e.start_year_hijri as event_start, coalesce(e.end_year_hijri, e.start_year_hijri) as event_end
           from historical_events e where e.retired_at is null and e.start_year_hijri is not null)`
    : sql`published_historical_events`;
  return sql`
    select coalesce(json_agg(json_build_object(
             'id', e.id, 'name', e.title, 'name_arabic', e.title_arabic, 'start', e.event_start, 'end', e.event_end,
             'category', e.category, 'location_name', e.location_name, 'location_id', e.location_id,
             'description', e.description, 'significance', e.significance,
             'track_id', ${withGrid ? sql`tt.id` : sql`null::text`},
             'track_slug', ${withGrid ? sql`tt.slug` : sql`null::text`},
             'track_category', ${withGrid ? sql`tt.category` : sql`null::text`},
             'verification_status', e.verification_status, 'publication_ready', e.publication_ready,
             'citation_source', e.citation_source, 'citation_locator', e.citation_locator, 'citation_url', e.citation_url,
             'citation', case when c.id is not null then json_build_object(
               'id', c.id, 'work_title', bw.title, 'work_title_ar', bw.title_ar, 'author', bw.author,
               'edition', nullif(concat_ws(', ', ed.editor, ed.publisher, ed.year), ''),
               'volume', c.volume, 'page', c.page, 'locator', c.locator,
               'url', coalesce(nullif(trim(c.url), ''), nullif(trim(ed.url), '')),
               'review_state', c.review_state
             ) end,
             'temporal_assertions', (${temporalAssertionsSubquery(audience, 'event_id')})
           ) order by e.event_start, e.id), '[]'::json)
    from ${source} e
    join window_bounds w on w.lo is not null and e.event_end >= w.lo and e.event_start <= w.hi
    ${withGrid ? sql`left join historical_events he on he.id = e.id and he.retired_at is null
    left join timeline_tracks tt on tt.id = he.track_id and tt.retired_at is null` : sql``}
    left join citations c on c.id = e.citation_id and c.retired_at is null
      ${review ? sql`` : sql`and c.review_state in ${REVIEWED_CITATION}`}
    left join bibliographic_works bw on bw.id = c.work_id and bw.retired_at is null
    left join editions ed on ed.id = c.edition_id and ed.retired_at is null`;
}

function timelineTracksQuery(): SQL {
  return sql`
    select coalesce(json_agg(json_build_object(
             'id', t.id, 'slug', t.slug, 'title', t.title, 'category', t.category, 'scope', t.scope,
             'description', t.description
           ) order by t.category, t.slug), '[]'::json)
    from timeline_tracks t
    where t.retired_at is null`;
}

function narratorResidencesQuery(audience: TimelineAudience): SQL {
  const review = audience === 'review';
  return sql`
    select coalesce(json_agg(json_build_object(
             'id', nr.id, 'narrator_id', nr.narrator_id, 'narrator_name', coalesce(n.name_en, n.name),
             'location_id', nr.location_id, 'location_name', l.name,
             'year_min', nr.year_min, 'year_max', nr.year_max, 'precision', nr.precision,
             'role', nr.role, 'review_state', nr.review_state,
             'citation', case when c.id is not null then json_build_object(
               'id', c.id, 'work_title', bw.title, 'work_title_ar', bw.title_ar, 'author', bw.author,
               'edition', nullif(concat_ws(', ', ed.editor, ed.publisher, ed.year), ''),
               'volume', c.volume, 'page', c.page, 'locator', c.locator,
               'url', coalesce(nullif(trim(c.url), ''), nullif(trim(ed.url), '')),
               'review_state', c.review_state
             ) end
           ) order by nr.year_min nulls last, nr.id), '[]'::json)
    from narrator_residences nr
    join ids on ids.narrator_id = nr.narrator_id
    join narrators n on n.id = nr.narrator_id and n.retired_at is null
    join locations l on l.id = nr.location_id and l.retired_at is null
    left join citations c on c.id = nr.citation_id and c.retired_at is null
      ${review ? sql`` : sql`and c.review_state in ${REVIEWED_CITATION}`}
    left join bibliographic_works bw on bw.id = c.work_id and bw.retired_at is null
    left join editions ed on ed.id = c.edition_id and ed.retired_at is null
    where nr.retired_at is null
      ${review ? sql`` : sql`and nr.review_state in ${REVIEWED_CITATION} and c.id is not null`}`;
}

function narratorAffiliationsQuery(audience: TimelineAudience): SQL {
  const review = audience === 'review';
  return sql`
    select coalesce(json_agg(json_build_object(
             'id', na.id, 'narrator_id', na.narrator_id, 'narrator_name', coalesce(n.name_en, n.name),
             'kind', na.kind, 'label', na.label, 'note', na.note, 'review_state', na.review_state,
             'citation', case when c.id is not null then json_build_object(
               'id', c.id, 'work_title', bw.title, 'work_title_ar', bw.title_ar, 'author', bw.author,
               'edition', nullif(concat_ws(', ', ed.editor, ed.publisher, ed.year), ''),
               'volume', c.volume, 'page', c.page, 'locator', c.locator,
               'url', coalesce(nullif(trim(c.url), ''), nullif(trim(ed.url), '')),
               'review_state', c.review_state
             ) end
           ) order by na.kind, na.label, na.id), '[]'::json)
    from narrator_affiliations na
    join ids on ids.narrator_id = na.narrator_id
    join narrators n on n.id = na.narrator_id and n.retired_at is null
    left join citations c on c.id = na.citation_id and c.retired_at is null
      ${review ? sql`` : sql`and c.review_state in ${REVIEWED_CITATION}`}
    left join bibliographic_works bw on bw.id = c.work_id and bw.retired_at is null
    left join editions ed on ed.id = c.edition_id and ed.retired_at is null
    where na.retired_at is null
      ${review ? sql`` : sql`and na.review_state in ${REVIEWED_CITATION} and c.id is not null`}`;
}

function placeSnapshotsWithin(audience: TimelineAudience): SQL {
  const review = audience === 'review';
  return sql`
    select coalesce(json_agg(json_build_object(
             'id', ps.id, 'location_id', ps.location_id, 'location_name', l.name,
             'year_min', ps.year_min, 'year_max', ps.year_max, 'precision', ps.precision,
             'polity_or_ruler', ps.polity_or_ruler, 'dominant_schools', ps.dominant_schools,
             'religious_communities', ps.religious_communities, 'languages', ps.languages,
             'ethnographic_notes', ps.ethnographic_notes, 'review_state', ps.review_state,
             'citation', case when c.id is not null then json_build_object(
               'id', c.id, 'work_title', bw.title, 'work_title_ar', bw.title_ar, 'author', bw.author,
               'edition', nullif(concat_ws(', ', ed.editor, ed.publisher, ed.year), ''),
               'volume', c.volume, 'page', c.page, 'locator', c.locator,
               'url', coalesce(nullif(trim(c.url), ''), nullif(trim(ed.url), '')),
               'review_state', c.review_state
             ) end
           ) order by ps.year_min nulls last, l.name, ps.id), '[]'::json)
    from place_snapshots ps
    join locations l on l.id = ps.location_id and l.retired_at is null
    join window_bounds w on w.lo is not null
      and (ps.year_max is null or ps.year_max >= w.lo)
      and (ps.year_min is null or ps.year_min <= w.hi)
    left join citations c on c.id = ps.citation_id and c.retired_at is null
      ${review ? sql`` : sql`and c.review_state in ${REVIEWED_CITATION}`}
    left join bibliographic_works bw on bw.id = c.work_id and bw.retired_at is null
    left join editions ed on ed.id = c.edition_id and ed.retired_at is null
    where ps.retired_at is null
      ${review ? sql`` : sql`and ps.review_state in ${REVIEWED_CITATION} and c.id is not null`}
      and (
        exists (select 1 from narrator_residences nr join ids on ids.narrator_id = nr.narrator_id where nr.location_id = ps.location_id and nr.retired_at is null)
        or exists (select 1 from narrator_locations nl join ids on ids.narrator_id = nl.narrator_id where nl.location_id = ps.location_id and nl.retired_at is null)
      )`;
}

function externalParallelsForHadiths(audience: TimelineAudience): SQL {
  const review = audience === 'review';
  return sql`
    select coalesce(json_agg(json_build_object(
             'id', ep.id, 'hadith_id', ep.hadith_id, 'tradition_source', ep.tradition_source,
             'relation_type', ep.relation_type, 'source_work', ep.source_work,
             'locator', ep.locator, 'note', ep.note, 'review_state', ep.review_state,
             'citation', case when c.id is not null then json_build_object(
               'id', c.id, 'work_title', bw.title, 'work_title_ar', bw.title_ar, 'author', bw.author,
               'edition', nullif(concat_ws(', ', ed.editor, ed.publisher, ed.year), ''),
               'volume', c.volume, 'page', c.page, 'locator', c.locator,
               'url', coalesce(nullif(trim(c.url), ''), nullif(trim(ed.url), '')),
               'review_state', c.review_state
             ) end
           ) order by ep.tradition_source, ep.source_work, ep.id), '[]'::json)
    from external_tradition_parallels ep
    join requested r on r.hadith_id = ep.hadith_id
    left join citations c on c.id = ep.citation_id and c.retired_at is null
      ${review ? sql`` : sql`and c.review_state in ${REVIEWED_CITATION}`}
    left join bibliographic_works bw on bw.id = c.work_id and bw.retired_at is null
    left join editions ed on ed.id = c.edition_id and ed.retired_at is null
    where ep.retired_at is null
      ${review ? sql`` : sql`and ep.review_state in ${REVIEWED_CITATION} and c.id is not null`}`;
}

function epochsWithin(audience: TimelineAudience): SQL {
  const review = audience === 'review';
  const source = review
    ? sql`(select e.*, e.start_year_hijri as epoch_start, coalesce(e.end_year_hijri_latest, e.end_year_hijri) as epoch_end
           from epochs e where e.retired_at is null and e.start_year_hijri is not null)`
    : sql`published_epochs`;
  return sql`
    select coalesce(json_agg(json_build_object(
             'id', e.id, 'name', e.name, 'name_arabic', e.name_arabic, 'start', e.epoch_start, 'end', e.epoch_end,
             'start_latest', e.start_year_hijri_latest, 'end_earliest', case when e.end_year_hijri_latest is not null then e.end_year_hijri end,
             'boundary_note', e.boundary_note, 'parent_id', e.parent_epoch_id, 'tradition_context', e.tradition_context,
             'alternate_names', e.alternate_names, 'overview', e.overview,
             'verification_status', e.verification_status, 'publication_ready', e.publication_ready,
             'citation', case when c.id is not null then json_build_object(
               'id', c.id, 'work_title', bw.title, 'work_title_ar', bw.title_ar, 'author', bw.author,
               'edition', nullif(concat_ws(', ', ed.editor, ed.publisher, ed.year), ''),
               'volume', c.volume, 'page', c.page, 'locator', c.locator,
               'url', coalesce(nullif(trim(c.url), ''), nullif(trim(ed.url), '')),
               'review_state', c.review_state
             ) end,
             'temporal_assertions', (${temporalAssertionsSubquery(audience, 'epoch_id')})
           ) order by e.epoch_start, e.parent_epoch_id nulls first, e.id), '[]'::json)
    from ${source} e
    join window_bounds w on w.lo is not null and (e.epoch_end is null or e.epoch_end >= w.lo) and e.epoch_start <= w.hi
    left join citations c on c.id = e.citation_id and c.retired_at is null
      ${review ? sql`` : sql`and c.review_state in ${REVIEWED_CITATION}`}
    left join bibliographic_works bw on bw.id = c.work_id and bw.retired_at is null
    left join editions ed on ed.id = c.edition_id and ed.retired_at is null`;
}

function narratorEventsFor(narratorId: string, audience: TimelineAudience): SQL {
  const review = audience === 'review';
  const eventSource = review
    ? sql`(select e.*, e.start_year_hijri as event_start, coalesce(e.end_year_hijri, e.start_year_hijri) as event_end
           from historical_events e where e.retired_at is null and e.start_year_hijri is not null)`
    : sql`published_historical_events`;
  return sql`
    select coalesce(json_agg(json_build_object(
             'id', ne.id,
             'event_id', ne.event_id,
             'role', ne.role,
             'stated_ar', ne.stated_ar,
             'citation', case when nc.id is not null then json_build_object(
               'id', nc.id, 'work_title', nbw.title, 'work_title_ar', nbw.title_ar, 'author', nbw.author,
               'edition', nullif(concat_ws(', ', ned.editor, ned.publisher, ned.year), ''),
               'volume', nc.volume, 'page', nc.page, 'locator', nc.locator,
               'url', coalesce(nullif(trim(nc.url), ''), nullif(trim(ned.url), '')),
               'review_state', nc.review_state
             ) end,
             'event', json_build_object(
               'id', e.id, 'name', e.title, 'name_arabic', e.title_arabic, 'start', e.event_start, 'end', e.event_end,
               'category', e.category, 'location_name', e.location_name, 'location_id', e.location_id,
               'description', e.description, 'significance', e.significance,
               'verification_status', e.verification_status, 'publication_ready', e.publication_ready,
               'citation_source', e.citation_source, 'citation_locator', e.citation_locator, 'citation_url', e.citation_url,
               'citation', case when ec.id is not null then json_build_object(
                 'id', ec.id, 'work_title', ebw.title, 'work_title_ar', ebw.title_ar, 'author', ebw.author,
                 'edition', nullif(concat_ws(', ', eed.editor, eed.publisher, eed.year), ''),
                 'volume', ec.volume, 'page', ec.page, 'locator', ec.locator,
                 'url', coalesce(nullif(trim(ec.url), ''), nullif(trim(eed.url), '')),
                 'review_state', ec.review_state
               ) end,
               'temporal_assertions', (${temporalAssertionsSubquery(audience, 'event_id')})
             )
           ) order by e.event_start, ne.id), '[]'::json)
    from narrator_events ne
    join ${eventSource} e on e.id = ne.event_id
    left join citations nc on nc.id = ne.citation_id and nc.retired_at is null
      ${review ? sql`` : sql`and nc.review_state in ${REVIEWED_CITATION}`}
    left join bibliographic_works nbw on nbw.id = nc.work_id and nbw.retired_at is null
    left join editions ned on ned.id = nc.edition_id and ned.retired_at is null
    left join citations ec on ec.id = e.citation_id and ec.retired_at is null
      ${review ? sql`` : sql`and ec.review_state in ${REVIEWED_CITATION}`}
    left join bibliographic_works ebw on ebw.id = ec.work_id and ebw.retired_at is null
    left join editions eed on eed.id = ec.edition_id and eed.retired_at is null
    where ne.narrator_id = ${narratorId} and ne.retired_at is null
      ${review ? sql`` : sql`and (ne.citation_id is null or nc.id is not null)`}`;
}

type Row = Record<string, unknown>;

function int(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? Math.trunc(parsed) : null;
}

function textOrNull(value: unknown): string | null {
  const text = typeof value === 'string' ? value.trim() : '';
  return text === '' ? null : text;
}

interface NarratorFacts {
  narrator_id: string;
  name_en: string | null;
  name_ar: string | null;
  lifespan: Lifespan;
  generation: GenerationClaim[];
  places: PlaceClaim[];
}

/** Builds the claims from one facts row; each claim keeps its own basis, nothing is merged into one value. */
function toFacts(row: Row): NarratorFacts {
  const bioBasis: DatumBasis = row.bio_cited === true ? 'bio_cited' : 'bio_uncited';
  const linked = Array.isArray(row.linked_places) ? (row.linked_places as Row[]) : [];
  const places: Array<PlaceClaim | null> = [
    row.bio_region ? { place: String(row.bio_region), relation: 'region', basis: bioBasis, location_id: null } : null,
    lexiconPlace(textOrNull(row.lexicon_birth_place), 'born'),
    lexiconPlace(textOrNull(row.lexicon_death_place), 'died'),
    ...linked.map((place): PlaceClaim => ({
      place: String(place.name),
      relation: place.relation as PlaceClaim['relation'],
      basis: historyBasis({
        verification_status: String(place.verification_status),
        publication_ready: place.verification_status === 'human_verified' || place.verification_status === 'source_verified',
      }),
      location_id: String(place.location_id),
    })),
  ];
  return {
    narrator_id: String(row.narrator_id),
    name_en: textOrNull(row.name_en),
    name_ar: textOrNull(row.name_ar),
    lifespan: buildLifespan([
      yearClaim('birth', int(row.lexicon_birth), 'lexicon_uncited'),
      yearClaim('death', int(row.lexicon_death), 'lexicon_uncited'),
      yearClaim('death', int(row.bio_death), bioBasis),
    ]),
    generation: [generationFromTabaqahClass(textOrNull(row.bio_tabaqah), bioBasis), parseLexiconGeneration(textOrNull(row.lexicon_generation), 'lexicon_uncited')]
      .filter((claim): claim is GenerationClaim => claim !== null),
    places: places.filter((place): place is PlaceClaim => place !== null),
  };
}

function toCitation(raw: unknown, fallback?: { source?: unknown; locator?: unknown; url?: unknown }): TimelineCitation | null {
  if (raw && typeof raw === 'object') {
    const row = raw as Row;
    const workTitle = textOrNull(row.work_title) ?? textOrNull(fallback?.source);
    const locator = textOrNull(row.locator) ?? textOrNull(fallback?.locator);
    const url = textOrNull(row.url) ?? textOrNull(fallback?.url);
    const id = textOrNull(row.id);
    if (id || workTitle || locator || url) {
      return {
        id,
        work_title: workTitle,
        work_title_ar: textOrNull(row.work_title_ar),
        author: textOrNull(row.author),
        edition: textOrNull(row.edition),
        volume: textOrNull(row.volume),
        page: textOrNull(row.page),
        locator,
        url,
        review_state: textOrNull(row.review_state),
      };
    }
  }
  const source = textOrNull(fallback?.source);
  const locator = textOrNull(fallback?.locator);
  const url = textOrNull(fallback?.url);
  if (!source && !locator && !url) return null;
  return {
    id: null,
    work_title: source,
    work_title_ar: null,
    author: null,
    edition: null,
    volume: null,
    page: null,
    locator,
    url,
    review_state: null,
  };
}

function toTemporalAssertions(raw: unknown): TimelineTemporalAssertion[] {
  if (!Array.isArray(raw)) return [];
  return (raw as Row[]).map((row) => ({
    id: String(row.id),
    predicate: String(row.predicate),
    year_min: int(row.year_min),
    year_max: int(row.year_max),
    statement_en: textOrNull(row.statement_en),
    stated_ar: textOrNull(row.stated_ar),
    review_state: String(row.review_state ?? 'candidate_only'),
    citation: toCitation(row.citation),
  }));
}

function toEvent(row: Row): EventEntry {
  return {
    kind: 'event',
    id: String(row.id),
    name: String(row.name),
    name_arabic: textOrNull(row.name_arabic),
    start: Number(row.start),
    end: int(row.end),
    start_latest: null,
    end_earliest: null,
    boundary_note: null,
    basis: historyBasis({ verification_status: String(row.verification_status), publication_ready: row.publication_ready === true }),
    category: textOrNull(row.category),
    location_name: textOrNull(row.location_name),
    location_id: textOrNull(row.location_id),
    description: textOrNull(row.description),
    significance: textOrNull(row.significance),
    track_id: textOrNull(row.track_id),
    track_slug: textOrNull(row.track_slug),
    track_category: (textOrNull(row.track_category) as TimelineTrackCategory | null) ?? null,
    citation: toCitation(row.citation, {
      source: row.citation_source,
      locator: row.citation_locator,
      url: row.citation_url,
    }),
    temporal_assertions: toTemporalAssertions(row.temporal_assertions),
  };
}

function toTrack(row: Row): TimelineTrackEntry {
  return {
    id: String(row.id),
    slug: String(row.slug),
    title: String(row.title),
    category: String(row.category) as TimelineTrackCategory,
    scope: String(row.scope) as TimelineTrackEntry['scope'],
    description: textOrNull(row.description),
  };
}

function toResidence(row: Row): NarratorResidenceEntry {
  return {
    id: String(row.id),
    narrator_id: String(row.narrator_id),
    narrator_name: textOrNull(row.narrator_name),
    location_id: String(row.location_id),
    location_name: textOrNull(row.location_name),
    year_min: int(row.year_min),
    year_max: int(row.year_max),
    precision: textOrNull(row.precision),
    role: String(row.role),
    review_state: String(row.review_state ?? 'candidate_only'),
    citation: toCitation(row.citation),
  };
}

function toAffiliation(row: Row): NarratorAffiliationEntry {
  return {
    id: String(row.id),
    narrator_id: String(row.narrator_id),
    narrator_name: textOrNull(row.narrator_name),
    kind: String(row.kind),
    label: String(row.label),
    note: textOrNull(row.note),
    review_state: String(row.review_state ?? 'candidate_only'),
    citation: toCitation(row.citation),
  };
}

function toPlaceSnapshot(row: Row): PlaceSnapshotEntry {
  return {
    id: String(row.id),
    location_id: String(row.location_id),
    location_name: textOrNull(row.location_name),
    year_min: int(row.year_min),
    year_max: int(row.year_max),
    precision: textOrNull(row.precision),
    polity_or_ruler: textOrNull(row.polity_or_ruler),
    dominant_schools: Array.isArray(row.dominant_schools) ? row.dominant_schools.map(String) : [],
    religious_communities:
      row.religious_communities && typeof row.religious_communities === 'object' && !Array.isArray(row.religious_communities)
        ? (row.religious_communities as Record<string, unknown>)
        : {},
    languages: Array.isArray(row.languages) ? row.languages.map(String) : [],
    ethnographic_notes: textOrNull(row.ethnographic_notes),
    review_state: String(row.review_state ?? 'candidate_only'),
    citation: toCitation(row.citation),
  };
}

function toParallel(row: Row): ExternalTraditionParallelEntry {
  return {
    id: String(row.id),
    hadith_id: String(row.hadith_id),
    tradition_source: String(row.tradition_source),
    relation_type: String(row.relation_type),
    source_work: String(row.source_work),
    locator: textOrNull(row.locator),
    note: textOrNull(row.note),
    review_state: String(row.review_state ?? 'candidate_only'),
    citation: toCitation(row.citation),
  };
}

function toEpoch(row: Row): EpochEntry {
  return {
    kind: 'epoch',
    id: String(row.id),
    name: String(row.name),
    name_arabic: textOrNull(row.name_arabic),
    start: Number(row.start),
    end: int(row.end),
    start_latest: int(row.start_latest),
    end_earliest: int(row.end_earliest),
    boundary_note: textOrNull(row.boundary_note),
    basis: historyBasis({ verification_status: String(row.verification_status), publication_ready: row.publication_ready === true }),
    parent_id: textOrNull(row.parent_id),
    tradition_context: textOrNull(row.tradition_context),
    alternate_names: Array.isArray(row.alternate_names) ? (row.alternate_names as EpochEntry['alternate_names']) : [],
    overview: textOrNull(row.overview),
    citation: toCitation(row.citation),
    temporal_assertions: toTemporalAssertions(row.temporal_assertions),
  };
}

function toNarratorEvent(row: Row): NarratorEventEntry {
  const event = toEvent((row.event ?? {}) as Row);
  return {
    id: String(row.id),
    event_id: String(row.event_id),
    role: String(row.role ?? 'Participant'),
    stated_ar: textOrNull(row.stated_ar),
    event,
    citation: toCitation(row.citation) ?? event.citation ?? null,
  };
}

function emptyLifespan(): Lifespan {
  return { birth: null, death: null, claims: [], competing: false };
}

/** Lifespan, generation, places, and the eras and events related to the life, for one narrator. */
export async function getNarratorTimeline(narratorId: string, visibility: ReadVisibility = PUBLIC_VISIBILITY): Promise<NarratorTimeline> {
  const audience = audienceFor(visibility);
  const [withEpochs, withGrid] = await Promise.all([epochsAvailable(), timelinesGridAvailable()]);
  const row = await oneRow<{
    facts: Row | null;
    events: Row[];
    epochs: Row[] | null;
    narrator_events: Row[];
    tracks: Row[] | null;
    residences: Row[] | null;
    affiliations: Row[] | null;
    place_snapshots: Row[] | null;
  }>(sql`
    with ids as (select ${narratorId}::text as narrator_id),
         facts as (${narratorFacts(audience)}),
         window_bounds as (${WINDOW})
    select (select to_jsonb(f) from facts f) as facts,
           (${eventsWithin(audience, withGrid)}) as events,
           ${withEpochs ? sql`(${epochsWithin(audience)})` : sql`null::json`} as epochs,
           (${narratorEventsFor(narratorId, audience)}) as narrator_events,
           ${withGrid ? sql`(${timelineTracksQuery()})` : sql`null::json`} as tracks,
           ${withGrid ? sql`(${narratorResidencesQuery(audience)})` : sql`null::json`} as residences,
           ${withGrid ? sql`(${narratorAffiliationsQuery(audience)})` : sql`null::json`} as affiliations,
           ${withGrid ? sql`(${placeSnapshotsWithin(audience)})` : sql`null::json`} as place_snapshots
  `);
  const facts = row?.facts ? toFacts(row.facts) : null;
  const lifespan = facts?.lifespan ?? emptyLifespan();
  const relate = <T extends EpochEntry | EventEntry>(entries: T[]) =>
    entries
      .map((entry) => ({ entry, relation: relationToLife(lifespan, entry) }))
      .filter((item): item is { entry: T; relation: NonNullable<typeof item.relation> } => item.relation !== null);
  return {
    narrator_id: narratorId,
    audience,
    lifespan,
    generation: facts?.generation ?? [],
    places: facts?.places ?? [],
    epochs: relate((row?.epochs ?? []).map(toEpoch)),
    events: relate((row?.events ?? []).map(toEvent)),
    narrator_events: (row?.narrator_events ?? []).map(toNarratorEvent),
    tracks: (row?.tracks ?? []).map(toTrack),
    residences: (row?.residences ?? []).map(toResidence),
    affiliations: (row?.affiliations ?? []).map(toAffiliation),
    place_snapshots: (row?.place_snapshots ?? []).map(toPlaceSnapshot),
    parallels: [],
    timelines_grid_available: withGrid,
    epochs_available: withEpochs,
  };
}

const IDENTITY_BASIS_LABELS: Record<string, string> = {
  reviewer_decision: 'confirmed by a reviewer',
  source_index_confirmed_by_text: 'confirmed by source and text',
  source_index: 'source index',
  name_exact: 'matched by name',
  name_spelling_fold: 'matched by name',
  name_kunya_only: 'matched by kunya only',
};

/** Mentions of the requested reports, as public views (public) or live base tables (curator), in one CTE set. */
function familySources(visibility: ReadVisibility): { mentions: SQL; candidates: SQL; hadiths: SQL } {
  const relations = hadithRelationsFor(visibility);
  const hadiths = sql`select h.id, t.code::text as tradition, col.name as source_work
                      from ${relations.hadiths} h join traditions t on t.id = h.tradition_id join collections col on col.id = h.collection_id
                      where ${relations.liveHadith} and h.id in (select hadith_id from requested)`;
  if (!isCuratorVisibility(visibility)) {
    return {
      mentions: sql`select l.id, l.chain_id, l.hadith_id, l.branch, l.position, l.surface_ar, l.narrator_id as verified_id
                    from public_chain_links l where l.hadith_id in (select hadith_id from requested)`,
      candidates: sql`select c.mention_id, c.narrator_id, c.basis::text as basis
                      from public_chain_mention_candidates c where c.hadith_id in (select hadith_id from requested)`,
      hadiths,
    };
  }
  return {
    mentions: sql`select m.id, m.chain_id, m.hadith_id, c.branch, m.position, m.surface_ar,
                         case when m.resolution in ${VERIFIED_RESOLUTIONS} then n.id end as verified_id
                  from chain_mentions m
                  join chains c on c.id = m.chain_id and c.retired_at is null
                  left join narrators n on n.id = m.narrator_id and n.retired_at is null
                  where m.retired_at is null and m.hadith_id in (select h.id from (${hadiths}) h)`,
    candidates: sql`select k.mention_id, k.narrator_id, k.basis::text as basis
                    from chain_mention_candidates k
                    join narrators n on n.id = k.narrator_id and n.retired_at is null
                    where k.retired_at is null and k.hadith_id in (select hadith_id from requested)`,
    hadiths,
  };
}

/** Decides how a position's person is known; dates are attached only to a verified link or one agreed candidate. */
function identify(mention: Row, candidates: Row[]): { identity: ChainIdentity; narratorId: string | null; bases: string[] } {
  const verifiedId = textOrNull(mention.verified_id);
  if (verifiedId) return { identity: 'verified', narratorId: verifiedId, bases: [] };
  const named = new Set(candidates.map((candidate) => String(candidate.narrator_id)));
  const bases = [...new Set(candidates.map((candidate) => IDENTITY_BASIS_LABELS[String(candidate.basis)] ?? String(candidate.basis)))];
  if (named.size === 1) return { identity: 'single_candidate', narratorId: [...named][0], bases };
  return { identity: named.size === 0 ? 'unidentified' : 'candidates_differ', narratorId: null, bases };
}

/**
 * Every chain (branch) of the given reports, transmitters earliest first, each with lifespan, generation and places;
 * per-chain span and chronological gaps; one shared axis with the eras and events it crosses.
 */
export async function getChainFamilyTimeline(hadithIds: string[], visibility: ReadVisibility = PUBLIC_VISIBILITY): Promise<ChainFamilyTimeline> {
  const audience = audienceFor(visibility);
  const ids = [...new Set(hadithIds.map((id) => id.trim()).filter(Boolean))].slice(0, MAX_FAMILY_REPORTS);
  const [withEpochs, withGrid] = await Promise.all([epochsAvailable(), timelinesGridAvailable()]);
  const sources = familySources(visibility);
  const row = await oneRow<{
    hadiths: Row[];
    mentions: Row[];
    candidates: Row[];
    facts: Row[];
    events: Row[];
    epochs: Row[] | null;
    tracks: Row[] | null;
    residences: Row[] | null;
    affiliations: Row[] | null;
    place_snapshots: Row[] | null;
    parallels: Row[] | null;
  }>(sql`
    with requested as (select jsonb_array_elements_text(${JSON.stringify(ids)}::jsonb) as hadith_id),
         mentions as (${sources.mentions}),
         candidates as (${sources.candidates}),
         ids as (select verified_id as narrator_id from mentions where verified_id is not null
                 union select narrator_id from candidates),
         facts as (${narratorFacts(audience)}),
         window_bounds as (${WINDOW})
    select (select coalesce(json_agg(to_jsonb(h)), '[]'::json) from (${sources.hadiths}) h) as hadiths,
           (select coalesce(json_agg(to_jsonb(m) order by m.hadith_id, m.branch, m.position), '[]'::json) from mentions m) as mentions,
           (select coalesce(json_agg(to_jsonb(c)), '[]'::json) from candidates c) as candidates,
           (select coalesce(json_agg(to_jsonb(f)), '[]'::json) from facts f) as facts,
           (${eventsWithin(audience, withGrid)}) as events,
           ${withEpochs ? sql`(${epochsWithin(audience)})` : sql`null::json`} as epochs,
           ${withGrid ? sql`(${timelineTracksQuery()})` : sql`null::json`} as tracks,
           ${withGrid ? sql`(${narratorResidencesQuery(audience)})` : sql`null::json`} as residences,
           ${withGrid ? sql`(${narratorAffiliationsQuery(audience)})` : sql`null::json`} as affiliations,
           ${withGrid ? sql`(${placeSnapshotsWithin(audience)})` : sql`null::json`} as place_snapshots,
           ${withGrid ? sql`(${externalParallelsForHadiths(audience)})` : sql`null::json`} as parallels
  `);

  const factsById = new Map((row?.facts ?? []).map((facts) => [String(facts.narrator_id), toFacts(facts)]));
  const candidatesByMention = new Map<string, Row[]>();
  for (const candidate of row?.candidates ?? []) {
    const key = String(candidate.mention_id);
    candidatesByMention.set(key, [...(candidatesByMention.get(key) ?? []), candidate]);
  }

  const byChain = new Map<string, Row[]>();
  for (const mention of row?.mentions ?? []) {
    const key = String(mention.chain_id);
    byChain.set(key, [...(byChain.get(key) ?? []), mention]);
  }

  const chains: ChainTimeline[] = [...byChain.entries()].map(([chainId, mentions]) => {
    const transmitters: ChainTransmitter[] = mentions
      .map((mention) => {
        const candidates = candidatesByMention.get(String(mention.id)) ?? [];
        const { identity, narratorId, bases } = identify(mention, candidates);
        const facts = narratorId ? factsById.get(narratorId) : undefined;
        const differing = identity === 'candidates_differ'
          ? [...new Set(candidates.map((candidate) => String(candidate.narrator_id)))].map((id) => ({
              narrator_id: id,
              name: factsById.get(id)?.name_en ?? factsById.get(id)?.name_ar ?? id,
            }))
          : [];
        return {
          mention_id: String(mention.id),
          position: Number(mention.position),
          surface_ar: String(mention.surface_ar),
          identity,
          identity_bases: bases,
          narrator_id: narratorId,
          name_en: facts?.name_en ?? null,
          name_ar: facts?.name_ar ?? null,
          candidate_names: differing,
          lifespan: facts?.lifespan ?? emptyLifespan(),
          generation: facts?.generation ?? [],
          places: facts?.places ?? [],
        };
      })
      .sort((left, right) => right.position - left.position);
    const first = mentions[0];
    return {
      chain_id: chainId,
      hadith_id: String(first.hadith_id),
      branch: Number(first.branch),
      transmitters,
      span: spanOfLifespans(transmitters.map((transmitter) => transmitter.lifespan)),
      gaps: chronologicalGaps(transmitters),
    };
  });
  chains.sort((left, right) => ids.indexOf(left.hadith_id) - ids.indexOf(right.hadith_id) || left.branch - right.branch);

  const hadiths = row?.hadiths ?? [];
  return {
    audience,
    hadith_ids: ids,
    traditions: Object.fromEntries(hadiths.map((hadith) => [String(hadith.id), textOrNull(hadith.tradition)])),
    source_works: Object.fromEntries(hadiths.map((hadith) => [String(hadith.id), textOrNull(hadith.source_work)])),
    chains,
    span: spanOfLifespans(chains.flatMap((chain) => chain.transmitters.map((transmitter) => transmitter.lifespan))),
    epochs: (row?.epochs ?? []).map(toEpoch),
    events: (row?.events ?? []).map(toEvent),
    tracks: (row?.tracks ?? []).map(toTrack),
    residences: (row?.residences ?? []).map(toResidence),
    affiliations: (row?.affiliations ?? []).map(toAffiliation),
    place_snapshots: (row?.place_snapshots ?? []).map(toPlaceSnapshot),
    parallels: (row?.parallels ?? []).map(toParallel),
    timelines_grid_available: withGrid,
    epochs_available: withEpochs,
  };
}
