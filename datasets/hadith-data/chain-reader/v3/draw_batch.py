"""Draw a fresh sample for a batch from the live uncertain population, excluding every report used in an earlier pilot or audit sample.

    python -B -X utf8 v3/draw_batch.py --population batch-001/private/population.jsonl --out-dir batch-001 --seed 20261122

Strata (batch 001): six Sunni books 250 (apportioned to each book's live uncertain count, largest remainder), al-Faqih 150, other Imami works except al-Kafi 100
(drawn from the pooled population, so a larger work contributes more). Inside a stratum the draw is uniform without replacement (random.Random(seed)).
Writes: <out-dir>/private/sample.json (opaque id + hadith id, shuffled packet order), <out-dir>/private/id_map.json, <out-dir>/draw.json (counts, exclusions, seed; no hadith ids).
Opaque ids are `b1-` and six hex characters of a salted hash; the salt is in the private map only. See v3/AGENTS.md §batch.
"""

from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import random
import secrets
import sys
from collections import Counter
from pathlib import Path

csv.field_size_limit(10 ** 9)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
AUDIT = ROOT.parent / "chain-audit"
SIX_BOOKS = ("sunni:bukhari", "sunni:muslim", "sunni:nasai", "sunni:tirmidhi", "sunni:abudawud", "sunni:ibnmajah")
STRATA = {"sunni_six_books": 250, "imami_faqih": 150, "imami_other_not_kafi": 100}


def excluded_ids() -> tuple[set[str], dict[str, int]]:
    """Hadith ids of every earlier sample: chain-audit sample_check.csv and verdicts.tsv (hadith_id, or chain_id minus its branch) and the pilot's reports.jsonl."""
    found: dict[str, set[str]] = {}

    def add(source: str, hadith_id: str) -> None:
        hadith_id = hadith_id.strip()
        if hadith_id.startswith("hadith:"):
            found.setdefault(source, set()).add(hadith_id)

    for pattern, delimiter in (("**/sample_check.csv", ","), ("**/verdicts.tsv", "\t")):
        for path in sorted(glob.glob(str(AUDIT / pattern), recursive=True)):
            with open(path, encoding="utf-8-sig", newline="") as handle:
                for row in csv.DictReader(handle, delimiter=delimiter):
                    source = str(Path(path).relative_to(AUDIT)).replace("\\", "/")
                    if row.get("hadith_id"):
                        add(source, row["hadith_id"])
                    chain_id = row.get("chain_id") or ""
                    if chain_id.startswith("chain:"):
                        add(source, "hadith:" + chain_id[len("chain:"):].rsplit(":", 1)[0])
    pilot = ROOT / "pilot" / "reports.jsonl"
    for line in pilot.read_text(encoding="utf-8").splitlines():
        if line.strip():
            add("chain-reader/pilot/reports.jsonl", json.loads(line)["hadith_id"])
    examples = json.loads((ROOT / "examples" / "examples.json").read_text(encoding="utf-8"))
    for text in [json.dumps(examples, ensure_ascii=False)]:
        for token in set(__import__("re").findall(r"hadith:[^\"\s,]+", text)):
            add("chain-reader/examples/examples.json", token)
    union = set().union(*found.values()) if found else set()
    return union, {source: len(ids) for source, ids in sorted(found.items())}


