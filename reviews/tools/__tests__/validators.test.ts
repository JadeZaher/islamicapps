/**
 * Human-review files and the citation standard: a valid contribution passes; each way a contributor can get it wrong
 * fails with its own message. Fixtures are real rows (Abu Dawud 4168, Taqrib entry 7557).
 * Run: npx tsx reviews/tools/__tests__/validators.test.ts
 */
import assert from 'node:assert/strict';
import path from 'node:path';
import { claimContentSha256, claimKey, sha256Hex } from '../../../src/lib/review/claim-key';
import { claimLineProblems } from '../validate-citations';
import { modelRegistryIds, readReviewTree, validateReviewFiles } from '../validate-reviews';

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

const TAQRIB_PASSAGE =
  'يحيى بن سعيد بن فروخ بفتح الفاء وتشديد الراء المضمومة وسكون الواو ثم معجمة التميمي أبو سعيد القطان البصري ثقة متقن حافظ إمام قدوة من كبار التاسعة مات سنة ثمان وتسعين وله ثمان وسبعون ع';
const taqribCitation = () => ({
  work: { author: 'Ibn Hajar al-Asqalani', title: 'Taqrib al-Tahdhib', tradition: 'Sunni' },
  edition: 'ed. Muhammad Awwama, Dar al-Rashid, Syria, 1406/1986; OpenITI 0852IbnHajarCasqalani.TaqribTahdhib.JK000121-ara1',
  locator: { kind: 'print', volume: '1', page: '591', entry: '7557' },
  passage: { text: TAQRIB_PASSAGE, language: 'ar' },
  source: { code: 'RIJ', licence: 'CC BY-NC-SA 4.0' },
  checked_against_sha256: sha256Hex(TAQRIB_PASSAGE),
});

const IDENTITY_KEY = claimKey.identity('mention:k6:19122:0001:0001', 'narrator:rawi:20031');
const IDENTITY_HASH = claimContentSha256(IDENTITY_KEY, ['0e8ffd95ac002574'.padEnd(64, '0'), sha256Hex('يحيى')]);

function validTree(): Map<string, Record<string, unknown>> {
  return new Map<string, Record<string, unknown>>([
    [
      'reviewers/first-reviewer.json',
      {
        format: 'shura-reviewer/1',
        handle: 'first-reviewer',
        display_name: 'First Reviewer',
        tradition_context: 'Sunni',
        permissions: [
          { capability: 'review', fields: ['identity', 'biography'], granted_by: 'owner', granted_on: '2026-11-21', basis: 'owner' },
          { capability: 'endorse', fields: ['identity'], granted_by: 'owner', granted_on: '2026-11-21', basis: 'owner' },
        ],
      },
    ],
    [
      'reviewers/second-reviewer.json',
      {
        format: 'shura-reviewer/1',
        handle: 'second-reviewer',
        display_name: 'Second Reviewer',
        tradition_context: null,
        permissions: [
          { capability: 'review', fields: ['identity'], granted_by: 'first-reviewer', granted_on: '2026-11-22', basis: 'endorsement', endorsement_id: 'en-first-second-identity' },
        ],
      },
    ],
    [
      'endorsements/en-first-second-identity.json',
      { format: 'shura-endorsement/1', id: 'en-first-second-identity', endorser: 'first-reviewer', endorsee: 'second-reviewer', field: 'identity', statement: 'Reads isnads closely.', endorsed_on: '2026-11-22' },
    ],
    [
      'entries/first-reviewer/rv-2026-11-21-first-reviewer-001.json',
      {
        format: 'shura-review/1',
        id: 'rv-2026-11-21-first-reviewer-001',
        reviewer: 'first-reviewer',
        claim: { kind: 'identity', key: IDENTITY_KEY, content_sha256: IDENTITY_HASH },
        stance: 'agrees',
        note: 'Musaddad and Ahmad from Yahya from Ubayd Allah: al-Qattan.',
        language: 'en',
        tradition_context: 'Sunni',
        citations: [taqribCitation()],
        ai_assistance: null,
        supersedes: null,
        submitted: '2026-11-21',
      },
    ],
  ]);
}

