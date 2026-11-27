import assert from 'node:assert/strict';
import {
  buildProvenanceSource,
  deriveSourceRecordId,
  normalizeNonEmpty,
  parseTranslationRow,
} from '../load-translations';

// normalizeNonEmpty
assert.equal(normalizeNonEmpty('  hello  '), 'hello');
assert.equal(normalizeNonEmpty('   '), null);
assert.equal(normalizeNonEmpty(null), null);
assert.equal(normalizeNonEmpty(42), null);

// deriveSourceRecordId
assert.equal(deriveSourceRecordId('k6:10105'), '10105');
assert.equal(deriveSourceRecordId('openiti:foo:bar'), 'foo:bar');
assert.equal(deriveSourceRecordId('no_colon'), null);
assert.equal(deriveSourceRecordId('trailing:'), null);

// buildProvenanceSource
assert.equal(
  buildProvenanceSource({
    origin_journal: 'openrouter_hy_mt2_30b_a3b_batch_no_usable_english_2026-11-21.jsonl',
    prompt_version: 'hy-mt2-default-en-prompt-v1',
    prompt_sha256: 'bfe84676c7ff76d354e42a458fa7e66b4a377a21cfb5db6d2f7df879df8ed4af',
    response_provider: null,
    created_at: '2026-11-21T14:46:58Z',
  }),
  'machine_translation_candidates/openrouter_hy_mt2_30b_a3b_batch_no_usable_english_2026-11-21.jsonl|prompt=hy-mt2-default-en-prompt-v1|prompt_sha256=bfe84676c7ff|provider=unrecorded|at=2026-11-21T14:46:58Z',
);
assert.equal(buildProvenanceSource({ origin_journal: '' }), null);

// parseTranslationRow: valid accepted_machine_unreviewed row
const valid = parseTranslationRow({
  record_id: 'k6:10105',
  arabic_sha256: 'd8fa80aa2c3088769eb451528d627e4d2ad2d00c1ec5f8d0f5463df26ad95267',
  text_en: 'And Ali ibn Hujr narrated it to me.',
  translation_source: 'hy-mt2-openrouter-v1',
  translation_model: 'tencent/hy-mt2-30b-a3b',
  translation_review_status: 'machine_unreviewed',
  origin_journal: 'openrouter_hy_mt2_30b_a3b_batch_no_usable_english_2026-11-21.jsonl',
  prompt_version: 'hy-mt2-default-en-prompt-v1',
  prompt_sha256: 'bfe84676c7ff76d354e42a458fa7e66b4a377a21cfb5db6d2f7df879df8ed4af',
  response_provider: null,
  created_at: '2026-11-21T14:46:58Z',
  qa: { status: 'accepted_machine_unreviewed', errors: [] },
});
assert.equal(valid.ok, true);
if (valid.ok) {
  assert.equal(valid.value.id, 'translation:k6:10105:en');
  assert.equal(valid.value.hadithId, 'hadith:k6:10105');
  assert.equal(valid.value.language, 'en');
  assert.equal(valid.value.state, 'machine_unreviewed');
  assert.equal(valid.value.qualityStatus, 'complete');
  assert.equal(valid.value.reviewStateRaw, 'machine_unreviewed');
  assert.equal(valid.value.source, 'hy-mt2-openrouter-v1');
  assert.equal(valid.value.model, 'tencent/hy-mt2-30b-a3b');
  assert.equal(valid.value.sourceRecordId, '10105');
}

// parseTranslationRow: rejects non-accepted QA status
const qaRejected = parseTranslationRow({
  record_id: 'k6:10105',
  arabic_sha256: 'abc',
  text_en: 'Some text',
  translation_source: 'hy-mt2-openrouter-v1',
  translation_model: 'tencent/hy-mt2-30b-a3b',
  origin_journal: 'journal.jsonl',
  qa: { status: 'rejected_arabic_leakage' },
});
assert.deepEqual(qaRejected, { ok: false, reason: 'qa_rejected' });

// parseTranslationRow: rejects missing required provenance / model / text
const missingModel = parseTranslationRow({
  record_id: 'k6:10105',
  arabic_sha256: 'abc',
  text_en: 'Some text',
  translation_source: 'hy-mt2-openrouter-v1',
  origin_journal: 'journal.jsonl',
  qa: { status: 'accepted_machine_unreviewed' },
});
assert.deepEqual(missingModel, { ok: false, reason: 'invalid' });

console.log('load-translations unit tests passed.');
