// Corpus census of back-reference openings and of how many get a usable previous report, per work: v2's lookup (chapter pool, printed number, 3 reports) beside v3's (book order, walk back).
//   node --env-file=.env.local datasets/hadith-data/chain-reader/v3/census_backref.cjs [--out v3/census_backref.json]
// Read-only on production; prints nothing secret. See v3/AGENTS.md §previous reports.
'use strict';
const fs = require('fs');
const path = require('path');
const lib = require('./backref_lib.cjs');

const HERE = __dirname;
const REPO = path.resolve(HERE, '..', '..', '..', '..');
const LAYERED = new Set(['sunni:ahmad', 'sunni:darimi', 'sunni:muwatta']);

// ---- v2's detector and lookup, reproduced from context/build_context.cjs (read-only original) ----
const MARKS = /[ً-ٰٟۖ-ۭـ​-‏‪-‮﻿]/g;
const PUNCT = /[\s،,.:;()\[\]«»"'*\-–—\/‘’“”…!?؟]+/g;
const foldV2 = (s) => (s || '').replace(MARKS, '').replace(PUNCT, ' ').replace(/[أإآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه').trim();
const OPENING_V2 = /^(?:\d+ )?(?:و ?)?(?:عنه|عنها|عنهم|بهذا الاسناد|باسناده|باسنادهم|بالاسناد|عن )/;
const opensV2 = (text) => { const f = foldV2(text); return OPENING_V2.test(f) || f.slice(0, 160).includes('بهذا الاسناد'); };
const leading = (t) => { const m = /^\s*(\d+)\s*[-–.]/.exec(t || ''); return m ? +m[1] : null; };

function v2Previous(row, readerTextOf, byChapter, byCollectionNumber) {
  const mine = leading(readerTextOf(row));
  const myKey = mine != null ? mine : row.hadith_no_int;
  let pool;
  if (row.chapter_id) pool = byChapter.get(row.collection + '|' + row.chapter_id) || [];
  else if (row.hadith_no_int == null) pool = [];
  else pool = (byCollectionNumber.get(row.collection) || []).filter((p) => p.hadith_no_int < row.hadith_no_int && p.hadith_no_int >= row.hadith_no_int - 4);
  const key = (p) => (mine != null && leading(p.text_ar) != null ? leading(p.text_ar) : p.hadith_no_int);
  const found = pool.filter((p) => p.id !== row.id && key(p) != null && key(p) < myKey).sort((x, y) => key(y) - key(x)).slice(0, 3);
  const supplied = [];
  for (const p of found) { supplied.push(p); if (!opensV2(p.text_ar)) break; }
  return supplied;
}

async function main() {
  const out = process.argv.includes('--out') ? process.argv[process.argv.indexOf('--out') + 1] : path.join(HERE, 'census_backref.json');
  const pg = require(path.join(REPO, 'node_modules', 'postgres')); const postgres = pg.default || pg;
  const sql = postgres(process.env.DATABASE_URL_PRODUCTION, { max: 1, connection: { default_transaction_read_only: 'on' } });
  const rows = (await sql`select h.id, c.source_work_id as collection, h.chapter_id, h.hadith_no_int, h.source_record_id, h.provider_hadith_id, h.collection_id,
      left(h.text_ar, 1400) as text_ar, left(coalesce(h.sanad, ''), 500) as sanad
    from hadiths h join collections c on c.id = h.collection_id where h.retired_at is null`);
  await sql.end();
  const readerTextOf = (r) => (LAYERED.has(r.collection) && (r.sanad || '').trim() ? `${r.sanad.trim()}\n\n${r.text_ar}` : r.text_ar);
  const byChapter = new Map(), byCollectionNumber = new Map();
  for (const r of rows) {
    if (r.chapter_id) { const k = r.collection + '|' + r.chapter_id; (byChapter.get(k) || byChapter.set(k, []).get(k)).push(r); }
    else (byCollectionNumber.get(r.collection) || byCollectionNumber.set(r.collection, []).get(r.collection)).push(r);
  }
  const books = lib.orderedBooks(rows);
  const positionIn = new Map();
  for (const list of books.values()) list.forEach((r, i) => positionIn.set(r.id, { list, i }));

  const perWork = {};
  const bump = (w) => (perWork[w] ||= { reports: 0, opens_v2_detector: 0, opens_v3: 0, forms: { pronoun: 0, isnad_phrase: 0, bare_an: 0 }, in_first_160_only: 0,
    v2_prev_supplied: 0, v2_chain_found: 0, v3_prev_supplied: 0, v3_chain_found: 0, v3_not_found_no_order: 0, v3_not_found_limit: 0 });
  for (const r of rows) {
    const w = bump(r.collection); w.reports++;
    const text = readerTextOf(r);
    const v2opens = opensV2(text); if (v2opens) w.opens_v2_detector++;
    const form = lib.openingForm(text);
    if (form === 'in_first_160') w.in_first_160_only++;
    if (!form || form === 'in_first_160') continue;
    w.opens_v3++; w.forms[form]++;
    // v2: what its builder supplied (it only looked when its own detector fired)
    if (v2opens) {
      const supplied = v2Previous(r, readerTextOf, byChapter, byCollectionNumber);
      if (supplied.length) w.v2_prev_supplied++;
      if (supplied.some((p) => lib.hasWrittenChain(p.text_ar))) w.v2_chain_found++;
    }
    // v3: book order, walk back to a report that writes its own chain
    const at = positionIn.get(r.id);
    if (!at) { w.v3_not_found_no_order++; continue; }
    const { previous, chainFound } = lib.walkBack(at.list, at.i, (p) => (LAYERED.has(p.collection) && (p.sanad || '').trim() ? `${p.sanad.trim()}\n\n${p.text_ar}` : p.text_ar));
    if (previous.length) w.v3_prev_supplied++;
    if (chainFound) w.v3_chain_found++; else w.v3_not_found_limit++;
  }
  const total = Object.values(perWork).reduce((a, w) => { for (const k of Object.keys(w)) if (typeof w[k] === 'number') a[k] = (a[k] || 0) + w[k]; for (const f of Object.keys(w.forms)) (a.forms ||= {})[f] = ((a.forms || {})[f] || 0) + w.forms[f]; return a; }, {});
  fs.writeFileSync(out, JSON.stringify({ built_at_utc: new Date().toISOString(), reports: rows.length, per_work: perWork, total }, null, 1) + '\n', 'utf8');
  console.table(Object.fromEntries(Object.entries(perWork).map(([k, w]) => [k, { reports: w.reports, opens_v2: w.opens_v2_detector, opens_v3: w.opens_v3, v2_prev: w.v2_prev_supplied, v2_chain: w.v2_chain_found, v3_chain: w.v3_chain_found, v3_none: w.v3_not_found_limit + w.v3_not_found_no_order }])));
  console.log(JSON.stringify(total));
}
main().catch((e) => { console.error(e.message); process.exit(1); });
