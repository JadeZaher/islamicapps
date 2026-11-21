/** Focused, DB-free contracts for the curated full-load path. */

import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { gzipSync } from 'node:zlib';
import {
  readAllRawis,
  readJsonl,
  readUnifiedCsv,
  sha256File,
} from '../lib/regen/io';
import {
  preflightCurationManifest,
  preflightRawiDataset,
  preflightUnifiedDataset,
  prepareUnifiedRowForLoad,
  isMeaningfulProvenanceLocator,
  isMeaningfulSourceRecordId,
  isSpecificTranslationModelIdentifier,
  translationModelRequired,
  translationContentIssue,
  validateFullregenBatchSize,
  assertDevIncompleteFullregenTarget,
  assertRailwayProductionFullregenAcknowledgement,
  DISPOSABLE_NEO4J_TEST_ACK,
  DISPOSABLE_NEO4J_TEST_TARGET_MARKER,
  RAILWAY_PRODUCTION_PROJECT_ID,
} from '../lib/regen/mode-fullregen';
import { buildNarratorOptionalProps } from '../lib/regen/load-narrators';
import { buildTier1Resolution } from '../lib/regen/load-chain';
import { assessTemporalPlausibility } from '../lib/regen/temporal-plausibility';
import {
  assertDatasetVersionLifecycleClass,
  assertDatasetVersionLifecycleIdentity,
  inferDatasetVersionReleaseClass,
  inferDatasetVersionLoadPurpose,
} from '../lib/regen/dataset-version';

let passed = 0;

function check(name: string, condition: boolean): void {
  assert.ok(condition, name);
  passed++;
  console.log(`  PASS ${name}`);
}

function csvCell(value: string | number): string {
  return `"${String(value).replace(/"/g, '""')}"`;
}

function csv(headers: string[], rows: Array<Array<string | number>>): string {
  return [headers, ...rows].map((row) =>
    headers.map((_, index) => csvCell(row[index] ?? '')).join(',')
  ).join('\r\n') + '\r\n';
}

async function collect<T>(items: AsyncIterable<T>): Promise<T[]> {
  const result: T[] = [];
  for await (const item of items) result.push(item);
  return result;
}

async function rejects(name: string, work: () => Promise<unknown>, pattern: RegExp): Promise<void> {
  await assert.rejects(work, pattern);
  passed++;
  console.log(`  PASS ${name}`);
}

