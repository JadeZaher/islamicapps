// Deterministic isnad-defect detectors over Sunni chains (read-only; pure functions over a data snapshot).
// Position 0 = collector's shaykh; position+1 = that narrator's teacher; last = nearest the Prophet.
'use strict';

const DIACRITICS = /[\u064B-\u0652\u0670\u0640\u06D6-\u06ED]/g;
// Character-level normalisation (length-preserving apart from diacritic removal).
function norm(s) {
  return (s || '')
    .replace(DIACRITICS, '')
    .replace(/[\u0623\u0625\u0622\u0671]/g, '\u0627')
    .replace(/\u0649/g, '\u064A')
    .replace(/\u200f|\u200e|\u202b|\u202c/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

const AR = '\u0621-\u064A';
// JS \b is ASCII-only, so Arabic word edges are spelled out with lookarounds.
const surfaceRegex = (surface) => {
  const esc = surface.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/ /g, '\\s+');
  return new RegExp(`(?<![${AR}])(?:\u0648|\u0641)?${esc}(?![${AR}])`, 'g');
};

const BARE_RELATION = new Set(
  ['ابي', 'ابيه', 'ابوه', 'جده', 'جدي', 'عمه', 'عمي', 'اخيه', 'ابيها', 'ابنه', 'امه', 'خاله', 'ابى', 'ابيهم', 'جدها', 'عمها', 'اخي', 'اخوه', 'ابن اخيه', 'ابنها'].map(norm)
);
const PROPHET_SURFACE = /^(?:ال)?نبي(?: صلى الله عليه وسلم)?$|رسول الله|^محمد صلى الله عليه وسلم|\u0635\u0644\u0649 \u0627\u0644\u0644\u0647/;
const COLLECTOR_SURFACE = {
  'collection:sunni:bukhari': /البخاري|محمد بن اسماعيل$/,
  'collection:sunni:muslim': /^مسلم$|مسلم بن الحجاج/,
  'collection:sunni:nasai': /النسائي|^ابو عبد الرحمن$/,
  'collection:sunni:tirmidhi': /الترمذي|^ابو عيسى$/,
  'collection:sunni:abudawud': /^ابو داود$|ابو داود السجستاني/,
  'collection:sunni:ibnmajah': /ابن ماجه|ابو عبد الله ابن ماجه/,
};

// A waw-only gap joins two names that report together (co-transmitters), not teacher -> student.
const WAW_GAP = /^[\s،,]*و?[\s،,]*$/; // waw is usually swallowed by the next surface => empty/comma-only gap
// Route break inside one chain: standalone ح (tahwil) or a new waw-prefixed transmission verb.
const TAHWIL_H = /(?:^|\s)\u062D(?=[\s.،,]|$)/;
const NEW_ROUTE_VERB_NORM = /(?:^|\s)(?:قال\s+)?و(?:اخبرنا|حدثنا|اخبرني|حدثني|انبانا|انباني|سمعت|اخبرتنا|حدثتنا)(?=\s|$)/;

// Locate each mention surface in normalised text in order; returns gaps between neighbouring surfaces.
function surfaceGaps(text, mentions) {
  const t = norm(text);
  let cursor = 0;
  const spans = [];
  for (const m of mentions) {
    const re = surfaceRegex(norm(m.surface_ar));
    re.lastIndex = cursor;
    const hit = re.exec(t);
    if (!hit) { spans.push(null); continue; }
    spans.push({ start: hit.index, end: hit.index + hit[0].length });
    cursor = hit.index + hit[0].length;
  }
  const gaps = [];
  for (let i = 0; i + 1 < mentions.length; i++) {
    const a = spans[i], b = spans[i + 1];
    gaps.push(a && b && b.start >= a.end ? t.slice(a.end, b.start) : null);
  }
  return { gaps, spans, normText: t };
}

function prepare(cache) {
  const narrators = new Map(cache.narrators.map((n) => [n.id, n]));
  const hadithById = new Map(cache.hadiths.map((h) => [h.id, h]));
  const chains = new Map(cache.chains.map((c) => [c.id, { ...c, mentions: [] }]));
  for (const m of cache.mentions) {
    const c = chains.get(m.chain_id);
    if (c) c.mentions.push(m);
  }
  for (const c of chains.values()) c.mentions.sort((a, b) => a.position - b.position);
  const chainsByHadith = new Map();
  for (const c of chains.values()) {
    if (!chainsByHadith.has(c.hadith_id)) chainsByHadith.set(c.hadith_id, []);
    chainsByHadith.get(c.hadith_id).push(c);
  }
  // Empirical "terminal" propensity: share of a narrator's appearances at the final position.
  const appear = new Map(), terminal = new Map();
  for (const c of chains.values()) {
    c.mentions.forEach((m, i) => {
      if (!m.narrator_id) return;
      appear.set(m.narrator_id, (appear.get(m.narrator_id) || 0) + 1);
      if (i === c.mentions.length - 1) terminal.set(m.narrator_id, (terminal.get(m.narrator_id) || 0) + 1);
    });
  }
  const terminalRate = (id) => (appear.get(id) >= 20 ? (terminal.get(id) || 0) / appear.get(id) : null);
  return { narrators, hadithById, chains, chainsByHadith, appear, terminal, terminalRate };
}


const NON_NAME = new Set(['بهذا', 'الاسناد', 'باسناده', 'كلاهما', 'احدهما', 'مثله', 'نحوه', 'بمثل', 'بنحو', 'بمعني', 'بمعناه', 'معناه', 'اللفظ', 'لفظ', 'كلهم', 'سمعا', 'زاد', 'فذكر', 'ذكر', 'الحديث', 'حديثه', 'رواية', 'انه', 'انها', 'كان', 'قالا', 'قالت', 'ح', 'مثل', 'نحو', 'بعضهم', 'جميعا', 'وكان', 'قال', 'تابعه', 'المعني', 'المعنى', 'قلت', 'جاءت', 'يوم', 'عام', 'فقال', 'فقالت', 'فنهاه', 'فذكر', 'هذا', 'عن', 'حدثتني', 'حدثني', 'حدثنا', 'اخبرني', 'اخبرنا', 'انبانا', 'سمعت', 'حدثته', 'حدثه', 'وحدثني', 'وحدثنا', 'واخبرنا', 'واخبرني', 'حدثت']);
const GAP_FUNCTION_WORDS = new Set(['حدثنا', 'اخبرنا', 'حدثني', 'اخبرني', 'انبانا', 'انباني', 'سمعت', 'عن', 'قال', 'قالا', 'قالوا', 'ثنا', 'نا', 'ان', 'انه', 'و', 'ح', 'حدثتنا', 'اخبرتنا', 'يقول', 'يحدث', 'قراءه', 'عليه', 'قرات', 'على', 'قالت', 'قلت', 'وحدثنا', 'واخبرنا', 'وحدثني', 'واخبرني', 'ثم', 'يعني', 'هو', 'وهو', 'يرفعه', 'يبلغ', 'رفعه', 'قراءة', 'سمعته', 'سمعتهم', 'حدثه', 'اخبره', 'حدثهم', 'بلغه']);
const GAP_ASIDE_WORDS = new Set(['جميعا', 'سمع', 'واحد', 'وانا', 'اسمع', 'غير', 'واللفظ', 'له', 'لفظ', 'بهذا', 'الاسناد', 'مثله', 'نحوه', 'كلاهما', 'كلهم', 'احدهما', 'او', 'مرة']);
const FATHER = new Set(['ابي', 'ابيه', 'ابوه', 'ابيها', 'ابى', 'ابيهم'].map(norm));
const GRAND = new Set(['جده', 'جدي', 'جدها'].map(norm));
const cleanName = (s) => norm((s || '').replace(/[()]/g, ' ').replace(/رضي الله عن\S*/g, ' ').replace(/\s+/g, ' '));
// Nasab segments: «هشام بن عروة بن الزبير» -> [هشام, عروة, الزبير]
const nasab = (name) => name.split(/\s+(?:بن|ابن)\s+/).map((x) => x.trim()).filter(Boolean);
const kunyaFold = (x) => x.replace(/(^|\s)ابي(?=\s|$)/g, '$1ابو');
// True when `expected` occurs as a contiguous token run inside `name` (kunya-folded).
const nameContains = (name, expected) => (' ' + kunyaFold(name) + ' ').includes(' ' + kunyaFold(expected) + ' ');

const tokens = (s) => norm(s).split(' ').filter(Boolean);
const collectionOf = (ctx, hadithId) => ctx.hadithById.get(hadithId)?.collection_id;

function hit(ctx, detector, kind, chain, mention, evidence, extra = {}) {
  return {
    detector, kind,
    collection: collectionOf(ctx, chain.hadith_id),
    chain_id: chain.id, hadith_id: chain.hadith_id,
    mention_id: mention ? mention.id : null,
    extraction_method: mention ? (mention.extraction_method || 'unresolved') : 'chain-level',
    evidence, ...extra,
  };
}

// Each detector: (ctx, chain) -> hits[]
const detectors = {
  // Adjacent identified mentions whose lifespans cannot be teacher -> student. Blame is assigned by
  // neighbour votes (a mention contradicting BOTH neighbours is the culprit), then by surface weakness.
  chrono_contradiction(ctx, chain) {
    const ms = chain.mentions, pairs = [];
    for (let i = 0; i + 1 < ms.length; i++) {
      const s = ms[i], t = ms[i + 1];
      if (!s.narrator_id || !t.narrator_id || s.narrator_id === t.narrator_id) continue;
      const sn = ctx.narrators.get(s.narrator_id), tn = ctx.narrators.get(t.narrator_id);
      if (!sn || !tn) continue;
      let rule = null, gap = null;
      if (tn.death_min != null && sn.death_max != null && tn.death_min - sn.death_max > 40) {
        rule = 'teacher_dies_>40y_after_student'; gap = tn.death_min - sn.death_max;
      } else if (sn.death_min != null && tn.death_max != null && sn.death_min - tn.death_max > 120) {
        rule = 'teacher_died_>120y_before_student'; gap = sn.death_min - tn.death_max;
      }
      if (rule) pairs.push({ i, s, t, sn, tn, rule, gap });
    }
    const votes = new Map();
    for (const p of pairs) for (const m of [p.s, p.t]) votes.set(m.id, (votes.get(m.id) || 0) + 1);
    const weak = (m) => BARE_RELATION.has(norm(m.surface_ar)) || tokens(m.surface_ar).length <= 1;
    // A mention is "supported" when its OTHER neighbour has known lifespans consistent with it.
    const consistent = (stud, teach) => {
      const a = stud.narrator_id && ctx.narrators.get(stud.narrator_id), b = teach.narrator_id && ctx.narrators.get(teach.narrator_id);
      if (!a || !b || a.death_max == null || b.death_min == null || a.death_min == null || b.death_max == null) return false;
      return !(b.death_min - a.death_max > 40) && !(a.death_min - b.death_max > 120);
    };
    const supported = (m, other) => {
      const idx = ms.indexOf(m);
      if (other === ms[idx + 1]) return idx > 0 ? consistent(ms[idx - 1], m) : false; // looked at student side
      return idx + 1 < ms.length ? consistent(m, ms[idx + 1]) : false;
    };
    const byCulprit = new Map();
    for (const p of pairs) {
      const sv = votes.get(p.s.id), tv = votes.get(p.t.id);
      let culprit, confidence, basis;
      const isRelation = (m) => BARE_RELATION.has(norm(m.surface_ar));
      // The final mention is normally a Companion: reliable by construction, so the other side is the suspect.
      const finalMention = ms[ms.length - 1];
      const companionLike = (m, n) => m === finalMention && n.death_max != null && n.death_max <= 120;
      const sSup = supported(p.s, p.t), tSup = supported(p.t, p.s);
      if (sv !== tv) { culprit = sv > tv ? p.s : p.t; confidence = 'high'; basis = 'contradicts_both_neighbours'; }
      else if (isRelation(p.s) !== isRelation(p.t)) { culprit = isRelation(p.s) ? p.s : p.t; confidence = 'high'; basis = 'bare_relation_resolved_to_implausible_person'; }
      else if (companionLike(p.t, p.tn) !== companionLike(p.s, p.sn)) { culprit = companionLike(p.t, p.tn) ? p.s : p.t; confidence = 'high'; basis = 'final_mention_is_companion_so_other_side_suspect'; }
      else if (sSup !== tSup) { culprit = sSup ? p.t : p.s; confidence = 'high'; basis = 'other_neighbour_unsupported_vs_supported'; }
      else if (weak(p.s) !== weak(p.t)) { culprit = weak(p.s) ? p.s : p.t; confidence = 'medium'; basis = 'weaker_surface_bare_name_or_relation'; }
      else { culprit = tokens(p.s.surface_ar).length <= tokens(p.t.surface_ar).length ? p.s : p.t; confidence = 'medium'; basis = 'ambiguous_pair'; }
      const other = culprit === p.s ? p.t : p.s;
      const entry = { p, other, confidence, basis };
      if (!byCulprit.has(culprit.id)) byCulprit.set(culprit.id, { culprit, entries: [] });
      byCulprit.get(culprit.id).entries.push(entry);
    }
    const out = [];
    for (const { culprit, entries } of byCulprit.values()) {
      const e = entries[0], p = e.p;
      const conf = entries.some((x) => x.confidence === 'high') ? 'high' : 'medium';
      const gapKind = e.basis === 'final_mention_is_companion_so_other_side_suspect' && tokens(culprit.surface_ar).length >= 2 && p.rule === 'teacher_died_>120y_before_student' ? 'missing_link' : 'misidentified';
      out.push(hit(ctx, 'chrono_contradiction', gapKind, chain, culprit, {
        rule: p.rule, values: {
          student_position: p.s.position, student_surface: p.s.surface_ar, student_narrator_id: p.s.narrator_id, student_death: [p.sn.death_min, p.sn.death_max],
          teacher_position: p.t.position, teacher_surface: p.t.surface_ar, teacher_narrator_id: p.t.narrator_id, teacher_death: [p.tn.death_min, p.tn.death_max], gap_years: p.gap,
          blame_basis: e.basis, culprit_position: culprit.position, contradicting_pairs: entries.length,
        },
      }, { pair: [p.s.id, p.t.id], gap_years: p.gap, rule_id: p.rule, confidence: conf, blame_basis: e.basis, culprit_narrator_id: culprit.narrator_id }));
    }
    return out;
  },

  repeated_narrator(ctx, chain) {
    const seen = new Map(), out = [];
    for (const m of chain.mentions) {
      if (!m.narrator_id) continue;
      if (seen.has(m.narrator_id)) {
        const first = seen.get(m.narrator_id);
        out.push(hit(ctx, 'repeated_narrator', 'branch_seam', chain, m, {
          rule: 'same_narrator_at_two_positions', values: { narrator_id: m.narrator_id, positions: [first.position, m.position], surfaces: [first.surface_ar, m.surface_ar] },
        }, { first_position: first.position, second_position: m.position }));
      } else seen.set(m.narrator_id, m);
    }
    return out;
  },

  // Route break (ح / new waw-verb) falling between two mentions of ONE stored chain.
  seam_in_chain(ctx, chain) {
    const h = ctx.hadithById.get(chain.hadith_id);
    if (!h || chain.mentions.length < 2) return [];
    const { gaps } = surfaceGaps(h.text_ar, chain.mentions);
    const out = [];
    gaps.forEach((g, i) => {
      if (g == null) return;
      const isH = TAHWIL_H.test(g), isVerb = NEW_ROUTE_VERB_NORM.test(g);
      if (!isH && !isVerb) return;
      const next = chain.mentions[i + 1];
      // Benign tahwil: text after the marker restates the previous shaykh (route re-converges on him), so one stored chain is right.
      // Key = the ism of the previous shaykh (first non-connector word, two for «عبد X»); the restatement may use a shorter/longer form.
      const prevWords = norm(chain.mentions[i].surface_ar).split(' ').filter((w) => !['بن', 'ابن', 'ابو', 'ابي'].includes(w));
      // Very common isms (محمد, علي, ...) must match with the following word too, otherwise another «محمد» would hide a real seam.
      const COMMON_ISM = new Set(['عبد', 'محمد', 'احمد', 'علي', 'عمر', 'عمرو', 'يحيي', 'ابراهيم', 'اسماعيل', 'سليمان', 'سعيد', 'عثمان', 'خالد', 'يزيد', 'الحسن', 'الحسين', 'حسن', 'حسين', 'موسي', 'عيسي', 'هشام', 'جعفر', 'يوسف', 'عبيد', 'مسلم', 'زيد', 'سعد', 'عبد الله']);
      const takeWords = prevWords[0] === 'عبد' || COMMON_ISM.has(prevWords[0]) ? 2 : 1;
      const prevKey = prevWords.slice(0, takeWords).join('(?:\\s+(?:بن|ابن))?\\s+').replace(/(^|\s)ال(?=..)/g, '$1');
      if (prevWords.length >= takeWords && prevKey.length > 2 && new RegExp(`(?<![ء-ي])(?:ال)?${prevKey}(?![ء-ي])`).test(norm(g))) return;
      out.push(hit(ctx, 'seam_in_chain', 'branch_seam', chain, next, {
        rule: isH ? 'tahwil_ح_between_adjacent_mentions' : 'new_route_verb_between_adjacent_mentions',
        values: { gap_text: g.trim(), split_before_position: next.position, previous_position: i, previous_surface: chain.mentions[i].surface_ar, next_surface: next.surface_ar },
      }, { split_position: next.position, gap: g }));
    });
    return out;
  },

  // Text carries route markers but the hadith has a single stored chain.
  tahwil_marker_vs_chain_count(ctx, chain) {
    const h = ctx.hadithById.get(chain.hadith_id);
    if (!h) return [];
    const all = ctx.chainsByHadith.get(chain.hadith_id);
    if (all[0].id !== chain.id) return []; // once per hadith
    const t = norm(h.text_ar);
    const prefix = t.slice(0, Math.max(0, t.indexOf('قال رسول الله') > 0 ? t.indexOf('قال رسول الله') : 400));
    // One route break = a standalone ح (optionally followed by its own «وحدثنا») or a bare waw-verb; count each once.
    const H_WITH_VERB = /(?:^|\s)ح(?=[\s.،,]|$)[\s.،,]*(?:و(?:حدثنا|اخبرنا|حدثني|اخبرني|انبانا|انباني))?/g;
    // A waw-verb at the very start («وحدثنا فلان») continues the book's flow; it is not a route break.
    const body = prefix.replace(/^\s*و(?:حدثنا|اخبرنا|حدثني|اخبرني|انبانا|انباني)(?=\s)/, '');
    const marked = body.replace(H_WITH_VERB, ' ¦ ').replace(new RegExp(NEW_ROUTE_VERB_NORM.source, 'g'), ' ¦ ');
    const markers = marked.split('').filter((c) => c === '¦');
    if (!markers.length) return [];
    if (all.length >= markers.length + 1) return [];
    return [hit(ctx, 'tahwil_marker_vs_chain_count', 'branch_seam', chain, null, {
      rule: 'route_markers_exceed_stored_chains_minus_one', values: { markers, stored_chains: all.length },
    }, { markers: markers.length, stored_chains: all.length })];
  },

  // Names joined only by waw («فلان وفلان قالا») stored as teacher -> student.
  co_transmitter_gap(ctx, chain) {
    const h = ctx.hadithById.get(chain.hadith_id);
    if (!h || chain.mentions.length < 2) return [];
    const { gaps } = surfaceGaps(h.text_ar, chain.mentions);
    const out = [];
    gaps.forEach((g, i) => {
      if (g == null || !WAW_GAP.test(g)) return;
      const a = chain.mentions[i], b = chain.mentions[i + 1];
      out.push(hit(ctx, 'co_transmitter_gap', 'co_transmitter', chain, b, {
        rule: 'adjacent_mentions_joined_only_by_waw', values: { gap_text: g, first_position: a.position, first_surface: a.surface_ar, second_position: b.position, second_surface: b.surface_ar },
      }, { first_position: a.position, second_position: b.position }));
    });
    return out;
  },

  // Stored order disagrees with the order the surfaces occur in the text (single-chain hadiths only).
  text_order_mismatch(ctx, chain) {
    const all = ctx.chainsByHadith.get(chain.hadith_id);
    const h = ctx.hadithById.get(chain.hadith_id);
    if (!h || all.length !== 1 || chain.mentions.length < 3) return [];
    const t = norm(h.text_ar);
    const matnAt = t.indexOf('قال رسول الله');
    const body = matnAt > 0 ? t.slice(0, matnAt) : t.slice(0, 600);
    const first = chain.mentions.map((m) => { const re = surfaceRegex(norm(m.surface_ar)); const x = re.exec(body); return x ? x.index : null; });
    const placed = chain.mentions.map((m, i) => ({ m, at: first[i] })).filter((x) => x.at != null);
    let inversions = 0, worst = null;
    for (let i = 1; i < placed.length; i++) if (placed[i].at < placed[i - 1].at) { inversions++; worst = worst || placed[i]; }
    if (inversions < 2) return [];
    return [hit(ctx, 'text_order_mismatch', 'order_reversed', chain, worst.m, {
      rule: 'surface_order_in_text_differs_from_stored_order', values: { inversions, placed: placed.length, first_inverted_position: worst.m.position },
    }, { inversions })];
  },

  // Whole chain stored nearest-Prophet-first: most identified adjacent pairs have the "teacher" dying later.
  chain_reversed(ctx, chain) {
    const ms = chain.mentions.filter((m) => m.narrator_id && ctx.narrators.get(m.narrator_id)?.death_min != null);
    if (ms.length < 4) return [];
    let later = 0, earlier = 0;
    for (let i = 0; i + 1 < ms.length; i++) {
      const a = ctx.narrators.get(ms[i].narrator_id), b = ctx.narrators.get(ms[i + 1].narrator_id);
      if (b.death_min > a.death_max + 5) later++; else if (a.death_min > b.death_max + 5) earlier++;
    }
    if (later >= 3 && later >= 3 * Math.max(earlier, 1)) {
      return [hit(ctx, 'chain_reversed', 'order_reversed', chain, null, { rule: 'teacher_dies_later_in_most_pairs', values: { pairs_teacher_later: later, pairs_teacher_earlier: earlier } })];
    }
    return [];
  },

  // Prophet / honorific surfaces stored as a narrator.
  prophet_as_mention(ctx, chain) {
    const out = [];
    chain.mentions.forEach((m, i) => {
      if (!PROPHET_SURFACE.test(norm(m.surface_ar))) return;
      out.push(hit(ctx, 'prophet_as_mention', i === chain.mentions.length - 1 ? 'not_a_narrator' : 'not_a_narrator', chain, m, {
        rule: i === chain.mentions.length - 1 ? 'prophet_surface_final_position' : 'prophet_surface_non_final_position', values: { position: m.position, surface: m.surface_ar, of: chain.mentions.length },
      }));
    });
    return out;
  },

  // Narrator that is overwhelmingly terminal (Companion-like, derived from the data) sitting mid-chain.
  companion_nonfinal(ctx, chain) {
    const out = [];
    const last = chain.mentions.length - 1;
    chain.mentions.forEach((m, i) => {
      if (i === last || !m.narrator_id) return;
      const r = ctx.terminalRate(m.narrator_id);
      if (r != null && r >= 0.7) {
        out.push(hit(ctx, 'companion_nonfinal', 'other', chain, m, {
          rule: 'terminal_rate_>=0.7_but_not_last', values: { position: m.position, of: chain.mentions.length, terminal_rate: +r.toFixed(2), appearances: ctx.appear.get(m.narrator_id), narrator_id: m.narrator_id, surface: m.surface_ar },
        }));
      }
    });
    return out;
  },

  // Bare relation («أبي», «أبيه», «جده») resolved to a person: verify against the student's nasab.
  bare_relation_resolved(ctx, chain) {
    const out = [];
    const ms = chain.mentions;
    const nameOf = (m) => { const n = m.narrator_id && ctx.narrators.get(m.narrator_id); return cleanName(n && n.name_ar) || norm(m.surface_ar); };
    ms.forEach((m, i) => {
      const rel = norm(m.surface_ar);
      if (!m.narrator_id || !BARE_RELATION.has(rel) || i === 0) return;
      const n = ctx.narrators.get(m.narrator_id);
      const isFather = FATHER.has(rel), isGrand = GRAND.has(rel);
      let expected = null, root = null;
      if (isFather) { root = ms[i - 1]; const nas = nasab(nameOf(root)); if (nas.length >= 2) expected = nas[1]; }
      else if (isGrand && i >= 2 && FATHER.has(norm(ms[i - 1].surface_ar))) { root = ms[i - 2]; const nas = nasab(nameOf(root)); if (nas.length >= 3) expected = nas[2]; }
      let verdict = 'unverifiable';
      if (expected) {
        // Compare the ism only («عبد الله» keeps two words): trailing nisba/kunya words in nasab segments are unreliable.
        const parts = kunyaFold(expected).split(' ');
        const head = (parts[0] === 'عبد' || parts[0] === 'ابو') && parts[1] ? parts.slice(0, 2).join(' ') : parts[0];
        verdict = nameContains(cleanName(n.name_ar), head) || nameContains(cleanName(n.name_ar), expected) ? 'consistent' : 'mismatch';
      }
      const base = { surface: m.surface_ar, position: m.position, narrator_id: m.narrator_id, narrator_name_ar: n && n.name_ar, root_student: root && nameOf(root), expected_name: expected, verdict };
      out.push(hit(ctx, 'bare_relation_resolved', verdict === 'mismatch' ? 'misidentified' : 'other', chain, m,
        { rule: verdict === 'mismatch' ? 'relation_resolved_to_person_whose_name_is_not_in_students_nasab' : 'relation_resolved_to_person_' + verdict, values: base }, { verdict }));
    });
    return out;
  },

  // Identified mention whose surface words do not occur in the resolved narrator's own name.
  surface_name_mismatch(ctx, chain) {
    const out = [];
    const stop = new Set(['بن', 'ابن', 'ابو', 'ابي', 'ام', 'عن', 'رضي', 'الله', 'عنه', 'عنها', 'عنهما']);
    const bag = (s) => kunyaFold(cleanName(s)).split(' ').map((w) => w.replace(/^ال(?=..)/, '').replace(/[ةه]$/, '')).filter((w) => w && !stop.has(w));
    for (const m of chain.mentions) {
      if (!m.narrator_id) continue;
      const n = ctx.narrators.get(m.narrator_id);
      if (!n || !n.name_ar) continue;
      const nw = new Set(bag(n.name_ar));
      if (BARE_RELATION.has(norm(m.surface_ar))) continue;
      // Only the explicit nasab words (the word after بن/ابن, not leading) are compared: kunya/nisba are often absent from name_ar.
      const toks = norm(m.surface_ar).split(' ');
      const nasabWords = [];
      toks.forEach((w, i) => { if (i > 0 && (w === 'بن' || w === 'ابن') && toks[i + 1]) nasabWords.push(...bag(toks[i + 1])); });
      const missing = nasabWords.filter((w) => !nw.has(w));
      if (missing.length) {
        out.push(hit(ctx, 'surface_name_mismatch', 'misidentified', chain, m, {
          rule: 'surface_words_absent_from_resolved_narrator_name', values: { position: m.position, surface: m.surface_ar, narrator_id: m.narrator_id, narrator_name_ar: n.name_ar, missing_words: missing },
        }));
      }
    }
    return out;
  },

  // Surface is a formula / aside / matn fragment rather than a person («بهذا الإسناد», «كلاهما», «اللفظ لفلان»).
  non_name_surface(ctx, chain) {
    const out = [];
    chain.mentions.forEach((m) => {
      const toks = tokens(m.surface_ar);
      const bad = toks.filter((w) => NON_NAME.has(w));
      const nasabConnectors = toks.filter((w) => w === 'بن' || w === 'ابن' || w === 'بنت').length;
      const longNonNasab = toks.length >= 7 && nasabConnectors < 2; // long nasab chains («X بن Y بن Z ...») are names, not leaks
      if (bad.length || longNonNasab) {
        out.push(hit(ctx, 'non_name_surface', 'not_a_narrator', chain, m, {
          rule: bad.length ? 'surface_contains_formula_word' : 'surface_has_7_or_more_words_without_nasab', values: { position: m.position, surface: m.surface_ar, words: bad, narrator_id: m.narrator_id || null },
        }));
      }
    });
    return out;
  },

  // Words in the text between two adjacent stored mentions that are neither transmission verbs nor markers: a possible unstored narrator.
  gap_has_unstored_words(ctx, chain) {
    const h = ctx.hadithById.get(chain.hadith_id);
    if (!h || chain.mentions.length < 2 || h.id.startsWith('hadith:pure-canon:')) return [];
    const { gaps } = surfaceGaps(h.text_ar, chain.mentions);
    const out = [];
    gaps.forEach((g, i) => {
      if (g == null) return;
      if (TAHWIL_H.test(g) || NEW_ROUTE_VERB_NORM.test(g)) return; // reported as seam
      if (/\s-\s|^\s*-|-\s*$/.test(g)) return; // editorial gloss between hyphens, not a narrator
      const rest = tokens(g.replace(/[،,.:؛]/g, ' ')).filter((w) => !GAP_FUNCTION_WORDS.has(w) && !GAP_ASIDE_WORDS.has(w));
      // Waw-led words are co-transmitters (K6 stores those as separate branches); need >=2 plain words to look like a name.
      if (rest.length >= 2 && rest.length <= 8 && !rest[0].startsWith('و')) {
        const b = chain.mentions[i + 1];
        out.push(hit(ctx, 'gap_has_unstored_words', 'missing_link', chain, b, {
          rule: 'text_between_adjacent_mentions_not_verbs', values: { before_position: i, after_position: b.position, extra_words: rest, gap_text: g.trim() },
        }));
      }
    });
    return out;
  },

  // Collector's own name used as a chain mention.
  collector_self_mention(ctx, chain) {
    const re = COLLECTOR_SURFACE[collectionOf(ctx, chain.hadith_id)];
    if (!re) return [];
    const out = [];
    chain.mentions.forEach((m) => {
      if (re.test(norm(m.surface_ar))) out.push(hit(ctx, 'collector_self_mention', 'not_a_narrator', chain, m, {
        rule: 'surface_matches_collector_name', values: { position: m.position, surface: m.surface_ar },
      }));
    });
    return out;
  },

  // Truncation proxy: final mention is a narrator who is almost never terminal elsewhere.
  truncated_before_companion(ctx, chain) {
    const last = chain.mentions[chain.mentions.length - 1];
    if (!last || !last.narrator_id) return [];
    const r = ctx.terminalRate(last.narrator_id);
    if (r != null && r <= 0.03) {
      return [hit(ctx, 'truncated_before_companion', 'missing_link', chain, last, {
        rule: 'final_mention_is_rarely_terminal_elsewhere', values: { position: last.position, terminal_rate: +r.toFixed(3), appearances: ctx.appear.get(last.narrator_id), narrator_id: last.narrator_id, surface: last.surface_ar },
      })];
    }
    return [];
  },
};

// Corpus-level detectors (need all chains).
const corpusDetectors = {
  // Pairs observed in both directions: flag the minority-direction adjacencies.
  bidirectional_pair(ctx) {
    const pairCount = new Map(); // "student|teacher" -> [{chain, mention}]
    for (const c of ctx.chains.values()) {
      for (let i = 0; i + 1 < c.mentions.length; i++) {
        const s = c.mentions[i], t = c.mentions[i + 1];
        if (!s.narrator_id || !t.narrator_id || s.narrator_id === t.narrator_id) continue;
        const k = `${s.narrator_id}|${t.narrator_id}`;
        if (!pairCount.has(k)) pairCount.set(k, []);
        pairCount.get(k).push({ c, s, t });
      }
    }
    const out = [];
    for (const [k, list] of pairCount) {
      const [a, b] = k.split('|');
      const rev = pairCount.get(`${b}|${a}`);
      if (!rev || k > `${b}|${a}`) continue; // handle each unordered pair once
      const [major, minor, majorKey] = list.length >= rev.length ? [list, rev, k] : [rev, list, `${b}|${a}`];
      for (const { c, s, t } of minor) {
        out.push(hit(ctx, 'bidirectional_pair', 'order_reversed', c, t, {
          rule: 'pair_seen_in_both_directions', values: { stored_direction: `${s.narrator_id} <- ${t.narrator_id}`, this_direction_count: minor.length, opposite_direction_count: major.length, student_position: s.position, teacher_position: t.position },
        }, { pair_key: k, minor_count: minor.length, major_count: major.length, pair: [s.id, t.id] }));
      }
    }
    return out;
  },

  // Chains above the per-collection 99th percentile length or of length 1.
  length_outlier(ctx) {
    const byCol = new Map();
    for (const c of ctx.chains.values()) {
      const col = collectionOf(ctx, c.hadith_id);
      if (!byCol.has(col)) byCol.set(col, []);
      byCol.get(col).push(c);
    }
    const out = [];
    for (const [col, list] of byCol) {
      const lens = list.map((c) => c.mentions.length).sort((x, y) => x - y);
      const p99 = lens[Math.floor(lens.length * 0.99)];
      for (const c of list) {
        const n = c.mentions.length;
        if (n > Math.max(p99, 9)) out.push(hit(ctx, 'length_outlier', 'other', c, null, { rule: 'length_above_collection_p99', values: { length: n, p99, collection: col } }));
        else if (n <= 1) out.push(hit(ctx, 'length_outlier', 'missing_link', c, null, { rule: 'length_<=1', values: { length: n } }));
      }
    }
    return out;
  },
};

function runAll(ctx, { only } = {}) {
  const hits = [];
  for (const chain of ctx.chains.values()) {
    for (const [name, fn] of Object.entries(detectors)) {
      if (only && !only.includes(name)) continue;
      hits.push(...fn(ctx, chain));
    }
  }
  for (const [name, fn] of Object.entries(corpusDetectors)) {
    if (only && !only.includes(name)) continue;
    hits.push(...fn(ctx));
  }
  return hits;
}

module.exports = { norm, prepare, detectors, corpusDetectors, runAll, surfaceGaps, tokens, BARE_RELATION };
