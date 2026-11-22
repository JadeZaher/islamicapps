"""Cut the round 3 Sunni builder fixtures: each report's text and the bundle branches the builder reads (projection-m2c).

Usage: python -I datasets/hadith-data/chain-audit/round2/make_r3_fixtures.py
Writes r3_fixtures.json beside this file (read by pg_export/test_chain_builder.py).
"""

import csv
import json
from collections import defaultdict
from pathlib import Path

csv.field_size_limit(2**31 - 1)
HERE = Path(__file__).resolve().parent
PROJECTION = HERE.parents[1] / "development" / "chain-builder-r2-2026-11-22" / "projection-m2c" / "canonical"
# The re-check's failing examples (README.md, regressions.jsonl, pop_verdicts.tsv) and cases round 2 got right.
REPORTS = [
    "hadith:k6:7805", "hadith:k6:4489", "hadith:k6:4794", "hadith:k6:16725", "hadith:k6:11239", "hadith:k6:13603",
    "hadith:k6:7852", "hadith:k6:25756", "hadith:k6:13589", "hadith:k6:21409", "hadith:pure-canon:pc_20809",
    "hadith:k6:7510", "hadith:k6:9735", "hadith:k6:11902", "hadith:k6:9552", "hadith:k6:4741", "hadith:k6:11255",
    "hadith:k6:9600", "hadith:k6:9826", "hadith:k6:13913", "hadith:k6:8169", "hadith:pure-canon:pc_46421",
    "hadith:pure-canon:pc_71896", "hadith:k6:28195", "hadith:k6:10025", "hadith:k6:14282", "hadith:k6:29819",
    "hadith:k6:26285", "hadith:k6:4144", "hadith:k6:27269", "hadith:k6:24036", "hadith:k6:21664", "hadith:k6:11006",
]


def main() -> None:
    wanted = set(REPORTS)
    text = {}
    with (PROJECTION / "hadiths.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["id"] in wanted:
                text[row["id"]] = row["text_ar"]
    chains = {}
    with (PROJECTION / "chains.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["hadith_id"] in wanted:
                chains[row["id"]] = (row["hadith_id"], int(row["branch"]))
    mentions = defaultdict(list)
    with (PROJECTION / "chain_mentions.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["chain_id"] in chains:
                mentions[row["chain_id"]].append((int(row["position"]), row["surface_ar"]))
    branches = defaultdict(list)
    for chain_id, (hadith_id, branch) in sorted(chains.items(), key=lambda item: item[1]):
        branches[hadith_id].append([surface for _, surface in sorted(mentions[chain_id])])
    out = {"generated_from": "development/chain-builder-r2-2026-11-22/projection-m2c (the Sunni builder's input)",
           "reports": {hadith_id: {"text_ar": text[hadith_id], "branches": branches[hadith_id]} for hadith_id in REPORTS}}
    (HERE / "r3_fixtures.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(out["reports"]), "reports")


if __name__ == "__main__":
    main()
