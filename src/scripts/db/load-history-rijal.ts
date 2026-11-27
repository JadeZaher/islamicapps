/**
 * Idempotent loader for the staged `history` (171 citations, 182 temporal assertions, 47 locations,
 * 105 event candidates, 38 epoch candidates, 64 narrator-event candidates) and `RIJ` (313,681 verified
 * citation references deduplicated by work/edition/span/sha256 + 6 works/editions + narrator-event
 * candidates) datasets targeting migration 0024 tables:
 *   - bibliographic_works, editions, citations, temporal_assertions
 *   - locations, historical_events, epochs, narrator_events
 *
 * Usage:
 *   npx tsx --conditions=react-server src/scripts/db/load-history-rijal.ts --dry-run --database development
 *   npx tsx --conditions=react-server src/scripts/db/load-history-rijal.ts --dry-run --database production
 *   npx tsx --conditions=react-server src/scripts/db/load-history-rijal.ts --database development
 *   npx tsx --conditions=react-server src/scripts/db/load-history-rijal.ts --database production --confirm-production
 */
import { createHash } from 'node:crypto';
import { createReadStream, readFileSync } from 'node:fs';
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
import { bibliographicWorks, citations, editions, temporalAssertions } from '../../db/schema/evidence';
import { epochs, historicalEvents, locations, narratorEvents } from '../../db/schema/history';
import { narrators } from '../../db/schema/narrators';
import { datasetVersions } from '../../db/schema/operations';

export const LOADER_ACTOR = 'system:load-history-rijal';
const BATCH_SIZE = 500;
const SHA256_RE = /^[0-9a-f]{64}$/;

const VALID_EVENT_CATEGORIES = new Set([
  'PROPHETIC_ERA',
  'RASHIDUN',
  'UMAYYAD',
  'ABBASID',
  'SCHOLARLY',
  'MILITARY',
  'POLITICAL',
  'SOCIAL',
  'RELIGIOUS',
  'SCIENTIFIC',
  'CULTURAL',
  'ECONOMIC',
] as const);
type EventCategory = typeof VALID_EVENT_CATEGORIES extends Set<infer T> ? T : never;

const VALID_TRADITIONS = new Set(['Sunni', 'Imami', 'Zaydi', 'Ibadi'] as const);
type HadithTradition = typeof VALID_TRADITIONS extends Set<infer T> ? T : never;

const VALID_RIGHTS = new Set(['cleared', 'pending', 'restricted'] as const);
type RightsStatus = typeof VALID_RIGHTS extends Set<infer T> ? T : never;

const RIJAL_CITED_JSONL_FILES = [
  'narrator_assessment_candidates.jsonl.gz',
  'narrator_event_candidates.jsonl.gz',
  'rijal_entries_ibn_hajar_taqrib.jsonl.gz',
  'rijal_entries_kashshi_ikhtiyar.jsonl.gz',
  'rijal_entries_mizzi_tahdhib_kamal.jsonl.gz',
  'rijal_entries_najashi_rijal.jsonl.gz',
  'rijal_entries_tusi_fihrist.jsonl.gz',
  'rijal_entries_tusi_rijal.jsonl.gz',
  'rijal_entry_statements.jsonl.gz',
  'rijal_links_imami_chain_names.jsonl.gz',
  'rijal_links_lexicon.jsonl.gz',
  'rijal_links_riwayat.jsonl.gz',
  'rijal_perspective_cells.jsonl.gz',
  'rijal_timeline_facts.jsonl.gz',
] as const;

export interface StagedWork {
  id: string;
  title: string;
  titleAr: string | null;
  author: string | null;
  authorDeathYearHijri: number | null;
  openitiUri: string | null;
}

export interface StagedEdition {
  id: string;
  workId: string;
  editor: string | null;
  publisher: string | null;
  place: string | null;
  year: string | null;
  locatorScheme: string | null;
  url: string | null;
  rightsStatus: RightsStatus;
}

export interface StagedCitation {
  id: string;
  workId: string;
  editionId: string | null;
  volume: string | null;
  page: string | null;
  locator: string | null;
  url: string | null;
  quoteAr: string | null;
  quoteEn: string | null;
  reviewState: 'candidate_only' | 'source_provided' | 'source_verified' | 'human_verified' | 'lexicon_unverified';
  sourceSpan: Record<string, unknown> | null;
  sourceSha256: string | null;
  sourceFile: string | null;
}

export interface StagedTemporalAssertion {
  id: string;
  eventId: string | null;
  epochId: string | null;
  collectionId: string | null;
  boundary: 'start' | 'end' | null;
  predicate: string;
  yearMin: number | null;
  yearMax: number | null;
  calendar: 'hijri' | 'gregorian';
  precision: string | null;
  alternatives: number[];
  monthDay: string | null;
  statedAr: string | null;
  statementEn: string | null;
  dateBasis: 'passage' | 'section_heading' | null;
  qualifier: string | null;
  reckoning: string | null;
  attributedTo: string | null;
  perspective: Record<string, unknown> | null;
  flags: string[];
  note: string | null;
  citationId: string;
  reviewState: 'candidate_only';
  aiReview: Record<string, unknown> | null;
  humanReviews: unknown[];
}

