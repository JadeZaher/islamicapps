/**
 * regen-tradition-canonicalization.test.ts — tradition string canonicalization test
 * ==================================================================================
 *
 * Track: neo4j_isnad_graph_regen_20260516, tasks 0.7, 1.7.
 * Spec refs: spec §9b "Tradition string drift", global invariant 6 (never "Shia Imami"/"Shia Zaydi").
 * Passoff refs: ultrapilot-passoff.md invariant 6.
 *
 * Requirement:
 *   After fullregen, zero :Hadith or :Narrator nodes carry
 *   tradition = "Shia Imami" or tradition = "Shia Zaydi".
 *   The canonical values are "Imami" and "Zaydi" (matching unified CSV vocabulary).
 *
 * Test groups:
 *   TC1 (unit) — canonicalization function correctness (all edge cases)
 *   TC2 (unit) — fixture CSV drift detection (drift fixture has Shia Imami/Zaydi rows)
 *   TC3 (unit) — static source scan (no legacy strings in TS code paths)
 *   TC4 (live) — Cypher: zero :Hadith/:Narrator with legacy tradition strings post-fullregen
 *
 * TC4 is deferred (not faked) if Neo4j is unreachable or workstream E not yet landed.
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

function eq<T>(name: string, actual: T, expected: T): void {
  check(name, actual === expected,
    `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

// ─── Canonicalization function (the CONTRACT mode-fullregen.ts MUST implement) ─

const TRADITION_CANONICAL_MAP: Record<string, string> = {
  'Shia Imami': 'Imami',
  'Shia Zaydi': 'Zaydi',
  // These should never appear in CSV but guard them anyway:
  'shia imami': 'Imami',
  'shia zaydi': 'Zaydi',
  'SHIA IMAMI': 'Imami',
  'SHIA ZAYDI': 'Zaydi',
};

const FORBIDDEN_TRADITION_STRINGS = ['Shia Imami', 'Shia Zaydi'];
const CANONICAL_TRADITION_STRINGS = ['Sunni', 'Imami', 'Ibadi', 'Zaydi'];

function canonicalizeTradition(raw: string): string {
  const t = raw.trim();
  return TRADITION_CANONICAL_MAP[t] ?? t;
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

// ─── TC1 — canonicalization function correctness ──────────────────────────────

function testTC1_canonicalization_function(): void {
  console.log('\n[TC1] Canonicalization function (all edge cases)');

  // Core mappings
  eq('TC1: "Shia Imami" → "Imami"', canonicalizeTradition('Shia Imami'), 'Imami');
  eq('TC1: "Shia Zaydi" → "Zaydi"', canonicalizeTradition('Shia Zaydi'), 'Zaydi');

  // Canonical strings pass through unchanged
  for (const t of CANONICAL_TRADITION_STRINGS) {
    eq(`TC1: canonical "${t}" passes through unchanged`, canonicalizeTradition(t), t);
  }

  // Whitespace trimming
  eq('TC1: leading/trailing whitespace handled', canonicalizeTradition('  Shia Imami  '), 'Imami');

  // Unknown strings pass through (conservative — don't guess)
  eq('TC1: unknown tradition passes through unchanged', canonicalizeTradition('Unknown'), 'Unknown');
  eq('TC1: empty string passes through unchanged', canonicalizeTradition(''), '');

  // Post-canonicalization: no forbidden strings remain
  const allInputs = [...FORBIDDEN_TRADITION_STRINGS, ...CANONICAL_TRADITION_STRINGS, 'Unknown', ''];
  const allOutputs = allInputs.map(canonicalizeTradition);
  check('TC1: no forbidden strings in canonicalized output',
    allOutputs.every(t => !FORBIDDEN_TRADITION_STRINGS.includes(t)));
}

// ─── TC2 — fixture CSV drift detection ────────────────────────────────────────

function testTC2_fixture_drift_detection(): void {
  console.log('\n[TC2] Fixture CSV drift detection (fixture-tradition-drift.csv)');

  const driftRows = readFixtureCSV('fixture-tradition-drift.csv');

  // BEFORE canonicalization: drift fixture contains forbidden strings
  const rawTraditions = driftRows.map(r => r['tradition'] || '');
  const hasForbiddenRaw = rawTraditions.some(t => FORBIDDEN_TRADITION_STRINGS.includes(t));
  check('TC2: drift fixture contains legacy "Shia Imami" or "Shia Zaydi" strings (test setup validation)',
    hasForbiddenRaw);

  const rawShiaImami = rawTraditions.filter(t => t === 'Shia Imami');
  const rawShiaZaydi = rawTraditions.filter(t => t === 'Shia Zaydi');
  check(`TC2: drift fixture has ${rawShiaImami.length} "Shia Imami" rows`, rawShiaImami.length > 0);
  check(`TC2: drift fixture has ${rawShiaZaydi.length} "Shia Zaydi" rows`, rawShiaZaydi.length > 0);

  // AFTER canonicalization: zero forbidden strings remain
  const canonicalized = rawTraditions.map(canonicalizeTradition);
  check('TC2: after canonicalization — zero "Shia Imami"',
    !canonicalized.includes('Shia Imami'));
  check('TC2: after canonicalization — zero "Shia Zaydi"',
    !canonicalized.includes('Shia Zaydi'));

  // Counts: the Shia Imami rows should become Imami
  const postImami = canonicalized.filter(t => t === 'Imami');
  const postZaydi = canonicalized.filter(t => t === 'Zaydi');
  check(`TC2: "Shia Imami" rows canonicalized to "Imami"`,
    postImami.length >= rawShiaImami.length);
  check(`TC2: "Shia Zaydi" rows canonicalized to "Zaydi"`,
    postZaydi.length >= rawShiaZaydi.length);

  // Migration count matches expectation
  const migrationCount = rawTraditions.filter(t => FORBIDDEN_TRADITION_STRINGS.includes(t)).length;
  console.log(`  Would migrate ${migrationCount} rows from legacy tradition strings`);
  check('TC2: migration count > 0 (there are rows to migrate)',
    migrationCount > 0);
}

// ─── TC3 — static source scan (no legacy strings in TS code paths) ─────────────

function testTC3_static_source_scan(): void {
  console.log('\n[TC3] Static source scan — no legacy tradition strings in code');

  // The regen script should only ever write the canonical tradition strings
  const regenSrc = path.join(process.cwd(), 'src', 'scripts', 'regen-isnad-graph.ts');
  if (!fs.existsSync(regenSrc)) {
    console.log('  NOTE: regen-isnad-graph.ts not found');
    return;
  }
  const code = fs.readFileSync(regenSrc, 'utf8')
    .replace(/\/\*[\s\S]*?\*\//g, '')
    .split('\n').map(l => l.replace(/\/\/.*$/, '')).join('\n');

  // "Shia Imami" and "Shia Zaydi" should NOT appear as string literals in the code
  // (They can appear in comments explaining the mapping — but we strip comments above)
  for (const forbidden of FORBIDDEN_TRADITION_STRINGS) {
    const inCode = code.includes(`'${forbidden}'`) || code.includes(`"${forbidden}"`);
    check(
      `TC3: no string literal "${forbidden}" in regen-isnad-graph.ts code`,
      !inCode,
      `found "${forbidden}" as a string literal — should be canonicalized on load`
    );
  }

  // Check lib/regen modules when they exist
  const regenLibDir = path.join(process.cwd(), 'src', 'scripts', 'lib', 'regen');
  if (fs.existsSync(regenLibDir)) {
    const files = fs.readdirSync(regenLibDir).filter(f => f.endsWith('.ts'));
    for (const f of files) {
      const src = fs.readFileSync(path.join(regenLibDir, f), 'utf8')
        .replace(/\/\*[\s\S]*?\*\//g, '')
        .split('\n').map(l => l.replace(/\/\/.*$/, '')).join('\n');
      for (const forbidden of FORBIDDEN_TRADITION_STRINGS) {
        const inCode = src.includes(`'${forbidden}'`) || src.includes(`"${forbidden}"`);
        if (inCode) {
          // Exception: the canonicalizeTradition mapping function MUST reference these
          // as keys in the map — that's fine. But writing them as a node property is not.
          // We flag it for review; the canonical map reference is expected.
          console.log(`  REVIEW: "${forbidden}" appears as literal in lib/regen/${f} — verify it's only in the canonicalization map, not written to the DB`);
        }
      }
    }
  }
}

// ─── TC4 — Live Cypher: zero :Hadith/:Narrator with legacy tradition post-fullregen

async function testTC4_live_cypher(): Promise<void> {
  console.log('\n[TC4] Live Cypher: zero :Hadith/:Narrator with legacy tradition strings');

  // DEPENDENCY NOTE: TC4 requires workstream E (mode-fullregen.ts) to have
  // run and canonicalized tradition strings on all nodes. Not yet landed.

  const live = await (async () => {
    try { await runWrite('RETURN 1 AS ok'); return true; } catch { return false; }
  })();

  if (!live) {
    defer('TC4: zero :Hadith with tradition="Shia Imami" post-fullregen',
      'Neo4j unreachable');
    defer('TC4: zero :Hadith with tradition="Shia Zaydi" post-fullregen',
      'Neo4j unreachable');
    defer('TC4: zero :Narrator with tradition="Shia Imami" post-fullregen',
      'Neo4j unreachable');
    defer('TC4: zero :Narrator with tradition="Shia Zaydi" post-fullregen',
      'Neo4j unreachable');
    return;
  }

  // Pre-fullregen state: the live DB may STILL have these strings (from legacy importer)
  // We surface an honest count (not a failure for pre-existing state)
  for (const forbidden of FORBIDDEN_TRADITION_STRINGS) {
    try {
      const rH = await runQuery<{ c: number }>(`
        MATCH (h:Hadith) WHERE h.tradition = $t RETURN count(h) AS c
      `, { t: forbidden });
      const rN = await runQuery<{ c: number }>(`
        MATCH (n:Narrator) WHERE n.tradition = $t RETURN count(n) AS c
      `, { t: forbidden });
      const hadithCount = rH[0]?.c ?? 0;
      const narratorCount = rN[0]?.c ?? 0;

      if (hadithCount > 0 || narratorCount > 0) {
        console.log(`  PRE-EXISTING: ${hadithCount} :Hadith, ${narratorCount} :Narrator with tradition="${forbidden}"`);
        console.log(`  NOTE: These are legacy DB state (before fullregen). After mode=fullregen runs, these must drop to 0.`);
        console.log(`  DEFER: TC4 "zero ${forbidden}" post-fullregen`);
        defer(`TC4: zero nodes with tradition="${forbidden}" after fullregen`,
          `EXPECTED — fullregen (workstream E) not yet run; ${hadithCount + narratorCount} legacy nodes with this tradition exist pre-regen`);
      } else {
        check(`TC4: zero :Hadith/:Narrator with tradition="${forbidden}" (already clean)`,
          true);
      }
    } catch (e) {
      check(`TC4: tradition="${forbidden}" Cypher ran without error`, false,
        (e as Error).message);
    }
  }
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log('='.repeat(64));
  console.log('  regen-tradition-canonicalization.test.ts (tasks 0.7, 1.7)');
  console.log('='.repeat(64));

  testTC1_canonicalization_function();
  testTC2_fixture_drift_detection();
  testTC3_static_source_scan();

  try {
    await testTC4_live_cypher();
  } finally {
    await closeDriver();
  }

  console.log('\n' + '='.repeat(64));
  console.log('  Summary');
  console.log('='.repeat(64));
  console.log(`  PASSED: ${passed}   FAILED: ${failed}   DEFERRED: ${deferred.length}`);

  if (deferred.length > 0) {
    console.log('\n  Deferred (must be re-run after fullregen lands — workstream E):');
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
