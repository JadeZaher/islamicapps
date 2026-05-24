/**
 * ingest-er-approved.ts — HITL ingestion of approved entity-resolution records
 * =============================================================================
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Phase 2 (FR-2.4, G-5)
 *
 * Reads datasets/hadith-data/er-staging.jsonl (produced by resolveNarrators),
 * filters to rows where `approved: true`, and writes :RESOLVES_TO edges from
 * :NameMention → :Narrator (RAWI) with provenance properties.
 *
 * INVARIANTS (GLOBAL — NON-NEGOTIABLE):
 *   1. Idempotent: re-running on the same staging file after success is a no-op.
 *   2. Never writes a :SAME_AS edge without reviewed_by (G-5).
 *   3. Never auto-approves: only rows with approved=true are processed.
 *   4. Parameterized Cypher only — no string interpolation of staging data.
 *   5. No deletes (tombstone instead) — this script adds edges, never removes.
 *
 * HITL workflow:
 *   1. Run `npm run db:regen -- --mode=fullregen` → populates er-staging.jsonl.
 *   2. Human reviews staging JSONL, sets `approved: true`, `approved_scholar_indx`,
 *      `reviewed_by`, `reviewed_at` on the rows they confirm.
 *   3. Run `npm run db:ingest-er` → commits only approved rows as :RESOLVES_TO.
 *   4. Zero :SAME_AS edges exist without reviewed_by (verified by G-5 test).
 *
 * Usage:
 *   npm run db:ingest-er
 *   npm run db:ingest-er -- --staging <path/to/er-staging.jsonl>
 *   npm run db:ingest-er -- --dry-run        # print what would be committed
 *   npm run db:ingest-er -- --tradition Imami  # filter by tradition
 */

import fs from 'fs';
import readline from 'readline';
import path from 'path';
import { loadEnv } from './lib/env';
import { runWrite, runQuery, closeDriver } from '../lib/db/neo4j';

loadEnv();

// ─── Types ────────────────────────────────────────────────────────────────────

/**
 * One record from er-staging.jsonl that has been human-approved.
 * Only rows with approved=true reach the write path.
 */
interface ApprovedStagingRecord {
  staged_at: number;
  surface_form: string;
  normalized_form: string;
  source_row_id: string;
  tradition: string;
  position: number;
  approved: true;
  approved_scholar_indx: number;
  reviewed_by: string;
  reviewed_at: string;
  quarantined?: boolean;
  candidates: Array<{
    scholar_indx: number;
    name: string;
    score: number;
    features: Record<string, unknown>;
  }>;
}

// ─── CLI ──────────────────────────────────────────────────────────────────────

interface CliArgs {
  staging: string;
  dryRun: boolean;
  tradition: string;
}

function parseArgs(): CliArgs {
  const argv = process.argv.slice(2);
  const args: CliArgs = {
    staging: path.join(process.cwd(), 'datasets', 'hadith-data', 'er-staging.jsonl'),
    dryRun: false,
    tradition: '',
  };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if ((a === '--staging' || a === '--input') && argv[i + 1]) args.staging = argv[++i];
    else if (a === '--dry-run') args.dryRun = true;
    else if (a === '--tradition' && argv[i + 1]) args.tradition = argv[++i];
  }
  return args;
}

// ─── Staging reader ───────────────────────────────────────────────────────────

/**
 * Stream approved records from the staging JSONL file.
 * Lines starting with '#' are the header comment block — skipped.
 * Lines without `approved: true` are silently skipped.
 */
async function* readApproved(
  stagingPath: string,
  traditionFilter: string,
): AsyncGenerator<ApprovedStagingRecord> {
  if (!fs.existsSync(stagingPath)) {
    console.error(`Staging file not found: ${stagingPath}`);
    return;
  }
  const rl = readline.createInterface({
    input: fs.createReadStream(stagingPath, { encoding: 'utf8' }),
    crlfDelay: Infinity,
  });
  for await (const line of rl) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue; // header comment
    let record: Record<string, unknown>;
    try {
      record = JSON.parse(trimmed);
    } catch {
      continue; // malformed line — skip
    }
    if (record['approved'] !== true) continue;
    if (!record['approved_scholar_indx']) continue;
    if (!record['reviewed_by'] || !record['reviewed_at']) {
      console.warn(
        `  SKIP (missing reviewed_by/reviewed_at): source_row_id=${record['source_row_id']}`,
      );
      continue;
    }
    if (traditionFilter && record['tradition'] !== traditionFilter) continue;
    yield record as unknown as ApprovedStagingRecord;
  }
}

