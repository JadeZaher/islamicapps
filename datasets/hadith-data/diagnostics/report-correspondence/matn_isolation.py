"""Isolate the matn of one corpus row with the canonical extractor's own sanad/matn boundary (README.md §Matn).

No second extractor: the boundary is extract_isnad_unified._split_on_tahweel + _matn_start, exactly as
_extract_segment_branches uses it to cut the chain. Stored text is never altered; the returned text is only compared.
"""

from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

# Methods, in precedence order.
METHOD_SOURCE_MATN_ONLY = "source_text_is_matn_only"      # Pure Canon: the source ships the chain separately
METHOD_NO_CHAIN_IN_SOURCE = "no_chain_in_source"          # reconciled sidecar: the source has no isnad
METHOD_MATN_COLUMN = "matn_column"                        # the dataset's matn_ar column
METHOD_EXTRACTOR = "extractor_boundary"                   # canonical extractor boundary on text_ar
METHOD_WHOLE_TEXT_FALLBACK = "whole_text_no_reliable_boundary"  # no chain visible at the start; flagged
METHOD_NONE = "no_usable_matn"

# Reliability labels.
RELIABLE = "reliable"
UNRELIABLE_NO_BOUNDARY = "unreliable_no_boundary_found"           # the extractor found no matn start
UNRELIABLE_SHORT_AFTER_LONG_CHAIN = "unreliable_boundary_late"    # chain prefix dominates; boundary probably late
UNRELIABLE_EXTRACTION_LIMIT = "unreliable_extraction_limit"
UNRELIABLE_EMPTY = "unreliable_empty_text"
MATN_COLUMN_NOT_IN_TEXT = "matn_column_not_in_text"               # column rejected, extractor used instead
MATN_COLUMN_INCLUDES_CHAIN = "matn_column_includes_chain"         # column starts where the text starts: rejected
COLUMN_PREFIX_LETTERS = 30

LATE_BOUNDARY_CHAIN_SHARE = 0.85   # boundary after 85 % of the text ...
LATE_BOUNDARY_MATN_CHARS = 40      # ... leaving under 40 letters of matn
LEADING_WORDS = 25                 # a fallback whole text whose first 25 words hold ...
CHAIN_LINKS_EXCLUDE = 3            # ... three or more transmission links still carries its chain


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def arabic_letters(text: str) -> str:
    """Arabic base letters only (U+0621..U+064A): the substring test ignores marks, spacing and punctuation."""
    return "".join(ch for ch in text or "" if "ء" <= ch <= "ي")


def load_sidecars(reconciled_dir: Path) -> tuple[dict, dict]:
    """(pure canon {record_id: text_ar_sha256 when text_ar_is_matn_only}, no-chain {record_id: (reason, sha)})."""
    matn_only: dict[str, str] = {}
    with gzip.open(reconciled_dir / "pure_canon_chain.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("text_ar_is_matn_only") is True:
                matn_only[row["record_id"]] = row["text_ar_sha256"]
    no_chain: dict[str, tuple[str, str]] = {}
    with gzip.open(reconciled_dir / "no_chain_in_source.jsonl.gz", "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            no_chain[row["record_id"]] = (row["reason"], row["text_ar_sha256"])
    return matn_only, no_chain


class MatnIsolator:
    def __init__(self, extractor, matn_only: dict, no_chain: dict):
        self.extractor = extractor
        self.matn_only = matn_only
        self.no_chain = no_chain
        self.sidecar_hash_mismatches = 0

    def leading_links(self, text: str) -> int:
        """Transmission links (the extractor's _LINK_RE) among the first LEADING_WORDS words."""
        head = " ".join(text.split()[:LEADING_WORDS])
        return len(self.extractor._LINK_RE.findall(head))

    def _extractor_matn(self, text_ar: str) -> tuple[str, str]:
        """Matn after the extractor's boundary; a missing or implausibly late boundary falls back to the whole last
        segment, unless that segment visibly opens with a chain (then nothing usable is returned)."""
        ex = self.extractor
        try:
            segments = ex._split_on_tahweel(text_ar)
        except ex.IsnadExtractionLimitError:
            return "", UNRELIABLE_EXTRACTION_LIMIT
        if not segments:
            return "", UNRELIABLE_EMPTY
        last = segments[-1]
        boundary = ex._matn_start(last)
        if boundary is not None:
            matn = last[boundary:].strip()
            stripped_total = sum(len(s) for s in segments)
            late = (stripped_total and (stripped_total - len(matn)) / stripped_total > LATE_BOUNDARY_CHAIN_SHARE
                    and len(matn) < LATE_BOUNDARY_MATN_CHARS)
            if not late:
                return matn, RELIABLE
            reason = UNRELIABLE_SHORT_AFTER_LONG_CHAIN
        else:
            reason = UNRELIABLE_NO_BOUNDARY
        if len(segments) > 1 or self.leading_links(last) >= CHAIN_LINKS_EXCLUDE:
            return "", reason + "_chain_present"     # the whole text would carry the chain: not usable
        return last, reason

    def isolate(self, row: dict) -> tuple[str, str, str, str]:
        """(matn text, method, reliability, note) for one corpus row."""
        record_id = row["record_id"].strip()
        text_ar = row["text_ar"] or ""
        if not text_ar.strip():
            return "", METHOD_NONE, UNRELIABLE_EMPTY, ""
        sidecar_sha = self.matn_only.get(record_id)
        if sidecar_sha is not None:
            if sidecar_sha == sha256_text(text_ar):
                return text_ar, METHOD_SOURCE_MATN_ONLY, RELIABLE, ""
            self.sidecar_hash_mismatches += 1
        no_chain = self.no_chain.get(record_id)
        if no_chain is not None:
            if no_chain[1] == sha256_text(text_ar):
                return text_ar, METHOD_NO_CHAIN_IN_SOURCE, RELIABLE, no_chain[0]
            self.sidecar_hash_mismatches += 1
        column = (row.get("matn_ar") or "").strip()
        note = ""
        if column:
            column_letters, text_letters = arabic_letters(column), arabic_letters(text_ar)
            if column_letters not in text_letters:
                note = MATN_COLUMN_NOT_IN_TEXT
            elif (text_letters.startswith(column_letters[:COLUMN_PREFIX_LETTERS])
                  and self.leading_links(column) >= CHAIN_LINKS_EXCLUDE):
                note = MATN_COLUMN_INCLUDES_CHAIN
            else:
                return column, METHOD_MATN_COLUMN, RELIABLE, ""
        matn, reliability = self._extractor_matn(text_ar)
        if not matn.strip():
            return "", METHOD_NONE, reliability, note
        method = METHOD_EXTRACTOR if reliability == RELIABLE else METHOD_WHOLE_TEXT_FALLBACK
        return matn, method, reliability, note
