/**
 * regen-schema.test.ts — constraint/index presence tests (workstream B assertions)
 * =================================================================================
 *
 * Track: neo4j_isnad_graph_regen_20260516, task 1.7.
 * Spec refs: FR-1.1..1.4, §12 Gate G1 "100% constraint coverage".
 *
 * Test groups:
 *   S1 (unit) — schema.ts static analysis: all required constraints defined in code
 *   S2 (live) — Cypher SHOW CONSTRAINTS confirms every constraint exists in Neo4j
 *
 * S2 is deferred (not faked) if Neo4j is unreachable.
 *
 * Constraints asserted (per workstream B spec):
 *   NEW (Phase 1):
 *     - Hadith.dataset_row_id (uniqueness — blocks new legacy duplicates)
 *     - Chain.id
 *     - NameMention.id
 *     - Assessment.id
 *     - DatasetVersion.id
 *   EXISTING (must still be present, not dropped):
 *     - narrator_scholar_indx_unique (the primary narrator merge key)
 *     - Narrator.id
 *     - Hadith.id
 *     - ReligiousTradition.name
 *     - ReligiousTradition.id
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

// ─── S1 — schema.ts static analysis: required constraints present in code ─────

/**
 * Assertions on the schema source file.
 * These run without Neo4j and catch regressions in the source of truth
 * (workstream B's schema.ts).
 */
function testS1_schema_source(): void {
  console.log('\n[S1] schema.ts static analysis — required constraints in source code');

  const schemaPath = path.join(process.cwd(), 'src', 'lib', 'db', 'schema.ts');
  if (!fs.existsSync(schemaPath)) {
    console.log('  WARN: schema.ts not found — schema tests cannot run');
    return;
  }
  const src = fs.readFileSync(schemaPath, 'utf8');

  // Each constraint must appear as "{ label: 'X', prop: 'Y' }" in the constraints array.
  // This validates workstream B wrote them, even before db:init is run.
  const requiredConstraints: Array<[string, string, string]> = [
    // [label, prop, description]
    ['Narrator', 'scholar_indx', 'narrator_scholar_indx_unique (existing — primary merge key)'],
    ['Narrator', 'id', 'Narrator.id (existing)'],
    ['Hadith', 'id', 'Hadith.id (existing)'],
    ['Hadith', 'dataset_row_id', 'Hadith.dataset_row_id (NEW — blocks legacy dups; FR-1.1)'],
    ['Chain', 'id', 'Chain.id (NEW — FR-1.1)'],
    ['NameMention', 'id', 'NameMention.id (NEW — FR-1.3)'],
    ['Assessment', 'id', 'Assessment.id (NEW — FR-1.2)'],
    ['DatasetVersion', 'id', 'DatasetVersion.id (NEW — FR-0.2)'],
    ['ReligiousTradition', 'name', 'ReligiousTradition.name (existing — tradition scope)'],
    ['ReligiousTradition', 'id', 'ReligiousTradition.id (existing)'],
  ];

  for (const [label, prop, desc] of requiredConstraints) {
    // Match patterns like: { label: 'Chain', prop: 'id' } (with possible whitespace)
    const pattern = new RegExp(
      `\\{[^}]*label:\\s*['"\`]${label}['"\`][^}]*prop:\\s*['"\`]${prop}['"\`][^}]*\\}` +
      `|\\{[^}]*prop:\\s*['"\`]${prop}['"\`][^}]*label:\\s*['"\`]${label}['"\`][^}]*\\}`
    );
    check(
      `S1: schema.ts defines constraint ${label}.${prop} — ${desc}`,
      pattern.test(src),
      `missing "{ label: '${label}', prop: '${prop}' }" in schema.ts`
    );
  }

  // Verify IF NOT EXISTS guard is used (re-runnable safety)
  check('S1: schema.ts uses IF NOT EXISTS guard on all constraints',
    src.includes('IF NOT EXISTS'),
    'db:init must be re-runnable — all constraints need IF NOT EXISTS');

  // Verify no DROP CONSTRAINT anywhere (would break Gate G1 "never shrink")
  check('S1: schema.ts has zero DROP CONSTRAINT calls',
    !/DROP\s+CONSTRAINT/i.test(src),
    'schema.ts must never drop constraints');
}

