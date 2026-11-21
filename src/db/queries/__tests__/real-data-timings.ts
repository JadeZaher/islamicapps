/**
 * Read-only timings of the main page queries against the loaded development database (never production).
 * Run: npx tsx --conditions=react-server src/db/queries/__tests__/real-data-timings.ts
 */
import path from 'node:path';
import { config as loadEnvironment } from 'dotenv';

loadEnvironment({ path: path.resolve(__dirname, '../../../../.env.local'), quiet: true });
if (!process.env.DATABASE_URL || process.env.DATABASE_URL === process.env.DATABASE_URL_PRODUCTION) {
  throw new Error('Timings run only against the development DATABASE_URL.');
}

async function main() {
  const { searchPublicHadiths, getPublicHadith } = await import('../hadith');
  const { searchHadithsForReview, getHadithForReview } = await import('../hadith-review');
  const { getChainGraph } = await import('../isnad');
  const { listNarrators, getNarratorDetail, getNarratorNetwork } = await import('../narrator');
  const { listNarratorsForReview, getNarratorForReview } = await import('../narrator-review');
  const { listPublicParallels } = await import('../comparative');
  const { oneRow } = await import('../sql-helpers');
  const { sql } = await import('drizzle-orm');
  const { getDatabase } = await import('../../client');

  const sample = await oneRow<{ hadith_id: string; narrator_id: string }>(sql`
    select m.hadith_id, m.narrator_id from chain_mentions m where m.narrator_id is not null
    order by m.id limit 1`);
  const busiest = await oneRow<{ narrator_id: string }>(sql`
    select narrator_id from chain_mentions where narrator_id is not null group by narrator_id order by count(*) desc limit 1`);
  const facts = await oneRow<Record<string, unknown>>(sql`
    select (select count(*)::int from public_hadiths) as public_hadiths,
           (select count(*)::int from collection_rights where rights_status = 'cleared') as cleared_works,
           (select count(*)::int from narrator_transmissions) as transmissions,
           (select string_agg(load_status::text || ':' || release_class::text || ':' || is_current::text, ', ') from dataset_versions) as versions`);
  console.log('database facts', facts);

  const cases: Array<[string, () => Promise<unknown>]> = [
    ['public browse page 1', () => searchPublicHadiths('', {}, { page: 1 })],
    ['public search Arabic "الأعمال بالنيات"', () => searchPublicHadiths('الأعمال بالنيات', {}, { page: 1 })],
    ['public hadith detail', () => getPublicHadith(sample!.hadith_id)],
    ['chain graph', () => getChainGraph(sample!.hadith_id)],
    ['public narrator list page 1', () => listNarrators('', {}, { page: 1 })],
    ['public narrator search "Abu Hurayra"', () => listNarrators('Abu Hurayra', {}, { page: 1 })],
    ['public narrator detail (busiest)', () => getNarratorDetail(busiest!.narrator_id)],
    ['narrator network (busiest)', () => getNarratorNetwork(busiest!.narrator_id)],
    ['public parallels page', () => listPublicParallels({ pageSize: 50 })],
    ['review browse page 1', () => searchHadithsForReview('', {}, { page: 1 })],
    ['review browse Imami page 40', () => searchHadithsForReview('', { tradition: 'Imami' }, { page: 40 })],
    ['review search Arabic "الأعمال بالنيات"', () => searchHadithsForReview('الأعمال بالنيات', {}, { page: 1 })],
    ['review search Arabic "الله" (common)', () => searchHadithsForReview('الله', {}, { page: 1 })],
    ['review search English "prayer"', () => searchHadithsForReview('prayer', {}, { page: 1 })],
    ['review search title "fasting"', () => searchHadithsForReview('fasting', {}, { page: 1 })],
    ['review hadith detail', () => getHadithForReview(sample!.hadith_id)],
    ['review narrator list page 1', () => listNarratorsForReview('', {}, { page: 1 })],
    ['review narrator search Arabic "أبو هريرة"', () => listNarratorsForReview('أبو هريرة', {}, { page: 1 })],
    ['review narrator detail (busiest)', () => getNarratorForReview(busiest!.narrator_id)],
  ];
  for (const [label, run] of cases) {
    const cold = performance.now();
    const result = (await run()) as { total?: number; nodes?: unknown[]; teachers?: unknown[] } | null;
    const coldMs = performance.now() - cold;
    const warm = performance.now();
    await run();
    const size = result?.total ?? result?.nodes?.length ?? result?.teachers?.length ?? (result ? 1 : 0);
    console.log(`${label.padEnd(44)} cold ${Math.round(coldMs).toString().padStart(5)} ms  warm ${Math.round(performance.now() - warm).toString().padStart(5)} ms  size ${size}`);
  }
  await getDatabase().$client.end({ timeout: 5 });
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
