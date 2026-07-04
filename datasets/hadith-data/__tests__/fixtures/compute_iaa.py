"""
Compute inter-annotator agreement (IAA) over taḥwīl annotation files.

Reads ≥2 JSONL annotation files. For each hadith_id present in ≥2 files,
computes:
  - Krippendorff's α (primary; unit = (hadith_id, branch_index, position),
    distance = binary 0/1 on _norm match)
  - Cohen's κ (secondary; unit = hadith_id, value = frozenset of _norm'd
    narrator surfaces across all branches)

Krippendorff's α is implemented inline (no PyPI dependency). The formula used:

    α = 1 - (D_o / D_e)

where D_o is the observed disagreement (mean over units of the fraction of
coder-pairs that disagree on that unit) and D_e is the expected disagreement
under the null hypothesis that all coders draw independently from the marginal
value distribution. Distance is binary: 0 if _norm(a) == _norm(b), 1 otherwise.
Missing data (one annotator's branch was shorter) is handled via a MISSING
sentinel that is treated as distinct from all real values.

Cohen's κ uses the standard (p_o − p_e) / (1 − p_e) formula on a
flattened narrator-set view: each unit is a hadith_id and the value is
the frozenset of unique _norm'd narrator surfaces across all that hadith's
branches. For >2 annotators, pairwise κ values are averaged.

Usage:
  python compute_iaa.py --annotators <file1.jsonl> <file2.jsonl> [<file3.jsonl>...]
                       [--out <path>] [--threshold 0.80]

Default out: docs/annotation/iaa-report-<YYYY-MM-DD>.md
Threshold defaults to 0.80 (used for the pass/fail header line).
Exit 0 if α >= threshold AND κ >= threshold, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
import pathlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from itertools import combinations
from typing import Any

# ---------------------------------------------------------------------------
# Import _norm from classify_attribution.py (three levels up from fixtures/).
# ---------------------------------------------------------------------------
_DATASETS_DIR = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_DATASETS_DIR))
from classify_attribution import _norm  # noqa: E402

# Sentinel for missing annotations (annotator had no value for this unit).
MISSING = "__MISSING__"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_annotations(path: pathlib.Path) -> dict[str, list[list[str]]]:
    """Return {hadith_id: expected_branches} from a JSONL annotation file."""
    result: dict[str, list[list[str]]] = {}
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid JSON — {exc}") from exc
            hid = row.get("hadith_id")
            branches = row.get("expected_branches")
            if hid is None or branches is None:
                continue
            result[str(hid)] = branches
    return result


# ---------------------------------------------------------------------------
# Krippendorff's α (inline, binary distance, ≥2 coders)
# ---------------------------------------------------------------------------

def _build_units(
    all_anns: list[tuple[str, dict[str, list[list[str]]]]],
) -> dict[tuple[str, int, int], dict[str, str]]:
    """
    Build the unit → {annotator_name: _norm'd value} mapping.

    Unit = (hadith_id, branch_index, position).
    Value = _norm(surface) or MISSING if that annotator lacks the slot.

    MISSING is written for an annotator when:
    - They have the hadith_id and the branch_index, but their branch is shorter
      than another annotator's (so the extra positions are absent in their data).
    - They have the hadith_id but fewer branches than another annotator.
    - They do not have the hadith_id at all (handled in _krippendorff_alpha
      by restricting to shared_ids before building units).
    """
    # Pass 1: record every explicitly-present (hid, bi, pos) → value.
    unit_values: dict[tuple[str, int, int], dict[str, str]] = defaultdict(dict)
    for ann_name, anns in all_anns:
        for hid, branches in anns.items():
            for bi, branch in enumerate(branches):
                for pos, surface in enumerate(branch):
                    unit_values[(hid, bi, pos)][ann_name] = _norm(surface)

    # Pass 2: for every unit that exists, mark MISSING for any annotator that
    # has the hadith_id (so they were "present" for this row) but simply had a
    # shorter branch or fewer branches — i.e. they never wrote a value for this
    # (bi, pos) slot.  This ensures shorter-branch annotators are penalised.
    ann_map: dict[str, dict[str, list[list[str]]]] = {name: anns for name, anns in all_anns}
    for (hid, bi, pos), coder_map in unit_values.items():
        for ann_name, anns in ann_map.items():
            if ann_name not in coder_map and hid in anns:
                # Annotator has this hadith_id but missed this (bi, pos).
                coder_map[ann_name] = MISSING

    return unit_values


def _krippendorff_alpha(
    all_anns: list[tuple[str, dict[str, list[list[str]]]]],
    shared_ids: set[str],
) -> float:
    """
    Compute Krippendorff's α over units restricted to shared_ids.

    Handles missing data via MISSING sentinel; missing slots are excluded
    from per-unit pair counts but included in the marginal distribution
    only when both annotators are present for a unit.
    """
    ann_names = [name for name, _ in all_anns]

    # Filter each annotator's data to shared_ids only.
    filtered: list[tuple[str, dict[str, list[list[str]]]]] = [
        (name, {hid: branches for hid, branches in anns.items() if hid in shared_ids})
        for name, anns in all_anns
    ]

    unit_values = _build_units(filtered)

    # Collect units that have ≥2 coders with known values (including MISSING
    # sentinel).  A unit where one annotator has a real value and another has
    # MISSING counts as a disagreement — the MISSING sentinel is a distinct
    # value, per spec.  We include units where the total number of annotators
    # that "touched" the hadith_id is ≥2 (at least one real + one MISSING is
    # enough).
    valid_units: list[dict[str, str]] = []
    for unit_key, coder_map in unit_values.items():
        # Fill MISSING for annotators who had no entry for this unit.
        full_map: dict[str, str] = {}
        for name in ann_names:
            full_map[name] = coder_map.get(name, MISSING)
        # Require ≥2 coders assigned any value (real or MISSING).
        if len(full_map) >= 2:
            valid_units.append(full_map)

    if not valid_units:
        return float("nan")

    # --- D_o: observed disagreement ---
    # For each unit, fraction of coder-pairs that disagree.
    # MISSING is treated as a distinct value: (real_value, MISSING) is a
    # disagreement.  All annotators (including those with MISSING) participate
    # in the pair count.
    d_o_sum = 0.0
    unit_count_with_pairs = 0
    for coder_map in valid_units:
        all_entries = list(coder_map.items())  # includes MISSING entries
        if len(all_entries) < 2:
            continue
        pairs = list(combinations(all_entries, 2))
        disagree = sum(1 for (_, va), (_, vb) in pairs if va != vb)
        d_o_sum += disagree / len(pairs)
        unit_count_with_pairs += 1

    if unit_count_with_pairs == 0:
        return float("nan")
    D_o = d_o_sum / unit_count_with_pairs

    # --- D_e: expected disagreement from marginal distribution ---
    # Count every (annotator, unit) value across all valid units, including
    # MISSING entries — MISSING is a value in the marginal distribution.
    value_counts: Counter[str] = Counter()
    for coder_map in valid_units:
        for v in coder_map.values():
            value_counts[v] += 1

    n = sum(value_counts.values())
    if n <= 1:
        return float("nan")

    # D_e = Σ_{v ≠ v'} n_v * n_{v'} / (n*(n-1))
    # Equivalent to (n^2 - Σ n_v^2) / (n*(n-1))
    sum_sq = sum(c * c for c in value_counts.values())
    D_e = (n * n - sum_sq) / (n * (n - 1))

    if D_e == 0.0:
        # All annotations agree (only one value) → perfect agreement.
        return 1.0

    return 1.0 - D_o / D_e


# ---------------------------------------------------------------------------
# Cohen's κ (secondary, flattened narrator-set view, ≥2 coders pairwise mean)
# ---------------------------------------------------------------------------

def _narrator_set(branches: list[list[str]]) -> frozenset[str]:
    """Unique _norm'd narrator surfaces across all branches of one hadith."""
    return frozenset(_norm(s) for branch in branches for s in branch)


def _cohen_kappa_pair(
    ann_a: dict[str, list[list[str]]],
    ann_b: dict[str, list[list[str]]],
    shared_ids: list[str],
) -> float:
    """Compute Cohen's κ for two annotators on the shared hadith_ids."""
    if not shared_ids:
        return float("nan")
    n = len(shared_ids)
    sets_a = [_narrator_set(ann_a[hid]) for hid in shared_ids]
    sets_b = [_narrator_set(ann_b[hid]) for hid in shared_ids]

    # p_o: fraction of units where both sets are identical.
    p_o = sum(1 for sa, sb in zip(sets_a, sets_b) if sa == sb) / n

    # p_e: expected agreement under independence of each annotator's marginals.
    counts_a: Counter[frozenset[str]] = Counter(sets_a)
    counts_b: Counter[frozenset[str]] = Counter(sets_b)
    all_vals = set(counts_a) | set(counts_b)
    p_e = sum((counts_a[v] / n) * (counts_b[v] / n) for v in all_vals)

    if p_e >= 1.0:
        return 1.0 if p_o >= 1.0 else 0.0

    return (p_o - p_e) / (1.0 - p_e)


# ---------------------------------------------------------------------------
# Dataclass + main computation
# ---------------------------------------------------------------------------

@dataclass
class IAAReport:
    alpha: float
    kappa_mean: float
    per_pair: list[tuple[str, str, float, float, int]]  # (ann_a, ann_b, alpha, kappa, n_shared)
    n_units: int
    n_disagreements: int
    disagreements: list[dict[str, Any]]  # truncated to 50, for rendering
    shared_hadith_ids: list[str]


def compute_iaa(files: list[pathlib.Path], threshold: float = 0.80) -> IAAReport:
    """
    Compute IAA across ≥2 annotation files.

    Returns an IAAReport with aggregate α/κ, per-pair scores, and
    a (capped) disagreement table.
    """
    if len(files) < 2:
        raise ValueError("At least 2 annotation files are required.")

    # Build unique annotator labels. When two files share the same filename
    # (e.g., the self-test case), append an index so labels never collide.
    raw_names = [f.name for f in files]
    seen: dict[str, int] = {}
    unique_names: list[str] = []
    for name in raw_names:
        if raw_names.count(name) > 1:
            count = seen.get(name, 0)
            unique_names.append(f"{name}[{count}]")
            seen[name] = count + 1
        else:
            unique_names.append(name)
            seen[name] = 1

    all_anns: list[tuple[str, dict[str, list[list[str]]]]] = [
        (unique_names[i], load_annotations(f)) for i, f in enumerate(files)
    ]

    # --- Shared hadith_ids (present in ≥2 annotators) ---
    from collections import Counter as _Counter
    id_counts: _Counter[str] = _Counter()
    for _, anns in all_anns:
        for hid in anns:
            id_counts[hid] += 1
    shared_ids = sorted(hid for hid, c in id_counts.items() if c >= 2)

    if not shared_ids:
        raise ValueError("No shared hadith_ids found across annotators.")

    # --- Per-pair scores ---
    per_pair: list[tuple[str, str, float, float, int]] = []
    pairs = list(combinations(range(len(all_anns)), 2))
    for i, j in pairs:
        name_a, anns_a = all_anns[i]
        name_b, anns_b = all_anns[j]
        pair_shared = sorted(set(anns_a) & set(anns_b))
        pair_ann_list = [(name_a, anns_a), (name_b, anns_b)]
        pair_alpha = _krippendorff_alpha(pair_ann_list, set(pair_shared))
        pair_kappa = _cohen_kappa_pair(anns_a, anns_b, pair_shared)
        per_pair.append((name_a, name_b, pair_alpha, pair_kappa, len(pair_shared)))

    # --- Aggregate α (all coders together over all shared ids) ---
    agg_alpha = _krippendorff_alpha(all_anns, set(shared_ids))

    # --- Aggregate κ (mean pairwise) ---
    valid_kappas = [k for _, _, _, k, _ in per_pair if not (k != k)]  # exclude nan
    kappa_mean = sum(valid_kappas) / len(valid_kappas) if valid_kappas else float("nan")

    # --- Unit count and disagreements ---
    filtered_anns = [
        (name, {hid: branches for hid, branches in anns.items() if hid in set(shared_ids)})
        for name, anns in all_anns
    ]
    unit_values = _build_units(filtered_anns)
    ann_names = [name for name, _ in all_anns]

    n_units = 0
    disagreements: list[dict[str, Any]] = []
    for (hid, bi, pos), coder_map in sorted(unit_values.items()):
        present = {n: coder_map.get(n, MISSING) for n in ann_names if coder_map.get(n, MISSING) != MISSING}
        if len(present) < 2:
            continue
        n_units += 1
        vals = list(present.values())
        if len(set(vals)) > 1:
            row: dict[str, Any] = {"hadith_id": hid, "branch": bi, "position": pos}
            for ann_name, val in present.items():
                row[ann_name] = val
            disagreements.append(row)

    n_disagreements = len(disagreements)
    capped = disagreements[:50]

    return IAAReport(
        alpha=agg_alpha,
        kappa_mean=kappa_mean,
        per_pair=per_pair,
        n_units=n_units,
        n_disagreements=n_disagreements,
        disagreements=capped,
        shared_hadith_ids=shared_ids,
    )


# ---------------------------------------------------------------------------
# Report renderer
# ---------------------------------------------------------------------------

_INTERPRET = """\
## How to interpret

- α >= 0.80: consensus level; rows are reproducible across annotators.
- 0.67 <= α < 0.80: marginal; investigate which case types triggered disagreement.
- α < 0.67: substantial disagreement; revisit guide §3–§4 or escalate ambiguous rows to difficulty 5.
"""


def render_report(
    report: IAAReport,
    out_path: pathlib.Path,
    threshold: float = 0.80,
    ann_files: list[pathlib.Path] | None = None,
) -> None:
    """Write the IAA Markdown report to out_path."""
    today = date.today().isoformat()
    n_ann = len(report.per_pair[0]) and (
        # count unique names from per_pair
        len({n for pair in report.per_pair for n in (pair[0], pair[1])})
    )
    ann_names_str = (
        ", ".join(f"`{f.name}`" for f in ann_files) if ann_files else "N/A"
    )

    def pf(val: float, t: float) -> str:
        if val != val:  # nan
            return "N/A"
        return "PASS" if val >= t else "FAIL"

    alpha_str = f"{report.alpha:.3f}" if report.alpha == report.alpha else "N/A"
    kappa_str = f"{report.kappa_mean:.3f}" if report.kappa_mean == report.kappa_mean else "N/A"

    lines = [
        f"# IAA Report — {today}",
        "",
        f"**Annotators:** {n_ann} ({ann_names_str})",
        f"**Shared hadith_ids:** {len(report.shared_hadith_ids)}",
        f"**Total units (triples):** {report.n_units}",
        f"**Krippendorff's α:** {alpha_str} ({pf(report.alpha, threshold)} at threshold {threshold})",
        f"**Cohen's κ (mean pairwise):** {kappa_str} ({pf(report.kappa_mean, threshold)} at threshold {threshold})",
        "",
    ]

    if len(report.shared_hadith_ids) < 20:
        lines += [
            f"> **WARN:** Only {len(report.shared_hadith_ids)} shared hadith_ids found. "
            "Fewer than 20 shared rows yields noisy estimates; results should be "
            "interpreted with caution.",
            "",
        ]

    lines += ["## Per-pair scores", ""]
    lines.append("| Pair | α | κ | n shared rows |")
    lines.append("|---|---:|---:|---:|")
    for name_a, name_b, pair_alpha, pair_kappa, n_shared in report.per_pair:
        a_s = f"{pair_alpha:.3f}" if pair_alpha == pair_alpha else "N/A"
        k_s = f"{pair_kappa:.3f}" if pair_kappa == pair_kappa else "N/A"
        lines.append(f"| {name_a} ↔ {name_b} | {a_s} | {k_s} | {n_shared} |")
    lines.append("")

    triples_agree = report.n_units - report.n_disagreements
    lines += [
        "## Aggregate",
        "",
        f"- Total triples computed: {report.n_units}",
        f"- Triples in full agreement: {triples_agree}",
        f"- Triples with partial disagreement: {report.n_disagreements}",
        f"- Pass rate at α >= {threshold}: {'yes' if report.alpha >= threshold else 'no'}",
        "",
    ]

    lines += ["## Disagreements", ""]
    if not report.disagreements:
        lines.append("_No disagreements found._")
    else:
        # Build header from keys (hadith_id, branch, position, then annotator names).
        sample = report.disagreements[0]
        ann_cols = [k for k in sample if k not in ("hadith_id", "branch", "position")]
        header = "| hadith_id | branch | position | " + " | ".join(ann_cols) + " |"
        sep = "|---|---:|---:|" + "|".join(["---"] * len(ann_cols)) + "|"
        lines.append(header)
        lines.append(sep)
        for row in report.disagreements:
            cells = [str(row.get("hadith_id", "")), str(row.get("branch", "")), str(row.get("position", ""))]
            for col in ann_cols:
                cells.append(str(row.get(col, "")))
            lines.append("| " + " | ".join(cells) + " |")
        if report.n_disagreements > 50:
            lines.append(f"")
            lines.append(f"_Showing first 50 of {report.n_disagreements} disagreements._")
    lines.append("")

    lines.append(_INTERPRET)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_out() -> pathlib.Path:
    today = date.today().isoformat()
    repo_root = pathlib.Path(__file__).resolve().parents[4]
    return repo_root / "docs" / "annotation" / f"iaa-report-{today}.md"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute Krippendorff's α and Cohen's κ over taḥwīl annotation files."
    )
    parser.add_argument(
        "--annotators",
        nargs="+",
        required=True,
        metavar="FILE",
        help="Two or more JSONL annotation files.",
    )
    parser.add_argument(
        "--out",
        default=None,
        metavar="PATH",
        help="Output path for the Markdown report (default: docs/annotation/iaa-report-<date>.md).",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.80,
        help="Pass/fail threshold for both α and κ (default: 0.80).",
    )
    args = parser.parse_args()

    files = [pathlib.Path(f) for f in args.annotators]
    for f in files:
        if not f.exists():
            print(f"ERROR: file not found: {f}", file=sys.stderr)
            return 2

    out_path = pathlib.Path(args.out) if args.out else _default_out()

    try:
        report = compute_iaa(files, threshold=args.threshold)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    render_report(report, out_path, threshold=args.threshold, ann_files=files)

    # Summary to stdout.
    alpha_s = f"{report.alpha:.4f}" if report.alpha == report.alpha else "N/A"
    kappa_s = f"{report.kappa_mean:.4f}" if report.kappa_mean == report.kappa_mean else "N/A"
    print(f"Krippendorff's α : {alpha_s}")
    print(f"Cohen's κ (mean) : {kappa_s}")
    print(f"Shared hadith_ids: {len(report.shared_hadith_ids)}")
    print(f"Total units      : {report.n_units}")
    print(f"Disagreements    : {report.n_disagreements}")
    print(f"Report written to: {out_path}")

    passed = (
        report.alpha == report.alpha and report.alpha >= args.threshold
        and report.kappa_mean == report.kappa_mean and report.kappa_mean >= args.threshold
    )
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
