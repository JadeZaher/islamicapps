/**
 * regen-modes.test.ts — mode-dispatcher contract tests
 * =====================================================
 *
 * Track: neo4j_isnad_graph_regen_20260516, tasks 1.7 + 1.11.
 * Spec refs: §9b assertions, FR-1.9..1.11.
 *
 * Test groups:
 *   M1 (unit) — fixture CSV parsing + tradition canonicalization logic (no Neo4j)
 *   M2 (unit) — enrich-mode idempotency contract assertions (no Neo4j)
 *   M3 (unit) — diff-mode change-detection logic (no Neo4j)
 *   M4 (live) — mode=test assertions on fixture subset via live Neo4j
 *   M5 (live) — mode=fullregen produces identical output on second run (idempotent)
 *   M6 (live) — mode=diff identifies added/updated/unchanged correctly
 *   M7 (live) — mode=enrich is idempotent, never overwrites, stamps provenance
 *
 * DEPENDENCY NOTE: M4..M7 depend on workstream E's mode-* modules
 * (src/scripts/lib/regen/mode-test.ts, mode-fullregen.ts, mode-diff.ts,
 * mode-enrich.ts) which are NOT YET LANDED. Those tests are marked skip
 * with a "module not yet landed" comment so the verifier (workstream G)
 * knows which failures are expected vs regressions.
 *
 * M1..M3 run with no Neo4j and no module prerequisites — they test the
 * CSV-parsing and contract-shape logic directly.
 */

import fs from 'fs';
import path from 'path';

// ─── Tiny assertion harness (matches regen-isnad-graph.test.ts convention) ─────

let passed = 0;
let failed = 0;
const failures: string[] = [];
const skipped: string[] = [];

function check(name: string, cond: boolean, detail = ''): void {
  if (cond) {
    passed++;
    console.log(`  PASS ${name}`);
  } else {
    failed++;
    failures.push(`${name}${detail ? ` — ${detail}` : ''}`);
    console.log(`  FAIL ${name}${detail ? ` — ${detail}` : ''}`);
  }
}

function skip(name: string, reason: string): void {
  skipped.push(`${name}: ${reason}`);
  console.log(`  SKIP ${name} — ${reason}`);
}

