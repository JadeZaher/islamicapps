// Corpus sizing for the chain reader: live reports, chains, reports with an `uncertain` chain, characters. Read-only SELECTs.
// usage: node --env-file=.env.local datasets/hadith-data/chain-reader/tools/sizing.cjs  -> writes ../sizing.json and prints a table
const fs = require('fs');
const path = require('path');
const pg = require('postgres'); const postgres = pg.default || pg;
const sql = postgres(process.env.DATABASE_URL_PRODUCTION, { max: 1, connect_timeout: 30 });
// text the reader would see: text_ar, plus the separate `sanad` field for the works whose text_ar is only the matn
const readerChars = sql`length(h.text_ar) + case when split_part(h.collection_id, ':', 3) in ('ahmad','darimi','muwatta') then coalesce(length(h.sanad), 0) + 2 else 0 end`;
(async () => {
  const work = sql`split_part(h.collection_id, ':', 2) tradition, split_part(h.collection_id, ':', 3) work`;
  const reports = await sql`select ${work}, count(*)::int reports, sum(${readerChars})::bigint chars from hadiths h where h.retired_at is null group by 1, 2`;
  const chains = await sql`select ${work}, count(*)::int chains, count(distinct c.hadith_id)::int reports_with_chain,
      count(distinct c.hadith_id) filter (where c.structure_status = 'uncertain')::int uncertain_reports,
      count(*) filter (where c.structure_status = 'uncertain')::int uncertain_chains
    from chains c join hadiths h on h.id = c.hadith_id where c.retired_at is null and h.retired_at is null group by 1, 2`;
  const uncertainChars = await sql`select ${work}, sum(${readerChars})::bigint chars, count(*)::int reports, max(${readerChars})::int longest
    from hadiths h where h.retired_at is null and exists (select 1 from chains c where c.hadith_id = h.id and c.retired_at is null and c.structure_status = 'uncertain') group by 1, 2`;
  const inherited = await sql`select ${work}, count(*)::int reports from hadiths h where h.retired_at is null and h.sanad_inherits_from is not null group by 1, 2`;
  const key = (r) => `${r.tradition}:${r.work}`;
  const rows = {};
  const slot = (r) => (rows[key(r)] ||= { tradition: r.tradition, work: r.work });
  reports.forEach((r) => Object.assign(slot(r), { reports: r.reports, chars: Number(r.chars) }));
  chains.forEach((r) => Object.assign(slot(r), { chains: r.chains, reports_with_chain: r.reports_with_chain, uncertain_reports: r.uncertain_reports, uncertain_chains: r.uncertain_chains }));
  uncertainChars.forEach((r) => Object.assign(slot(r), { uncertain_chars: Number(r.chars), uncertain_longest: r.longest }));
  inherited.forEach((r) => Object.assign(slot(r), { inherited_reports: r.reports }));
  const list = Object.values(rows).sort((a, b) => (a.tradition + a.work).localeCompare(b.tradition + b.work));
  const total = (rowsIn) => rowsIn.reduce((t, r) => { for (const k of ['reports', 'chars', 'chains', 'reports_with_chain', 'uncertain_reports', 'uncertain_chains', 'uncertain_chars', 'inherited_reports']) t[k] = (t[k] || 0) + (r[k] || 0); return t; }, {});
  const byTradition = {};
  for (const t of [...new Set(list.map((r) => r.tradition))]) byTradition[t] = total(list.filter((r) => r.tradition === t));
  const out = { measured_at: new Date().toISOString(), per_work: list, per_tradition: byTradition, all: total(list) };
  fs.writeFileSync(path.join(__dirname, '..', 'sizing.json'), JSON.stringify(out, null, 1) + '\n');
  console.log(JSON.stringify(out.per_tradition), JSON.stringify(out.all));
  await sql.end();
})();
