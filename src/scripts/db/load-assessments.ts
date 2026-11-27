/**
 * Idempotent loader for the staged `grading-coverage` assessment outputs in
 * `datasets/hadith-data/assessments/`:
 *   - hadith_assessments.jsonl.gz   -> `hadith_assessments`
 *   - narrator_assessments.jsonl.gz -> `narrator_assessments`
 *
 * No placeholder rows are written: uncited rows (`citation_status !== 'cited'`),
 * unlinked narrator rows (`narrator_id == null`), and rows with missing FK targets
 * are filtered out and reported explicitly.
 *
 * Usage:
 *   npx tsx --conditions=react-server src/scripts/db/load-assessments.ts --dry-run --database development
 *   npx tsx --conditions=react-server src/scripts/db/load-assessments.ts --dry-run --database production
 *   npx tsx --conditions=react-server src/scripts/db/load-assessments.ts --database development
 *   npx tsx --conditions=react-server src/scripts/db/load-assessments.ts --database production --confirm-production
 */
import { createReadStream } from 'node:fs';
import { resolve } from 'node:path';
import { createInterface } from 'node:readline';
import { createGunzip } from 'node:zlib';
import { config as loadEnvironment } from 'dotenv';
import { eq, inArray, sql } from 'drizzle-orm';
import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { connectionOptions } from '../../db/connection-options';
import * as schema from '../../db/schema';
import { hadithAssessments, narratorAssessments } from '../../db/schema/assessments';
import { hadiths, traditions } from '../../db/schema/corpus';
import { citations } from '../../db/schema/evidence';
import { narrators } from '../../db/schema/narrators';
import { datasetVersions } from '../../db/schema/operations';
import { resolveTargetDatabase } from '../../db/target-database';

export const LOADER_ACTOR = 'system:load-assessments';
export const BATCH_SIZE = 500;

const VALID_GRADE_SCHEMES = new Set([
  'sunni_7tier',
  'imami_4tier',
  'zaydi_3tier',
  'ibadi_2tier',
  'unspecified',
] as const);
export type GradeScheme = typeof VALID_GRADE_SCHEMES extends Set<infer T> ? T : never;

const VALID_ASSESSMENT_KINDS = new Set([
  'cited_ruling',
  'compiler_criterion',
  'compiler_statement',
  'collection_label',
] as const);
export type AssessmentKind = typeof VALID_ASSESSMENT_KINDS extends Set<infer T> ? T : never;

const VALID_GRADE_CANONICAL = new Set([
  'sahih',
  'hasan',
  'muwaththaq',
  'da_if',
  'majhul',
  'mursal',
  'mawdu',
  'mu_tabar',
  'mukhtalaf',
  'ungraded',
] as const);
export type GradeCanonical = typeof VALID_GRADE_CANONICAL extends Set<infer T> ? T : never;

const VALID_REVIEW_STATES = new Set([
  'candidate_only',
  'lexicon_unverified',
  'source_provided',
  'source_verified',
  'human_verified',
] as const);
export type EvidenceReviewState = typeof VALID_REVIEW_STATES extends Set<infer T> ? T : never;

const VALID_NARRATOR_ASSESSMENT_KINDS = new Set(['critic_ruling', 'consensus_summary'] as const);
export type NarratorAssessmentKind = typeof VALID_NARRATOR_ASSESSMENT_KINDS extends Set<infer T> ? T : never;

const VALID_NARRATOR_VERDICTS = new Set([
  'thiqa',
  'thiqa_thabt',
  'saduq',
  'la_basa_bihi',
  'majhul',
  'daif',
  'matruk',
  'kadhab',
  'mukhtalaf_fihi',
  'not_applicable',
] as const);
export type NarratorVerdict = typeof VALID_NARRATOR_VERDICTS extends Set<infer T> ? T : never;

export interface StagedHadithAssessment {
  id: string;
  hadithId: string;
  traditionId: string;
  gradeScheme: GradeScheme;
  ordinal: number;
  kind: AssessmentKind;
  grader: string | null;
  gradeRaw: string;
  gradeCanonical: GradeCanonical | null;
  gradeDetail: string | null;
  citationRaw: string | null;
  citedWork: string | null;
  citedVolume: string | null;
  citedPage: string | null;
  citationId: string | null;
  sourceField: string;
  reviewState: EvidenceReviewState;
  alreadyLoaded: boolean;
}

export interface StagedNarratorAssessment {
  id: string;
  narratorId: string;
  traditionId: string;
  kind: NarratorAssessmentKind;
  verdict: NarratorVerdict;
  critic: string | null;
  quoteAr: string;
  isCompanion: boolean | null;
  provenance: string;
  citationId: string | null;
}

