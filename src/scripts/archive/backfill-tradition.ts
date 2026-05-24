// DEPRECATED 2026-05-20 — superseded by `npm run db:regen` (track: neo4j_isnad_graph_regen_20260516).
// Archived for historical reference; see src/scripts/archive/README.md for full disposition.
/**
 * Backfill tradition='Sunni' on hadiths that don't have a tradition set.
 * Shia hadiths already have tradition='Shia' from the import script.
 */
import { loadEnv } from './lib/env';
import { runWrite, runQuery, closeDriver } from '../lib/db/neo4j';

loadEnv();

async function main() {
  const before = await runQuery<{ tradition: string; cnt: number }>(
    `MATCH (h:Hadith) RETURN h.tradition AS tradition, count(h) AS cnt ORDER BY cnt DESC`
  );
  console.log('Before:');
  for (const r of before) {
    console.log(`  ${r.tradition || '(null)'}: ${r.cnt}`);
  }

  const result = await runWrite<{ updated: number }>(
    `MATCH (h:Hadith) WHERE h.tradition IS NULL OR h.tradition = '' SET h.tradition = 'Sunni' RETURN count(h) AS updated`
  );
  console.log(`\nUpdated ${result[0]?.updated ?? 0} hadiths to tradition='Sunni'`);

  const after = await runQuery<{ tradition: string; cnt: number }>(
    `MATCH (h:Hadith) RETURN h.tradition AS tradition, count(h) AS cnt ORDER BY cnt DESC`
  );
  console.log('\nAfter:');
  for (const r of after) {
    console.log(`  ${r.tradition || '(null)'}: ${r.cnt}`);
  }

  await closeDriver();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
