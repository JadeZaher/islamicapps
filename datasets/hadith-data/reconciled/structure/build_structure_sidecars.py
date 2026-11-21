"""Build the report-structure sidecars (see README.md). Deterministic, standard library only, read-only on every input.

    python -B datasets/hadith-data/reconciled/structure/build_structure_sidecars.py [--production-dump FILE]

Writes only beside this script. Nothing existing is modified; no database or network access.
"""

import argparse
import collections
import csv
import gzip
import hashlib
import io
import json
import os
import re
import sqlite3
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import structure_logic as logic  # noqa: E402
import structure_provenance as provenance  # noqa: E402

csv.field_size_limit(1 << 30)
HADITH_DATA = HERE.parent.parent
DATASETS = HADITH_DATA.parent
REPO = DATASETS.parent

CORPUS = HADITH_DATA / "development" / "incomplete-curation" / "all_hadiths_unified.incomplete.csv.gz"
CLEAN_K6 = HADITH_DATA / "all_hadiths_clean.csv.gz"
K6_ARCHIVE = DATASETS / "archive" / "datasets.7z"
K6_MEMBER = "datasets/hadith-data/all_hadiths_clean.csv"
BSDTAR = os.environ.get("BSDTAR", r"C:\Windows\System32\tar.exe")
THAQALAYN_DIR = HADITH_DATA / "shia-hadith" / "v2_books"
PURE_CANON_JSONL = HADITH_DATA / "archive" / "sheikahmad-pure-canon" / "pure_canon.jsonl"
PURE_CANON_XLSX = HADITH_DATA / "sheikahmad" / "Hadith-Pure-Canon-Authentica.xlsx"
PURE_CANON_EDITIONS = HADITH_DATA / "diagnostics" / "provenance-recovery" / "pure_canon_edition_by_work.jsonl"
OPENITI_RABI = HADITH_DATA / "openiti-sources" / "rabi" / "jamic_sahih_ibadiyya.txt"
OPENITI_ZAYD = HADITH_DATA / "openiti-sources" / "zayd" / "musnad_zaydiyya_052.mARkdown"
CROSSWALK = HADITH_DATA / "reconciled" / "external_report_crosswalk.jsonl.gz"
KG_DB = DATASETS / "sources" / "external" / "hadith-kg" / "hadith-kg.db"
REGISTRY_TS = REPO / "src" / "lib" / "sources" / "registry.ts"
RIWAYAT_DB = DATASETS / "sources" / "external" / "riwayat-corpus" / "hadith_master.db"

K6_WORKS = {
    "Sahih Bukhari": "sunni:bukhari", "Sahih Muslim": "sunni:muslim", "Sunan Abi Da'ud": "sunni:abudawud",
    "Jami' al-Tirmidhi": "sunni:tirmidhi", "Sunan an-Nasa'i": "sunni:nasai", "Sunan Ibn Majah": "sunni:ibnmajah",
}
PURE_CANON_WORKS = {
    "Musnad Ahmad": "sunni:ahmad", "Sunan al-Darimi": "sunni:darimi", "Musnad al-Shafi'i": "sunni:shafii",
    "Muwatta' Malik": "sunni:muwatta",
}
PURE_CANON_LABELS_AR = {"مسند حنبل": "sunni:ahmad", "سنن الدارمي": "sunni:darimi", "شافعي": "sunni:shafii",
                        "موطأ مالك": "sunni:muwatta"}
PURE_CANON_EDITION_LABEL = {"موطأ مالك": "sunni:muwatta", "سنن الدارمي": "sunni:darimi"}
OPENITI_WORKS = {"ibadi": "ibadi:musnad-rabi", "zaydi": "zaydi:musnad-zayd", "imami": "imami:sahifat-al-imam-ali-al-rida"}

