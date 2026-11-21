#!/usr/bin/env python3
"""Q7: deterministic stratified sample of 200 reports to extend the 32-report isnad gold set (UN-annotated).

Strata: tradition quota x collection x chain-length bucket x taḥwīl/branching, with the gold-set rows excluded.
Every annotation field is blank; the extractor output is included only as a reviewer aid, labelled as such.
Writes output/validation_sample_200.jsonl and output/validation_sample_200.csv. Usage: python -B draw_validation_sample.py
"""

import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reconcile_common as rc  # noqa: E402

common = rc.common
OUTPUT = common.output_directory("chain-reconciliation/output")
GOLD = common.HADITH_DATA_DIR / "__tests__" / "fixtures" / "all-tradition-isnad-gold-v1.jsonl"
QUOTA = {"Sunni": 80, "Imami": 70, "Ibadi": 25, "Zaydi": 25}
SEED = "chain-reconciliation-validation-v1"


def length_bucket(branches) -> str:
    if not branches:
        return "none"
    longest = max(len(branch) for branch in branches)
    return "1-3" if longest <= 3 else "4-6" if longest <= 6 else "7+"


def stable_rank(*parts) -> str:
    return hashlib.sha256("|".join((SEED,) + tuple(str(p) for p in parts)).encode("utf-8")).hexdigest()


def main() -> None:
    canon = rc.Canon()
    pure_canon = rc.read_pure_canon()
    gold_texts = {json.loads(line)["text_ar"].strip() for line in open(GOLD, encoding="utf-8") if line.strip()}
    strata = defaultdict(list)
    for row_number, row in common.iter_corpus_rows():
        text = (row.get("text_ar") or "").strip()
        if not text or text in gold_texts:
            continue
        tradition = common.clean(row.get("tradition"))
        source = common.clean(row.get("source"))
        chain_text = text
        if source in rc.PURE_CANON_SOURCES:
            chains = {(m.get("chain") or "").strip() for m in pure_canon.get(text, [])}
            chain_text = next(iter(chains)) if len(chains) == 1 else ""
        branches = canon.extract(chain_text) if chain_text else []
        shape = "branched" if branches and len(branches) > 1 else "single"
        key = (tradition, source, length_bucket(branches), shape)
        strata[key].append((stable_rank(row_number, text[:64]), row_number, row, chain_text, branches or []))

    chosen = []
    for tradition, quota in QUOTA.items():
        keys = sorted(k for k in strata if k[0] == tradition)
        for bucket in keys:
            strata[bucket].sort(key=lambda item: item[0])
        # Round-robin over strata so every collection/length/shape cell gets a turn before any gets a second.
        picked, depth = [], 0
        while len(picked) < quota and any(len(strata[k]) > depth for k in keys):
            for bucket in sorted(keys, key=lambda k: stable_rank(*k)):
                if len(picked) < quota and len(strata[bucket]) > depth:
                    picked.append((bucket, strata[bucket][depth]))
            depth += 1
        chosen.extend(picked)

    rows = []
    for (tradition, source, bucket, shape), (_, row_number, row, chain_text, branches) in chosen:
        rows.append({
            "sample_id": f"val-{len(rows) + 1:03d}", "row": common.row_reference(row_number, row),
            "tradition": tradition, "source": source, "stratum_chain_length": bucket, "stratum_shape": shape,
            "chain_text_basis": "pure_canon_chain_field" if chain_text != (row.get("text_ar") or "").strip()
            else "master_text_ar",
            "text_ar": chain_text if chain_text != (row.get("text_ar") or "").strip() else row.get("text_ar"),
            "extractor_output_reviewer_aid_not_gold": branches,
            "expected_branches": None, "annotation_basis": None, "annotator": None, "annotated_at": None,
            "notes": None})
    common.write_jsonl(OUTPUT, "validation_sample_200.jsonl", rows)
    handle, _ = common.open_output(OUTPUT, "validation_sample_200.csv")
    with handle:
        writer = csv.writer(handle)
        writer.writerow(["sample_id", "line", "id", "tradition", "source", "chain_length", "shape", "chain_text_basis",
                         "text_ar_head", "extractor_output_reviewer_aid", "expected_branches", "annotation_basis",
                         "annotator", "notes"])
        for row in rows:
            writer.writerow([row["sample_id"], row["row"]["line"], row["row"]["id"], row["tradition"], row["source"],
                             row["stratum_chain_length"], row["stratum_shape"], row["chain_text_basis"],
                             (row["text_ar"] or "")[:400],
                             " || ".join(" > ".join(b) for b in row["extractor_output_reviewer_aid_not_gold"]),
                             "", "", "", ""])
    counts = defaultdict(int)
    for row in rows:
        counts[(row["tradition"], row["stratum_chain_length"], row["stratum_shape"])] += 1
    print(len(rows), json.dumps({" | ".join(k): v for k, v in sorted(counts.items())}, ensure_ascii=False, indent=0))


if __name__ == "__main__":
    main()
