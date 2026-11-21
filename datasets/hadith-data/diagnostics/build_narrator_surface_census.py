#!/usr/bin/env python3
"""J1: census of every distinct unresolved narrator surface in the corpus (diagnostic only).

Reuses the exact resolver path of audit_narrator_resolution.py (extract_isnad_branches +
regen.narrator_normalize + build_narrator_index) so totals reconcile with
sanad_resolution_audit.json. Writes only under diagnostics/narrator-resolution/.

Usage: python -B diagnostics/build_narrator_surface_census.py
"""

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import diagnostic_common as common  # noqa: E402
from narrator_surface_logic import CATEGORY_ORDER, categorize_surface  # noqa: E402

JOB = "narrator-resolution"
CURVE_POINTS = (10, 50, 100, 250, 500, 1000, 2000, 5000, 10000, 20000)
CONTEXT_SHARE = 0.8
START, END = "<START>", "<END>"


def smallest_set_reaching(counts: list[int], share: float) -> int:
    """Number of largest contexts needed to cover `share` of a surface's occurrences."""
    total = sum(counts)
    running = 0
    for needed, count in enumerate(sorted(counts, reverse=True), 1):
        running += count
        if running >= share * total:
            return needed
    return len(counts)


def main() -> None:
    started = time.time()
    regen = common.load_regen()
    extractor = common.load_extractor()
    resolve, exact_index, blocked_index = common.build_resolver(regen)
    norm_cache: dict[str, str] = {}

    def normalize(raw: str) -> str:
        cached = norm_cache.get(raw)
        if cached is None:
            cached = sys.intern(regen.narrator_normalize(raw))
            norm_cache[raw] = cached
        return cached

    attempted = Counter()
    unresolved_by_tradition: dict[str, Counter] = defaultdict(Counter)
    occurrences: Counter = Counter()
    by_tradition: dict[str, Counter] = defaultdict(Counter)
    by_source: dict[str, Counter] = defaultdict(Counter)
    raw_examples: dict[str, list] = defaultdict(list)
    example_rows: dict[str, list] = defaultdict(list)
    teacher_context: Counter = Counter()
    student_context: Counter = Counter()
    surface_source_teacher: Counter = Counter()
    row_unresolved: list[tuple[str, tuple]] = []
    metrics = Counter()
    rows_by_tradition = defaultdict(Counter)

    for row_number, row in common.iter_corpus_rows():
        tradition = common.clean(row.get("tradition")) or "<missing>"
        source = common.clean(row.get("source")) or "<missing>"
        metrics["rows"] += 1
        rows_by_tradition[tradition]["rows"] += 1
        try:
            branches = extractor.extract_isnad_branches(row.get("text_ar") or "")
        except extractor.IsnadExtractionLimitError:
            metrics["rows_extraction_limited"] += 1
            continue
        if not branches:
            metrics["rows_without_extracted_chain"] += 1
            rows_by_tradition[tradition]["rows_without_extracted_chain"] += 1
            continue
        metrics["rows_with_extracted_chain"] += 1
        rows_by_tradition[tradition]["rows_with_extracted_chain"] += 1
        row_surfaces: set[str] = set()
        for branch in branches:
            norms = [normalize(raw) for raw in branch]
            for position, (raw, norm) in enumerate(zip(branch, norms)):
                metrics["surfaces_attempted"] += 1
                attempted[tradition] += 1
                if resolve(norm):
                    continue
                metrics["unresolved_surface_occurrences"] += 1
                unresolved_by_tradition[tradition]["occurrences"] += 1
                occurrences[norm] += 1
                by_tradition[norm][tradition] += 1
                by_source[norm][source] += 1
                examples = raw_examples[norm]
                if raw not in examples and len(examples) < 3:
                    examples.append(raw)
                refs = example_rows[norm]
                if len(refs) < 5 and not any(ref["line"] == row_number for ref in refs):
                    refs.append(common.row_reference(row_number, row))
                teacher = norms[position + 1] if position + 1 < len(norms) else END
                student = norms[position - 1] if position > 0 else START
                teacher_context[(norm, teacher)] += 1
                student_context[(norm, student)] += 1
                surface_source_teacher[(norm, source, teacher)] += 1
                row_surfaces.add(norm)
        if row_surfaces:
            metrics["rows_with_unresolved_surface"] += 1
            row_unresolved.append((tradition, tuple(row_surfaces)))
        else:
            metrics["rows_fully_resolved"] += 1
            rows_by_tradition[tradition]["rows_fully_resolved"] += 1

    ranked = sorted(occurrences.items(), key=lambda item: (-item[1], item[0]))
    rank_of = {norm: rank for rank, (norm, _) in enumerate(ranked)}
    total_unresolved = metrics["unresolved_surface_occurrences"]

    # Group contexts per surface.
    teachers_by_surface: dict[str, list] = defaultdict(list)
    for (norm, teacher), count in teacher_context.items():
        teachers_by_surface[norm].append((count, teacher))
    students_by_surface: dict[str, list] = defaultdict(list)
    for (norm, student), count in student_context.items():
        students_by_surface[norm].append((count, student))
    triples_by_surface: dict[str, list] = defaultdict(list)
    for (norm, source, teacher), count in surface_source_teacher.items():
        triples_by_surface[norm].append(count)

    # Row-level curve under the atomic rule: a row completes once its worst-ranked surface is reviewed.
    worst_rank_by_tradition: dict[str, list] = defaultdict(list)
    for tradition, surfaces in row_unresolved:
        worst_rank_by_tradition[tradition].append(max(rank_of[norm] for norm in surfaces))
    row_curve = {}
    for points in (0,) + CURVE_POINTS + (len(ranked),):
        entry = {"rows_fully_resolvable": 0, "by_tradition": {}}
        for tradition in sorted(rows_by_tradition):
            baseline = rows_by_tradition[tradition]["rows_fully_resolved"]
            gained = sum(1 for worst in worst_rank_by_tradition.get(tradition, ()) if worst < points)
            entry["by_tradition"][tradition] = baseline + gained
            entry["rows_fully_resolvable"] += baseline + gained
        row_curve[str(points)] = entry

    # Per-surface blocked-candidate counts (prefix/kunya candidates, never identities).
    blocked_counts = {norm: len(regen.narrator_resolution_candidates(norm, blocked_index))
                      for norm, _ in ranked}

    coverage = []
    cumulative = 0
    cumulative_by_rank = []
    for norm, count in ranked:
        cumulative += count
        cumulative_by_rank.append(cumulative)
    for points in CURVE_POINTS + (len(ranked),):
        covered = cumulative_by_rank[min(points, len(ranked)) - 1]
        coverage.append({"top_n_surfaces": min(points, len(ranked)), "occurrences_covered": covered,
                         "percent_of_unresolved": round(100 * covered / total_unresolved, 1)})

    categories = defaultdict(lambda: {"occurrences": 0, "distinct": 0})
    category_of = {}
    for norm, count in ranked:
        category = categorize_surface(norm)
        category_of[norm] = category
        categories[category]["occurrences"] += count
        categories[category]["distinct"] += 1

    candidate_tiers = {}
    for top in (500, 2000):
        tiers = {"0": [0, 0], "1": [0, 0], "2-5": [0, 0], ">5": [0, 0]}
        for norm, count in ranked[:top]:
            found = blocked_counts[norm]
            key = "0" if found == 0 else "1" if found == 1 else "2-5" if found <= 5 else ">5"
            tiers[key][0] += 1
            tiers[key][1] += count
        candidate_tiers[str(top)] = {k: {"surfaces": v[0], "occurrences": v[1]} for k, v in tiers.items()}

    unit_counts = {}
    for top in (100, 500, 2000):
        scope = [norm for norm, _ in ranked[:top]]
        unit_counts[str(top)] = {
            "distinct_surface_teacher_contexts": sum(len(teachers_by_surface[n]) for n in scope),
            "teacher_contexts_covering_80pct_per_surface": sum(
                smallest_set_reaching([c for c, _ in teachers_by_surface[n]], CONTEXT_SHARE) for n in scope),
            "distinct_surface_source_units": sum(len(by_source[n]) for n in scope),
            "distinct_surface_source_teacher_triples": sum(len(triples_by_surface[n]) for n in scope),
            "surface_source_teacher_triples_covering_80pct_per_surface": sum(
                smallest_set_reaching(triples_by_surface[n], CONTEXT_SHARE) for n in scope),
        }

    frequency = Counter(count for _, count in ranked)
    never_single = sum(categories[c]["occurrences"] for c in ("relational_or_fragment", "collective_or_anonymous"))
    after_audit = common.DIAGNOSTICS_DIR / JOB / "sanad_resolution_audit_after_adoption.json"
    audit_path = after_audit if after_audit.exists() else common.HADITH_DATA_DIR / "sanad_resolution_audit.json"
    audit_metrics = json.loads(audit_path.read_text(encoding="utf-8"))["metrics"]
    reconciliation = {
        key: {"this_run": metrics[key], "sanad_resolution_audit": audit_metrics[key],
              "equal": metrics[key] == audit_metrics[key]}
        for key in ("rows", "rows_with_extracted_chain", "rows_without_extracted_chain",
                    "rows_extraction_limited", "rows_fully_resolved", "rows_with_unresolved_surface",
                    "surfaces_attempted", "unresolved_surface_occurrences")
    }

    out = common.output_directory(JOB)
    inputs = common.input_fingerprints(common.CORPUS_PATH, common.REGISTRY_PATH)
    header = common.header_object(JOB, "python -B datasets/hadith-data/diagnostics/build_narrator_surface_census.py", inputs)

    def census_rows():
        cumulative_running = 0
        for rank, (norm, count) in enumerate(ranked, 1):
            cumulative_running += count
            yield {
                "rank": rank,
                "surface_normalized": norm,
                "raw_examples": raw_examples[norm],
                "occurrences": count,
                "cumulative_occurrences": cumulative_running,
                "cumulative_share_of_unresolved": round(cumulative_running / total_unresolved, 5),
                "category": category_of[norm],
                "by_tradition": dict(by_tradition[norm].most_common()),
                "by_source_top10": dict(by_source[norm].most_common(10)),
                "teacher_contexts_top10": [[s, c] for c, s in sorted(teachers_by_surface[norm], key=lambda x: (-x[0], x[1]))[:10]],
                "student_contexts_top10": [[s, c] for c, s in sorted(students_by_surface[norm], key=lambda x: (-x[0], x[1]))[:10]],
                "example_rows": example_rows[norm],
                "blocked_candidate_count": blocked_counts[norm],
                "status": "unreviewed_census_row",
            }

    census_count = common.write_jsonl(out, "surface_census.jsonl.gz", census_rows(), gzipped=True)
    curve = {
        "header": header,
        "reconciliation_audit_file": common.relative_path(audit_path),
        "reconciliation_with_sanad_resolution_audit": reconciliation,
        "totals": {**dict(metrics), "distinct_unresolved_surfaces": len(ranked),
                   "unresolved_by_tradition": {t: c["occurrences"] for t, c in sorted(unresolved_by_tradition.items())},
                   "attempted_by_tradition": dict(sorted(attempted.items()))},
        "occurrence_coverage_curve": coverage,
        "frequency_shape": {"singletons": frequency[1],
                            "surfaces_10_or_more": sum(v for k, v in frequency.items() if k >= 10),
                            "surfaces_50_or_more": sum(v for k, v in frequency.items() if k >= 50)},
        "row_curve_atomic_upper_bound": row_curve,
        "categories": {c: categories[c] for c in CATEGORY_ORDER if c in categories},
        "occurrences_that_can_never_become_one_registry_id": never_single,
        "blocked_candidate_availability": candidate_tiers,
        "review_unit_counts": unit_counts,
        "seconds": round(time.time() - started, 1),
    }
    common.write_json(out, "surface_curve.json", curve)
    print(json.dumps({"census_rows": census_count, "seconds": curve["seconds"],
                      "reconciliation_all_equal": all(v["equal"] for v in reconciliation.values())}))


if __name__ == "__main__":
    main()
