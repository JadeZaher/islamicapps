/**
 * regen-multi-isnad.test.ts — multi-isnad :Chain node test
 * =========================================================
 *
 * Track: neo4j_isnad_graph_regen_20260516, task 1.7.
 * Spec refs: FR-1.1, §9 Reliability Ledger.
 *
 * Spec requirement (FR-1.1):
 *   "A hadith with N distinct chains has N :Chain nodes, not one merged chain."
 *   ":Chain carries position-ordered membership so chain order is recoverable."
 *
 * Test groups:
 *   MI1 (unit) — distinct-isnad detection logic (no Neo4j)
 *   MI2 (unit) — Chain key derivation (distinct chains → distinct keys)
 *   MI3 (live) — Neo4j assertion: hadith with 2 distinct chains → 2 :Chain nodes
 *
 * MI3 depends on workstream C's load-chain.ts (not yet landed) — deferred.
 *
 * Fixture: src/scripts/__tests__/fixtures/regen/fixture-multi-isnad.csv
 *   - "multi-isnad-h1-chain1" and "multi-isnad-h1-chain2" represent the same
 *     hadith text (same matn) transmitted via two distinct isnads.
 *   - "single-chain-hadith" has one chain only.
 */

import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
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

function eq<T>(name: string, actual: T, expected: T): void {
  check(name, actual === expected,
    `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

// ─── CSV parsing ──────────────────────────────────────────────────────────────

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

// ─── Chain key derivation (mirrors load-chain.ts contract) ───────────────────

/**
 * A :Chain is keyed by the hadith's stable business key + a hash of the
 * normalized isnad string. Two rows with the same hadith_no but different
 * sanad strings → two distinct Chain IDs.
 *
 * This is the CONTRACT that workstream C's load-chain.ts MUST satisfy.
 * We test the contract here independently of the module.
 */
function deriveChainKey(hadithBusinessKey: string, sanadNormalized: string): string {
  const h = crypto.createHash('sha256')
    .update(`${hadithBusinessKey}::${sanadNormalized}`)
    .digest('hex')
    .slice(0, 16);
  return `chain-${h}`;
}

/**
 * Group rows by "logical hadith" (same source + hadith_no = same matn).
 * Returns a map from the logical hadith key → array of rows (one per distinct chain).
 */
function groupByHadith(rows: CSVRow[]): Map<string, CSVRow[]> {
  const m = new Map<string, CSVRow[]>();
  for (const row of rows) {
    // Strip chain suffix from hadith_no to find the logical hadith
    // (e.g. hadith_no "100" and "100b" both belong to Bukhari #100)
    const logicalKey = `${row['source']}::${(row['hadith_no'] || '').replace(/[a-z]$/, '')}`;
    if (!m.has(logicalKey)) m.set(logicalKey, []);
    m.get(logicalKey)!.push(row);
  }
  return m;
}

// ─── MI1 — Distinct-isnad detection logic (no Neo4j) ─────────────────────────

function testMI1_distinct_isnad_detection(): void {
  console.log('\n[MI1] Distinct-isnad detection logic (fixture CSV, no Neo4j)');

  const rows = readFixtureCSV('fixture-multi-isnad.csv');
  eq('fixture-multi-isnad.csv row count', rows.length, 3);

  // Two rows share the same logical hadith (Bukhari #100) but have different sanads
  const bukhari100 = rows.filter(r =>
    r['source'] === 'Sahih Bukhari' &&
    (r['hadith_no'] === '100' || r['hadith_no'] === '100b')
  );
  eq('Bukhari #100 has two rows in fixture (two distinct chains)', bukhari100.length, 2);

  // The sanad strings must be different
  const sanads = bukhari100.map(r => r['sanad'] || '');
  check('Two Bukhari #100 rows have different sanad strings',
    sanads[0] !== sanads[1],
    `sanad[0]="${sanads[0]}", sanad[1]="${sanads[1]}"`);

  // Single-chain hadith
  const singleChain = rows.filter(r => r['source'] === 'Sahih Muslim');
  eq('Sahih Muslim fixture has 1 row (single chain)', singleChain.length, 1);

  // Grouping logic
  const grouped = groupByHadith(rows);
  console.log(`  Distinct logical hadiths in fixture: ${grouped.size}`);
  for (const [key, group] of grouped) {
    console.log(`    "${key}": ${group.length} chain(s)`);
  }

  // Find the hadith with multiple chains
  const multiChainEntries = [...grouped.entries()].filter(([, g]) => g.length > 1);
  check('At least one logical hadith has multiple chains in fixture',
    multiChainEntries.length >= 1,
    `expected ≥1 multi-chain hadith, found ${multiChainEntries.length}`);
}

// ─── MI2 — Chain key derivation (distinct chains → distinct keys) ─────────────

function testMI2_chain_key_derivation(): void {
  console.log('\n[MI2] Chain key derivation (distinct isnads → distinct keys)');

  const rows = readFixtureCSV('fixture-multi-isnad.csv');
  const bukhari100 = rows.filter(r =>
    r['source'] === 'Sahih Bukhari' &&
    (r['hadith_no'] === '100' || r['hadith_no'] === '100b')
  );

  const hadithKey = 'bukhari::100'; // the logical hadith business key
  const chain1Key = deriveChainKey(hadithKey, bukhari100[0]?.['sanad'] || '');
  const chain2Key = deriveChainKey(hadithKey, bukhari100[1]?.['sanad'] || '');

  check('Two distinct isnads for same hadith → two distinct chain keys',
    chain1Key !== chain2Key,
    `chain1Key="${chain1Key}", chain2Key="${chain2Key}"`);

  // Determinism: same inputs → same key
  const chain1KeyAgain = deriveChainKey(hadithKey, bukhari100[0]?.['sanad'] || '');
  check('Chain key derivation is deterministic (same input → same key)',
    chain1Key === chain1KeyAgain);

  // Single-chain hadith → exactly one key
  const singleChain = rows.find(r => r['source'] === 'Sahih Muslim');
  if (singleChain) {
    const singleKey = deriveChainKey('muslim::200', singleChain['sanad'] || '');
    check('Single-chain hadith → one unique chain key', singleKey.startsWith('chain-'));
  }

  // Empty sanad → still unique (keyed by hadith business key)
  const emptyKey = deriveChainKey('test::1', '');
  check('Empty sanad still produces a valid chain key', emptyKey.startsWith('chain-'));

  // Two different hadiths with the SAME sanad → different chain keys (because hadith biz key differs)
  const key1 = deriveChainKey('bukhari::1', 'عمر بن الخطاب');
  const key2 = deriveChainKey('muslim::1', 'عمر بن الخطاب');
  check('Same sanad on different hadiths → different chain keys',
    key1 !== key2);
}

// ─── MI3 — Live Neo4j: two distinct chains → two :Chain nodes ────────────────

async function testMI3_live_neo4j(): Promise<void> {
  console.log('\n[MI3] Live Neo4j: hadith with 2 distinct chains → 2 :Chain nodes');

  // DEPENDENCY NOTE: This test requires workstream C's load-chain.ts to have
  // written :Chain nodes to Neo4j. That module is NOT YET LANDED.
  defer('MI3: 2 distinct chains → 2 :Chain nodes in Neo4j',
    'EXPECTED — module not yet landed: src/scripts/lib/regen/load-chain.ts (workstream C)');

  // Document the Cypher assertion for verifier G:
  console.log('\n  Cypher for verifier G (workstream G):');
  console.log(`
  // Find hadiths that share a text_ar fingerprint but have multiple chains:
  MATCH (h:Hadith)-[:INCLUDES|PART_OF]->(c:Chain)
  WITH h, count(DISTINCT c) AS chainCount
  WHERE chainCount > 1
  RETURN h.dataset_row_id, h.source, h.hadith_no, chainCount
  ORDER BY chainCount DESC LIMIT 10;

  // Assert: after fullregen, fixture multi-isnad hadith has exactly 2 chains:
  MATCH (h:Hadith {source: 'Sahih Bukhari', hadith_no: '100'})-[:INCLUDES]->(c:Chain)
  RETURN count(DISTINCT c) AS chainCount
  // Expected: 2
  `);
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log('='.repeat(64));
  console.log('  regen-multi-isnad.test.ts — multi-isnad :Chain node test (task 1.7)');
  console.log('='.repeat(64));

  testMI1_distinct_isnad_detection();
  testMI2_chain_key_derivation();

  try {
    await testMI3_live_neo4j();
  } finally {
    await closeDriver();
  }

  console.log('\n' + '='.repeat(64));
  console.log('  Summary');
  console.log('='.repeat(64));
  console.log(`  PASSED: ${passed}   FAILED: ${failed}   DEFERRED: ${deferred.length}`);

  if (deferred.length > 0) {
    console.log('\n  Deferred (EXPECTED — workstream C load-chain.ts not yet landed):');
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
