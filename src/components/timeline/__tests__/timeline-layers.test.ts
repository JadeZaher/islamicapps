/**
 * Flow tests for Context Layers (timelines-and-contact-grid_20261127):
 * - Toggleable Context Layers (all off by default, clean initial view)
 * - Attested vs. Contextual separation
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
  filterPoliticalEvents,
  filterTechEvents,
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
];

check('CONTEXT_LAYERS exposes the 4 required toggleable layers', () => {
  assert.deepEqual(
    CONTEXT_LAYERS.map((layer) => layer.id),
    ['political', 'places', 'tech', 'parallels'],
  );
  assert.deepEqual(
    CONTEXT_LAYERS.map((layer) => layer.label),
    ['Political', 'Places & Demographics', 'Tech & Writing', "Parallels & Isra'iliyyat"],
  );
});

check('event track filters partition political, tech, and demographic events cleanly', () => {
  assert.deepEqual(
    filterPoliticalEvents(SAMPLE_EVENTS).map((e) => e.id),
    ['evt-pol'],
  );
  assert.deepEqual(
    filterTechEvents(SAMPLE_EVENTS).map((e) => e.id),
    ['evt-tech'],
  );
  assert.deepEqual(
    filterDemographicEvents(SAMPLE_EVENTS).map((e) => e.id),
    ['evt-demo'],
  );
});

check('default view keeps all Context Layers toggled off (uncluttered initial render)', () => {
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
  assert.equal((html.match(/aria-pressed="false"/g) ?? []).length, 4);
  assert.ok(!html.includes('data-layer="political"'));
  assert.ok(!html.includes('data-layer="places"'));
  assert.ok(!html.includes('data-layer="tech"'));
  assert.ok(!html.includes('data-layer="parallels"'));
});

check('toggling layers on renders attested vs. contextual separation explicitly', () => {
  const html = renderToStaticMarkup(
    React.createElement(ContextLayers, {
      audience: 'review',
      events: SAMPLE_EVENTS,
      residences: SAMPLE_RESIDENCES,
      affiliations: SAMPLE_AFFILIATIONS,
      placeSnapshots: SAMPLE_PLACE_SNAPSHOTS,
      parallels: SAMPLE_PARALLELS,
      initialLayers: ['political', 'places', 'tech', 'parallels'],
    }),
  );

  assert.equal((html.match(/aria-pressed="true"/g) ?? []).length, 4);
  assert.ok(html.includes('data-layer="political"'));
  assert.ok(html.includes('data-layer="places"'));
  assert.ok(html.includes('data-layer="tech"'));
  assert.ok(html.includes('data-layer="parallels"'));

  // Attested subgroups: Residences & mobility + Affiliations
  assert.ok(html.includes('Residences &amp; mobility'));
  assert.ok(html.includes('Affiliations'));
  assert.equal((html.match(/>Attested</g) ?? []).length, 2);

  // Contextual subgroups/panels: Political, Place snapshots, Demographic & trade shifts, Tech & writing, Parallels
  assert.ok(html.includes('Place snapshots'));
  assert.ok(html.includes('Demographic &amp; trade shifts'));
  assert.equal((html.match(/>Contextual</g) ?? []).length, 5);
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

check('public vs. review empty-state messaging and candidate tagging behave as expected', () => {
  const publicEmpty = renderToStaticMarkup(
    React.createElement(ContextLayers, {
      audience: 'public',
      events: [],
      initialLayers: ['political', 'places', 'tech', 'parallels'],
    }),
  );
  assert.equal((publicEmpty.match(/reviewed and cited/g) ?? []).length, 4);

  const reviewEmpty = renderToStaticMarkup(
    React.createElement(ContextLayers, {
      audience: 'review',
      events: [],
      initialLayers: ['political', 'places', 'tech', 'parallels'],
    }),
  );
  assert.ok(!reviewEmpty.includes('reviewed and cited'));

  const reviewWithCandidate = renderToStaticMarkup(
    React.createElement(ContextLayers, {
      audience: 'review',
      events: [],
      parallels: SAMPLE_PARALLELS,
      initialLayers: ['parallels'],
    }),
  );
  assert.ok(reviewWithCandidate.includes('Babylonian Talmud, Sanhedrin'));
  assert.ok(reviewWithCandidate.includes('>candidate<'));
});

check('timeline.ts strictly gates candidate_only and unreviewed citations to review audience', () => {
  const timelineSource = readFileSync(path.resolve(process.cwd(), 'src/db/queries/timeline.ts'), 'utf8');

  // Verify each of the 4 new evidence-bearing tables enforces review_state + reviewed citation for public audience.
  const requiredGuards = [
    'from narrator_residences nr',
    'nr.review_state in ${REVIEWED_CITATION} and c.id is not null',
    'from narrator_affiliations na',
    'na.review_state in ${REVIEWED_CITATION} and c.id is not null',
    'from place_snapshots ps',
    'ps.review_state in ${REVIEWED_CITATION} and c.id is not null',
    'from external_tradition_parallels ep',
    'ep.review_state in ${REVIEWED_CITATION} and c.id is not null',
  ];

  for (const guard of requiredGuards) {
    assert.ok(timelineSource.includes(guard), `Missing public gating guard in src/db/queries/timeline.ts: ${guard}`);
  }
});

if (failures.length > 0) {
  console.error(`\n${failures.length} check(s) failed.`);
  process.exit(1);
}
console.log('\nAll timeline-layers checks passed.');
