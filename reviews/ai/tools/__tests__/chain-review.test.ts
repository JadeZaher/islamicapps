/**
 * AI reviewer tier flows through the CLIs (reviews/ai/AGENTS.md §AI review tier), on real tranche-02 readings and the pilot's real
 * review outputs (chain-reader/reviewer/pilot-001/outputs/pass-1, prompt 1.0.0) in a private store: submit (tool v3.3), decide, record the
 * reviews, decide again. Transitions: applied + confirmation -> "AI reviewed"; applied + correction with one run -> stays applied, disputed;
 * the same correction repeated by a second review -> a new fix replaces it (the old one listed for revert); held with clearable holds +
 * confirmation -> applied; held with a non-clearable hold -> stays held; pending + confirmation -> AI reviewed; keep_stored on an applied
 * reading whose stored chain differs -> set aside and listed for revert; a human decision wins. Two inputs are made here, not by a model,
 * and say so: the second review of 80cd84 (a copy of its first, as a faithful second run would write) and one keep_stored decision.
 *
 *   npx tsx reviews/ai/tools/__tests__/chain-review.test.ts
 */
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { appendFileSync, cpSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { APPLICATION_FORMAT, REPOSITORY_ROOT, type FixState } from '../chain-fix-lib';

const failures: string[] = [];
function check(name: string, run: () => void): void {
  try {
    run();
    console.log(`ok   ${name}`);
  } catch (error) {
    failures.push(name);
    console.error(`FAIL ${name}\n     ${error instanceof Error ? error.message : String(error)}`);
  }
}

const READER = path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'chain-reader');
const T02 = path.join(READER, 'tranches', 'tranche-02');
const PILOT = path.join(READER, 'reviewer', 'pilot-001');
const work = mkdtempSync(path.join(tmpdir(), 'chain-review-test-'));
const store = path.join(work, 'store');
const overrides = path.join(work, 'accepted_overrides.jsonl.gz');
const batch = path.join(work, 'pilot-001');

// The pilot's items used here (opaque -> tranche-02 reading), each standing for one transition.
const APPLIED_CONFIRMED = 'cr1-cb858d'; //     applied, confirm_reading
const PENDING_CONFIRMED = 'cr1-0041c9'; //     left unapplied (pending), confirm_reading
const APPLIED_CORRECTED = 'cr1-80cd84'; //     applied, confirm_with_correction (substantive)
const HELD_CLEARABLE = 'cr1-2cd568'; //        held by has_variant_group (clearable), confirm_reading
const HELD_BLOCKED = 'cr1-18f33f'; //          held by has_variant_group plus an archive hold `needs_ruling` (not clearable)
const APPLIED_KEPT_STORED = 'cr1-e87ace'; //   applied; its decision is set to keep_stored here (synthetic)

function run(script: string, args: string[], expectCode = 0): string {
  const result = spawnSync(process.execPath, ['--import', 'tsx', path.join(REPOSITORY_ROOT, 'reviews', 'ai', 'tools', script), ...args],
    { cwd: REPOSITORY_ROOT, encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 });
  const output = `${result.stdout}${result.stderr}`;
  assert.equal(result.status, expectCode, `${script} exited ${result.status}:\n${output.slice(-3000)}`);
  return output;
}
function python(args: string[]): string {
  const result = spawnSync('python', ['-B', '-X', 'utf8', ...args], { cwd: READER, encoding: 'utf8', maxBuffer: 256 * 1024 * 1024 });
  assert.equal(result.status, 0, `${args[0]} failed:\n${result.stderr.slice(-3000)}`);
  return result.stdout;
}
const listFiles = (directory: string, suffix: string) => readdirSync(directory).filter((name) => name.endsWith(suffix)).sort().map((name) => path.join(directory, name));
const states = () => new Map((JSON.parse(readFileSync(path.join(store, 'state.json'), 'utf8')).fixes as FixState[]).map((s) => [s.fix_id, s]));
const queue = () => JSON.parse(readFileSync(path.join(store, 'queue.json'), 'utf8'));

