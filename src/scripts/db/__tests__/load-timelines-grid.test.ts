import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import {
  BATCH_SIZE,
  buildTimelinesLoadPlan,
  classifyHistoricalEventTrack,
  CORE_TIMELINE_TRACKS,
  parseExternalTraditionParallelRow,
  parseLoaderArgs,
  parseNarratorAffiliationRow,
  parseNarratorResidenceRow,
  parsePlaceSnapshotRow,
  VALID_TRACK_CATEGORIES,
  VALID_TRACK_SCOPES,
} from '../load-timelines-grid';

async function runTests(): Promise<void> {
  // 1. Core timeline tracks (7 Phase 1 + 4 Phase 4 = 11)
  assert.equal(BATCH_SIZE, 500);
  assert.equal(CORE_TIMELINE_TRACKS.length, 11);
  const trackIds = new Set(CORE_TIMELINE_TRACKS.map((t) => t.id));
  const trackSlugs = new Set(CORE_TIMELINE_TRACKS.map((t) => t.slug));
  assert.equal(trackIds.size, 11);
  assert.equal(trackSlugs.size, 11);
  for (const requiredId of [
    'track:social_gender_norms',
    'track:myths_literature_art',
    'track:food_agriculture_ecology',
    'track:economic_tensions',
  ]) {
    assert.ok(trackIds.has(requiredId), `missing Phase 4 track: ${requiredId}`);
  }
  for (const t of CORE_TIMELINE_TRACKS) {
    assert.ok(VALID_TRACK_CATEGORIES.has(t.category), `invalid category: ${t.category}`);
    assert.ok(VALID_TRACK_SCOPES.has(t.scope), `invalid scope: ${t.scope}`);
  }

  // 2. Historical event track classification
  assert.equal(
    classifyHistoricalEventTrack({ title: 'Adoption of Samarkand Paper in Baghdad', category: 'CULTURAL' }),
    'track:technological',
  );
  assert.equal(
    classifyHistoricalEventTrack({ title: 'Darb Zubaydah Pilgrimage Route', category: 'ECONOMIC' }),
    'track:trade_pilgrimage',
  );
  assert.equal(
    classifyHistoricalEventTrack({ title: 'Founding of Kufa', category: 'POLITICAL' }),
    'track:demographic_shift',
  );
  assert.equal(
    classifyHistoricalEventTrack({ title: 'The Mihnah Inquisition', category: 'POLITICAL' }),
    'track:legal_theological',
  );
  assert.equal(
    classifyHistoricalEventTrack({ title: 'Bayt al-Hikma Translation Movement', category: 'CULTURAL' }),
    'track:intellectual_movement',
  );
  assert.equal(classifyHistoricalEventTrack({ title: 'Battle of Siffin', category: 'MILITARY' }), 'track:political');
  assert.equal(classifyHistoricalEventTrack({ title: 'Unknown Event', category: null }), 'track:world_event');

  // 3. Row parsers (valid + invalid)
  const validSnapshot = parsePlaceSnapshotRow({
    id: 'ps:kufa:40',
    location_id: 'loc:kufa',
    year_min: 35,
    year_max: 45,
    polity_or_ruler: 'Rashidun Caliphate',
    dominant_schools: ['Kufan ra-y'],
    religious_communities: { muslim: 'majority', christian: 'present' },
    languages: ['Arabic', 'Aramaic'],
    social_norms: { kinship: 'tribal_quarter_compounds' },
    material_culture: { coinage: 'arab_sasanian_drachms' },
    citation_id: 'cit:1',
    review_state: 'source_verified',
  });
  assert.ok(validSnapshot);
  assert.equal(validSnapshot.locationId, 'loc:kufa');
  assert.equal(validSnapshot.reviewState, 'source_verified');
  assert.deepEqual(validSnapshot.socialNorms, { kinship: 'tribal_quarter_compounds' });
  assert.deepEqual(validSnapshot.materialCulture, { coinage: 'arab_sasanian_drachms' });

  // Pre-Hijri / negative year range support
  const preHijriSnapshot = parsePlaceSnapshotRow({
    id: 'ps:mecca:pre',
    location_id: 'loc:mecca',
    year_min: -30,
    year_max: -1,
    citation_id: 'cit:pre',
  });
  assert.ok(preHijriSnapshot);
  assert.equal(preHijriSnapshot.yearMin, -30);
  assert.equal(preHijriSnapshot.socialNorms, null);
  assert.equal(preHijriSnapshot.materialCulture, null);
  assert.equal(
    parsePlaceSnapshotRow({
      id: 'ps:bad-social-norms',
      location_id: 'loc:kufa',
      social_norms: ['not-an-object'],
      citation_id: 'cit:1',
    }),
    null,
  );
  assert.equal(
    parsePlaceSnapshotRow({
      id: 'ps:bad-material-culture',
      location_id: 'loc:kufa',
      material_culture: 'not-an-object',
      citation_id: 'cit:1',
    }),
    null,
  );
  assert.equal(
    parsePlaceSnapshotRow({ id: 'ps:bad', location_id: 'loc:kufa', year_min: 100, year_max: 50, citation_id: 'cit:1' }),
    null,
  );
  assert.equal(
    parsePlaceSnapshotRow({
      id: 'ps:bad-json',
      location_id: 'loc:kufa',
      religious_communities: ['not-an-object'],
      citation_id: 'cit:1',
    }),
    null,
  );

  const validResidence = parseNarratorResidenceRow({
    id: 'nr:1',
    narrator_id: 'narr:1',
    location_id: 'loc:medina',
    year_min: 100,
    year_max: 150,
    role: 'taught',
    citation_id: 'cit:2',
  });
  assert.ok(validResidence);
  assert.equal(validResidence.reviewState, 'candidate_only');
  assert.equal(
    parseNarratorResidenceRow({
      id: 'nr:bad',
      narrator_id: 'narr:1',
      location_id: 'loc:medina',
      role: 'invalid_role',
      citation_id: 'cit:2',
    }),
    null,
  );

  const validAffiliation = parseNarratorAffiliationRow({
    id: 'na:1',
    narrator_id: 'narr:1',
    kind: 'legal_school',
    label: 'Maliki',
    citation_id: 'cit:3',
  });
  assert.ok(validAffiliation);
  assert.equal(
    parseNarratorAffiliationRow({
      id: 'na:bad',
      narrator_id: 'narr:1',
      kind: 'unknown_kind',
      label: 'X',
      citation_id: 'cit:3',
    }),
    null,
  );

  const validParallel = parseExternalTraditionParallelRow({
    id: 'etp:1',
    hadith_id: 'hadith:1',
    tradition_source: 'midrash_talmud',
    relation_type: 'shared_motif',
    source_work: 'Babylonian Talmud',
    locator: 'Sanhedrin 37a',
    citation_id: 'cit:4',
  });
  assert.ok(validParallel);
  for (const src of ['ancient_near_eastern_myth', 'arabian_folklore', 'greco_roman', 'poetry_adab']) {
    const p = parseExternalTraditionParallelRow({
      id: `etp:${src}`,
      hadith_id: 'hadith:1',
      tradition_source: src,
      relation_type: 'shared_motif',
      source_work: 'Primary Source',
      citation_id: 'cit:4',
    });
    assert.ok(p, `expected Phase 4 tradition_source ${src} to be accepted`);
  }
  assert.equal(
    parseExternalTraditionParallelRow({
      id: 'etp:bad',
      hadith_id: 'hadith:1',
      tradition_source: 'invalid_source',
      relation_type: 'shared_motif',
      source_work: 'X',
      citation_id: 'cit:4',
    }),
    null,
  );

  // 4. CLI args parsing
  assert.deepEqual(parseLoaderArgs([]), {
    dryRun: false,
    database: 'development',
    dataDir: null,
    reclassifyEvents: false,
  });
  assert.deepEqual(parseLoaderArgs(['--dry-run', '--database=production', '--reclassify-events']), {
    dryRun: true,
    database: 'production',
    dataDir: null,
    reclassifyEvents: true,
  });
  assert.deepEqual(parseLoaderArgs(['--dir', 'datasets/hadith-data/timelines-grid']), {
    dryRun: false,
    database: 'development',
    dataDir: 'datasets/hadith-data/timelines-grid',
    reclassifyEvents: false,
  });
  assert.deepEqual(parseLoaderArgs(['--dir=custom/batch']), {
    dryRun: false,
    database: 'development',
    dataDir: 'custom/batch',
    reclassifyEvents: false,
  });
  assert.throws(() => parseLoaderArgs(['--database', 'staging']), /development or production/);

  // 5. buildTimelinesLoadPlan with staged JSONL files + missing directory + starter seed
  const missingPlan = await buildTimelinesLoadPlan(join(tmpdir(), 'nonexistent-timelines-dir-xyz'));
  assert.equal(missingPlan.tracks.length, 11);
  assert.equal(missingPlan.works.length, 0);
  assert.equal(missingPlan.editions.length, 0);
  assert.equal(missingPlan.citations.length, 0);
  assert.equal(missingPlan.placeSnapshots.length, 0);

  const starterSeedPlan = await buildTimelinesLoadPlan(join(process.cwd(), 'datasets/hadith-data/timelines-grid'));
  assert.equal(starterSeedPlan.citationsSkipped, 0);
  assert.ok(starterSeedPlan.works.length >= 10);
  assert.ok(starterSeedPlan.editions.length >= 10);
  assert.ok(starterSeedPlan.citations.length >= 15);
  assert.equal(starterSeedPlan.placeSnapshotsSkipped, 0);
  assert.equal(starterSeedPlan.externalTraditionParallelsSkipped, 0);
  assert.ok(starterSeedPlan.placeSnapshots.length >= 3);
  assert.ok(starterSeedPlan.externalTraditionParallels.length >= 4);
  for (const ps of starterSeedPlan.placeSnapshots) {
    assert.equal(ps.reviewState, 'candidate_only');
    assert.ok(ps.socialNorms !== null && ps.materialCulture !== null);
  }
  for (const etp of starterSeedPlan.externalTraditionParallels) {
    assert.equal(etp.reviewState, 'candidate_only');
  }

  const tempDir = mkdtempSync(join(tmpdir(), 'timelines-loader-test-'));
  try {
    writeFileSync(
      join(tempDir, 'place_snapshots.jsonl'),
      [
        JSON.stringify({ id: 'ps:1', location_id: 'loc:kufa', year_min: 40, year_max: 60, citation_id: 'cit:1' }),
        JSON.stringify({ id: 'ps:bad', location_id: 'loc:kufa', year_min: 80, year_max: 60, citation_id: 'cit:1' }),
      ].join('\n'),
    );
    writeFileSync(
      join(tempDir, 'narrator_residences.jsonl'),
      JSON.stringify({ id: 'nr:1', narrator_id: 'n:1', location_id: 'loc:kufa', role: 'studied', citation_id: 'cit:1' }),
    );
    const plan = await buildTimelinesLoadPlan(tempDir);
    assert.equal(plan.placeSnapshots.length, 1);
    assert.equal(plan.placeSnapshotsSkipped, 1);
    assert.equal(plan.narratorResidences.length, 1);
    assert.equal(plan.narratorAffiliations.length, 0);
    assert.equal(plan.externalTraditionParallels.length, 0);
  } finally {
    rmSync(tempDir, { recursive: true, force: true });
  }

  console.log('load-timelines-grid unit tests passed.');
}

runTests().catch((err) => {
  console.error(err);
  process.exit(1);
});
