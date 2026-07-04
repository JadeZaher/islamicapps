"""
Phase 0 / T-0.2, T-0.3, T-0.4 audits for uniform_isnad_extraction_20260609.

T-0.2 — Sample lone ح inside text_ar that does NOT match the taḥwīl-context
        regex (i.e., false-positive risk audit — are there cases where lone
        ح in a quoted matn was missed by our detector, or worse, would have
        been over-matched by a naive detector?).

T-0.3 — Pull 50 of the 1-ح Sahih Muslim rows and run a quick convergence
        analysis: split the text on ح + look at narrator overlap between
        the two branches. Calibration set for FR-1.1 step 3 heuristic.

T-0.4 — Probe Thaqalayn arabicText (via the v2_books JSONs we already
        surveyed on 2026-06-05) — confirm classical isnad grammar (حدثنا /
        أخبرنا / عن) is present, and check diacritization vs the existing
        _norm function.
"""
from __future__ import annotations
import csv
import glob
import json
import os
import re
import sys

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

BASE = os.path.dirname(os.path.abspath(__file__))
UNIFIED = os.path.join(BASE, 'all_hadiths_unified.csv')
SHIA_BOOKS = os.path.join(BASE, 'shia-hadith', 'v2_books')
OUT_DIR = os.path.normpath(os.path.join(BASE, '..', '..', '.omc', 'research', 'uniform-isnad'))
OUT_MD = os.path.join(OUT_DIR, 'phase0-misc-audits.md')

# Same taḥwīl detector as T-0.1
TAHWEEL_RE = re.compile(
    r'(?:^|[\s،.])ح\s+و?(?:حدثنا|حدثني|أخبرنا|أخبرني|أنبأنا|أنبأني|ثنا|نا)',
)
# Lone ح with NO verb context — for T-0.2 false-positive sampling
LONE_HEH_RE = re.compile(r'(?:^|[\s،.])ح(?:[\s،.]|$)')

# Bring in the existing classical isnad cleaners + _norm if available
sys.path.insert(0, BASE)
try:
    # _norm is in classify_attribution.py at datasets/ root
    sys.path.insert(0, os.path.normpath(os.path.join(BASE, '..')))
    from classify_attribution import _norm  # noqa
except Exception as e:
    print(f'WARN: could not import _norm: {e}', file=sys.stderr)
    _norm = lambda s: s


