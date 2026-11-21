#!/usr/bin/env python3
"""Render one narrator's perspectives matrix and per-source timelines from the rijal layer outputs (Markdown).

Rows: perspectives (each work, each critic al-Mizzi quotes, the narrator lexicon), grouped by tradition in
alphabetical order (ibadi, imami, sunni, zaydi), then sources that are not tradition-scoped. Columns: aspects.
An empty cell means the source is silent. Candidate-linked entries are kept and marked. This is the shape the
narrator page should render; see README.md §Load specification.

Usage (repo root):
  python -B datasets/hadith-data/rijal/render_narrator_matrix.py --scholar-indx 3002 [--imami-name "ابان بن تغلب"]
"""

import argparse
import csv
import gzip
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
OUT = HERE / "output"
LEXICON = HERE.parent.parent / "narrator-data" / "all_rawis.csv"
TRADITIONS = ("ibadi", "imami", "sunni", "zaydi")
ASPECTS = ("verdict_term", "reliability_qualifier", "generation_or_imam", "death_date", "places", "teachers",
           "students", "books", "doctrinal_or_other_note")


def read(name):
    with gzip.open(OUT / name, "rt", encoding="utf-8") as handle:
        for line in handle:
            yield json.loads(line)


def short(text, limit=90):
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit - 1] + "…"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scholar-indx")
    parser.add_argument("--imami-name", help="name key as in imami_chain_names.jsonl.gz")
    parser.add_argument("--max-teachers", type=int, default=4)
    args = parser.parse_args()

    links = []
    if args.scholar_indx:
        links += [r for r in read("rijal_links_lexicon.jsonl.gz") if r["scholar_indx"] == args.scholar_indx]
    if args.imami_name:
        links += [r for r in read("rijal_links_imami_chain_names.jsonl.gz") if r["name_key"] == args.imami_name]
    entry_state = {}
    for link in links:
        unique = link.get("biography_verification_status") == "unique" or (
            link.get("candidate_count") == 1 and not link.get("short_name"))
        entry_state[link["entry_id"]] = ("machine link (unique, unreviewed)" if unique
                                         else f"CANDIDATE (one of {link.get('candidate_count') or link.get('candidate_count_in_work')}; link not established)")
    cells = [c for c in read("rijal_perspective_cells.jsonl.gz") if c["entry_id"] in entry_state]
    facts = [f for f in read("rijal_timeline_facts.jsonl.gz") if f["entry_id"] in entry_state]

    grid = defaultdict(lambda: defaultdict(list))
    labels, traditions = {}, {}
    for cell in cells:
        row = (cell["perspective_id"], cell["entry_id"])
        labels[row] = cell["perspective_label"]
        traditions[row] = cell["tradition"]
        value = cell["verbatim_ar"] or json.dumps(cell["normalised"], ensure_ascii=False)
        if cell["aspect"] in ("teachers", "students") and len(grid[row][cell["aspect"]]) >= args.max_teachers:
            if not grid[row][cell["aspect"]][-1].startswith("+"):
                grid[row][cell["aspect"]].append("+ more")
            continue
        flags = [f for f in cell["flags"] if f in ("negated", "hearsay_or_reported", "subject_may_differ")]
        page = cell["locator"].get("page") or ""
        grid[row][cell["aspect"]].append(f"{short(value, 60)} [{page}]" + (f" ({', '.join(flags)})" if flags else ""))

    lexicon_row = None
    if args.scholar_indx:
        with open(LEXICON, encoding="utf-8", newline="") as handle:
            lexicon_row = next((r for r in csv.DictReader(handle) if r["scholar_indx"].strip() == args.scholar_indx),
                               None)

    print("| Tradition | Perspective (entry; link state) | " + " | ".join(ASPECTS) + " |")
    print("|" + "---|" * (len(ASPECTS) + 2))
    for tradition in TRADITIONS:
        for row in sorted(r for r in grid if traditions[r] == tradition):
            perspective, entry_id = row
            head = f"{labels[row]} — `{entry_id.split(':', 1)[1]}`; {entry_state[entry_id]}"
            print(f"| {tradition} | {head} | " + " | ".join("<br>".join(grid[row].get(a, [])) for a in ASPECTS) + " |")
    if lexicon_row:
        values = {"verdict_term": lexicon_row["grade"], "generation_or_imam": lexicon_row["grade"],
                  "death_date": lexicon_row["death_date_place"], "places": lexicon_row["places_of_stay"],
                  "teachers": short(lexicon_row["teachers"], 60), "students": short(lexicon_row["students"], 60),
                  "books": lexicon_row["books"]}
        print("| not tradition-scoped | Narrator lexicon (not yet cited) | "
              + " | ".join(short(values.get(a, ""), 60) for a in ASPECTS) + " |")

    print("\n**Timelines, one row per source (never merged)**\n")
    by_perspective = defaultdict(list)
    for fact in facts:
        by_perspective[(fact["tradition"], fact["perspective_label"], fact["entry_id"])].append(fact)
    for (tradition, label, entry_id), rows in sorted(by_perspective.items()):
        parts = []
        for fact in rows:
            when = fact.get("date_as_written") or ""
            years = (f"{fact['year_min']}–{fact['year_max']}" if fact.get("year_min") is not None
                     and fact.get("year_max") is not None and fact["year_min"] != fact["year_max"]
                     else str(fact.get("year_min") or fact.get("year_max") or ""))
            where = fact.get("place_as_written") or fact.get("event_as_written") or ""
            parts.append(f"{fact['kind']}: «{short(fact['citation'].get('passage_ar') or fact['verbatim'], 70)}»"
                         + (f" → {years} AH" if years else "") + (f" @ {where}" if where and not years else "")
                         + f" [{fact['citation']['locator'].get('page')}]")
        print(f"- {tradition} · {label} (`{entry_id.split(':', 1)[1]}`; {entry_state[entry_id]}): " + "; ".join(parts))


if __name__ == "__main__":
    main()
