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
  GenerationClaim,
  Lifespan,
  NarratorTimeline,
  PlaceClaim,
  TimelineAudience,
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

function eventsWithin(audience: TimelineAudience): SQL {
  const source = audience === 'review'
    ? sql`(select e.*, e.start_year_hijri as event_start, coalesce(e.end_year_hijri, e.start_year_hijri) as event_end
           from historical_events e where e.retired_at is null and e.start_year_hijri is not null)`
    : sql`published_historical_events`;
  return sql`
    select coalesce(json_agg(json_build_object(
             'id', e.id, 'name', e.title, 'name_arabic', e.title_arabic, 'start', e.event_start, 'end', e.event_end,
             'category', e.category, 'location_name', e.location_name, 'location_id', e.location_id,
             'description', e.description, 'verification_status', e.verification_status,
             'publication_ready', e.publication_ready) order by e.event_start, e.id), '[]'::json)
    from ${source} e, window_bounds w
    where w.lo is not null and e.event_end >= w.lo and e.event_start <= w.hi`;
}

function epochsWithin(audience: TimelineAudience): SQL {
  const source = audience === 'review'
    ? sql`(select e.*, e.start_year_hijri as epoch_start, coalesce(e.end_year_hijri_latest, e.end_year_hijri) as epoch_end
           from epochs e where e.retired_at is null and e.start_year_hijri is not null)`
    : sql`published_epochs`;
  return sql`
    select coalesce(json_agg(json_build_object(
             'id', e.id, 'name', e.name, 'name_arabic', e.name_arabic, 'start', e.epoch_start, 'end', e.epoch_end,
             'start_latest', e.start_year_hijri_latest, 'end_earliest', case when e.end_year_hijri_latest is not null then e.end_year_hijri end,
             'boundary_note', e.boundary_note, 'parent_id', e.parent_epoch_id, 'tradition_context', e.tradition_context,
             'alternate_names', e.alternate_names, 'overview', e.overview,
             'verification_status', e.verification_status, 'publication_ready', e.publication_ready)
             order by e.epoch_start, e.parent_epoch_id nulls first, e.id), '[]'::json)
    from ${source} e, window_bounds w
    where w.lo is not null and (e.epoch_end is null or e.epoch_end >= w.lo) and e.epoch_start <= w.hi`;
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
  };
}

function emptyLifespan(): Lifespan {
  return { birth: null, death: null, claims: [], competing: false };
}

/** Lifespan, generation, places, and the eras and events related to the life, for one narrator. */
export async function getNarratorTimeline(narratorId: string, visibility: ReadVisibility = PUBLIC_VISIBILITY): Promise<NarratorTimeline> {
  const audience = audienceFor(visibility);
  const withEpochs = await epochsAvailable();
  const row = await oneRow<{ facts: Row | null; events: Row[]; epochs: Row[] | null }>(sql`
    with ids as (select ${narratorId}::text as narrator_id),
         facts as (${narratorFacts(audience)}),
         window_bounds as (${WINDOW})
    select (select to_jsonb(f) from facts f) as facts,
           (${eventsWithin(audience)}) as events,
           ${withEpochs ? sql`(${epochsWithin(audience)})` : sql`null::json`} as epochs
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
  const withEpochs = await epochsAvailable();
  const sources = familySources(visibility);
  const row = await oneRow<{ hadiths: Row[]; mentions: Row[]; candidates: Row[]; facts: Row[]; events: Row[]; epochs: Row[] | null }>(sql`
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
           (${eventsWithin(audience)}) as events,
           ${withEpochs ? sql`(${epochsWithin(audience)})` : sql`null::json`} as epochs
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
    epochs_available: withEpochs,
  };
}
