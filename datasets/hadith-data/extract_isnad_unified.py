"""
datasets/hadith-data/extract_isnad_unified.py

The canonical taḥwīl-aware isnad extractor for the unified pipeline.

Replaces the three divergent paths (K6 sidecar parse, OpenITI inline,
classical Sunni `extract_classical_isnad`) with one algorithm:
candidate C — LCS-suffix branch reconstruction (winner of the Phase 0.5
algorithmic bake-off; Jaccard median 0.845, p25 0.625 on 5 fixtures).

Public surface:
  extract_isnad_branches(text_ar: str) -> list[list[str]]
  resolve_branches_to_indxs(branches: list[list[str]], resolve_narrator: Callable) -> list[list[int]]
  _compute_chain_indx(text_ar: str | None, fallback: str | None, resolve_narrator: Callable | None = None) -> str

Module-level stats dict for telemetry:
  _UNIFIED_CHAIN_STATS: dict[str, int]
    - "rows_with_text": total rows where text_ar was non-empty
    - "rows_branched": rows where >1 branch was produced
    - "branches_total": total branch count emitted
    - "narrators_attempted": total surface forms passed to resolver
    - "narrators_resolved": total surface forms that resolved to int indx
    - "fallback_used": rows where text_ar was None/empty and fallback path fired

This module owns the algorithm; `algo_candidates/candidate_C_lcs_suffix.py`
stays in place as the reference implementation for regression / future
bake-off rounds. The two MUST stay byte-equivalent on Phase 0.5 fixtures.
"""
from __future__ import annotations

import pathlib
import sys
from collections.abc import Callable
from typing import Optional

# Reuse _common.py helpers from algo_candidates/ (winner of Phase 0.5 bake-off
# imports from the same module). Per spec FR-1.1 promotion path, the helpers
# stay in algo_candidates/_common.py for this phase. If they later migrate
# under extract_isnad_unified/, flip the import.
_HERE = pathlib.Path(__file__).resolve().parent
_ALGO = _HERE / "algo_candidates"
if str(_ALGO) not in sys.path:
    sys.path.insert(0, str(_ALGO))

from _common import (  # noqa: E402
    TAHWEEL_RE,
    MATN_ANCHORS,
    split_on_tahweel,
    clean_segment,
    split_into_names,
    find_matn_start,
    name_normalize,
    is_name_token,
)


# Loose name matcher — promoted verbatim from
# `algo_candidates/candidate_B_name_span._matches`. Candidate C reuses this
# matcher; the unified extractor owns its own copy to avoid the relative-
# import dance the candidate package requires. The two implementations
# MUST stay in sync for the unified extractor to remain byte-equivalent to
# the bake-off winner on Phase 0.5 fixtures.
def _matches(a: str, b: str) -> bool:
    """Loose name match — equality, prefix/suffix, substring, or token-bag.

    Promoted verbatim from `candidate_B_name_span._matches`. See that
    module's docstring for the matching philosophy.
    """
    a = name_normalize(a)
    b = name_normalize(b)
    if a == b:
        return True
    if len(a) < 4 or len(b) < 4:
        return False
    if a in b or b in a:
        return True
    # Token-bag overlap: >= 2 shared whitespace-separated tokens of length >= 3.
    at = set(t for t in a.split() if len(t) >= 3)
    bt = set(t for t in b.split() if len(t) >= 3)
    return len(at & bt) >= 2

# --------------------------------------------------------------------------- #
# Module-level telemetry
# --------------------------------------------------------------------------- #

_UNIFIED_CHAIN_STATS: dict[str, int] = {
    "rows_with_text": 0,
    "rows_branched": 0,
    "branches_total": 0,
    "narrators_attempted": 0,
    "narrators_resolved": 0,
    "fallback_used": 0,
}


def reset_stats() -> None:
    """Zero the module-level stats dict — for tests and per-run resets."""
    for k in _UNIFIED_CHAIN_STATS:
        _UNIFIED_CHAIN_STATS[k] = 0


