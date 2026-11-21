"""Pure logic for finding Qur'an quotations in report text (see README.md in this directory).

Nothing here reads files except `load_tanzil`, and nothing writes. Method: both sides are folded to a letters-only
skeleton (project normalizer plus Qur'an-specific orthographic folds), the Qur'an skeletons are indexed by letter
k-grams, and maximal exact matches are extended from seeds at hadith word starts.
"""

from __future__ import annotations

import bisect
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
HADITH_DATA = HERE.parent
sys.path.insert(0, str(HADITH_DATA))
sys.path.insert(0, str(HADITH_DATA.parent))
import regen_unified_csvs as _regen  # noqa: E402  (canonical project normalizer, imported at run time)

SEED_LETTERS = 10          # k-gram length used to seed a match (about three words once alef is folded away)
MIN_SPAN_LETTERS = 10      # a recorded span is at least this many skeleton letters (shorter cannot be seeded)

# --- Qur'an-specific orthographic folds ---------------------------------------------------------------------------
# Applied on top of `narrator_normalize` (vocalization, tatweel, alef/ya variants, NFKC, format controls), to BOTH
# sides, for comparison only. Uthmani and imla'i spellings differ in where an alef is written (dagger alef, alef
# khanjariyya, alef wasla, madda), so every alef is dropped; hamza and its seats (alef, waw, ya carriers) are dropped
# because the two orthographies seat it differently; ta marbuta becomes ta because Uthmani writes open ta in places
# (رحمت) where imla'i writes ة; Persian/Urdu letter shapes become the Arabic letters.
QURANIC_FOLDS = {
    "ا": "", "ء": "", "ؤ": "", "ئ": "",
    "ة": "ت", "ۃ": "ت",
    "ی": "ي", "ے": "ي", "ى": "ي",
    "ک": "ك", "ھ": "ه", "ہ": "ه", "ە": "ه",
}


def project_normalize(text: str) -> str:
    """The project's own comparison normalizer (NFKC, format controls, vocalization, tatweel, alef and ya variants)."""
    return _regen.narrator_normalize(text)


def fold_quranic_orthography(normalized: str) -> str:
    """Qur'an orthographic folds on text already passed through `project_normalize`."""
    return "".join(QURANIC_FOLDS.get(char, char) for char in normalized)


def _is_skeleton_letter(char: str) -> bool:
    return "ء" <= char <= "ي" and char != "ـ"


def skeleton_of_char(char: str) -> str:
    """Skeleton text one character contributes: letters, a space for a separator, nothing for a mark."""
    produced = []
    for item in fold_quranic_orthography(project_normalize(char)):
        if _is_skeleton_letter(item):
            produced.append(item)
        elif unicodedata.category(item) in ("Mn", "Me", "Mc", "Cf") or item == "ـ":
            continue
        else:
            produced.append(" ")
    return "".join(produced)


class _SkeletonTable(dict):
    """str.translate table that computes each distinct character once, through `skeleton_of_char`."""

    def __missing__(self, code: int) -> str:
        value = skeleton_of_char(chr(code))
        self[code] = value
        return value


_TABLE = _SkeletonTable()


def skeleton_words(text: str) -> list[str]:
    """The comparison words of `text`: maximal runs of skeleton letters between separators."""
    return (text or "").translate(_TABLE).split()


@dataclass
class Skeleton:
    letters: str                 # all words concatenated
    word_starts: list[int]       # letter offset where each word starts
    word_ends: list[int]         # exclusive


def build_skeleton(text: str) -> Skeleton:
    words = skeleton_words(text)
    starts, ends, position = [], [], 0
    for word in words:
        starts.append(position)
        position += len(word)
        ends.append(position)
    return Skeleton("".join(words), starts, ends)


def letter_origins(text: str) -> list[int]:
    """Offset in `text` of every skeleton letter (same order as `Skeleton.letters`)."""
    origins = []
    for offset, char in enumerate(text or ""):
        origins.extend([offset] * sum(1 for item in _TABLE[ord(char)] if item != " "))
    return origins


# --- The Qur'an -------------------------------------------------------------------------------------------------


