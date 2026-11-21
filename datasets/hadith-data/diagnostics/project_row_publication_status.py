#!/usr/bin/env python3
"""J9: per-row publication-status projection (the finding-07 section f facets) from the preserved snapshot.

Writes only under diagnostics/publication-status/: row_status.csv.gz, summary.json,
summary_by_collection.csv. Facet values describe state; they never assert a grade, identity or
translation, and nothing here is a publication decision.

Usage: python -B diagnostics/project_row_publication_status.py
"""

import csv
import gzip
import json
import re
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402

JOB = "publication-status"
K6_SOURCES = {"Sahih Bukhari", "Sahih Muslim", "Sunan an-Nasa'i", "Sunan Abi Da'ud", "Sunan Ibn Majah",
              "Jami' al-Tirmidhi"}
PURE_CANON_SOURCES = {"Musnad Ahmad", "Sunan al-Darimi", "Musnad al-Shafi'i", "Muwatta' Malik"}
COMPILER_CRITERION_SOURCES = {"Sahih Bukhari", "Sahih Muslim"}
FAMILY_SOURCE_DOC = {
    "sunnah_com_k6_snapshot": "sunnah-com.md", "pure_canon": "sheikahmad-pure-canon.md",
    "thaqalayn_api": "thaqalayn-api.md", "openiti_rida_appendix": "musnad-rida-openiti.md",
    "openiti_ibadi": "jami-sahih-rabi-openiti.md", "openiti_zaydi": "musnad-zayd-openiti.md",
}
ARABIC_LETTER = re.compile(r"[ء-ي]")


def upstream_family(row: dict) -> str:
    """Upstream lineage inferred from tradition/source/url (the snapshot has no provenance column)."""
    tradition, source = common.clean(row["tradition"]), common.clean(row["source"])
    if tradition == "Sunni":
        return ("sunnah_com_k6_snapshot" if source in K6_SOURCES
                else "pure_canon" if source in PURE_CANON_SOURCES else "unclassified")
    if tradition == "Imami":
        if "thaqalayn.net" in (row.get("url") or ""):
            return "thaqalayn_api"
        return "openiti_rida_appendix" if source == "Sahifat al-Imam Ali al-Rida" else "unclassified"
    return {"Ibadi": "openiti_ibadi", "Zaydi": "openiti_zaydi"}.get(tradition, "unclassified")


def read_front_matter(name: str) -> dict:
    """Minimal key: value reader for the first lines of a datasets/sources/*.md front matter."""
    text = (common.DATASETS_DIR / "sources" / name).read_text(encoding="utf-8")
    block = text.split("---")[1] if text.startswith("---") else ""
    found = {}
    for line in block.splitlines():
        match = re.match(r"^(license|license_url|id):\s*(.+)$", line)
        if match:
            found[match.group(1)] = match.group(2).strip()
    return found


