#!/usr/bin/env python3
"""Pure Canon chain sidecar plus 'no chain in source' flags (non-destructive re-ETL).

pure_canon_chain.jsonl.gz: one row per Pure Canon report of the four ingested works, keyed by `pure-canon:<pc id>`,
with the source's separate `chain` text byte-for-byte, its SHA-256 and the canonical extractor's branches.
no_chain_in_source.jsonl.gz: reports whose source carries no isnad (Pure Canon rows without `chain`, every
Nahj al-Balagha report), so downstream never shows a chain the extractor reads out of matn text.
`text_ar` is never altered. See README.md. Usage: python -B datasets/hadith-data/reconciled/build_pure_canon_chain_sidecar.py
"""

import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sidecar_io as io_  # noqa: E402

rc, common = io_.rc, io_.common
NAHJ_BOOK = "Nahj al-Balāgha"


def main() -> None:
    canon = rc.Canon()
    regen = canon.regen
    source_map = regen.CLASSICAL_SOURCE_MAP

    def surfaces_in(text: str):
        branches = canon.extract(text)
        return branches, sum(len(b) for b in branches or [])

    chain_rows, flag_rows = [], []
    counts = Counter()
    with open(rc.PURE_CANON, encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            obj = json.loads(line)
            source = source_map.get(obj.get("source", ""))
            if source is None:
                continue
            pc_id = str(obj.get("id") or "").strip()
            text_ar = obj.get("text_ar", "")
            chain = obj.get("chain", "") or ""
            record_id = f"pure-canon:{pc_id}"
            _, invented = surfaces_in(text_ar)
            if chain.strip():
                branches, extracted = surfaces_in(chain)
                status = ("chain_in_source" if extracted else
                          "chain_in_source_extraction_limit" if branches is None else
                          "chain_in_source_no_narrator_extracted")
                counts[f"{source} | {status}"] += 1
                chain_rows.append({
                    "record_id": record_id, "source_record_id": pc_id, "source": source,
                    "hadith_no": str(obj.get("hadith_no", "")), "text_ar_sha256": io_.sha256_text(text_ar),
                    "chain_status": status, "chain": chain, "chain_sha256": io_.sha256_text(chain),
                    "branches": branches or [], "surface_count": extracted,
                    "text_ar_is_matn_only": True, "text_ar_extraction_surfaces_to_suppress": invented,
                    "basis": "source_chain_field", "review_state": "unreviewed"})
            else:
                counts[f"{source} | no_chain_in_source"] += 1
                flag_rows.append({
                    "record_id": record_id, "source_record_id": pc_id, "source": source,
                    "text_ar_sha256": io_.sha256_text(text_ar), "reason": "source_dataset_ships_no_chain",
                    "text_ar_extraction_invents_narrators": invented > 0, "invented_surface_count": invented,
                    "suppress_extracted_chain": True, "review_state": "unreviewed"})
    for file_id, hadith in rc.iter_thaqalayn():
        if hadith.get("book") != NAHJ_BOOK:
            continue
        identity = regen.apply_thaqalayn_identity({"provider_file_id": file_id, "hadith_id": hadith.get("id")})
        _, invented = surfaces_in(hadith.get("arabicText", ""))
        counts[f"{NAHJ_BOOK} | no_chain_in_source"] += 1
        flag_rows.append({
            "record_id": identity["record_id"], "source_record_id": identity["source_record_id"],
            "source": NAHJ_BOOK, "text_ar_sha256": io_.sha256_text(hadith.get("arabicText", "")),
            "reason": "work_without_isnad_by_design",
            "text_ar_extraction_invents_narrators": invented > 0, "invented_surface_count": invented,
            "suppress_extracted_chain": True, "review_state": "unreviewed"})

    chain_output = io_.write_jsonl_gz("pure_canon_chain.jsonl.gz", chain_rows)
    flag_output = io_.write_jsonl_gz("no_chain_in_source.jsonl.gz", flag_rows)
    here = Path(__file__).resolve()
    thaqalayn_files = sorted(rc.THAQALAYN_DIR.glob("*.json"))
    io_.write_manifest("pure_canon_chain.manifest.json", {
        "artifact": "pure_canon_chain + no_chain_in_source",
        "status": "sidecar_unreviewed_not_a_release_input",
        "meaning": "Source-provided Pure Canon chain text (verbatim) with canonical extraction; reports whose source "
                   "has no isnad, so any chain extracted from their text_ar is matn noise",
        "command": "python -B datasets/hadith-data/reconciled/build_pure_canon_chain_sidecar.py",
        "inputs_sha256": {**common.input_fingerprints(rc.PURE_CANON, common.REGISTRY_PATH, *thaqalayn_files)},
        "code_sha256": io_.code_fingerprints(here, io_.RECONCILED_DIR / "sidecar_io.py",
                                             io_.RECONCILE_DIR / "reconcile_common.py",
                                             common.HADITH_DATA_DIR / "regen_unified_csvs.py",
                                             common.HADITH_DATA_DIR / "extract_isnad_unified.py"),
        "outputs": [chain_output, flag_output],
        "counts": {
            "by_source_and_status": dict(sorted(counts.items())),
            "chain_rows": len(chain_rows), "no_chain_rows": len(flag_rows),
            "chain_rows_with_extracted_narrators": sum(1 for r in chain_rows if r["surface_count"]),
            "chain_surfaces_extracted": sum(r["surface_count"] for r in chain_rows),
            "pure_canon_rows_whose_matn_yields_false_narrators": sum(
                1 for r in chain_rows if r["text_ar_extraction_surfaces_to_suppress"]) + sum(
                1 for r in flag_rows if r["source"] != NAHJ_BOOK and r["text_ar_extraction_invents_narrators"]),
            "nahj_rows_whose_text_yields_false_narrators": sum(
                1 for r in flag_rows if r["source"] == NAHJ_BOOK and r["text_ar_extraction_invents_narrators"]),
        },
        "not_carried": "Closing compiler statements (workbook column L) and edition header rows are already "
                       "extracted by diagnostics/grading-recovery and diagnostics/provenance-recovery; not duplicated.",
    })
    print(chain_output, flag_output)


if __name__ == "__main__":
    main()
