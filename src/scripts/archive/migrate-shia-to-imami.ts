// DEPRECATED 2026-05-20 — superseded by `npm run db:regen` (track: neo4j_isnad_graph_regen_20260516).
// Archived for historical reference; see src/scripts/archive/README.md for full disposition.
/**
 * migrate-shia-to-imami.ts
 * ========================
 * Re-tags hadiths with tradition='Shia' to tradition='Shia Imami' (Twelver)
 * and migrates IN_SCHOOL edges from the legacy 'Shia' SchoolOfThought node
 * to the canonical 'Shia Imami' node.
 *
 * Idempotent — safe to run multiple times.
 *
 * Usage:
 *   npx tsx src/scripts/migrate-shia-to-imami.ts
 *   npx tsx src/scripts/migrate-shia-to-imami.ts --dry-run
 */

import { loadEnv } from './lib/env';
import { runQuery, runWrite, closeDriver } from '../lib/db/neo4j';

loadEnv();

async function main() {
  const dryRun = process.argv.includes('--dry-run');

  console.log('='.repeat(60));
  console.log('  Migrate tradition=Shia → Shia Imami');
  console.log('='.repeat(60));
  if (dryRun) console.log('  [DRY RUN — no writes]\n');

  // 1. Show current state
  const before = await runQuery<{ tradition: string | null; cnt: number }>(
    `MATCH (h:Hadith) RETURN h.tradition AS tradition, count(h) AS cnt ORDER BY cnt DESC`
  );
  console.log('Before:');
  for (const r of before) {
    console.log(`  ${String(r.tradition ?? '(null)').padEnd(22)} ${Number(r.cnt)}`);
  }

  // 2. Update tradition property on all Shia hadiths
  if (!dryRun) {
    const updated = await runWrite<{ updated: number }>(
      `MATCH (h:Hadith) WHERE h.tradition = 'Shia'
       SET h.tradition = 'Shia Imami'
       RETURN count(h) AS updated`
    );
    console.log(`\nUpdated ${Number(updated[0]?.updated ?? 0)} hadiths: tradition='Shia' → 'Shia Imami'`);
  } else {
    const count = before.find(r => r.tradition === 'Shia');
    console.log(`\nWould update ${Number(count?.cnt ?? 0)} hadiths: tradition='Shia' → 'Shia Imami'`);
  }

  // 3. Migrate IN_SCHOOL edges from legacy 'Shia' to 'Shia Imami'
  if (!dryRun) {
    // Create edges to Shia Imami for hadiths that had edges to legacy Shia
    const migrated = await runWrite<{ migrated: number }>(
      `MATCH (h:Hadith)-[old:IN_SCHOOL]->(legacy:SchoolOfThought {name: 'Shia'})
       MATCH (imami:SchoolOfThought {name: 'Shia Imami'})
       MERGE (h)-[:IN_SCHOOL]->(imami)
       DELETE old
       RETURN count(h) AS migrated`
    );
    console.log(`Migrated ${Number(migrated[0]?.migrated ?? 0)} IN_SCHOOL edges: Shia → Shia Imami`);
  }

  // 4. Migrate Source CANON_OF edges
  if (!dryRun) {
    const srcMigrated = await runWrite<{ migrated: number }>(
      `MATCH (s:Source)-[old:CANON_OF]->(legacy:SchoolOfThought {name: 'Shia'})
       MATCH (imami:SchoolOfThought {name: 'Shia Imami'})
       MERGE (s)-[:CANON_OF]->(imami)
       DELETE old
       RETURN count(s) AS migrated`
    );
    console.log(`Migrated ${Number(srcMigrated[0]?.migrated ?? 0)} Source CANON_OF edges: Shia → Shia Imami`);
  }

  // 5. Remove legacy Shia SchoolOfThought if it has no remaining edges
  if (!dryRun) {
    const remaining = await runQuery<{ cnt: number }>(
      `MATCH (s:SchoolOfThought {name: 'Shia'})-[r]-() RETURN count(r) AS cnt`
    );
    if (Number(remaining[0]?.cnt ?? 0) === 0) {
      await runWrite(`MATCH (s:SchoolOfThought {name: 'Shia'}) DELETE s`);
      console.log(`Deleted orphaned SchoolOfThought node 'Shia'`);
    } else {
      console.log(`Legacy 'Shia' node still has ${Number(remaining[0]?.cnt)} edges — kept`);
    }
  }

  // 6. Verify
  const after = await runQuery<{ tradition: string | null; cnt: number }>(
    `MATCH (h:Hadith) RETURN h.tradition AS tradition, count(h) AS cnt ORDER BY cnt DESC`
  );
  console.log('\nAfter:');
  for (const r of after) {
    console.log(`  ${String(r.tradition ?? '(null)').padEnd(22)} ${Number(r.cnt)}`);
  }

  console.log('\nDone.');
  await closeDriver();
}

main()
  .catch((err) => {
    console.error('Fatal:', err.message);
    process.exit(1);
  })
  .finally(() => closeDriver());
