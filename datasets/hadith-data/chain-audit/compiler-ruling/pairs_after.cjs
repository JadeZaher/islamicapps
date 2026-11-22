// Read-only: every narrator_transmissions pair with its traditions, from adjacent mentions or a compiler head (0019).
// Usage: node --env-file=.env.local pairs_after.cjs <out.json>
const fs = require('fs');
const pg = require('postgres'); const postgres = pg.default || pg;
const sql = postgres(process.env.DATABASE_URL_PRODUCTION, { max: 1, connect_timeout: 30 });
(async () => {
  const rows = await sql`
    with links as (
      select a.narrator_id s, b.narrator_id t, h.collection_id c from chain_mentions a
      join chain_mentions b on b.chain_id = a.chain_id and b.position = a.position + 1 and b.retired_at is null
      join chains ch on ch.id = a.chain_id and ch.retired_at is null and ch.structure_status = 'checked_by_rule'
      join hadiths h on h.id = ch.hadith_id where a.retired_at is null and a.narrator_id is not null and b.narrator_id is not null
      union all
      select ch.compiler_narrator_id, b.narrator_id, h.collection_id from chains ch
      join chain_mentions b on b.chain_id = ch.id and b.position = 0 and b.retired_at is null
      join hadiths h on h.id = ch.hadith_id
      where ch.retired_at is null and ch.compiler_link = 'direct' and ch.suspension is null and ch.structure_status = 'checked_by_rule')
    select t.student_id, t.teacher_id, t.hadith_count, t.extraction_methods,
           array_agg(distinct split_part(l.c, ':', 2)) as traditions
    from narrator_transmissions t join links l on l.s = t.student_id and l.t = t.teacher_id
    group by 1, 2, 3, 4`;
  const total = await sql`select count(*)::int as n from narrator_transmissions`;
  fs.writeFileSync(process.argv[2], JSON.stringify({ view_rows: total[0].n, pairs: rows }));
  console.log('view rows', total[0].n, 'attributed pairs', rows.length);
  await sql.end();
})();
