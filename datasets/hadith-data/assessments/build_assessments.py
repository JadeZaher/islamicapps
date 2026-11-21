#!/usr/bin/env python3
"""Consolidate every attributable report grading and narrator verdict on disk into load-ready, credited rows.

Reads only (see README.md for inputs, hashes and licences); writes only into this directory. Deterministic: sorted
rows, gzip mtime 0, no timestamps in row files. Usage (repository root):

    python -B datasets/hadith-data/assessments/build_assessments.py
"""

from __future__ import annotations

import bisect
import collections
import csv
import gzip
import hashlib
import json
import pathlib
import re
import sqlite3
import sys

sys.dont_write_bytecode = True
HERE = pathlib.Path(__file__).resolve().parent
HADITH_DATA = HERE.parent
DATASETS = HADITH_DATA.parent
REPO = DATASETS.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HADITH_DATA / "diagnostics" / "biography-verification"))
import assessment_logic as L  # noqa: E402

csv.field_size_limit(10 ** 9)
PROJECTION = HADITH_DATA / "development" / "pg-load-2026-11-21" / "projection-v3" / "canonical"
HADITHS_CSV = PROJECTION / "hadiths.csv"
ASSESSMENTS_CSV = PROJECTION / "hadith_assessments.csv"
NARRATORS_CSV = PROJECTION / "narrators.csv"
GRADING_RECOVERY = HADITH_DATA / "diagnostics" / "grading-recovery"
COLUMN_L = GRADING_RECOVERY / "pure_canon_closing_statement_candidates.jsonl"
CRITERION_BASIS = GRADING_RECOVERY / "compiler_criterion_basis.jsonl"
PURE_CANON = HADITH_DATA / "archive" / "sheikahmad-pure-canon" / "pure_canon.jsonl"
BIOVER = HADITH_DATA / "diagnostics" / "biography-verification"
TAQRIB_ENTRIES = BIOVER / "rijal_entries_taqrib.jsonl.gz"
RIJAL_LINKS = BIOVER / "lexicon_rijal_links.jsonl.gz"
LEXICON_LABELS = HADITH_DATA / "diagnostics" / "biography-recovery" / "narrator_assessment_candidates.jsonl"
EXTERNAL_LINKS = HADITH_DATA / "reconciled" / "external_narrator_lexicon_links.jsonl.gz"
KG_NARRATORS = HADITH_DATA / "reconciled" / "hadith_kg_narrators.jsonl.gz"
CROSSWALK = HADITH_DATA / "reconciled" / "external_report_crosswalk.jsonl.gz"
EXTERNAL = DATASETS / "sources" / "external"
HADITH_KG = EXTERNAL / "hadith-kg" / "hadith-kg.db"
RIWAYAT = EXTERNAL / "riwayat-corpus" / "hadith_master.db"
RIJAL_LANE = HADITH_DATA / "rijal"

LICENCE = {
    "SUN": "sunnah.com text by permission (owner, 2026-11-21)",
    "THQ": "CC BY 4.0 (Thaqalayn)",
    "NMC": "NabiMuhammad.com Pure Canon by permission (owner, 2026-11-21)",
    "RIJ": "CC BY-NC-SA 4.0 (OpenITI rijal text; derived rows share alike, non-commercial)",
    "HKG": "CC BY 4.0 (hadith-kg by emadjumaah, revision 8ae7e3d5)",
    "MSD": "Muslim Scholars Database lexicon by permission (owner, 2026-11-21)",
    "OITI": "CC BY-NC-SA 4.0 (OpenITI)",
}
GRADE_SCHEME = {"tradition:sunni": "sunni_7tier", "tradition:imami": "imami_4tier", "tradition:zaydi": "zaydi_3tier",
                "tradition:ibadi": "ibadi_2tier"}
COLUMN_L_WORK = {"سنن الترمذي": "sunni:tirmidhi", "سنن الترمذي 1/5": "sunni:tirmidhi", "سنن أبي داود": "sunni:abudawud",
                 "صحيح البخاري": "sunni:bukhari", "سنن النسائي": "sunni:nasai", "صحيح مسلم": "sunni:muslim",
                 "سنن ابن ماجه": "sunni:ibnmajah", "مسند حنبل": "sunni:ahmad", "موطأ مالك": "sunni:muwatta",
                 "سنن الدارمي": "sunni:darimi"}
MIN_JOIN_LETTERS = 40
JOIN_FALLBACK_LETTERS = 60
REVIEW = "candidate_only"


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 22), b""):
            digest.update(block)
    return digest.hexdigest()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(REPO).as_posix()


