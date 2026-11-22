#!/usr/bin/env python3
"""Scorer input for the corrected OpenITI reports: production text beside its source window.

    python -I -X utf8 build_corrected_windows.py --snapshot <production rows jsonl.gz> --out output/records_with_windows_corrected.jsonl.gz

The snapshot is one JSON object per report (id, source_record_id, text_ar, sanad_ar, matn_ar) read from production. The window is the
source edition's paragraphs around the report (two before, two after, at most 7,000 characters), as deterministic_checks.window_for
builds it. A report whose opening cannot be found in the source gets no window and is listed, not scored.
"""
from __future__ import annotations

import argparse
import bisect
import gzip
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import eq_source as eq  # noqa: E402

RIDA_START = "مسند الإمام علي الرضا"
PREFIX_LETTERS = 40


def letters_only(text: str) -> str:
    return re.sub(r"[^ء-ي]", "", text)


def work_of(record_id: str) -> str:
    return eq.work_of(record_id)


def locate_all(rows: list[dict], paragraphs: list[dict]) -> dict[str, tuple[int, int]]:
    """(start, end) of each report in the letters-only concatenation of the paragraphs, searched in file order."""
    texts = [letters_only(p["text"]) for p in paragraphs]
    offsets, total = [], 0
    for text in texts:
        offsets.append(total)
        total += len(text)
    joined = "".join(texts)
    found: dict[str, tuple[int, int]] = {}
    cursor = 0
    for row in rows:
        letters = letters_only(row["text_ar"])
        if len(letters) < 8:
            continue
        needle = letters[:PREFIX_LETTERS]
        at = joined.find(needle, cursor)
        if at < 0:
            at = joined.find(needle)
        if at < 0:
            continue
        found[row["id"]] = (at, at + len(letters))
        cursor = at + 1
    return found, offsets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    with gzip.open(args.snapshot, "rt", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    by_work: dict[str, list[dict]] = {}
    for row in rows:
        by_work.setdefault(work_of(row["source_record_id"] if "source_record_id" in row else row["id"]), []).append(row)
    windows, missing = [], []
    for work, items in sorted(by_work.items()):
        paragraphs = eq.paragraph_stream(eq.read_source(work))
        if work == "rida":
            first = next(i for i, p in enumerate(paragraphs) if RIDA_START in p["text"])
            paragraphs = paragraphs[first:]
        found, offsets = locate_all(items, paragraphs)
        starts_raw = [p["raw_start"] for p in paragraphs]
        for row in items:
            span = found.get(row["id"])
            if span is None:
                missing.append(row["id"])
                continue
            first = max(0, bisect.bisect_right(offsets, span[0]) - 1 - 2)
            last = min(len(paragraphs) - 1, bisect.bisect_right(offsets, max(span[0], span[1] - 1)) - 1 + 2)
            window = "\n".join(p["text"] for p in paragraphs[first:last + 1])[:7000]
            windows.append({"id": row["id"], "source_record_id": row.get("source_record_id"), "work": work, "text_ar": row["text_ar"],
                            "sanad": row.get("sanad_ar"), "matn_ar": row.get("matn_ar"), "window_ar": window,
                            "window_raw_span": [starts_raw[first], paragraphs[last]["raw_end"]]})
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with gzip.open(args.out, "wt", encoding="utf-8", newline="\n") as handle:
        for window in windows:
            handle.write(json.dumps(window, ensure_ascii=False) + "\n")
    print(json.dumps({"reports": len(rows), "windows": len(windows), "not_located": len(missing), "not_located_ids": missing[:40]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
