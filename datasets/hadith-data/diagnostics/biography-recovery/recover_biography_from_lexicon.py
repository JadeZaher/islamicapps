"""Part A: recover biography and assessment candidates from the free-text columns of all_rawis.csv.

Streams the lexicon once. Writes only inside diagnostics/biography-recovery/. Every candidate keeps the
verbatim source cell, its column and its row locator, and is marked unreviewed. Nothing is promoted.
"""

import collections
import csv
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import diagnostic_common as common  # noqa: E402  (read-only reuse of the shared helpers)
import lexicon_raw_parsing as parsing  # noqa: E402

JOB = "biography-recovery"
REVIEW_STATE = "unreviewed_lexicon_candidate"
SOURCE_STATUS = "source_status_unknown"
LEXICON = common.REGISTRY_PATH
TAG_MARKERS = {"Sahaba", "1st Century", "Early Muslim", "Late Muslim", "Child"}
EXPECTED_TERMS = {
    "Thiqah": {"ثقة", "ثقة ثبت", "ثقة حافظ", "ثقة متقن", "ثقة فقيه"},
    "Sadooq": {"صدوق"},
    "Maqbool": {"مقبول"},
    "Weak": {"ضعيف"},
    "Abandoned": {"متروك"},
    "Unknown-Majhool": {"مجهول"},
}
PARSED_COLUMNS = {
    ("birth_year", "hijri"): "birth_date_hijri",
    ("birth_year", "gregorian"): "birth_date_gregorian",
    ("death_year", "hijri"): "death_date_hijri",
    ("death_year", "gregorian"): "death_date_gregorian",
}


def present(value):
    return value not in ("", "NA", None)


def parsed_int(value):
    return int(value) if present(value) and value.lstrip("-").isdigit() else None


def precision_of(span, qualifiers):
    if "unresolved_after_and_before" in qualifiers:
        return "unresolved_qualifier"
    if "after" in qualifiers:
        return "lower_bound"
    if "before" in qualifiers:
        return "upper_bound"
    if span["relation"] == "range":
        return "range"
    if span["relation"] == "alternatives":
        return "alternatives"
    return "circa" if ("circa" in qualifiers or "estimated" in qualifiers) else "exact"


def relation_to_parsed(span, precision, parsed_value):
    if parsed_value is None:
        return "new_not_in_parsed_columns"
    values = span["values_as_written"]
    if span["era"] == "BH":
        return "era_sign_lost_in_parsed" if parsed_value in values else "contradicts_parsed"
    if parsed_value not in values:
        return "contradicts_parsed"
    return "agrees" if precision == "exact" and len(values) == 1 else "parsed_keeps_one_value_loses_qualifier_or_range"


def date_candidates(row, locator, predicate, column, summary_bucket):
    cell = row[column]
    if not present(cell):
        return []
    parsed = parsing.parse_place_cell(cell)
    out = []
    for era_key, span in parsed["date"]["calendars"].items():
        precision = precision_of(span, parsed["date"]["qualifiers"])
        parsed_column = PARSED_COLUMNS.get((predicate, span["calendar"]))
        parsed_value = parsed_int(row[parsed_column]) if parsed_column else None
        relation = relation_to_parsed(span, precision, parsed_value)
        sentinel = span["values_as_written"] == [0]
        out.append({
            **locator,
            "predicate": predicate,
            "calendar": span["calendar"],
            "era": span["era"],
            "year_min": span["year_min"],
            "year_max": span["year_max"],
            "values_as_written": span["values_as_written"],
            "precision": "zero_placeholder_suspected" if sentinel else precision,
            "qualifiers": parsed["date"]["qualifiers"],
            "parser_flags": parsed["date"]["flags"],
            "source_column": column,
            "source_cell_verbatim": cell,
            "parsed_column": parsed_column,
            "parsed_column_value": parsed_value,
            "relation_to_parsed_column": relation,
            "review_state": REVIEW_STATE,
            "source_status": SOURCE_STATUS,
            "citation_id": None,
        })
    return out


def place_candidates(row, locator, predicate, column, parsed_column):
    cell = row[column]
    if not present(cell):
        return []
    parsed = parsing.parse_place_cell(cell)
    parsed_text = row[parsed_column] if present(row[parsed_column]) else None
    out = []
    for index, place in enumerate(parsed["places"], 1):
        out.append({
            **locator, "predicate": predicate, "ordinal": index, "value_text": place,
            "day_month_notes": parsed["day_month_notes"],
            "source_column": column, "source_cell_verbatim": cell,
            "parsed_column": parsed_column, "parsed_column_value": parsed_text,
            "relation_to_parsed_column": "new_not_in_parsed_columns" if not parsed_text
            else ("agrees" if place in parsed_text else "differs_from_parsed"),
            "review_state": REVIEW_STATE, "source_status": SOURCE_STATUS, "citation_id": None,
        })
    return out


