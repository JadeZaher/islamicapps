#!/usr/bin/env python3
"""Build the author-rooted rijal layer: work registry, entries per work, attributed statements, link candidates
(lexicon, Riwayat labels, Imami chain names), coverage, review samples and a manifest.

Every output row is an unreviewed candidate. Method, licences and the load specification: README.md here.
Usage (repo root): python -B datasets/hadith-data/rijal/build_rijal_layer.py
"""

import csv
import gzip
import hashlib
import io
import json
import pathlib
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "diagnostics" / "biography-verification"))
import rijal_extract as rx  # noqa: E402
import rijal_parsing as rp  # noqa: E402
import rijal_sources as rs  # noqa: E402
import verify_lexicon_against_rijal as vl  # noqa: E402

common = rs.common
OUT = HERE / "output"
CHAIN_SNAPSHOT = HERE / "inputs" / "imami_chain_mentions.tsv.gz"
SEED = "rijal-layer-v1"
OPENITI_RELEASE = "OpenITI release 2025.1.9 (Zenodo 10.5281/zenodo.17767721)"
LICENCE = "CC BY-NC-SA 4.0"
SUNNI_WORKS = ("ibn_hajar_taqrib", "mizzi_tahdhib_kamal")
IMAMI_WORKS = ("najashi_rijal", "tusi_rijal", "tusi_fihrist", "kashshi_ikhtiyar")

# Extensions of the existing reader (runtime only; rijal_sources.py is not edited): women ($$) in Tusi and Mizzi,
# Taqrib's four nisba-only entries ($DIC_NIS$), and al-Kashshi, whose sections are '### |' headings.
rs.WORKS["ibn_hajar_taqrib"]["entry_markers"] = ("### $ ", "### $$ ", "### $DIC_NIS$ ")
rs.WORKS["mizzi_tahdhib_kamal"]["entry_markers"] = ("### $ ", "### $$ ")
rs.WORKS["tusi_rijal"]["entry_markers"] = ("### $ ", "### $$ ")
rs.WORKS["kashshi_ikhtiyar"] = {
    "path": rs.EXTERNAL / "openiti-0460ShaykhTusi.IkhtiyarMacrifatRijal"
            / "0460ShaykhTusi.IkhtiyarMacrifatRijal.Shia002932VolsBK1-ara1.mARkdown",
    "tradition": "imami", "critic": "al-Kashshi, selection by al-Tusi", "title": "Ikhtiyar Ma'rifat al-Rijal",
    "openiti_uri": "0460ShaykhTusi.IkhtiyarMacrifatRijal.Shia002932VolsBK1-ara1", "entry_markers": (),
}

AUTHORS = {
    "ibn_hajar": {"name_en": "Ibn Hajar al-Asqalani", "name_ar": "ابن حجر العسقلاني", "tradition": "sunni"},
    "mizzi": {"name_en": "Jamal al-Din al-Mizzi", "name_ar": "جمال الدين المزي", "tradition": "sunni"},
    "najashi": {"name_en": "Ahmad b. Ali al-Najashi", "name_ar": "أحمد بن علي النجاشي", "tradition": "imami"},
    "tusi": {"name_en": "Shaykh al-Ta'ifa Muhammad b. al-Hasan al-Tusi", "name_ar": "الشيخ الطوسي",
             "tradition": "imami"},
    "kashshi": {"name_en": "Abu Amr Muhammad b. Umar al-Kashshi", "name_ar": "أبو عمرو محمد بن عمر الكشي",
                "tradition": "imami"},
}
WORK_META = {
    "ibn_hajar_taqrib": {"author": "ibn_hajar", "title_en": "Taqrib al-Tahdhib", "scheme": "ibn_hajar_taqrib_maratib",
                         "entry_unit": "numbered tarjama (Awwama's numbers)"},
    "mizzi_tahdhib_kamal": {"author": "mizzi", "title_en": "Tahdhib al-Kamal fi Asma' al-Rijal",
                            "scheme": "mizzi_reported_statements",
                            "entry_unit": "numbered tarjama (Bashar Awwad Ma'ruf's numbers)"},
    "najashi_rijal": {"author": "najashi", "title_en": "Rijal al-Najashi (Fihrist asma' musannifi al-Shi'a)",
                      "scheme": "najashi_rijal_terms", "entry_unit": "numbered entry"},
    "tusi_rijal": {"author": "tusi", "title_en": "Rijal al-Tusi", "scheme": "tusi_rijal_terms",
                   "entry_unit": "numbered entry, grouped by the Imam a narrator transmitted from"},
    "tusi_fihrist": {"author": "tusi", "title_en": "al-Fihrist", "scheme": "tusi_fihrist_terms",
                     "entry_unit": "numbered entry ([global] number-in-chapter)"},
    "kashshi_ikhtiyar": {"author": "kashshi", "selector": "tusi",
                         "title_en": "Ikhtiyar Ma'rifat al-Rijal (al-Tusi's selection from al-Kashshi's Rijal)",
                         "scheme": "kashshi_reported_statements",
                         "entry_unit": "section on a person or group, holding numbered reports"},
}


# --- output ------------------------------------------------------------------------------------------------------

def _guard(name: str) -> Path:
    path = (OUT / name).resolve()
    if OUT.resolve() not in path.parents:
        raise RuntimeError(f"{path} escapes {OUT}")
    return path