@dataclass
class QuranStream:
    """One edition's skeleton as a single string (suras separated by '#'), with verse boundaries."""
    edition: str
    letters: str
    verse_starts: list[int]                      # stream offset of each verse's first letter
    verses: list[tuple[int, int]]                # (sura, aya) parallel to verse_starts
    verse_letter_origins: list[list[int]]        # per verse: char offset in the verse text of each skeleton letter
    verse_texts: list[str]
    index: dict = field(default_factory=dict)    # k-gram -> positions
    word_start: bytearray = field(default_factory=bytearray)   # 1 where an edition word starts (stream offset)
    word_end: bytearray = field(default_factory=bytearray)     # 1 at an exclusive word end

    def verse_at(self, position: int) -> tuple[int, int]:
        return self.verses[bisect.bisect_right(self.verse_starts, position) - 1]

    def verse_index_at(self, position: int) -> int:
        return bisect.bisect_right(self.verse_starts, position) - 1


def parse_tanzil(lines) -> list[tuple[int, int, str]]:
    """`sura|aya|text` rows of a Tanzil txt-2 file; '#' comment lines and blanks are skipped."""
    rows = []
    for line in lines:
        line = line.rstrip("\r\n")
        if not line or line.startswith("#"):
            continue
        sura, aya, text = line.split("|", 2)
        rows.append((int(sura), int(aya), text))
    return rows


def build_stream(edition: str, rows: list[tuple[int, int, str]], seed_letters: int = SEED_LETTERS) -> QuranStream:
    pieces, verse_starts, verses, origins, texts, bounds = [], [], [], [], [], []
    position, previous_sura = 0, None
    for sura, aya, text in rows:
        if previous_sura is not None and sura != previous_sura:
            pieces.append("#")
            position += 1
        previous_sura = sura
        letters = skeleton_words(text)
        joined = "".join(letters)
        edge = position
        for word in letters:
            bounds.append((edge, edge + len(word)))
            edge += len(word)
        verse_starts.append(position)
        verses.append((sura, aya))
        texts.append(text)
        origins.append(letter_origins(text))
        pieces.append(joined)
        position += len(joined)
    stream = QuranStream(edition, "".join(pieces), verse_starts, verses, origins, texts)
    stream.word_start, stream.word_end = bytearray(position + 2), bytearray(position + 2)
    for begin, finish in bounds:
        stream.word_start[begin] = 1
        stream.word_end[finish] = 1
    letters, index = stream.letters, stream.index
    for offset in range(len(letters) - seed_letters + 1):
        key = letters[offset:offset + seed_letters]
        if "#" not in key:
            index.setdefault(key, []).append(offset)
    return stream


def load_tanzil(directory: Path) -> dict[str, QuranStream]:
    """Both Tanzil editions (simple-clean, imla'i; uthmani) as indexed streams."""
    streams = {}
    for edition in ("simple-clean", "uthmani"):
        with open(directory / f"quran-{edition}.txt", encoding="utf-8", newline="") as handle:
            streams[edition] = build_stream(edition, parse_tanzil(handle))
    return streams


# --- Matching ---------------------------------------------------------------------------------------------------


@dataclass
class Span:
    start_letter: int            # skeleton letter offsets in the report [start, end)
    end_letter: int
    words: int
    candidates: list[dict]       # [{edition, sura, aya_from, aya_to, quran_text}]


def _quran_text(stream: QuranStream, first: int, last: int) -> tuple[tuple[int, int], tuple[int, int], str]:
    """Verse range and the edition's own text covering stream letters [first, last]."""
    v_first, v_last = stream.verse_index_at(first), stream.verse_index_at(last)
    parts = []
    for verse in range(v_first, v_last + 1):
        origins = stream.verse_letter_origins[verse]
        text = stream.verse_texts[verse]
        verse_start = stream.verse_starts[verse]
        low = max(first, verse_start) - verse_start
        high = min(last, verse_start + len(origins) - 1) - verse_start
        begin, end = widen_over_silent(text, origins[low], origins[high] + 1)
        parts.append(text[begin:end])
    return stream.verses[v_first], stream.verses[v_last], " ".join(parts)


