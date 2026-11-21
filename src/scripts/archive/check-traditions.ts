/**
 * Quick diagnostic: show all distinct h.tradition values in the DB.
 */
import { loadEnv } from './lib/env';
import { runQuery, closeDriver } from '../lib/db/neo4j';

loadEnv();

async function main() {
  console.log('--- Hadith tradition values ---');
  const result = await runQuery<{ tradition: string | null; cnt: number }>(
    'MATCH (h:Hadith) RETURN h.tradition AS tradition, count(h) AS cnt ORDER BY cnt DESC'
  );
  for (const r of result) {
    console.log(`  ${String(r.tradition ?? '(null)').padEnd(22)} ${Number(r.cnt)}`);
  }

  console.log('\n--- SchoolOfThought nodes ---');
  const schools = await runQuery<{ name: string; tradition: string | null }>(
    'MATCH (s:SchoolOfThought) RETURN s.name AS name, s.tradition AS tradition'
  );
  for (const s of schools) {
    console.log(`  ${s.name} | tradition=${s.tradition ?? '(null)'}`);
  }

  console.log('\n--- Shia source sample ---');
  const shia = await runQuery<{ tradition: string | null; cnt: number }>(
    `MATCH (h:Hadith) WHERE h.source = 'Al-Kafi' RETURN h.tradition AS tradition, count(h) AS cnt`
  );
  for (const r of shia) {
    console.log(`  Al-Kafi: tradition=${r.tradition ?? '(null)'} count=${Number(r.cnt)}`);
  }

  console.log('\n--- Zaydi source sample ---');
  const zaydi = await runQuery<{ tradition: string | null; source: string; cnt: number }>(
    `MATCH (h:Hadith) WHERE h.source CONTAINS 'Zayd' RETURN h.tradition AS tradition, h.source AS source, count(h) AS cnt`
  );
  if (zaydi.length === 0) {
    console.log('  No Zaydi hadiths found.');
  }
  for (const r of zaydi) {
    console.log(`  ${r.source}: tradition=${r.tradition ?? '(null)'} count=${Number(r.cnt)}`);
  }

  await closeDriver();
}

main().catch((err) => {
  console.error('Fatal:', err.message);
  process.exit(1);
});
