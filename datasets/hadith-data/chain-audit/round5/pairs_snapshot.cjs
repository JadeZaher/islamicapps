// Round 5: every narrator_transmissions pair with the traditions of the checked chains that support it. Read-only.
// Usage: node --env-file=.env.local datasets/hadith-data/chain-audit/round5/pairs_snapshot.cjs <out.json>
const fs = require('fs');
const pg = require('postgres'); const postgres = pg.default || pg;
const sql = postgres(process.env.DATABASE_URL_PRODUCTION, { max: 1, connect_timeout: 30 });
(async () => {
  const rows = await sql`
    select t.student_id, t.teacher_id, t.hadith_count,
           array_agg(distinct split_part(h.collection_id, ':', 2)) as traditions,
           array_agg(distinct split_part(h.collection_id, ':', 3)) as works
    from narrator_transmissions t
    join chain_mentions a on a.narrator_id = t.student_id and a.retired_at is null
    join chain_mentions b on b.chain_id = a.chain_id and b.position = a.position + 1 and b.narrator_id = t.teacher_id and b.retired_at is null
    join chains c on c.id = a.chain_id and c.retired_at is null and c.structure_status is distinct from 'uncertain'
    join hadiths h on h.id = c.hadith_id
    group by t.student_id, t.teacher_id, t.hadith_count`;
  const total = await sql`select count(*)::int as n from narrator_transmissions`;
  fs.writeFileSync(process.argv[2], JSON.stringify({ view_rows: total[0].n, pairs: rows }));
  console.log('view rows', total[0].n, 'attributed pairs', rows.length);
  await sql.end();
})();
