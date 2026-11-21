#!/usr/bin/env python3
"""Part A: profile hadith-kg and the Riwayat corpus and measure their joins to our narrators and reports.

Reads both SQLite files read-only (`mode=ro&immutable=1`), never executes anything from them. Narrators: shared
external ids (none exist), else exact canonical name key plus overlapping death year, unique on both sides. Reports:
exact letters-only text equality, and their matn contained in our text (hash-verified). README.md has the method.
Usage (repo root): python -B datasets/hadith-data/diagnostics/biography-verification/profile_external_datasets.py
"""

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
from verify_lexicon_against_rijal import interval_distance, _raw_years  # noqa: E402

common = rs.common
OUT = common.output_directory(rs.JOB)
SEED = "biography-verification-profile-v1"
MATN_MIN_LETTERS = 40
KEY_LETTERS = 30
MAX_BUCKET = 400  # a suffix key shared by more matns than this is not distinctive and is skipped (counted)

# our display label -> folded Arabic/slug fragment of the same work in the external dataset (quality check only)
SAME_WORK = {
    "Musnad Ahmad": ("مسند احمد",), "Sahih Muslim": ("صحيح مسلم",), "Sahih Bukhari": ("صحيح البخاري",),
    "Sunan an-Nasa'i": ("النساي", "النسائ"), "Sunan Abi Da'ud": ("ابي داود",), "Sunan Ibn Majah": ("ابن ماج",),
    "Jami' al-Tirmidhi": ("الترمذي",), "Sunan al-Darimi": ("الدارمي",), "Musnad al-Shafi'i": ("الشافعي",),
    "Muwatta' Malik": ("موطا",), "Al-Kāfi": ("al-kafi",), "Man Lā Yaḥḍuruh al-Faqīh": ("man-la-yahduruhu",),
    "Al-Amālī": ("al-amali",), "Al-Khiṣāl": ("al-khisal",), "Kitāb al-Ghayba": ("kitab-al-ghayba",),
    "Thawāb al-Aʿmāl wa ʿiqāb al-Aʿmāl": ("thawab-al-amal",), "ʿUyūn akhbār al-Riḍā": ("uyun-akhbar",),
    "Maʿānī al-ʾAkhbār": ("maani-al-akhbar",), "Kāmil al-Ziyārāt": ("kamil-al-ziyarat",),
    "Al-Tawḥīd": ("al-tawhid",), "Muʿjam al-Aḥādīth al-Muʿtabara": ("mujam-al-ahadith",),
    "Kitāb al-Zuhd": ("kitab-al-zuhd",), "Kitāb al-Ḍuʿafāʾ": ("kitab-al-duafa",), "Kitāb al-Muʾmin": ("kitab-al-mumin",),
    "Ṣifāt al-Shīʿa": ("sifat-al-shia",), "Faḍaʾil al-Shīʿa": ("fadail-al-shia",), "Nahj al-Balāgha": ("nahj-al-balagha",),
    "al-Jami al-Sahih (Musnad al-Rabi ibn Habib)": ("الربيع بن حبيب",), "Musnad al-Imam Zayd ibn Ali": ("مسند زيد",),
}


def connect(path: Path):
    connection = sqlite3.connect(pathlib.Path(path).as_uri() + "?mode=ro&immutable=1", uri=True)
    return connection


def skeleton(text: str) -> tuple:
    """(letters-only canonical text, word end offsets). narrator_normalize = NFKC (expands ﷺ), Cf removal,
    vocalization/tatweel removal, alef and ya folds; then only Arabic letters are kept."""
    words = re.findall(r"[ء-ي]+", rs.regen().narrator_normalize(text or ""))
    ends, total = [], 0
    for word in words:
        total += len(word)
        ends.append(total)
    return "".join(words), ends


# --- profiles ----------------------------------------------------------------------------------------------------

def table_profile(connection) -> dict:
    out = {}
    for name, kind, sql in connection.execute(
            "select name, type, sql from sqlite_master where type in ('table','view') order by name"):
        if name.startswith("sqlite_"):
            continue
        columns = [row[1] for row in connection.execute(f'pragma table_info("{name}")')]
        out[name] = {"type": kind, "rows": connection.execute(f'select count(*) from "{name}"').fetchone()[0],
                     "columns": columns}
    return out


