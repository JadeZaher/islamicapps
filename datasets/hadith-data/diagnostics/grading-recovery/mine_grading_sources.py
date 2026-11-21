"""D2 + D4 + D5: grading columns in the unified corpus and the original sources, in-text compiler statements,
and confirmation that the dataset-wide ثابت label is excluded everywhere written by these jobs.
"""

import collections
import gzip
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import diagnostic_common as common  # noqa: E402

JOB = "grading-recovery"
HADITH = common.HADITH_DATA_DIR
THAQALAYN_DIR = HADITH / "shia-hadith" / "v2_books"
PURE_CANON_XLSX = HADITH / "sheikahmad" / "Hadith-Pure-Canon-Authentica.xlsx"
THABIT = "ثابت"

SPEAKER = re.compile(r"قال\s+(أبو\s+داود|أبو\s+عيسى|أبو\s+عبد\s+الرحمن|أبو\s+عبد\s+الله|أبو\s+الحسين|الترمذي|النسائي|البخاري|مسلم|الربيع|الصدوق)")
GRADE_PHRASE = re.compile(
    r"(?:هذا|هو)\s+(?:ال)?حديث\s+(?:حسن|صحيح|غريب|ضعيف|منكر|شاذ|مرسل)|إسناده\s+(?:صحيح|حسن|ضعيف|جيد)|"
    r"(?:حديث|إسناد)\s+(?:صحيح|حسن|ضعيف)\s|هذا\s+(?:خطأ|وهم|منكر)")
TERMS = ["صحيح", "حسن", "ضعيف", "غريب", "منكر", "شاذ", "مرسل", "خطأ", "وهم", "جيد"]
COMPILER_OF_PHRASE = {"أبو داود": "Abu Dawud", "أبو عيسى": "Abu 'Isa al-Tirmidhi", "أبو عبد الرحمن": "Abu 'Abd al-Rahman al-Nasa'i",
                      "الترمذي": "al-Tirmidhi", "النسائي": "al-Nasa'i", "البخاري": "al-Bukhari", "مسلم": "Muslim"}
COMPILER_PHRASES_BY_WORK = {"Sunan Abi Da'ud": {"أبو داود"}, "Sunan an-Nasa'i": {"أبو عبد الرحمن", "النسائي"},
                            "Sahih Muslim": {"مسلم", "أبو الحسين"}, "Sahih Bukhari": {"البخاري"}}
AMBIGUOUS_SPEAKERS = {"أبو عبد الله", "أبو الحسين", "الربيع", "الصدوق"}


def parse_entries(cell):
    out = []
    for segment in cell.split(" | "):
        if ":" in segment:
            out.append(segment.split(":", 1)[0].strip())
    return out


def corpus_census():
    per_source = collections.defaultdict(lambda: collections.Counter())
    distinct = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    entries_per_row = collections.Counter()
    graders_all = collections.Counter()
    thabit_hits = collections.Counter()
    inline = collections.defaultdict(collections.Counter)
    inline_samples = collections.defaultdict(list)
    candidates = []
    for line_no, row in common.iter_corpus_rows():
        key = f"{row['tradition']}|{row['source'].strip()}"
        c = per_source[key]
        c["rows"] += 1
        for column in ("grade_tradition", "grade_source", "grade_value", "gradings_full"):
            if row[column].strip():
                c[column] += 1
                if column != "gradings_full":
                    distinct[key][column][row[column].strip()] += 1
            if THABIT in row[column]:
                thabit_hits[(row["source"].strip(), column)] += 1
        if row["gradings_full"].strip():
            graders = parse_entries(row["gradings_full"])
            entries_per_row[len(graders)] += 1
            graders_all.update(graders)
            if len(set(graders)) > 1:
                c["rows_with_two_or_more_distinct_graders"] += 1
            if len(graders) != len(set(graders)):
                c["rows_where_one_grader_appears_twice"] += 1
        text = row["text_ar"]
        speaker_hits = list(SPEAKER.finditer(text))
        grade_hit = GRADE_PHRASE.search(text)
        if speaker_hits:
            inline[key]["rows_with_speaker_phrase"] += 1
        if grade_hit:
            inline[key]["rows_with_grade_phrase"] += 1
        if speaker_hits and grade_hit:
            inline[key]["rows_with_both"] += 1
        inline[key]["rows"] += 1
        if "Tirmidhi" in key:
            continue  # J6b already extracted these
        for match in speaker_hits:
            phrase = re.sub(r"\s+", " ", match.group(1))
            window = text[match.start(): match.start() + 220]
            found = [t for t in TERMS if t in window]
            if not found:
                continue
            work = row["source"].strip()
            if phrase in COMPILER_PHRASES_BY_WORK.get(work, set()):
                status, attributed = "phrase_matches_the_work_compiler_unverified", COMPILER_OF_PHRASE.get(phrase, phrase)
            elif phrase in AMBIGUOUS_SPEAKERS:
                status, attributed = "speaker_ambiguous_needs_review", None
            else:
                status, attributed = "phrase_names_a_person_other_than_the_work_compiler", None
            candidates.append({
                "snapshot_id": row["id"], "hadith_id": row["hadith_id"], "source": work, "tradition": row["tradition"],
                "snapshot_line": line_no, "speaker_phrase": phrase, "attributed_to": attributed,
                "attribution_status": status, "statement_ar": window, "char_start": match.start(), "terms_in_window": found,
                "status": "inline_statement_candidate_regex_unreviewed"})
    return per_source, distinct, entries_per_row, graders_all, thabit_hits, inline, candidates


