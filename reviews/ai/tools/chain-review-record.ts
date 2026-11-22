/**
 * Record a reviewer set's AI reviews (chain-reader/reviewer, prompt 1.1.0) per item into the chain-fix store, with what
 * review_rules_v1_1.outcome does with each on the fix's CURRENT state, then recompute the states (reviews/ai/AGENTS.md §AI review tier).
 * A correction two independent reviews wrote alike becomes a new fix (planned by the engine, `corrects_fix_id`); an invalid item is
 * recorded in `review-invalid/` and changes nothing.
 *
 *   npx tsx reviews/ai/tools/chain-review-record.ts --batch <reviewer set folder> [--prompt-version 1.1.0] [--store <dir>]
 *        [--overrides <file>] [--check-only] [--allow-out-of-order] [--now <UTC>] [--extra-second <dir> ...] [--expect <outcomes.tsv>]
 * `--extra-second`: batch-shaped folders whose pass-2 reviews count as second runs (record_reviews_v1_1 `extra_second_dirs`). `--expect`: the
 * reviewer side's outcomes.tsv (columns by header name; extra trailing columns ignored): every recorded outcome must equal it, else nothing is written.
 */
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import {
  appendRecords,
  argumentsOf,
  chainSha256,
  computeStates,
  DEFAULT_OVERRIDES,
  DEFAULT_STORE,
  fixIdOf,
  readApplications,
  readArchiveHolds,
  readReviews,
  readSubmissions,
  reconcile,
  REPOSITORY_ROOT,
  REVIEW_FORMAT,
  REVIEWER_PROMPTS,
  REVIEWER_SPECIALIST_ID,
  routesKey,
  runEngine,
  storePaths,
  submissionIdOf,
  SUBMISSION_FORMAT,
  utcNow,
  type FixState,
  type Review,
  type ReviewOutcome,
  type Submission,
} from './chain-fix-lib';
import { sha256Hex } from './specialist-lib';

const BRIDGE = path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'chain-fixes', 'review_bridge.py');
const USAGE = 'usage: npx tsx reviews/ai/tools/chain-review-record.ts --batch <reviewer set folder> [--prompt-version 1.1.0] [--store <dir>] [--overrides <file>] [--check-only] [--allow-out-of-order]';

/** One item as review_bridge.py returns it. */
interface BridgeRun { run_id: string; model_id: string; started_at: string; finished_at: string }
interface BridgeReview { id: string; decision: string; question: string | null; reasons: { claim: string; source: string; quote: string }[]; variant_verdicts: unknown[]; corrected_reading: unknown; uncertainty: string }
interface BridgeItem {
  opaque: string;
  valid: boolean;
  problem: string | null;
  review: BridgeReview | null;
  pass_label: string | null;
  packet: string | null;
  packet_sha256: string | null;
  run: BridgeRun | null;
  second: { review: BridgeReview; pass_label: string; packet: string | null; packet_sha256: string | null; run: BridgeRun | null } | null;
  decision?: string;
  effective?: string;
  outcome: ReviewOutcome | null;
  second_run: boolean | null;
  readers_agree: boolean;
  agreed_empty: boolean;
  codes?: string[];
  text_sha256?: string;
  text?: string;
  context?: unknown;
}

/** The status the reviewer's rule reads: the fix store's, never the packet's. */
function statusOf(state: FixState): 'held' | 'pending' | 'applied' | null {
  if (state.database === 'applied') return 'applied';
  if (state.state === 'accepted') return 'pending';
  if (state.state === 'held' || state.state === 'awaiting_human' || state.state === 'disputed') return 'held';
  return null;
}

function runBridge(request: object): { items: BridgeItem[]; clearable: string[] } {
  const python = process.env.CHAIN_FIX_PYTHON ?? 'python';
  const result = spawnSync(python, ['-I', BRIDGE], { input: Buffer.from(JSON.stringify(request), 'utf8'), maxBuffer: 512 * 1024 * 1024 });
  if (result.error) throw new Error(`could not run ${python}: ${result.error.message}`);
  if (result.status !== 0) throw new Error(`review_bridge.py failed:\n${result.stderr.toString('utf8')}`);
  return JSON.parse(result.stdout.toString('utf8'));
}

