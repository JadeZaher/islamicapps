"""Spelling and epithet folds of the v3.2 tool (copy of v3_1/norm_v3_1.py; see v3_2/AGENTS.md §folds, v3_2/FOLDS.md): what two spellings of one name have in common.

`fold_chars` keeps an index map so a surface found in the folded text is returned in the text's own characters.
`link_key` is the comparison form of one link, used by canonical(): equivalent readings compare equal.
"""

from __future__ import annotations

import bisect
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from norm import MARKS  # noqa: E402  (v1: diacritics, tatweel, zero-width; read-only import)

PUNCTUATION = re.compile(r"[\s،,.:;()\[\]«»\"'*\-–—/‘’“”…!?؟]+")   # same set as `PUNCT` in v3/build_context_v3.cjs

CHAR_FOLD = str.maketrans({
    "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ی": "ي", "ې": "ي", "ے": "ي", "ئ": "ي",
    "ک": "ك", "ة": "ه", "ھ": "ه", "ہ": "ه", "ە": "ه", "ؤ": "و",
})
DELETED = {"ء"}                                    # a bare hamza carries no letter of its own
KUNYA_CASE = {"ابي": "ابو", "ابا": "ابو", "ذي": "ذو", "ذا": "ذو", "اخي": "اخو", "اخا": "اخو"}
KUNYA_PATTERN = {"ابو": "اب[ويا]", "ابي": "اب[ويا]", "ابا": "اب[ويا]", "ذو": "ذ[ويا]", "ذي": "ذ[ويا]", "ذا": "ذ[ويا]",
                 "اخو": "اخ[ويا]", "اخي": "اخ[ويا]", "اخا": "اخ[ويا]"}
IMAM_LAQAB = {"الصادق", "الباقر", "الكاظم", "الرضا", "الجواد", "الهادي", "العسكري", "السجاد"}   # folded; an Imam's laqab alone, or after his kunya/ism («أبو الحسن الرضا»), names the same link
EPITHETS = {"الكاتب", "العدل", "الفقيه", "الشيخ", "القاضي", "الحافظ", "الامام", "المعروف", "المقرى", "المقري", "الضرير"}   # folded; trailing titles that are not part of a name
HONORIFIC_WORDS = re.compile(r"(?:^| )(?:صلي الله عليه وآله وسلم|صلي الله عليه وسلم|صلي الله عليه واله وسلم|عليه السلام|عليها السلام|عليهم السلام|عليهما السلام|رضي الله عنه|رضي الله عنها|رضي الله عنهم|رحمه الله|رحمهم الله|ع)(?= |$)")


def fold_chars(text: str) -> tuple[str, list[int]]:
    """The text with marks, tatweel and a bare hamza removed and letter variants folded, and for each kept character its index in `text`."""
    kept, index = [], []
    for i, ch in enumerate(text):
        if MARKS.match(ch) or ch in DELETED:
            continue
        kept.append(ch.translate(CHAR_FOLD))
        index.append(i)
    return "".join(kept), index


def fold_v3(value: str) -> str:
    """Letters-only comparison form: variants folded, punctuation one space, kunya case (أبو/أبي/أبا) folded."""
    folded, _ = fold_chars(value)
    folded = PUNCTUATION.sub(" ", folded).strip()
    return " ".join(KUNYA_CASE.get(token, token) for token in folded.split())


def folded_cursor(index: list[int], original_end: int) -> int:
    """Position in the folded text of an offset in the original text: the number of kept characters before it."""
    return bisect.bisect_left(index, original_end)


TITLE_PREFIXES = (("ام", "المومنين"), ("امير", "المومنين"))    # folded: «أم المؤمنين عائشة» = «عائشة», «أمير المؤمنين علي» = «علي»; the title alone stays a name
TRAILING_RELATION = ("امراه", "ابيه")                              # «أم محمد امرأة أبيه» = «أم محمد»
KUNYA_START = ("ابو", "ام")                                        # «أبو عمر صاحب أبي العباس ثعلب» = «أبو عمر»: «صاحب» is cut only after a kunya


def appended_epithet_cut(tokens: list[str]) -> list[str]:
    """Drop what is appended to a name and is not part of it: «X مولى Y» (a patron, any name before it), «ابو/ام X صاحب Y» (a companion of another man) and a trailing «امرأة أبيه»."""
    for index in range(1, len(tokens)):
        if tokens[index] == "مولي" or (tokens[index] == "صاحب" and tokens[0] in KUNYA_START and index >= 2):
            return tokens[:index]
    if len(tokens) >= 4 and tuple(tokens[-2:]) == TRAILING_RELATION:
        return tokens[:-2]
    return tokens


def _tokens(surface: str) -> list[str]:
    value = HONORIFIC_WORDS.sub(" ", " " + fold_v3(surface) + " ").strip()
    return value.split()


def link_key(surface: str) -> str:
    """Comparison form of a link in canonical(): fold_v3, an attached «و» and a bare «و» before the name dropped, a trailing epithet
    («الكاتب», «العدل») and a trailing nisba (ال…ي, or its dual ال…يان after at least two name words) dropped, so «…الشجاعي الكاتب» equals «…الشجاعي».
    v3.2 adds: «لل» for «ال» after an attached «ل» («للرضا»), an Imam's laqab alone for «أبو الحسن الرضا» (no «بن» in the name), and a case-ending alif
    («جابرا» = «جابر», four letters or more) folded on the last word."""
    tokens = _tokens(surface)
    if tokens and tokens[0] == "و":
        tokens = tokens[1:]
    if tokens and len(tokens[0]) > 2 and tokens[0].startswith("و"):
        tokens[0] = tokens[0][1:]
    if tokens and len(tokens[0]) > 3 and tokens[0].startswith("لل"):
        tokens[0] = "ال" + tokens[0][2:]                    # للرضا = ل + الرضا
    if len(tokens) > 2 and tuple(tokens[:2]) in TITLE_PREFIXES:
        tokens = tokens[2:]                                 # v3.2: a title before the name
    tokens = appended_epithet_cut(tokens)                   # v3.2: a patron, a companion or a relation appended to the name
    while len(tokens) > 2 and tokens[-1] in EPITHETS:
        tokens.pop()
    if len(tokens) >= 3 and re.fullmatch(r"ال[ء-ي]{3,}ي(?:ان|ين)?", tokens[-1]) and tokens[-2] != "بن":
        tokens.pop()
    if len(tokens) >= 2 and tokens[-1] in IMAM_LAQAB and "بن" not in tokens[:-1]:
        tokens = tokens[-1:]
    if tokens and len(tokens[-1]) >= 4 and tokens[-1].endswith("ا"):
        tokens[-1] = tokens[-1][:-1]                        # a case-ending alif; «الرضا» and «جابرا» fold alike on both sides
    return " ".join(tokens)


def same_man(first: str, second: str) -> bool:
    """Two neighbouring names that are one man written twice: equal keys of two or more words, or the short form of the long one
    («المعتمر», then «معتمر بن سليمان»: the article marks it as a short form; or a short form of two or more words)."""
    a, b = link_key(first).split(), link_key(second).split()
    if not a or not b:
        return False
    if a == b:
        return len(a) >= 2
    short, long_ = (a, b) if len(a) <= len(b) else (b, a)
    article = short[0].startswith("ال")
    stem = ([short[0][2:]] + short[1:]) if article else short
    long_stem = ([long_[0][2:]] + long_[1:]) if long_[0].startswith("ال") else long_
    if stem == long_stem[: len(stem)] and len(long_stem) > len(stem) and long_stem[len(stem)] == "بن":
        return article or len(stem) >= 2
    return False
