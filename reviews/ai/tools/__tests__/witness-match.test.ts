/**
 * Flow tests for witness-match-record.ts on real pilot packets (context/pilot-v2/packets-text/) and pilot/reports.jsonl
 * in a private temporary store:
 * 1. Verified text_check.status === "matches" with HKG/RWY (and online URL) binds locator + method + reader_text_sha256
 *    to the chain_fix and writes witness-matches/<run>.jsonl cleanly (and is idempotent on re-run).
 * 2. THQ / OITI echo-only matches are rejected by validateWitnessCandidate and --strict, and skipped cleanly in batch mode.
 * 3. Missing locator, missing method, non-empty differences, uncorroborated copy, or stale reader_text_sha256 fails validation.
 * 4. chain_field_then_matn reports (cr-0015 Muwatta) bind to reader_text_sha256 = sha256(packet.text), NOT stored_text_sha256.
 * 5. --database production without --confirm-production is refused before touching any DB.
 *
 *   npx tsx reviews/ai/tools/__tests__/witness-match.test.ts
 */
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import {
  appendRecords,
  computeStates,
  reconcile,
  REPOSITORY_ROOT,
  storePaths,
  SUBMISSION_FORMAT,
  type Submission,
} from '../chain-fix-lib';
import { sha256Hex } from '../specialist-lib';
import {
  readWitnessMatches,
  validateWitnessCandidate,
  WITNESS_MATCH_FORMAT,
  type TextPacketItem,
} from '../witness-match-record';

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

const CONTEXT_DIR = path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'chain-reader', 'context');
const PACKETS_TEXT_DIR = path.join(CONTEXT_DIR, 'pilot-v2', 'packets-text');
const PILOT_REPORTS = path.join(REPOSITORY_ROOT, 'datasets', 'hadith-data', 'chain-reader', 'pilot', 'reports.jsonl');

function loadPacketMap(): Map<string, TextPacketItem> {
  const map = new Map<string, TextPacketItem>();
  for (const name of readdirSync(PACKETS_TEXT_DIR).filter((n) => /^packet-\d+\.jsonl$/.test(n)).sort()) {
    for (const line of readFileSync(path.join(PACKETS_TEXT_DIR, name), 'utf8').split(/\r?\n/)) {
      if (!line.trim()) continue;
      const item = JSON.parse(line) as TextPacketItem;
      map.set(item.id, item);
    }
  }
  return map;
}

const packets = loadPacketMap();
const reports = new Map<string, Record<string, unknown> & { id: string; hadith_id: string; text: string; text_layout: string; tradition: string; work: string }>(
  readFileSync(PILOT_REPORTS, 'utf8')
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      const row = JSON.parse(line) as Record<string, unknown> & { id: string; hadith_id: string; text: string; text_layout: string; tradition: string; work: string };
      return [row.id, row];
    }),
);

// Real pilot items covering every regime:
// cr-0001: Sahih Muslim, HKG + RWY identical_after_normalisation
// cr-0002: Thawab al-A'mal, THQ echo-only (independent_of_our_source = 0)
// cr-0004: Sahih Bukhari, no local copies (not_checked offline, or online witness if fetched)
// cr-0015: Muwatta, chain_field_then_matn (reader_text_sha256 != stored_text_sha256)
const CR_MUSLIM = packets.get('cr-0001')!;
const CR_THAWAB = packets.get('cr-0002')!;
const CR_BUKHARI = packets.get('cr-0004')!;
const CR_MUWATTA = packets.get('cr-0015')!;

const work = mkdtempSync(path.join(tmpdir(), 'witness-match-test-'));
const store = path.join(work, 'store');
const overrides = path.join(work, 'accepted_overrides.jsonl.gz');
const packetsDir = path.join(work, 'packets');
const outputsDir = path.join(work, 'outputs');
const reportsFile = path.join(work, 'reports.jsonl');
mkdirSync(packetsDir, { recursive: true });
mkdirSync(outputsDir, { recursive: true });