try {
  // The pilot set, copied so a second review and the synthetic decision can be added without touching it.
  cpSync(PILOT, batch, { recursive: true, filter: (source) => !source.includes(`${path.sep}adjudication`) });
  const idMap = JSON.parse(readFileSync(path.join(batch, 'private', 'id_map.json'), 'utf8')).ids as Record<string, string>;
  const chosen = [APPLIED_CONFIRMED, PENDING_CONFIRMED, APPLIED_CORRECTED, HELD_CLEARABLE, HELD_BLOCKED, APPLIED_KEPT_STORED];
  const readings = chosen.map((opaque) => idMap[opaque]);
  writeFileSync(path.join(work, 'only.txt'), `${readings.join('\n')}\n`);

  // Envelopes for the chosen readings (tool v3.3). The two held ones need the triage's release flag to reach an envelope at all: the
  // pipeline's engine then holds them (has_variant_group), which is the state under test. Production never passes that flag.
  python(['v3_3/to_submission_v3_3.py', '--packets', path.join(T02, 'packets'), '--reports', path.join(T02, 'private', 'reports.jsonl'),
    '--pass-a', path.join(T02, 'outputs', 'pass-a'), '--pass-b', path.join(T02, 'outputs', 'pass-b'), '--out', path.join(work, 'envelopes'),
    '--batch', 't02', '--reader-prompt', 'v3_2', '--only', path.join(work, 'only.txt'), '--variant-notes-supported', '--release-variant-readings']);
  const envelopes = listFiles(path.join(work, 'envelopes'), '.json');
  assert.ok(envelopes.length > 0, 'no envelope written');
  for (const envelope of envelopes) run('chain-fix-submit.ts', ['--envelope', envelope, '--reports', path.join(T02, 'private', 'reports.jsonl'), '--store', store]);
  run('chain-fix-decide.ts', ['--store', store, '--overrides', overrides]);

  const fixOf = (opaque: string) => [...states().values()].find((s) => s.representative_submission_id && readSubmissionItem(s.representative_submission_id) === idMap[opaque])!;
  const submissionItems = new Map<string, string>();
  function readSubmissionItem(submissionId: string): string | undefined {
    if (submissionItems.size === 0) {
      for (const file of listFiles(path.join(store, 'submissions'), '.jsonl')) {
        for (const line of readFileSync(file, 'utf8').split('\n').filter(Boolean)) {
          const row = JSON.parse(line) as { submission_id: string; packet_item_id: string };
          submissionItems.set(row.submission_id, row.packet_item_id);
        }
      }
    }
    return submissionItems.get(submissionId);
  }

  check('tool v3.3 envelopes are accepted; the variant readings are held by the engine, the rest accepted', () => {
    for (const opaque of [HELD_CLEARABLE, HELD_BLOCKED]) assert.equal(fixOf(opaque).state, 'held');
    for (const opaque of [APPLIED_CONFIRMED, PENDING_CONFIRMED, APPLIED_CORRECTED, APPLIED_KEPT_STORED]) assert.equal(fixOf(opaque).state, 'accepted', opaque);
  });

  // The applied ones: an application line, as chain-fix-apply.ts writes after a database write. A non-clearable archive hold on one held reading.
  mkdirSync(path.join(store, 'applications'), { recursive: true });
  for (const opaque of [APPLIED_CONFIRMED, APPLIED_CORRECTED, APPLIED_KEPT_STORED]) {
    const fix = fixOf(opaque);
    appendFileSync(path.join(store, 'applications', '2026-11-22.jsonl'), `${JSON.stringify({ format: APPLICATION_FORMAT, fix_id: fix.fix_id, hadith_id: fix.hadith_id, action: 'applied', at: '2026-11-22T20:00:00Z', dataset_version_id: 'test' })}\n`);
  }
  run('chain-fix-hold.ts', ['--store', store, '--fix', fixOf(HELD_BLOCKED).fix_id, '--code', 'needs_ruling', '--detail', 'test: a point the rulings do not settle', '--by', 'test']);
  run('chain-fix-decide.ts', ['--store', store, '--overrides', overrides]);

  // Synthetic keep_stored on one applied reading (the pilot has none).
  for (const file of listFiles(path.join(batch, 'outputs', 'pass-1'), '.output.json')) {
    const output = JSON.parse(readFileSync(file, 'utf8'));
    let touched = false;
    for (const review of output.reviews) if (review.id === APPLIED_KEPT_STORED) { review.decision = 'keep_stored'; review.corrected_reading = null; touched = true; }
    if (touched) writeFileSync(file, JSON.stringify(output, null, 1));
  }
  const recorded = run('chain-review-record.ts', ['--batch', batch, '--prompt-version', '1.0.0', '--store', store, '--overrides', overrides, '--now', '2026-11-22T22:00:00Z']);
  const after = () => new Map(chosen.map((opaque) => [opaque, fixOf(opaque)]));

  check('applied + confirmation: stays applied, AI reviewed (model, run), never "verified"', () => {
    const fix = after().get(APPLIED_CONFIRMED)!;
    assert.equal(fix.state, 'accepted');
    assert.equal(fix.ai_review?.model_id, 'claude-opus-5-5');
    assert.match(fix.ai_review!.run_id, /^pilot-001-review-p1-/);
    assert.equal(fix.structure_status, 'read_by_model');
  });
  check('pending + confirmation: accepted and AI reviewed (apply_reading)', () => {
    const fix = after().get(PENDING_CONFIRMED)!;
    assert.equal(fix.state, 'accepted');
    assert.equal(fix.ai_review?.outcome, 'apply_reading');
  });
  check('applied + a correction with one run: never reverted, labelled disputed, queued for the second review', () => {
    const fix = after().get(APPLIED_CORRECTED)!;
    assert.equal(fix.state, 'accepted');
    assert.notEqual(fix.effect, null); // still in the overrides: never reverted by a correction
    assert.equal(fix.ai_disputed?.outcome, 'label_disputed');
    assert.ok(queue().ai_disputed_awaiting_second_review.some((entry: { fix_id: string }) => entry.fix_id === fix.fix_id));
    assert.ok(!queue().revert_before_apply.includes(fix.fix_id));
  });
  check('held, clearable holds only + confirmation: accepted (applied by the next apply), AI reviewed', () => {
    const fix = after().get(HELD_CLEARABLE)!;
    assert.equal(fix.state, 'accepted');
    assert.deepEqual(fix.holds, ['has_variant_group']);
    assert.equal(fix.ai_review?.outcome, 'apply_reading');
  });
  check('held with a non-clearable hold: stays held whatever the reviewer says; the review is recorded', () => {
    const fix = after().get(HELD_BLOCKED)!;
    assert.equal(fix.state, 'held');
    assert.ok(fix.holds.includes('needs_ruling'));
    assert.match(recorded, new RegExp(`${HELD_BLOCKED} ${fix.fix_id}: confirm_reading -> keep_held`));
  });
  check('keep_stored on an applied reading whose stored chain differs: set aside and listed for revert', () => {
    const fix = after().get(APPLIED_KEPT_STORED)!;
    assert.equal(fix.state, 'set_aside_by_ai');
    assert.equal(fix.effect, null);
    assert.ok(queue().revert_before_apply.includes(fix.fix_id));
  });

  // The second independent review of 80cd84 writes the same correction (a copy of the first, as a faithful second run would).
  const pass1 = JSON.parse(readFileSync(path.join(batch, 'packets', 'packet-01.json'), 'utf8'));
  let packetWithItem = pass1;
  let firstReview: unknown = null;
  for (const number of ['01', '02', '03', '04', '05', '06', '07', '08', '09']) {
    const packet = JSON.parse(readFileSync(path.join(batch, 'packets', `packet-${number}.json`), 'utf8'));
    if (packet.items.some((item: { id: string }) => item.id === APPLIED_CORRECTED)) {
      packetWithItem = packet;
      firstReview = JSON.parse(readFileSync(path.join(batch, 'outputs', 'pass-1', `packet-${number}.output.json`), 'utf8')).reviews.find((r: { id: string }) => r.id === APPLIED_CORRECTED);
    }
  }
  mkdirSync(path.join(batch, 'packets-pass-2'), { recursive: true });
  mkdirSync(path.join(batch, 'outputs', 'pass-2'), { recursive: true });
  writeFileSync(path.join(batch, 'packets-pass-2', 'packet-01.json'), JSON.stringify({ ...packetWithItem, packet_id: 'pilot-001-p2-01', pass: 2,
    items: packetWithItem.items.filter((item: { id: string }) => item.id === APPLIED_CORRECTED) }));
  writeFileSync(path.join(batch, 'outputs', 'pass-2', 'packet-01.output.json'), JSON.stringify({ format: 'shura-chain-review-output/1', specialist_id: 'chain-reviewer',
    prompt_version: '1.0.0', packet_id: 'pilot-001-p2-01', reviews: [firstReview] }));
  writeFileSync(path.join(batch, 'outputs', 'pass-2', 'RUN.txt'), 'run_id=test-review-p2-01 | packet=01 | model=claude-opus-5-5 | start=2026-11-22T22:10:00Z | end=2026-11-22T22:12:00Z | items=1\n');
  run('chain-review-record.ts', ['--batch', batch, '--prompt-version', '1.0.0', '--store', store, '--overrides', overrides, '--now', '2026-11-22T22:30:00Z']);

  check('the same correction by a second review: a new fix replaces the applied reading, which is listed for revert first', () => {
    const all = states();
    const old = [...all.values()].find((s) => s.fix_id === after().get(APPLIED_CORRECTED)!.fix_id && s.state === 'superseded')
      ?? [...all.values()].find((s) => readSubmissionItem(s.representative_submission_id) === idMap[APPLIED_CORRECTED] && s.state === 'superseded');
    assert.ok(old, 'the readers\' fix is superseded');
    const corrected = [...all.values()].find((s) => s.ai_corrected?.corrects_fix_id === old!.fix_id)!;
    assert.ok(corrected, 'a correction fix exists');
    assert.equal(corrected.state, 'accepted');
    assert.equal(corrected.runs.length, 2);
    assert.ok(queue().revert_before_apply.includes(old!.fix_id));
  });

  // A human decision wins over every AI state.
  const cleared = after().get(HELD_CLEARABLE)!;
  run('chain-fix-review.ts', ['--store', store, '--overrides', overrides, '--fix', cleared.fix_id, '--decision', 'confirmed', '--reviewer', 'Test Person', '--note', 'read against the Arabic']);
  check('a human confirmation wins: confirmed, verified_by_reviewer', () => {
    const fix = states().get(cleared.fix_id)!;
    assert.equal(fix.state, 'confirmed');
    assert.equal(fix.structure_status, 'verified_by_reviewer');
  });
} catch (error) {
  failures.push('setup');
  console.error(`FAIL setup\n     ${error instanceof Error ? error.stack : String(error)}`);
} finally {
  rmSync(work, { recursive: true, force: true });
}

if (failures.length > 0) {
  console.error(`${failures.length} failed: ${failures.join(', ')}`);
  process.exitCode = 1;
} else {
  console.log('all chain-review flows passed');
}
