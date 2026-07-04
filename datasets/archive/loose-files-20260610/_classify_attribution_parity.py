#!/usr/bin/env python3
"""
_classify_attribution_parity.py — Python ground truth for the TS port test
==========================================================================

Internal helper for the TypeScript regression test in
`src/scripts/__tests__/regen-isnad-graph.test.ts` (track
`neo4j_isnad_graph_regen_20260516`, Blocker 2 — faithful-port parity).

The reviewer found that JavaScript `RegExp` `\b` is ASCII-only while Python
`re` `\b` on `str` is Unicode-aware, so the TS port silently misclassified
~951 rows and produced a wrong `unknown_attribution_fraction`. The fix
replaces every Arabic-adjacent `\b` in the TS port with a Unicode-correct
lookaround that mirrors Python `\w` exactly (`[\p{L}\p{N}_]`). This script
provides the authoritative Python output the TS test compares against on
every sampled real row from `datasets/hadith-data/all_hadiths_unified.csv`.

CLI:
    python _classify_attribution_parity.py
      --csv  <path to all_hadiths_unified.csv>
      --rows <comma-separated 0-based row indices>      # OR  --rows-file <path>
      [--out <jsonl out path>]                          # default: stdout

Output: one JSONL line per requested row:
    {"idx": N, "attributed_to": "...", "narration_level": "..."}

Counts CSV RECORDS (multiline-quoted-field aware) via `csv.DictReader`, never
lines. Sets `csv.field_size_limit(10**8)` so the long Arabic `text_ar` fields
do not trip the default 128 KiB cap. UTF-8 throughout.
"""

import argparse
import csv
import json
import os
import sys

# Import the canonical classifier from the sibling module. The script lives
# in `datasets/`, so this works whether invoked from repo root or anywhere
# else (we manipulate sys.path defensively).
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from classify_attribution import classify  # noqa: E402

# Arabic text_ar fields and embedded fanciful quotation can exceed the default
# csv field-size cap (~131 KiB). 100 MiB is far above the largest seen field.
csv.field_size_limit(10**8)

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Emit Python classify() ground truth for selected CSV rows."
    )
    ap.add_argument("--csv", required=True, help="Path to all_hadiths_unified.csv")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--rows", help="Comma-separated 0-based row indices")
    g.add_argument("--rows-file", help="Path to a file with one row index per line")
    ap.add_argument("--out", help="Output JSONL path (default: stdout)")
    args = ap.parse_args()

    if args.rows is not None:
        wanted = sorted({int(x) for x in args.rows.split(",") if x.strip()})
    else:
        with open(args.rows_file, encoding="utf-8") as fh:
            wanted = sorted({int(line.strip()) for line in fh if line.strip()})

    if not wanted:
        print("No row indices supplied", file=sys.stderr)
        return 2

    want_set = set(wanted)
    max_idx = wanted[-1]

    out_lines: list[str] = []
    with open(args.csv, encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for idx, row in enumerate(reader):
            if idx in want_set:
                attributed_to, narration_level = classify(
                    row.get("text_ar"),
                    row.get("sanad"),
                    row.get("tradition", "") or "",
                    row.get("source", "") or "",
                )
                out_lines.append(
                    json.dumps(
                        {
                            "idx": idx,
                            "attributed_to": attributed_to,
                            "narration_level": narration_level,
                        },
                        ensure_ascii=False,
                    )
                )
            if idx >= max_idx:
                # Honest about CSV scope: we only need rows up to the highest
                # requested index. csv.DictReader is single-pass; this avoids
                # walking the remaining ~70k rows.
                break

    blob = "\n".join(out_lines) + ("\n" if out_lines else "")
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(blob)
    else:
        sys.stdout.write(blob)
    return 0


if __name__ == "__main__":
    sys.exit(main())
