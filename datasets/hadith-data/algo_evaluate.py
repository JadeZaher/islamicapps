"""Evaluate the canonical extractor against the provenance-backed gold set."""
from __future__ import annotations

import json
import pathlib
import statistics
import sys
from collections import defaultdict
from collections.abc import Callable


BASE = pathlib.Path(__file__).resolve().parent
ROOT = BASE.parents[1]
GOLD = BASE / "__tests__" / "fixtures" / "all-tradition-isnad-gold-v1.jsonl"
OUT_MD = ROOT / ".omc" / "research" / "uniform-isnad" / "algo-evaluation.md"
MIN_FIXTURES = 30
MIN_BRANCH_COUNT_ACCURACY = 0.90
MIN_JACCARD_MEDIAN = 0.90
MIN_ORDERED_SIMILARITY_MEDIAN = 0.90
MIN_TRADITION_BRANCH_COUNT_ACCURACY = 0.80
MIN_TRADITION_ORDERED_SIMILARITY = 0.80

sys.path.insert(0, str(BASE))

from extract_isnad_unified import extract_isnad_branches, name_normalize  # noqa: E402
from algo_candidates import CANDIDATES as LEGACY_CANDIDATES  # noqa: E402


def _jaccard(left: list[str], right: list[str]) -> float:
    a = {name_normalize(value) for value in left if value.strip()}
    b = {name_normalize(value) for value in right if value.strip()}
    return 1.0 if not (a | b) else len(a & b) / len(a | b)


def _edit_distance(left: list[str], right: list[str]) -> int:
    a = [name_normalize(value) for value in left]
    b = [name_normalize(value) for value in right]
    matrix = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a) + 1):
        matrix[i][0] = i
    for j in range(len(b) + 1):
        matrix[0][j] = j
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            matrix[i][j] = min(
                matrix[i - 1][j] + 1,
                matrix[i][j - 1] + 1,
                matrix[i - 1][j - 1] + cost,
            )
    return matrix[-1][-1]


def _ordered_similarity(left: list[str], right: list[str]) -> float:
    """Return normalized narrator-sequence edit similarity in [0, 1]."""
    longest = max(len(left), len(right))
    if longest == 0:
        return 1.0
    return 1.0 - (_edit_distance(left, right) / longest)


def _align(
    actual: list[list[str]], expected: list[list[str]]
) -> list[tuple[float, float, int, list[str], list[str]]]:
    remaining = list(expected)
    aligned: list[tuple[float, float, int, list[str], list[str]]] = []
    for branch in actual:
        if not remaining:
            aligned.append((0.0, 0.0, len(branch), branch, []))
            continue
        ranked = [
            (
                (_jaccard(branch, candidate) + _ordered_similarity(branch, candidate)) / 2,
                _ordered_similarity(branch, candidate),
                _jaccard(branch, candidate),
                -index,
                index,
            )
            for index, candidate in enumerate(remaining)
        ]
        _, ordered, score, _, best_index = max(ranked)
        target = remaining.pop(best_index)
        aligned.append((score, ordered, _edit_distance(branch, target), branch, target))
    aligned.extend((0.0, 0.0, len(target), [], target) for target in remaining)
    return aligned


def _percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * fraction)
    return ordered[index]


def evaluate(
    name: str,
    extractor: Callable[[str], list[list[str]]],
    fixtures: list[dict],
) -> dict:
    branch_hits = 0
    jaccards: list[float] = []
    ordered_similarities: list[float] = []
    edits: list[int] = []
    details: list[dict] = []
    errors: list[dict] = []
    by_tradition: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {"branch_hits": [], "jaccards": [], "ordered": []}
    )
    for row in fixtures:
        try:
            actual = extractor(row["text_ar"])
        except Exception as error:  # evaluator must report, not hide, a broken row
            errors.append({"case_id": row["case_id"], "error": f"{type(error).__name__}: {error}"})
            continue
        expected = row["expected_branches"]
        branch_count_match = int(len(actual) == len(expected))
        branch_hits += branch_count_match
        aligned = _align(actual, expected)
        scores = [item[0] for item in aligned]
        ordered_scores = [item[1] for item in aligned]
        jaccards.extend(scores)
        ordered_similarities.extend(ordered_scores)
        edits.extend(item[2] for item in aligned)
        tradition = by_tradition[row["tradition"]]
        tradition["branch_hits"].append(branch_count_match)
        tradition["jaccards"].extend(scores)
        tradition["ordered"].extend(ordered_scores)
        details.append(
            {
                "case_id": row["case_id"],
                "tradition": row["tradition"],
                "branch_count_match": bool(branch_count_match),
                "mean_jaccard": statistics.mean(scores) if scores else 0.0,
                "mean_ordered_similarity": (
                    statistics.mean(ordered_scores) if ordered_scores else 0.0
                ),
                "actual": actual,
                "expected": expected,
            }
        )
    return {
        "name": name,
        "fixtures": len(fixtures),
        "errors": errors,
        "branch_count_accuracy": branch_hits / len(fixtures),
        "jaccard_median": statistics.median(jaccards) if jaccards else 0.0,
        "jaccard_p25": _percentile(jaccards, 0.25),
        "jaccard_p75": _percentile(jaccards, 0.75),
        "jaccard_mean": statistics.mean(jaccards) if jaccards else 0.0,
        "ordered_similarity_median": (
            statistics.median(ordered_similarities)
            if ordered_similarities else 0.0
        ),
        "ordered_similarity_mean": (
            statistics.mean(ordered_similarities)
            if ordered_similarities else 0.0
        ),
        "edit_median": statistics.median(edits) if edits else 0.0,
        "traditions": {
            tradition: {
                "branch_count_accuracy": statistics.mean(metrics["branch_hits"]),
                "mean_jaccard": statistics.mean(metrics["jaccards"]),
                "mean_ordered_similarity": statistics.mean(metrics["ordered"]),
            }
            for tradition, metrics in sorted(by_tradition.items())
        },
        "details": details,
    }


