/**
 * regen-isnad-graph.ts — Thin CLI dispatcher for isnad graph regeneration.
 *
 * Track: neo4j_isnad_graph_regen_20260516
 * Supersedes `src/scripts/import-datasets.ts` (DEPRECATED, kept per D-1).
 *
 * Run:
 *   npm run db:regen -- --mode=test|fullregen|diff|enrich
 *   npm run db:regen -- --mode=enrich --field=<name> --source=<path>
 *   npm run db:regen -- --list
 */

import { loadEnv } from './lib/env';
import { closeDriver } from '../lib/db/neo4j';

loadEnv();

// ─── Types ────────────────────────────────────────────────────────────────────

export interface CliArgs {
  mode: 'test' | 'fullregen' | 'diff' | 'enrich' | null;
  field: string;
  source: string;
  stagingPath: string;
  allowKnownGaps: boolean;
  batchSize: number;
  concurrency: number;
  list: boolean;
}

// ─── Mode descriptions ────────────────────────────────────────────────────────

const MODE_DESCRIPTIONS: Record<string, string> = {
  test:      'Read-only: run all spec §9b + G-1..G-6 guardrail checks; emit JSON summary.',
  fullregen: 'Full idempotent regen: migrate legacy scalars, stream unified CSV, build all nodes/edges/assessments, flag temporal plausibility.',
  diff:      'Incremental: compare CSV to DB on biz key; MERGE only new/changed rows; emit added/updated/unchanged/tombstoned summary.',
  enrich:    'Field enrichment: apply a JSONL source to fill one empty field on :Hadith; never overwrites populated values.',
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

/** Extract value from --flag=val or --flag val form. Returns undefined if not found. */
function getArg(argv: string[], flag: string, idx: number): string | undefined {
  const a = argv[idx];
  if (a === flag && argv[idx + 1]) return argv[idx + 1];
  if (a.startsWith(flag + '=')) return a.slice(flag.length + 1);
  return undefined;
}

function parseArgs(): CliArgs {
  const argv = process.argv.slice(2);
  const args: CliArgs = {
    mode: null, field: '', source: '', stagingPath: '',
    allowKnownGaps: false,
    batchSize: parseInt(process.env['BATCH_SIZE'] ?? '500', 10) || 500,
    concurrency: parseInt(process.env['CONCURRENCY'] ?? '4', 10) || 4,
    list: false,
  };

  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--list') { args.list = true; continue; }
    if (a === '--allow-known-gaps') { args.allowKnownGaps = true; continue; }

    const mode = getArg(argv, '--mode', i);
    if (mode !== undefined) {
      if (['test','fullregen','diff','enrich'].includes(mode)) args.mode = mode as CliArgs['mode'];
      else { console.error(`Unknown --mode: "${mode}"`); process.exitCode = 1; }
      if (!a.includes('=')) i++;
      continue;
    }
    const field = getArg(argv, '--field', i);
    if (field !== undefined) { args.field = field; if (!a.includes('=')) i++; continue; }
    const source = getArg(argv, '--source', i);
    if (source !== undefined) { args.source = source; if (!a.includes('=')) i++; continue; }
    const staging = getArg(argv, '--staging-path', i);
    if (staging !== undefined) { args.stagingPath = staging; if (!a.includes('=')) i++; continue; }
    const batch = getArg(argv, '--batch-size', i);
    if (batch !== undefined) { args.batchSize = parseInt(batch, 10) || args.batchSize; if (!a.includes('=')) i++; continue; }
    const conc = getArg(argv, '--concurrency', i);
    if (conc !== undefined) { args.concurrency = parseInt(conc, 10) || args.concurrency; if (!a.includes('=')) i++; continue; }
  }
  return args;
}

function validate(args: CliArgs): boolean {
  if (args.list) return true;
  if (!args.mode) {
    console.error('Error: --mode is required. Use: test | fullregen | diff | enrich (or --list)');
    return false;
  }
  if (args.mode === 'enrich') {
    if (!args.field) { console.error('Error: --field required for --mode=enrich'); return false; }
    if (!args.source) { console.error('Error: --source required for --mode=enrich'); return false; }
  }
  return true;
}

function printList(): void {
  console.log('Available modes (npm run db:regen -- --mode=<mode>):\n');
  for (const [mode, desc] of Object.entries(MODE_DESCRIPTIONS)) {
    console.log(`  ${mode.padEnd(12)} ${desc}`);
  }
  console.log('\nFlags:');
  console.log('  --mode=<mode>        Required. One of: test, fullregen, diff, enrich');
  console.log('  --field=<name>       Required for enrich. Field name to populate.');
  console.log('  --source=<path>      Required for enrich. Path to JSONL source.');
  console.log('  --staging-path=<p>   Path to er-staging.jsonl (default: datasets/hadith-data/er-staging.jsonl)');
  console.log('  --allow-known-gaps   Skip documented known-gap test failures.');
  console.log('  --batch-size=N       Rows per batch (default: 500 or env BATCH_SIZE).');
  console.log('  --concurrency=N      Parallel workers (default: 4 or env CONCURRENCY).');
  console.log('  --list               Print this help and exit.\n');
}

// ─── Dispatch ─────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  const args = parseArgs();
  if (!validate(args)) { process.exitCode = 1; return; }
  if (args.list) { printList(); return; }

  switch (args.mode) {
    case 'test': {
      const { runModeTest } = await import('./lib/regen/mode-test');
      await runModeTest(args);
      break;
    }
    case 'fullregen': {
      const { runModeFullregen } = await import('./lib/regen/mode-fullregen');
      await runModeFullregen(args);
      break;
    }
    case 'diff': {
      const { runModeDiff } = await import('./lib/regen/mode-diff');
      await runModeDiff(args);
      break;
    }
    case 'enrich': {
      const { runModeEnrich } = await import('./lib/regen/mode-enrich');
      await runModeEnrich(args);
      break;
    }
  }
}

const invokedDirectly = /regen-isnad-graph\.(ts|js)$/.test(process.argv[1] ?? '');
if (invokedDirectly) {
  main()
    .catch((err) => { console.error('\nregen-isnad-graph failed:', err); process.exitCode = 1; })
    .finally(() => closeDriver());
}

// ─── runRegen — programmatic entry point (used by tests) ─────────────────────

/**
 * Programmatic entry point for tests. Accepts the legacy fixture-test shape
 * { limit?, noWrite?, versionLabel? } and dispatches to runModeFullregen.
 * The `limit` and `noWrite` fields are accepted for API compatibility but
 * are not yet plumbed into the mode (fullregen always runs to completion).
 */
export interface RunRegenOpts {
  limit?: number;
  noWrite?: boolean;
  versionLabel?: string;
}

export async function runRegen(opts: RunRegenOpts = {}): Promise<void> {
  const args: CliArgs = {
    mode: 'fullregen',
    field: '',
    source: '',
    stagingPath: '',
    allowKnownGaps: false,
    batchSize: parseInt(process.env['BATCH_SIZE'] ?? '500', 10) || 500,
    concurrency: parseInt(process.env['CONCURRENCY'] ?? '4', 10) || 4,
    list: false,
  };
  const { runModeFullregen } = await import('./lib/regen/mode-fullregen');
  await runModeFullregen(args);
}