def _trim_to_word_boundaries(skeleton: Skeleton, stream: QuranStream, a: int, b: int, delta: int):
    """Shrink [a, b) to the longest interval that starts and ends on a report word boundary AND on a word boundary of
    the Qur'an edition at the matching stream offsets (`delta` = stream offset minus report offset)."""
    starts, ends = skeleton.word_starts, skeleton.word_ends
    first = bisect.bisect_left(starts, a)
    while first < len(starts) and starts[first] < b and not stream.word_start[starts[first] + delta]:
        first += 1
    last = bisect.bisect_right(ends, b) - 1
    while last >= first and last >= 0 and not stream.word_end[ends[last] + delta]:
        last -= 1
    if first >= len(starts) or last < first or ends[last] <= starts[first]:
        return None
    return starts[first], ends[last]


def find_spans(skeleton: Skeleton, stream: QuranStream, seed_letters: int = SEED_LETTERS,
               min_letters: int = MIN_SPAN_LETTERS) -> list[Span]:
    """Maximal exact matches of the report skeleton against one Qur'an stream.

    Seeds sit at report word starts; each seed occurrence is extended both ways at letter level, the interval is
    trimmed inward to report word boundaries, and the longest trimmed interval wins. All Qur'an occurrences that
    cover that interval are kept as candidates (repeated verses are never resolved here).
    """
    letters, quran = skeleton.letters, stream.letters
    starts, ends = skeleton.word_starts, skeleton.word_ends
    spans: list[Span] = []
    floor = 0                        # letters before this are already inside an accepted span
    word = 0
    while word < len(starts):
        seed = starts[word]
        if seed < floor:
            word = bisect.bisect_left(starts, floor, word)
            continue
        if seed + seed_letters > len(letters):
            break
        positions = stream.index.get(letters[seed:seed + seed_letters])
        if not positions:
            word += 1
            continue
        best = None                  # (trimmed length, a, b)
        raw = []
        for position in positions:
            forward = seed_letters
            while (seed + forward < len(letters) and position + forward < len(quran)
                   and letters[seed + forward] == quran[position + forward]):
                forward += 1
            backward = 0
            while (seed - backward - 1 >= floor and position - backward - 1 >= 0
                   and letters[seed - backward - 1] == quran[position - backward - 1]):
                backward += 1
            delta = position - seed
            trimmed = _trim_to_word_boundaries(skeleton, stream, seed - backward, seed + forward, delta)
            if trimmed is None:
                continue
            raw.append((delta, seed - backward, seed + forward))
            if best is None or trimmed[1] - trimmed[0] > best[0]:
                best = (trimmed[1] - trimmed[0], trimmed[0], trimmed[1])
        if best is None or best[0] < min_letters:
            word += 1
            continue
        _, a, b = best
        candidates, seen = [], set()
        for delta, raw_start, raw_end in raw:
            if raw_start > a or raw_end < b:          # the occurrence does not cover the winning interval
                continue
            if not (stream.word_start[a + delta] and stream.word_end[b + delta]):
                continue                              # same letters, but not on this edition's word boundaries
            first, last = a + delta, b + delta - 1
            if "#" in quran[first:last + 1]:
                continue
            (s1, a1), (s2, a2), text = _quran_text(stream, first, last)
            if s1 != s2:
                continue
            key = (s1, a1, a2)
            if key in seen:
                continue
            seen.add(key)
            candidates.append({"edition": stream.edition, "sura": s1, "aya_from": a1, "aya_to": a2,
                               "quran_text": text})
        if not candidates:
            word += 1
            continue
        candidates.sort(key=lambda c: (c["sura"], c["aya_from"], c["aya_to"]))
        words = bisect.bisect_left(starts, b) - bisect.bisect_left(starts, a)
        spans.append(Span(a, b, words, candidates))
        floor = b
        word = bisect.bisect_left(starts, b, word)
    return spans


def merge_editions(per_edition: list[list[Span]]) -> list[Span]:
    """One non-overlapping span list from several editions: identical intervals pool their candidates, the longest
    interval wins an overlap."""
    pooled: dict[tuple[int, int], Span] = {}
    for spans in per_edition:
        for span in spans:
            key = (span.start_letter, span.end_letter)
            if key in pooled:
                known = {(c["sura"], c["aya_from"], c["aya_to"]) for c in pooled[key].candidates}
                for candidate in span.candidates:
                    if (candidate["sura"], candidate["aya_from"], candidate["aya_to"]) not in known:
                        pooled[key].candidates.append(candidate)
            else:
                pooled[key] = Span(span.start_letter, span.end_letter, span.words, list(span.candidates))
    accepted: list[Span] = []
    for span in sorted(pooled.values(), key=lambda s: (-(s.end_letter - s.start_letter), s.start_letter)):
        if all(span.end_letter <= other.start_letter or span.start_letter >= other.end_letter for other in accepted):
            accepted.append(span)
    accepted.sort(key=lambda s: s.start_letter)
    for span in accepted:
        span.candidates.sort(key=lambda c: (c["sura"], c["aya_from"], c["aya_to"], c["edition"]))
    return accepted


