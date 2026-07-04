"""
Candidate A — simple_set.

Original FR-1.1 proposal. Verb-split tokenizer, set-intersection on
_norm'd tokens to find convergence narrator. The Phase 0 / T-0.3 audit
showed this only succeeds ~30% of the time; included here as baseline.
"""
from __future__ import annotations
from . import _common


def extract_branches(text_ar: str) -> list[list[str]]:
    segments = _common.split_on_tahweel(text_ar)
    if len(segments) <= 1:
        names = _common.split_into_names(segments[0]) if segments else []
        return [names] if names else []

    # Per-segment name lists
    per_seg = [_common.split_into_names(s) for s in segments]
    # Drop the matn-tail from the LAST segment (heuristic: matn-anchor cuts it)
    last_idx = len(segments) - 1
    matn_pos = _common.find_matn_start(segments[last_idx])
    if matn_pos is not None:
        last_with_matn_cut = segments[last_idx][:matn_pos]
        per_seg[last_idx] = _common.split_into_names(last_with_matn_cut)

    # Find convergence narrator: a token appearing in ALL segments
    norm_sets = [set(_common.name_normalize(n) for n in seg) for seg in per_seg]
    if not norm_sets:
        return []
    shared = set.intersection(*norm_sets) if all(norm_sets) else set()
    if not shared:
        # No-stitch fallback: emit each branch as truncated
        return [seg for seg in per_seg if seg]

    # For each branch, find LAST occurrence of any shared name; everything
    # after it (in the LAST branch) is the shared suffix.
    def last_idx_of_shared(names: list[str]) -> int:
        for i in range(len(names) - 1, -1, -1):
            if _common.name_normalize(names[i]) in shared:
                return i
        return -1

    convergence_idxs = [last_idx_of_shared(seg) for seg in per_seg]
    # Shared suffix taken from the LAST branch
    last_branch = per_seg[-1]
    last_conv_idx = convergence_idxs[-1]
    shared_suffix = last_branch[last_conv_idx + 1:] if last_conv_idx >= 0 else []

    branches: list[list[str]] = []
    for i, names in enumerate(per_seg):
        ci = convergence_idxs[i]
        if ci < 0:
            branches.append(names)
            continue
        prefix = names[:ci + 1]
        branches.append(prefix + shared_suffix)
    return branches