export interface AssessmentsLoadPlan {
  hadithAssessments: StagedHadithAssessment[];
  hadithAssessmentsRawTotal: number;
  hadithAssessmentsSkippedUncited: number;
  hadithAssessmentsSkippedInvalid: number;
  narratorAssessments: StagedNarratorAssessment[];
  narratorAssessmentsRawTotal: number;
  narratorAssessmentsSkippedUncited: number;
  narratorAssessmentsSkippedNoNarratorId: number;
  narratorAssessmentsSkippedInvalid: number;
}

export function normalizeNonEmpty(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function normalizeGradeScheme(value: unknown): GradeScheme | null {
  if (typeof value !== 'string') return null;
  return VALID_GRADE_SCHEMES.has(value as GradeScheme) ? (value as GradeScheme) : null;
}

export function normalizeAssessmentKind(value: unknown): AssessmentKind | null {
  if (typeof value !== 'string') return null;
  return VALID_ASSESSMENT_KINDS.has(value as AssessmentKind) ? (value as AssessmentKind) : null;
}

export function normalizeGradeCanonical(value: unknown): GradeCanonical | null {
  if (typeof value !== 'string') return null;
  return VALID_GRADE_CANONICAL.has(value as GradeCanonical) ? (value as GradeCanonical) : null;
}

export function normalizeReviewState(value: unknown): EvidenceReviewState {
  if (typeof value === 'string' && VALID_REVIEW_STATES.has(value as EvidenceReviewState)) {
    return value as EvidenceReviewState;
  }
  return 'candidate_only';
}

export function normalizeNarratorAssessmentKind(value: unknown): NarratorAssessmentKind | null {
  if (typeof value !== 'string') return null;
  return VALID_NARRATOR_ASSESSMENT_KINDS.has(value as NarratorAssessmentKind)
    ? (value as NarratorAssessmentKind)
    : null;
}

export function normalizeNarratorVerdict(value: unknown): NarratorVerdict | null {
  if (typeof value !== 'string') return null;
  return VALID_NARRATOR_VERDICTS.has(value as NarratorVerdict) ? (value as NarratorVerdict) : null;
}

export function buildNarratorProvenance(row: Record<string, unknown>): string {
  const codes = Array.isArray(row.source_codes)
    ? row.source_codes.map(String).filter((s) => s.trim().length > 0)
    : [];
  const basis = normalizeNonEmpty(row.basis_kind) ?? 'unknown_basis';
  const work = normalizeNonEmpty(row.work) ?? normalizeNonEmpty(row.rijal_work_key);
  const prefix = codes.length > 0 ? codes.join('+') : 'UNKNOWN';
  return work ? `${prefix}:${basis}:${work}` : `${prefix}:${basis}`;
}

export function parseHadithAssessmentRow(
  row: Record<string, unknown>,
): { ok: true; value: StagedHadithAssessment } | { ok: false; reason: 'uncited' | 'invalid' } {
  if (row.citation_status !== 'cited') {
    return { ok: false, reason: 'uncited' };
  }
  const id = normalizeNonEmpty(row.id);
  const hadithId = normalizeNonEmpty(row.hadith_id);
  const traditionId = normalizeNonEmpty(row.tradition_id);
  const gradeScheme = normalizeGradeScheme(row.grade_scheme);
  const kind = normalizeAssessmentKind(row.kind);
  const gradeRaw = normalizeNonEmpty(row.grade_raw);
  const sourceField = normalizeNonEmpty(row.source_field);
  const ordinal = typeof row.ordinal === 'number' && Number.isInteger(row.ordinal) ? row.ordinal : null;

  if (!id || !hadithId || !traditionId || !gradeScheme || !kind || !gradeRaw || !sourceField || ordinal === null) {
    return { ok: false, reason: 'invalid' };
  }

  return {
    ok: true,
    value: {
      id,
      hadithId,
      traditionId,
      gradeScheme,
      ordinal,
      kind,
      grader: normalizeNonEmpty(row.grader),
      gradeRaw,
      gradeCanonical: normalizeGradeCanonical(row.grade_canonical),
      gradeDetail: normalizeNonEmpty(row.statement_ar) ?? normalizeNonEmpty(row.grade_detail),
      citationRaw: normalizeNonEmpty(row.citation_raw),
      citedWork: normalizeNonEmpty(row.cited_work),
      citedVolume: row.cited_volume != null ? normalizeNonEmpty(String(row.cited_volume)) : null,
      citedPage: row.cited_page != null ? normalizeNonEmpty(String(row.cited_page)) : null,
      citationId: normalizeNonEmpty(row.citation_id),
      sourceField,
      reviewState: normalizeReviewState(row.review_state),
      alreadyLoaded: row.already_loaded === true,
    },
  };
}

export function parseNarratorAssessmentRow(
  row: Record<string, unknown>,
): { ok: true; value: StagedNarratorAssessment } | { ok: false; reason: 'uncited' | 'no_narrator_id' | 'invalid' } {
  if (row.citation_status !== 'cited') {
    return { ok: false, reason: 'uncited' };
  }
  const narratorId = normalizeNonEmpty(row.narrator_id);
  if (!narratorId) {
    return { ok: false, reason: 'no_narrator_id' };
  }
  const id = normalizeNonEmpty(row.id);
  const traditionId = normalizeNonEmpty(row.tradition_id);
  const kind = normalizeNarratorAssessmentKind(row.kind);
  const quoteAr = normalizeNonEmpty(row.quote_ar) ?? normalizeNonEmpty(row.verdict_raw);

  if (!id || !traditionId || !kind || !quoteAr) {
    return { ok: false, reason: 'invalid' };
  }

  const verdict = normalizeNarratorVerdict(row.verdict_canonical) ?? 'not_applicable';
  const isCompanion = row.aspect === 'generation_or_imam' ? true : null;

  return {
    ok: true,
    value: {
      id,
      narratorId,
      traditionId,
      kind,
      verdict,
      critic: normalizeNonEmpty(row.critic),
      quoteAr,
      isCompanion,
      provenance: buildNarratorProvenance(row),
      citationId: normalizeNonEmpty(row.citation_id),
    },
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
  options: { includeHadith: boolean; includeNarrator: boolean },
): Promise<AssessmentsLoadPlan> {
  const assessmentsDir = resolve(repoRoot, 'datasets/hadith-data/assessments');

  const hadithMap = new Map<string, StagedHadithAssessment>();
  let hadithRawTotal = 0;
  let hadithSkippedUncited = 0;
  let hadithSkippedInvalid = 0;

  if (options.includeHadith) {
    hadithRawTotal = await readJsonlGz(resolve(assessmentsDir, 'hadith_assessments.jsonl.gz'), (row) => {
      const parsed = parseHadithAssessmentRow(row);
      if (!parsed.ok) {
        if (parsed.reason === 'uncited') hadithSkippedUncited += 1;
        else hadithSkippedInvalid += 1;
        return;
      }
      const nk = `${parsed.value.hadithId}|${parsed.value.traditionId}|${parsed.value.sourceField}|${parsed.value.ordinal}`;
      hadithMap.set(nk, parsed.value);
    });
  }

  const narratorMap = new Map<string, StagedNarratorAssessment>();
  let narratorRawTotal = 0;
  let narratorSkippedUncited = 0;
  let narratorSkippedNoNarratorId = 0;
  let narratorSkippedInvalid = 0;

  if (options.includeNarrator) {
    narratorRawTotal = await readJsonlGz(resolve(assessmentsDir, 'narrator_assessments.jsonl.gz'), (row) => {
      const parsed = parseNarratorAssessmentRow(row);
      if (!parsed.ok) {
        if (parsed.reason === 'uncited') narratorSkippedUncited += 1;
        else if (parsed.reason === 'no_narrator_id') narratorSkippedNoNarratorId += 1;
        else narratorSkippedInvalid += 1;
        return;
      }
      narratorMap.set(parsed.value.id, parsed.value);
    });
  }

  return {
    hadithAssessments: Array.from(hadithMap.values()),
    hadithAssessmentsRawTotal: hadithRawTotal,
    hadithAssessmentsSkippedUncited: hadithSkippedUncited,
    hadithAssessmentsSkippedInvalid: hadithSkippedInvalid,
    narratorAssessments: Array.from(narratorMap.values()),
    narratorAssessmentsRawTotal: narratorRawTotal,
    narratorAssessmentsSkippedUncited: narratorSkippedUncited,
    narratorAssessmentsSkippedNoNarratorId: narratorSkippedNoNarratorId,
    narratorAssessmentsSkippedInvalid: narratorSkippedInvalid,
  };
}

function resolveConnectionForScript(
  argv: readonly string[],
  dryRun: boolean,
): { name: 'development' | 'production'; url: string } {
  if (!dryRun) {
    return resolveTargetDatabase(argv, { required: true });
  }
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
  const dryRun = argv.includes('--dry-run');
  const onlyIdx = argv.indexOf('--only');
  const only = onlyIdx >= 0 ? argv[onlyIdx + 1] : undefined;
  const includeHadith = !only || only === 'hadith';
  const includeNarrator = !only || only === 'narrator';
  if (!includeHadith && !includeNarrator) {
    throw new Error('--only must be "hadith" or "narrator".');
  }

  const target = resolveConnectionForScript(argv, dryRun);
  const repoRoot = process.cwd();
  console.log(`[load-assessments] Target: ${target.name} (${dryRun ? 'DRY RUN — no writes' : 'LIVE WRITE'})`);

  const plan = await buildLoadPlan(repoRoot, { includeHadith, includeNarrator });

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

    // 2. Validate FK targets: traditions, hadiths, narrators, citations
    const existingTraditionIds = new Set<string>();
    const traditionRows = await db.select({ id: traditions.id }).from(traditions);
    for (const r of traditionRows) existingTraditionIds.add(r.id);

    const existingHadithIds = new Set<string>();
    if (plan.hadithAssessments.length > 0) {
      const candidateHadithIds = Array.from(new Set(plan.hadithAssessments.map((h) => h.hadithId)));
      await runBatched(candidateHadithIds, BATCH_SIZE, async (batch) => {
        const rows = await db
          .select({ id: hadiths.id })
          .from(hadiths)
          .where(inArray(hadiths.id, [...batch]));
        for (const r of rows) existingHadithIds.add(r.id);
      });
    }

    const existingNarratorIds = new Set<string>();
    if (plan.narratorAssessments.length > 0) {
      const candidateNarratorIds = Array.from(new Set(plan.narratorAssessments.map((n) => n.narratorId)));
      await runBatched(candidateNarratorIds, BATCH_SIZE, async (batch) => {
        const rows = await db
          .select({ id: narrators.id })
          .from(narrators)
          .where(inArray(narrators.id, [...batch]));
        for (const r of rows) existingNarratorIds.add(r.id);
      });
    }

    const candidateCitationIds = Array.from(
      new Set([
        ...plan.hadithAssessments.map((h) => h.citationId).filter((id): id is string => id !== null),
        ...plan.narratorAssessments.map((n) => n.citationId).filter((id): id is string => id !== null),
      ]),
    );
    const existingCitationIds = new Set<string>();
    if (candidateCitationIds.length > 0) {
      await runBatched(candidateCitationIds, BATCH_SIZE, async (batch) => {
        const rows = await db
          .select({ id: citations.id })
          .from(citations)
          .where(inArray(citations.id, [...batch]));
        for (const r of rows) existingCitationIds.add(r.id);
      });
    }

    const validHadithAssessments = plan.hadithAssessments.filter(
      (h) =>
        existingHadithIds.has(h.hadithId) &&
        existingTraditionIds.has(h.traditionId) &&
        (h.citationId === null || existingCitationIds.has(h.citationId)),
    );
    const skippedHadithFk = plan.hadithAssessments.length - validHadithAssessments.length;

    const validNarratorAssessments = plan.narratorAssessments.filter(
      (n) =>
        existingNarratorIds.has(n.narratorId) &&
        existingTraditionIds.has(n.traditionId) &&
        (n.citationId === null || existingCitationIds.has(n.citationId)),
    );
    const skippedNarratorFk = plan.narratorAssessments.length - validNarratorAssessments.length;

    const hadithNewCount = validHadithAssessments.filter((h) => !h.alreadyLoaded).length;
    const hadithAlreadyLoadedCount = validHadithAssessments.filter((h) => h.alreadyLoaded).length;
    const narratorCanonicalCount = validNarratorAssessments.filter((n) => n.verdict !== 'not_applicable').length;
    const narratorCompanionCount = validNarratorAssessments.filter((n) => n.isCompanion === true).length;

    console.log(`[load-assessments] Current dataset_version_id: ${datasetVersionId}`);
    console.log(`[load-assessments] Staged counts:`);
    console.log(
      `  hadith_assessments   : ${validHadithAssessments.length} ready ` +
        `(new: ${hadithNewCount}, already_loaded_upsert: ${hadithAlreadyLoadedCount}; ` +
        `raw: ${plan.hadithAssessmentsRawTotal}, skipped uncited: ${plan.hadithAssessmentsSkippedUncited}, ` +
        `invalid: ${plan.hadithAssessmentsSkippedInvalid}, missing FK: ${skippedHadithFk})`,
    );
    console.log(
      `  narrator_assessments : ${validNarratorAssessments.length} ready ` +
        `(with canonical verdict: ${narratorCanonicalCount}, companion: ${narratorCompanionCount}; ` +
        `raw: ${plan.narratorAssessmentsRawTotal}, skipped uncited: ${plan.narratorAssessmentsSkippedUncited}, ` +
        `no narrator_id: ${plan.narratorAssessmentsSkippedNoNarratorId}, invalid: ${plan.narratorAssessmentsSkippedInvalid}, ` +
        `missing FK: ${skippedNarratorFk})`,
    );

    if (dryRun) {
      console.log(`[load-assessments] Dry-run complete. 0 rows written.`);
      return;
    }

    const now = new Date();

    // 3. Upsert hadith_assessments
    await runBatched(validHadithAssessments, BATCH_SIZE, async (batch) => {
      await db
        .insert(hadithAssessments)
        .values(
          batch.map((h) => ({
            id: h.id,
            hadithId: h.hadithId,
            traditionId: h.traditionId,
            gradeScheme: h.gradeScheme,
            ordinal: h.ordinal,
            kind: h.kind,
            grader: h.grader,
            gradeRaw: h.gradeRaw,
            gradeCanonical: h.gradeCanonical,
            gradeDetail: h.gradeDetail,
            citationRaw: h.citationRaw,
            citedWork: h.citedWork,
            citedVolume: h.citedVolume,
            citedPage: h.citedPage,
            citationId: h.citationId,
            sourceField: h.sourceField,
            reviewState: h.reviewState,
            firstSeenDatasetVersionId: datasetVersionId,
            changedInDatasetVersionId: datasetVersionId,
            updatedAt: now,
          })),
        )
        .onConflictDoUpdate({
          target: [
            hadithAssessments.hadithId,
            hadithAssessments.traditionId,
            hadithAssessments.sourceField,
            hadithAssessments.ordinal,
          ],
          set: {
            gradeScheme: sql`excluded.grade_scheme`,
            kind: sql`excluded.kind`,
            grader: sql`excluded.grader`,
            gradeRaw: sql`excluded.grade_raw`,
            gradeCanonical: sql`excluded.grade_canonical`,
            gradeDetail: sql`excluded.grade_detail`,
            citationRaw: sql`excluded.citation_raw`,
            citedWork: sql`excluded.cited_work`,
            citedVolume: sql`excluded.cited_volume`,
            citedPage: sql`excluded.cited_page`,
            citationId: sql`excluded.citation_id`,
            reviewState: sql`excluded.review_state`,
            changedInDatasetVersionId: sql`excluded.changed_in_dataset_version_id`,
            updatedAt: now,
          },
        });
    });

    // 4. Upsert narrator_assessments
    await runBatched(validNarratorAssessments, BATCH_SIZE, async (batch) => {
      await db
        .insert(narratorAssessments)
        .values(
          batch.map((n) => ({
            id: n.id,
            narratorId: n.narratorId,
            traditionId: n.traditionId,
            kind: n.kind,
            verdict: n.verdict,
            critic: n.critic,
            quoteAr: n.quoteAr,
            quoteEn: null,
            tadilText: null,
            jarhText: null,
            isCompanion: n.isCompanion,
            disagreement: false,
            criticQuoteCount: null,
            provenance: n.provenance,
            citationId: n.citationId,
            status: 'proposed' as const,
            createdBy: LOADER_ACTOR,
            updatedBy: LOADER_ACTOR,
            updatedAt: now,
          })),
        )
        .onConflictDoUpdate({
          target: narratorAssessments.id,
          set: {
            narratorId: sql`excluded.narrator_id`,
            traditionId: sql`excluded.tradition_id`,
            kind: sql`excluded.kind`,
            verdict: sql`excluded.verdict`,
            critic: sql`excluded.critic`,
            quoteAr: sql`excluded.quote_ar`,
            isCompanion: sql`excluded.is_companion`,
            provenance: sql`excluded.provenance`,
            citationId: sql`excluded.citation_id`,
            updatedBy: LOADER_ACTOR,
            updatedAt: now,
          },
        });
    });

    console.log(
      `[load-assessments] Live write complete: ${validHadithAssessments.length} hadith_assessments, ${validNarratorAssessments.length} narrator_assessments upserted.`,
    );
  } finally {
    await sqlClient.end({ timeout: 5 });
  }
}

const isEntrypoint =
  process.argv[1] &&
  (process.argv[1].endsWith('load-assessments.ts') || process.argv[1].endsWith('load-assessments.js'));

if (isEntrypoint) {
  executeLoad(process.argv.slice(2)).catch((err) => {
    console.error('[load-assessments] FAILED:', err);
    process.exit(1);
  });
}
