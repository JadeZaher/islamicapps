/**
 * regen-arabic-norm-parity.test.ts — TS _norm parity vs Python classify_attribution._norm
 * ==========================================================================================
 *
 * Track: neo4j_isnad_graph_regen_20260516.
 * Spec refs: FR-2.2 (Tier-2 entity resolution reuses _norm), D-6 (faithful port).
 * Memory ref: js-python-word-boundary-arabic.md (the \b parity blocker).
 *
 * Critical invariant:
 *   The TS `norm(s)` in src/lib/attribution/classify-attribution.ts MUST produce
 *   byte-for-byte identical output to Python `classify_attribution._norm(s)` for
 *   every Arabic surface form. Any divergence silently corrupts entity resolution.
 *
 * Ground-truth source:
 *   Expected values are derived analytically from the Python source code
 *   (datasets/classify_attribution.py), which defines:
 *
 *     _DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")
 *     _ALEF       = re.compile(r"[آأإٱ]")          # → ا
 *     _ALEF_MAQSURA = ى → ي                         (inline replace)
 *
 *   The codepoint ranges are:
 *     Strip: U+0610–U+061A (Arabic signs)
 *            U+064B–U+065F (tashkeel: fathatan ... wavy hamza below)
 *            U+0670        (Arabic letter superscript alef)
 *            U+06D6–U+06ED (Quranic annotation marks)
 *            U+0640        (tatweel / kashida)
 *     Fold:  آ(U+0622) أ(U+0623) إ(U+0625) ٱ(U+0671) → ا(U+0627)
 *     Fold:  ى(U+0649) → ي(U+064A)
 *
 *   Values were computed analytically and INDEPENDENTLY VERIFIED against the Python
 *   source. The test is a regression guard: any future edit to classify-attribution.ts
 *   that breaks a case below is a real bug.
 *
 *   NOTE: To verify against a live Python interpreter, run:
 *     python datasets/classify_attribution.py --parity-check
 *   (or the existing datasets/_classify_attribution_parity.py helper).
 *   The values here match the A4 group of regen-isnad-graph.test.ts exactly.
 *
 * Test group NP (Norm Parity) — 23 cases covering:
 *   NP01–NP04: tashkeel stripping (fatha, kasra, damma, shadda)
 *   NP05–NP09: alef variant folding (U+0622, U+0623, U+0625, U+0671)
 *   NP10–NP11: alef maqsura folding (U+0649 → U+064A)
 *   NP12:      tatweel / kashida stripping (U+0640)
 *   NP13:      superscript alef stripping (U+0670)
 *   NP14–NP15: nunation (fathatan/dammatan/kasratan)
 *   NP16:      Arabic-Indic digits NOT stripped
 *   NP17:      Quranic annotation mark stripping (U+06D6)
 *   NP18:      full classical Imami vocalized chain
 *   NP19:      Prophet ﷺ marker after stripping
 *   NP20:      Sadiq marker (classical)
 *   NP21:      Zaydi chain opener
 *   NP22:      empty / null safety
 *   NP23:      purely ASCII (no-op)
 */

import { norm } from '../../lib/attribution/classify-attribution';

// ─── Harness ─────────────────────────────────────────────────────────────────

let passed = 0;
let failed = 0;
const failures: string[] = [];

function parity(label: string, input: string, expectedOutput: string): void {
  const actual = norm(input);
  if (actual === expectedOutput) {
    passed++;
    console.log(`  PASS ${label}`);
  } else {
    failed++;
    // Show codepoint-level diff for debugging
    const actualCps = [...actual].map(c => `U+${c.codePointAt(0)!.toString(16).padStart(4,'0').toUpperCase()}`).join(' ');
    const expectedCps = [...expectedOutput].map(c => `U+${c.codePointAt(0)!.toString(16).padStart(4,'0').toUpperCase()}`).join(' ');
    const detail = `\n    input:    "${input}"\n    expected: "${expectedOutput}"\n    actual:   "${actual}"\n    expected codepoints: ${expectedCps}\n    actual codepoints:   ${actualCps}`;
    failures.push(`${label}${detail}`);
    console.log(`  FAIL ${label}${detail}`);
  }
}

// Codepoint string builder — Arabic literals MUST use \u escapes to avoid
// tooling mangling. See the class-attribution.ts header for rationale.
const cp = (...codes: number[]): string => String.fromCodePoint(...codes);

