#!/usr/bin/env python3
"""Report crosswalk: each of our reports -> the same report in hadith-kg and in the Riwayat corpus.

Normalized Arabic only (narrator_normalize, letters only); whole text equal, else our matn (isolated with
report-correspondence/matn_isolation.py) contained in their text at word boundaries; same work required; unique on
both sides or `ambiguous` (recorded, never used). Our tradition is carried; the dataset's label is provenance only.
Writes external_report_crosswalk.jsonl.gz and its manifest here. See README.md §External sources.
Usage (repo root): python -B datasets/hadith-data/reconciled/build_external_report_crosswalk.py
"""

import hashlib
import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import external_source_io as xio  # noqa: E402
import external_source_logic as logic  # noqa: E402

io_, common, isolation = xio.io_, xio.common, xio.isolation
MAX_CANDIDATES_KEPT = 10


def digest(text: str) -> bytes:
    return hashlib.blake2b(text.encode("utf-8"), digest_size=16).digest()


class Ours:
    """Our reports in corpus order, with letters-only whole text (as a digest) and isolated matn."""

    def __init__(self, normalize, started):
        regen_extractor = common.load_extractor()
        matn_only, no_chain = isolation.load_sidecars(io_.RECONCILED_DIR)
        isolator = isolation.MatnIsolator(regen_extractor, matn_only, no_chain)
        self.rows = []
        self.whole = defaultdict(lambda: defaultdict(list))   # work -> digest -> [index]
        self.matn_key = defaultdict(lambda: defaultdict(list))  # work -> first KEY_LETTERS letters -> [index]
        self.matn = {}
        self.methods = Counter()
        for index, row in enumerate(xio.iter_corpus()):
            work = row["source_work_id"]
            text = row["text_ar"] or ""
            matn, method, reliability, _ = isolator.isolate(row)
            entry = {"record_id": row["record_id"], "tradition": row["tradition"], "source": row["source"],
                     "source_work_id": work, "hadith_no": row["hadith_no"].strip(), "url": row["url"].strip(),
                     "volume": row["volume"].strip(), "arabic_sha256": isolation.sha256_text(text),
                     "matn_method": method, "matn_reliability": reliability}
            self.rows.append(entry)
            if work in logic.WORK_MAP:
                whole, _ = logic.skeleton_words(normalize(text))
                if whole:
                    self.whole[work][digest(whole)].append(index)
                letters, _ = logic.skeleton_words(normalize(matn)) if matn else ("", [])
                if len(letters) >= logic.MATN_MIN_LETTERS:
                    self.matn[index] = letters
                    self.matn_key[work][letters[:logic.KEY_LETTERS]].append(index)
                    self.methods[f"{row['tradition']}:{method}"] += 1
                else:
                    self.methods[f"{row['tradition']}:matn_under_{logic.MATN_MIN_LETTERS}_letters"] += 1
            if index % 20000 == 0:
                xio.progress(started, f"our reports read: {index}")


def scan(dataset, rows, ours, normalize, started):
    """Stream one dataset's rows of the mapped works; return per-report hits and external metadata."""
    books = logic.external_books(dataset)
    whole_hits, matn_hits = defaultdict(list), defaultdict(list)
    meta = {}
    scanned = 0
    for external_id, book, text, info in rows:
        scanned += 1
        work = books[book]
        letters, starts = logic.skeleton_words(normalize(logic.strip_quran_labels(text)))
        if not letters:
            continue
        hit = False
        for index in ours.whole[work].get(digest(letters), ()):
            whole_hits[index].append(external_id)
            hit = True
        keys = ours.matn_key.get(work)
        if keys:
            start_set = set(starts)
            total = len(letters)
            for position in starts:
                if position + logic.KEY_LETTERS > total:
                    break
                for index in keys.get(letters[position:position + logic.KEY_LETTERS], ()):
                    needle = ours.matn[index]
                    end = position + len(needle)
                    if (end == total or end in start_set) and letters.startswith(needle, position):
                        if external_id not in matn_hits[index]:
                            matn_hits[index].append(external_id)
                        hit = True
        if hit:
            meta[external_id] = {**info, "external_book": book, "external_arabic_sha256": isolation.sha256_text(text)}
        if scanned % 20000 == 0:
            xio.progress(started, f"{dataset}: {scanned} rows scanned")
    return whole_hits, matn_hits, meta, scanned


def kg_rows(connection):
    books = sorted(logic.external_books(logic.DATASET_HADITH_KG))
    sql = (f"select id, book_id, no_inbook, page_no, nass from hadiths where book_id in ({','.join('?' * len(books))}) "
           "order by id")
    for hadith_id, book_id, no_inbook, page_no, nass in connection.execute(sql, books):
        yield str(hadith_id), book_id, nass, {"external_locator": {"book_id": book_id, "no_inbook": no_inbook,
                                                                    "page_no": page_no}}