def profile_hadith_kg(connection) -> dict:
    q = lambda sql, *a: connection.execute(sql, a).fetchall()  # noqa: E731
    return {
        "tables": table_profile(connection),
        "meta": dict(q("select key, value from meta")),
        "identifiers": {
            "narrator": "rawis.id (integer, dataset-internal; no external id column)",
            "report": "hadiths.id (integer); human locator books.id + hadiths.no_inbook (+ page_no)",
            "chain": "sanads.id; ordered narrators in sanad_rawis (pos 0 = book author, ascending to the companion)",
            "mention": "hadith_rawis (hadith_id, seq) with character offsets into hadiths.nass",
        },
        "rawis_fields_filled": dict(zip(
            ("rows", "death_year", "death_year_raw", "birth_year_raw", "iqama", "death_place", "stubs"),
            q("select count(*), count(death_year), count(death_year_raw), count(birth_year_raw), count(iqama), "
              "count(death_place), sum(is_stub) from rawis")[0])),
        "rawis_by_tabaka": q("select tabaka, count(*), count(death_year) from rawis group by tabaka order by tabaka"),
        "rawis_rank_top": q("select rank, count(*) from rawis group by rank order by 2 desc limit 15"),
        "books_by_category": q("select tasnif, count(*), sum(hadith_qty) from books group by tasnif order by 3 desc"),
        "hadiths_with_matn_span": q("select count(*) from hadiths where matn_start is not null and matn_end is not null")[0][0],
        "tradition_note": "books carry no tradition field; nearly all are Sunni works, but book 55 is Musnad Zayd "
                          "(Zaydi) and book 56 Musnad al-Rabi' b. Habib (Ibadi); no Imami collection",
        "non_sunni_books": q("select id, name, author_name, hadith_qty from books where id in (55, 56)"),
    }


def profile_riwayat(connection) -> dict:
    q = lambda sql, *a: connection.execute(sql, a).fetchall()  # noqa: E731
    shia_mentions = q("""select count(*), count(narrator_id), count(distinct narrator_id)
                         from chain_mention m join hadith h on h.id = m.hadith_id where h.tradition = 'shia'""")[0]
    return {
        "tables": table_profile(connection),
        "identifiers": {
            "narrator": "narrator.id ('N0000123'); crosswalk narrator_source_id(source, source_id)",
            "report": "hadith.id; upstream ids in hadith.source_ids JSON (kg = hadith-kg hadiths.id, thaqalayn = T:<book>:...)",
            "chain": "chain_mention rows per (hadith_id, chain_no) ordered by pos; reference_chain for MIDS/SemanticHadith",
        },
        "crosswalk_sources": q("select source, count(*), count(distinct narrator_id) from narrator_source_id group by 1 order by 2 desc"),
        "narrators_by_tradition": q("select tradition, count(*), count(death_year), count(tabaqa), count(city) from narrator group by 1"),
        "hadith_by_tradition_tier": q("select tradition, chain_tier, count(*) from hadith group by 1, 2"),
        "shia_books": q("select book, count(*) from hadith where tradition = 'shia' group by 1 order by 2 desc"),
        "shia_chain_mentions": {"mentions": shia_mentions[0], "with_asserted_id": shia_mentions[1],
                                "distinct_ids": shia_mentions[2]},
        "id_method_top": q("select id_method, count(*) from chain_mention group by 1 order by 2 desc limit 20"),
        "muslimscholars_namespace_present": False,
    }


# --- report joins ------------------------------------------------------------------------------------------------

def build_report_index(rows):
    """rows: (their_id, book, full_text, matn_text). Returns full-text hash index and matn suffix index."""
    full_index = defaultdict(list)
    suffix_index = defaultdict(list)
    counts = Counter()
    for their_id, book, full_text, matn_text in rows:
        full, _ = skeleton(full_text)
        if full:
            full_index[hash(full)].append((their_id, book))
        matn, _ = skeleton(matn_text) if matn_text else ("", [])
        if len(matn) >= MATN_MIN_LETTERS:
            suffix_index[matn[-KEY_LETTERS:]].append((len(matn), hash(matn), their_id, book))
            counts["matn_indexed"] += 1
        else:
            counts["matn_too_short_or_missing"] += 1
        counts["rows"] += 1
    return full_index, suffix_index, counts


