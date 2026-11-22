// Corpus coverage per tradition and work: second local copies of the text and populated metadata fields.
//   node --env-file=.env.local datasets/hadith-data/chain-reader/context/coverage.cjs > context/coverage.json
// Read-only. Independent copy = hadith-kg or Riwayat unique match (reconciled crosswalk); source-file copy = the provider's own file we loaded from.
'use strict';
const path = require('path'); const fs = require('fs'); const zlib = require('zlib'); const readline = require('readline');
const REPO = path.resolve(__dirname, '..', '..', '..', '..');
const pg = require(path.join(REPO, 'node_modules', 'postgres')); const postgres = pg.default || pg;
(async () => {
  const sql = postgres(process.env.DATABASE_URL_PRODUCTION, { max: 1, connection: { default_transaction_read_only: 'on' } });
  const rows = await sql`select c.source_work_id as work, c.tradition_id as tradition, count(*)::int as reports,
      count(h.book_id)::int as book, count(h.chapter_title)::int as chapter, count(h.hadith_no)::int as report_number, count(h.volume)::int as volume,
      count(h.page_ref)::int as page, count(h.url)::int as url,
      count(*) filter (where h.source_record_id like 'provider-file:%')::int as thaqalayn_raw,
      count(*) filter (where exists (select 1 from hadith_assessments a where a.hadith_id = h.id and a.retired_at is null))::int as grading
    from hadiths h join collections c on c.id = h.collection_id where h.retired_at is null group by 1, 2 order by 2, 1`;
  const copies = {}; // work -> {kg:Set, rwy:Set}
  const lines = readline.createInterface({ input: fs.createReadStream(path.join(REPO, 'datasets', 'hadith-data', 'reconciled', 'external_report_crosswalk.jsonl.gz')).pipe(zlib.createGunzip()) });
  for await (const line of lines) { if (!line) continue; const d = JSON.parse(line); if (!d.used) continue; const w = (copies[d.source_work_id] ||= { hadith_kg: new Set(), riwayat: new Set(), either: new Set() }); w[d.dataset].add(d.record_id); w.either.add(d.record_id); }
  const out = rows.map((r) => {
    const c = copies[r.work] || { hadith_kg: new Set(), riwayat: new Set(), either: new Set() };
    const fileCopy = r.thaqalayn_raw || (['ibadi:musnad-rabi', 'zaydi:musnad-zayd'].includes(r.work) ? r.reports : 0);
    return { ...r, tradition: r.tradition.replace('tradition:', ''), independent_copy_hadith_kg: c.hadith_kg.size, independent_copy_riwayat: c.riwayat.size, independent_copy_any: c.either.size, source_file_copy: fileCopy };
  });
  console.log(JSON.stringify(out, null, 1));
  await sql.end();
})().catch((e) => { console.error(e.message); process.exit(1); });
