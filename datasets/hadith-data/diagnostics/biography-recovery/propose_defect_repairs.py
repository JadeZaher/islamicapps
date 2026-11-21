"""Part C: classify the existing lexicon defect flags and propose dispositions (proposals only).

Reads diagnostics/biography/lexicon_defects.jsonl (existing J8 output) and the lexicon; changes nothing.
"""

import collections
import csv
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import diagnostic_common as common  # noqa: E402
import lexicon_raw_parsing as parsing  # noqa: E402

JOB = "biography-recovery"
DEFECTS = common.DIAGNOSTICS_DIR / "biography" / "lexicon_defects.jsonl"
LEXICON = common.REGISTRY_PATH
STATUS = "repair_proposal_unreviewed"
BH_LOADER_NOTE = ("src/scripts/lib/regen/io.ts:351-361 parseHijriYear already restores the BH sign (-Math.abs) when the raw "
                  "birth/death cell contains BH, so the typed value loaded into the graph is negative; the J8 flag compares the "
                  "unsigned CSV column and is a false positive for rows whose raw cell carries BH")


def present(value):
    return value not in ("", "NA", None)


def span(cell, era):
    return parsing.parse_place_cell(cell)["date"]["calendars"].get(era) if present(cell) else None


def classify_inverted(row):
    birth, death = row["birth_date_place"], row["death_date_place"]
    b_bh, d_bh = span(birth, "BH"), span(death, "BH")
    b_ah, d_ah = span(birth, "AH"), span(death, "AH")
    if b_bh and (d_ah or d_bh):
        if d_bh and abs(d_bh["values_as_written"][0]) > abs(b_bh["values_as_written"][0]):
            return "birth_after_death_even_with_BH_sign", "keep_as_disputed", None
        corrected = {"birth_year_hijri_signed": b_bh["year_min"], "death_year_hijri_signed":
                     (d_bh or d_ah)["year_min"] if d_bh else d_ah["year_min"]}
        return "calendar_confusion_BH_sign_dropped", "correct_from_raw_text", corrected
    if b_ah and d_ah and b_ah["year_min"] > d_ah["year_min"]:
        return "swap_or_typo_candidate_both_AH", "keep_as_disputed", None
    return "unclassified", "keep_as_disputed", None