export interface StagedLocation {
  id: string;
  name: string;
  nameArabic: string | null;
  modernCountry: string | null;
  region: string | null;
  description: string | null;
  latitude: number | null;
  longitude: number | null;
  kind: string | null;
  formsAr: string[];
  ambiguousForms: Record<string, unknown> | null;
  citedInCitationIds: string[];
  coordinatesBasis: string | null;
}

export interface StagedEvent {
  id: string;
  key: string | null;
  originKind: 'seed' | 'history_lane_candidate';
  title: string;
  titleArabic: string | null;
  category: EventCategory | null;
  startYearHijri: number | null;
  endYearHijri: number | null;
  locationName: string | null;
  traditionContext: HadithTradition | null;
  citationId: string | null;
}

export interface StagedEpochCitation {
  id: string;
  citationId: string | null;
}

export interface StagedNarratorEvent {
  narratorId: string;
  eventId: string;
  role: string;
  citationId: string | null;
  statedAr: string | null;
  aiReview: Record<string, unknown> | null;
  humanReviews: unknown[];
}

export interface LoadPlan {
  works: StagedWork[];
  editions: StagedEdition[];
  historyCitations: StagedCitation[];
  rijalCitations: StagedCitation[];
  rijalCitationRefsTotal: number;
  temporalAssertions: StagedTemporalAssertion[];
  temporalAssertionsSkipped: number;
  locations: StagedLocation[];
  events: StagedEvent[];
  epochCitations: StagedEpochCitation[];
  narratorEvents: StagedNarratorEvent[];
  narratorEventsSkippedMissingKeys: number;
}

export function deterministicRijalCitationId(
  workId: string,
  editionId: string | null,
  sourceSpan: Record<string, unknown> | null,
  sourceSha256: string | null,
): string {
  const start = sourceSpan && typeof sourceSpan.start === 'number' ? sourceSpan.start : '';
  const end = sourceSpan && typeof sourceSpan.end === 'number' ? sourceSpan.end : '';
  const key = `${workId}|${editionId ?? ''}|${start}|${end}|${sourceSha256 ?? ''}`;
  const digest = createHash('sha256').update(key).digest('hex').slice(0, 20);
  return `cit:rijal:${digest}`;
}

export function normalizeSha256(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim().toLowerCase();
  return SHA256_RE.test(trimmed) ? trimmed : null;
}

export function normalizeNonEmpty(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function normalizeJsonObject(value: unknown): Record<string, unknown> | null {
  if (value !== null && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, unknown>;
  }
  return null;
}

export function normalizeTradition(value: unknown): HadithTradition | null {
  if (typeof value !== 'string') return null;
  const map: Record<string, HadithTradition> = {
    sunni: 'Sunni',
    imami: 'Imami',
    zaydi: 'Zaydi',
    ibadi: 'Ibadi',
  };
  return map[value.trim().toLowerCase()] ?? null;
}

export function normalizeCategory(value: unknown): EventCategory | null {
  if (typeof value !== 'string') return null;
  return VALID_EVENT_CATEGORIES.has(value as EventCategory) ? (value as EventCategory) : null;
}

export function normalizeRights(value: unknown): RightsStatus {
  if (typeof value === 'string' && VALID_RIGHTS.has(value as RightsStatus)) {
    return value as RightsStatus;
  }
  return 'pending';
}

export function formatRijalLocator(locator: unknown): { volume: string | null; page: string | null; text: string | null } {
  if (!locator || typeof locator !== 'object' || Array.isArray(locator)) {
    return { volume: null, page: null, text: null };
  }
  const obj = locator as Record<string, unknown>;
  const volume = obj.volume != null ? String(obj.volume) : null;
  const page = obj.page != null ? String(obj.page) : null;
  const entry = obj.entry_number != null ? String(obj.entry_number) : null;
  const parts: string[] = [];
  if (volume) parts.push(`v${volume}`);
  if (page) parts.push(`p${page}`);
  if (entry) parts.push(`entry ${entry}`);
  return {
    volume,
    page,
    text: parts.length > 0 ? parts.join(', ') : null,
  };
}

async function readJsonlGz<T = Record<string, unknown>>(filePath: string, onRow: (row: T) => void): Promise<number> {
  let count = 0;
  const stream = createReadStream(filePath).pipe(createGunzip());
  const rl = createInterface({ input: stream, crlfDelay: Infinity });
  for await (const line of rl) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    onRow(JSON.parse(trimmed) as T);
    count += 1;
  }
  return count;
}