def apportion(total: int, weights: dict[str, int]) -> dict[str, int]:
    """Largest-remainder apportionment of `total` to the weights."""
    weight_sum = sum(weights.values())
    exact = {key: total * value / weight_sum for key, value in weights.items()}
    seats = {key: int(value) for key, value in exact.items()}
    for key in sorted(exact, key=lambda k: (exact[k] - seats[k], k), reverse=True)[: total - sum(seats.values())]:
        seats[key] += 1
    return seats


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--population", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--batch", default="b1", help="prefix of the opaque ids")
    args = parser.parse_args(argv)
    population = [json.loads(line) for line in Path(args.population).read_text(encoding="utf-8").splitlines() if line.strip()]
    excluded, excluded_by_source = excluded_ids()
    live = Counter(row["work"] for row in population)
    pool = [row for row in population if row["hadith_id"] not in excluded]
    removed = Counter(row["work"] for row in population if row["hadith_id"] in excluded)
    rng = random.Random(args.seed)
    strata_pool = {
        "sunni_six_books": [r for r in pool if r["work"] in SIX_BOOKS],
        "imami_faqih": [r for r in pool if r["work"] == "imami:man-la-yahduruhu-al-faqih"],
        "imami_other_not_kafi": [r for r in pool if r["work"].startswith("imami:") and r["work"] not in ("imami:al-kafi", "imami:man-la-yahduruhu-al-faqih")],
    }
    chosen: list[tuple[str, dict]] = []
    quota_by_book = apportion(STRATA["sunni_six_books"], {book: sum(1 for r in strata_pool["sunni_six_books"] if r["work"] == book) for book in SIX_BOOKS})
    for book in SIX_BOOKS:
        members = sorted((r for r in strata_pool["sunni_six_books"] if r["work"] == book), key=lambda r: r["hadith_id"])
        chosen += [("sunni_six_books", r) for r in rng.sample(members, quota_by_book[book])]
    for stratum in ("imami_faqih", "imami_other_not_kafi"):
        members = sorted(strata_pool[stratum], key=lambda r: r["hadith_id"])
        chosen += [(stratum, r) for r in rng.sample(members, STRATA[stratum])]
    rng.shuffle(chosen)                                           # packet order: works mixed, so position tells nothing
    salt = secrets.token_hex(16)
    sample, id_map, seen = [], {}, set()
    for stratum, row in chosen:
        opaque = f"{args.batch}-" + hashlib.sha256((salt + row["hadith_id"]).encode()).hexdigest()[:6]
        assert opaque not in seen, "opaque id collision: draw again"
        seen.add(opaque)
        sample.append({"id": opaque, "hadith_id": row["hadith_id"]})
        id_map[opaque] = {"hadith_id": row["hadith_id"], "work": row["work"], "stratum": stratum, "opening": row["opening"]}
    out = Path(args.out_dir)
    (out / "private").mkdir(parents=True, exist_ok=True)
    (out / "private" / "sample.json").write_text(json.dumps(sample, ensure_ascii=False, indent=0) + "\n", encoding="utf-8", newline="\n")
    (out / "private" / "id_map.json").write_text(json.dumps({"salt": salt, "seed": args.seed, "ids": id_map}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    population_sha = hashlib.sha256(Path(args.population).read_bytes()).hexdigest()
    draw = {
        "format": "shura-chain-batch-draw/1", "seed": args.seed, "method": "random.Random(seed).sample without replacement inside each stratum, hadith ids sorted before the draw; Sunni quota per book by largest remainder of the live uncertain count after exclusions",
        "population": {"definition": "reports with at least one non-retired chain with structure_status = 'uncertain' (live production read-only)", "reports": len(population), "sha256_of_population_file": population_sha, "by_work": dict(sorted(live.items()))},
        "excluded": {"union_hadith_ids": len(excluded), "by_source_file": excluded_by_source, "population_reports_removed": sum(removed.values()), "removed_by_work": dict(sorted(removed.items()))},
        "strata": {name: {"requested": STRATA[name], "drawn": sum(1 for s, _ in chosen if s == name), "pool_after_exclusion": len(strata_pool[name])} for name in STRATA},
        "sunni_quota_by_book": quota_by_book, "drawn_by_work": dict(sorted(Counter(r["work"] for _, r in chosen).items())),
        "drawn_opening_with_back_reference": dict(sorted(Counter(r["work"] for _, r in chosen if r["opening"]).items())),
        "reports": len(chosen),
    }
    (out / "draw.json").write_text(json.dumps(draw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: draw[k] for k in ("reports", "strata", "drawn_by_work")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
