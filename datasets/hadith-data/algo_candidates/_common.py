"""
Shared helpers for taḥwīl-aware isnad extraction candidates.

Imports from the existing classical extractor in regen_unified_csvs.py
where possible, but does NOT modify it. New helpers added here.
"""
from __future__ import annotations
import re
import sys
import os
from typing import Iterable

# Path setup so we can import the existing extractor + _norm.
_BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(_BASE, '..')))
sys.path.insert(0, os.path.normpath(os.path.join(_BASE, '..', '..')))

# We deliberately re-define the regexes here (matching regen_unified_csvs.py)
# so the candidates have no implicit ordering dependency on the existing
# extractor. Once a winner is picked, the shared module under
# extract_isnad_unified.py will import from regen_unified_csvs as the spec
# requires (FR-1.1 step 6).

TAHWEEL_RE = re.compile(
    r'(?:^|[\s،.])ح\s+و?(?:حدثنا|حدثني|أخبرنا|أخبرني|أنبأنا|أنبأني|ثنا|نا)',
)
CHAIN_VERB_SPLIT = re.compile(
    r"(?:حدثنا|حدثني|أخبرنا|أخبرني|أنبأنا|أنبأني|ثنا|نا)\s+"
)
AAN_SPLIT = re.compile(r"\bعن\b")
TRAILING_NARRATIVE = re.compile(r"\s*(?:قال|قالت|قالوا|يقول|وهو|قد|في|عن)\s*$")
HONORIFIC = re.compile(
    r"\s*رض[ىي]\s*الله\s*عنه?[امه]*\s*"
    r"|\s*رحمه\s*الله\s*"
    r"|\s*عليه\s*السلام\s*"
    r"|\s*صلى\s*الله\s*عليه\s*(?:وآله\s*)?وسلم\s*"
    r"|\s*أم\s+المؤمنين\s*"
)
PUNCT = re.compile(r"[،,.:؛!؟\"'\(\)\[\]‏‎]+")
NARRATIVE = re.compile(
    r"\b(?:ثم|حتى|فقال|فقالت|فكان|فلما|إذ|فأخذ|فرجع|فدخل|قلت|قال|أن|وهو|أنه)\b"
)
MATN_ANCHORS = re.compile(
    r"عن النبي|عن رسول الله|قال رسول الله|قال النبي|قال صلى الله|"
    r"عن أبي عبد الله|قال أبو عبد الله|قال أبو جعفر|"
    # Round-2 additions: matn-introducing verbs that don't reference the Prophet/Imam directly.
    # NOTE: must NOT swallow `يقول` when it's part of an isnad narrator-frame
    # like "سمع علقمة … يقول"; we therefore require a more specific context.
    r"يقول لا يحدث|سمعت رسول الله|"
    r"يخطب قال|يخطب يقول|سمعت النبي|"
    # Companion-attributed matn cues (Imami / general)
    r"قال رضي الله عنه"
)
# Round-2: trailing connectives glued to a name token by the upstream cleaner.
# Examples we saw:
#   "أبو بكر بن أبي شيبة أيضا" (also)
#   "المغيرة بن شعبة قالا"     (they two said — dual-speaker frame)
#   "ربعي بن حراش أنه سمع عليا" (sub-narration frame)
TRAILING_CONNECTIVES = re.compile(
    r"\s+(?:"
    r"أيضا|كذلك|"
    r"قالا|قالوا|قالت|قال(?:ت)?(?:\s+ل[يهنا])?|"
    r"أنه\s+(?:سمع|قال|رأى)|"
    r"يقول|يخطب|"
    r"رضي\s+الله\s+عنه[امه]*"
    r")\b.*$"
)
# Round-2: a co-transmitter clause is something like "X و Y" or "X وَ Y" — the
# downstream split_into_names tokenizer emits "X و Y" or even "X وY" as one name.
# Strip the appended " و<other>" tail so we keep only the FIRST narrator surface.
# Example: "شعبة وسفيان" → "شعبة"; "محمد بن المثنى وابن بشار قالا" → "محمد بن المثنى".
# We KEEP both narrators by emitting them as separate name tokens later in
# split_into_names. Here in clean_segment we just strip the suffix.
COTRANSMITTER_SUFFIX = re.compile(
    r"\s+و(?=\S)"  # whitespace + و directly followed by a non-space letter
)


