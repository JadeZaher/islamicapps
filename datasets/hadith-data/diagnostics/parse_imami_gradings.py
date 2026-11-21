#!/usr/bin/env python3
"""J6a: parse the Imami `gradings_full` cell into structured, citation-bound entries (imports nothing).

Each cell holds ' | '-separated entries 'Grader:  term   (Work (volume/page))'. The parser only splits what
the source wrote; it never maps a term to a scale or a grade. Writes only under diagnostics/grading/.

Usage: python -B diagnostics/parse_imami_gradings.py
"""

import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402

JOB = "grading"
_TAIL = re.compile(r"\((?P<work>[^()]*?)(?:\s*\((?P<volume>\d+)\s*/\s*(?P<page>\d+)\))?\)\s*$")


def parse_grading_entries(cell: str) -> tuple[list[dict], list[str]]:
    """Split a gradings_full cell into entries; returns (entries, unparsable_fragments)."""
    entries, failures = [], []
    for fragment in (cell or "").split(" | "):
        fragment = fragment.strip()
        if not fragment:
            continue
        grader, colon, rest = fragment.partition(":")
        tail = _TAIL.search(rest)
        if not colon or not tail:
            failures.append(fragment)
            continue
        term = " ".join(rest[:tail.start()].split())
        entries.append({
            "grader": " ".join(grader.split()), "term_ar": term, "cited_work": tail.group("work").strip(),
            "volume": int(tail.group("volume")) if tail.group("volume") else None,
            "page": int(tail.group("page")) if tail.group("page") else None, "raw": fragment})
    return entries, failures


def main() -> None:
    started = time.time()
    structured, failures = [], []
    graders, terms, works = Counter(), Counter(), Counter()
    term_by_grader = defaultdict(Counter)
    rows_with_cell = rows_fully_parsed = rows_with_failure = rows_with_no_locator = 0
    entries_total = entries_with_page = 0
    for row_number, row in common.iter_corpus_rows():
        cell = row.get("gradings_full") or ""
        if not cell.strip():
            continue
        rows_with_cell += 1
        entries, bad = parse_grading_entries(cell)
        reference = common.row_reference(row_number, row)
        for position, entry in enumerate(entries, 1):
            entries_total += 1
            entries_with_page += entry["page"] is not None
            graders[entry["grader"]] += 1
            terms[entry["term_ar"]] += 1
            works[entry["cited_work"]] += 1
            term_by_grader[entry["grader"]][entry["term_ar"]] += 1
            structured.append({**reference, "entry_no": position, **entry, "tradition": common.clean(row["tradition"]),
                               "status": "source_provided_unreviewed"})
        for fragment in bad:
            failures.append({**reference, "fragment": fragment})
        rows_fully_parsed += bool(entries) and not bad
        rows_with_failure += bool(bad)
        rows_with_no_locator += bool(entries) and all(e["page"] is None for e in entries)
    out = common.output_directory(JOB)
    structured_count = common.write_jsonl(out, "imami_gradings_structured.jsonl", structured)
    failure_count = common.write_jsonl(out, "parse_failures.jsonl", failures)
    common.write_json(out, "imami_gradings_summary.json", {
        "header": common.header_object(
            JOB, "python -B datasets/hadith-data/diagnostics/parse_imami_gradings.py",
            common.input_fingerprints(common.CORPUS_PATH)),
        "rows_with_gradings_full": rows_with_cell, "rows_fully_parsed": rows_fully_parsed,
        "rows_with_unparsable_fragment": rows_with_failure,
        "rows_whose_entries_all_lack_volume_page_locator": rows_with_no_locator,
        "entries_total": entries_total, "entries_with_volume_page": entries_with_page,
        "graders": dict(graders.most_common()), "cited_works": dict(works.most_common()),
        "distinct_terms": len(terms), "top_terms": dict(terms.most_common(40)),
        "top_terms_by_grader": {g: dict(c.most_common(15)) for g, c in term_by_grader.items()},
        "rows_written": {"imami_gradings_structured.jsonl": structured_count, "parse_failures.jsonl": failure_count},
        "caution": ("Terms are quoted verbatim, not mapped. Some terms (for example 'لم يخرجه', 'he did not include it') "
                    "record non-inclusion in a collection and are not rulings on a report's reliability."),
        "seconds": round(time.time() - started, 1),
    })
    print({"entries": structured_count, "failures": failure_count, "rows": rows_with_cell, "seconds": round(time.time() - started, 1)})


if __name__ == "__main__":
    main()
