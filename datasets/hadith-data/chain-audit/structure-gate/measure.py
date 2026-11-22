"""Measure the chain structure gate (pg_export/chain_structure.py) on the re-checks' read verdicts and on a projection.

Usage (from the repository root; read-only, writes only --out):
  python -I datasets/hadith-data/chain-audit/structure-gate/measure.py \
      --read datasets/hadith-data/development/chain-builder-r3-2026-11-22/projection-b2 \
      --before datasets/hadith-data/development/chain-builder-r2-2026-11-22/projection-m3 \
      --out datasets/hadith-data/chain-audit/structure-gate/results.json

`--read` is the projection the round-3 re-check read (2026.11.22.8). Labelled units: every round-3 sampled item whose report
has a chain (chain-level, or report-level when the item names no chain and the report has several), plus round-2 items whose
report's chains are identical in `--before` (round 2's projection) and `--read`. Round-2 "defect" counts only its strict kinds.
"""

from __future__ import annotations

import argparse
import collections
import csv
import gzip
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(ROOT / "datasets/hadith-data/pg_export"), str(ROOT / "datasets/hadith-data"), str(ROOT / "datasets")]
import chain_structure as cs  # noqa: E402

csv.field_size_limit(2**31 - 1)
AUDIT = ROOT / "datasets/hadith-data/chain-audit"
ROUND2_STRICT = {"missing_link", "branch_seam", "wrong_split", "false_seam", "merged_names", "concatenated_isnads",
                 "not_a_narrator", "truncated_route", "inherited_chain_wrong", "duplicated_narrator"}
TRADITION = {"collection:sunni": "Sunni", "collection:imami": "Imami", "collection:ibadi": "Ibadi", "collection:zaydi": "Zaydi"}
RETIRE = ("prose_work", "chapter_heading")


