#!/usr/bin/env python3
"""Part B: recheck lexicon life dates, generation and places against Taqrib, Tahdhib al-Kamal and hadith-kg.

Parses the rijal texts into entries, links lexicon narrators CONSERVATIVELY (exact canonical-key match, unique on
both sides), compares fields, and writes cited assertion candidates (all unreviewed), a 100-row spot-check
worksheet and a summary. Method and limits: README.md in this directory.
Usage (repo root): python -B datasets/hadith-data/diagnostics/biography-verification/verify_lexicon_against_rijal.py
"""

import csv
import hashlib
import json
import pathlib
import random
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rijal_parsing as rp  # noqa: E402
import rijal_sources as rs  # noqa: E402

common = rs.common
OUT = common.output_directory(rs.JOB)
SEED = "biography-verification-v1"
LICENCE_NOTE = ("Derived from OpenITI texts (CC BY-NC-SA 4.0: attribution, non-commercial, share-alike) and "
                "hadith-kg (CC BY 4.0, emadjumaah/hadith-kg).")


# --- source parsing ----------------------------------------------------------------------------------------------

def parse_taqrib() -> list:
    header = rs.openiti_header(rs.WORKS["ibn_hajar_taqrib"]["path"])
    records = []
    for entry in rs.read_entries("ibn_hajar_taqrib"):
        folded = rp.fold_for_phrases(entry["text"])
        head_skip = rp.headword_tokens(folded, skip_glosses=True)
        head_stop = rp.headword_tokens(folded, skip_glosses=False)
        tabaqa = rp.find_tabaqa(folded)
        verdict = rp.find_verdict(folded, len(" ".join(head_stop)))
        deaths = rp.parse_year_statements(folded, "death", tabaqa["tabaqa"], use_taqrib_century=True)
        births = rp.parse_year_statements(folded, "birth", tabaqa["tabaqa"], use_taqrib_century=True)
        keys = {rs.name_key(" ".join(head_skip)), rs.name_key(" ".join(head_stop))} - {""}
        records.append({
            "work": "ibn_hajar_taqrib", "entry_number": entry["entry_number"], "marker": entry["marker"],
            "line": entry["line"], "start_page": entry["start_page"], "pages": entry["pages"],
            "headword": " ".join(head_skip), "headword_before_gloss": " ".join(head_stop),
            "keys": sorted(keys), "tabaqa": tabaqa, "verdict": verdict, "death_statements": deaths,
            "birth_statements": births, "residence_phrases": rp.residence_phrases(folded),
            "nisba_places": sorted(rp.nisba_places(head_skip)), "passage_ar": entry["text"],
        })
    return records, header


_ATTRIBUTION = re.compile(r"(?<![ء-ي])و?قال\s+([^:،.]{2,70}?)\s*:")


def parse_mizzi() -> list:
    work = "mizzi_tahdhib_kamal"
    header = rs.openiti_header(rs.WORKS[work]["path"])
    pages = rs.PageIndex(rs.read_document(work))
    records = []
    for entry in rs.read_entries(work):
        heading = rp.mizzi_heading(entry["text"])
        folded_heading = rp.fold_for_phrases(heading)
        first_part = re.split(r"[،,]", folded_heading, maxsplit=1)[0]
        head_first = rp.headword_tokens(first_part)
        head_full = rp.headword_tokens(" ".join(re.sub(r"[،,]", " ", folded_heading).split()))
        keys = {rs.name_key(" ".join(head_first)), rs.name_key(" ".join(head_full))} - {""}
        statements = []
        for paragraph in re.finditer(r"(?:^|\n)(?:# |### \$ )([^\n]*(?:\n~~[^\n]*)*)", entry["raw"]):
            paragraph_display = rs.display_text(paragraph.group(1))
            folded = rp.fold_for_phrases(paragraph_display)
            page = pages.page_at(entry["raw_start"] + paragraph.start())
            for kind in ("death", "birth"):
                for statement in rp.parse_year_statements(folded, kind, None, use_taqrib_century=False):
                    clause_at = folded.find(statement["clause_verbatim"][:12])
                    speaker = None
                    for match in _ATTRIBUTION.finditer(folded, 0, clause_at if clause_at >= 0 else len(folded)):
                        speaker = match.group(1)
                    statement.update({"kind": kind, "page": page, "reported_by_verbatim": speaker,
                                      "paragraph_ar": paragraph_display[:1200]})
                    statements.append(statement)
        records.append({
            "work": work, "entry_number": entry["entry_number"], "line": entry["line"],
            "start_page": entry["start_page"], "pages": entry["pages"][:6], "heading": heading,
            "keys": sorted(keys), "year_statements": statements,
            "nisba_places": sorted(rp.nisba_places(head_full)), "passage_head_ar": entry["text"][:600],
        })
    return records, header


def _raw_years(raw):
    """hadith-kg year strings: '217' or a range '130 - 121' (kept as written)."""
    if raw is None:
        return None
    text = str(raw).strip()
    if re.fullmatch(r"\d+", text):
        return {"year_min": int(text), "year_max": int(text), "precision": "exact", "verbatim": text}
    match = re.fullmatch(r"(\d+)\s*-\s*(\d+)", text)
    if match:
        low, high = sorted((int(match.group(1)), int(match.group(2))))
        return {"year_min": low, "year_max": high, "precision": "range", "verbatim": text}
    return {"year_min": None, "year_max": None, "precision": "unparsed", "verbatim": text}


