/**
 * Chain-fix flows through the CLIs, on real pilot reports (datasets/hadith-data/chain-reader/pilot/reports.jsonl):
 * submit (accepted, refused, duplicate), decide (lone, agreed, disputed, held), review (many reviewers, a human rejection),
 * a v2 reading (levels, expanded by the tool), a reader's proposal filed for a person to decide, and (0021) a batch-001 reading
 * under prompt v3 re-triaged by tool v3.1: "no chain by reading" in its own envelope, refused elsewhere, and an archive hold.
 * (0023-free, 2026-11-22) a v3.2 reading with a variant remark: held without the switch; with it one chain plus a remark, replayed, and
 * taken away with the chain by a rejection. Each run uses a private store and overrides file in a temporary directory. Run: npx tsx reviews/ai/tools/__tests__/chain-fix.test.ts
 */
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { gunzipSync } from 'node:zlib';
import { buildOverrides, computeStates, readerPrompt, REPOSITORY_ROOT, type Submission } from '../chain-fix-lib';

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

const PILOT = path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'chain-reader', 'pilot', 'reports.jsonl');
const pilot = new Map(
  readFileSync(PILOT, 'utf8').split('\n').filter(Boolean).map((line) => {
    const row = JSON.parse(line) as { id: string; text: string };
    return [row.id, row as Record<string, unknown> & { id: string; text: string }];
  }),
);
const ABU_DAWUD = pilot.get('cr-0248')!; // k6:17633: «يزيد بن خالد، وقتيبة، أن الليث بن سعد، حدثهم»; the stored chains lost al-Layth
const NASAI = pilot.get('cr-0278')!; //    k6:25022: «سمعت مسروقا، والأسود، قالا نشهد على عائشة»; the stored chains stop before ʿAʾisha
const MUSLIM = pilot.get('cr-0001')!; //   k6:10943: labelled correct; «أبي سعيد، الخدري» is written with a comma inside

const work = mkdtempSync(path.join(tmpdir(), 'chain-fix-test-'));
const store = path.join(work, 'store');
const overrides = path.join(work, 'accepted_overrides.jsonl.gz');
const packetPath = path.join(work, 'packet-01.jsonl');
const reportsPath = path.join(work, 'reports.jsonl');
const subjects = [ABU_DAWUD, NASAI, MUSLIM];
writeFileSync(packetPath, subjects.map((row) => JSON.stringify({ id: row.id, text: row.text })).join('\n') + '\n', 'utf8');
writeFileSync(reportsPath, subjects.map((row) => JSON.stringify(row)).join('\n') + '\n', 'utf8');
const prompt = readerPrompt();

/** A link located in the text (the n-th occurrence of the surface at or after `from`). */
function link(text: string, surface: string, kind = 'narrator', from = 0) {
  const start = text.indexOf(surface, from);
  if (start < 0) throw new Error(`fixture: ${surface} not in text`);
  return { surface, start, end: start + surface.length, kind };
}
function routes(text: string, names: string[][], tailFrom: number | null) {
  return names.map((route) => {
    let cursor = 0;
    return {
      links: route.map((name) => {
        const found = link(text, name, 'narrator', cursor);
        cursor = found.end;
        return found;
      }),
      shared_tail_from: tailFrom,
    };
  });
}
const abuDawudFixed = (order: 'as_written' | 'reversed' = 'as_written') => {
  const read = routes(ABU_DAWUD.text, [
    ['يزيد بن خالد', 'الليث بن سعد', 'بكير', 'سليمان بن يسار', 'أبي هريرة'],
    ['قتيبة', 'الليث بن سعد', 'بكير', 'سليمان بن يسار', 'أبي هريرة'],
  ], 1);
  return { id: ABU_DAWUD.id, routes: order === 'reversed' ? read.reverse() : read, matn_start: ABU_DAWUD.text.indexOf('بعثنا'), notes: [] };
};
const nasaiFixed = () => ({
  id: NASAI.id,
  routes: routes(NASAI.text, [
    ['إسماعيل بن مسعود', 'خالد بن الحارث', 'شعبة', 'أبي إسحاق', 'مسروقا', 'عائشة'],
    ['إسماعيل بن مسعود', 'خالد بن الحارث', 'شعبة', 'أبي إسحاق', 'الأسود', 'عائشة'],
  ], null),
  matn_start: NASAI.text.indexOf('كان رسول'),
  notes: [],
});
// The two Nasa'i routes share their first four links, written once: the same offsets in both.
const routesHead = routes(NASAI.text, [['إسماعيل بن مسعود', 'خالد بن الحارث', 'شعبة', 'أبي إسحاق']], null)[0].links;
const nasaiAsStored = () => ({
  id: NASAI.id,
  routes: routes(NASAI.text, [['إسماعيل بن مسعود', 'خالد بن الحارث', 'شعبة', 'أبي إسحاق', 'مسروقا']], null).concat(
    [{ links: [...routesHead, link(NASAI.text, 'الأسود')], shared_tail_from: null }],
  ),
  matn_start: NASAI.text.indexOf('قالا'),
  notes: [],
});
const muslimAsStored = () => ({
  id: MUSLIM.id,
  routes: routes(MUSLIM.text, [
    ['عبيد الله بن عمر القواريري', 'سفيان بن عيينة', 'ابن أبي نجيح', 'مجاهد', 'قزعة', 'أبي سعيد، الخدري'],
    ['أحمد بن عبدة', 'سفيان بن عيينة', 'ابن أبي نجيح', 'مجاهد', 'قزعة', 'أبي سعيد، الخدري'],
  ], 1),
  matn_start: MUSLIM.text.indexOf('ذكر العزل'),
  notes: [],
});

