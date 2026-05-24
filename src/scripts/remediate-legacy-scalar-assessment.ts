/**
 * remediate-legacy-scalar-assessment.ts — Gate-G0 Blocker 1 no-delete fix
 * ========================================================================
 *
 * Track: neo4j_isnad_graph_regen_20260516 — Phase 0 Gate G-0, Blocker 1.
 *
 * THE BLOCKER
 *   Spec §5 G-1 (exact, unscoped):
 *     MATCH (n) WHERE (n:Narrator OR n:Hadith)
 *       AND (n.reliability IS NOT NULL OR n.grade IS NOT NULL)
 *     RETURN count(n)
 *   currently returns 24,347. Gate G-0 requires 0. The violating nodes are
 *   :Narrator/:Hadith carrying scalar `reliability`/`grade` written by the
 *   DEPRECATED `import-datasets.ts` (mapGradeToTabaqah path) BEFORE this
 *   track. The new `regen-isnad-graph.ts` writes NONE of those scalars (BUG
 *   2 / G-1 fix). Closing the gate therefore requires a one-time no-delete
 *   property strip of the legacy data — exactly what this script does.
 *
 * HARD RULES
 *   - NO `DETACH DELETE` / no node or edge `DELETE` anywhere (NFR-2 / standing
 *     `feedback_no_delete_backup.md`). A property `REMOVE` is NOT a node/edge
 *     delete — that distinction was adjudicated by the reviewer.
 *   - Belt-and-suspenders BACKUP FIRST: dump every targeted node's
 *     {labels, scholar_indx, id, reliability, grade} to a JSON file. If the
 *     default backup path already exists, write a timestamped sibling rather
 *     than blindly overwrite.
 *   - Idempotent: re-running after the first pass is a no-op (the targeted
 *     property predicate finds 0 nodes). Cypher is parameterized.
 *   - `tabaqah` is a genealogical generation bucket (Companion/Successor/…),
 *     NOT an assessment scalar, so it MUST NOT be stripped.
 *
 * VERIFY IN-SCRIPT
 *   - Re-run the exact spec §5 G-1 Cypher → assert returns 0.
 *   - Print before/after :Narrator and :Hadith node counts AND their
 *     in/out edge counts: only the two properties should differ; node and
 *     edge cardinalities must be byte-stable.
 *
 * Run:
 *   npm run db:remediate-legacy-assessment            # writes
 *   npm run db:remediate-legacy-assessment -- --dry   # parse + report only
 */

import fs from 'fs';
import path from 'path';
import { loadEnv } from './lib/env';
import { runQuery, runWrite, closeDriver } from '../lib/db/neo4j';

loadEnv();

// ─── CLI ─────────────────────────────────────────────────────────────────────

interface CliArgs {
  /** Skip the strip; only run the backup + the before/after diagnostic queries. */
  dry: boolean;
  /** Override the default batch size (default: 5,000 — well below Cypher limits). */
  batchSize: number;
}

function parseArgs(): CliArgs {
  const argv = process.argv.slice(2);
  const args: CliArgs = { dry: false, batchSize: 5000 };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--dry' || a === '--dry-run') args.dry = true;
    else if (a === '--batch-size' && argv[i + 1]) args.batchSize = parseInt(argv[++i], 10) || 5000;
  }
  return args;
}

// ─── Diagnostic queries (exact spec §5 G-1 shape preserved) ──────────────────

/** The EXACT spec §5 G-1 Cypher. Do not edit the shape — it is the gate query. */
async function g1ViolationCount(): Promise<number> {
  const r = await runQuery<{ c: number }>(`
    MATCH (n)
    WHERE (n:Narrator OR n:Hadith)
      AND (n.reliability IS NOT NULL OR n.grade IS NOT NULL)
    RETURN count(n) AS c
  `);
  return r[0].c;
}

interface LabelCounts {
  narrators: number;
  hadiths: number;
}

interface EdgeCounts {
  narratorRels: number;
  hadithRels: number;
}

async function labelCounts(): Promise<LabelCounts> {
  const r = await runQuery<LabelCounts>(`
    MATCH (n:Narrator) WITH count(n) AS narrators
    MATCH (h:Hadith) RETURN narrators, count(h) AS hadiths
  `);
  return r[0];
}

/**
 * Total edges touching a :Narrator or :Hadith node (start OR end). This is
 * the right "edges otherwise unchanged" cardinality — Cypher counts each
 * relationship once even if both endpoints qualify.
 */
