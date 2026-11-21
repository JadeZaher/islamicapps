#!/usr/bin/env python3
"""Q0: inventory of every chain-relevant local asset: size, hash, rows, columns/keys, chain-field coverage.

Read-only. Writes output/local_asset_inventory.json. Usage: python -B inventory_local_assets.py
"""

import csv
import gzip
import io
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconcile_common as rc  # noqa: E402

common = rc.common
OUTPUT = common.output_directory("chain-reconciliation/output")
HD = common.HADITH_DATA_DIR
DS = common.DATASETS_DIR


def nonblank(value) -> bool:
    if isinstance(value, (list, dict)):
        return bool(value)
    return bool(str(value or "").strip()) and str(value).strip() not in ("NA", "[]")


def profile_csv(handle, chain_fields):
    reader = csv.DictReader(handle)
    rows, filled = 0, Counter()
    for row in reader:
        rows += 1
        for field in chain_fields:
            if nonblank(row.get(field)):
                filled[field] += 1
    return {"rows": rows, "columns": reader.fieldnames, "chain_field_nonblank": dict(filled)}


def profile_jsonl(path, chain_fields):
    rows, keys, filled = 0, Counter(), Counter()
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            rows += 1
            keys.update(record.keys())
            for field in chain_fields:
                if nonblank(record.get(field)):
                    filled[field] += 1
    return {"rows": rows, "columns": sorted(keys), "chain_field_nonblank": dict(filled)}


def profile_parsed_json(path, chain_fields):
    hadiths = json.load(open(path, encoding="utf-8")).get("hadiths", [])
    keys, filled = Counter(), Counter()
    for record in hadiths:
        keys.update(record.keys())
        for field in chain_fields:
            if nonblank(record.get(field)):
                filled[field] += 1
    return {"rows": len(hadiths), "columns": sorted(keys), "chain_field_nonblank": dict(filled)}


def main() -> None:
    assets = []

    def add(path: Path, kind: str, role: str, profile):
        entry = {"path": common.relative_path(path), "bytes": path.stat().st_size, "sha256": common.sha256_file(path),
                 "kind": kind, "role": role}
        entry.update(profile() if profile else {})
        assets.append(entry)

    open_gz = lambda p: gzip.open(p, "rt", encoding="utf-8", newline="")  # noqa: E731
    open_txt = lambda p: open(p, encoding="utf-8", errors="replace", newline="")  # noqa: E731
    add(common.CORPUS_PATH, "csv.gz", "committed master (26 cols)",
        lambda: profile_csv(open_gz(common.CORPUS_PATH), ["chain_indx", "sanad", "text_ar", "page_ref", "url"]))
    for name in ("all_hadiths_clean.csv.gz", "all_hadiths_shia.csv.gz"):
        add(HD / name, "csv.gz", "compatibility projection",
            lambda n=name: profile_csv(open_gz(HD / n), ["chain_indx", "sanad"]))
    k6_rows, k6_sha = rc.read_k6_original()
    assets.append({"path": f"{common.relative_path(rc.K6_ARCHIVE)}!{rc.K6_MEMBER}", "bytes": None, "sha256": k6_sha,
                   "kind": "csv inside 7z", "role": "ORIGINAL K6 download (source-provided chain_indx)",
                   "rows": len(k6_rows), "columns": list(k6_rows[0].keys()),
                   "chain_field_nonblank": {"chain_indx": sum(1 for r in k6_rows if rc.parse_ids(r["chain_indx"]))}})
    add(rc.K6_ARCHIVE, "7z", "archive: original K6 CSV, all_rawis, Ibadi OCR pipeline", None)
    add(common.REGISTRY_PATH, "csv", "narrator lexicon (muslimscholars.info-derived ids)",
        lambda: profile_csv(open_txt(common.REGISTRY_PATH), ["teachers_inds", "students_inds", "parents",
                                                              "death_date_hijri", "grade"]))
    add(HD / "sunni_isnad.jsonl", "jsonl", "local heuristic sidecar (display sanad), K6 only",
        lambda: profile_jsonl(HD / "sunni_isnad.jsonl", ["sanad"]))
    add(rc.PURE_CANON, "jsonl", "ORIGINAL Pure Canon normalized export (separate `chain` field)",
        lambda: profile_jsonl(rc.PURE_CANON, ["chain", "text_ar"]))
    cp = HD / "archive" / "classical-pipeline"
    add(cp / "classical_sanad_parsed.jsonl", "jsonl", "local parse of Pure Canon chains (narrator names, no ids)",
        lambda: profile_jsonl(cp / "classical_sanad_parsed.jsonl", ["narrators", "chain_raw"]))
    add(cp / "classical_canon_enhanced.csv", "csv", "Pure Canon + English (chain column)",
        lambda: profile_csv(open_txt(cp / "classical_canon_enhanced.csv"), ["chain", "sanad_enhanced"]))
    snap = HD / "archive" / "unified-snapshots" / "unified_hadith_consolidated.csv.gz"
    add(snap, "csv.gz", "2026-04 snapshot (chain_indices from older resolver + K6)",
        lambda: profile_csv(open_gz(snap), ["chain_indices", "sanad_arabic", "sanad_english"]))
    for tradition, path in rc.OPENITI_PARSED.items():
        add(path, "json", f"OpenITI parse ({tradition}); sanad_detail is the local parser's output",
            lambda p=path: profile_parsed_json(p, ["sanad", "sanad_detail", "page_ref"]))
    thaq = Counter()
    for _, hadith in rc.iter_thaqalayn():
        thaq["rows"] += 1
        for field in ("thaqalaynSanad", "arabicText", "gradingsFull", "thaqalaynMatn"):
            thaq[field] += nonblank(hadith.get(field))
    total_bytes = sum(p.stat().st_size for p in rc.THAQALAYN_DIR.glob("*.json"))
    assets.append({"path": common.relative_path(rc.THAQALAYN_DIR), "bytes": total_bytes, "sha256": None,
                   "kind": "33 JSON book arrays + BookNames.json", "role": "ORIGINAL Thaqalayn V2 provider snapshot",
                   "rows": thaq.pop("rows"), "chain_field_nonblank": dict(thaq),
                   "columns": ["id", "bookId", "book", "volume", "category", "chapter", "author", "translator",
                               "englishText", "arabicText", "URL", "thaqalaynSanad", "thaqalaynMatn",
                               "majlisiGrading", "behbudiGrading", "mohseniGrading", "gradingsFull"]})
    neo = HD / "development" / "neo4j-import" / "hadith-graph-v1-final"
    add(neo / "relationships" / "includes.csv", "csv", "bundle INCLUDES (atomic exact links)", None)
    add(neo / "nodes" / "name_mentions.csv", "csv", "bundle name mentions", None)
    add(HD / "classical_narrator_gap.csv", "csv", "regen gap file", None)
    add(HD / "narrator_alias_candidates.json", "json", "machine-audited Unicode aliases", None)
    for path in sorted((DS / "sources" / "external").glob("*/*")):
        add(path, path.suffix or "text", "external download (this job)", None)
    common.write_json(OUTPUT, "local_asset_inventory.json", {
        "header": common.header_object("chain-reconciliation/inventory",
                                       "python -B datasets/hadith-data/diagnostics/chain-reconciliation/inventory_local_assets.py", {}),
        "assets": assets})
    for asset in assets:
        print(asset["path"], asset.get("rows"), asset.get("chain_field_nonblank"))


if __name__ == "__main__":
    main()
