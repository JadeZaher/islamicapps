/**
 * Flow tests for Context Layers (timelines-and-contact-grid_20261127, Phase 4 / 0026):
 * - All 8 toggleable Context Layers (all off by default, clean initial view)
 * - Pre-Hijri / BCE year formatting (BH / c. CE / c. BCE)
 * - Attested vs. Contextual separation
 * - `social_norms` and `material_culture` rendering on place snapshots & thematic layers
 * - Clickable citation links (external HTTP URLs and /sources fallback)
 * - Public vs. review gating in UI and query layer
 *
 * Run: npx tsx src/components/timeline/__tests__/timeline-layers.test.ts
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import path from 'node:path';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import type {
  EventEntry,
  ExternalTraditionParallelEntry,
  NarratorAffiliationEntry,
  NarratorResidenceEntry,
  PlaceSnapshotEntry,
  TimelineCitation,
} from '@/db/queries/timeline-contracts';

// Stub CSS module imports so client components can be SSR-rendered under tsx.
const require = createRequire(import.meta.url);
const Module = require('node:module') as {
  _load: (request: string, parent: unknown, isMain: boolean) => unknown;
};
const cssProxy: Record<string, string> = new Proxy(
  {},
  {
    get: (_target, prop) => (typeof prop === 'string' ? prop : ''),
  },
);
const cssModuleExport = { __esModule: true, default: cssProxy };
const originalLoad = Module._load;
Module._load = function (request: string, parent: unknown, isMain: boolean) {
  if (request.endsWith('.css')) return cssModuleExport;
  return originalLoad.call(this, request, parent, isMain);
};

// Load components after CSS stub is registered.
const {
  CONTEXT_LAYERS,
  ContextLayers,
  filterDemographicEvents,
  filterEconomicTensionsEvents,
  filterFoodAgricultureEvents,
  filterMythsLiteratureArtEvents,
  filterPoliticalEvents,
  filterSocialGenderEvents,
  filterTechEvents,
  formatContextInterval,
  formatContextYear,
  formatContextYearSpan,
} = require('../ContextLayers') as typeof import('../ContextLayers');
const { CitationLink, formatCitationLabel } = require('../CitationLink') as typeof import('../CitationLink');

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

const VERIFIED_HTTP_CITATION: TimelineCitation = {
  id: 'cit-1',
  work_title: 'Tarikh al-Tabari',
  work_title_ar: 'تاريخ الطبري',
  author: 'al-Tabari',
  edition: 'De Goeje',
  volume: '2',
  page: '115',
  locator: 's.a. 132',
  url: 'https://example.org/tabari/2/115',
  review_state: 'human_verified',
};

const FALLBACK_CITATION: TimelineCitation = {
  id: 'cit-2',
  work_title: 'Tahdhib al-Kamal',
  work_title_ar: null,
  author: 'al-Mizzi',
  edition: null,
  volume: '4',
  page: '88',
  locator: null,
  url: null,
  review_state: 'source_verified',
};

const CANDIDATE_CITATION: TimelineCitation = {
  id: 'cit-3',
  work_title: 'Draft Corpus Note',
  work_title_ar: null,
  author: 'Staging',
  edition: null,
  volume: null,
  page: null,
  locator: 'note 7',
  url: 'https://example.org/draft/7',
  review_state: 'candidate_only',
};

const SAMPLE_EVENTS: EventEntry[] = [
  {
    kind: 'event',
    id: 'evt-pol',
    name: 'Abbasid Revolution',
    name_arabic: 'الثورة العباسية',
    start: 132,
    end: 132,
    start_latest: null,
    end_earliest: null,
    boundary_note: null,
    basis: 'reviewed_cited',
    category: 'political',
    location_name: 'Kufa',
    location_id: 'loc-kufa',
    description: 'Shift of caliphal authority.',
    track_category: 'political',
    citation: VERIFIED_HTTP_CITATION,
  },
  {
    kind: 'event',
    id: 'evt-tech',
    name: 'Paper mill established in Baghdad',
    name_arabic: null,
    start: 178,
    end: 178,
    start_latest: null,
    end_earliest: null,
    boundary_note: null,
    basis: 'reviewed_cited',
    category: 'technological',
    location_name: 'Baghdad',
    location_id: 'loc-baghdad',
    description: 'Spread of rag paper in administrative and scholarly copying.',
    track_category: 'technological',
    citation: FALLBACK_CITATION,
  },
  {
    kind: 'event',
    id: 'evt-demo',
    name: 'Kufa garrison settlement expansion',
    name_arabic: null,
    start: 40,
    end: 50,
    start_latest: null,
    end_earliest: null,
    boundary_note: null,
    basis: 'reviewed_cited',
    category: 'demographic',
    location_name: 'Kufa',
    location_id: 'loc-kufa',
    description: 'Tribal quarters consolidated.',
    track_category: 'demographic_shift',
    citation: VERIFIED_HTTP_CITATION,
  },
  {
    kind: 'event',
    id: 'evt-social',
    name: 'Code of Hammurabi family & dowry clauses',
    name_arabic: null,
    start: -2450,
    end: -2440,
    start_latest: null,
    end_earliest: null,
    boundary_note: null,
    basis: 'reviewed_cited',
    category: 'social',
    location_name: 'Babylon',
    location_id: 'loc-babylon',
    description: 'Early Near Eastern codification of marriage, inheritance, and household norms.',
    track_category: 'social_gender_norms',
    citation: VERIFIED_HTTP_CITATION,
  },
  {
    kind: 'event',
    id: 'evt-myths',
    name: 'Muallaqat oral performance at Ukaz',
    name_arabic: 'المعلقات',
    start: -50,
    end: -30,
    start_latest: null,
    end_earliest: null,
    boundary_note: null,
    basis: 'reviewed_cited',
    category: 'literature',
    location_name: 'Ukaz',
    location_id: 'loc-ukaz',
    description: 'Pre-Islamic Arabian poetic canon recited at seasonal fairs.',
    track_category: 'myths_literature_art',
    citation: FALLBACK_CITATION,
  },
  {
    kind: 'event',
    id: 'evt-food',
    name: 'Sawad canal irrigation expansion',
    name_arabic: null,
    start: 15,
    end: 40,
    start_latest: null,
    end_earliest: null,
    boundary_note: null,
    basis: 'reviewed_cited',
    category: 'agriculture',
    location_name: 'Lower Iraq',
    location_id: 'loc-sawad',
    description: 'Date-palm and barley cultivation across southern Mesopotamian canals.',
    track_category: 'food_agriculture_ecology',
    citation: VERIFIED_HTTP_CITATION,
  },
  {
    kind: 'event',
    id: 'evt-econ',
    name: 'Umayyad silver dirham coinage reform',
    name_arabic: null,
    start: 77,
    end: 79,
    start_latest: null,
    end_earliest: null,
    boundary_note: null,
    basis: 'reviewed_cited',
    category: 'economic',
    location_name: 'Damascus',
    location_id: 'loc-damascus',
    description: 'Standardization of epigraphic gold dinars and silver dirhams.',
    track_category: 'economic_tensions',
    citation: VERIFIED_HTTP_CITATION,
  },
];

const SAMPLE_RESIDENCES: NarratorResidenceEntry[] = [
  {
    id: 'res-1',
    narrator_id: 'nar-1',
    narrator_name: 'Sufyan al-Thawri',
    location_id: 'loc-kufa',
    location_name: 'Kufa',
    year_min: 120,
    year_max: 155,
    precision: 'range',
    role: 'taught_at',
    review_state: 'human_verified',
    citation: FALLBACK_CITATION,
  },
];

const SAMPLE_AFFILIATIONS: NarratorAffiliationEntry[] = [
  {
    id: 'aff-1',
    narrator_id: 'nar-1',
    narrator_name: 'Sufyan al-Thawri',
    kind: 'madhhab',
    label: 'Thawri',
    note: 'Kufan juristic circle',
    review_state: 'human_verified',
    citation: VERIFIED_HTTP_CITATION,
  },
];

const SAMPLE_PLACE_SNAPSHOTS: PlaceSnapshotEntry[] = [
  {
    id: 'ps-1',
    location_id: 'loc-kufa',
    location_name: 'Kufa',
    year_min: 120,
    year_max: 160,
    precision: 'range',
    polity_or_ruler: 'Early Abbasid',
    dominant_schools: ['Kufan ra-y', 'Ahl al-Hadith'],
    religious_communities: { muslim: 'majority', christian: 'present' },
    languages: ['Arabic', 'Aramaic'],
    ethnographic_notes: 'Major Iraqi scholarly crossroads.',
    social_norms: { kinship_structure: 'tribal quarters', women_scholarship: 'attested in domestic circles' },
    material_culture: { staples: ['barley', 'dates'], writing_medium: 'parchment and early rag paper' },
    review_state: 'human_verified',
    citation: VERIFIED_HTTP_CITATION,
  },
];

const SAMPLE_PARALLELS: ExternalTraditionParallelEntry[] = [
  {
    id: 'par-1',
    hadith_id: 'had-1',
    tradition_source: 'israiliyyat',
    relation_type: 'shared_motif',
    source_work: 'Babylonian Talmud, Sanhedrin',
    locator: '37a',
    note: 'Parallel ethical maxim cited in tafsir literature.',
    review_state: 'candidate_only',
    citation: CANDIDATE_CITATION,
  },
  {
    id: 'par-2',
    hadith_id: 'had-1',
    tradition_source: 'ancient_near_eastern_myth',
    relation_type: 'shared_motif',
    source_work: 'Epic of Gilgamesh, Tablet XI',
    locator: 'lines 1-190',
    note: 'Ancient Near Eastern flood narrative motif.',
    review_state: 'candidate_only',
    citation: CANDIDATE_CITATION,
  },
];

check('CONTEXT_LAYERS exposes all 8 required toggleable layers', () => {
  assert.deepEqual(
    CONTEXT_LAYERS.map((layer) => layer.id),
    [
      'political',
      'places',
      'tech',
      'parallels',
      'social_gender_norms',
      'myths_literature_art',
      'food_agriculture_ecology',
      'economic_tensions',
    ],
  );
  assert.deepEqual(
    CONTEXT_LAYERS.map((layer) => layer.label),
    [
      'Political',
      'Places & Demographics',
      'Tech & Writing',
      "Parallels & Isra'iliyyat",
      'Social & Gender Norms',
      'Myths, Poetry & Art',
      'Food & Agriculture',
      'Economic Tensions',
    ],
  );
});

check('event track filters partition all 7 event track categories cleanly', () => {
  assert.deepEqual(filterPoliticalEvents(SAMPLE_EVENTS).map((e) => e.id), ['evt-pol']);
  assert.deepEqual(filterTechEvents(SAMPLE_EVENTS).map((e) => e.id), ['evt-tech']);
  assert.deepEqual(filterDemographicEvents(SAMPLE_EVENTS).map((e) => e.id), ['evt-demo']);
  assert.deepEqual(filterSocialGenderEvents(SAMPLE_EVENTS).map((e) => e.id), ['evt-social']);
  assert.deepEqual(filterMythsLiteratureArtEvents(SAMPLE_EVENTS).map((e) => e.id), ['evt-myths']);
  assert.deepEqual(filterFoodAgricultureEvents(SAMPLE_EVENTS).map((e) => e.id), ['evt-food']);
  assert.deepEqual(filterEconomicTensionsEvents(SAMPLE_EVENTS).map((e) => e.id), ['evt-econ']);
});

check('pre-Hijri / BCE year formatting renders BH, c. CE, and c. BCE cleanly', () => {
  assert.equal(formatContextYear(132), '132 AH');
  assert.equal(formatContextYear(0), '0 (not a Hijri year)');
  assert.equal(formatContextYear(-53), '53 BH (c. 571 CE)');
  assert.equal(formatContextYear(-2500), '2500 BH (c. 1805 BCE)');
  assert.equal(formatContextYearSpan(-2450, -2440), '2450 BH (c. 1756 BCE) – 2440 BH (c. 1746 BCE)');
  assert.equal(formatContextYearSpan(null, null), 'Date unrecorded');
  assert.equal(formatContextInterval({ start: -53, end: null }), 'from 53 BH (c. 571 CE)');
});

check('default view keeps all 8 Context Layers toggled off (uncluttered initial render)', () => {
  const html = renderToStaticMarkup(
    React.createElement(ContextLayers, {
      audience: 'public',
      events: SAMPLE_EVENTS,
      residences: SAMPLE_RESIDENCES,
      affiliations: SAMPLE_AFFILIATIONS,
      placeSnapshots: SAMPLE_PLACE_SNAPSHOTS,
      parallels: SAMPLE_PARALLELS,
    }),
  );

  assert.ok(html.includes('Political'));
  assert.ok(html.includes('Places &amp; Demographics'));
  assert.ok(html.includes('Tech &amp; Writing'));
  assert.ok(html.includes('Parallels &amp; Isra&#x27;iliyyat'));
  assert.ok(html.includes('Social &amp; Gender Norms'));
  assert.ok(html.includes('Myths, Poetry &amp; Art'));
  assert.ok(html.includes('Food &amp; Agriculture'));
  assert.ok(html.includes('Economic Tensions'));
  assert.equal((html.match(/aria-pressed="false"/g) ?? []).length, 8);
  for (const layer of CONTEXT_LAYERS) {
    assert.ok(!html.includes(`data-layer="${layer.id}"`), `Layer ${layer.id} should be off by default`);
  }
});

check('toggling all 8 layers on renders attested vs. contextual separation, social_norms, material_culture, and BH/BCE dates', () => {
  const html = renderToStaticMarkup(
    React.createElement(ContextLayers, {
      audience: 'review',
      events: SAMPLE_EVENTS,
      residences: SAMPLE_RESIDENCES,
      affiliations: SAMPLE_AFFILIATIONS,
      placeSnapshots: SAMPLE_PLACE_SNAPSHOTS,
      parallels: SAMPLE_PARALLELS,
      initialLayers: CONTEXT_LAYERS.map((l) => l.id),
    }),
  );

  assert.equal((html.match(/aria-pressed="true"/g) ?? []).length, 8);
  for (const layer of CONTEXT_LAYERS) {
    assert.ok(html.includes(`data-layer="${layer.id}"`), `Expected panel for layer ${layer.id}`);
  }

  // Attested subgroups: Residences & mobility + Affiliations
  assert.ok(html.includes('Residences &amp; mobility'));
  assert.ok(html.includes('Affiliations'));
  assert.equal((html.match(/>Attested</g) ?? []).length, 2);

  // Contextual panels & subgroups include all 4 new axes
  assert.ok(html.includes('Place snapshots'));
  assert.ok(html.includes('Demographic &amp; trade shifts'));
  assert.ok(html.includes('Place social norms'));
  assert.ok(html.includes('Literary &amp; mythological parallels'));
  assert.ok(html.includes('Material culture &amp; diet'));
  assert.ok(html.includes('Economic tensions &amp; material life'));

  // social_norms & material_culture fields rendered
  assert.ok(html.includes('Social norms: kinship structure: tribal quarters; women scholarship: attested in domestic circles'));
  assert.ok(html.includes('Material culture: staples: barley, dates; writing medium: parchment and early rag paper'));

  // Pre-Hijri / BCE event date rendered in social_gender_norms panel
  assert.ok(html.includes('2450 BH (c. 1756 BCE) – 2440 BH (c. 1746 BCE)'));
  assert.ok(html.includes('Epic of Gilgamesh, Tablet XI'));
});

check('every citation renders as a clickable link (external HTTP or /sources fallback)', () => {
  assert.equal(formatCitationLabel(VERIFIED_HTTP_CITATION), 'al-Tabari, Tarikh al-Tabari (vol. 2, p. 115, s.a. 132)');

  const httpHtml = renderToStaticMarkup(React.createElement(CitationLink, { citation: VERIFIED_HTTP_CITATION }));
  assert.ok(httpHtml.includes('href="https://example.org/tabari/2/115"'));
  assert.ok(httpHtml.includes('target="_blank"'));
  assert.ok(httpHtml.includes('rel="noopener noreferrer"'));
  assert.ok(!httpHtml.includes('candidate'));

  const fallbackHtml = renderToStaticMarkup(React.createElement(CitationLink, { citation: FALLBACK_CITATION }));
  assert.ok(fallbackHtml.includes('href="/sources"'));
  assert.ok(fallbackHtml.includes('al-Mizzi, Tahdhib al-Kamal (vol. 4, p. 88)'));

  const candidateHtml = renderToStaticMarkup(React.createElement(CitationLink, { citation: CANDIDATE_CITATION }));
  assert.ok(candidateHtml.includes('href="https://example.org/draft/7"'));
  assert.ok(candidateHtml.includes('>candidate<'));
});

check('public vs. review empty-state messaging and candidate tagging behave as expected across all 8 layers', () => {
  const allLayers = CONTEXT_LAYERS.map((l) => l.id);
  const publicEmpty = renderToStaticMarkup(
    React.createElement(ContextLayers, {
      audience: 'public',
      events: [],
      initialLayers: allLayers,
    }),
  );
  assert.equal((publicEmpty.match(/reviewed and cited/g) ?? []).length, 8);

  const reviewEmpty = renderToStaticMarkup(
    React.createElement(ContextLayers, {
      audience: 'review',
      events: [],
      initialLayers: allLayers,
    }),
  );
  assert.ok(!reviewEmpty.includes('reviewed and cited'));

  const reviewWithCandidate = renderToStaticMarkup(
    React.createElement(ContextLayers, {
      audience: 'review',
      events: [],
      parallels: SAMPLE_PARALLELS,
      initialLayers: ['parallels', 'myths_literature_art'],
    }),
  );
  assert.ok(reviewWithCandidate.includes('Babylonian Talmud, Sanhedrin'));
  assert.ok(reviewWithCandidate.includes('Epic of Gilgamesh, Tablet XI'));
  assert.ok(reviewWithCandidate.includes('>candidate<'));
});

check('timeline.ts strictly gates candidate_only and unreviewed citations to review audience and selects Phase 4 columns', () => {
  const timelineSource = readFileSync(path.resolve(process.cwd(), 'src/db/queries/timeline.ts'), 'utf8');

  const requiredGuards = [
    'from narrator_residences nr',
    'nr.review_state in ${REVIEWED_CITATION} and c.id is not null',
    'from narrator_affiliations na',
    'na.review_state in ${REVIEWED_CITATION} and c.id is not null',
    'from place_snapshots ps',
    'ps.review_state in ${REVIEWED_CITATION} and c.id is not null',
    'from external_tradition_parallels ep',
    'ep.review_state in ${REVIEWED_CITATION} and c.id is not null',
    'ps.social_norms',
    'ps.material_culture',
  ];

  for (const guard of requiredGuards) {
    assert.ok(timelineSource.includes(guard), `Missing guard/column in src/db/queries/timeline.ts: ${guard}`);
  }
});

if (failures.length > 0) {
  console.error(`\n${failures.length} check(s) failed.`);
  process.exit(1);
}
console.log('\nAll timeline-layers checks passed.');
