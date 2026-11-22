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
DEVELOPMENT = HERE.parents[1] / "development" / "chain-builder-r2-2026-11-22"
PROJECTION = DEVELOPMENT / "projection-m2c" / "canonical"          # the Sunni builder's input (Sunni untouched there)
IMAMI_PROJECTION = DEVELOPMENT / "projection-m1" / "canonical"      # the Imami builder's input (before round 2's Imami cut)
# The re-check's failing examples (README.md, regressions.jsonl, pop_verdicts.tsv) and cases round 2 got right.
REPORTS = [
    "hadith:k6:7805", "hadith:k6:4489", "hadith:k6:4794", "hadith:k6:16725", "hadith:k6:11239", "hadith:k6:13603",
    "hadith:k6:7852", "hadith:k6:25756", "hadith:k6:13589", "hadith:k6:21409", "hadith:pure-canon:pc_20809",
    "hadith:k6:7510", "hadith:k6:9735", "hadith:k6:11902", "hadith:k6:9552", "hadith:k6:4741", "hadith:k6:11255",
    "hadith:k6:9600", "hadith:k6:9826", "hadith:k6:13913", "hadith:k6:8169", "hadith:pure-canon:pc_46421",
    "hadith:pure-canon:pc_71896", "hadith:k6:28195", "hadith:k6:10025", "hadith:k6:14282", "hadith:k6:29819",
    "hadith:k6:26285", "hadith:k6:4144", "hadith:k6:27269", "hadith:k6:24036", "hadith:k6:21664", "hadith:k6:11006",
    "hadith:k6:9123", "hadith:k6:5155", "hadith:k6:14609", "hadith:k6:7666", "hadith:k6:18840",
]
# The re-check's Imami examples (patterns 6-8 and its Imami regression rows) and cases round 2 got right.
IMAMI_REPORTS = [
    "hadith:thaqalayn:f02c69a82883b8f2aa7763ce", "hadith:thaqalayn:1cee22846aab05dfbd59a888",
    "hadith:thaqalayn:b0c303b331dd554a8f3ea875", "hadith:thaqalayn:9dec2b996ad72f438d6910a3",
    "hadith:thaqalayn:2c8be8488724f439fc0556b2", "hadith:thaqalayn:1adbb3bc592355214cdb0be0",
    "hadith:thaqalayn:a38d215bee8c93fe2a02f810", "hadith:thaqalayn:f324c6f008626b3fe13da974",
    "hadith:thaqalayn:a8b7fa847a54b597f3b6e49e", "hadith:thaqalayn:d4b7d1dc574f1227818536e9",
    "hadith:thaqalayn:a1472a2b00e9f4b54e31e78f", "hadith:thaqalayn:4087da29a9e9548088a747f3",
    "hadith:thaqalayn:120a39aa967232cf18315ac4", "hadith:thaqalayn:5416571b4b45bb12b2600305",
    "hadith:thaqalayn:51c6afe40902764815d56ec9", "hadith:thaqalayn:19446c6246d0e379f43ca50e",
    "hadith:thaqalayn:e07ff81a1c3cf42113435ca7", "hadith:thaqalayn:07b3c9089c6fc4b7ed88073a",
    "hadith:thaqalayn:96c911ea2470e429cda031d4", "hadith:thaqalayn:4ede892fc226a4bd5a26764a",
]


def cut(projection: Path, reports: list[str]) -> dict:
    wanted = set(reports)
    text = {}
    with (projection / "hadiths.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["id"] in wanted:
                text[row["id"]] = row["text_ar"]
    chains = {}
    with (projection / "chains.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["hadith_id"] in wanted:
                chains[row["id"]] = (row["hadith_id"], int(row["branch"]))
    mentions = defaultdict(list)
    with (projection / "chain_mentions.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["chain_id"] in chains:
                mentions[row["chain_id"]].append((int(row["position"]), row["surface_ar"]))
    branches = defaultdict(list)
    for chain_id, (hadith_id, branch) in sorted(chains.items(), key=lambda item: item[1]):
        branches[hadith_id].append([surface for _, surface in sorted(mentions[chain_id])])
    return {hadith_id: {"text_ar": text[hadith_id], "branches": branches[hadith_id]} for hadith_id in reports}


def main() -> None:
    out = {"generated_from": "development/chain-builder-r2-2026-11-22: projection-m2c (Sunni input), projection-m1 (Imami input)",
           "reports": cut(PROJECTION, REPORTS), "imami_reports": cut(IMAMI_PROJECTION, IMAMI_REPORTS)}
    (HERE / "r3_fixtures.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(len(out["reports"]), "Sunni reports,", len(out["imami_reports"]), "Imami reports")


if __name__ == "__main__":
    main()
