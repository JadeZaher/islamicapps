#!/usr/bin/env python3
"""Pre-load citation check for the rijal layer: every record carries a citation; every `cited` one is re-read
from its source file (SHA-256 match, span slice, passage found in the span with markup removed).

Exit 1 if any record lacks a citation or any `cited` record fails. Usage (repo root):
python -B datasets/hadith-data/rijal/validate_citations.py
"""

import gzip
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rijal_extract as rx  # noqa: E402

REPO = HERE.parent.parent.parent
OUT = HERE / "output"


def records():
    works = json.loads((OUT / "rijal_works.json").read_text(encoding="utf-8"))["works"]
    for work in works:
        yield "rijal_works.json", work
    for path in sorted(OUT.glob("*.jsonl.gz")):
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                yield path.name, json.loads(line)


def main() -> int:
    sources, hashes = {}, {}
    counts = defaultdict(Counter)
    failures = []
    for name, record in records():
        citation = record.get("citation")
        if not isinstance(citation, dict) or citation.get("citation_status") not in ("cited", "not_yet_cited"):
            counts[name]["missing_citation"] += 1
            failures.append((name, "missing citation", record.get("entry_id") or record.get("link_id")))
            continue
        if citation["citation_status"] == "not_yet_cited":
            if not citation.get("not_yet_cited_reason"):
                counts[name]["not_yet_cited_without_reason"] += 1
                failures.append((name, "not_yet_cited without a reason", None))
            else:
                counts[name]["not_yet_cited"] += 1
            continue
        source_file = citation["source_file"]
        if source_file not in sources:
            raw = (REPO / source_file).read_bytes()
            hashes[source_file] = hashlib.sha256(raw).hexdigest()
            sources[source_file] = raw.decode("utf-8", errors="replace")
        problems = rx.citation_problems(citation, sources[source_file], hashes[source_file])
        if problems:
            counts[name]["cited_but_fails"] += 1
            if len(failures) < 50:
                failures.append((name, "; ".join(problems), record.get("entry_id") or record.get("link_id")))
        else:
            counts[name]["cited_and_verified"] += 1
    report = {"by_output": {k: dict(v) for k, v in sorted(counts.items())},
              "totals": dict(sum(counts.values(), Counter())), "first_failures": failures[:50]}
    (OUT / "citation_validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                                                  encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=1)[:4000])
    return 1 if any(c["missing_citation"] or c["cited_but_fails"] or c["not_yet_cited_without_reason"]
                    for c in counts.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
