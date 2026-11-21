"""D1 + D3: shape existing grading diagnostics into load-ready `hadith_assessments` candidate rows.

Inputs are the existing diagnostics/grading/ outputs (read only) and the unified corpus (compiler criterion links).
Every row names a grader or compiler, is tradition-scoped, keeps the verbatim Arabic and is `unreviewed`.
Non-rulings are excluded and counted. The dataset-wide label ثابت never becomes a grade_raw (asserted below).
"""

import collections
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import diagnostic_common as common  # noqa: E402

JOB = "grading-recovery"
GRADING_DIR = common.DIAGNOSTICS_DIR / "grading"
IMAMI = GRADING_DIR / "imami_gradings_structured.jsonl"
TIRMIDHI = GRADING_DIR / "tirmidhi_compiler_statements.jsonl"
THABIT = "ثابت"
REVIEW = {"review_state": "unreviewed", "citation_id": None, "grade_canonical": None,
          "grade_canonical_note": "no mapping to a scale is applied here; the loader's mapToCanonical owns that step"}

# Whitespace-free, Persian ya/kaf folded keys of terms that are not rulings.
NON_RULING_CLASSES = {
    "لميخرجه": "not_included_by_grader",
    "لميذكره": "not_included_by_grader",
    "لميذكرعندهشيء": "not_included_by_grader",
    "لميذكرالطريق": "chain_not_given",
    "لميحقق": "not_investigated",
    "لاواسطة": "chain_description_not_ruling",
    "سكتعنه": "grader_silent",
    "كالسابق": "back_reference_only",
    "كالسابقأيضا": "back_reference_only",
    "مثلالسندالسابق": "back_reference_only",
    "بالسندالسابق": "back_reference_only",
}
COMPILERS = {
    " Sahih Bukhari ": ("Muhammad ibn Isma'il al-Bukhari", "Sahih al-Bukhari"),
    " Sahih Muslim ": ("Muslim ibn al-Hajjaj", "Sahih Muslim"),
}


def fold(term):
    folded = (term or "").replace("ی", "ي").replace("ک", "ك")
    for ch in (" ", "‏", "‎", " "):
        folded = folded.replace(ch, "")
    return folded


def imami_rows():
    rows, excluded = [], []
    for line in IMAMI.open(encoding="utf-8"):
        entry = json.loads(line)
        reason = NON_RULING_CLASSES.get(fold(entry["term_ar"]))
        base = {"snapshot_id": entry["id"], "hadith_id": entry["hadith_id"], "source": entry["source"], "snapshot_line": entry["line"]}
        if reason:
            excluded.append({**base, "grader": entry["grader"], "term_ar_verbatim": entry["term_ar"], "reason": reason, "raw": entry["raw"]})
            continue
        rows.append({
            "candidate_id": f"assessment-cand:{entry['id']}:imami:gradings_full:{entry['entry_no']}",
            **base, "record_id_candidate": None,
            "record_id_note": "Thaqalayn record_id is derived at load by regen_unified_csvs.thaqalayn_source_record_id; the preserved snapshot has no record_id column",
            "tradition_id": "imami", "grade_scheme": "imami_4tier", "ordinal": entry["entry_no"], "kind": "cited_ruling",
            "grader": entry["grader"], "grade_raw": entry["term_ar"], "grade_detail": None,
            "citation_raw": entry["raw"][entry["raw"].find("(") + 1: entry["raw"].rfind(")")] if "(" in entry["raw"] else None,
            "cited_work": entry["cited_work"], "cited_volume": entry["volume"], "cited_page": entry["page"],
            "source_field": "gradings_full", "source_cell_verbatim": entry["raw"], **REVIEW,
        })
    return rows, excluded


def tirmidhi_rows():
    rows, held = [], []
    for line in TIRMIDHI.open(encoding="utf-8"):
        s = json.loads(line)
        base = {"snapshot_id": s["id"], "hadith_id": s["hadith_id"], "source": s["source"], "snapshot_line": s["line"],
                "statement_no": s["statement_no"], "statement_ar_verbatim": s["statement_ar"],
                "char_start": s["char_start"], "char_end": s["char_end"]}
        if not s["terms_found"]:
            held.append({**base, "reason": "no_grade_term_in_statement"})
        elif s["speaker_hint_other_authority"]:
            held.append({**base, "reason": "another_authority_quoted_not_the_compiler", "terms_found": s["terms_found"]})
        elif not s["preceded_by_qala_abu_isa"]:
            held.append({**base, "reason": "speaker_not_marked_as_abu_isa", "terms_found": s["terms_found"]})
        else:
            rows.append({
                "candidate_id": f"assessment-cand:{s['id']}:sunni:text_ar:{s['statement_no']}",
                **base, "record_id_candidate": f"k6:{s['id']}", "tradition_id": "sunni", "grade_scheme": "sunni_7tier",
                "ordinal": s["statement_no"], "kind": "compiler_statement",
                "grader": "Abu 'Isa Muhammad ibn 'Isa al-Tirmidhi (compiler of Jami' al-Tirmidhi)",
                "grade_raw": " ".join(s["terms_found"]), "terms_found_in_source_order": s["terms_found"], "grade_detail": None,
                "citation_raw": None, "cited_work": "Jami' al-Tirmidhi", "cited_volume": None, "cited_page": None,
                "source_field": "text_ar", "source_cell_verbatim": s["statement_ar"], **REVIEW,
                "attribution_basis": "statement follows the phrase قال أبو عيسى in the report's own Arabic text",
            })
    return rows, held