def original_thaqalayn():
    rows = entries = 0
    per_column = collections.Counter()
    author_fields = collections.Counter()
    for path in sorted(THAQALAYN_DIR.glob("[0-9]*.json")):
        for record in json.loads(path.read_text(encoding="utf-8")):
            if "arabicText" not in record:
                continue
            rows += 1
            for column in ("mohseniGrading", "behbudiGrading", "majlisiGrading"):
                if record[column] not in ("", None):
                    per_column[column] += 1
            grading = record["gradingsFull"]
            grading = json.loads(grading) if isinstance(grading, str) and grading.strip() else (grading or [])
            for entry in grading:
                entries += 1
                for k, v in entry["author"].items():
                    if k != "name_en" and v:
                        author_fields[k] += 1
                if entry.get("grade_en"):
                    author_fields["grade_en"] += 1
    return {"records": rows, "gradingsFull_entries": entries, "per_grader_column_nonempty": dict(per_column),
            "non_null_author_or_english_fields": dict(author_fields)}


def pure_canon_closing_statements():
    z = zipfile.ZipFile(PURE_CANON_XLSX)
    strings = []
    for _, el in ET.iterparse(z.open("xl/sharedStrings.xml")):
        if el.tag.endswith("}si"):
            strings.append("".join(t.text or "" for t in el.iter() if t.tag.endswith("}t")))
            el.clear()
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    out, by_source, rows_seen, dropped_cols = [], collections.Counter(), 0, collections.Counter()
    for _, el in ET.iterparse(z.open("xl/worksheets/sheet1.xml")):
        if not el.tag.endswith("}row"):
            continue
        row_number = int(el.get("r"))
        cells = {}
        for cell in el:
            v = cell.find("m:v", ns)
            if v is None:
                continue
            value = strings[int(v.text)] if cell.get("t") == "s" else v.text
            cells[re.match(r"[A-Z]+", cell.get("r")).group(0)] = value
        el.clear()
        if row_number == 1:
            continue
        rows_seen += 1
        for col in ("E", "F", "I", "K", "L"):
            if cells.get(col, "").strip():
                dropped_cols[col] += 1
        closing, after = cells.get("L", "").strip(), cells.get("K", "").strip()
        if not closing:
            continue
        label = cells.get("D", "").strip()
        short = label.split(" اسم الكتاب")[0][:60]
        speaker = SPEAKER.search(closing)
        terms = [t for t in TERMS if t in closing]
        by_source[short] += 1
        out.append({
            "workbook": "datasets/hadith-data/sheikahmad/Hadith-Pure-Canon-Authentica.xlsx", "sheet": "Sheet1", "sheet_row": row_number,
            "pure_canon_id": f"pc_{cells.get('A')}", "source_label": short, "hadith_no_in_book": cells.get("N"),
            "closing_text_ar_verbatim": closing[:700], "after_hadith_text_ar_verbatim": after[:400] or None,
            "speaker_phrase": re.sub(r"\s+", " ", speaker.group(1)) if speaker else None, "terms_in_closing": terms,
            "status": "closing_statement_candidate_unreviewed",
            "note": "text_ar in pure_canon.jsonl is column B only; these columns are not carried into the unified corpus"})
    return out, by_source, rows_seen, dropped_cols


