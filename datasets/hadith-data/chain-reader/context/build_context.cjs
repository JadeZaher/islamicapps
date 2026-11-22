// Builds context-carrying packets {id, text, context} for the chain reader and the text/metadata checker (see context/AGENTS.md).
//   node --env-file=.env.local datasets/hadith-data/chain-reader/context/build_context.cjs --kind chain|text|both [--out-dir D] [--hadith-ids file] [--limit N]
//        [--stored-chain] [--readings-a DIR --readings-b DIR] [--no-archive-flags] [--coverage]
// Read-only on production (DATABASE_URL_PRODUCTION is never printed). Deterministic: no timestamps inside packets (the manifest has them).
'use strict';
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const crypto = require('crypto');
const readline = require('readline');

const HERE = __dirname;
const ROOT = path.resolve(HERE, '..');
const REPO = path.resolve(ROOT, '..', '..', '..');
const SIDECARS = path.join(REPO, 'datasets', 'hadith-data', 'reconciled');
const EXTERNAL = path.join(REPO, 'datasets', 'sources', 'external');
const BUDGET = { chain: 3000, text: 3600 };            // characters of JSON per report's context (see README §Size)
const PROFILES = JSON.parse(fs.readFileSync(path.join(HERE, 'work_profiles.json'), 'utf8'));

