"""
Candidate D — position_anchored.

Find the matn-anchor (عن النبي / قال رسول الله / etc.) in the LAST
ح-segment. Walk backward from the matn through the last branch to
identify narrators. For each earlier branch, walk backward from THEIR
end and align to the last-branch reverse-walk by name match (loose).
The aligned portion is the shared post-convergence segment.

This is the most "Arabic-grammar-aware" candidate because it uses the
matn boundary explicitly. Strongest on rows where simple intersection
fails because the convergence narrator is mentioned with different
surface forms in different branches.
"""
from __future__ import annotations
from . import _common
from .candidate_B_name_span import _matches


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

    # For each earlier branch, walk backward over last_branch from the
    # matn (i.e., end of last_branch) and try to find a name in earlier
    # branch that matches a name in last_branch. The first match (deepest
    # in chain = closest to matn) defines the convergence; the slice of
    # last_branch from that point to the end is the shared suffix.
    branches: list[list[str]] = []
    for i in range(last_idx):
        names = per_seg[i]
        if not names:
            continue
        # Iterate names in earlier branch from end backward; for each, find
        # its LATEST match position in last_branch.
        best_in_self = -1
        best_in_last = -1
        for j in range(len(names) - 1, -1, -1):
            for k in range(len(last_branch) - 1, -1, -1):
                if _matches(names[j], last_branch[k]):
                    if k > best_in_last:
                        best_in_last = k
                        best_in_self = j
                    break  # take the LATEST k for this j
            # Don't break the j loop — try all j and pick the LATEST in last
        if best_in_last < 0:
            branches.append(names)
            continue
        prefix = names[:best_in_self]  # exclusive — the convergence narrator comes from last_branch
        suffix = last_branch[best_in_last:]
        branches.append(prefix + suffix)
    branches.append(per_seg[-1])
    return branches
