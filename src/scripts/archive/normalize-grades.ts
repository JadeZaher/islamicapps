// DEPRECATED 2026-05-20 — superseded by `npm run db:regen` (track: neo4j_isnad_graph_regen_20260516).
// Archived for historical reference; see src/scripts/archive/README.md for full disposition.
/**
 * normalize-grades.ts
 *
 * Reads every distinct (display_grade, tradition) pair from Neo4j,
 * computes grade_canonical + grade_detail via the grade-taxonomy module,
 * then batch-updates all Hadith nodes.
 *
 * Strategy: group-by-grade (~200 distinct combos) rather than per-hadith
 * (~99K), so the whole run is ~200 write queries + 1 index creation.
 *
 * Usage:
 *   npx tsx src/scripts/normalize-grades.ts
 */

import { loadEnv } from './lib/env';
import { runQuery, runWrite, closeDriver } from '../lib/db/neo4j';
import { mapToCanonical, cleanGradeDetail, GradeCanonical } from '../lib/constants/grade-taxonomy';

loadEnv();

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GradeGroup {
  grade: string | null;
  tradition: string | null;
  count: number;
}

interface UpdateResult {
  updated: number;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  console.log('='.repeat(60));
  console.log('  Hadith Grade Normalisation');
  console.log('='.repeat(60));

  // ------------------------------------------------------------------
  // Step 1 -- Fetch distinct (display_grade, tradition) groups
  // ------------------------------------------------------------------
  console.log('\n[1/4] Querying distinct grade groups...');

  const groups = await runQuery<GradeGroup>(`
    MATCH (h:Hadith)
    RETURN h.display_grade AS grade, h.tradition AS tradition, count(h) AS count
    ORDER BY count DESC
  `);

  console.log(`      Found ${groups.length} distinct (grade, tradition) combinations`);
  const totalHadiths = groups.reduce((sum, g) => sum + g.count, 0);
  console.log(`      Covering ${totalHadiths.toLocaleString()} hadiths total`);

  // ------------------------------------------------------------------
  // Step 2 -- Compute canonical mapping for each group
  // ------------------------------------------------------------------
  console.log('\n[2/4] Computing canonical mappings...');

  interface MappedGroup extends GradeGroup {
    canonical: GradeCanonical;
    detail: string;
  }

  const mapped: MappedGroup[] = groups.map((g) => ({
    ...g,
    canonical: mapToCanonical(g.grade, g.tradition),
    detail: cleanGradeDetail(g.grade),
  }));

  // Log a few examples
  const sample = mapped.slice(0, 15);
  console.log('\n      Sample mappings:');
  console.log('      ' + '-'.repeat(80));
  for (const m of sample) {
    const gradeStr = m.grade === null || m.grade === '' ? '(empty)' : m.grade;
    console.log(
      `      ${String(m.count).padStart(6)} | ${(m.tradition ?? '(null)').padEnd(10)} | ${gradeStr.padEnd(30)} -> ${m.canonical}`,
    );
  }
  console.log('      ' + '-'.repeat(80));

  // ------------------------------------------------------------------
  // Step 3 -- Batch update Neo4j (one query per group)
  // ------------------------------------------------------------------
  console.log('\n[3/4] Updating Hadith nodes in Neo4j...');

  let updatedTotal = 0;
  let groupsProcessed = 0;

  for (const m of mapped) {
    // Build a WHERE clause that correctly handles null grade and null tradition
    const gradeIsNull = m.grade === null || m.grade === undefined;
    const traditionIsNull = m.tradition === null || m.tradition === undefined;

    let whereClause: string;
    const params: Record<string, unknown> = {
      canonical: m.canonical,
      detail: m.detail,
    };

    if (gradeIsNull && traditionIsNull) {
      whereClause = 'h.display_grade IS NULL AND h.tradition IS NULL';
    } else if (gradeIsNull) {
      whereClause = 'h.display_grade IS NULL AND h.tradition = $tradition';
      params.tradition = m.tradition;
    } else if (traditionIsNull) {
      whereClause = 'h.display_grade = $grade AND h.tradition IS NULL';
      params.grade = m.grade;
    } else {
      whereClause = 'h.display_grade = $grade AND h.tradition = $tradition';
      params.grade = m.grade;
      params.tradition = m.tradition;
    }

    try {
      const result = await runWrite<UpdateResult>(
        `
        MATCH (h:Hadith)
        WHERE ${whereClause}
        SET h.grade_canonical = $canonical,
            h.grade_detail    = $detail
        RETURN count(h) AS updated
        `,
        params,
      );

      const count = result[0]?.updated ?? 0;
      updatedTotal += count;
      groupsProcessed++;

      if (groupsProcessed % 50 === 0 || groupsProcessed === mapped.length) {
        console.log(
          `      ... ${groupsProcessed}/${mapped.length} groups -> ${updatedTotal.toLocaleString()} hadiths updated`,
        );
      }
    } catch (err) {
      const gradeStr = m.grade === null ? 'NULL' : `"${m.grade}"`;
      console.error(`      ERROR updating grade=${gradeStr} tradition=${m.tradition}:`, err);
    }
  }

  console.log(`      Done. ${updatedTotal.toLocaleString()} hadiths updated across ${groupsProcessed} groups.`);

  // ------------------------------------------------------------------
  // Step 4 -- Create index + summary report
  // ------------------------------------------------------------------
  console.log('\n[4/4] Creating index and generating summary...');

  try {
    await runWrite(
      'CREATE INDEX hadith_grade_canonical_idx IF NOT EXISTS FOR (h:Hadith) ON (h.grade_canonical)',
    );
    console.log('      Index hadith_grade_canonical_idx created (or already existed).');
  } catch (err) {
    console.warn('      Warning: could not create index:', err);
  }

  // Summary distribution per tradition
  const summary = await runQuery<{
    tradition: string | null;
    canonical: string;
    cnt: number;
  }>(`
    MATCH (h:Hadith)
    WHERE h.grade_canonical IS NOT NULL
    RETURN h.tradition AS tradition, h.grade_canonical AS canonical, count(h) AS cnt
    ORDER BY tradition, cnt DESC
  `);

  // Group by tradition for display
  const byTradition = new Map<string, Map<string, number>>();
  for (const row of summary) {
    const trad = row.tradition ?? '(none)';
    if (!byTradition.has(trad)) byTradition.set(trad, new Map());
    byTradition.get(trad)!.set(row.canonical, row.cnt);
  }

  console.log('\n' + '='.repeat(60));
  console.log('  Grade Distribution by Tradition');
  console.log('='.repeat(60));

  for (const [tradition, grades] of byTradition) {
    console.log(`\n  [${tradition}]`);
    const tradTotal = [...grades.values()].reduce((a, b) => a + b, 0);
    for (const [grade, count] of grades) {
      const pct = ((count / tradTotal) * 100).toFixed(1);
      console.log(`    ${grade.padEnd(14)} ${String(count).padStart(7)}  (${pct}%)`);
    }
    console.log(`    ${'TOTAL'.padEnd(14)} ${String(tradTotal).padStart(7)}`);
  }

  // Grand total
  const grandTotal = [...byTradition.values()].reduce(
    (sum, m) => sum + [...m.values()].reduce((a, b) => a + b, 0),
    0,
  );
  console.log(`\n  Grand total: ${grandTotal.toLocaleString()} hadiths normalised.`);
  console.log('='.repeat(60));

  await closeDriver();
  console.log('\nDone.');
}

main().catch((err) => {
  console.error('Fatal error:', err);
  process.exit(1);
});
