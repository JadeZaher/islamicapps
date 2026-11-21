"""Draws the fixed 50-row sample (40 date claims, 10 involvement rows; hash order, seed `history-sample-v1`) and writes
it with the judgements recorded in `sample_judgements.json` (right / doubtful / wrong, with a reason).

    python -B datasets/hadith-data/history/sample_for_judgement.py           # writes output/sample_50_judged.csv
    python -B datasets/hadith-data/history/sample_for_judgement.py --print   # prints the rows to judge
"""
import csv
import gzip
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / 'output'


def load(name):
    with gzip.open(OUT / name, 'rt', encoding='utf-8') as handle:
        return [json.loads(line) for line in handle]


def order(row_id):
    return hashlib.sha256(f'history-sample-v1|{row_id}'.encode()).hexdigest()


def main():
    claims, involvement = load('date_claims.jsonl.gz'), load('narrator_event_candidates.jsonl.gz')
    citations = {c['id']: c for c in load('citations.jsonl.gz')}
    sample = sorted(claims, key=lambda c: order(c['id']))[:40] + sorted(involvement, key=lambda r: order(r['id']))[:10]
    if '--print' in sys.argv:
        sys.stdout.reconfigure(encoding='utf-8')
        for row in sample:
            quote = citations[row['citation_id']]['quote_ar']
            target = row.get('target') or row.get('event_target')
            print(f"{row['id']} | {target} {row.get('boundary') or ''} | {row.get('year_hijri', row.get('role'))} | {row['ai_review']['outcome']} | {row['stated_ar']}")
            print('   H:', citations[row['citation_id']]['locator'].get('annal_heading'), '| Q:', re.sub(r'\s+', ' ', quote)[:300])
        return
    judgements = json.loads((HERE / 'sample_judgements.json').read_text(encoding='utf-8'))
    with open(OUT / 'sample_50_judged.csv', 'w', encoding='utf-8', newline='') as handle:
        writer = csv.writer(handle)
        writer.writerow(['row', 'id', 'kind', 'target', 'claim', 'ai_review', 'source_reference', 'quote_ar', 'judgement', 'reason'])
        for number, row in enumerate(sample, 1):
            judged = judgements.get(row['id'], ['unjudged', ''])
            kind = 'date_claim' if 'year_hijri' in row else 'involvement'
            claim = row.get('year_hijri') if kind == 'date_claim' else f"{row['narrator_id']} {row['role']}"
            citation = citations[row['citation_id']]
            writer.writerow([number, row['id'], kind, row.get('target') or row.get('event_target'), claim, row['ai_review']['outcome'],
                             citation['source_reference'], citation['quote_ar'], judged[0], judged[1]])
    print(json.dumps(Counter(judgements.get(r['id'], ['unjudged'])[0] for r in sample)))


if __name__ == '__main__':
    main()