def residence_candidates(row, locator):
    cell = row["places_of_stay"]
    if not present(cell):
        return []
    return [{
        **locator, "predicate": "residence", "ordinal": index, "value_text": place.strip(),
        "source_column": "places_of_stay", "source_cell_verbatim": cell,
        "parsed_column": None, "parsed_column_value": None,
        "relation_to_parsed_column": "new_not_in_parsed_columns",
        "review_state": REVIEW_STATE, "source_status": SOURCE_STATUS, "citation_id": None,
    } for index, place in enumerate(cell.split(","), 1) if place.strip()]


def tabaqah_candidates(row, locator):
    out = []
    cell = row["grade"]
    if present(cell):
        marker = parsing.parse_generation_cell(cell)
        out.append({
            **locator, "predicate": "tabaqah", "value_text": cell.strip(),
            "category": marker["category"], "century_ah": marker["century_ah"],
            "generation_number": marker["generation_number"],
            "other_bracket_labels": marker["other_bracket_labels"],
            "source_column": "grade", "source_cell_verbatim": cell,
            "parsed_column": None, "parsed_column_value": None,
            "relation_to_parsed_column": "new_not_in_parsed_columns",
            "review_state": REVIEW_STATE, "source_status": SOURCE_STATUS, "citation_id": None,
        })
    if present(row["tags"]):
        for tag in row["tags"].split(" , "):
            label = tag.split("[")[0].strip()
            if label in TAG_MARKERS:
                out.append({
                    **locator, "predicate": "tabaqah", "value_text": label, "category": "tag_marker",
                    "century_ah": 1 if label == "1st Century" else None, "generation_number": None,
                    "other_bracket_labels": [],
                    "source_column": "tags", "source_cell_verbatim": row["tags"],
                    "parsed_column": None, "parsed_column_value": None,
                    "relation_to_parsed_column": "new_not_in_parsed_columns",
                    "review_state": REVIEW_STATE, "source_status": SOURCE_STATUS, "citation_id": None,
                })
    return out


def assessment_candidates(row, locator):
    cell = row["area_of_interest"]
    if not present(cell):
        return None
    parsed = parsing.parse_area_of_interest(cell)
    if not parsed["parsed"] or not (parsed["english_grade_label"] or parsed["term_ar"]):
        return None
    term = parsed["term_ar"]
    return {
        **locator,
        "kind": "companion_status_label" if term == "صحابي" else "lexicon_grade_label",
        "term_ar": term,
        "english_grade_label": parsed["english_grade_label"],
        "book_symbols_ar": parsed["symbols_ar"],
        "area_of_interest_text": parsed["area"],
        "critic": None,
        "critic_note": "unnamed in the cell; the '[ symbols - term ]' layout matches the Taqrib al-Tahdhib convention "
                       "(format resemblance only, not verified, not an attribution)",
        "tradition_id": None,
        "tradition_note": "lexicon is cross-tradition and not tradition-scoped (datasets/sources/narrator-lexicon.md)",
        "source_column": "area_of_interest", "source_cell_verbatim": cell,
        "review_state": REVIEW_STATE, "source_status": SOURCE_STATUS, "citation_id": None,
    }


def marker_tensions(locator, marker, death_values):
    flags = []
    if not death_values:
        return flags
    year = death_values[0]
    if marker["category"] == "companion" and year > 110:
        flags.append("companion_marker_but_death_year_after_110_AH")
    if marker["century_ah"] and marker["category"] == "century_marker" and year < (marker["century_ah"] - 1) * 100 + 1:
        flags.append("century_marker_later_than_death_year")
    return [{**locator, "tension": flag, "marker": marker["verbatim"], "death_year_candidate_hijri": year,
             "review_state": REVIEW_STATE} for flag in flags]