const relative = (file: string | null) => (file ? path.relative(REPOSITORY_ROOT, path.resolve(file)).replace(/\\/g, '/') : '');

async function main(): Promise<number> {
  const args = argumentsOf(process.argv.slice(2));
  if (args.has('help') || !args.get('batch')) {
    console.log(USAGE);
    return args.has('help') ? 0 : 2;
  }
  const batch = path.resolve(args.get('batch')!);
  const promptVersion = args.get('prompt-version') ?? '1.1.0';
  const promptPath = REVIEWER_PROMPTS[promptVersion];
  if (!promptPath) return fail([`--prompt-version: one of ${Object.keys(REVIEWER_PROMPTS).join(', ')}`]);
  const promptSha256 = sha256Hex(readFileSync(path.join(REPOSITORY_ROOT, promptPath)));
  const paths = storePaths(args.get('store') ?? DEFAULT_STORE);
  const idMap = (JSON.parse(readFileSync(path.join(batch, 'private', 'id_map.json'), 'utf8')) as { ids: Record<string, string> }).ids;

  const submissions = readSubmissions(paths);
  const reviews = readReviews(paths);
  const states = computeStates(submissions, reviews, readApplications(paths), readArchiveHolds(paths));
  const stateOf = new Map(states.map((state) => [state.fix_id, state]));
  const bySubmission = new Map(submissions.map((s) => [s.submission_id, s]));
  // A reading id names the fix the readers' runs gave (the newest reader submission of that packet item, not a correction).
  const fixOfReading = new Map<string, string>();
  for (const s of [...submissions].filter((x) => !x.corrects_fix_id).sort((a, b) => a.submitted_at.localeCompare(b.submitted_at))) fixOfReading.set(s.packet_item_id, s.fix_id);

  const facts: Record<string, { status: string; codes: string[]; stored_equals_reading: boolean | null; human: string | null }> = {};
  const fixOfOpaque = new Map<string, FixState>();
  const notInStore: string[] = [];
  for (const [opaque, readingId] of Object.entries(idMap)) {
    const state = stateOf.get(fixOfReading.get(readingId) ?? '');
    const status = state ? statusOf(state) : null;
    if (!state || !status) {
      notInStore.push(`${opaque} (${readingId}): ${state ? `state ${state.state}: no review status` : 'no fix in the store'}`);
      continue;
    }
    fixOfOpaque.set(opaque, state);
    const representative = bySubmission.get(state.representative_submission_id)!;
    const humans = reviews.filter((r) => r.fix_id === state.fix_id && r.reviewer_kind === 'human').sort((a, b) => a.reviewed_at.localeCompare(b.reviewed_at));
    // The fix's own comparison decides whether the stored chain equals the reading (INTEGRATION-v1_1.md item 5).
    facts[opaque] = { status, codes: state.holds, stored_equals_reading: representative.fix_kinds.length === 1 && representative.fix_kinds[0] === 'no_change',
      human: humans.at(-1)?.decision === 'confirmed' || humans.at(-1)?.decision === 'rejected' ? humans.at(-1)!.decision : null };
  }

  const extraSecond = process.argv.slice(2).filter((value, index, all) => all[index - 1] === '--extra-second').map((dir) => path.resolve(dir));
  const bridged = runBridge({ batch, prompt_version: promptVersion, allow_out_of_order: args.has('allow-out-of-order'), facts, extra_second_dirs: extraSecond });
  const expected = args.get('expect') ? expectedOutcomes(args.get('expect')!) : null;
  const clearable = new Set(bridged.clearable);
  const known = new Set(reviews.map((r) => r.review_id));
  const knownSubmissions = new Set(submissions.map((s) => s.submission_id));
  const now = args.get('now') ?? utcNow();
  const newReviews: Review[] = [];
  const invalid: object[] = [];
  const corrections: Submission[] = [];
  const problems: string[] = [];
  const tally: Record<string, number> = {};
  for (const item of bridged.items) {
    const state = fixOfOpaque.get(item.opaque);
    if (!item.valid || !item.review) {
      // Recorded invalid with its first reason; the item stays exactly as it was and is re-queued by the reviewer's builder.
      invalid.push({ format: 'shura-chain-review-invalid/1', batch: relative(batch), opaque: item.opaque, reading_id: idMap[item.opaque], fix_id: state?.fix_id ?? null, problem: item.problem, at: now });
      tally.invalid = (tally.invalid ?? 0) + 1;
      continue;
    }
    if (!state || !item.outcome) continue;
    if (!item.run?.model_id || !item.packet_sha256) {
      problems.push(`${item.opaque}: no RUN.txt line names the model and run of its packet; the review cannot be attributed`);
      continue;
    }
    if (item.text_sha256 !== bySubmission.get(state.representative_submission_id)!.reader_text_sha256) {
      problems.push(`${item.opaque}: stale: the reviewer read another text than the fix (${state.fix_id}) is bound to`);
      continue;
    }
    const pass = Number(/^\d+/.exec(item.pass_label ?? '1')?.[0] ?? 1);
    const review: Review = {
      format: REVIEW_FORMAT,
      review_id: `chain-fix-review:${sha256Hex([state.fix_id, item.run.run_id, item.opaque, String(pass)].join('\u001f')).slice(0, 24)}`,
      fix_id: state.fix_id,
      hadith_id: state.hadith_id,
      reviewer_kind: 'ai',
      reviewer: REVIEWER_SPECIALIST_ID,
      model_id: item.run.model_id,
      prompt_path: promptPath,
      prompt_sha256: promptSha256,
      decision: null,
      superseded_by: null,
      note: (item.review.reasons[0]?.claim ?? `AI review: ${item.review.decision}`).slice(0, 2000),
      citation: null,
      reviewed_at: item.run.finished_at,
      review_decision: item.review.decision,
      outcome: item.outcome,
      codes_at_review: item.codes ?? [],
      status_at_review: facts[item.opaque].status as 'held' | 'pending' | 'applied',
      run_id: item.run.run_id,
      pass,
      packet_path: relative(item.packet),
      packet_sha256: item.packet_sha256,
      packet_item_id: item.opaque,
      started_at: item.run.started_at,
      finished_at: item.run.finished_at,
      specialist_version: promptVersion,
      uncertainty: item.review.uncertainty,
      question: item.review.question,
      reasons: item.review.reasons,
      variant_verdicts: item.review.variant_verdicts,
      corrected_reading: item.review.corrected_reading ?? null,
      second_run_id: item.second?.run?.run_id ?? null,
      second_run_agrees: item.second_run,
    };
    if (expected && expected.get(item.opaque) !== item.outcome) problems.push(`${item.opaque}: outcome ${item.outcome} here, ${expected.get(item.opaque) ?? 'none'} on the reviewer side`);
    tally[item.outcome] = (tally[item.outcome] ?? 0) + 1;
    if (!known.has(review.review_id)) newReviews.push(review);
    if (item.outcome === 'apply_correction' && item.second && item.text !== undefined) {
      const built = correctionSubmissions(item, state, bySubmission.get(state.representative_submission_id)!, clearable, promptPath, promptSha256, promptVersion, now);
      if (typeof built === 'string') problems.push(`${item.opaque}: ${built}`);
      else corrections.push(...built.filter((s) => !knownSubmissions.has(s.submission_id)));
    }
  }
  for (const line of notInStore) console.log(`skip ${line}`);
  for (const review of newReviews) console.log(`ok   ${review.packet_item_id} ${review.fix_id}: ${review.review_decision} -> ${review.outcome}`);
  for (const correction of corrections) console.log(`fix  ${correction.packet_item_id}: correction ${correction.fix_id} of ${correction.corrects_fix_id} (run ${correction.orchestrator_run_id})`);
  console.log(`items: ${JSON.stringify(tally)}; new reviews ${newReviews.length}; correction submissions ${corrections.length}`);
  if (problems.length > 0) return fail(problems);
  if (args.has('check-only')) return 0;
  appendRecords(path.join(paths.reviews, `ai-${REVIEWER_SPECIALIST_ID}.jsonl`), newReviews);
  appendRecords(path.join(paths.root, 'review-invalid', `${path.basename(batch)}.jsonl`), invalid);
  for (const runId of [...new Set(corrections.map((s) => s.orchestrator_run_id))]) {
    appendRecords(path.join(paths.submissions, `${runId}.jsonl`), corrections.filter((s) => s.orchestrator_run_id === runId));
  }
  const { transitions } = reconcile(paths, args.get('overrides') ?? DEFAULT_OVERRIDES, now);
  console.log(`decide: ${transitions.length} transition(s)`);
  return 0;
}

