/**
 * Idempotent loader for staged `candidate_only` machine English translations in
 * `datasets/hadith-data/machine_translation_candidates/machine_english_overlay.jsonl.gz`
 * into Postgres `translations`.
 *
 * Safety invariants (see drizzle/core/0018_machine_english_gate.sql and src/db/load/verify-data.ts):
 *   - Every inserted row has `state = 'machine_unreviewed'`, `review_state_raw = 'machine_unreviewed'`,
 *     `quality_status = 'complete'`, non-empty `source`, `model`, `provenance_source`, and
 *     `arabic_sha256 = hadiths.arabic_sha256`.
 *   - Existing `source_provided` / `source_verified` / `human_verified` rows are NEVER overwritten
 *     (guarded both by pre-filtering and `ON CONFLICT (hadith_id, language) DO NOTHING`).
 *   - Public visibility remains gated by `public_translations` (`collection_rights.english_policy =
 *     'source_provided_and_machine_allowed'`).
 *
 * Usage:
 *   npx tsx --conditions=react-server src/scripts/db/load-translations.ts --dry-run --database development
 *   npx tsx --conditions=react-server src/scripts/db/load-translations.ts --dry-run --database production
 *   npx tsx --conditions=react-server src/scripts/db/load-translations.ts --database development
 *   npx tsx --conditions=react-server src/scripts/db/load-translations.ts --database production --confirm-production
 */
import { createReadStream } from 'node:fs';
import { resolve } from 'node:path';
import { createInterface } from 'node:readline';
import { createGunzip } from 'node:zlib';
import { config as loadEnvironment } from 'dotenv';
import { and, eq, inArray } from 'drizzle-orm';
import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import { connectionOptions } from '../../db/connection-options';
import * as schema from '../../db/schema';
import { hadiths, translations } from '../../db/schema/corpus';
import { datasetVersions } from '../../db/schema/operations';
import { resolveTargetDatabase } from '../../db/target-database';

export const LOADER_ACTOR = 'system:load-translations';
export const BATCH_SIZE = 500;
export const DEFAULT_OVERLAY_REL_PATH =
  'datasets/hadith-data/machine_translation_candidates/machine_english_overlay.jsonl.gz';

export interface StagedMachineTranslation {
  id: string;
  hadithId: string;
  recordId: string;
  language: 'en';
  text: string;
  state: 'machine_unreviewed';
  qualityStatus: 'complete';
  reviewStateRaw: 'machine_unreviewed';
  source: string;
  model: string;
  provenanceSource: string;
  sourceRecordId: string | null;
  arabicSha256: string;
}

export interface TranslationsLoadPlan {
  rows: StagedMachineTranslation[];
  rawTotal: number;
  skippedQaRejected: number;
  skippedInvalid: number;
  duplicateRecordIds: number;
}