def write_jsonl_gz(name: str, rows: list) -> int:
    path = HERE / name
    with open(path, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
        for row in rows:
            handle.write((json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8"))
    return len(rows)


def write_json(name: str, value) -> None:
    with open(HERE / name, "w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")


def read_jsonl(path: pathlib.Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def connect_readonly(path: pathlib.Path) -> sqlite3.Connection:
    return sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)


# --- corpus ------------------------------------------------------------------------------------------------------

def load_corpus() -> dict:
    corpus = {}
    with open(HADITHS_CSV, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            corpus[row["id"]] = {
                "record_id": row["record_id"], "work": row["collection_id"].replace("collection:", ""),
                "tradition_id": row["tradition_id"], "text_ar": row["text_ar"] or "", "arabic_sha256": row["arabic_sha256"],
                "hadith_no": row["hadith_no"], "quality_excluded": row["quality_excluded"],
            }
    return corpus


# --- report gradings ---------------------------------------------------------------------------------------------

def imami_rows(corpus: dict) -> list:
    """The loaded Imami cited rulings, carried with their ids; canonical re-derived conservatively beside the loaded one."""
    rows = []
    with open(ASSESSMENTS_CSV, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["kind"] != "cited_ruling":
                continue
            canonical, reason = L.imami_canonical(row["grade_raw"])
            assert L.imami_non_ruling_reason(row["grade_raw"]) is None, row["id"]
            report = corpus[row["hadith_id"]]
            rows.append({
                "id": row["id"], "hadith_id": row["hadith_id"], "record_id": report["record_id"], "work": report["work"],
                "tradition_id": row["tradition_id"], "grade_scheme": row["grade_scheme"], "ordinal": int(row["ordinal"]),
                "kind": "cited_ruling", "basis_kind": "cited_ruling_in_commentary", "grader": row["grader"], "grader_ar": None,
                "as_quoted_by": None, "grade_raw": row["grade_raw"], "grade_canonical": canonical, "canonical_reason": reason,
                "grade_canonical_loaded": row["grade_canonical"] or None, "statement_ar": row["grade_raw"],
                "citation_raw": row["citation_raw"] or None, "cited_work": row["cited_work"] or None,
                "cited_volume": row["cited_volume"] or None, "cited_page": row["cited_page"] or None,
                "source_field": row["source_field"], "char_start": None, "char_end": None,
                "arabic_sha256": report["arabic_sha256"], "attribution_basis": "Thaqalayn's gradings field names the grader and cites his work",
                "source_codes": ["THQ"], "licence": LICENCE["THQ"], "review_state": REVIEW, "already_loaded": True,
                "corroborated_by": [],
            })
    return rows


def statement_row(hadith_id: str, report: dict, statement: dict, source_field: str, source_codes: list, ordinal: int,
                  extra: dict | None = None) -> dict:
    canonical, reason = L.statement_canonical(statement.get("term_folded"))
    kind = "cited_ruling" if statement["decision"] == "quoted_ruling" else "compiler_statement"
    basis = {"text_ar": "compiler_statement_in_report_text", "pure_canon_column_l": "compiler_statement_in_closing_column"}[source_field]
    if statement["decision"] == "quoted_ruling":
        basis = "ruling_quoted_by_compiler"
    tradition = report["tradition_id"]
    return {
        "id": f"assessment:{report['record_id']}:{tradition.split(':')[1]}:{source_field}:{ordinal:02d}",
        "hadith_id": hadith_id, "record_id": report["record_id"], "work": report["work"], "tradition_id": tradition,
        "grade_scheme": GRADE_SCHEME[tradition], "ordinal": ordinal, "kind": kind, "basis_kind": basis,
        "grader": statement["grader"], "grader_ar": statement.get("grader_ar"), "as_quoted_by": statement.get("quoted_by"),
        "grade_raw": statement["term_ar"], "grade_canonical": canonical, "canonical_reason": reason,
        "grade_canonical_loaded": None,
        "statement_ar": statement["source_span_verbatim"] if source_field == "text_ar" else statement["statement_ar"], "terms_in_order": statement["terms_in_order"],
        "citation_raw": None, "cited_work": L.COMPILER_VOICE[report["work"]]["work"], "cited_volume": None, "cited_page": None,
        "source_field": source_field, "char_start": statement.get("char_start") if source_field == "text_ar" else None,
        "char_end": statement.get("char_end") if source_field == "text_ar" else None,
        "arabic_sha256": report["arabic_sha256"], "attribution_basis": statement["attribution_basis"],
        "source_codes": source_codes, "licence": "; ".join(LICENCE[c] for c in source_codes), "review_state": REVIEW,
        "already_loaded": False, "corroborated_by": [], **(extra or {}),
    }


def in_text_statements(corpus: dict):
    rows, held = [], []
    for hadith_id in sorted(corpus):
        report = corpus[hadith_id]
        if report["work"] not in L.COMPILER_VOICE:
            continue
        ordinal = 0
        for statement in L.report_statements(report["text_ar"], report["work"]):
            assert report["text_ar"][statement["char_start"]:statement["char_end"]] == statement["source_span_verbatim"]
            if statement["decision"] == "held":
                held.append({"hadith_id": hadith_id, "record_id": report["record_id"], "work": report["work"],
                             "tradition_id": report["tradition_id"], "source_field": "text_ar", "reason": statement["reason"],
                             "statement_ar": statement["statement_ar"], "term_ar": statement.get("term_ar"),
                             "named_subject": statement.get("named_subject"), "char_start": statement["char_start"],
                             "char_end": statement["char_end"]})
                continue
            ordinal += 1
            rows.append(statement_row(hadith_id, report, statement, "text_ar", ["SUN"] if hadith_id.startswith("hadith:k6:")
                                      else ["NMC"] if hadith_id.startswith("hadith:pure-canon:") else ["OITI"], ordinal))
    return rows, held


def load_pure_canon_rows() -> dict:
    """pc id -> (work, matn letters, chain letters, hadith_no) for every Pure Canon row of the mapped works."""
    out = {}
    for row in read_jsonl(PURE_CANON):
        work = COLUMN_L_WORK.get((row.get("source") or "").strip())
        if work:
            out[row["id"]] = {"work": work, "letters": L.comparison_letters(row["text_ar"]),
                              "chain_letters": L.chain_name_letters(row.get("chain") or ""), "hadith_no": row.get("hadith_no"),
                              "text_ar": row["text_ar"]}
    return out


class WorkIndex:
    """All rows of one work as one letters string, for unique-occurrence lookups."""

    def __init__(self, items: list):
        self.ids, self.starts, parts, position = [], [], [], 0
        for hadith_id, letters in items:
            self.ids.append(hadith_id)
            self.starts.append(position)
            parts.append(letters)
            position += len(letters) + 1
        self.blob = "|".join(parts)

    def rows_containing(self, needle: str, limit: int = 3) -> list:
        found, start = [], 0
        while len(found) < limit:
            position = self.blob.find(needle, start)
            if position < 0:
                break
            index = bisect.bisect_right(self.starts, position) - 1
            if not found or found[-1][0] != self.ids[index]:
                found.append((self.ids[index], position - self.starts[index]))
            start = position + 1
        return found


def column_l_statements(corpus: dict, in_text: list):
    """Pure Canon closing statements: loaded pc rows join by id; six-book rows join to K6 by unique Arabic text."""
    pc_rows = load_pure_canon_rows()
    letters_count = collections.Counter((v["work"], v["letters"]) for v in pc_rows.values())
    k6_by_work = collections.defaultdict(list)
    for hadith_id, report in corpus.items():
        if hadith_id.startswith("hadith:k6:"):
            k6_by_work[report["work"]].append((hadith_id, L.comparison_letters(report["text_ar"])))
    letters_by_id = {hid: letters for items in k6_by_work.values() for hid, letters in items}
    indexes = {work: WorkIndex(sorted(items)) for work, items in k6_by_work.items()}
    existing = collections.defaultdict(list)
    for row in in_text:
        existing[row["hadith_id"]].append(row)
    rows, held, joins = [], [], []
    ordinals = collections.Counter()
    for candidate in sorted(read_jsonl(COLUMN_L), key=lambda r: int(r["pure_canon_id"].split("_")[1])):
        pc_id = candidate["pure_canon_id"]
        work = COLUMN_L_WORK.get(candidate["source_label"].strip())
        closing = candidate["closing_text_ar_verbatim"] or ""
        base_held = {"pure_canon_id": pc_id, "work": work, "source_field": "pure_canon_column_l", "statement_ar": closing,
                     "sheet_row": candidate["sheet_row"]}
        loaded_id = f"hadith:pure-canon:{pc_id}"
        join = {"pure_canon_id": pc_id, "work": work, "sheet_row": candidate["sheet_row"],
                "pc_hadith_no": candidate.get("hadith_no_in_book")}
        if loaded_id in corpus:
            target, join_basis = loaded_id, "pure_canon_id_loaded"
        elif work in indexes:
            pc = pc_rows.get(pc_id)
            if pc is None or len(pc["letters"]) < MIN_JOIN_LETTERS:
                joins.append({**join, "status": "matn_too_short_or_missing"})
                held.append({**base_held, "reason": "join_matn_too_short_or_missing"})
                continue
            if letters_count[(work, pc["letters"])] > 1:
                joins.append({**join, "status": "pc_matn_not_unique_in_work"})
                held.append({**base_held, "reason": "join_pc_matn_not_unique_in_work"})
                continue
            found = indexes[work].rows_containing(pc["letters"])
            matn_match = "whole_matn_contained"
            if not found and len(pc["letters"]) >= 2 * JOIN_FALLBACK_LETTERS:
                tail = indexes[work].rows_containing(pc["letters"][-JOIN_FALLBACK_LETTERS:])
                head = {f[0] for f in indexes[work].rows_containing(pc["letters"][:JOIN_FALLBACK_LETTERS])}
                found = [f for f in tail if f[0] in head]
                matn_match = "opening_and_closing_60_letters_contained"
            if len(found) != 1:
                joins.append({**join, "status": "no_k6_row" if not found else "several_k6_rows",
                              "candidates": [f[0] for f in found]})
                held.append({**base_held, "reason": "join_no_unique_k6_row" if found else "join_no_k6_row"})
                continue
            target, offset = found[0]
            chain = pc["chain_letters"]
            k6_chain = L.chain_name_letters(corpus[target]["text_ar"])
            if not chain:
                chain_class = "no_chain_in_pure_canon"
            elif chain in k6_chain:
                chain_class = "chain_names_contained"
            elif len(chain) >= 20 and chain[:20] in k6_chain:
                chain_class = "chain_opening_names_agree"
            else:
                chain_class = "chain_differs"
            joins.append({**join, "status": "joined" if chain_class != "chain_differs" else "chain_differs", "matn_match": matn_match,
                          "hadith_id": target, "chain_agreement": chain_class, "k6_hadith_no": corpus[target]["hadith_no"]})
            if chain_class == "chain_differs":
                held.append({**base_held, "reason": "join_chain_differs", "hadith_id_candidate": target})
                continue
            join_basis = f"unique_{matn_match}_{chain_class}"
        else:
            joins.append({**join, "status": "work_not_in_corpus"})
            held.append({**base_held, "reason": "work_not_in_corpus"})
            continue
        report = corpus[target]
        opener = L.first_chain_opener(closing)
        statements = []
        if report["work"] in L.COMPILER_VOICE:
            statements = L.report_statements(closing[:opener], report["work"])
            statements += [{**s, "decision": "held", "reason": "follows_another_chain_in_closing_text"}
                           for s in L.report_statements(closing[opener:], report["work"]) if s["decision"] != "held"]
        if not statements:
            held.append({**base_held, "hadith_id": target, "reason": "no_report_grading_clause_in_closing_text"})
            continue
        for statement in statements:
            if statement["decision"] == "held":
                held.append({**base_held, "hadith_id": target, "reason": statement["reason"], "term_ar": statement.get("term_ar")})
                continue
            same = [r for r in existing[target] if r["grader"] == statement["grader"]
                    and L.fold(r["grade_raw"]) == L.fold(statement["term_ar"])]
            if same:
                for row in same:
                    row["corroborated_by"].append({"source_code": "NMC", "source_field": "pure_canon_column_l",
                                                   "pure_canon_id": pc_id, "sheet_row": candidate["sheet_row"],
                                                   "statement_ar": statement["statement_ar"]})
                continue
            ordinals[target] += 1
            rows.append(statement_row(target, report, statement, "pure_canon_column_l", ["NMC"] if target == loaded_id
                                      else ["NMC", "SUN"], ordinals[target],
                                      {"pure_canon_id": pc_id, "sheet_row": candidate["sheet_row"], "join_basis": join_basis,
                                       "k6_has_in_text_statement": bool(existing[target])}))
    return rows, held, joins


def criterion_links(corpus: dict) -> list:
    basis = {r["work"]: r for r in read_jsonl(CRITERION_BASIS)}
    names = {"sunni:bukhari": "Sahih al-Bukhari", "sunni:muslim": "Sahih Muslim"}
    rows = []
    for hadith_id in sorted(corpus):
        report = corpus[hadith_id]
        if report["work"] in names:
            item = basis[names[report["work"]]]
            rows.append({"id": f"assessment:{report['record_id']}:sunni:compiler_criterion:00", "hadith_id": hadith_id,
                         "record_id": report["record_id"], "tradition_id": "tradition:sunni", "grade_scheme": "sunni_7tier",
                         "ordinal": 0, "kind": "compiler_criterion", "basis_kind": "compiler_criterion",
                         "criterion_basis_id": item["criterion_basis_id"], "grader": item["compiler"],
                         "grade_raw": f"included in {item['work']} under its compiler's stated criterion",
                         "grade_canonical": None, "canonical_reason": "criterion_is_not_a_verdict_on_this_report",
                         "source_field": "collection_membership", "source_codes": ["SUN"], "licence": LICENCE["SUN"],
                         "review_state": REVIEW, "arabic_sha256": report["arabic_sha256"]})
    return rows


# --- narrator verdicts -------------------------------------------------------------------------------------------

def unique_links(source: str) -> dict:
    """rijal entry number -> lexicon scholar_indx, for unique links only (biography-verification)."""
    out = {}
    for row in read_jsonl(RIJAL_LINKS):
        if row["source"] == source and row["status"] == "unique":
            out[row["entry_number"]] = row["scholar_indx"]
    return out


def narrator_row(**fields) -> dict:
    base = {"narrator_id": None, "subject_ref": None, "link_basis": None, "tradition_id": None, "kind": "critic_ruling",
            "basis_kind": None, "critic": None, "critic_ar": None, "critic_key": None, "as_quoted_by": None, "reporter_ar": None,
            "verdict_raw": None, "verdict_canonical": None, "canonical_reason": None, "quote_ar": None, "work": None,
            "citation": None, "source_codes": [], "licence": None, "review_state": REVIEW}
    base.update(fields)
    return base


def taqrib_rows(narrators: set) -> list:
    links = unique_links("ibn_hajar_taqrib")
    rows = []
    for entry in read_jsonl(TAQRIB_ENTRIES):
        verdict = (entry.get("verdict") or {}).get("verdict_text")
        if not verdict:
            continue
        canonical, reason = L.narrator_canonical(verdict)
        scholar = links.get(entry["entry_number"])
        narrator_id = f"narrator:rawi:{scholar}" if scholar and f"narrator:rawi:{scholar}" in narrators else None
        kind = "companion_status" if L._COMPANION.match(verdict) else "verdict"
        rows.append(narrator_row(
            id=f"narrator-assessment:taqrib:{entry['entry_number']}:L{entry['line']}:1", narrator_id=narrator_id,
            subject_ref=f"rijal:ibn-hajar-taqrib:{entry['entry_number']}",
            link_basis="biography-verification unique name link" if narrator_id else None, tradition_id="tradition:sunni",
            basis_kind="rijal_entry_verdict" if kind == "verdict" else "companion_status_in_rijal_entry",
            critic="Ibn Hajar al-Asqalani (d. 852)", critic_ar="ابن حجر العسقلاني", critic_key="ibn_hajar",
            verdict_raw=verdict, verdict_canonical=canonical if kind == "verdict" else None,
            canonical_reason=reason if kind == "verdict" else "companion_status_not_a_verdict", quote_ar=entry["passage_ar"],
            work="Taqrib al-Tahdhib (ed. Muhammad Awwama)",
            citation={"work_id": "work:ibn_hajar_taqrib", "edition_id": "edition:openiti:0852IbnHajarCasqalani.TaqribTahdhib.JK000121-ara1",
                      "entry": entry["entry_number"], "page": entry["start_page"], "pages": entry["pages"]},
            rijal_work_key="ibn_hajar_taqrib", openiti_line=entry["line"], verbatim_passage=entry["passage_ar"],
            source_codes=["RIJ"], licence=LICENCE["RIJ"], verdict_is_folded_span=True))
    return rows


def mizzi_rows(narrators: set):
    import rijal_sources as rs
    links = unique_links("mizzi_tahdhib_kamal")
    rows, held = [], []
    for entry in rs.read_entries("mizzi_tahdhib_kamal"):
        number = entry["entry_number"] or f"line{entry['line']}"
        scholar = links.get(entry["entry_number"]) if entry["entry_number"] else None
        narrator_id = f"narrator:rawi:{scholar}" if scholar and f"narrator:rawi:{scholar}" in narrators else None
        text = entry["text"]
        cut = text.find("روى عنه")
        statements = L.mizzi_statements(text[cut:] if cut >= 0 else text)
        for index, statement in enumerate(statements, 1):
            base = {"subject_ref": f"rijal:mizzi-tahdhib-al-kamal:{number}", "narrator_id": narrator_id}
            if statement["decision"] == "held":
                held.append({**base, "reason": statement["reason"], "speaker_ar_verbatim": statement["speaker_ar_verbatim"],
                             "statement_ar": statement["statement_ar"]})
                continue
            listed = statement["decision"] == "listed_in_work"
            verdict_raw = statement["verdict_ar_folded"] if not listed else statement["verdict_ar_folded"]
            canonical, reason = (None, "listing_in_a_work_is_not_a_verdict_term") if listed else \
                L.narrator_canonical(re.split(r"[،.]", verdict_raw)[0])
            rows.append(narrator_row(
                id=f"narrator-assessment:mizzi:{number}:L{entry['line']}:{index}", **base,
                link_basis="biography-verification unique name link" if narrator_id else None, tradition_id="tradition:sunni",
                basis_kind="listed_in_work" if listed else "critic_quoted_in_rijal_work",
                critic=statement.get("critic_display"), critic_ar=statement["critic_ar"], critic_key=statement.get("critic_key"),
                as_quoted_by="al-Mizzi (d. 742), Tahdhib al-Kamal", reporter_ar=statement.get("reporter_ar"),
                critic_resolution=statement["resolution"], verdict_raw=verdict_raw, verdict_terms=statement.get("terms"),
                verdict_canonical=canonical, canonical_reason=reason, quote_ar=statement["statement_ar"],
                speaker_ar_verbatim=statement["speaker_ar_verbatim"], work="Tahdhib al-Kamal (ed. Bashar Awwad Ma'ruf)",
                citation={"work_id": "work:mizzi_tahdhib_kamal", "edition_id": "edition:openiti:0742Mizzi.TahdhibKamal.Shamela0003722-ara1",
                          "entry": number, "page": entry["start_page"], "pages": entry["pages"]},
                rijal_work_key="mizzi_tahdhib_kamal", openiti_line=entry["line"], verbatim_passage=statement["statement_ar"],
                source_codes=["RIJ"], licence=LICENCE["RIJ"]))
    return rows, held


def imami_rijal_rows():
    """al-Najashi and al-Tusi: the rijal lane's files when present, else the OpenITI entries via rijal_sources."""
    import rijal_sources as rs
    rows, held, source = [], [], "openiti_entries_via_rijal_sources"
    if RIJAL_LANE.exists() and any(RIJAL_LANE.glob("*najashi*")):
        source = "rijal_lane_present_but_not_consumed"
    works = {"najashi_rijal": ("al-Najashi (d. 450)", "النجاشي", "Rijal al-Najashi", "najashi"),
             "tusi_rijal": ("al-Tusi (d. 460)", "الطوسي", "Rijal al-Tusi", "tusi-rijal"),
             "tusi_fihrist": ("al-Tusi (d. 460)", "الطوسي", "al-Fihrist", "tusi-fihrist")}
    for work, (critic, critic_ar, title, slug) in works.items():
        for entry in rs.read_entries(work):
            number = entry["entry_number"] or f"line{entry['line']}"
            for index, verdict in enumerate(L.imami_rijal_verdicts(entry["text"]), 1):
                base = {"subject_ref": f"rijal:{slug}:{number}", "work": work}
                if verdict["decision"] == "held":
                    held.append({**base, "reason": verdict["reason"], "clause_ar_folded": verdict["clause_ar_folded"],
                                 "entry_head": entry["text"][:120]})
                    continue
                canonical, reason = L.narrator_canonical(verdict["verdict_ar_folded"])
                rows.append(narrator_row(
                    id=f"narrator-assessment:{slug}:{number}:L{entry['line']}:{index}", subject_ref=base["subject_ref"],
                    tradition_id="tradition:imami", basis_kind="rijal_entry_verdict", critic=critic, critic_ar=critic_ar,
                    critic_key=slug.split("-")[0], verdict_raw=verdict["verdict_ar_folded"], clause_ar_folded=verdict["clause_ar_folded"], verdict_terms=verdict["terms"],
                    verdict_canonical=canonical, canonical_reason=reason, quote_ar=entry["text"][:1200], entry_head_ar=entry["text"][:160],
                    work=title, citation={"work_id": f"work:{work}", "edition_id": f"edition:openiti:{rs.WORKS[work]['openiti_uri']}",
                                          "entry": number, "page": entry["start_page"], "pages": entry["pages"]},
                    rijal_work_key=work, openiti_line=entry["line"],
                    verbatim_passage=locate_verbatim(entry["text"], verdict["clause_ar_folded"]),
                    narrator_link_note="no Imami narrator authority is loaded; attached to the rijal entry",
                    source_codes=["RIJ"], licence=LICENCE["RIJ"]))
    return rows, held, source


def hadith_kg_rows(narrators: set):
    links = {}
    for row in read_jsonl(EXTERNAL_LINKS):
        if row["external_narrator_id"].startswith("hadith-kg:rawi:"):
            links[int(row["external_narrator_id"].split(":")[-1])] = row
    contexts = {}
    for row in read_jsonl(KG_NARRATORS):
        contexts[row["rawi_id"]] = row.get("tradition_context_chain_positions") or {}
    connection = connect_readonly(HADITH_KG)
    alems = {r[0]: r[1:] for r in connection.execute("select id, name, shuhra, death_year, tabaka from alems")}
    rows, excluded = [], collections.Counter()
    profile = {"by_kind": collections.Counter(), "by_critic": collections.Counter(), "books_named": collections.Counter(),
               "excluded": excluded, "statements": 0}
    for statement_id, alem_id, rawi_id, qawl in connection.execute("select id, alem_id, rawi_id, qawl from aqwal order by id"):
        profile["statements"] += 1
        if alem_id in L.HADITH_KG_NOT_A_CRITIC:
            excluded[L.HADITH_KG_NOT_A_CRITIC[alem_id]] += 1
            continue
        book, text = L.qawl_book_and_text(qawl)
        kind, listed_work = L.classify_critic_statement(text)
        if kind in ("silence", "mention_only"):
            excluded[f"{kind}_not_a_verdict"] += 1
            continue
        name, shuhra, death_year, _ = alems[alem_id]
        link = links.get(rawi_id)
        narrator_id = f"narrator:rawi:{link['scholar_indx']}" if link and f"narrator:rawi:{link['scholar_indx']}" in narrators else None
        tradition = "tradition:imami" if alem_id in L.HADITH_KG_IMAMI_CRITICS else "tradition:sunni"
        canonical, reason = L.narrator_canonical(text) if kind == "verdict" else (None, f"{kind}_not_a_verdict_term")
        profile["by_kind"][kind] += 1
        profile["by_critic"][shuhra] += 1
        if book:
            profile["books_named"][book] += 1
        rows.append(narrator_row(
            id=f"narrator-assessment:hadith-kg:aqwal:{statement_id}", narrator_id=narrator_id,
            subject_ref=f"narrator:hadith-kg:{rawi_id}", link_basis=link["basis"] if narrator_id else None,
            tradition_id=tradition, tradition_basis="critic's own tradition" if alem_id in L.HADITH_KG_IMAMI_CRITICS
            else "default: hadith-kg's critic register is the Sunni jarh wa ta'dil literature",
            basis_kind={"verdict": "dataset_record_of_critic_statement", "listed_in_work": "listed_in_work",
                        "companion_status": "companion_status_statement"}[kind],
            critic=shuhra, critic_ar=shuhra, critic_full_name_ar=name, critic_death_year=death_year or None,
            critic_key=f"hadith-kg:alem:{alem_id}", as_quoted_by="hadith-kg (al-Jami' Hadith Knowledge Graph, from hadithdb 2017)",
            verdict_raw=qawl, verdict_text_without_book=text, book_named_in_statement=book, listed_work=listed_work,
            verdict_canonical=canonical, canonical_reason=reason, quote_ar=qawl, work=None,
            external_tradition_context=contexts.get(rawi_id), citation={"dataset": "hadith-kg", "table": "aqwal", "row_id": statement_id,
                                                                        "alem_id": alem_id, "rawi_id": rawi_id},
            source_codes=["HKG"], licence=LICENCE["HKG"]))
    connection.close()
    return rows, profile


def lexicon_rows(narrators: set) -> list:
    rows = []
    for row in read_jsonl(LEXICON_LABELS):
        narrator_id = f"narrator:rawi:{row['scholar_indx']}"
        rows.append(narrator_row(
            id=f"narrator-assessment:lexicon:{row['scholar_indx']}:1", narrator_id=narrator_id if narrator_id in narrators else None,
            subject_ref=f"lexicon:{row['scholar_indx']}", link_basis="lexicon row", tradition_id=None,
            kind="consensus_summary", basis_kind="narrator_lexicon_source_not_stated", critic=None,
            verdict_raw=row["term_ar"], verdict_canonical=None,
            canonical_reason="lexicon label: no critic named, so no verdict category is asserted",
            quote_ar=row["source_cell_verbatim"], work="narrator lexicon (Muslim Scholars Database)",
            label_kind=row["kind"], book_symbols_ar=row["book_symbols_ar"],
            display_label="narrator lexicon, source not stated", source_codes=["MSD"], licence=LICENCE["MSD"]))
    return rows


# --- exclusions: computed gradings in the external datasets --------------------------------------------------------

def external_exclusion_profile() -> dict:
    connection = connect_readonly(HADITH_KG)
    q = lambda sql: connection.execute(sql).fetchall()  # noqa: E731
    contingency = q("select max_rank, matn_no, count(*) from sanads group by 1, 2 order by 1, 2")
    by_rank = collections.defaultdict(dict)
    for rank, label, count in contingency:
        by_rank[str(rank)][str(label)] = count
    total_hukum = q("select count(*) from sanads")[0][0]
    templated = sum(c for h, c in q("select hukum, count(*) from sanads group by 1") if L.is_templated_hukum(h))
    named_in_hukum = q("select count(*) from sanads where hukum like '%الألباني%' or hukum like '%صححه%' or hukum like '%حسنه%'")[0][0]
    out = {
        "hadith_kg": {
            "excluded_fields": L.HADITH_KG_COMPUTED_FIELDS,
            "hadith_rows_with_hukm_label": q("select count(*) from hadiths")[0][0],
            "sanad_rows": total_hukum, "sanads_hukum_in_templated_frames": templated,
            "sanads_hukum_naming_a_scholar_or_verb_of_grading": named_in_hukum,
            "chain_label_by_weakest_rank": by_rank,
            "how_told_apart": ("A grading is kept only when the dataset names who said it. hadith-kg's report and chain labels "
                               "name no grader; every hukum sentence is built from one of a few frames around narrator rank "
                               "wording; and the chain label is determined by the weakest narrator rank (contingency table "
                               "chain_label_by_weakest_rank), i.e. computed."),
        },
    }
    connection.close()
    connection = connect_readonly(RIWAYAT)
    columns = {table: [c[1] for c in connection.execute(f"pragma table_info({table})")]
               for (table,) in connection.execute("select name from sqlite_master where type='table'")}
    grading_like = {t: [c for c in cols if re.search(r"grade|hukm|hukum|rank|verdict|jarh|tadil|reliab", c, re.I)]
                    for t, cols in columns.items()}
    out["riwayat"] = {"tables": sorted(columns), "columns_that_look_like_grading": {k: v for k, v in grading_like.items() if v},
                      "conclusion": "No report grading and no critic statement is stored. Narrator fields (tradition, madhhab, "
                                    "tabaqa, death_year) and identification confidences are the corpus's own labels or model "
                                    "outputs, not verdicts; nothing is taken from Riwayat."}
    connection.close()
    return out


# --- coverage ------------------------------------------------------------------------------------------------------

def coverage(corpus: dict, report_rows: list, narrator_rows: list, narrators: set) -> dict:
    graded_before, graded_after = collections.defaultdict(set), collections.defaultdict(set)
    for row in report_rows:
        graded_after[row["hadith_id"]].add(row["grader"])
        if row.get("already_loaded"):
            graded_before[row["hadith_id"]].add(row["grader"])
    by_tradition = collections.defaultdict(lambda: collections.Counter())
    by_work = collections.defaultdict(lambda: collections.Counter())
    for hadith_id, report in corpus.items():
        for key, table in ((report["tradition_id"], by_tradition), (report["work"], by_work)):
            table[key]["reports"] += 1
            table[key]["before"] += hadith_id in graded_before
            table[key]["after"] += hadith_id in graded_after
            table[key]["after_two_or_more_graders"] += len(graded_after.get(hadith_id, ())) > 1
    competing = 0
    raw_by_report = collections.defaultdict(lambda: collections.defaultdict(set))
    for row in report_rows:
        raw_by_report[row["hadith_id"]][row["grader"]].add(L.fold(row["grade_raw"]))
    for graders in raw_by_report.values():
        if len(graders) > 1 and len({frozenset(v) for v in graders.values()}) > 1:
            competing += 1
    attributed = [r for r in narrator_rows if r["critic"] or r["critic_ar"]]
    per_narrator = collections.defaultdict(set)
    per_narrator_canonical = collections.defaultdict(lambda: collections.defaultdict(set))
    for row in attributed:
        if row["narrator_id"]:
            per_narrator[row["narrator_id"]].add(row["critic_key"] or row["critic_ar"])
            if row["verdict_canonical"]:
                per_narrator_canonical[row["narrator_id"]][row["verdict_canonical"]].add(row["critic_key"] or row["critic_ar"])
    by_source = collections.Counter()
    for row in attributed:
        if row["narrator_id"]:
            by_source[row["source_codes"][0] + ":" + (row["work"] or "hadith-kg")] += 1
    lexicon_only = {r["narrator_id"] for r in narrator_rows if r["basis_kind"] == "narrator_lexicon_source_not_stated" and r["narrator_id"]}
    subjects = collections.Counter(r["subject_ref"].split(":")[0] + ":" + r["subject_ref"].split(":")[1]
                                   for r in attributed if not r["narrator_id"])
    return {
        "reports_by_tradition": {k: dict(v) for k, v in sorted(by_tradition.items())},
        "reports_by_work": {k: dict(v) for k, v in sorted(by_work.items())},
        "reports_with_rulings_from_two_or_more_graders_that_differ_in_wording": competing,
        "narrators": {
            "lexicon_narrators_loaded": len(narrators),
            "before_with_attributed_verdict": 0,
            "before_note": "production narrator_assessments: 20 consensus_summary rows, critic null (not attributed)",
            "after_with_attributed_verdict": len(per_narrator),
            "after_with_two_or_more_named_critics": sum(1 for v in per_narrator.values() if len(v) > 1),
            "after_with_competing_mapped_verdicts": sum(1 for v in per_narrator_canonical.values() if len(v) > 1),
            "after_with_lexicon_label_only_source_not_stated": len(lexicon_only - set(per_narrator)),
            "attributed_rows_attached_to_lexicon_narrators_by_source": dict(by_source),
            "attributed_rows_attached_only_to_a_rijal_entry_or_external_narrator": dict(subjects),
        },
    }


def ibadi_zaydi_narrator_reach(kg_rows: list) -> dict:
    out = {}
    for tradition in ("Ibadi", "Zaydi"):
        subjects = {r["subject_ref"] for r in kg_rows if (r.get("external_tradition_context") or {}).get(tradition)}
        out[tradition] = {"hadith_kg_narrators_in_chains_with_a_critic_statement": len(subjects),
                          "statements": sum(1 for r in kg_rows if (r.get("external_tradition_context") or {}).get(tradition)),
                          "note": "statements by Sunni critics about narrators who appear in this tradition's chains in hadith-kg; "
                                  "shown as Sunni critics' verdicts, never as this tradition's"}
    return out


# --- overstatements ----------------------------------------------------------------------------------------------

def overstatements(imami: list) -> list:
    grouped = collections.defaultdict(lambda: {"rows": 0, "graders": collections.Counter()})
    for row in imami:
        if row["grade_canonical_loaded"] != row["grade_canonical"]:
            key = (row["grade_raw"], row["grade_canonical_loaded"], row["grade_canonical"], row["canonical_reason"])
            grouped[key]["rows"] += 1
            grouped[key]["graders"][row["grader"]] += 1
    out = []
    for (raw, loaded, conservative, reason), value in sorted(grouped.items(), key=lambda kv: -kv[1]["rows"]):
        out.append({"grade_raw": raw, "loaded_canonical": loaded, "conservative_canonical": conservative, "reason": reason,
                    "rows": value["rows"], "graders": dict(value["graders"])})
    return out


def locate_verbatim(text: str, clause_folded: str) -> str | None:
    """The original words of `text` whose fold is `clause_folded` (None when it cannot be located exactly)."""
    folded = L.fold(text)
    start = folded.find(clause_folded) if clause_folded else -1
    if start < 0:
        return None
    return L.verbatim_span(text, start, start + len(clause_folded))


# --- one citation shape for every row (validate_citations.py checks it) -----------------------------------------

RIJAL_LANE_OUTPUT = RIJAL_LANE / "output"
REGISTRY_LICENCE = {"SUN": "Permission (owner, 2026-11-21)", "THQ": "CC BY 4.0", "NMC": "Permission (owner, 2026-11-21)",
                    "RIJ": "CC BY-NC-SA 4.0", "HKG": "CC BY 4.0", "MSD": "Permission (owner, 2026-11-21)",
                    "OITI": "CC BY-NC-SA 4.0"}
REPORT_EDITIONS = {
    "SUN": "sunnah.com Arabic via Kaggle fahd09/hadith-dataset (retrieved 2018-08-22), as loaded in projection 2026.11.21.3",
    "NMC": "NabiMuhammad.com, Hadith Pure Canon Authentica workbook (Hadith-Pure-Canon-Authentica.xlsx, Sheet1; retrieved 2026-03-29)",
    "THQ": "Thaqalayn (ThaqalaynAPI v2 books, retrieved 2026-04-19): the report's gradings field",
    "OITI": "OpenITI release 2025.1.9",
}
WORKBOOK_SHA256 = "2189b0a511d78d1ef05ad3a4bb3c9ca16fccfbdfe415ed910af66ed8aa26cca0"  # grading-recovery README


class RijalLane:
    """Read-only view of the rijal lane's output: entry ids, works, passages and statements by (work, OpenITI line)."""

    def __init__(self):
        self.present = (RIJAL_LANE_OUTPUT / "rijal_works.json").exists()
        self.by_line, self.statements, self.works = {}, collections.defaultdict(list), {}
        if not self.present:
            return
        works = json.loads((RIJAL_LANE_OUTPUT / "rijal_works.json").read_text(encoding="utf-8"))
        self.works = {w["work_id"].split(":", 1)[1]: w for w in works["works"]}
        for key in ("ibn_hajar_taqrib", "mizzi_tahdhib_kamal", "najashi_rijal", "tusi_rijal", "tusi_fihrist"):
            for entry in read_jsonl(RIJAL_LANE_OUTPUT / f"rijal_entries_{key}.jsonl.gz"):
                self.by_line[(key, entry["line"])] = {"entry_id": entry["entry_id"], "passage_ar": entry["passage_ar"],
                                                      "passage_sha256": entry["passage_sha256"]}
        for statement in read_jsonl(RIJAL_LANE_OUTPUT / "rijal_entry_statements.jsonl.gz"):
            self.statements[statement["entry_id"]].append(statement)


def citation_gaps(citation: dict, quoted: bool = False) -> list:
    """Missing parts of a citation (empty list = cited). A critic quoted inside another work needs no title of his own."""
    missing = []
    work = citation.get("work") or {}
    for field in ("author", "title", "tradition"):
        if not work.get(field) and not (field == "title" and (quoted or work.get("title_note"))):
            missing.append(f"work.{field}")
    if not citation.get("edition"):
        missing.append("edition")
    locator = citation.get("locator") or {}
    if not any(locator.get(k) for k in ("volume", "page", "entry", "hadith_number", "record_id", "sheet_row")):
        missing.append("locator")
    if not citation.get("passage_ar"):
        missing.append("passage_ar")
    source = citation.get("source") or {}
    if not (source.get("code") and source.get("licence")):
        missing.append("source")
    if not citation.get("text_sha256"):
        missing.append("text_sha256")
    return missing


def finalize_report(row: dict, file_sha: dict) -> dict:
    code = row["source_codes"][0]
    tradition = row["tradition_id"].split(":")[1]
    if row["kind"] == "compiler_criterion":
        row["citation"] = {"work": {"author": row["grader"], "title": row["criterion_basis_id"], "tradition": tradition},
                           "edition": None, "locator": {"record_id": row["record_id"]}, "passage_ar": None,
                           "source": {"code": code, "licence": REGISTRY_LICENCE[code]}, "text_sha256": row["arabic_sha256"]}
        row["citation_status"] = "not_yet_cited"
        row["citation_missing"] = ["criterion: the compiler's stated conditions are not stored from a reviewed edition"]
        row["perspective_id"] = f"perspective:{row['grader']}:criterion"
        return row
    if row["source_field"] == "gradings_full":
        work = {"author": row["grader"], "title": row["cited_work"], "tradition": tradition}
        locator = {"volume": row["cited_volume"], "page": row["cited_page"], "record_id": row["record_id"],
                   "cited_as": row["citation_raw"]}
        passage, span, text_sha, edition = row["grade_raw"], None, row["arabic_sha256"], REPORT_EDITIONS["THQ"]
        note = "passage is the term as Thaqalayn's gradings field records it; text_sha256 binds the report it is attached to"
    else:
        voice = L.COMPILER_VOICE[row["work"]]
        work = {"author": voice["compiler"], "title": voice["work"], "tradition": tradition}
        if row["source_field"] == "text_ar":
            locator = {"hadith_number": row.get("hadith_no"), "record_id": row["record_id"]}
            passage, span, text_sha = row["statement_ar"], [row["char_start"], row["char_end"]], row["arabic_sha256"]
            edition, note = REPORT_EDITIONS[code], "character span is into hadiths.text_ar of the report"
        else:
            locator = {"sheet_row": row["sheet_row"], "record_id": f"pure-canon:{row['pure_canon_id']}",
                       "attached_to": row["record_id"]}
            passage, span, text_sha = row["statement_ar"], None, WORKBOOK_SHA256
            edition = REPORT_EDITIONS["NMC"]
            note = "closing column L of the workbook row; attached by " + row.get("join_basis", "pure_canon_id")
    if row.get("as_quoted_by"):
        work["quoted_in"] = row["as_quoted_by"]
    citation = {"work": work, "edition": edition, "locator": locator, "passage_ar": passage, "char_span": span,
                "source": {"code": code, "licence": REGISTRY_LICENCE[code]}, "text_sha256": text_sha, "note": note}
    missing = citation_gaps(citation)
    row.update(citation=citation, citation_status="cited" if not missing else "not_yet_cited", citation_missing=missing)
    row["perspective_id"] = f"perspective:{row['grader']}:{row['basis_kind']}"
    return row


def finalize_narrator(row: dict, lane: RijalLane, file_sha: dict) -> dict:
    kind = {"companion_status_in_rijal_entry": "companion_status", "companion_status_statement": "companion_status",
            "listed_in_work": "listed_in_work"}.get(row["basis_kind"], "verdict")
    row["aspect"], row["aspect_detail"] = L.aspects_of(row.get("verdict_raw") or "", kind)
    tradition = (row["tradition_id"] or "tradition:none").split(":")[1]
    if row["basis_kind"] == "narrator_lexicon_source_not_stated":
        row["citation"] = {"work": {"author": None, "title": "narrator lexicon", "tradition": None}, "edition": None,
                           "locator": {"record_id": row["subject_ref"]}, "passage_ar": row["quote_ar"],
                           "source": {"code": "MSD", "licence": REGISTRY_LICENCE["MSD"]}, "text_sha256": file_sha["lexicon"]}
        row["citation_status"] = "not_yet_cited"
        row["citation_missing"] = ["source not stated: the lexicon does not say whose verdict this is or from which work"]
        row["perspective_id"] = "perspective:narrator_lexicon"
        return row
    if row["source_codes"] == ["HKG"]:
        book = row.get("book_named_in_statement")
        work = {"author": row["critic_ar"], "title": book, "tradition": tradition,
                "title_note": None if book else "hadith-kg does not say which of the critic's works"}
        citation = {"work": work, "edition": "hadith-kg (al-Jami' Hadith Knowledge Graph) by emadjumaah, revision 8ae7e3d5",
                    "locator": {"dataset": "hadith-kg", "dataset_version": "8ae7e3d5be284a6b32a989cd41866343fc19501c",
                                "record_id": f"aqwal:{row['citation']['row_id']}"},
                    "passage_ar": row["quote_ar"], "char_span": None,
                    "source": {"code": "HKG", "licence": REGISTRY_LICENCE["HKG"]}, "text_sha256": file_sha["hadith_kg"],
                    "text_sha256_of": "hadith-kg.db", "credit": ["the critic named", "hadith-kg, the dataset's record"]}
        missing = citation_gaps(citation)
        row.update(citation=citation, citation_status="cited" if not missing else "not_yet_cited", citation_missing=missing,
                   perspective_id=f"perspective:hadith_kg:critic:{row['citation']['alem_id']}")
        return row
    key = row["rijal_work_key"]
    lane_entry = lane.by_line.get((key, row["openiti_line"])) if lane.present else None
    meta = lane.works.get(key, {})
    edition = meta.get("edition") or {}
    quoted = bool(row.get("as_quoted_by"))
    if quoted:
        work = {"author": row["critic"] or row["critic_ar"], "title": None, "tradition": tradition,
                "quoted_in": f"{meta.get('author_name_en', 'al-Mizzi')}, {meta.get('title_en', 'Tahdhib al-Kamal')}"}
    else:
        work = {"author": meta.get("author_name_en") or row["critic"], "title": meta.get("title_en") or row["work"],
                "tradition": tradition}
    passage = row.get("verbatim_passage")
    span = None
    if lane_entry and passage:
        start = lane_entry["passage_ar"].find(passage)
        span = [start, start + len(passage)] if start >= 0 else None
    edition_text = (f"OpenITI {meta.get('openiti_uri')} ({meta.get('openiti_release')}); ed. {edition.get('editor', '')}, "
                    f"{edition.get('publisher', '')}").strip(" ,;") if meta else row["citation"]["edition_id"]
    citation = {"work": work, "edition": edition_text,
                "locator": {"entry": row["citation"]["entry"], "page": row["citation"]["page"],
                            "pages": row["citation"]["pages"], "rijal_entry_id": lane_entry["entry_id"] if lane_entry else None},
                "passage_ar": passage, "char_span": span,
                "char_span_of": "rijal lane entry passage_ar" if span else None,
                "source": {"code": "RIJ", "licence": REGISTRY_LICENCE["RIJ"]},
                "text_sha256": lane_entry["passage_sha256"] if lane_entry else file_sha[key],
                "text_sha256_of": "rijal lane entry passage_ar" if lane_entry else "OpenITI file"}
    missing = citation_gaps(citation, quoted)
    row.update(citation=citation, citation_status="cited" if not missing else "not_yet_cited", citation_missing=missing)
    if lane_entry:
        row["subject_ref"] = lane_entry["entry_id"]
        mine = {L.fold(t) for t in (row.get("verdict_terms") or [])} or {L.fold(row.get("verdict_raw") or "")}
        row["rijal_lane_statement_ids"] = sorted(
            st["statement_id"] for st in lane.statements.get(lane_entry["entry_id"], [])
            if any(L.fold(st["term_verbatim"]) == t or t.startswith(L.fold(st["term_verbatim"])) for t in mine if t))
    critic_slug = "_".join(L.fold(row["critic_ar"] or "").split())
    row["perspective_id"] = f"perspective:{key}:quoted:{critic_slug}" if quoted else f"perspective:{key}"
    return row


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    corpus = load_corpus()
    narrators = set()
    with open(NARRATORS_CSV, encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            narrators.add(row["id"])

    imami = imami_rows(corpus)
    in_text, in_text_held = in_text_statements(corpus)
    column_l, column_l_held, joins = column_l_statements(corpus, in_text)
    report_rows = sorted(imami + in_text + column_l, key=lambda r: r["id"])
    for row in report_rows:
        row["hadith_no"] = corpus[row["hadith_id"]]["hadith_no"]
    assert len({r["id"] for r in report_rows}) == len(report_rows), "duplicate assessment id"
    assert all("ثابت" != L.fold(r["grade_raw"]) for r in report_rows), "the dataset-wide ثابت label leaked"
    criteria = criterion_links(corpus)

    taqrib = taqrib_rows(narrators)
    mizzi, mizzi_held = mizzi_rows(narrators)
    imami_rijal, imami_rijal_held, imami_rijal_source = imami_rijal_rows()
    kg, kg_profile = hadith_kg_rows(narrators)
    lexicon = lexicon_rows(narrators)
    narrator_rows = sorted(taqrib + mizzi + imami_rijal + kg + lexicon, key=lambda r: r["id"])
    import rijal_sources as rs_works
    file_sha = {"hadith_kg": sha256_file(HADITH_KG), "lexicon": sha256_file(LEXICON_LABELS)}
    for key in ("ibn_hajar_taqrib", "mizzi_tahdhib_kamal", "najashi_rijal", "tusi_rijal", "tusi_fihrist"):
        file_sha[key] = sha256_file(pathlib.Path(rs_works.WORKS[key]["path"]))
    lane = RijalLane()
    report_rows = [finalize_report(r, file_sha) for r in report_rows]
    criteria = [finalize_report(r, file_sha) for r in criteria]
    narrator_rows = [finalize_narrator(r, lane, file_sha) for r in narrator_rows]
    duplicates = [k for k, v in collections.Counter(r["id"] for r in narrator_rows).items() if v > 1]
    assert not duplicates, f"duplicate narrator assessment ids: {duplicates[:10]} ({len(duplicates)})"

    counts = {
        "hadith_assessments.jsonl.gz": write_jsonl_gz("hadith_assessments.jsonl.gz", report_rows),
        "hadith_assessments_held_back.jsonl.gz": write_jsonl_gz(
            "hadith_assessments_held_back.jsonl.gz", sorted(in_text_held + column_l_held,
                                                            key=lambda r: (r.get("hadith_id") or "", r.get("pure_canon_id") or "",
                                                                           r.get("char_start") or 0, r["reason"]))),
        "pure_canon_column_l_joins.jsonl.gz": write_jsonl_gz("pure_canon_column_l_joins.jsonl.gz", joins),
        "compiler_criterion_links.jsonl.gz": write_jsonl_gz("compiler_criterion_links.jsonl.gz", criteria),
        "narrator_assessments.jsonl.gz": write_jsonl_gz("narrator_assessments.jsonl.gz", narrator_rows),
        "narrator_assessments_held_back.jsonl.gz": write_jsonl_gz(
            "narrator_assessments_held_back.jsonl.gz",
            sorted(mizzi_held + imami_rijal_held, key=lambda r: (r["subject_ref"], r["reason"], r.get("statement_ar") or r.get("clause_ar_folded")))),
    }

    report_summary = {
        "by_kind_and_grader": dict(collections.Counter(f"{r['basis_kind']} | {r['grader']}" for r in report_rows)),
        "in_text_held_by_reason": dict(collections.Counter(f"{r['work']} | {r['reason']}" for r in in_text_held)),
        "column_l_held_by_reason": dict(collections.Counter(r["reason"] for r in column_l_held)),
        "column_l_join_status": dict(collections.Counter(j["status"] for j in joins)),
        "column_l_join_chain_agreement": dict(collections.Counter(j.get("chain_agreement") for j in joins if j.get("hadith_id"))),
        "column_l_rows_corroborating_an_in_text_statement": sum(len(r["corroborated_by"]) for r in report_rows),
        "canonical_set": dict(collections.Counter(f"{r['basis_kind']} | {r['grade_canonical']}" for r in report_rows)),
        "compiler_criterion_links": dict(collections.Counter(r["criterion_basis_id"] for r in criteria)),
    }
    narrator_summary = {
        "by_basis_and_source": dict(collections.Counter(f"{r['basis_kind']} | {r['source_codes'][0]} | {r['work'] or 'hadith-kg'}"
                                                        for r in narrator_rows)),
        "linked_to_lexicon_narrator": dict(collections.Counter(f"{r['source_codes'][0]} | {r['work'] or 'hadith-kg'} | {bool(r['narrator_id'])}"
                                                               for r in narrator_rows)),
        "mizzi_by_critic_top40": dict(collections.Counter(r["critic"] or ("unmapped: " + (r["critic_ar"] or ""))
                                                          for r in mizzi).most_common(40)),
        "mizzi_critic_resolution": dict(collections.Counter(r["critic_resolution"] for r in mizzi)),
        "mizzi_held_by_reason": dict(collections.Counter(r["reason"] for r in mizzi_held)),
        "imami_rijal_source": imami_rijal_source,
        "imami_rijal_by_work": dict(collections.Counter(r["work"] for r in imami_rijal)),
        "imami_rijal_terms": dict(collections.Counter(t for r in imami_rijal for t in r["verdict_terms"])),
        "imami_rijal_held_by_reason": dict(collections.Counter(f"{r['work']} | {r['reason']}" for r in imami_rijal_held)),
        "hadith_kg": {"statements": kg_profile["statements"], "kept_by_kind": dict(kg_profile["by_kind"]),
                      "excluded": dict(kg_profile["excluded"]), "critics_top40": dict(kg_profile["by_critic"].most_common(40)),
                      "books_named_in_statements_top25": dict(kg_profile["books_named"].most_common(25)),
                      "distinct_critics_kept": len(kg_profile["by_critic"]),
                      "distinct_subjects_kept": len({r["subject_ref"] for r in kg}),
                      "kept_linked_to_lexicon_narrator": sum(1 for r in kg if r["narrator_id"])},
        "verdict_canonical": dict(collections.Counter(f"{r['basis_kind']} | {r['verdict_canonical']}" for r in narrator_rows)),
    }
    citation_summary = {
        "reports": dict(collections.Counter(f"{r['basis_kind']} | {r['citation_status']}" for r in report_rows + criteria)),
        "narrators": dict(collections.Counter(f"{r['basis_kind']} | {r['citation_status']}" for r in narrator_rows)),
        "not_yet_cited_reasons": dict(collections.Counter(m for r in report_rows + criteria + narrator_rows
                                                          for m in r.get("citation_missing", []))),
        "rijal_lane_consumed": lane.present,
        "narrator_aspects": dict(collections.Counter(f"{r['aspect']} | {'+'.join(r['aspect_detail'])}" for r in narrator_rows)),
        "rows_matching_a_rijal_lane_statement": sum(1 for r in narrator_rows if r.get("rijal_lane_statement_ids")),
        "rijal_rows_without_lane_entry": sum(1 for r in narrator_rows if r["source_codes"] == ["RIJ"]
                                             and not str(r["subject_ref"]).startswith("rijal_entry:")),
    }
    cover = coverage(corpus, report_rows, narrator_rows, narrators)
    cover["ibadi_zaydi_narrators_reached_through_hadith_kg"] = ibadi_zaydi_narrator_reach(kg)
    write_json("summary.json", {"reports": report_summary, "narrators": narrator_summary, "coverage": cover,
                                "citations": citation_summary})
    write_json("taxonomy_overstatements.json", {
        "meaning": "Loaded Imami rows whose canonical (src/lib/constants/grade-taxonomy.ts) states more than, or other than, "
                   "the grader's words; conservative_canonical is what this build proposes (null = keep the verbatim term only).",
        "rows": overstatements(imami)})
    write_json("external_exclusions.json", external_exclusion_profile())

    inputs = [HADITHS_CSV, ASSESSMENTS_CSV, NARRATORS_CSV, COLUMN_L, CRITERION_BASIS, PURE_CANON, TAQRIB_ENTRIES, RIJAL_LINKS,
              LEXICON_LABELS, EXTERNAL_LINKS, KG_NARRATORS, HADITH_KG, RIWAYAT]
    import rijal_sources as rs
    inputs += [rs.WORKS[w]["path"] for w in ("mizzi_tahdhib_kamal", "najashi_rijal", "tusi_rijal", "tusi_fihrist")]
    if lane.present:
        inputs += [RIJAL_LANE_OUTPUT / "rijal_works.json", RIJAL_LANE_OUTPUT / "rijal_entry_statements.jsonl.gz"]
        inputs += [RIJAL_LANE_OUTPUT / f"rijal_entries_{k}.jsonl.gz" for k in
                   ("ibn_hajar_taqrib", "mizzi_tahdhib_kamal", "najashi_rijal", "tusi_rijal", "tusi_fihrist")]
    code = [HERE / "assessment_logic.py", HERE / "build_assessments.py", BIOVER / "rijal_sources.py"]
    write_json("manifest.json", {
        "command": "python -B datasets/hadith-data/assessments/build_assessments.py",
        "inputs_sha256": {rel(p): sha256_file(p) for p in inputs},
        "code_sha256": {rel(p): sha256_file(p) for p in code},
        "outputs": {name: {"rows": n, "sha256": sha256_file(HERE / name)} for name, n in counts.items()},
        "review_state": "every row is candidate_only (unreviewed)",
    })
    print(json.dumps({"counts": counts, "reports": report_summary["by_kind_and_grader"],
                      "coverage_by_tradition": cover["reports_by_tradition"], "narrators": cover["narrators"]},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