def load_hadith_kg() -> list:
    uri = pathlib.Path(rs.HADITH_KG).as_uri() + "?mode=ro&immutable=1"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    records = []
    for row in connection.execute("select * from rawis"):
        name, nickname = row["name"] or "", row["nickname"] or ""
        nasab_tokens = rp.fold_for_phrases((row["nasab"] or "").replace("،", " ").replace(",", " ")).split()
        keys = {rs.name_key(name), rs.name_key(nickname)} - {""}
        tokens = set()
        for key in keys:
            tokens.update(key.split())
        tokens.update(rs.name_key(" ".join(nasab_tokens)).split())
        iqama_tokens = rp.fold_for_phrases((row["iqama"] or "").replace("،", " ")).split()
        death_place_tokens = rp.fold_for_phrases(row["death_place"] or "").split()
        records.append({
            "work": "hadith_kg", "entry_number": str(row["id"]), "name": name, "nickname": nickname,
            "keys": sorted(keys), "extra_tokens": tokens, "tabaka": row["tabaka"], "rank": row["rank"],
            "death": _raw_years(row["death_year_raw"]), "birth": _raw_years(row["birth_year_raw"]),
            "iqama": row["iqama"], "death_place": row["death_place"], "nasab": row["nasab"],
            "iqama_places": sorted(rp.arabic_places(iqama_tokens)),
            "death_place_places": sorted(rp.arabic_places(death_place_tokens)),
            "nasab_places": sorted(rp.arabic_places(nasab_tokens)), "is_stub": row["is_stub"],
        })
    connection.close()
    return records


# --- linking -----------------------------------------------------------------------------------------------------

def link(lexicon: list, records: list) -> dict:
    """scholar_indx -> link result. Tier A: full key equal; tier B: exact ism-nasab chain + lexicon's other tokens
    all present in the entry. Both tiers require exactly one candidate on each side; ambiguity is recorded."""
    key_index = defaultdict(set)
    chain_index = defaultdict(set)
    record_tokens = []
    for index, record in enumerate(records):
        tokens = set(record.get("extra_tokens", ()))
        for key in record["keys"]:
            key_index[key].add(index)
            chain_index[rp.name_chain(key.split())[0]].add(index)
            tokens.update(key.split())
        record_tokens.append(tokens)
    lexicon_key_count = Counter(row["key"] for row in lexicon)
    lexicon_by_chain = defaultdict(list)
    for row in lexicon:
        row["chain"], row["rest"] = rp.name_chain(row["key"].split())
        if not row["placeholder_reason"]:
            lexicon_by_chain[row["chain"]].append(row)
    results = {}
    for row in lexicon:
        sid = row["scholar_indx"]
        if row["placeholder_reason"]:
            results[sid] = {"status": "not_linkable_placeholder", "reason": row["placeholder_reason"]}
            continue
        hits = key_index.get(row["key"], set())
        if hits:
            if len(hits) == 1 and lexicon_key_count[row["key"]] == 1:
                results[sid] = {"status": "unique", "tier": "A_full_name_key", "record": next(iter(hits))}
            else:
                results[sid] = {"status": "ambiguous", "tier": "A_full_name_key", "candidates": sorted(hits)[:20],
                                "candidate_count": len(hits), "lexicon_rows_with_key": lexicon_key_count[row["key"]]}
            continue
        if not any(token in ("بن", "بنت") for token in row["chain"].split()):
            results[sid] = {"status": "none"}
            continue
        rest = set(row["rest"])
        hits = {i for i in chain_index.get(row["chain"], ()) if rest <= record_tokens[i]}
        if not hits:
            results[sid] = {"status": "none"}
            continue
        if len(hits) == 1:
            index = next(iter(hits))
            back = [other for other in lexicon_by_chain[row["chain"]] if set(other["rest"]) <= record_tokens[index]]
            if len(back) == 1:
                results[sid] = {"status": "unique", "tier": "B_nasab_chain_plus_tokens", "record": index}
                continue
            results[sid] = {"status": "ambiguous", "tier": "B_nasab_chain_plus_tokens", "candidates": [index],
                            "candidate_count": 1, "lexicon_rows_with_key": len(back)}
            continue
        results[sid] = {"status": "ambiguous", "tier": "B_nasab_chain_plus_tokens", "candidates": sorted(hits)[:20],
                        "candidate_count": len(hits), "lexicon_rows_with_key": None}
    claimed = Counter(result["record"] for result in results.values() if result["status"] == "unique")
    for result in results.values():
        if result["status"] == "unique" and claimed[result["record"]] > 1:
            result.update({"status": "ambiguous", "candidates": [result["record"]], "candidate_count": 1,
                           "lexicon_rows_with_key": claimed[result["record"]],
                           "note": "entry_claimed_by_several_lexicon_rows"})
            result.pop("record")
    return results


# --- comparison --------------------------------------------------------------------------------------------------

def interval_distance(a_min, a_max, b_min, b_max) -> int:
    """Gap in years between two intervals with open (None) bounds; 0 when they overlap."""
    low_a = a_min if a_min is not None else -10 ** 6
    high_a = a_max if a_max is not None else 10 ** 6
    low_b = b_min if b_min is not None else -10 ** 6
    high_b = b_max if b_max is not None else 10 ** 6
    return max(0, low_b - high_a, low_a - high_b)


def year_class(distance: int, exact_both: bool, century_offset: bool) -> str:
    if distance == 0:
        return "agree" if exact_both else "consistent"
    if century_offset:
        return "differs_by_exactly_100"
    if distance <= 2:
        return "variant_1_2_years"
    if distance <= 10:
        return "differ_3_10_years"
    return "gross_conflict"