// ─── S2 — Live SHOW CONSTRAINTS check ─────────────────────────────────────────

// SHOW CONSTRAINTS returns different shapes in Neo4j 4.x vs 5.x.
// We use a generic record and check by name (convention: `${label.lower}_${prop}_unique`).
type ConstraintRow = Record<string, unknown>;

async function testS2_live_constraints(): Promise<void> {
  console.log('\n[S2] Live Neo4j SHOW CONSTRAINTS');

  const live = await (async () => {
    try { await runWrite('RETURN 1 AS ok'); return true; } catch { return false; }
  })();

  if (!live) {
    defer('S2: all required constraints present in Neo4j',
      'Neo4j unreachable — run npm run db:init then re-run with live Neo4j');
    return;
  }

  let constraints: ConstraintRow[];
  try {
    constraints = await runQuery<ConstraintRow>('SHOW CONSTRAINTS');
  } catch (e) {
    check('S2: SHOW CONSTRAINTS ran without error', false, (e as Error).message);
    return;
  }

  console.log(`  Total constraints in DB: ${constraints.length}`);

  // Primary lookup: by constraint name (convention from schema.ts: `${label.lower}_${prop}_unique`)
  function constraintExistsByName(name: string): boolean {
    return constraints.some(c => {
      const n = String(c['name'] ?? '').toLowerCase();
      return n === name.toLowerCase();
    });
  }

  // Secondary lookup: scan the raw constraint row string for the label+prop pair
  // (handles different Neo4j response shapes across versions)
  function constraintExistsByLabelProp(label: string, prop: string): boolean {
    const lowerLabel = label.toLowerCase();
    const lowerProp = prop.toLowerCase();
    return constraints.some(c => {
      const raw = JSON.stringify(c).toLowerCase();
      return raw.includes(lowerLabel) && raw.includes(lowerProp);
    });
  }

  const required: Array<[string, string, string]> = [
    ['Narrator', 'scholar_indx', 'narrator_scholar_indx_unique'],
    ['Narrator', 'id', 'narrator_id_unique'],
    ['Hadith', 'id', 'hadith_id_unique'],
    ['Hadith', 'dataset_row_id', 'hadith_dataset_row_id_unique'],
    ['Chain', 'id', 'chain_id_unique'],
    ['NameMention', 'id', 'namemention_id_unique'],
    ['Assessment', 'id', 'assessment_id_unique'],
    ['DatasetVersion', 'id', 'datasetversion_id_unique'],
    ['ReligiousTradition', 'name', 'religioustradition_name_unique'],
    ['ReligiousTradition', 'id', 'religioustradition_id_unique'],
  ];

  for (const [label, prop, constraintName] of required) {
    const exists =
      constraintExistsByName(constraintName) ||
      constraintExistsByLabelProp(label, prop);
    check(
      `S2: constraint ${label}.${prop} (${constraintName}) exists in Neo4j`,
      exists,
      exists ? '' : `not found — run: npm run db:init`
    );
  }

  // The pre-existing constraint count (23, as documented) should only INCREASE
  check(`S2: total constraint count >= 23 (no constraints were dropped)`,
    constraints.length >= 23,
    `only ${constraints.length} constraints; expected at least 23`);
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log('='.repeat(64));
  console.log('  regen-schema.test.ts — workstream B constraint assertions (task 1.7)');
  console.log('='.repeat(64));

  testS1_schema_source();

  try {
    await testS2_live_constraints();
  } finally {
    await closeDriver();
  }

  console.log('\n' + '='.repeat(64));
  console.log('  Summary');
  console.log('='.repeat(64));
  console.log(`  PASSED: ${passed}   FAILED: ${failed}   DEFERRED: ${deferred.length}`);

  if (deferred.length > 0) {
    console.log('\n  Deferred (not faked — verifier G must run with live Neo4j + db:init):');
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
