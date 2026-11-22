"""Column-level diff of two projections (every canonical table, by id): which columns changed in how many rows (read-only).

    python -X utf8 table_diff.py <before projection> <after projection> <out json>
"""
import csv, json, sys
from collections import Counter
from pathlib import Path

csv.field_size_limit(2**31 - 1)


def read(path):
    with open(path, encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        return header, {row[0]: row for row in reader}


def main(before, after, out):
    report = {}
    for file in sorted((Path(before) / "canonical").glob("*.csv")):
        other = Path(after) / "canonical" / file.name
        header_a, rows_a = read(file)
        header_b, rows_b = read(other)
        entry = {"rows_before": len(rows_a), "rows_after": len(rows_b), "header_equal": header_a == header_b,
                 "added": len(rows_b.keys() - rows_a.keys()), "removed": len(rows_a.keys() - rows_b.keys())}
        changed = Counter()
        rows_changed = 0
        for key in rows_a.keys() & rows_b.keys():
            a, b = rows_a[key], rows_b[key]
            if a != b:
                rows_changed += 1
                for name, x, y in zip(header_a, a, b):
                    if x != y:
                        changed[name] += 1
        entry["rows_changed"] = rows_changed
        entry["columns_changed"] = dict(sorted(changed.items()))
        report[file.name] = entry
    Path(out).write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    for name, entry in report.items():
        if entry["rows_changed"] or entry["added"] or entry["removed"] or not entry["header_equal"]:
            print(name, entry)
    print("tables compared:", len(report))


if __name__ == "__main__":
    main(*sys.argv[1:4])
