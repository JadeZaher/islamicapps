// Round 5: write every curation table to JSON lines before a load (rollback evidence). Read-only.
// Usage: node --env-file=.env.local datasets/hadith-data/chain-audit/round5/dump_curation.cjs <out-dir>
const fs = require('fs');
const path = require('path');
const pg = require('postgres'); const postgres = pg.default || pg;
const sql = postgres(process.env.DATABASE_URL_PRODUCTION, { max: 1, connect_timeout: 30 });
const tables = fs.readdirSync(process.argv[3] || 'datasets/hadith-data/development/chain-structure-gate-2026-11-22/curation-dump-before')
  .filter((name) => name.endsWith('.jsonl')).map((name) => name.replace('.jsonl', ''));
(async () => {
  fs.mkdirSync(process.argv[2], { recursive: true });
  for (const table of tables) {
    const rows = await sql.unsafe(`select * from "${table}"`);
    fs.writeFileSync(path.join(process.argv[2], `${table}.jsonl`), rows.map((row) => JSON.stringify(row)).join('\n') + (rows.length ? '\n' : ''));
  }
  console.log('dumped', tables.length, 'tables');
  await sql.end();
})();