def scan_outputs_for_thabit(out_dir):
    """D5: ثابت may appear only as a quoted source value, never as a grade/term field in what these jobs wrote."""
    problems = []
    for path in sorted(out_dir.glob("hadith_assessments_*.jsonl")) + sorted(out_dir.glob("compiler_criterion*.jsonl*")):
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                record = json.loads(line)
                if THABIT in str(record.get("grade_raw", "")):
                    problems.append(path.name)
                    break
    bio_dir = common.DIAGNOSTICS_DIR / "biography-recovery"
    for path in sorted(bio_dir.glob("narrator_assessment_candidates.jsonl")):
        for line in path.open(encoding="utf-8"):
            if THABIT in (json.loads(line).get("term_ar") or ""):
                problems.append(path.name)
                break
    return problems


def main():
    out_dir = common.output_directory(JOB)
    inputs = common.input_fingerprints(common.CORPUS_PATH, PURE_CANON_XLSX)
    per_source, distinct, entries_per_row, graders_all, thabit_hits, inline, candidates = corpus_census()
    n_candidates = common.write_jsonl(out_dir, "inline_compiler_statement_candidates.jsonl.gz", candidates, gzipped=True)
    closing, closing_by_source, workbook_rows, dropped = pure_canon_closing_statements()
    n_closing = common.write_jsonl(out_dir, "pure_canon_closing_statement_candidates.jsonl", closing)
    original = original_thaqalayn()
    ibadi_zaydi_keys = {}
    for rel in ("ibadi-hadith", "zaydi-hadith", "rida-hadith"):
        hadiths = json.loads((HADITH / rel / "parsed_hadiths.json").read_text(encoding="utf-8"))["hadiths"]
        ibadi_zaydi_keys[rel] = sorted({k for h in hadiths for k in h if "grade" in k.lower() or "hukm" in k.lower()})
    problems = scan_outputs_for_thabit(out_dir)
    census = {}
    for key, c in sorted(per_source.items()):
        census[key] = {**dict(c), "distinct_grade_value": len(distinct[key]["grade_value"]),
                       "distinct_grade_source": len(distinct[key]["grade_source"]),
                       "grade_value_top": dict(distinct[key]["grade_value"].most_common(3)),
                       "grade_source_top": dict(distinct[key]["grade_source"].most_common(3))}
    summary = {
        "header": common.header_object(JOB, "python -B datasets/hadith-data/diagnostics/grading-recovery/mine_grading_sources.py", inputs),
        "d2_unified_grading_columns": {
            "per_source": census,
            "distinct_graders_in_gradings_full": dict(graders_all),
            "gradings_full_entries_per_row": dict(sorted(entries_per_row.items())),
            "rows_with_two_or_more_distinct_graders": sum(c.get("rows_with_two_or_more_distinct_graders", 0) for c in per_source.values()),
            "rows_where_one_grader_appears_twice": sum(c.get("rows_where_one_grader_appears_twice", 0) for c in per_source.values()),
            "distinct_non_thabit_grade_values_in_grade_value_column": 0,
        },
        "d2_original_thaqalayn_json": original,
        "d2_ibadi_zaydi_rida_parsed_hadiths_grade_like_keys": ibadi_zaydi_keys,
        "d4_inline_statements": {
            "unified_text_ar_scan_by_source": {k: dict(v) for k, v in sorted(inline.items())},
            "non_tirmidhi_candidates_written": n_candidates,
            "by_source": dict(collections.Counter(c["source"] for c in candidates)),
            "by_attribution_status": dict(collections.Counter(c["attribution_status"] for c in candidates)),
            "pure_canon_workbook": {"data_rows": workbook_rows, "rows_with_closing_statement_L": n_closing,
                                    "closing_by_source_label": dict(closing_by_source.most_common()),
                                    "non_empty_columns_not_carried_into_unified": dict(dropped)},
        },
        "d5_thabit": {
            "unified_rows_with_thabit_by_source_and_column": {f"{s}|{c}": n for (s, c), n in sorted(thabit_hits.items())},
            "grade_rows_total": sum(thabit_hits.values()),
            "outputs_of_these_jobs_with_thabit_as_grade": problems,
        },
    }
    census_values = summary["d2_unified_grading_columns"]["per_source"]
    summary["d2_unified_grading_columns"]["distinct_non_thabit_grade_values_in_grade_value_column"] = sum(
        1 for k, c in census_values.items() for v in c["grade_value_top"] if v != THABIT)
    common.write_json(out_dir, "grading_sources_census.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "header"}, ensure_ascii=False, indent=1)[:9000])


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