async function edgeCounts(): Promise<EdgeCounts> {
  const narrRels = await runQuery<{ c: number }>(`
    MATCH (n:Narrator)-[r]-() RETURN count(DISTINCT r) AS c
  `);
  const hadRels = await runQuery<{ c: number }>(`
    MATCH (h:Hadith)-[r]-() RETURN count(DISTINCT r) AS c
  `);
  return { narratorRels: narrRels[0].c, hadithRels: hadRels[0].c };
}

// ─── Backup (belt-and-suspenders; reimport-reversible already) ───────────────

interface BackupRow {
  labels: string[];
  scholar_indx: number | null;
  id: string | null;
  reliability: string | number | null;
  grade: string | number | null;
}

async function fetchBackupRows(): Promise<BackupRow[]> {
  return runQuery<BackupRow>(`
    MATCH (n)
    WHERE (n:Narrator OR n:Hadith)
      AND (n.reliability IS NOT NULL OR n.grade IS NOT NULL)
    RETURN labels(n) AS labels,
           n.scholar_indx AS scholar_indx,
           n.id AS id,
           n.reliability AS reliability,
           n.grade AS grade
  `);
}

function chooseBackupPath(): string {
  const dir = path.join(process.cwd(), '.omc', 'research', 'neo4j-hadith-graph');
  fs.mkdirSync(dir, { recursive: true });
  const primary = path.join(dir, 'phase0-legacy-reliability-backup.json');
  if (!fs.existsSync(primary)) return primary;
  // Do NOT overwrite an existing backup blindly — write a timestamped sibling.
  const ts = new Date().toISOString().replace(/[:.]/g, '-');
  return path.join(dir, `phase0-legacy-reliability-backup.${ts}.json`);
}

// ─── No-delete property strip (REMOVE only — NFR-2 compliant) ────────────────
//
// `REMOVE n.reliability, n.grade` is a property removal — NOT a node or edge
// delete. The reviewer adjudicated this distinction explicitly. The node, all
// its other properties (including `tabaqah`), and every incident relationship
// are preserved byte-stably.
//
// Batched via `apoc.periodic.iterate`-style hand-rolled loop: the predicate
// itself bounds the work, so each iteration shrinks the candidate set. Cypher
// driver retries (executeWrite) keep this transient-fault tolerant.

async function stripOneBatch(batchSize: number): Promise<number> {
  // `LIMIT` requires an INTEGER. The neo4j JS driver serializes a plain JS
  // number as a float, so we coerce to integer in Cypher via toInteger().
  const r = await runWrite<{ stripped: number }>(
    `
    MATCH (n)
    WHERE (n:Narrator OR n:Hadith)
      AND (n.reliability IS NOT NULL OR n.grade IS NOT NULL)
    WITH n LIMIT toInteger($batchSize)
    REMOVE n.reliability, n.grade
    RETURN count(n) AS stripped
  `,
    { batchSize }
  );
  return r[0].stripped;
}

