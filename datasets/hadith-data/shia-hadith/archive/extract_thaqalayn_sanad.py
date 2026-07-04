# Archived 2026-06-24: superseded by extract_isnad_unified.py; preserved for reference.
"""
extract_thaqalayn_sanad.py
--------------------------
Parse English-structured thaqalaynSanad strings into ordered narrator surface
forms, then resolve each to a scholar_indx via the rawi lexicon resolver.

No side effects on import.  All dependencies are stdlib or already in-tree.
"""

import re
import sys
import os
from typing import Optional

# ---------------------------------------------------------------------------
# Regex constants
# ---------------------------------------------------------------------------

# Strip leading "N. " numbering
_RE_LEADING_NUM = re.compile(r"^\s*\d+\.\s*")

# Preamble: "<Author> has said:" / "has narrated:" / "has been narrated by"
# We strip everything up to and including the first colon that follows
# a preamble verb — then handle "A number of our people..." specially.
_RE_PREAMBLE_COLON = re.compile(
    r"^.+?(?:has said|has narrated|has reported|narrated|reported|said)\s*:\s*",
    re.IGNORECASE,
)

# "A number of our people of whom one is <NAME> narrated from"
_RE_OF_WHOM_ONE = re.compile(
    r"of whom one is\s+(.+?)\s+narrated from",
    re.IGNORECASE,
)

# Split on "narrated from" or bare "from" (word-boundary)
_RE_FROM_SPLIT = re.compile(r"\bnarrated from\b|\bfrom\b", re.IGNORECASE)

# Trailing cue words that signal the Imam/matan start — cut here
_RE_TRAILING_CUE = re.compile(
    r"\s+(?:that\b|who\b|saying\b|said\b|has said\b|reports\b|the following\b"
    r"|in a marfu[''ʿ]?\b|in a\b)"
    r"|[\s,]+\((?:as|a\.s\.|saws|s|swt|p)\)\s*$"
    r"|\s+\((?:as|a\.s\.|saws|s|swt|p)\)\s*$",
    re.IGNORECASE,
)

# Honorific suffixes to strip from individual segments
_RE_HONORIFICS = re.compile(
    r"\s*\((?:as|a\.s\.|saws|s\.a\.w\.s\.|s|swt|p|saw)\)\s*",
    re.IGNORECASE,
)

# Segments to skip — they are connective narrative phrases, not names
_SKIP_PATTERNS = re.compile(
    r"(?:one of our people|marfu[''ʿ]?|maqtu[''ʿ]?|in a \w+ manner"
    r"|anonymous|unknown|some of our companions|a number of our)",
    re.IGNORECASE,
)

