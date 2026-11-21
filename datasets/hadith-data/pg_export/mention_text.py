"""Where a chain mention sits in its report's own Arabic (pure, standard library). See pg_export/AGENTS.md §Latin names.

The extractor stores each surface without harakat or tatweel; the report text is byte-faithful, so the vowel marks a
name carries are recovered by finding the surface again in the text with the marks skipped, at word boundaries, in
chain order. Also answers whether an honorific marker (ع, عليه السلام, ...) follows the name in the text.
"""

from __future__ import annotations

import re
from typing import Sequence

from transliteration import MARK

ARABIC_LETTER = re.compile(r"[ء-يٱ-ۓ]")
# An honorific right after a name: ع, (ع), عليه/عليها/عليهما/عليهم السلام, صلوات الله عليه.
HONORIFIC_AFTER = re.compile(
    r"^[\s\-–—(\[]*(?:ع(?![ء-ي])|عليه(?:ما|م|ا)?\s*ال?سلام|صلوات\s+الله\s+عليه|صلى\s+الله\s+عليه)")


class PlainText:
    """The text with marks removed, and the original index of every kept character."""

    def __init__(self, text: str):
        self.original = text or ""
        kept: list[str] = []
        self.index: list[int] = []
        for position, char in enumerate(self.original):
            if MARK.match(char):
                continue
            kept.append(char)
            self.index.append(position)
        self.plain = "".join(kept)

    def find_word(self, surface: str, start: int = 0) -> int:
        """First plain-text offset >= start where `surface` stands as whole words; -1 when absent."""
        if not surface:
            return -1
        position = self.plain.find(surface, start)
        while position >= 0:
            before = self.plain[position - 1] if position > 0 else " "
            end = position + len(surface)
            after = self.plain[end] if end < len(self.plain) else " "
            if not ARABIC_LETTER.match(before) and not ARABIC_LETTER.match(after):
                return position
            position = self.plain.find(surface, position + 1)
        return -1

    def original_span(self, start: int, length: int) -> str:
        """The original characters (marks included, trailing marks of the last letter too) for a plain-text span."""
        first = self.index[start]
        last = self.index[start + length - 1] + 1
        while last < len(self.original) and MARK.match(self.original[last]):
            last += 1
        return self.original[first:last]

    def honorific_after(self, start: int, length: int) -> bool:
        """True when an honorific marker follows the span in the text (or ends the surface itself)."""
        return bool(HONORIFIC_AFTER.match(self.plain[start + length:]))


def locate_mentions(text: PlainText, surfaces: Sequence[str]) -> list[tuple[int, int] | None]:
    """(plain start, length) of each surface of one branch, searched in chain order; None when not found as written."""
    spans: list[tuple[int, int] | None] = []
    cursor = 0
    for surface in surfaces:
        # The extractor writes a following (ع)/عليه السلام as ' ع'; the name itself is found without it.
        name = re.sub(r"\s+\(?ع\)?$", "", surface or "").strip() or surface
        position = text.find_word(name, cursor)
        if position < 0:
            position = text.find_word(name, 0)   # a branch after a tahwil may restart from the text's opening
        if position < 0:
            spans.append(None)
            continue
        spans.append((position, len(name)))
        cursor = position + len(name)
    return spans


def surface_has_honorific(surface: str) -> bool:
    """The surface itself ends with the abbreviation (`أبي عبد الله ع`)."""
    return bool(re.search(r"(?:^|\s)\(?ع\)?$", surface or ""))