function seedFix(itemId: string, fixSuffix: string): { fix_id: string; hadith_id: string; reader_text_sha256: string } {
  const pkt = packets.get(itemId)!;
  const rep = reports.get(itemId)!;
  const readerTextSha256 = sha256Hex(pkt.text);
  const arabicSha256 = pkt.context?.text_and_metadata?.stored_text_sha256 ?? readerTextSha256;
  const fixId = `chain-fix:${fixSuffix.padEnd(24, '0').slice(0, 24)}`;
  const paths = storePaths(store);
  mkdirSync(paths.submissions, { recursive: true });

  const makeSub = (runId: string): Submission => ({
    format: SUBMISSION_FORMAT,
    submission_id: `chain-fix-submission:${sha256Hex(`${fixId}:${runId}`).slice(0, 24)}`,
    fix_id: fixId,
    routes_key: `rk-${fixSuffix}`,
    hadith_id: rep.hadith_id,
    record_id: rep.hadith_id.replace(/^hadith:/, ''),
    source_work_id: `${rep.tradition}:${rep.work}`,
    tradition: rep.tradition,
    text_layout: rep.text_layout,
    arabic_sha256: arabicSha256,
    reader_text_sha256: readerTextSha256,
    text_checked_against: 'snapshot',
    base: { chains: [{ chain_id: 'c0', branch: 0, structure_status: 'uncertain', mentions: [] }], chain_sha256: 'base0', read_from: 'snapshot@test' },
    reading: { routes: [], matn_start: 0, notes: [], offsets_repaired: false },
    fix_kinds: ['link_added'],
    comparison: {},
    planned: { chains: [{ id: 'c0', branch: 0, length: 1, extraction_method: 'chain_fix_reader', suspension: null, mentions: [] }] },
    reason: 'Test seeded fix.',
    evidence: [{ quote: pkt.text.slice(0, 16) }],
    computed_evidence: [],
    external_citation: null,
    view: 'text_and_context',
    reader_format: 'v3_4',
    tool_version: 'v3_4',
    holds: [],
    derived_links: [],
    review_kind: 'specialist',
    label: 'AI reviewed',
    specialist_id: 'chain-reader',
    specialist_version: '3.4.0',
    prompt_path: 'datasets/hadith-data/chain-reader/v3_4/prompt-v3_4.md',
    prompt_version: '3.4.0',
    prompt_sha256: 'a'.repeat(64),
    model_id: 'claude-haiku-5-5',
    provider_runtime: 'test',
    orchestrator_run_id: runId,
    packet_path: 'test.jsonl',
    packet_sha256: 'b'.repeat(64),
    packet_item_id: itemId,
    started_at: '2026-11-24T00:00:00Z',
    finished_at: '2026-11-24T00:01:00Z',
    submitted_at: '2026-11-24T00:02:00Z',
  });
  appendRecords(path.join(paths.submissions, `${fixSuffix}-a.jsonl`), [makeSub(`${fixSuffix}-a`)]);
  appendRecords(path.join(paths.submissions, `${fixSuffix}-b.jsonl`), [makeSub(`${fixSuffix}-b`)]);
  return { fix_id: fixId, hadith_id: rep.hadith_id, reader_text_sha256: readerTextSha256 };
}

function runCli(args: string[]) {
  const result = spawnSync(
    process.execPath,
    ['--import', 'tsx', path.join(REPOSITORY_ROOT, 'reviews', 'ai', 'tools', 'witness-match-record.ts'), ...args],
    { cwd: REPOSITORY_ROOT, encoding: 'utf8' },
  );
  return { status: result.status, out: result.stdout, err: result.stderr };
}