# Single stop words that are not names
_STOP_WORDS = {"him", "them", "us", "one", "some", "he", "she", "it",
               "they", "who", "her", "his", "the", "al", "ibn"}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_thaqalayn_sanad(thaqalayn_sanad: str) -> list[str]:
    """Split a Thaqalayn English-structured sanad string into ordered
    surface-form names suitable for resolve_narrator.

    Returns ordered list of clean surface forms.
    Returns [] if the input is empty or has no parseable chain.
    """
    if not thaqalayn_sanad or not thaqalayn_sanad.strip():
        return []

    text = thaqalayn_sanad.strip()

    # Bail early if no chain indicators
    if "from" not in text.lower() and "narrated" not in text.lower():
        return []

    # --- Step 1: Strip leading "N. " numbering ---
    text = _RE_LEADING_NUM.sub("", text)

    # --- Step 2: Handle "of whom one is <NAME> narrated from" ---
    of_whom_match = _RE_OF_WHOM_ONE.search(text)
    first_from_preamble: Optional[str] = None
    if of_whom_match:
        first_from_preamble = of_whom_match.group(1).strip()
        # Truncate text to start at "narrated from" after the match
        text = text[of_whom_match.end() - len("narrated from"):]
        text = re.sub(r"^narrated from\s*", "", text, flags=re.IGNORECASE)

    # --- Step 3: Strip leading compiler preamble (up to first colon) ---
    # E.g. "Ali bin Muhammad has narrated from Sahl..." — no colon, no strip needed.
    # E.g. "Abu Jaʿfar Muhammad b. Yaʿqub (al-Kulayni) has said: A number of..."
    # Skip this step if of_whom already consumed the preamble (first_from_preamble set).
    #
    # CRITICAL: Only accept a colon-preamble match if it ends BEFORE the first "from"
    # split point in the text.  Without this guard, a trailing "Ali (as) said:" causes
    # the lazy .+? to backtrack all the way to the end and eat the whole chain.
    preamble_match = None
    compiler_name: Optional[str] = None
    if not first_from_preamble:
        first_from_match = _RE_FROM_SPLIT.search(text)
        preamble_search_end = first_from_match.start() if first_from_match else len(text)

        candidate = _RE_PREAMBLE_COLON.match(text)
        if candidate and candidate.end() <= preamble_search_end:
            # Legitimate preamble: the verb+colon occurs before the first "from"
            preamble_match = candidate
            compiler_name = text[: preamble_match.start()].strip()
            text = text[preamble_match.end():].strip()
            # After stripping preamble, if text starts with "A number of...",
            # try of_whom_match again on remaining
            of_whom_match2 = _RE_OF_WHOM_ONE.search(text)
            if of_whom_match2:
                first_from_preamble = of_whom_match2.group(1).strip()
                text = text[of_whom_match2.end() - len("narrated from"):]
                text = re.sub(r"^narrated from\s*", "", text, flags=re.IGNORECASE)

    # --- Step 4: Split on "narrated from" / "from" ---
    segments_raw = _RE_FROM_SPLIT.split(text)

    # If preamble was NOT a colon-style, the first raw segment IS the compiler name
    # (e.g. "Ali bin Muhammad has narrated from Sahl...").  After splitting on
    # "narrated from", segments_raw[0] = "Ali bin Muhammad has " — extract the name.
    if not preamble_match and not first_from_preamble and segments_raw:
        preamble_seg = segments_raw[0]
        # Strip trailing verb residue: "has narrated", "has said", "has", "narrated", etc.
        cleaned_preamble = re.sub(
            r"\s+(?:has\s+narrated|has\s+said|has\s+reported|narrates|narrated|reported|said|reports|has)\s*$",
            "",
            preamble_seg,
            flags=re.IGNORECASE,
        ).strip()
        if cleaned_preamble:
            compiler_name = cleaned_preamble
        segments_raw = segments_raw[1:]  # drop preamble segment

    # --- Step 5: Clean last segment (strip trailing cue) ---
    if segments_raw:
        last = segments_raw[-1]
        # Apply trailing cue strip
        cue_match = _RE_TRAILING_CUE.search(last)
        if cue_match:
            last = last[: cue_match.start()]
        segments_raw[-1] = last

    # --- Step 6: Clean and filter all segments ---
    names: list[str] = []

    def _clean_segment(seg: str) -> str:
        seg = seg.strip().strip(",").strip()
        seg = _RE_HONORIFICS.sub(" ", seg).strip()
        seg = seg.strip().strip(",").strip()
        return seg

    def _is_valid(seg: str) -> bool:
        if not seg:
            return False
        words = seg.split()
        if len(words) == 1 and words[0].lower() in _STOP_WORDS:
            return False
        if re.match(r"^\d+$", seg):
            return False
        if _SKIP_PATTERNS.search(seg):
            return False
        # Very short fragments that are not names
        if len(seg) < 2:
            return False
        return True

    # Insert compiler name first (either from "of whom one is" path or
    # from non-colon preamble extraction path).
    # For colon-preamble path (Sample 1), first_from_preamble is used;
    # compiler_name holds the book author (al-Kulayni etc.) which is the
    # implicit outer frame — skip it unless there was no of_whom match.
    leading_name: Optional[str] = None
    if first_from_preamble:
        # "of whom one is <NAME>" — this IS the first chain link
        leading_name = first_from_preamble
    elif compiler_name and not preamble_match:
        # Non-colon preamble: compiler IS the first link (e.g. "Ali bin Muhammad has narrated from")
        leading_name = compiler_name
    # For colon-preamble WITHOUT of_whom: compiler is book-author (al-Kulayni, al-Saduq),
    # not counted as a chain link — leave leading_name=None.

    if leading_name:
        cleaned = _clean_segment(leading_name)
        if _is_valid(cleaned):
            names.append(cleaned)

    for seg in segments_raw:
        cleaned = _clean_segment(seg)
        if _is_valid(cleaned):
            names.append(cleaned)

    return names


