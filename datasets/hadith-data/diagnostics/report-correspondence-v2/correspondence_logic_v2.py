"""Pure logic for report correspondence v2: compiler-remark cut, formula inventory and residual text, short sayings,
a content-word signature, and the v2 pair verdict. Shared v1 code (shingles, MinHash, local containment, clusters) is
imported from ../report-correspondence/correspondence_logic.py, never copied.

Standard library only, no I/O except reading the grading-recovery rule modules. Rationale: README.md in this
directory, sections "Method" and "Classes".
"""

from __future__ import annotations

import re
import sys
import zlib
from array import array
from dataclasses import dataclass
from pathlib import Path

JOB_DIR = Path(__file__).resolve().parent
DIAGNOSTICS_DIR = JOB_DIR.parent
V1_DIR = DIAGNOSTICS_DIR / "report-correspondence"
GRADING_RECOVERY_DIR = DIAGNOSTICS_DIR / "grading-recovery"
for _directory in (str(DIAGNOSTICS_DIR), str(V1_DIR)):
    if _directory not in sys.path:
        sys.path.append(_directory)

import diagnostic_common as common  # noqa: E402
import correspondence_logic as v1  # noqa: E402

METHOD_VERSION = "report-correspondence-v2"

# ─── Parameters (README.md §Method) ─────────────────────────────────────────────────────────────────
GRAM_WORDS = 4                    # formula inventory unit: word 4-grams of the comparison text
FORMULA_MIN_DOCUMENTS = 60        # a 4-gram found in at least this many reports is a formula span
FORMULA_MIN_RUN_WORDS = 6         # only runs of at least this many flagged words are removed (short frames are content)
QURAN_GRAM_WORDS = 5              # five consecutive words equal to a Qur'an span mark a quotation
MIN_RESIDUAL_WORDS = 3            # strong classes need this many words left after formula removal, on both sides
MIN_SHARED_RESIDUAL_SHINGLES = 8  # and this many shared residual shingles
PARTIAL_MIN_RESIDUAL_WORDS = 10   # partial overlap: the shorter residual
RESCUE_RESIDUAL_JACCARD = 0.15    # a pair the v1 rules keep on the whole text stays a variant while the residual shares this
RESCUE_RESIDUAL_CONTAINMENT = 0.45  # ... and a partial overlap while the residual containment is at least this
SHORT_MIN_WORDS = 3               # a saying shorter than this is never matched
SHORT_SAME_WORDING_JACCARD = 0.90 # two short reports: near-identical residual wording
SHORT_MIN_SHARED_SHINGLES = 6
SHORT_LENGTH_RATIO = 0.70         # and similar length
QUOTED_CONTAINMENT = 0.95         # a short saying counts as quoted only when (nearly) all of it sits in one window
QUOTED_MIN_RATIO = 2.0            # the longer report must be this many times longer (and 5 words longer)
QUOTED_MIN_EXTRA_WORDS = 5
QUOTED_MAX_SAYING_WORDS = v1.PARTIAL_MIN_WORDS - 1   # up to 14 words; from 15 on it is an ordinary partial overlap
SHORT_POSTING_CAP = 400           # a shingle held by more reports than this cannot seed short-saying candidates
QUOTED_MIN_SHINGLES = 8           # and at least 12 letters
QUOTED_MAX_ANCHOR_DOCUMENTS = 60  # a quoted saying must have a shingle found in at most this many reports (distinctive)
NO_ANCHOR = 10 ** 9
REFERENTIAL_TOKENS = frozenset({"مثله", "بمثله", "نحوه", "بنحوه", "بمعناه", "مثلها", "بمثلها", "نحوها", "بنحوها", "وبمثله"})
CONTENT_MAX_DOCUMENT_SHARE = 0.015  # content words found in more than 1.5 % of reports are left out
CONTENT_MIN_TOKENS = 8            # a report needs this many content stems to get the third signature
CONTENT_SALT = 0xC0DEFACE
INLINE_STATEMENT_WINDOW = 220     # characters after a speaker phrase searched for a grade term (mine_grading_sources)

CLASS_SAME_WORDING = v1.CLASS_SAME_WORDING
CLASS_VARIANT = v1.CLASS_VARIANT
CLASS_PARTIAL = v1.CLASS_PARTIAL
CLASS_SHORT_SAME_WORDING = "short_saying_same_wording"
CLASS_QUOTED = "saying_quoted_within_longer_report"
CLASS_FORMULA_ONLY = "formula_only"
SHOWN_CLASSES = (CLASS_SAME_WORDING, CLASS_VARIANT, CLASS_PARTIAL, CLASS_SHORT_SAME_WORDING, CLASS_QUOTED)