let envelopeCount = 0;
function envelope(runId: string, fixes: object[], overridesOf: Record<string, unknown> = {}): string {
  const file = path.join(work, `envelope-${(envelopeCount += 1)}.json`);
  const run = { model_id: 'claude-haiku-4-5', provider_runtime: 'Claude Code subagent, fresh context', run_id: runId, started_at: '2026-11-22T15:00:00Z', finished_at: '2026-11-22T15:02:00Z', prompt_sha256: prompt.sha256, view: 'text_only', ...overridesOf };
  writeFileSync(file, JSON.stringify({ format: 'shura-chain-fix-envelope/1', run, packet: packetPath, fixes }), 'utf8');
  return file;
}
const fix = (output: object, quote: string) => ({ output, reason: 'Read from the Arabic as written.', evidence: [{ quote }], external_citation: null });

function cli(tool: string, args: string[]) {
  const result = spawnSync(process.execPath, ['--import', 'tsx', path.join(REPOSITORY_ROOT, 'reviews', 'ai', 'tools', `${tool}.ts`), ...args], { cwd: REPOSITORY_ROOT, encoding: 'utf8' });
  return { status: result.status, out: result.stdout, err: result.stderr };
}
const submit = (file: string, extra: string[] = []) => cli('chain-fix-submit', ['--envelope', file, '--reports', reportsPath, '--store', store, ...extra]);
const decide = () => cli('chain-fix-decide', ['--store', store, '--overrides', overrides]);
const review = (args: string[]) => cli('chain-fix-review', [...args, '--store', store, '--overrides', overrides]);
const submissionsOnDisk = (): Submission[] => {
  const directory = path.join(store, 'submissions');
  if (!existsSync(directory)) return [];
  return readdirSync(directory).filter((n) => n.endsWith('.jsonl')).flatMap((n) => readFileSync(path.join(directory, n), 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l) as Submission));
};
const overrideRows = () => (existsSync(overrides) ? gunzipSync(readFileSync(overrides)).toString('utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l) as Record<string, unknown>) : []);
const stateOf = (fixId: string) => (JSON.parse(readFileSync(path.join(store, 'state.json'), 'utf8')) as { fixes: { fix_id: string; state: string; structure_status: string | null; reviewers: string[] }[] }).fixes.find((f) => f.fix_id === fixId)!;

let abuDawudFixId = '';

check('every tool answers --help', () => {
  for (const tool of ['chain-fix-submit', 'chain-fix-decide', 'chain-fix-review', 'chain-fix-status']) assert.equal(cli(tool, ['--help']).status, 0, tool);
});

check('a valid fix is recorded with its provenance, the computed fix kinds and the identity carry rule', () => {
  const result = submit(envelope('run-a', [fix(abuDawudFixed(), 'أن الليث بن سعد، حدثهم عن بكير')]));
  assert.equal(result.status, 0, result.err);
  const [record] = submissionsOnDisk();
  abuDawudFixId = record.fix_id;
  assert.equal(record.hadith_id, 'hadith:k6:17633');
  assert.equal(record.model_id, 'claude-haiku-4-5');
  assert.equal(record.prompt_sha256, prompt.sha256);
  assert.equal(record.orchestrator_run_id, 'run-a');
  assert.equal(record.label, 'AI reviewed');
  assert.equal(record.arabic_sha256.length, 64);
  assert.deepEqual(record.fix_kinds, ['link_added', 'shared_tail_attached']);
  assert.deepEqual(record.computed_evidence.map((e) => e.quote), ['الليث بن سعد', 'الليث بن سعد']);
  const [first] = record.planned.chains;
  const byName = new Map(first.mentions.map((m) => [m.surface_ar, m]));
  assert.equal(byName.get('الليث بن سعد')!.kept_mention_id, null, 'a new name keeps nothing');
  assert.equal(byName.get('يزيد بن خالد')!.kept_mention_id, 'mention:k6:17633:0000:0000', 'an unchanged name keeps its stored mention');
  assert.equal(byName.get('يزيد بن خالد')!.carry_identity, false, 'its teacher changed, so its identity is not carried');
  assert.equal(byName.get('سليمان بن يسار')!.carry_identity, true, 'name and both neighbours unchanged: identity carried');
});

check('a surface that is not an exact substring is refused with the validator’s own words, nothing recorded', () => {
  const output = abuDawudFixed();
  output.routes[0].links[1] = { ...output.routes[0].links[1], surface: 'الليث بن سعد المصري' };
  const result = submit(envelope('run-bad', [fix(output, 'أن الليث بن سعد')]));
  assert.equal(result.status, 1);
  assert.match(result.err, /surface_mismatch: r0l1 'الليث بن سعد المصري'/);
  assert.match(result.err, /nothing recorded/);
  assert.ok(!submissionsOnDisk().some((s) => s.orchestrator_run_id === 'run-bad'));
});

check('an evidence quote that is not in the text is refused', () => {
  const result = submit(envelope('run-bad', [fix(abuDawudFixed(), 'أن الليث بن سعد المصري حدثهم')]));
  assert.equal(result.status, 1);
  assert.match(result.err, /evidence: quote 0 is not in the text \(letters must be exact\)/);
});

check('a reading of an older text (stale hash) is refused', () => {
  const changed = path.join(work, 'reports-changed.jsonl');
  writeFileSync(changed, subjects.map((row) => JSON.stringify(row.id === ABU_DAWUD.id ? { ...row, text: `${row.text} ` } : row)).join('\n') + '\n', 'utf8');
  const result = cli('chain-fix-submit', ['--envelope', envelope('run-c', [fix(abuDawudFixed(), 'الليث بن سعد')]), '--reports', changed, '--store', store]);
  assert.equal(result.status, 1);
  assert.match(result.err, /stale text/);
});

check('a reading made under another prompt hash is refused', () => {
  const result = submit(envelope('run-c', [fix(abuDawudFixed(), 'الليث بن سعد')], { prompt_sha256: '0'.repeat(64) }));
  assert.equal(result.status, 1);
  assert.match(result.err, /not a registered reader prompt/);
});

check('a reader who saw the stored chain must quote around every change', () => {
  const result = submit(envelope('run-fixer', [fix(abuDawudFixed(), 'أبي هريرة')], { view: 'text_and_stored_chain' }));
  assert.equal(result.status, 1);
  assert.match(result.err, /no quote contains the added link 'الليث بن سعد'/);
});

check('the same reading from the same run is a duplicate: reported, not recorded twice', () => {
  const result = submit(envelope('run-a', [fix(abuDawudFixed(), 'أن الليث بن سعد، حدثهم عن بكير')]));
  assert.equal(result.status, 0, result.err);
  assert.match(result.out, /dup /);
  assert.equal(submissionsOnDisk().length, 1);
});

check('one reader alone does not change the overrides', () => {
  assert.equal(decide().status, 0);
  assert.equal(stateOf(abuDawudFixId).state, 'submitted');
  assert.ok(!overrideRows().some((row) => row.hadith_id === 'hadith:k6:17633'));
});

check('a second independent reader with the same routes (in another order) makes an accepted override', () => {
  assert.equal(submit(envelope('run-b', [fix(abuDawudFixed('reversed'), 'وقتيبة، أن الليث بن سعد')])).status, 0);
  const decided = decide();
  assert.equal(decided.status, 0, decided.err);
  assert.equal(stateOf(abuDawudFixId).state, 'accepted');
  const row = overrideRows().find((r) => r.hadith_id === 'hadith:k6:17633')!;
  assert.equal(row.effect, 'replace_routes');
  assert.equal(row.structure_status, 'read_by_model');
  assert.equal(row.fix_id, abuDawudFixId);
  assert.equal((row.planned as { chains: unknown[] }).chains.length, 2);
  assert.equal(decide().out.includes('->'), false, 'a second decide changes nothing');
});

check('readers who disagree make a dispute and no override', () => {
  assert.equal(submit(envelope('run-a', [fix(nasaiFixed(), 'قالا نشهد على عائشة')])).status, 0);
  assert.equal(submit(envelope('run-b', [fix(nasaiAsStored(), 'سمعت مسروقا، والأسود')])).status, 0);
  decide();
  const nasai = submissionsOnDisk().filter((s) => s.hadith_id === 'hadith:k6:25022');
  assert.equal(nasai.length, 2);
  assert.deepEqual(nasai.map((s) => stateOf(s.fix_id).state), ['disputed', 'disputed']);
  assert.ok(nasai.some((s) => s.fix_kinds.includes('no_change')) && nasai.some((s) => s.fix_kinds.includes('link_added')));
  assert.ok(!overrideRows().some((row) => row.hadith_id === 'hadith:k6:25022'));
});

check('a lone reading that leaves the stored chain unchanged is recorded beside it, nothing replaced', () => {
  assert.equal(submit(envelope('run-a', [fix(muslimAsStored(), 'عن أبي سعيد، الخدري')])).status, 0);
  decide();
  const [muslim] = submissionsOnDisk().filter((s) => s.hadith_id === 'hadith:k6:10943');
  assert.deepEqual(muslim.fix_kinds, ['no_change']);
  const row = overrideRows().find((r) => r.hadith_id === 'hadith:k6:10943')!;
  assert.equal(row.effect, 'annotate');
  assert.equal(row.planned, null);
});

check('many reviewers on one fix are all kept; a human confirmation is the only "verified"', () => {
  const ai = review(['--fix', abuDawudFixId, '--decision', 'confirmed', '--reviewer', 'chain-reader-audit', '--note', 'Read the opening again.', '--ai', '--model', 'claude-opus-5-5', '--prompt', 'datasets/hadith-data/chain-reader/prompt.md', '--prompt-sha256', prompt.sha256]);
  assert.equal(ai.status, 0, ai.err);
  assert.equal(stateOf(abuDawudFixId).state, 'accepted', 'an AI review never moves a fix');
  assert.equal(review(['--fix', abuDawudFixId, '--decision', 'confirmed', '--reviewer', 'Reviewer One', '--note', '«أن الليث بن سعد حدثهم» names al-Layth between both shaykhs and Bukayr.', '--citation-edition', 'Sunan Abi Dawud, ed. al-Arnaʾut, 4:300', '--citation-quote', 'أن الليث بن سعد حدثهم']).status, 0);
  assert.equal(review(['--fix', abuDawudFixId, '--decision', 'confirmed', '--reviewer', 'Reviewer Two', '--note', 'Agree.']).status, 0);
  const state = stateOf(abuDawudFixId);
  assert.equal(state.state, 'confirmed');
  assert.equal(state.structure_status, 'verified_by_reviewer');
  assert.deepEqual(state.reviewers, ['ai:chain-reader-audit', 'human:Reviewer One', 'human:Reviewer Two']);
  assert.equal(overrideRows().find((r) => r.hadith_id === 'hadith:k6:17633')!.structure_status, 'verified_by_reviewer');
});

check('a review without a named reviewer, or an AI review without its model and prompt, is refused', () => {
  assert.match(review(['--fix', abuDawudFixId, '--decision', 'rejected', '--note', 'No.']).err, /--reviewer/);
  assert.match(review(['--fix', abuDawudFixId, '--decision', 'rejected', '--reviewer', 'x', '--note', 'No.', '--ai']).err, /--ai needs --model/);
});

check('a human rejection removes the fix from the overrides and deletes nothing', () => {
  const before = submissionsOnDisk().length;
  const result = review(['--fix', abuDawudFixId, '--decision', 'rejected', '--reviewer', 'Reviewer Three', '--note', 'Checked another manuscript reading; holding back.']);
  assert.equal(result.status, 0, result.err);
  assert.equal(stateOf(abuDawudFixId).state, 'rejected');
  assert.ok(!overrideRows().some((row) => row.hadith_id === 'hadith:k6:17633'));
  assert.equal(submissionsOnDisk().length, before);
  const reviews = readdirSync(path.join(store, 'reviews')).flatMap((n) => readFileSync(path.join(store, 'reviews', n), 'utf8').split('\n').filter(Boolean));
  assert.equal(reviews.length, 4);
  const transitions = readFileSync(path.join(store, 'transitions.jsonl'), 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l) as { fix_id: string; to: string });
  assert.deepEqual(transitions.filter((t) => t.fix_id === abuDawudFixId).map((t) => t.to), ['submitted', 'accepted', 'confirmed', 'rejected']);
});

// cr-0058 (k6:10997, Sahih Muslim): a real v2 output (levels, no offsets) whose chain has two «جميعا»: two readers agree,
// and the tool still holds it (HOLDS.md nested_jami); its finding beyond the chain is filed as a proposal.
const V2_ID = 'cr-0058';
const v2Directory = path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'chain-reader', 'context');
const v2Item = readdirSync(path.join(v2Directory, 'pilot-v2', 'packets')).filter((n) => /^packet-\d+\.jsonl$/.test(n))
  .flatMap((n) => readFileSync(path.join(v2Directory, 'pilot-v2', 'packets', n), 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l) as { id: string; text: string }))
  .find((row) => row.id === V2_ID)!;
