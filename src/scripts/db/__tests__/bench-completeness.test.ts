import assert from 'node:assert/strict';
import {
  evaluateInvariants,
  formatCompletenessReport,
  parseBenchArgs,
  pct,
  type CollectionCompletenessRow,
  type CompletenessReport,
  type NarratorCompletenessSummary,
  type OrphanCheckCounts,
  type TimelineCitationsSummary,
} from '../bench-completeness';

function sampleCollection(overrides: Partial<CollectionCompletenessRow> = {}): CollectionCompletenessRow {
  return {
    collectionId: 'col:1',
    slug: 'sahih-al-bukhari',
    name: 'Sahih al-Bukhari',
    sortKey: 1,
    totalLiveHadiths: 100,
    publicHadiths: 100,
    translations: {
      total: 80,
      sourceProvided: 60,
      machineUnreviewed: 20,
      humanVerified: 0,
      sourceVerified: 0,
      unknownProvenance: 0,
      missing: 20,
      coveragePct: 80,
      missingPct: 20,
    },
    chains: {
      totalLiveChains: 110,
      hadithsWithChain: 95,
      coveragePct: 95,
      checkedByRule: 90,
      uncertain: 10,
      readByModel: 5,
      aiReviewed: 2,
      agentVerified: 1,
      verifiedByReviewer: 2,
      otherOrNull: 0,
    },
    assessments: {
      totalLiveAssessments: 100,
      hadithsWithAssessment: 100,
      coveragePct: 100,
    },
    ...overrides,
  };
}

const sampleNarrators: NarratorCompletenessSummary = {
  totalLiveNarrators: 500,
  byAuthority: { rawi: 400, hadith_kg: 100 },
  bios: { total: 50, published: 30, verified: 10, proposed: 10, coveragePct: 10 },
  lifespans: { total: 250, coveragePct: 50 },
  assessments: { total: 200, distinctNarrators: 150, published: 100, verified: 50, proposed: 50, coveragePct: 30 },
  events: { total: 40, distinctNarrators: 30, distinctEvents: 15, coveragePct: 6 },
};

const sampleTimeline: TimelineCitationsSummary = {
  epochs: { total: 10, cited: 8, publishedFlag: 6, publishedView: 6 },
  historicalEvents: { total: 100, cited: 90, publishedFlag: 50, publishedView: 50 },
  temporalAssertions: { total: 120, byReviewState: { candidate_only: 100, source_verified: 20 } },
  locations: { total: 40, withCoordinates: 35, cited: 30 },
  citations: {
    total: 1000,
    history: 150,
    rijal: 800,
    other: 50,
    byReviewState: { source_verified: 800, candidate_only: 200 },
  },
  bibliographicWorks: 15,
  editions: 15,
};

const zeroOrphans: OrphanCheckCounts = {
  hadithsCollection: 0,
  translationsHadith: 0,
  chainsHadith: 0,
  hadithAssessmentsHadith: 0,
  narratorBiosNarrator: 0,
  narratorAssessmentsNarrator: 0,
  narratorEventsNarrator: 0,
  narratorEventsEvent: 0,
  temporalAssertionsCitation: 0,
  citationsWork: 0,
  editionsWork: 0,
};

// 1. CLI argument parsing
assert.deepEqual(parseBenchArgs([]), { database: 'development', json: false, minTranslationPct: null });
assert.deepEqual(parseBenchArgs(['--database', 'production', '--json']), {
  database: 'production',
  json: true,
  minTranslationPct: null,
});
assert.deepEqual(parseBenchArgs(['--database=production', '--min-translation-pct=75.5']), {
  database: 'production',
  json: false,
  minTranslationPct: 75.5,
});
assert.throws(() => parseBenchArgs(['--database', 'staging']), /development or production/);
assert.throws(() => parseBenchArgs(['--min-translation-pct', '150']), /between 0 and 100/);

// 2. Percentage math
assert.equal(pct(0, 0), 0);
assert.equal(pct(1, 3), 33.33);
assert.equal(pct(2, 3), 66.67);
assert.equal(pct(100, 100), 100);

// 3. Passing mathematical invariants
const passingInvs = evaluateInvariants({
  collections: [sampleCollection()],
  totalLiveHadithsDirect: 100,
  totalPublicHadithsDirect: 100,
  narrators: sampleNarrators,
  timelineAndCitations: sampleTimeline,
  orphans: zeroOrphans,
  minTranslationPct: 75,
});
assert.equal(passingInvs.every((i) => i.passed), true);
assert.ok(passingInvs.some((i) => i.name === 'min_translation_pct_threshold'));

// 4. Failing mathematical invariants
const badCol = sampleCollection({
  translations: {
    total: 80,
    sourceProvided: 50, // sum 70 != 80
    machineUnreviewed: 20,
    humanVerified: 0,
    sourceVerified: 0,
    unknownProvenance: 0,
    missing: 20,
    coveragePct: 80,
    missingPct: 20,
  },
});
const failingInvs = evaluateInvariants({
  collections: [badCol],
  totalLiveHadithsDirect: 105,
  totalPublicHadithsDirect: 100,
  narrators: sampleNarrators,
  timelineAndCitations: sampleTimeline,
  orphans: { ...zeroOrphans, chainsHadith: 3 },
  minTranslationPct: 90,
});
const byName = Object.fromEntries(failingInvs.map((i) => [i.name, i]));
assert.equal(byName.per_collection_hadith_sum.passed, false);
assert.equal(byName.translation_coverage_partition.passed, false);
assert.equal(byName.zero_orphaned_fks.passed, false);
assert.match(byName.zero_orphaned_fks.detail ?? '', /chainsHadith=3/);
assert.equal(byName.min_translation_pct_threshold.passed, false);

// 5. Report formatting
const report: CompletenessReport = {
  database: 'production',
  generatedAt: '2026-11-27T17:20:00.000Z',
  totals: {
    collections: 1,
    totalLiveHadiths: 100,
    totalPublicHadiths: 100,
    totalTranslatedHadiths: 80,
    totalMissingTranslationHadiths: 20,
    translationCoveragePct: 80,
    totalHadithsWithChain: 95,
    chainCoveragePct: 95,
    totalHadithsWithAssessment: 100,
    assessmentCoveragePct: 100,
  },
  collections: [sampleCollection()],
  narrators: sampleNarrators,
  timelineAndCitations: sampleTimeline,
  invariants: passingInvs,
  allPassed: true,
};
const output = formatCompletenessReport(report);
assert.match(output, /COMPLETENESS BENCHMARK \(production\)/);
assert.match(output, /sahih-al-bukhari/);
assert.match(output, /OVERALL: PASS/);

console.log('bench-completeness unit tests passed.');