export function normalizeNonEmpty(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

export function deriveSourceRecordId(recordId: string): string | null {
  const idx = recordId.indexOf(':');
  if (idx < 0 || idx === recordId.length - 1) return null;
  return recordId.slice(idx + 1);
}

export function buildProvenanceSource(row: Record<string, unknown>): string | null {
  const originJournal = normalizeNonEmpty(row.origin_journal);
  if (!originJournal) return null;
  const promptVersion = normalizeNonEmpty(row.prompt_version) ?? 'unrecorded';
  const promptSha = normalizeNonEmpty(row.prompt_sha256);
  const promptShaShort = promptSha ? promptSha.slice(0, 12) : 'unrecorded';
  const provider = normalizeNonEmpty(row.response_provider) ?? 'unrecorded';
  const createdAt = normalizeNonEmpty(row.created_at) ?? 'unrecorded';
  return `machine_translation_candidates/${originJournal}|prompt=${promptVersion}|prompt_sha256=${promptShaShort}|provider=${provider}|at=${createdAt}`;
}

export function parseTranslationRow(
  row: Record<string, unknown>,
): { ok: true; value: StagedMachineTranslation } | { ok: false; reason: 'qa_rejected' | 'invalid' } {
  const qa = row.qa && typeof row.qa === 'object' ? (row.qa as Record<string, unknown>) : null;
  if (!qa || qa.status !== 'accepted_machine_unreviewed') {
    return { ok: false, reason: 'qa_rejected' };
  }

  const recordId = normalizeNonEmpty(row.record_id);
  const text = normalizeNonEmpty(row.text_en);
  const arabicSha256 = normalizeNonEmpty(row.arabic_sha256);
  const source = normalizeNonEmpty(row.translation_source);
  const model = normalizeNonEmpty(row.translation_model) ?? normalizeNonEmpty(row.response_model);
  const provenanceSource = buildProvenanceSource(row);

  if (!recordId || !text || !arabicSha256 || !source || !model || !provenanceSource) {
    return { ok: false, reason: 'invalid' };
  }

  return {
    ok: true,
    value: {
      id: `translation:${recordId}:en`,
      hadithId: `hadith:${recordId}`,
      recordId,
      language: 'en',
      text,
      state: 'machine_unreviewed',
      qualityStatus: 'complete',
      reviewStateRaw: 'machine_unreviewed',
      source,
      model,
      provenanceSource,
      sourceRecordId: deriveSourceRecordId(recordId),
      arabicSha256,
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

export async function buildLoadPlan(filePath: string): Promise<TranslationsLoadPlan> {
  const byHadithId = new Map<string, StagedMachineTranslation>();
  let skippedQaRejected = 0;
  let skippedInvalid = 0;
  let duplicateRecordIds = 0;

  const rawTotal = await readJsonlGz(filePath, (row) => {
    const parsed = parseTranslationRow(row);
    if (!parsed.ok) {
      if (parsed.reason === 'qa_rejected') skippedQaRejected += 1;
      else skippedInvalid += 1;
      return;
    }
    if (byHadithId.has(parsed.value.hadithId)) {
      duplicateRecordIds += 1;
    }
    byHadithId.set(parsed.value.hadithId, parsed.value);
  });

  return {
    rows: Array.from(byHadithId.values()),
    rawTotal,
    skippedQaRejected,
    skippedInvalid,
    duplicateRecordIds,
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
  const inputIdx = argv.indexOf('--input');
  const inputPath =
    inputIdx >= 0 && argv[inputIdx + 1]
      ? resolve(process.cwd(), argv[inputIdx + 1])
      : resolve(process.cwd(), DEFAULT_OVERLAY_REL_PATH);

  const target = resolveConnectionForScript(argv, dryRun);
  console.log(`[load-translations] Target: ${target.name} (${dryRun ? 'DRY RUN — no writes' : 'LIVE WRITE'})`);
  console.log(`[load-translations] Input: ${inputPath}`);

  const plan = await buildLoadPlan(inputPath);

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

    // 2. Fetch target hadiths (for FK validation, arabic_sha256 binding, and source_record_id)
    const hadithInfo = new Map<string, { arabicSha256: string; sourceRecordId: string | null }>();
    const candidateHadithIds = plan.rows.map((r) => r.hadithId);
    await runBatched(candidateHadithIds, BATCH_SIZE, async (batch) => {
      const rows = await db
        .select({
          id: hadiths.id,
          arabicSha256: hadiths.arabicSha256,
          sourceRecordId: hadiths.sourceRecordId,
        })
        .from(hadiths)
        .where(inArray(hadiths.id, [...batch]));
      for (const r of rows) {
        hadithInfo.set(r.id, { arabicSha256: r.arabicSha256, sourceRecordId: r.sourceRecordId });
      }
    });

    // 3. Fetch existing English translations for these hadiths
    const existingByHadithId = new Map<string, { id: string; state: string; retiredAt: Date | null }>();
    await runBatched(candidateHadithIds, BATCH_SIZE, async (batch) => {
      const rows = await db
        .select({
          id: translations.id,
          hadithId: translations.hadithId,
          state: translations.state,
          retiredAt: translations.retiredAt,
        })
        .from(translations)
        .where(and(inArray(translations.hadithId, [...batch]), eq(translations.language, 'en')));
      for (const r of rows) {
        existingByHadithId.set(r.hadithId, { id: r.id, state: r.state, retiredAt: r.retiredAt });
      }
    });

    // 4. Classify every staged row
    const toInsert: StagedMachineTranslation[] = [];
    let skippedMissingHadith = 0;
    let skippedHashMismatch = 0;
    let alreadyMachineUnreviewed = 0;
    let protectedExisting = 0;
    let existingOther = 0;

    for (const row of plan.rows) {
      const h = hadithInfo.get(row.hadithId);
      if (!h) {
        skippedMissingHadith += 1;
        continue;
      }
      if (h.arabicSha256 !== row.arabicSha256) {
        skippedHashMismatch += 1;
        continue;
      }
      const existing = existingByHadithId.get(row.hadithId);
      if (existing) {
        if (existing.retiredAt === null && existing.state === 'machine_unreviewed') {
          alreadyMachineUnreviewed += 1;
        } else if (
          existing.retiredAt === null &&
          (existing.state === 'source_provided' ||
            existing.state === 'source_verified' ||
            existing.state === 'human_verified')
        ) {
          protectedExisting += 1;
        } else {
          existingOther += 1;
        }
        continue;
      }
      toInsert.push({
        ...row,
        sourceRecordId: h.sourceRecordId ?? row.sourceRecordId,
      });
    }

    console.log(`[load-translations] Current dataset_version_id: ${datasetVersionId}`);
    console.log(`[load-translations] Staged summary:`);
    console.log(`  raw_rows_in_file          : ${plan.rawTotal}`);
    console.log(`  parsed_valid_unique       : ${plan.rows.length}`);
    console.log(`  skipped_qa_rejected       : ${plan.skippedQaRejected}`);
    console.log(`  skipped_invalid           : ${plan.skippedInvalid}`);
    console.log(`  duplicate_record_ids      : ${plan.duplicateRecordIds}`);
    console.log(`  skipped_missing_hadith    : ${skippedMissingHadith}`);
    console.log(`  skipped_hash_mismatch     : ${skippedHashMismatch}`);
    console.log(`  already_machine_unreviewed: ${alreadyMachineUnreviewed}`);
    console.log(`  protected_existing_en     : ${protectedExisting}`);
    console.log(`  existing_other_en         : ${existingOther}`);
    console.log(`  new_machine_rows_to_insert: ${toInsert.length}`);

    if (dryRun) {
      console.log(`[load-translations] Dry-run complete. 0 rows written.`);
      return;
    }

    if (toInsert.length === 0) {
      console.log(`[load-translations] Nothing new to insert. 0 rows written.`);
      return;
    }

    const now = new Date();
    await runBatched(toInsert, BATCH_SIZE, async (batch) => {
      await db
        .insert(translations)
        .values(
          batch.map((r) => ({
            id: r.id,
            hadithId: r.hadithId,
            language: r.language,
            text: r.text,
            matnText: null,
            state: r.state,
            qualityStatus: r.qualityStatus,
            reviewStateRaw: r.reviewStateRaw,
            source: r.source,
            model: r.model,
            translator: null,
            provenanceSource: r.provenanceSource,
            sourceRecordId: r.sourceRecordId,
            arabicSha256: r.arabicSha256,
            firstSeenDatasetVersionId: datasetVersionId,
            changedInDatasetVersionId: datasetVersionId,
            updatedAt: now,
          })),
        )
        .onConflictDoNothing({
          target: [translations.hadithId, translations.language],
        });
    });

    console.log(`[load-translations] Live write complete: ${toInsert.length} machine_unreviewed rows inserted.`);
  } finally {
    await sqlClient.end({ timeout: 5 });
  }
}

const isEntrypoint =
  process.argv[1] &&
  (process.argv[1].endsWith('load-translations.ts') || process.argv[1].endsWith('load-translations.js'));

if (isEntrypoint) {
  executeLoad(process.argv.slice(2)).catch((err) => {
    console.error('[load-translations] FAILED:', err);
    process.exit(1);
  });
}