def criterion_links():
    """D3: per-report link to the work-level compiler criterion basis (never a verdict)."""
    counts = collections.Counter()
    for _, row in common.iter_corpus_rows():
        compiler = COMPILERS.get(row["source"])
        if not compiler:
            continue
        counts[row["source"].strip()] += 1
        yield {
            "candidate_id": f"assessment-cand:{row['id']}:sunni:compiler_criterion:0",
            "snapshot_id": row["id"], "hadith_id": row["hadith_id"], "source": row["source"].strip(),
            "record_id_candidate": f"k6:{row['id']}", "tradition_id": "sunni", "grade_scheme": "sunni_7tier", "ordinal": 0,
            "kind": "compiler_criterion", "grader": compiler[0], "grade_raw": f"inclusion in {compiler[1]} under its compiler's stated criterion",
            "grade_canonical": None, "criterion_basis_id": "criterion:" + compiler[1].lower().replace(" ", "-").replace("'", ""),
            "has_arabic_text": bool(row["text_ar"].strip()), "source_field": "collection_membership",
            "review_state": "unreviewed", "citation_id": None,
        }


def main():
    out_dir = common.output_directory(JOB)
    inputs = common.input_fingerprints(IMAMI, TIRMIDHI, common.CORPUS_PATH)
    imami, imami_excluded = imami_rows()
    tirmidhi, tirmidhi_held = tirmidhi_rows()
    counts = {
        "hadith_assessments_imami_cited_ruling.jsonl": common.write_jsonl(out_dir, "hadith_assessments_imami_cited_ruling.jsonl", imami),
        "imami_non_rulings_excluded.jsonl": common.write_jsonl(out_dir, "imami_non_rulings_excluded.jsonl", imami_excluded),
        "hadith_assessments_tirmidhi_compiler_statement.jsonl": common.write_jsonl(out_dir, "hadith_assessments_tirmidhi_compiler_statement.jsonl", tirmidhi),
        "tirmidhi_statements_held_back.jsonl": common.write_jsonl(out_dir, "tirmidhi_statements_held_back.jsonl", tirmidhi_held),
        "compiler_criterion_row_links.jsonl.gz": common.write_jsonl(out_dir, "compiler_criterion_row_links.jsonl.gz", criterion_links(), gzipped=True),
    }
    criterion_by_work = collections.Counter()
    with __import__("gzip").open(out_dir / "compiler_criterion_row_links.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            criterion_by_work[json.loads(line)["source"]] += 1
    basis = [
        {"criterion_basis_id": "criterion:sahih-al-bukhari", "work": "Sahih al-Bukhari", "compiler": "Muhammad ibn Isma'il al-Bukhari",
         "reports_in_unified_corpus": criterion_by_work["Sahih Bukhari"], "criterion_statement_ar": None,
         "citation_needed": "the compiler's stated conditions must be cited from a reviewed edition; none is stored locally",
         "suggested_sources_unverified": ["Ibn Hajar, Hady al-Sari (muqaddima of Fath al-Bari)", "al-Hazimi, Shurut al-A'imma al-Khamsa"]},
        {"criterion_basis_id": "criterion:sahih-muslim", "work": "Sahih Muslim", "compiler": "Muslim ibn al-Hajjaj",
         "reports_in_unified_corpus": criterion_by_work["Sahih Muslim"], "criterion_statement_ar": None,
         "citation_needed": "the compiler's stated conditions must be cited from a reviewed edition; none is stored locally",
         "suggested_sources_unverified": ["Muslim, Muqaddima to the Sahih", "al-Nawawi, Sharh Sahih Muslim (muqaddima)"]},
    ]
    counts["compiler_criterion_basis.jsonl"] = common.write_jsonl(out_dir, "compiler_criterion_basis.jsonl", basis)
    all_rows = imami + tirmidhi
    assert all(THABIT not in row["grade_raw"] for row in all_rows), "ثابت leaked into grade_raw"
    term_after = collections.Counter(r["grade_raw"] for r in imami)
    summary = {
        "header": common.header_object(JOB, "python -B datasets/hadith-data/diagnostics/grading-recovery/build_hadith_assessment_rows.py", inputs),
        "output_rows": counts,
        "imami": {"entries_in_existing_parse": len(imami) + len(imami_excluded), "load_ready_cited_rulings": len(imami),
                  "excluded_non_rulings": len(imami_excluded),
                  "excluded_by_reason": dict(collections.Counter(r["reason"] for r in imami_excluded)),
                  "excluded_by_term": dict(collections.Counter(r["term_ar_verbatim"] for r in imami_excluded).most_common(12)),
                  "load_ready_by_grader": dict(collections.Counter(r["grader"] for r in imami)),
                  "hadith_rows_with_at_least_one_ruling": len({r["snapshot_id"] for r in imami}),
                  "hadith_rows_with_two_or_more_rulings": sum(1 for n in collections.Counter(r["snapshot_id"] for r in imami).values() if n > 1),
                  "hadith_rows_where_the_same_grader_rules_twice": sum(
                      1 for n in collections.Counter((r["snapshot_id"], r["grader"]) for r in imami).values() if n > 1),
                  "load_ready_with_volume_page": sum(1 for r in imami if r["cited_page"] is not None)},
        "tirmidhi": {"statements_in_existing_extraction": len(tirmidhi) + len(tirmidhi_held), "load_ready": len(tirmidhi),
                     "held_back_by_reason": dict(collections.Counter(r["reason"] for r in tirmidhi_held)),
                     "tirmidhi_rows_with_load_ready_statement": len({r["snapshot_id"] for r in tirmidhi}),
                     "term_sets": dict(collections.Counter(r["grade_raw"] for r in tirmidhi).most_common(10))},
        "compiler_criterion": {r["work"]: r["reports_in_unified_corpus"] for r in basis},
        "thabit_exclusion_check": "no grade_raw in any row written here equals or contains ثابت (assertion at write time)",
    }
    common.write_json(out_dir, "hadith_assessment_summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "header"}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