async function stripAll(batchSize: number): Promise<{ totalStripped: number; batches: number }> {
  let totalStripped = 0;
  let batches = 0;
  // Bounded loop: if the predicate ever stops shrinking, abort loudly so we
  // never spin on an unintended fixed-point.
  for (let i = 0; i < 200; i++) {
    const stripped = await stripOneBatch(batchSize);
    if (stripped === 0) break;
    totalStripped += stripped;
    batches++;
    console.log(`  · batch ${batches}: stripped ${stripped} (running total ${totalStripped})`);
  }
  const remaining = await g1ViolationCount();
  if (remaining > 0) {
    throw new Error(
      `Unexpected: ${remaining} G-1 violations remain after stripping loop. ` +
        `This should be impossible if the predicate matches what REMOVE targeted; ` +
        `investigate before re-running.`
    );
  }
  return { totalStripped, batches };
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log('='.repeat(72));
  console.log('  remediate-legacy-scalar-assessment (Blocker 1, no-delete REMOVE)');
  console.log('='.repeat(72));
  const args = parseArgs();
  if (args.dry) console.log('⚙️  --dry: backup + diagnostics only; NO writes.');
  console.log(`⚙️  batch size: ${args.batchSize}`);

  // 1. BEFORE: diagnostic baseline.
  console.log('\n📊 Baseline (before strip):');
  const beforeG1 = await g1ViolationCount();
  const beforeLabels = await labelCounts();
  const beforeEdges = await edgeCounts();
  console.log(`   §5 G-1 violation count: ${beforeG1}`);
  console.log(`   :Narrator nodes: ${beforeLabels.narrators}`);
  console.log(`   :Hadith nodes:   ${beforeLabels.hadiths}`);
  console.log(`   Narrator edges:  ${beforeEdges.narratorRels}`);
  console.log(`   Hadith edges:    ${beforeEdges.hadithRels}`);

  if (beforeG1 === 0) {
    console.log('\n✅ Already clean (G-1 count = 0). Nothing to do; idempotent no-op.');
    await closeDriver();
    return;
  }

  // 2. BACKUP (belt-and-suspenders; reimport-reversible already).
  console.log('\n💾 Backing up legacy reliability/grade values...');
  const backupRows = await fetchBackupRows();
  if (backupRows.length !== beforeG1) {
    throw new Error(
      `Backup count (${backupRows.length}) != G-1 count (${beforeG1}); ` +
        'predicate skew — refusing to strip.'
    );
  }
  const backupPath = chooseBackupPath();
  const backupBlob = {
    generated_at: new Date().toISOString(),
    track: 'neo4j_isnad_graph_regen_20260516',
    blocker: 'Phase 0 / Gate G0 — Blocker 1: legacy scalar-assessment strip',
    spec_query: 'MATCH (n) WHERE (n:Narrator OR n:Hadith) AND (n.reliability IS NOT NULL OR n.grade IS NOT NULL) RETURN count(n)',
    expected_count: beforeG1,
    rows: backupRows,
    notes:
      'Belt-and-suspenders backup. The values are a pure function of ' +
      'all_rawis.csv `grade` via mapGradeToTabaqah() in the DEPRECATED ' +
      'import-datasets.ts, so the strip is reimport-reversible regardless. ' +
      'This file is the receipt the reviewer asked for.',
  };
  fs.writeFileSync(backupPath, JSON.stringify(backupBlob, null, 2), 'utf8');
  console.log(`   📄 backup written: ${backupPath}`);
  console.log(`   rows backed up: ${backupRows.length}`);

  if (args.dry) {
    console.log('\n⏹️  --dry set: skipping strip. Done.');
    await closeDriver();
    return;
  }

  // 3. STRIP (no-delete; REMOVE properties only).
  console.log(`\n🧹 Stripping n.reliability + n.grade in batches of ${args.batchSize}...`);
  const { totalStripped, batches } = await stripAll(args.batchSize);
  console.log(`   ✅ Total nodes touched: ${totalStripped} (in ${batches} batches)`);

  // 4. AFTER: re-run the exact §5 G-1 Cypher (the gate query) and the baseline
  //    diagnostics; assert nothing else changed.
  console.log('\n📊 After strip:');
  const afterG1 = await g1ViolationCount();
  const afterLabels = await labelCounts();
  const afterEdges = await edgeCounts();
  console.log(`   §5 G-1 violation count: ${afterG1}   (was ${beforeG1})`);
  console.log(`   :Narrator nodes: ${afterLabels.narrators}   (was ${beforeLabels.narrators})`);
  console.log(`   :Hadith nodes:   ${afterLabels.hadiths}   (was ${beforeLabels.hadiths})`);
  console.log(`   Narrator edges:  ${afterEdges.narratorRels}   (was ${beforeEdges.narratorRels})`);
  console.log(`   Hadith edges:    ${afterEdges.hadithRels}   (was ${beforeEdges.hadithRels})`);

  // 5. Hard assertions — fail noisily if anything other than the two properties changed.
  if (afterG1 !== 0) throw new Error(`Gate not closed: G-1 count = ${afterG1} (expected 0)`);
  if (afterLabels.narrators !== beforeLabels.narrators)
    throw new Error(
      `Narrator node count changed: ${beforeLabels.narrators} → ${afterLabels.narrators} ` +
        '(no-delete violated; aborting before further damage)'
    );
  if (afterLabels.hadiths !== beforeLabels.hadiths)
    throw new Error(
      `Hadith node count changed: ${beforeLabels.hadiths} → ${afterLabels.hadiths} ` +
        '(no-delete violated; aborting before further damage)'
    );
  if (afterEdges.narratorRels !== beforeEdges.narratorRels)
    throw new Error(
      `Narrator edge count changed: ${beforeEdges.narratorRels} → ${afterEdges.narratorRels}`
    );
  if (afterEdges.hadithRels !== beforeEdges.hadithRels)
    throw new Error(
      `Hadith edge count changed: ${beforeEdges.hadithRels} → ${afterEdges.hadithRels}`
    );

  console.log('\n✅ Gate G-0 Blocker 1 closed:');
  console.log(`   §5 G-1 count: ${beforeG1} → 0`);
  console.log('   Node + edge cardinalities unchanged (only n.reliability, n.grade removed).');
  console.log(`   Backup: ${backupPath}`);

  await closeDriver();
}

main().catch((err) => {
  console.error('\n❌ remediation failed:', err);
  process.exitCode = 1;
  void closeDriver();
});