def compare_years(lexicon_values: list, source_values: list) -> dict:
    """Compare every lexicon value with every source alternative; the closest pair decides the class."""
    usable_lexicon = [v for v in lexicon_values if v.get("precision") != "zero_placeholder_suspected"
                      and (v.get("year_min") is not None or v.get("year_max") is not None)]
    usable_source = [v for v in source_values if v.get("year_min") is not None or v.get("year_max") is not None]
    century_only = [v for v in source_values if v.get("within_century")]
    yearless_source = [_brief(v) for v in source_values if v not in usable_source]
    if not usable_lexicon and not usable_source:
        return {"class": "neither" if not (lexicon_values or source_values) else "no_comparable_year",
                "source_statements_without_year": yearless_source}
    if usable_lexicon and not usable_source:
        if century_only:
            matched = any(v["within_century"][0] <= (lv["year_min"] % 100) <= v["within_century"][1]
                          for v in century_only for lv in usable_lexicon if lv.get("year_min") is not None)
            return {"class": "agree_within_century_only" if matched else "differ_within_century_only",
                    "lexicon_value": _brief(usable_lexicon[0]), "source_statements_without_year": yearless_source}
        return {"class": "lexicon_only", "lexicon_value": _brief(usable_lexicon[0]),
                "source_statements_without_year": yearless_source}
    if usable_source and not usable_lexicon:
        return {"class": "source_only", "source_alternatives": [_brief(v) for v in usable_source]}
    best = None
    for lexicon_value in usable_lexicon:
        for position, source_value in enumerate(usable_source):
            distance = interval_distance(lexicon_value.get("year_min"), lexicon_value.get("year_max"),
                                         source_value.get("year_min"), source_value.get("year_max"))
            exact_both = (lexicon_value.get("precision") == "exact" and source_value.get("precision") == "exact"
                          and lexicon_value.get("year_min") == lexicon_value.get("year_max")
                          and source_value.get("year_min") == source_value.get("year_max"))
            century_offset = (lexicon_value.get("year_min") is not None and source_value.get("year_min") is not None
                              and abs(lexicon_value["year_min"] - source_value["year_min"]) == 100)
            candidate = (distance, position, exact_both, century_offset, lexicon_value, source_value)
            if best is None or candidate[:2] < best[:2]:
                best = candidate
    distance, position, exact_both, century_offset, lexicon_value, source_value = best
    return {"class": year_class(distance, exact_both, century_offset), "difference_years": distance,
            "matched_source_alternative_index": position,
            "matched_first_source_alternative": position == 0,
            "lexicon_value": _brief(lexicon_value), "source_value": _brief(source_value),
            "source_alternatives": [_brief(v) for v in usable_source]}


def _brief(value: dict) -> dict:
    keys = ("year_min", "year_max", "precision", "flags", "qualifiers", "alternative_verbatim", "verbatim",
            "source_cell_verbatim", "reported_by_verbatim", "page")
    return {k: value[k] for k in keys if k in value and value[k] not in (None, [], "")}


def lexicon_values(candidates: list, predicate: str) -> list:
    return [c for c in candidates if c["predicate"] == predicate and c.get("calendar") == "hijri"]


def lexicon_places(candidates: list) -> tuple:
    places, unmapped, verbatim = set(), [], []
    for candidate in candidates:
        if candidate["predicate"] in ("birth_place", "death_place", "residence"):
            found, missing = rp.english_places(candidate.get("value_text"))
            places |= found
            unmapped += missing
            verbatim.append(f'{candidate["predicate"]}: {candidate.get("value_text")}')
    return places, unmapped, verbatim


def generation_class_band(tabaqa):
    if tabaqa is None:
        return None
    if tabaqa == 1:
        return "companion"
    if tabaqa <= 6:
        return "follower"
    if tabaqa <= 9:
        return "successor_of_follower"
    return "century_marker"


# --- citations and assertions ------------------------------------------------------------------------------------

def edition_record(work_key: str, header: dict) -> dict:
    work = rs.WORKS[work_key]
    return {
        "work_id": f"work:{work_key}", "edition_id": f"edition:openiti:{work['openiti_uri']}",
        "title": work["title"], "author": work["critic"], "tradition": work["tradition"],
        "openiti_uri": work["openiti_uri"], "editor": header.get("040.EdEDITOR"),
        "publisher": header.get("043.EdPUBLISHER"), "place": header.get("044.EdPLACE"),
        "year": header.get("045.EdYEAR"), "edition_number": header.get("041.EdNUMBER"),
        "locator_scheme": "entry number as printed in the OpenITI text; page = vNpM from OpenITI PageV markers",
        "licence": "CC BY-NC-SA 4.0 (OpenITI release 2025.1.9, Zenodo 10.5281/zenodo.17767721)",
        "rights_status_note": "not cleared for commercial use; see docs/rights (owner gate)",
    }


def assertion_id(*parts) -> str:
    return "bva:" + hashlib.sha256("|".join(str(p) for p in parts).encode("utf-8")).hexdigest()[:20]


def make_assertion(narrator_id, predicate, citation_id, citation, quote, link_info, value_text=None, year_min=None,
                   year_max=None, precision=None, flags=None, attributed_to=None, calendar="hijri", ordinal=0):
    return {
        "id": assertion_id(narrator_id, predicate, citation_id, ordinal, value_text, year_min, year_max),
        "narrator_id": narrator_id, "predicate": predicate, "value_text": value_text,
        "year_min": year_min, "year_max": year_max,
        "calendar": calendar if (year_min is not None or year_max is not None) else None,
        "precision": precision, "flags": flags or [], "attributed_to": attributed_to,
        "citation_id": citation_id, "citation": citation, "quote_ar": quote,
        "review_state": "candidate_only", "reviewed": False, "supersedes_assertion_id": None,
        "link": link_info,
        "basis": "rijal_entry_linked_by_exact_name_key (candidate link, not an identification)",
    }


# --- main --------------------------------------------------------------------------------------------------------

