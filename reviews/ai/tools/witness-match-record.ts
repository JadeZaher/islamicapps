/**
 * Validate and record verified text-checker matches (`shura-text-checker-output/1`) as `chain_fix_witness_matches`
 * records to unlock the `Agent verified` tier (0023).
 *
 * Requires `text_check.status === "matches"` with empty `differences`, at least one independent witness (`HKG`, `RWY`, or
 * `online` URL — never `THQ`/`OITI` echo-only), non-empty `locator` and `method`, and `reader_text_sha256` bound to the
 * `chain_fix`. Writes append-only JSONL records under `<store>/witness-matches/` and optionally inserts into Postgres
 * `chain_fix_witness_matches` when `--database development|production` is given (never writes DB without `--database`).
 *
 *   npx tsx reviews/ai/tools/witness-match-record.ts --packets <dir|file> --outputs <dir|file> --reports <reports.jsonl>
 *        [--store <dir>] [--fix <chain-fix:id>] [--method <method>] [--strict] [--allow-missing-fix] [--check-only]
 *        [--database development|production --confirm-production --dry-run]
 */
import { existsSync, mkdirSync, readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import postgres from 'postgres';
import { resolveTargetDatabase } from '../../../src/db/target-database';
import {
  appendRecords,
  argumentsOf,
  computeStates,
  DEFAULT_STORE,
  readApplications,
  readArchiveHolds,
  readReviews,
  readSubmissions,
  REPOSITORY_ROOT,
  storePaths,
  utcNow,
  type FixState,
  type Submission,
} from './chain-fix-lib';
import { sha256Hex } from './specialist-lib';

export const WITNESS_MATCH_FORMAT = 'shura-chain-fix-witness-match/1';
export const ACTOR = 'witness-match-record';
export const INDEPENDENT_LOCAL_SOURCES = new Set(['HKG', 'RWY']);
export const ECHO_ONLY_SOURCES = new Set(['THQ', 'OITI']);
export const MATCHING_COPY_RELATIONS = new Set(['identical_after_normalisation', 'identical_except_word_spacing']);
const VALID_SHA256 = /^[0-9a-f]{64}$/;
const URL_PATTERN = /^https?:\/\/\S+$/i;
const FENCE = /^\s*```(?:json)?\s*\n([\s\S]*?)\n\s*```\s*$/;

const USAGE = `usage: npx tsx reviews/ai/tools/witness-match-record.ts --packets <dir|file> --outputs <dir|file> --reports <reports.jsonl>
         [--store <dir>] [--fix <chain-fix:id>] [--method <method>] [--run-id <id>] [--model <id>]
         [--strict] [--allow-missing-fix] [--check-only]
         [--database development|production [--confirm-production] [--dry-run]]`;

export interface PacketCopy {
  source: string;
  locator?: string;
  relation?: string;
}

export interface TextPacketItem {
  id: string;
  text: string;
  context?: {
    work?: { name?: string; tradition?: string };
    text_and_metadata?: {
      stored_text_sha256?: string;
      copies?: PacketCopy[];
    };
  };
}

export interface TextCheckerOutput {
  id: string;
  text_check: {
    status: string;
    compared: string[];
    differences: unknown[];
    reason?: string;
    witness?: string;
    locator?: string;
    method?: string;
  };
  metadata_check: {
    status: string;
    compared: string[];
    differences: unknown[];
    reason?: string;
  };
  fixes: unknown[];
  notes: string[];
}

export interface ReportRow {
  id: string;
  hadith_id: string;
  text: string;
  text_layout?: string;
}

export interface BoundChainFix {
  fix_id: string;
  hadith_id: string;
  reader_text_sha256: string;
}

export interface WitnessMatchRecord {
  format: typeof WITNESS_MATCH_FORMAT;
  id: string;
  fix_id: string;
  hadith_id: string;
  witness: string;
  locator: string;
  method: string;
  matched: boolean;
  reader_text_sha256: string;
  note: string;
  packet_item_id: string;
  packet_path: string;
  packet_sha256: string;
  compared: string[];
  independent_sources: string[];
  model_id: string | null;
  run_id: string | null;
  recorded_at: string;
  created_by: string;
}

export interface WitnessValidationInput {
  output: unknown;
  packet: TextPacketItem;
  fix: BoundChainFix;
  report?: ReportRow;
  methodOverride?: string;
  packetPath?: string;
  packetSha256?: string;
  runId?: string | null;
  modelId?: string | null;
  recordedAt?: string;
}

export interface WitnessValidationResult {
  valid: boolean;
  classification: 'independent_match' | 'echo_only' | 'not_matches' | 'invalid';
  errors: string[];
  record: WitnessMatchRecord | null;
}

export function isOnlineCompared(entry: string): boolean {
  const trimmed = entry.trim();
  return trimmed === 'online' || URL_PATTERN.test(trimmed);
}

export function parseCheckerJson(raw: string): unknown {
  const fenced = FENCE.exec(raw);
  return JSON.parse(fenced ? fenced[1] : raw);
}

function witnessLabelForSource(source: string): string {
  if (source === 'HKG') return 'hadith-kg';
  if (source === 'RWY') return 'Riwayat';
  if (URL_PATTERN.test(source)) {
    try {
      return new URL(source).hostname;
    } catch {
      return source;
    }
  }
  return source;
}

function methodForRelation(source: string, relation?: string): string {
  if (isOnlineCompared(source)) return 'online_text_check';
  if (relation === 'identical_after_normalisation') return 'local_copy_normalised_match';
  if (relation === 'identical_except_word_spacing') return 'local_copy_word_spacing_match';
  return relation ? `local_copy:${relation}` : 'local_copy_match';
}

export function witnessMatchIdOf(fixId: string, readerTextSha256: string, witness: string, locator: string, method: string): string {
  return `witness-match:${sha256Hex([fixId, readerTextSha256, witness, locator, method].join('\u001f')).slice(0, 24)}`;
}

/**
 * Validate one text-checker output as a primary-witness match for a chain fix.
 * Enforces:
 * - `text_check.status === "matches"` with empty `differences`
 * - At least one independent witness (`HKG`, `RWY`, or `online` URL; never `THQ`/`OITI` echo-only)
 * - Non-empty `locator` and `method`
 * - `reader_text_sha256` bound to the packet text and matching `fix.reader_text_sha256`
 */
export function validateWitnessCandidate(input: WitnessValidationInput): WitnessValidationResult {
  const { output, packet, fix, report } = input;
  const errors: string[] = [];

  if (!output || typeof output !== 'object' || Array.isArray(output)) {
    return { valid: false, classification: 'invalid', errors: ['shape: output is not a JSON object'], record: null };
  }
  const obj = output as Record<string, unknown>;
  if (obj.id !== packet.id) {
    errors.push(`id: ${JSON.stringify(obj.id)} does not match packet id ${JSON.stringify(packet.id)}`);
  }
  const tc = obj.text_check as Record<string, unknown> | undefined;
  if (!tc || typeof tc !== 'object' || Array.isArray(tc)) {
    return { valid: false, classification: 'invalid', errors: [...errors, 'text_check: missing or not an object'], record: null };
  }
  const status = tc.status;
  if (status !== 'matches') {
    return {
      valid: false,
      classification: 'not_matches',
      errors: [...errors, `text_check.status: expected "matches", got ${JSON.stringify(status)}`],
      record: null,
    };
  }
  if (!Array.isArray(tc.differences) || tc.differences.length > 0) {
    errors.push('text_check.differences: status "matches" must have an empty differences array');
  }
  if (!Array.isArray(tc.compared) || !tc.compared.every((c): c is string => typeof c === 'string' && c.trim().length > 0)) {
    return { valid: false, classification: 'invalid', errors: [...errors, 'text_check.compared: must be a non-empty list of source codes or URLs'], record: null };
  }

  const compared = tc.compared.map((c) => c.trim());
  const independentLocal = compared.filter((c) => INDEPENDENT_LOCAL_SOURCES.has(c));
  const onlineEntries = compared.filter((c) => isOnlineCompared(c));
  const echoEntries = compared.filter((c) => ECHO_ONLY_SOURCES.has(c));
  const hasIndependent = independentLocal.length > 0 || onlineEntries.length > 0;

  if (!hasIndependent) {
    if (echoEntries.length > 0) {
      return {
        valid: false,
        classification: 'echo_only',
        errors: [...errors, `independent_witness: only echo source(s) (${echoEntries.join(', ')}) present; an independent witness (HKG, RWY, or online) is required`],
        record: null,
      };
    }
    return {
      valid: false,
      classification: 'invalid',
      errors: [...errors, `independent_witness: compared (${compared.join(', ') || 'none'}) includes no independent witness (HKG, RWY, or online)`],
      record: null,
    };
  }

  // Verify local independent copies against packet context copies and resolve witness + locator + method.
  const copies = packet.context?.text_and_metadata?.copies ?? [];
  const matchedLocal: { source: string; locator: string; relation: string }[] = [];
  for (const src of independentLocal) {
    const copy = copies.find((c) => c.source === src);
    if (!copy) {
      errors.push(`witness_copy: ${src} is claimed in compared, but packet context.text_and_metadata.copies has no ${src} entry`);
      continue;
    }
    if (!copy.relation || !MATCHING_COPY_RELATIONS.has(copy.relation)) {
      errors.push(`witness_relation: ${src} copy has relation ${JSON.stringify(copy.relation ?? null)}, not a whole-text match`);
      continue;
    }
    const loc = (typeof tc.locator === 'string' && tc.locator.trim()) ? tc.locator.trim() : (copy.locator ?? '').trim();
    if (!loc) {
      errors.push(`locator: ${src} copy is missing a non-empty locator`);
      continue;
    }
    matchedLocal.push({ source: src, locator: loc, relation: copy.relation });
  }

  let primaryWitness = '';
  let primaryLocator = '';
  let primaryMethod = '';

  const explicitWitness = typeof tc.witness === 'string' ? tc.witness.trim() : '';
  const explicitLocator = typeof tc.locator === 'string' ? tc.locator.trim() : '';
  const explicitMethod = (input.methodOverride ?? (typeof tc.method === 'string' ? tc.method : '')).trim();

  if (matchedLocal.length > 0) {
    const preferred = matchedLocal.find((m) => m.source === 'HKG') ?? matchedLocal[0];
    primaryWitness = explicitWitness || (matchedLocal.length > 1 ? matchedLocal.map((m) => witnessLabelForSource(m.source)).join(' + ') : witnessLabelForSource(preferred.source));
    primaryLocator = explicitLocator || matchedLocal.map((m) => m.locator).join('; ');
    primaryMethod = explicitMethod || methodForRelation(preferred.source, preferred.relation);
  } else if (onlineEntries.length > 0) {
    const firstOnline = onlineEntries[0];
    const urlLocator = URL_PATTERN.test(firstOnline) ? firstOnline : '';
    primaryWitness = explicitWitness || witnessLabelForSource(firstOnline);
    primaryLocator = explicitLocator || urlLocator;
    primaryMethod = explicitMethod || methodForRelation(firstOnline);
    if (!primaryLocator) {
      errors.push('locator: online witness requires a URL or explicit non-empty locator');
    }
  }

  if (!primaryWitness.trim()) errors.push('witness: resolved witness is empty');
  if (!primaryLocator.trim()) errors.push('locator: resolved locator is empty');
  if (!primaryMethod.trim()) errors.push('method: resolved method is empty');

  const readerTextSha256 = sha256Hex(packet.text);
  if (!VALID_SHA256.test(readerTextSha256)) {
    errors.push(`reader_text_sha256: invalid sha256 ${readerTextSha256}`);
  }
  if (report) {
    if (report.text !== packet.text) {
      errors.push(`report_text: packet text hash ${readerTextSha256} does not match report ${report.id} text hash ${sha256Hex(report.text)}`);
    }
    if (report.hadith_id !== fix.hadith_id) {
      errors.push(`hadith_id: report ${report.id} is ${report.hadith_id}, but fix ${fix.fix_id} belongs to ${fix.hadith_id}`);
    }
  }
  if (!VALID_SHA256.test(fix.reader_text_sha256)) {
    errors.push(`fix.reader_text_sha256: invalid sha256 on fix ${fix.fix_id}`);
  } else if (fix.reader_text_sha256 !== readerTextSha256) {
    errors.push(`stale_reader_text_sha256: packet text sha256 (${readerTextSha256}) does not match chain_fix ${fix.fix_id} (${fix.reader_text_sha256})`);
  }

  const independentSources = [...new Set([...matchedLocal.map((m) => m.source), ...(onlineEntries.length > 0 ? ['online'] : [])])];
  const noteParts = [`Verified text_check=matches via ${compared.join(', ')}`];
  if (echoEntries.length > 0) noteParts.push(`(echo sources also listed: ${echoEntries.join(', ')})`);
  const note = noteParts.join(' ');

  if (errors.length > 0) {
    return { valid: false, classification: 'invalid', errors, record: null };
  }

  return {
    valid: true,
    classification: 'independent_match',
    errors: [],
    record: {
      format: WITNESS_MATCH_FORMAT,
      id: witnessMatchIdOf(fix.fix_id, readerTextSha256, primaryWitness, primaryLocator, primaryMethod),
      fix_id: fix.fix_id,
      hadith_id: fix.hadith_id,
      witness: primaryWitness,
      locator: primaryLocator,
      method: primaryMethod,
      matched: true,
      reader_text_sha256: readerTextSha256,
      note,
      packet_item_id: packet.id,
      packet_path: input.packetPath ?? '',
      packet_sha256: input.packetSha256 ?? '',
      compared,
      independent_sources: independentSources,
      model_id: input.modelId ?? null,
      run_id: input.runId ?? null,
      recorded_at: input.recordedAt ?? utcNow(),
      created_by: ACTOR,
    },
  };
}

export function readWitnessMatches(storeRoot: string): WitnessMatchRecord[] {
  const dir = path.join(storeRoot, 'witness-matches');
  if (!existsSync(dir)) return [];
  return readdirSync(dir)
    .filter((name) => name.endsWith('.jsonl'))
    .sort()
    .flatMap((name) =>
      readFileSync(path.join(dir, name), 'utf8')
        .split('\n')
        .filter(Boolean)
        .map((line) => JSON.parse(line) as WitnessMatchRecord),
    );
}

interface LoadedPackets {
  items: Map<string, { item: TextPacketItem; packetPath: string; packetSha256: string; packetNum: string | null }>;
}

function loadPackets(target: string): LoadedPackets {
  const resolved = path.resolve(target);
  const files = statSync(resolved).isDirectory()
    ? readdirSync(resolved)
        .filter((n) => /^packet-.*\.jsonl$/.test(n))
        .sort()
        .map((n) => path.join(resolved, n))
    : [resolved];
  const items = new Map<string, { item: TextPacketItem; packetPath: string; packetSha256: string; packetNum: string | null }>();
  for (const file of files) {
    const bytes = readFileSync(file);
    const packetSha256 = sha256Hex(bytes);
    const packetPath = path.relative(REPOSITORY_ROOT, file).replace(/\\/g, '/');
    const numMatch = /packet-(\d+)\.jsonl$/.exec(path.basename(file));
    const packetNum = numMatch ? numMatch[1] : null;
    for (const line of bytes.toString('utf8').split(/\r?\n/)) {
      if (!line.trim()) continue;
      const item = JSON.parse(line) as TextPacketItem;
      items.set(item.id, { item, packetPath, packetSha256, packetNum });
    }
  }
  return { items };
}

function parseRunTxt(outputsDir: string): Map<string, { run_id: string; model_id: string }> {
  const map = new Map<string, { run_id: string; model_id: string }>();
  const runTxt = path.join(outputsDir, 'RUN.txt');
  if (!existsSync(runTxt)) return map;
  for (const line of readFileSync(runTxt, 'utf8').split(/\r?\n/)) {
    if (!line.trim()) continue;
    const runId = /\brun_id=([^\s|]+)/.exec(line)?.[1];
    const model = /\bmodel=([^\s|]+)/.exec(line)?.[1];
    const packets = /\bpackets=([^\s|]+)/.exec(line)?.[1];
    if (!runId || !model || !packets) continue;
    for (const p of packets.split(',')) {
      map.set(p.trim(), { run_id: runId, model_id: model });
    }
  }
  return map;
}

/** Pick the active chain_fix for each hadith_id in the store (accepting an explicit fix override when requested). */
function resolveFixes(storeRoot: string, explicitFixId?: string): { byHadith: Map<string, BoundChainFix>; byFix: Map<string, BoundChainFix> } {
  const paths = storePaths(storeRoot);
  const submissions = readSubmissions(paths);
  const bySubmission = new Map<string, Submission>(submissions.map((s) => [s.submission_id, s]));
  const states = computeStates(submissions, readReviews(paths), readApplications(paths), readArchiveHolds(paths));

  const priority = (s: FixState): number => {
    if (s.state === 'confirmed') return 0;
    if (s.state === 'accepted' && s.effect !== null) return 1;
    if (s.state === 'accepted') return 2;
    if (s.state === 'held' || s.state === 'awaiting_human' || s.state === 'submitted' || s.state === 'disputed') return 3;
    return 4;
  };

  const byFix = new Map<string, BoundChainFix>();
  const grouped = new Map<string, FixState[]>();
  for (const state of states) {
    const rep = bySubmission.get(state.representative_submission_id);
    if (!rep) continue;
    byFix.set(state.fix_id, { fix_id: state.fix_id, hadith_id: state.hadith_id, reader_text_sha256: rep.reader_text_sha256 });
    grouped.set(state.hadith_id, [...(grouped.get(state.hadith_id) ?? []), state]);
  }
  const byHadith = new Map<string, BoundChainFix>();
  for (const [hadithId, candidates] of grouped) {
    const sorted = [...candidates].sort((a, b) => priority(a) - priority(b) || a.fix_id.localeCompare(b.fix_id));
    const chosen = sorted[0];
    if (chosen && priority(chosen) < 4) {
      byHadith.set(hadithId, byFix.get(chosen.fix_id)!);
    }
  }
  if (explicitFixId && !byFix.has(explicitFixId)) {
    throw new Error(`--fix ${explicitFixId} is not in store ${storeRoot}`);
  }
  return { byHadith, byFix };
}

export async function recordWitnessMatchesToDatabase(
  records: WitnessMatchRecord[],
  argv: string[],
  dryRun: boolean,
): Promise<{ inserted: number; skippedExisting: number }> {
  if (records.length === 0) return { inserted: 0, skippedExisting: 0 };
  const target = resolveTargetDatabase(argv, { required: true });
  const sql = postgres(target.url, {
    max: 1,
    idle_timeout: 0,
    max_lifetime: null,
    prepare: false,
    onnotice: () => {},
    connection: { application_name: ACTOR, statement_timeout: 60_000, lock_timeout: 5_000 },
  });
  let inserted = 0;
  let skippedExisting = 0;
  class DryRunRollback extends Error {}
  try {
    await sql
      .begin(async (tx) => {
        const fixIds = [...new Set(records.map((r) => r.fix_id))];
        const fixes = await tx<{ id: string; hadith_id: string; reader_text_sha256: string }[]>`
          select id, hadith_id, reader_text_sha256 from chain_fixes where id = any(${fixIds})`;
        const fixMap = new Map(fixes.map((f) => [f.id, f]));
        const existing = new Set(
          (await tx<{ id: string }[]>`select id from chain_fix_witness_matches where id = any(${records.map((r) => r.id)})`).map((r) => r.id),
        );
        for (const rec of records) {
          const dbFix = fixMap.get(rec.fix_id);
          if (!dbFix) throw new Error(`database has no chain_fixes row ${rec.fix_id}; mirror/apply fixes first`);
          if (dbFix.hadith_id !== rec.hadith_id) throw new Error(`database fix ${rec.fix_id} belongs to ${dbFix.hadith_id}, not ${rec.hadith_id}`);
          if (dbFix.reader_text_sha256 !== rec.reader_text_sha256) {
            throw new Error(`database fix ${rec.fix_id} reader_text_sha256 ${dbFix.reader_text_sha256} does not match ${rec.reader_text_sha256}`);
          }
          if (existing.has(rec.id)) {
            skippedExisting += 1;
            continue;
          }
          await tx`
            insert into chain_fix_witness_matches
              (id, fix_id, hadith_id, witness, locator, method, matched, reader_text_sha256, note, created_by, updated_by)
            values
              (${rec.id}, ${rec.fix_id}, ${rec.hadith_id}, ${rec.witness}, ${rec.locator}, ${rec.method}, ${rec.matched},
               ${rec.reader_text_sha256}, ${rec.note}, ${ACTOR}, ${ACTOR})
            on conflict (id) do nothing`;
          inserted += 1;
        }
        if (dryRun) throw new DryRunRollback();
      })
      .catch((error) => {
        if (!(error instanceof DryRunRollback)) throw error;
      });
  } finally {
    await sql.end({ timeout: 5 });
  }
  return { inserted, skippedExisting };
}

async function main(): Promise<number> {
  const argv = process.argv.slice(2);
  const args = argumentsOf(argv);
  if (args.has('help') || !args.get('packets') || !args.get('outputs') || !args.get('reports')) {
    console.log(USAGE);
    return args.has('help') ? 0 : 2;
  }

  const packetsArg = args.get('packets')!;
  const outputsArg = path.resolve(args.get('outputs')!);
  const reportsArg = path.resolve(args.get('reports')!);
  const storeRoot = path.resolve(args.get('store') ?? DEFAULT_STORE);
  const explicitFixId = args.get('fix');
  const methodOverride = args.get('method');
  const checkOnly = args.has('check-only');
  const allowMissingFix = args.has('allow-missing-fix');
  const isSingleOutput = !statSync(outputsArg).isDirectory();
  const strict = args.has('strict') || isSingleOutput;

  // Check database target up front before doing work if --database was passed, so missing --confirm-production fails immediately.
  const useDatabase = args.has('database');
  if (useDatabase) {
    resolveTargetDatabase(argv, { required: true });
  }

  const { items: packetItems } = loadPackets(packetsArg);
  const reports = new Map<string, ReportRow>(
    readFileSync(reportsArg, 'utf8')
      .split(/\r?\n/)
      .filter((l) => l.trim())
      .map((l) => {
        const row = JSON.parse(l) as ReportRow;
        return [row.id, row];
      }),
  );
  const { byHadith, byFix } = resolveFixes(storeRoot, explicitFixId);

  const outputFiles = isSingleOutput
    ? [outputsArg]
    : readdirSync(outputsArg)
        .filter((n) => n.endsWith('.json'))
        .sort()
        .map((n) => path.join(outputsArg, n));
  if (isSingleOutput && explicitFixId && outputFiles.length !== 1) {
    throw new Error('--fix requires a single output item');
  }

  const runByPacket = isSingleOutput ? new Map<string, { run_id: string; model_id: string }>() : parseRunTxt(outputsArg);
  const fallbackRunId = args.get('run-id') ?? null;
  const fallbackModel = args.get('model') ?? null;
  const now = args.get('now') ?? utcNow();

  const records: WitnessMatchRecord[] = [];
  const problems: string[] = [];
  const tally = {
    examined: 0,
    matched_independent: 0,
    skipped_echo_only: 0,
    skipped_not_matches: 0,
    skipped_no_fix: 0,
    duplicates: 0,
  };

  for (const file of outputFiles) {
    tally.examined += 1;
    let parsed: unknown;
    try {
      parsed = parseCheckerJson(readFileSync(file, 'utf8'));
    } catch (error) {
      problems.push(`${path.basename(file)}: not valid JSON (${error instanceof Error ? error.message : String(error)})`);
      continue;
    }
    const stemId = path.basename(file, '.json');
    const outputId = parsed && typeof parsed === 'object' && typeof (parsed as { id?: unknown }).id === 'string' ? (parsed as { id: string }).id : stemId;
    const loadedPacket = packetItems.get(outputId);
    if (!loadedPacket) {
      problems.push(`${outputId}: not found in --packets`);
      continue;
    }
    const report = reports.get(outputId);
    if (!report) {
      problems.push(`${outputId}: not found in --reports`);
      continue;
    }

    const tc = parsed && typeof parsed === 'object' ? (parsed as { text_check?: { status?: unknown; compared?: unknown } }).text_check : undefined;
    if (!strict && tc && typeof tc === 'object' && tc.status !== 'matches' && (tc.status === 'not_checked' || tc.status === 'differs')) {
      tally.skipped_not_matches += 1;
      continue;
    }

    const fix = explicitFixId ? byFix.get(explicitFixId) : byHadith.get(report.hadith_id);
    if (!fix) {
      if (allowMissingFix && !strict) {
        tally.skipped_no_fix += 1;
        continue;
      }
      problems.push(`${outputId} (${report.hadith_id}): no active chain_fix in store`);
      continue;
    }

    const runMeta = loadedPacket.packetNum ? runByPacket.get(loadedPacket.packetNum) : undefined;
    const result = validateWitnessCandidate({
      output: parsed,
      packet: loadedPacket.item,
      fix,
      report,
      methodOverride,
      packetPath: loadedPacket.packetPath,
      packetSha256: loadedPacket.packetSha256,
      runId: runMeta?.run_id ?? fallbackRunId,
      modelId: runMeta?.model_id ?? fallbackModel,
      recordedAt: now,
    });

    if (!result.valid) {
      if (!strict && result.classification === 'echo_only') {
        tally.skipped_echo_only += 1;
        continue;
      }
      for (const err of result.errors) problems.push(`${outputId}: ${err}`);
      continue;
    }
    tally.matched_independent += 1;
    records.push(result.record!);
  }

  if (problems.length > 0) {
    for (const p of problems) console.error(`FAIL ${p}`);
    console.error(`nothing recorded: ${problems.length} problem(s)`);
    return 1;
  }

  const existing = new Set(readWitnessMatches(storeRoot).map((r) => r.id));
  const fresh = records.filter((r) => !existing.has(r.id));
  tally.duplicates = records.length - fresh.length;

  for (const r of fresh) {
    console.log(`ok   ${r.packet_item_id} ${r.fix_id} (${r.hadith_id}): witness="${r.witness}" locator="${r.locator}" method="${r.method}"`);
  }
  for (const r of records.filter((x) => existing.has(x.id))) {
    console.log(`dup  ${r.packet_item_id}: already recorded as ${r.id}`);
  }

  if (!checkOnly && fresh.length > 0) {
    const dir = path.join(storeRoot, 'witness-matches');
    mkdirSync(dir, { recursive: true });
    const byRun = new Map<string, WitnessMatchRecord[]>();
    for (const r of fresh) {
      const bucket = r.run_id ? r.run_id.replace(/[^A-Za-z0-9._-]+/g, '-') : 'witness-matches';
      byRun.set(bucket, [...(byRun.get(bucket) ?? []), r]);
    }
    for (const [bucket, group] of byRun) {
      appendRecords(path.join(dir, `${bucket}.jsonl`), group);
    }
  }

  let dbSummary = '';
  if (useDatabase && !checkOnly) {
    const dbResult = await recordWitnessMatchesToDatabase(records, argv, args.has('dry-run'));
    dbSummary = `; db inserted=${dbResult.inserted}, db_existing=${dbResult.skippedExisting}${args.has('dry-run') ? ' (dry-run rolled back)' : ''}`;
  }

  console.log(
    `summary: examined=${tally.examined}, matched=${tally.matched_independent}, fresh=${fresh.length}, dup=${tally.duplicates}, `
      + `skipped_echo=${tally.skipped_echo_only}, skipped_not_matches=${tally.skipped_not_matches}, skipped_no_fix=${tally.skipped_no_fix}${dbSummary}`,
  );
  return 0;
}

if (require.main === module) {
  main().then(
    (code) => (process.exitCode = code),
    (error) => {
      console.error(`FAIL ${error instanceof Error ? error.message : String(error)}`);
      process.exitCode = 1;
    },
  );
}
