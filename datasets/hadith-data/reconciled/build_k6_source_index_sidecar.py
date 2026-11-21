#!/usr/bin/env python3
"""K6 source-index sidecar: the original download's ordered narrator ids per report, with text agreement.

Reads the original K6 CSV inside archive/datasets.7z (read-only) and the canonical K6 input all_hadiths_clean.csv.gz
for the stable `k6:<id>` key; writes k6_source_index.jsonl.gz and k6_source_index.manifest.json here. Never writes
`chain_indx` or any existing file. A source id is the source's claim; every row is unreviewed. See README.md.
Usage: python -B datasets/hadith-data/reconciled/build_k6_source_index_sidecar.py
"""

import csv
import gzip
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sidecar_io as io_  # noqa: E402

rc, common = io_.rc, io_.common
sys.path.insert(0, str(io_.RECONCILE_DIR))
from measure_source_index_agreement import classify  # noqa: E402

CLEAN_INPUT = common.HADITH_DATA_DIR / "all_hadiths_clean.csv.gz"
CORROBORATED_CLASSES = ("full_agreement", "multi_branch_all_source_ids_aligned")


def basis_for(agreement_class: str) -> str:
    """Corroborated label only for fully confirmed reports; every other report is labelled by its class."""
    if agreement_class in CORROBORATED_CLASSES:
        return rc.BASIS_CORROBORATED
    if agreement_class == "no_source_index":
        return "no_source_index"
    return f"source_index_{agreement_class}"


def main() -> None:
    canon = rc.Canon()
    originals, member_sha = rc.read_k6_original()
    with gzip.open(CLEAN_INPUT, "rt", encoding="utf-8", newline="") as handle:
        clean = [row for row in csv.DictReader(handle) if (row.get("source") or "").strip() in rc.K6_SOURCES]
    if len(clean) != len(originals):
        raise SystemExit(f"K6 row count differs: canonical input {len(clean)}, original {len(originals)}")

    counts, bases = Counter(), Counter()
    rows = []
    for position, (original, current) in enumerate(zip(originals, clean)):
        if original["text_ar"] != current["text_ar"] or original["source"].strip() != current["source"].strip():
            raise SystemExit(f"K6 join failed at position {position}: Arabic or source differs")
        ids = rc.parse_ids(original["chain_indx"])
        branches = canon.extract(current["text_ar"])
        label, tiers, pairs = classify(canon, ids, branches)
        counts[label] += 1
        basis = basis_for(label)
        bases[basis] += 1
        legacy_id = (current.get("id") or "").strip()
        rows.append({
            "record_id": f"k6:{legacy_id}", "source_record_id": legacy_id,
            "source": current["source"].strip(), "hadith_no": (current.get("hadith_no") or "").strip(),
            "arabic_sha256": io_.sha256_text(current["text_ar"]),
            "source_ids": ids, "source_id_count": len(ids),
            "agreement_class": label, "basis": basis,
            "text_branches": branches or [],
            "position_name_tiers": tiers,
            "aligned_positions": [{"source_position": i, "branch": b, "branch_position": j, "name_tier": t}
                                  for i, b, j, t in pairs],
            "source_ids_missing_from_registry": sorted({i for i in ids if i not in canon.registry}, key=int),
            "review_state": "unreviewed",
        })
    output = io_.write_jsonl_gz("k6_source_index.jsonl.gz", rows)
    here = Path(__file__).resolve()
    io_.write_manifest("k6_source_index.manifest.json", {
        "artifact": "k6_source_index", "status": "sidecar_unreviewed_not_a_release_input",
        "meaning": "Original K6 per-report narrator ids (the source's claim) and their agreement with the Arabic text",
        "command": "python -B datasets/hadith-data/reconciled/build_k6_source_index_sidecar.py",
        "inputs_sha256": {
            **common.input_fingerprints(rc.K6_ARCHIVE, CLEAN_INPUT, common.REGISTRY_PATH),
            f"{common.relative_path(rc.K6_ARCHIVE)}!{rc.K6_MEMBER}": member_sha},
        "code_sha256": io_.code_fingerprints(here, io_.RECONCILED_DIR / "sidecar_io.py",
                                             io_.RECONCILE_DIR / "reconcile_common.py",
                                             io_.RECONCILE_DIR / "measure_source_index_agreement.py",
                                             common.HADITH_DATA_DIR / "regen_unified_csvs.py",
                                             common.HADITH_DATA_DIR / "extract_isnad_unified.py"),
        "join": "file position plus byte-identical Arabic and source (K6 `id` is not unique in the original)",
        "output": output,
        "counts": {"reports": len(rows), "by_agreement_class": dict(sorted(counts.items())),
                   "by_basis": dict(sorted(bases.items())),
                   "source_ids": sum(r["source_id_count"] for r in rows),
                   "source_ids_corroborated_by_aligned_text": sum(len(r["aligned_positions"]) for r in rows)},
    })
    print(output, dict(bases))


if __name__ == "__main__":
    main()
