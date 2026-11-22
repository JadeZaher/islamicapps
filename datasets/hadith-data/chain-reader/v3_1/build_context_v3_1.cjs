// Builds context-carrying chain packets {id, text, context} for the v3.1 chain reader (copy of v3/build_context_v3.cjs; see v3_1/AGENTS.md §previous reports).
//   node --env-file=.env.local datasets/hadith-data/chain-reader/v3_1/build_context_v3_1.cjs --sample <sample.json> --out-dir <dir> [--packet-size 20] [--no-archive-flags]
// sample.json: [{"id": "<opaque id>", "hadith_id": "hadith:..."}, ...] in packet order. Read-only on production (DATABASE_URL_PRODUCTION is never printed).
// Changes from v2: previous reports are found in book order (provider file and numeric id) and walked back to a report that writes its own chain (up to LIMIT),
// every intermediate carried and marked `has_written_chain`; the named chain is not elided; previous_reports sit outside the 3,000-character budget (own cap);
// `context.work.key` names the work for the tool's compiler aliases. Packets carry no hadith id; the opaque-id map is the caller's private file.
// v3.1 (owner ruling 2): an asker with a pronoun («وسأله X», «وكتب إليه»), «وقال عليه السلام» and a bare «وعن X» in an Imami work also get previous reports; the walk stops at the nearest earlier report
// that writes its chain OR names the speaker in its opening (`supplies: 'chain' | 'speaker'`), every intermediate carried. The private reports file lists each previous report's hadith id.
'use strict';
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const crypto = require('crypto');
const readline = require('readline');
const lib = require('./backref_lib_v3_1.cjs');

const HERE = __dirname;
const ROOT = path.resolve(HERE, '..');
const REPO = path.resolve(ROOT, '..', '..', '..');
const SIDECARS = path.join(REPO, 'datasets', 'hadith-data', 'reconciled');
const EXTERNAL = path.join(REPO, 'datasets', 'sources', 'external');
const BUDGET = { chain: 3000, previous: 2600 };        // characters of JSON per report: everything but previous_reports; previous_reports on their own
const PROFILES = JSON.parse(fs.readFileSync(path.join(HERE, 'work_profiles_v3_1.json'), 'utf8'));
const LAYERED = ['sunni:ahmad', 'sunni:darimi', 'sunni:muwatta'];

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

const leadingNumber = (t) => { const m = /^\s*(\d+)\s*[-–.ـ]/.exec(t || ''); return m ? m[1] : null; };

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
const OMIT_ORDER = ['source_notes', 'name_facts', 'correspondences', 'archive_flags', 'source_claims', 'parent_report']; // dropped first -> last when over budget
function fitBudget(context, budget, omitted) {
  const size = () => JSON.stringify(context).length;
  const trims = [
    () => { if (context.name_facts) context.name_facts.forEach((f) => { delete f.same_name_in_lexicon; }); },
    () => { if (context.correspondences) context.correspondences = context.correspondences.slice(0, 2); },
    () => { if (context.correspondences) context.correspondences.forEach((c) => { c.chain_text = clip(c.chain_text || '', 160); }); },
    () => { if (context.name_facts) context.name_facts = context.name_facts.slice(0, 6); },
    () => { if (context.source_claims) context.source_claims.forEach((c) => { if (c.english_sanad) c.english_sanad = clip(c.english_sanad, 240); }); },
  ];
  for (const t of trims) { if (size() <= budget) return; t(); }
  for (const key of OMIT_ORDER) { if (size() <= budget) return; if (context[key] !== undefined) { delete context[key]; omitted.push(key); } }
}
/** previous_reports within their own cap: intermediates shorten first (each is still carried), then the named chain's saying, then its middle (marked …). */
function fitPrevious(items, cap = BUDGET.previous) {
  const size = () => JSON.stringify(items).length;
  const steps = [
    () => items.forEach((p) => { if (!p.has_written_chain) p.chain_text = clip(p.chain_text, 90); }),
    () => items.forEach((p) => { delete p.text_head; }),
    () => items.forEach((p) => { if (p.has_written_chain) p.chain_text = trimSpan(p.chain_text, 1200); }),
    () => items.forEach((p) => { if (!p.has_written_chain) p.chain_text = clip(p.chain_text, 50); }),
  ];
  for (const step of steps) { if (size() <= cap) break; step(); }
  return items;
}