_MASK64 = 0xFFFFFFFFFFFFFFFF
_GRAM_MULTIPLIER = 1_000_003

# ─── Compiler remarks (rule imported from grading-recovery, for comparison only) ─────────────────────


class CompilerRules:
    """Compiler-statement boundaries of the grading-recovery job: its Tirmidhi extractor and its per-work speaker
    phrases are imported, not copied. A cut shortens the text compared; the stored text is never altered."""

    def __init__(self):
        grading = common.load_module("mine_grading_sources_for_v2", GRADING_RECOVERY_DIR / "mine_grading_sources.py")
        tirmidhi = common.load_module("extract_tirmidhi_for_v2", DIAGNOSTICS_DIR / "extract_tirmidhi_compiler_statements.py")
        self.speaker = grading.SPEAKER
        self.work_speakers = grading.COMPILER_PHRASES_BY_WORK   # work -> speaker phrases that name its compiler
        self.grade_terms = grading.TERMS
        self.tirmidhi_label = tirmidhi.SOURCE_LABEL
        self.statements = tirmidhi.extract_compiler_statements  # sentence-level statements with char_start
        self.qala_abu_isa = tirmidhi._QALA_ABU_ISA

    def cut_position(self, text: str, work: str) -> int | None:
        """Character offset where a compiler's own remark starts in a matn, or None."""
        positions: list[int] = []
        if work == self.tirmidhi_label:
            positions.extend(m.start() for m in self.qala_abu_isa.finditer(text))
            positions.extend(s["char_start"] for s in self.statements(text) if s["char_start"] >= 0)
        else:
            phrases = self.work_speakers.get(work)
            if phrases:
                for match in self.speaker.finditer(text):
                    phrase = re.sub(r"\s+", " ", match.group(1))
                    window = text[match.start(): match.start() + INLINE_STATEMENT_WINDOW]
                    if phrase in phrases and any(term in window for term in self.grade_terms):
                        positions.append(match.start())
        return min(positions) if positions else None

    def cut(self, text: str, work: str) -> tuple[str, bool]:
        position = self.cut_position(text, work)
        if position is None:
            return text, False
        return text[:position], True


# ─── Word grams, formula inventory, residual text ────────────────────────────────────────────────────


def gram_keys(word_ids: list[int], size: int) -> list[int]:
    """Deterministic 64-bit key of every consecutive `size`-word gram (polynomial over word ids)."""
    keys = []
    for start in range(len(word_ids) - size + 1):
        key = 0
        for word_id in word_ids[start:start + size]:
            key = (key * _GRAM_MULTIPLIER + word_id + 1) & _MASK64
        keys.append(key)
    return keys


class GramCounter:
    """Document frequency of word grams in two passes: a count-min array finds the candidates, an exact dict confirms.

    Bounded memory (128 MB array plus the few thousand confirmed grams) instead of one dict entry per distinct gram.
    """

    SLOT_BITS = 25

    def __init__(self):
        self.slots = array("I", bytes(4 * (1 << self.SLOT_BITS)))
        self.mask = (1 << self.SLOT_BITS) - 1
        self.exact: dict[int, int] = {}
        self.threshold = 0

    def first_pass(self, keys) -> None:
        for key in set(keys):
            self.slots[key & self.mask] += 1

    def second_pass(self, keys, threshold: int) -> None:
        self.threshold = threshold
        for key in set(keys):
            if self.slots[key & self.mask] >= threshold:
                self.exact[key] = self.exact.get(key, 0) + 1

    def frequent(self) -> set[int]:
        return {key for key, count in self.exact.items() if count >= self.threshold}


def formula_flags(word_ids: list[int], frequent: set[int], quran: set[int]) -> bytearray:
    """Per word position: 0 ordinary, 1 inside a frequent gram, 2 inside a Qur'an quotation (1 wins on overlap)."""
    flags = bytearray(len(word_ids))
    if quran:
        for start, key in enumerate(gram_keys(word_ids, QURAN_GRAM_WORDS)):
            if key in quran:
                for position in range(start, start + QURAN_GRAM_WORDS):
                    flags[position] = 2
    if frequent:
        marked = bytearray(len(word_ids))
        for start, key in enumerate(gram_keys(word_ids, GRAM_WORDS)):
            if key in frequent:
                marked[start:start + GRAM_WORDS] = b"\x01" * GRAM_WORDS
        position = 0
        while position < len(marked):
            if not marked[position]:
                position += 1
                continue
            end = position
            while end < len(marked) and marked[end]:
                end += 1
            if end - position >= FORMULA_MIN_RUN_WORDS:
                flags[position:end] = b"\x01" * (end - position)
            position = end
    return flags


