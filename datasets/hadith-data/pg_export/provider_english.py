"""Thaqalayn's own English for an Imami name (pure). Input: the diagnostic surface lexicon built by
diagnostics/chain-reconciliation/measure_imami_provider_sanad.py, which pairs each Thaqalayn English sanad sentence with
the extracted Arabic chain where both have the same number of names. See pg_export/AGENTS.md §Latin names.

A pairing is a translation alignment, never an identity, and an alignment can be shifted by one name in every report
that repeats the same chain (بكر بن عبد الله بن حبيب paired with "Tamim ibn Buhlool"). So a name takes the provider's
English only when one form (spelling variants pooled) holds at least half of its pairings, reads as a name, and renders
the same consonants (`renders`): the first word opens with the same consonant, and the Arabic name's last word is heard
after it.
"""

from __future__ import annotations

import gzip
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from transliteration import strip_marks

MINIMUM_SHARE = 0.5
_REPORTING = re.compile(r"\b(?:said|narrated|reported|informed|told|quoted|from|that|who|has|have)\b", re.IGNORECASE)
_HONORIFIC_TAIL = re.compile(r"\s*\((?:s|a|as|a\.s\.?|s\.a\.?|saw|s\.a\.w\.?|pbuh|asws|ajfs|ra)\)", re.IGNORECASE)
_CLAUSE_TAIL = re.compile(r"\s+-\s+|\s*\(|\s+(?:quoted|narrated|reported|said|who)\b", re.IGNORECASE)
_QUOTES = re.compile("[’‘`'ʿʾ]")
# Kinship and collective phrases the provider translates rather than transliterates: accepted for those keys only, the
# kinship ones only when the English says the same relation ("father" for أبيه).
_KINSHIP_KEYS = {"ابيه": "father", "جده": "father", "اخيه": "brother", "ابائه": "father", "عمه": "uncle"}
_COLLECTIVE_KEYS = {"عدة من اصحابنا", "بعض اصحابنا", "جماعة من اصحابنا", "بعض اصحابه", "رجل", "جماعة"}

_ARABIC_SKELETON = {
    "ب": "b", "ت": "t", "ث": "t", "ج": "j", "ح": "h", "خ": "k", "د": "d", "ذ": "d", "ر": "r", "ز": "z", "س": "s",
    "ش": "s", "ص": "s", "ض": "d", "ط": "t", "ظ": "z", "غ": "g", "ف": "f", "ق": "k", "ك": "k", "ل": "l", "م": "m",
    "ن": "n", "ه": "h", "و": "w", "ي": "y",
}
_CONNECTORS_AR = {"بن", "ابن", "بنت", "ابنه", "ع"}
_CONNECTORS_EN = {"ibn", "bin", "b", "bint", "son", "of", "the", "and"}


def _arabic_skeleton(word: str) -> str:
    """Consonant skeleton of an Arabic word: the article dropped, و and ي kept only word-initially (else vowels)."""
    word = re.sub("[أإآٱ]", "ا", strip_marks(word)).replace("ى", "ي").replace("ة", "")
    if word.startswith("ال") and len(word) > 3:
        word = word[2:]
    out = []
    for index, letter in enumerate(word):
        latin = _ARABIC_SKELETON.get(letter)
        if latin is None or (latin in "wy" and index > 0):
            continue
        if not out or out[-1] != latin:
            out.append(latin)
    return "".join(out)


def _english_skeleton(word: str) -> str:
    """Consonant skeleton of an English rendering: digraphs as one letter, q and c as k, inner w and y as vowels."""
    word = unicodedata.normalize("NFKD", word.lower())
    word = re.sub(r"^(?:al|el|ar|as|ad|an|az|at|ash|adh)-", "", word)
    word = re.sub(r"[^a-z]", "", word)
    word = re.sub(r"ah$", "a", word)   # ta marbuta written -ah
    for digraph, letter in (("th", "t"), ("dh", "d"), ("kh", "k"), ("sh", "s"), ("gh", "g"), ("ph", "f")):
        word = word.replace(digraph, letter)
    word = word.replace("q", "k").replace("c", "k")
    out = []
    for index, letter in enumerate(word):
        if letter in "aeiou" or (letter in "wy" and index > 0):
            continue
        if not out or out[-1] != letter:
            out.append(letter)
    return "".join(out)


