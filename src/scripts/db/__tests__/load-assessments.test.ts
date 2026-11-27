import assert from 'node:assert/strict';
import {
  buildNarratorProvenance,
  normalizeAssessmentKind,
  normalizeGradeCanonical,
  normalizeGradeScheme,
  normalizeNarratorAssessmentKind,
  normalizeNarratorVerdict,
  normalizeReviewState,
  parseHadithAssessmentRow,
  parseNarratorAssessmentRow,
} from '../load-assessments';

// Enum normalizers
assert.equal(normalizeGradeScheme('sunni_7tier'), 'sunni_7tier');
assert.equal(normalizeGradeScheme('imami_4tier'), 'imami_4tier');
assert.equal(normalizeGradeScheme('invalid'), null);

assert.equal(normalizeAssessmentKind('compiler_statement'), 'compiler_statement');
assert.equal(normalizeAssessmentKind('cited_ruling'), 'cited_ruling');
assert.equal(normalizeAssessmentKind('unknown'), null);

assert.equal(normalizeGradeCanonical('sahih'), 'sahih');
assert.equal(normalizeGradeCanonical('da_if'), 'da_if');
assert.equal(normalizeGradeCanonical(null), null);
assert.equal(normalizeGradeCanonical('bogus'), null);

assert.equal(normalizeReviewState('candidate_only'), 'candidate_only');
assert.equal(normalizeReviewState('unknown'), 'candidate_only');

assert.equal(normalizeNarratorAssessmentKind('critic_ruling'), 'critic_ruling');
assert.equal(normalizeNarratorAssessmentKind('bogus'), null);

assert.equal(normalizeNarratorVerdict('thiqa'), 'thiqa');
assert.equal(normalizeNarratorVerdict('matruk'), 'matruk');
assert.equal(normalizeNarratorVerdict(null), null);

// Provenance builder
assert.equal(
  buildNarratorProvenance({ source_codes: ['HKG'], basis_kind: 'dataset_record_of_critic_statement', work: null }),
  'HKG:dataset_record_of_critic_statement',
);
assert.equal(
  buildNarratorProvenance({
    source_codes: ['RIJ'],
    basis_kind: 'critic_quoted_in_rijal_work',
    rijal_work_key: 'mizzi_tahdhib_kamal',
  }),
  'RIJ:critic_quoted_in_rijal_work:mizzi_tahdhib_kamal',
);

// Hadith assessment row parsing: valid cited row
const haValid = parseHadithAssessmentRow({
  id: 'assessment:k6:14985:sunni:text_ar:01',
  hadith_id: 'hadith:k6:14985',
  tradition_id: 'tradition:sunni',
  grade_scheme: 'sunni_7tier',
  ordinal: 1,
  kind: 'compiler_statement',
  grader: "Abu Dawud Sulayman ibn al-Ash'ath al-Sijistani (d. 275)",
  grade_raw: 'هذا حديث منكر',
  grade_canonical: null,
  statement_ar: 'قال أبو داود هذا حديث منكر',
  citation_raw: null,
  cited_work: 'Sunan Abi Dawud',
  cited_volume: null,
  cited_page: null,
  source_field: 'text_ar',
  review_state: 'candidate_only',
  citation_status: 'cited',
  already_loaded: false,
});
assert.equal(haValid.ok, true);
if (haValid.ok) {
  assert.equal(haValid.value.hadithId, 'hadith:k6:14985');
  assert.equal(haValid.value.gradeCanonical, null);
  assert.equal(haValid.value.alreadyLoaded, false);
}

// Hadith assessment row parsing: rejects uncited / placeholder rows
const haUncited = parseHadithAssessmentRow({
  id: 'assessment:placeholder',
  hadith_id: 'hadith:k6:1',
  tradition_id: 'tradition:sunni',
  grade_scheme: 'sunni_7tier',
  ordinal: 1,
  kind: 'compiler_criterion',
  grade_raw: 'صحيح',
  source_field: 'criterion',
  citation_status: 'not_yet_cited',
});
assert.deepEqual(haUncited, { ok: false, reason: 'uncited' });

// Narrator assessment row parsing: valid cited row with canonical verdict
const naValid = parseNarratorAssessmentRow({
  id: 'narrator-assessment:hadith-kg:aqwal:10790',
  narrator_id: 'narrator:rawi:28061',
  tradition_id: 'tradition:sunni',
  kind: 'critic_ruling',
  verdict_canonical: 'matruk',
  critic: 'أبو بشر الدولابي',
  quote_ar: 'متروك',
  aspect: 'verdict_term',
  basis_kind: 'dataset_record_of_critic_statement',
  source_codes: ['HKG'],
  citation_status: 'cited',
});
assert.equal(naValid.ok, true);
if (naValid.ok) {
  assert.equal(naValid.value.verdict, 'matruk');
  assert.equal(naValid.value.isCompanion, null);
  assert.equal(naValid.value.provenance, 'HKG:dataset_record_of_critic_statement');
}

// Narrator assessment row parsing: companion status maps to not_applicable + isCompanion=true
const naCompanion = parseNarratorAssessmentRow({
  id: 'narrator-assessment:hadith-kg:aqwal:112630',
  narrator_id: 'narrator:rawi:4046',
  tradition_id: 'tradition:sunni',
  kind: 'critic_ruling',
  verdict_canonical: null,
  critic: 'خليفة بن خياط العصفري',
  quote_ar: 'جزم بأن له صحبة',
  aspect: 'generation_or_imam',
  basis_kind: 'companion_status_statement',
  source_codes: ['HKG'],
  citation_status: 'cited',
});
assert.equal(naCompanion.ok, true);
if (naCompanion.ok) {
  assert.equal(naCompanion.value.verdict, 'not_applicable');
  assert.equal(naCompanion.value.isCompanion, true);
}

// Narrator assessment row parsing: rejects uncited lexicon labels and unlinked rows
const naUncited = parseNarratorAssessmentRow({
  id: 'narrator-assessment:msd:1',
  narrator_id: 'narrator:rawi:1',
  tradition_id: null,
  kind: 'consensus_summary',
  verdict_canonical: null,
  quote_ar: 'ثقة',
  citation_status: 'not_yet_cited',
});
assert.deepEqual(naUncited, { ok: false, reason: 'uncited' });

const naUnlinked = parseNarratorAssessmentRow({
  id: 'narrator-assessment:hadith-kg:aqwal:100',
  narrator_id: null,
  tradition_id: 'tradition:sunni',
  kind: 'critic_ruling',
  verdict_canonical: null,
  quote_ar: 'أثنى عليه',
  citation_status: 'cited',
});
assert.deepEqual(naUnlinked, { ok: false, reason: 'no_narrator_id' });

console.log('load-assessments unit tests passed.');