def residual_words(words: list[str], flags: bytearray) -> list[str]:
    return [word for word, flag in zip(words, flags) if not flag]


def formula_runs(words: list[str], flags: bytearray) -> list[tuple[str, str]]:
    """Maximal runs of flagged words as (kind, text); kind is 'quran' when any word of the run is Qur'anic."""
    runs, start = [], None
    for position in range(len(words) + 1):
        flagged = position < len(words) and flags[position]
        if flagged and start is None:
            start = position
        elif not flagged and start is not None:
            kinds = set(flags[start:position])
            runs.append(("quran" if 2 in kinds and 1 not in kinds else "frequent", " ".join(words[start:position])))
            start = None
    return runs


# ─── Content words (the third signature) ─────────────────────────────────────────────────────────────

_PREFIXES = ("وال", "فال", "بال", "كال", "لل", "ال", "و", "ف")


def content_stem(word: str) -> str:
    """Light stem: one leading conjunction or article group removed when 3 or more letters remain."""
    for prefix in _PREFIXES:
        if word.startswith(prefix) and len(word) - len(prefix) >= 3:
            return word[len(prefix):]
    return word


def content_hash(stem: str) -> int:
    return v1._mix64(zlib.crc32(stem.encode("utf-8"))) & 0xFFFFFFFF


# ─── Pair evaluation ─────────────────────────────────────────────────────────────────────────────────


@dataclass
class Prepared:
    """One report ready for comparison: comparison words, the residual after formula removal, and shingle sets."""
    words: list[str]
    residual: list[str]
    full_letters: bytes
    residual_letters: bytes
    full_shingles: array
    residual_shingles: array
    referential: bool = False          # a short report that only points at another ("... بمثله"): never a saying
    anchor_documents: int = NO_ANCHOR  # reports holding the saying's rarest shingle (set for short reports)


def prepare(words: list[str], flags: bytearray | None) -> Prepared:
    residual = residual_words(words, flags) if flags is not None and any(flags) else words
    full_letters = v1.letters_bytes(words)
    residual_letters = full_letters if residual is words else v1.letters_bytes(residual)
    full_shingles = v1.shingle_set(words) if words else array("I")
    residual_shingles = full_shingles if residual is words else (v1.shingle_set(residual) if residual else array("I"))
    referential = len(words) <= QUOTED_MAX_SAYING_WORDS and any(word in REFERENTIAL_TOKENS for word in words)
    return Prepared(words, residual, full_letters, residual_letters, full_shingles, residual_shingles, referential)


def pair_score(set_a: set, shingles_b, letters_a: bytes, letters_b: bytes, sequence_a=None, sequence_b=None):
    """Exact Jaccard and (local) containment of two shingle collections; the v1 scorer with its gating."""
    shared = len(set_a.intersection(shingles_b))
    score = v1.PairScore(shared, len(set_a), len(shingles_b))
    gate = min(v1.VARIANT_CONTAINMENT, v1.PARTIAL_CONTAINMENT)
    if score.global_containment >= gate and v1.needs_local_containment(len(letters_a), len(letters_b)):
        if len(letters_a) <= len(letters_b):
            local = v1.local_containment(set_a, sequence_b() if sequence_b else v1.shingle_hashes_at(letters_b),
                                         len(letters_a))
        else:
            local = v1.local_containment(set(shingles_b), sequence_a() if sequence_a else v1.shingle_hashes_at(letters_a),
                                         len(letters_b))
        score = v1.PairScore(shared, score.size_a, score.size_b, local)
    return score


def strong_or_partial(score: v1.PairScore, residual_a: int, residual_b: int) -> str | None:
    """Same-wording / variant / partial classes on residual scores (v1 thresholds, residual word minimums)."""
    smaller = min(residual_a, residual_b)
    if smaller >= MIN_RESIDUAL_WORDS and score.shared >= MIN_SHARED_RESIDUAL_SHINGLES:
        if score.jaccard >= v1.SAME_WORDING_JACCARD:
            return CLASS_SAME_WORDING
        if score.jaccard >= v1.VARIANT_JACCARD and score.containment >= v1.VARIANT_CONTAINMENT:
            return CLASS_VARIANT
    if (smaller >= PARTIAL_MIN_RESIDUAL_WORDS and score.containment >= v1.PARTIAL_CONTAINMENT
            and score.shared >= MIN_SHARED_RESIDUAL_SHINGLES):
        return CLASS_PARTIAL
    return None


@dataclass(frozen=True)
class Verdict:
    pair_class: str
    score: v1.PairScore          # residual scores: they decided the class
    full: v1.PairScore           # scores on the whole comparison text
    short_side: str = ""         # 'a' or 'b': which report is the short saying (quoted class, short class)


