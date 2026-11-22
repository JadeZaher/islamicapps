// Ad-hoc read-only query: node --env-file=.env.local q.cjs "<sql>" ; prints JSON rows.
const pg = require('postgres'); const postgres = pg.default || pg;
const sql = postgres(process.env.DATABASE_URL_PRODUCTION, { max: 1, connect_timeout: 30 });
(async () => {
  try { const rows = await sql.unsafe(process.argv[2]); console.log(JSON.stringify(rows, null, 0)); }
  catch (e) { console.error('ERR', e.message); process.exitCode = 1; }
  finally { await sql.end(); }
})();
