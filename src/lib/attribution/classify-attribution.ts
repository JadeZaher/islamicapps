/**
 * classify-attribution.ts — faithful TypeScript port of
 * `datasets/classify_attribution.py`.
 *
 * Phase 0 (track neo4j_isnad_graph_regen_20260516, FR-0.3 / D-6) requires the
 * REAL `attributed_to × narration_level × tradition` distribution to be
 * measured over the unified CSV. The Python classifier is deterministic and
 * rule-based on Arabic markers; this is a 1:1 port — the `_norm` normalization
 * and every marker regex are transcribed verbatim from the Python source so
 * the TS measurement matches the Python ground truth. DO NOT re-invent the
 * Arabic normalization here.
 *
 * Source of truth: datasets/classify_attribution.py (read before editing).
 * Any divergence is a bug; keep this file in lock-step with the Python.
 */

// ── Arabic normalization (port of classify_attribution._norm) ───────────────
//
// The EXACT codepoints of the Python source character classes were read
// byte-for-byte from datasets/classify_attribution.py and are reproduced here
// with explicit \u escapes (Arabic literals are NOT used — they were silently
// mangled by tooling and wrongly swallowed the base Arabic letter block
// U+0621–U+064A, normalizing everything to ""). Do not "simplify" back to
// literals.
//
// Python: _DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")  — codepoints:
//   U+0610–U+061A  (Arabic signs: high hamza … small high seen)
//   U+064B–U+065F  (tashkeel: fathatan … wavy hamza below — NOT letters)
//   U+0670         (Arabic letter superscript alef)
//   U+06D6–U+06ED  (Quranic annotation marks)
//   U+0640         (tatweel / kashida)
const _DIACRITICS = /[ؐ-ًؚ-ٰٟۖ-ۭـ]/g;
// Python: _ALEF = re.compile(r"[آأإٱ]") — U+0622 U+0623 U+0625 U+0671 → ا (U+0627)
const _ALEF = /[آأإٱ]/g;

/** Strip tashkeel/tatweel and unify alef/ya for marker matching. */
export function norm(s: string | null | undefined): string {
  let out = (s || '').replace(_DIACRITICS, '');
  out = out.replace(_ALEF, 'ا'); // → ا
  out = out.replace(/ى/g, 'ي'); // ى → ي
  return out;
}

// NOTE: every pattern below matches norm()-ed text — no diacritics, alef
// variants folded to ا, ى folded to ي. Literals are written in that
// normalized form (e.g. ابي not أبي), transcribed verbatim from the Python.

// ── Unicode-correct word boundary (Python `\b` parity) ──────────────────────
//
// FAITHFUL-PORT FIX (track neo4j_isnad_graph_regen_20260516, Blocker 2):
// JavaScript `RegExp` `\b` is ASCII-only — it treats every Arabic codepoint as
// a NON-word char, so any `\b` adjacent to an Arabic letter behaves completely
// differently from Python `re`, whose `\b` on `str` is Unicode-aware. Python's
// regex word char `\w` over U+0600–U+06FF is exactly the set
// `[\p{L}\p{N}_]` (verified codepoint-by-codepoint against `re`: identical
// ranges 0x620–0x64a, 0x660–0x669, 0x66e–0x66f, 0x671–0x6d3, 0x6d5,
// 0x6e5–0x6e6, 0x6ee–0x6fc, 0x6ff; combining marks U+064B/U+0670/U+06D6 are
// NOT word chars in either engine — and `_norm` strips them anyway). So a
// Python trailing `\b` is precisely "the following position is not a word
// char" and a leading `\b` is "the preceding position is not a word char".
// `\p{L}|\p{N}|_` mirrors Python's actual `\w` (it is NOT the narrower
// `[ء-ي]`, which would wrongly drop Arabic-Indic digits and extended Arabic
// letters); regexes using it MUST carry the `u` flag.
//
// Every `\b` in this file is a TRAILING boundary (an Arabic word char
// immediately precedes it), so the faithful substitution is the trailing
// form below. The leading form (for any future marker) is the symmetric
// lookbehind: `(?<![\p{L}\p{N}_])X` for a Python leading `\bX`.
const WB_TRAIL = '(?![\\p{L}\\p{N}_])'; // Python trailing  X\b   → X(?![\w])

// ── Prophet ﷺ attribution (→ marfu) ──────────────────────────────────────
const _PROPHET_RE = new RegExp(
  'رسول\\s+الله' +
    '|النبي' +
    WB_TRAIL +
    '|صلي\\s+الله\\s+عليه\\s+و(?:سلم|اله|الـه)' +
    '|سمعت\\s+رسول\\s+الله' +
    '|كان\\s+رسول\\s+الله' +
    '|ان\\s+النبي' +
    '|عن\\s+النبي',
  'u'
);

// Hadith qudsi: Prophet relating directly from God (still marfu, flagged).
const _QUDSI_RE = new RegExp(
  'قال\\s+الله\\s+(?:تعالي|عز\\s+وجل|تبارك)' +
    '|في(?:ما)?\\s+يرويه?\\s+عن\\s+رب' +
    '|الحديث\\s+القدسي'
);