def main() -> None:
    taqrib, taqrib_header = parse_taqrib()
    mizzi, mizzi_header = parse_mizzi()
    hadith_kg = load_hadith_kg()
    lexicon = rs.load_lexicon()
    candidates = rs.load_lexicon_candidates()
    assessments = {}
    with open(rs.LEXICON_ASSESSMENTS, encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            assessments.setdefault(row["scholar_indx"], []).append(row)

    common.write_jsonl(OUT, "rijal_entries_taqrib.jsonl.gz", taqrib, gzipped=True)
    common.write_jsonl(OUT, "rijal_entries_mizzi.jsonl.gz", mizzi, gzipped=True)

    sources = {"ibn_hajar_taqrib": taqrib, "mizzi_tahdhib_kamal": mizzi, "hadith_kg": hadith_kg}
    links = {name: link(lexicon, records) for name, records in sources.items()}
    editions = {"ibn_hajar_taqrib": edition_record("ibn_hajar_taqrib", taqrib_header),
                "mizzi_tahdhib_kamal": edition_record("mizzi_tahdhib_kamal", mizzi_header),
                "hadith_kg": {"work_id": "work:hadith_kg", "edition_id": "edition:hf:emadjumaah/hadith-kg@8ae7e3d5",
                              "title": "hadith-kg (al-Jami' Hadith Knowledge Graph), table rawis",
                              "author": "emadjumaah (compiled from hadithdb, 2017)", "tradition": "sunni",
                              "locator_scheme": "rawis.id", "licence": "CC BY 4.0",
                              "rights_status_note": "derived database; rows carry no per-row source citation"}}

    link_rows, comparison_rows, assertions, verdicts, citations = [], [], [], [], {}
    stats = defaultdict(Counter)
    lexicon_by_id = {row["scholar_indx"]: row for row in lexicon}

    for row in lexicon:
        sid = row["scholar_indx"]
        group = row["generation_class"]
        for source_name, records in sources.items():
            result = links[source_name][sid]
            stats[f"link_{source_name}"][result["status"]] += 1
            stats[f"link_{source_name}_by_generation_class"][f'{group}:{result["status"]}'] += 1
            if result["status"] == "unique":
                stats[f"link_{source_name}_tier"][result["tier"]] += 1
            out = {"scholar_indx": sid, "lexicon_arabic_name": row["arabic_name"], "lexicon_key": row["key"],
                   "source": source_name, "status": result["status"], "tier": result.get("tier"),
                   "reason": result.get("reason"), "note": result.get("note")}
            if result["status"] == "unique":
                record = records[result["record"]]
                out["entry_number"] = record["entry_number"]
                out["entry_keys"] = record["keys"]
            if result["status"] == "ambiguous":
                out["candidate_entries"] = [records[i]["entry_number"] for i in result["candidates"]]
                out["candidate_count"] = result["candidate_count"]
                out["lexicon_rows_with_key"] = result.get("lexicon_rows_with_key")
            link_rows.append(out)

    # Per linked narrator comparisons
    for row in lexicon:
        sid = row["scholar_indx"]
        lexicon_candidates = candidates.get(sid, [])
        lex_death = lexicon_values(lexicon_candidates, "death_year")
        lex_birth = lexicon_values(lexicon_candidates, "birth_year")
        lex_places, lex_unmapped, lex_place_verbatim = lexicon_places(lexicon_candidates)
        has_lex_death = any(v.get("precision") != "zero_placeholder_suspected" for v in lex_death)
        mizzi_link = links["mizzi_tahdhib_kamal"][sid]
        mizzi_record = mizzi[mizzi_link["record"]] if mizzi_link["status"] == "unique" else None

        # Taqrib
        result = links["ibn_hajar_taqrib"][sid]
        if result["status"] == "unique":
            record = taqrib[result["record"]]
            link_info = {"source": "ibn_hajar_taqrib", "tier": result["tier"], "entry_number": record["entry_number"]}
            citation_id = f"cit:taqrib:{record['entry_number']}"
            citation = {"work_id": editions["ibn_hajar_taqrib"]["work_id"],
                        "edition_id": editions["ibn_hajar_taqrib"]["edition_id"],
                        "locator": f"entry {record['entry_number']}", "page": record["start_page"],
                        "pages": record["pages"], "openiti_line": record["line"]}
            citations[citation_id] = dict(citation, id=citation_id, quote_ar=record["passage_ar"],
                                          review_state="candidate_only")
            death_cmp = compare_years(lex_death, record["death_statements"])
            if mizzi_record and death_cmp["class"] in ("variant_1_2_years", "differ_3_10_years", "gross_conflict",
                                                       "differs_by_exactly_100"):
                mizzi_deaths = [s for s in mizzi_record["year_statements"] if s["kind"] == "death"
                                and "subject_may_differ" not in s["flags"]]
                mizzi_cmp = compare_years(lex_death, mizzi_deaths)
                death_cmp["lexicon_vs_mizzi_statements"] = mizzi_cmp.get("class")
                death_cmp["mizzi_statement_matching_lexicon"] = mizzi_cmp.get("source_value")
            birth_cmp = compare_years(lex_birth, record["birth_statements"])
            tabaqa = record["tabaqa"]["tabaqa"]
            if row["generation_number"] is not None and tabaqa is not None:
                gen_cls = "agree" if row["generation_number"] == tabaqa else "differ"
            elif row["generation_number"] is not None:
                gen_cls = "lexicon_only"
            elif tabaqa is not None:
                gen_cls = "source_only"
            else:
                gen_cls = "neither"
            band_cls = None
            if tabaqa is not None:
                band_cls = "agree" if generation_class_band(tabaqa) == row["generation_class"] else "differ"
            source_places = set(record["nisba_places"])
            for phrase in record["residence_phrases"]:
                source_places |= set(phrase["places"])
            place_cls = rp.compare_place_sets(lex_places, source_places)
            verdict_text = record["verdict"]["verdict_text"]
            lexicon_terms = [a.get("term_ar") for a in assessments.get(sid, []) if a.get("term_ar")]
            comparison_rows.append({
                "scholar_indx": sid, "source": "ibn_hajar_taqrib", "tier": result["tier"],
                "entry_number": record["entry_number"], "page": record["start_page"],
                "death_year": death_cmp, "birth_year": birth_cmp,
                "generation": {"class": gen_cls, "lexicon_generation_number": row["generation_number"],
                               "lexicon_marker": row["grade_marker"], "source_tabaqa": tabaqa,
                               "source_tabaqa_basis": record["tabaqa"]["basis"],
                               "source_tabaqa_verbatim": record["tabaqa"]["verbatim"],
                               "difference": (abs(row["generation_number"] - tabaqa)
                                              if gen_cls == "differ" else None),
                               "class_band": band_cls},
                "places": {"class": place_cls, "lexicon_places": sorted(lex_places),
                           "lexicon_place_cells": lex_place_verbatim, "lexicon_unmapped": lex_unmapped,
                           "source_places": sorted(source_places),
                           "source_basis": "headword nisbas plus نزيل/سكن phrases (attachment, not proof of residence)"},
                "verdict": {"lexicon_label_terms": lexicon_terms, "taqrib_verdict_folded": verdict_text,
                            "lexicon_has_label": bool(lexicon_terms), "source_has_verdict": bool(verdict_text),
                            "label_term_in_verdict": (any(rp.fold_for_phrases(t) in (verdict_text or "")
                                                          for t in lexicon_terms) if lexicon_terms and verdict_text
                                                      else None)},
                "lexicon_arabic_name": row["arabic_name"], "taqrib_headword": record["headword"],
                "passage_ar": record["passage_ar"],
            })
            stats["taqrib_death"][death_cmp["class"]] += 1
            stats[f"taqrib_death_{result['tier']}"][death_cmp["class"]] += 1
            if "lexicon_vs_mizzi_statements" in death_cmp:
                stats["taqrib_death_disagreement_vs_mizzi"][f'{death_cmp["class"]}:mizzi_{death_cmp["lexicon_vs_mizzi_statements"]}'] += 1
            if death_cmp["class"] in ("agree", "consistent", "variant_1_2_years", "differ_3_10_years", "gross_conflict",
                                      "differs_by_exactly_100"):
                source_flags = death_cmp["source_value"].get("flags") or []
                basis = ("century_inferred_literal_rule" if "century_by_author_convention" in source_flags else
                         "century_inferred_tabaqa_era" if "century_by_tabaqa_era_not_literal_rule" in source_flags else
                         "century_written")
                death_cmp["source_century_basis"] = basis
                stats["taqrib_death_century_basis"][f'{death_cmp["class"]}:{basis}'] += 1
                if not death_cmp["matched_first_source_alternative"]:
                    stats["taqrib_death_matched_later_alternative"][death_cmp["class"]] += 1
            stats["taqrib_birth"][birth_cmp["class"]] += 1
            stats["taqrib_generation"][gen_cls] += 1
            if gen_cls == "differ":
                stats["taqrib_generation_difference_size"][str(abs(row["generation_number"] - tabaqa))] += 1
            if band_cls:
                stats["taqrib_generation_class_band"][f'{row["generation_class"]}:{band_cls}'] += 1
            stats["taqrib_places"][place_cls] += 1
            stats["taqrib_gains"]["death_year" if (not has_lex_death and death_cmp["class"] == "source_only") else "_"] += 1
            stats["taqrib_gains"]["tabaqa" if gen_cls == "source_only" else "_"] += 1
            stats["taqrib_gains"]["verdict_where_lexicon_has_no_label" if (verdict_text and not lexicon_terms) else "_"] += 1
            stats["taqrib_gains"]["verdict_any" if verdict_text else "_"] += 1
            if lexicon_terms and verdict_text:
                stats["taqrib_verdict_vs_lexicon_label"]["term_found" if comparison_rows[-1]["verdict"]["label_term_in_verdict"] else "term_not_found"] += 1

            # assertions from Taqrib
            for ordinal, statement in enumerate(record["death_statements"]):
                assertions.append(make_assertion(
                    sid, "death_year", citation_id, citation, record["passage_ar"], link_info,
                    value_text=statement["alternative_verbatim"] or statement["clause_verbatim"],
                    year_min=statement["year_min"], year_max=statement["year_max"], precision=statement["precision"],
                    flags=statement["flags"] + ([f'alternative_marker:{statement["alternative_marker"]}']
                                                if statement["alternative_marker"] else []),
                    attributed_to="Ibn Hajar, Taqrib al-Tahdhib", ordinal=ordinal))
            if tabaqa is not None:
                assertions.append(make_assertion(
                    sid, "tabaqah", citation_id, citation, record["passage_ar"], link_info,
                    value_text=record["tabaqa"]["verbatim"], precision=record["tabaqa"]["basis"],
                    flags=[f'ibn_hajar_tabaqa:{tabaqa}'] + ([f'qualifier:{record["tabaqa"]["qualifier"]}']
                                                           if record["tabaqa"]["qualifier"] else []),
                    attributed_to="Ibn Hajar, Taqrib al-Tahdhib"))
            for ordinal, phrase in enumerate(record["residence_phrases"]):
                assertions.append(make_assertion(
                    sid, "residence", citation_id, citation, record["passage_ar"], link_info,
                    value_text=phrase["verbatim"], precision="place_as_written",
                    flags=[f"place_id:{p}" for p in phrase["places"]], attributed_to="Ibn Hajar, Taqrib al-Tahdhib",
                    ordinal=ordinal))
            if verdict_text:
                verdicts.append({
                    "id": assertion_id(sid, "verdict", citation_id), "narrator_id": sid,
                    "critic": "Ibn Hajar al-Asqalani (d. 852)", "work": "Taqrib al-Tahdhib", "tradition": "sunni",
                    "verdict_text_folded": verdict_text, "first_term": record["verdict"]["first_term"],
                    "citation_id": citation_id, "citation": citation, "quote_ar": record["passage_ar"],
                    "review_state": "candidate_only", "reviewed": False, "link": link_info,
                    "lexicon_label_terms": lexicon_terms,
                    "note": "span extracted heuristically from the first verdict term to the tabaqa clause; check against quote_ar",
                })

        # Mizzi (secondary): compared on death year, and statements emitted as competing candidates
        if mizzi_record:
            link_info = {"source": "mizzi_tahdhib_kamal", "tier": mizzi_link["tier"],
                         "entry_number": mizzi_record["entry_number"]}
            deaths = [s for s in mizzi_record["year_statements"] if s["kind"] == "death"]
            births = [s for s in mizzi_record["year_statements"] if s["kind"] == "birth"]
            safe_deaths = [s for s in deaths if "subject_may_differ" not in s["flags"]]
            safe_births = [s for s in births if "subject_may_differ" not in s["flags"]]
            death_cmp = compare_years(lex_death, safe_deaths)
            birth_cmp = compare_years(lex_birth, safe_births)
            place_cls = rp.compare_place_sets(lex_places, set(mizzi_record["nisba_places"]))
            comparison_rows.append({
                "scholar_indx": sid, "source": "mizzi_tahdhib_kamal", "tier": mizzi_link["tier"],
                "entry_number": mizzi_record["entry_number"], "page": mizzi_record["start_page"],
                "death_year": death_cmp, "birth_year": birth_cmp,
                "places": {"class": place_cls, "lexicon_places": sorted(lex_places),
                           "source_places": mizzi_record["nisba_places"], "source_basis": "heading nisbas"},
                "lexicon_arabic_name": row["arabic_name"], "mizzi_heading": mizzi_record["heading"],
            })
            stats["mizzi_death"][death_cmp["class"]] += 1
            stats["mizzi_birth"][birth_cmp["class"]] += 1
            stats["mizzi_places"][place_cls] += 1
            stats["mizzi_gains"]["death_year" if (not has_lex_death and death_cmp["class"] == "source_only") else "_"] += 1
            for ordinal, statement in enumerate(deaths + births):
                citation_id = f"cit:mizzi:{mizzi_record['entry_number']}:{statement['page']}"
                citation = {"work_id": editions["mizzi_tahdhib_kamal"]["work_id"],
                            "edition_id": editions["mizzi_tahdhib_kamal"]["edition_id"],
                            "locator": f"entry {mizzi_record['entry_number']}", "page": statement["page"]}
                citations.setdefault(citation_id, dict(citation, id=citation_id, quote_ar=statement["paragraph_ar"],
                                                       review_state="candidate_only"))
                assertions.append(make_assertion(
                    sid, f'{statement["kind"]}_year', citation_id, citation, statement["paragraph_ar"], link_info,
                    value_text=statement["alternative_verbatim"] or statement["clause_verbatim"],
                    year_min=statement["year_min"], year_max=statement["year_max"], precision=statement["precision"],
                    flags=statement["flags"], ordinal=ordinal,
                    attributed_to=(f'{statement["reported_by_verbatim"]} (as reported by al-Mizzi)'
                                   if statement["reported_by_verbatim"] else "al-Mizzi, Tahdhib al-Kamal (speaker not parsed)")))

        # hadith-kg (derived database)
        kg_link = links["hadith_kg"][sid]
        if kg_link["status"] == "unique":
            record = hadith_kg[kg_link["record"]]
            link_info = {"source": "hadith_kg", "tier": kg_link["tier"], "entry_number": record["entry_number"]}
            death_cmp = compare_years(lex_death, [record["death"]] if record["death"] else [])
            birth_cmp = compare_years(lex_birth, [record["birth"]] if record["birth"] else [])
            kg_places = set(record["iqama_places"]) | set(record["death_place_places"])
            place_cls = rp.compare_place_sets(lex_places, kg_places)
            kg_tabaka = record["tabaka"] if record["tabaka"] else None
            if row["generation_number"] is not None and kg_tabaka is not None:
                gen_cls = "agree" if row["generation_number"] == kg_tabaka else "differ"
            elif row["generation_number"] is not None:
                gen_cls = "lexicon_only"
            elif kg_tabaka is not None:
                gen_cls = "source_only"
            else:
                gen_cls = "neither"
            comparison_rows.append({
                "scholar_indx": sid, "source": "hadith_kg", "tier": kg_link["tier"],
                "entry_number": record["entry_number"], "death_year": death_cmp, "birth_year": birth_cmp,
                "generation": {"class": gen_cls, "lexicon_generation_number": row["generation_number"],
                               "source_tabaka": kg_tabaka,
                               "note": "hadith-kg tabaka scale runs 1-38; numbers above 12 are not Ibn Hajar's"},
                "places": {"class": place_cls, "lexicon_places": sorted(lex_places), "source_places": sorted(kg_places),
                           "source_cells": {"iqama": record["iqama"], "death_place": record["death_place"]}},
                "lexicon_arabic_name": row["arabic_name"], "kg_name": record["name"], "kg_nickname": record["nickname"],
            })
            stats["kg_death"][death_cmp["class"]] += 1
            stats["kg_birth"][birth_cmp["class"]] += 1
            stats["kg_places"][place_cls] += 1
            stats["kg_generation"][gen_cls] += 1
            stats["kg_gains"]["death_year" if (not has_lex_death and death_cmp["class"] == "source_only") else "_"] += 1
            citation_id = f"cit:hadith_kg:rawis:{record['entry_number']}"
            citation = {"work_id": "work:hadith_kg", "edition_id": editions["hadith_kg"]["edition_id"],
                        "locator": f"rawis.id={record['entry_number']}"}
            citations.setdefault(citation_id, dict(citation, id=citation_id, quote_ar=None,
                                                   review_state="candidate_only"))
            quote = json.dumps({k: record[k] for k in ("name", "nickname", "nasab", "iqama", "death_place", "tabaka",
                                                       "rank")} | {"death_year_raw": (record["death"] or {}).get("verbatim"),
                                                                   "birth_year_raw": (record["birth"] or {}).get("verbatim")},
                               ensure_ascii=False)
            for predicate, value in (("death_year", record["death"]), ("birth_year", record["birth"])):
                if value:
                    assertions.append(make_assertion(sid, predicate, citation_id, citation, quote, link_info,
                                                     value_text=value["verbatim"], year_min=value["year_min"],
                                                     year_max=value["year_max"], precision=value["precision"],
                                                     attributed_to="hadith-kg rawis (derived database)"))
            if record["iqama"]:
                assertions.append(make_assertion(sid, "residence", citation_id, citation, quote, link_info,
                                                 value_text=record["iqama"], precision="place_as_written",
                                                 flags=[f"place_id:{p}" for p in record["iqama_places"]],
                                                 attributed_to="hadith-kg rawis (derived database)"))
            if record["death_place"]:
                assertions.append(make_assertion(sid, "death_place", citation_id, citation, quote, link_info,
                                                 value_text=record["death_place"], precision="place_as_written",
                                                 flags=[f"place_id:{p}" for p in record["death_place_places"]],
                                                 attributed_to="hadith-kg rawis (derived database)"))

    # Any-source gains (union over the three sources)
    gained = Counter()
    by_narrator = defaultdict(dict)
    for comparison in comparison_rows:
        by_narrator[comparison["scholar_indx"]][comparison["source"]] = comparison
    for sid, per_source in by_narrator.items():
        lexicon_row = lexicon_by_id[sid]
        has_lex_death = any(v.get("precision") != "zero_placeholder_suspected"
                            for v in lexicon_values(candidates.get(sid, []), "death_year"))
        if not has_lex_death and any(c["death_year"]["class"] == "source_only" for c in per_source.values()):
            gained["death_year_any_source"] += 1
        if not has_lex_death and per_source.get("ibn_hajar_taqrib", {}).get("death_year", {}).get("class") == "source_only":
            gained["death_year_from_taqrib"] += 1
        if lexicon_row["generation_number"] is None and per_source.get("ibn_hajar_taqrib", {}).get("generation", {}).get("class") == "source_only":
            gained["tabaqa_number_from_taqrib"] += 1
        taqrib_cmp = per_source.get("ibn_hajar_taqrib")
        if taqrib_cmp and taqrib_cmp["verdict"]["source_has_verdict"] and not taqrib_cmp["verdict"]["lexicon_has_label"]:
            gained["attributed_verdict_where_lexicon_has_no_label"] += 1
        if taqrib_cmp and taqrib_cmp["verdict"]["source_has_verdict"]:
            gained["attributed_verdict_any"] += 1
        lex_birth_present = bool(lexicon_values(candidates.get(sid, []), "birth_year"))
        if not lex_birth_present and any(c["birth_year"]["class"] == "source_only" for c in per_source.values()):
            gained["birth_year_any_source"] += 1

    # Death-year agreement over linked narrators with both values (Taqrib unique links)
    worksheet = draw_worksheet(comparison_rows, lexicon_by_id, candidates)

    common.write_jsonl(OUT, "lexicon_rijal_links.jsonl.gz", link_rows, gzipped=True)
    common.write_jsonl(OUT, "lexicon_source_comparisons.jsonl.gz", comparison_rows, gzipped=True)
    common.write_jsonl(OUT, "cited_biographical_assertion_candidates.jsonl.gz", assertions, gzipped=True)
    common.write_jsonl(OUT, "citation_candidates.jsonl.gz", list(citations.values()), gzipped=True)
    common.write_jsonl(OUT, "taqrib_verdict_candidates.jsonl.gz", verdicts, gzipped=True)
    common.write_json(OUT, "works_and_editions.json", editions)
    write_worksheet(worksheet)

    inputs = common.input_fingerprints(rs.LEXICON, rs.LEXICON_CANDIDATES, rs.LEXICON_ASSESSMENTS,
                                       rs.WORKS["ibn_hajar_taqrib"]["path"], rs.WORKS["mizzi_tahdhib_kamal"]["path"],
                                       rs.HADITH_KG, common.HADITH_DATA_DIR / "regen_unified_csvs.py")
    parse_stats = {
        "taqrib_entries": len(taqrib),
        "taqrib_with_tabaqa": sum(1 for r in taqrib if r["tabaqa"]["tabaqa"] is not None),
        "taqrib_with_verdict": sum(1 for r in taqrib if r["verdict"]["verdict_text"]),
        "taqrib_with_death_statement": sum(1 for r in taqrib if r["death_statements"]),
        "taqrib_with_death_year": sum(1 for r in taqrib if any(s["year_min"] is not None or s["year_max"] is not None
                                                              for s in r["death_statements"])),
        "taqrib_death_statement_precision": Counter(s["precision"] for r in taqrib for s in r["death_statements"]),
        "taqrib_death_flags": Counter(f for r in taqrib for s in r["death_statements"] for f in s["flags"]),
        "mizzi_entries": len(mizzi),
        "mizzi_with_death_year_statement": sum(1 for r in mizzi if any(s["kind"] == "death" and s["year_min"] is not None
                                                                       for s in r["year_statements"])),
        "mizzi_year_statements": sum(len(r["year_statements"]) for r in mizzi),
        "hadith_kg_rawis": len(hadith_kg),
    }
    summary = {
        "header": common.header_object(rs.JOB, "python -B datasets/hadith-data/diagnostics/biography-verification/"
                                                "verify_lexicon_against_rijal.py", inputs),
        "licence": LICENCE_NOTE,
        "lexicon_rows": len(lexicon),
        "lexicon_placeholders": sum(1 for r in lexicon if r["placeholder_reason"]),
        "parse": parse_stats,
        "stats": {name: dict(counter) for name, counter in sorted(stats.items())},
        "gains": dict(gained),
        "outputs": {"assertion_candidates": len(assertions), "assertion_predicates": Counter(a["predicate"] + ":" + a["link"]["source"] for a in assertions),
                    "citations": len(citations), "verdict_candidates": len(verdicts),
                    "comparisons": len(comparison_rows), "link_rows": len(link_rows), "worksheet_rows": len(worksheet)},
    }
    common.write_json(OUT, "verification_summary.json", summary)
    print(json.dumps({"parse": parse_stats, "gains": dict(gained), "outputs": summary["outputs"]}, ensure_ascii=False,
                     default=str)[:3000])


# --- worksheet ---------------------------------------------------------------------------------------------------

STRATA = [  # (label, predicate on a Taqrib comparison, quota)
    ("death_agree", lambda c: c["source"] == "ibn_hajar_taqrib" and c["death_year"]["class"] == "agree", 20),
    ("death_consistent_range_or_bound", lambda c: c["source"] == "ibn_hajar_taqrib" and c["death_year"]["class"] == "consistent", 5),
    ("death_variant_1_2", lambda c: c["source"] == "ibn_hajar_taqrib" and c["death_year"]["class"] == "variant_1_2_years", 15),
    ("death_differ_3_10", lambda c: c["source"] == "ibn_hajar_taqrib" and c["death_year"]["class"] == "differ_3_10_years", 8),
    ("death_gross_or_century", lambda c: c["source"] == "ibn_hajar_taqrib" and c["death_year"]["class"] in ("gross_conflict", "differs_by_exactly_100"), 15),
    ("death_source_only_gain", lambda c: c["source"] == "ibn_hajar_taqrib" and c["death_year"]["class"] == "source_only", 7),
    ("generation_differ", lambda c: c["source"] == "ibn_hajar_taqrib" and c["generation"]["class"] == "differ", 10),
    ("generation_agree", lambda c: c["source"] == "ibn_hajar_taqrib" and c["generation"]["class"] == "agree", 5),
    ("places_differ", lambda c: c["source"] == "ibn_hajar_taqrib" and c["places"]["class"] == "differ", 8),
    ("places_agree", lambda c: c["source"] == "ibn_hajar_taqrib" and c["places"]["class"] == "agree", 4),
    ("tier_b_link_any", lambda c: c["source"] == "ibn_hajar_taqrib" and c["tier"].startswith("B"), 3),
]


def draw_worksheet(comparisons, lexicon_by_id, candidates) -> list:
    rng = random.Random(SEED)
    used = set()
    rows = []
    strata = list(STRATA)
    strata.append(("top_up_random_linked_death_year",
                   lambda c: c["source"] == "ibn_hajar_taqrib" and c["death_year"]["class"] not in ("neither",), None))
    for label, predicate, quota in strata:
        if quota is None:
            quota = 100 - len(rows)
        if quota <= 0:
            continue
        pool = sorted((c for c in comparisons if predicate(c) and c["scholar_indx"] not in used),
                      key=lambda c: int(c["scholar_indx"]))
        for comparison in rng.sample(pool, min(quota, len(pool))):
            used.add(comparison["scholar_indx"])
            field = ("generation" if label.startswith("generation") else
                     "places" if label.startswith("places") else "death_year")
            lexicon_row = lexicon_by_id[comparison["scholar_indx"]]
            info = comparison[field]
            if field == "death_year":
                lexicon_value = "; ".join(sorted({c["source_cell_verbatim"] for c in candidates.get(comparison["scholar_indx"], [])
                                                  if c["predicate"] == "death_year"})) or "(none)"
                source_value = json.dumps(info.get("source_alternatives") or info.get("source_value"), ensure_ascii=False)
            elif field == "generation":
                lexicon_value = lexicon_row["grade_marker"]
                source_value = f'tabaqa {info["source_tabaqa"]} ({info["source_tabaqa_verbatim"]})'
            else:
                lexicon_value = "; ".join(info.get("lexicon_place_cells") or []) or "(none)"
                source_value = ", ".join(info["source_places"])
            rows.append({
                "worksheet_row": len(rows) + 1, "stratum": label, "scholar_indx": comparison["scholar_indx"],
                "lexicon_name_ar": lexicon_row["arabic_name"], "lexicon_name_field": lexicon_row["name_field"],
                "link_tier": comparison["tier"], "field": field, "lexicon_value": lexicon_value,
                "source_work": "Ibn Hajar, Taqrib al-Tahdhib (ed. Awwama)",
                "source_locator": f'entry {comparison["entry_number"]}, {comparison["page"]}',
                "source_passage_ar": comparison["passage_ar"], "source_value_parsed": source_value,
                "machine_comparison": info["class"],
                "difference": info.get("difference_years", info.get("difference")),
                "mizzi_note": info.get("lexicon_vs_mizzi_statements") or "",
                "reviewer_same_person": "", "reviewer_source_value_read_correctly": "",
                "reviewer_lexicon_value_correct": "", "reviewer_comment": "", "reviewer_name": "", "reviewed_at": "",
            })
    return rows


def write_worksheet(rows) -> None:
    handle, _ = common.open_output(OUT, "spot_check_worksheet_100.csv")
    with handle:
        handle.write("﻿")  # Excel opens UTF-8 Arabic correctly with a BOM
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