def widen_over_silent(text: str, start: int, end: int) -> tuple[int, int]:
    """Widen [start, end) over characters the skeleton drops but that belong to the edge words: marks, tatweel and
    silent letters (alef, hamza and seats), so a quotation never starts or ends in the middle of a word."""
    while start > 0 and _TABLE[ord(text[start - 1])] == "" and unicodedata.category(text[start - 1]) != "Cf":
        start -= 1
    while end < len(text) and _TABLE[ord(text[end])] == "" and unicodedata.category(text[end]) != "Cf":
        end += 1
    return start, end


def original_offsets(text: str, origins: list[int], span: Span) -> tuple[int, int]:
    """[start, end) in the stored text for a span, widened over silent characters at both edges."""
    return widen_over_silent(text, origins[span.start_letter], origins[span.end_letter - 1] + 1)


# --- Formulae and cues ------------------------------------------------------------------------------------------

# Phrases spoken as formulae, not quoted as scripture. Written normally; compared as skeletons.
FORMULAE = {
    "basmala": "بسم الله الرحمن الرحيم",
    "hamdala": "الحمد لله رب العالمين",
    "tahlil": "لا إله إلا الله",
    "tahlil_wahdahu": "لا إله إلا الله وحده لا شريك له",
    "istirja": "إنا لله وإنا إليه راجعون",
    "hasbala": "حسبنا الله ونعم الوكيل",
    "tawfiq": "وما توفيقي إلا بالله",
    "inshallah": "إن شاء الله",
    "subhan": "سبحان الله",
    "sami_allah": "سمعنا وأطعنا",
    "taawwudh_phrase": "أعوذ بالله من الشيطان الرجيم",
    "lahu_al_mulk": "له الملك وله الحمد وهو على كل شيء قدير",
    "yuhyi_wa_yumit": "يحيي ويميت وهو على كل شيء قدير",
    "radiya_anhum": "رضي الله عنهم",
    "radiya_anhu_wa_radu": "رضي الله عنهم ورضوا عنه",
    "rabbana_atina": "ربنا آتنا في الدنيا حسنة وفي الآخرة حسنة وقنا عذاب النار",
    "salla": "صلوا عليه وسلموا تسليما",
    "ya_ayyuha_alladhina_amanu": "يا أيها الذين آمنوا",
    "ya_ayyuha_alnas": "يا أيها الناس",
}


def formula_skeletons() -> dict[str, str]:
    return {name: "".join(skeleton_words(text)) for name, text in FORMULAE.items()}


_FORMULA_SKELETONS = None


def formula_of(span_skeleton: str) -> str | None:
    """Name of the formula whose skeleton contains the span's (or equals it), else None."""
    global _FORMULA_SKELETONS
    if _FORMULA_SKELETONS is None:
        _FORMULA_SKELETONS = formula_skeletons()
    for name, skeleton in _FORMULA_SKELETONS.items():
        if span_skeleton in skeleton:
            return name
    return None


BRACKETS = "﴾﴿{}"   # ornate parentheses U+FD3E/U+FD3F (either logical order occurs) and sunnah.com's braces
_AYAH_END_MARK = "۝"
_EPITHET = r"(?:\s*(?:عز وجل|عزوجل|تبارك وتعالي|سبحانه وتعالي|جل ثناؤه|جل وعلا|تعالي|سبحانه))*"
_INTRODUCER = re.compile(
    r"(?<![ء-ي])[وف]?(?:قال الله|قال تعالي|قال عز وجل|قال جل|قوله|قول الله|فانزل الله|انزل الله|انزلت|"
    r"نزلت|نزل|تلا|وتلا|فتلا|قرا|وقرا|فقرا|يقرا|الاية|اية|كتاب الله|في كتابه|يقول الله|يقول تعالي|"
    r"صدق الله|قرانا|وهو قول|في قول|فاني قراتها)" + _EPITHET + r"[\s\W]*$")