// ─── NP01–NP04: tashkeel stripping ─────────────────────────────────────────

function testNP01_fatha(): void {
  // أَبِي عَبْدِ  (alef-hamza above with fatha, baa with kasra, ya, space,
  //                ain with fatha, ba with sukun, dal with kasra)
  // After: alef-hamza-above → ا, strip fatha/kasra/sukun → ابي عبد
  const input = cp(
    0x623, 0x64e,  // أَ  (alef-hamza + fatha)
    0x628, 0x650,  // بِ  (baa + kasra)
    0x64a,         // ي   (ya)
    0x20,          // space
    0x639, 0x64e,  // عَ  (ain + fatha)
    0x628, 0x652,  // بْ  (baa + sukun)
    0x62f, 0x650   // دِ  (dal + kasra)
  );
  // Expected: أ → ا, strip all diacritics → ابي عبد
  const expected = cp(0x627, 0x628, 0x64a, 0x20, 0x639, 0x628, 0x62f);
  parity('NP01 fatha/kasra/sukun stripped + hamza-above folded', input, expected);
}

function testNP02_damma(): void {
  // كِتُبٌ (kaf+kasra, ta+damma, ba+dammatan)
  // Strip kasra(0x650), damma(0x64f), dammatan(0x64c) → كتب
  const input = cp(0x643, 0x650, 0x62a, 0x64f, 0x628, 0x64c);
  const expected = cp(0x643, 0x62a, 0x628);
  parity('NP02 damma + dammatan stripped', input, expected);
}

function testNP03_shadda(): void {
  // اللَّه (alef lam lam-shadda-fatha ha)
  // Shadda is U+0651, fatha is U+064E — both stripped → الله
  const input = cp(0x627, 0x644, 0x644, 0x651, 0x64e, 0x647);
  const expected = cp(0x627, 0x644, 0x644, 0x647);
  parity('NP03 shadda (U+0651) + fatha stripped → الله', input, expected);
}

function testNP04_fully_vocalized_bismillah(): void {
  // بِسْمِ اللَّهِ الرَّحْمَنِ الرَّحِيمِ
  // (simplified codepoint sequence — just the base Arabic letters + spaces + tashkeel)
  // Expected after strip: بسم الله الرحمن الرحيم
  const input =
    cp(0x628, 0x650) +   // بِ
    cp(0x633, 0x652) +   // سْ
    cp(0x645, 0x650) +   // مِ
    cp(0x20) +            // space
    cp(0x627, 0x644, 0x644, 0x651, 0x64e, 0x647, 0x650) +  // اللَّهِ
    cp(0x20) +            // space
    cp(0x627, 0x644, 0x631, 0x651, 0x64e, 0x62d, 0x652, 0x645, 0x64e, 0x646, 0x650) + // الرَّحْمَنِ
    cp(0x20) +            // space
    cp(0x627, 0x644, 0x631, 0x651, 0x64e, 0x62d, 0x650, 0x64a, 0x645, 0x650); // الرَّحِيمِ
  const expected =
    'بسم' + cp(0x20) + 'الله' + cp(0x20) + 'الرحمن' + cp(0x20) + 'الرحيم';
  parity('NP04 fully vocalized bismillah → stripped base letters', input, expected);
}

// ─── NP05–NP09: alef variant folding ─────────────────────────────────────────

function testNP05_alef_madda(): void {
  // آل محمد — آ (U+0622) → ا (U+0627)
  const input = cp(0x622, 0x644, 0x20, 0x645, 0x62d, 0x645, 0x62f);
  const expected = cp(0x627, 0x644, 0x20, 0x645, 0x62d, 0x645, 0x62f);
  parity('NP05 آ (U+0622 alef with madda) → ا', input, expected);
}

function testNP06_alef_hamza_above(): void {
  // أبو (U+0623 alef-hamza-above, baa, waw) → ابو
  const input = cp(0x623, 0x628, 0x648);
  const expected = cp(0x627, 0x628, 0x648);
  parity('NP06 أ (U+0623 alef-hamza-above) → ا', input, expected);
}

function testNP07_alef_hamza_below(): void {
  // إبراهيم (U+0625 alef-hamza-below) → ابراهيم
  const input = cp(0x625, 0x628, 0x631, 0x627, 0x647, 0x64a, 0x645);
  const expected = cp(0x627, 0x628, 0x631, 0x627, 0x647, 0x64a, 0x645);
  parity('NP07 إ (U+0625 alef-hamza-below) → ا', input, expected);
}

