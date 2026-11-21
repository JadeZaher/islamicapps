/**
 * Review model integrity: every AI-review label the app can show has a /method entry; specialist prompts match the
 * registry; the summary rule never becomes a vote; claim keys are well formed. Discovers enums at run time.
 * Run: npx tsx src/lib/review/__tests__/review.test.ts
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import * as schemaEnums from '../../../db/schema/enums';
import { GLOSSARY_ENTRIES, getGlossaryEntry } from '../../glossary/terms';
import { claimKey, claimKeyProblem } from '../claim-key';
import { renderAiReviewMarkdown } from '../generate-doc';
import { allProcedures, METHOD_SECTIONS, NOT_AI_REVIEWED, REVIEW_BEARING_ENUMS, SPECIALISTS } from '../procedures';
import { summariseClaim, type HumanReviewForSummary } from '../summary';

const ROOT = path.resolve(__dirname, '..', '..', '..', '..');
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

interface PgEnumLike {
  enumName: string;
  enumValues: readonly string[];
}
const enums = new Map(
  Object.values(schemaEnums)
    .filter((value): value is typeof value & PgEnumLike => typeof value === 'function' && 'enumName' in value)
    .map((value) => [(value as unknown as PgEnumLike).enumName, (value as unknown as PgEnumLike).enumValues]),
);

check('every review-bearing enum value has a /method procedure or a stated reason it is not AI review', () => {
  const covered = new Set(allProcedures().flatMap((procedure) => procedure.covers));
  const missing: string[] = [];
  for (const name of REVIEW_BEARING_ENUMS) {
    const values = enums.get(name);
    assert.ok(values, `enum ${name} no longer exists`);
    for (const value of values) {
      const reference = `${name}.${value}` as const;
      if (!covered.has(reference) && !(reference in NOT_AI_REVIEWED)) missing.push(reference);
    }
  }
  assert.deepEqual(missing, [], `no /method entry for: ${missing.join(', ')}`);
});

check('procedure coverage names only real enum values, and no value twice', () => {
  const seen = new Set<string>();
  for (const procedure of allProcedures()) {
    for (const reference of procedure.covers) {
      const [name, value] = reference.split('.');
      assert.ok(enums.get(name)?.includes(value), `${procedure.id} covers unknown ${reference}`);
      assert.ok(!seen.has(reference), `${reference} is covered twice`);
      assert.ok(!(reference in NOT_AI_REVIEWED), `${reference} is both covered and declared not AI-reviewed`);
      seen.add(reference);
    }
  }
});

check('every glossary entry that names AI or machine review links to a procedure', () => {
  const linked = new Set(allProcedures().flatMap((procedure) => procedure.glossary));
  const aiTerms = GLOSSARY_ENTRIES.filter((entry) =>
    [entry.term, ...(entry.aliases ?? [])].some((text) => /\b(ai review|machine review|machine-reviewed|machine-proposed)\b/i.test(text)),
  );
  assert.ok(aiTerms.length > 0);
  for (const entry of aiTerms) assert.ok(linked.has(entry.slug), `glossary "${entry.slug}" has no /method procedure`);
  for (const slug of linked) assert.ok(getGlossaryEntry(slug), `procedure links unknown glossary slug ${slug}`);
});

check('anchors are unique and every in-use procedure states a measurement or says it has none', () => {
  const anchors = [...METHOD_SECTIONS.map((section) => section.id), ...allProcedures().map((procedure) => procedure.id), ...SPECIALISTS.map((specialist) => `specialist-${specialist.id}`)];
  assert.equal(new Set(anchors).size, anchors.length);
  for (const procedure of allProcedures()) {
    assert.ok(procedure.measured || procedure.unmeasured, `${procedure.id} neither measured nor says so`);
    assert.ok(procedure.sources.length > 0, `${procedure.id} credits no source`);
  }
});

check('each specialist has its prompt file and the registry records its current hash', () => {
  const registry = JSON.parse(readFileSync(path.join(ROOT, 'reviews', 'ai', 'specialists.json'), 'utf8')) as {
    specialists: { id: string; prompt_sha256: string; prompt_version: string }[];
  };
  for (const specialist of SPECIALISTS) {
    const bytes = readFileSync(path.join(ROOT, specialist.prompt));
    const entry = registry.specialists.find((row) => row.id === specialist.id);
    assert.ok(entry, `${specialist.id} missing from reviews/ai/specialists.json`);
    assert.equal(entry.prompt_sha256, createHash('sha256').update(bytes).digest('hex'), `${specialist.id} prompt changed: rebuild the registry`);
    assert.ok(new RegExp(`^version: ${entry.prompt_version.replace(/\./g, '\\.')}$`, 'm').test(bytes.toString('utf8')));
  }
});

check('docs/review/ai-review.md is generated from the same data as /method', () => {
  assert.equal(readFileSync(path.join(ROOT, 'docs', 'review', 'ai-review.md'), 'utf8'), renderAiReviewMarkdown());
});

// ── Summary: counts by stance, one view per reviewer, stale reviews not counted ────────────────────────────────
const HASH = 'f'.repeat(64);
const review = (id: string, reviewerId: string, stance: HumanReviewForSummary['stance'], extra: Partial<HumanReviewForSummary> = {}): HumanReviewForSummary => ({
  id,
  reviewerId,
  stance,
  contentSha256: HASH,
  submittedAt: '2026-11-21',
  supersedesId: null,
  retired: false,
  ...extra,
});

const summaryCases: readonly [string, Parameters<typeof summariseClaim>[1], HumanReviewForSummary[], string, string][] = [
  ['AI only', [{ kind: 'rule', outcome: 'supports' }], [], 'ai_reviewed', 'AI-reviewed (checked by rule)'],
  [
    'agreeing and qualifying reviewers',
    [{ kind: 'rule', outcome: 'supports' }],
    [review('a', 'r1', 'agrees'), review('b', 'r2', 'agrees'), review('c', 'r3', 'qualifies')],
    'ai_reviewed',
    'AI-reviewed (checked by rule) · 3 human reviews: 2 agree, 1 qualifies',
  ],
  [
    'one disagreement shows both views',
    [{ kind: 'rule', outcome: 'supports' }, { kind: 'specialist', outcome: 'supports' }],
    [review('a', 'r1', 'agrees'), review('b', 'r2', 'disagrees')],
    'reviewers_differ',
    'Reviewers differ (checked by rule and AI specialist review) · 2 human reviews: 1 agrees, 1 disagrees',
  ],
  [
    'a superseded review is history, not a second voice',
    [{ kind: 'rule', outcome: 'supports' }],
    [review('a', 'r1', 'disagrees'), review('b', 'r1', 'agrees', { supersedesId: 'a', submittedAt: '2026-11-22' })],
    'ai_reviewed',
    'AI-reviewed (checked by rule) · 1 human review: 1 agrees',
  ],
  [
    'a review of an earlier text is listed, not counted',
    [{ kind: 'rule', outcome: 'supports' }],
    [review('a', 'r1', 'disagrees', { contentSha256: 'e'.repeat(64) })],
    'ai_reviewed',
    'AI-reviewed (checked by rule) · 1 review of an earlier text',
  ],
  ['a contested specialist review', [{ kind: 'specialist', outcome: 'contested' }], [], 'reviewers_differ', 'Reviewers differ (AI specialist review)'],
];
for (const [name, ai, human, state, label] of summaryCases) {
  check(`summary: ${name}`, () => {
    const summary = summariseClaim(HASH, ai, human);
    assert.equal(summary.state, state);
    assert.equal(summary.label, label);
    assert.ok(!/verified|confirmed|%/.test(summary.label), 'a summary never claims verification or a percentage');
  });
}

// ── Claim keys ─────────────────────────────────────────────────────────────────────────────────────────────────
check('claim keys: real ids parse; malformed and misordered keys are refused', () => {
  assert.equal(claimKeyProblem('identity', claimKey.identity('mention:k6:19122:0001:0001', 'narrator:rawi:20031')), null);
  const pair = claimKey.correspondence('hadith:thaqalayn:06c871a7dec1feb72290ba14', 'hadith:k6:19122');
  assert.equal(pair, 'correspondence|hadith:k6:19122|hadith:thaqalayn:06c871a7dec1feb72290ba14');
  assert.equal(claimKeyProblem('correspondence', pair), null);
  assert.equal(claimKeyProblem('correspondence', claimKey.correspondence('hadith:openiti:zaydi:zayd_0613|613|V01P382', 'hadith:thaqalayn:ac5af7210a58861b0fcf63a9')), null);
  assert.match(claimKeyProblem('correspondence', 'correspondence|hadith:thaqalayn:x|hadith:k6:1')!, /byte order/);
  assert.match(claimKeyProblem('quran_citation', 'quran_citation|hadith:k6:1|50|40|2:255')!, /greater than start/);
});

if (failures.length > 0) {
  console.error(`\n${failures.length} failed`);
  process.exitCode = 1;
}