def short_side_of(words_a: int, words_b: int) -> str:
    return "a" if words_a <= words_b else "b"


def rescued_class(full_class: str, score: v1.PairScore, residual_a: int, residual_b: int) -> str | None:
    """A pair the v1 rules keep on the whole text stays a telling when the residual still shows real overlap."""
    smaller = min(residual_a, residual_b)
    if smaller < MIN_RESIDUAL_WORDS or score.shared < MIN_SHARED_RESIDUAL_SHINGLES:
        return None
    if full_class in v1.STRONG_CLASSES and score.jaccard >= RESCUE_RESIDUAL_JACCARD:
        return CLASS_VARIANT
    if (full_class == CLASS_PARTIAL and smaller >= PARTIAL_MIN_RESIDUAL_WORDS
            and score.containment >= RESCUE_RESIDUAL_CONTAINMENT):
        return CLASS_PARTIAL
    return None


def judge(words_a: int, words_b: int, residual_a: int, residual_b: int, score: v1.PairScore, full: v1.PairScore,
          short_referential: bool = False, short_anchor: int = NO_ANCHOR) -> Verdict | None:
    """The v2 class of a scored pair, or None. Order: strong/partial on residual; the v1 class kept when the residual
    still shows overlap; short same wording; quoted saying; formula_only for what is left of the v1 classes."""
    smaller_words, larger_words = min(words_a, words_b), max(words_a, words_b)
    full_class = v1.classify(full, words_a, words_b)
    if smaller_words >= v1.MIN_WORDS:
        pair_class = strong_or_partial(score, residual_a, residual_b)
        if pair_class == CLASS_PARTIAL and smaller_words < v1.PARTIAL_MIN_WORDS:
            pair_class = None
        if pair_class is not None:
            return Verdict(pair_class, score, full)
        if full_class is not None:
            kept = rescued_class(full_class, score, residual_a, residual_b)
            if kept is not None:
                return Verdict(kept, score, full)
    smaller_residual = min(residual_a, residual_b)
    if smaller_words >= SHORT_MIN_WORDS and smaller_residual >= SHORT_MIN_WORDS and not short_referential:
        side = short_side_of(words_a, words_b)
        if (smaller_words < v1.MIN_WORDS and larger_words < v1.MIN_WORDS * 2
                and smaller_words / larger_words >= SHORT_LENGTH_RATIO
                and score.jaccard >= SHORT_SAME_WORDING_JACCARD and score.shared >= SHORT_MIN_SHARED_SHINGLES):
            return Verdict(CLASS_SHORT_SAME_WORDING, score, full, side)
        if (smaller_words <= QUOTED_MAX_SAYING_WORDS and short_anchor <= QUOTED_MAX_ANCHOR_DOCUMENTS
                and larger_words >= max(QUOTED_MIN_RATIO * smaller_words, smaller_words + QUOTED_MIN_EXTRA_WORDS)
                and score.containment >= QUOTED_CONTAINMENT and score.shared >= SHORT_MIN_SHARED_SHINGLES
                and min(score.size_a, score.size_b) >= QUOTED_MIN_SHINGLES):
            return Verdict(CLASS_QUOTED, score, full, side)
    if full_class is not None:
        return Verdict(CLASS_FORMULA_ONLY, score, full)
    return None


def compare(a: Prepared, b: Prepared, set_a_full: set | None = None, set_a_residual: set | None = None,
            sequence_a=None, sequence_b=None) -> Verdict | None:
    """Full v2 comparison of two prepared reports. Sets and sequence callables may be passed to reuse work."""
    set_a_full = set_a_full if set_a_full is not None else set(a.full_shingles)
    set_a_residual = set_a_residual if set_a_residual is not None else (
        set_a_full if a.residual_shingles is a.full_shingles else set(a.residual_shingles))
    residual_score = pair_score(set_a_residual, b.residual_shingles, a.residual_letters, b.residual_letters,
                                sequence_a, sequence_b)
    if b.residual_shingles is b.full_shingles and a.residual_shingles is a.full_shingles:
        full_score = residual_score
    else:
        full_score = pair_score(set_a_full, b.full_shingles, a.full_letters, b.full_letters)
    short = a if len(a.words) <= len(b.words) else b
    return judge(len(a.words), len(b.words), len(a.residual), len(b.residual), residual_score, full_score,
                 short.referential, short.anchor_documents)


def quran_gram_keys(verse_word_lists, vocabulary_id) -> set[int]:
    """Keys of every QURAN_GRAM_WORDS gram of every verse (word ids come from the corpus vocabulary)."""
    keys: set[int] = set()
    for words in verse_word_lists:
        keys.update(gram_keys([vocabulary_id(word) for word in words], QURAN_GRAM_WORDS))
    return keys