_AFTER = re.compile(r"^[\s\W]{0,6}(?:الاية|اية|حتي بلغ|الي قوله|الي اخر الاية|الي قول|سورة|ثم تلا|ونحوه)")
_QUOTE_OPEN, _QUOTE_CLOSE = "«\"“([{<", "»\"”)]}>"


def sura_key(name: str) -> str:
    return "".join(skeleton_words(name))


def cues_around(text: str, start: int, end: int, sura_names: list[str]) -> list[dict]:
    """Cues for a quotation at text[start:end]: what the surrounding text says about it. Each cue is
    {kind, text} with kind one of brackets, ayah_end_mark, introducer, aya_word_after, sura_named,
    quote_marks."""
    cues = []
    before, after = text[max(0, start - 14):start], text[end:end + 14]
    if any(char in BRACKETS for char in before + after):
        cues.append({"kind": "brackets", "text": (before + "…" + after).strip()})
    if _AYAH_END_MARK in text[end:end + 6] or _AYAH_END_MARK in text[max(0, start - 3):start]:
        cues.append({"kind": "ayah_end_mark", "text": _AYAH_END_MARK})
    near_before = project_normalize(text[max(0, start - 90):start])
    match = _INTRODUCER.search(near_before)
    if match:
        cues.append({"kind": "introducer", "text": match.group(0).strip(" :،,-")})
    near_after = project_normalize(text[end:end + 40])
    match = _AFTER.match(near_after)
    if match:
        cues.append({"kind": "aya_word_after", "text": match.group(0).strip()})
    window = " ".join(skeleton_words(text[max(0, start - 120):start])[-10:] + skeleton_words(text[end:end + 90])[:10])
    for name in sura_names:
        if name and re.search(r"(?<![ء-ي])سورت\s+" + re.escape(name), window):
            cues.append({"kind": "sura_named", "text": name})
            break
    near = text[max(0, start - 3):start].strip(" ‏‎")[-1:], text[end:end + 3].strip(" ‏‎")[:1]
    if near[0] and near[0] in _QUOTE_OPEN and near[1] and near[1] in _QUOTE_CLOSE and not cues:
        cues.append({"kind": "quote_marks", "text": near[0] + near[1]})
    return cues


STRONG_CUES = {"brackets", "ayah_end_mark", "introducer", "sura_named", "aya_word_after"}


# --- Classification ---------------------------------------------------------------------------------------------
# Parameters measured against hadith-kg's markings (README.md, "Choosing the parameters").
PARAMS = {
    "common_phrase_reports": 15,   # an uncued phrase of at most `common_phrase_max_words` seen in this many reports
    "common_phrase_max_words": 6,
    "cued_high_words": 5,          # strong cue and at least this many words: high
    "cued_low_words": 3,           # strong cue and this many: low
    "uncued_high_words": 15,       # no cue: long enough to be unmistakable
    "uncued_medium_words": 10,
    "uncued_low_words": 5,         # fewer uncued words is a short phrase, never a citation
}


def classify_span(words: int, formula: str | None, cues: list[dict], report_count: int, params: dict = PARAMS) -> dict:
    """{kind, confidence}: kind is formula | common_phrase | short_phrase | citation. `confidence` is high / medium /
    low for a citation and None otherwise. `report_count` is the number of distinct reports holding the same span."""
    strong = any(cue["kind"] in STRONG_CUES for cue in cues)
    if formula:
        return {"kind": "formula", "confidence": None}
    if not strong and words <= params["common_phrase_max_words"] and report_count >= params["common_phrase_reports"]:
        return {"kind": "common_phrase", "confidence": None}
    if strong:
        if words >= params["cued_high_words"]:
            return {"kind": "citation", "confidence": "high"}
        if words >= params["cued_low_words"]:
            return {"kind": "citation", "confidence": "low"}
        return {"kind": "short_phrase", "confidence": None}
    if words >= params["uncued_high_words"]:
        return {"kind": "citation", "confidence": "high"}
    if words >= params["uncued_medium_words"]:
        return {"kind": "citation", "confidence": "medium"}
    if words >= params["uncued_low_words"]:
        return {"kind": "citation", "confidence": "low"}
    return {"kind": "short_phrase", "confidence": None}