def split_on_tahweel(text_ar: str) -> list[str]:
    """Split text_ar into ح-separated raw segments.

    Returns the segments in original order. A single-chain hadith returns
    a 1-element list.

    Round-2 fix: locate the ح character position deterministically and skip
    the surrounding whitespace + optional و prefix, so the next segment
    starts cleanly at the post-ح verb. The previous regex-search inside
    `text_ar[m.start():m.end()+1]` was OFF BY ONE when ح was at the very
    start of m's match (no leading whitespace).
    """
    if not text_ar:
        return []
    matches = list(TAHWEEL_RE.finditer(text_ar))
    if not matches:
        return [text_ar.strip()]
    segments: list[str] = []
    last = 0
    # Pre-compile the post-ح skipper once.
    post_h_skip = re.compile(r"^\s+و?\s*")
    for m in matches:
        # m.start() is one char BEFORE the ح (the leading whitespace/punct).
        # Find the ح itself within the match span:
        match_text = text_ar[m.start():m.end()]
        h_offset = match_text.find('ح')
        if h_offset < 0:
            # Defensive: regex matched but no ح?  Skip past the match end.
            segments.append(text_ar[last:m.start()].strip())
            last = m.end()
            continue
        # Split point is just BEFORE the ح (so the pre-segment ends cleanly,
        # without including the ح character).
        split_at = m.start() + h_offset
        segments.append(text_ar[last:split_at].strip())
        # Skip the ح character + the post-ح whitespace + optional و so the
        # next segment starts at the verb (حدثنا/أخبرنا/etc.).
        after_h = split_at + 1
        skip_m = post_h_skip.match(text_ar[after_h:])
        last = after_h + (skip_m.end() if skip_m else 0)
    segments.append(text_ar[last:].strip())
    return [s for s in segments if s]


def clean_segment(raw: str) -> str:
    s = HONORIFIC.sub(" ", raw.strip())
    s = PUNCT.sub(" ", s)
    s = TRAILING_NARRATIVE.sub("", s)
    # Round-2: strip trailing connective frames (أيضا, قالا, أنه سمع, etc.)
    # BEFORE collapsing whitespace, so the regex anchors fire on real word
    # boundaries.
    s = TRAILING_CONNECTIVES.sub("", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _split_co_transmitters(name: str) -> list[str]:
    """Split "X و Y" / "X وY" co-transmitter chains into [X, Y].

    A leading و on the FIRST token doesn't count (that's just the Arabic
    "and-then" conjunction at sentence start). We only split when و appears
    INSIDE the name (i.e., not at position 0).

    Examples:
      "شعبة وسفيان"               → ["شعبة", "سفيان"]
      "محمد بن المثنى وابن بشار"  → ["محمد بن المثنى", "ابن بشار"]
      "وضاح بن عبد الله"          → ["وضاح بن عبد الله"]   (leading و, no split)
      "عبد الله بن"               → ["عبد الله بن"]         (no و-coordination)
    """
    if not name or len(name) < 4:
        return [name] if name else []
    parts = COTRANSMITTER_SUFFIX.split(name)
    if len(parts) == 1:
        return parts
    # The FIRST و (at position > 0) splits. Subsequent و's also split.
    cleaned = []
    for i, p in enumerate(parts):
        p = p.strip()
        if not p:
            continue
        # Strip a leading "و" that the split left behind on parts[1:]
        if i > 0 and p.startswith("و"):
            p = p[1:].strip()
        if p and len(p) >= 2:
            cleaned.append(p)
    return cleaned or [name]


def split_into_names(segment: str) -> list[str]:
    """Split a ح-segment into per-narrator surface forms.

    Same algorithm as extract_classical_isnad: split on transmission verbs,
    then within each piece split on عن. Each non-empty result is a candidate
    narrator surface form.

    Round-2: handle co-transmitters by splitting "X و Y" into [X, Y] after
    the verb/عن split, since the upstream split keeps them in one piece.
    """
    if not segment:
        return []
    names: list[str] = []
    for verb_part in CHAIN_VERB_SPLIT.split(segment):
        for aan_part in AAN_SPLIT.split(verb_part):
            cleaned = clean_segment(aan_part)
            if not cleaned:
                continue
            if NARRATIVE.search(cleaned):
                # cut at the narrative connective
                m = NARRATIVE.search(cleaned)
                cleaned = cleaned[:m.start()].strip()
                if not cleaned:
                    continue
            # filter implausible
            if len(cleaned) < 2:
                continue
            if len(cleaned.split()) > 8:
                # too long to be a single name
                continue
            # Round-2: handle co-transmitters by splitting on internal و.
            for sub in _split_co_transmitters(cleaned):
                if sub and len(sub) >= 2:
                    names.append(sub)
    return names


def find_matn_start(segment: str) -> int | None:
    """Return char index where the matn (vs. isnad) begins, or None if no
    matn-anchor found."""
    m = MATN_ANCHORS.search(segment)
    return m.start() if m else None


def name_normalize(s: str) -> str:
    """Strip optional leading particles (و, ف) and trim, for token matching.

    Lighter than _norm — preserves intra-token Arabic-letter precision but
    handles whitespace and common prefixes.
    """
    s = s.strip()
    s = re.sub(r"^[وفأ]\s+", "", s)
    return re.sub(r"\s+", " ", s)


def is_name_token(s: str) -> bool:
    return bool(s) and len(s) >= 3 and not NARRATIVE.search(s)
