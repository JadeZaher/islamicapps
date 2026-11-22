"""Markdown tables for README.md: pilot coverage per context kind and tradition, sizes, corpus coverage of second copies and metadata.

    python -I -X utf8 tools/coverage_tables.py
"""

from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

CONTEXT = Path(__file__).resolve().parents[1]
ROOT = CONTEXT.parent
SECTION = {"sunni": "Sunni", "imami": "Imami", "ibadi": "Ibadi", "zaydi": "Zaydi"}


def packets(directory: str) -> list[dict]:
    return [json.loads(line) for path in sorted((CONTEXT / "pilot-v2" / directory).glob("packet-*.jsonl")) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:.0f}%" if whole else "-"


def main() -> None:
    pilot = {row["id"]: row for row in (json.loads(l) for l in (ROOT / "pilot" / "reports.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}
    chain, text = packets("packets"), packets("packets-text")
    print(f"packets: chain {len(chain)} reports in {len(list((CONTEXT / 'pilot-v2' / 'packets').glob('packet-*.jsonl')))} files; text {len(text)}")
    for name, rows in (("chain", chain), ("text", text)):
        sizes = sorted(len(json.dumps(r["context"], ensure_ascii=False)) for r in rows)
        packet_chars = [len(json.dumps(r, ensure_ascii=False)) for r in rows]
        print(f"{name}: context chars median {statistics.median(sizes):.0f}, p95 {sizes[int(0.95 * len(sizes))]}, max {sizes[-1]}; whole report line (text+context) median {statistics.median(packet_chars):.0f}, max {max(packet_chars)}")
    print("\n### Pilot: share of reports with each chain-context kind, by tradition\n")
    kinds = ["previous_reports", "parent_report", "source_claims", "sources_agree", "name_facts", "correspondences", "archive_flags", "source_notes"]
    by_tradition: dict[str, list[dict]] = defaultdict(list)
    for row in chain:
        by_tradition[pilot[row["id"]]["tradition"]].append(row)
    print("| kind | " + " | ".join(f"{SECTION[t]} ({len(by_tradition[t])})" for t in SECTION) + " | all (284) |")
    print("|---|" + "---|" * (len(SECTION) + 1))
    for kind in kinds:
        cells = [pct(sum(1 for r in by_tradition[t] if kind in r["context"]), len(by_tradition[t])) for t in SECTION]
        print(f"| {kind} | " + " | ".join(cells) + f" | {pct(sum(1 for r in chain if kind in r['context']), len(chain))} |")
    omitted = Counter(k for r in chain for k in r["context"].get("omitted_for_size", []))
    print(f"\nomitted for size (chain): {dict(omitted)}; reports with something omitted: {sum(1 for r in chain if 'omitted_for_size' in r['context'])}")
    print("\n### Pilot: source claims by source, by tradition\n")
    print("| source | " + " | ".join(SECTION[t] for t in SECTION) + " |")
    print("|---|" + "---|" * len(SECTION))
    for source in ("K6I", "HKG", "RWY", "THQ", "NMC"):
        cells = [pct(sum(1 for r in by_tradition[t] if any(c["source"] == source for c in r["context"].get("source_claims", []))), len(by_tradition[t])) for t in SECTION]
        print(f"| {source} | " + " | ".join(cells) + " |")
    print("\n### Pilot: text and metadata, by tradition\n")
    print("| | " + " | ".join(SECTION[t] for t in SECTION) + " | all |")
    print("|---|" + "---|" * (len(SECTION) + 1))
    by_text: dict[str, list[dict]] = defaultdict(list)
    for row in text:
        by_text[pilot[row["id"]]["tradition"]].append(row)
    tests = {
        "at least one second local copy": lambda tm: tm["second_local_copies"] > 0,
        "at least one copy independent of our source file": lambda tm: tm["independent_of_our_source"] > 0,
        "a computed difference found": lambda tm: bool(tm.get("differences_found")),
        "no second local copy (finding)": lambda tm: tm["second_local_copies"] == 0,
        "book stored": lambda tm: bool(tm["metadata"]["ours"]["book"]),
        "chapter stored": lambda tm: bool(tm["metadata"]["ours"]["chapter"]),
        "report number stored": lambda tm: bool(tm["metadata"]["ours"]["report_number"]),
        "volume stored": lambda tm: bool(tm["metadata"]["ours"]["volume"]),
        "page stored": lambda tm: bool(tm["metadata"]["ours"]["page"]),
        "url stored": lambda tm: bool(tm["metadata"]["ours"]["url"]),
        "a grading stored": lambda tm: bool(tm["metadata"]["gradings"]),
        "a local source gives metadata for comparison": lambda tm: bool(tm["metadata"]["local"]),
    }
    for name, test in tests.items():
        cells = [pct(sum(1 for r in by_text[t] if test(r["context"]["text_and_metadata"])), len(by_text[t])) for t in SECTION]
        print(f"| {name} | " + " | ".join(cells) + f" | {pct(sum(1 for r in text if test(r['context']['text_and_metadata'])), len(text))} |")
    print("\n### Corpus (live reports): second local copy and populated metadata, by work\n")
    coverage = json.loads((CONTEXT / "coverage.json").read_text(encoding="utf-8"))
    print("| work | reports | indep. copy (hadith-kg / Riwayat / either) | source-file copy | book | chapter | number | volume | page | url | grading |")
    print("|---|---:|---|---|---|---|---|---|---|---|---|")
    totals: dict[str, Counter] = defaultdict(Counter)
    for row in coverage:
        n = row["reports"]
        print(f"| {row['work']} | {n:,} | {pct(row['independent_copy_hadith_kg'], n)} / {pct(row['independent_copy_riwayat'], n)} / {pct(row['independent_copy_any'], n)} | {pct(row['source_file_copy'], n)} | {pct(row['book'], n)} | {pct(row['chapter'], n)} | {pct(row['report_number'], n)} | {pct(row['volume'], n)} | {pct(row['page'], n)} | {pct(row['url'], n)} | {pct(row['grading'], n)} |")
        for key in ("reports", "independent_copy_any", "source_file_copy", "book", "chapter", "report_number", "volume", "page", "url", "grading"):
            totals[row["tradition"]][key] += row[key]
    print("\n| tradition | reports | indep. copy (any) | source-file copy | book | chapter | number | volume | page | url | grading |")
    print("|---|---:|---|---|---|---|---|---|---|---|---|")
    for t, c in totals.items():
        n = c["reports"]
        print(f"| {t} | {n:,} | {pct(c['independent_copy_any'], n)} | {pct(c['source_file_copy'], n)} | " + " | ".join(pct(c[k], n) for k in ("book", "chapter", "report_number", "volume", "page", "url", "grading")) + " |")


if __name__ == "__main__":
    main()