async function main(): Promise<void> {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'regen-full-load-'));
  try {
    check('DatasetVersion lifecycle class is inferred from consistent immutable markers',
      inferDatasetVersionReleaseClass({
        release_class: 'release',
        release_eligible: true,
        non_release: false,
        load_status: 'complete',
      }) === 'release' &&
      inferDatasetVersionReleaseClass({
        release_class: 'non_release',
        release_eligible: false,
        non_release: true,
        load_status: 'non_release_loaded',
      }) === 'non_release');
    assert.throws(
      () => assertDatasetVersionLifecycleClass({
        release_class: 'release',
        release_eligible: true,
        non_release: false,
      }, 'non_release'),
      /refusing non_release reuse/,
    );
    assert.throws(
      () => assertDatasetVersionLifecycleClass({
        release_class: 'non_release',
        release_eligible: false,
        non_release: true,
      }, 'release'),
      /refusing release reuse/,
    );
    passed += 2;
    console.log('  PASS release DatasetVersion cannot be reused by development/diff');
    console.log('  PASS non-release DatasetVersion cannot be reused by strict release');
    check('DatasetVersion load purpose is inferred from immutable or legacy reason markers',
      inferDatasetVersionLoadPurpose({
        release_class: 'non_release',
        release_eligible: false,
        non_release: true,
        load_purpose: 'dev_fullregen',
      }) === 'dev_fullregen' &&
      inferDatasetVersionLoadPurpose({
        release_eligible: false,
        non_release: true,
        non_release_reason: 'legacy_diff_mode',
      }) === 'legacy_diff' &&
      inferDatasetVersionLoadPurpose({
        release_class: 'non_release',
        release_eligible: false,
        non_release: true,
        load_purpose: 'dev_fullregen',
        non_release_reason: 'legacy_diff_mode',
      }) === null);
    assert.throws(
      () => assertDatasetVersionLifecycleIdentity({
        release_class: 'non_release',
        release_eligible: false,
        non_release: true,
        load_purpose: 'dev_fullregen',
        non_release_reason: 'dev_allow_incomplete_data',
      }, 'non_release', 'legacy_diff'),
      /purpose is dev_fullregen; refusing legacy_diff reuse/,
    );
    passed++;
    console.log('  PASS development fullregen DatasetVersion cannot be reused by legacy diff');
    assert.throws(
      () => assertDatasetVersionLifecycleIdentity({
        release_class: 'non_release',
        release_eligible: false,
        non_release: true,
        load_purpose: 'dev_fullregen',
        non_release_reason: 'arbitrary_unrecognized_reason',
      }, 'non_release', 'dev_fullregen'),
      /reason is arbitrary_unrecognized_reason; expected dev_allow_incomplete_data/,
    );
    check('null legacy reason remains eligible for exact purpose-bound backfill',
      inferDatasetVersionLoadPurpose({
        release_class: 'non_release',
        release_eligible: false,
        non_release: true,
        load_purpose: 'dev_fullregen',
        non_release_reason: null,
      }) === 'dev_fullregen');
    passed++;
    console.log('  PASS arbitrary existing non-release reason is rejected before writes');

    const headers = [
      'id', 'hadith_id', 'source', 'tradition', 'hadith_no', 'chain_indx',
      'text_ar', 'text_en', 'record_id', 'source_record_id', 'provenance_source',
      'translation_status', 'translation_source', 'translation_model',
      'translation_review_status', 'source_work_id', 'provider_book_id',
      'source_display_label',
    ];
    const curatedCsv = csv(headers, [
      [1, 'h1', 'Sahih Bukhari', 'Sunni', '1', '1,2', 'Arabic\nsecond "quote"', 'English, complete',
        'book-a:h1', 'h1', 'fixture-a', 'complete', 'fixture-a', 'model-a', 'human_verified', ''],
      [2, 'h2', 'Al-Kafi', 'Imami', '2', '7', 'نص', 'A complete translation',
        'book-b:h2', 'h2', 'fixture-b', 'complete', 'fixture-b', '', 'source_verified',
        'imami:al-kafi', 'Al-Kafi-Volume-1-Kulayni', 'Al-Kafi'],
    ]);
    const unifiedPath = path.join(tempDir, 'unified.csv');
    fs.writeFileSync(unifiedPath, curatedCsv, 'utf8');

    const rows = await collect(readUnifiedCsv(unifiedPath));
    check('streamed CSV retains multiline quoted text', rows[0]?.text_ar === 'Arabic\nsecond "quote"');
    check('streamed CSV parses escaped quotes and comma fields', rows[0]?.text_en === 'English, complete');
    check('new durable identity and translation metadata are mapped',
      rows[0]?.record_id === 'book-a:h1' && rows[0]?.translation_status === 'complete');

    const plainHash = await sha256File(unifiedPath);
    fs.writeFileSync(`${unifiedPath}.gz`, gzipSync(Buffer.from(curatedCsv, 'utf8')));
    fs.unlinkSync(unifiedPath);
    const gzipHash = await sha256File(unifiedPath);
    check('logical SHA-256 is identical for plain and gzip inputs', plainHash === gzipHash);
    check('gzip fallback streams the same two CSV rows', (await collect(readUnifiedCsv(unifiedPath))).length === 2);

    const strict = await preflightUnifiedDataset(unifiedPath, false);
    check('strict preflight accepts fully curated rows',
      strict.totalRecords === 2 && strict.missingEnglish === 0 && strict.nonCompleteTranslations === 0 &&
      strict.nonReleaseTranslationReviewStatuses === 0);
    check('source-verified translations do not invent a model requirement',
      !translationModelRequired(rows[1]));
    check('strict preflight retains the provider-backed Imami source-work key',
      strict.missingImamiSourceWorkIds === 0 && rows[1]?.source_work_id === 'imami:al-kafi');

    const missingImamiSourceWorkPath = path.join(tempDir, 'missing-imami-source-work.csv');
    fs.writeFileSync(missingImamiSourceWorkPath, csv(headers, [
      [1, 'h1', 'Al-Kafi', 'Imami', '1', '1', 'Arabic', 'English text', 'imami:1', 'h1', 'fixture',
        'complete', 'licensed source edition', '', 'source_verified'],
    ]));
    await rejects('strict release rejects Imami compiler identity inferred only from a display source',
      () => preflightUnifiedDataset(missingImamiSourceWorkPath, false), /missing_imami_source_work_id=1/);
    check('provenance validators reject placeholders while retaining real identities',
      isMeaningfulSourceRecordId('1') &&
      !isMeaningfulSourceRecordId('<missing>') &&
      isMeaningfulProvenanceLocator('Thaqalayn API V2') &&
      !isMeaningfulProvenanceLocator('unknown') &&
      !isMeaningfulProvenanceLocator('x'));
    check('model identifiers require a namespace and specific model component',
      isSpecificTranslationModelIdentifier('google/gemma-4-e4b') &&
      isSpecificTranslationModelIdentifier('manual:claude-opus-4.7') &&
      !isSpecificTranslationModelIdentifier('OpenAI') &&
      !isSpecificTranslationModelIdentifier('model') &&
      !isSpecificTranslationModelIdentifier('x') &&
      !isSpecificTranslationModelIdentifier('model/x'));

    const missingProvenancePath = path.join(tempDir, 'missing-provenance.csv');
    fs.writeFileSync(missingProvenancePath, csv(headers, [
      [1, 'h1', 'Sahih Bukhari', 'Sunni', '1', '1', 'نص', 'English text', 'metadata:1', '', '',
        'complete', '', '', ''],
    ]));
    await rejects('release rows require source and translation provenance fields',
      () => preflightUnifiedDataset(missingProvenancePath, false),
      /missing_source_record_id=1, missing_provenance_source=1.*missing_translation_source=1.*missing_translation_review_status=1/);

    fs.writeFileSync(missingProvenancePath, csv(headers, [
      [1, 'h1', 'Sahih Bukhari', 'Sunni', '1', '1', 'Arabic', 'English text', 'metadata:placeholder',
        '<missing>', 'unknown', 'complete', 'N/A', '', 'human_verified'],
    ]));
    await rejects('placeholder provenance tokens cannot satisfy strict release metadata',
      () => preflightUnifiedDataset(missingProvenancePath, false),
      /missing_source_record_id=1, missing_provenance_source=1.*missing_translation_source=1/);

    const missingModelPath = path.join(tempDir, 'missing-model.csv');
    fs.writeFileSync(missingModelPath, csv(headers, [
      [1, 'h1', 'Sahih Bukhari', 'Sunni', '1', '1', 'نص', 'English text', 'metadata:2', 'h1', 'fixture',
        'complete', 'classical-pipeline', '', 'machine_unreviewed'],
    ]));
    await rejects('machine/model translation provenance requires an exact model identifier',
      () => preflightUnifiedDataset(missingModelPath, false), /missing_required_translation_model=1/);
    fs.writeFileSync(missingModelPath, csv(headers, [
      [1, 'h1', 'Sahih Bukhari', 'Sunni', '1', '1', 'Arabic', 'English text', 'metadata:3', 'h1', 'fixture',
        'complete', 'OpenAI API', 'unknown', 'human_verified'],
    ]));
    await rejects('placeholder model identifiers fail closed for model-sourced text',
      () => preflightUnifiedDataset(missingModelPath, false), /missing_required_translation_model=1/);

    const manifestPath = path.join(tempDir, 'curation_manifest.json');
    fs.writeFileSync(unifiedPath, curatedCsv, 'utf8');
    const imamiRegistryPath = path.join(tempDir, 'imami_source_work_registry.json');
    fs.writeFileSync(imamiRegistryPath, JSON.stringify({
      schema_version: 1,
      source_works: [{
        source_work_id: 'imami:al-kafi',
        canonical_source: 'Al-Kafi',
        compiler: 'Muhammad ibn Yaqub al-Kulayni',
        provider_book_ids: ['Al-Kafi-Volume-1-Kulayni'],
      }],
      non_provider_source_works: [],
    }));
    const rawiInputPath = path.join(tempDir, 'all_rawis.csv');
    fs.writeFileSync(rawiInputPath, 'scholar_indx,name\n1,Fixture\n');
    const sourceRegistryPath = path.join(process.cwd(), 'src/lib/constants/sources.ts');
    const rawHash = (filePath: string): string =>
      createHash('sha256').update(fs.readFileSync(filePath)).digest('hex');
    const inputBinding = (filePath: string) => ({
      bytes: fs.statSync(filePath).size,
      sha256: rawHash(filePath),
    });
    const relativeInput = (filePath: string): string =>
      path.relative(tempDir, filePath).replace(/\\/g, '/');
    const handoffPaths = {
      unifiedPath,
      rawiPath: rawiInputPath,
      imamiSourceWorkRegistryPath: imamiRegistryPath,
      sourceRegistryPath,
    };
    fs.writeFileSync(manifestPath, JSON.stringify({
      ready_for_full_load: false,
      record_count: 2,
      stable_record_id_count: 2,
      release_blockers: { translation: 1 },
    }));
    await rejects('release loading requires an explicit ready curation manifest',
      () => preflightCurationManifest(manifestPath, strict, plainHash, false, handoffPaths),
      /not release-ready/);
    const passedGate = { passed: true, counts: {} };
    const readyManifest = {
      schema_version: 2,
      dataset_schema: headers,
      candidate_content_sha256: 'a'.repeat(64),
      ready_for_full_load: true,
      published_dataset: {
        logical_sha256: plainHash,
        csv: {
          path: path.basename(unifiedPath),
          bytes: fs.statSync(unifiedPath).size,
          sha256: plainHash,
        },
        gzip: {
          path: path.basename(`${unifiedPath}.gz`),
          bytes: fs.statSync(`${unifiedPath}.gz`).size,
          sha256: rawHash(`${unifiedPath}.gz`),
          logical_sha256: plainHash,
        },
      },
      record_count: 2,
      stable_record_id_count: 2,
      tradition_counts: { Sunni: 1, Imami: 1, Ibadi: 0, Zaydi: 0 },
      release_blockers: {},
      full_load_gates: {
        chain: passedGate,
        citation_bound_evidence: passedGate,
        corpus_nonempty: passedGate,
        corpus_shape: passedGate,
        curation_backlog: passedGate,
        provenance: passedGate,
        source_registry: passedGate,
        text_and_content: passedGate,
        translation_review: passedGate,
      },
      inputs: {
        [relativeInput(rawiInputPath)]: inputBinding(rawiInputPath),
        [relativeInput(imamiRegistryPath)]: inputBinding(imamiRegistryPath),
        [relativeInput(sourceRegistryPath)]: inputBinding(sourceRegistryPath),
      },
    };
    fs.writeFileSync(manifestPath, JSON.stringify(readyManifest));
    await preflightCurationManifest(manifestPath, strict, plainHash, false, handoffPaths);
    check('ready manifest independently binds gates, inputs, content, and Imami work identity', true);
    fs.writeFileSync(manifestPath, JSON.stringify({
      ...readyManifest,
      full_load_gates: { ...readyManifest.full_load_gates, chain: { passed: false } },
    }));
    await rejects('summary ready boolean cannot hide a failed full-load gate',
      () => preflightCurationManifest(manifestPath, strict, plainHash, false, handoffPaths),
      /full_load_gates\.chain\.passed/);
    fs.writeFileSync(manifestPath, JSON.stringify(readyManifest));

    const invalidPath = path.join(tempDir, 'invalid.csv');
    fs.writeFileSync(invalidPath, csv(headers, [
      [1, 'h1', 'Sahih Bukhari', 'Sunni', '1', '', '', 'English', 'bad:1', 'h1', 'fixture',
        'complete', 'fixture', '', 'human_verified'],
      [2, 'h2', 'Sahih Bukhari', 'Sunni', '2', '', 'نص', '', 'bad:2', 'h2', 'fixture',
        'missing', '', '', 'unreviewed'],
    ]));
    await rejects('strict preflight blocks missing Arabic/English and non-complete status',
      () => preflightUnifiedDataset(invalidPath, false), /curation preflight failed before DB mutation/);

    const mislabeledTranslationPath = path.join(tempDir, 'mislabeled-translation.csv');
    fs.writeFileSync(mislabeledTranslationPath, csv(headers, [
      [1, 'h1', 'Sahih Bukhari', 'Sunni', '1', '', 'نفس النص', 'نفس النص', 'bad-translation:1', 'h1',
        'fixture', 'complete', '', '', 'reviewed'],
    ]));
    await rejects('a complete label cannot hide Arabic copied into the English field',
      () => preflightUnifiedDataset(mislabeledTranslationPath, false), /translation_status_not_complete=1/);
    const mislabeledRows = await collect(readUnifiedCsv(mislabeledTranslationPath));
    check('development override persists the detected translation failure status',
      prepareUnifiedRowForLoad(mislabeledRows[0], true).translation_status === 'copied_input');
    check('translation QA mirrors placeholder, normalized-copy, Arabic-leakage, and language checks',
      translationContentIssue({ text_en: 'Draft TODO translation', text_ar: 'نص' }) === 'placeholder' &&
      translationContentIssue({ text_en: 'Draft TODO_1 translation', text_ar: 'نص' }) === 'placeholder' &&
      translationContentIssue({ text_en: 'Draft 1PLACEHOLDER2 translation', text_ar: 'نص' }) === 'placeholder' &&
      translationContentIssue({ text_en: 'نص!!!', text_ar: 'نص' }) === 'copied_input' &&
      translationContentIssue({ text_en: 'English with نص', text_ar: 'متن' }) === 'arabic_leakage' &&
      translationContentIssue({ text_en: 'English Текст текст текст', text_ar: 'متن' }) === 'wrong_language');

    const shortTranslationPath = path.join(tempDir, 'short-translation.csv');
    fs.writeFileSync(shortTranslationPath, csv(headers, [
      [1, 'h1', 'Sahih Bukhari', 'Sunni', '1', '1', 'كلوا', 'Eat.', 'short:1', 'h1', 'fixture',
        'complete', 'fixture', '', 'human_verified'],
    ]));
    check('genuine short translations are not mislabeled as placeholders',
      (await preflightUnifiedDataset(shortTranslationPath, false)).nonCompleteTranslations === 0);

    const unresolvedReviewPath = path.join(tempDir, 'unresolved-review.csv');
    fs.writeFileSync(unresolvedReviewPath, csv(headers, [
      [1, 'h1', 'Sahih Bukhari', 'Sunni', '1', '1', 'Arabic', 'English text', 'review:1', 'h1', 'fixture',
        'complete', 'licensed-source', '', 'source_provided'],
    ]));
    await rejects('bare source-provided review state is not a publication verification',
      () => preflightUnifiedDataset(unresolvedReviewPath, false),
      /nonrelease_translation_review_status=1/);

    const suspiciousShortPath = path.join(tempDir, 'suspicious-short.csv');
    fs.writeFileSync(suspiciousShortPath, csv(headers, [
      [1, 'h1', 'Sahih Bukhari', 'Sunni', '1', '', 'حدثنا '.repeat(20), "Nafi'", 'short:2', 'h1', 'fixture',
        'complete', 'fixture', '', 'reviewed'],
    ]));
    await rejects('short English against long Arabic is explicitly release-blocking',
      () => preflightUnifiedDataset(suspiciousShortPath, false), /translation_status_not_complete=1/);

    const duplicatePath = path.join(tempDir, 'duplicate.csv');
    fs.writeFileSync(duplicatePath, csv(headers, [
      [1, 'h1', 'Book A', 'Sunni', '1', '', 'نص', 'English', 'duplicate', 'h1', 'fixture', 'complete', '', '', ''],
      [2, 'h2', 'Book A', 'Sunni', '2', '', 'نص', 'English', 'duplicate', 'h2', 'fixture', 'complete', '', '', ''],
    ]));
    await rejects('duplicate durable identities remain blocked under the dev override',
      () => preflightUnifiedDataset(duplicatePath, true), /duplicate durable record_id/);

    const invalidStatusPath = path.join(tempDir, 'invalid-status.csv');
    fs.writeFileSync(invalidStatusPath, csv(headers, [
      [1, 'h1', 'Book A', 'Sunni', '1', '', 'نص', 'English', 'bad-status:1', 'h1', 'fixture',
        'pending_review', '', '', ''],
    ]));
    await rejects('unknown translation statuses are rejected even in development',
      () => preflightUnifiedDataset(invalidStatusPath, true), /outside the supported vocabulary/);

    const malformedChainPath = path.join(tempDir, 'malformed-chain.csv');
    fs.writeFileSync(malformedChainPath, csv(headers, [
      [1, 'h1', 'Book A', 'Sunni', '1', '1,not-an-id', 'نص', 'English', 'bad-chain:1', 'h1',
        'fixture', 'complete', '', '', ''],
    ]));
    await rejects('malformed chain indices fail during the read-only gate',
      () => preflightUnifiedDataset(malformedChainPath, true), /Invalid chain_indx token/);

    const invalidTraditionPath = path.join(tempDir, 'invalid-tradition.csv');
    fs.writeFileSync(invalidTraditionPath, csv(headers, [
      [1, 'h1', 'Book A', 'Unknown School', '1', '', 'نص', 'English', 'bad-tradition:1', 'h1',
        'fixture', 'complete', '', '', ''],
    ]));
    await rejects('unsupported traditions cannot silently default to Sunni',
      () => preflightUnifiedDataset(invalidTraditionPath, true), /unsupported tradition/);

    const invalidGradeHeaders = [...headers, 'grade_tradition'];
    const invalidGradeTraditionPath = path.join(tempDir, 'invalid-grade-tradition.csv');
    fs.writeFileSync(invalidGradeTraditionPath, csv(invalidGradeHeaders, [
      [1, 'h1', 'Sahih Bukhari', 'Sunni', '1', '1', 'نص', 'English text', 'grade:1', 'h1',
        'fixture', 'complete', '', '', 'reviewed', '', '', '', 'Unmapped School'],
    ]));
    await rejects('unsupported grade traditions fail during read-only preflight',
      () => preflightUnifiedDataset(invalidGradeTraditionPath, true), /unsupported grade_tradition/);

    const conflictingSourcePath = path.join(tempDir, 'conflicting-source.csv');
    fs.writeFileSync(conflictingSourcePath, csv(headers, [
      [1, 'h1', 'Cross-Tradition Book', 'Sunni', '1', '', 'نص', 'English text', 'source:1', 'h1',
        'fixture', 'complete', '', '', 'reviewed'],
      [2, 'h2', 'Cross-Tradition Book', 'Imami', '2', '', 'نص', 'English text', 'source:2', 'h2',
        'fixture', 'complete', '', '', 'reviewed'],
    ]));
    await rejects('one source cannot silently acquire conflicting traditions',
      () => preflightUnifiedDataset(conflictingSourcePath, true), /source_tradition_conflicts=1/);

    const registryMismatchPath = path.join(tempDir, 'registry-mismatch.csv');
    fs.writeFileSync(registryMismatchPath, csv(headers, [
      [1, 'h1', 'Al-Kafi', 'Sunni', '1', '', 'نص', 'English text', 'source:3', 'h1',
        'fixture', 'complete', '', '', 'reviewed'],
    ]));
    await rejects('registered source tradition mismatches fail before writes',
      () => preflightUnifiedDataset(registryMismatchPath, true), /source_registry_mismatches=1/);

    const unregisteredSourcePath = path.join(tempDir, 'unregistered-source.csv');
    fs.writeFileSync(unregisteredSourcePath, csv(headers, [
      [1, 'h1', 'Unregistered Imami Work', 'Imami', '1', '', 'نص', 'English text', 'source:4', 'h1',
        'fixture', 'complete', '', '', 'reviewed'],
    ]));
    await rejects('unregistered work/compiler identities block a curated release',
      () => preflightUnifiedDataset(unregisteredSourcePath, false), /unregistered_source_rows=1/);
    const devUnregistered = await preflightUnifiedDataset(unregisteredSourcePath, true);
    check('development preserves an unregistered source explicit tradition',
      devUnregistered.sourceTraditions.get('Unregistered Imami Work') === 'Imami');

    const emptyChainPath = path.join(tempDir, 'empty-chain.csv');
    fs.writeFileSync(emptyChainPath, csv(headers, [
      [1, 'h1', 'Sahih Bukhari', 'Sunni', '1', '', 'نص', 'English text', 'chain:empty', 'h1',
        'fixture', 'complete', '', '', 'reviewed'],
    ]));
    await rejects('a release cannot represent an empty sanad as a complete Chain',
      () => preflightUnifiedDataset(emptyChainPath, false), /missing_chain_indx=1/);

    const legacyHeaders = ['id', 'hadith_id', 'source', 'tradition', 'hadith_no', 'text_ar', 'text_en'];
    const legacyPath = path.join(tempDir, 'legacy.csv');
    fs.writeFileSync(legacyPath, csv(legacyHeaders, [
      [1, 'legacy-1', 'Sahih Bukhari', 'Sunni', '1', 'نص', 'English translation'],
    ]));
    await rejects('legacy schema requires an explicit dev-only override',
      () => preflightUnifiedDataset(legacyPath, false), /missing_record_id=1/);
    const legacyReport = await preflightUnifiedDataset(legacyPath, true);
    check('dev override reports every derived legacy identity', legacyReport.legacyRecordIdsDerived === 1);
    const legacyRows = await collect(readUnifiedCsv(legacyPath));
    const preparedA = prepareUnifiedRowForLoad(legacyRows[0], true);
    const replayRows = await collect(readUnifiedCsv(legacyPath));
    const preparedB = prepareUnifiedRowForLoad(replayRows[0], true);
    check('legacy dev identity is deterministic and translation status is explicit',
      preparedA.record_id === preparedB.record_id && preparedA.translation_status === 'complete');

    const jsonlPath = path.join(tempDir, 'records.jsonl');
    fs.writeFileSync(`${jsonlPath}.gz`, gzipSync('{"id":1}\nnot-json\n{"id":2}\n'));
    const originalWarn = console.warn;
    let jsonRows: Array<{ id: number }>;
    try {
      console.warn = () => undefined;
      jsonRows = await collect(readJsonl<{ id: number }>(jsonlPath));
    } finally {
      console.warn = originalWarn;
    }
    check('gzip JSONL is streamed and malformed lines are skipped',
      jsonRows.map((row) => row.id).join(',') === '1,2');

    const rawisPath = path.join(tempDir, 'rawis.csv');
    const rawisCsv = csv(
      ['scholar_indx', 'name', 'name_arabic', 'bio', 'grade', 'birth_date', 'birth_date_hijri', 'death_date_hijri'],
      [
        [7, 'Narrator Seven', 'N/A', 'NA', 'thiqa', '', 20, 88],
        [8, 'Narrator Eight', '', '', '', "['20 BH']", 20, 90],
        [9, 'Narrator Nine', '', '', '', '', '30 BH', 91],
      ],
    );
    fs.writeFileSync(`${rawisPath}.gz`, gzipSync(rawisCsv));
    const rawis = await readAllRawis(rawisPath);
    const rawi = rawis.get(7)!;
    const optionalProps = buildNarratorOptionalProps(rawi);
    check('absent narrator metadata remains absent from sparse Neo4j updates',
      !('bio' in optionalProps) && !('name_arabic' in optionalProps) && !('name_english' in optionalProps));
    check('available narrator dates and source grade remain loadable',
      optionalProps.birth_date_hijri === 20 && optionalProps.death_date_hijri === 88 && optionalProps._raw_grade === 'thiqa');
    check('exact numeric years may use BH context while qualified canonical tokens remain raw',
      rawis.get(8)?.birth_date_hijri === -20 &&
      rawis.get(9)?.birth_date_hijri === null &&
      rawis.get(9)?.birth_date_hijri_raw === '30 BH');
    check('qualified canonical dates are preserved without parseInt truncation',
      buildNarratorOptionalProps(rawis.get(9)!).birth_date_hijri_raw === '30 BH');
    preflightRawiDataset(rawis);
    check('consistent narrator lifetime dates pass read-only preflight', true);
    await rejects('narrator death-before-birth is rejected before writes', async () => {
      preflightRawiDataset(new Map([
        [7, { ...rawis.get(7)!, birth_date_hijri: 100, death_date_hijri: 90 }],
      ]));
    }, /death_before_birth_hijri=1/);
    await rejects('inconsistent canonical AH/CE pairs are rejected before writes', async () => {
      preflightRawiDataset(new Map([
        [7, { ...rawis.get(7)!, birth_date_hijri: 20, birth_date_gregorian: 1900 }],
      ]));
    }, /inconsistent_birth_calendar_pairs=1/);
    check('temporal plausibility uses lifetime overlap rather than an inverted death-gap proxy',
      assessTemporalPlausibility(rawis.get(7), rawis.get(8)).plausibility === 'plausible' &&
      assessTemporalPlausibility(
        { ...rawis.get(7)!, birth_date_hijri: 100 },
        rawis.get(8),
      ).plausibility === 'impossible');

    await rejects('strict preflight blocks chain indices absent from the rawi vocabulary',
      () => preflightUnifiedDataset(unifiedPath, false, rawis), /unknown_chain_indx_references=2/);
    const unresolvedReport = await preflightUnifiedDataset(unifiedPath, true, rawis);
    check('development preflight reports every unresolved chain reference',
      unresolvedReport.missingNarratorReferences === 2 &&
      unresolvedReport.missingNarratorIds.join(',') === '1,2');
    const devTier1 = buildTier1Resolution(rows[0], rawis)[0];
    check('development loads retain missing chain IDs as explicit NameMentions',
      devTier1?.resolved.length === 0 && devTier1?.mentions.length === 2);

    check('CLI batch size is honored', validateFullregenBatchSize(37) === 37);
    assert.throws(() => validateFullregenBatchSize(0), /positive integer/);
    passed++;
    console.log('  PASS invalid batch sizes fail before loading');
    assert.throws(
      () => assertRailwayProductionFullregenAcknowledgement(
        'bolt://switchyard.proxy.rlwy.net:12345',
        false,
        'wrong-project',
        {},
      ),
      new RegExp(RAILWAY_PRODUCTION_PROJECT_ID),
    );
    passed++;
    console.log('  PASS Railway release fullregen requires exact project cost acknowledgement');
    assert.doesNotThrow(() => assertRailwayProductionFullregenAcknowledgement(
      'bolt://switchyard.proxy.rlwy.net:12345',
      false,
      RAILWAY_PRODUCTION_PROJECT_ID,
      {},
    ));
    assert.doesNotThrow(() => assertRailwayProductionFullregenAcknowledgement(
      'bolt://localhost:7687',
      false,
      undefined,
      {},
    ));
    assert.throws(() => assertRailwayProductionFullregenAcknowledgement(
      'bolt://switchyard.proxy.rlwy.net:12345',
      true,
      'wrong-project',
      {},
    ), /forbidden for every Railway target/);
    assert.throws(() => assertRailwayProductionFullregenAcknowledgement(
      'bolt://switchyard.proxy.rlwy.net:12345',
      true,
      RAILWAY_PRODUCTION_PROJECT_ID,
      {},
    ), /forbidden for every Railway target/);
    assert.throws(() => assertRailwayProductionFullregenAcknowledgement(
      'bolt://neo4j:7687',
      false,
      RAILWAY_PRODUCTION_PROJECT_ID,
      { projectId: 'wrong-project', environmentId: 'railway-environment' },
    ), /runtime project identity mismatch/);
    assert.doesNotThrow(() => assertRailwayProductionFullregenAcknowledgement(
      'bolt://neo4j:7687',
      false,
      RAILWAY_PRODUCTION_PROJECT_ID,
      { projectId: RAILWAY_PRODUCTION_PROJECT_ID, environmentId: 'railway-environment' },
    ));
    passed += 6;
    console.log('  PASS exact Railway acknowledgement gates release while every Railway dev override is refused');

    const disposableDevEnvironment = {
      NODE_ENV: 'development',
      NEO4J_URL: 'bolt://127.0.0.1:7687',
      NEO4J_USERNAME: 'neo4j-test',
      NEO4J_PASSWORD: 'test-password',
      NEO4J_TEST_URI: 'bolt://127.0.0.1:7687',
      NEO4J_TEST_USERNAME: 'neo4j-test',
      NEO4J_TEST_PASSWORD: 'test-password',
      RUN_LIVE_NEO4J_TESTS: '1',
      NEO4J_TEST_TARGET_MARKER: DISPOSABLE_NEO4J_TEST_TARGET_MARKER,
      NEO4J_TEST_DISPOSABLE_ACK: DISPOSABLE_NEO4J_TEST_ACK,
    };
    assert.doesNotThrow(() => assertDevIncompleteFullregenTarget(true, disposableDevEnvironment));
    assert.throws(() => assertDevIncompleteFullregenTarget(true, {
      ...disposableDevEnvironment,
      NEO4J_URL: 'bolt://example.com:7687',
      NEO4J_TEST_URI: 'bolt://example.com:7687',
    }), /loopback/);
    assert.throws(() => assertDevIncompleteFullregenTarget(true, {
      ...disposableDevEnvironment,
      NEO4J_URL: 'neo4j://127.0.0.1:7687',
      NEO4J_TEST_URI: 'neo4j://127.0.0.1:7687',
    }), /direct bolt/);
    assert.throws(() => assertDevIncompleteFullregenTarget(true, {
      ...disposableDevEnvironment,
      NODE_ENV: 'production',
    }), /forbidden in production or remote/);
    passed += 4;
    console.log('  PASS incomplete-data fullregen is confined to an explicitly acknowledged loopback test target');

    const modeSource = fs.readFileSync(path.join(process.cwd(), 'src/scripts/lib/regen/mode-fullregen.ts'), 'utf8');
    const ioSource = fs.readFileSync(path.join(process.cwd(), 'src/scripts/lib/regen/io.ts'), 'utf8');
    const batchSource = fs.readFileSync(path.join(process.cwd(), 'src/scripts/lib/regen/batch-loaders.ts'), 'utf8');
    const versionSource = fs.readFileSync(path.join(process.cwd(), 'src/scripts/lib/regen/dataset-version.ts'), 'utf8');
    const entitySource = fs.readFileSync(path.join(process.cwd(), 'src/scripts/lib/regen/entity-resolution.ts'), 'utf8');
    const temporalSource = fs.readFileSync(path.join(process.cwd(), 'src/scripts/lib/regen/temporal-plausibility.ts'), 'utf8');
    const graphSource = fs.readFileSync(path.join(process.cwd(), 'src/app/actions/graph-actions.ts'), 'utf8');
    const narratorPageSource = fs.readFileSync(path.join(process.cwd(), 'src/app/narrator/[id]/page.tsx'), 'utf8');
    const neo4jTestEnvSource = fs.readFileSync(path.join(process.cwd(), 'src/scripts/__tests__/neo4j-test-env.ts'), 'utf8');
    const historySeedSource = fs.readFileSync(path.join(process.cwd(), 'src/scripts/seed-historical-data.ts'), 'utf8');
    const rowLoaderSource = fs.readFileSync(path.join(process.cwd(), 'src/scripts/lib/regen/load-hadith.ts'), 'utf8');
    const diffSource = fs.readFileSync(path.join(process.cwd(), 'src/scripts/lib/regen/mode-diff.ts'), 'utf8');
    check('fullregen does not replay multi-transaction slices',
      !modeSource.includes('flushSlice') && !modeSource.includes('loadChainsBatchFresh'));
    check('fullregen bounds batches by UTF-8 payload as well as row count',
      modeSource.includes('MAX_BUFFER_PAYLOAD_BYTES') && modeSource.includes('bufferPayloadBytes') &&
      modeSource.includes('rowPayloadBytes > MAX_BUFFER_PAYLOAD_BYTES'));
    check('DatasetVersion activation is deferred until all load phases pass',
      modeSource.includes('activateImmediately: false') && modeSource.includes('activateDatasetVersion(dvId)') &&
      versionSource.includes("target.load_status = 'complete'"));
    check('development override is machine-marked and cannot activate a complete version',
      modeSource.includes('markDatasetVersionNonReleaseLoaded(') &&
      modeSource.includes("'dev_fullregen'") &&
      modeSource.includes("'dev_allow_incomplete_data'") &&
      modeSource.includes('Development Full Regen Finished (Non-Release)') &&
      versionSource.includes("dv.load_status = 'non_release_loaded'") &&
      versionSource.includes('target.release_eligible') &&
      versionSource.includes('target.non_release'));
    check('legacy diff override cannot activate or deactivate release versions',
      diffSource.includes('assertDevIncompleteFullregenTarget(args.devAllowIncompleteData)') &&
      diffSource.includes("releaseEligible: false") &&
      diffSource.includes("loadPurpose: 'legacy_diff'") &&
      diffSource.includes("markDatasetVersionNonReleaseLoaded(dvId, 'legacy_diff', 'legacy_diff_mode')") &&
      !diffSource.includes('deactivateOtherVersions'));
    const cleanTargetGateCall = modeSource.indexOf(
      'const graphIdentity = await preflightExistingGraphIdentity(',
    );
    const railwayCostGateCall = modeSource.lastIndexOf(
      'assertRailwayProductionFullregenAcknowledgement(',
    );
    check('Railway cost acknowledgement follows local curation guards and precedes DB access',
      railwayCostGateCall > modeSource.indexOf('await preflightCurationManifest(') &&
      railwayCostGateCall < modeSource.indexOf('await withFullregenLease('));
    check('validated and loaded rows come from one content-addressed immutable snapshot',
      modeSource.includes('withImmutableHadithSnapshot(') &&
      modeSource.includes('copyFile(sourcePath, snapshotPath, fs.constants.COPYFILE_EXCL)') &&
      modeSource.includes('preflightUnifiedDataset(\n        hadithSnapshotPath,') &&
      modeSource.includes('readUnifiedCsv(hadithSnapshotPath)') &&
      modeSource.includes('Immutable load snapshot hash changed before finalization'));
    check('fullregen holds one uniqueness-backed database lease across clean-target check and writes',
      versionSource.includes('CREATE CONSTRAINT fullregen_lease_name_unique IF NOT EXISTS') &&
      versionSource.includes('owner_token = $ownerToken') &&
      !versionSource.includes('OR lease.expires_at < datetime()') &&
      versionSource.includes('WHERE lease.expires_at > datetime()') &&
      versionSource.includes("MATCH (lease:FullregenLease { name: $leaseName, owner_token: $ownerToken })") &&
      versionSource.includes('clearInterval(timer)') &&
      modeSource.indexOf('await withFullregenLease(') < cleanTargetGateCall &&
      modeSource.includes('await lease.assertHeld()'));
    check('release fullregen requires a clean blue-green target before schema or data mutation',
      modeSource.includes('preflightExistingGraphIdentity(') &&
      modeSource.includes('clean/blue-green target') &&
      cleanTargetGateCall >= 0 && cleanTargetGateCall < modeSource.indexOf('await initializeSchema()'));
    check('unregistered sources use validated row traditions without a Sunni fallback',
      !modeSource.includes('will default to Sunni') &&
      !ioSource.includes("TRADITION_MAP[key] ?? 'Sunni'") &&
      !batchSource.includes('defaulting tradition to Sunni') &&
      !rowLoaderSource.includes('defaulting tradition to Sunni') &&
      batchSource.includes('const sourceTradition = rowTradition'));
    check('Hadith/Chain/Assessment writes use record_id-derived identities',
      batchSource.includes('MERGE (h:Hadith { record_id: row.record_id })') &&
      batchSource.includes("'record_id'") && batchSource.includes('chainKeysByRow'));
    check('chain edges are position-idempotent and never bridge unresolved gaps',
      batchSource.includes('INCLUDES { position: e.position }') &&
      batchSource.includes('teacher.position !== student.position + 1'));
    check('entity-resolution vocabulary indexes are cached once per rawi map',
      entitySource.includes('WeakMap<Map<number, RawiRecord>, RawiLookupIndexes>'));
    check('temporal annotations use bounded UNWIND writes instead of one transaction per edge',
      temporalSource.includes('TEMPORAL_WRITE_BATCH_SIZE') &&
      temporalSource.includes('UNWIND $updates AS update') &&
      temporalSource.includes('LIMIT $limit'));
    check('unknown narrator lifetimes cannot select the entire event catalog',
      graphSource.includes('(birthYear IS NOT NULL OR deathYear IS NOT NULL)') &&
      graphSource.includes('coalesce(e.start_year_hijri, e.year_hijri) AS eventStart') &&
      graphSource.includes('coalesce(e.end_year_hijri, e.start_year_hijri, e.year_hijri) AS eventEnd') &&
      graphSource.includes('n.birth_date_hijri') && graphSource.includes('n.death_date_hijri'));
    check('narrator action exposes typed AH/CE aliases without asserting legacy reliability',
      graphSource.includes('Promise<EnhancedNarratorDetails | null>') &&
      graphSource.includes('birth_year_gregorian: birthGregorian') &&
      graphSource.includes('death_year_gregorian: deathGregorian') &&
      narratorPageSource.includes('narratorDetails.reliability &&') &&
      !narratorPageSource.includes("NarratorClientPageProps['narratorDetails']"));
    check('all live graph scans refuse Railway and application endpoints before write-only gates',
      neo4jTestEnvSource.indexOf('if (isRailwayHost(host))') >= 0 &&
      neo4jTestEnvSource.indexOf('if (isRailwayHost(host))') < neo4jTestEnvSource.indexOf('if (options.writes)') &&
      neo4jTestEnvSource.indexOf('live tests refuse the application NEO4J_URL endpoint') <
        neo4jTestEnvSource.indexOf('if (options.writes)'));
    check('historical seed IDs are deterministic and remain explicitly unverified',
      !historySeedSource.includes('randomUUID') && historySeedSource.includes("stableSeedId('location'") &&
      historySeedSource.includes("stableSeedId('historical-event'") &&
      historySeedSource.includes("verification_status = 'unverified_seed'") &&
      historySeedSource.includes("MATCH (l:Location {id: $location_id})"));
    check('historical event seed reruns cannot overwrite reviewed or published claims',
      historySeedSource.includes("e.verification_status = 'unverified_seed'") &&
      historySeedSource.includes('e.publication_ready = false AS seed_editable') &&
      historySeedSource.includes('FOREACH (_ IN CASE WHEN seed_editable THEN [1] ELSE [] END |'));

    console.log(`\n${passed} focused full-load hardening checks passed.`);
  } finally {
    fs.rmSync(tempDir, { recursive: true, force: true });
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