def _render(results: list[dict], fixture_count: int) -> str:
    lines = [
        "# Uniform isnad extraction evaluation",
        "",
        f"Fixtures: `{GOLD.relative_to(ROOT)}` ({fixture_count} provenance-backed records)",
        "",
        "The canonical release gate requires overall branch-count accuracy >= 0.90, median branch Jaccard >= 0.90, median ordered edit similarity >= 0.90, and for every tradition branch-count accuracy and mean ordered similarity >= 0.80. Legacy candidates are comparison baselines only.",
        "",
        "| Extractor | branch-count accuracy | Jaccard median | ordered median | p25 | p75 | mean | edit median | errors |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for result in results:
        lines.append(
            f"| `{result['name']}` | {result['branch_count_accuracy']:.3f} | "
            f"{result['jaccard_median']:.3f} | "
            f"{result['ordered_similarity_median']:.3f} | "
            f"{result['jaccard_p25']:.3f} | "
            f"{result['jaccard_p75']:.3f} | {result['jaccard_mean']:.3f} | "
            f"{result['edit_median']:.1f} | {len(result['errors'])} |"
        )
    canonical = results[0]
    lines.extend(["", "## Canonical tradition breakdown", ""])
    for tradition, metrics in canonical["traditions"].items():
        lines.append(
            f"- {tradition}: branch-count accuracy "
            f"`{metrics['branch_count_accuracy']:.3f}`, mean branch Jaccard "
            f"`{metrics['mean_jaccard']:.3f}`, mean ordered similarity "
            f"`{metrics['mean_ordered_similarity']:.3f}`"
        )
    lines.extend(["", "## Canonical cases below 0.80", ""])
    failures = [detail for detail in canonical["details"] if detail["mean_jaccard"] < 0.80]
    if not failures:
        lines.append("None.")
    for detail in failures:
        lines.append(
            f"- `{detail['case_id']}` ({detail['tradition']}): "
            f"mean Jaccard `{detail['mean_jaccard']:.3f}`, "
            f"mean ordered similarity `{detail['mean_ordered_similarity']:.3f}`, "
            f"branch-count match `{detail['branch_count_match']}`"
        )
    if canonical["errors"]:
        lines.extend(["", "## Canonical errors", ""])
        for error in canonical["errors"]:
            lines.append(f"- `{error['case_id']}`: {error['error']}")
    return "\n".join(lines) + "\n"


def _canonical_gate_failures(result: dict) -> list[str]:
    failures = []
    if result["errors"]:
        failures.append("canonical errors")
    if result["branch_count_accuracy"] < MIN_BRANCH_COUNT_ACCURACY:
        failures.append("overall branch-count accuracy")
    if result["jaccard_median"] < MIN_JACCARD_MEDIAN:
        failures.append("median branch Jaccard")
    if result["ordered_similarity_median"] < MIN_ORDERED_SIMILARITY_MEDIAN:
        failures.append("median ordered similarity")
    for tradition, metrics in result["traditions"].items():
        if metrics["branch_count_accuracy"] < MIN_TRADITION_BRANCH_COUNT_ACCURACY:
            failures.append(f"{tradition} branch-count accuracy")
        if metrics["mean_ordered_similarity"] < MIN_TRADITION_ORDERED_SIMILARITY:
            failures.append(f"{tradition} ordered similarity")
    return failures


def main() -> int:
    fixtures = [
        json.loads(line)
        for line in GOLD.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(fixtures) < MIN_FIXTURES:
        print(f"ERROR: gold set has {len(fixtures)} rows; requires >= {MIN_FIXTURES}", file=sys.stderr)
        return 2
    evaluated = [("canonical_uniform", extract_isnad_branches)]
    evaluated.extend((f"legacy_{name}", extractor) for name, extractor in LEGACY_CANDIDATES.items())
    results = [evaluate(name, extractor, fixtures) for name, extractor in evaluated]
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(
        _render(results, len(fixtures)), encoding="utf-8", newline="\n"
    )
    canonical = results[0]
    print(
        f"canonical_uniform fixtures={len(fixtures)} "
        f"branch_acc={canonical['branch_count_accuracy']:.3f} "
        f"jaccard_median={canonical['jaccard_median']:.3f} "
        f"ordered_median={canonical['ordered_similarity_median']:.3f} "
        f"jaccard_p25={canonical['jaccard_p25']:.3f} "
        f"errors={len(canonical['errors'])}"
    )
    return int(bool(_canonical_gate_failures(canonical)))


if __name__ == "__main__":
    raise SystemExit(main())