export async function buildLoadPlan(
  repoRoot: string,
  options: { includeHistory: boolean; includeRijal: boolean },
): Promise<LoadPlan> {
  const historyDir = resolve(repoRoot, 'datasets/hadith-data/history/output');
  const rijalDir = resolve(repoRoot, 'datasets/hadith-data/rijal/output');

  const worksMap = new Map<string, StagedWork>();
  const editionsMap = new Map<string, StagedEdition>();
  const historyCitationsMap = new Map<string, StagedCitation>();
  const rijalCitationsMap = new Map<string, StagedCitation>();
  let rijalCitationRefsTotal = 0;

  const temporalAssertionsList: StagedTemporalAssertion[] = [];
  let temporalAssertionsSkipped = 0;
  const locationsList: StagedLocation[] = [];
  const eventsList: StagedEvent[] = [];
  const epochCitationsList: StagedEpochCitation[] = [];
  const narratorEventsMap = new Map<string, StagedNarratorEvent>();
  let narratorEventsSkippedMissingKeys = 0;

  const eventByTitle = new Map<string, string>();
  const eventByKey = new Map<string, string>();
  const claimIdToCitationId = new Map<string, string>();

  // 1. Load History lane
  if (options.includeHistory) {
    const worksRaw = JSON.parse(
      readFileSync(resolve(historyDir, 'works_and_editions.json'), 'utf-8'),
    ) as Record<string, Record<string, unknown>>;
    for (const w of Object.values(worksRaw)) {
      const workId = String(w.work_id);
      worksMap.set(workId, {
        id: workId,
        title: String(w.title),
        titleAr: normalizeNonEmpty(w.title_ar),
        author: normalizeNonEmpty(w.author),
        authorDeathYearHijri: typeof w.author_death_year_hijri === 'number' ? w.author_death_year_hijri : null,
        openitiUri: normalizeNonEmpty(w.openiti_uri),
      });
      const editionId = normalizeNonEmpty(w.edition_id);
      if (editionId) {
        editionsMap.set(editionId, {
          id: editionId,
          workId,
          editor: normalizeNonEmpty(w.editor),
          publisher: normalizeNonEmpty(w.publisher),
          place: normalizeNonEmpty(w.place),
          year: normalizeNonEmpty(w.year),
          locatorScheme: normalizeNonEmpty(w.locator_scheme),
          url: normalizeNonEmpty(w.library_url),
          rightsStatus: normalizeRights(w.rights_status),
        });
      }
    }

    await readJsonlGz(resolve(historyDir, 'citations.jsonl.gz'), (row) => {
      const id = String(row.id);
      const workId = String(row.work_id);
      const editionId = normalizeNonEmpty(row.edition_id);
      historyCitationsMap.set(id, {
        id,
        workId,
        editionId,
        volume: row.volume != null ? String(row.volume) : null,
        page: row.page != null ? String(row.page) : null,
        locator: normalizeNonEmpty(row.locator_text),
        url: null,
        quoteAr: normalizeNonEmpty(row.quote_ar),
        quoteEn: null,
        reviewState: 'candidate_only',
        sourceSpan: normalizeJsonObject(row.source_span),
        sourceSha256: normalizeSha256(row.source_sha256),
        sourceFile: normalizeNonEmpty(row.source_file),
      });
    });

    await readJsonlGz(resolve(historyDir, 'location_candidates.jsonl.gz'), (row) => {
      const id = String(row.id);
      const lat = typeof row.latitude === 'number' && row.latitude >= -90 && row.latitude <= 90 ? row.latitude : null;
      const lon = typeof row.longitude === 'number' && row.longitude >= -180 && row.longitude <= 180 ? row.longitude : null;
      locationsList.push({
        id,
        name: String(row.name),
        nameArabic: normalizeNonEmpty(row.name_arabic),
        modernCountry: normalizeNonEmpty(row.modern_country),
        region: normalizeNonEmpty(row.region),
        description: normalizeNonEmpty(row.reasoning),
        latitude: lat,
        longitude: lon,
        kind: normalizeNonEmpty(row.kind),
        formsAr: Array.isArray(row.forms_ar) ? row.forms_ar.map(String) : [],
        ambiguousForms: normalizeJsonObject(row.ambiguous_forms),
        citedInCitationIds: Array.isArray(row.cited_in_citation_ids) ? row.cited_in_citation_ids.map(String) : [],
        coordinatesBasis: normalizeNonEmpty(row.coordinates_basis),
      });
    });

    // Read event_candidates first so date_claims and narrator_event_candidates can resolve titles/keys -> event_id
    await readJsonlGz(resolve(historyDir, 'event_candidates.jsonl.gz'), (row) => {
      const id = String(row.id);
      const title = String(row.title);
      const key = normalizeNonEmpty(row.key);
      const originKind = row.origin === 'seed' ? 'seed' : 'history_lane_candidate';
      eventByTitle.set(title, id);
      if (key) eventByKey.set(key, id);

      const startYear =
        typeof row.start_year_hijri === 'number'
          ? row.start_year_hijri
          : typeof row.seed_start_year_hijri === 'number'
            ? row.seed_start_year_hijri
            : null;
      let endYear =
        typeof row.end_year_hijri === 'number'
          ? row.end_year_hijri
          : typeof row.seed_end_year_hijri === 'number'
            ? row.seed_end_year_hijri
            : null;
      if (startYear !== null && endYear !== null && endYear < startYear) {
        endYear = null;
      }

      eventsList.push({
        id,
        key,
        originKind,
        title,
        titleArabic: normalizeNonEmpty(row.title_arabic),
        category: normalizeCategory(row.category),
        startYearHijri: startYear,
        endYearHijri: endYear,
        locationName: normalizeNonEmpty(row.location_name),
        traditionContext: normalizeTradition(row.tradition_context),
        citationId: null,
      });
    });

    await readJsonlGz(resolve(historyDir, 'date_claims.jsonl.gz'), (row) => {
      const id = String(row.id);
      const citationId = String(row.citation_id);
      claimIdToCitationId.set(id, citationId);

      const targetKind = String(row.target_kind);
      const target = String(row.target);
      let eventId: string | null = null;
      let epochId: string | null = null;
      if (targetKind === 'epoch') {
        epochId = target;
      } else if (targetKind === 'event') {
        eventId = eventByTitle.get(target) ?? null;
      } else if (targetKind === 'new') {
        eventId = eventByKey.get(target) ?? null;
      }

      if ((eventId ? 1 : 0) + (epochId ? 1 : 0) !== 1) {
        temporalAssertionsSkipped += 1;
        return;
      }

      const rawBoundary = normalizeNonEmpty(row.boundary);
      const boundary: 'start' | 'end' | null =
        epochId && (rawBoundary === 'start' || rawBoundary === 'end') ? rawBoundary : null;
      const yearHijri = typeof row.year_hijri === 'number' ? row.year_hijri : null;
      const rawDateBasis = normalizeNonEmpty(row.date_basis);
      const dateBasis: 'passage' | 'section_heading' | null =
        rawDateBasis === 'passage' || rawDateBasis === 'section_heading' ? rawDateBasis : null;
      const alternatives = Array.isArray(row.alternatives_stated)
        ? row.alternatives_stated.filter((v): v is number => typeof v === 'number' && Number.isInteger(v))
        : [];
      const flags = Array.isArray(row.flags) ? row.flags.map(String) : [];

      temporalAssertionsList.push({
        id,
        eventId,
        epochId,
        collectionId: null,
        boundary,
        predicate: normalizeNonEmpty(row.predicate) ?? 'occurred_in',
        yearMin: yearHijri,
        yearMax: yearHijri,
        calendar: 'hijri',
        precision: yearHijri !== null ? 'year' : null,
        alternatives,
        monthDay: normalizeNonEmpty(row.month_day),
        statedAr: normalizeNonEmpty(row.stated_ar),
        statementEn: normalizeNonEmpty(row.statement_en),
        dateBasis,
        qualifier: normalizeNonEmpty(row.qualifier),
        reckoning: normalizeNonEmpty(row.reckoning),
        attributedTo: normalizeNonEmpty(row.attributed_to),
        perspective: normalizeJsonObject(row.perspective),
        flags,
        note: normalizeNonEmpty(row.note),
        citationId,
        reviewState: 'candidate_only',
        aiReview: normalizeJsonObject(row.ai_review),
        humanReviews: Array.isArray(row.human_reviews) ? row.human_reviews : [],
      });
    });

    await readJsonlGz(resolve(historyDir, 'epoch_candidates.jsonl.gz'), (row) => {
      const id = String(row.id);
      const claimRef = normalizeNonEmpty(row.citation_id_for_epochs_row);
      const citationId = claimRef ? (claimIdToCitationId.get(claimRef) ?? null) : null;
      epochCitationsList.push({ id, citationId });
    });

    await readJsonlGz(resolve(historyDir, 'narrator_event_candidates.jsonl.gz'), (row) => {
      const narratorId = normalizeNonEmpty(row.narrator_id);
      const eventId =
        normalizeNonEmpty(row.event_id) ??
        (normalizeNonEmpty(row.event_new_key) ? (eventByKey.get(String(row.event_new_key)) ?? null) : null);
      if (!narratorId || !eventId) {
        narratorEventsSkippedMissingKeys += 1;
        return;
      }
      const role = normalizeNonEmpty(row.role) ?? 'Participant';
      const dedupeKey = `${narratorId}|${eventId}|${role}`;
      narratorEventsMap.set(dedupeKey, {
        narratorId,
        eventId,
        role,
        citationId: normalizeNonEmpty(row.citation_id),
        statedAr: normalizeNonEmpty(row.stated_ar),
        aiReview: normalizeJsonObject(row.ai_review),
        humanReviews: Array.isArray(row.human_reviews) ? row.human_reviews : [],
      });
    });
  }

  // 2. Load RIJ lane
  if (options.includeRijal) {
    const rijalWorksRaw = JSON.parse(readFileSync(resolve(rijalDir, 'rijal_works.json'), 'utf-8')) as {
      works: Array<Record<string, unknown>>;
    };

    const rijalWorkEditionId = new Map<string, string>();
    for (const w of rijalWorksRaw.works) {
      const workId = String(w.work_id);
      const openitiUri = normalizeNonEmpty(w.openiti_uri);
      worksMap.set(workId, {
        id: workId,
        title: String(w.title_en),
        titleAr: normalizeNonEmpty(w.title_ar),
        author: normalizeNonEmpty(w.author_name_en),
        authorDeathYearHijri: typeof w.author_death_year_hijri === 'number' ? w.author_death_year_hijri : null,
        openitiUri,
      });

      const editionId = openitiUri ? `edition:openiti:${openitiUri}` : `edition:${workId}`;
      rijalWorkEditionId.set(workId, editionId);
      const ed = normalizeJsonObject(w.edition);
      editionsMap.set(editionId, {
        id: editionId,
        workId,
        editor: normalizeNonEmpty(ed?.editor),
        publisher: normalizeNonEmpty(ed?.publisher),
        place: normalizeNonEmpty(ed?.place),
        year: normalizeNonEmpty(ed?.year),
        locatorScheme: normalizeNonEmpty(w.locator_scheme),
        url: normalizeNonEmpty(ed?.read_online) ?? normalizeNonEmpty(ed?.version_based_on),
        rightsStatus: 'pending',
      });

      // Also ingest the header citation on rijal_works.json (6 rows)
      const cit = normalizeJsonObject(w.citation);
      if (cit && cit.citation_status === 'cited') {
        rijalCitationRefsTotal += 1;
        const span = normalizeJsonObject(cit.source_span);
        const sha = normalizeSha256(cit.source_sha256);
        const citId = deterministicRijalCitationId(workId, editionId, span, sha);
        if (!rijalCitationsMap.has(citId)) {
          const loc = formatRijalLocator(cit.locator);
          rijalCitationsMap.set(citId, {
            id: citId,
            workId,
            editionId,
            volume: loc.volume,
            page: loc.page,
            locator: loc.text,
            url: null,
            quoteAr: normalizeNonEmpty(cit.passage_ar),
            quoteEn: null,
            reviewState: 'candidate_only',
            sourceSpan: span,
            sourceSha256: sha,
            sourceFile: normalizeNonEmpty(cit.source_file),
          });
        }
      }
    }

    for (const fileName of RIJAL_CITED_JSONL_FILES) {
      await readJsonlGz(resolve(rijalDir, fileName), (row) => {
        const cit = normalizeJsonObject(row.citation);
        if (!cit || cit.citation_status !== 'cited') return;
        rijalCitationRefsTotal += 1;

        const workObj = normalizeJsonObject(cit.work);
        const workId = normalizeNonEmpty(workObj?.work_id);
        if (!workId || !worksMap.has(workId)) return;

        const editionObj = normalizeJsonObject(cit.edition);
        const openitiUri = normalizeNonEmpty(editionObj?.openiti_uri);
        const editionId = (openitiUri ? `edition:openiti:${openitiUri}` : null) ?? rijalWorkEditionId.get(workId) ?? null;
        const span = normalizeJsonObject(cit.source_span);
        const sha = normalizeSha256(cit.source_sha256);
        const citId = deterministicRijalCitationId(workId, editionId, span, sha);

        if (!rijalCitationsMap.has(citId)) {
          const loc = formatRijalLocator(cit.locator);
          rijalCitationsMap.set(citId, {
            id: citId,
            workId,
            editionId,
            volume: loc.volume,
            page: loc.page,
            locator: loc.text,
            url: null,
            quoteAr: normalizeNonEmpty(cit.passage_ar),
            quoteEn: null,
            reviewState: 'candidate_only',
            sourceSpan: span,
            sourceSha256: sha,
            sourceFile: normalizeNonEmpty(cit.source_file),
          });
        }
      });
    }
  }

  return {
    works: Array.from(worksMap.values()),
    editions: Array.from(editionsMap.values()),
    historyCitations: Array.from(historyCitationsMap.values()),
    rijalCitations: Array.from(rijalCitationsMap.values()),
    rijalCitationRefsTotal,
    temporalAssertions: temporalAssertionsList,
    temporalAssertionsSkipped,
    locations: locationsList,
    events: eventsList,
    epochCitations: epochCitationsList,
    narratorEvents: Array.from(narratorEventsMap.values()),
    narratorEventsSkippedMissingKeys,
  };
}

