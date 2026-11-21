"""Measure what the LSH candidate step misses: exact all-pairs scoring for a fixed random sample of reports.

Run after build_report_correspondence.py (it reads that job's pair file). README.md §Recall.

    python -B datasets/hadith-data/diagnostics/report-correspondence/measure_lsh_recall.py
"""

from __future__ import annotations

import csv
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
JOB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(JOB_DIR))

import build_report_correspondence as build  # noqa: E402
import correspondence_logic as logic  # noqa: E402

SAMPLE_RANDOM = 300          # uniformly from all eligible reports
SAMPLE_PER_MINORITY = 50     # plus this many from each non-Sunni tradition
SEED = build.SEED + 1
GATE = min(logic.VARIANT_CONTAINMENT, logic.PARTIAL_CONTAINMENT)


def main() -> None:
    started = time.time()
    out_dir = build.common.output_directory(f"{build.JOB}/output")
    reports, _, _ = build.read_corpus(started)
    eligible = [i for i in range(len(reports)) if reports.eligible[i]]
    rng = random.Random(SEED)
    queries = set(rng.sample(eligible, SAMPLE_RANDOM))
    for tradition in ("Imami", "Zaydi", "Ibadi"):
        pool = sorted(i for i in eligible if reports.tradition[i] == tradition and i not in queries)
        queries.update(rng.sample(pool, min(SAMPLE_PER_MINORITY, len(pool))))
    queries = sorted(queries)
    postings: dict[int, list[int]] = defaultdict(list)
    for q in queries:
        for value in reports.shingles[q]:
            postings[value].append(q)
    build.progress(f"{len(queries)} query reports; exact scan of {len(eligible)} reports", started)

    sequence = build.make_sequence_cache(reports)
    query_sets = {q: set(reports.shingles[q]) for q in queries}
    truth = []
    for done, d in enumerate(eligible):
        shared = Counter()
        for value in reports.shingles[d]:
            for q in postings.get(value, ()):
                shared[q] += 1
        for q, count in shared.items():
            if q == d or count < GATE * min(len(query_sets[q]), len(reports.shingles[d])):
                continue   # every class needs containment >= GATE, so the exact score could not keep it
            score = build.exact_score(reports, q, d, query_sets[q], sequence)
            pair_class = logic.classify(score, reports.words[q], reports.words[d])
            if pair_class is not None:
                truth.append((q, d, pair_class, score))
        if done % 20000 == 0:
            build.progress(f"scanned {done}", started)

    found = set()
    with open(out_dir / "report_correspondence_pairs.csv", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            found.add((row["hadith_id_a"], row["hadith_id_b"]))
    totals, hits = Counter(), Counter()
    seen = set()
    for q, d, pair_class, score in truth:
        key = tuple(sorted((reports.hadith_id[q], reports.hadith_id[d])))
        if key in seen:
            continue
        seen.add(key)
        strata = [f"class:{pair_class}", f"scope:{build.scope(reports, q, d)}",
                  f"band:{pair_class}|{logic.score_band(score, pair_class)}", "all"]
        for stratum in strata:
            totals[stratum] += 1
            if key in found:
                hits[stratum] += 1
    result = {
        "query_reports": len(queries), "seed": SEED, "true_pairs_touching_queries": totals["all"],
        "recall": {k: {"true_pairs": totals[k], "found_by_lsh": hits[k], "recall": round(hits[k] / totals[k], 3)}
                   for k in sorted(totals)},
        "note": "Truth = every pair the exact scorer would keep, for pairs touching a sampled report.",
    }
    build.common.write_json(out_dir, "lsh_recall.json", result)
    build.progress(f"recall overall {result['recall']['all']}", started)


if __name__ == "__main__":
    main()
