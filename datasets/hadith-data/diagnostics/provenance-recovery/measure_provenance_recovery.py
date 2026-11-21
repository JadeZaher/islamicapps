"""Part E: edition/volume/page/URL provenance in the original sources that the unified CSV lacks.

Streams the unified corpus once; reads original assets read-only; writes only inside provenance-recovery/.
Edition values are verbatim source strings, unreviewed, and never a cited claim.
"""

import collections
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import diagnostic_common as common  # noqa: E402

JOB = "provenance-recovery"
HADITH = common.HADITH_DATA_DIR
THAQALAYN = HADITH / "shia-hadith" / "v2_books"
PURE_CANON = HADITH / "archive" / "sheikahmad-pure-canon" / "pure_canon.jsonl"
DISPOSITIONS = HADITH / "curation_dispositions.jsonl"
OPENITI = {
    "al-Jami al-Sahih (Musnad al-Rabi ibn Habib)": HADITH / "openiti-sources" / "rabi" / "jamic_sahih_ibadiyya.txt",
    "Musnad al-Imam Zayd ibn Ali": HADITH / "openiti-sources" / "zayd" / "musnad_zaydiyya_052.mARkdown",
    "Sahifat al-Imam Ali al-Rida": HADITH / "openiti-sources" / "zayd" / "musnad_zaydiyya_052.mARkdown",
}
REVIEW = {"review_state": "unreviewed_local_candidate", "citation_id": None}
PAGE_REF = re.compile(r"^V(\d+)P(\d+)$")


def header_lines(path):
    text = path.read_text(encoding="utf-8-sig")
    header = text.split("#META#Header#End#")[0] if "#META#Header#End#" in text else text[:6000]
    return [(n, line.strip()) for n, line in enumerate(header.splitlines(), 1) if line.startswith("#META#")]


def edition_evidence(path):
    """Publisher line and any statement that pagination follows the printed edition, with header line numbers."""
    publisher = pagination = None
    for number, line in header_lines(path):
        if publisher is None and re.search(r"EdPUBLISHER|الناشر", line) and "NODATA" not in line:
            publisher = (number, line)
        if pagination is None and "ترقيم الصفحات موافق للمطبوع" in line:
            pagination = (number, line)
    return publisher, pagination


def pure_canon_edition_rows():
    out = {}
    for number, line in enumerate(PURE_CANON.open(encoding="utf-8"), 1):
        record = json.loads(line)
        source = record["source"]
        if "معلومات عن النشرة" not in source:
            continue
        label = source.split(" اسم الكتاب")[0].split(" 1/")[0].strip()
        edition = re.search(r"معلومات عن النشرة.*?(?=عدد الأجزاء\s*\d+|$)", source)
        volumes = re.search(r"عدد الأجزاء\s*\d+", source)
        out[label] = {"label_ar": label, "jsonl_line": number, "pure_canon_id": record["id"],
                      "edition_text_verbatim": edition.group(0).strip() if edition else None,
                      "volumes_text_verbatim": volumes.group(0) if volumes else None}
    return out


def thaqalayn_metadata():
    rows = []
    for path in sorted(THAQALAYN.glob("[0-9]*.json"), key=lambda p: int(p.stem)):
        records = [r for r in json.loads(path.read_text(encoding="utf-8")) if "arabicText" in r]
        if not records:
            continue
        first = records[0]
        rows.append({"provider_file_id": int(path.stem), "provider_book_id": first["bookId"], "book": first["book"],
                     "author_verbatim": first["author"], "translator_verbatim": first["translator"],
                     "records": len(records), "distinct_volumes": len({r["volume"] for r in records}),
                     "url_example": first["URL"], **REVIEW})
    return rows


def missing_arabic_report(rows, pure_canon_by_ref):
    dispositions = {}
    for line in DISPOSITIONS.open(encoding="utf-8"):
        d = json.loads(line)
        dispositions[d["record_id"]] = d
    report = []
    for line_no, row in rows:
        record_id = f"k6:{row['id']}"
        d = dispositions.get(record_id, {})
        reference = d.get("official_reference")
        candidate = None
        if reference:
            source_ar = "صحيح مسلم" if reference.startswith("muslim") else "سنن الترمذي" if reference.startswith("tirmidhi") else None
            number = re.sub(r"[^0-9]", "", reference.split(":")[1].rstrip("abc")) if ":" in reference else ""
            hit = pure_canon_by_ref.get((source_ar, number))
            if hit:
                candidate = {"pure_canon_id": hit["id"], "hadith_no": hit["hadith_no"], "text_ar_head": hit["text_ar"][:160],
                             "caveat": "numbering equality between the sunnah.com reference and the Pure Canon edition is assumed, not verified; "
                                       "rights for Pure Canon text are unstated"}
        report.append({
            "snapshot_id": row["id"], "csv_line": line_no, "source": row["source"].strip(), "hadith_no_cell": row["hadith_no"],
            "english_head": row["text_en"].strip()[:140], "disposition": d.get("disposition"),
            "official_reference": reference, "disposition_note": d.get("note"),
            "locally_recoverable_arabic": "no_copy_in_any_local_lineage_file" if not candidate else "candidate_in_pure_canon_needs_verification",
            "pure_canon_candidate": candidate})
    return report