# Numbering scheme per Thaqalayn work, from the measured evidence in numbering_audit.json (README, "Thaqalayn").
#   per_chapter     number = last URL segment, counted inside a chapter (bab); cite the path volume/book/chapter/number.
#   unit_in_book    number = chapterInCategoryId: the work's own unit (Nahj sermon/letter/saying; one majlis hadith) in
#                   its category; rows that share it are fragments, told apart by the URL segment.
#   continuous_work number = the number the provider's Arabic (or English) text opens with, continuous across the work.
THAQALAYN_SCHEME = collections.defaultdict(lambda: "per_chapter")
THAQALAYN_SCHEME.update({
    "imami:nahj-al-balagha": "unit_in_book", "imami:al-amali-mufid": "unit_in_book",
    "imami:man-la-yahduruhu-al-faqih": "continuous_work", "imami:kitab-al-mumin": "continuous_work",
    "imami:kitab-al-ghayba-tusi": "continuous_work",
})
CONTINUOUS_PRINTED_SOURCE = {  # which provider text carries the continuous number, in order of preference
    "imami:man-la-yahduruhu-al-faqih": ("ar",), "imami:kitab-al-mumin": ("ar", "en"), "imami:kitab-al-ghayba-tusi": ("ar",),
}


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def write_jsonl_gz(path, rows):
    count = 0
    with open(path, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
        for row in rows:
            handle.write((dumps(row) + "\n").encode("utf-8"))
            count += 1
    return count


def write_csv_gz(path, columns, rows):
    count = 0
    with open(path, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
        text = io.TextIOWrapper(gz, encoding="utf-8", newline="")
        writer = csv.writer(text, lineterminator="\n", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(columns)
        for row in rows:
            writer.writerow(["|".join(map(str, row[c])) if isinstance(row.get(c), list) else ("" if row.get(c) is None else row[c])
                             for c in columns])
            count += 1
        text.flush()
        text.detach()
    return count


# ---------------------------------------------------------------------------------------------------------------------
# Readers
# ---------------------------------------------------------------------------------------------------------------------

def read_corpus():
    """Every report of the record-id corpus, text columns dropped except K6's (needed to bind the original file)."""
    rows = []
    with gzip.open(CORPUS, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            keep = {k: row[k] for k in ("id", "hadith_id", "provider_file_id", "source", "source_work_id", "tradition",
                                        "volume", "chapter_no", "hadith_no", "chapter", "category", "url", "page_ref",
                                        "record_id", "source_record_id")}
            if keep["record_id"].startswith("k6:"):
                keep["text_ar"] = row["text_ar"]
            rows.append(keep)
    return rows


def read_k6_original():
    data = subprocess.run([BSDTAR, "-xOf", str(K6_ARCHIVE), K6_MEMBER], capture_output=True, timeout=300, check=True).stdout
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"), newline="")))
    return rows, hashlib.sha256(data).hexdigest()


def read_thaqalayn():
    """{(provider_file_id, provider_id): record} in provider-file order."""
    records = {}
    for path in sorted(THAQALAYN_DIR.glob("[0-9]*.json"), key=lambda p: int(p.stem)):
        for record in json.load(open(path, encoding="utf-8")):
            records[(path.stem, str(record["id"]))] = record
    return records


_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def read_pure_canon_workbook(books):
    """Columns A (row), D (book), E (musnad group), F (companion), M (shelf), N (number) of Sheet1 for the given books."""
    archive = zipfile.ZipFile(PURE_CANON_XLSX)
    strings = []
    for _, element in ET.iterparse(archive.open("xl/sharedStrings.xml")):
        if element.tag == _NS + "si":
            strings.append("".join(t.text or "" for t in element.iter(_NS + "t")))
            element.clear()
    header, rows = {}, {}
    for _, element in ET.iterparse(archive.open("xl/worksheets/sheet1.xml")):
        if element.tag != _NS + "row":
            continue
        cells = {}
        for cell in element.findall(_NS + "c"):
            value = cell.find(_NS + "v")
            if value is None:
                continue
            column = re.match(r"[A-Z]+", cell.get("r")).group(0)
            cells[column] = strings[int(value.text)] if cell.get("t") == "s" else value.text
        if element.get("r") == "1":
            header = cells
        elif cells.get("D") in books:
            rows["pc_" + cells["A"]] = cells
        element.clear()
    return header, rows


def read_openiti_header(path):
    """Publisher and pagination lines from an OpenITI file header, verbatim, with their 1-based line numbers."""
    found = {}
    for number, line in enumerate(open(path, encoding="utf-8").read().split("\n"), start=1):
        if line.startswith("#META#Header#End#"):
            break
        if re.match(r"#META# (013\.EdPUBLISHER|الناشر:)", line):
            found.setdefault("publisher", (number, line))
        if "ترقيم الصفحات موافق للمطبوع" in line and line.startswith("#META# comments:"):
            found["pagination_matches_print"] = (number, line)
        if line.startswith("#META# 014.BookVOLS"):
            found["volumes"] = (number, line)
    return found


def parse_rabi_source():
    """Numbered hadith lines of the Ibadi source in order. Each entry: dict with number, repeat marker, line number,
    start page (the last page marker on an EARLIER line: a marker opens its page, so a hadith that begins before a
    marker begins on the previous page), kitab ordinal and title, bab number and heading. Bab numbers restart in every kitab."""
    entries, page, kitab, bab = [], None, (0, None, None), (None, None, None)
    for number, line in enumerate(open(OPENITI_RABI, encoding="utf-8").read().split("\n"), start=1):
        marker = re.search(r"PageV(\d+)P(\d+)", line)
        heading = re.match(r"^# \[(\d+)\]\s*(.*)$", line)
        kitab_heading = re.match(r"^# (كتاب\b.*)$", line)
        hadith = re.match(r"^# (\d+)\s*(مكرر)?\s*\)", line)
        if heading:
            bab = (int(heading.group(1)), heading.group(2).strip(), number)
        elif kitab_heading:
            kitab = (kitab[0] + 1, kitab_heading.group(1).strip(), number)
            bab = (None, None, None)
        if hadith:
            entries.append({"number": int(hadith.group(1)), "repeat": bool(hadith.group(2)), "line": number, "page": page,
                            "kitab": kitab, "bab": bab})
        if marker:
            page = (int(marker.group(1)), int(marker.group(2)))
    return entries


# ---------------------------------------------------------------------------------------------------------------------
# Row construction
# ---------------------------------------------------------------------------------------------------------------------

def blank_row(record_id, work_id, tradition, source_label):
    return {
        "record_id": record_id, "hadith_id": "hadith:" + record_id, "work_id": work_id, "tradition": tradition,
        "source_label": source_label,
        "source_order": None, "source_position": None, "source_order_basis": None,
        "volume": None, "volume_source": None,
        "book_number": None, "book_title": None, "book_title_ar": None, "book_source": None,
        "chapter_number": None, "chapter_title": None, "chapter_source": None, "chapter_status": None,
        "report_number": None, "report_number_display": None, "number_scheme": None, "number_scope": None,
        "number_source": None, "number_raw": None, "number_flags": [],
        "printed_number": None, "printed_number_source": None, "hadith_in_chapter": None,
        "section_ordinal": None, "section_companion": None, "section_group": None, "section_basis": None,
        "reference_key": None, "reference_text": None, "reference_unique": False, "reference_basis": None,
        "edition_text": None, "edition_volume": None, "edition_page": None, "edition_source": None,
        "edition_pagination_asserted_to_match_print": None,
        "loaded_chapter_number": None, "loaded_chapter_title": None, "loaded_edition_page": None,
        "flags": [], "review_state": "unreviewed",
    }


def build_thaqalayn(corpus_rows, provider):
    rows, scheme_stats = [], {}
    by_work = collections.defaultdict(list)
    for corpus in corpus_rows:
        record = provider[(corpus["provider_file_id"], corpus["hadith_id"])]
        by_work[corpus["source_work_id"]].append((corpus, record))
    for work_id, pairs in by_work.items():
        scheme = THAQALAYN_SCHEME[work_id]
        pairs.sort(key=lambda pair: (int(pair[1]["volume"]), int(pair[1]["id"])))
        volumes = {str(record["volume"]) for _, record in pairs}
        printed_present = 0
        for corpus, record in pairs:
            path = logic.parse_thaqalayn_url(record["URL"])
            if path is None:
                raise SystemExit(f"unparseable Thaqalayn URL {record['URL']!r}")
            file_id, category, chapter, item = path
            row = blank_row(corpus["record_id"], work_id, "Imami", corpus["source"])
            row["volume"], row["volume_source"] = str(record["volume"]), "provider_json.volume"
            row["book_number"], row["book_title"] = str(record["categoryId"]), record["category"] or None
            row["book_source"] = "provider_json.categoryId/category"
            row["chapter_number"], row["chapter_title"] = str(record["chapterInCategoryId"]), record["chapter"] or None
            row["chapter_source"], row["chapter_status"] = "provider_json.chapterInCategoryId/chapter", "source"
            row["hadith_in_chapter"] = item
            row["source_position"] = int(record["id"])
            row["_file_id"] = corpus["provider_file_id"]
            row["source_order_basis"] = "provider file order: (volume, provider id); provider ids are 1..n per file"
            printed_ar = logic.printed_lead_number(record["arabicText"], "ar")
            printed_en = logic.printed_lead_number(record["englishText"], "en")
            row["_printed_ar"], row["_printed_en"] = printed_ar, printed_en
            row["_path"] = (int(record["volume"]), category, chapter, item)
            if str(record["categoryId"]) != str(category) or str(record["chapterInCategoryId"]) != str(chapter):
                row["flags"].append("provider_fields_disagree_with_url")
            row["number_scheme"] = scheme
            if scheme == "continuous_work":
                value = None
                for language in CONTINUOUS_PRINTED_SOURCE[work_id]:
                    candidate = printed_ar if language == "ar" else printed_en
                    if candidate is not None:
                        value, row["number_source"] = candidate, ("printed_lead_of_provider_arabic_text" if language == "ar"
                                                                  else "printed_lead_of_provider_english_text")
                        break
                row["report_number"], row["number_scope"] = value, "work"
                if value is None:
                    row["number_flags"].append("printed_number_absent_in_provider_text")
                else:
                    printed_present += 1
                row["printed_number"], row["printed_number_source"] = value, row["number_source"]
            elif scheme == "unit_in_book":
                row["report_number"], row["number_scope"] = int(chapter), "book"
                row["number_source"] = "provider_json.chapterInCategoryId"
            else:
                row["report_number"], row["number_scope"] = item, "chapter"
                row["number_source"] = "provider_url_last_segment"
                best = printed_ar if printed_ar is not None else printed_en
                if best is not None:
                    row["printed_number"] = best
                    row["printed_number_source"] = ("printed_lead_of_provider_arabic_text" if printed_ar is not None
                                                    else "printed_lead_of_provider_english_text")
            row["report_number_display"] = None if row["report_number"] is None else str(row["report_number"])
            rows.append(row)
        scheme_stats[work_id] = {"scheme": scheme, "volumes": sorted(volumes, key=int), "reports": len(pairs)}
    return rows, scheme_stats


def finish_thaqalayn(rows):
    """Reference keys, texts and source order for Thaqalayn rows (needs the whole work to test uniqueness)."""
    by_work = collections.defaultdict(list)
    for row in rows:
        by_work[row["work_id"]].append(row)
    for work_id, group in by_work.items():
        group.sort(key=lambda r: (int(r["volume"]), r["source_position"]))
        multi_volume = len({r["volume"] for r in group}) > 1
        for rank, row in enumerate(group, start=1):
            row["source_order"] = rank
        path_keys = [f"v{r['_path'][0]}/b{r['_path'][1]}/c{r['_path'][2]}/h{r['_path'][3]}" for r in group]
        counts = collections.Counter(path_keys)
        for row, key in zip(group, path_keys):
            scheme = row["number_scheme"]
            unique = counts[key] == 1
            row["reference_key"] = key
            row["reference_basis"] = "provider_path_volume_book_chapter_hadith"
            if not unique:
                tie = row["printed_number"]
                tied_key = f"{key}/p{tie}" if tie is not None else None
                row["flags"].append("provider_path_collides_within_work")
                row["_tied_key"] = tied_key
            row["reference_unique"] = unique
            volume = f"Vol. {row['volume']}, " if multi_volume else ""
            book, chapter, item = row["_path"][1], row["_path"][2], row["_path"][3]
            if scheme == "per_chapter":
                row["reference_text"] = f"{volume}Book {book}, Chapter {chapter}, Hadith {item}"
            elif scheme == "unit_in_book":
                title = row["book_title"] or f"Book {book}"
                row["reference_text"] = f"{title} {chapter}" + (f" (part {item})" if item != 1 else "")
            else:
                row["reference_text"] = (f"No. {row['report_number']}" if row["report_number"] is not None
                                         else f"{volume}Book {book}, Chapter {chapter}, Hadith {item}")
        # a colliding path is resolved only where the printed number then tells the rows apart
        tied = collections.Counter(r["_tied_key"] for r in group if r.get("_tied_key"))
        for row in group:
            key = row.get("_tied_key")
            if key and tied[key] == 1:
                row["reference_key"] = key
                row["reference_basis"] = "provider_path_plus_printed_number"
                row["reference_unique"] = True
                row["flags"].append("collision_resolved_by_printed_number")
    return rows


def build_k6(corpus_rows):
    originals, member_sha = read_k6_original()
    with gzip.open(CLEAN_K6, "rt", encoding="utf-8", newline="") as handle:
        clean = [row for row in csv.DictReader(handle) if (row.get("source") or "").strip() in K6_WORKS]
    if len(clean) != len(originals):
        raise SystemExit(f"K6 row count differs: clean {len(clean)}, original {len(originals)}")
    corpus_by_id = {row["record_id"]: row for row in corpus_rows}
    rows = []
    for position, (original, current) in enumerate(zip(originals, clean), start=1):
        if original["text_ar"] != current["text_ar"] or original["source"].strip() != current["source"].strip():
            raise SystemExit(f"K6 join failed at position {position}")
        record_id = "k6:" + (current.get("id") or "").strip()
        corpus = corpus_by_id[record_id]
        if corpus["text_ar"] != current["text_ar"]:
            raise SystemExit(f"corpus text differs for {record_id}")
        source = current["source"].strip()
        row = blank_row(record_id, K6_WORKS[source], "Sunni", source)
        row["source_position"] = position
        row["source_order_basis"] = "row position in the original K6 CSV (archive/datasets.7z), sunnah.com order"
        english, arabic = logic.split_kitab_title(current["chapter"])
        row["book_number"], row["book_title"], row["book_title_ar"] = current["chapter_no"].strip(), english, arabic
        row["book_source"] = "k6_original.chapter_no/chapter (the kitab; the source has no bab)"
        row["chapter_status"] = "no_source_provides_a_bab"
        parsed = logic.parse_number(original["hadith_no"])
        row["number_raw"], row["number_flags"] = original["hadith_no"], list(parsed["flags"])
        row["report_number"], row["report_number_display"] = parsed["value"], logic.display_number(parsed)
        row["number_scheme"], row["number_scope"], row["number_source"] = "continuous_work", "work", "k6_original.hadith_no"
        row["_parsed"] = parsed
        row["_kitab"] = int(current["chapter_no"])
        rows.append(row)
    return rows, member_sha


def finish_k6(rows):
    """Reference key per printed number; a number shared by several reports is only told apart by a derived ordinal."""
    by_work = collections.defaultdict(list)
    for row in rows:
        by_work[row["work_id"]].append(row)
    for group in by_work.values():
        for rank, row in enumerate(group, start=1):
            row["source_order"] = rank
        keys = [None if r["report_number"] is None else (r["book_number"], r["report_number_display"]) for r in group]
        counts = collections.Counter(k for k in keys if k is not None)
        seen = collections.Counter()
        for row, key in zip(group, keys):
            if key is None:
                row["flags"].append("unnumbered_in_source")
                row["reference_key"] = None
                row["reference_text"] = None
                row["reference_basis"] = "none_cite_by_stable_id"
                continue
            seen[key] += 1
            row["reference_key"] = f"b{key[0]}/n{key[1]}"
            row["reference_unique"] = counts[key] == 1
            row["reference_basis"] = "kitab_number_and_printed_number"
            row["reference_text"] = f"Book {key[0]}, Hadith {key[1]}"
            if counts[key] > 1:
                row["flags"].append("number_shared_with_other_reports")
                row["_ordinal"] = (seen[key], counts[key])
    return rows


def build_pure_canon(corpus_rows):
    jsonl = {}
    for line in open(PURE_CANON_JSONL, encoding="utf-8"):
        if line.strip():
            record = json.loads(line)
            jsonl[record["id"]] = record
    header, workbook = read_pure_canon_workbook(set(PURE_CANON_LABELS_AR))
    editions = {}
    for line in open(PURE_CANON_EDITIONS, encoding="utf-8"):
        if line.strip():
            entry = json.loads(line)
            if entry["label_ar"] in PURE_CANON_EDITION_LABEL and entry["row_level_numbering_shared_with_unified"]:
                editions[PURE_CANON_EDITION_LABEL[entry["label_ar"]]] = entry
    workbook_mismatch = collections.Counter()
    rows = []
    by_work = collections.defaultdict(list)
    for corpus in corpus_rows:
        pc_id = corpus["record_id"].split(":", 1)[1]
        record, cells = jsonl[pc_id], workbook.get(pc_id)
        work_id = PURE_CANON_WORKS[corpus["source"].strip()]
        if cells is None:
            workbook_mismatch["row_missing_from_workbook"] += 1
        else:
            if cells.get("M") != record["shelf_no"]:
                workbook_mismatch["shelf_differs_from_jsonl"] += 1
            if (cells.get("N") or "") != record["hadith_no"] and not (record["hadith_no"] in ("", None) and cells.get("N") is None):
                workbook_mismatch["number_differs_from_jsonl"] += 1
        row = blank_row(corpus["record_id"], work_id, "Sunni", corpus["source"].strip())
        row["source_position"] = int(record["shelf_no"])
        row["source_order_basis"] = "Pure Canon shelf_no (workbook column M, 'كتاب الحديث'): the work's own position in the library shelf"
        parsed = logic.parse_number(record["hadith_no"])
        row["number_raw"], row["number_flags"] = record["hadith_no"], list(parsed["flags"])
        row["report_number"], row["report_number_display"] = parsed["value"], logic.display_number(parsed)
        row["number_source"] = "pure_canon.hadith_no (workbook column N, 'رقم الحديث بالكتاب')"
        row["number_scheme"] = "continuous_work" if work_id != "sunni:ahmad" else "per_section"
        row["number_scope"] = "work" if work_id != "sunni:ahmad" else "section"
        if cells:
            row["section_companion"] = (cells.get("F") or "").strip() or None
            row["section_group"] = (cells.get("E") or "").strip() or None
        row["_parsed"] = parsed
        if work_id in editions:
            edition = editions[work_id]
            row["edition_text"] = (edition["edition_text_verbatim"] + " " + edition["volumes_text_verbatim"]).strip()
            row["edition_source"] = f"pure_canon.jsonl header row {edition['pure_canon_id']} (edition the numbering belongs to)"
        by_work[work_id].append(row)
        rows.append(row)
    for work_id, group in by_work.items():
        group.sort(key=lambda r: r["source_position"])
        for rank, row in enumerate(group, start=1):
            row["source_order"] = rank
        if work_id == "sunni:ahmad":
            ordinals = logic.ahmad_section_ordinals([r["_parsed"] for r in group])
            for row, ordinal in zip(group, ordinals):
                row["section_ordinal"] = ordinal
                row["section_basis"] = "derived: a section starts at a `1]` opener or where the number falls back to 1"
            keys = [None if r["report_number"] is None else (r["section_ordinal"], r["report_number_display"]) for r in group]
        else:
            keys = [None if r["report_number"] is None else r["report_number_display"] for r in group]
        counts = collections.Counter(k for k in keys if k is not None)
        for row, key in zip(group, keys):
            if key is None:
                row["reference_basis"] = "none_cite_by_stable_id"
                row["flags"].append("no_usable_number")
                continue
            row["reference_unique"] = counts[key] == 1
            row["reference_basis"] = "printed_number_in_section" if work_id == "sunni:ahmad" else "printed_number"
            if work_id == "sunni:ahmad":
                row["reference_key"] = f"s{key[0]}/n{key[1]}"
                row["reference_text"] = f"Section {key[0]}, No. {key[1]}"
            else:
                row["reference_key"] = f"n{key}"
                row["reference_text"] = f"No. {key}"
            if counts[key] > 1:
                row["flags"].append("number_shared_with_other_reports")
    return rows, dict(workbook_mismatch), header


def build_openiti(corpus_rows):
    rabi_header = read_openiti_header(OPENITI_RABI)
    zayd_header = read_openiti_header(OPENITI_ZAYD)
    source_entries = parse_rabi_source()
    rows, by_work = [], collections.defaultdict(list)
    for corpus in corpus_rows:
        tradition = corpus["record_id"].split(":")[1]
        work_id = OPENITI_WORKS[tradition]
        row = blank_row(corpus["record_id"], work_id, corpus["tradition"], corpus["source"].strip())
        parsed = logic.parse_number(corpus["hadith_no"])
        suffix = re.search(r"_\d+([a-z])$", corpus["hadith_id"])
        row["number_raw"], row["number_flags"] = corpus["hadith_no"], list(parsed["flags"])
        if suffix:
            parsed["letter"] = suffix.group(1)
            row["number_flags"].append("variant_suffix_from_hadith_id")
        row["report_number"], row["report_number_display"] = parsed["value"], logic.display_number(parsed)
        row["volume"], row["volume_source"] = corpus["volume"] or None, "openiti_parse.volume"
        category, chapter = corpus["category"].strip(), corpus["chapter"].strip()
        row["book_title"] = category or None
        row["book_source"] = "openiti_parse.category (section heading in the source text)"
        row["chapter_title"] = chapter or None
        row["chapter_source"], row["chapter_status"] = "openiti_parse.chapter (bab heading in the source text)", "source"
        row["_corpus_chapter_no"] = corpus["chapter_no"]
        row["_page"] = logic.parse_page_ref(corpus["page_ref"])
        row["_hadith_id"] = corpus["hadith_id"]
        page = row["_page"]
        header = rabi_header if tradition == "ibadi" else zayd_header
        if page:
            row["edition_volume"], row["edition_page"] = str(page[0]), str(page[1])
        publisher = header.get("publisher")
        if publisher:
            row["edition_text"] = publisher[1].replace("#META# ", "", 1).strip()
            row["edition_source"] = (f"{(OPENITI_RABI if tradition == 'ibadi' else OPENITI_ZAYD).name} header line {publisher[0]}; "
                                     f"page marker {corpus['page_ref'] or 'absent'}")
        row["edition_pagination_asserted_to_match_print"] = ("pagination_matches_print" in header) if tradition == "ibadi" else False
        if not page:
            row["flags"].append("no_page_marker")
        row["number_scheme"], row["number_scope"] = ("continuous_work", "work")
        row["number_source"] = {"ibadi": "source text numbered line `# n)`", "zaydi": "parser sequence (source lines carry no number)",
                                "imami": "parser sequence (source lines carry no number)"}[tradition]
        row["_parsed"] = parsed
        by_work[work_id].append(row)
        rows.append(row)
    checks = {}
    for work_id, group in by_work.items():
        group.sort(key=lambda r: logic.natural_key(r["_hadith_id"]))
        for rank, row in enumerate(group, start=1):
            row["source_order"], row["source_position"] = rank, rank
            row["source_order_basis"] = "natural order of the parser's hadith_id (rabi_0001, rabi_0001b, rabi_0002 ...)"
    # Ibadi: bind each report to its numbered source line; the source's own kitab/bab/page win, the loaded values are kept
    ibadi = by_work["ibadi:musnad-rabi"]
    occurrence, source_index = collections.Counter(), collections.defaultdict(list)
    for entry in source_entries:
        source_index[(entry["number"], entry["repeat"])].append(entry)
    matched = page_equal = bab_equal = title_equal = 0

    def bare(title):
        return (title or "").replace("باب", "", 1).strip(" :")

    for row in ibadi:
        repeated = "variant_suffix_from_hadith_id" in row["number_flags"]
        key = (row["report_number"], repeated)
        occurrence[key] += 1
        entries = source_index.get(key, [])
        if occurrence[key] > len(entries):
            row["flags"].append("not_found_in_source_text")
            continue
        entry = entries[occurrence[key] - 1]
        matched += 1
        row["source_position"] = entry["line"]
        row["source_order_basis"] = "line number of the report's numbered line in the OpenITI source text"
        loaded_page = row["_page"]
        page_equal += int(entry["page"] == loaded_page)
        if entry["page"] != loaded_page:
            row["loaded_edition_page"] = None if loaded_page is None else str(loaded_page[1])
            row["flags"].append("start_page_differs_from_loaded_page_ref")
        row["edition_volume"], row["edition_page"] = (str(entry["page"][0]), str(entry["page"][1])) if entry["page"] else (None, None)
        if entry["page"] is None:
            row["flags"].append("before_first_page_marker")
        kitab_ordinal, kitab_title, _ = entry["kitab"]
        row["book_number"], row["book_title"] = None, (kitab_title if kitab_ordinal else None)
        row["book_source"] = "source text heading `# كتاب ...` (the source gives no kitab number, so none is emitted)"
        bab_number, bab_title, bab_line = entry["bab"]
        number_equal = str(bab_number) == row["_corpus_chapter_no"]
        text_equal = bare(bab_title) == (row["chapter_title"] or "").strip(" :")
        bab_equal += int(number_equal)
        title_equal += int(text_equal)
        if not (number_equal and text_equal):
            row["loaded_chapter_number"], row["loaded_chapter_title"] = row["_corpus_chapter_no"], row["chapter_title"]
            row["flags"].append("bab_differs_from_loaded_chapter")
        row["chapter_number"], row["chapter_title"] = (str(bab_number), bab_title) if bab_number is not None else (None, None)
        row["chapter_source"] = f"source text heading `# [n] باب ...` (line {bab_line}); numbers restart in each kitab"
    ibadi.sort(key=lambda r: (r["source_position"], r["source_order"]))
    for rank, row in enumerate(ibadi, start=1):
        row["source_order"] = rank
    checks["ibadi_source_lines"] = {"numbered_lines_in_source": len(source_entries), "reports": len(ibadi), "bound": matched,
                                    "start_page_equal_to_loaded_page_ref": page_equal, "bab_number_equal_to_loaded": bab_equal,
                                    "bab_title_equal_to_loaded": title_equal}
    order_vs_id = sum(1 for x, y in zip(sorted(ibadi, key=lambda r: logic.natural_key(r["_hadith_id"])), ibadi) if x is y)
    checks["ibadi_source_order_equals_hadith_id_order"] = order_vs_id
    # Zaydi and Rida: the source numbers neither kitab nor bab, so ordinals count heading runs in source order
    for work_id in ("zaydi:musnad-zayd", "imami:sahifat-al-imam-ali-al-rida"):
        group = by_work[work_id]
        kitab_run = bab_run = 0
        previous = (object(), object())
        for row in group:
            pair = (row["book_title"], row["chapter_title"])
            if pair[0] != previous[0]:
                kitab_run += 1
            if pair != previous:
                bab_run += 1
            previous = pair
            row["book_number"], row["chapter_number"] = None, None
            row["report_number"], row["report_number_display"] = None, None
            row["number_scheme"], row["number_scope"], row["number_source"] = None, None, "none: the source text numbers no hadith"
            row["flags"].append("source_numbers_no_kitab_bab_or_hadith_none_emitted")
            row["flags"].append("page_is_first_marker_after_hadith_start_may_be_one_page_late")
        pages = [r["_page"][1] for r in group if r["_page"]]
        checks[f"{work_id}_page_order_monotone"] = {"steps": len(pages) - 1, "nondecreasing": sum(1 for x, y in zip(pages, pages[1:]) if y >= x)}
    # reference keys
    for work_id, group in by_work.items():
        keys = [None if r["report_number"] is None else f"{r['report_number_display']}" for r in group]
        counts = collections.Counter(k for k in keys if k is not None)
        for row, key in zip(group, keys):
            if key is None:
                row["reference_basis"] = "none_cite_by_stable_id"
                continue
            row["reference_key"] = f"n{key}"
            row["reference_unique"] = counts[key] == 1
            row["reference_basis"] = "printed_number" if work_id == "ibadi:musnad-rabi" else "parser_sequence_number"
            page = row["_page"]
            row["reference_text"] = f"No. {key}" + (f" (vol. {page[0]}, p. {page[1]})" if page else "")
            if counts[key] > 1:
                row["flags"].append("number_shared_with_other_reports")
    return rows, checks


# ---------------------------------------------------------------------------------------------------------------------
# External claims (hadith-kg, Riwayat): the dataset's own statement, never merged into our fields
# ---------------------------------------------------------------------------------------------------------------------

def read_kg_books():
    connection = sqlite3.connect(f"file:{KG_DB.as_posix()}?mode=ro&immutable=1", uri=True)
    books = {row[0]: {"name": row[1], "author": row[2], "city": row[3], "publisher": row[4], "edition": row[5]}
             for row in connection.execute("select id, name, author_name, city, dar, tabaa from books")}
    connection.close()
    return books


def build_external_claims(rows_by_id):
    kg_books = read_kg_books()
    claims, disagreements = [], []
    with gzip.open(CROSSWALK, "rt", encoding="utf-8") as handle:
        for line in handle:
            entry = json.loads(line)
            if not entry["used"]:
                continue
            row = rows_by_id.get(entry["record_id"])
            if row is None:
                continue
            locator = entry["external_locator"]
            claim = {"record_id": entry["record_id"], "hadith_id": row["hadith_id"], "work_id": row["work_id"],
                     "dataset": entry["dataset"], "external_report_id": entry["external_report_id"],
                     "match_class": entry["match_class"], "arabic_sha256": entry["arabic_sha256"],
                     "external_arabic_sha256": entry["external_arabic_sha256"], "review_state": "unreviewed",
                     "asserted_by": "hadith-kg (CC BY 4.0)" if entry["dataset"] == "hadith_kg" else "Riwayat corpus (CC0 layer)",
                     "claimed_number": None, "claimed_page": None, "claimed_chapter": None, "claimed_hadith_in_chapter": None,
                     "claimed_edition": None, "comparison": {}}
            if entry["dataset"] == "hadith_kg":
                book = kg_books[locator["book_id"]]
                claim["claimed_number"], claim["claimed_page"] = locator["no_inbook"], locator["page_no"]
                claim["claimed_edition"] = {"book_as_named": book["name"], "city": book["city"], "publisher": book["publisher"],
                                            "edition": book["edition"], "volume": None,
                                            "note": "page_no as hadith-kg gives it; no volume is recorded"}
                if row["report_number"] is not None and row["tradition"] != "Imami":
                    claim["comparison"]["our_number"] = row["report_number"]
                    claim["comparison"]["number_equal"] = row["report_number"] == locator["no_inbook"]
            else:
                number = locator.get("number")
                parts = (number or "").split(":")[1:]
                if row["tradition"] == "Imami" and len(parts) >= 2 and all(p.isdigit() for p in parts) and "chapter_number" in row                         and row["hadith_in_chapter"] is not None:
                    # Thaqalayn locator `<work>:[<volume>:[<book>:]]<chapter>:<hadith>`; the last two are chapter and hadith
                    ints = [int(p) for p in parts]
                    claim["claimed_chapter"], claim["claimed_hadith_in_chapter"] = ints[-2], ints[-1]
                    claim["claimed_number"] = number
                    claim["comparison"] = {
                        "our_chapter": int(row["chapter_number"]), "our_hadith_in_chapter": row["hadith_in_chapter"],
                        "chapter_equal": int(row["chapter_number"]) == ints[-2], "hadith_equal": row["hadith_in_chapter"] == ints[-1]}
                    if len(ints) == 4:  # volume, book, chapter, hadith (al-Kafi)
                        claim["comparison"]["volume_and_book_equal"] = (str(ints[0]), str(ints[1])) == (row["volume"], row["book_number"])
                elif number and number.isdigit():
                    claim["claimed_number"] = int(number)
                    if row["report_number"] is not None:
                        claim["comparison"] = {"our_number": row["report_number"], "number_equal": row["report_number"] == int(number)}
                else:
                    claim["claimed_number"] = number
            claims.append(claim)
            comparison = claim["comparison"]
            differs = (comparison.get("number_equal") is False or comparison.get("chapter_equal") is False
                       or comparison.get("hadith_equal") is False or comparison.get("volume_and_book_equal") is False)
            if differs:
                disagreements.append({k: claim[k] for k in ("record_id", "hadith_id", "work_id", "dataset", "external_report_id",
                                                            "claimed_number", "claimed_page", "claimed_chapter",
                                                            "claimed_hadith_in_chapter", "comparison")})
    return claims, disagreements


# ---------------------------------------------------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------------------------------------------------

def audit(rows, production, thaqalayn_stats, extra):
    """Per work: reports, citable before (stored number, current site string) and after (this sidecar)."""
    by_work = collections.defaultdict(list)
    for row in rows:
        by_work[row["work_id"]].append(row)
    result = {}
    for work_id, group in sorted(by_work.items()):
        entry = {"reports": len(group), "tradition": group[0]["tradition"], "number_scheme": group[0]["number_scheme"]}
        if production:
            prod = [production[r["record_id"]] for r in group]
            stored = [p["hadith_no"].strip() or None for p in prod]
            stored = [None if s is None or s == "0" else s for s in stored]
            counts = collections.Counter(s for s in stored if s)
            entry["before_stored_number"] = {
                "reports_with_a_number": sum(counts.values()),
                "reports_whose_number_is_unique_in_work": sum(1 for s in stored if s and counts[s] == 1),
                "distinct_numbers": len(counts)}
            strings = [logic.site_reference_today(p["id"], p["hadith_no"], p["url"], p["volume"], p["page_ref"], p["book_number"])
                       for p in prod]
            string_counts = collections.Counter(strings)
            fallback = [bool(re.search(r"record |Record |unnumbered", s)) for s in strings]
            entry["before_site_reference_string"] = {
                "reports_whose_string_is_unique_in_work": sum(1 for s in strings if string_counts[s] == 1),
                "of_which_a_real_reference_not_a_record_id_fallback": sum(1 for s, f in zip(strings, fallback) if string_counts[s] == 1 and not f),
                "reports_showing_a_record_id_fallback": sum(fallback),
                "distinct_strings": len(string_counts)}
        keys = [r["reference_key"] for r in group]
        key_counts = collections.Counter(k for k in keys if k)
        entry["after"] = {
            "reports_with_a_reference_key": sum(key_counts.values()),
            "reports_unique_by_printed_or_provider_reference": sum(1 for r in group if r["reference_unique"]),
            "reports_sharing_a_reference": sum(v for v in key_counts.values() if v > 1),
            "distinct_reference_keys_repeated": sum(1 for v in key_counts.values() if v > 1),
            "reports_without_reference": sum(1 for r in group if not r["reference_key"]),
            "source_order_unique": len({r["source_order"] for r in group}) == len(group),
        }
        entry["chapters_recovered"] = {
            "reports_with_book_level": sum(1 for r in group if r["book_number"] or r["book_title"]),
            "reports_with_chapter_bab": sum(1 for r in group if r["chapter_status"] == "source"
                                            and (r["chapter_number"] or r["chapter_title"])),
        }
        entry["edition_locators"] = {
            "reports_with_page": sum(1 for r in group if r["edition_page"]),
            "reports_with_edition_text": sum(1 for r in group if r["edition_text"]),
        }
        result[work_id] = entry
    result["_thaqalayn_scheme"] = thaqalayn_stats
    result.update(extra)
    return result


def thaqalayn_evidence(rows):
    """Measured uniqueness of each candidate number in each scope, per Thaqalayn work (the evidence behind THAQALAYN_SCHEME)."""
    by_work = collections.defaultdict(list)
    for row in rows:
        by_work[row["work_id"]].append(row)
    evidence = {}
    for work_id, group in by_work.items():
        entry = {}
        candidates = {
            "url_hadith": lambda r: r["hadith_in_chapter"],
            "chapterInCategoryId": lambda r: int(r["chapter_number"]),
            "printed_arabic_lead": lambda r: r["_printed_ar"],
            "printed_english_lead": lambda r: r["_printed_en"],
        }
        scopes = {"work": lambda r: (), "volume": lambda r: (r["volume"],), "book": lambda r: (r["volume"], r["book_number"]),
                  "chapter": lambda r: (r["volume"], r["book_number"], r["chapter_number"])}
        for name, getter in candidates.items():
            covered = sum(1 for r in group if getter(r) is not None)
            per_scope = {}
            for scope_name, scope in scopes.items():
                keys = [None if getter(r) is None else scope(r) + (getter(r),) for r in group]
                _, unique, _ = logic.unique_rows(keys)
                per_scope[scope_name] = round(100 * unique / covered, 1) if covered else None
            entry[name] = {"coverage_percent": round(100 * covered / len(group), 1), "unique_percent_by_scope": per_scope}
        printed = [(r["_printed_ar"] if r["_printed_ar"] is not None else r["_printed_en"], r["hadith_in_chapter"]) for r in group]
        both = [(a, b) for a, b in printed if a is not None]
        entry["printed_equals_url_hadith_percent"] = round(100 * sum(1 for a, b in both if a == b) / len(both), 1) if both else None
        evidence[work_id] = entry
    return evidence


def read_production_dump(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return {row["record_id"]: row for row in csv.DictReader(handle)}


def compare_with_production(corpus_rows, production):
    """Do the loaded rows equal the corpus on the fields this lane reads?"""
    differences = collections.Counter()
    missing = 0
    for row in corpus_rows:
        prod = production.get(row["record_id"])
        if prod is None:
            missing += 1
            continue
        for ours, theirs in (("hadith_no", "hadith_no"), ("volume", "volume"), ("chapter_no", "chapter_no"), ("url", "url"),
                             ("page_ref", "page_ref")):
            if (row[ours] or "").strip() != (prod[theirs] or "").strip():
                differences[ours] += 1
    return {"corpus_reports": len(corpus_rows), "production_reports": len(production), "corpus_not_in_production": missing,
            "field_differences": dict(differences)}


# ---------------------------------------------------------------------------------------------------------------------
# Provenance (see structure_provenance.py)
# ---------------------------------------------------------------------------------------------------------------------

def file_hashes():
    """key -> (repo-relative path, sha256) for every file a reference can be read from."""
    out = {"k6": (str(K6_ARCHIVE.relative_to(DATASETS.parent)) + ":" + K6_MEMBER, read_k6_member_sha()),
           "pc": (str(PURE_CANON_JSONL.relative_to(REPO)), sha256_file(PURE_CANON_JSONL)),
           "xlsx": (str(PURE_CANON_XLSX.relative_to(REPO)), sha256_file(PURE_CANON_XLSX)),
           "rabi": (str(OPENITI_RABI.relative_to(REPO)), sha256_file(OPENITI_RABI)),
           "zayd": (str(OPENITI_ZAYD.relative_to(REPO)), sha256_file(OPENITI_ZAYD)),
           "kg": (str(KG_DB.relative_to(REPO)), sha256_file(KG_DB)),
           "riwayat": (str(RIWAYAT_DB.relative_to(REPO)), sha256_file(RIWAYAT_DB))}
    for path in sorted(THAQALAYN_DIR.glob("[0-9]*.json"), key=lambda p: int(p.stem)):
        out[f"thq:{path.stem}"] = (str(path.relative_to(REPO)), sha256_file(path))
    return {key: (path.replace("\\", "/"), sha) for key, (path, sha) in out.items()}


def read_k6_member_sha():
    data = subprocess.run([BSDTAR, "-xOf", str(K6_ARCHIVE), K6_MEMBER], capture_output=True, timeout=300, check=True).stdout
    return hashlib.sha256(data).hexdigest()


KG_VERSION = "hadith-kg Hugging Face revision 8ae7e3d5be284a6b32a989cd41866343fc19501c"
RIWAYAT_VERSION = "Riwayat corpus v1, Zenodo doi:10.5281/zenodo.23630501"

# field group -> emitted row columns withdrawn when the group's record fails validation
GROUP_COLUMNS = {
    "volume": ["volume", "volume_source"],
    "book": ["book_number", "book_title", "book_title_ar", "book_source"],
    "chapter": ["chapter_number", "chapter_title", "chapter_source"],
    "number": ["report_number", "report_number_display", "number_scheme", "number_scope", "number_source", "printed_number",
               "printed_number_source"],
    "hadith_in_chapter": ["hadith_in_chapter"],
    "source_order": ["source_order", "source_position", "source_order_basis"],
    "edition": ["edition_text", "edition_volume", "edition_page", "edition_source", "edition_pagination_asserted_to_match_print"],
    "section": ["section_ordinal", "section_companion", "section_group", "section_basis"],
}
REFERENCE_DEPENDS = {"number", "volume", "book", "chapter", "hadith_in_chapter"}


def _heading_lines(path):
    lines = open(path, encoding="utf-8").read().split("\n")
    return [re.sub(r"^[#\s|~]+", "", line).strip() for line in lines if line.startswith("#")]


def make_records(row, files, registry, headings):
    """Provenance records for every emitted reference field of one report."""
    out = []
    work = row["work_id"]

    def add(group, field, value, code, file_key, record_id, source_field, kind="source_value", derivation=None, edition=None):
        if value in (None, ""):
            return
        path, sha = files[file_key]
        meta = registry.get(code, {"name": None, "licence": None})
        out.append({"record_id": row["record_id"], "hadith_id": row["hadith_id"], "work_id": work, "group": group, "field": field,
                    "value": str(value), "claim_by": "project_source_file", "kind": kind, "derivation": derivation,
                    "source_code": code, "source_name": meta["name"], "licence": meta["licence"], "source_file": path,
                    "source_sha256": sha, "source_version": None, "source_record_id": record_id, "source_field": source_field,
                    "edition": edition, "review_state": "unreviewed"})

    rank_note = "dense rank of the source's own position key within the work (ties impossible: keys are unique)"
    if row["record_id"].startswith("thaqalayn:"):
        key, rid = f"thq:{row['_file_id']}", f"provider id {row['source_position']}"
        add("volume", "volume", row["volume"], "THQ", key, rid, "volume")
        add("book", "book_number", row["book_number"], "THQ", key, rid, "categoryId, category")
        add("chapter", "chapter_number", row["chapter_number"], "THQ", key, rid, "chapterInCategoryId, chapter")
        add("hadith_in_chapter", "hadith_in_chapter", row["hadith_in_chapter"], "THQ", key, rid, "URL (last path segment)")
        number_field = {"provider_url_last_segment": "URL (last path segment)", "provider_json.chapterInCategoryId": "chapterInCategoryId",
                        "printed_lead_of_provider_arabic_text": "arabicText (leading numeral)",
                        "printed_lead_of_provider_english_text": "englishText (leading numeral)"}
        add("number", "number", row["report_number"], "THQ", key, rid, number_field.get(row["number_source"], row["number_source"]))
        add("number", "printed_number", row["printed_number"], "THQ", key, rid, number_field.get(row["printed_number_source"] or "", ""))
        add("source_order", "source_order", row["source_order"], "THQ", key, rid, "volume, id", "derived", rank_note)
    elif row["record_id"].startswith("k6:"):
        rid = f"row {row['source_position']} of the original CSV"
        add("book", "book_number", row["book_number"], "SUN", "k6", rid, "chapter_no, chapter (the kitab)")
        add("number", "number", row["report_number"], "SUN", "k6", rid, "hadith_no")
        add("source_order", "source_order", row["source_order"], "SUN", "k6", rid, "row position", "derived", rank_note)
    elif row["record_id"].startswith("pure-canon:"):
        pc = row["record_id"].split(":", 1)[1]
        add("number", "number", row["report_number"], "NMC", "pc", pc, "hadith_no (workbook column N)")
        add("source_order", "source_order", row["source_order"], "NMC", "pc", pc, "shelf_no (workbook column M)", "derived", rank_note)
        row_a = pc.split("_", 1)[1]
        add("section", "section_companion", row["section_companion"], "NMC", "xlsx", f"Sheet1 row with A={row_a}", "column F (companion)")
        add("section", "section_group", row["section_group"], "NMC", "xlsx", f"Sheet1 row with A={row_a}", "column E (musnad group)")
        add("section", "section_ordinal", row["section_ordinal"], "NMC", "pc", pc, "hadith_no (restarts)", "derived",
            "section starts at a `1]` opener or where hadith_no falls below the previous row, in shelf_no order (structure_logic.ahmad_section_ordinals)")
        if row["edition_text"]:
            header = re.search(r"header row (pc_\d+)", row["edition_source"] or "")
            add("edition", "edition_text", row["edition_text"], "NMC", "pc", header.group(1) if header else None,
                "source column of the work's header row", edition=row["edition_text"])
    elif row["record_id"].startswith("openiti:"):
        ibadi = work == "ibadi:musnad-rabi"
        key, other = ("rabi" if ibadi else "zayd"), row["_hadith_id"]
        rid = f"line {row['source_position']}" if ibadi else f"hadith_id {other}"
        if ibadi:
            add("number", "number", row["report_number"], "OITI", key, rid, "numbered line `# n)`")
            add("chapter", "chapter_number", row["chapter_number"], "OITI", key, rid, "heading `# [n] باب` preceding the line")
            add("book", "book_title", row["book_title"], "OITI", key, rid, "heading `# كتاب` preceding the line")
            if row["volume"] and row["_page"]:
                add("volume", "volume", row["volume"], "OITI", key, rid, "PageV<vol>P<page> marker in force at the line")
        else:
            for group, field, value in (("book", "book_title", row["book_title"]), ("chapter", "chapter_title", row["chapter_title"])):
                probe = (value or "").strip()[:30]
                if probe and any(line.startswith(probe) for line in headings):
                    add(group, field, value, "OITI", key, f"heading text {probe!r}", "heading line (`### |` kitab, `### ||` bab)")
            if row["volume"] and row["_page"]:
                add("volume", "volume", row["volume"], "OITI", key, f"page marker {row['_page']}", "PageV<vol>P<page> marker")
        add("source_order", "source_order", row["source_order"], "OITI", key, rid, "line position" if ibadi else "order of hadith paragraphs",
            "derived", rank_note)
        if row["edition_text"]:
            header_line = re.search(r"header line (\d+)", row["edition_source"] or "")
            add("edition", "edition_text", row["edition_text"], "OITI", key, f"header line {header_line.group(1)}" if header_line else None,
                "publisher line in the file header (verbatim)", edition=row["edition_text"])
        if row["edition_page"] and row["edition_text"]:
            add("edition", "edition_page", row["edition_page"], "OITI", key, rid if ibadi else f"page marker {row['_page']}",
                "PageV<vol>P<page> marker; publisher line in the file header", edition=row["edition_text"])
    return out


def make_claim_records(claim, files, registry):
    """Records for one external claim, labelled as that dataset's claim."""
    kg = claim["dataset"] == "hadith_kg"
    code, key = ("HKG", "kg") if kg else ("RWY", "riwayat")
    path, sha = files[key]
    meta = registry[code]
    base = {"record_id": claim["record_id"], "hadith_id": claim["hadith_id"], "work_id": claim["work_id"], "group": "external",
            "claim_by": "external_dataset", "kind": "source_value", "derivation": None, "source_code": code, "source_name": meta["name"],
            "licence": meta["licence"], "source_file": path, "source_sha256": sha,
            "source_version": KG_VERSION if kg else RIWAYAT_VERSION,
            "source_record_id": (f"hadiths.id {claim['external_report_id']}" if kg else f"hadith.id {claim['external_report_id']}"),
            "review_state": "unreviewed (the dataset's claim, not ours)"}
    out = []
    value = claim["claimed_number"]
    if value not in (None, ""):
        out.append({**base, "field": "external_number", "value": str(value), "edition": None,
                    "source_field": "hadiths.no_inbook" if kg else "hadith.number"})
    if kg and claim["claimed_page"]:
        edition = claim["claimed_edition"]
        named = ", ".join(x for x in (edition["publisher"], edition["city"], edition["edition"]) if x)
        out.append({**base, "field": "edition_page", "value": str(claim["claimed_page"]), "edition": named or None,
                    "source_field": "hadiths.page_no; books.dar, books.city, books.tabaa"})
    return out


def make_all_provenance(rows, claims, files, registry):
    known = {sha for _, sha in files.values()}
    headings = _heading_lines(OPENITI_ZAYD)
    by_work = collections.defaultdict(lambda: collections.Counter())
    by_source = collections.defaultdict(lambda: collections.Counter())
    by_group = collections.defaultdict(lambda: collections.Counter())
    problems = collections.Counter()
    kept, withdrawn_samples = [], []
    for row in rows:
        records = make_records(row, files, registry, headings)
        failed_groups = set()
        for record in records:
            issues = provenance.validate_record(record, registry, known)
            ok = not issues
            by_work[row["work_id"]]["pass" if ok else "fail"] += 1
            by_source[record["source_code"]]["pass" if ok else "fail"] += 1
            by_group[record["group"]]["pass" if ok else "fail"] += 1
            if ok:
                kept.append(record)
            else:
                failed_groups.add(record["group"])
                for issue in issues:
                    problems[issue] += 1
                if len(withdrawn_samples) < 10:
                    withdrawn_samples.append({"record_id": row["record_id"], "field": record["field"], "issues": issues})
        # a group that has a value in the row but no passing record is not emitted
        for group, columns in GROUP_COLUMNS.items():
            has_value = any(row.get(c) not in (None, "", []) for c in columns if not c.endswith("_source") and c != "number_scope"
                            and c != "number_scheme" and c != "edition_pagination_asserted_to_match_print")
            sourced = any(r["group"] == group and r["record_id"] == row["record_id"] for r in records) and group not in failed_groups
            if has_value and not sourced:
                for column in columns:
                    row[column] = None
                row["flags"].append(f"withdrawn_unsourced:{group}")
                by_work[row["work_id"]]["withdrawn_group"] += 1
                failed_groups.add(group)
        if failed_groups & (REFERENCE_DEPENDS if row["record_id"].startswith("thaqalayn:") else {"number"}):
            row["reference_key"] = row["reference_text"] = None
            row["reference_unique"] = False
            row["reference_basis"] = "withdrawn_unsourced"
    claim_ok, claim_records = [], []
    for claim in claims:
        records = make_claim_records(claim, files, registry)
        ok = bool(records) and all(not provenance.validate_record(r, registry, known) for r in records)
        claim_ok.append(ok)
        for r in records:
            good = not provenance.validate_record(r, registry, known)
            by_work[claim["work_id"]]["pass" if good else "fail"] += 1
            by_source[r["source_code"]]["pass" if good else "fail"] += 1
            by_group["external"]["pass" if good else "fail"] += 1
        if ok:
            claim_records.extend(records)
    report = {
        "standard": "every emitted reference needs source_code (registry), licence (registry), source_file, source_sha256 (a hash of an input file), "
                    "source_record_id, source_field; external claims also source_version and claim_by=external_dataset; derived values name their rule",
        "records_passing_by_work": {k: dict(v) for k, v in sorted(by_work.items())},
        "records_passing_by_source": {k: dict(v) for k, v in sorted(by_source.items())},
        "records_passing_by_field_group": {k: dict(v) for k, v in sorted(by_group.items())},
        "problems": dict(problems), "problem_samples": withdrawn_samples,
        "source_files": {k: {"file": p, "sha256": h} for k, (p, h) in sorted(files.items())},
        "registry_codes_used": {c: registry[c] for c in sorted({r["source_code"] for r in kept + claim_records})},
        "rows_with_a_withdrawn_group": sum(1 for r in rows if any(str(f).startswith("withdrawn_unsourced") for f in r["flags"])),
        "claims_total": len(claims), "claims_passing": sum(claim_ok),
    }
    return kept, claim_records, {"report": report, "claim_ok": claim_ok}


# ---------------------------------------------------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------------------------------------------------

def build_nodes(rows):
    """One row per distinct book (kitab) and chapter (bab) per work, with the titles the sources carry."""
    nodes = collections.OrderedDict()
    for row in sorted(rows, key=lambda r: (r["work_id"], r["source_order"])):
        parent = None
        if row["volume"] is not None or row["work_id"].startswith("imami:"):
            parent_key = (row["work_id"], "volume", row["volume"])
            if parent_key not in nodes:
                nodes[parent_key] = {"work_id": row["work_id"], "level": "volume", "volume": row["volume"], "book_number": None,
                                     "chapter_number": None, "title": None, "title_ar": None, "source": row["volume_source"],
                                     "first_source_order": row["source_order"], "report_count": 0, "titles_seen": []}
            nodes[parent_key]["report_count"] += 1
        if row["book_number"] is not None or row["book_title"]:
            key = (row["work_id"], "book", row["volume"], row["book_number"], row["book_title"] if row["book_number"] is None else None)
            if key not in nodes:
                nodes[key] = {"work_id": row["work_id"], "level": "book", "volume": row["volume"], "book_number": row["book_number"],
                              "chapter_number": None, "title": row["book_title"], "title_ar": row["book_title_ar"],
                              "source": row["book_source"], "first_source_order": row["source_order"], "report_count": 0,
                              "titles_seen": []}
            node = nodes[key]
            node["report_count"] += 1
            if row["book_title"] and row["book_title"] not in node["titles_seen"]:
                node["titles_seen"].append(row["book_title"])
        if row["chapter_status"] == "source" and (row["chapter_number"] or row["chapter_title"]):
            ordinal = row.get("_bab_ordinal")
            key = (row["work_id"], "chapter", row["volume"], row["book_number"], row["chapter_number"],
                   row["chapter_title"] if row["chapter_number"] is None else None, row["book_title"] if row["book_number"] is None else None)
            if key not in nodes:
                nodes[key] = {"work_id": row["work_id"], "level": "chapter", "volume": row["volume"], "book_number": row["book_number"],
                              "chapter_number": row["chapter_number"], "chapter_ordinal_derived": ordinal, "title": row["chapter_title"],
                              "title_ar": None, "source": row["chapter_source"], "first_source_order": row["source_order"],
                              "report_count": 0, "titles_seen": []}
            node = nodes[key]
            node["report_count"] += 1
            if row["chapter_title"] and row["chapter_title"] not in node["titles_seen"]:
                node["titles_seen"].append(row["chapter_title"])
    out = []
    for key, node in nodes.items():
        node["title_conflict"] = len(node["titles_seen"]) > 1
        if node["title_conflict"]:
            node["title"] = node["titles_seen"][0]
        node.pop("titles_seen") if not node["title_conflict"] else None
        out.append(node)
    return out


# ---------------------------------------------------------------------------------------------------------------------

FLAT_COLUMNS = [
    "record_id", "hadith_id", "work_id", "tradition", "source_order", "source_position", "source_order_basis",
    "volume", "volume_source", "book_number", "book_title", "book_title_ar", "book_source",
    "chapter_number", "chapter_title", "chapter_source", "chapter_status",
    "report_number", "report_number_display", "number_scheme", "number_scope", "number_source", "number_raw", "number_flags",
    "printed_number", "printed_number_source", "hadith_in_chapter",
    "section_ordinal", "section_companion", "section_group", "section_basis",
    "reference_key", "reference_text", "reference_unique", "reference_basis",
    "edition_text", "edition_volume", "edition_page", "edition_source", "edition_pagination_asserted_to_match_print",
    "loaded_chapter_number", "loaded_chapter_title", "loaded_edition_page",
    "flags", "review_state",
]


def public_row(row):
    out = {column: row[column] for column in FLAT_COLUMNS}
    ordinal = row.get("_ordinal")
    if ordinal:
        out["shared_number_ordinal"], out["shared_number_group_size"] = ordinal
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--production-dump", help="CSV from the read-only SELECT documented in README.md (record_id, hadith_no, ...)")
    arguments = parser.parse_args()

    corpus = read_corpus()
    production = read_production_dump(arguments.production_dump) if arguments.production_dump else None
    production_check = compare_with_production(corpus, production) if production else None

    thaqalayn_provider = read_thaqalayn()
    thaqalayn_corpus = [r for r in corpus if r["record_id"].startswith("thaqalayn:")]
    thaqalayn_rows, thaqalayn_stats = build_thaqalayn(thaqalayn_corpus, thaqalayn_provider)
    thaqalayn_rows = finish_thaqalayn(thaqalayn_rows)
    evidence = thaqalayn_evidence(thaqalayn_rows)

    k6_rows, k6_member_sha = build_k6([r for r in corpus if r["record_id"].startswith("k6:")])
    k6_rows = finish_k6(k6_rows)
    pure_rows, workbook_mismatch, workbook_header = build_pure_canon([r for r in corpus if r["record_id"].startswith("pure-canon:")])
    openiti_rows, openiti_checks = build_openiti([r for r in corpus if r["record_id"].startswith("openiti:")])

    all_rows = thaqalayn_rows + k6_rows + pure_rows + openiti_rows
    if len(all_rows) != len(corpus) or len({r["record_id"] for r in all_rows}) != len(corpus):
        raise SystemExit(f"coverage: {len(all_rows)} rows for {len(corpus)} corpus reports")
    all_rows.sort(key=lambda r: (r["work_id"], r["source_order"]))
    rows_by_id = {r["record_id"]: r for r in all_rows}
    claims, disagreements = build_external_claims(rows_by_id)
    hashes = file_hashes()
    registry = provenance.load_registry(REGISTRY_TS)
    records, claim_records, validation = make_all_provenance(all_rows, claims, hashes, registry)
    claims = [c for c, ok in zip(claims, validation["claim_ok"]) if ok]
    kept_claims = {(c["record_id"], c["dataset"]) for c in claims}
    disagreements = [d for d in disagreements if (d["record_id"], d["dataset"]) in kept_claims]
    rows_by_id = {r["record_id"]: r for r in all_rows}

    summary = audit(all_rows, production, thaqalayn_stats, {})
    # external coverage per work
    coverage = collections.defaultdict(lambda: collections.Counter())
    comparisons = collections.defaultdict(lambda: collections.Counter())
    for claim in claims:
        coverage[claim["work_id"]][claim["dataset"]] += 1
        if claim["claimed_page"]:
            coverage[claim["work_id"]]["hadith_kg_with_page"] += 1
        for field in ("number_equal", "chapter_equal", "hadith_equal", "volume_and_book_equal"):
            if field in claim["comparison"]:
                comparisons[claim["work_id"]][f"{claim['dataset']}.{field}={claim['comparison'][field]}"] += 1
    disagreement_counts = collections.defaultdict(lambda: collections.Counter())
    for item in disagreements:
        disagreement_counts[item["work_id"]][item["dataset"]] += 1
    for work_id in summary:
        if work_id.startswith("_"):
            continue
        summary[work_id]["external_claims"] = dict(coverage[work_id])
        summary[work_id]["external_comparison"] = dict(sorted(comparisons[work_id].items()))
        summary[work_id]["external_disagreements"] = dict(disagreement_counts[work_id])
    summary["_thaqalayn_measured_evidence"] = evidence
    summary["_production_cross_check"] = production_check
    summary["_pure_canon_workbook_cross_check"] = workbook_mismatch
    summary["_openiti_checks"] = openiti_checks
    ahmad = [r for r in all_rows if r["work_id"] == "sunni:ahmad"]
    sections = collections.Counter(r["section_ordinal"] for r in ahmad)
    dominant = collections.defaultdict(collections.Counter)
    for r in ahmad:
        dominant[r["section_ordinal"]][r["section_companion"]] += 1
    summary["_ahmad_sections"] = {
        "sections_derived": len(sections), "reports_in_sections_of_one": sum(1 for v in sections.values() if v == 1),
        "sections_where_one_companion_label_covers_95_percent": sum(
            1 for ordinal, c in dominant.items() if c.most_common(1)[0][1] >= 0.95 * sections[ordinal]),
        "distinct_companion_labels": len({r["section_companion"] for r in ahmad}),
        "opener_rows": sum(1 for r in ahmad if "trailing_bracket" in r["number_flags"]),
    }
    k6_stats = collections.defaultdict(collections.Counter)
    for r in k6_rows:
        for flag in r["number_flags"]:
            k6_stats[r["work_id"]][flag] += 1
        if r["_kitab"] is not None:
            k6_stats[r["work_id"]]["kitab_numbers"] += 0
    summary["_k6_number_flags"] = {k: dict(v) for k, v in k6_stats.items()}

    nodes = build_nodes(all_rows)
    public = [public_row(r) for r in all_rows]

    outputs = {}
    outputs["report_structure.jsonl.gz"] = write_jsonl_gz(HERE / "report_structure.jsonl.gz", public)
    outputs["report_structure_flat.csv.gz"] = write_csv_gz(HERE / "report_structure_flat.csv.gz", FLAT_COLUMNS, public)
    outputs["reference_provenance.jsonl.gz"] = write_jsonl_gz(HERE / "reference_provenance.jsonl.gz", records + claim_records)
    with open(HERE / "provenance_validation.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(validation["report"], handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    outputs["structure_nodes.jsonl.gz"] = write_jsonl_gz(HERE / "structure_nodes.jsonl.gz", nodes)
    outputs["external_locator_claims.jsonl.gz"] = write_jsonl_gz(HERE / "external_locator_claims.jsonl.gz", claims)
    outputs["structure_disagreements.jsonl.gz"] = write_jsonl_gz(HERE / "structure_disagreements.jsonl.gz", disagreements)
    with open(HERE / "numbering_audit.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    rows_csv = []
    for work_id, entry in summary.items():
        if work_id.startswith("_"):
            continue
        rows_csv.append({
            "work_id": work_id, "tradition": entry["tradition"], "reports": entry["reports"], "number_scheme": entry["number_scheme"],
            "before_unique_stored_number": entry.get("before_stored_number", {}).get("reports_whose_number_is_unique_in_work"),
            "before_unique_site_reference": entry.get("before_site_reference_string", {}).get("of_which_a_real_reference_not_a_record_id_fallback"),
            "after_unique_reference": entry["after"]["reports_unique_by_printed_or_provider_reference"],
            "after_without_reference": entry["after"]["reports_without_reference"],
            "after_sharing_reference": entry["after"]["reports_sharing_a_reference"],
            "reports_with_book_level": entry["chapters_recovered"]["reports_with_book_level"],
            "reports_with_chapter_bab": entry["chapters_recovered"]["reports_with_chapter_bab"],
            "reports_with_page": entry["edition_locators"]["reports_with_page"],
            "reports_with_external_page_claim": entry["external_claims"].get("hadith_kg_with_page", 0),
            "reports_with_edition_text": entry["edition_locators"]["reports_with_edition_text"],
            "external_claims": "|".join(f"{k}={v}" for k, v in sorted(entry["external_claims"].items())),
        })
    audit_columns = list(rows_csv[0])
    outputs["numbering_audit.csv.gz"] = write_csv_gz(HERE / "numbering_audit.csv.gz", audit_columns, rows_csv)

    inputs = {
        "corpus_all_hadiths_unified.incomplete.csv.gz": sha256_file(CORPUS), "all_hadiths_clean.csv.gz": sha256_file(CLEAN_K6),
        "archive/datasets.7z": sha256_file(K6_ARCHIVE), "archive/datasets.7z:all_hadiths_clean.csv (member)": k6_member_sha,
        "pure_canon.jsonl": sha256_file(PURE_CANON_JSONL), "Hadith-Pure-Canon-Authentica.xlsx": sha256_file(PURE_CANON_XLSX),
        "pure_canon_edition_by_work.jsonl": sha256_file(PURE_CANON_EDITIONS), "jamic_sahih_ibadiyya.txt": sha256_file(OPENITI_RABI),
        "musnad_zaydiyya_052.mARkdown": sha256_file(OPENITI_ZAYD), "external_report_crosswalk.jsonl.gz": sha256_file(CROSSWALK),
        "hadith-kg.db": sha256_file(KG_DB),
        "shia-hadith/v2_books/*.json": {p.name: sha256_file(p) for p in sorted(THAQALAYN_DIR.glob("[0-9]*.json"), key=lambda p: int(p.stem))},
    }
    if production and arguments.production_dump:
        inputs["production_dump (not reproducible bytes: production may change)"] = sha256_file(arguments.production_dump)
    manifest = {
        "artifact": "report_structure", "status": "sidecar_unreviewed_not_a_release_input",
        "command": "python -B datasets/hadith-data/reconciled/structure/build_structure_sidecars.py --production-dump <csv>",
        "inputs_sha256": inputs,
        "code_sha256": {"build_structure_sidecars.py": sha256_file(Path(__file__)), "structure_logic.py": sha256_file(HERE / "structure_logic.py")},
        "outputs": {name: {"rows": count, "sha256": sha256_file(HERE / name)} for name, count in outputs.items()},
        "numbering_audit.json": sha256_file(HERE / "numbering_audit.json"),
        "pure_canon_workbook_header": workbook_header,
        "riwayat_db_not_opened": "Riwayat locators come from the existing crosswalk (external_locator), which binds the matched rows",
    }
    with open(HERE / "structure.manifest.json", "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    print(json.dumps({"outputs": outputs}, indent=1))


if __name__ == "__main__":
    main()