def riwayat_rows(connection):
    books = sorted(logic.external_books(logic.DATASET_RIWAYAT))
    sql = (f"select id, book, number, source_ids, tradition, text from hadith where book in "
           f"({','.join('?' * len(books))}) order by id")
    for hadith_id, book, number, source_ids, tradition, text in connection.execute(sql, books):
        yield hadith_id, book, text, {"external_locator": {"number": number, "source_ids": source_ids},
                                      "external_tradition_label": tradition}


def locator_tail_agrees(our_url: str, number: str) -> bool:
    """Riwayat's Thaqalayn number and our Thaqalayn URL end in the same chapter and hadith numbers."""
    ours = [part for part in (our_url or "").rstrip("/").split("/") if part.isdigit()]
    theirs = (number or "").split(":")
    return len(ours) >= 2 and len(theirs) >= 3 and ours[-2:] == theirs[-2:]


def main() -> None:
    started = time.time()
    regen = common.load_regen()
    normalize = regen.narrator_normalize
    ours = Ours(normalize, started)
    xio.progress(started, f"our reports: {len(ours.rows)}; matn keys built")

    results = {}
    scanned = {}
    for dataset, connect_path, reader in ((logic.DATASET_HADITH_KG, xio.HADITH_KG, kg_rows),
                                          (logic.DATASET_RIWAYAT, xio.RIWAYAT, riwayat_rows)):
        connection = xio.connect(connect_path)
        try:
            whole_hits, matn_hits, meta, scanned[dataset] = scan(dataset, reader(connection), ours, normalize, started)
        finally:
            connection.close()
        selected = {index: logic.select_match(whole_hits.get(index, ()), matn_hits.get(index, ()))
                    for index in set(whole_hits) | set(matn_hits)}
        selected = {index: value for index, value in selected.items() if value[0]}
        results[dataset] = (logic.enforce_reverse_uniqueness(selected), meta)
        xio.progress(started, f"{dataset}: {len(selected)} of our reports have a same-work candidate")

    rows = []
    counts = {dataset: defaultdict(Counter) for dataset in logic.DATASETS}
    kg_used = {}
    for dataset in logic.DATASETS:
        decided, meta = results[dataset]
        for index, (match_class, candidates, reason) in decided.items():
            ours_row = ours.rows[index]
            used = match_class in (logic.MATCH_WHOLE, logic.MATCH_MATN)
            record = {
                "record_id": ours_row["record_id"], "hadith_id": f"hadith:{ours_row['record_id']}",
                "tradition": ours_row["tradition"], "source": ours_row["source"],
                "source_work_id": ours_row["source_work_id"], "arabic_sha256": ours_row["arabic_sha256"],
                "matn_method": ours_row["matn_method"], "matn_reliability": ours_row["matn_reliability"],
                "dataset": dataset, "match_class": match_class, "used": used, "ambiguity_reason": reason or None,
                "candidate_count": len(candidates), "candidates": candidates[:MAX_CANDIDATES_KEPT],
                "external_report_id": candidates[0] if used else None,
                "review_state": "unreviewed",
            }
            if used:
                info = meta[candidates[0]]
                record.update({key: info.get(key) for key in ("external_book", "external_locator",
                                                              "external_arabic_sha256", "external_tradition_label")})
                if dataset == logic.DATASET_RIWAYAT and ours_row["tradition"] == "Imami":
                    record["thaqalayn_locator_tail_agrees"] = locator_tail_agrees(
                        ours_row["url"], info["external_locator"]["number"])
                if dataset == logic.DATASET_HADITH_KG:
                    kg_used[ours_row["record_id"]] = candidates[0]
            rows.append(record)
            tradition, work = ours_row["tradition"], ours_row["source_work_id"]
            counts[dataset]["by_tradition_class"][f"{tradition}:{match_class}"] += 1
            counts[dataset]["by_work_class"][f"{tradition}|{work}:{match_class}"] += 1
            if reason:
                counts[dataset]["ambiguity_reason"][reason] += 1

    # Cross-checks that do not feed the match: Riwayat's own kg id, Riwayat's Thaqalayn locator.
    checks = Counter()
    for record in rows:
        if record["dataset"] != logic.DATASET_RIWAYAT or not record["used"]:
            continue
        if record["tradition"] == "Imami":
            checks[f"imami_thaqalayn_locator_tail_{'agrees' if record['thaqalayn_locator_tail_agrees'] else 'differs'}"] += 1
        kg_id = json.loads(record["external_locator"]["source_ids"] or "{}").get("kg")
        mine = kg_used.get(record["record_id"])
        if kg_id is not None and mine is not None:
            checks["riwayat_kg_id_equals_our_kg_match" if str(kg_id) == mine else "riwayat_kg_id_differs_from_our_kg_match"] += 1

    rows.sort(key=lambda r: (r["record_id"], r["dataset"]))
    output = io_.write_jsonl_gz(xio.CROSSWALK, rows)
    totals = Counter(row["tradition"] for row in ours.rows)
    work_totals = Counter(f"{row['tradition']}|{row['source_work_id']}" for row in ours.rows)
    rates = {}
    for dataset in logic.DATASETS:
        by_class = counts[dataset]["by_tradition_class"]
        rates[dataset] = {tradition: {
            "reports": total,
            **{cls: by_class.get(f"{tradition}:{cls}", 0) for cls in (logic.MATCH_WHOLE, logic.MATCH_MATN,
                                                                       logic.MATCH_AMBIGUOUS)},
            "used_percent": round(100 * (by_class.get(f"{tradition}:{logic.MATCH_WHOLE}", 0)
                                         + by_class.get(f"{tradition}:{logic.MATCH_MATN}", 0)) / total, 1)}
            for tradition, total in sorted(totals.items())}
    by_work = {dataset: {} for dataset in logic.DATASETS}
    for dataset in logic.DATASETS:
        for key, total in sorted(work_totals.items()):
            row_counts = {cls: counts[dataset]["by_work_class"].get(f"{key}:{cls}", 0)
                          for cls in (logic.MATCH_WHOLE, logic.MATCH_MATN, logic.MATCH_AMBIGUOUS)}
            used = row_counts[logic.MATCH_WHOLE] + row_counts[logic.MATCH_MATN]
            by_work[dataset][key] = {"reports": total, **row_counts, "used_percent": round(100 * used / total, 1),
                                     "work_has_counterpart": key.split("|", 1)[1] in logic.WORK_MAP
                                     and dataset in logic.WORK_MAP[key.split("|", 1)[1]]}
    here = Path(__file__).resolve()
    io_.write_manifest("external_report_crosswalk.manifest.json", {
        "artifact": "external_report_crosswalk", "status": "sidecar_unreviewed_not_a_release_input",
        "meaning": "Our report -> the same report in hadith-kg and in Riwayat by normalized Arabic; a candidate "
                   "correspondence, not an identity. `ambiguous` rows are recorded and never used.",
        "command": "python -B datasets/hadith-data/reconciled/build_external_report_crosswalk.py",
        "licence": xio.LICENCE,
        "inputs_sha256": common.input_fingerprints(
            xio.CORPUS, xio.WORK_REGISTRY, xio.HADITH_KG, xio.RIWAYAT,
            io_.RECONCILED_DIR / "pure_canon_chain.jsonl.gz", io_.RECONCILED_DIR / "no_chain_in_source.jsonl.gz"),
        "code_sha256": io_.code_fingerprints(
            here, io_.RECONCILED_DIR / "external_source_logic.py", io_.RECONCILED_DIR / "external_source_io.py",
            io_.RECONCILED_DIR / "sidecar_io.py", common.DIAGNOSTICS_DIR / "report-correspondence" / "matn_isolation.py",
            common.HADITH_DATA_DIR / "regen_unified_csvs.py", common.HADITH_DATA_DIR / "extract_isnad_unified.py"),
        "method": {
            "normalization": "regen_unified_csvs.narrator_normalize (NFKC, format controls, vocalization, tatweel, "
                             "alef and ya folds), then Arabic base letters only; on the external side hadith-kg's "
                             "inline verse labels (`سورة <name> آية <n>`) are removed first (they are editorial "
                             "insertions; Riwayat's Sunni texts inherit them)",
            "classes": {logic.MATCH_WHOLE: "letters-only whole text equal",
                        logic.MATCH_MATN: f"our isolated matn (>= {logic.MATN_MIN_LETTERS} letters) is a substring of "
                                          "their letters-only text starting and ending at word boundaries",
                        logic.MATCH_AMBIGUOUS: "several same-work candidates, or the external report is the pick of "
                                               "several of our reports; recorded, not used"},
            "same_work": "only external books mapped to our source_work_id in external_source_logic.WORK_MAP are read",
            "tradition": "our tradition is carried; Riwayat's label is kept as external_tradition_label (it labels "
                         "Musnad Zayd and Musnad al-Rabi' as sunni)",
        },
        "external_rows_scanned": scanned,
        "our_matn_methods": dict(sorted(ours.methods.items())),
        "output": output,
        "rates_by_tradition": rates,
        "rates_by_work": by_work,
        "ambiguity_reasons": {d: dict(counts[d]["ambiguity_reason"]) for d in logic.DATASETS},
        "cross_checks_not_used_for_matching": dict(sorted(checks.items())),
    })
    xio.progress(started, json.dumps(rates, ensure_ascii=False))


if __name__ == "__main__":
    main()
