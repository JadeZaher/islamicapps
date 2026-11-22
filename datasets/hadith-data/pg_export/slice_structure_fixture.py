"""Cut the chain structure gate flow-test fixture: real rows of a projection, closed over foreign keys.

Usage: python -I datasets/hadith-data/pg_export/slice_structure_fixture.py <projection dir> <out.json>
Reports: one uncertain report the owner named (k6:19535, k6:10685 or k6:5344) holding a standing adjacent pair, and one
report whose chains are all checked by rule in which the same student stands beside another teacher. Read by
src/db/queries/__tests__/structure-flows.test.ts.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(2**31 - 1)

NAMED_UNCERTAIN = ["hadith:k6:19535", "hadith:k6:10685", "hadith:k6:5344"]
TABLES = ["traditions", "sources", "collections", "books", "chapters", "hadiths", "narrators", "narrator_lexicon_profiles",
          "chains", "chain_mentions", "chain_mention_candidates"]


def rows(directory: Path, table: str) -> list[dict]:
    with (directory / "canonical" / f"{table}.csv").open(encoding="utf-8", newline="") as handle:
        return [{key: (value if value != "" else None) for key, value in row.items()} for row in csv.DictReader(handle)]


def standing_pairs(mentions: list[dict]) -> list[tuple[str, str, str]]:
    """(chain id, student, teacher) for each adjacent pair whose two identities stand (the view's own rule, simplified)."""
    by_chain: dict[str, dict[int, dict]] = defaultdict(dict)
    for mention in mentions:
        by_chain[mention["chain_id"]][int(mention["position"])] = mention
    out = []
    for chain_id, chain in by_chain.items():
        for position, student in chain.items():
            teacher = chain.get(position + 1)
            if (teacher and student["narrator_id"] and teacher["narrator_id"] and student["narrator_id"] != teacher["narrator_id"]
                    and student["resolution_basis"] == teacher["resolution_basis"] == "source_index"
                    and student["link_kind"] not in ("anonymous", "not_a_narrator")
                    and teacher["link_kind"] not in ("anonymous", "not_a_narrator")):
                out.append((chain_id, student["narrator_id"], teacher["narrator_id"]))
    return out


def main(projection: Path, output: Path) -> None:
    manifest = json.loads((projection / "canonical" / "manifest.json").read_text(encoding="utf-8"))
    chains = {row["id"]: row for row in rows(projection, "chains")}
    mentions = rows(projection, "chain_mentions")
    pairs = standing_pairs(mentions)
    status_of_report: dict[str, set[str]] = defaultdict(set)
    for chain in chains.values():
        status_of_report[chain["hadith_id"]].add(chain["structure_status"])
    pairs_by_student: dict[str, list[tuple[str, str]]] = defaultdict(list)   # student -> (teacher, report) in checked reports
    for chain_id, student, teacher in pairs:
        report = chains[chain_id]["hadith_id"]
        if status_of_report[report] == {"checked_by_rule"} and report.startswith("hadith:k6:"):
            pairs_by_student[student].append((teacher, report))
    chosen = None
    for uncertain in NAMED_UNCERTAIN:
        for chain_id, student, teacher in pairs:
            if chains[chain_id]["hadith_id"] != uncertain or chains[chain_id]["structure_status"] != "uncertain":
                continue
            others = sorted((t, r) for t, r in pairs_by_student.get(student, []) if t != teacher
                            and not any(s == student and tt == teacher and chains[c]["hadith_id"] == r for c, s, tt in pairs))
            if others:
                chosen = {"uncertain_report": uncertain, "student": student, "uncertain_teacher": teacher,
                          "checked_report": others[0][1], "checked_teacher": others[0][0]}
                break
        if chosen:
            break
    if chosen is None:
        raise SystemExit("no named uncertain report shares a student with a checked report")
    reports = sorted({chosen["uncertain_report"], chosen["checked_report"]})

    hadiths = {row["id"]: row for row in rows(projection, "hadiths")}
    picked_mentions = [m for m in mentions if m["hadith_id"] in reports]
    picked_candidates = [c for c in rows(projection, "chain_mention_candidates") if c["hadith_id"] in reports]
    narrator_ids = ({c["narrator_id"] for c in picked_candidates} | {m["narrator_id"] for m in picked_mentions if m["narrator_id"]}
                    | {m["name_latin_narrator_id"] for m in picked_mentions if m["name_latin_narrator_id"]})
    collections = {hadiths[h]["collection_id"] for h in reports}
    profiles = {row["narrator_id"]: row for row in rows(projection, "narrator_lexicon_profiles")}
    out: dict = {"generated_from": {"projection_content_sha256": manifest["content_sha256"],
                                    "projection_version": manifest["projection_version"]},
                 "reports": reports, "chosen": chosen}
    out["traditions"] = rows(projection, "traditions")
    out["collections"] = [row for row in rows(projection, "collections") if row["id"] in collections]
    out["sources"] = [row for row in rows(projection, "sources") if row["id"] in {c["source_id"] for c in out["collections"]}]
    out["hadiths"] = [hadiths[h] for h in reports]
    out["books"] = [row for row in rows(projection, "books") if row["id"] in {hadiths[h]["book_id"] for h in reports}]
    out["chapters"] = [row for row in rows(projection, "chapters") if row["id"] in {hadiths[h]["chapter_id"] for h in reports}]
    out["narrators"] = [row for row in rows(projection, "narrators") if row["id"] in narrator_ids]
    out["narrator_lexicon_profiles"] = [profiles[n] for n in sorted(narrator_ids) if n in profiles]
    out["chains"] = [row for row in chains.values() if row["hadith_id"] in reports]
    out["chain_mentions"] = picked_mentions
    out["chain_mention_candidates"] = picked_candidates
    output.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({table: len(out[table]) for table in TABLES}, sort_keys=True))
    print(json.dumps(chosen, ensure_ascii=False))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