def renders(arabic: str, english: str) -> bool:
    """True when the English form plausibly spells this Arabic name (not a neighbour's)."""
    arabic_words = [w for w in strip_marks(arabic).split() if w not in _CONNECTORS_AR]
    english_words = [w for w in re.split(r"[\s,]+", english) if w and w.lower().strip(".") not in _CONNECTORS_EN]
    if not arabic_words or not english_words:
        return False
    first_ar, first_en = _arabic_skeleton(arabic_words[0]), _english_skeleton(english_words[0])
    if not first_ar or not first_en or first_ar[0] != first_en[0]:
        return False
    # The last Arabic word's opening consonant must be heard after the first English word (or inside it, when the
    # English joins two words: Abu ʿAbdillah).
    last_ar = _arabic_skeleton(arabic_words[-1])[:1]
    rest = "".join(_english_skeleton(word) for word in english_words[1:]) or first_en[1:]
    return not last_ar or len(arabic_words) == 1 or last_ar in rest


def clean_form(form: str) -> str:
    """The name part of a provider form: honorific tails and a trailing reporting clause removed; a leading lowercase
    kunya (abu Ja'far) capitalized."""
    form = _HONORIFIC_TAIL.sub("", " ".join(form.split()))
    form = _CLAUSE_TAIL.split(form, maxsplit=1)[0].strip(" ,.;:-")
    return re.sub(r"^ab([ui]) ", lambda match: "Ab" + match.group(1) + " ", form)


def variant_key(form: str) -> str:
    """Spelling variants of one form compare equal: case, marks, quote characters and b./bin/ibn folded."""
    folded = "".join(char for char in unicodedata.normalize("NFKD", form.lower()) if not unicodedata.combining(char))
    folded = _QUOTES.sub("", folded)
    folded = re.sub(r"\b(?:b\.|bin|ibn)\s", "ibn ", folded)
    return " ".join(folded.split())


def chosen_form(english_forms: dict[str, int]) -> tuple[str, int, int] | None:
    """(form, its pairings, all pairings listed) for the dominant English form, or None when none dominates. Spelling
    variants are pooled; the form shown is the most frequent spelling of the dominant variant."""
    total = sum(english_forms.values())
    pooled: Counter = Counter()
    spellings: dict[str, Counter] = {}
    for raw, count in english_forms.items():
        form = clean_form(raw)
        if not form:
            continue
        key = variant_key(form)
        pooled[key] += count
        spellings.setdefault(key, Counter())[form] += count
    if not pooled:
        return None
    key, count = sorted(pooled.items(), key=lambda item: (-item[1], item[0]))[0]
    form = sorted(spellings[key].items(), key=lambda item: (-item[1], item[0]))[0][0]
    if count / total < MINIMUM_SHARE or len(form) > 80:
        return None
    if not re.search(r"[A-Za-z]", form) or re.search(r"[؀-ۿ\d]", form) or _REPORTING.search(form):
        return None
    return form, count, total


def provider_form(arabic_key: str, english_forms: dict[str, int]) -> tuple[str, int, int] | None:
    """The provider's English for one Arabic key when it dominates and renders that name; None otherwise."""
    chosen = chosen_form(english_forms)
    if chosen is None:
        return None
    if arabic_key in _COLLECTIVE_KEYS:
        return chosen
    kinship = _KINSHIP_KEYS.get(arabic_key)
    if kinship is not None:
        return chosen if kinship in chosen[0].lower() else None
    return chosen if renders(arabic_key, chosen[0]) else None


class ProviderEnglish:
    def __init__(self, path: Path):
        self.path = path
        self.forms: dict[str, tuple[str, int, int]] = {}
        self.rejected = 0
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                if not row.get("english_forms"):
                    continue
                chosen = provider_form(row["arabic_key"], row["english_forms"])
                if chosen:
                    self.forms[row["arabic_key"]] = chosen
                else:
                    self.rejected += 1

    def lookup(self, key: str) -> tuple[str, str] | None:
        """(English form, detail) for a folded Arabic key, or None."""
        hit = self.forms.get(key)
        if hit is None:
            return None
        form, count, total = hit
        return form, f"thaqalayn_english_sanad:{count}/{total}"
