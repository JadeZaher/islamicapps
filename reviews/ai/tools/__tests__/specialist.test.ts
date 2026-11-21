/**
 * Specialist review flow: an output is checked against its packet (one verdict per claim, quotes that really occur in
 * the packet, the vocabulary), records carry model, prompt hash and UTC times, and packets never leak a verdict.
 * Uses the real pilot packets when present. Run: npx tsx reviews/ai/tools/__tests__/specialist.test.ts
 */
import assert from 'node:assert/strict';
import { existsSync, readdirSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { buildSpecialistRecords, packetLeaks, scoreAgainstKnownAnswers, validateSpecialistOutput, type Packet, type PacketManifestItem } from '../specialist-lib';

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

// Abu Dawud 4168 and Ma'ani al-Akhbar 275, as stored in production (2026-11-21).
const TEXT_A = 'حدثنا أحمد بن حنبل، ومسدد، قالا حدثنا يحيى، عن عبيد الله، قال حدثني نافع، عن عبد الله، قال لعن رسول الله صلى الله عليه وسلم الواصلة والمستوصلة والواشمة والمستوشمة ‏.‏';
const TEXT_B = 'حدثنا الحسين بن إبراهيم بن أحمد بن هشام المكتب، قال حدثنا علي بن إبراهيم، عن أبيه، عن محمد بن أبي عمير، عن إبراهيم بن زياد الكرخي قال: سمعت أبا عبد الله عليه السلام يقول: لعن رسول الله صلى الله عليه وآله الواصلة والمستوصلة يعني الزانية والقوادة.';

const packet: Packet = {
  format: 'shura-review-packet/1',
  packet_id: 'correspondence/test/packet-01',
  specialist_id: 'correspondence',
  prompt_version: '1.0.0',
  items: [{ item_id: 'I1', claim_ids: ['I1'], passages: [{ id: 'A', text: TEXT_A }, { id: 'B', text: TEXT_B }] }],
  glossary: [],
};
const goodOutput = () => ({
  format: 'shura-specialist-output/1',
  specialist_id: 'correspondence',
  prompt_version: '1.0.0',
  packet_id: packet.packet_id,
  verdicts: [
    {
      claim_id: 'I1',
      outcome: 'contested',
      reading: 'same_ruling_different_speaker',
      reasons: ['Both quote the Prophet’s curse; B is an Imam’s report that adds a gloss of the terms.'],
      evidence: [
        { passage_id: 'A', quote: 'لعن رسول الله صلى الله عليه وسلم الواصلة والمستوصلة' },
        { passage_id: 'B', quote: 'يعني الزانية والقوادة' },
      ],
      uncertainty: 'medium',
      proposals: [{ kind: 'difference', text: 'B glosses al-wasila and al-mustawsila as the adulteress and the procuress.' }],
    },
  ],
});

check('a well-formed output passes', () => assert.deepEqual(validateSpecialistOutput(packet, goodOutput(), '1.0.0'), []));

const cases: readonly [string, (output: ReturnType<typeof goodOutput>) => void, RegExp][] = [
  ['a quote that is not in the text (fabricated or normalised)', (output) => (output.verdicts[0].evidence[0].quote = 'لعن رسول الله ﷺ الواصلة'), /not an exact substring/],
  ['a quote attributed to the wrong text', (output) => (output.verdicts[0].evidence[1].passage_id = 'A'), /not an exact substring of A/],
  ['an outcome outside the vocabulary', (output) => ((output.verdicts[0] as { outcome: string }).outcome = 'likely'), /outcome/],
  ['a reading that contradicts the outcome', (output) => (output.verdicts[0].reading = 'unrelated'), /goes with outcome contradicts/],
  ['a missing verdict', (output) => (output.verdicts = []), /no verdict for claim_id I1/],
  ['a claim id not in the packet', (output) => (output.verdicts[0].claim_id = 'I9'), /not in the packet/],
  ['a stale prompt version', (output) => (output.prompt_version = '0.9.0'), /prompt_version/],
  ['supports with no evidence', (output) => Object.assign(output.verdicts[0], { outcome: 'supports', reading: 'same_report_variant', evidence: [] }), /needs at least one evidence quote/],
  ['extra prose fields', (output) => ((output as Record<string, unknown>).commentary = 'I think...'), /unknown top-level field/],
];
for (const [name, mutate, expected] of cases) {
  check(`rejects ${name}`, () => {
    const output = goodOutput();
    mutate(output);
    const problems = validateSpecialistOutput(packet, output, '1.0.0');
    assert.ok(problems.some((problem) => expected.test(problem)), `expected ${expected}, got:\n${problems.join('\n')}`);
  });
}

const manifest: PacketManifestItem[] = [
  { item_id: 'I1', claim_id: 'I1', claim_kind: 'correspondence', claim_key: 'correspondence|hadith:k6:19122|hadith:thaqalayn:06c871a7dec1feb72290ba14', content_sha256: 'a'.repeat(64), stratum: 'worked_example', pipeline_view: 'class=variant', known_answer: { outcome: 'supports', source: 'test' } },
];
const run = { model_id: 'claude-opus-5-5', provider_runtime: 'Claude Code subagent', started_at: '2026-11-21T14:00:00Z', finished_at: '2026-11-21T14:01:10Z', orchestrator_run_id: 'test' };
const recordInput = (overrides: Partial<typeof run> = {}) => ({
  packet,
  packetPath: 'reviews/ai/packets/correspondence/test/packet-01.json',
  packetSha256: 'b'.repeat(64),
  manifest,
  output: goodOutput() as never,
  outputSha256: 'c'.repeat(64),
  prompt: { path: 'reviews/ai/prompts/correspondence.md', version: '1.0.0', sha256: 'd'.repeat(64) },
  specialistVersion: '1.0.0',
  run: { ...run, ...overrides },
});

check('a record notes the model, prompt hash, UTC times and the claim it answers', () => {
  const [record] = buildSpecialistRecords(recordInput());
  assert.equal(record.model_id, 'claude-opus-5-5');
  assert.equal(record.prompt_sha256, 'd'.repeat(64));
  assert.equal(record.started_at, '2026-11-21T14:00:00Z');
  assert.equal(record.claim_key, manifest[0].claim_key);
  assert.equal(record.review_kind, 'specialist');
});

check('a record refuses local time, reversed times and a missing model', () => {
  assert.throws(() => buildSpecialistRecords(recordInput({ started_at: '2026-11-21 14:00' })), /UTC/);
  assert.throws(() => buildSpecialistRecords(recordInput({ finished_at: '2026-11-21T13:00:00Z' })), /before/);
  assert.throws(() => buildSpecialistRecords(recordInput({ model_id: '' })), /model_id/);
});

check('agreement with known answers is counted per claim, never averaged into a score', () => {
  const score = scoreAgainstKnownAnswers(manifest, goodOutput().verdicts as never);
  assert.deepEqual({ known: score.known, agree: score.agree }, { known: 1, agree: 0 });
  assert.equal(score.rows[0].got, 'contested');
});

check('a packet that carries the pipeline’s scores is caught', () => {
  assert.deepEqual(packetLeaks({ items: [{ jaccard: 0.41, candidates: [{ basis: 'source_index' }] }] }), ['basis', 'jaccard']);
});

check('the pilot packets on disk leak nothing and answer to their manifests', () => {
  const root = path.resolve(__dirname, '..', '..', 'packets');
  if (!existsSync(root)) return;
  let packets = 0;
  for (const specialist of readdirSync(root)) {
    for (const batch of readdirSync(path.join(root, specialist))) {
      const directory = path.join(root, specialist, batch);
      for (const file of readdirSync(directory).filter((name) => /^packet-\d+\.json$/.test(name))) {
        const onDisk = JSON.parse(readFileSync(path.join(directory, file), 'utf8')) as Packet;
        const hidden = JSON.parse(readFileSync(path.join(directory, file.replace('.json', '.manifest.json')), 'utf8')) as { items: PacketManifestItem[] };
        assert.deepEqual(packetLeaks(onDisk), [], `${file} leaks`);
        const claimIds = onDisk.items.flatMap((item) => item.claim_ids).sort();
        assert.deepEqual(hidden.items.map((item) => item.claim_id).sort(), claimIds, `${file} manifest does not match`);
        assert.ok(!JSON.stringify(onDisk).includes('known_answer'), `${file} carries an answer`);
        packets += 1;
      }
    }
  }
  assert.ok(packets > 0);
});

if (failures.length > 0) {
  console.error(`\n${failures.length} failed`);
  process.exitCode = 1;
}