const asFiles = (tree: Map<string, Record<string, unknown>>) => new Map([...tree].map(([file, value]) => [file, JSON.stringify(value)]));
const MODELS = new Set(['claude-opus-5-5']);
const REVIEW = 'entries/first-reviewer/rv-2026-11-21-first-reviewer-001.json';

check('a valid contribution passes', () => {
  assert.deepEqual(validateReviewFiles(asFiles(validTree()), MODELS), []);
});

const reviewMutations: readonly [string, (tree: Map<string, Record<string, unknown>>) => void, RegExp][] = [
  ['an unknown stance', (tree) => (tree.get(REVIEW)!.stance = 'approves'), /stance must be one of/],
  ['a disagreement with no citation', (tree) => Object.assign(tree.get(REVIEW)!, { stance: 'disagrees', citations: [] }), /needs at least one citation/],
  ['a bare-title citation', (tree) => ((tree.get(REVIEW)!.citations as Record<string, unknown>[])[0].locator = { kind: 'print', volume: '1' }), /bare title or volume/],
  ['a citation with no passage', (tree) => ((tree.get(REVIEW)!.citations as Record<string, unknown>[])[0].passage = { text: '', language: 'ar' }), /verbatim passage/],
  ['a model’s knowledge as a citation', (tree) => ((tree.get(REVIEW)!.citations as Record<string, unknown>[])[0].work = { author: 'Claude', title: 'model knowledge', tradition: 'none' }), /model’s own knowledge/],
  ['a wrong licence for the source', (tree) => ((tree.get(REVIEW)!.citations as Record<string, unknown>[])[0].source = { code: 'RIJ', licence: 'CC BY 4.0' }), /registry’s "CC BY-NC-SA 4.0"/],
  ['a reviewer with no permission for the field', (tree) => (tree.get(REVIEW)!.claim = { kind: 'translation', key: 'translation|hadith:k6:19122|en', content_sha256: IDENTITY_HASH }), /did not hold "review" for translation/],
  ['a review submitted before the grant', (tree) => (tree.get(REVIEW)!.submitted = '2026-11-20'), /did not hold "review"/],
  ['a malformed claim key', (tree) => (tree.get(REVIEW)!.claim = { kind: 'identity', key: 'identity|k6:19122|20031', content_sha256: IDENTITY_HASH }), /grammar/],
  ['a missing content hash', (tree) => (tree.get(REVIEW)!.claim = { kind: 'identity', key: IDENTITY_KEY, content_sha256: 'abc' }), /content_sha256/],
  ['an anonymous reviewer', (tree) => (tree.get('reviewers/first-reviewer.json')!.display_name = ''), /never anonymous/],
  ['self-endorsement', (tree) => Object.assign(tree.get('endorsements/en-first-second-identity.json')!, { endorsee: 'first-reviewer' }), /cannot endorse themselves/],
  ['an endorsement by someone without endorse', (tree) => (tree.get('reviewers/first-reviewer.json')!.permissions = [(tree.get('reviewers/first-reviewer.json')!.permissions as unknown[])[0]]), /did not hold "endorse"/],
  ['an endorsement widened to another field', (tree) => ((tree.get('reviewers/second-reviewer.json')!.permissions as Record<string, unknown>[])[0].fields = ['identity', 'grading']), /grants only its own field/],
  ['an unknown field (typo)', (tree) => (tree.get(REVIEW)!.stanse = 'agrees'), /unknown field "stanse"/],
  ['an AI assistant not in the model registry', (tree) => (tree.get(REVIEW)!.ai_assistance = { model: 'gpt-x', role: 'drafting' }), /model registry id/],
];