// ── Imam markers (→ imam, when not raised to the Prophet) ─────────────────
// Ordered: more specific kunya/laqab first. Value = canonical attributed_to.
const _IMAM_MARKERS: ReadonlyArray<readonly [RegExp, string]> = [
  [new RegExp('ابي\\s+عبد\\s+الله(?:\\s+الصادق|\\s+جعفر)?|جعفر\\s+بن\\s+محمد|الصادق'), 'Imam al-Sadiq'],
  // "Abu Ja'far" alone is ambiguous: al-Baqir vs al-Kulayni (compiler of
  // al-Kafi, "ابو جعفر محمد بن يعقوب", at the head of every chain) vs
  // al-Jawad. Require a Baqir-disambiguating form and explicitly exclude the
  // al-Kulayni patronymic so the compiler is never read as the Imam.
  [
    new RegExp(
      'الباقر|ابي\\s+جعفر\\s+محمد\\s+بن\\s+علي' +
        '|ابي\\s+جعفر(?!\\s+محمد\\s+بن\\s+يعقوب)(?!\\s+الثاني)' +
        '\\s+عليه\\s+السلام'
    ),
    'Imam al-Baqir',
  ],
  [new RegExp('ابي\\s+الحسن\\s+الرضا|علي\\s+بن\\s+موسي\\s+الرضا|الرضا'), 'Imam al-Rida'],
  [new RegExp('ابي\\s+الحسن\\s+موسي|موسي\\s+بن\\s+جعفر|الكاظم|ابي\\s+ابراهيم'), 'Imam al-Kazim'],
  [new RegExp('ابي\\s+جعفر\\s+(?:الثاني|الجواد)|الجواد|محمد\\s+بن\\s+علي\\s+التقي'), 'Imam al-Jawad'],
  [new RegExp('ابي\\s+الحسن\\s+(?:الثالث|علي\\s+بن\\s+محمد)|الهادي|علي\\s+بن\\s+محمد\\s+النقي'), 'Imam al-Hadi'],
  [
    new RegExp('ابي\\s+محمد\\s+(?:الحسن\\s+بن\\s+علي)?\\s*العسكري|العسكري|الحسن\\s+بن\\s+علي\\s+العسكري'),
    'Imam al-Askari',
  ],
  [
    new RegExp('القائم' + WB_TRAIL + '|المهدي|صاحب\\s+(?:الزمان|الامر)|الحجة\\s+بن\\s+الحسن', 'u'),
    'Imam al-Mahdi',
  ],
  [new RegExp('الحسين\\s+بن\\s+علي|ابي\\s+عبد\\s+الله\\s+الحسين'), 'Imam al-Husayn'],
  [new RegExp('الحسن\\s+بن\\s+علي(?!\\s+العسكري)|ابي\\s+محمد\\s+الحسن(?!\\s+العسكري)'), 'Imam al-Hasan'],
  [new RegExp('زين\\s+العابدين|علي\\s+بن\\s+الحسين|السجاد'), 'Imam Zayn al-Abidin'],
  [new RegExp('فاطمة(?:\\s+الزهراء)?|الزهراء'), 'Fatima al-Zahra'],
  [new RegExp('زيد\\s+بن\\s+علي'), 'Zayd ibn Ali'],
  [
    new RegExp(
      'امير\\s+المؤمنين|علي\\s+بن\\s+ابي\\s+طالب|قال\\s+علي' +
        WB_TRAIL +
        '|عن\\s+علي' +
        WB_TRAIL,
      'u'
    ),
    'Imam Ali',
  ],
];

// Generic Ahl al-Bayt phrasing when a specific Imam can't be pinned down.
const _AHL_BAYT_RE = new RegExp('عن\\s+ابائه|اهل\\s+البيت|عليهم\\s+السلام|عليه\\s+السلام');

// Successor (Tabi'i) self-statement cue, Sunni context.
const _MAQTU_RE = new RegExp('عن\\s+(?:الحسن|مجاهد|عطاء|قتادة|الزهري|ابراهيم\\s+النخعي)\\s+قال');

// Musnad Zayd: "حدثني زيد بن علي عن أبيه عن جده عن علي" is the *isnad opener*
// (Zayd is the narrator, not the speaker). The terminus is decided by where
// the matn stops — at the Prophet, at Imam Ali, or at Zayd's own fiqh ruling.
const _ZAYDI_OPENER_RE = new RegExp(
  'حدثني\\s+زيد\\s+بن\\s+علي\\s+عن\\s+ابيه\\s+عن\\s+جده\\s+عن\\s+علي' +
    '|زيد\\s+بن\\s+علي\\s+عن\\s+ابائه',
  'g'
);
// Zayd ibn Ali speaking in his own juristic voice (not as isnad link).
const _ZAYD_SPEAKER_RE = new RegExp('(?:^|\\s|\\.)\\(?\\s*(?:و)?قال\\s+زيد\\s+بن\\s+علي');
// Imam Ali as the terminal speaker (the saying stops at Ali). Covers the
// Musnad Zayd chain tails "عن (جده) علي بن ابي طالب ... قال" and a bare
// "قال علي" / "امير المؤمنين", where no Prophet attribution follows.
const _ALI_SPEAKER_RE = new RegExp(
  'علي\\s+بن\\s+ابي\\s+طالب[^.؟!]*?قال' +
    '|عن\\s+علي' +
    WB_TRAIL +
    '[^.؟!]*?قال' +
    '|قال\\s+علي' +
    WB_TRAIL +
    '|امير\\s+المؤمنين',
  'u'
);