const v2Output = JSON.parse(readFileSync(path.join(v2Directory, 'outputs-v2', 'run-a', `${V2_ID}.json`), 'utf8')) as object;
const v2Packet = path.join(work, 'packet-v2.jsonl');
const v2Reports = path.join(work, 'reports-v2.jsonl');
writeFileSync(v2Packet, `${JSON.stringify(v2Item)}\n`, 'utf8');
writeFileSync(v2Reports, `${JSON.stringify(pilot.get(V2_ID))}\n`, 'utf8');
const v2Envelope = (runId: string) => {
  const file = path.join(work, `envelope-${runId}.json`);
  const run = { model_id: 'claude-haiku-5-5', provider_runtime: 'Claude Code subagent, fresh context', run_id: runId, started_at: '2026-11-22T15:00:00Z',
    finished_at: '2026-11-22T15:02:00Z', prompt_sha256: readerPrompt('v2').sha256, view: 'text_only', reader_format: 'v2' };
  writeFileSync(file, JSON.stringify({ format: 'shura-chain-fix-envelope/1', run, packet: v2Packet, fixes: [fix(v2Output, v2Item.text.slice(0, 12))] }), 'utf8');
  return file;
};
let proposalId = '';

check('a v2 reading is expanded and recorded; two agreeing readers of a held reading make no override', () => {
  for (const runId of ['run-v2a', 'run-v2b']) {
    const result = cli('chain-fix-submit', ['--envelope', v2Envelope(runId), '--reports', v2Reports, '--store', store]);
    assert.equal(result.status, 0, result.err);
    assert.match(result.out, /held: nested_jami/);
  }
  decide();
  const [submission] = submissionsOnDisk().filter((s) => s.hadith_id === 'hadith:k6:10997');
  assert.equal(submission.reader_format, 'v2');
  assert.ok(submission.reading.routes.every((route) => route.links.every((l) => l.start !== null)), 'the derived compiler head is never a planned link');
  const state = stateOf(submission.fix_id) as ReturnType<typeof stateOf> & { holds: string[] };
  assert.equal(state.state, 'held');
  assert.deepEqual(state.holds, ['nested_jami']);
  assert.ok(!overrideRows().some((row) => row.hadith_id === 'hadith:k6:10997'));
  const queue = JSON.parse(readFileSync(path.join(store, 'queue.json'), 'utf8')) as { held: { fix_id: string }[] };
  assert.deepEqual(queue.held.map((entry) => entry.fix_id), [submission.fix_id]);
});

