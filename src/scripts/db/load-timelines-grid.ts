/**
 * Idempotent loader for migration 0025 (Multi-Axis Timelines & Cultural-Contact Grid):
 *   - Seeds core `timeline_tracks` (political, world_event, technological,
 *     intellectual_movement, demographic_shift, legal_theological, trade_pilgrimage)
 *   - Classifies existing `historical_events` into `timeline_tracks` via `track_id`
 *   - Loads staged `place_snapshots`, `narrator_residences`, `narrator_affiliations`,
 *     and `external_tradition_parallels` from JSONL / JSONL.gz files with FK validation
 *
 * Usage:
 *   npx tsx --conditions=react-server src/scripts/db/load-timelines-grid.ts --dry-run --database development
 *   npx tsx --conditions=react-server src/scripts/db/load-timelines-grid.ts --dry-run --database production
 *   npx tsx --conditions=react-server src/scripts/db/load-timelines-grid.ts --database development
 *   npx tsx --conditions=react-server src/scripts/db/load-timelines-grid.ts --database production --confirm-production
 */
import { createReadStream, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { createInterface } from 'node:readline';
import { createGunzip } from 'node:zlib';
import { config as loadEnvironment } from 'dotenv';
import { eq, inArray, isNull, sql } from 'drizzle-orm';
import postgres from 'postgres';
import { drizzle } from 'drizzle-orm/postgres-js';
import { connectionOptions } from '../../db/connection-options';
import { resolveTargetDatabase } from '../../db/target-database';
import * as schema from '../../db/schema';
import { hadiths } from '../../db/schema/corpus';
import { citations } from '../../db/schema/evidence';
import { historicalEvents, locations } from '../../db/schema/history';
import { narrators } from '../../db/schema/narrators';
import { datasetVersions } from '../../db/schema/operations';
import {
  externalTraditionParallels,
  narratorAffiliations,
  narratorResidences,
  placeSnapshots,
  timelineTracks,
} from '../../db/schema/timelines';

export const LOADER_ACTOR = 'system:load-timelines-grid';
export const BATCH_SIZE = 500;

export const VALID_TRACK_CATEGORIES = new Set([
  'political',
  'world_event',
  'technological',
  'intellectual_movement',
  'demographic_shift',
  'legal_theological',
  'trade_pilgrimage',
] as const);
export type TrackCategory = typeof VALID_TRACK_CATEGORIES extends Set<infer T> ? T : never;

export const VALID_TRACK_SCOPES = new Set(['global', 'regional', 'city'] as const);
export type TrackScope = typeof VALID_TRACK_SCOPES extends Set<infer T> ? T : never;

export const VALID_RESIDENCE_ROLES = new Set([
  'born',
  'studied',
  'taught',
  'qadi',
  'governor',
  'rihla_visit',
  'died',
] as const);
export type ResidenceRole = typeof VALID_RESIDENCE_ROLES extends Set<infer T> ? T : never;

export const VALID_AFFILIATION_KINDS = new Set([
  'tribe',
  'mawla_of',
  'legal_school',
  'theological_tendency',
  'political_faction',
  'convert_background',
  'profession',
] as const);
export type AffiliationKind = typeof VALID_AFFILIATION_KINDS extends Set<infer T> ? T : never;

export const VALID_TRADITION_SOURCES = new Set([
  'biblical',
  'midrash_talmud',
  'syriac_christian',
  'sasanian_andarz',
  'pre_islamic_poetry',
  'other',
] as const);
export type TraditionSource = typeof VALID_TRADITION_SOURCES extends Set<infer T> ? T : never;

export const VALID_RELATION_TYPES = new Set([
  'direct_quote',
  'structural_parallel',
  'shared_motif',
  'polemical_response',
] as const);
export type RelationType = typeof VALID_RELATION_TYPES extends Set<infer T> ? T : never;

export const VALID_REVIEW_STATES = new Set([
  'candidate_only',
  'source_provided',
  'source_verified',
  'human_verified',
  'lexicon_unverified',
] as const);
export type EvidenceReviewState = typeof VALID_REVIEW_STATES extends Set<infer T> ? T : never;

export interface CoreTimelineTrack {
  id: string;
  slug: string;
  title: string;
  category: TrackCategory;
  scope: TrackScope;
  description: string;
}

export const CORE_TIMELINE_TRACKS: readonly CoreTimelineTrack[] = [
  {
    id: 'track:political',
    slug: 'political',
    title: 'Political & Dynastic History',
    category: 'political',
    scope: 'regional',
    description: 'Caliphal successions, fitnahs, dynastic transitions, rebellions, and military campaigns.',
  },
  {
    id: 'track:world_event',
    slug: 'world-event',
    title: 'World & Geopolitical Events',
    category: 'world_event',
    scope: 'global',
    description: 'Broader Mediterranean, Near Eastern, and Eurasian events contextualizing the Islamic world.',
  },
  {
    id: 'track:technological',
    slug: 'technological',
    title: 'Writing Media & Technological Shifts',
    category: 'technological',
    scope: 'global',
    description: 'Paper adoption, orthographic reforms, book production, tadwin, and communication technologies.',
  },
  {
    id: 'track:intellectual_movement',
    slug: 'intellectual-movement',
    title: 'Intellectual & Scholarly Movements',
    category: 'intellectual_movement',
    scope: 'regional',
    description: 'Translation movements, scholarly circles, biographical compilations, and epistemic shifts.',
  },
  {
    id: 'track:demographic_shift',
    slug: 'demographic-shift',
    title: 'Demographic & Urban Shifts',
    category: 'demographic_shift',
    scope: 'city',
    description: 'Founding of garrison cities (amsar), migrations, plagues, famines, and urban transformations.',
  },
  {
    id: 'track:legal_theological',
    slug: 'legal-theological',
    title: 'Legal & Theological Developments',
    category: 'legal_theological',
    scope: 'regional',
    description: 'Formation of legal schools (madhahib), theological debates, mihnah, and doctrinal milestones.',
  },
  {
    id: 'track:trade_pilgrimage',
    slug: 'trade-pilgrimage',
    title: 'Trade & Pilgrimage Corridors',
    category: 'trade_pilgrimage',
    scope: 'regional',
    description: 'Hajj routes, rihla travel corridors, overland caravans, and maritime trade networks.',
  },
] as const;

export interface StagedPlaceSnapshot {
  id: string;
  locationId: string;
  yearMin: number | null;
  yearMax: number | null;
  precision: string | null;
  polityOrRuler: string | null;
  dominantSchools: string[];
  religiousCommunities: Record<string, unknown>;
  languages: string[];
  ethnographicNotes: string | null;
  citationId: string;
  reviewState: EvidenceReviewState;
}

export interface StagedNarratorResidence {
  id: string;
  narratorId: string;
  locationId: string;
  yearMin: number | null;
  yearMax: number | null;
  precision: string | null;
  role: ResidenceRole;
  citationId: string;
  reviewState: EvidenceReviewState;
}

export interface StagedNarratorAffiliation {
  id: string;
  narratorId: string;
  kind: AffiliationKind;
  label: string;
  note: string | null;
  citationId: string;
  reviewState: EvidenceReviewState;
}

export interface StagedExternalTraditionParallel {
  id: string;
  hadithId: string;
  traditionSource: TraditionSource;
  relationType: RelationType;
  sourceWork: string;
  locator: string | null;
  note: string | null;
  citationId: string;
  reviewState: EvidenceReviewState;
}

export interface TimelinesLoadPlan {
  tracks: readonly CoreTimelineTrack[];
  placeSnapshots: StagedPlaceSnapshot[];
  placeSnapshotsSkipped: number;
  narratorResidences: StagedNarratorResidence[];
  narratorResidencesSkipped: number;
  narratorAffiliations: StagedNarratorAffiliation[];
  narratorAffiliationsSkipped: number;
  externalTraditionParallels: StagedExternalTraditionParallel[];
  externalTraditionParallelsSkipped: number;
}

export interface LoaderArgs {
  dryRun: boolean;
  database: 'development' | 'production';
  dataDir: string | null;
  reclassifyEvents: boolean;
}

export function normalizeNonEmpty(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function normalizeInt(value: unknown): number | null {
  if (typeof value === 'number' && Number.isInteger(value)) return value;
  return null;
}

export function normalizeStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((v) => (typeof v === 'string' ? v.trim() : ''))
    .filter((v) => v.length > 0);
}

export function normalizePlainObject(value: unknown): Record<string, unknown> | null {
  if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

export function normalizeReviewState(value: unknown): EvidenceReviewState {
  if (typeof value === 'string' && VALID_REVIEW_STATES.has(value as EvidenceReviewState)) {
    return value as EvidenceReviewState;
  }
  return 'candidate_only';
}

export function isValidYearRange(yearMin: number | null, yearMax: number | null): boolean {
  return yearMin === null || yearMax === null || yearMax >= yearMin;
}

/**
 * Classifies a `historical_events` row into one of the 7 core `timeline_tracks` IDs.
 * Keyword checks run first for domain-specific tracks (technological, trade_pilgrimage,
 * demographic_shift, legal_theological, intellectual_movement), then fall back to `category`.
 */
export function classifyHistoricalEventTrack(event: {
  category?: string | null;
  title?: string | null;
  description?: string | null;
}): string {
  const text = `${event.title ?? ''} ${event.description ?? ''}`.toLowerCase();

  if (/\b(paper|papermaking|parchment|codex|diacritic|orthograph|script|tadwin|writing|samarkand paper|printing)\b/.test(text)) {
    return 'track:technological';
  }
  if (/\b(hajj|pilgrimage|caravan|trade route|silk road|maritime|rihla|zubaydah)\b/.test(text)) {
    return 'track:trade_pilgrimage';
  }
  if (/\b(plague|famine|amsar|garrison city|founding of kufa|founding of basra|founding of baghdad|founding of fustat|migration|urbanization)\b/.test(text)) {
    return 'track:demographic_shift';
  }
  if (/\b(mihnah|mihna|madhhab|fiqh|creed|kalam|mu'tazil|ash'ar|hanbali|shafi'i|maliki|hanafi|ja'fari|canonical)\b/.test(text)) {
    return 'track:legal_theological';
  }
  if (/\b(bayt al-hikma|house of wisdom|translation movement|rijal|isnad|compilation|sahih|musnad)\b/.test(text)) {
    return 'track:intellectual_movement';
  }

  switch (event.category) {
    case 'POLITICAL':
    case 'MILITARY':
    case 'PROPHETIC_ERA':
    case 'RASHIDUN':
    case 'UMAYYAD':
    case 'ABBASID':
      return 'track:political';
    case 'SCIENTIFIC':
      return 'track:technological';
    case 'SCHOLARLY':
    case 'CULTURAL':
      return 'track:intellectual_movement';
    case 'RELIGIOUS':
      return 'track:legal_theological';
    case 'SOCIAL':
      return 'track:demographic_shift';
    case 'ECONOMIC':
      return 'track:trade_pilgrimage';
    default:
      return 'track:world_event';
  }
}

export function parsePlaceSnapshotRow(row: Record<string, unknown>): StagedPlaceSnapshot | null {
  const id = normalizeNonEmpty(row.id);
  const locationId = normalizeNonEmpty(row.location_id ?? row.locationId);
  const citationId = normalizeNonEmpty(row.citation_id ?? row.citationId);
  if (!id || !locationId || !citationId) return null;

  const yearMin = normalizeInt(row.year_min ?? row.yearMin);
  const yearMax = normalizeInt(row.year_max ?? row.yearMax);
  if (!isValidYearRange(yearMin, yearMax)) return null;

  const rawCommunities = row.religious_communities ?? row.religiousCommunities;
  const religiousCommunities = rawCommunities === undefined || rawCommunities === null
    ? {}
    : normalizePlainObject(rawCommunities);
  if (!religiousCommunities) return null;

  return {
    id,
    locationId,
    yearMin,
    yearMax,
    precision: normalizeNonEmpty(row.precision),
    polityOrRuler: normalizeNonEmpty(row.polity_or_ruler ?? row.polityOrRuler),
    dominantSchools: normalizeStringArray(row.dominant_schools ?? row.dominantSchools),
    religiousCommunities,
    languages: normalizeStringArray(row.languages),
    ethnographicNotes: normalizeNonEmpty(row.ethnographic_notes ?? row.ethnographicNotes),
    citationId,
    reviewState: normalizeReviewState(row.review_state ?? row.reviewState),
  };
}

export function parseNarratorResidenceRow(row: Record<string, unknown>): StagedNarratorResidence | null {
  const id = normalizeNonEmpty(row.id);
  const narratorId = normalizeNonEmpty(row.narrator_id ?? row.narratorId);
  const locationId = normalizeNonEmpty(row.location_id ?? row.locationId);
  const citationId = normalizeNonEmpty(row.citation_id ?? row.citationId);
  const role = normalizeNonEmpty(row.role);
  if (!id || !narratorId || !locationId || !citationId || !role) return null;
  if (!VALID_RESIDENCE_ROLES.has(role as ResidenceRole)) return null;

  const yearMin = normalizeInt(row.year_min ?? row.yearMin);
  const yearMax = normalizeInt(row.year_max ?? row.yearMax);
  if (!isValidYearRange(yearMin, yearMax)) return null;

  return {
    id,
    narratorId,
    locationId,
    yearMin,
    yearMax,
    precision: normalizeNonEmpty(row.precision),
    role: role as ResidenceRole,
    citationId,
    reviewState: normalizeReviewState(row.review_state ?? row.reviewState),
  };
}

export function parseNarratorAffiliationRow(row: Record<string, unknown>): StagedNarratorAffiliation | null {
  const id = normalizeNonEmpty(row.id);
  const narratorId = normalizeNonEmpty(row.narrator_id ?? row.narratorId);
  const kind = normalizeNonEmpty(row.kind);
  const label = normalizeNonEmpty(row.label);
  const citationId = normalizeNonEmpty(row.citation_id ?? row.citationId);
  if (!id || !narratorId || !kind || !label || !citationId) return null;
  if (!VALID_AFFILIATION_KINDS.has(kind as AffiliationKind)) return null;

  return {
    id,
    narratorId,
    kind: kind as AffiliationKind,
    label,
    note: normalizeNonEmpty(row.note),
    citationId,
    reviewState: normalizeReviewState(row.review_state ?? row.reviewState),
  };
}

export function parseExternalTraditionParallelRow(
  row: Record<string, unknown>,
): StagedExternalTraditionParallel | null {
  const id = normalizeNonEmpty(row.id);
  const hadithId = normalizeNonEmpty(row.hadith_id ?? row.hadithId);
  const traditionSource = normalizeNonEmpty(row.tradition_source ?? row.traditionSource);
  const relationType = normalizeNonEmpty(row.relation_type ?? row.relationType);
  const sourceWork = normalizeNonEmpty(row.source_work ?? row.sourceWork);
  const citationId = normalizeNonEmpty(row.citation_id ?? row.citationId);
  if (!id || !hadithId || !traditionSource || !relationType || !sourceWork || !citationId) return null;
  if (!VALID_TRADITION_SOURCES.has(traditionSource as TraditionSource)) return null;
  if (!VALID_RELATION_TYPES.has(relationType as RelationType)) return null;

  return {
    id,
    hadithId,
    traditionSource: traditionSource as TraditionSource,
    relationType: relationType as RelationType,
    sourceWork,
    locator: normalizeNonEmpty(row.locator),
    note: normalizeNonEmpty(row.note),
    citationId,
    reviewState: normalizeReviewState(row.review_state ?? row.reviewState),
  };
}

async function readJsonlIfPresent(
  dir: string,
  baseName: string,
  onRow: (row: Record<string, unknown>) => void,
): Promise<boolean> {
  const gzPath = resolve(dir, `${baseName}.jsonl.gz`);
  const plainPath = resolve(dir, `${baseName}.jsonl`);
  const targetPath = existsSync(gzPath) ? gzPath : existsSync(plainPath) ? plainPath : null;
  if (!targetPath) return false;

  const rawStream = createReadStream(targetPath);
  const input = targetPath.endsWith('.gz') ? rawStream.pipe(createGunzip()) : rawStream;
  const rl = createInterface({ input, crlfDelay: Infinity });
  for await (const line of rl) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    onRow(JSON.parse(trimmed) as Record<string, unknown>);
  }
  return true;
}

export async function buildTimelinesLoadPlan(dataDir: string): Promise<TimelinesLoadPlan> {
  const placeSnapshotsList: StagedPlaceSnapshot[] = [];
  let placeSnapshotsSkipped = 0;
  const narratorResidencesList: StagedNarratorResidence[] = [];
  let narratorResidencesSkipped = 0;
  const narratorAffiliationsList: StagedNarratorAffiliation[] = [];
  let narratorAffiliationsSkipped = 0;
  const externalTraditionParallelsList: StagedExternalTraditionParallel[] = [];
  let externalTraditionParallelsSkipped = 0;

  if (existsSync(dataDir)) {
    await readJsonlIfPresent(dataDir, 'place_snapshots', (row) => {
      const parsed = parsePlaceSnapshotRow(row);
      if (parsed) placeSnapshotsList.push(parsed);
      else placeSnapshotsSkipped += 1;
    });

    await readJsonlIfPresent(dataDir, 'narrator_residences', (row) => {
      const parsed = parseNarratorResidenceRow(row);
      if (parsed) narratorResidencesList.push(parsed);
      else narratorResidencesSkipped += 1;
    });

    await readJsonlIfPresent(dataDir, 'narrator_affiliations', (row) => {
      const parsed = parseNarratorAffiliationRow(row);
      if (parsed) narratorAffiliationsList.push(parsed);
      else narratorAffiliationsSkipped += 1;
    });

    await readJsonlIfPresent(dataDir, 'external_tradition_parallels', (row) => {
      const parsed = parseExternalTraditionParallelRow(row);
      if (parsed) externalTraditionParallelsList.push(parsed);
      else externalTraditionParallelsSkipped += 1;
    });
  }

  return {
    tracks: CORE_TIMELINE_TRACKS,
    placeSnapshots: placeSnapshotsList,
    placeSnapshotsSkipped,
    narratorResidences: narratorResidencesList,
    narratorResidencesSkipped,
    narratorAffiliations: narratorAffiliationsList,
    narratorAffiliationsSkipped,
    externalTraditionParallels: externalTraditionParallelsList,
    externalTraditionParallelsSkipped,
  };
}

export function parseLoaderArgs(argv: readonly string[]): LoaderArgs {
  const dryRun = argv.includes('--dry-run');
  const reclassifyEvents = argv.includes('--reclassify-events');

  const dbIdx = argv.indexOf('--database');
  const requestedDb =
    dbIdx >= 0
      ? argv[dbIdx + 1]
      : argv.find((v) => v.startsWith('--database='))?.slice('--database='.length);
  const database = (requestedDb ?? 'development') as 'development' | 'production';
  if (database !== 'development' && database !== 'production') {
    throw new Error(`--database must be development or production, not "${database}".`);
  }

  const dirIdx = argv.indexOf('--data-dir');
  const dataDir =
    dirIdx >= 0
      ? (argv[dirIdx + 1] ?? null)
      : (argv.find((v) => v.startsWith('--data-dir='))?.slice('--data-dir='.length) ?? null);

  return { dryRun, database, dataDir, reclassifyEvents };
}

function resolveConnectionForScript(
  argv: readonly string[],
  dryRun: boolean,
): { name: 'development' | 'production'; url: string } {
  if (!dryRun) {
    return resolveTargetDatabase(argv, { required: true });
  }
  loadEnvironment({ path: '.env.local', quiet: true });
  const parsed = parseLoaderArgs(argv);
  if (parsed.database === 'production') {
    const url = process.env.DATABASE_URL_PRODUCTION?.trim();
    if (!url) throw new Error('DATABASE_URL_PRODUCTION is not set.');
    return { name: 'production', url };
  }
  return resolveTargetDatabase(['--database', 'development'], { required: true });
}

async function runBatched<T>(
  items: readonly T[],
  batchSize: number,
  fn: (batch: readonly T[]) => Promise<void>,
): Promise<void> {
  for (let i = 0; i < items.length; i += batchSize) {
    await fn(items.slice(i, i + batchSize));
  }
}

export async function executeLoad(argv: readonly string[]): Promise<void> {
  const args = parseLoaderArgs(argv);
  const target = resolveConnectionForScript(argv, args.dryRun);
  const dataDir = args.dataDir
    ? resolve(process.cwd(), args.dataDir)
    : resolve(process.cwd(), 'datasets/hadith-data/timelines/output');

  console.log(
    `[load-timelines-grid] Target: ${target.name} (${args.dryRun ? 'DRY RUN — no writes' : 'LIVE WRITE'})`,
  );

  const plan = await buildTimelinesLoadPlan(dataDir);
  const sqlClient = postgres(target.url, connectionOptions(target.url, 5));
  const db = drizzle(sqlClient, { schema });

  try {
    const [currentDv] = await db
      .select({ id: datasetVersions.id })
      .from(datasetVersions)
      .where(eq(datasetVersions.isCurrent, true))
      .limit(1);
    const datasetVersionId = currentDv?.id;
    if (!datasetVersionId) {
      throw new Error('No current dataset_versions row (is_current = true) found in target database.');
    }

    // Fetch existing historical_events to classify
    const eventsToClassify = await db
      .select({
        id: historicalEvents.id,
        category: historicalEvents.category,
        title: historicalEvents.title,
        description: historicalEvents.description,
        trackId: historicalEvents.trackId,
      })
      .from(historicalEvents)
      .where(args.reclassifyEvents ? isNull(historicalEvents.retiredAt) : isNull(historicalEvents.trackId));

    const eventTrackAssignments = eventsToClassify.map((ev) => ({
      id: ev.id,
      trackId: classifyHistoricalEventTrack(ev),
    }));

    // Validate FKs for staged tables
    const fetchExistingIds = async (
      ids: readonly string[],
      queryBatch: (batch: string[]) => Promise<Array<{ id: string }>>,
    ): Promise<Set<string>> => {
      const found = new Set<string>();
      const uniqueIds = Array.from(new Set(ids));
      await runBatched(uniqueIds, BATCH_SIZE, async (batch) => {
        const rows = await queryBatch([...batch]);
        for (const r of rows) found.add(r.id);
      });
      return found;
    };

    const allCitationIds = [
      ...plan.placeSnapshots.map((r) => r.citationId),
      ...plan.narratorResidences.map((r) => r.citationId),
      ...plan.narratorAffiliations.map((r) => r.citationId),
      ...plan.externalTraditionParallels.map((r) => r.citationId),
    ];
    const allLocationIds = [
      ...plan.placeSnapshots.map((r) => r.locationId),
      ...plan.narratorResidences.map((r) => r.locationId),
    ];
    const allNarratorIds = [
      ...plan.narratorResidences.map((r) => r.narratorId),
      ...plan.narratorAffiliations.map((r) => r.narratorId),
    ];
    const allHadithIds = plan.externalTraditionParallels.map((r) => r.hadithId);

    const [validCitations, validLocations, validNarrators, validHadiths] = await Promise.all([
      fetchExistingIds(allCitationIds, (b) =>
        db.select({ id: citations.id }).from(citations).where(inArray(citations.id, b)),
      ),
      fetchExistingIds(allLocationIds, (b) =>
        db.select({ id: locations.id }).from(locations).where(inArray(locations.id, b)),
      ),
      fetchExistingIds(allNarratorIds, (b) =>
        db.select({ id: narrators.id }).from(narrators).where(inArray(narrators.id, b)),
      ),
      fetchExistingIds(allHadithIds, (b) =>
        db.select({ id: hadiths.id }).from(hadiths).where(inArray(hadiths.id, b)),
      ),
    ]);

    const readyPlaceSnapshots = plan.placeSnapshots.filter(
      (r) => validLocations.has(r.locationId) && validCitations.has(r.citationId),
    );
    const readyResidences = plan.narratorResidences.filter(
      (r) =>
        validNarrators.has(r.narratorId) &&
        validLocations.has(r.locationId) &&
        validCitations.has(r.citationId),
    );
    const readyAffiliations = plan.narratorAffiliations.filter(
      (r) => validNarrators.has(r.narratorId) && validCitations.has(r.citationId),
    );
    const readyParallels = plan.externalTraditionParallels.filter(
      (r) => validHadiths.has(r.hadithId) && validCitations.has(r.citationId),
    );

    console.log(`[load-timelines-grid] Current dataset_version_id: ${datasetVersionId}`);
    console.log(`[load-timelines-grid] Plan summary:`);
    console.log(`  timeline_tracks              : ${plan.tracks.length}`);
    console.log(`  historical_events to classify: ${eventTrackAssignments.length}`);
    console.log(
      `  place_snapshots              : ${readyPlaceSnapshots.length} ready (parse-skipped: ${plan.placeSnapshotsSkipped}, fk-skipped: ${plan.placeSnapshots.length - readyPlaceSnapshots.length})`,
    );
    console.log(
      `  narrator_residences          : ${readyResidences.length} ready (parse-skipped: ${plan.narratorResidencesSkipped}, fk-skipped: ${plan.narratorResidences.length - readyResidences.length})`,
    );
    console.log(
      `  narrator_affiliations        : ${readyAffiliations.length} ready (parse-skipped: ${plan.narratorAffiliationsSkipped}, fk-skipped: ${plan.narratorAffiliations.length - readyAffiliations.length})`,
    );
    console.log(
      `  external_tradition_parallels : ${readyParallels.length} ready (parse-skipped: ${plan.externalTraditionParallelsSkipped}, fk-skipped: ${plan.externalTraditionParallels.length - readyParallels.length})`,
    );

    if (args.dryRun) {
      console.log(`[load-timelines-grid] Dry-run complete. 0 rows written.`);
      return;
    }

    const now = new Date();

    // 1. Upsert core timeline_tracks
    await runBatched(plan.tracks, BATCH_SIZE, async (batch) => {
      await db
        .insert(timelineTracks)
        .values(
          batch.map((t) => ({
            id: t.id,
            slug: t.slug,
            title: t.title,
            category: t.category,
            scope: t.scope,
            description: t.description,
            firstSeenDatasetVersionId: datasetVersionId,
            changedInDatasetVersionId: datasetVersionId,
            updatedAt: now,
          })),
        )
        .onConflictDoUpdate({
          target: timelineTracks.id,
          set: {
            slug: sql`excluded.slug`,
            title: sql`excluded.title`,
            category: sql`excluded.category`,
            scope: sql`excluded.scope`,
            description: sql`excluded.description`,
            changedInDatasetVersionId: sql`excluded.changed_in_dataset_version_id`,
            updatedAt: now,
          },
        });
    });

    // 2. Classify historical_events into timeline_tracks
    const eventIdsByTrack = new Map<string, string[]>();
    for (const assignment of eventTrackAssignments) {
      const list = eventIdsByTrack.get(assignment.trackId) ?? [];
      list.push(assignment.id);
      eventIdsByTrack.set(assignment.trackId, list);
    }
    for (const [trackId, ids] of eventIdsByTrack.entries()) {
      await runBatched(ids, BATCH_SIZE, async (batch) => {
        await db
          .update(historicalEvents)
          .set({ trackId, updatedAt: now })
          .where(inArray(historicalEvents.id, [...batch]));
      });
    }

    // 3. Upsert place_snapshots
    await runBatched(readyPlaceSnapshots, BATCH_SIZE, async (batch) => {
      await db
        .insert(placeSnapshots)
        .values(
          batch.map((r) => ({
            id: r.id,
            locationId: r.locationId,
            yearMin: r.yearMin,
            yearMax: r.yearMax,
            precision: r.precision,
            polityOrRuler: r.polityOrRuler,
            dominantSchools: r.dominantSchools,
            religiousCommunities: r.religiousCommunities,
            languages: r.languages,
            ethnographicNotes: r.ethnographicNotes,
            citationId: r.citationId,
            reviewState: r.reviewState,
            firstSeenDatasetVersionId: datasetVersionId,
            changedInDatasetVersionId: datasetVersionId,
            updatedAt: now,
          })),
        )
        .onConflictDoUpdate({
          target: placeSnapshots.id,
          set: {
            locationId: sql`excluded.location_id`,
            yearMin: sql`excluded.year_min`,
            yearMax: sql`excluded.year_max`,
            precision: sql`excluded.precision`,
            polityOrRuler: sql`excluded.polity_or_ruler`,
            dominantSchools: sql`excluded.dominant_schools`,
            religiousCommunities: sql`excluded.religious_communities`,
            languages: sql`excluded.languages`,
            ethnographicNotes: sql`excluded.ethnographic_notes`,
            citationId: sql`excluded.citation_id`,
            reviewState: sql`excluded.review_state`,
            changedInDatasetVersionId: sql`excluded.changed_in_dataset_version_id`,
            updatedAt: now,
          },
        });
    });

    // 4. Upsert narrator_residences
    await runBatched(readyResidences, BATCH_SIZE, async (batch) => {
      await db
        .insert(narratorResidences)
        .values(
          batch.map((r) => ({
            id: r.id,
            narratorId: r.narratorId,
            locationId: r.locationId,
            yearMin: r.yearMin,
            yearMax: r.yearMax,
            precision: r.precision,
            role: r.role,
            citationId: r.citationId,
            reviewState: r.reviewState,
            firstSeenDatasetVersionId: datasetVersionId,
            changedInDatasetVersionId: datasetVersionId,
            updatedAt: now,
          })),
        )
        .onConflictDoUpdate({
          target: narratorResidences.id,
          set: {
            narratorId: sql`excluded.narrator_id`,
            locationId: sql`excluded.location_id`,
            yearMin: sql`excluded.year_min`,
            yearMax: sql`excluded.year_max`,
            precision: sql`excluded.precision`,
            role: sql`excluded.role`,
            citationId: sql`excluded.citation_id`,
            reviewState: sql`excluded.review_state`,
            changedInDatasetVersionId: sql`excluded.changed_in_dataset_version_id`,
            updatedAt: now,
          },
        });
    });

    // 5. Upsert narrator_affiliations
    await runBatched(readyAffiliations, BATCH_SIZE, async (batch) => {
      await db
        .insert(narratorAffiliations)
        .values(
          batch.map((r) => ({
            id: r.id,
            narratorId: r.narratorId,
            kind: r.kind,
            label: r.label,
            note: r.note,
            citationId: r.citationId,
            reviewState: r.reviewState,
            firstSeenDatasetVersionId: datasetVersionId,
            changedInDatasetVersionId: datasetVersionId,
            updatedAt: now,
          })),
        )
        .onConflictDoUpdate({
          target: narratorAffiliations.id,
          set: {
            narratorId: sql`excluded.narrator_id`,
            kind: sql`excluded.kind`,
            label: sql`excluded.label`,
            note: sql`excluded.note`,
            citationId: sql`excluded.citation_id`,
            reviewState: sql`excluded.review_state`,
            changedInDatasetVersionId: sql`excluded.changed_in_dataset_version_id`,
            updatedAt: now,
          },
        });
    });

    // 6. Upsert external_tradition_parallels
    await runBatched(readyParallels, BATCH_SIZE, async (batch) => {
      await db
        .insert(externalTraditionParallels)
        .values(
          batch.map((r) => ({
            id: r.id,
            hadithId: r.hadithId,
            traditionSource: r.traditionSource,
            relationType: r.relationType,
            sourceWork: r.sourceWork,
            locator: r.locator,
            note: r.note,
            citationId: r.citationId,
            reviewState: r.reviewState,
            firstSeenDatasetVersionId: datasetVersionId,
            changedInDatasetVersionId: datasetVersionId,
            updatedAt: now,
          })),
        )
        .onConflictDoUpdate({
          target: externalTraditionParallels.id,
          set: {
            hadithId: sql`excluded.hadith_id`,
            traditionSource: sql`excluded.tradition_source`,
            relationType: sql`excluded.relation_type`,
            sourceWork: sql`excluded.source_work`,
            locator: sql`excluded.locator`,
            note: sql`excluded.note`,
            citationId: sql`excluded.citation_id`,
            reviewState: sql`excluded.review_state`,
            changedInDatasetVersionId: sql`excluded.changed_in_dataset_version_id`,
            updatedAt: now,
          },
        });
    });

    console.log(`[load-timelines-grid] Write complete.`);
  } finally {
    await sqlClient.end({ timeout: 5 });
  }
}

if (/load-timelines-grid\.ts$/.test(process.argv[1] ?? '')) {
  executeLoad(process.argv.slice(2)).catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  });
}