// ─── Idempotency check ────────────────────────────────────────────────────────

/**
 * Returns true if a :RESOLVES_TO edge already exists between this NameMention
 * (identified by surface_form + source_row_id) and the target scholar_indx.
 *
 * The NameMention is keyed on normalized_form + source_row_id; the Narrator
 * is keyed on scholar_indx. This is the idempotency anchor.
 */
async function edgeExists(
  normalizedForm: string,
  sourceRowId: string,
  scholarIndx: number,
): Promise<boolean> {
  const rows = await runQuery<{ found: boolean }>(
    `MATCH (m:NameMention {normalized_form: $nf})
       WHERE m.source_row_id = $rid
     MATCH (n:Narrator {scholar_indx: $si})
     RETURN EXISTS((m)-[:RESOLVES_TO]->(n)) AS found`,
    { nf: normalizedForm, rid: sourceRowId, si: scholarIndx },
  );
  return rows.length > 0 && rows[0].found === true;
}

// ─── Write :RESOLVES_TO ───────────────────────────────────────────────────────

/**
 * Idempotently MERGE a :RESOLVES_TO edge from a :NameMention to a :Narrator.
 *
 * Properties required by spec FR-1.4:
 *   confidence        — top-candidate score from staging (≤ 1.0)
 *   extraction_method — always 'rerank' for HITL-approved records
 *   reviewed_by       — human reviewer identifier
 *   reviewed_at       — ISO 8601 timestamp of human review
 *   quarantined       — true for unmeasured strata (NFR-3)
 *
 * INVARIANT: No auto-write. This function is ONLY called for approved=true rows.
 */
async function writeResolvesTo(record: ApprovedStagingRecord): Promise<void> {
  const topScore =
    record.candidates.length > 0 ? record.candidates[0].score : 0.5;

  await runWrite(
    `MATCH (m:NameMention {normalized_form: $nf})
       WHERE m.source_row_id = $rid
     MATCH (n:Narrator {scholar_indx: $si})
     MERGE (m)-[r:RESOLVES_TO]->(n)
     ON CREATE SET
       r.confidence         = $conf,
       r.extraction_method  = 'rerank',
       r.reviewed_by        = $reviewedBy,
       r.reviewed_at        = $reviewedAt,
       r.quarantined        = $quarantined,
       r.created_at         = datetime()`,
    {
      nf: record.normalized_form,
      rid: record.source_row_id,
      si: record.approved_scholar_indx,
      conf: topScore,
      reviewedBy: record.reviewed_by,
      reviewedAt: record.reviewed_at,
      quarantined: record.quarantined ?? false,
    },
  );
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const args = parseArgs();

  console.log('ingest-er-approved.ts — HITL entity resolution ingest');
  console.log('Staging file:', args.staging);
  if (args.dryRun) console.log('DRY RUN — no writes will be made');
  if (args.tradition) console.log('Tradition filter:', args.tradition);
  console.log('');

  let total = 0;
  let committed = 0;
  let skipped = 0;
  let errors = 0;

  for await (const record of readApproved(args.staging, args.tradition)) {
    total++;
    try {
      // Idempotency: skip if the edge already exists
      const exists = await edgeExists(
        record.normalized_form,
        record.source_row_id,
        record.approved_scholar_indx,
      );
      if (exists) {
        skipped++;
        continue;
      }

      if (args.dryRun) {
        console.log(
          `  [DRY RUN] RESOLVES_TO: "${record.surface_form}" → scholar_indx=${record.approved_scholar_indx}` +
            ` (reviewed_by=${record.reviewed_by}, tradition=${record.tradition})`,
        );
        committed++;
        continue;
      }

      await writeResolvesTo(record);
      committed++;

      if (committed % 50 === 0) {
        console.log(`  committed ${committed} / ${total} processed so far...`);
      }
    } catch (err) {
      errors++;
      console.error(
        `  ERROR on source_row_id=${record.source_row_id}: ${(err as Error).message}`,
      );
    }
  }

  console.log('');
  console.log('=== Summary ===');
  console.log(`  Total approved rows processed : ${total}`);
  console.log(`  Edges committed               : ${committed}`);
  console.log(`  Skipped (already existed)     : ${skipped}`);
  console.log(`  Errors                        : ${errors}`);
  if (args.dryRun) console.log('  (dry run — no writes were made)');

  if (errors > 0) {
    console.error(`\n${errors} error(s) encountered. Check logs above.`);
    process.exitCode = 1;
  }

  await closeDriver();
}

main().catch((err) => {
  console.error('Fatal:', err);
  process.exit(1);
});