check("a reader's finding beyond the chain is filed as a proposal and only a person decides it", () => {
  const listed = cli('chain-fix-status', ['--store', store, '--proposals']);
  assert.equal(listed.status, 0, listed.err);
  const line = listed.out.split('\n').find((l) => l.includes('hadith:k6:10997') && l.startsWith('proposed'))!;
  assert.ok(line, listed.out);
  assert.match(line, /chain_differs_from_source \(chain\).*read by claude-haiku-5-5/);
  proposalId = /(reader-proposal:[0-9a-f]{24})/.exec(line)![1];
  assert.match(review(['--proposal', proposalId, '--decision', 'accepted', '--reviewer', 'x', '--note', 'n', '--ai']).err, /decided by a person/);
  const decided = review(['--proposal', proposalId, '--decision', 'rejected', '--reviewer', 'Reviewer One', '--note', 'The source index lists a different route; the text is as stored.']);
  assert.equal(decided.status, 0, decided.err);
  assert.match(decided.out, /rejected_by_reviewer/);
});

check('status counts by state, work and tradition', () => {
  const result = cli('chain-fix-status', ['--store', store, '--awaiting']);
  assert.equal(result.status, 0, result.err);
  assert.match(result.out, /^all\s+accepted 1, disputed 2, held 1, rejected 1/m);
  assert.match(result.out, /work:sunni:nasai\s+disputed 2/);
});

// Reader v3: envelopes written by chain-reader/v3/to_submission.py from the pilot's two passes (outputs-v2 run-a / run-b).
const v3Out = path.join(work, 'v3-submissions');
spawnSync('python', ['-B', '-X', 'utf8', 'v3/to_submission.py', '--packets', 'context/pilot-v2/packets', '--reports', 'pilot/reports.jsonl',
  '--pass-a', 'context/outputs-v2/run-a', '--pass-b', 'context/outputs-v2/run-b', '--out', v3Out], { cwd: path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'chain-reader'), encoding: 'utf8' });
const v3Envelope = path.join(v3Out, 'packet-12.envelope.json');
const v3Store = path.join(work, 'store-v3');
const v3Overrides = path.join(work, 'v3-overrides.jsonl.gz');