// Sunni/Ibadi named-Companion speaker cue (port of the inline Python regex in
// the final non-Prophet branch).
const _COMPANION_SPEAKER_RE = new RegExp(
  'قال\\s+(?:عمر|ابو\\s+بكر|عثمان|ابن\\s+عباس|ابن\\s+مسعود|عائشة)' + WB_TRAIL,
  'u'
);

export type NarrationLevel = 'marfu' | 'imam' | 'mawquf' | 'maqtu' | 'unknown';

export interface AttributionResult {
  attributed_to: string;
  narration_level: NarrationLevel;
}

/**
 * Faithful port of classify_attribution.classify().
 *
 * Resolution order (Prophet always wins over an Imam in the chain):
 *   1. Prophet markers           → marfu
 *   2. Hadith qudsi              → marfu (qudsi)
 *   3. Specific Imam markers     → imam (Shia traditions)
 *   4. Ahl al-Bayt, no specific  → imam / Ahl al-Bayt
 *   5. Sunni Companion stop      → mawquf
 *   6. Successor self-statement  → maqtu
 *   7. otherwise                 → unknown
 */
export function classify(
  text_ar: string | null | undefined,
  sanad: string | string[] | null | undefined = null,
  tradition = '',
  source = ''
): AttributionResult {
  const text = norm(text_ar || '');
  const sanadStr = sanad == null ? '' : Array.isArray(sanad) ? sanad.join(' ') : String(sanad);
  const sanad_blob = norm(sanadStr);

  // Prophet attribution always wins (an Imam may merely be a chain link).
  if (_PROPHET_RE.test(text)) {
    if (_QUDSI_RE.test(text)) return { attributed_to: 'Prophet Muhammad (qudsi)', narration_level: 'marfu' };
    return { attributed_to: 'Prophet Muhammad', narration_level: 'marfu' };
  }
  if (_QUDSI_RE.test(text)) return { attributed_to: 'Prophet Muhammad (qudsi)', narration_level: 'marfu' };

  const is_zaydi = tradition === 'Zaydi' || source.includes('Zayd');
  const is_imami = tradition === 'Imami' || source.includes('Rida');

  // ── Zaydi Musnad Zayd: resolve the matn terminus, not the isnad opener ──
  if (is_zaydi) {
    // Strip the standard isnad opener so "زيد بن علي" in the chain head
    // isn't mistaken for the speaker.
    const matn = text.replace(_ZAYDI_OPENER_RE, '');
    if (_ZAYD_SPEAKER_RE.test(matn)) return { attributed_to: 'Zayd ibn Ali', narration_level: 'imam' };
    if (_ALI_SPEAKER_RE.test(text)) return { attributed_to: 'Imam Ali', narration_level: 'imam' };
    for (const [rx, name] of _IMAM_MARKERS) {
      if (name === 'Imam Ali' || name === 'Zayd ibn Ali') continue;
      if (rx.test(matn)) return { attributed_to: name, narration_level: 'imam' };
    }
    if (_AHL_BAYT_RE.test(text)) return { attributed_to: 'Ahl al-Bayt', narration_level: 'imam' };
    return { attributed_to: 'unknown', narration_level: 'unknown' };
  }

  // ── Imami (Twelver) and Musnad al-Rida ──
  if (is_imami) {
    for (const [rx, name] of _IMAM_MARKERS) {
      if (rx.test(text) || rx.test(sanad_blob)) return { attributed_to: name, narration_level: 'imam' };
    }
    if (_AHL_BAYT_RE.test(text)) return { attributed_to: 'Ahl al-Bayt', narration_level: 'imam' };
    return { attributed_to: 'unknown', narration_level: 'unknown' };
  }

  // ── Sunni / Ibadi: no Shia Imams; non-Prophet → Companion/Successor ──
  if (_MAQTU_RE.test(text)) return { attributed_to: 'Successor', narration_level: 'maqtu' };
  // A clearly attributed non-Prophet saying by a named early authority is a
  // Companion statement (mawquf) in Sunni/Ibadi usul — never a Shia Imam.
  if (_ALI_SPEAKER_RE.test(text) || _COMPANION_SPEAKER_RE.test(text))
    return { attributed_to: 'Companion', narration_level: 'mawquf' };

  return { attributed_to: 'unknown', narration_level: 'unknown' };
}
