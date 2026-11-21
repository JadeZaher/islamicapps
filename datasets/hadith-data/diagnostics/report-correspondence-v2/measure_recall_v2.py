"""Measure what the v2 candidate step misses: exact all-pairs scoring of a fixed sample of reports under the v2 rules.

Run after build_report_correspondence_v2.py (it reads that job's pair file, including each pair's `found_by`). Recall is
reported for the whole candidate step and for the v1 mechanisms alone (window LSH and the short-saying index, i.e. without
the v2 content-word signature), so the gain of the third signature is read from one truth set. README.md §Recall.

    python -B datasets/hadith-data/diagnostics/report-correspondence-v2/measure_recall_v2.py
"""

from __future__ import annotations

import csv
import random
import sys
import time
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

sys.dont_write_bytecode = True
JOB_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(JOB_DIR))

import build_report_correspondence_v2 as build  # noqa: E402
import correspondence_logic_v2 as logic2  # noqa: E402
import correspondence_logic as v1  # noqa: E402

SAMPLE_RANDOM = 300
SAMPLE_PER_MINORITY = 50
SEED = build.SEED + 1
GATE = 0.4   # every class needs residual or whole-text containment of at least this much on the shorter side
BASELINE_ORIGINS = build.ORIGIN_WINDOW | build.ORIGIN_SHORT


def band_of(verdict) -> str:
    band_class = v1.CLASS_PARTIAL if verdict.pair_class in (logic2.CLASS_PARTIAL, logic2.CLASS_QUOTED) else v1.CLASS_VARIANT
    return v1.score_band(verdict.score, band_class)


def main() -> None:
    started = time.time()
    out_dir = build.common.output_directory(f"{build.JOB}/output")
    reports, _, normalizer = build.read_corpus(started)
    vocabulary = build.Vocabulary()
    quran_keys = logic2.quran_gram_keys(build.load_quran(normalizer), vocabulary.id)
    frequent, _, id_lists = build.build_formula_inventory(reports, vocabulary, quran_keys, started)
    build.prepare_reports(reports, id_lists, frequent, quran_keys, started)
    del id_lists
    build.short_index_pairs(reports, {}, started)   # sets each short report's anchor_documents, as the build does
    eligible = [i for i, p in enumerate(reports.prepared) if p is not None]
    rng = random.Random(SEED)
    queries = set(rng.sample(eligible, SAMPLE_RANDOM))
    for tradition in ("Imami", "Zaydi", "Ibadi"):
        pool = sorted(i for i in eligible if reports.tradition[i] == tradition and i not in queries)
        queries.update(rng.sample(pool, min(SAMPLE_PER_MINORITY, len(pool))))
    queries = sorted(queries)
    postings_full: dict[int, list] = defaultdict(list)
    postings_residual: dict[int, list] = defaultdict(list)
    for q in queries:
        prepared = reports.prepared[q]
        for value in prepared.full_shingles:
            postings_full[value].append(q)
        if prepared.residual_shingles is not prepared.full_shingles:
            for value in prepared.residual_shingles:
                postings_residual[value].append(q)
    query_full = {q: set(reports.prepared[q].full_shingles) for q in queries}
    query_residual = {q: (query_full[q] if reports.prepared[q].residual_shingles is reports.prepared[q].full_shingles
                          else set(reports.prepared[q].residual_shingles)) for q in queries}
    sequence_cache = lru_cache(maxsize=4096)(lambda index: v1.shingle_hashes_at(reports.prepared[index].residual_letters))
    progress = build.progress
    progress(f"{len(queries)} query reports; exact scan of {len(eligible)} reports", started)
    truth = []
    for done, d in enumerate(eligible):
        prepared_d = reports.prepared[d]
        shared_full, shared_residual = Counter(), Counter()
        for value in prepared_d.full_shingles:
            for q in postings_full.get(value, ()):
                shared_full[q] += 1
        same_arrays = prepared_d.residual_shingles is prepared_d.full_shingles
        for value in prepared_d.residual_shingles:
            for q in (postings_full if same_arrays else postings_residual).get(value, ()):
                shared_residual[q] += 1
        for q in set(shared_full) | set(shared_residual):
            if q == d:
                continue
            prepared_q = reports.prepared[q]
            full_ok = shared_full[q] >= GATE * min(len(prepared_q.full_shingles), len(prepared_d.full_shingles))
            residual_ok = shared_residual[q] >= GATE * min(len(prepared_q.residual_shingles), len(prepared_d.residual_shingles))
            if not (full_ok or residual_ok):
                continue
            verdict = logic2.compare(prepared_q, prepared_d, query_full[q], query_residual[q],
                                     lambda q=q: sequence_cache(q), lambda d=d: sequence_cache(d))
            if verdict is not None:
                truth.append((q, d, verdict))
        if done % 25000 == 0:
            progress(f"scanned {done}", started)

    found: dict[tuple, int] = {}
    names = {name: bit for bit, name in build.ORIGIN_NAMES}
    with open(out_dir / "report_correspondence_pairs.csv", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            found[(row["hadith_id_a"], row["hadith_id_b"])] = sum(names[n] for n in row["found_by"].split("+"))
    totals, hits_all, hits_baseline = Counter(), Counter(), Counter()
    seen = set()
    for q, d, verdict in truth:
        key = tuple(sorted((reports.hadith_id[q], reports.hadith_id[d])))
        if key in seen:
            continue
        seen.add(key)
        scope = build.v1build.scope(reports, q, d)
        strata = [f"class:{verdict.pair_class}", f"scope:{scope}", f"band:{verdict.pair_class}|{band_of(verdict)}", "all"]
        if verdict.pair_class in logic2.SHOWN_CLASSES:
            strata += ["shown_classes", f"shown_classes_scope:{scope}"]
        for stratum in strata:
            totals[stratum] += 1
            origin = found.get(key)
            if origin is not None:
                hits_all[stratum] += 1
                if origin & BASELINE_ORIGINS:
                    hits_baseline[stratum] += 1
    result = {
        "query_reports": len(queries), "seed": SEED, "true_pairs_touching_queries": totals["all"],
        "note": "Truth = every pair the v2 exact scorer would keep, for pairs touching a sampled report. "
                "recall_without_content_signature counts only pairs the window LSH or the short index found.",
        "recall": {k: {"true_pairs": totals[k], "found": hits_all[k], "recall": round(hits_all[k] / totals[k], 3),
                       "found_without_content_signature": hits_baseline[k],
                       "recall_without_content_signature": round(hits_baseline[k] / totals[k], 3)}
                   for k in sorted(totals)},
    }
    build.common.write_json(out_dir, "recall_v2.json", result)
    progress(f"recall (shown classes) {result['recall'].get('shown_classes')}", started)


if __name__ == "__main__":
    main()