check('a v3 envelope (text and context, two passes) is recorded as two blind runs and the agreed reading is accepted', () => {
  const result = cli('chain-fix-submit', ['--envelope', v3Envelope, '--reports', PILOT, '--store', v3Store]);
  assert.equal(result.status, 0, result.err);
  const submissions = readdirSync(path.join(v3Store, 'submissions')).flatMap((n) => readFileSync(path.join(v3Store, 'submissions', n), 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l) as Submission));
  assert.equal(new Set(submissions.map((s) => s.orchestrator_run_id)).size, 2, 'pass A and pass B are two runs');
  assert.ok(submissions.every((s) => s.view === 'text_and_context' && s.reader_format === 'v3' && s.prompt_path.endsWith('v3/prompt-v3.md')));
  assert.ok(submissions.some((s) => (s.derived_links ?? []).some((link) => link.kind === 'compiler_head' && link.origin === 'work')),
    'the compiler head is kept as a derived link with its origin, never a planned row');
  assert.equal(cli('chain-fix-decide', ['--store', v3Store, '--overrides', v3Overrides]).status, 0);
  const states = (JSON.parse(readFileSync(path.join(v3Store, 'state.json'), 'utf8')) as { fixes: { state: string; text_only_runs: number; holds: string[] }[] }).fixes;
  // A pilot report whose stored chain is rule-checked waits for the owner (hold stored_chain_checked_by_rule); every other is accepted.
  assert.ok(states.some((state) => state.state === 'accepted'), JSON.stringify(states.map((x) => x.state)));
  assert.ok(states.every((state) => state.text_only_runs === 2 && (state.state === 'accepted'
    || (state.state === 'held' && state.holds.join() === 'stored_chain_checked_by_rule'))), JSON.stringify(states.map((x) => [x.state, x.holds])));
});

// v3.1 (0021): batch 001's «العائد في هبته» (b1-2c405e) read under prompt v3, both passes empty, re-triaged by tool v3.1.
const batchDirectory = path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'chain-reader', 'v3', 'batch-001');
const noChainItem = readdirSync(path.join(batchDirectory, 'packets')).filter((n) => /^packet-\d+\.jsonl$/.test(n))
  .flatMap((n) => readFileSync(path.join(batchDirectory, 'packets', n), 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l) as { id: string; text: string }))
  .find((row) => row.id === 'b1-2c405e')!;
const noChainOutput = JSON.parse(readFileSync(path.join(batchDirectory, 'outputs', 'pass-a', 'b1-2c405e.json'), 'utf8')) as object;
const noChainPacket = path.join(work, 'packet-nochain.jsonl');
const noChainReports = path.join(work, 'reports-nochain.jsonl');
writeFileSync(noChainPacket, `${JSON.stringify(noChainItem)}\n`, 'utf8');
writeFileSync(noChainReports, `${JSON.stringify({ id: 'b1-2c405e', hadith_id: 'hadith:test:nochain', tradition: 'imami', work: 'man-la-yahduruhu-al-faqih',
  text: noChainItem.text, text_layout: 'full_text', stored_chains: [{ chain_id: 'chain:test:nochain:0000', branch: 0, structure_status: 'uncertain', surfaces: ['العائد في هبته'] }] })}\n`, 'utf8');
const v31Store = path.join(work, 'store-v31');
const v31Overrides = path.join(work, 'v31-overrides.jsonl.gz');
const v31Envelope = (format: string, runOverrides: Record<string, unknown> = {}) => {
  const file = path.join(work, `envelope-v31-${format.length}-${Object.keys(runOverrides).length}.json`);
  const run = { model_id: 'claude-haiku-5-5', provider_runtime: 'Claude Code subagent, fresh context', run_id: 'b1-a-test', started_at: '2026-11-22T16:20:00Z',
    finished_at: '2026-11-22T16:27:00Z', prompt_sha256: readerPrompt('v3').sha256, view: 'text_and_context', tool_version: 'v3_1',
    second_reader: { model_id: 'claude-haiku-5-5', run_id: 'b1-b-test', started_at: '2026-11-22T16:30:00Z', finished_at: '2026-11-22T16:37:00Z' }, ...runOverrides };
  const fixEntry = { output: noChainOutput, disposition: 'no_chain_by_reading', reason: 'Two readers read no isnad.', evidence: [{ quote: noChainItem.text.slice(0, 20) }],
    external_citation: null, reader_output_v3: noChainOutput };
  writeFileSync(file, JSON.stringify({ format, run, packet: noChainPacket, fixes: [fixEntry] }), 'utf8');
  return file;
};

check('"no chain by reading": refused in a chain envelope, recorded from its own envelope with the prompt the reader ran and the tool that held it', () => {
  const refused = cli('chain-fix-submit', ['--envelope', v31Envelope('shura-chain-fix-envelope/1'), '--reports', noChainReports, '--store', v31Store]);
  assert.equal(refused.status, 1);
  assert.match(refused.err, /has no route; submit it in a shura-chain-no-chain-envelope\/1/);
  const wrongTool = cli('chain-fix-submit', ['--envelope', v31Envelope('shura-chain-no-chain-envelope/1', { prompt_sha256: readerPrompt('v3_1').sha256, tool_version: 'v3' }), '--reports', noChainReports, '--store', v31Store]);
  assert.match(wrongTool.err, /run.tool_version: v3 cannot read a v3_1 reading/);
  const recorded = cli('chain-fix-submit', ['--envelope', v31Envelope('shura-chain-no-chain-envelope/1'), '--reports', noChainReports, '--store', v31Store]);
  assert.equal(recorded.status, 0, recorded.err);
  const submissions = readdirSync(path.join(v31Store, 'submissions')).flatMap((n) => readFileSync(path.join(v31Store, 'submissions', n), 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l) as Submission));
  assert.equal(submissions.length, 2);
  assert.ok(submissions.every((x) => x.disposition === 'no_chain_by_reading' && x.tool_version === 'v3_1' && x.prompt_path.endsWith('v3/prompt-v3.md') && x.planned.chains.length === 0));
  assert.equal(cli('chain-fix-decide', ['--store', v31Store, '--overrides', v31Overrides]).status, 0);
  const [row] = gunzipSync(readFileSync(v31Overrides)).toString('utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l) as Record<string, unknown>);
  assert.deepEqual([row.effect, row.disposition, row.structure_status, (row.planned as { chains: unknown[] }).chains.length], ['replace_routes', 'no_chain_by_reading', 'read_by_model', 0]);
  assert.equal((row.read_by as { tool_version: string }).tool_version, 'v3_1');
});