def resolve_thaqalayn_chain(
    thaqalayn_sanad: str,
    exact_index: dict,
    blocked_index: dict,
) -> tuple[str, dict]:
    """Parse thaqalayn_sanad and resolve to comma-separated scholar_indx string.

    Returns (chain_indx_str, stats_dict) where stats_dict = {
        'attempted': int,       # total names parsed
        'resolved': int,        # how many resolved to a scholar_indx
        'parsed_names': list,   # surface forms (for debug)
    }
    Chain_indx_str is "" if nothing resolved.
    """
    # Import resolver lazily so this module is importable even standalone
    try:
        # Allow import from different call contexts
        _resolve = _get_resolver()
    except ImportError:
        parsed = parse_thaqalayn_sanad(thaqalayn_sanad)
        return "", {
            "attempted": len(parsed),
            "resolved": 0,
            "parsed_names": parsed,
        }

    parsed = parse_thaqalayn_sanad(thaqalayn_sanad)
    resolved_ids: list[str] = []
    for name in parsed:
        idx = _resolve(name, exact_index, blocked_index)
        if idx is not None:
            resolved_ids.append(str(idx))

    chain_str = ",".join(resolved_ids)
    return chain_str, {
        "attempted": len(parsed),
        "resolved": len(resolved_ids),
        "parsed_names": parsed,
    }


# ---------------------------------------------------------------------------
# Internal: lazy resolver import
# ---------------------------------------------------------------------------

_cached_resolve_fn = None


def _get_resolver():
    """Return the resolve_narrator function, importing it lazily."""
    global _cached_resolve_fn
    if _cached_resolve_fn is not None:
        return _cached_resolve_fn

    # regen_unified_csvs.py lives one directory up from this file
    _here = os.path.dirname(os.path.abspath(__file__))
    _parent = os.path.dirname(_here)
    if _parent not in sys.path:
        sys.path.insert(0, _parent)

    # classify_attribution is two levels up (in datasets/)
    _datasets = os.path.dirname(_parent)
    if _datasets not in sys.path:
        sys.path.insert(0, _datasets)

    from regen_unified_csvs import resolve_narrator  # noqa: PLC0415
    _cached_resolve_fn = resolve_narrator
    return _cached_resolve_fn


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys as _sys
    if hasattr(_sys.stdout, "reconfigure"):
        try:
            _sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    SAMPLES = [
        (
            "1",
            " 1. Abu Jaʿfar Muhammad b. Yaʿqub (al-Kulayni) has said: A number of our people "
            "of whom one is Muhammad b. Yahya al-ʿAttar narrated from Ahmad b. Muhammad from "
            "Hasan b. Mahbub from al-ʿAla b. Razin from Muhammad b. Muslim that Abu Jaʿfar "
            "(al-Baqir) (as) has said: ",
        ),
        (
            "2",
            "2. Ali bin Muhammad has narrated from Sahl ibn Ziyad, from ʿAmr ibn ʿUthman, "
            "from Mufaddal ibn Salih from Saʿd ibn Tarif from al-Asbagh ibn Nubatah that "
            "Ali (as) said:",
        ),
        (
            "3",
            "3. Ahmad ibn ʾIdris has narrated from Muhammad ibn ʿAbd al-Jabbar, from one of "
            "our people in a marfu' manner that",
        ),
        (
            "4",
            "4. Muhammad ibn Yahya has narrated from Ahmad ibn Muhammad ibn ʿIsa from ibn "
            "Faddal from al-Hassan ibn al-Jahm that he heard (Imam) al-Ridha (as) saying,",
        ),
    ]

    print("=" * 70)
    print("Smoke test: parse_thaqalayn_sanad")
    print("=" * 70)
    for label, text in SAMPLES:
        result = parse_thaqalayn_sanad(text)
        print(f"\nInput {label}:")
        print(f"  {text[:80].strip()}...")
        print(f"  -> {result}")

    print("\n" + "=" * 70)
    print("Expected (approximate):")
    print(
        "  1: ['Muhammad b. Yahya al-ʿAttar', 'Ahmad b. Muhammad', "
        "'Hasan b. Mahbub', 'al-ʿAla b. Razin', 'Muhammad b. Muslim', 'Abu Jaʿfar']"
    )
    print(
        "  2: ['Ali bin Muhammad', 'Sahl ibn Ziyad', 'ʿAmr ibn ʿUthman', "
        "'Mufaddal ibn Salih', 'Saʿd ibn Tarif', 'al-Asbagh ibn Nubatah', 'Ali']"
    )
    print("  3: ['Ahmad ibn ʾIdris', 'Muhammad ibn ʿAbd al-Jabbar']")
    print(
        "  4: ['Muhammad ibn Yahya', 'Ahmad ibn Muhammad ibn ʿIsa', "
        "'ibn Faddal', 'al-Hassan ibn al-Jahm', 'al-Ridha']"
    )
