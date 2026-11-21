#!/usr/bin/env python3
"""J8: defect report over the narrator lexicon all_rawis.csv plus a graph-degree priority list.

The lexicon is an uncited vocabulary (datasets/sources/narrator-lexicon.md), so these are DEFECT FLAGS about
the lexicon itself; they correct nothing and assert no date. Writes only under diagnostics/biography/.

Usage: python -B diagnostics/report_narrator_lexicon_defects.py
"""

import csv
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402
from narrator_surface_logic import parse_generation, parse_indx_list  # noqa: E402

JOB = "biography"
HIJRI_TO_GREGORIAN_SLOPE = 0.970229
HIJRI_EPOCH_CE = 621.57
GREGORIAN_TOLERANCE_YEARS = 3.0
MAX_PLAUSIBLE_AGE = 120
SPIKE_FACTOR = 3.0


def to_int(value: str):
    value = (value or "").strip()
    return int(value) if value.lstrip("-").isdigit() else None


def main() -> None:
    started = time.time()
    with open(common.REGISTRY_PATH, encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    known_ids = {(r.get("scholar_indx") or "").strip() for r in rows}
    defects = []
    kinds = Counter()

    def flag(row, kind, detail):
        kinds[kind] += 1
        defects.append({"scholar_indx": row["scholar_indx"], "name": row["name"], "defect": kind,
                        **detail, "status": "lexicon_defect_flag_unreviewed"})

    death_hijri_counts = Counter()
    degree_rows = []
    dangling = 0
    asymmetric = 0
    teacher_sets = {r["scholar_indx"]: parse_indx_list(r.get("teachers_inds")) for r in rows}
    student_sets = {r["scholar_indx"]: parse_indx_list(r.get("students_inds")) for r in rows}
    for row in rows:
        birth, death = to_int(row.get("birth_date_hijri")), to_int(row.get("death_date_hijri"))
        birth_ce, death_ce = to_int(row.get("birth_date_gregorian")), to_int(row.get("death_date_gregorian"))
        if death is not None:
            death_hijri_counts[death] += 1
        if birth is not None and death is not None and death < birth:
            flag(row, "inverted_birth_death_hijri", {"birth_hijri": birth, "death_hijri": death})
        if birth is not None and death is not None and 0 <= death - birth and death - birth > MAX_PLAUSIBLE_AGE:
            flag(row, "implausible_age_over_120", {"birth_hijri": birth, "death_hijri": death})
        if death == 0:
            flag(row, "death_hijri_zero_sentinel_suspected", {"death_hijri": 0})
        for label, hijri, gregorian in (("birth", birth, birth_ce), ("death", death, death_ce)):
            if hijri is not None and gregorian is not None:
                expected = HIJRI_EPOCH_CE + hijri * HIJRI_TO_GREGORIAN_SLOPE
                if abs(gregorian - expected) > GREGORIAN_TOLERANCE_YEARS:
                    flag(row, f"{label}_gregorian_disagrees_with_hijri",
                         {f"{label}_hijri": hijri, f"{label}_gregorian": gregorian, "expected_gregorian": round(expected, 1)})
        if (row.get("death_reason") or "").strip() == "Natural" and death is None and death_ce is None:
            kinds["death_reason_natural_without_any_death_date"] += 1
        teachers, students = teacher_sets[row["scholar_indx"]], student_sets[row["scholar_indx"]]
        missing = [i for i in teachers | students if i not in known_ids]
        if missing:
            dangling += 1
        for teacher in teachers:
            if teacher in student_sets and row["scholar_indx"] not in student_sets[teacher]:
                asymmetric += 1
        degree_rows.append((row["scholar_indx"], row["name"], len(teachers), len(students),
                            parse_generation(row.get("grade")), death))
    # Spikes: a death year whose count is >= 3x the mean of its neighbours (round-number defaulting).
    spikes = {}
    for year, count in death_hijri_counts.items():
        neighbours = [death_hijri_counts.get(year + d, 0) for d in (-2, -1, 1, 2)]
        mean = sum(neighbours) / 4
        if year > 0 and count >= 20 and count >= SPIKE_FACTOR * max(mean, 1):
            spikes[year] = {"count": count, "neighbour_mean": round(mean, 1)}
    exact_name_owners = defaultdict(set)
    regen = common.load_regen()
    for row in rows:
        arabic = regen._extract_arabic_name(row["name"])
        if arabic:
            exact_name_owners[regen.narrator_normalize(arabic)].add(row["scholar_indx"])
    duplicates = {n: sorted(ids) for n, ids in exact_name_owners.items() if len(ids) >= 2}

    out = common.output_directory(JOB)
    count = common.write_jsonl(out, "lexicon_defects.jsonl", defects)
    degree_rows.sort(key=lambda r: (-(r[2] + r[3]), int(r[0])))
    with open(out / "narrator_priority.csv", "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rank", "scholar_indx", "name", "teachers_count", "students_count", "graph_degree",
                         "generation", "death_hijri", "basis"])
        for rank, (indx, name, teachers, students, generation, death) in enumerate(degree_rows, 1):
            writer.writerow([rank, indx, name, teachers, students, teachers + students, generation or "",
                             "" if death is None else death, "registry_graph_degree_not_resolved_frequency"])
    coverage = {field: sum(1 for r in rows if (r.get(field) or "NA").strip() not in ("NA", "", "[]"))
                for field in ("birth_date_hijri", "death_date_hijri", "death_date_gregorian", "teachers_inds",
                              "students_inds", "parents")}
    neither = sum(1 for r in rows if to_int(r.get("birth_date_hijri")) is None and to_int(r.get("death_date_hijri")) is None)
    common.write_json(out, "lexicon_defects_summary.json", {
        "header": common.header_object(
            JOB, "python -B datasets/hadith-data/diagnostics/report_narrator_lexicon_defects.py",
            common.input_fingerprints(common.REGISTRY_PATH)),
        "registry_rows": len(rows), "defect_flags": count, "defect_kinds": dict(kinds.most_common()),
        "rows_with_neither_birth_nor_death_hijri": neither,
        "share_with_neither_hijri_year": round(neither / len(rows), 4),
        "field_fill_counts": coverage,
        "death_year_spikes_suspect_defaulting": dict(sorted(spikes.items())),
        "rows_with_graph_ids_not_in_registry": dangling,
        "teacher_links_not_mirrored_in_teachers_students_list": asymmetric,
        "duplicate_normalized_arabic_names": len(duplicates),
        "duplicate_normalized_arabic_names_examples": dict(list(sorted(duplicates.items(), key=lambda kv: -len(kv[1])))[:15]),
        "priority_basis": "teachers_inds + students_inds counts in the lexicon; refresh from resolved-chain frequency after review decisions exist",
        "seconds": round(time.time() - started, 1),
    })
    print({"defects": count, "kinds": dict(kinds), "neither_hijri": neither, "spikes": spikes, "dups": len(duplicates),
           "seconds": round(time.time() - started, 1)})


if __name__ == "__main__":
    main()