def main():
    out_dir = common.output_directory(JOB)
    inputs = common.input_fingerprints(LEXICON)
    assertions, assessments, discrepancies, tensions = [], [], [], []
    counters = collections.Counter()
    before_after = collections.defaultdict(lambda: [0, 0])  # name -> [parsed-only, parsed+recovered]
    relation_counts = collections.Counter()
    qualifier_counts = collections.Counter()
    pair_counts = collections.Counter()
    unexpected_pairs = collections.Counter()
    gain_samples = collections.defaultdict(list)

    with LEXICON.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        previous_line = reader.line_num
        for row_number, row in enumerate(reader, 1):
            csv_line = previous_line + 1
            previous_line = reader.line_num
            counters["rows"] += 1
            locator = {"scholar_indx": row["scholar_indx"], "lexicon_row_number": row_number, "lexicon_csv_line": csv_line}
            produced = []
            produced += date_candidates(row, locator, "birth_year", "birth_date_place", None)
            produced += date_candidates(row, locator, "death_year", "death_date_place", None)
            birth_places = place_candidates(row, locator, "birth_place", "birth_date_place", "birth_place")
            death_places = place_candidates(row, locator, "death_place", "death_date_place", "death_place")
            residence = residence_candidates(row, locator)
            tabaqah = tabaqah_candidates(row, locator)
            produced += birth_places + death_places + residence + tabaqah

            # coverage: parsed-only versus parsed plus recovered
            parsed_death = any(parsed_int(row[c]) not in (None, 0) for c in ("death_date_hijri", "death_date_gregorian"))
            parsed_birth = any(parsed_int(row[c]) not in (None, 0) for c in ("birth_date_hijri", "birth_date_gregorian"))
            rec_death = any(a["predicate"] == "death_year" and a["precision"] != "zero_placeholder_suspected" for a in produced)
            rec_birth = any(a["predicate"] == "birth_year" and a["precision"] != "zero_placeholder_suspected" for a in produced)
            rec_death_hijri_gap = any(a["predicate"] == "death_year" and a["calendar"] == "hijri"
                                      and a["relation_to_parsed_column"] == "new_not_in_parsed_columns"
                                      and a["precision"] != "zero_placeholder_suspected" for a in produced)
            rec_birth_hijri_gap = any(a["predicate"] == "birth_year" and a["calendar"] == "hijri"
                                      and a["relation_to_parsed_column"] == "new_not_in_parsed_columns" for a in produced)
            rec_death_any_gap = any(a["predicate"] == "death_year" and a["relation_to_parsed_column"] == "new_not_in_parsed_columns"
                                    and a["calendar"] != "unspecified" and a["precision"] != "zero_placeholder_suspected" for a in produced)
            def tally(name, parsed_flag, recovered_flag):
                before_after[name][0] += int(parsed_flag)
                before_after[name][1] += int(parsed_flag or recovered_flag)
            tally("death_year_any_calendar", parsed_death, rec_death)
            tally("birth_year_any_calendar", parsed_birth, rec_birth)
            tally("any_birth_or_death_year", parsed_death or parsed_birth, rec_death or rec_birth)
            era_marker = any(a["predicate"] == "tabaqah" and (a["century_ah"] or a["category"] in ("companion", "follower", "successor_of_followers", "prophet"))
                             for a in tabaqah)
            tally("any_year_or_generation_marker", parsed_death or parsed_birth, rec_death or rec_birth or bool(tabaqah))
            tally("generation_or_tabaqah_marker", False, bool(tabaqah))
            tally("numeric_generation_number", False, any(a.get("generation_number") for a in tabaqah))
            parsed_place = present(row["birth_place"]) and row["birth_place"] != "" or (present(row["death_place"]) and row["death_place"] != "")
            tally("any_place_birth_death_or_residence", parsed_place, bool(birth_places or death_places or residence))
            tally("residence_place", False, bool(residence))
            if rec_death_any_gap:
                counters["narrators_gaining_a_death_year_not_in_parsed_columns"] += 1
            if rec_death_hijri_gap:
                counters["narrators_gaining_a_hijri_death_year"] += 1
            if rec_birth_hijri_gap:
                counters["narrators_gaining_a_hijri_birth_year"] += 1

            for a in produced:
                if a["predicate"] in ("birth_year", "death_year"):
                    relation_counts[(a["predicate"], a["relation_to_parsed_column"])] += 1
                    for q in a["qualifiers"]:
                        qualifier_counts[(a["predicate"], q)] += 1
                    if a["relation_to_parsed_column"] not in ("agrees", "new_not_in_parsed_columns"):
                        discrepancies.append({k: a[k] for k in (
                            "scholar_indx", "lexicon_row_number", "lexicon_csv_line", "predicate", "calendar", "era",
                            "values_as_written", "year_min", "year_max", "precision", "qualifiers", "parser_flags",
                            "source_column", "source_cell_verbatim", "parsed_column", "parsed_column_value",
                            "relation_to_parsed_column", "review_state")})
                    if len(gain_samples[(a["predicate"], a["relation_to_parsed_column"])]) < 3:
                        gain_samples[(a["predicate"], a["relation_to_parsed_column"])].append(a["source_cell_verbatim"])
                else:
                    relation_counts[(a["predicate"], a["relation_to_parsed_column"])] += 1
            assertions.extend(produced)

            death_values = [a["values_as_written"][0] for a in produced
                            if a["predicate"] == "death_year" and a["calendar"] == "hijri" and a["era"] == "AH"
                            and a["precision"] in ("exact", "circa")]
            if present(row["grade"]):
                tensions += marker_tensions(locator, parsing.parse_generation_cell(row["grade"]), death_values)

            assessment = assessment_candidates(row, locator)
            if assessment:
                assessments.append(assessment)
                pair_counts[(assessment["english_grade_label"], assessment["term_ar"])] += 1
                label = assessment["english_grade_label"]
                if label and assessment["term_ar"] and assessment["term_ar"] not in EXPECTED_TERMS.get(label, set()):
                    unexpected_pairs[(label, assessment["term_ar"])] += 1

    n_assertions = common.write_jsonl(out_dir, "biographical_assertion_candidates.jsonl", assertions)
    n_assess = common.write_jsonl(out_dir, "narrator_assessment_candidates.jsonl", assessments)
    n_disc = common.write_jsonl(out_dir, "raw_vs_parsed_discrepancies.jsonl", discrepancies)
    n_tension = common.write_jsonl(out_dir, "marker_vs_death_year_tensions.jsonl", tensions)

    predicate_counts = collections.Counter(a["predicate"] for a in assertions)
    narrators_with_assessment = len({a["scholar_indx"] for a in assessments})
    with_arabic = sum(1 for a in assessments if a["term_ar"])
    summary = {
        "header": common.header_object(JOB, "python -B datasets/hadith-data/diagnostics/biography-recovery/recover_biography_from_lexicon.py", inputs),
        "lexicon_rows": counters["rows"],
        "correction_to_task_premise": "the `grade` column holds a generation/class marker (Companion, Follower, "
                                      "'3rd Century AH [10th generation]'), not a verdict; verdict-like labels live in `area_of_interest`.",
        "coverage_before_after": {k: {"parsed_columns_only": v[0], "parsed_plus_recovered": v[1], "gain": v[1] - v[0],
                                      "before_pct": round(100 * v[0] / counters["rows"], 1),
                                      "after_pct": round(100 * v[1] / counters["rows"], 1)} for k, v in before_after.items()},
        "narrators_gaining_a_death_year_not_in_parsed_columns": counters["narrators_gaining_a_death_year_not_in_parsed_columns"],
        "narrators_gaining_a_hijri_death_year": counters["narrators_gaining_a_hijri_death_year"],
        "narrators_gaining_a_hijri_birth_year": counters["narrators_gaining_a_hijri_birth_year"],
        "candidate_rows_by_predicate": dict(predicate_counts),
        "relation_to_parsed_columns": {f"{p}|{r}": n for (p, r), n in sorted(relation_counts.items())},
        "qualifier_counts": {f"{p}|{q}": n for (p, q), n in sorted(qualifier_counts.items())},
        "discrepancy_examples_verbatim": {f"{p}|{r}": s for (p, r), s in gain_samples.items()},
        "assessment_candidates": {
            "rows": n_assess, "narrators": narrators_with_assessment, "with_arabic_term": with_arabic,
            "english_label_only": n_assess - with_arabic,
            "label_term_pairs": {f"{l}|{t}": n for (l, t), n in pair_counts.most_common(40)},
            "unexpected_label_term_pairs_top": {f"{l}|{t}": n for (l, t), n in unexpected_pairs.most_common(15)},
        },
        "marker_vs_death_year_tensions": n_tension,
        "output_rows": {"biographical_assertion_candidates.jsonl": n_assertions, "narrator_assessment_candidates.jsonl": n_assess,
                        "raw_vs_parsed_discrepancies.jsonl": n_disc, "marker_vs_death_year_tensions.jsonl": n_tension},
    }
    common.write_json(out_dir, "recovery_summary.json", summary)
    print(f"candidates {n_assertions}, assessments {n_assess}, discrepancies {n_disc}, tensions {n_tension}")


if __name__ == "__main__":
    main()
