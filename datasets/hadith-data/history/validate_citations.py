"""Pre-load validator for the history lane's citations and claims (owner rule: one complete citation per claim).

    python -B datasets/hadith-data/history/validate_citations.py      # exit 1 on any failure

Checks every citation: required fields; the source file's SHA-256; the character span re-read from the file, markup
removed and whitespace collapsed, equals `quote_ar`; the byte span matches the character span. Checks every claim and
involvement row: its citation exists, and `citation_status` is `cited` only when the citation is complete.
"""
import gzip
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import history_text as ht  # noqa: E402

OUT = HERE / 'output'
REQUIRED = ('id', 'work_id', 'edition_id', 'work', 'edition', 'locator', 'locator_text', 'quote_ar', 'source_span',
            'source_file', 'source_sha256', 'source_reference', 'licence')


def rows(name):
    with gzip.open(OUT / name, 'rt', encoding='utf-8') as handle:
        return [json.loads(line) for line in handle]


def main():
    failures, files, hashes = [], {}, {}
    citations = {c['id']: c for c in rows('citations.jsonl.gz')}
    for cid, c in citations.items():
        missing = [k for k in REQUIRED if c.get(k) in (None, '', {})]
        if missing:
            failures.append(f'{cid}: missing {missing}')
            continue
        if not (c['work'].get('author') and c['work'].get('title')):
            failures.append(f'{cid}: work author/title missing')
        path = ht.REPO_ROOT / c['source_file']
        if path not in files:
            files[path] = path.read_text(encoding='utf-8')
            hashes[path] = ht.sha256_file(path)
        if hashes[path] != c['source_sha256']:
            failures.append(f'{cid}: source SHA-256 differs')
        span = c['source_span']
        raw = files[path][span['char_start']:span['char_end']]
        reread = re.sub(r'\s+', ' ', ht._MARKUP.sub(' ', raw)).strip()
        if reread != c['quote_ar']:
            failures.append(f'{cid}: span text != quote_ar')
        prefix = len(files[path][:span['char_start']].encode('utf-8'))
        if prefix != span['byte_start'] or prefix + len(raw.encode('utf-8')) != span['byte_end']:
            failures.append(f'{cid}: byte span inconsistent')
    counts = {'cited': 0, 'not_yet_cited': 0}
    for name in ('date_claims.jsonl.gz', 'narrator_event_candidates.jsonl.gz'):
        for row in rows(name):
            counts[row['citation_status']] = counts.get(row['citation_status'], 0) + 1
            if row['citation_id'] not in citations:
                failures.append(f"{row['id']}: citation {row['citation_id']} not found")
            if row['citation_status'] == 'cited' and not row['ai_review']:
                failures.append(f"{row['id']}: no AI-review record")
    print(json.dumps({'citations_checked': len(citations), 'claim_rows': counts, 'failures': len(failures)}, indent=1))
    for failure in failures[:40]:
        print('FAIL', failure)
    sys.exit(1 if failures else 0)


if __name__ == '__main__':
    main()
