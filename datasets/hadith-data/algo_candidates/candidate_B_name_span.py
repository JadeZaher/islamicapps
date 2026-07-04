"""
Candidate B — name_span.

Like A but with looser name matching: a name token in one branch matches
a name token in another if EITHER is a prefix/suffix of the other. This
catches:
  - سفيان matches سفيان بن عيينة
  - سماك matches سماك بن حرب
  - ابن بريدة matches عبد الله بن بريدة
"""
from __future__ import annotations
from . import _common


def _matches(a: str, b: str) -> bool:
    """Loose name match — either prefix-of, suffix-of, or whole-substring of."""
    a = _common.name_normalize(a)
    b = _common.name_normalize(b)
    if a == b:
        return True
    if len(a) < 4 or len(b) < 4:
        return False
    if a in b or b in a:
        return True
    # Token-bag overlap: ≥2 shared whitespace-separated tokens of length ≥3
    at = set(t for t in a.split() if len(t) >= 3)
    bt = set(t for t in b.split() if len(t) >= 3)
    return len(at & bt) >= 2


def _find_matching_index(needle: str, haystack: list[str]) -> int:
    for i, h in enumerate(haystack):
        if _matches(needle, h):
            return i
    return -1


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

    if not per_seg or not per_seg[-1]:
        return [seg for seg in per_seg if seg]

    # Convergence detection: for each branch i (except the last), find the
    # LATEST position in branch i that matches ANY name in the last branch.
    # The matched name in the last branch is the convergence; everything
    # after it in the last branch is the shared suffix.
    last_branch = per_seg[-1]
    branches: list[list[str]] = []
    # Track the LATEST convergence position across all earlier branches in
    # the LAST branch — this determines the shared suffix length.
    latest_conv_in_last = -1

    earlier_conv: list[int] = []  # convergence index in branch i itself
    earlier_conv_in_last: list[int] = []  # convergence index in last branch
    for i in range(last_idx):
        best_self = -1
        best_in_last = -1
        for j, name in enumerate(per_seg[i]):
            in_last_idx = _find_matching_index(name, last_branch)
            if in_last_idx >= 0:
                # Prefer the LATEST occurrence (deepest in chain)
                if in_last_idx > best_in_last:
                    best_in_last = in_last_idx
                    best_self = j
        earlier_conv.append(best_self)
        earlier_conv_in_last.append(best_in_last)
        if best_in_last > latest_conv_in_last:
            latest_conv_in_last = best_in_last

    if latest_conv_in_last < 0:
        # No-stitch fallback
        return [seg for seg in per_seg if seg]

    shared_suffix = last_branch[latest_conv_in_last + 1:]

    for i in range(last_idx):
        ci = earlier_conv[i]
        if ci < 0:
            # this branch never matched — keep its names raw
            branches.append(per_seg[i])
            continue
        prefix = per_seg[i][:ci + 1]
        # The shared suffix should include intermediary narrators between
        # this branch's convergence point and the last branch's convergence
        # point. Pull them from the last branch in [this branch's match in
        # last_branch + 1 : latest_conv_in_last] inclusive.
        my_match_in_last = earlier_conv_in_last[i]
        bridge = last_branch[my_match_in_last + 1: latest_conv_in_last + 1] if my_match_in_last < latest_conv_in_last else []
        branches.append(prefix + bridge + shared_suffix)

    # The last branch always gets its full self
    branches.append(per_seg[-1])

    return branches
