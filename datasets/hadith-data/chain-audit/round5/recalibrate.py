"""Round 5: recalibrate the chain structure gate on a split (tuning = rounds 2/3, held-out = round 4), read-only.

Run from the repository root (about 10 minutes; 10 worker processes, all stopped on exit):
  python -I -X utf8 datasets/hadith-data/chain-audit/round5/recalibrate.py --out datasets/hadith-data/chain-audit/round5/results.json
Prints the tables the README quotes. The round-4 gate is read from git (`lib.ROUND4_COMMIT`), the new gate from the working tree.
"""

from __future__ import annotations

import argparse
import collections
import json
import multiprocessing
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lib  # noqa: E402

cs = lib.cs
RETIRED = {"prose_work", "chapter_heading"}
SMALL_WORKS = ["al-khisal", "al-amali-saduq", "uyun-akhbar-al-rida", "maani-al-akhbar", "kitab-al-ghayba-tusi", "kamil-al-ziyarat",
               "kamal-al-din", "al-tawhid-saduq", "mujam-al-ahadith-al-mutabara", "kitab-al-ghayba-numani", "al-amali-mufid",
               "kitab-al-zuhd", "kitab-al-mumin", "sifat-al-shia", "fadail-al-shia"]
_WORKER: dict = {}


def configure(module, config: dict) -> None:
    module.FEATURES = frozenset(config["features"])
    module.UNCHECKED_WORKS = frozenset(config["unchecked"])
    module.MANY_ROUTES = config["many"]
    module.GATE_REASONS = frozenset(config["gate"])


def _init(reports):
    _WORKER["reports"] = reports
    _WORKER["old"] = lib.load_round4_gate()


def _chunk(task):
    """Gate reasons per chain id for reports[start:end] under one config (module: 'new' or 'round4')."""
    name, config, start, end = task
    module = _WORKER["old"] if name == "round4" else cs
    configure(module, config)
    out = {}
    for hadith_id, report in _WORKER["reports"][start:end]:
        tradition = next(n for p, n in lib.measure.TRADITION.items() if report["collection"].startswith(p))
        work = report["collection"].split(":", 1)[1]
        reasons = module.assess(module.ReportChains(report["detection"], [c["surfaces"] for c in report["chains"]], tradition,
                                                    [c["inherited"] for c in report["chains"]], hadith_id.startswith("hadith:thaqalayn:"),
                                                    work, report["from_text"]))
        for chain, codes in zip(report["chains"], reasons):
            out[chain["id"]] = tuple(codes)
    return out


def production(pool, name, config, size):
    merged = {}
    for part in pool.map(_chunk, [(name, config, s, min(s + 4000, size)) for s in range(0, size, 4000)]):
        merged.update(part)
    return merged


def unit_status(module, config, reports, units):
    """unit -> True when the gate checks it (no gate reason, not retired)."""
    configure(module, config)
    assessed = lib.assess_units(module, reports, units)
    gate = set(config["gate"]) | RETIRED
    return {id(unit): not (lib.unit_reasons(unit, assessed) & gate) for unit in units}