check('an archive hold keeps an agreed reading out of the overrides', () => {
  const [fix] = (JSON.parse(readFileSync(path.join(v31Store, 'state.json'), 'utf8')) as { fixes: { fix_id: string }[] }).fixes;
  const held = cli('chain-fix-hold', ['--store', v31Store, '--fix', fix.fix_id, '--code', 'cited_by_later_report', '--detail', 'a later report repeats this chain', '--by', 'test']);
  assert.equal(held.status, 0, held.err);
  assert.equal(cli('chain-fix-decide', ['--store', v31Store, '--overrides', v31Overrides]).status, 0);
  const [state] = (JSON.parse(readFileSync(path.join(v31Store, 'state.json'), 'utf8')) as { fixes: { state: string; holds: string[] }[] }).fixes;
  assert.deepEqual([state.state, state.holds], ['held', ['cited_by_later_report']]);
  assert.equal(gunzipSync(readFileSync(v31Overrides)).toString('utf8'), '');
});

// v3.2 (variant remarks): tranche 01's «بمثل حديث سليمان بن بلال» (t01-30fa50): one route and a remark about another version. Both passes
// write the route and the remark; the envelope comes from to_submission_v3_2.py, with and without --variant-notes-supported.
const readerDirectory = path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'chain-reader');
const variantItem = readFileSync(path.join(readerDirectory, 'v3_2', 'examples', 'example-packets.jsonl'), 'utf8').split('\n').filter(Boolean)
  .map((l) => JSON.parse(l) as { id: string; text: string; context: unknown }).find((row) => row.id === 't01-30fa50')!;
const variantReader = (withRemark: boolean) => ({
  id: 't01-30fa50', status: 'read', shared_tail: null, needs_ruling: false, notes: [], fixes: [],
  groups: [
    { levels: ['محمد بن المثنى', 'عبد الوهاب', 'يحيى بن سعيد', 'عبد الله بن عامر بن ربيعة', 'عائشة'].map((surface) => [{ surface, kind: 'narrator' }]) },
    ...(withRemark ? [{ variant: true, levels: [[{ surface: 'سليمان بن بلال', kind: 'narrator' }]] }] : []),
  ],
});
const variantDirectory = path.join(work, 'variant');
const variantRoot = (...parts: string[]) => path.join(variantDirectory, ...parts);
mkdirSync(variantRoot('packets'), { recursive: true });
for (const pass of ['a', 'b']) {
  mkdirSync(variantRoot('outputs', `pass-${pass}`), { recursive: true });
  writeFileSync(variantRoot('outputs', `pass-${pass}`, 't01-30fa50.json'), JSON.stringify(variantReader(true)), 'utf8');
  writeFileSync(variantRoot('outputs', `pass-${pass}`, 'RUN.txt'),
    `run_id=vt-${pass}-001 | packets=001 | model=claude-haiku-5-5 | start=2026-11-22T18:0${pass === 'a' ? 2 : 7}:00Z | end=2026-11-22T18:0${pass === 'a' ? 5 : 9}:00Z | files=1\n`, 'utf8');
}
writeFileSync(variantRoot('packets', 'packet-001.jsonl'), `${JSON.stringify({ id: variantItem.id, text: variantItem.text, context: variantItem.context })}\n`, 'utf8');
const variantReports = variantRoot('reports.jsonl');
writeFileSync(variantReports, `${JSON.stringify({ id: 't01-30fa50', hadith_id: 'hadith:test:variant', previous_reports: [], tradition: 'sunni', work: 'muslim', text: variantItem.text,
  text_layout: 'full_text', stored_chains: [{ chain_id: 'chain:test:variant:0000', branch: 0, structure_status: 'uncertain',
    surfaces: ['حدثناه محمد بن المثنى', 'عبد الوهاب', 'يحيى بن سعيد', 'عبد الله بن عامر بن ربيعة'] }] })}\n`, 'utf8');
const toSubmission = (out: string, extra: string[] = []) => spawnSync('python', ['-B', '-X', 'utf8', 'v3_2/to_submission_v3_2.py', '--packets', variantRoot('packets'), '--reports', variantReports,
  '--pass-a', variantRoot('outputs', 'pass-a'), '--pass-b', variantRoot('outputs', 'pass-b'), '--out', variantRoot(out), '--batch', 'vt', ...extra], { cwd: readerDirectory, encoding: 'utf8' });
const variantStore = (name: string) => path.join(work, name);
const variantSubmit = (envelopePath: string, storeDirectory: string, extra: string[] = []) =>
  cli('chain-fix-submit', ['--envelope', envelopePath, '--reports', variantReports, '--store', storeDirectory, ...extra]);
