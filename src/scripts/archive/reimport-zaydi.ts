// DEPRECATED 2026-05-20 — superseded by `npm run db:regen` (track: neo4j_isnad_graph_regen_20260516).
// Archived for historical reference; see src/scripts/archive/README.md for full disposition.
/**
 * reimport-zaydi.ts
 * =================
 * Removes old Zaydi hadiths from Neo4j and re-imports from the updated
 * parsed_zaydi_hadiths.json (625+ hadiths after parser fixes).
 *
 * Steps:
 *   1. Delete all existing Zaydi hadiths (tradition='Shia Zaydi')
 *   2. Re-run the standard import from parsed_zaydi_hadiths.json
 *
 * Usage:
 *   npx tsx src/scripts/reimport-zaydi.ts
 *   npx tsx src/scripts/reimport-zaydi.ts --dry-run
 */

import { loadEnv } from './lib/env';
import { runQuery, runWrite, closeDriver } from '../lib/db/neo4j';

loadEnv();

async function main() {
  const dryRun = process.argv.includes('--dry-run');

  console.log('='.repeat(60));
  console.log('  Re-import Zaydi Hadiths');
  console.log('='.repeat(60));
  if (dryRun) console.log('  [DRY RUN]\n');

  // 1. Count existing
  const before = await runQuery<{ cnt: number }>(
    `MATCH (h:Hadith {tradition: 'Shia Zaydi'}) RETURN count(h) AS cnt`
  );
  console.log(`\nExisting Zaydi hadiths: ${Number(before[0]?.cnt ?? 0)}`);

  // 2. Delete existing Zaydi hadiths and their edges
  if (!dryRun) {
    // Delete in batches to avoid memory issues
    let deleted = 0;
    let batch;
    do {
      batch = await runWrite<{ cnt: number }>(
        `MATCH (h:Hadith {tradition: 'Shia Zaydi'})
         WITH h LIMIT 500
         DETACH DELETE h
         RETURN count(*) AS cnt`
      );
      deleted += Number(batch[0]?.cnt ?? 0);
      if (Number(batch[0]?.cnt ?? 0) > 0) {
        process.stdout.write(`  Deleted ${deleted} hadiths...\r`);
      }
    } while (Number(batch[0]?.cnt ?? 0) > 0);
    console.log(`  Deleted ${deleted} Zaydi hadiths total`);
  }

  // 3. Re-import using the standard import script
  console.log('\n  Now run the import script:');
  console.log('  npx tsx src/scripts/import-zaydi-collections.ts\n');

  // Verify
  const after = await runQuery<{ cnt: number }>(
    `MATCH (h:Hadith {tradition: 'Shia Zaydi'}) RETURN count(h) AS cnt`
  );
  console.log(`Zaydi hadiths after cleanup: ${Number(after[0]?.cnt ?? 0)}`);

  await closeDriver();
}

main().catch((err) => {
  console.error('Fatal:', err.message);
  process.exit(1);
});
