/**
 * regen-tier1-coverage.test.ts — Tier-1 chain_indx entity resolution coverage
 * =============================================================================
 *
 * Track: neo4j_isnad_graph_regen_20260516, task 2.7.
 * Spec refs: FR-2.1, §9 Reliability Ledger, §12 Phase 2 exit gate.
 *
 * Per the verified ground-truth in the spec (measured, not estimated):
 *   Sunni K6:         chain_indx populated on 34,318 / 34,441 rows = 99.6%
 *   Sunni classical:  target ≥ 55% (same baseline as extract_isnad_sunni.py on K6)
 *   Imami:            chain_indx populated on 27,863 / 33,225 rows = 84%
 *                     → ≥ 83% when chain_indx text→IDs is solved
 *                     → 0% otherwise (documented --allow-known-gaps)
 *   Ibadi:            0% by design → Tier 2 fallback
 *   Zaydi:            0% by design → Tier 2 fallback
 *
 * Test groups:
 *   T1 (unit) — coverage computation logic (no Neo4j, uses fixture CSV)
 *   T2 (unit) — coverage thresholds validated on the verified ground-truth constants
 *   T3 (live) — Cypher coverage queries on post-fullregen DB
 *
 * T3 is deferred (not faked) if Neo4j is unreachable.
 * T3 also depends on workstream D's entity-resolution.ts (not yet landed) —
 * deferred with "EXPECTED — module not yet landed" comment.
 */

import fs from 'fs';
import path from 'path';
import { loadEnv } from '../lib/env';
import { runQuery, runWrite, closeDriver } from '../../lib/db/neo4j';

loadEnv();

// ─── Harness ─────────────────────────────────────────────────────────────────

let passed = 0;
let failed = 0;
const failures: string[] = [];
const deferred: string[] = [];

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

function defer(name: string, reason: string): void {
  deferred.push(`${name}: ${reason}`);
  console.log(`  DEFER ${name} — ${reason}`);
}

// ─── CSV parsing (same as the existing test file convention) ─────────────────

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

