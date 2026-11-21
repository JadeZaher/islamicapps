#!/usr/bin/env python3
"""Pre-load citation check for every row this directory emits (see README.md §Citations).

A row passes when `citation_status == "cited"` and its citation is complete, or when it is `not_yet_cited` with a
stated reason. For report rows read from a stored text, the passage must equal `text_ar[start:end]` of the report and
the report's Arabic must still hash to `text_sha256`. Exit 1 on any failure. Usage (repository root):

    python -B datasets/hadith-data/assessments/validate_citations.py
"""

import collections
import csv
import gzip
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
HADITHS = HERE.parent / "development" / "pg-load-2026-11-21" / "projection-v3" / "canonical" / "hadiths.csv"
FILES = ("hadith_assessments.jsonl.gz", "compiler_criterion_links.jsonl.gz", "narrator_assessments.jsonl.gz")
REGISTRY_CODES = {"THQ", "OITI", "SUN", "NMC", "MSD", "K6I", "RIJ", "HKG", "RWY", "SWI"}


def problems(row: dict) -> list:
    found = []
    status = row.get("citation_status")
    citation = row.get("citation") or {}
    if status not in ("cited", "not_yet_cited"):
        return ["citation_status missing"]
    if (citation.get("source") or {}).get("code") not in REGISTRY_CODES:
        found.append("source code not in src/lib/sources/registry.ts")
    if status == "not_yet_cited":
        return found + ([] if row.get("citation_missing") else ["not_yet_cited without a reason"])
    work = citation.get("work") or {}
    if not work.get("author"):
        found.append("work.author")
    if not work.get("title") and not (work.get("quoted_in") or work.get("title_note")):
        found.append("work.title")
    if not work.get("tradition"):
        found.append("work.tradition")
    for field in ("edition", "passage_ar", "text_sha256"):
        if not citation.get(field):
            found.append(field)
    if not (citation.get("source") or {}).get("licence"):
        found.append("source.licence")
    locator = citation.get("locator") or {}
    if not any(locator.get(k) for k in ("volume", "page", "entry", "hadith_number", "record_id", "sheet_row")):
        found.append("locator")
    return found


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    csv.field_size_limit(10 ** 9)
    texts = {}
    with open(HADITHS, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            texts[row["id"]] = row["text_ar"]
    tally, failures = collections.Counter(), []
    for name in FILES:
        with gzip.open(HERE / name, "rt", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                found = problems(row)
                citation = row.get("citation") or {}
                span = citation.get("char_span")
                if not found and span and row.get("source_field") == "text_ar":
                    text = texts.get(row["hadith_id"], "")
                    if hashlib.sha256(text.encode("utf-8")).hexdigest() != citation["text_sha256"]:
                        found.append("report Arabic no longer matches text_sha256")
                    elif text[span[0]:span[1]] != citation["passage_ar"]:
                        found.append("passage is not text_ar[start:end]")
                kind = row.get("basis_kind")
                tally[(name, kind, row.get("citation_status"), "fail" if found else "pass")] += 1
                if found:
                    failures.append({"id": row["id"], "problems": found})
    for key, count in sorted(tally.items()):
        print(" | ".join(str(k) for k in key), count)
    print(f"failures: {len(failures)}")
    for failure in failures[:20]:
        print(json.dumps(failure, ensure_ascii=False))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
