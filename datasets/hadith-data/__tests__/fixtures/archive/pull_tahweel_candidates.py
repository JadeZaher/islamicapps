"""
Pull real K6 taḥwīl hadiths from the unified CSV and emit them as
fixture-candidates for hand annotation.

Output: tahweel-gold-candidates.jsonl — one JSON line per row with
{hadith_id, source, hadith_no, text_ar, ح_count}. A human (Jade) is
expected to read each row, fill in `expected_branches`, and re-save as
tahweel-gold.jsonl.

This is the "candidate-extraction" half of building the gold set; the
"annotation" half is manual.
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
UNIFIED = os.path.normpath(os.path.join(BASE, '..', '..', 'all_hadiths_unified.csv'))
OUT = os.path.join(BASE, 'tahweel-gold-candidates.jsonl')

TAHWEEL_RE = re.compile(
    r'(?:^|[\s،.])ح\s+و?(?:حدثنا|حدثني|أخبرنا|أخبرني|أنبأنا|أنبأني|ثنا|نا)',
)

# Distribution targets: span all six K6 sources + cover the 4+ branch case.
PER_SOURCE_TARGET = {
    "Sahih Bukhari": 4,
    "Sahih Muslim": 14,           # the source with the most taḥwīl
    "Jami' al-Tirmidhi": 4,       # includes the canary Tirmidhi #1
    "Sunan Abi Da'ud": 4,
    "Sunan Ibn Majah": 4,
    "Sunan an-Nasa'i": 4,
}

# Always include Tirmidhi #1 (the canary that started this whole investigation)
ALWAYS_INCLUDE = [
    ("Jami' al-Tirmidhi", '1'),
]


def main() -> int:
    if not os.path.exists(UNIFIED):
        print(f'ERROR: {UNIFIED} not found', file=sys.stderr)
        return 1

    per_source: dict[str, list] = defaultdict(list)
    always_hits: list = []
    with open(UNIFIED, 'r', encoding='utf-8', errors='replace') as f:
        for row in csv.DictReader(f):
            src = (row.get('source') or '').strip()
            text_ar = (row.get('text_ar') or '').strip()
            if not text_ar:
                continue
            hadith_no = (row.get('hadith_no') or '').strip()
            ح_count = len(TAHWEEL_RE.findall(text_ar))
            # Always-include rule
            if (src, hadith_no) in ALWAYS_INCLUDE:
                always_hits.append((row, ح_count))
                continue
            if src not in PER_SOURCE_TARGET:
                continue
            if ح_count == 0:
                continue
            per_source[src].append((row, ح_count))

    # For each source pick a mix: 60% 1-ح, 30% 2-ح, 10% 3+-ح
    picked = []
    for src, target in PER_SOURCE_TARGET.items():
        rows = per_source[src]
        if not rows:
            continue
        rows_1 = [r for r in rows if r[1] == 1]
        rows_2 = [r for r in rows if r[1] == 2]
        rows_3p = [r for r in rows if r[1] >= 3]
        n1 = int(target * 0.6)
        n2 = int(target * 0.3)
        n3 = target - n1 - n2
        picked.extend(rows_1[:n1])
        picked.extend(rows_2[:n2])
        picked.extend(rows_3p[:n3])
    picked.extend(always_hits)

    # Emit
    written = 0
    with open(OUT, 'w', encoding='utf-8') as f:
        for row, count in picked:
            payload = {
                'hadith_id': (row.get('hadith_id') or '').strip(),
                'source': (row.get('source') or '').strip(),
                'hadith_no': (row.get('hadith_no') or '').strip(),
                'tahweel_count': count,
                'text_ar': (row.get('text_ar') or '').strip(),
                'sanad': (row.get('sanad') or '').strip(),
                'expected_branches': None,  # for human annotation
                'notes': '',                # for human annotation
            }
            f.write(json.dumps(payload, ensure_ascii=False) + '\n')
            written += 1
    print(f'Wrote {OUT} ({written} candidates)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