def main():
    out_dir = common.output_directory(JOB)
    per_source = collections.defaultdict(collections.Counter)
    locator_rows, missing_rows = [], []
    evidence = {name: edition_evidence(path) for name, path in OPENITI.items()}
    thaqalayn = thaqalayn_metadata()
    thaqalayn_by_file = {r["provider_file_id"]: r for r in thaqalayn}
    imami_with_provider_locator = 0
    for line_no, row in common.iter_corpus_rows():
        source = row["source"].strip()
        key = f"{row['tradition']}|{source}"
        c = per_source[key]
        c["rows"] += 1
        for column in ("volume", "chapter_no", "hadith_no", "chapter", "category", "url", "page_ref"):
            if row[column].strip():
                c[column] += 1
        if not row["text_ar"].strip():
            missing_rows.append((line_no, row))
        match = re.match(r"https://thaqalayn\.net/hadith/(\d+)/", row["url"])
        if match and int(match.group(1)) in thaqalayn_by_file:
            imami_with_provider_locator += 1
        if source in OPENITI:
            publisher, pagination = evidence[source]
            page = PAGE_REF.match(row["page_ref"].strip())
            locator_rows.append({
                "snapshot_id": row["id"], "hadith_id": row["hadith_id"], "csv_line": line_no, "source": source,
                "page_ref_verbatim": row["page_ref"] or None,
                "printed_volume": int(page.group(1)) if page else None, "printed_page": int(page.group(2)) if page else None,
                "edition_publisher_verbatim": publisher[1] if publisher else None,
                "edition_header_file": common.relative_path(OPENITI[source]),
                "edition_header_line": publisher[0] if publisher else None,
                "pagination_matches_print_asserted_by_header": bool(pagination),
                "pagination_evidence_verbatim": pagination[1] if pagination else None,
                "locator_status": ("printed_page_candidate_header_asserts_match" if (page and pagination)
                                   else "edition_known_page_equivalence_unverified" if page else "no_page_marker_in_row"),
                **REVIEW})
    n_locator = common.write_jsonl(out_dir, "edition_locator_candidates.jsonl.gz", locator_rows, gzipped=True)
    pure_by_ref = {}
    for line in PURE_CANON.open(encoding="utf-8"):
        record = json.loads(line)
        if record["source"] in ("صحيح مسلم", "سنن الترمذي") and record["hadith_no"]:
            pure_by_ref[(record["source"], record["hadith_no"])] = record
    missing = missing_arabic_report(missing_rows, pure_by_ref)
    n_missing = common.write_jsonl(out_dir, "missing_arabic_recovery.jsonl", missing)
    n_thaq = common.write_jsonl(out_dir, "thaqalayn_book_provenance.jsonl", thaqalayn)
    pure_editions = pure_canon_edition_rows()
    work_map = {"سنن الدارمي": "Sunan al-Darimi", "موطأ مالك": "Muwatta' Malik", "سنن النسائي": "Sunan an-Nasa'i",
                "صحيح البخاري": "Sahih Bukhari", "صحيح مسلم": "Sahih Muslim", "سنن أبي داود": "Sunan Abi Da'ud",
                "سنن الترمذي": "Jami' al-Tirmidhi", "سنن ابن ماجه": "Sunan Ibn Majah"}
    edition_by_work = []
    for label, info in pure_editions.items():
        unified_source = work_map.get(label)
        rows_n = per_source.get(f"Sunni|{unified_source}", {}).get("rows", 0) if unified_source else 0
        edition_by_work.append({**info, "unified_source": unified_source, "unified_rows": rows_n,
                                "row_level_numbering_shared_with_unified": unified_source in ("Sunan al-Darimi", "Muwatta' Malik"),
                                "note": ("rows come from pure_canon.jsonl, so the edition applies to their numbering"
                                         if unified_source in ("Sunan al-Darimi", "Muwatta' Malik") else
                                         "unified rows come from a different lineage (K6); numbering equivalence unverified"),
                                **REVIEW})
    n_edition = common.write_jsonl(out_dir, "pure_canon_edition_by_work.jsonl", edition_by_work)

    def total(prefix=None, pred=None):
        return sum(c["rows"] for k, c in per_source.items() if (pred(k) if pred else k.startswith(prefix)))
    summary = {
        "header": common.header_object(JOB, "python -B datasets/hadith-data/diagnostics/provenance-recovery/measure_provenance_recovery.py",
                                       common.input_fingerprints(common.CORPUS_PATH, PURE_CANON, DISPOSITIONS,
                                                                 *sorted(set(OPENITI.values())), *sorted(THAQALAYN.glob("[0-9]*.json")))),
        "unified_locator_fields_by_source": {k: dict(v) for k, v in sorted(per_source.items())},
        "reports_total": total(pred=lambda k: True),
        "openiti_derived": {"reports": n_locator,
                            "with_page_ref_already_in_unified": sum(1 for r in locator_rows if r["page_ref_verbatim"]),
                            "gain_edition_level_locator": sum(1 for r in locator_rows if r["edition_publisher_verbatim"]),
                            "gain_printed_page_candidate_header_asserts_match": sum(
                                1 for r in locator_rows if r["locator_status"] == "printed_page_candidate_header_asserts_match"),
                            "edition_known_but_page_equivalence_unverified": sum(
                                1 for r in locator_rows if r["locator_status"] == "edition_known_page_equivalence_unverified"),
                            "no_page_marker_in_row": sum(1 for r in locator_rows if r["locator_status"] == "no_page_marker_in_row"),
                            "by_source": dict(collections.Counter(r["source"] for r in locator_rows)),
                            "header_evidence": {k: [e[1] if e else None for e in v] for k, v in evidence.items()}},
        "thaqalayn_imami": {"unified_rows_whose_url_maps_to_a_provider_file": imami_with_provider_locator,
                            "provider_files": n_thaq,
                            "fields_in_original_not_in_unified": ["bookId (provider_book_id)", "provider file id (v2_books file name)",
                                                                  "author", "translator", "categoryId", "chapterInCategoryId",
                                                                  "gradingsFull author/reference objects"],
                            "printed_edition_or_page_in_original": "none; volume and a thaqalayn.net URL are the only locators"},
        "pure_canon": {"header_rows_carrying_edition_text": n_edition,
                       "unified_rows_that_gain_a_work_level_edition_candidate": sum(
                           r["unified_rows"] for r in edition_by_work if r["row_level_numbering_shared_with_unified"]),
                       "collections_without_any_edition_text_in_pure_canon": ["مسند حنبل (23,529 unified rows)", "شافعي (2,054 unified rows)"],
                       "other_original_fields_not_in_unified": {"shelf_no": "internal NabiMuhammad shelf index, not a printed locator",
                                                                "row_no": "workbook order"}},
        "k6_sunni": {"rows": total(pred=lambda k: k.startswith("Sunni|") and not any(
                         n in k for n in ("Ahmad", "Shafi", "Muwatta", "Darimi"))),
                     "volume_page_url_in_any_local_lineage": 0,
                     "note": "the clean CSV, seven backups and the archived consolidated snapshot carry chapter_no only; "
                             "no printed or web locator exists locally for these reports"},
        "missing_arabic": {"rows": n_missing,
                           "recoverable_locally": sum(1 for r in missing if r["locally_recoverable_arabic"] == "no_copy_in_any_local_lineage_file") == 0,
                           "no_arabic_in_any_local_lineage_file": sum(1 for r in missing if r["locally_recoverable_arabic"] == "no_copy_in_any_local_lineage_file"),
                           "pure_canon_candidates_needing_verification": sum(1 for r in missing if r["pure_canon_candidate"]),
                           "not_reports_per_curation_dispositions": [r["snapshot_id"] for r in missing
                                                                      if r["disposition"] in ("reclassify_exclude_from_hadith_load", "merge_tombstone")]},
        "output_rows": {"edition_locator_candidates.jsonl.gz": n_locator, "missing_arabic_recovery.jsonl": n_missing,
                        "thaqalayn_book_provenance.jsonl": n_thaq, "pure_canon_edition_by_work.jsonl": n_edition},
    }
    common.write_json(out_dir, "provenance_summary.json", summary)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("header", "unified_locator_fields_by_source")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