def join_reports(our_rows, full_index, suffix_index, label: str) -> tuple:
    stats = defaultdict(Counter)
    samples = []
    skipped_buckets = Counter()
    per_row = []
    for row in our_rows:
        tradition = row["tradition"]
        text, ends = skeleton(row["text_ar"])
        full_hits = full_index.get(hash(text), []) if text else []
        matn_hits = []
        if text:
            seen = set()
            for end in ends:
                if end < KEY_LETTERS:
                    continue
                bucket = suffix_index.get(text[end - KEY_LETTERS:end])
                if not bucket:
                    continue
                if len(bucket) > MAX_BUCKET:
                    skipped_buckets[label] += 1
                    continue
                for length, digest, their_id, book in bucket:
                    start = end - length
                    if start >= 0 and their_id not in seen and hash(text[start:end]) == digest:
                        seen.add(their_id)
                        matn_hits.append((their_id, book))
        level = "full_text_equal" if full_hits else ("matn_contained" if matn_hits else "none")
        stats["by_tradition"][f"{tradition}:{level}"] += 1
        stats["by_source"][f'{tradition}|{row["source"]}:{level}'] += 1
        hits = full_hits or matn_hits
        patterns = SAME_WORK.get(row["source"])
        if hits and patterns:
            same = any(any(p in rp.fold_for_phrases(str(book)) for p in patterns) for _, book in hits)
            stats["same_work_among_matched"][f"{tradition}:{'same_work' if same else 'other_work_only'}"] += 1
        if hits:
            for book in sorted({str(b) for _, b in hits})[:3]:
                stats["matched_external_books_top"][f"{tradition}|{book}"] += 1
            stats["candidate_count"][f"{tradition}:{min(len(hits), 10)}{'+' if len(hits) >= 10 else ''}"] += 1
            per_row.append({"line": row["line"], "id": row["id"], "source": row["source"], "tradition": tradition,
                            "level": level, "candidates": [str(h[0]) for h in hits[:10]], "candidate_count": len(hits)})
            samples.append((row, level, hits))
    return stats, samples, per_row, skipped_buckets


def our_reports():
    rows = []
    for line, row in common.iter_corpus_rows():
        rows.append({"line": line, "id": row["id"], "source": row["source"].strip(), "tradition": row["tradition"],
                     "text_ar": row["text_ar"]})
    return rows


# --- narrator joins ----------------------------------------------------------------------------------------------

def narrator_join(lexicon, lexicon_years, external) -> dict:
    """external: list of (ext_id, keys, (year_min, year_max) | None). Name + overlapping death year, unique both ways."""
    by_key = defaultdict(list)
    for ext_id, keys, years in external:
        for key in keys:
            by_key[key].append((ext_id, years))
    forward = {}
    name_only = Counter()
    for row in lexicon:
        if row["placeholder_reason"]:
            continue
        candidates = {ext_id: years for ext_id, years in by_key.get(row["key"], [])}
        name_only["unique" if len(candidates) == 1 else "ambiguous" if candidates else "none"] += 1
        years = lexicon_years.get(row["scholar_indx"])
        if not years:
            continue
        hits = [ext_id for ext_id, ext_years in candidates.items() if ext_years and any(
            interval_distance(y["year_min"], y["year_max"], ext_years[0], ext_years[1]) == 0 for y in years)]
        forward[row["scholar_indx"]] = hits
    claimed = Counter(hits[0] for hits in forward.values() if len(hits) == 1)
    result = {}
    for sid, hits in forward.items():
        if len(hits) == 1 and claimed[hits[0]] == 1:
            result[sid] = ("unique", hits[0])
        elif hits:
            result[sid] = ("ambiguous", hits[:5])
        else:
            result[sid] = ("none", None)
    return result, name_only


