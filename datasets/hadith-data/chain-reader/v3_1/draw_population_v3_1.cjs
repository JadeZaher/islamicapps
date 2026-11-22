// The live population for the full run (copy of v3/draw_population.cjs): every report that currently has at least one chain with structure_status = 'uncertain' (read-only).
//   node --env-file=.env.local datasets/hadith-data/chain-reader/v3_1/draw_population_v3_1.cjs --out <population.jsonl>
// One JSON line per report: {hadith_id, work, uncertain_chains, reader_chars, opening} (opening: the v3.1 opening class at the start of the text (pronoun, isnad_phrase, bare_an,
// asker_pronoun, asker_named, implicit_speaker, first_person, collective), or null). Prints {reports, sha256, built_at_utc, dataset_version: {id, git_head, completed_at}}.
'use strict';
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const lib = require('./backref_lib_v3_1.cjs');

const REPO = path.resolve(__dirname, '..', '..', '..', '..');       // v3_1/ is one level below chain-reader/, as v3/ is
const LAYERED = new Set(['sunni:ahmad', 'sunni:darimi', 'sunni:muwatta']);

async function main() {
  if (process.argv.includes('--version-only')) { // the current dataset version alone (the tranche builder compares it before and after a build)
    const pgv = require(path.join(REPO, 'node_modules', 'postgres')); const connect = pgv.default || pgv;
    const sqlv = connect(process.env.DATABASE_URL_PRODUCTION, { max: 1, connection: { default_transaction_read_only: 'on' } });
    const rows = await sqlv`select id, git_head, completed_at from dataset_versions where is_current limit 1`;
    await sqlv.end();
    console.log(JSON.stringify({ dataset_version: rows[0] || null, at_utc: new Date().toISOString() }));
    return;
  }
  const out = process.argv.includes('--out') ? process.argv[process.argv.indexOf('--out') + 1] : null;
  if (!out) throw new Error('--out <population.jsonl> is required');
  const pg = require(path.join(REPO, 'node_modules', 'postgres')); const postgres = pg.default || pg;
  const sql = postgres(process.env.DATABASE_URL_PRODUCTION, { max: 1, connection: { default_transaction_read_only: 'on' } });
  const rows = await sql`select h.id as hadith_id, c.source_work_id as work, count(ch.id)::int as uncertain_chains, length(h.text_ar)::int as text_chars, length(coalesce(h.sanad, ''))::int as sanad_chars, left(h.text_ar, 600) as head, left(coalesce(h.sanad, ''), 200) as sanad_head
    from hadiths h join collections c on c.id = h.collection_id
    join chains ch on ch.hadith_id = h.id and ch.retired_at is null and ch.structure_status = 'uncertain'
    where h.retired_at is null group by h.id, c.source_work_id, h.text_ar, h.sanad order by h.id`;
  const dv = await sql`select id, git_head, completed_at from dataset_versions where is_current limit 1`;
  await sql.end();
  const lines = rows.map((r) => {
    const layered = LAYERED.has(r.work) && r.sanad_chars > 0;
    const head = layered ? `${r.sanad_head.trim()}\n\n${r.head}` : r.head;
    return JSON.stringify({ hadith_id: r.hadith_id, work: r.work, uncertain_chains: r.uncertain_chains, reader_chars: layered ? r.sanad_chars + 2 + r.text_chars : r.text_chars, opening: lib.openingClass(head) });
  });
  fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
  fs.writeFileSync(path.resolve(out), lines.join('\n') + '\n', 'utf8');
  const sha = crypto.createHash('sha256').update(fs.readFileSync(path.resolve(out))).digest('hex');
  console.log(JSON.stringify({ reports: rows.length, sha256: sha, built_at_utc: new Date().toISOString(), dataset_version: dv[0] || null }));
}
main().catch((e) => { console.error(e.message); process.exit(1); });
