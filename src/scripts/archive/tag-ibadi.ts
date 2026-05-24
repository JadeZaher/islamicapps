// DEPRECATED 2026-05-20 — superseded by `npm run db:regen` (track: neo4j_isnad_graph_regen_20260516).
// Archived for historical reference; see src/scripts/archive/README.md for full disposition.
/**
 * Tag Musnad al-Rabi hadiths as Ibadi tradition.
 */
import { loadEnv } from './lib/env';
import { runWrite, runQuery, closeDriver } from '../lib/db/neo4j';

loadEnv();

async function main() {
  // Check
  const check = await runQuery<{ source: string; tradition: string; cnt: number }>(
    `MATCH (h:Hadith) WHERE h.source CONTAINS 'Rabi' RETURN h.source AS source, h.tradition AS tradition, count(h) AS cnt`
  );
  console.log('Musnad al-Rabi hadiths:');
  for (const r of check) console.log(`  ${r.source}: ${r.tradition} (${r.cnt})`);

  // Tag as Ibadi
  const result = await runWrite<{ updated: number }>(
    `MATCH (h:Hadith) WHERE h.source CONTAINS 'Rabi' SET h.tradition = 'Ibadi' RETURN count(h) AS updated`
  );
  console.log(`\nUpdated ${result[0]?.updated ?? 0} hadiths to Ibadi`);

  // Create SchoolOfThought:Ibadi
  await runWrite(
    `MERGE (s:SchoolOfThought {name: 'Ibadi'}) ON CREATE SET s.id = randomUUID(), s.tradition = 'Ibadi', s.created_at = datetime()`
  );

  // Link Source to Ibadi school (and remove Sunni link)
  await runWrite(`MATCH (s:Source) WHERE s.name CONTAINS 'Rabi' MATCH (sch:SchoolOfThought {name: 'Ibadi'}) MERGE (s)-[:CANON_OF]->(sch)`);
  await runWrite(`MATCH (s:Source)-[r:CANON_OF]->(sch:SchoolOfThought {name: 'Sunni'}) WHERE s.name CONTAINS 'Rabi' DELETE r`);

  // Link Ibadi hadiths to Ibadi school (and remove Sunni link)
  await runWrite(`MATCH (h:Hadith {tradition: 'Ibadi'}) MATCH (sch:SchoolOfThought {name: 'Ibadi'}) MERGE (h)-[:IN_SCHOOL]->(sch)`);
  await runWrite(`MATCH (h:Hadith {tradition: 'Ibadi'})-[r:IN_SCHOOL]->(sch:SchoolOfThought {name: 'Sunni'}) DELETE r`);

  const after = await runQuery<{ tradition: string; cnt: number }>(
    `MATCH (h:Hadith) RETURN h.tradition AS tradition, count(h) AS cnt ORDER BY cnt DESC`
  );
  console.log('\nFinal counts:');
  for (const r of after) console.log(`  ${r.tradition}: ${r.cnt}`);

  await closeDriver();
}

main().catch((err) => { console.error(err); process.exit(1); });