const decideVariant = (storeDirectory: string, overridesFile: string) => cli('chain-fix-decide', ['--store', storeDirectory, '--overrides', overridesFile]);
const rowsOf = (file: string) => gunzipSync(readFileSync(file)).toString('utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l) as Record<string, unknown> & { planned: { chains: { mentions: { surface_ar: string }[] }[] } | null; variant_remarks?: { quote: string; surfaces: string[][]; passes: string[]; by: { pass: string; run_id: string }[] }[] });

check('a reading with a variant remark is held without the switch; with it, it is one chain plus a remark, applied and replayed, and a rejection takes both away', () => {
  // Without the switch the reader tool holds it: nothing reaches an envelope.
  assert.equal(toSubmission('held').status, 0);
  assert.match(readFileSync(variantRoot('held', 'not_submitted.tsv'), 'utf8'), /t01-30fa50\theld: has_variant_group/);
  assert.ok(!existsSync(variantRoot('held', 'packet-001.envelope.json')));
  // With it the envelope carries pass B's unchanged output, from which the pipeline computes the union of the two passes' remarks.
  assert.equal(toSubmission('open', ['--variant-notes-supported']).status, 0);
  const envelopePath = variantRoot('open', 'packet-001.envelope.json');
  const [entry] = (JSON.parse(readFileSync(envelopePath, 'utf8')) as { fixes: { reader_output_v3_b: { id: string } }[] }).fixes;
  assert.equal(entry.reader_output_v3_b.id, 't01-30fa50');

  // The submit tool's own switch: without it the same envelope is recorded held (has_variant_group); decide queues it and applies nothing.
  const closedStore = variantStore('store-variant-closed');
  const closedOverrides = path.join(work, 'variant-closed.jsonl.gz');
  assert.equal(variantSubmit(envelopePath, closedStore).status, 0);
  assert.equal(decideVariant(closedStore, closedOverrides).status, 0);
  assert.equal((JSON.parse(readFileSync(path.join(closedStore, 'state.json'), 'utf8')) as { fixes: { state: string; holds: string[] }[] }).fixes[0].holds.join(), 'has_variant_group');
  assert.equal(rowsOf(closedOverrides).length, 0);

  const openStore = variantStore('store-variant-open');
  const openOverrides = path.join(work, 'variant-open.jsonl.gz');
  const recorded = variantSubmit(envelopePath, openStore, ['--variant-notes-supported']);
  assert.equal(recorded.status, 0, recorded.err);
  assert.equal(decideVariant(openStore, openOverrides).status, 0);
  const [row] = rowsOf(openOverrides);
  assert.deepEqual([row.effect, row.state, row.planned!.chains.length], ['replace_routes', 'accepted', 1], 'one chain');
  assert.deepEqual(row.planned!.chains[0].mentions.map((m) => m.surface_ar).includes('سليمان بن بلال'), false, 'the remark is never a link');
  const [remark] = row.variant_remarks!;
  assert.equal(row.variant_remarks!.length, 1);
  assert.deepEqual([remark.surfaces, remark.passes, remark.by.map((b) => b.run_id)], [[['سليمان بن بلال']], ['a', 'b'], ['vt-a-001', 'vt-b-001']]);
  assert.ok(remark.quote.includes('بمثل حديث سليمان بن بلال'));
  // The projection's replay reads the same remark and the same single chain from the overrides file.
  const replayed = spawnSync('python', ['-I', '-X', 'utf8', '-c',
    'import sys, json; sys.path.insert(0, sys.argv[1]); import replay; rows = replay.load_overrides(__import__("pathlib").Path(sys.argv[2])); '
    + 'row = rows["hadith:test:variant"]; print(json.dumps({"chains": len(row["planned"]["chains"]), "remarks": replay.variant_remarks_of(row)}, ensure_ascii=False))',
    path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'chain-fixes'), openOverrides], { encoding: 'utf8' });
  assert.equal(replayed.status, 0, replayed.stderr);
  const replay = JSON.parse(replayed.stdout) as { chains: number; remarks: { quote: string }[] };
  assert.deepEqual([replay.chains, replay.remarks.map((r) => r.quote)], [1, [remark.quote]]);
  // A human rejection leaves both: the override (chain and remark) goes in the same call.
  const [state] = (JSON.parse(readFileSync(path.join(openStore, 'state.json'), 'utf8')) as { fixes: { fix_id: string }[] }).fixes;
  const rejected = cli('chain-fix-review', ['--fix', state.fix_id, '--decision', 'rejected', '--reviewer', 'Reviewer One', '--note', 'The remark names the wrong version.', '--store', openStore, '--overrides', openOverrides]);
  assert.equal(rejected.status, 0, rejected.err);
  assert.equal(rowsOf(openOverrides).length, 0);
});