def main():
    out_dir = common.output_directory(JOB)
    inputs = common.input_fingerprints(LEXICON, DEFECTS)
    rows = {}
    with LEXICON.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        previous = reader.line_num
        for number, row in enumerate(reader, 1):
            row["_locator"] = {"lexicon_row_number": number, "lexicon_csv_line": previous + 1}
            previous = reader.line_num
            rows[row["scholar_indx"]] = row

    proposals, counts = [], collections.Counter()
    for line in DEFECTS.open(encoding="utf-8"):
        flag = json.loads(line)
        row = rows[flag["scholar_indx"]]
        base = {"scholar_indx": flag["scholar_indx"], **row["_locator"], "defect_kind": flag["defect"],
                "birth_date_place_verbatim": row["birth_date_place"], "death_date_place_verbatim": row["death_date_place"],
                "parsed": {c: row[c] for c in ("birth_date_hijri", "birth_date_gregorian", "death_date_hijri", "death_date_gregorian")},
                "status": STATUS}
        if flag["defect"] == "inverted_birth_death_hijri":
            cls, disposition, corrected = classify_inverted(row)
            proposals.append({**base, "classification": cls, "proposed_disposition": disposition,
                              "proposed_values": corrected,
                              "evidence": "raw cell carries an explicit BH era token; the parsed column stored the bare magnitude",
                              "loader_note": BH_LOADER_NOTE if cls == "calendar_confusion_BH_sign_dropped" else None})
            counts[(flag["defect"], cls)] += 1
        elif flag["defect"] == "death_hijri_zero_sentinel_suspected":
            marker = parsing.parse_generation_cell(row["grade"])
            qualifier = "after" if "after" in row["death_date_place"].lower() else "none"
            cls = f"zero_placeholder_with_{qualifier}_qualifier"
            proposals.append({**base, "classification": cls, "proposed_disposition": "blank_it",
                              "proposed_values": None,
                              "alternative_anchor_from_other_cell": {"grade_cell": row["grade"], "category": marker["category"],
                                                                      "century_ah": marker["century_ah"],
                                                                      "generation_number": marker["generation_number"]},
                              "evidence": "year 0 does not exist in the hijri calendar; the cell otherwise carries no date"})
            counts[(flag["defect"], cls, marker["category"])] += 1
        elif flag["defect"] in ("birth_gregorian_disagrees_with_hijri", "death_gregorian_disagrees_with_hijri"):
            predicate_cell = row["birth_date_place"] if flag["defect"].startswith("birth") else row["death_date_place"]
            parsed_cell = parsing.parse_place_cell(predicate_cell)
            date = parsed_cell["date"]
            if any(s["era"] == "BH" for s in date["calendars"].values()):
                cls, disposition = "calendar_confusion_BH_sign_dropped", "correct_from_raw_text"
            elif any(f == "range_end_expanded_from_abbreviation" for f in date["flags"]):
                cls, disposition = "gregorian_range_truncated_by_parser", "correct_from_raw_text"
            elif any(s["relation"] != "single" for s in date["calendars"].values()):
                cls, disposition = "alternatives_mixed_between_calendars", "keep_as_disputed"
            else:
                cls, disposition = "gregorian_hijri_pair_inconsistent_in_source_text", "keep_as_disputed"
            proposals.append({**base, "classification": cls, "proposed_disposition": disposition,
                              "loader_note": BH_LOADER_NOTE if cls == "calendar_confusion_BH_sign_dropped" else None,
                              "raw_calendars": {k: {"year_min": v["year_min"], "year_max": v["year_max"], "relation": v["relation"]}
                                                 for k, v in date["calendars"].items()},
                              "status": STATUS})
            counts[(flag["defect"], cls)] += 1

    n_proposals = common.write_jsonl(out_dir, "defect_repair_proposals.jsonl", proposals)

    # death_reason: "Natural" default, and reasons the parsed column drops or merges.
    natural_rows, reason_loss, natural_class = [], collections.Counter(), collections.Counter()
    for row in rows.values():
        death = row["death_date_place"]
        parsed_cell = parsing.parse_place_cell(death) if present(death) else None
        raw_reason = parsed_cell["reason_text"] if parsed_cell else None
        has_date = bool(parsed_cell and parsed_cell["date"]["present"])
        has_place = bool(parsed_cell and parsed_cell["places"])
        if raw_reason:
            base_reason = raw_reason.split("(")[0].strip()
            if base_reason != row["death_reason"]:
                reason_loss[(raw_reason if len(raw_reason) < 25 else base_reason, row["death_reason"])] += 1
        if row["death_reason"] == "Natural" and not (present(row["death_date_hijri"]) or present(row["death_date_gregorian"])):
            cls = ("template_default_no_date_no_place" if not has_place else "no_date_place_only")
            natural_class[cls] += 1
            natural_rows.append({
                "scholar_indx": row["scholar_indx"], **row["_locator"], "classification": cls,
                "death_date_place_verbatim": death, "parsed_death_reason": "Natural",
                "proposed_disposition": "blank_it" if cls == "template_default_no_date_no_place" else "keep_as_disputed",
                "proposed_value": "unknown", "status": STATUS})
    n_natural = common.write_jsonl(out_dir, "death_reason_natural_default_proposals.jsonl.gz", natural_rows, gzipped=True)

    summary = {
        "header": common.header_object(JOB, "python -B datasets/hadith-data/diagnostics/biography-recovery/propose_defect_repairs.py", inputs),
        "proposal_rows": n_proposals,
        "classification_counts": {" | ".join(map(str, k)): n for k, n in sorted(counts.items(), key=lambda kv: -kv[1])},
        "natural_default_rows": n_natural,
        "natural_default_classification": dict(natural_class),
        "death_reason_raw_vs_parsed_differences": {f"raw `{r}` -> parsed `{p}`": n for (r, p), n in reason_loss.most_common(20)},
    }
    common.write_json(out_dir, "defect_repair_summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "header"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