// ---------- Arabic helpers ----------
const MARKS = /[ً-ٰٟۖ-ۭـ​-‏‪-‮﻿]/g;
const HONORIFIC = /\s*[(]?\s*(?:رضي الله عنه[ما]?|رضي الله عنها|رحمه الله|صلى الله عليه وسلم|عليه السلام|\(ع\))\s*[)]?\s*$/;
const stripMarks = (s) => (s || '').replace(MARKS, '');
const PUNCT = /[\s،,.:;()\[\]«»"'*\-–—\/‘’“”…!?؟]+/g;
function fold(s) { // letters-only comparison form: no marks, one space between words, alef/ya/ta-marbuta folded
  return stripMarks(s).replace(PUNCT, ' ').replace(/[أإآٱ]/g, 'ا').replace(/ى/g, 'ي').replace(/ة/g, 'ه').trim();
}
const clip = (s, n) => (s.length <= n ? s : s.slice(0, n).replace(/\s+\S*$/, '') + '…');
function stripWithMap(text) { // text without marks and a map from stripped index to original index
  let out = ''; const map = [];
  for (let i = 0; i < text.length; i++) { if (!MARKS.test(text[i])) { out += text[i]; map.push(i); } MARKS.lastIndex = 0; }
  return { out, map };
}

// ---------- IO helpers ----------
function arg(name, fallback = null) { const i = process.argv.indexOf('--' + name); return i < 0 ? fallback : (process.argv[i + 1] && !process.argv[i + 1].startsWith('--') ? process.argv[i + 1] : true); }
async function gzLines(file, onRow) {
  const lines = readline.createInterface({ input: fs.createReadStream(file).pipe(zlib.createGunzip()), crlfDelay: Infinity });
  for await (const line of lines) if (line) onRow(JSON.parse(line));
}
function sha256File(file) { return crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'); }
function median(a) { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : 0; }
function pct(a, p) { const s = [...a].sort((x, y) => x - y); return s.length ? s[Math.min(s.length - 1, Math.floor(p * s.length))] : 0; }

// ---------- text comparison (computed by the builder, never by the reader) ----------
const LEADING_NUMBER = /^\s*\d+\s*[-ـ.]\s*/;
function diffTexts(ours, theirs) {
  const prep = (t) => fold(t.replace(LEADING_NUMBER, '').replace(/ﷺ/g, 'صلى الله عليه وسلم')); // a printed number and the ﷺ ligature are not wording
  const a = prep(ours), b = prep(theirs); // a printed report number is not part of the wording
  const wordsOurs = a ? a.split(' ').length : 0, wordsTheirs = b ? b.split(' ').length : 0;
  const base = { words_ours: wordsOurs, words_theirs: wordsTheirs, length_ratio: a.length ? +(b.length / a.length).toFixed(2) : null };
  if (!b) return { relation: 'other_copy_empty', ...base };
  if (a === b) return { relation: 'identical_after_normalisation', ...base };
  if (a.replace(/ /g, '') === b.replace(/ /g, '')) return { relation: 'identical_except_word_spacing', ...base }; // words glued or split: often the other copy's defect
  if (b.includes(a)) {
    const at = b.indexOf(a);
    return { relation: 'ours_inside_theirs', ...base, theirs_extra_before: clip(b.slice(0, at).trim().split(' ').slice(-14).join(' '), 90), theirs_extra_after: clip(b.slice(at + a.length).trim(), 90) };
  }
  if (a.includes(b)) {
    const at = a.indexOf(b);
    return { relation: 'theirs_inside_ours', ...base, ours_extra_before: clip(a.slice(0, at).trim().split(' ').slice(-14).join(' '), 90), ours_extra_after: clip(a.slice(at + b.length).trim(), 90) };
  }
  const aw = a.split(' '), bw = b.split(' ');
  let p = 0; while (p < aw.length && p < bw.length && aw[p] === bw[p]) p++;
  let s = 0; while (s < aw.length - p && s < bw.length - p && aw[aw.length - 1 - s] === bw[bw.length - 1 - s]) s++;
  const mid = (w) => clip(w.slice(Math.max(0, p - 2), w.length - s).join(' '), 110);
  return { relation: 'differs', ...base, shared_opening_words: p, shared_closing_words: s, ours_span: mid(aw), theirs_span: mid(bw) };
}

// ---------- name and chain helpers ----------
function chainSpan(text, surfaces) { // end of the chain in `text`: the last stored surface located in order; null when none found
  const { out, map } = stripWithMap(text); let cursor = 0, end = -1;
  for (const surface of surfaces) {
    const needle = stripMarks(surface).trim(); if (!needle) continue;
    let at = out.indexOf(needle, cursor); if (at < 0) at = out.indexOf(needle); if (at < 0) continue;
    cursor = at + needle.length; end = Math.max(end, cursor);
  }
  if (end < 0) return null;
  const original = map[Math.min(end, map.length) - 1] + 1;
  const tail = text.slice(original).match(/^[^\s]*/)[0];
  return text.slice(0, original + tail.length);
}
function trimSpan(span, cap) { return span.length <= cap ? span : span.slice(0, Math.floor(cap * 0.4)).replace(/\s+\S*$/, '') + ' … ' + span.slice(span.length - Math.floor(cap * 0.55)).replace(/^\S*\s+/, ''); }
const OPENING = /^(?:\d+ )?(?:و ?)?(?:عنه|عنها|عنهم|بهذا الاسناد|باسناده|باسنادهم|بالاسناد|عن )/; // on the folded text: marks, hamza and punctuation are already gone
function opensWithBackReference(text) { const f = fold(text); return OPENING.test(f) || f.slice(0, 160).includes('بهذا الاسناد'); }
const STRUCTURE_WORDS = {
  duplicated_link: 'one person seems to be stored as two neighbouring names', joined_names: 'one position holds two names joined by «و»',
  ghayr_wahid_half: 'half of «غير واحد» is stored as a name', short_beside_long: 'this route is much shorter than another route of the report',
  repeated_name: 'the same name stands twice in the chain', text_between_links: 'the text names more between two stored names than the chain holds',
  text_names_more_after: 'the text names a further transmitter after the last stored name', not_a_name: 'a stored name contains words that are not a name',
  unaccounted_route_marker: 'the text marks more routes («ح», «جميعا», «كلهم») than were stored', crossed_routes: "two of al-Kulayni's routes appear joined in one chain",
  many_routes: 'the report has three or more routes, which the rules read wrong too often', sibling_skips_link: 'two routes of this report differ by one name in the middle',
  work_not_checked: 'chains in this work were read wrong too often to rely on',
};
const SUSPENSION_WORDS = { back_reference: 'the report relies on the previous report\'s chain', mid_chain_start: 'the report starts in the middle of a usual chain', route_given_elsewhere: 'the report says its route is given elsewhere' };

// ---------- context assembly ----------
const OMIT_ORDER = ['source_notes', 'name_facts', 'correspondences', 'archive_flags', 'source_claims', 'previous_reports', 'parent_report']; // dropped first -> last when over budget
function fitBudget(context, budget, omitted) {
  const size = () => JSON.stringify(context).length;
  const trims = [
    () => { if (context.name_facts) context.name_facts.forEach((f) => { delete f.same_name_in_lexicon; }); },
    () => { if (context.correspondences) context.correspondences = context.correspondences.slice(0, 2); },
    () => { if (context.correspondences) context.correspondences.forEach((c) => { c.chain_text = clip(c.chain_text || '', 160); }); },
    () => { if (context.name_facts) context.name_facts = context.name_facts.slice(0, 6); },
    () => { if (context.source_claims) context.source_claims.forEach((c) => { if (c.english_sanad) c.english_sanad = clip(c.english_sanad, 240); }); },
    () => { if (context.previous_reports) context.previous_reports.forEach((p) => { p.chain_text = trimSpan(p.chain_text, 300); if (p.text_head) p.text_head = clip(p.text_head, 160); }); },
    () => { if (context.previous_reports) { context.previous_reports = context.previous_reports.slice(0, 2); context.previous_reports.forEach((p) => { p.chain_text = trimSpan(p.chain_text, 220); delete p.text_head; }); } },
  ];
  for (const t of trims) { if (size() <= budget) return; t(); }
  for (const key of OMIT_ORDER) { if (size() <= budget) return; if (context[key] !== undefined) { delete context[key]; omitted.push(key); } }
}

async function main() {
  const kind = arg('kind', 'both');
  const outDir = path.resolve(arg('out-dir', path.join(HERE, 'pilot-v2')));
  const wantStored = !!arg('stored-chain'); const noFlags = !!arg('no-archive-flags');
  const pg = require(path.join(REPO, 'node_modules', 'postgres')); const postgres = pg.default || pg;
  if (!process.env.DATABASE_URL_PRODUCTION) throw new Error('DATABASE_URL_PRODUCTION is not set (use --env-file=.env.local)');
  const sql = postgres(process.env.DATABASE_URL_PRODUCTION, { max: 2, connect_timeout: 30, connection: { default_transaction_read_only: 'on' } });
  const { DatabaseSync } = require('node:sqlite');

  // 1. the reports to build
  let reports;
  const idsFile = arg('hadith-ids');
  if (idsFile) {
    const ids = JSON.parse(fs.readFileSync(idsFile, 'utf8'));
    const rows = await sql`select id, collection_id, text_ar, sanad from hadiths where id in ${sql(ids)}`;
    const byId = Object.fromEntries(rows.map((r) => [r.id, r]));
    reports = ids.filter((i) => byId[i]).map((hid, n) => {
      const r = byId[hid]; const work = r.collection_id.split(':').slice(1).join(':');
      const layered = ['sunni:ahmad', 'sunni:darimi', 'sunni:muwatta'].includes(work) && (r.sanad || '').trim();
      return { id: 'cx-' + String(n + 1).padStart(4, '0'), hadith_id: hid, text: layered ? `${r.sanad.trim()}\n\n${r.text_ar}` : r.text_ar, work };
    });
  } else {
    reports = fs.readFileSync(path.join(ROOT, 'pilot', 'reports.jsonl'), 'utf8').split('\n').filter(Boolean).map((l) => JSON.parse(l)).map((r) => ({ id: r.id, hadith_id: r.hadith_id, text: r.text, work: r.work }));
  }
  const limit = arg('limit'); if (limit) reports = reports.slice(0, +limit);
  const hadithIds = reports.map((r) => r.hadith_id); const recordIds = new Set(hadithIds.map((h) => h.replace(/^hadith:/, '')));

  // 2. database rows
  const hadiths = await sql`select h.id, h.record_id, h.source_record_id, h.collection_id, h.chapter_id, h.chapter_no, h.chapter_title, h.hadith_no, h.hadith_no_int, h.volume, h.page_ref, h.url,
      h.source_display_label, h.tradition_id, h.text_ar, h.arabic_sha256, h.sanad, h.matn_ar, h.sanad_inherits_from, h.sanad_ar, h.source_notes, h.provider_hadith_id,
      b.name as book_name, b.volume as book_volume, c.name as collection_name, c.source_work_id
    from hadiths h left join books b on b.id = h.book_id join collections c on c.id = h.collection_id where h.id in ${sql(hadithIds)}`;
  const H = Object.fromEntries(hadiths.map((h) => [h.id, h]));
  const chainRows = await sql`select id, hadith_id, branch, structure_status, structure_reasons, suspension, missing_link_after from chains where hadith_id in ${sql(hadithIds)} and retired_at is null order by hadith_id, branch`;
  const mentionRows = await sql`select chain_id, hadith_id, position, surface_ar, identity_withheld_reason from chain_mentions where hadith_id in ${sql(hadithIds)} and retired_at is null order by chain_id, position`;
  const assessments = await sql`select hadith_id, ordinal, kind, grader, grade_raw, grade_canonical, cited_work, cited_volume, cited_page, source_field from hadith_assessments where hadith_id in ${sql(hadithIds)} and retired_at is null order by hadith_id, ordinal`;
  const corrRows = await sql`select hadith_id, corresponding_hadith_id, relation_class, jaccard, containment, confirmed from public_report_correspondences where hadith_id in ${sql(hadithIds)}`;

  // previous reports (the same chapter, nearest earlier numbers; a few when each opens with a back-reference)
  const previous = {};
  if (kind !== 'text') for (const r of reports) {
    const h = H[r.hadith_id]; if (!h) continue;
    const text0 = r.text; if (!(opensWithBackReference(text0) || chainRows.some((c) => c.hadith_id === r.hadith_id && c.suspension))) continue;
    const leading = (t) => { const m = /^\s*(\d+)\s*[-–.]/.exec(t || ''); return m ? +m[1] : null; }; // the number printed before the text orders reports where hadith_no repeats
    const pool = h.chapter_id
      ? await sql`select id, hadith_no, hadith_no_int, text_ar, sanad, collection_id, chapter_id from hadiths where collection_id = ${h.collection_id} and chapter_id = ${h.chapter_id} and retired_at is null`
      : h.hadith_no_int == null ? [] : await sql`select id, hadith_no, hadith_no_int, text_ar, sanad, collection_id, chapter_id from hadiths where collection_id = ${h.collection_id} and retired_at is null and hadith_no_int < ${h.hadith_no_int} and hadith_no_int >= ${h.hadith_no_int - 4}`;
    const mine = leading(r.text);
    const key = (p) => (mine != null && leading(p.text_ar) != null ? leading(p.text_ar) : p.hadith_no_int);
    const myKey = mine != null ? mine : h.hadith_no_int;
    const found = pool.filter((p) => p.id !== h.id && key(p) != null && key(p) < myKey).sort((x, y) => key(y) - key(x)).slice(0, 3);
    previous[r.hadith_id] = found;
  }
  const extraIds = new Set(); // previous, parent and corresponding reports whose mentions we need to find their chain spans
  Object.values(previous).flat().forEach((p) => extraIds.add(p.id));
  corrRows.forEach((c) => extraIds.add(c.corresponding_hadith_id));
  hadiths.forEach((h) => h.sanad_inherits_from && extraIds.add(h.sanad_inherits_from));
  const extraList = [...extraIds];
  const extraHadiths = extraList.length ? await sql`select h.id, h.hadith_no, h.text_ar, h.sanad, h.sanad_ar, h.collection_id, c.name as collection_name, c.source_work_id, c.tradition_id from hadiths h join collections c on c.id = h.collection_id where h.id in ${sql(extraList)}` : [];
  const X = Object.fromEntries(extraHadiths.map((h) => [h.id, h]));
  const extraMentions = extraList.length ? await sql`select hadith_id, chain_id, position, surface_ar from chain_mentions where hadith_id in ${sql(extraList)} and retired_at is null order by chain_id, position` : [];
  const surfacesOf = {}; for (const m of extraMentions) (surfacesOf[m.hadith_id] ||= []).push(m.surface_ar);

  // 3. sidecars (only the rows of our reports)
  const k6 = {}, pure = {}, noChain = {}, openiti = {}, cross = { hadith_kg: {}, riwayat: {} };
  const sidecarFiles = ['k6_source_index', 'pure_canon_chain', 'no_chain_in_source', 'openiti_extraction', 'external_report_crosswalk'].map((n) => path.join(SIDECARS, n + '.jsonl.gz'));
  await gzLines(sidecarFiles[0], (d) => { if (recordIds.has(d.record_id)) k6[d.record_id] = d; });
  await gzLines(sidecarFiles[1], (d) => { if (recordIds.has(d.record_id)) pure[d.record_id] = d; });
  await gzLines(sidecarFiles[2], (d) => { if (recordIds.has(d.record_id)) noChain[d.record_id] = d; });
  await gzLines(sidecarFiles[3], (d) => { if (recordIds.has(d.record_id)) openiti[d.record_id] = d; });
  await gzLines(sidecarFiles[4], (d) => { if (d.used && recordIds.has(d.record_id) && cross[d.dataset]) cross[d.dataset][d.record_id] = d; });

  // 4. lexicon rows for K6 ids, and the lexicon name index for same-name notes (Sunni lexicon only)
  const k6Ids = new Set(); Object.values(k6).forEach((d) => (d.source_ids || []).forEach((i) => k6Ids.add('narrator:rawi:' + i)));
  const lexRows = k6Ids.size ? await sql`select n.id, n.name_ar, p.death_year_hijri, p.tabaqah_raw, p.death_place from narrators n left join narrator_lexicon_profiles p on p.narrator_id = n.id where n.id in ${sql([...k6Ids])}` : [];
  const lexById = Object.fromEntries(lexRows.map((r) => [r.id, r]));
  const lexAll = kind === 'text' ? [] : await sql`select n.id, n.name_ar, p.death_year_hijri, p.death_place from narrators n left join narrator_lexicon_profiles p on p.narrator_id = n.id where n.authority = 'rawi' and n.retired_at is null`;
  const lexKey = new Map();
  const nameKey3 = (name) => { const t = fold(name).split(' '); return t.length >= 3 && t[1] === 'بن' ? t.slice(0, 3).join(' ') : null; };
  for (const r of lexAll) { const k = nameKey3(r.name_ar || ''); if (k) (lexKey.get(k) || lexKey.set(k, []).get(k)).push(r); }

  // 5. external sqlite databases (read-only, immutable)
  const open = (p) => new DatabaseSync('file:' + p.replace(/\\/g, '/') + '?mode=ro&immutable=1', { readOnly: true });
  const kg = open(path.join(EXTERNAL, 'hadith-kg', 'hadith-kg.db')), rw = open(path.join(EXTERNAL, 'riwayat-corpus', 'hadith_master.db'));
  const kgSanads = kg.prepare('select s.id from sanads s where s.hadith_id = ? order by s.id');
  const kgRawis = kg.prepare('select r.id, r.name, r.death_year_raw, r.tabaka, r.iqama, r.death_place from sanad_rawis sr join rawis r on r.id = sr.rawi_id where sr.sanad_id = ? and sr.pos > 0 order by sr.pos');
  const kgHadith = kg.prepare('select h.nass, h.no_inbook, h.page_no, b.name as book_name from hadiths h join books b on b.id = h.book_id where h.id = ?');
  const rwMentions = rw.prepare('select m.chain_no, m.pos, m.surface, m.narrator_id, m.id_method, n.std_name, n.death_year, n.tabaqa, n.city from chain_mention m left join narrator n on n.id = m.narrator_id where m.hadith_id = ? and m.surface is not null order by m.chain_no, m.pos');
  const rwHadith = rw.prepare('select text, book, number from hadith where id = ?');

  // 6. local raw copies: Thaqalayn v2_books JSON and the OpenITI raw files
  const thqCache = {};
  function thaqalaynRaw(h) {
    const m = /^provider-file:(\d+)\|hadith:(\S+)$/.exec(h.source_record_id || ''); if (!m) return null;
    const file = path.join(REPO, 'datasets', 'hadith-data', 'shia-hadith', 'v2_books', m[1] + '.json');
    if (!fs.existsSync(file)) return null;
    thqCache[m[1]] ||= JSON.parse(fs.readFileSync(file, 'utf8'));
    return thqCache[m[1]].find((x) => String(x.id) === m[2]) || null;
  }
  const openitiRaw = {};
  function openitiRawFolded(work) {
    const dir = path.join(REPO, 'datasets', 'hadith-data', 'openiti-sources');
    const f = work === 'ibadi:musnad-rabi' ? path.join(dir, 'rabi', 'jamic_sahih_ibadiyya.txt') : work === 'zaydi:musnad-zayd' ? path.join(dir, 'zayd', 'musnad_zaydiyya_052.mARkdown') : null;
    if (!f || !fs.existsSync(f)) return null;
    return (openitiRaw[f] ||= fold(fs.readFileSync(f, 'utf8').replace(/ms\d+|PageV\d+P\d+|^#+[^\n]*|~~|\$|@\w+/gm, ' ')));
  }

  // 7. build per report
  const stats = { reports: reports.length, kinds: {}, omitted: {} };
  const bump = (k) => { stats.kinds[k] = (stats.kinds[k] || 0) + 1; };
  const built = [];
  for (const r of reports) {
    const h = H[r.hadith_id]; if (!h) { built.push({ id: r.id, text: r.text, context: { error: 'report not found' } }); continue; }
    const record = r.hadith_id.replace(/^hadith:/, ''); const work = h.source_work_id; const profile = PROFILES[work] || {}; const tradition = h.tradition_id.replace('tradition:', '');
    const chains = chainRows.filter((c) => c.hadith_id === r.hadith_id);
    const common = {
      work: {
        name: h.collection_name, tradition, source: profile.source || null,
        compiler: profile.compiler_head ? { ar: profile.compiler_ar, en: profile.compiler_en, head_of_every_chain: true, added_by_tool: true } : { head_of_every_chain: false, note: profile.compiler_note || 'no compiler head for this work' },
        book: h.book_name || null, chapter: h.chapter_title || null, report_number: h.hadith_no, convention: profile.convention || null,
        ...(profile.compiler_note && profile.compiler_head ? { compiler_note: profile.compiler_note } : {}),
      },
    };
    const context = { ...common }; const omitted = [];
    // ---- chain context ----
    const chainContext = {};
    const hasChainField = ['sunni:ahmad', 'sunni:darimi', 'sunni:muwatta'].includes(work);
    const prevList = previous[r.hadith_id] || [];
    const prevOut = [];
    for (const [i, p] of prevList.entries()) {
      const span = hasChainField ? (p.sanad || '').trim() : (chainSpan(p.text_ar, surfacesOf[p.id] || []) || clip(p.text_ar, 350));
      const item = { ref: 'prev' + (i + 1), number: p.hadith_no, source: profile.source || null, chain_text: trimSpan(span, 480) };
      if (!hasChainField && span.length < p.text_ar.length - 20) item.text_head = clip(p.text_ar, 300); // the report itself, so the reader sees what follows the chain
      prevOut.push(item);
      if (!opensWithBackReference(p.text_ar)) break;
    }
    if (kind !== 'text') {
      if (prevOut.length) chainContext.previous_reports = prevOut;
      const needsPrevious = opensWithBackReference(r.text) || chains.some((c) => c.suspension === 'back_reference' || c.suspension === 'mid_chain_start');
      const shortRemainder = (stripMarks(r.text.slice(0, 260)).match(/\sعن\s/g) || []).length <= 1; // a full chain follows the opening: readable, only held; otherwise the chain is the previous report's
      if (needsPrevious && shortRemainder && !prevOut.length && !h.sanad_inherits_from) chainContext.needs_previous_report = true; // the reader must answer cannot_read_without_previous_report
      if (h.sanad_inherits_from) {
        const par = X[h.sanad_inherits_from];
        chainContext.parent_report = par ? { ref: 'parent', source: profile.source || 'OITI', number: par.hadith_no, chain_text: trimSpan((par.sanad_ar || clip(par.text_ar, 400)), 480), note: 'this report repeats the parent report\'s chain; its own text does not carry it' } : { ref: 'parent', note: 'parent not found' };
      }
      // source claims, as each source wrote them
      const claims = []; const absent = [];
      const names = []; // for name_facts: {name, src, ...}
      const k6d = k6[record];
      if (k6d && (k6d.source_ids || []).length) {
        const seq = k6d.source_ids.map((i) => (lexById['narrator:rawi:' + i] || {}).name_ar || ('(id ' + i + ' not in lexicon)'));
        claims.push({ source: 'K6I', what: 'the K6 dataset\'s own narrator index, in source order (names are the lexicon\'s names for those ids; routes are not separated)', sequence: seq });
        k6d.source_ids.forEach((i) => { const l = lexById['narrator:rawi:' + i]; if (l) names.push({ name: (l.name_ar || '').replace(HONORIFIC, '').trim(), src: 'MSD', died_ah: l.death_year_hijri, generation: l.tabaqah_raw, place: l.death_place, lex: l.id }); });
      } else if (r.hadith_id.includes(':k6:')) absent.push('K6I: no narrator index for this report');
      const kgx = cross.hadith_kg[record];
      if (kgx) {
        const routes = []; const seen = new Set(); const rawisSeen = [];
        for (const s of kgSanads.all(+kgx.external_report_id)) {
          const rawis = kgRawis.all(s.id); const key = rawis.map((x) => x.id).join(','); if (seen.has(key) || !rawis.length) continue; seen.add(key);
          routes.push(rawis.map((x) => x.name)); rawis.forEach((x) => rawisSeen.push(x));
        }
        if (routes.length) claims.push({ source: 'HKG', what: 'hadith-kg\'s narrator list per sanad, nearest the compiler first (the compiler is dropped)', routes: routes.slice(0, 3) });
        rawisSeen.forEach((x) => names.push({ name: x.name, src: 'HKG', died_ah: x.death_year_raw, generation: x.tabaka != null ? 'tabaka ' + x.tabaka + ' (1-38 scale)' : null, place: x.death_place || (x.iqama ? clip(x.iqama, 40) : null) }));
      } else if (tradition !== 'imami') absent.push('HKG: no unique matching report in hadith-kg');
      const rwx = cross.riwayat[record];
      if (rwx) {
        const byChain = {};
        for (const m of rwMentions.all(rwx.external_report_id)) (byChain[m.chain_no] ||= []).push(m);
        const routes = Object.values(byChain).map((ms) => ms.map((m) => stripMarks(m.surface)));
        if (routes.length) claims.push({ source: 'RWY', what: 'the Riwayat corpus\'s chain mentions as it read them in its copy of the text (a machine reading; surfaces as in its text)', routes: routes.slice(0, 3) });
        Object.values(byChain).flat().forEach((m) => { if (m.std_name) names.push({ name: m.std_name, src: 'RWY', died_ah: m.death_year, generation: m.tabaqa ? 'tabaqa ' + m.tabaqa : null, place: m.city, assertion: /^source_annotation/.test(m.id_method || '') ? 'annotation' : 'machine' }); });
      } else absent.push('RWY: no unique matching report in Riwayat');
      if (tradition === 'imami' && profile.source === 'THQ' && (h.sanad || '').trim()) claims.push({ source: 'THQ', what: 'Thaqalayn\'s English sanad as provided', english_sanad: clip(h.sanad.trim(), 420) });
      if (hasChainField) claims.push({ source: 'NMC', what: 'the first lines of the text are the source\'s own chain field; nothing further to add', note: pure[record] ? 'chain_status ' + pure[record].chain_status : null });
      if (noChain[record]) claims.push({ source: 'NMC', what: 'the source ships NO chain for this report (' + noChain[record].reason + '); read only what the text itself writes' });
      if (openiti[record] && (openiti[record].source_notes || []).length) chainContext.source_notes = openiti[record].source_notes.slice(0, 3).map((n) => ({ source: 'OITI', kind: n.kind, text_ar: clip(n.text_ar, 200) }));
      // do the sources agree?
      const flat = claims.filter((c) => c.sequence || c.routes).map((c) => ({ source: c.source, names: (c.sequence || c.routes.flat()).map(fold) }));
      if (flat.length >= 2) {
        const compat = (x, y) => { const a = x.split(' '), b = y.split(' '); const [s, l] = a.length <= b.length ? [a, b] : [b, a]; return s.every((t) => l.includes(t)); };
        const lines = [];
        for (let i = 0; i < flat.length; i++) for (let j = i + 1; j < flat.length; j++) {
          const miss = flat[i].names.filter((n) => !flat[j].names.some((m) => compat(n, m)));
          const miss2 = flat[j].names.filter((n) => !flat[i].names.some((m) => compat(n, m)));
          if (miss.length || miss2.length) lines.push(`${flat[i].source} and ${flat[j].source} differ: ${flat[i].source} only: ${clip(miss.slice(0, 3).join('، ') || '-', 60)}; ${flat[j].source} only: ${clip(miss2.slice(0, 3).join('، ') || '-', 60)}`);
        }
        chainContext.sources_agree = lines.length ? { agree: false, differences: lines.slice(0, 3) } : { agree: true };
      }
      if (claims.length) chainContext.source_claims = claims;
      if (absent.length) chainContext.sources_absent = absent;
      // name facts: one per distinct name, lexicon first; Sunni lexicon only for Sunni reports
      const seenName = new Set(); const facts = [];
      for (const n of names) {
        const key = fold(n.name); if (seenName.has(key)) continue; seenName.add(key);
        const same = (tradition === 'sunni' && n.lex) ? (lexKey.get(nameKey3(n.name)) || []).filter((x) => x.id !== n.lex && x.death_year_hijri != null).slice(0, 3).map((x) => ({ died_ah: x.death_year_hijri, place: x.death_place })) : [];
        const fact = { name: n.name, src: n.src }; if (n.died_ah != null) fact.died_ah = n.died_ah; if (n.generation) fact.generation = n.generation; if (n.place) fact.place = n.place; if (n.assertion) fact.assertion = n.assertion; if (same.length) fact.same_name_in_lexicon = same;
        if (fact.died_ah != null || fact.generation || fact.place) facts.push(fact);
      }
      if (facts.length) chainContext.name_facts = facts;
      // correspondences
      const corr = corrRows.filter((c) => c.hadith_id === r.hadith_id).map((c) => ({ c, o: X[c.corresponding_hadith_id] })).filter((x) => x.o);
      const rank = { same_wording: 0, variant: 1, partial: 2 };
      corr.sort((a, b) => (b.c.confirmed - a.c.confirmed) || ((rank[a.c.relation_class] ?? 3) - (rank[b.c.relation_class] ?? 3)) || (b.c.jaccard - a.c.jaccard) || (a.o.id < b.o.id ? -1 : 1));
      const corrOut = corr.filter((x) => x.o.source_work_id !== work || true).slice(0, 3).map((x, i) => {
        const oprof = PROFILES[x.o.source_work_id] || {};
        const span = ['sunni:ahmad', 'sunni:darimi', 'sunni:muwatta'].includes(x.o.source_work_id) ? (x.o.sanad || '').trim() : (chainSpan(x.o.text_ar, surfacesOf[x.o.id] || []) || clip(x.o.text_ar, 260));
        return { ref: 'corr' + (i + 1), source: oprof.source || null, found_by: 'SWI', work: x.o.collection_name, tradition: x.o.tradition_id.replace('tradition:', ''), number: x.o.hadith_no, relation: x.c.relation_class, confirmed: !!x.c.confirmed, chain_text: trimSpan(span || '', 300) };
      });
      if (corrOut.length) chainContext.correspondences = corrOut;
      // archive flags
      if (!noFlags) {
        const flags = [];
        for (const c of chains) {
          if (c.structure_status === 'uncertain') flags.push({ source: 'SWI', flag: 'rule-based reading flagged uncertain: ' + (c.structure_reasons || []).map((x) => STRUCTURE_WORDS[x] || x).join('; ') });
          if (c.suspension) flags.push({ source: 'SWI', flag: SUSPENSION_WORDS[c.suspension] || c.suspension });
        }
        mentionRows.filter((m) => m.hadith_id === r.hadith_id && m.identity_withheld_reason).slice(0, 2).forEach((m) => flags.push({ source: 'SWI', flag: 'identity withheld: ' + clip(m.identity_withheld_reason, 160) }));
        const uniq = [...new Map(flags.map((f) => [f.flag, f])).values()];
        if (uniq.length) chainContext.archive_flags = uniq.slice(0, 4);
      }
      if (wantStored) chainContext.stored_chain = { source: 'SWI', routes: chains.map((c) => mentionRows.filter((m) => m.chain_id === c.id).map((m) => m.surface_ar)) };
      Object.assign(context, chainContext);
    }
    // ---- text and metadata context ----
    if (kind !== 'chain') {
      const tm = { stored_text_sha256: h.arabic_sha256, stored_text_chars: h.text_ar.length, copies: [], source_file_hashes: [] };
      const pushCopy = (source, locator, theirs) => tm.copies.push({ source, locator, ...diffTexts(h.text_ar, theirs) });
      const kgx = cross.hadith_kg[record]; const rwx = cross.riwayat[record];
      const meta = { ours: { collection: h.collection_name, book: h.book_name || null, chapter: h.chapter_title || null, chapter_no: h.chapter_no || null, report_number: h.hadith_no, volume: h.volume || h.book_volume || null, page: h.page_ref || null, url: h.url || null, source_display_label: h.source_display_label || null, tradition }, gradings: assessments.filter((a) => a.hadith_id === r.hadith_id).slice(0, 4).map((a) => ({ grader: a.grader, grade: a.grade_raw, kind: a.kind, cited: [a.cited_work, a.cited_volume, a.cited_page].filter(Boolean).join(' ') || null, source_field: a.source_field })), local: [], disagreements: [] };
      if (kgx) { const row = kgHadith.get(+kgx.external_report_id); if (row) { pushCopy('HKG', 'hadith-kg hadith ' + kgx.external_report_id + ' (' + kgx.match_class + ')', row.nass); meta.local.push({ source: 'HKG', book: row.book_name, number_in_book: row.no_inbook, page: row.page_no }); } }
      if (rwx) { const row = rwHadith.get(rwx.external_report_id); if (row) { pushCopy('RWY', 'Riwayat ' + rwx.external_report_id + ' (' + rwx.match_class + ')', row.text); meta.local.push({ source: 'RWY', book: row.book, number: row.number }); } }
      let raw = null; if (profile.source === 'THQ') raw = thaqalaynRaw(h);
      if (raw) {
        pushCopy('THQ', 'Thaqalayn API V2 ' + raw.bookId + ' id ' + raw.id + ' (the provider\'s own text, our source file)', raw.arabicText);
        const grades = [['mohseniGrading', 'Muhsini'], ['behbudiGrading', 'al-Behbudi'], ['majlisiGrading', 'al-Majlisi']].filter(([k]) => raw[k]).map(([k, g]) => ({ grader: g, grade: raw[k] }));
        meta.local.push({ source: 'THQ', book: raw.book, volume: raw.volume, category: raw.category, chapter: raw.chapter, url: raw.URL, gradings: grades });
        if (String(raw.volume || '') !== String(h.volume || h.book_volume || '') && raw.volume) meta.disagreements.push('volume: ours ' + (h.volume || h.book_volume || 'none') + ', THQ ' + raw.volume);
        if (grades.length && !meta.gradings.length) meta.disagreements.push('grading: THQ gives ' + grades.map((g) => g.grader + ' ' + g.grade).join(', ') + '; none stored');
      }
      const rawFolded = (work === 'ibadi:musnad-rabi' || work === 'zaydi:musnad-zayd') ? openitiRawFolded(work) : null;
      if (rawFolded) { const ours = fold(h.text_ar.replace(LEADING_NUMBER, '')); const words = ours.split(' '); const head = words.slice(0, 10).join(' '), tailWords = words.slice(-8).join(' ');
        const relation = rawFolded.includes(ours) ? 'identical_after_normalisation' : rawFolded.includes(head) && rawFolded.includes(tailWords) ? 'start_and_end_located_in_raw_file' : 'not_located_in_raw_file'; // page markers inside the raw text can break a whole-text match
        tm.copies.push({ source: 'OITI', locator: 'the OpenITI raw file we downloaded (our source file)', relation, words_ours: words.length, ...(relation === 'not_located_in_raw_file' ? { note: 'raw-file markup and orthography can prevent a match: not evidence of a difference' } : {}) }); }
      if (pure[record]) tm.source_file_hashes.push({ source: 'NMC', same_as_stored: pure[record].text_ar_sha256 === h.arabic_sha256, note: 'the Pure Canon source file\'s text hash' });
      if (k6[record]) tm.source_file_hashes.push({ source: 'K6I', same_as_stored: k6[record].arabic_sha256 === h.arabic_sha256, note: 'the K6 dataset text hash' });
      const independent = tm.copies.filter((c) => c.source !== 'THQ' && c.source !== 'OITI').length;
      tm.second_local_copies = tm.copies.length; tm.independent_of_our_source = independent;
      tm.statement = tm.copies.length ? `${tm.copies.length} local copy/copies of this text besides ours` + (independent ? '' : ' (none independent of the file we loaded from)') : 'NO second local copy of this report\'s text exists in the downloads: nothing local to compare with (itself a finding)';
      if (tm.copies.some((c) => !['identical_after_normalisation', 'identical_except_word_spacing', 'start_and_end_located_in_raw_file', 'not_located_in_raw_file'].includes(c.relation))) tm.differences_found = true;
      if (kgx && meta.local.find((l) => l.source === 'HKG') && String(meta.local.find((l) => l.source === 'HKG').number_in_book) !== String(h.hadith_no)) meta.disagreements.push('number: ours ' + h.hadith_no + ', HKG ' + meta.local.find((l) => l.source === 'HKG').number_in_book + ' (different numbering schemes are common; read before reporting)');
      const filled = ['book', 'chapter', 'report_number', 'volume', 'page', 'url'].filter((k) => meta.ours[k]); const missing = ['book', 'chapter', 'report_number', 'volume', 'page', 'url', 'gradings'].filter((k) => k === 'gradings' ? !meta.gradings.length : !meta.ours[k]);
      meta.not_stored = missing;
      // lookup keys for the online check (public references only)
      const lookup = { collection: h.collection_name, number: h.hadith_no };
      const matn = clip(fold(h.matn_ar || '') || fold(h.text_ar).split(' ').slice(Math.floor(fold(h.text_ar).split(' ').length * 0.55)).join(' '), 70);
      lookup.matn_phrase_ar = matn.split(' ').slice(0, 8).join(' ');
      lookup.opening_words_ar = fold(h.text_ar).split(' ').slice(0, 8).join(' ');
      if (profile.sunnah_collection) { lookup.hadith_api = `https://cdn.jsdelivr.net/gh/fawazahmed0/hadith-api@1/editions/${profile.hadith_api_edition}/${h.hadith_no}.json`; lookup.sunnah_com_blocked = `${profile.sunnah_collection}:${h.hadith_no}`; }
      if (raw) lookup.thaqalayn_api = { bookId: raw.bookId, id: String(raw.id), url: `https://www.thaqalayn-api.net/api/v2/${raw.bookId}` };
      if (profile.openiti_uri) lookup.openiti = profile.openiti_uri;
      lookup.turath_search = 'api.turath.io/search?q=<matn_phrase_ar or opening_words_ar>&ver=3';
      if (tradition === 'imami') lookup.noor = 'hadith.inoor.ir ElasticHadithList by opening words (rate limited)';
      context.text_and_metadata = { ...tm, metadata: meta, lookup };
    }
    const budget = kind === 'text' ? BUDGET.text : BUDGET.chain;
    if (kind === 'both') { /* both context kinds in one packet are for inspection only; budget applies to the sum */ }
    fitBudget(context, budget * (kind === 'both' ? 2 : 1) - 110, omitted);
    if (omitted.length) { context.omitted_for_size = omitted; omitted.forEach((o) => { stats.omitted[o] = (stats.omitted[o] || 0) + 1; }); }
    Object.keys(context).forEach((k) => { if (!['work', 'omitted_for_size'].includes(k)) bump(k); });
    built.push({ id: r.id, text: r.text, context });
  }
  kg.close(); rw.close();

  // 8. write packets (same grouping as the v1 pilot packets when they exist) and the manifest
  fs.mkdirSync(outDir, { recursive: true });
  const groups = [];
  const v1Dir = path.join(ROOT, 'pilot', 'packets');
  if (!idsFile && fs.existsSync(v1Dir)) {
    const byId = Object.fromEntries(built.map((b) => [b.id, b]));
    for (const f of fs.readdirSync(v1Dir).filter((n) => /^packet-\d+\.jsonl$/.test(n)).sort()) groups.push([f, fs.readFileSync(path.join(v1Dir, f), 'utf8').split('\n').filter(Boolean).map((l) => byId[JSON.parse(l).id]).filter(Boolean)]);
  } else for (let i = 0; i < built.length; i += 25) groups.push([`packet-${String(i / 25 + 1).padStart(2, '0')}.jsonl`, built.slice(i, i + 25)]);
  const packetDir = path.join(outDir, kind === 'text' ? 'packets-text' : kind === 'both' ? 'packets-both' : 'packets');
  fs.mkdirSync(packetDir, { recursive: true });
  for (const [name, items] of groups) fs.writeFileSync(path.join(packetDir, name), items.map((b) => JSON.stringify(b)).join('\n') + '\n', 'utf8');
  const sizes = built.map((b) => JSON.stringify(b.context).length);
  const dv = await sql`select id, git_head, completed_at from dataset_versions where is_current limit 1`;
  const manifest = {
    built_at_utc: new Date().toISOString(), kind, reports: built.length, packets: groups.length, packet_size: 25,
    context_chars: { median: median(sizes), p95: pct(sizes, 0.95), max: Math.max(...sizes), budget: BUDGET[kind] || null },
    reports_with_context_kind: stats.kinds, omitted_for_size: stats.omitted,
    inputs: {
      pilot_reports_sha256: sha256File(path.join(ROOT, 'pilot', 'reports.jsonl')), work_profiles_sha256: sha256File(path.join(HERE, 'work_profiles.json')), builder_sha256: sha256File(__filename),
      sidecars: Object.fromEntries(sidecarFiles.map((f) => [path.basename(f), sha256File(f)])),
      external_databases: { 'hadith-kg.db': 'sha256 d528084321e715006712e0e2461809a3afc9408065a1d1af90238c8b723815a6 (datasets/sources/external/hadith-kg/README.md)', 'hadith_master.db (Riwayat)': 'bound by reconciled/external_identity_sidecars.manifest.json inputs_sha256' },
      production_dataset_version: dv[0] || null,
    },
  };
  fs.writeFileSync(path.join(packetDir, 'manifest.json'), JSON.stringify(manifest, null, 1) + '\n', 'utf8');
  console.log(JSON.stringify({ packetDir, ...manifest.context_chars, kinds: stats.kinds, omitted: stats.omitted }));
  await sql.end();
}
if (require.main === module) main().catch((e) => { console.error(e.message); process.exit(1); });
else module.exports = { fold, diffTexts, chainSpan, opensWithBackReference, trimSpan, fitBudget };