async function main() {
  const sampleFile = arg('sample'); if (!sampleFile || sampleFile === true) throw new Error('--sample <sample.json> is required');
  const outDir = path.resolve(arg('out-dir', path.join(HERE, 'packets')));
  const packetSize = +arg('packet-size', 20); const noFlags = !!arg('no-archive-flags');
  const pg = require(path.join(REPO, 'node_modules', 'postgres')); const postgres = pg.default || pg;
  if (!process.env.DATABASE_URL_PRODUCTION) throw new Error('DATABASE_URL_PRODUCTION is not set (use --env-file=.env.local)');
  const sql = postgres(process.env.DATABASE_URL_PRODUCTION, { max: 2, connect_timeout: 30, connection: { default_transaction_read_only: 'on' } });
  const { DatabaseSync } = require('node:sqlite');

  // 1. the reports to build
  const sample = JSON.parse(fs.readFileSync(sampleFile, 'utf8'));
  const hadithIds = sample.map((s) => s.hadith_id); const recordIds = new Set(hadithIds.map((h) => h.replace(/^hadith:/, '')));
  const rowsOf = await sql`select id, collection_id, text_ar, sanad from hadiths where id in ${sql(hadithIds)} and retired_at is null`;
  const byId = Object.fromEntries(rowsOf.map((r) => [r.id, r]));
  const workOf = (collectionId) => collectionId.replace(/^collection:/, '');
  const readerTextOf = (r) => (LAYERED.includes(workOf(r.collection_id)) && (r.sanad || '').trim() ? `${r.sanad.trim()}\n\n${r.text_ar}` : r.text_ar);
  const reports = sample.filter((s) => byId[s.hadith_id]).map((s) => ({ id: s.id, hadith_id: s.hadith_id, text: readerTextOf(byId[s.hadith_id]), work: workOf(byId[s.hadith_id].collection_id) }));
  const missingReports = sample.length - reports.length;

  // 2. database rows
  const hadiths = await sql`select h.id, h.record_id, h.source_record_id, h.collection_id, h.chapter_id, h.chapter_no, h.chapter_title, h.hadith_no, h.hadith_no_int, h.volume,
      h.source_display_label, h.tradition_id, h.text_ar, h.arabic_sha256, h.sanad, h.sanad_inherits_from, h.sanad_ar, h.source_notes, h.provider_hadith_id,
      b.name as book_name, c.name as collection_name, c.source_work_id
    from hadiths h left join books b on b.id = h.book_id join collections c on c.id = h.collection_id where h.id in ${sql(hadithIds)}`;
  const H = Object.fromEntries(hadiths.map((h) => [h.id, h]));
  const chainRows = await sql`select id, hadith_id, branch, structure_status, structure_reasons, suspension, missing_link_after from chains where hadith_id in ${sql(hadithIds)} and retired_at is null order by hadith_id, branch`;
  const mentionRows = await sql`select chain_id, hadith_id, position, surface_ar, identity_withheld_reason from chain_mentions where hadith_id in ${sql(hadithIds)} and retired_at is null order by chain_id, position`;
  const corrRows = await sql`select hadith_id, corresponding_hadith_id, relation_class, jaccard, containment, confirmed from public_report_correspondences where hadith_id in ${sql(hadithIds)}`;

  // previous reports: book order, walked back to a report that writes its own chain
  const walks = {};
  const needing = reports.filter((r) => H[r.hadith_id] && (lib.inheritsAtTheStart(r.text) || chainRows.some((c) => c.hadith_id === r.hadith_id && (c.suspension === 'back_reference' || c.suspension === 'mid_chain_start'))));
  if (needing.length) {
    const collections = [...new Set(needing.map((r) => H[r.hadith_id].collection_id))];
    const bookRows = await sql`select id, collection_id, source_record_id, provider_hadith_id, hadith_no, text_ar, sanad from hadiths where collection_id in ${sql(collections)} and retired_at is null`;
    const books = lib.orderedBooks(bookRows);
    const position = new Map(); for (const list of books.values()) list.forEach((row, i) => position.set(row.id, { list, i }));
    for (const r of needing) {
      const at = position.get(r.hadith_id);
      const widened = H[r.hadith_id].tradition_id === 'tradition:imami' && ['bare_an', 'asker_pronoun', 'implicit_speaker'].includes(lib.openingClass(r.text));
      walks[r.hadith_id] = at ? lib.walkBack(at.list, at.i, readerTextOf, lib.LIMIT, widened) : { previous: [], chainFound: false, supplies: null, noOrder: true };
    }
  }
  const extraIds = new Set(); // previous, parent and corresponding reports whose mentions we need to find their chain spans
  Object.values(walks).forEach((w) => w.previous.forEach((p) => extraIds.add(p.id)));
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
  const lexAll = await sql`select n.id, n.name_ar, p.death_year_hijri, p.death_place from narrators n left join narrator_lexicon_profiles p on p.narrator_id = n.id where n.authority = 'rawi' and n.retired_at is null`;
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

  // 7. build per report
  const stats = { reports: reports.length, kinds: {}, omitted: {}, previous: { needed: 0, supplied: 0, chain_found: 0, flagged_needs_previous_report: 0, parent: 0 } };
  const bump = (k) => { stats.kinds[k] = (stats.kinds[k] || 0) + 1; };
  const built = [];
  for (const r of reports) {
    const h = H[r.hadith_id]; if (!h) { built.push({ id: r.id, text: r.text, context: { error: 'report not found' } }); continue; }
    const record = r.hadith_id.replace(/^hadith:/, ''); const work = h.source_work_id; const profile = PROFILES[work] || {}; const tradition = h.tradition_id.replace('tradition:', '');
    const chains = chainRows.filter((c) => c.hadith_id === r.hadith_id);
    const common = {
      work: {
        key: work, name: h.collection_name, tradition, source: profile.source || null,
        compiler: profile.compiler_head ? { ar: profile.compiler_ar, en: profile.compiler_en, head_of_every_chain: true, added_by_tool: true } : { head_of_every_chain: false, note: profile.compiler_note || 'no compiler head for this work' },
        book: h.book_name || null, chapter: h.chapter_title || null, report_number: h.hadith_no, convention: profile.convention || null,
        ...(profile.compiler_note && profile.compiler_head ? { compiler_note: profile.compiler_note } : {}),
      },
    };
    const context = { ...common }; const omitted = [];
    const chainContext = {};
    const hasChainField = LAYERED.includes(work);
    // previous reports: nearest first, up to and including the first that writes its own chain; each intermediate is carried
    const prevOut = [];
    const walk = walks[r.hadith_id];
    if (walk) {
      stats.previous.needed++;
      walk.previous.forEach((p, i) => {
        const bearing = walk.chainFound && i === walk.previous.length - 1;
        const speakerOnly = bearing && walk.supplies === 'speaker';
        const span = hasChainField ? (p.sanad || '').trim() : speakerOnly ? clip(p.text_ar, 320) : (chainSpan(p.text_ar, surfacesOf[p.id] || []) || clip(p.text_ar, 450));
        const item = { ref: 'prev' + (i + 1), number: leadingNumber(p.text_ar) || p.hadith_no, source: profile.source || null, has_written_chain: bearing, ...(bearing ? { supplies: walk.supplies } : {}), chain_text: bearing ? trimSpan(span, 900) : clip(span, 140) };
        if (bearing && !speakerOnly && !hasChainField && span.length < p.text_ar.length - 20) item.text_head = clip(p.text_ar, 300); // the report itself, so the reader sees what follows the chain
        prevOut.push(item);
      });
    }
    {
      const needsPrevious = lib.opensAtTheStart(r.text) || chains.some((c) => c.suspension === 'back_reference' || c.suspension === 'mid_chain_start');
      const shortRemainder = (stripMarks(r.text.slice(0, 260)).match(/\sعن\s/g) || []).length <= 1; // a full chain follows the opening: readable, only held; otherwise the chain is the previous report's
      const chainFound = !!(walk && walk.chainFound);
      const trueBackReference = ['pronoun', 'isnad_phrase'].includes(lib.openingForm(r.text)) || chains.some((c) => c.suspension === 'back_reference' || c.suspension === 'mid_chain_start'); // a bare «وعن X» (al-Faqih's way of writing a saying) is read from its text and only held
      if (needsPrevious && trueBackReference && shortRemainder && !chainFound && !h.sanad_inherits_from) { chainContext.needs_previous_report = true; stats.previous.flagged_needs_previous_report++; } // the reader must answer cannot_read_without_previous_report
      if (prevOut.length) stats.previous.supplied++;
      if (chainFound) { stats.previous.chain_found++; if (walk.supplies === 'speaker') stats.previous.speaker_found = (stats.previous.speaker_found || 0) + 1; }
      if (h.sanad_inherits_from) {
        stats.previous.parent++;
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
      Object.assign(context, chainContext);
    }
    fitBudget(context, BUDGET.chain - 110, omitted);
    let finalContext = context;
    if (prevOut.length) { const { work: w, ...rest } = context; finalContext = { work: w, previous_reports: fitPrevious(prevOut), ...rest }; }
    if (omitted.length) { finalContext.omitted_for_size = omitted; omitted.forEach((o) => { stats.omitted[o] = (stats.omitted[o] || 0) + 1; }); }
    Object.keys(finalContext).forEach((k) => { if (!['work', 'omitted_for_size'].includes(k)) bump(k); });
    built.push({ id: r.id, text: r.text, context: finalContext, _work: work });
  }
  kg.close(); rw.close();
  const reportsOut = arg('reports-out'); // the packets' hidden half for the fix pipeline's submit tool (--reports): same text as the packet, stored chains as surfaces
  if (reportsOut && reportsOut !== true) {
    const snapshotAt = new Date().toISOString();
    const lines = reports.filter((r) => H[r.hadith_id]).map((r) => { const h = H[r.hadith_id];
      const storedChains = chainRows.filter((c) => c.hadith_id === r.hadith_id).map((c) => ({ chain_id: c.id, branch: c.branch, structure_status: c.structure_status, surfaces: mentionRows.filter((m) => m.chain_id === c.id).map((m) => m.surface_ar) }));
      const walked = walks[r.hadith_id]; const previousIds = walked ? walked.previous.map((p, i) => ({ ref: 'prev' + (i + 1), hadith_id: p.id, supplies: walked.chainFound && i === walked.previous.length - 1 ? walked.supplies : null })) : [];
      return JSON.stringify({ id: r.id, hadith_id: r.hadith_id, previous_reports: previousIds, tradition: h.tradition_id.replace('tradition:', ''), work: h.source_work_id.split(':').pop(), text: r.text, text_layout: LAYERED.includes(h.source_work_id) ? 'chain_field_then_matn' : 'full_text', snapshot_at: snapshotAt, stored_chains: storedChains }); });
    fs.mkdirSync(path.dirname(path.resolve(reportsOut)), { recursive: true });
    fs.writeFileSync(path.resolve(reportsOut), lines.join('\n') + '\n', 'utf8');
  }

  // 8. write packets and the manifest
  fs.mkdirSync(outDir, { recursive: true });
  const groups = [];
  for (let i = 0; i < built.length; i += packetSize) groups.push([`packet-${String(i / packetSize + 1).padStart(3, '0')}.jsonl`, built.slice(i, i + packetSize)]);
  const bytes = {};
  for (const [name, items] of groups) { const data = items.map(({ _work, ...b }) => JSON.stringify(b)).join('\n') + '\n'; fs.writeFileSync(path.join(outDir, name), data, 'utf8'); bytes[name] = Buffer.byteLength(data, 'utf8'); }
  const sizes = built.map((b) => JSON.stringify(b.context).length);
  const workCounts = {}; built.forEach((b) => { workCounts[b._work] = (workCounts[b._work] || 0) + 1; });
  const dv = await sql`select id, git_head, completed_at from dataset_versions where is_current limit 1`;
  const manifest = {
    format: 'shura-chain-packets-manifest/3', built_at_utc: new Date().toISOString(), reports: built.length, requested: sample.length, not_found_in_production: missingReports, packets: groups.length, packet_size: packetSize,
    packet_bytes: bytes, total_bytes: Object.values(bytes).reduce((a, b) => a + b, 0),
    context_chars: { median: median(sizes), p95: pct(sizes, 0.95), max: Math.max(...sizes), budget_without_previous_reports: BUDGET.chain, previous_reports_cap: BUDGET.previous },
    work_counts: Object.fromEntries(Object.entries(workCounts).sort()), reports_with_context_kind: stats.kinds, omitted_for_size: stats.omitted, previous_reports: stats.previous, walk_back_limit: lib.LIMIT,
    inputs: {
      sample_sha256: sha256File(path.resolve(sampleFile)), work_profiles_sha256: sha256File(path.join(HERE, 'work_profiles_v3_1.json')), builder_sha256: sha256File(__filename), backref_lib_sha256: sha256File(path.join(HERE, 'backref_lib_v3_1.cjs')),
      sidecars: Object.fromEntries(sidecarFiles.map((f) => [path.basename(f), sha256File(f)])),
      external_databases: { 'hadith-kg.db': 'sha256 d528084321e715006712e0e2461809a3afc9408065a1d1af90238c8b723815a6 (datasets/sources/external/hadith-kg/README.md)', 'hadith_master.db (Riwayat)': 'bound by reconciled/external_identity_sidecars.manifest.json inputs_sha256' },
      production_dataset_version: dv[0] || null,
    },
    ids: built.map((b) => b.id),
  };
  fs.writeFileSync(path.join(outDir, 'manifest.json'), JSON.stringify(manifest, null, 1) + '\n', 'utf8');
  console.log(JSON.stringify({ outDir, reports: built.length, packets: groups.length, ...manifest.context_chars, previous: stats.previous, omitted: stats.omitted }));
  await sql.end();
}
if (require.main === module) main().catch((e) => { console.error(e.message); process.exit(1); });
else module.exports = { fitBudget, fitPrevious, leadingNumber, chainSpan, trimSpan };