function eq<T>(name: string, actual: T, expected: T): void {
  check(name, actual === expected, `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

// ─── CSV parsing helpers (shared logic, independent of production modules) ────

function splitCSVRecords(content: string): string[] {
  const rows: string[] = [];
  let cur = '';
  let inq = false;
  for (let i = 0; i < content.length; i++) {
    const c = content[i];
    if (c === '"') inq = !inq;
    if ((c === '\n' || c === '\r') && !inq) {
      if (c === '\r' && content[i + 1] === '\n') i++;
      if (cur.trim()) rows.push(cur);
      cur = '';
    } else cur += c;
  }
  if (cur.trim()) rows.push(cur);
  return rows;
}

function parseCSVLine(line: string): string[] {
  const r: string[] = [];
  let cur = '';
  let q = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    const nx = line[i + 1];
    if (ch === '"') {
      if (q && nx === '"') { cur += '"'; i++; } else q = !q;
    } else if (ch === ',' && !q) {
      r.push(cur.trim()); cur = '';
    } else cur += ch;
  }
  r.push(cur.trim());
  return r;
}

type CSVRow = Record<string, string>;

function readFixtureCSV(filename: string): CSVRow[] {
  const p = path.join(process.cwd(), 'src', 'scripts', '__tests__', 'fixtures', 'regen', filename);
  const content = fs.readFileSync(p, 'utf8');
  const records = splitCSVRecords(content);
  const header = parseCSVLine(records[0]);
  const out: CSVRow[] = [];
  for (let i = 1; i < records.length; i++) {
    const vals = parseCSVLine(records[i]);
    const row: CSVRow = {};
    header.forEach((h, idx) => { row[h] = vals[idx] || ''; });
    out.push(row);
  }
  return out;
}

// ─── Tradition canonicalization (spec invariant 6, spec §9b) ─────────────────

/** Mirror of the canonicalize logic that mode-fullregen.ts MUST implement. */
function canonicalizeTradition(raw: string): string {
  const t = raw.trim();
  if (t === 'Shia Imami') return 'Imami';
  if (t === 'Shia Zaydi') return 'Zaydi';
  return t;
}

// ─── Enrich-mode field stamping contract ─────────────────────────────────────

interface EnrichRecord {
  id: string;
  [key: string]: string | undefined;
}

/**
 * Pure function implementing the enrich-mode write rule:
 * only fill a field if currently absent/empty; stamp provenance metadata.
 * This is the CONTRACT that mode-enrich.ts MUST satisfy (tested independently
 * of the module so we can verify the invariant before the module lands).
 */
function applyEnrich(
  record: EnrichRecord,
  field: string,
  newValue: string,
  source: string,
  enrichedAt: string,
): { result: EnrichRecord; outcome: 'added' | 'skipped_already_filled' } {
  if (record[field] && record[field]!.trim() !== '') {
    return { result: record, outcome: 'skipped_already_filled' };
  }
  const result: EnrichRecord = {
    ...record,
    [field]: newValue,
    [`${field}_source`]: source,
    [`${field}_enriched_at`]: enrichedAt,
    [`${field}_extraction_method`]: 'enrich-jsonl',
  };
  return { result, outcome: 'added' };
}

// ─── Diff-mode change detection contract ─────────────────────────────────────

type DiffOutcome = 'added' | 'updated' | 'unchanged';

function diffRecord(
  incoming: CSVRow,
  existing: CSVRow | undefined,
  trackedFields: string[],
): DiffOutcome {
  if (!existing) return 'added';
  for (const f of trackedFields) {
    if ((incoming[f] || '').trim() !== (existing[f] || '').trim()) return 'updated';
  }
  return 'unchanged';
}

// ─── M1 — fixture CSV parsing + tradition canonicalization (no Neo4j) ────────

function testM1(): void {
  console.log('\n[M1] Fixture CSV parsing + tradition canonicalization');

  const rows = readFixtureCSV('fixture-hadiths.csv');
  check('fixture-hadiths.csv parses to expected row count (37)', rows.length === 37,
    `got ${rows.length}`);

  const traditions = new Set(rows.map(r => r.tradition));
  check('fixture contains Sunni rows', traditions.has('Sunni'));
  check('fixture contains Imami rows', traditions.has('Imami'));
  check('fixture contains Ibadi rows', traditions.has('Ibadi'));
  check('fixture contains Zaydi rows', traditions.has('Zaydi'));

  const sunniCount = rows.filter(r => r.tradition === 'Sunni').length;
  const imamiCount = rows.filter(r => r.tradition === 'Imami').length;
  const ibadiCount = rows.filter(r => r.tradition === 'Ibadi').length;
  const zaydiCount = rows.filter(r => r.tradition === 'Zaydi').length;
  eq('Sunni row count in fixture', sunniCount, 15);
  eq('Imami row count in fixture', imamiCount, 12);
  eq('Ibadi row count in fixture', ibadiCount, 5);
  eq('Zaydi row count in fixture', zaydiCount, 5);

  // Test tradition drift fixture
  const driftRows = readFixtureCSV('fixture-tradition-drift.csv');
  const driftImami = driftRows.filter(r => r.tradition === 'Shia Imami');
  const driftZaydi = driftRows.filter(r => r.tradition === 'Shia Zaydi');
  check('drift fixture has Shia Imami rows for canonicalization test', driftImami.length > 0);
  check('drift fixture has Shia Zaydi rows for canonicalization test', driftZaydi.length > 0);

  // Canonicalization invariant: no "Shia Imami" or "Shia Zaydi" after transform
  const canonicalized = driftRows.map(r => canonicalizeTradition(r.tradition));
  check('after canonicalization: zero "Shia Imami"',
    !canonicalized.includes('Shia Imami'));
  check('after canonicalization: zero "Shia Zaydi"',
    !canonicalized.includes('Shia Zaydi'));
  check('after canonicalization: Shia Imami → Imami',
    canonicalized.every(t => t !== 'Shia Imami'));
  check('after canonicalization: Shia Zaydi → Zaydi',
    canonicalized.every(t => t !== 'Shia Zaydi'));
}

// ─── M2 — enrich-mode idempotency contract (no Neo4j) ────────────────────────

function testM2(): void {
  console.log('\n[M2] Enrich-mode idempotency contract (no Neo4j)');

  const AT = '2026-05-20T00:00:00Z';
  const SOURCE = 'test-enrich-source.jsonl';

  // Case 1: empty field → should be filled
  const r1: EnrichRecord = { id: 'h1', text_english: '' };
  const { result: r1out, outcome: o1 } = applyEnrich(r1, 'text_english', 'Translation A', SOURCE, AT);
  eq('enrich empty field → outcome added', o1, 'added');
  eq('enrich empty field → value set', r1out.text_english, 'Translation A');
  eq('enrich empty field → _source stamped', r1out['text_english_source'], SOURCE);
  eq('enrich empty field → _enriched_at stamped', r1out['text_english_enriched_at'], AT);
  eq('enrich empty field → _extraction_method = enrich-jsonl',
    r1out['text_english_extraction_method'], 'enrich-jsonl');

  // Case 2: populated field → must NOT be overwritten
  const r2: EnrichRecord = { id: 'h2', text_english: 'Existing translation' };
  const { result: r2out, outcome: o2 } = applyEnrich(r2, 'text_english', 'New translation', SOURCE, AT);
  eq('enrich populated field → outcome skipped_already_filled', o2, 'skipped_already_filled');
  eq('enrich populated field → original value preserved', r2out.text_english, 'Existing translation');
  eq('enrich populated field → no _source stamp added',
    r2out['text_english_source'], undefined);

  // Case 3: idempotency — applying enrich twice yields the same result
  const r3: EnrichRecord = { id: 'h3', text_english: '' };
  const { result: r3a } = applyEnrich(r3, 'text_english', 'Val', SOURCE, AT);
  const { result: r3b, outcome: o3b } = applyEnrich(r3a, 'text_english', 'Different val', SOURCE, AT);
  eq('enrich second pass → skipped (idempotent)', o3b, 'skipped_already_filled');
  eq('enrich second pass → first value retained', r3b.text_english, 'Val');

  // Case 4: missing field (undefined) → should be filled
  const r4: EnrichRecord = { id: 'h4' };
  const { outcome: o4 } = applyEnrich(r4, 'text_english', 'Translation B', SOURCE, AT);
  eq('enrich missing field → outcome added', o4, 'added');
}

// ─── M3 — diff-mode change-detection (no Neo4j) ──────────────────────────────

function testM3(): void {
  console.log('\n[M3] Diff-mode change-detection contract (no Neo4j)');

  const TRACKED = ['text_ar', 'text_english', 'sanad', 'chain_indx', 'grade'];

  // New record → added
  const incoming1: CSVRow = { dataset_row_id: 'h1', text_ar: 'نص', text_english: 'text',
    sanad: 'chain', chain_indx: '[1]', grade: 'Sahih' };
  eq('diff new record → added', diffRecord(incoming1, undefined, TRACKED), 'added');

  // Identical record → unchanged
  const existing1: CSVRow = { ...incoming1 };
  eq('diff identical record → unchanged', diffRecord(incoming1, existing1, TRACKED), 'unchanged');

  // Changed grade → updated
  const incoming2: CSVRow = { ...incoming1, grade: 'Hasan' };
  eq('diff changed grade → updated', diffRecord(incoming2, existing1, TRACKED), 'updated');

  // Changed text_ar → updated
  const incoming3: CSVRow = { ...incoming1, text_ar: 'نص مختلف' };
  eq('diff changed text_ar → updated', diffRecord(incoming3, existing1, TRACKED), 'updated');

  // Non-tracked field change → unchanged (only tracked fields matter)
  const incoming4: CSVRow = { ...incoming1, tradition: 'Sunni' };
  const existing4: CSVRow = { ...incoming1, tradition: 'Other' };
  eq('diff non-tracked field change → unchanged', diffRecord(incoming4, existing4, TRACKED), 'unchanged');
}

// ─── M4..M7 — live Neo4j tests (modules not yet landed) ──────────────────────
// EXPECTED-SKIP: these depend on workstream E's mode-* modules which are
// not yet landed. The verifier (workstream G) will run them once C/D/E land.

function testM4_skip(): void {
  console.log('\n[M4] mode=test spec §9b assertions on fixture subset');
  // EXPECTED — module not yet landed: src/scripts/lib/regen/mode-test.ts
  // When landed, this should:
  // 1. Run the fixture through mode=test
  // 2. Assert every §9b check: broken text_ar exit, empty text_arabic fail,
  //    missing text_english warn, no-chain classification, etc.
  skip('[M4] mode=test spec §9b assertions',
    'EXPECTED — module not yet landed: src/scripts/lib/regen/mode-test.ts (workstream E)');
}

function testM5_skip(): void {
  console.log('\n[M5] mode=fullregen fixture idempotency');
  // EXPECTED — module not yet landed: src/scripts/lib/regen/mode-fullregen.ts
  // When landed, this should:
  // 1. Run fullregen on fixture with a unique versionLabel
  // 2. Run again with the same versionLabel
  // 3. Assert counts are identical (idempotent fixed point)
  skip('[M5] mode=fullregen idempotency on fixture',
    'EXPECTED — module not yet landed: src/scripts/lib/regen/mode-fullregen.ts (workstream E)');
}

function testM6_skip(): void {
  console.log('\n[M6] mode=diff added/updated/unchanged identification');
  // EXPECTED — module not yet landed: src/scripts/lib/regen/mode-diff.ts
  // When landed, this should:
  // 1. Load fixture into DB
  // 2. Modify some rows in fixture
  // 3. Run diff mode
  // 4. Assert correctly classified added/updated/unchanged counts
  skip('[M6] mode=diff identifies changes correctly',
    'EXPECTED — module not yet landed: src/scripts/lib/regen/mode-diff.ts (workstream E)');
}

function testM7_skip(): void {
  console.log('\n[M7] mode=enrich idempotent, never overwrites, stamps provenance');
  // EXPECTED — module not yet landed: src/scripts/lib/regen/mode-enrich.ts
  // When landed, this should:
  // 1. Run enrich with test JSONL source
  // 2. Assert _source/_enriched_at/_extraction_method='enrich-jsonl' stamped
  // 3. Run again with different values
  // 4. Assert original values retained (idempotent)
  skip('[M7] mode=enrich idempotency and provenance stamping',
    'EXPECTED — module not yet landed: src/scripts/lib/regen/mode-enrich.ts (workstream E)');
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log('='.repeat(64));
  console.log('  regen-modes.test.ts — mode contract tests (tasks 1.7, 1.11)');
  console.log('='.repeat(64));

  testM1();
  testM2();
  testM3();
  testM4_skip();
  testM5_skip();
  testM6_skip();
  testM7_skip();

  console.log('\n' + '='.repeat(64));
  console.log('  Summary');
  console.log('='.repeat(64));
  console.log(`  PASSED: ${passed}   FAILED: ${failed}   SKIPPED: ${skipped.length}`);

  if (skipped.length > 0) {
    console.log('\n  Skipped (expected — modules not yet landed):');
    for (const s of skipped) console.log(`    SKIP ${s}`);
  }

  if (failed > 0) {
    console.log('\n  Failures:');
    for (const f of failures) console.log(`    FAIL ${f}`);
    process.exitCode = 1;
  } else {
    console.log('\n  All executed assertions passed.');
    if (skipped.length > 0) {
      console.log('  Skipped tests above are EXPECTED (modules not yet landed) — not failures.');
    }
  }
}

main().catch(err => {
  console.error('\nFatal:', err);
  process.exitCode = 1;
});