# --------------------------------------------------------------------------- #
# Algorithm — port of candidate_C_lcs_suffix.extract_branches
# --------------------------------------------------------------------------- #


def _longest_common_suffix(short: list[str], long: list[str]) -> int:
    """Return the length L such that the last L items of `short` align,
    in order with loose name matching, to a contiguous slice of `long`.

    Port of `candidate_C_lcs_suffix._longest_common_suffix`. Matching uses
    `_matches` (from candidate B) for tolerance to surface drift.
    """
    for L in range(min(len(short), len(long)), 0, -1):
        suf_short = short[-L:]
        for start in range(len(long) - L + 1):
            ok = True
            for k in range(L):
                if not _matches(suf_short[k], long[start + k]):
                    ok = False
                    break
            if ok:
                return L
    return 0


def extract_isnad_branches(text_ar: str | None) -> list[list[str]]:
    """FR-1.1 — Parse a classical Arabic isnad into one branch per ح-segment.

    Each branch is the ordered list of narrator surface forms from the
    initial transmitter through the shared post-convergence segment to
    the Companion / Imam / Prophet attribution point. Surface forms are
    preserved VERBATIM as they appear in `text_ar` (no normalization;
    resolution is the resolver's job).

    Algorithm: candidate C — longest-common-suffix branch reconstruction.

    Returns:
      [[]]                              if text_ar is None or empty.
      [[name, name, ...]]               if no ح-splitter (single chain;
                                        ~98.2% of corpus per Phase 0).
      [branch_a, branch_b, ...]         when N ح-splitters are present.

    Each inner list is in chain order (top of chain → Companion at end).
    """
    if not text_ar:
        return [[]]

    _UNIFIED_CHAIN_STATS["rows_with_text"] += 1

    segments = split_on_tahweel(text_ar)
    if len(segments) <= 1:
        names = split_into_names(segments[0]) if segments else []
        out = [names] if names else [[]]
        _UNIFIED_CHAIN_STATS["branches_total"] += len(out)
        return out

    per_seg = [split_into_names(s) for s in segments]
    last_idx = len(segments) - 1

    # Trim matn from the LAST segment if a matn-anchor fires inside it.
    matn_pos = find_matn_start(segments[last_idx])
    if matn_pos is not None:
        per_seg[last_idx] = split_into_names(segments[last_idx][:matn_pos])

    last_branch = per_seg[-1]
    if not last_branch:
        # No tail to stitch onto — emit whatever non-empty segments we have.
        out = [seg for seg in per_seg if seg]
        if not out:
            out = [[]]
        _UNIFIED_CHAIN_STATS["branches_total"] += len(out)
        if len(out) > 1:
            _UNIFIED_CHAIN_STATS["rows_branched"] += 1
        return out

    branches: list[list[str]] = []
    for i in range(last_idx):
        names = per_seg[i]
        if not names:
            continue
        L = _longest_common_suffix(names, last_branch)
        if L == 0:
            # No-stitch fallback for this branch — emit as-is.
            branches.append(names)
            continue
        # Re-locate the match start in last_branch so we know where the
        # shared post-convergence segment begins.
        suf_short = names[-L:]
        match_start_in_last = -1
        for start in range(len(last_branch) - L + 1):
            if all(_matches(suf_short[k], last_branch[start + k]) for k in range(L)):
                match_start_in_last = start
                break
        if match_start_in_last < 0:
            branches.append(names)
            continue
        prefix = names[:-L]
        suffix = last_branch[match_start_in_last:]
        branches.append(prefix + suffix)
    branches.append(per_seg[-1])

    # Drop any branch that wound up empty.
    branches = [b for b in branches if b]
    if not branches:
        branches = [[]]

    _UNIFIED_CHAIN_STATS["branches_total"] += len(branches)
    if len(branches) > 1:
        _UNIFIED_CHAIN_STATS["rows_branched"] += 1
    return branches