def write_jsonl_gz(name: str, rows) -> int:
    """Deterministic gzip (mtime 0, no file name) of JSON lines."""
    path = _guard(name)
    count = 0
    with open(path, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0, compresslevel=9) as gz:
        for row in rows:
            gz.write((json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8"))
            count += 1
    return count


def write_json(name: str, value) -> None:
    _guard(name).write_text(json.dumps(value, ensure_ascii=False, indent=1, sort_keys=False) + "\n", encoding="utf-8")


def write_csv(name: str, header: list, rows: list) -> int:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    _guard(name).write_text(buffer.getvalue(), encoding="utf-8-sig")
    return len(rows)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def stable_order(*parts) -> str:
    return hashlib.sha256((SEED + "|" + "|".join(str(p) for p in parts)).encode("utf-8")).hexdigest()


# --- registry ----------------------------------------------------------------------------------------------------

def _yml_fields(path: Path) -> dict:
    fields = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = re.match(r"^(\d+#[A-Z]+#[A-Z#]*):\s*(.*)$", line)
        if match and match.group(2).strip():
            fields[match.group(1).rstrip("#")] = match.group(2).strip()
    return fields


def registry() -> dict:
    works = {}
    for work_key in SUNNI_WORKS + IMAMI_WORKS:
        work = rs.WORKS[work_key]
        meta = WORK_META[work_key]
        header = rs.openiti_header(work["path"])
        yml = Path(str(work["path"]).rsplit(".", 1)[0] + ".yml")
        yml_fields = _yml_fields(yml) if yml.exists() else {}
        died = header.get("011.AuthorDIED")
        author = AUTHORS[meta["author"]]
        editor = header.get("040.EdEDITOR")
        publisher = header.get("043.EdPUBLISHER")
        place = header.get("044.EdPLACE")
        year = header.get("045.EdYEAR")
        edition_bits = ", ".join(bit for bit in (f"ed. {editor}" if editor else None, publisher, place, year) if bit)
        if work_key == "kashshi_ikhtiyar":
            author_line = "al-Kashshi (4th/10th c.), in the selection made by al-Tusi (d. 460)"
            death = {"author_death_year_hijri": None,
                     "author_death_note": "al-Kashshi's death year is not given in the OpenITI header; the header's "
                                          "AuthorDIED 460 is al-Tusi, who made the selection",
                     "selector_author_id": "rijal_author:tusi", "selector_death_year_hijri": int(died) if died else None}
        else:
            author_line = f"{author['name_en']} (d. {died})"
            death = {"author_death_year_hijri": int(died) if died and died.isdigit() else None,
                     "author_death_note": "from the OpenITI header field 011.AuthorDIED"}
        works[work_key] = {
            "work_id": f"rijal_work:{work_key}", "work_key": work_key, "author_id": f"rijal_author:{meta['author']}",
            "author_name_en": author["name_en"], "author_name_ar": author["name_ar"],
            "author_name_ar_openiti": header.get("010.AuthorNAME"), **death,
            "tradition": work["tradition"], "title_en": meta["title_en"], "title_ar": header.get("020.BookTITLE"),
            "verdict_scheme": meta["scheme"], "entry_unit": meta["entry_unit"],
            "openiti_uri": work["openiti_uri"], "openiti_release": OPENITI_RELEASE,
            "edition": {"editor": editor, "publisher": publisher, "place": place, "year": year,
                        "edition_number": header.get("041.EdNUMBER"), "volumes": header.get("022.BookVOLS"),
                        "lib_uri": header.get("030.LibURI"), "read_online": header.get("031.LibREADONLINE"),
                        "misc": header.get("999.MiscINFO"), "version_based_on": yml_fields.get("80#VERS#BASED"),
                        "version_issues": yml_fields.get("90#VERS#ISSUES")},
            "openiti_header": header,
            "source_file": common.relative_path(Path(work["path"])),
            "source_sha256": common.sha256_file(Path(work["path"])),
            "licence": LICENCE,
            "licence_conditions": "attribution; non-commercial use only; derivatives under the same licence",
            "required_attribution": (
                f"{meta['title_en']} by {author_line}"
                + (f", {edition_bits}" if edition_bits else "")
                + f". Arabic text from OpenITI ({work['openiti_uri']}), {OPENITI_RELEASE}, {LICENCE}. "
                  "Entry division and extracted fields by Shura wa Istehsan, unreviewed."),
            "locator_scheme": "entry number as printed in the OpenITI text (Kashshi: section ordinal plus report "
                              "numbers); page vNpM from the OpenITI PageV marker that closes the page",
        }
    return works


# --- entries -----------------------------------------------------------------------------------------------------

def _locator(page_label):
    match = re.match(r"v(\d+)p(\d+)", page_label or "")
    return {"volume": match.group(1), "page": match.group(2)} if match else {"volume": None, "page": None}


def _paragraphs(raw: str, raw_start: int, pages) -> list:
    """Paragraphs of an entry: each '# ' line with everything up to the next one (continuations, page lines)."""
    out = []
    starts = [m.start() for m in re.finditer(r"(?:^|\n)# ", raw)]
    first_line_end = raw.find("\n")
    if not starts or starts[0] > 0:
        starts.insert(0, 0)
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(raw)
        chunk = raw[start:end]
        if index == 0 and chunk.startswith("### "):
            chunk = chunk[chunk.find(" ", 4) + 1:] if first_line_end != -1 else chunk
        text = rs.display_text(chunk.lstrip("\n").removeprefix("# "))
        if text:
            out.append({"text": text, "page": pages.page_at(raw_start + start)})
    return out


def _headword_keys(headword_folded: str) -> list:
    tokens = rp.headword_tokens(headword_folded)
    keys = {rs.name_key(" ".join(tokens))} - {""}
    return sorted(keys)


def _kunya_stripped_variant(key: str) -> str | None:
    """'ابو الفضل سدير بن حكيم' -> 'سدير بن حكيم' (a leading kunya before an ism-nasab chain)."""
    tokens = key.split()
    if tokens and tokens[0] in ("ابو", "ابي", "ابا", "ام"):
        cut = 3 if len(tokens) > 2 and tokens[1] == "عبد" else 2
        rest = tokens[cut:]
        if len(rest) >= 3 and "بن" in rest:
            return " ".join(rest)
    return None


def _statement_rows(statements: list, extra: dict) -> list:
    rows = []
    for statement in statements:
        row = {key: value for key, value in statement.items() if key != "folded_offset"}
        row.update(extra)
        rows.append(row)
    return rows


def build_taqrib(work: dict) -> list:
    records, _ = vl.parse_taqrib()
    raw_entries = list(rs.read_entries("ibn_hajar_taqrib"))
    assert [r["line"] for r in records] == [e["line"] for e in raw_entries]
    entries = []
    for record, raw_entry in zip(records, raw_entries):
        text = record["passage_ar"]
        folded, offsets = rx.fold_with_offsets(text)
        head_len = len(record["headword_before_gloss"])
        statements = []
        verdict = record["verdict"]
        if verdict["verdict_text"]:
            start = folded.find(verdict["verdict_text"], head_len)
            if start >= 0:
                verbatim = rx.verbatim_span(text, offsets, start, start + len(verdict["verdict_text"]))
                first = rx.SUNNI_TERM_IDS.get(verdict["first_term"], verdict["first_term"])
                statements.append({
                    "scheme": work["verdict_scheme"], "term_id": first, "term_verbatim": verbatim,
                    "clause_verbatim": verbatim, "speaker_verbatim": None,
                    "flags": ["companion_status"] if first in rx.COMPANION_TERM_IDS else [],
                    "is_verdict_on_subject": True, "span_rule": "first maratib term to the tabaqa clause"})
        entries.append({
            "entry_number": record["entry_number"], "marker": record["marker"], "line": record["line"],
            "start_page": record["start_page"], "pages": record["pages"],
            "headword_ar": rx.verbatim_span(text, offsets, 0, head_len) if head_len else None,
            "headword_keys": record["keys"], "passage_ar": text, "statements": statements,
            "tabaqa": record["tabaqa"], "death_statements": record["death_statements"],
            "birth_statements": record["birth_statements"], "residence_phrases": record["residence_phrases"],
            "nisba_places": record["nisba_places"],
            "_span": (raw_entry["raw_start"], raw_entry["raw_start"] + len(raw_entry["raw"])),
        })
    return entries


def build_mizzi(work: dict) -> list:
    records, _ = vl.parse_mizzi()
    raw_entries = list(rs.read_entries("mizzi_tahdhib_kamal"))
    assert len(raw_entries) == len(records), "Mizzi reader and parser disagree on entry count"
    document_pages = rs.PageIndex(rs.read_document("mizzi_tahdhib_kamal"))
    entries = []
    for record, entry in zip(records, raw_entries):
        assert record["line"] == entry["line"]
        lists = rx.mizzi_lists(entry["text"])
        number = re.match(r"\s*\(?\s*(\d+)", entry["raw"].split("\n", 1)[0][len(entry["marker"]):])
        statements = []
        for index, paragraph in enumerate(_paragraphs(entry["raw"], entry["raw_start"], document_pages)):
            spans = tuple(rx.mizzi_lists(paragraph["text"])["spans"])
            found = rx.find_terms(paragraph["text"], work["verdict_scheme"], "sunni", skip_spans=spans)
            statements.extend(_statement_rows(found, {"paragraph": index, "page": paragraph["page"]}))
        entries.append({
            "entry_number": record["entry_number"] or (number.group(1) if number else None), "marker": entry["marker"],
            "line": record["line"], "start_page": record["start_page"], "pages": entry["pages"],
            "headword_ar": re.split(r"\.", entry["text"], maxsplit=1)[0].strip(), "heading_clean": record["heading"],
            "headword_keys": record["keys"], "passage_ar": entry["text"], "statements": statements,
            "death_statements": [s for s in record["year_statements"] if s["kind"] == "death"],
            "birth_statements": [s for s in record["year_statements"] if s["kind"] == "birth"],
            "teachers_named": lists["teachers"], "students_named": lists["students"],
            "teachers_named_verbatim": lists["teachers_verbatim"], "students_named_verbatim": lists["students_verbatim"],
            "nisba_places": record["nisba_places"],
            "_span": (entry["raw_start"], entry["raw_start"] + len(entry["raw"])),
        })
    return entries


_LONE_HASH = re.compile(r"(?<!\S)#(?!\S)")
_IMAMI_PREFIX = re.compile(r"^\s*(?:\[\s*(\d+)\s*\]\s*)?(\d+)?\s*-?\s*")


def build_imami_numbered(work_key: str, work: dict) -> list:
    """al-Najashi, al-Tusi's Rijal and Fihrist: '### $ N - name ...' entries."""
    document = rs.read_document(work_key)
    pages = rs.PageIndex(document)
    top_sections = [(m.start(), rs.display_text(m.group(1))) for m in re.finditer(r"^### \|(?!\|)\s*(.*)$", document,
                                                                                    flags=re.M)]
    section_spans = {m.start(): (m.start(), m.end()) for m in re.finditer(r"^### \|(?!\|).*$", document, flags=re.M)}
    sub_sections = [(m.start(), rs.display_text(m.group(1))) for m in re.finditer(r"^### \|\|\s*(.*)$", document,
                                                                                    flags=re.M)]

    def section_at(sections, offset):
        current = None
        for start, title in sections:
            if start < offset:
                current = title
            else:
                break
        return current

    entries = []
    for entry in rs.read_entries(work_key):
        first_line = entry["raw"].split("\n", 1)[0][len(entry["marker"]):]
        prefix = _IMAMI_PREFIX.match(first_line)
        global_number, local_number = prefix.group(1), prefix.group(2)
        number = global_number or local_number or entry["entry_number"]
        body = rs.display_text(entry["raw"][len(entry["marker"]) + 1:] if entry["raw"].startswith(entry["marker"] + " ")
                               else entry["raw"])
        body = _IMAMI_PREFIX.sub("", body, count=1)
        body = " ".join(_LONE_HASH.sub(" ", body).split())
        headword = re.split(r"[،,.:]", body, maxsplit=1)[0].strip()
        head_folded = rx.phrase_fold(headword)
        keys = _headword_keys(head_folded)
        section = section_at(top_sections, entry["raw_start"])
        subject_keys = set(keys)

        def is_subject(folded_name, subject_keys=subject_keys):
            key = rs.name_key(folded_name)
            return bool(key) and any(rx.names_agree(key, subject) for subject in subject_keys)

        people = rx.named_people(body, is_subject=is_subject)
        imams_named = []
        for teacher in people["teachers"]:
            reading = rx.imam_reading(teacher, rijal_clause=True)
            if reading:
                imams_named.append({"name_as_written": teacher, **reading})
        statements = rx.find_terms(body, work["verdict_scheme"], "imami", skip_spans=tuple(rx.route_spans(body)))
        row = {
            "entry_number": number, "number_in_chapter": local_number if global_number else None,
            "marker": entry["marker"], "line": entry["line"], "start_page": entry["start_page"],
            "pages": entry["pages"], "headword_ar": headword, "headword_keys": keys, "passage_ar": body,
            "statements": _statement_rows(statements, {}),
            "death_statements": rp.parse_year_statements(rx.phrase_fold(body), "death", None, False),
            "birth_statements": rp.parse_year_statements(rx.phrase_fold(body), "birth", None, False),
            "teachers_named": [t for t in people["teachers"] if not rx.imam_reading(t, rijal_clause=True)],
            "imams_named": imams_named, "students_named": people["students"],
            "route_students": people["route_students"], "routes": people["routes"],
            "books": rx.books_named(body) if work_key in ("najashi_rijal", "tusi_fihrist") else [],
            "section_heading": section, "subsection_heading": section_at(sub_sections, entry["raw_start"]),
            "_span": (entry["raw_start"], entry["raw_start"] + len(entry["raw"])),
        }
        if work_key == "tusi_rijal":
            row["imam_grouping"] = {"imam": rx.tusi_section_imam(section or ""), "section_heading": section,
                                    "basis": "al-Tusi lists the entry in this chapter"}
            section_start = max((start for start, _ in top_sections if start < entry["raw_start"]), default=None)
            row["_section_span"] = section_spans.get(section_start)
        entries.append(row)
    return entries


def build_kashshi(work: dict) -> tuple:
    document = rs.read_document("kashshi_ikhtiyar")
    pages = rs.PageIndex(document)
    headings = list(re.finditer(r"^### (\|+)\s*(.*)$", document, flags=re.M))
    entries, paratext_sections, ordinal, parent = [], 0, 0, None
    newlines = [m.start() for m in re.finditer("\n", document)]
    import bisect
    for index, heading in enumerate(headings):
        level, title = len(heading.group(1)), heading.group(2).strip()
        start = heading.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(document)
        if title.startswith("PARATEXT"):
            paratext_sections += 1
            continue
        ordinal += 1
        body_raw = document[start:end]
        paragraphs = _paragraphs("\n" + body_raw.lstrip("\n"), start, pages)
        reports = rx.split_kashshi_reports(paragraphs)
        subjects = rx.kashshi_subjects(title)
        keys = set()
        for subject in subjects["subjects"]:
            key = rs.name_key(subject)
            if key:
                keys.add(key)
                variant = _kunya_stripped_variant(key)
                if variant:
                    keys.add(variant)
        statements = []
        for report in reports:
            report["text"] = " ".join(_LONE_HASH.sub(" ", report["text"]).split())
            found = rx.find_terms(report["text"], work["verdict_scheme"], "imami")
            for statement in found:  # a report may speak of anyone; only a clause naming the subject counts
                named = rx.clause_names_subject(statement["clause_verbatim"], sorted(keys))
                statement["flags"].append("clause_names_section_subject" if named else "report_subject_not_established")
                statement["is_verdict_on_subject"] = statement["is_verdict_on_subject"] and named
            statements.extend(_statement_rows(found, {"report_number": report["number"], "page": report["page"]}))
        entry_id_number = f"s{ordinal}"
        numbers = [r["number"] for r in reports if r["number"]]
        row = {
            "entry_number": entry_id_number, "section_level": level, "section_title_ar": rs.display_text(title),
            "parent_entry_number": parent if level == 2 else None,
            "line": bisect.bisect_left(newlines, heading.start()) + 1,
            "start_page": pages.page_at(start), "pages": sorted({r["page"] for r in reports if r["page"]},
                                                                key=lambda p: tuple(int(x) for x in
                                                                                    re.findall(r"\d+", p))),
            "headword_ar": rs.display_text(title) or None, "subject_kind": subjects["kind"],
            "subjects_ar": subjects["subjects"], "headword_keys": sorted(keys),
            "report_numbers": [numbers[0], numbers[-1]] if numbers else None,
            "reports": reports, "passage_ar": rx.citable_text(body_raw),
            "_span": (heading.start(), end),
            "statements": statements,
            "death_statements": [s for r in reports
                                 for s in rp.parse_year_statements(rx.phrase_fold(r["text"]), "death", None, False)
                                 if "subject_may_differ" not in s["flags"]],
        }
        if level == 1:
            parent = entry_id_number
        entries.append(row)
    return entries, paratext_sections


def finalise_entries(work_key: str, work: dict, entries: list) -> list:
    """Stable ids (number, then '~n' for a repeated number), work/author/tradition, locator and passage hash."""
    seen = Counter()
    for entry in entries:
        number = entry.get("entry_number") or f"line{entry['line']}"
        seen[number] += 1
        suffix = "" if seen[number] == 1 else f"~{seen[number]}"
        entry["entry_id"] = f"rijal_entry:{work_key}:{number}{suffix}"
        if entry.get("parent_entry_number"):
            entry["parent_entry_id"] = f"rijal_entry:{work_key}:{entry['parent_entry_number']}"
        entry.update({"work_id": work["work_id"], "author_id": work["author_id"], "tradition": work["tradition"],
                      "locator": _locator(entry.get("start_page")),
                      "passage_sha256": sha256_text(entry["passage_ar"] or ""),
                      "extraction": {"by": "rijal/build_rijal_layer.py", "reviewed": False,
                                     "review_state": "candidate_only"}})
    ordered = []
    for entry in entries:  # id fields first for readability
        head = {key: entry[key] for key in ("entry_id", "work_id", "author_id", "tradition", "entry_number")}
        ordered.append({**head, **{k: v for k, v in entry.items() if k not in head}})
    return ordered


# --- citations (one shape for every record; checked again by validate_citations.py) -----------------------------

SOURCE_REF = "RIJ"
_DOCUMENTS = {}
_FOLD_CACHE = {}


def document(work_key: str) -> str:
    if work_key not in _DOCUMENTS:
        _DOCUMENTS[work_key] = rs.read_document(work_key)
    return _DOCUMENTS[work_key]


def _finish(citation: dict, problems: list) -> dict:
    citation["citation_status"] = "not_yet_cited" if problems else "cited"
    citation["not_yet_cited_reason"] = "; ".join(problems) if problems else None
    return citation


def make_citation(work: dict, entry: dict, verbatim: str | None, page: str | None = None, span=None) -> dict:
    """A complete citation, or one marked not_yet_cited with its reason (never silently incomplete).
    `span` cites another part of the file than the entry (al-Tusi's chapter heading for the Imam grouping)."""
    if span:
        citable = rx.citable_text(document(work["work_key"])[span[0]:span[1]])
        return _citation_from(work, entry, *rx.locate_verbatim(citable, verbatim), span, page)
    start, end = entry["_span"]
    if "_citable" not in entry:
        entry["_citable"] = rx.citable_text(document(work["work_key"])[start:end])
    folded = None
    if verbatim and verbatim not in entry["_citable"]:
        if _FOLD_CACHE.get("entry_id") != entry["entry_id"]:  # one-entry cache: callers cite entry by entry
            _FOLD_CACHE.update(entry_id=entry["entry_id"], value=rx.fold_with_offsets(entry["_citable"]))
        folded = _FOLD_CACHE["value"]
    passage, reason = rx.locate_verbatim(entry["_citable"], verbatim, folded)
    return _citation_from(work, entry, passage, reason, (start, end), page)


def _citation_from(work: dict, entry: dict, passage, reason, span: tuple, page) -> dict:
    start, end = span
    page = page or entry.get("start_page")
    edition = work["edition"]
    citation = {
        "work": {"work_id": work["work_id"], "author": work["author_name_en"], "title": work["title_en"],
                 "title_ar": work["title_ar"], "tradition": work["tradition"]},
        "edition": {"openiti_uri": work["openiti_uri"], "openiti_release": OPENITI_RELEASE,
                    "editor": edition["editor"], "publisher": edition["publisher"], "place": edition["place"],
                    "year": edition["year"], "edition_number": edition["edition_number"]},
        "locator": {"entry_number": entry["entry_number"] or f"unnumbered entry (file line {entry['line']})",
                    "page": page, **_locator(page)},
        "passage_ar": passage,
        "source_span": {"start": start, "end": end,
                        "unit": "Unicode code points of the UTF-8 source file (LF line ends); passage_ar occurs in "
                                "the span once OpenITI markup is removed"},
        "source_ref": SOURCE_REF, "licence": LICENCE, "source_file": work["source_file"],
        "source_sha256": work["source_sha256"],
    }
    return _finish(citation, [reason] if reason else rx.citation_problems(citation))


def header_citation(work: dict) -> dict:
    """A registry record cites the OpenITI header line that names the work."""
    text = document(work["work_key"])
    match = re.search(r"^#META# 020\.BookTITLE.*$", text, flags=re.M)
    citation = {
        "work": {"work_id": work["work_id"], "author": work["author_name_en"], "title": work["title_en"],
                 "title_ar": work["title_ar"], "tradition": work["tradition"]},
        "edition": {"openiti_uri": work["openiti_uri"], "openiti_release": OPENITI_RELEASE},
        "locator": {"entry_number": "header", "page": "header", "volume": None},
        "passage_ar": " ".join(match.group(0).split()) if match else None,
        "source_span": {"start": match.start() if match else None, "end": match.end() if match else None,
                        "unit": "Unicode code points of the UTF-8 source file"},
        "source_ref": SOURCE_REF, "licence": LICENCE, "source_file": work["source_file"],
        "source_sha256": work["source_sha256"]}
    return _finish(citation, rx.citation_problems(citation))


def not_cited(reason: str, **provenance) -> dict:
    """For records whose substance is not read from a rijal text (our chain names)."""
    return {"citation_status": "not_yet_cited", "not_yet_cited_reason": reason, **provenance}


# --- perspective matrix cells ------------------------------------------------------------------------------------
# Rows of the narrator-page matrix are perspectives (a work, or a critic quoted inside al-Mizzi); columns are
# aspects. One row here = one cell value; an absent (perspective, aspect) pair means that source is silent.

ASPECTS = ("verdict_term", "reliability_qualifier", "generation_or_imam", "death_date", "places", "teachers",
           "students", "books", "doctrinal_or_other_note")
QUALIFIER_TERMS = {"jalil", "wajh", "ayn", "shaykh_ashabina", "sahih_al_hadith", "naqi_al_hadith", "mudtarib",
                   "mukhallit", "yuraf_wa_yunkar", "laysa_bi_dhaka", "layyin", "fihi_lin", "hafiz", "imam", "hujja",
                   "mutqin", "thabt", "asnada_anhu", "thiqa_fi_al_hadith"}
DOCTRINAL_TERMS = {"ghali", "waqifi", "fathi", "ammi", "zaydi", "fasid_al_madhhab", "murtafi_al_qawl",
                   "imami_al_madhhab", "min_ashabina"}


def _speaker_perspective(work_key: str, speaker: str | None) -> tuple:
    if not speaker:
        return f"perspective:{work_key}", None
    clean = " ".join(re.sub(r"\(\s*\d+\s*\)|[^\sء-ي]", " ", rx.phrase_fold(speaker)).split())
    return f"perspective:{work_key}:quoted:{clean.replace(' ', '_')}", clean


def perspective_cells(entry: dict, work: dict) -> list:
    work_key = entry["work_id"].split(":", 1)[1]
    quoted_label = work_key == "mizzi_tahdhib_kamal"
    cells = []

    def add(aspect, verbatim, normalised=None, page=None, speaker=None, flags=(), source_field=None, span=None,
            cite=None):
        if not verbatim and normalised is None:
            return
        perspective_id, speaker_clean = _speaker_perspective(work_key, speaker if quoted_label else None)
        cells.append({
            "perspective_id": perspective_id, "tradition": work["tradition"], "work_id": work["work_id"],
            "author_id": work["author_id"],
            "perspective_label": (f"{speaker_clean} (as quoted by al-Mizzi, Tahdhib al-Kamal)" if speaker_clean
                                  else f"{work['author_name_en']}, {work['title_en']}"),
            "quoted_critic_ar": speaker_clean, "entry_id": entry["entry_id"], "aspect": aspect,
            "verbatim_ar": verbatim, "normalised": normalised, "flags": list(flags),
            "locator": {"entry_number": entry["entry_number"], "page": page or entry.get("start_page"),
                        **_locator(page or entry.get("start_page"))},
            "source_field": source_field, "review_state": "candidate_only",
            "citation": make_citation(work, entry, cite or verbatim or entry.get("headword_ar"), page, span)})

    for statement in entry["statements"]:
        term = statement["term_id"]
        aspect = ("generation_or_imam" if term in rx.COMPANION_TERM_IDS else
                  "doctrinal_or_other_note" if term in DOCTRINAL_TERMS else
                  "reliability_qualifier" if term in QUALIFIER_TERMS or not statement["is_verdict_on_subject"]
                  else "verdict_term")
        add(aspect, statement["clause_verbatim"] if aspect != "verdict_term" else statement["term_verbatim"],
            {"term_id": term, "scheme": statement["scheme"], "term_verbatim": statement["term_verbatim"]},
            statement.get("page"), statement.get("speaker_verbatim"), statement["flags"], "statements")
    tabaqa = entry.get("tabaqa") or {}
    if tabaqa.get("tabaqa"):
        add("generation_or_imam", tabaqa["verbatim"], {"tabaqa": tabaqa["tabaqa"], "qualifier": tabaqa["qualifier"]},
            source_field="tabaqa", flags=["verbatim_is_letter_folded"])
    grouping = entry.get("imam_grouping")
    if grouping and grouping.get("imam"):
        add("generation_or_imam", grouping["section_heading"], {"companion_of_imam": grouping["imam"]},
            source_field="imam_grouping", span=entry.get("_section_span"))
    for named in entry.get("imams_named", []):
        add("generation_or_imam", "روى عن " + named["name_as_written"],
            {"transmitted_from_imam": named["imams"], "basis": named["basis"]}, source_field="imams_named",
            flags=["verbatim_is_letter_folded"], cite=named["name_as_written"])
    for death in entry.get("death_statements", []):
        add("death_date", death["clause_verbatim"],
            {"year_min": death.get("year_min"), "year_max": death.get("year_max"), "precision": death["precision"],
             "alternative": death["alternative"], "within_century": death.get("within_century")},
            death.get("page"), death.get("reported_by_verbatim"),
            ["verbatim_is_letter_folded"] + death["flags"], "death_statements")
    for phrase in entry.get("residence_phrases", []):
        add("places", phrase["verbatim"], {"places": phrase["places"]}, source_field="residence_phrases",
            flags=["verbatim_is_letter_folded"])
    if entry.get("nisba_places"):
        add("places", None, {"nisba_places": entry["nisba_places"]}, source_field="nisba_places",
            flags=["nisba_is_attachment_not_proof_of_residence"])
    for field, aspect in (("teachers_named", "teachers"), ("students_named", "students"),
                          ("route_students", "students")):
        printed = entry.get(field + "_verbatim") or []
        for index, name in enumerate(entry.get(field, [])):
            add(aspect, name, None, source_field=field, flags=["verbatim_is_letter_folded"],
                cite=printed[index] if index < len(printed) else None)
    for book in entry.get("books", []):
        add("books", book["verbatim"], {"kind": book["kind"]}, source_field="books")
    for ordinal, cell in enumerate(cells):
        cell["cell_id"] = f"rijal_cell:{entry['entry_id'].split(':', 1)[1]}:{ordinal}"
    return cells


# --- per-perspective life timelines ------------------------------------------------------------------------------

HISTORY_SPEC = HERE.parent / "history" / "claims_spec.py"


def timeline_facts(entry: dict, work: dict) -> list:
    """Dated or placed facts one entry states, each its own cited record under its perspective (never merged)."""
    work_key = work["work_key"]
    if work_key == "kashshi_ikhtiyar":
        return []  # its reports speak of many people; see README "Not done"
    facts = []
    for statement in entry.get("death_statements", []):
        facts.append((rx.death_or_birth_fact(statement, "died"), statement.get("page"),
                      statement.get("reported_by_verbatim")))
    for statement in entry.get("birth_statements", []):
        facts.append((rx.death_or_birth_fact(statement, "born"), statement.get("page"),
                      statement.get("reported_by_verbatim")))
    text = entry["passage_ar"] or ""
    spans = tuple(rx.mizzi_lists(text)["spans"]) if work_key == "mizzi_tahdhib_kamal" else ()
    folded = rx.phrase_fold(text)
    for fact in rx.life_facts(text, spans):
        speaker = None
        if work_key == "mizzi_tahdhib_kamal":
            for match in rx._SPEAKER.finditer(folded, 0, fact["offset"]):
                speaker = match.group(1).strip()
        fact.pop("offset")
        facts.append((fact, None, speaker))
    rows = []
    for ordinal, (fact, page, speaker) in enumerate(facts):
        perspective_id, speaker_clean = _speaker_perspective(work_key, speaker if work_key == "mizzi_tahdhib_kamal"
                                                             else None)
        rows.append({
            "timeline_fact_id": f"rijal_fact:{entry['entry_id'].split(':', 1)[1]}:{ordinal}",
            "entry_id": entry["entry_id"], "perspective_id": perspective_id, "tradition": work["tradition"],
            "perspective_label": (f"{speaker_clean} (as quoted by al-Mizzi, Tahdhib al-Kamal)" if speaker_clean
                                  else f"{work['author_name_en']}, {work['title_en']}"),
            **fact, "verbatim_is_letter_folded": True,
            "subject_note": ("clause flagged subject_may_differ" if "subject_may_differ" in fact.get("date_flags", [])
                             else None),
            "review_state": "candidate_only",
            "citation": make_citation(work, entry, fact["verbatim"], page)})
    return rows


# --- biography availability --------------------------------------------------------------------------------------

LEXICON_FIELDS = {"verdict": ("grade",), "generation": ("grade",), "death_date": ("death_date_hijri", "death_date_place"),
                  "birth_date": ("birth_date_hijri", "birth_date_place"),
                  "places": ("places_of_stay", "birth_place", "death_place"), "teachers": ("teachers",),
                  "students": ("students",), "books": ("books",)}


def lexicon_coverage(row: dict) -> dict:
    data = row["row"]
    covered = {aspect: any((data.get(field) or "").strip() for field in fields)
               for aspect, fields in LEXICON_FIELDS.items()}
    covered["generation"] = row["generation_number"] is not None or row["generation_class"] != "other"
    covered["verdict"] = bool(re.sub(r"\[[^]]*\]", "", data.get("grade") or "").strip())
    return covered


def entry_coverage(entry: dict, cells_by_entry: dict) -> dict:
    aspects = {cell["aspect"] for cell in cells_by_entry.get(entry["entry_id"], [])}
    return {"verdict": "verdict_term" in aspects, "qualifiers": "reliability_qualifier" in aspects,
            "generation": "generation_or_imam" in aspects,
            "death_date": any(d.get("year_min") is not None or d.get("year_max") is not None
                              for d in entry.get("death_statements", [])),
            "death_clause": bool(entry.get("death_statements")), "birth_date": bool(entry.get("birth_statements")),
            "places": "places" in aspects, "teachers": "teachers" in aspects, "students": "students" in aspects,
            "books": "books" in aspects, "doctrinal_note": "doctrinal_or_other_note" in aspects,
            "passage_characters": len(entry["passage_ar"] or "")}


def availability_class(items: list) -> str:
    standing = [i for i in items if i["link_state"] in ("lexicon_row_itself", "unique_machine_link_unreviewed",
                                                       "dataset_record_itself") and i["says_something"]]
    if len(standing) >= 2:
        return "several_sources"
    if len(standing) == 1:
        return "lexicon_only" if standing[0]["source"] == "narrator_lexicon" else "one_source"
    return "nothing"


# --- link candidates ---------------------------------------------------------------------------------------------

class EntryIndex:
    """Name lookups over the entries of a set of works (one tradition)."""

    def __init__(self, entries: list):
        self.entries = {entry["entry_id"]: entry for entry in entries}
        self.by_key = defaultdict(set)
        self.by_prefix = defaultdict(set)
        self.by_token = defaultdict(set)
        self.tokens = {}
        self.teacher_keys, self.student_keys, self.imams = {}, {}, {}
        for entry in entries:
            entry_id = entry["entry_id"]
            tokens = set()
            for key in entry["headword_keys"]:
                self.by_key[key].add(entry_id)
                key_tokens = key.split()
                tokens.update(key_tokens)
                for token in set(rx.case_fold_tokens(key_tokens)):
                    self.by_token[token].add(entry_id)
                chain = rp.name_chain(key_tokens)[0].split()
                for cut in range(3, len(chain) + 1):
                    if cut == len(chain) or chain[cut] in ("بن", "بنت"):
                        self.by_prefix[" ".join(chain[:cut])].add(entry_id)
            self.tokens[entry_id] = tokens
            # only person-like names corroborate ('وغيره', 'أبيه', a bare ism or kunya never do)
            self.teacher_keys[entry_id] = {k: n for n, k in ((n, rs.name_key(n)) for n in entry.get("teachers_named", []))
                                           if k and rx.name_shape(k) in ("full", "ibn")}
            students = list(entry.get("students_named", [])) + list(entry.get("route_students", []))
            self.student_keys[entry_id] = {k: n for n, k in ((n, rs.name_key(n)) for n in students)
                                           if k and rx.name_shape(k) in ("full", "ibn")}
            imams = set()
            grouping = entry.get("imam_grouping")
            if grouping and grouping.get("imam") and grouping["imam"] != "none":
                imams.add(("tusi_section", grouping["imam"]))
            for named in entry.get("imams_named", []):
                for imam in named["imams"]:
                    imams.add(("entry_text", imam))
            self.imams[entry_id] = imams

    def name_candidates(self, key: str, shape: str) -> tuple:
        """(basis per entry id, pool size) for a name key by name alone."""
        short = shape in ("single", "kunya", "ibn")
        found = {}
        for entry_id in self.by_key.get(key, ()):
            found[entry_id] = "short_name_in_headword" if short else "exact_full_name"
        tokens = key.split()
        if short:
            folded = [t for t in rx.case_fold_tokens(tokens) if t not in ("بن", "بنت")]
            pool = set.intersection(*(self.by_token.get(t, set()) for t in folded)) if folded else set()
        else:
            chain = rp.name_chain(tokens)[0]
            pool = set(self.by_prefix.get(chain, set())) if "بن" in chain.split() else set()
        for entry_id in sorted(pool - set(found)):
            basis = rx.name_match_basis(key, self.entries[entry_id]["headword_keys"], self.tokens[entry_id], shape)
            if basis:
                found[entry_id] = basis
        return found, len(pool)


class ChainContext:
    """What our (or Riwayat's) chains say around one name: Imams narrated from, chain-head Imams, neighbours."""

    def __init__(self):
        self.occurrences = 0
        self.imams_from = Counter()      # tuple(imams) of the next mention when it is an Imam reading
        self.head_imams = Counter()      # tuple(imams) at the chain end, name not adjacent
        self.teachers = Counter()        # keys of the next (older) mention
        self.students = Counter()        # keys of the previous (younger) mention
        self.surfaces = Counter()


def build_contexts(chains: dict, key_of) -> dict:
    """chains: chain id -> ordered list of (surface, extra). Position grows toward the Imam (last mention)."""
    contexts = defaultdict(ChainContext)
    for chain_id in sorted(chains):
        mentions = chains[chain_id]
        keys = [key_of(surface) for surface, _ in mentions]
        readings = [rx.imam_reading(surface, at_chain_end=(index == len(mentions) - 1))
                    for index, (surface, _) in enumerate(mentions)]
        head = readings[-1] if mentions else None
        for index, (surface, _) in enumerate(mentions):
            key = keys[index]
            if not key or readings[index]:
                continue
            context = contexts[key]
            context.occurrences += 1
            context.surfaces[surface] += 1
            if index + 1 < len(mentions):
                if readings[index + 1]:
                    context.imams_from[tuple(readings[index + 1]["imams"])] += 1
                elif keys[index + 1]:
                    context.teachers[keys[index + 1]] += 1
                if head and index + 1 != len(mentions) - 1:
                    context.head_imams[tuple(head["imams"])] += 1
            if index > 0 and keys[index - 1] and not readings[index - 1]:
                context.students[keys[index - 1]] += 1
    return contexts


def corroboration(index: EntryIndex, entry_id: str, context: ChainContext) -> list:
    evidence = []
    for source, imam in sorted(index.imams[entry_id]):
        direct = {reading: count for reading, count in context.imams_from.items() if imam in reading}
        label = "tusi_section_imam" if source == "tusi_section" else "entry_imam"
        if direct:
            evidence.append({"evidence": f"{label}_is_imam_narrated_from", "imam": imam,
                             "chain_readings": {"|".join(k): v for k, v in sorted(direct.items())},
                             "shared_reading": any(len(k) > 1 for k in direct)})
            continue
        heads = {reading: count for reading, count in context.head_imams.items() if imam in reading}
        if heads:
            evidence.append({"evidence": f"{label}_is_chain_head_imam", "imam": imam,
                             "chain_readings": {"|".join(k): v for k, v in sorted(heads.items())},
                             "shared_reading": any(len(k) > 1 for k in heads)})
    for kind, entry_names, chain_names in (("entry_teacher_is_chain_teacher", index.teacher_keys[entry_id],
                                            context.teachers),
                                           ("entry_student_is_chain_student", index.student_keys[entry_id],
                                            context.students)):
        matches = []
        for entry_key, written in sorted(entry_names.items()):
            for chain_key, count in sorted(chain_names.items()):
                how = rx.names_agree(entry_key, chain_key)
                if how:
                    matches.append({"entry_name": written, "chain_name_key": chain_key, "chain_count": count,
                                    "how": how})
        if matches:
            evidence.append({"evidence": kind, "matches": matches[:10], "match_count": len(matches)})
    return evidence


def link_names(names: dict, index: EntryIndex, contexts_for, link_set: str) -> tuple:
    """names: name id -> {'keys': {key: [forms]}, ...}. Returns (candidate rows, per-name status)."""
    rows, status = [], {}
    for name_id in sorted(names):
        info = names[name_id]
        candidates = {}
        reasons = Counter()
        for key in sorted(info["keys"]):
            shape = rx.name_shape(key)
            if shape in ("relational_name", "collective_or_anonymous_name", "no_arabic_name"):
                reasons[shape] += 1
                continue
            reading = rx.imam_reading(key, at_chain_end=True)
            if reading and (reading["basis"] == "explicit_name" or shape == "kunya"):
                reasons["imam_name"] += 1
                continue
            short = shape in ("single", "kunya", "ibn")
            found, pool = index.name_candidates(key, shape)
            if short and pool > 300:
                reasons["short_name_too_many_homonyms"] += 1
                continue
            context = contexts_for(name_id, key)
            for entry_id, basis in found.items():
                extra = corroboration(index, entry_id, context) if context else []
                if short and not extra:
                    reasons["short_name_without_corroboration"] += 1
                    continue
                evidence = [{"evidence": basis, "name_key": key, "name_shape": shape, "forms": info["keys"][key][:5],
                             "entry_headword_keys": index.entries[entry_id]["headword_keys"]}] + extra
                previous = candidates.get(entry_id)
                if previous is None or sum(rx.EVIDENCE_WEIGHT[e["evidence"]] for e in evidence) > \
                        sum(rx.EVIDENCE_WEIGHT[e["evidence"]] for e in previous["evidence"]):
                    entry = index.entries[entry_id]
                    candidates[entry_id] = {"entry_id": entry_id, "work_id": entry["work_id"],
                                            "author_id": entry["author_id"], "evidence": evidence,
                                            "name_basis": basis, "short_name": short}
        ranked = rx.rank_candidates(list(candidates.values()))
        count = len(ranked)
        status[name_id] = {"candidates": count, "reasons": dict(reasons),
                           "by_work": dict(Counter(c["work_id"] for c in ranked))}
        for candidate in ranked:
            rows.append({
                "link_id": f"rijal_link:{link_set}:{name_id}:{candidate['entry_id'].split(':', 1)[1]}",
                "link_set": link_set, "name_id": name_id, "name_as_written": info["display"],
                "occurrences": info.get("occurrences"), "entry_id": candidate["entry_id"],
                "work_id": candidate["work_id"], "author_id": candidate["author_id"],
                "name_basis": candidate["name_basis"], "short_name": candidate["short_name"],
                "evidence": candidate["evidence"], "evidence_fired": sorted({e["evidence"] for e in
                                                                             candidate["evidence"]}),
                "evidence_score": candidate["evidence_score"], "rank": candidate["rank"],
                "candidate_count": count, "selected": False, "review_state": "candidate_only",
                "basis_note": "machine candidate; several candidates are never resolved to one",
            })
    return rows, status


def lexicon_links(lexicon: list, works_entries: dict) -> tuple:
    """Lexicon (Sunni-centred) -> Taqrib and Tahdhib al-Kamal, every candidate kept. Tier A (full key) and tier B
    (exact nasab chain + other tokens) as in biography-verification; its unique links are checked for parity."""
    rows, status, parity = [], {}, Counter()
    for work_key in SUNNI_WORKS:
        entries = works_entries[work_key]
        records = [{"keys": e["headword_keys"]} for e in entries]
        existing = vl.link(lexicon, records)
        key_index, chain_index, tokens = defaultdict(set), defaultdict(set), []
        for position, entry in enumerate(entries):
            entry_tokens = set()
            for key in entry["headword_keys"]:
                key_index[key].add(position)
                chain_index[rp.name_chain(key.split())[0]].add(position)
                entry_tokens.update(key.split())
            tokens.append(entry_tokens)
        key_count = Counter(row["key"] for row in lexicon if not row["placeholder_reason"])
        for row in lexicon:
            sid = row["scholar_indx"]
            state = status.setdefault(sid, {"by_work": {}, "placeholder_reason": row["placeholder_reason"]})
            if row["placeholder_reason"]:
                continue
            hits = {p: "A_full_name_key" for p in key_index.get(row["key"], ())}
            if not hits:
                chain, rest = rp.name_chain(row["key"].split())
                if "بن" in chain.split() or "بنت" in chain.split():
                    hits = {p: "B_nasab_chain_plus_tokens" for p in chain_index.get(chain, ()) if set(rest) <= tokens[p]}
            result = existing[sid]
            if result["status"] == "unique":
                parity["unique_agrees" if list(hits) == [result["record"]] else "unique_differs"] += 1
            state["by_work"][work_key] = len(hits)
            ranked = sorted(hits, key=lambda p: entries[p]["entry_id"])
            for position in ranked:
                entry = entries[position]
                evidence = [{"evidence": hits[position], "lexicon_key": row["key"],
                             "entry_headword_keys": entry["headword_keys"],
                             "entries_in_work_with_this_name": len(hits),
                             "lexicon_rows_with_this_key": key_count[row["key"]]}]
                rows.append({
                    "link_id": f"rijal_link:lexicon:{sid}:{entry['entry_id'].split(':', 1)[1]}",
                    "link_set": "lexicon", "name_id": f"narrator:rawi:{sid}", "scholar_indx": sid,
                    "name_as_written": row["arabic_name"], "entry_id": entry["entry_id"],
                    "work_id": entry["work_id"], "author_id": entry["author_id"], "name_basis": hits[position],
                    "evidence": evidence, "evidence_fired": [hits[position]],
                    "candidate_count_in_work": len(hits),
                    "biography_verification_status": result["status"],
                    "selected": False, "review_state": "candidate_only",
                    "basis_note": ("unique on both sides (biography-verification's conservative link)"
                                   if result["status"] == "unique" else
                                   "candidate kept; biography-verification left it unlinked "
                                   f"({result['status']}); nothing picked"),
                })
    for state in status.values():
        state["candidates"] = sum(state["by_work"].values())
    return rows, status, dict(parity)


# --- inputs: Riwayat, chain snapshot -----------------------------------------------------------------------------

def load_riwayat():
    uri = pathlib.Path(rs.RIWAYAT).as_uri() + "?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    q = lambda sql, *a: connection.execute(sql, a).fetchall()  # noqa: E731
    mentions = q("""select m.hadith_id, m.chain_no, m.pos, m.surface, m.narrator_id from chain_mention m
                    join hadith h on h.id = m.hadith_id where h.tradition = 'shia'
                    order by m.hadith_id, m.chain_no, m.pos""")
    info = {row[0]: row[1:] for row in q("select id, std_name, tradition from narrator")}
    forms = defaultdict(set)
    asserted = {m[4] for m in mentions if m[4]}
    for narrator_id, form in q("select narrator_id, form from narrator_name where type in ('full','popular')"):
        if narrator_id in asserted:
            forms[narrator_id].add(form)
    connection.close()
    chains, mention_count = defaultdict(list), Counter()
    for hadith_id, chain_no, pos, surface, narrator_id in mentions:
        chains[f"{hadith_id}:{chain_no}"].append((surface or "", narrator_id))
        if narrator_id:
            mention_count[narrator_id] += 1
    names = {}
    for narrator_id in sorted(asserted):
        std_name, tradition = info.get(narrator_id, (None, None))
        keys = defaultdict(list)
        for form in sorted(forms.get(narrator_id, set()) | ({std_name} if std_name else set())):
            key = rs.name_key(form)
            if key:
                keys[key].append(form)
        names[narrator_id] = {"keys": dict(keys), "display": std_name, "occurrences": mention_count[narrator_id],
                              "riwayat_tradition_label": tradition}
    return names, chains


def load_chain_snapshot():
    chains = defaultdict(list)
    with gzip.open(CHAIN_SNAPSHOT, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            chains[row["chain_id"]].append((int(row["position"]), row["surface_ar"], row["surface_normalized"]))
    ordered = {}
    for chain_id, mentions in chains.items():
        mentions.sort()
        ordered[chain_id] = [(surface, normalized) for _, surface, normalized in mentions]
    return ordered


# --- samples -----------------------------------------------------------------------------------------------------

def _evidence_text(row: dict) -> str:
    parts = []
    for item in row["evidence"]:
        label = item["evidence"]
        if "imam" in item:
            label += f"({item['imam']})"
        if "matches" in item:
            label += "(" + "; ".join(m["entry_name"] for m in item["matches"][:3]) + ")"
        parts.append(label)
    return " + ".join(parts)


def draw_samples(link_rows: list, entries_by_id: dict, per_set: int, tag: str) -> list:
    """Stratified per link set: half from names with one candidate, half from names with several."""
    groups = defaultdict(list)
    for row in link_rows:
        count = row.get("candidate_count", row.get("candidate_count_in_work"))
        groups[(row["link_set"], "one" if count == 1 else "several")].append(row)
    picked = []
    for link_set in ("lexicon", "riwayat", "imami_chain_name"):
        for stratum in ("one", "several"):
            pool = sorted(groups[(link_set, stratum)], key=lambda r: stable_order(tag, r["link_id"]))
            picked.extend(pool[:per_set // 2])
    out = []
    for number, row in enumerate(picked, 1):
        entry = entries_by_id[row["entry_id"]]
        out.append([f"{tag}-{number:03d}", row["link_set"], row["link_id"], row["name_as_written"],
                    row.get("candidate_count", row.get("candidate_count_in_work")), row.get("rank", ""),
                    row["entry_id"], entry.get("start_page") or "", entry.get("headword_ar") or "",
                    _evidence_text(row), (entry["passage_ar"] or "")[:700]])
    return out


SAMPLE_HEADER = ["sample_id", "link_set", "link_id", "name_as_written", "candidate_count", "rank", "entry_id",
                 "page", "entry_headword_ar", "evidence_fired", "entry_passage_ar_first_700"]


# --- main --------------------------------------------------------------------------------------------------------

def main() -> None:
    OUT.mkdir(exist_ok=True)
    works = registry()
    entries_by_work, extra_counts = {}, {}
    entries_by_work["ibn_hajar_taqrib"] = build_taqrib(works["ibn_hajar_taqrib"])
    entries_by_work["mizzi_tahdhib_kamal"] = build_mizzi(works["mizzi_tahdhib_kamal"])
    for work_key in ("najashi_rijal", "tusi_rijal", "tusi_fihrist"):
        entries_by_work[work_key] = build_imami_numbered(work_key, works[work_key])
    entries_by_work["kashshi_ikhtiyar"], extra_counts["kashshi_paratext_sections_skipped"] = \
        build_kashshi(works["kashshi_ikhtiyar"])
    for work_key, entries in entries_by_work.items():
        entries_by_work[work_key] = finalise_entries(work_key, works[work_key], entries)
    entries_by_id = {e["entry_id"]: e for entries in entries_by_work.values() for e in entries}
    for work_key, entries in entries_by_work.items():
        for entry in entries:
            entry["citation"] = make_citation(works[work_key], entry, entry["passage_ar"])

    outputs = {}
    for work in works.values():
        work["citation"] = header_citation(work)
    write_json("rijal_works.json", {"authors": {f"rijal_author:{k}": v for k, v in AUTHORS.items()},
                                    "works": list(works.values())})
    outputs["rijal_works.json"] = len(works)

    statement_rows = []
    for work_key, entries in entries_by_work.items():
        work = works[work_key]
        for entry in entries:
            for ordinal, statement in enumerate(entry["statements"]):
                statement_rows.append({
                    "statement_id": f"rijal_statement:{entry['entry_id'].split(':', 1)[1]}:{ordinal}",
                    "entry_id": entry["entry_id"], "work_id": work["work_id"], "author_id": work["author_id"],
                    "tradition": work["tradition"], "ordinal": ordinal, **statement,
                    "attributed_to": (work["author_name_en"] if not statement.get("speaker_verbatim")
                                      else f"{statement['speaker_verbatim']} (as reported in {work['title_en']})"),
                    "review_state": "candidate_only",
                    "citation": make_citation(work, entry, statement["clause_verbatim"] or statement["term_verbatim"],
                                              statement.get("page"))})
    outputs["rijal_entry_statements.jsonl.gz"] = write_jsonl_gz("rijal_entry_statements.jsonl.gz", statement_rows)
    cell_rows = [cell for work_key, entries in entries_by_work.items() for entry in entries
                 for cell in perspective_cells(entry, works[work_key])]
    outputs["rijal_perspective_cells.jsonl.gz"] = write_jsonl_gz("rijal_perspective_cells.jsonl.gz", cell_rows)
    timeline_rows = [fact for work_key, entries in entries_by_work.items() for entry in entries
                     for fact in timeline_facts(entry, works[work_key])]
    outputs["rijal_timeline_facts.jsonl.gz"] = write_jsonl_gz("rijal_timeline_facts.jsonl.gz", timeline_rows)
    write_json("gazetteer_proposed.json", {
        "status": "proposed_unreviewed",
        "rule": "a written place maps to an id only when one of these letter-folded forms (optionally with ب/و/ل) "
                "matches it exactly; anything else stays as written and unmapped",
        "not_mapped_on_purpose": {"عمان": "Oman and Amman are written alike unvocalised",
                                  "الهمداني": "a Yemeni tribe, not Hamadhan", "البخاري/النسائي": "compilers' nisbas"},
        "places": rx.gazetteer()})
    outputs["gazetteer_proposed.json"] = len(rx.gazetteer())

    # (a) lexicon
    lexicon = rs.load_lexicon()
    lexicon_rows, lexicon_status, parity = lexicon_links(lexicon, entries_by_work)

    # (b) Imami: Riwayat labels and our chain names, against Imami works only
    imami_index = EntryIndex([e for w in IMAMI_WORKS for e in entries_by_work[w]])
    riwayat_names, riwayat_chains = load_riwayat()
    riwayat_contexts = build_contexts({k: [(s, None) for s, _ in v] for k, v in riwayat_chains.items()}, rs.name_key)
    riwayat_rows, riwayat_status = link_names(riwayat_names, imami_index,
                                              lambda name_id, key: riwayat_contexts.get(key), "riwayat")

    chains = load_chain_snapshot()
    chain_contexts = build_contexts(chains, rs.name_key)
    surface_keys = Counter()
    distinct_normalized = set()
    key_surfaces = defaultdict(Counter)
    for mentions in chains.values():
        for surface, normalized in mentions:
            distinct_normalized.add(normalized)
            key = rs.name_key(surface)
            surface_keys[key] += 1
            key_surfaces[key][surface] += 1
    chain_names = {}
    for key, count in surface_keys.items():
        if not key:
            continue
        name_id = "k" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
        chain_names[name_id] = {"keys": {key: [s for s, _ in key_surfaces[key].most_common(5)]},
                                "display": key_surfaces[key].most_common(1)[0][0], "occurrences": count,
                                "name_key": key}
    chain_rows, chain_status = link_names(chain_names, imami_index,
                                          lambda name_id, key: chain_contexts.get(key), "imami_chain_name")
    for row in chain_rows:
        row["name_key"] = chain_names[row["name_id"]]["name_key"]
    for row in lexicon_rows + riwayat_rows + chain_rows:  # the rijal side of a link: the headword the name matched
        entry = entries_by_id[row["entry_id"]]
        row["citation"] = make_citation(works[entry["work_id"].split(":", 1)[1]], entry, entry["headword_ar"])
    outputs["rijal_links_lexicon.jsonl.gz"] = write_jsonl_gz("rijal_links_lexicon.jsonl.gz", lexicon_rows)
    outputs["rijal_links_riwayat.jsonl.gz"] = write_jsonl_gz("rijal_links_riwayat.jsonl.gz", riwayat_rows)
    outputs["rijal_links_imami_chain_names.jsonl.gz"] = write_jsonl_gz("rijal_links_imami_chain_names.jsonl.gz",
                                                                       chain_rows)
    snapshot_sha = common.sha256_file(CHAIN_SNAPSHOT)
    name_rows = [{"name_id": name_id, "name_key": info["name_key"], "surfaces": info["keys"][info["name_key"]],
                  "occurrences": info["occurrences"], **chain_status[name_id],
                  "citation": not_cited("a name as written in our Imami chains, not a passage of a rijal text; each "
                                        "mention is cited by its chain_mentions row",
                                        source_file=common.relative_path(CHAIN_SNAPSHOT), source_sha256=snapshot_sha)}
                 for name_id, info in sorted(chain_names.items())]
    outputs["imami_chain_names.jsonl.gz"] = write_jsonl_gz("imami_chain_names.jsonl.gz", name_rows)

    # narrator_assessments projection: lexicon narrators with exactly one candidate entry in a work
    assessment_rows = []
    one_per_work = Counter((r["scholar_indx"], r["work_id"]) for r in lexicon_rows)
    statements_by_entry = defaultdict(list)
    for statement in statement_rows:
        statements_by_entry[statement["entry_id"]].append(statement)
    for row in lexicon_rows:
        if one_per_work[(row["scholar_indx"], row["work_id"])] != 1 or row["work_id"] != "rijal_work:ibn_hajar_taqrib":
            continue
        for statement in statements_by_entry[row["entry_id"]]:
            if not statement["is_verdict_on_subject"]:
                continue
            assessment_rows.append({
                "id": f"narrator_assessment:rijal:{row['scholar_indx']}:{statement['statement_id'].split(':', 1)[1]}",
                "narrator_id": row["name_id"], "tradition_id": "tradition:sunni", "kind": "critic_ruling",
                "verdict": "not_applicable", "verdict_term_id": statement["term_id"],
                "critic": "Ibn Hajar al-Asqalani", "quote_ar": statement["term_verbatim"],
                "provenance": f"{statement['statement_id']} via {row['link_id']}",
                "citation_entry_id": row["entry_id"], "status": "proposed",
                "link_status": row["biography_verification_status"],
                "note": "verdict enum holds no scheme-specific grade; the term and quote carry the author's words",
                "citation": statement["citation"]})
    outputs["narrator_assessment_candidates.jsonl.gz"] = write_jsonl_gz("narrator_assessment_candidates.jsonl.gz",
                                                                        assessment_rows)

    # narrator-event link candidates: an entry naming an event, carried to every narrator the entry is linked to
    links_by_entry = defaultdict(list)
    for row in lexicon_rows + riwayat_rows + chain_rows:
        links_by_entry[row["entry_id"]].append(row)
    history_sha = common.sha256_file(HISTORY_SPEC) if HISTORY_SPEC.exists() else None
    event_rows = []
    for fact in timeline_rows:
        if fact["kind"] not in ("present_at_event", "regnal_dating"):
            continue
        for link in links_by_entry.get(fact["entry_id"], []):
            state = ("unique_machine_link_unreviewed" if link.get("biography_verification_status") == "unique"
                     or (link.get("candidate_count") == 1 and not link.get("short_name"))
                     else "possible_entry_link_not_established")
            event_rows.append({
                "candidate_id": f"rijal_event_candidate:{fact['timeline_fact_id'].split(':', 1)[1]}:{link['name_id']}",
                "narrator_ref": link["name_id"], "link_id": link["link_id"], "link_state": state,
                "entry_id": fact["entry_id"], "perspective_id": fact["perspective_id"], "kind": fact["kind"],
                "event_as_written": fact.get("event_as_written") or fact.get("ruler_or_period_as_written"),
                "history_event_ref": fact.get("history_event_ref"),
                "history_event_ref_source": ({"file": common.relative_path(HISTORY_SPEC), "sha256": history_sha,
                                              "note": "history lane event title/key; ids not yet published"}
                                             if fact.get("history_event_ref") else None),
                "basis": "the entry's own words name the event; involvement is never inferred from dates",
                "review_state": "candidate_only", "citation": fact["citation"]})
    outputs["narrator_event_candidates.jsonl.gz"] = write_jsonl_gz("narrator_event_candidates.jsonl.gz", event_rows)

    # biography availability, one record per narrator we hold
    cells_by_entry = defaultdict(list)
    for cell in cell_rows:
        cells_by_entry[cell["entry_id"]].append(cell)
    coverage_by_entry = {eid: entry_coverage(e, cells_by_entry) for eid, e in entries_by_id.items()}
    kg_links, riwayat_lexicon_links = defaultdict(set), defaultdict(set)
    with gzip.open(HERE.parent / "diagnostics" / "biography-verification" / "lexicon_rijal_links.jsonl.gz", "rt",
                   encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["source"] == "hadith_kg" and row["status"] == "unique":
                kg_links[row["scholar_indx"]].add(row["entry_number"])
    with gzip.open(HERE.parent / "reconciled" / "external_narrator_lexicon_links.jsonl.gz", "rt",
                   encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            namespace, _, external = row["external_narrator_id"].partition(":rawi:") if "hadith-kg" in \
                row["external_narrator_id"] else (None, None, None)
            if external:
                kg_links[row["scholar_indx"]].add(external)
            elif row["external_narrator_id"].startswith("riwayat:"):
                riwayat_lexicon_links[row["scholar_indx"]].add(row["external_narrator_id"].split(":", 1)[1])
    kg = sqlite3.connect(pathlib.Path(rs.HADITH_KG).as_uri() + "?mode=ro&immutable=1", uri=True)
    kg_rows = {str(r[0]): r[1:] for r in kg.execute(
        "select id, death_year_raw, birth_year_raw, iqama, death_place, tabaka, rank from rawis")}
    kg.close()
    rw = sqlite3.connect(pathlib.Path(rs.RIWAYAT).as_uri() + "?mode=ro&immutable=1", uri=True)
    rw_rows = {r[0]: r[1:] for r in rw.execute(
        "select id, death_year, birth_year, tabaqa, city, death_city, madhhab from narrator")}
    rw.close()

    def kg_item(rawi_id):
        death, birth, iqama, death_place, tabaka, rank = kg_rows.get(rawi_id, (None,) * 6)
        covers = {"verdict_dataset_wording": bool(rank), "generation": bool(tabaka), "death_date": bool(death),
                  "birth_date": bool(birth), "places": bool(iqama or death_place)}
        return {"source": "hadith_kg", "record_id": f"hadith-kg:rawi:{rawi_id}",
                "link_state": "unique_machine_link_unreviewed", "covers": covers, "says_something": any(covers.values()),
                "citation_status": "not_yet_cited",
                "not_yet_cited_reason": "derived database (CC BY 4.0); rows carry no per-row source citation"}

    def riwayat_item(narrator_id, state):
        death, birth, tabaqa, city, death_city, madhhab = rw_rows.get(narrator_id, (None,) * 6)
        covers = {"death_date": death is not None, "birth_date": birth is not None, "generation": tabaqa is not None,
                  "places": bool(city or death_city), "doctrinal_note": bool(madhhab)}
        return {"source": "riwayat", "record_id": f"riwayat:{narrator_id}", "link_state": state, "covers": covers,
                "says_something": any(covers.values()), "citation_status": "not_yet_cited",
                "not_yet_cited_reason": "Riwayat corpus fields (CC0) carry no per-row source citation"}

    def rijal_item(link, state):
        entry = entries_by_id[link["entry_id"]]
        covers = coverage_by_entry[link["entry_id"]]
        return {"source": entry["work_id"], "record_id": entry["entry_id"], "link_id": link["link_id"],
                "link_state": state, "covers": covers,
                "says_something": any(v for k, v in covers.items() if k != "passage_characters"),
                "citation_status": entry["citation"]["citation_status"], "locator": entry["citation"]["locator"]}

    lexicon_links_by_sid = defaultdict(list)
    for row in lexicon_rows:
        lexicon_links_by_sid[row["scholar_indx"]].append(row)
    availability = []
    index_citation = not_cited("index record: availability is derived from the listed sources, each of which "
                               "carries its own citation status")
    for row in lexicon:
        sid = row["scholar_indx"]
        covers = lexicon_coverage(row)
        items = [{"source": "narrator_lexicon", "record_id": f"narrator:rawi:{sid}", "link_state": "lexicon_row_itself",
                  "covers": covers, "says_something": any(covers.values()), "citation_status": "not_yet_cited",
                  "not_yet_cited_reason": "narrator lexicon, not yet cited to a source text",
                  "locator": {"csv_line": row["csv_line"]}}]
        for link in lexicon_links_by_sid.get(sid, []):
            items.append(rijal_item(link, "unique_machine_link_unreviewed"
                                    if link["biography_verification_status"] == "unique"
                                    else "possible_entry_link_not_established"))
        items += [kg_item(rawi) for rawi in sorted(kg_links.get(sid, ()))]
        items += [riwayat_item(nid, "unique_machine_link_unreviewed") for nid in sorted(riwayat_lexicon_links.get(sid, ()))]
        availability.append({"narrator_ref": f"narrator:rawi:{sid}", "name_ar": row["arabic_name"],
                             "narrator_set": "lexicon", "tradition": "sunni_lexicon",
                             "generation": row["generation_class"], "placeholder_reason": row["placeholder_reason"],
                             "availability_class": availability_class(items),
                             "possible_entries": sum(i["link_state"] == "possible_entry_link_not_established"
                                                     for i in items), "sources": items, "citation": index_citation})
    riwayat_links_by_name, chain_links_by_name = defaultdict(list), defaultdict(list)
    for row in riwayat_rows:
        riwayat_links_by_name[row["name_id"]].append(row)
    for row in chain_rows:
        chain_links_by_name[row["name_id"]].append(row)

    def candidate_state(link):
        return ("unique_machine_link_unreviewed" if link["candidate_count"] == 1 and not link["short_name"]
                else "possible_entry_link_not_established")

    for name_id, info in sorted(riwayat_names.items()):
        items = [riwayat_item(name_id, "dataset_record_itself")]
        items += [rijal_item(link, candidate_state(link)) for link in riwayat_links_by_name.get(name_id, [])]
        availability.append({"narrator_ref": f"riwayat:{name_id}", "name_ar": info["display"],
                             "narrator_set": "riwayat_label", "tradition": "imami",
                             "generation": (f"riwayat_tabaqa:{rw_rows[name_id][2]}" if name_id in rw_rows
                                            and rw_rows[name_id][2] is not None else "unknown"),
                             "availability_class": availability_class(items),
                             "possible_entries": sum(i["link_state"] == "possible_entry_link_not_established"
                                                     for i in items), "sources": items, "citation": index_citation})
    for name_id, info in sorted(chain_names.items()):
        items = [rijal_item(link, candidate_state(link)) for link in chain_links_by_name.get(name_id, [])]
        availability.append({"narrator_ref": f"imami_chain_name:{name_id}", "name_ar": info["display"],
                             "name_key": info["name_key"], "narrator_set": "imami_chain_name", "tradition": "imami",
                             "generation": "unknown", "occurrences": info["occurrences"],
                             "availability_class": availability_class(items),
                             "possible_entries": sum(i["link_state"] == "possible_entry_link_not_established"
                                                     for i in items), "sources": items, "citation": index_citation})
    outputs["biography_availability.jsonl.gz"] = write_jsonl_gz("biography_availability.jsonl.gz", availability)

    for work_key, entries in entries_by_work.items():
        name = f"rijal_entries_{work_key}.jsonl.gz"
        outputs[name] = write_jsonl_gz(name, ({k: v for k, v in e.items() if not k.startswith("_")} for e in entries))

    citation_status = {}
    for label, rows in (("rijal_works.json", list(works.values())),
                        *((f"rijal_entries_{w}.jsonl.gz", e) for w, e in entries_by_work.items()),
                        ("rijal_entry_statements.jsonl.gz", statement_rows),
                        ("rijal_perspective_cells.jsonl.gz", cell_rows),
                        ("rijal_links_lexicon.jsonl.gz", lexicon_rows), ("rijal_links_riwayat.jsonl.gz", riwayat_rows),
                        ("rijal_links_imami_chain_names.jsonl.gz", chain_rows),
                        ("imami_chain_names.jsonl.gz", name_rows),
                        ("narrator_assessment_candidates.jsonl.gz", assessment_rows),
                        ("rijal_timeline_facts.jsonl.gz", timeline_rows),
                        ("narrator_event_candidates.jsonl.gz", event_rows),
                        ("biography_availability.jsonl.gz", availability)):
        counts = Counter(row["citation"]["citation_status"] for row in rows)
        reasons = Counter(row["citation"]["not_yet_cited_reason"] for row in rows
                          if row["citation"]["citation_status"] != "cited")
        citation_status[label] = {"cited": counts["cited"], "not_yet_cited": counts["not_yet_cited"],
                                  "reasons": dict(reasons.most_common(8))}

    # coverage
    def bucket(count):
        return "none" if count == 0 else "one" if count == 1 else "several"

    lexicon_linkable = [r for r in lexicon if not r["placeholder_reason"]]
    coverage = {"entries_per_work": {}, "lexicon": {}, "riwayat_labels": {}, "imami_chain_names": {}}
    for work_key, entries in entries_by_work.items():
        stats = Counter()
        for entry in entries:
            stats["entries"] += 1
            stats["with_headword_key"] += bool(entry["headword_keys"])
            stats["with_statement"] += bool(entry["statements"])
            stats["with_verdict_on_subject"] += any(s["is_verdict_on_subject"] for s in entry["statements"])
            stats["statements"] += len(entry["statements"])
            stats["statements_flagged_not_on_subject"] += sum(not s["is_verdict_on_subject"]
                                                              for s in entry["statements"])
            stats["with_death_year"] += any(d.get("year_min") is not None or d.get("year_max") is not None
                                            for d in entry.get("death_statements", []))
            stats["with_death_clause"] += bool(entry.get("death_statements"))
            stats["with_books"] += bool(entry.get("books"))
            stats["books"] += len(entry.get("books", []))
            stats["with_teachers"] += bool(entry.get("teachers_named"))
            stats["with_students_or_route_students"] += bool(entry.get("students_named") or entry.get("route_students"))
            stats["with_imams_named"] += bool(entry.get("imams_named"))
            stats["with_tabaqa"] += bool((entry.get("tabaqa") or {}).get("tabaqa"))
            if entry.get("imam_grouping"):
                stats[f"imam_section:{entry['imam_grouping']['imam']}"] += 1
            if entry.get("subject_kind"):
                stats[f"subject_kind:{entry['subject_kind']}"] += 1
            if entry.get("reports") is not None:
                stats["reports"] += len(entry["reports"])
        coverage["entries_per_work"][work_key] = dict(sorted(stats.items()))
    term_counts = defaultdict(Counter)
    for statement in statement_rows:
        if statement["is_verdict_on_subject"]:
            term_counts[statement["work_id"]][statement["term_id"]] += 1
    coverage["verdict_terms_on_subject_by_work"] = {k: dict(v.most_common(25)) for k, v in sorted(term_counts.items())}
    lex = Counter()
    for row in lexicon_linkable:
        state = lexicon_status[row["scholar_indx"]]
        for work_key in SUNNI_WORKS:
            lex[f"{work_key}:{bucket(state['by_work'].get(work_key, 0))}"] += 1
        lex[f"either:{bucket(state['candidates'])}"] += 1
    coverage["lexicon"] = {"rows": len(lexicon), "linkable_rows": len(lexicon_linkable),
                           "placeholder_rows_never_linked": len(lexicon) - len(lexicon_linkable),
                           "by_bucket": dict(sorted(lex.items())), "parity_with_biography_verification": parity,
                           "note": "'either' counts candidate entries across both works; the same person normally "
                                   "has one entry in each, so 2 here is often one Taqrib + one Tahdhib entry"}
    for label, names, status in (("riwayat_labels", riwayat_names, riwayat_status),
                                 ("imami_chain_names", chain_names, chain_status)):
        counts, weighted, reasons, works_hit = Counter(), Counter(), Counter(), Counter()
        for name_id, info in names.items():
            b = bucket(status[name_id]["candidates"])
            counts[b] += 1
            weighted[b] += info["occurrences"] or 0
            for reason, n in status[name_id]["reasons"].items():
                reasons[reason] += 1
            for work_id in status[name_id]["by_work"]:
                works_hit[work_id] += 1
        coverage[label] = {"names": len(names), "by_bucket": dict(counts),
                           "occurrences_by_bucket": dict(weighted),
                           "occurrences_total": sum(i["occurrences"] or 0 for i in names.values()),
                           "names_with_a_candidate_in_work": dict(sorted(works_hit.items())),
                           "names_with_skip_reason": dict(sorted(reasons.items()))}
    coverage["imami_chain_names"]["distinct_surface_normalized"] = len(distinct_normalized)
    coverage["imami_chain_names"]["mentions"] = sum(len(v) for v in chains.values())
    coverage["imami_chain_names"]["chains"] = len(chains)
    evidence_counts = defaultdict(Counter)
    for row in riwayat_rows + chain_rows:
        for item in row["evidence_fired"]:
            evidence_counts[row["link_set"]][item] += 1
    coverage["evidence_fired"] = {k: dict(sorted(v.items())) for k, v in sorted(evidence_counts.items())}
    coverage["extra"] = extra_counts
    coverage["citation_status_by_output"] = citation_status
    classes = defaultdict(Counter)
    for record in availability:
        classes[f"{record['narrator_set']}|{record['tradition']}"][record["availability_class"]] += 1
        if record["narrator_set"] == "lexicon":
            classes[f"lexicon_by_generation|{record['generation']}"][record["availability_class"]] += 1
        classes[f"{record['narrator_set']}|with_possible_entries"]["yes" if record["possible_entries"] else "no"] += 1
    coverage["biography_availability"] = {k: dict(sorted(v.items())) for k, v in sorted(classes.items())}
    coverage["timeline_facts_by_kind"] = dict(sorted(Counter(f["kind"] for f in timeline_rows).items()))
    coverage["timeline_places"] = {"mapped": sum(1 for f in timeline_rows if f.get("place_id")),
                                   "written_but_unmapped": sum(1 for f in timeline_rows if f.get("place_as_written")
                                                               and not f.get("place_id"))}
    coverage["timeline_facts_by_work"] = dict(sorted(Counter(f["entry_id"].split(":")[1]
                                                             for f in timeline_rows).items()))
    coverage["event_candidates"] = {"rows": len(event_rows),
                                    "with_history_event_ref": sum(1 for r in event_rows if r["history_event_ref"]),
                                    "by_event": dict(Counter(r["event_as_written"] for r in event_rows
                                                             if r["kind"] == "present_at_event").most_common(20))}
    write_json("rijal_coverage.json", coverage)

    # samples
    all_links = lexicon_rows + riwayat_rows + chain_rows
    judged = draw_samples(all_links, entries_by_id, 20, "judge")
    outputs["sample_60_for_judgement.csv"] = write_csv("sample_60_for_judgement.csv", SAMPLE_HEADER, judged)
    judged_ids = {row[2] for row in judged}
    worksheet = draw_samples([r for r in all_links if r["link_id"] not in judged_ids], entries_by_id, 50, "review")
    outputs["review_worksheet_150.csv"] = write_csv(
        "review_worksheet_150.csv", SAMPLE_HEADER + ["reviewer_judgement (right/plausible/wrong)", "reviewer_note"],
        [row + ["", ""] for row in worksheet])

    inputs = {common.relative_path(Path(rs.WORKS[w]["path"])): common.sha256_file(Path(rs.WORKS[w]["path"]))
              for w in SUNNI_WORKS + IMAMI_WORKS}
    for path in (rs.LEXICON, rs.RIWAYAT, CHAIN_SNAPSHOT, HERE / "rijal_extract.py", Path(__file__),
                 Path(rp.__file__), Path(rs.__file__), Path(vl.__file__),
                 HERE.parent / "reconciled" / "external_source_logic.py", HERE.parent / "regen_unified_csvs.py"):
        inputs[common.relative_path(Path(path))] = common.sha256_file(Path(path))
    manifest = {"command": "python -B datasets/hadith-data/rijal/build_rijal_layer.py", "inputs_sha256": inputs,
                "outputs": {name: {"rows": rows, "sha256": common.sha256_file(_guard(name))}
                            for name, rows in sorted(outputs.items())},
                "licence": f"{LICENCE} (derived from OpenITI texts); Riwayat labels CC0; chain names are the "
                           "project's own extraction",
                "status": "candidate_only_unreviewed"}
    write_json("rijal_manifest.json", manifest)
    print(json.dumps({"outputs": {k: v["rows"] for k, v in manifest["outputs"].items()},
                      "coverage": {k: coverage[k] for k in ("lexicon", "riwayat_labels", "imami_chain_names")}},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
