"""
Phase 0 / T-0.1 audit for uniform_isnad_extraction_20260609.

Counts ح-splitter occurrences per hadith across all_hadiths_unified.csv,
per-source. Output: .omc/research/uniform-isnad/tahweel-stats.md (Markdown
table) plus tahweel-stats.json (machine-readable).

The ح-splitter pattern matches lone heh preceded by punctuation/whitespace
and followed by و? + a transmission verb (حدثنا/أخبرنا/etc.) — that's the
classical taḥwīl-of-isnad convention. Lone ح inside a quoted matn (e.g. as
part of an Arabic word) won't match because the verb-anchor isn't present.
"""
from __future__ import annotations
import csv
import json
import os
import re
import sys
from collections import defaultdict

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

BASE = os.path.dirname(os.path.abspath(__file__))
UNIFIED = os.path.join(BASE, 'all_hadiths_unified.csv')
OUT_DIR = os.path.normpath(os.path.join(BASE, '..', '..', '.omc', 'research', 'uniform-isnad'))
OUT_MD = os.path.join(OUT_DIR, 'tahweel-stats.md')
OUT_JSON = os.path.join(OUT_DIR, 'tahweel-stats.json')

# Taḥwīl detector. Anchored requirement: ح surrounded by transmission context.
# Pattern: (start | punctuation | whitespace) + ح + whitespace + (optional و) +
# transmission verb.
TAHWEEL_RE = re.compile(
    r'(?:^|[\s،.])ح\s+و?(?:حدثنا|حدثني|أخبرنا|أخبرني|أنبأنا|أنبأني|ثنا|نا)',
)


def main() -> int:
    if not os.path.exists(UNIFIED):
        print(f'ERROR: {UNIFIED} not found', file=sys.stderr)
        return 1
    os.makedirs(OUT_DIR, exist_ok=True)

    per_source: dict[str, dict] = defaultdict(lambda: {
        '0_branches': 0,
        '1_branches': 0,  # 1 ح = 2 branches in the isnad (one taḥwīl splitter)
        '2_branches': 0,  # 2 ح = 3 branches
        '3_branches': 0,  # 3 ح = 4 branches
        '4plus_branches': 0,
        'total_rows': 0,
        'rows_with_text_ar': 0,
    })

    grand_total = 0
    with open(UNIFIED, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            grand_total += 1
            src = (row.get('source') or '').strip() or '(blank)'
            text_ar = (row.get('text_ar') or '').strip()
            d = per_source[src]
            d['total_rows'] += 1
            if not text_ar:
                d['0_branches'] += 1
                continue
            d['rows_with_text_ar'] += 1
            count = len(TAHWEEL_RE.findall(text_ar))
            if count == 0:
                d['0_branches'] += 1
            elif count == 1:
                d['1_branches'] += 1
            elif count == 2:
                d['2_branches'] += 1
            elif count == 3:
                d['3_branches'] += 1
            else:
                d['4plus_branches'] += 1

    # Write JSON
    payload = {'generated_utc': __import__('datetime').datetime.utcnow().isoformat() + 'Z',
               'total_rows': grand_total,
               'per_source': dict(per_source)}
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    # Write Markdown
    lines = [
        '# Taḥwīl-occurrence audit',
        '',
        f'Generated: {payload["generated_utc"]}  ',
        f'Source: `datasets/hadith-data/all_hadiths_unified.csv`  ',
        f'Detector regex: `{TAHWEEL_RE.pattern}`  ',
        f'Total rows scanned: {grand_total:,}',
        '',
        'Columns:',
        '- **rows** total rows from that source',
        '- **w/ text_ar** rows where `text_ar` is non-empty',
        '- **0br** no ح splitter (single chain)',
        '- **1br** 1 ح splitter (2 chains)',
        '- **2br** 2 ح splitters (3 chains)',
        '- **3br** 3 ح splitters (4 chains)',
        '- **4+** 4 or more ح splitters',
        '- **multi%** percentage of `w/ text_ar` rows that have at least one ح',
        '',
        '| Source | rows | w/ text_ar | 0br | 1br | 2br | 3br | 4+ | multi% |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    rows = []
    for src in sorted(per_source, key=lambda s: -per_source[s]['total_rows']):
        d = per_source[src]
        multi = d['1_branches'] + d['2_branches'] + d['3_branches'] + d['4plus_branches']
        denom = d['rows_with_text_ar']
        pct = f'{100 * multi / denom:.1f}%' if denom else '—'
        rows.append((src, d, multi, pct))
        lines.append(
            f'| {src} | {d["total_rows"]:,} | {d["rows_with_text_ar"]:,} | '
            f'{d["0_branches"]:,} | {d["1_branches"]:,} | {d["2_branches"]:,} | '
            f'{d["3_branches"]:,} | {d["4plus_branches"]:,} | {pct} |'
        )

    # Aggregate totals
    agg = {
        '0_branches': sum(d['0_branches'] for d in per_source.values()),
        '1_branches': sum(d['1_branches'] for d in per_source.values()),
        '2_branches': sum(d['2_branches'] for d in per_source.values()),
        '3_branches': sum(d['3_branches'] for d in per_source.values()),
        '4plus_branches': sum(d['4plus_branches'] for d in per_source.values()),
        'total_rows': sum(d['total_rows'] for d in per_source.values()),
        'rows_with_text_ar': sum(d['rows_with_text_ar'] for d in per_source.values()),
    }
    multi_total = agg['1_branches'] + agg['2_branches'] + agg['3_branches'] + agg['4plus_branches']
    pct_total = f'{100 * multi_total / agg["rows_with_text_ar"]:.1f}%' if agg['rows_with_text_ar'] else '—'
    lines.append(
        f'| **TOTAL** | **{agg["total_rows"]:,}** | **{agg["rows_with_text_ar"]:,}** | '
        f'**{agg["0_branches"]:,}** | **{agg["1_branches"]:,}** | **{agg["2_branches"]:,}** | '
        f'**{agg["3_branches"]:,}** | **{agg["4plus_branches"]:,}** | **{pct_total}** |'
    )

    lines.append('')
    lines.append('## Headline numbers')
    lines.append('')
    lines.append(f'- Rows requiring multi-branch extractor: **{multi_total:,}** ({pct_total} of rows with text_ar)')
    lines.append(f'- Maximum branches per hadith observed: **{1 + max(int(k.replace("plus_branches","").replace("_branches","")) for k in agg if "branches" in k):,}** (4+ class indicates rare high-branching cases — Q2 in spec)')
    lines.append('')
    lines.append('## Decisions this audit feeds')
    lines.append('')
    lines.append('- **T-1.1 algorithm complexity**: if 2br+ is < 1% of corpus, optimize the algorithm for 1br as the common case and treat 2+ as edge cases.')
    lines.append('- **T-1.3 convergence detection**: 1br rows are the calibration set for T-0.3.')
    lines.append('- **Phase 5 UI rendering**: the per-source multi% tells us which source pages need the multi-chain renderer up front (high-multi% sources) vs. which can defer it (low-multi% sources).')

    with open(OUT_MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')

    print(f'Wrote {OUT_MD}')
    print(f'Wrote {OUT_JSON}')
    print()
    print(f'Total rows: {agg["total_rows"]:,}')
    print(f'With text_ar: {agg["rows_with_text_ar"]:,}')
    print(f'Multi-branch (≥1 ح): {multi_total:,} ({pct_total})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
