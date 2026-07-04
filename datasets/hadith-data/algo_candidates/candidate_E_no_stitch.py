"""
Candidate E — no_stitch.

The 'do nothing' baseline. Emit each ح-segment as an independent
truncated branch. Any candidate worth shipping must beat this on the
post-convergence segment metric (since E loses everything after the
splitter).
"""
from __future__ import annotations
from . import _common


def extract_branches(text_ar: str) -> list[list[str]]:
    segments = _common.split_on_tahweel(text_ar)
    if not segments:
        return []
    per_seg = [_common.split_into_names(s) for s in segments]
    last_idx = len(segments) - 1
    matn_pos = _common.find_matn_start(segments[last_idx]) if segments else None
    if matn_pos is not None:
        per_seg[last_idx] = _common.split_into_names(segments[last_idx][:matn_pos])
    return [seg for seg in per_seg if seg]