function resolveConnectionForScript(argv: readonly string[], dryRun: boolean): { name: 'development' | 'production'; url: string } {
  if (!dryRun) {
    return resolveTargetDatabase(argv, { required: true });
  }
  // In --dry-run mode, allow read-only inspection of production without --confirm-production
  loadEnvironment({ path: '.env.local', quiet: true });
  const idx = argv.indexOf('--database');
  const requested = idx >= 0 ? argv[idx + 1] : argv.find((v) => v.startsWith('--database='))?.slice('--database='.length);
  const name = (requested ?? 'development') as 'development' | 'production';
  if (name === 'production') {
    const url = process.env.DATABASE_URL_PRODUCTION?.trim();
    if (!url) throw new Error('DATABASE_URL_PRODUCTION is not set.');
    return { name: 'production', url };
  }
  return resolveTargetDatabase(['--database', 'development'], { required: true });
}

async function runBatched<T>(items: readonly T[], batchSize: number, fn: (batch: readonly T[]) => Promise<void>): Promise<void> {
  for (let i = 0; i < items.length; i += batchSize) {
    await fn(items.slice(i, i + batchSize));
  }
}

export async function executeLoad(argv: readonly string[]): Promise<void> {
  const dryRun = argv.includes('--dry-run');
  const onlyIdx = argv.indexOf('--only');
  const only = onlyIdx >= 0 ? argv[onlyIdx + 1] : undefined;
  const includeHistory = !only || only === 'history';
  const includeRijal = !only || only === 'rijal';
  if (!includeHistory && !includeRijal) {
    throw new Error('--only must be "history" or "rijal".');
  }

  const target = resolveConnectionForScript(argv, dryRun);
  const repoRoot = process.cwd();
  console.log(`[load-history-rijal] Target: ${target.name} (${dryRun ? 'DRY RUN — no writes' : 'LIVE WRITE'})`);

  const plan = await buildLoadPlan(repoRoot, { includeHistory, includeRijal });

  const sqlClient = postgres(target.url, connectionOptions(target.url, 5));
  const db = drizzle(sqlClient, { schema });

  try {
    // 1. Resolve current dataset_version_id
    const [currentDv] = await db
      .select({ id: datasetVersions.id })
      .from(datasetVersions)
      .where(eq(datasetVersions.isCurrent, true))
      .limit(1);
    const datasetVersionId = currentDv?.id;
    if (!datasetVersionId) {
      throw new Error('No current dataset_versions row (is_current = true) found in target database.');
    }

    // 2. Validate FK targets for narrator_events & epochs
    const existingNarratorIds = new Set<string>();
    if (plan.narratorEvents.length > 0) {
      const candidateNarratorIds = Array.from(new Set(plan.narratorEvents.map((ne) => ne.narratorId)));
      await runBatched(candidateNarratorIds, 500, async (batch) => {
        const rows = await db
          .select({ id: narrators.id })
          .from(narrators)
          .where(inArray(narrators.id, [...batch]));
        for (const r of rows) existingNarratorIds.add(r.id);
      });
    }

    const validNarratorEvents = plan.narratorEvents.filter((ne) => existingNarratorIds.has(ne.narratorId));
    const skippedMissingNarratorFk = plan.narratorEvents.length - validNarratorEvents.length;

    const existingEpochIds = new Set<string>();
    if (plan.epochCitations.length > 0) {
      const rows = await db.select({ id: epochs.id }).from(epochs);
      for (const r of rows) existingEpochIds.add(r.id);
    }
    const matchingEpochCitations = plan.epochCitations.filter((e) => e.citationId && existingEpochIds.has(e.id));

    const newEvents = plan.events.filter((e) => e.originKind === 'history_lane_candidate');
    const seedEvents = plan.events.filter((e) => e.originKind === 'seed');

    console.log(`[load-history-rijal] Current dataset_version_id: ${datasetVersionId}`);
    console.log(`[load-history-rijal] Staged counts:`);
    console.log(`  bibliographic_works : ${plan.works.length}`);
    console.log(`  editions            : ${plan.editions.length}`);
    console.log(`  citations (history) : ${plan.historyCitations.length}`);
    console.log(`  citations (rijal)   : ${plan.rijalCitations.length} distinct (from ${plan.rijalCitationRefsTotal} verified references)`);
    console.log(`  temporal_assertions : ${plan.temporalAssertions.length} (skipped unresolved: ${plan.temporalAssertionsSkipped})`);
    console.log(`  locations           : ${plan.locations.length}`);
    console.log(`  historical_events   : ${newEvents.length} new candidates (+ ${seedEvents.length} seed refs)`);
    console.log(`  epochs (cit links)  : ${matchingEpochCitations.length} / ${plan.epochCitations.length}`);
    console.log(`  narrator_events     : ${validNarratorEvents.length} ready (skipped missing keys: ${plan.narratorEventsSkippedMissingKeys}, missing narrator FK: ${skippedMissingNarratorFk})`);

    if (dryRun) {
      console.log(`[load-history-rijal] Dry-run complete. 0 rows written.`);
      return;
    }

    const now = new Date();

    // Upsert bibliographic_works
    await runBatched(plan.works, BATCH_SIZE, async (batch) => {
      await db
        .insert(bibliographicWorks)
        .values(
          batch.map((w) => ({
            id: w.id,
            title: w.title,
            titleAr: w.titleAr,
            author: w.author,
            authorDeathYearHijri: w.authorDeathYearHijri,
            openitiUri: w.openitiUri,
            firstSeenDatasetVersionId: datasetVersionId,
            changedInDatasetVersionId: datasetVersionId,
            updatedAt: now,
          })),
        )
        .onConflictDoUpdate({
          target: bibliographicWorks.id,
          set: {
            title: sql`excluded.title`,
            titleAr: sql`excluded.title_ar`,
            author: sql`excluded.author`,
            authorDeathYearHijri: sql`excluded.author_death_year_hijri`,
            openitiUri: sql`excluded.openiti_uri`,
            changedInDatasetVersionId: sql`excluded.changed_in_dataset_version_id`,
            updatedAt: now,
          },
        });
    });

    // Upsert editions
    await runBatched(plan.editions, BATCH_SIZE, async (batch) => {
      await db
        .insert(editions)
        .values(
          batch.map((e) => ({
            id: e.id,
            workId: e.workId,
            editor: e.editor,
            publisher: e.publisher,
            place: e.place,
            year: e.year,
            locatorScheme: e.locatorScheme,
            url: e.url,
            rightsStatus: e.rightsStatus,
            firstSeenDatasetVersionId: datasetVersionId,
            changedInDatasetVersionId: datasetVersionId,
            updatedAt: now,
          })),
        )
        .onConflictDoUpdate({
          target: editions.id,
          set: {
            editor: sql`excluded.editor`,
            publisher: sql`excluded.publisher`,
            place: sql`excluded.place`,
            year: sql`excluded.year`,
            locatorScheme: sql`excluded.locator_scheme`,
            url: sql`excluded.url`,
            changedInDatasetVersionId: sql`excluded.changed_in_dataset_version_id`,
            updatedAt: now,
          },
        });
    });

    // Upsert citations (history + rijal)
    const allCitations = [...plan.historyCitations, ...plan.rijalCitations];
    await runBatched(allCitations, BATCH_SIZE, async (batch) => {
      await db
        .insert(citations)
        .values(
          batch.map((c) => ({
            id: c.id,
            workId: c.workId,
            editionId: c.editionId,
            volume: c.volume,
            page: c.page,
            locator: c.locator,
            url: c.url,
            quoteAr: c.quoteAr,
            quoteEn: c.quoteEn,
            reviewState: c.reviewState,
            sourceSpan: c.sourceSpan,
            sourceSha256: c.sourceSha256,
            sourceFile: c.sourceFile,
            firstSeenDatasetVersionId: datasetVersionId,
            changedInDatasetVersionId: datasetVersionId,
            updatedAt: now,
          })),
        )
        .onConflictDoUpdate({
          target: citations.id,
          set: {
            editionId: sql`excluded.edition_id`,
            volume: sql`excluded.volume`,
            page: sql`excluded.page`,
            locator: sql`excluded.locator`,
            quoteAr: sql`excluded.quote_ar`,
            sourceSpan: sql`excluded.source_span`,
            sourceSha256: sql`excluded.source_sha256`,
            sourceFile: sql`excluded.source_file`,
            changedInDatasetVersionId: sql`excluded.changed_in_dataset_version_id`,
            updatedAt: now,
          },
        });
    });

    // Upsert temporal_assertions
    await runBatched(plan.temporalAssertions, BATCH_SIZE, async (batch) => {
      await db
        .insert(temporalAssertions)
        .values(
          batch.map((ta) => ({
            id: ta.id,
            eventId: ta.eventId,
            epochId: ta.epochId,
            collectionId: ta.collectionId,
            boundary: ta.boundary,
            predicate: ta.predicate,
            yearMin: ta.yearMin,
            yearMax: ta.yearMax,
            calendar: ta.calendar,
            precision: ta.precision,
            alternatives: ta.alternatives,
            monthDay: ta.monthDay,
            statedAr: ta.statedAr,
            statementEn: ta.statementEn,
            dateBasis: ta.dateBasis,
            qualifier: ta.qualifier,
            reckoning: ta.reckoning,
            attributedTo: ta.attributedTo,
            perspective: ta.perspective,
            flags: ta.flags,
            note: ta.note,
            citationId: ta.citationId,
            reviewState: ta.reviewState,
            aiReview: ta.aiReview,
            humanReviews: ta.humanReviews,
            firstSeenDatasetVersionId: datasetVersionId,
            changedInDatasetVersionId: datasetVersionId,
            updatedAt: now,
          })),
        )
        .onConflictDoUpdate({
          target: temporalAssertions.id,
          set: {
            eventId: sql`excluded.event_id`,
            epochId: sql`excluded.epoch_id`,
            boundary: sql`excluded.boundary`,
            predicate: sql`excluded.predicate`,
            yearMin: sql`excluded.year_min`,
            yearMax: sql`excluded.year_max`,
            alternatives: sql`excluded.alternatives`,
            monthDay: sql`excluded.month_day`,
            statedAr: sql`excluded.stated_ar`,
            statementEn: sql`excluded.statement_en`,
            dateBasis: sql`excluded.date_basis`,
            qualifier: sql`excluded.qualifier`,
            reckoning: sql`excluded.reckoning`,
            attributedTo: sql`excluded.attributed_to`,
            perspective: sql`excluded.perspective`,
            flags: sql`excluded.flags`,
            note: sql`excluded.note`,
            citationId: sql`excluded.citation_id`,
            aiReview: sql`excluded.ai_review`,
            changedInDatasetVersionId: sql`excluded.changed_in_dataset_version_id`,
            updatedAt: now,
          },
        });
    });

    // Upsert locations
    await runBatched(plan.locations, BATCH_SIZE, async (batch) => {
      await db
        .insert(locations)
        .values(
          batch.map((loc) => ({
            id: loc.id,
            name: loc.name,
            nameArabic: loc.nameArabic,
            modernCountry: loc.modernCountry,
            region: loc.region,
            description: loc.description,
            latitude: loc.latitude,
            longitude: loc.longitude,
            verificationStatus: 'unverified' as const,
            origin: 'ai_research' as const,
            kind: loc.kind,
            formsAr: loc.formsAr,
            ambiguousForms: loc.ambiguousForms,
            citedInCitationIds: loc.citedInCitationIds,
            coordinatesBasis: loc.coordinatesBasis,
            createdBy: LOADER_ACTOR,
            updatedBy: LOADER_ACTOR,
            updatedAt: now,
          })),
        )
        .onConflictDoUpdate({
          target: locations.id,
          set: {
            nameArabic: sql`coalesce(${locations.nameArabic}, excluded.name_arabic)`,
            kind: sql`excluded.kind`,
            formsAr: sql`excluded.forms_ar`,
            ambiguousForms: sql`excluded.ambiguous_forms`,
            citedInCitationIds: sql`excluded.cited_in_citation_ids`,
            coordinatesBasis: sql`excluded.coordinates_basis`,
            updatedBy: LOADER_ACTOR,
            updatedAt: now,
          },
        });
    });

    // Upsert new historical_events candidates
    await runBatched(newEvents, BATCH_SIZE, async (batch) => {
      await db
        .insert(historicalEvents)
        .values(
          batch.map((ev) => ({
            id: ev.id,
            key: ev.key,
            title: ev.title,
            titleArabic: ev.titleArabic,
            category: ev.category,
            startYearHijri: ev.startYearHijri,
            endYearHijri: ev.endYearHijri,
            locationName: ev.locationName,
            traditionContext: ev.traditionContext,
            verificationStatus: 'unverified' as const,
            publicationReady: false,
            origin: 'ai_research' as const,
            createdBy: LOADER_ACTOR,
            updatedBy: LOADER_ACTOR,
            updatedAt: now,
          })),
        )
        .onConflictDoUpdate({
          target: historicalEvents.id,
          set: {
            key: sql`coalesce(${historicalEvents.key}, excluded.key)`,
            titleArabic: sql`coalesce(${historicalEvents.titleArabic}, excluded.title_arabic)`,
            traditionContext: sql`coalesce(${historicalEvents.traditionContext}, excluded.tradition_context)`,
            updatedBy: LOADER_ACTOR,
            updatedAt: now,
          },
        });
    });

    // Link citation_id on existing epochs where citation_id is currently null
    for (const ep of matchingEpochCitations) {
      if (!ep.citationId) continue;
      await db
        .update(epochs)
        .set({ citationId: ep.citationId, updatedBy: LOADER_ACTOR, updatedAt: now })
        .where(sql`${epochs.id} = ${ep.id} and ${epochs.citationId} is null`);
    }

    // Upsert narrator_events (idempotent on live unique index (narrator_id, event_id, role) where retired_at is null)
    await runBatched(validNarratorEvents, BATCH_SIZE, async (batch) => {
      await db
        .insert(narratorEvents)
        .values(
          batch.map((ne) => ({
            narratorId: ne.narratorId,
            eventId: ne.eventId,
            role: ne.role,
            citationId: ne.citationId,
            statedAr: ne.statedAr,
            aiReview: ne.aiReview,
            humanReviews: ne.humanReviews,
            createdBy: LOADER_ACTOR,
          })),
        )
        .onConflictDoUpdate({
          target: [narratorEvents.narratorId, narratorEvents.eventId, narratorEvents.role],
          targetWhere: isNull(narratorEvents.retiredAt),
          set: {
            citationId: sql`coalesce(excluded.citation_id, ${narratorEvents.citationId})`,
            statedAr: sql`coalesce(excluded.stated_ar, ${narratorEvents.statedAr})`,
            aiReview: sql`coalesce(excluded.ai_review, ${narratorEvents.aiReview})`,
          },
        });
    });

    console.log(`[load-history-rijal] Live load complete.`);
  } finally {
    await sqlClient.end({ timeout: 5 });
  }
}

if (/load-history-rijal\.ts$/.test(process.argv[1] ?? '')) {
  executeLoad(process.argv.slice(2)).catch((error) => {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  });
}