# --------------------------------------------------------------------------- #
# FR-1.2 — Resolution
# --------------------------------------------------------------------------- #


def resolve_branches_to_indxs(
    branches: list[list[str]],
    resolve_narrator: Callable[[str], Optional[int]],
) -> list[list[int]]:
    """FR-1.2 — Map each surface form to a scholar_indx via the resolver.

    Unresolved names are SKIPPED (not None-tombstoned) to keep chain_indx
    cells int-only. Empty branches after filtering are dropped.

    The resolver callback signature matches what `regen_unified_csvs.py`
    will wrap around its `resolve_narrator(surface, exact_index, blocked_index)`
    in Phase 2 — the unified extractor stays decoupled from the index
    plumbing.

    Updates `_UNIFIED_CHAIN_STATS["narrators_attempted"]` and
    `_UNIFIED_CHAIN_STATS["narrators_resolved"]`.
    """
    resolved_branches: list[list[int]] = []
    for branch in branches:
        if not branch:
            continue
        resolved: list[int] = []
        for surface in branch:
            _UNIFIED_CHAIN_STATS["narrators_attempted"] += 1
            indx = resolve_narrator(surface)
            if indx is None:
                continue
            try:
                indx_int = int(indx)
            except (TypeError, ValueError):
                continue
            resolved.append(indx_int)
            _UNIFIED_CHAIN_STATS["narrators_resolved"] += 1
        if resolved:
            resolved_branches.append(resolved)
    return resolved_branches


# --------------------------------------------------------------------------- #
# FR-3.1 — Canonical chain_indx CSV cell
# --------------------------------------------------------------------------- #


def _compute_chain_indx(
    text_ar: str | None,
    fallback: str | None = None,
    resolve_narrator: Optional[Callable[[str], Optional[int]]] = None,
) -> str:
    """FR-3.1 — Returns the canonical CSV cell value for chain_indx.

    Multi-branch format: '1,2,3|4,5,6' (commas within branch, pipes between).
    Single-branch falls back to flat 'i,j,k' (no pipe) for backwards
    compatibility — the TS loader's `parseIndices` handles both forms but
    the existing CSV has comma-only cells.

    Behavior:
      - If `text_ar` is None or empty:
          - if `fallback` is non-empty, return `fallback` verbatim and bump
            `_UNIFIED_CHAIN_STATS["fallback_used"]`. The fallback is assumed
            to be a valid chain_indx string from a sidecar.
          - otherwise return ''.
      - If `text_ar` is non-empty but `resolve_narrator` is None, raise
        ValueError — the unified pipeline always supplies a resolver; the
        parameter is optional only so callers can test the text-only
        extractor path in isolation.
      - Otherwise: extract_isnad_branches → resolve_branches_to_indxs → format.
    """
    if not text_ar:
        if fallback:
            _UNIFIED_CHAIN_STATS["fallback_used"] += 1
            return fallback
        return ""

    if resolve_narrator is None:
        raise ValueError(
            "_compute_chain_indx requires a resolve_narrator callback when "
            "text_ar is provided; got None."
        )

    branches = extract_isnad_branches(text_ar)
    resolved = resolve_branches_to_indxs(branches, resolve_narrator)
    if not resolved:
        return ""
    if len(resolved) == 1:
        return ",".join(str(i) for i in resolved[0])
    return "|".join(",".join(str(i) for i in branch) for branch in resolved)


# --------------------------------------------------------------------------- #
# Re-exports for callers + test helpers
# --------------------------------------------------------------------------- #

__all__ = [
    "extract_isnad_branches",
    "resolve_branches_to_indxs",
    "_compute_chain_indx",
    "_UNIFIED_CHAIN_STATS",
    "reset_stats",
    # Helpers re-exported so callers don't need to reach into algo_candidates.
    "TAHWEEL_RE",
    "MATN_ANCHORS",
    "name_normalize",
    "is_name_token",
]
