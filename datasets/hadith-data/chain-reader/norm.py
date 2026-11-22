"""Comparison forms shared by score.py, tools/build_pilot.py and the tests (see AGENTS.md §norm)."""

import re

MARKS = re.compile(r"[ً-ٰۖ-ۭـ​-‏‪-‮﻿]")
PUNCTUATION = re.compile(r"[\s،,.:;()\[\]«»\"'*\-–—/]+")


def fold_exact(value: str) -> str:
    """Diacritic-, whitespace- and punctuation-insensitive form (punctuation inside a name counts as a space)."""
    return PUNCTUATION.sub(" ", MARKS.sub("", value)).strip()


def fold_loose(value: str) -> str:
    """fold_exact plus hamza/alef-maqsura/ta-marbuta/Persian letter folding."""
    value = fold_exact(value)
    value = re.sub("[أإآٱ]", "ا", value).replace("ى", "ي").replace("ة", "ه").replace("ی", "ي").replace("ک", "ك")
    return value


def surface_in_text(surface: str, text: str) -> bool:
    """Whether the surface's words stand in the text as whole words (loose form)."""
    needle = fold_loose(surface)
    return bool(needle) and f" {needle} " in f" {fold_loose(text)} "