def main() -> None:
    random.seed(SEED)
    kg = connect(rs.HADITH_KG)
    riwayat = connect(rs.RIWAYAT)
    summary = {"hadith_kg": profile_hadith_kg(kg), "riwayat": profile_riwayat(riwayat)}

    # Narrators -------------------------------------------------------------------------------------------------
    lexicon = rs.load_lexicon()
    candidates = rs.load_lexicon_candidates()
    lexicon_years = {}
    for sid, rows in candidates.items():
        years = [r for r in rows if r["predicate"] == "death_year" and r.get("calendar") == "hijri"
                 and r.get("precision") != "zero_placeholder_suspected"
                 and (r.get("year_min") is not None or r.get("year_max") is not None)]
        if years:
            lexicon_years[sid] = years
    kg_external = []
    for rawi_id, name, nickname, death_raw in kg.execute("select id, name, nickname, death_year_raw from rawis"):
        years = _raw_years(death_raw)
        kg_external.append((rawi_id, {rs.name_key(name), rs.name_key(nickname)} - {""},
                            (years["year_min"], years["year_max"]) if years and years["year_min"] is not None else None))
    riwayat_forms = defaultdict(set)
    for narrator_id, form in riwayat.execute(
            "select narrator_id, form from narrator_name where type in ('full', 'popular')"):
        riwayat_forms[narrator_id].add(form)
    riwayat_external = []
    riwayat_kg = {}
    for narrator_id, source_id in riwayat.execute("select narrator_id, source_id from narrator_source_id where source = 'kg'"):
        riwayat_kg.setdefault(narrator_id, set()).add(int(source_id))
    for narrator_id, std_name, tradition, death_year in riwayat.execute(
            "select id, std_name, tradition, death_year from narrator where tradition != 'shia'"):
        keys = {rs.name_key(form) for form in riwayat_forms.get(narrator_id, set()) | {std_name or ""}} - {""}
        riwayat_external.append((narrator_id, keys, (death_year, death_year) if death_year is not None else None))
    kg_join, kg_name_only = narrator_join(lexicon, lexicon_years, kg_external)
    riw_join, riw_name_only = narrator_join(lexicon, lexicon_years, riwayat_external)
    by_class = defaultdict(Counter)
    lexicon_by_id = {row["scholar_indx"]: row for row in lexicon}
    bridge = Counter()
    narrator_rows = []
    for sid in lexicon_years:
        row = lexicon_by_id[sid]
        if row["placeholder_reason"]:
            by_class["placeholder_not_joined"][row["generation_class"]] += 1
            continue
        kg_status = kg_join.get(sid, ("none", None))
        riw_status = riw_join.get(sid, ("none", None))
        by_class["hadith_kg"][f'{row["generation_class"]}:{kg_status[0]}'] += 1
        by_class["riwayat"][f'{row["generation_class"]}:{riw_status[0]}'] += 1
        if kg_status[0] == "unique" and riw_status[0] == "unique":
            crosswalk = riwayat_kg.get(riw_status[1], set())
            bridge["riwayat_kg_crosswalk_agrees" if kg_status[1] in crosswalk else
                   "riwayat_kg_crosswalk_differs" if crosswalk else "riwayat_has_no_kg_crosswalk"] += 1
        narrator_rows.append({"scholar_indx": sid, "lexicon_arabic_name": row["arabic_name"],
                              "lexicon_death_cells": sorted({y["source_cell_verbatim"] for y in lexicon_years[sid]}),
                              "hadith_kg": {"status": kg_status[0], "rawi_id": kg_status[1]},
                              "riwayat": {"status": riw_status[0], "narrator_id": riw_status[1]},
                              "basis": "exact canonical name key + overlapping death year (candidate, unreviewed)"})
    narrator_sample = []
    unique_both = [r for r in narrator_rows if r["hadith_kg"]["status"] == "unique"]
    for record in random.sample(unique_both, min(20, len(unique_both))):
        kg_row = kg.execute("select id, name, nickname, death_year_raw, tabaka, rank from rawis where id = ?",
                            (record["hadith_kg"]["rawi_id"],)).fetchone()
        narrator_sample.append({"scholar_indx": record["scholar_indx"], "lexicon": record["lexicon_arabic_name"],
                                "lexicon_death": record["lexicon_death_cells"], "hadith_kg": kg_row,
                                "riwayat": record["riwayat"]})
    summary["narrator_join"] = {
        "shared_external_ids": "none: hadith-kg has only internal rawis.id; Riwayat crosswalks itq, chains, kg, sh, "
                               "thq, mids; neither carries muslimscholars.info (the origin of scholar_indx)",
        "lexicon_rows_with_usable_hijri_death_year": len(lexicon_years),
        "name_only_unique_both_sides_context": {"hadith_kg": dict(kg_name_only), "riwayat": dict(riw_name_only)},
        "name_plus_death_year": {k: dict(v) for k, v in by_class.items()},
        "riwayat_kg_bridge_consistency_on_doubly_joined": dict(bridge),
        "sample": narrator_sample,
    }
    common.write_jsonl(OUT, "narrator_join_name_plus_death_year.jsonl.gz", narrator_rows, gzipped=True)

    # Reports ---------------------------------------------------------------------------------------------------
    ours = our_reports()
    kg_rows = ((hid, book, nass, nass[ms:me] if ms is not None and me is not None else None)
               for hid, book, nass, ms, me in kg.execute(
                   "select h.id, b.name, h.nass, h.matn_start, h.matn_end from hadiths h join books b on b.id = h.book_id"))
    full_index, suffix_index, kg_index_counts = build_report_index(kg_rows)
    kg_stats, kg_samples, kg_per_row, kg_skipped = join_reports(ours, full_index, suffix_index, "hadith_kg")
    del full_index, suffix_index
    riw_rows = ((hid, book, text, text[ms:me] if ms is not None and me is not None else None)
                for hid, book, text, ms, me in riwayat.execute("select id, book, text, matn_start, matn_end from hadith"))
    full_index, suffix_index, riw_index_counts = build_report_index(riw_rows)
    riw_stats, riw_samples, riw_per_row, riw_skipped = join_reports(ours, full_index, suffix_index, "riwayat")
    del full_index, suffix_index

    def sample(samples, label):
        out = []
        by_tradition = defaultdict(list)
        for item in samples:
            by_tradition[item[0]["tradition"]].append(item)
        for tradition, items in sorted(by_tradition.items()):
            for row, level, hits in random.sample(items, min(6, len(items))):
                out.append({"tradition": tradition, "our_source": row["source"], "our_line": row["line"],
                            "level": level, "their_books": sorted({str(b) for _, b in hits})[:5],
                            "candidate_count": len(hits), "our_text_head": row["text_ar"][:160]})
        return out

    summary["report_join"] = {
        "method": f"letters-only canonical text; full equality, or their matn (>= {MATN_MIN_LETTERS} letters) "
                  f"contained in our text_ar, located by its last {KEY_LETTERS} letters and verified by hash",
        "our_rows": len(ours), "our_rows_by_tradition": dict(Counter(r["tradition"] for r in ours)),
        "hadith_kg": {"index": dict(kg_index_counts), "skipped_nondistinctive_lookups": kg_skipped["hadith_kg"],
                      **{k: dict(v) for k, v in kg_stats.items() if k != "by_source"},
                      "by_source": dict(kg_stats["by_source"]), "sample": sample(kg_samples, "hadith_kg")},
        "riwayat": {"index": dict(riw_index_counts), "skipped_nondistinctive_lookups": riw_skipped["riwayat"],
                    **{k: dict(v) for k, v in riw_stats.items() if k != "by_source"},
                    "by_source": dict(riw_stats["by_source"]), "sample": sample(riw_samples, "riwayat")},
    }
    common.write_jsonl(OUT, "report_join_hadith_kg.jsonl.gz", kg_per_row, gzipped=True)
    common.write_jsonl(OUT, "report_join_riwayat.jsonl.gz", riw_per_row, gzipped=True)

    inputs = common.input_fingerprints(rs.LEXICON, rs.LEXICON_CANDIDATES, common.CORPUS_PATH, rs.HADITH_KG, rs.RIWAYAT,
                                       common.HADITH_DATA_DIR / "regen_unified_csvs.py")
    summary["header"] = common.header_object(rs.JOB, "python -B datasets/hadith-data/diagnostics/biography-verification/"
                                                     "profile_external_datasets.py", inputs)
    summary["licence"] = ("hadith-kg CC BY 4.0 (emadjumaah/hadith-kg); Riwayat corpus CC0 for its own layer, texts "
                          "inherit their sources (hadith-kg CC BY 4.0, Thaqalayn and others)")
    common.write_json(OUT, "external_dataset_profile.json", summary)
    kg.close()
    riwayat.close()
    print(json.dumps({"narrator": summary["narrator_join"]["name_plus_death_year"],
                      "bridge": summary["narrator_join"]["riwayat_kg_bridge_consistency_on_doubly_joined"],
                      "kg_reports": summary["report_join"]["hadith_kg"]["by_tradition"],
                      "riw_reports": summary["report_join"]["riwayat"]["by_tradition"]}, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
