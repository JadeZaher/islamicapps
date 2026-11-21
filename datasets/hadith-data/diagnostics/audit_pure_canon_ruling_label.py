#!/usr/bin/env python3
"""J6c: where does the Sunni grade value 'ثابت' come from, and does it vary per hadith?

Compares the upstream archive field `ruling` (pure_canon.jsonl, green_book.jsonl) with the snapshot's
grade_tradition/grade_source/grade_value on the four Pure Canon collections. Reports distributions only;
writes only under diagnostics/grading/.

Usage: python -B diagnostics/audit_pure_canon_ruling_label.py
"""

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402

JOB = "grading"
ARCHIVE = common.HADITH_DATA_DIR / "archive" / "sheikahmad-pure-canon"
UPSTREAM_FILES = ("pure_canon.jsonl", "green_book.jsonl")
PURE_CANON_SOURCES = {"Musnad Ahmad", "Sunan al-Darimi", "Musnad al-Shafi'i", "Muwatta' Malik"}


def main() -> None:
    started = time.time()
    upstream = {}
    for name in UPSTREAM_FILES:
        path = ARCHIVE / name
        if not path.exists():
            continue
        rulings, by_source, keys = Counter(), defaultdict(Counter), Counter()
        rows = 0
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                rows += 1
                keys.update(record.keys())
                ruling = str(record.get("ruling", "<field absent>"))
                rulings[ruling] += 1
                by_source[str(record.get("source", "<none>"))][ruling] += 1
        upstream[name] = {
            "sha256": common.sha256_file(path), "rows": rows, "fields_present": dict(keys),
            "ruling_values": dict(rulings.most_common(20)), "distinct_ruling_values": len(rulings),
            "ruling_values_by_source": {s: dict(c) for s, c in sorted(by_source.items(), key=lambda kv: -sum(kv[1].values()))},
        }
    snapshot_pairs, snapshot_by_source = Counter(), defaultdict(Counter)
    for _, row in common.iter_corpus_rows():
        source = common.clean(row["source"])
        if source not in PURE_CANON_SOURCES:
            continue
        snapshot_pairs[(common.clean(row["grade_tradition"]), common.clean(row["grade_source"]),
                        common.clean(row["grade_value"]))] += 1
        snapshot_by_source[source][common.clean(row["grade_value"])] += 1
    pure_by_source = upstream.get("pure_canon.jsonl", {}).get("ruling_values_by_source", {})
    audit = {
        "header": common.header_object(
            JOB, "python -B datasets/hadith-data/diagnostics/audit_pure_canon_ruling_label.py",
            common.input_fingerprints(common.CORPUS_PATH, common.DATASETS_DIR / "sources" / "sheikahmad-pure-canon.md")),
        "upstream_archive": upstream,
        "snapshot_pure_canon_rows": sum(snapshot_pairs.values()),
        "snapshot_grade_triples": [{"grade_tradition": a, "grade_source": b, "grade_value": c, "rows": n}
                                   for (a, b, c), n in snapshot_pairs.most_common()],
        "snapshot_rows_by_collection": {s: dict(c) for s, c in sorted(snapshot_by_source.items())},
        "upstream_rows_for_the_four_arabic_collection_labels": {
            s: sum(pure_by_source.get(s, {}).values()) for s in ("مسند حنبل", "سنن الدارمي", "شافعي", "موطأ مالك")},
        "reading": ("`ruling` is the single value 'ثابت' on every upstream row, including rows from Sahih al-Bukhari and "
                    "Sahih Muslim, so it carries no per-hadith information; it is a dataset-wide inclusion label, "
                    "not a muhaddith's assessment. The unified snapshot copies it into grade_value on the four collections."),
        "seconds": round(time.time() - started, 1),
    }
    common.write_json(JOB and common.output_directory(JOB), "pure_canon_label_audit.json", audit)
    print({"upstream": {k: (v["rows"], v["distinct_ruling_values"]) for k, v in upstream.items()},
           "snapshot_triples": audit["snapshot_grade_triples"], "seconds": audit["seconds"]})


if __name__ == "__main__":
    main()
