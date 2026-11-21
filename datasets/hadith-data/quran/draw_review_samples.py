"""Draw the deterministic review samples: 80 rows to be read and 150 for a blank human worksheet (disjoint).

    python -B datasets/hadith-data/quran/draw_review_samples.py

Rows are ranked by sha256(salt + id) inside each stratum, so the draw is reproducible and independent of file order.
Writes quran_reading_80_unlabelled.csv (the reader fills `verdict`, see README.md) and quran_review_worksheet_150.csv.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "reconciled"))
import external_source_io as xio  # noqa: E402

# (stratum name, predicate on a row) with the quota of the 80-row reading and of the 150-row worksheet.
STRATA = [
    ("citation_high_cued", lambda r: r["confidence"] == "high" and r["primary_cue"] is not None, 14, 30),
    ("citation_high_uncued", lambda r: r["confidence"] == "high" and r["primary_cue"] is None, 8, 14),
    ("citation_medium", lambda r: r["confidence"] == "medium", 8, 14),
    ("citation_low_cued", lambda r: r["confidence"] == "low" and r["primary_cue"] is not None, 6, 12),
    ("citation_low_uncued", lambda r: r["confidence"] == "low" and r["primary_cue"] is None, 12, 24),
    ("short_phrase", lambda r: r["kind"] == "short_phrase", 12, 20),
    ("common_phrase", lambda r: r["kind"] == "common_phrase", 8, 14),
    ("formula", lambda r: r["kind"] == "formula", 6, 12),
    ("ambiguous_candidates", lambda r: r["kind"] == "citation" and r["ambiguous"], 6, 10),
]
CONTEXT = 70


def rank(salt: str, identifier: str) -> str:
    return hashlib.sha256(f"{salt}|{identifier}".encode("utf-8")).hexdigest()


def read(name: str):
    with gzip.open(HERE / name, "rt", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def draw(rows, quota_index: int, taken: set, salt: str) -> list[tuple[str, dict]]:
    chosen = []
    for name, predicate, *quotas in STRATA:
        pool = sorted((r for r in rows if predicate(r) and r["id"] not in taken), key=lambda r: rank(salt, r["id"]))
        for row in pool[:quotas[quota_index]]:
            taken.add(row["id"])
            chosen.append((name, row))
    return chosen


def main() -> None:
    rows = list(read("hadith_quran_citations.jsonl.gz")) + list(read("hadith_quran_phrases.jsonl.gz"))
    taken: set = set()
    reading = draw(rows, 0, taken, "reading-80")
    worksheet = draw(rows, 1, taken, "worksheet-150")
    need = {row["record_id"] for _, row in reading + worksheet}
    texts = {r["record_id"]: r["text_ar"] or "" for r in xio.iter_corpus() if r["record_id"] in need}

    def line(stratum, row):
        text = texts[row["record_id"]]
        assert text[row["start"]:row["end"]] == row["quote_ar"]
        first = row["candidates"][0]
        return {"id": row["id"], "stratum": stratum, "tradition": row["tradition"], "source": row["source"],
                "kind": row["kind"], "confidence": row["confidence"] or "", "words": row["words"],
                "cue": row["primary_cue"] or "", "references": " | ".join(c["ref"] for c in row["candidates"][:6]),
                "context_before": text[max(0, row["start"] - CONTEXT):row["start"]].replace("\n", " "),
                "quotation": row["quote_ar"].replace("\n", " "),
                "context_after": text[row["end"]:row["end"] + CONTEXT].replace("\n", " "),
                "quran_text_first_candidate": first["quran_text"]}

    columns = ["id", "stratum", "tradition", "source", "kind", "confidence", "words", "cue", "references",
               "context_before", "quotation", "context_after", "quran_text_first_candidate"]
    review_columns = ["verdict", "correct_reference", "notes", "reviewer"]
    reading_rows = [line(name, row) for name, row in sorted(reading, key=lambda x: (x[0], x[1]["id"]))]
    worksheet_rows = [line(name, row) for name, row in sorted(worksheet, key=lambda x: (x[0], x[1]["id"]))]
    for path, content, extra in ((HERE / "quran_reading_80_unlabelled.csv", reading_rows, []),
                                 (HERE / "quran_review_worksheet_150.csv", worksheet_rows, review_columns)):
        with open(path, "w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns + extra, lineterminator="\n")
            writer.writeheader()
            for entry in content:
                writer.writerow({**entry, **{key: "" for key in extra}})
    counts = defaultdict(int)
    for name, _ in reading:
        counts[name] += 1
    print(len(reading_rows), len(worksheet_rows), dict(counts))


if __name__ == "__main__":
    main()