for (const [name, mutate, expected] of reviewMutations) {
  check(`rejects ${name}`, () => {
    const tree = validTree();
    mutate(tree);
    const problems = validateReviewFiles(asFiles(tree), MODELS);
    assert.ok(problems.some((problem) => expected.test(problem)), `expected ${expected}, got:\n${problems.join('\n')}`);
  });
}

check('a second live review of one claim must supersede the first; superseding passes', () => {
  const tree = validTree();
  const second: Record<string, unknown> = { ...tree.get(REVIEW)!, id: 'rv-2026-11-23-first-reviewer-002', stance: 'qualifies', submitted: '2026-11-23' };
  tree.set('entries/first-reviewer/rv-2026-11-23-first-reviewer-002.json', second);
  assert.ok(validateReviewFiles(asFiles(tree), MODELS).some((problem) => /already has live review/.test(problem)));
  second.supersedes = 'rv-2026-11-21-first-reviewer-001';
  assert.deepEqual(validateReviewFiles(asFiles(tree), MODELS), []);
});

check('the repository reviews/ directory is valid', () => {
  const root = path.resolve(__dirname, '..', '..');
  assert.deepEqual(validateReviewFiles(readReviewTree(root), modelRegistryIds(path.resolve(root, '..'))), []);
});

// ── Claims against the citation standard ─────────────────────────────────────────────────────────────────────────
const citedBiography = {
  claim_kind: 'biography',
  claim_key: 'biography|narrator:rawi:20031|death_year|taqrib-7557',
  citation_status: 'cited',
  citations: [taqribCitation()],
};

check('a cited biographical value passes', () => assert.deepEqual(claimLineProblems(citedBiography), []));

const claimCases: readonly [string, unknown, RegExp][] = [
  ['a lexicon dataset record as the citation of a biographical value', { ...citedBiography, citations: [{ ...taqribCitation(), locator: { kind: 'dataset', dataset: 'Muslim Scholars Database', version: '2026-07-20', record_id: '20031' } }] }, /does not cite a biography claim/],
  ['a dataset locator with no record id', { claim_kind: 'identity', claim_key: IDENTITY_KEY, citation_status: 'cited', citations: [{ ...taqribCitation(), locator: { kind: 'dataset', dataset: 'K6', version: '2018-08-22', record_id: '' } }] }, /record id/],
  ['an uncited value without the label', { ...citedBiography, citation_status: 'not_yet_cited', citations: [], shown_under: 'owner decision 2026-11-21 (fourth round)' }, /label "not yet cited"/],
  ['an uncited value with no decision to show it', { ...citedBiography, citation_status: 'not_yet_cited', citations: [], label: 'not yet cited' }, /shown_under/],
  ['a correspondence citing one text only', { claim_kind: 'correspondence', claim_key: claimKey.correspondence('hadith:k6:19122', 'hadith:thaqalayn:06c871a7dec1feb72290ba14'), citation_status: 'cited', citations: [taqribCitation()] }, /at least 2 citations/],
  ['a web citation without its retrieval date', { ...citedBiography, claim_kind: 'numbering', claim_key: 'numbering|hadith:k6:19122|sunnah_com', citations: [{ ...taqribCitation(), locator: { kind: 'web', url: 'https://sunnah.com/abudawud:4168', retrieved: '' } }] }, /retrieval date/],
];
for (const [name, line, expected] of claimCases) {
  check(`rejects ${name}`, () => {
    const problems = claimLineProblems(line);
    assert.ok(problems.some((problem) => expected.test(problem)), `expected ${expected}, got:\n${problems.join('\n')}`);
  });
}

check('an uncited value shown under an owner decision passes with its label', () => {
  assert.deepEqual(
    claimLineProblems({ ...citedBiography, citation_status: 'not_yet_cited', citations: [], label: 'not yet cited', shown_under: 'RUNBOOK owner decisions, fourth round: lexicon values shown labelled' }),
    [],
  );
});

if (failures.length > 0) {
  console.error(`\n${failures.length} failed`);
  process.exitCode = 1;
}
