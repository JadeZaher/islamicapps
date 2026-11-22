// Read-only: a hash of every chains, chain_mentions and chain_mention_candidates row (live and retired), with the 0019
// columns removed, so the same hash before and after a step proves the step left those rows byte-identical.
// Usage: node --env-file=.env.local rows_hash.cjs <label> [--development]
const pg = require('postgres'); const postgres = pg.default || pg;
const url = process.argv.includes('--development') ? process.env.DATABASE_URL : process.env.DATABASE_URL_PRODUCTION;
const sql = postgres(url, { max: 1, connect_timeout: 30, idle_timeout: 0 });
const NEW = "- 'chain_fix_id' - 'compiler_narrator_id' - 'compiler_link'";
(async () => {
  const out = { label: process.argv[2], at: new Date().toISOString() };
  for (const [table, strip] of [['chains', NEW], ['chain_mentions', ''], ['chain_mention_candidates', '']]) {
    const [row] = await sql.unsafe(`select count(*)::int as rows, count(*) filter (where retired_at is null)::int as live,
      md5(string_agg(md5((to_jsonb(t) ${strip})::text), '' order by t.id)) as hash from ${table} t`);
    out[table] = row;
  }
  const [network] = await sql.unsafe(`select count(*)::int as rows, md5(string_agg(md5(to_jsonb(t)::text), '' order by student_id, teacher_id)) as hash from narrator_transmissions t`);
  out.narrator_transmissions = network;
  console.log(JSON.stringify(out));
  await sql.end();
})().catch(async (e) => { console.error('ERR', e.message); process.exitCode = 1; await sql.end(); });
