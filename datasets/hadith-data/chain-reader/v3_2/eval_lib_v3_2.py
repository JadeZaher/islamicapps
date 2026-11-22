"""Shared helpers of the v3.2 re-triage evaluations (Wilson intervals, group of a work, the weighted right-rate of tranche 01's judge). Read-only; see v3_2/README.md."""

from __future__ import annotations

import csv
import math
from pathlib import Path

GROUPS = ("sunni_six_books", "imami_faqih", "imami_other_not_kafi")
RIGHT = ("R", "RO")


def wilson(k: float, n: float, z: float = 1.96) -> tuple[float, float]:
    if n <= 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def pct(k: int, n: int) -> str:
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f}% ({100 * lo:.1f}-{100 * hi:.1f})"


def weighted_rate(per_group: dict[str, tuple[int, int]], weights: dict[str, int]) -> tuple[float, tuple[float, float]]:
    """Weighted proportion over the groups (weights = each group's eligible readings) and its Wilson interval on the effective n (tranche 01's numbers_t1.py method)."""
    total = sum(weights[g] for g in per_group if per_group[g][1])
    p, variance = 0.0, 0.0
    for g, (k, n) in per_group.items():
        if not n:
            continue
        share = weights[g] / total
        p += share * k / n
        variance += share ** 2 * (k / n) * (1 - k / n) / n
    if variance == 0:
        return p, (p, p)
    n_eff = p * (1 - p) / variance
    return p, wilson(p * n_eff, n_eff)


def read_tsv(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as handle:
        return {row["id"]: row for row in csv.DictReader(handle, delimiter="\t")}


def holds_of(row: dict) -> list[str]:
    return [h for h in row["holds"].split(",") if h]