check('a later no_change reader run with the same fix_id as an AI correction emits one FixState and one override', () => {
  const baseSub = (overridesSub: Partial<Submission>): Submission => ({
    format: 'shura-chain-fix-submission/1',
    submission_id: 'chain-fix-submission:test-1',
    fix_id: 'chain-fix:deadbeef0000000000000001',
    hadith_id: 'hadith:test:dedup',
    record_id: 'test:dedup',
    tradition: 'sunni',
    source_work_id: 'sunni:bukhari',
    arabic_sha256: 'a'.repeat(64),
    reader_text_sha256: 'b'.repeat(64),
    text_layout: 'full_text',
    text_checked_against: 'database',
    routes_key: 'r0',
    fix_kinds: ['link_added'],
    comparison: {},
    base: { read_from: 'production@2026-11-22T18:00:00Z', chain_sha256: 'base-old', chains: [{ chain_id: 'c0', branch: 0, structure_status: 'uncertain', mentions: [] }] },
    reading: { routes: [], matn_start: 0, notes: [], offsets_repaired: false },
    planned: { chains: [{ id: 'c0', branch: 0, length: 1, extraction_method: 'chain_fix_reader', suspension: null, mentions: [] }] },
    disposition: null,
    reason: 'test',
    evidence: [],
    computed_evidence: [],
    external_citation: null,
    holds: [],
    view: 'text_and_stored_chain',
    review_kind: 'specialist',
    label: 'AI reviewed',
    specialist_id: 'chain-reviewer',
    specialist_version: '1.1.0',
    prompt_path: 'p',
    prompt_version: '1.0.0',
    prompt_sha256: 'c'.repeat(64),
    model_id: 'claude-opus-5-5',
    provider_runtime: 'test',
    orchestrator_run_id: 'review-1',
    packet_path: 'p.json',
    packet_sha256: 'd'.repeat(64),
    packet_item_id: 'item-1',
    started_at: '2026-11-23T02:00:00Z',
    finished_at: '2026-11-23T02:01:00Z',
    submitted_at: '2026-11-23T02:20:00Z',
    corrects_fix_id: 'chain-fix:old000000000000000000001',
    ...overridesSub,
  });
  const submissions: Submission[] = [
    baseSub({ submission_id: 'chain-fix-submission:corr-1', orchestrator_run_id: 'review-p1' }),
    baseSub({ submission_id: 'chain-fix-submission:corr-2', orchestrator_run_id: 'review-p2' }),
    baseSub({ submission_id: 'chain-fix-submission:reread-a', orchestrator_run_id: 'reread-a', view: 'text_and_context', specialist_id: 'chain-reader', model_id: 'claude-haiku-5-5', fix_kinds: ['no_change'], base: { read_from: 'production@2026-11-24T06:00:00Z', chain_sha256: 'base-corrected', chains: [{ chain_id: 'c0', branch: 0, structure_status: 'read_by_model', mentions: [] }] }, submitted_at: '2026-11-24T06:38:00Z', corrects_fix_id: undefined }),
    baseSub({ submission_id: 'chain-fix-submission:reread-b', orchestrator_run_id: 'reread-b', view: 'text_and_context', specialist_id: 'chain-reader', model_id: 'claude-haiku-5-5', fix_kinds: ['no_change'], base: { read_from: 'production@2026-11-24T06:00:00Z', chain_sha256: 'base-corrected', chains: [{ chain_id: 'c0', branch: 0, structure_status: 'read_by_model', mentions: [] }] }, submitted_at: '2026-11-24T06:38:00Z', corrects_fix_id: undefined }),
  ];
  const states = computeStates(submissions, [], []);
  assert.equal(states.length, 1);
  assert.equal(states[0].fix_id, 'chain-fix:deadbeef0000000000000001');
  assert.equal(states[0].effect, 'replace_routes');
  assert.equal(states[0].ai_corrected?.corrects_fix_id, 'chain-fix:old000000000000000000001');
  const lines = gunzipSync(buildOverrides(states, submissions)).toString('utf8').split('\n').filter(Boolean);
  assert.equal(lines.length, 1);
  const override = JSON.parse(lines[0]) as { effect: string; base_chain_sha256: string };
  assert.equal(override.effect, 'replace_routes');
  assert.equal(override.base_chain_sha256, 'base-old');

  const noChainSubs: Submission[] = [
    baseSub({ submission_id: 'chain-fix-submission:nc-1', fix_id: 'chain-fix:deadbeef0000000000000002', hadith_id: 'hadith:test:nochain-reread', orchestrator_run_id: 't02-a', view: 'text_and_context', specialist_id: 'chain-reader', model_id: 'claude-haiku-5-5', fix_kinds: ['link_removed', 'chain_removed'], disposition: 'no_chain_by_reading', planned: { chains: [] }, base: { read_from: 'production@2026-11-23T00:00:00Z', chain_sha256: 'base-stored', chains: [{ chain_id: 'c1', branch: 0, structure_status: 'uncertain', mentions: [] }] }, submitted_at: '2026-11-23T00:27:00Z', corrects_fix_id: undefined }),
    baseSub({ submission_id: 'chain-fix-submission:nc-2', fix_id: 'chain-fix:deadbeef0000000000000002', hadith_id: 'hadith:test:nochain-reread', orchestrator_run_id: 't02-b', view: 'text_and_context', specialist_id: 'chain-reader', model_id: 'claude-haiku-5-5', fix_kinds: ['link_removed', 'chain_removed'], disposition: 'no_chain_by_reading', planned: { chains: [] }, base: { read_from: 'production@2026-11-23T00:00:00Z', chain_sha256: 'base-stored', chains: [{ chain_id: 'c1', branch: 0, structure_status: 'uncertain', mentions: [] }] }, submitted_at: '2026-11-23T00:27:00Z', corrects_fix_id: undefined }),
    baseSub({ submission_id: 'chain-fix-submission:nc-3', fix_id: 'chain-fix:deadbeef0000000000000002', hadith_id: 'hadith:test:nochain-reread', orchestrator_run_id: 'r4-a', view: 'text_and_context', specialist_id: 'chain-reader', model_id: 'claude-haiku-5-5', fix_kinds: ['no_change'], disposition: 'no_chain_by_reading', planned: { chains: [] }, base: { read_from: 'production@2026-11-24T06:00:00Z', chain_sha256: 'base-empty', chains: [] }, submitted_at: '2026-11-24T06:38:00Z', corrects_fix_id: undefined }),
    baseSub({ submission_id: 'chain-fix-submission:nc-4', fix_id: 'chain-fix:deadbeef0000000000000002', hadith_id: 'hadith:test:nochain-reread', orchestrator_run_id: 'r4-b', view: 'text_and_context', specialist_id: 'chain-reader', model_id: 'claude-haiku-5-5', fix_kinds: ['no_change'], disposition: 'no_chain_by_reading', planned: { chains: [] }, base: { read_from: 'production@2026-11-24T06:00:00Z', chain_sha256: 'base-empty', chains: [] }, submitted_at: '2026-11-24T06:38:00Z', corrects_fix_id: undefined }),
  ];
  const ncStates = computeStates(noChainSubs, [], []);
  assert.equal(ncStates.length, 1);
  assert.equal(ncStates[0].effect, 'replace_routes');
  assert.equal(ncStates[0].structure_status, 'read_by_model');
  const [ncLine] = gunzipSync(buildOverrides(ncStates, noChainSubs)).toString('utf8').split('\n').filter(Boolean);
  const ncOverride = JSON.parse(ncLine) as { effect: string; base_chain_sha256: string; disposition: string };
  assert.deepEqual([ncOverride.effect, ncOverride.base_chain_sha256, ncOverride.disposition], ['replace_routes', 'base-stored', 'no_chain_by_reading']);
});

rmSync(work, { recursive: true, force: true });
if (failures.length > 0) {
  console.error(`\n${failures.length} failed`);
  process.exitCode = 1;
}
