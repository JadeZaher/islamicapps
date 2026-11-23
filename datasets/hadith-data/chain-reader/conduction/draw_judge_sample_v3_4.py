"""Draw the judge's random sample of one tranche UNDER THE v3.4 TOOL (sayings-supported triage): 100 eligible readings, stratified by group, fixed seed per tranche (copy of tranches/draw_judge_sample.py).

    python -B -X utf8 v3_2/draw_judge_sample_v3_2.py --tranche 02 [--n 100] [--base-seed 20261200]            (from chain-reader/, after v3_2/triage_v3_2.py wrote tranche-NN/triage-v3_4-sayings)
    python -B -X utf8 v3_2/draw_judge_sample_v3_2.py --tranche 02 --base-seed 20261300 --exclude tranches/tranche-02/judge-v3_4/sample.tsv --out-name extension      (the extension: seed 20261302, disjoint from the first draw)

Reads tranche-NN/triage-v3_4-sayings/{triage.tsv, readings/}; writes tranche-NN/judge-v3_4/ (sample.tsv, draw.json, dump.jsonl; `<out-name>-` prefixed for an extension). The dump also lists each reading's variant remarks.

Eligible = what the pipeline would apply: both passes valid, canonical-equal, status read, no hold (`triage.tsv` eligible = True), a reading with links or an empty reading ("no chain by reading").
Seed = base seed + tranche number (reproducible; nobody picks the reports). The sample is split over the three groups (six Sunni books, al-Faqih, other Imami) in proportion to the eligible
readings of each, largest remainder, at least one per group that has any; inside a group a uniform draw without replacement from the ids sorted. Writes tranche-NN/judge/:
sample.tsv (id, group, work, applies), draw.json (seed, eligible and drawn per group), dump.jsonl (per report: the text, the agreed reading's routes, the stored chain, the previous reports' ids)
for the judge, who reads the Arabic and writes right / wrong / undecided with a quote (analysis-batch-001 is the model). dump.jsonl carries the stored chain: the judge is not a reader.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TRANCHES = HERE.parent / "tranches"
GROUPS = ("sunni_six_books", "imami_faqih", "imami_other_not_kafi")
MARK = {"imam_in_text": "[M]", "inherited": "[I]", "unnamed": "[U]", "relation": "[R]", "back_reference": "[B]", "compiler_head": "[C]"}


def apportion(total: int, weights: dict[str, int]) -> dict[str, int]:
    """Largest-remainder apportionment of `total` to the weights, at least one to a group that has any (when the total allows)."""
    weight_sum = sum(weights.values())
    if weight_sum == 0:
        return {key: 0 for key in weights}
    exact = {key: total * value / weight_sum for key, value in weights.items()}
    seats = {key: int(value) for key, value in exact.items()}
    for key in sorted(exact, key=lambda k: (exact[k] - seats[k], k), reverse=True)[: total - sum(seats.values())]:
        seats[key] += 1
    for key, weight in weights.items():
        if weight and seats[key] == 0:
            donor = max(seats, key=lambda k: seats[k])
            seats[donor] -= 1
            seats[key] = 1
    return seats


def draw(eligible_by_group: dict[str, list[str]], n: int, seed: int) -> dict[str, list[str]]:
    rng = random.Random(seed)
    total = sum(len(v) for v in eligible_by_group.values())
    quota = apportion(min(n, total), {g: len(v) for g, v in eligible_by_group.items()})
    return {g: sorted(rng.sample(sorted(eligible_by_group[g]), min(quota[g], len(eligible_by_group[g])))) for g in GROUPS if g in eligible_by_group}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tranche", required=True, help="two digits, e.g. 01")
    parser.add_argument("--n", type=int, default=100)
    parser.add_argument("--base-seed", type=int, default=20261200)
    parser.add_argument("--exclude", help="a sample.tsv whose ids are left out of the draw (the extension of a first draw)")
    parser.add_argument("--out-name", default="", help="prefix of the three output files (an extension: `extension`)")
    args = parser.parse_args(argv)
    tdir = TRANCHES / f"tranche-{int(args.tranche):02d}"
    with (tdir / "triage-v3_4-sayings" / "triage.tsv").open(encoding="utf-8") as handle:
        triage = list(csv.DictReader(handle, delimiter="\t"))
    id_map = json.loads((tdir / "private" / "id_map.json").read_text(encoding="utf-8"))["ids"]
    reports = {row["id"]: row for row in (json.loads(line) for line in (tdir / "private" / "reports.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())}
    left_out = set()
    if args.exclude:
        with Path(args.exclude).open(encoding="utf-8") as handle:
            left_out = {row["id"] for row in csv.DictReader(handle, delimiter="	")}
    eligible = {g: [] for g in GROUPS}
    applies = {}
    for row in triage:
        if row["eligible"] == "True" and row["id"] not in left_out:
            eligible[id_map[row["id"]]["stratum"]].append(row["id"])
            applies[row["id"]] = row["applies"]
    seed = args.base_seed + int(args.tranche)
    drawn = draw(eligible, args.n, seed)
    out = tdir / "judge-v3_4"
    out.mkdir(exist_ok=True)
    prefix = f"{args.out_name}-" if args.out_name else ""
    ids = [i for g in GROUPS for i in drawn.get(g, [])]
    with (out / f"{prefix}sample.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "group", "work", "applies"])
        for i in ids:
            writer.writerow([i, id_map[i]["stratum"], id_map[i]["work"], applies[i]])
    lines = []
    for i in ids:
        reading = json.loads((tdir / "triage-v3_4-sayings" / "readings" / f"{i}.json").read_text(encoding="utf-8"))["expanded_a"]
        routes = [" > ".join(MARK.get(link["kind"], "") + link["surface"] for link in route["links"]) for route in reading["routes"]]
        stored = [s for chain in reports[i]["stored_chains"] for s in chain["surfaces"]]
        lines.append(json.dumps({"id": i, "group": id_map[i]["stratum"], "work": id_map[i]["work"], "applies": applies[i], "text": reports[i]["text"], "agreed_routes": routes, "stored_surfaces": stored,
                                 "previous_reports": [p["hadith_id"] for p in reports[i].get("previous_reports") or []],
                                 "variant_remarks": [r["quote"] for r in reading.get("variant_remarks") or []]}, ensure_ascii=False))
    (out / f"{prefix}dump.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (out / f"{prefix}draw.json").write_text(json.dumps({"tranche": f"{int(args.tranche):02d}", "seed": seed, "base_seed": args.base_seed, "n_requested": args.n, "eligible_by_group": {g: len(v) for g, v in eligible.items()},
                                               "drawn_by_group": {g: len(v) for g, v in drawn.items()}, "no_chain_among_drawn": sum(applies[i] == "no_chain" for i in ids)}, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"tranche {args.tranche}: drew {len(ids)} of {sum(len(v) for v in eligible.values())} eligible (seed {seed}): " + ", ".join(f"{g} {len(drawn.get(g, []))}" for g in GROUPS), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