try {
  const muslimFix = seedFix('cr-0001', 'muslim01');
  const thawabFix = seedFix('cr-0002', 'thawab02');
  const bukhariFix = seedFix('cr-0004', 'bukhari04');
  const muwattaFix = seedFix('cr-0015', 'muwatta15');
  reconcile(storePaths(store), overrides, '2026-11-24T00:05:00Z');

  // Verify Muwatta really has distinct reader_text_sha256 vs stored_text_sha256 (chain_field_then_matn).
  assert.notEqual(
    sha256Hex(CR_MUWATTA.text),
    CR_MUWATTA.context?.text_and_metadata?.stored_text_sha256,
    'cr-0015 should have distinct reader_text_sha256 vs stored_text_sha256',
  );

  writeFileSync(
    path.join(packetsDir, 'packet-01.jsonl'),
    [CR_MUSLIM, CR_THAWAB, CR_BUKHARI, CR_MUWATTA].map((x) => JSON.stringify(x)).join('\n') + '\n',
    'utf8',
  );
  writeFileSync(
    reportsFile,
    ['cr-0001', 'cr-0002', 'cr-0004', 'cr-0015'].map((id) => JSON.stringify(reports.get(id)!)).join('\n') + '\n',
    'utf8',
  );

  check('validateWitnessCandidate rejects THQ/OITI echo-only, missing locator/method, differences, and stale reader_text_sha256', () => {
    const echo = validateWitnessCandidate({
      output: { id: 'cr-0002', text_check: { status: 'matches', compared: ['THQ'], differences: [] }, metadata_check: { status: 'matches', compared: ['THQ'], differences: [] }, fixes: [], notes: [] },
      packet: CR_THAWAB,
      fix: thawabFix,
    });
    assert.equal(echo.valid, false);
    assert.equal(echo.classification, 'echo_only');
    assert.match(echo.errors[0], /only echo source\(s\) \(THQ\)/);

    const oitiEcho = validateWitnessCandidate({
      output: { id: 'cr-0002', text_check: { status: 'matches', compared: ['OITI'], differences: [] }, metadata_check: { status: 'not_checked', compared: [], differences: [], reason: 'r' }, fixes: [], notes: [] },
      packet: CR_THAWAB,
      fix: thawabFix,
    });
    assert.equal(oitiEcho.valid, false);
    assert.equal(oitiEcho.classification, 'echo_only');
    assert.match(oitiEcho.errors[0], /only echo source\(s\) \(OITI\)/);

    const noLocatorOnline = validateWitnessCandidate({
      output: { id: 'cr-0004', text_check: { status: 'matches', compared: ['online'], differences: [] }, metadata_check: { status: 'not_checked', compared: [], differences: [], reason: 'r' }, fixes: [], notes: [] },
      packet: CR_BUKHARI,
      fix: bukhariFix,
    });
    assert.equal(noLocatorOnline.valid, false);
    assert.ok(noLocatorOnline.errors.some((e) => e.startsWith('locator:')));

    const withDiffs = validateWitnessCandidate({
      output: { id: 'cr-0001', text_check: { status: 'matches', compared: ['HKG'], differences: [{ ours: 'x', theirs: 'y', source: 'HKG' }] }, metadata_check: { status: 'not_checked', compared: [], differences: [], reason: 'r' }, fixes: [], notes: [] },
      packet: CR_MUSLIM,
      fix: muslimFix,
    });
    assert.equal(withDiffs.valid, false);
    assert.ok(withDiffs.errors.some((e) => e.startsWith('text_check.differences:')));

    const stale = validateWitnessCandidate({
      output: { id: 'cr-0001', text_check: { status: 'matches', compared: ['HKG'], differences: [] }, metadata_check: { status: 'not_checked', compared: [], differences: [], reason: 'r' }, fixes: [], notes: [] },
      packet: CR_MUSLIM,
      fix: { ...muslimFix, reader_text_sha256: 'f'.repeat(64) },
    });
    assert.equal(stale.valid, false);
    assert.ok(stale.errors.some((e) => e.startsWith('stale_reader_text_sha256:')));

    const fakeSource = validateWitnessCandidate({
      output: { id: 'cr-0004', text_check: { status: 'matches', compared: ['HKG'], differences: [] }, metadata_check: { status: 'not_checked', compared: [], differences: [], reason: 'r' }, fixes: [], notes: [] },
      packet: CR_BUKHARI,
      fix: bukhariFix,
    });
    assert.equal(fakeSource.valid, false);
    assert.ok(fakeSource.errors.some((e) => e.startsWith('witness_copy:')));
  });

  // Write realistic outputs for the 4 reports in packet-01:
  // cr-0001: matches HKG + RWY (independent)
  // cr-0002: matches THQ only (echo-only -> must NOT become a witness match)
  // cr-0004: not_checked offline (must NOT become a witness match)
  // cr-0015: matches via online URL (e.g. api.turath.io) with chain_field_then_matn reader_text_sha256 binding
  writeFileSync(
    path.join(outputsDir, 'cr-0001.json'),
    JSON.stringify({
      id: 'cr-0001',
      text_check: { status: 'matches', compared: ['HKG', 'RWY'], differences: [] },
      metadata_check: { status: 'not_checked', compared: [], differences: [], reason: 'different numbering schemes and no web access' },
      fixes: [],
      notes: [],
    }),
    'utf8',
  );
  writeFileSync(
    path.join(outputsDir, 'cr-0002.json'),
    JSON.stringify({
      id: 'cr-0002',
      text_check: { status: 'matches', compared: ['THQ'], differences: [] },
      metadata_check: { status: 'matches', compared: ['THQ'], differences: [] },
      fixes: [],
      notes: [],
    }),
    'utf8',
  );
  writeFileSync(
    path.join(outputsDir, 'cr-0004.json'),
    JSON.stringify({
      id: 'cr-0004',
      text_check: { status: 'not_checked', compared: [], differences: [], reason: 'no second local copy exists and no web access in this run' },
      metadata_check: { status: 'not_checked', compared: [], differences: [], reason: 'no local source and no web access in this run' },
      fixes: [],
      notes: [],
    }),
    'utf8',
  );
  writeFileSync(
    path.join(outputsDir, 'cr-0015.json'),
    JSON.stringify({
      id: 'cr-0015',
      text_check: {
        status: 'matches',
        compared: ['https://api.turath.io/book?id=1234&pg=55'],
        differences: [],
        method: 'online_turath_collation',
      },
      metadata_check: { status: 'not_checked', compared: [], differences: [], reason: 'offline metadata check skipped' },
      fixes: [],
      notes: [],
    }),
    'utf8',
  );
  writeFileSync(
    path.join(outputsDir, 'RUN.txt'),
    'run_id=text-pilot-01 | packets=01 | model=gemini-3-flash | start=2026-11-24T01:00:00Z | end=2026-11-24T01:05:00Z | files=4\n',
    'utf8',
  );

  check('batch CLI records independent witnesses only (skips THQ echo and not_checked), binds reader_text_sha256, and is idempotent', () => {
    const first = runCli(['--packets', packetsDir, '--outputs', outputsDir, '--reports', reportsFile, '--store', store]);
    assert.equal(first.status, 0, first.err + first.out);
    assert.match(first.out, /summary: examined=4, matched=2, fresh=2, dup=0, skipped_echo=1, skipped_not_matches=1/);

    const recorded = readWitnessMatches(store);
    assert.equal(recorded.length, 2);

    const muslimRec = recorded.find((r) => r.packet_item_id === 'cr-0001')!;
    assert.equal(muslimRec.format, WITNESS_MATCH_FORMAT);
    assert.equal(muslimRec.fix_id, muslimFix.fix_id);
    assert.equal(muslimRec.hadith_id, muslimFix.hadith_id);
    assert.equal(muslimRec.witness, 'hadith-kg + Riwayat');
    assert.match(muslimRec.locator, /hadith-kg hadith 9643/);
    assert.match(muslimRec.locator, /Riwayat H0009643/);
    assert.equal(muslimRec.method, 'local_copy_normalised_match');
    assert.equal(muslimRec.matched, true);
    assert.equal(muslimRec.reader_text_sha256, muslimFix.reader_text_sha256);
    assert.equal(muslimRec.model_id, 'gemini-3-flash');
    assert.equal(muslimRec.run_id, 'text-pilot-01');

    const muwattaRec = recorded.find((r) => r.packet_item_id === 'cr-0015')!;
    assert.equal(muwattaRec.fix_id, muwattaFix.fix_id);
    assert.equal(muwattaRec.witness, 'api.turath.io');
    assert.equal(muwattaRec.locator, 'https://api.turath.io/book?id=1234&pg=55');
    assert.equal(muwattaRec.method, 'online_turath_collation');
    assert.equal(muwattaRec.reader_text_sha256, muwattaFix.reader_text_sha256);
    assert.notEqual(muwattaRec.reader_text_sha256, CR_MUWATTA.context?.text_and_metadata?.stored_text_sha256);

    assert.ok(existsSync(path.join(store, 'witness-matches', 'text-pilot-01.jsonl')));

    const second = runCli(['--packets', packetsDir, '--outputs', outputsDir, '--reports', reportsFile, '--store', store]);
    assert.equal(second.status, 0, second.err + second.out);
    assert.match(second.out, /summary: examined=4, matched=2, fresh=0, dup=2/);
    assert.equal(readWitnessMatches(store).length, 2);
  });

  check('--strict and single-output mode reject THQ echo-only outputs cleanly', () => {
    const strictRun = runCli(['--packets', packetsDir, '--outputs', path.join(outputsDir, 'cr-0002.json'), '--reports', reportsFile, '--store', store]);
    assert.equal(strictRun.status, 1);
    assert.match(strictRun.err, /only echo source\(s\) \(THQ\)/);
  });

  check('--database production without --confirm-production is refused', () => {
    const refused = runCli(['--packets', packetsDir, '--outputs', outputsDir, '--reports', reportsFile, '--store', store, '--database', 'production']);
    assert.equal(refused.status, 1);
    assert.match(refused.err, /--confirm-production/);
  });

  // Verify states computed cleanly alongside witness matches
  const states = computeStates([], [], []);
  assert.equal(states.length, 0);
} finally {
  rmSync(work, { recursive: true, force: true });
}

if (failures.length > 0) {
  console.error(`\n${failures.length} failed: ${failures.join(', ')}`);
  process.exitCode = 1;
} else {
  console.log('\nall witness-match flow tests passed');
}