def main() -> None:
    started = time.time()
    regen = common.load_regen()
    extractor = common.load_extractor()
    exact_index, _ = regen.build_narrator_index(str(common.REGISTRY_PATH))

    licenses = {family: read_front_matter(doc) for family, doc in FAMILY_SOURCE_DOC.items()}
    dispositions = {}
    disposition_path = common.HADITH_DATA_DIR / "curation_dispositions.jsonl"
    for line in disposition_path.read_text(encoding="utf-8").splitlines():
        entry = json.loads(line)
        dispositions[entry["record_id"]] = entry

    out = common.output_directory(JOB)
    columns = ["id", "hadith_id", "tradition", "source", "upstream_family", "rights_status",
               "source_text_status", "arabic_letters", "translation_state", "translation_issue",
               "chain_status", "chain_branches", "chain_links", "chain_links_exact_resolved",
               "chain_absence_hint", "grading_status", "has_cited_grading", "disposition_on_file",
               "arabic_displayable_if_rights_cleared", "english_shown_if_rights_cleared",
               "chain_links_overlay_if_rights_cleared", "publishable_today_current_gate"]
    facet_totals: dict[str, Counter] = defaultdict(Counter)
    by_tradition: dict[str, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    by_collection: dict[tuple, dict[str, Counter]] = defaultdict(lambda: defaultdict(Counter))
    scenario = Counter()
    seen_ids = set()
    duplicate_ids = 0

    raw = open(out / "row_status.csv.gz", "wb")
    gz = gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0)
    import io
    text_out = io.TextIOWrapper(gz, encoding="utf-8", newline="")
    writer = csv.writer(text_out, lineterminator="\n")
    writer.writerow(columns)
    rows_written = 0

    for _, row in common.iter_corpus_rows():
        tradition = common.clean(row["tradition"])
        source = common.clean(row["source"])
        family = upstream_family(row)
        row_id = common.clean(row["id"])
        if row_id in seen_ids:
            duplicate_ids += 1
        seen_ids.add(row_id)

        letters = len(ARABIC_LETTER.findall(row.get("text_ar") or ""))
        source_text_status = "present" if letters >= 3 else "missing"
        english = row.get("text_en") or ""
        issue = regen.translation_issue(english, row.get("text_ar") or "")
        if not english.strip():
            translation_state = "none"
        elif issue:
            translation_state = "present_defective"
        else:
            translation_state = {
                "thaqalayn_api": "present_clean_source_provided_unreviewed",
                "sunnah_com_k6_snapshot": "present_clean_source_status_unknown",
            }.get(family, "present_clean_provenance_unrecorded")

        links = resolved = 0
        branches_count = 0
        hint = ""
        try:
            branches = extractor.extract_isnad_branches(row.get("text_ar") or "")
        except extractor.IsnadExtractionLimitError:
            branches = None
        if branches is None:
            chain_status = "extraction_failed"
        elif not branches:
            chain_status = "no_chain_extracted"
            hint = ("source_genre_likely_without_isnad" if source == "Nahj al-Balāgha"
                    else "unclassified_absent_in_source_or_extractor_miss")
        else:
            branches_count = len(branches)
            for branch in branches:
                for surface in branch:
                    links += 1
                    if exact_index.get(regen.narrator_normalize(surface)):
                        resolved += 1
            chain_status = ("complete_exact" if resolved == links
                            else "unresolved" if resolved == 0 else "partial")

        grade_value = common.clean(row.get("grade_value"))
        has_cited = bool(common.clean(row.get("gradings_full"))) and tradition == "Imami"
        if has_cited:
            grading_status = "cited_assessments_present"
        elif tradition == "Sunni" and grade_value == "ثابت":
            grading_status = "collection_label_only_not_a_grade"
        elif source in COMPILER_CRITERION_SOURCES:
            grading_status = "compiler_criterion_candidate"
        else:
            grading_status = "none_recorded_in_corpus"

        disposition = ""
        if family == "sunnah_com_k6_snapshot":
            entry = dispositions.get(f"k6:{row_id}")
            disposition = entry["disposition"] if entry else ""
        license_text = licenses.get(family, {}).get("license", "unknown")
        rights_status = "pending_no_clearance_recorded" if license_text else "unknown"

        arabic_ok = source_text_status == "present"
        english_ok = translation_state == "present_clean_source_provided_unreviewed"
        overlay_links = resolved > 0
        writer.writerow([row_id, common.clean(row["hadith_id"]), tradition, source, family, rights_status,
                         source_text_status, letters, translation_state, issue, chain_status, branches_count,
                         links, resolved, hint, grading_status, int(has_cited), disposition,
                         int(arabic_ok), int(english_ok), int(overlay_links), 0])
        rows_written += 1

        facets = {"upstream_family": family, "source_text_status": source_text_status,
                  "translation_state": translation_state, "chain_status": chain_status,
                  "grading_status": grading_status, "rights_status": rights_status}
        for name, value in facets.items():
            facet_totals[name][value] += 1
            by_tradition[tradition][name][value] += 1
            by_collection[(tradition, source)][name][value] += 1
        by_collection[(tradition, source)]["rows"]["rows"] += 1
        by_tradition[tradition]["rows"]["rows"] += 1
        scenario["rows"] += 1
        scenario["arabic_displayable_if_rights_cleared"] += int(arabic_ok)
        scenario["arabic_with_chain_as_written"] += int(arabic_ok and branches_count > 0)
        scenario["english_shown_if_rights_cleared"] += int(english_ok)
        scenario["arabic_with_at_least_one_verified_link_overlay"] += int(arabic_ok and overlay_links)
        scenario["arabic_with_complete_exact_chain"] += int(arabic_ok and chain_status == "complete_exact")
        scenario["has_cited_grading"] += int(has_cited)
        scenario["arabic_and_english_shown_and_complete_chain"] += int(
            arabic_ok and english_ok and chain_status == "complete_exact")
        if row.get("chain_indx"):
            scenario["snapshot_rows_with_nonblank_chain_indx"] += 1

    text_out.flush()
    text_out.detach()
    gz.close()
    raw.close()

    def plain(nested):
        return {key: {facet: dict(sorted(counter.items())) for facet, counter in value.items()}
                for key, value in nested.items()}

    summary = {
        "header": common.header_object(
            JOB, "python -B datasets/hadith-data/diagnostics/project_row_publication_status.py",
            common.input_fingerprints(common.CORPUS_PATH, common.REGISTRY_PATH, disposition_path)),
        "rows": rows_written,
        "duplicate_id_values": duplicate_ids,
        "facet_totals": {name: dict(sorted(c.items())) for name, c in facet_totals.items()},
        "scenario_if_rights_cleared_for_every_work": dict(scenario),
        "publishable_today_under_current_all_or_nothing_gate": 0,
        "licenses_as_stated_in_datasets_sources": licenses,
        "by_tradition": plain(by_tradition),
        "method_notes": [
            "The preserved snapshot has no record_id, source_work_id, translation_source or translation_review_status columns; "
            "upstream family is inferred from tradition/source/url and translation provenance is inferred from family.",
            "translation_state never reaches human_verified/source_verified: no review evidence exists in the snapshot.",
            "chain_status uses exact unique registry resolution only (same resolver as the audit); partial means some links resolve.",
            "arabic letters >= 3 is the presence test; 3 non-Arabic sources (blank, 's', '* * * * *') fall under missing.",
            "Dispositions are joined only for K6 rows by `k6:<id>`; the pure-canon disposition cannot be joined (no pc id column).",
        ],
        "seconds": round(time.time() - started, 1),
    }
    common.write_json(out, "summary.json", summary)
    with open(out / "summary_by_collection.csv", "w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        facet_names = ["source_text_status", "translation_state", "chain_status", "grading_status"]
        writer.writerow(["tradition", "source", "rows"] + [f"{f}:{v}" for f in facet_names
                        for v in sorted({v for key in by_collection for v in by_collection[key][f]})])
        header_values = [(f, v) for f in facet_names
                         for v in sorted({v for key in by_collection for v in by_collection[key][f]})]
        for (tradition, source), facets in sorted(by_collection.items(), key=lambda kv: -kv[1]["rows"]["rows"]):
            writer.writerow([tradition, source, facets["rows"]["rows"]] + [facets[f].get(v, 0) for f, v in header_values])
    print(json.dumps({"rows": rows_written, "seconds": summary["seconds"]}))


if __name__ == "__main__":
    main()