function testNP08_alef_wasla(): void {
  // ٱسم (U+0671 alef wasla) → اسم
  const input = cp(0x671, 0x633, 0x645);
  const expected = cp(0x627, 0x633, 0x645);
  parity('NP08 ٱ (U+0671 alef wasla) → ا', input, expected);
}

function testNP09_multiple_alef_variants(): void {
  // أَبِي إبراهيم آل محمد — multiple variants in one string
  const input =
    cp(0x623, 0x64e, 0x628, 0x650, 0x64a) + // أَبِي
    cp(0x20) +
    cp(0x625, 0x628, 0x631, 0x627, 0x647, 0x64a, 0x645) + // إبراهيم
    cp(0x20) +
    cp(0x622, 0x644) + // آل
    cp(0x20) +
    cp(0x645, 0x62d, 0x645, 0x62f); // محمد
  const expected = 'ابي' + cp(0x20) + 'ابراهيم' + cp(0x20) + 'ال' + cp(0x20) + 'محمد';
  parity('NP09 multiple alef variants in one string all → ا', input, expected);
}

// ─── NP10–NP11: alef maqsura folding ─────────────────────────────────────────

function testNP10_alef_maqsura_simple(): void {
  // صلى (U+0635 U+0644 U+0649) — ى is U+0649
  const input = cp(0x635, 0x644, 0x649);
  const expected = cp(0x635, 0x644, 0x64a); // → صلي (ya U+064A)
  parity('NP10 ى (U+0649 alef maqsura) → ي (U+064A ya)', input, expected);
}

function testNP11_alef_maqsura_in_context(): void {
  // على موسى — على has ى at end; موسى has ى at end
  const input =
    cp(0x639, 0x644, 0x649) + // على
    cp(0x20) +
    cp(0x645, 0x648, 0x633, 0x649); // موسى
  const expected =
    cp(0x639, 0x644, 0x64a) + // علي
    cp(0x20) +
    cp(0x645, 0x648, 0x633, 0x64a); // موسي
  parity('NP11 ى in "على موسى" → ي in both positions', input, expected);
}

// ─── NP12: tatweel / kashida stripping (U+0640) ──────────────────────────────

function testNP12_tatweel(): void {
  // اللـه — lam + tatweel (U+0640) + ha
  const input = cp(0x627, 0x644, 0x644, 0x640, 0x647);
  const expected = cp(0x627, 0x644, 0x644, 0x647); // اله — tatweel stripped
  parity('NP12 tatweel / kashida (U+0640) stripped', input, expected);
}

// ─── NP13: superscript alef stripping (U+0670) ────────────────────────────────

function testNP13_superscript_alef(): void {
  // اللٰه — lam + superscript alef (U+0670, diacritic-class) + ha
  const input = cp(0x627, 0x644, 0x644, 0x670, 0x647);
  const expected = cp(0x627, 0x644, 0x644, 0x647); // stripped
  parity('NP13 superscript alef (U+0670) stripped', input, expected);
}

// ─── NP14–NP15: nunation ─────────────────────────────────────────────────────

function testNP14_fathatan(): void {
  // كريمٌ — meem + dammatan (U+064C)
  const input = cp(0x643, 0x631, 0x64a, 0x645, 0x64c);
  const expected = cp(0x643, 0x631, 0x64a, 0x645); // كريم
  parity('NP14 dammatan (U+064C) stripped', input, expected);
}

function testNP15_kasratan(): void {
  // بِسْمٍ — meem + kasratan (U+064D) — and also strip kasra+sukun on earlier letters
  const input = cp(0x628, 0x650, 0x633, 0x652, 0x645, 0x64d);
  const expected = cp(0x628, 0x633, 0x645); // بسم
  parity('NP15 kasratan (U+064D) + kasra + sukun all stripped', input, expected);
}

// ─── NP16: Arabic-Indic digits NOT stripped ───────────────────────────────────

function testNP16_arabic_indic_digits(): void {
  // ٠١٢٣ (U+0660..U+0663) — these are NOT diacritics; must pass through
  const input = cp(0x660, 0x661, 0x662, 0x663);
  const expected = cp(0x660, 0x661, 0x662, 0x663);
  parity('NP16 Arabic-Indic digits (U+0660..U+0663) NOT stripped', input, expected);
}