def weighted_rate(units, kept, population, rng, rounds=2000):
    """Defect rate among checked chains, each unit weighted by its round-4 stratum's population over its sample size."""
    def estimate(sample):
        strata = collections.Counter(u["round4_stratum"] for u in sample)
        num = den = 0.0
        for unit in sample:
            weight = population[unit["round4_stratum"]] / strata[unit["round4_stratum"]]
            if kept[id(unit)]:
                den += weight
                num += weight * unit["defect"]
        return num / den if den else 0.0
    by_stratum = collections.defaultdict(list)
    for unit in units:
        by_stratum[unit["round4_stratum"]].append(unit)
    draws = sorted(estimate([rng.choice(members) for members in by_stratum.values() for _ in members]) for _ in range(rounds))
    return estimate(units), draws[int(0.025 * rounds)], draws[int(0.975 * rounds)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    r3 = lib.measure.load_projection(lib.READ_R3)
    before_r2 = lib.measure.load_projection(lib.BEFORE_R2)
    r4 = lib.measure.load_projection(lib.READ_R4)
    tuning, held = lib.measure.labelled_units(r3, before_r2), lib.held_out_units(r4)
    old = lib.load_round4_gate()
    final = {"features": sorted(cs.FEATURES), "unchecked": sorted(cs.UNCHECKED_WORKS), "many": cs.MANY_ROUTES, "gate": sorted(cs.GATE_REASONS)}
    round4 = {"features": [], "unchecked": sorted(old.UNCHECKED_WORKS), "many": old.MANY_ROUTES, "gate": sorted(old.GATE_REASONS)}
    # Each ablation is the final gate with one change reversed.
    ablations = {name: {**final, "features": [f for f in final["features"] if f != name]} for name in final["features"]}
    ablations["work_not_checked_blanket"] = {**final, "unchecked": round4["unchecked"]}
    ablations["sibling_skips_link"] = {**final, "gate": [g for g in final["gate"] if g != "sibling_skips_link"]}
    ablations["many_routes_at_4"] = {**final, "many": 4}
    ablations["many_routes_at_5"] = {**final, "many": 5}
    ablations["many_routes_off"] = {**final, "many": 10**6}

    results: dict = {"labelled": {"tuning": len(tuning), "tuning_defective": sum(u["defect"] for u in tuning),
                                  "held_out": len(held), "held_out_defective": sum(u["defect"] for u in held)}}
    reports_list = list(r4.items())
    with multiprocessing.get_context("spawn").Pool(10, _init, (reports_list,)) as pool:
        production_before = production(pool, "round4", round4, len(reports_list))
        production_after = production(pool, "new", final, len(reports_list))
        production_ablated = {name: production(pool, "new", config, len(reports_list)) for name, config in ablations.items()}

    status = {}
    for set_name, units, reports in (("tuning", tuning, r3), ("held_out", held, r4)):
        status[set_name] = {"round4": unit_status(old, round4, reports, units), "final": unit_status(cs, final, reports, units),
                            **{name: unit_status(cs, config, reports, units) for name, config in ablations.items()}}
    configure(cs, final)

    results["tables"] = {}
    for set_name, units in (("tuning", tuning), ("held_out", held)):
        results["tables"][set_name] = {}
        for label in ("round4", "final"):
            kept = status[set_name][label]
            raw = collections.defaultdict(lambda: [0, 0, 0, 0])
            for unit in units:
                for key in {unit["group"], "all"} | ({"sunni"} if unit["group"].startswith("sunni") else set()):
                    row = raw[key]
                    row[0] += 1
                    row[1] += unit["defect"]
                    row[2] += kept[id(unit)]
                    row[3] += kept[id(unit)] and unit["defect"]
            results["tables"][set_name][label] = {k: {"n": r[0], "defects": r[1], "checked": r[2], "defects_among_checked": r[3],
                                                      "among_checked": lib.fmt(r[3], r[2]), "share_checked": f"{r[2]}/{r[0]}"}
                                                  for k, r in sorted(raw.items())}

    # Round 4's strata (checked / withheld) are not proportional to the population: weight them back.
    group_of_report = {h: lib.measure.group_of(h) for h in r4}
    rng = random.Random(20261122)
    weighted = {}
    for group in ("sunni", "sunni_k6", "imami"):
        population = collections.Counter()
        for hadith_id, report in r4.items():
            if group_of_report[hadith_id] == group or (group == "sunni" and group_of_report[hadith_id].startswith("sunni")):
                for chain in report["chains"]:
                    population["withheld" if production_before[chain["id"]] else "checked"] += 1
        members = [u for u in held if u["group"] == group or (group == "sunni" and u["group"].startswith("sunni"))]
        weighted[group] = {label: [round(100 * x, 1) for x in weighted_rate(members, status["held_out"][label], population, rng)]
                           for label in ("round4", "final")}
    results["held_out_weighted_point_low_high"] = weighted

    # Per change: what it flags / releases on each set and in production.
    effects = {}
    for name in ablations:
        entry = {}
        for set_name, units in (("tuning", tuning), ("held_out", held)):
            flagged = [u for u in units if status[set_name][name][id(u)] and not status[set_name]["final"][id(u)]]
            released = [u for u in units if not status[set_name][name][id(u)] and status[set_name]["final"][id(u)]]
            entry[set_name] = {"flagged_defective": sum(u["defect"] for u in flagged), "flagged_correct": sum(not u["defect"] for u in flagged),
                               "released_defective": sum(u["defect"] for u in released), "released_correct": sum(not u["defect"] for u in released)}
        other = production_ablated[name]
        entry["production"] = {"chains_flagged_by_change": sum(1 for c in production_after if production_after[c] and not other[c]),
                               "chains_released_by_change": sum(1 for c in production_after if not production_after[c] and other[c])}
        effects[name] = entry
    results["effects"] = effects

    shares = collections.defaultdict(lambda: [0, 0, 0])
    for hadith_id, report in r4.items():
        work = report["collection"].split(":", 1)[1]
        for chain in report["chains"]:
            for key in {group_of_report[hadith_id], "all", work}:
                row = shares[key]
                row[0] += 1
                row[1] += not production_before[chain["id"]]
                row[2] += not production_after[chain["id"]]
    results["production_share_checked"] = {k: {"chains": r[0], "checked_before": r[1], "checked_after": r[2]} for k, r in sorted(shares.items())}

    per_work = {}
    for work in SMALL_WORKS:
        key = f"imami:{work}"
        row = {"production_chains": shares[key][0], "checked_before": shares[key][1], "checked_after": shares[key][2]}
        for set_name, units, reports in (("tuning", tuning, r3), ("held_out", held, r4)):
            mine = [u for u in units if reports[u["hadith_id"]]["collection"] == f"collection:{key}"]
            kept = [u for u in mine if status[set_name]["final"][id(u)]]
            row[set_name] = {"units": len(mine), "defective": sum(u["defect"] for u in mine), "checked_after": len(kept),
                             "defective_among_checked_after": sum(u["defect"] for u in kept)}
        per_work[work] = row
    results["small_works"] = per_work

    args.out.write_text(json.dumps(results, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (lib.DEV / "gate-recalibration-2026-11-22" / "production_status.json").write_text(json.dumps(
        {"round4": {c: list(v) for c, v in production_before.items() if v}, "final": {c: list(v) for c, v in production_after.items() if v}},
        ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