def t02_false_positive_audit() -> list[dict]:
    """Find rows where the simple lone-ح regex matches but the taḥwīl regex doesn't.

    Those are 'lone ح in quoted matn or word' — our regex correctly skipped
    them. Sample 10 to confirm the detector isn't over-restrictive.
    """
    samples = []
    with open(UNIFIED, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            text_ar = (row.get('text_ar') or '').strip()
            if not text_ar:
                continue
            lone_count = len(LONE_HEH_RE.findall(text_ar))
            verb_count = len(TAHWEEL_RE.findall(text_ar))
            if lone_count > 0 and verb_count == 0:
                samples.append({
                    'source': row.get('source', '').strip(),
                    'hadith_no': row.get('hadith_no', '').strip(),
                    'lone_count': lone_count,
                    'snippet': text_ar[:200].replace('\n', ' '),
                })
                if len(samples) >= 10:
                    break
    return samples


def t03_convergence_calibration(target: int = 50) -> dict:
    """For each 1-ح Sahih Muslim row, split on the ح position and look for
    narrator overlap between the two raw text segments.

    Approach (rough, just for calibration — Phase 1 will be precise):
      1. Find the ح splitter position.
      2. Take the pre-ح text and the post-ح text as two raw chains.
      3. Strip honorifics + punct.
      4. Tokenise on حدثنا|أخبرنا|عن|قال (the existing _CHAIN_VERB_SPLIT
         family).
      5. Find overlapping tokens (any contiguous sequence of ≥2 Arabic words
         that appears in both segments).
      6. Report: how many rows have ≥1 overlap, what's the median segment-
         length overlap, are there any rows with zero overlap (which would
         mean the algorithm needs a no-convergence fallback per spec).
    """
    rows_examined = 0
    rows_with_overlap = 0
    rows_no_overlap = 0
    overlap_token_counts = []
    no_overlap_samples = []

    # Reuse the cleaners
    _PUNCT = re.compile(r'[،,.:؛!؟"\'\(\)\[\]‏‎]+')
    _HONORIFIC = re.compile(
        r'\s*رض[ىي]\s*الله\s*عنه?[امه]*\s*'
        r'|\s*رحمه\s*الله\s*'
        r'|\s*عليه\s*السلام\s*'
        r'|\s*صلى\s*الله\s*عليه\s*(?:وآله\s*)?وسلم\s*'
        r'|\s*أم\s+المؤمنين\s*'
    )
    _CHAIN_VERB = re.compile(r'حدثنا|حدثني|أخبرنا|أخبرني|أنبأنا|أنبأني|ثنا|نا|عن|قال')

    def clean(s: str) -> str:
        s = _HONORIFIC.sub(' ', s)
        s = _PUNCT.sub(' ', s)
        return re.sub(r'\s+', ' ', s).strip()

    def tokenize_segments(s: str) -> list[str]:
        # Split on verbs, return non-empty trimmed segments
        return [p.strip() for p in _CHAIN_VERB.split(s) if p.strip()]

    with open(UNIFIED, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            if row.get('source', '').strip() != 'Sahih Muslim':
                continue
            text_ar = (row.get('text_ar') or '').strip()
            if not text_ar:
                continue
            matches = list(TAHWEEL_RE.finditer(text_ar))
            if len(matches) != 1:
                continue
            rows_examined += 1
            split_pos = matches[0].start()
            pre = clean(text_ar[:split_pos])
            post = clean(text_ar[split_pos + 1:])
            pre_segs = tokenize_segments(pre)
            post_segs = tokenize_segments(post)

            pre_set = set(_norm(s) for s in pre_segs if len(s) > 3)
            post_set = set(_norm(s) for s in post_segs if len(s) > 3)
            overlap = pre_set & post_set
            if overlap:
                rows_with_overlap += 1
                overlap_token_counts.append(len(overlap))
            else:
                rows_no_overlap += 1
                if len(no_overlap_samples) < 5:
                    no_overlap_samples.append({
                        'hadith_no': row.get('hadith_no', '').strip(),
                        'pre_segs': pre_segs[:5],
                        'post_segs': post_segs[:5],
                    })
            if rows_examined >= target:
                break

    return {
        'rows_examined': rows_examined,
        'rows_with_overlap': rows_with_overlap,
        'rows_no_overlap': rows_no_overlap,
        'median_overlap_count': sorted(overlap_token_counts)[len(overlap_token_counts) // 2] if overlap_token_counts else 0,
        'no_overlap_samples': no_overlap_samples,
    }


def t04_thaqalayn_arabic_probe() -> dict:
    """Probe Thaqalayn v2_books arabicText for classical isnad grammar +
    diacritization sensitivity of _norm."""
    pattern = os.path.join(SHIA_BOOKS, '*.json')
    files = sorted(glob.glob(pattern))
    samples = []
    isnad_grammar_hits = 0
    total_arabic = 0
    diacritic_re = re.compile(r'[ً-ٰٟ]')  # Arabic diacritics
    grammar_re = re.compile(r'حدثنا|حدثني|أخبرنا|أنبأنا|عَنْ|عَن')
    for f in files:
        if os.path.basename(f) == 'BookNames.json':
            continue
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except Exception:
            continue
        for entry in data:
            arabic = entry.get('arabicText', '') or ''
            if not arabic.strip():
                continue
            total_arabic += 1
            has_grammar = bool(grammar_re.search(arabic))
            if has_grammar:
                isnad_grammar_hits += 1
            if len(samples) < 5 and has_grammar:
                diacritized = bool(diacritic_re.search(arabic[:200]))
                norm_input = arabic[:150]
                norm_output = _norm(norm_input)
                samples.append({
                    'book': entry.get('book', '?'),
                    'id': entry.get('id', '?'),
                    'first_200_chars': arabic[:200],
                    'has_diacritics_in_first_200': diacritized,
                    'norm_strips_diacritics_correctly': norm_input != norm_output,
                })
        if total_arabic > 1000:
            break  # enough sampled
    return {
        'sampled_rows': total_arabic,
        'with_isnad_grammar': isnad_grammar_hits,
        'pct_with_grammar': f'{100 * isnad_grammar_hits / max(total_arabic, 1):.1f}%',
        'samples': samples,
    }


def main() -> int:
    os.makedirs(OUT_DIR, exist_ok=True)
    print('Running T-0.2 false-positive audit...')
    t02 = t02_false_positive_audit()
    print(f'  {len(t02)} samples found')
    print('Running T-0.3 convergence calibration...')
    t03 = t03_convergence_calibration()
    print(f'  examined {t03["rows_examined"]} rows; overlap={t03["rows_with_overlap"]} none={t03["rows_no_overlap"]}')
    print('Running T-0.4 Thaqalayn arabicText probe...')
    t04 = t04_thaqalayn_arabic_probe()
    print(f'  {t04["with_isnad_grammar"]}/{t04["sampled_rows"]} rows have isnad grammar')

    lines = [
        '# Phase 0 misc audits (T-0.2 / T-0.3 / T-0.4)',
        '',
        f'Generated: {__import__("datetime").datetime.utcnow().isoformat()}Z',
        '',
        '## T-0.2 — Lone ح false-positive risk',
        '',
        f'Found {len(t02)} sample rows where a lone ح appears in text_ar but is NOT ',
        'preceded by transmission-verb context (the taḥwīl detector correctly skipped them). ',
        'Each row\'s lone-ح count, source, hadith_no, and a 200-char snippet:',
        '',
        '| Source | hadith_no | lone_ح count | first 200 chars |',
        '|---|---|---:|---|',
    ]
    for s in t02:
        lines.append(f'| {s["source"]} | {s["hadith_no"]} | {s["lone_count"]} | `{s["snippet"]}` |')
    lines.extend([
        '',
        'Interpretation: if these snippets show lone ح as part of an Arabic word, in the matn, ',
        'or in narrative text (NOT as an isnad splitter), the detector is correctly conservative. ',
        'If any sample shows what looks like a real taḥwīl splitter that the detector missed, ',
        'we need to broaden the regex.',
        '',
        '## T-0.3 — Convergence-narrator calibration (Sahih Muslim 1-ح subset)',
        '',
        f'Examined: **{t03["rows_examined"]}** 1-ح rows from Sahih Muslim',
        f'Rows with detectable token overlap between pre-ح and post-ح segments: **{t03["rows_with_overlap"]}**',
        f'Rows with NO overlap (need no-stitch fallback per FR-1.1 step 3 last bullet): **{t03["rows_no_overlap"]}**',
        f'Median overlapping-token count in overlap rows: **{t03["median_overlap_count"]}**',
        '',
        'Decision feedback:',
        f'- If overlap rate > 95%: stitch is the dominant case; no-stitch fallback rare and OK.',
        f'- If overlap rate < 80%: stitch detection needs more robust token matching (perhaps trigram or LCS).',
        f'- Observed: **{100 * t03["rows_with_overlap"] / max(t03["rows_examined"], 1):.1f}%** overlap rate.',
        '',
    ])
    if t03['no_overlap_samples']:
        lines.append('No-overlap sample rows (Hadith # + first 5 segs each side):')
        lines.append('')
        for sample in t03['no_overlap_samples']:
            lines.append(f'- Muslim #{sample["hadith_no"]}: pre={sample["pre_segs"]}; post={sample["post_segs"]}')
        lines.append('')
    lines.extend([
        '## T-0.4 — Thaqalayn arabicText probe',
        '',
        f'Sampled: {t04["sampled_rows"]:,} rows across v2_books JSONs (cap 1,000)',
        f'With classical isnad grammar (حدثنا/أخبرنا/أنبأنا/عَن): **{t04["with_isnad_grammar"]:,}** ({t04["pct_with_grammar"]})',
        '',
        'Sample rows:',
        '',
    ])
    for s in t04['samples']:
        lines.append(f'- **{s["book"]} #{s["id"]}** diacritized={s["has_diacritics_in_first_200"]} norm-strips-diacritics={s["norm_strips_diacritics_correctly"]}')
        lines.append(f'  - `{s["first_200_chars"][:200]}`')
        lines.append('')
    lines.extend([
        'Decision feedback:',
        '- If `pct_with_grammar` > 80% → `arabicText` is the right priority-1 source for Imami extraction (FR-3.2).',
        '- If `norm-strips-diacritics-correctly` is True across samples → existing `_norm` handles Thaqalayn diacritization; no separate normalisation pass needed.',
        '',
    ])
    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print()
    print(f'Wrote {OUT_MD}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