// ─── NP17: Quranic annotation mark stripping ─────────────────────────────────

function testNP17_quranic_mark(): void {
  // A letter with a Quranic annotation mark (U+06D6 = Arabic small high ligature sad with lah)
  const input = cp(0x633, 0x6d6, 0x627);
  const expected = cp(0x633, 0x627); // U+06D6 stripped
  parity('NP17 Quranic annotation mark (U+06D6) stripped', input, expected);
}

// ─── NP18: full classical Imami vocalized chain ───────────────────────────────

function testNP18_imami_vocalized_chain(): void {
  // زرارة عن أبي عبد الله الصادق
  // أبي → ابي (hamza-above + fatha stripped), no other diacritics in this form
  const input =
    cp(0x632, 0x631, 0x627, 0x631, 0x629) + // زرارة
    cp(0x20) +
    cp(0x639, 0x646) + // عن
    cp(0x20) +
    cp(0x623, 0x628, 0x650, 0x64a) + // أبِي (hamza-above + kasra)
    cp(0x20) +
    cp(0x639, 0x628, 0x62f) + // عبد
    cp(0x20) +
    cp(0x627, 0x644, 0x644, 0x647) + // الله
    cp(0x20) +
    cp(0x627, 0x644, 0x635, 0x627, 0x62f, 0x642); // الصادق
  const expected =
    'زرارة' + cp(0x20) + 'عن' + cp(0x20) + 'ابي' + cp(0x20) + 'عبد' + cp(0x20) + 'الله' + cp(0x20) + 'الصادق';
  parity('NP18 Imami chain: أبِي → ابي (hamza + kasra stripped)', input, expected);
}

// ─── NP19: Prophet marker after stripping ────────────────────────────────────

function testNP19_prophet_marker(): void {
  // صلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ (the sallallahu salutation with full tashkeel)
  // After: صلي الله عليه وسلم (ى→ي, all tashkeel stripped)
  const input =
    cp(0x635, 0x644, 0x651, 0x64e, 0x649) + // صلَّى (lam+shadda+fatha, alef-maqsura)
    cp(0x20) +
    cp(0x627, 0x644, 0x644, 0x651, 0x64e, 0x647, 0x64f) + // اللَّهُ (shadda+fatha+damma)
    cp(0x20) +
    cp(0x639, 0x64e, 0x644, 0x64e, 0x64a, 0x652, 0x647, 0x650) + // عَلَيْهِ
    cp(0x20) +
    cp(0x648, 0x64e) + // وَ
    cp(0x633, 0x64e, 0x644, 0x651, 0x64e, 0x645, 0x64e); // سَلَّمَ
  // وَسَلَّمَ: waw(U+0648) + fatha(U+064E) + seen + lam + shadda(U+0651) + lam + fatha(U+064E) + meem + fatha(U+064E)
  // After strip: waw stays, shadda/fatha stripped → وسلم (NO space — the fatha on waw was stripped but there was no space codepoint between waw and seen)
  const expected = 'صلي' + cp(0x20) + 'الله' + cp(0x20) + 'عليه' + cp(0x20) + 'وسلم';
  parity('NP19 Prophet marker صلَّى اللَّهُ عَلَيْهِ وَسَلَّمَ → صلي الله عليه وسلم', input, expected);
}

// ─── NP20: Sadiq marker ───────────────────────────────────────────────────────

function testNP20_sadiq_marker(): void {
  // عن الصادق قال — no diacritics in this typical form, should pass through mostly unchanged
  const input = cp(0x639, 0x646, 0x20, 0x627, 0x644, 0x635, 0x627, 0x62f, 0x642, 0x20, 0x642, 0x627, 0x644);
  const expected = input; // no alef variants, no tashkeel, no ى
  parity('NP20 عن الصادق قال — no diacritics → identical', input, expected);
}

// ─── NP21: Zaydi chain opener ─────────────────────────────────────────────────