/**
 * The correction as a new fix: the engine plans the corrected reading (tool v3.4) against the readers' stored base, one submission per
 * review run (both runs wrote the same routes: the engine re-checks it). Holds a reviewer may clear are dropped; any other stands.
 */
function correctionSubmissions(item: BridgeItem, state: FixState, readers: Submission, clearable: Set<string>, promptPath: string, promptSha256: string,
                               promptVersion: string, now: string): Submission[] | string {
  const first = item.review!.corrected_reading as Record<string, unknown> | null;
  const second = item.second!.review.corrected_reading as Record<string, unknown> | null;
  if (!first || !second || !item.second!.run) return 'the correction or its second run is missing';
  const id = String(first.id ?? item.opaque);
  const [result] = runEngine([{
    key: '0', text: item.text!, expected_id: id, output: first, other_output: { ...second, id }, base: { chains: readers.base.chains.map((c) => ({ branch: c.branch, mentions: c.mentions })) },
    record_id: readers.record_id, source_work_id: readers.source_work_id, evidence: item.review!.reasons.filter((r) => r.source === 'text').map((r) => r.quote),
    require_coverage: false, reader_format: 'v3_4', tool_version: 'v3_4', context: item.context, sayings_supported: true,
  }]);
  if (result.errors.length > 0 || !result.planned) return `the correction does not plan: ${result.errors.slice(0, 2).join('; ')}`;
  const { fix_kinds: fixKinds, ...comparison } = result.comparison!;
  const fixId = fixIdOf(readers.hadith_id, readers.arabic_sha256, readers.reader_text_sha256, routesKey(result.planned));
  const holds = result.holds.filter((hold) => !clearable.has(hold.code));
  return [{ run: item.run!, review: item.review! }, { run: item.second!.run, review: item.second!.review }].map(({ run }) => ({
    ...readers,
    format: SUBMISSION_FORMAT,
    submission_id: submissionIdOf(fixId, run.run_id, run.model_id),
    fix_id: fixId,
    routes_key: routesKey(result.planned!),
    base: { ...readers.base, chain_sha256: chainSha256(readers.base.chains) },
    reading: { ...result.reading!, offsets_repaired: result.offsets_repaired },
    fix_kinds: fixKinds,
    comparison,
    planned: result.planned!,
    reason: "The AI reviewer's correction; a second independent review wrote the same routes.",
    evidence: (result.evidence_quotes ?? item.review!.reasons.filter((r) => r.source === 'text').map((r) => r.quote)).map((quote) => ({ quote })),
    computed_evidence: result.computed_evidence,
    external_citation: null,
    view: 'text_and_stored_chain',
    reader_format: 'v3_4',
    tool_version: 'v3_4',
    disposition: result.disposition,
    holds,
    derived_links: result.derived_links,
    corrects_fix_id: state.fix_id,
    specialist_id: REVIEWER_SPECIALIST_ID,
    specialist_version: promptVersion,
    prompt_path: promptPath,
    prompt_version: promptVersion,
    prompt_sha256: promptSha256,
    model_id: run.model_id,
    provider_runtime: 'Conduction worker (chain reviewer)',
    orchestrator_run_id: run.run_id,
    packet_path: relative(item.packet),
    packet_sha256: item.packet_sha256!,
    packet_item_id: item.opaque,
    started_at: run.started_at,
    finished_at: run.finished_at,
    submitted_at: now,
  }));
}

/** opaque -> outcome from a reviewer-side outcomes.tsv; columns found by header name, so added trailing columns change nothing. */
function expectedOutcomes(file: string): Map<string, string> {
  const [header, ...lines] = readFileSync(file, 'utf8').split(/\r?\n/).filter(Boolean).map((line) => line.split('\t'));
  const opaque = header.indexOf('opaque');
  const outcome = header.indexOf('outcome');
  return new Map(lines.map((cells) => [cells[opaque], cells[outcome]]));
}

function fail(problems: string[]): number {
  for (const problem of problems) console.error(`FAIL ${problem}`);
  console.error(`nothing recorded: ${problems.length} problem(s)`);
  return 1;
}

main().then(
  (code) => (process.exitCode = code),
  (error) => {
    console.error(`FAIL ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  },
);
