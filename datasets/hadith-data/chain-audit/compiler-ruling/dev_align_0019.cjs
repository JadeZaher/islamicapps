// One-off: bring the development database's chain_fix_decisions to the final 0019 body (dev ran an earlier draft).
const pg = require('postgres'); const postgres = pg.default || pg;
const sql = postgres(process.env.DATABASE_URL, { max: 1, connect_timeout: 30 });
(async () => {
  await sql.unsafe(`alter table chain_fix_decisions add column if not exists hold_codes text[] default '{}'::text[] not null`);
  await sql.unsafe(`alter table chain_fix_decisions drop constraint if exists chain_fix_decisions_state_check`);
  await sql.unsafe(`alter table chain_fix_decisions add constraint chain_fix_decisions_state_check check (state in ('submitted', 'disputed', 'outvoted', 'held', 'accepted', 'confirmed', 'rejected', 'superseded', 'stale'))`);
  await sql.unsafe(`alter table chain_fix_decisions drop constraint if exists chain_fix_decisions_hold_codes_check`);
  await sql.unsafe(`alter table chain_fix_decisions add constraint chain_fix_decisions_hold_codes_check check ((state = 'held') = (cardinality(hold_codes) > 0) or state in ('confirmed', 'rejected', 'superseded'))`);
  console.log('aligned');
  await sql.end();
})().catch(async (e) => { console.error('ERR', e.message); process.exitCode = 1; await sql.end(); });