def load_projection(directory: Path) -> dict[str, dict]:
    """Per report: collection, text, detection text, chains (id, surfaces, inherited)."""
    pure_canon = {}
    with gzip.open(ROOT / "datasets/hadith-data/reconciled/pure_canon_chain.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            pure_canon["hadith:" + row["record_id"]] = row["chain"]
    canonical = directory / "canonical"
    mentions = collections.defaultdict(list)
    with (canonical / "chain_mentions.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            mentions[row["chain_id"]].append((int(row["position"]), row["surface_ar"], bool(row["inherited_from_mention_id"])))
    chains = collections.defaultdict(list)
    with (canonical / "chains.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            found = sorted(mentions[row["id"]])
            chains[row["hadith_id"]].append({"id": row["id"], "branch": int(row["branch"]), "surfaces": [m[1] for m in found],
                                             "inherited": any(m[2] for m in found)})
    reports = {}
    with (canonical / "hadiths.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["id"] in chains:
                reports[row["id"]] = {"collection": row["collection_id"], "text": row["text_ar"],
                                      "detection": pure_canon.get(row["id"]) or row["sanad_ar"] or row["text_ar"],
                                      "from_text": row["id"] not in pure_canon,
                                      "chains": sorted(chains[row["id"]], key=lambda chain: chain["branch"])}
    return reports


def assess_all(reports: dict[str, dict], only: set[str] | None = None) -> dict[str, dict]:
    out = {}
    for hadith_id, report in reports.items():
        if only is not None and hadith_id not in only:
            continue
        tradition = next(name for prefix, name in TRADITION.items() if report["collection"].startswith(prefix))
        work = report["collection"].split(":", 1)[1]
        retire = cs.retire_reason(work, tradition, report["text"], report["from_text"])
        reasons = cs.assess(cs.ReportChains(report["detection"], [c["surfaces"] for c in report["chains"]], tradition,
                                            [c["inherited"] for c in report["chains"]], hadith_id.startswith("hadith:thaqalayn:"),
                                            work, report["from_text"]), measure_all=True)
        out[hadith_id] = {"retire": retire, "reasons": {c["id"]: r for c, r in zip(report["chains"], reasons)}}
    return out


def group_of(hadith_id: str) -> str:
    if hadith_id.startswith("hadith:k6:"):
        return "sunni_k6"
    if hadith_id.startswith("hadith:pure-canon:"):
        return "sunni_pure_canon"
    for work in ("rabi", "zayd", "rida"):
        if f"{work}_" in hadith_id:
            return work
    return "imami"


def labelled_units(read: dict, before: dict) -> list[dict]:
    units = []
    for row in csv.DictReader((AUDIT / "round3/sample_check.csv").open(encoding="utf-8-sig")):
        report = read.get(row["hadith_id"])
        if not report or not report["chains"]:
            continue          # a report with no stored chain asserts no pair: nothing to gate
        chain_id = row["chain_id"] or (report["chains"][0]["id"] if len(report["chains"]) == 1 else None)
        units.append({"set": "round3_random" if row["stratum"] == "random" else "round3_population", "hadith_id": row["hadith_id"],
                      "chain_id": chain_id, "defect": row["verdict"] == "defect", "group": group_of(row["hadith_id"])})
    seen = {(unit["hadith_id"], unit["chain_id"]) for unit in units}
    for row in csv.DictReader((AUDIT / "round2/sample_check.csv").open(encoding="utf-8-sig")):
        if row["verdict"] not in ("ok", "defect") or (row["hadith_id"], row["chain_id"]) in seen:
            continue
        now, then = read.get(row["hadith_id"]), before.get(row["hadith_id"])
        if not now or not then or [(c["id"], c["surfaces"]) for c in now["chains"]] != [(c["id"], c["surfaces"]) for c in then["chains"]]:
            continue          # the chain changed since round 2 read it: its verdict no longer applies
        units.append({"set": "round2_unchanged", "hadith_id": row["hadith_id"], "chain_id": row["chain_id"],
                      "defect": row["verdict"] == "defect" and row["kind"] in ROUND2_STRICT, "group": group_of(row["hadith_id"])})
    return units


def reasons_of(unit: dict, assessed: dict) -> set[str]:
    result = assessed[unit["hadith_id"]]
    if result["retire"]:
        return {result["retire"]}
    if unit["chain_id"]:
        return set(result["reasons"][unit["chain_id"]])
    return set().union(*result["reasons"].values())


def wilson(k: int, n: int, z: float = 1.96) -> str:
    if n == 0:
        return "0/0"
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{k}/{n} = {100 * p:.1f}% ({100 * max(0, c - m):.1f}-{100 * min(1, c + m):.1f})"


def gate(units: list[dict], assessed: dict, active: set[str], sets: set[str] | None) -> dict:
    table = collections.defaultdict(lambda: [0, 0, 0, 0])      # n, defects, checked, defects among checked
    for unit in units:
        if sets and unit["set"] not in sets:
            continue
        reasons = reasons_of(unit, assessed)
        kept = not (reasons & (active | set(RETIRE)))
        keys = {unit["group"], "all"} | ({"sunni"} if unit["group"].startswith("sunni") else set())
        for key in keys:
            row = table[key]
            row[0] += 1
            row[1] += unit["defect"]
            row[2] += kept
            row[3] += kept and unit["defect"]
    return {key: {"before": wilson(d, n), "checked_share": f"{k}/{n}", "among_checked": wilson(dk, k)}
            for key, (n, d, k, dk) in sorted(table.items())}


def curve(units: list[dict], assessed: dict, codes: list[str]) -> list[dict]:
    """Greedy path: at each step add the detector that removes the most defects per correct chain lost."""
    def totals(active):
        n = d = k = dk = 0
        for unit in units:
            kept = not (reasons_of(unit, assessed) & (set(active) | set(RETIRE)))
            n, d, k, dk = n + 1, d + unit["defect"], k + kept, dk + (kept and unit["defect"])
        return n, d, k, dk
    path, active, remaining = [], [], list(codes)
    while remaining:
        base = totals(active)
        def value(code):
            after = totals(active + [code])
            return (base[3] - after[3]) / ((base[2] - base[3]) - (after[2] - after[3]) + 0.5)
        best = max(remaining, key=lambda code: (value(code), code))
        active.append(best)
        remaining.remove(best)
        n, d, k, dk = totals(active)
        path.append({"add": best, "correct_kept": f"{k - dk}/{n - d}", "defects_kept": f"{dk}/{d}", "rate_among_checked": wilson(dk, k),
                     "in_gate": best in cs.GATE_REASONS})
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--read", type=Path, required=True)
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    read, before = load_projection(args.read), load_projection(args.before)
    units = labelled_units(read, before)
    assessed = assess_all(read, {unit["hadith_id"] for unit in units})
    detectors = collections.defaultdict(lambda: [0, 0])
    for unit in units:
        for code in reasons_of(unit, assessed):
            detectors[code][0 if unit["defect"] else 1] += 1
    production = collections.Counter()
    for result in assess_all(read).values():
        for reasons in result["reasons"].values():
            production.update([result["retire"]] if result["retire"] else reasons)
    codes = sorted(code for code in detectors if code not in RETIRE)
    results = {
        "labelled_units": {"total": len(units), "defective": sum(unit["defect"] for unit in units),
                           "by_set": collections.Counter(unit["set"] for unit in units)},
        "detectors": {code: {"flags_defective": d, "flags_correct": c, "production_chains": production[code],
                             "in_gate": code in cs.GATE_REASONS or code in RETIRE}
                      for code, (d, c) in sorted(detectors.items(), key=lambda item: -item[1][0])},
        "gate_round3_random": gate(units, assessed, set(cs.GATE_REASONS), {"round3_random"}),
        "gate_all_labelled": gate(units, assessed, set(cs.GATE_REASONS), None),
        "curve_all_labelled": curve(units, assessed, codes),
    }
    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({key: results[key] for key in ("labelled_units", "gate_round3_random")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