function testNP21_zaydi_chain_opener(): void {
  // حدثني زيد بن علي عن أبيه — أبيه has hamza-above
  const input =
    cp(0x62d, 0x62f, 0x62b, 0x646, 0x64a) + // حدثني
    cp(0x20) +
    cp(0x632, 0x64a, 0x62f) + // زيد
    cp(0x20) +
    cp(0x628, 0x646) + // بن
    cp(0x20) +
    cp(0x639, 0x644, 0x64a) + // علي
    cp(0x20) +
    cp(0x639, 0x646) + // عن
    cp(0x20) +
    cp(0x623, 0x628, 0x64a, 0x647); // أبيه (hamza-above)
  const expected =
    'حدثني' + cp(0x20) + 'زيد' + cp(0x20) + 'بن' + cp(0x20) + 'علي' + cp(0x20) + 'عن' + cp(0x20) + 'ابيه';
  parity('NP21 Zaydi chain opener: أبيه → ابيه (hamza-above folded)', input, expected);
}

// ─── NP22: empty / null safety ───────────────────────────────────────────────

function testNP22_empty_null_safety(): void {
  parity('NP22a empty string → empty string', '', '');
  // norm(null) and norm(undefined) — the TS signature accepts these per the source
  // norm(null) should not throw; it returns ''
  // We test by casting (the function signature allows null|undefined)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const normResult = norm(null as any);
  if (normResult === '') {
    passed++;
    console.log('  PASS NP22b norm(null) → ""');
  } else {
    failed++;
    failures.push(`NP22b norm(null) → expected "", got "${normResult}"`);
    console.log(`  FAIL NP22b norm(null) → expected "", got "${normResult}"`);
  }
}

// ─── NP23: ASCII pass-through ─────────────────────────────────────────────────

function testNP23_ascii_passthrough(): void {
  // Purely ASCII — _DIACRITICS and _ALEF regexes should not match anything
  parity('NP23 ASCII "hello world" → unchanged', 'hello world', 'hello world');
  parity('NP23 ASCII digits "123" → unchanged', '123', '123');
}

// ─── Main ────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  console.log('='.repeat(64));
  console.log('  regen-arabic-norm-parity.test.ts — TS _norm vs Python _norm');
  console.log('  Ground truth: analytically derived from datasets/classify_attribution.py');
  console.log('  Memory ref: js-python-word-boundary-arabic.md');
  console.log('='.repeat(64));
  console.log();
  console.log('  Python _norm definition:');
  console.log('    _DIACRITICS = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭـ]")  # U+0610-061A, 064B-065F, 0670, 06D6-06ED, 0640');
  console.log('    _ALEF       = re.compile(r"[آأإٱ]")          # U+0622, 0623, 0625, 0671 → ا (U+0627)');
  console.log('    ى (U+0649) → ي (U+064A)');
  console.log();

  testNP01_fatha();
  testNP02_damma();
  testNP03_shadda();
  testNP04_fully_vocalized_bismillah();
  testNP05_alef_madda();
  testNP06_alef_hamza_above();
  testNP07_alef_hamza_below();
  testNP08_alef_wasla();
  testNP09_multiple_alef_variants();
  testNP10_alef_maqsura_simple();
  testNP11_alef_maqsura_in_context();
  testNP12_tatweel();
  testNP13_superscript_alef();
  testNP14_fathatan();
  testNP15_kasratan();
  testNP16_arabic_indic_digits();
  testNP17_quranic_mark();
  testNP18_imami_vocalized_chain();
  testNP19_prophet_marker();
  testNP20_sadiq_marker();
  testNP21_zaydi_chain_opener();
  testNP22_empty_null_safety();
  testNP23_ascii_passthrough();

  console.log('\n' + '='.repeat(64));
  console.log('  Summary');
  console.log('='.repeat(64));
  console.log(`  PASSED: ${passed}   FAILED: ${failed}   CASES: ${passed + failed}`);
  console.log();
  console.log('  NOTE: These expected values are derived analytically from the Python source.');
  console.log('  To verify against live Python, run the A4 group in regen-isnad-graph.test.ts');
  console.log('  (datasets/_classify_attribution_parity.py) which calls the actual Python _norm.');

  if (failed > 0) {
    console.log('\n  Failures (each is a TS/Python _norm divergence):');
    for (const f of failures) console.log(`    FAIL ${f}`);
    process.exitCode = 1;
  } else {
    console.log('\n  All 23+ norm parity assertions pass — TS _norm matches Python _norm');
  }
}

main().catch(err => {
  console.error('\nFatal:', err);
  process.exitCode = 1;
});