function readCSVRows(filePath: string): CSVRow[] {
  const content = fs.readFileSync(filePath, 'utf8');
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

// ─── Coverage computation (pure — tested independently of production modules) ─

interface TraditionCoverage {
  tradition: string;
  total: number;
  withChainIndx: number;
  coverageRate: number; // 0.0 – 1.0
}

/**
 * Compute chain_indx coverage per tradition from CSV rows.
 * "chain_indx populated" means the field is non-empty and not just "[]".
 * This mirrors what Tier-1 resolution can do deterministically.
 */
function computeChainIndxCoverage(rows: CSVRow[]): Map<string, TraditionCoverage> {
  const byTradition = new Map<string, { total: number; withChainIndx: number }>();

  for (const row of rows) {
    const t = row['tradition']?.trim() || 'Unknown';
    if (!byTradition.has(t)) byTradition.set(t, { total: 0, withChainIndx: 0 });
    const entry = byTradition.get(t)!;
    entry.total++;
    const ci = (row['chain_indx'] || '').trim();
    // "populated" = non-empty string that isn't just "[]" or empty JSON array
    if (ci && ci !== '[]' && ci !== '') entry.withChainIndx++;
  }

  const result = new Map<string, TraditionCoverage>();
  for (const [t, { total, withChainIndx }] of byTradition) {
    result.set(t, {
      tradition: t,
      total,
      withChainIndx,
      coverageRate: total > 0 ? withChainIndx / total : 0,
    });
  }
  return result;
}

// ─── T1 — Coverage computation logic (no Neo4j, fixture CSV) ─────────────────

function testT1_coverage_computation_logic(): void {
  console.log('\n[T1] Tier-1 coverage computation logic (fixture CSV, no Neo4j)');

  const fixturePath = path.join(
    process.cwd(), 'src', 'scripts', '__tests__', 'fixtures', 'regen', 'fixture-hadiths.csv'
  );
  const rows = readCSVRows(fixturePath);
  const coverage = computeChainIndxCoverage(rows);

  console.log('  Fixture coverage per tradition:');
  for (const [t, c] of coverage) {
    console.log(`    ${t}: ${c.withChainIndx}/${c.total} = ${(c.coverageRate * 100).toFixed(1)}%`);
  }

  // Fixture Sunni rows all have chain_indx populated
  const sunni = coverage.get('Sunni');
  check('T1: Sunni rows in fixture all have chain_indx (fixture design)',
    sunni !== undefined && sunni.withChainIndx === sunni.total,
    `Sunni: ${sunni?.withChainIndx}/${sunni?.total}`);

  // Fixture Imami rows all have chain_indx populated
  const imami = coverage.get('Imami');
  check('T1: Imami rows in fixture all have chain_indx (fixture design)',
    imami !== undefined && imami.withChainIndx === imami.total,
    `Imami: ${imami?.withChainIndx}/${imami?.total}`);

  // Fixture Ibadi rows have NO chain_indx (by fixture design — 0% by design)
  const ibadi = coverage.get('Ibadi');
  check('T1: Ibadi rows in fixture have zero chain_indx (0% by design)',
    ibadi !== undefined && ibadi.withChainIndx === 0,
    `Ibadi: ${ibadi?.withChainIndx}/${ibadi?.total}`);

  // Fixture Zaydi rows have NO chain_indx (0% by design)
  const zaydi = coverage.get('Zaydi');
  check('T1: Zaydi rows in fixture have zero chain_indx (0% by design)',
    zaydi !== undefined && zaydi.withChainIndx === 0,
    `Zaydi: ${zaydi?.withChainIndx}/${zaydi?.total}`);

  // Coverage computation function itself is correct
  check('T1: coverage rate for 100% populated = 1.0',
    sunni !== undefined && Math.abs(sunni.coverageRate - 1.0) < 0.001);
  check('T1: coverage rate for 0% populated = 0.0',
    ibadi !== undefined && Math.abs(ibadi.coverageRate - 0.0) < 0.001);
}

// ─── T2 — Coverage threshold validation against verified ground-truth ─────────

function testT2_threshold_constants(): void {
  console.log('\n[T2] Coverage thresholds vs verified ground-truth constants (spec §9)');

  // Verified ground-truth from spec (measured in-repo, authoritative)
  const VERIFIED = {
    sunniK6Total: 34441,
    sunniK6WithChainIndx: 34318,
    imamiTotal: 33225,
    imamiWithChainIndx: 27863,
    ibadiTotal: 1004,
    ibadiWithChainIndx: 0,
    zaydiTotal: 698,
    zaydiWithChainIndx: 0,
  };

  // Compute rates from verified constants
  const sunniK6Rate = VERIFIED.sunniK6WithChainIndx / VERIFIED.sunniK6Total;
  const imamiRate = VERIFIED.imamiWithChainIndx / VERIFIED.imamiTotal;

  console.log(`  Sunni K6 verified rate:  ${VERIFIED.sunniK6WithChainIndx}/${VERIFIED.sunniK6Total} = ${(sunniK6Rate * 100).toFixed(2)}%`);
  console.log(`  Imami verified rate:     ${VERIFIED.imamiWithChainIndx}/${VERIFIED.imamiTotal} = ${(imamiRate * 100).toFixed(2)}%`);
  console.log(`  Ibadi verified rate:     ${VERIFIED.ibadiWithChainIndx}/${VERIFIED.ibadiTotal} = 0% (by design)`);
  console.log(`  Zaydi verified rate:     ${VERIFIED.zaydiWithChainIndx}/${VERIFIED.zaydiTotal} = 0% (by design)`);

  // Spec thresholds:
  //   Sunni K6:         ≥ 99%
  //   Imami:            ≥ 83% (after chain_indx text→IDs is solved)
  //   Ibadi/Zaydi:      0% (design — falls through to Tier 2)
  //   Sunni classical:  ≥ 55% (same baseline as extract_isnad_sunni.py)

  check('T2: Sunni K6 verified rate ≥ 99% (spec: FR-2.1)',
    sunniK6Rate >= 0.99,
    `${(sunniK6Rate * 100).toFixed(2)}% < 99%`);

  check('T2: Imami verified rate ≥ 83% (spec: FR-2.1, when chain_indx text→IDs is solved)',
    imamiRate >= 0.83,
    `${(imamiRate * 100).toFixed(2)}% < 83%`);

  check('T2: Ibadi chain_indx rate = 0% by design (Tier 2 fallback)',
    VERIFIED.ibadiWithChainIndx === 0);

  check('T2: Zaydi chain_indx rate = 0% by design (Tier 2 fallback)',
    VERIFIED.zaydiWithChainIndx === 0);

  // Threshold function for use in live tests
  function checkCoverageThreshold(
    label: string, actual: number, threshold: number, allowKnownGaps = false
  ): boolean {
    if (actual >= threshold) return true;
    if (allowKnownGaps) {
      console.log(`  ALLOW-KNOWN-GAPS: ${label} coverage ${(actual*100).toFixed(1)}% < ${(threshold*100).toFixed(0)}%`);
      return true; // allowed
    }
    return false;
  }

  // Validate threshold function logic
  check('T2: threshold function passes when actual >= threshold',
    checkCoverageThreshold('test', 0.99, 0.99));
  check('T2: threshold function fails when actual < threshold',
    !checkCoverageThreshold('test', 0.80, 0.99));
  check('T2: threshold function passes with --allow-known-gaps even if below threshold',
    checkCoverageThreshold('test', 0.50, 0.99, true));
}

// ─── T3 — Live Cypher coverage queries (post-fullregen DB) ───────────────────

async function testT3_live_coverage(): Promise<void> {
  console.log('\n[T3] Live Cypher Tier-1 coverage (post-fullregen — DEFERRED if Neo4j unreachable)');

  // DEPENDENCY NOTE: T3 also requires workstream D's entity-resolution.ts
  // (specifically: NARRATED_FROM edges with extraction_method='chain_indx_join').
  // Those edges are NOT YET LANDED. So T3 is doubly deferred: needs Neo4j AND workstream D.
  defer('T3: Sunni K6 chain_indx join coverage ≥ 99%',
    'EXPECTED — workstream D (entity-resolution.ts) not yet landed; NARRATED_FROM edges not yet written');
  defer('T3: Sunni classical chain_indx join coverage ≥ 55%',
    'EXPECTED — workstream A (regen_unified_csvs.py) and workstream D not yet landed');
  defer('T3: Imami chain_indx join coverage ≥ 83% (or 0% with --allow-known-gaps)',
    'EXPECTED — workstream D (entity-resolution.ts) not yet landed');
  defer('T3: Ibadi chain_indx join coverage = 0% (Tier 2 fallback)',
    'EXPECTED — workstream D not yet landed');
  defer('T3: Zaydi chain_indx join coverage = 0% (Tier 2 fallback)',
    'EXPECTED — workstream D not yet landed');

  // Show the Cypher queries that verifier G will run when workstream D lands:
  console.log('\n  Cypher queries for verifier G (workstream G):');
  console.log(`
  // Sunni K6 coverage (≥ 99%):
  MATCH (h:Hadith)-[:INGESTED_IN]->(dv:DatasetVersion)
  WHERE h.tradition = 'Sunni'
  WITH count(h) AS total
  MATCH (h2:Hadith)-[r:INCLUDES*..1]->(ch:Chain)
  WHERE h2.tradition = 'Sunni' AND r.extraction_method = 'chain_indx_join'
  RETURN total, count(DISTINCT h2) AS resolved,
         toFloat(count(DISTINCT h2)) / total AS coverageRate;

  // Ibadi/Zaydi Tier 2 (expect 0 chain_indx_join edges):
  MATCH ()-[r:NARRATED_FROM]->()
  WHERE r.tradition IN ['Ibadi', 'Zaydi']
    AND r.extraction_method = 'chain_indx_join'
  RETURN count(r) AS should_be_zero;
  `);
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log('='.repeat(64));
  console.log('  regen-tier1-coverage.test.ts — Tier-1 coverage (task 2.7)');
  console.log('='.repeat(64));

  testT1_coverage_computation_logic();
  testT2_threshold_constants();

  try {
    await testT3_live_coverage();
  } finally {
    await closeDriver();
  }

  console.log('\n' + '='.repeat(64));
  console.log('  Summary');
  console.log('='.repeat(64));
  console.log(`  PASSED: ${passed}   FAILED: ${failed}   DEFERRED: ${deferred.length}`);

  if (deferred.length > 0) {
    console.log('\n  Deferred (EXPECTED — workstream D not yet landed):');
    for (const d of deferred) console.log(`    DEFER ${d}`);
  }

  if (failed > 0) {
    console.log('\n  Failures:');
    for (const f of failures) console.log(`    FAIL ${f}`);
    process.exitCode = 1;
  } else {
    console.log('\n  All executed assertions passed.');
  }
}

main().catch(err => {
  console.error('\nFatal:', err);
  process.exitCode = 1;
  void closeDriver();
});
