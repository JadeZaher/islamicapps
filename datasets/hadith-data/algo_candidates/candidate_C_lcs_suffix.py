"""
Candidate C — lcs_suffix.

Find the LONGEST COMMON SUFFIX of the segments' name-lists. That LCS is
the shared post-convergence segment. Each branch = its pre-suffix prefix
+ the shared suffix.

This is more robust than set-intersection when narrator names drift in
surface form between branches: it works on EQUALITY between the names in
the LAST branch and a CONTIGUOUS-SUFFIX MATCH in each earlier branch,
using candidate B's loose matching.
"""
from __future__ import annotations
from . import _common
from .candidate_B_name_span import _matches


def _longest_common_suffix(short: list[str], long: list[str]) -> int:
    """Return the length L such that the last L items of `short` align,
    in order with loose-matching, to a contiguous tail of `long`.

    short is a candidate earlier branch.
    long is the last branch (which carries the full chain to the matn).
    """
    best = 0
    for L in range(min(len(short), len(long)), 0, -1):
        suf_short = short[-L:]
        # Try to align suf_short to any contiguous slice of long
        for start in range(len(long) - L + 1):
            ok = True
            for k in range(L):
                if not _matches(suf_short[k], long[start + k]):
                    ok = False
                    break
            if ok:
                return L
        # else try smaller L
    return best


def extract_branches(text_ar: str) -> list[list[str]]:
    segments = _common.split_on_tahweel(text_ar)
    if len(segments) <= 1:
        names = _common.split_into_names(segments[0]) if segments else []
        return [names] if names else []

    per_seg = [_common.split_into_names(s) for s in segments]
    last_idx = len(segments) - 1
    matn_pos = _common.find_matn_start(segments[last_idx])
    if matn_pos is not None:
        per_seg[last_idx] = _common.split_into_names(segments[last_idx][:matn_pos])

    last_branch = per_seg[-1]
    if not last_branch:
        return [seg for seg in per_seg if seg]

    branches: list[list[str]] = []
    for i in range(last_idx):
        names = per_seg[i]
        if not names:
            continue
        L = _longest_common_suffix(names, last_branch)
        if L == 0:
            # No-stitch fallback for this branch
            branches.append(names)
            continue
        # The earlier branch's prefix is everything UP TO the start of its
        # suffix match. The shared post-convergence segment comes from the
        # last_branch's CORRESPONDING slice onward (i.e., once we matched
        # `names[-L:]` to some position in last_branch, everything after
        # that position is shared).
        # Re-locate match start in last_branch:
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
        # The shared suffix = the matched slice + everything after it in last_branch
        suffix = last_branch[match_start_in_last:]
        branches.append(prefix + suffix)
    branches.append(per_seg[-1])
    return branches
