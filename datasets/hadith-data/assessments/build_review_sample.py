#!/usr/bin/env python3
"""Review artefacts for the consolidated rows: the 785 held-back Tirmidhi statements' final disposition, a stratified
60-row sample for a reader's judgement, and a blank 150-row review worksheet. Deterministic (fixed seeds).

    python -B datasets/hadith-data/assessments/build_review_sample.py
"""

import collections
import csv
import gzip
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import assessment_logic as L  # noqa: E402

csv.field_size_limit(10 ** 9)
HADITHS = HERE.parent / "development" / "pg-load-2026-11-21" / "projection-v3" / "canonical" / "hadiths.csv"
OLD_HELD = HERE.parent / "diagnostics" / "grading-recovery" / "tirmidhi_statements_held_back.jsonl"
STRATA_REPORTS = {"cited_ruling_in_commentary": 8, "compiler_statement_in_report_text|sunni:tirmidhi": 8,
                  "compiler_statement_in_report_text|other": 6, "compiler_statement_in_closing_column": 5,
                  "ruling_quoted_by_compiler": 3}
STRATA_NARRATORS = {"rijal_entry_verdict|ibn_hajar_taqrib": 5, "critic_quoted_in_rijal_work": 8,
                    "rijal_entry_verdict|imami": 6, "dataset_record_of_critic_statement": 7, "listed_in_work": 2,
                    "narrator_lexicon_source_not_stated": 2}
BLANK = {"reviewer": "", "term_matches_passage (yes/no/doubtful)": "", "attribution_correct (yes/no/doubtful)": "",
         "attached_to_right_report_or_narrator (yes/no/doubtful)": "", "canonical_ok (yes/no/n.a.)": "", "notes": ""}


def read(name):
    with gzip.open(HERE / name, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def report_stratum(row):
    if row["basis_kind"] == "compiler_statement_in_report_text":
        return row["basis_kind"] + ("|sunni:tirmidhi" if row["work"] == "sunni:tirmidhi" else "|other")
    return row["basis_kind"]


def narrator_stratum(row):
    if row["basis_kind"] == "rijal_entry_verdict":
        return "rijal_entry_verdict|" + ("ibn_hajar_taqrib" if row.get("rijal_work_key") == "ibn_hajar_taqrib" else "imami")
    return row["basis_kind"]


def draw(rows, strata, key, rng):
    grouped = collections.defaultdict(list)
    for row in rows:
        grouped[key(row)].append(row)
    out = []
    for stratum, size in strata.items():
        pool = sorted(grouped.get(stratum, []), key=lambda r: r["id"])
        out += [(stratum, r) for r in rng.sample(pool, min(size, len(pool)))]
    return out


def context(row, texts):
    citation = row.get("citation") or {}
    if "hadith_id" in row:
        text = texts.get(row["hadith_id"], "")
        span = citation.get("char_span")
        if span:
            return text[max(0, span[0] - 220):span[0]] + " ⟦" + text[span[0]:span[1]] + "⟧"
        return text[:260]
    return (row.get("entry_head_ar") or row.get("quote_ar") or "")[:300]


def flat(stratum, row, texts):
    citation = row.get("citation") or {}
    is_report = "hadith_id" in row
    return {
        "id": row["id"], "stratum": stratum, "attached_to": row.get("hadith_id") or row.get("narrator_id") or row.get("subject_ref"),
        "subject_ref": row.get("subject_ref", ""), "tradition": row.get("tradition_id"),
        "grader_or_critic": row.get("grader") if is_report else (row.get("critic") or row.get("critic_ar")),
        "as_quoted_by": row.get("as_quoted_by") or "", "reporter_ar": row.get("reporter_ar") or "",
        "term_ar": row.get("grade_raw") if is_report else row.get("verdict_raw"),
        "canonical": row.get("grade_canonical") if is_report else row.get("verdict_canonical"),
        "aspect": "" if is_report else f"{row.get('aspect')} {'+'.join(row.get('aspect_detail') or [])}",
        "passage_ar": citation.get("passage_ar") or "", "locator": json.dumps(citation.get("locator"), ensure_ascii=False),
        "context_ar": context(row, texts),
    }


def write_csv(name, rows):
    with open(HERE / name, "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def tirmidhi_dispositions(reports, held):
    emitted = collections.defaultdict(list)
    for row in reports:
        emitted[row["hadith_id"]].append(row)
    held_by = collections.defaultdict(list)
    for row in held:
        if row.get("hadith_id"):
            held_by[row["hadith_id"]].append(row)
    out = []
    with open(OLD_HELD, encoding="utf-8") as handle:
        for line in handle:
            old = json.loads(line)
            hadith_id = f"hadith:k6:{old['snapshot_id']}"
            needle = L.fold(old["statement_ar_verbatim"])[:60]
            promoted = [r for r in emitted[hadith_id] if r["source_field"] == "text_ar" and needle and
                        (needle in L.fold(r["statement_ar"]) or L.fold(r["statement_ar"])[:60] in L.fold(old["statement_ar_verbatim"]))]
            kept = [r for r in held_by[hadith_id] if r.get("source_field") == "text_ar" and needle and (needle in L.fold(r["statement_ar"]) or
                                                                 L.fold(r["statement_ar"])[:60] in L.fold(old["statement_ar_verbatim"]))]
            if promoted:
                disposition = {"disposition": "promoted", "assessment_id": promoted[0]["id"],
                               "basis": promoted[0]["attribution_basis"], "grader": promoted[0]["grader"]}
            elif kept:
                disposition = {"disposition": "held", "reason": kept[0]["reason"]}
            else:
                disposition = {"disposition": "held", "reason": "no_report_subject_grading_clause"}
            out.append({"hadith_id": hadith_id, "old_reason": old["reason"], "statement_ar": old["statement_ar_verbatim"],
                        **disposition})
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    reports = read("hadith_assessments.jsonl.gz")
    narrators = read("narrator_assessments.jsonl.gz")
    held = read("hadith_assessments_held_back.jsonl.gz")
    texts = {}
    with open(HADITHS, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            texts[row["id"]] = row["text_ar"]
    dispositions = tirmidhi_dispositions(reports, held)
    with open(HERE / "tirmidhi_785_dispositions.jsonl.gz", "wb") as raw, \
            gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
        for row in dispositions:
            handle.write((json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8"))
    tally = collections.Counter(f"{d['old_reason']} -> {d['disposition']}:{d.get('reason') or d.get('grader')}" for d in dispositions)
    sample = draw(reports, STRATA_REPORTS, report_stratum, random.Random("assessments-sample-60")) + \
        draw(narrators, STRATA_NARRATORS, narrator_stratum, random.Random("assessments-sample-60"))
    if "--draw-sample" in sys.argv:   # the judged draw (sample_60_judged.csv) is a fixed artefact; redraw only on purpose
        write_csv("sample_60_for_judgement.csv", [flat(s, r, texts) for s, r in sample])
    rng = random.Random("assessments-worksheet-150")
    pool = sorted([r for r in reports + narrators if r.get("citation_status") == "cited"], key=lambda r: r["id"])
    worksheet = [{**flat("random_cited_row", r, texts), **BLANK} for r in rng.sample(pool, 150)]
    write_csv("review_worksheet_150.csv", worksheet)
    print(json.dumps({"tirmidhi_785": dict(tally), "total": len(dispositions), "sample": len(sample)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
