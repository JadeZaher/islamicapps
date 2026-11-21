"""Canonical, tradition-neutral isnad surface extractor.

See ``datasets/hadith-data/AGENTS.md`` for the parsing contract, provenance
requirements, and known limits. This module extracts source surfaces; it does
not infer narrator identities.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable
from typing import Optional


MAX_ISNAD_BRANCHES = 64

_TRANSMISSION_VERBS = (
    "حدثنا|حدثني|اخبرنا|اخبرني|أخبرنا|أخبرني|انبأنا|انبأني|"
    "أنبأنا|أنبأني|ثنا|نا|سمعت"
)
_LINK_RE = re.compile(
    rf"\b(?:"
    rf"قال(?:ا|ت|وا)?[\s:،-]+(?:و?\s*)?(?:{_TRANSMISSION_VERBS})|"
    rf"يقول[\s:،-]+سمعت|أنه[\s:،-]+سمع|انّه[\s:،-]+سمع|"
    rf"رفعه[\s:،-]+إلى|رفعه[\s:،-]+الى|"
    rf"و?(?:{_TRANSMISSION_VERBS})|عن"
    rf")\b"
)
_TRANSMISSION_AHEAD_RE = re.compile(
    rf"^[\s،,.;:ـ-]*(?:و\s*)?"
    rf"(?:(?:قال|وقال)\b.{{0,80}}?)?(?:{_TRANSMISSION_VERBS})\b"
)
_LONE_H_RE = re.compile(r"(?<![\w])ح(?=[\s،,.;:ـ-])")
_PROPHET_BOUNDARY_RE = re.compile(
    r"\b(?:عن|أن|ان|سمعت)\s+(?:النبيء|النبي|رسول\s+الله)\b"
)
_SPEECH_RE = re.compile(r"\b(?:قال|قالت|قالوا|يقول)\b")
_SPEECH_LINK_RE = re.compile(
    rf"^[\s:،-]*(?:و\s*)?(?:{_TRANSMISSION_VERBS})\b"
)
_ARABIC_LETTER_RE = re.compile(r"[ء-ي]")
_EDITORIAL_RE = re.compile(
    r"[-–—]\s*(?:يعني|واللفظ\s+له|وهذا\s+حديثه)[^-–—]*[-–—]"
)
_HONORIFIC_RE = re.compile(
    r"\s*(?:"
    r"رض[ىي]\s+الله\s+عنه(?:ا|ما|م|ن)?|رحم(?:ه|هم|ها)\s+الله(?:\s+تعالى)?|"
    r"عليه(?:ما|م)?\s+السلام|"
    r"سلام\s+الله\s+عليه(?:م)?(?:\s+أجمعين\s+آمين\s+إلى\s+يوم\s+الدين)?|"
    r"صلى\s+الله\s+عليه(?:\s+وآله)?\s+وسلم|"
    r"أم\s+المؤمنين|(?<![\w])ع\s*م(?![\w])"
    r")\s*"
)
_TRAILING_FRAME_RE = re.compile(
    r"\s+(?:"
    r"قالا|قالت|قالوا|قال|يقول|أن|ان|أنه|انّه|وهو|"
    r"على\s+المنبر|في\s+قوله\s+تعالى|يخطب|"
    r"واللفظ\s+له|وهذا\s+حديثه|أيضا|جميعا"
    r")\b.*$"
)
_PUNCT_RE = re.compile(r"[،,.:؛!?؟\"'«»“”‘’()\[\]{}ـ=‏‎]+")
_LEADING_LABEL_RE = re.compile(
    r"^(?:\d+(?:[-/ـ]\d+)*\s*|قال\s+|وقال\s+|وبإسناده\s+|وباسناده\s+)"
)
_PATRONYMIC_CONNECTORS = {
    "بن", "ابن", "بنت", "أبو", "ابو", "أبي", "ابي", "أبا", "ابا", "أم", "ام"
}
_WEAK_CONVERGENCE = {
    "ابي", "ابيه", "ابا", "ابوه", "امه", "جده", "جدّه", "ابائه", "آبائه",
    "بعض اصحابنا", "بعض أصحابنا",
}


_UNIFIED_CHAIN_STATS: dict[str, int] = {
    "rows_with_text": 0,
    "rows_empty": 0,
    "rows_single": 0,
    "rows_branched": 0,
    "branches_total": 0,
    "branches_unstitched": 0,
    "narrators_attempted": 0,
    "narrators_resolved": 0,
    "narrators_unresolved": 0,
    "narrators_invalid": 0,
    "rows_resolution_failed": 0,
    "rows_extraction_failed": 0,
    "fallback_used": 0,
}


class UnresolvedNarratorError(ValueError):
    """Report one surface that makes atomic chain resolution fail."""

    def __init__(
        self,
        surface: str,
        branch_index: int,
        narrator_index: int,
        reason: str,
    ) -> None:
        self.surface = surface
        self.branch_index = branch_index
        self.narrator_index = narrator_index
        self.reason = reason
        super().__init__(
            f"cannot resolve narrator {surface!r} at branch {branch_index}, "
            f"position {narrator_index}: {reason}"
        )


class IsnadExtractionLimitError(ValueError):
    """Report a branch expansion rejected before allocation."""

    def __init__(self, stage: str, projected: int,
                 limit: int = MAX_ISNAD_BRANCHES) -> None:
        self.stage = stage
        self.projected = projected
        self.limit = limit
        super().__init__(
            f"isnad branch expansion at {stage} projects {projected} branches; "
            f"limit is {limit}"
        )


def _check_branch_limit(stage: str, projected: int) -> None:
    if projected <= MAX_ISNAD_BRANCHES:
        return
    _UNIFIED_CHAIN_STATS["rows_extraction_failed"] += 1
    raise IsnadExtractionLimitError(stage, projected)


def reset_stats() -> None:
    """Reset deterministic run telemetry."""
    for key in _UNIFIED_CHAIN_STATS:
        _UNIFIED_CHAIN_STATS[key] = 0


def _strip_arabic_marks(value: str) -> str:
    """Remove vocalization/tatweel while retaining Arabic letters."""
    return "".join(
        ch for ch in unicodedata.normalize("NFKC", value)
        if ch != "ـ" and unicodedata.category(ch) != "Mn"
    )


def name_normalize(value: str) -> str:
    """Normalize a source surface only for comparison, never identity."""
    value = _strip_arabic_marks(value)
    value = value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    value = re.sub(r"\bابن\b", "بن", value)
    value = re.sub(r"^[وف]\s*", "", value.strip())
    return re.sub(r"\s+", " ", value)


def is_name_token(value: str) -> bool:
    """Return whether a cleaned surface is plausible narrator text."""
    words = value.split()
    return bool(_ARABIC_LETTER_RE.search(value)) and 1 <= len(words) <= 14


def _split_on_tahweel(text_ar: str) -> list[str]:
    text = _strip_arabic_marks(text_ar)
    split_points: list[int] = []
    for match in _LONE_H_RE.finditer(text):
        if _TRANSMISSION_AHEAD_RE.search(text[match.end():match.end() + 120]):
            _check_branch_limit("tahweel_stitching", len(split_points) + 2)
            split_points.append(match.start())
    if not split_points:
        return [text.strip()] if text.strip() else []
    segments: list[str] = []
    start = 0
    for point in split_points:
        segment = text[start:point].strip()
        if segment:
            segments.append(segment)
        start = point + 1
    tail = text[start:].strip()
    if tail:
        segments.append(tail)
    return segments


def _matn_start(segment: str) -> Optional[int]:
    candidates = [m.start() for m in _PROPHET_BOUNDARY_RE.finditer(segment)]
    first_link = _LINK_RE.search(segment)
    for match in _SPEECH_RE.finditer(segment):
        if _SPEECH_LINK_RE.search(segment[match.end():match.end() + 40]):
            continue
        if match.start() == 0 and first_link and first_link.start() < 120:
            continue
        if first_link and match.start() > first_link.start():
            candidates.append(match.start())
    return min(candidates) if candidates else None


def _split_co_transmitters(surface: str, force: bool = False) -> list[str]:
    """Split conjunctions without corrupting names such as Ibn Wahb."""
    matches = list(re.finditer(r"\s+و(?=\S)", surface))
    if not matches:
        return [surface]
    split_matches = []
    for match in matches:
        prefix = surface[:match.start()].strip()
        previous = prefix.split()[-1] if prefix.split() else ""
        if previous not in _PATRONYMIC_CONNECTORS:
            split_matches.append(match)
    if not split_matches and force:
        split_matches.append(matches[-1])
    if not split_matches:
        return [surface]
    parts: list[str] = []
    start = 0
    for match in split_matches:
        left = surface[start:match.start()].strip()
        if left:
            parts.append(left)
        start = match.end()
    tail = surface[start:].strip()
    if tail:
        parts.append(tail)
    return parts if len(parts) > 1 else [surface]


def _repair_joined_name_tokens(value: str) -> str:
    """Separate common joined tokens after any leading conjunction is removed."""
    value = re.sub(r"\bبن(?=ال)", "بن ", value)
    return re.sub(r"\bعبد(?=الله)", "عبد ", value)


def _clean_surface(
    raw: str, *, force_co_transmitters: bool = False
) -> list[str]:
    explicit_pair = force_co_transmitters or bool(re.search(r"\bقالا\b", raw))
    raw = _EDITORIAL_RE.sub(" ", raw)
    raw = _HONORIFIC_RE.sub(" ", raw)
    raw = _repair_joined_name_tokens(raw)
    raw = re.sub(r"\s+ما\s*$", "", raw)
    raw = raw.strip()
    while True:
        cleaned_lead = _LEADING_LABEL_RE.sub("", raw, count=1)
        if cleaned_lead == raw:
            break
        raw = cleaned_lead.strip()
    raw = _TRAILING_FRAME_RE.sub("", raw)
    raw = _PUNCT_RE.sub(" ", raw)
    surface = re.sub(r"\s+", " ", raw).strip(" -")
    if not surface or not is_name_token(surface):
        return []
    if any(token in surface for token in ("رسول الله", "النبي صلى", "قال الله")):
        return []
    if len(surface.split()) > 14:
        return []
    parts = _split_co_transmitters(surface, force=explicit_pair)
    return [
        repaired for part in parts
        if is_name_token(repaired := _repair_joined_name_tokens(part))
    ]


def _extract_segment_branches(segment: str) -> list[list[str]]:
    boundary = _matn_start(segment)
    chain_text = segment[:boundary].strip() if boundary is not None else segment.strip()
    links = list(_LINK_RE.finditer(chain_text))
    if not links:
        alternatives = _clean_surface(chain_text)
        return [[surface] for surface in alternatives]

    levels: list[list[str]] = []
    prefix = chain_text[:links[0].start()].strip()
    if prefix and not any(mark in prefix for mark in ("\"", "«", "»")):
        cleaned = _clean_surface(prefix)
        if cleaned:
            levels.append(cleaned)
    for index, link in enumerate(links):
        next_link = links[index + 1] if index + 1 < len(links) else None
        end = next_link.start() if next_link is not None else len(chain_text)
        # A following dual verb marks the current level as parallel transmitters.
        force_pair = bool(
            next_link
            and re.match(r"(?:و?قالا)\b", next_link.group().strip())
        )
        cleaned = _clean_surface(
            chain_text[link.end():end], force_co_transmitters=force_pair
        )
        if cleaned:
            levels.append(cleaned)

    branches: list[list[str]] = [[]]
    for alternatives in levels:
        _check_branch_limit(
            "segment_co_transmitters", len(branches) * len(alternatives)
        )
        branches = [
            branch + [surface]
            for branch in branches
            for surface in alternatives
            if not branch or surface != branch[-1]
        ]
    return branches


def _matches(left: str, right: str) -> bool:
    a = name_normalize(left)
    b = name_normalize(right)
    if a == b:
        return True
    if len(a) < 4 or len(b) < 4:
        return False
    if a in b or b in a:
        return True
    at = {word for word in a.split() if len(word) >= 3}
    bt = {word for word in b.split() if len(word) >= 3}
    return len(at & bt) >= 2


def _suffix_alignment(earlier: list[str], last: list[str]) -> Optional[tuple[int, int]]:
    """Return (suffix length, last-branch start) for the strongest alignment."""
    for length in range(min(len(earlier), len(last)), 0, -1):
        suffix = earlier[-length:]
        for start in range(len(last) - length, -1, -1):
            if all(_matches(suffix[offset], last[start + offset]) for offset in range(length)):
                if length == 1 and name_normalize(suffix[0]) in _WEAK_CONVERGENCE:
                    continue
                return length, start
    return None


def extract_isnad_branches(text_ar: Optional[str]) -> list[list[str]]:
    """Extract ordered narrator surfaces, one list per taḥwīl branch."""
    if not text_ar or not text_ar.strip():
        _UNIFIED_CHAIN_STATS["rows_empty"] += 1
        return []

    _UNIFIED_CHAIN_STATS["rows_with_text"] += 1
    segments = _split_on_tahweel(text_ar)
    per_segment: list[list[list[str]]] = []
    collected_branches = 0
    for segment in segments:
        group = _extract_segment_branches(segment)
        if not group:
            continue
        _check_branch_limit(
            "tahweel_segment_collection", collected_branches + len(group)
        )
        collected_branches += len(group)
        per_segment.append(group)
    if not per_segment:
        return []
    if len(per_segment) == 1:
        branches = per_segment[0]
        if len(branches) == 1:
            _UNIFIED_CHAIN_STATS["rows_single"] += 1
        else:
            _UNIFIED_CHAIN_STATS["rows_branched"] += 1
        _UNIFIED_CHAIN_STATS["branches_total"] += len(branches)
        return branches

    last_group = per_segment[-1]
    projected = len(last_group) + sum(
        len(earlier_group) * len(last_group)
        for earlier_group in per_segment[:-1]
    )
    _check_branch_limit("tahweel_stitching", projected)
    branches: list[list[str]] = []
    for earlier_group in per_segment[:-1]:
        for earlier in earlier_group:
            stitched: list[list[str]] = []
            for last in last_group:
                alignment = _suffix_alignment(earlier, last)
                if alignment is None:
                    continue
                length, start = alignment
                stitched.append(earlier + last[start + length:])
            if stitched:
                branches.extend(stitched)
            else:
                _UNIFIED_CHAIN_STATS["branches_unstitched"] += 1
                branches.append(earlier)
    branches.extend(last_group)
    deduplicated: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for branch in branches:
        key = tuple(branch)
        if key in seen:
            continue
        _check_branch_limit("tahweel_deduplication", len(deduplicated) + 1)
        seen.add(key)
        deduplicated.append(branch)
    branches = deduplicated
    _UNIFIED_CHAIN_STATS["rows_branched"] += 1
    _UNIFIED_CHAIN_STATS["branches_total"] += len(branches)
    return branches


def resolve_branches_to_indxs(
    branches: Iterable[Iterable[str]],
    resolve_narrator: Callable[[str], Optional[int]],
) -> list[list[int]]:
    """Resolve surfaces per branch while preserving branch boundaries."""
    resolved_branches: list[list[int]] = []
    for branch_index, branch in enumerate(branches):
        resolved: list[int] = []
        for narrator_index, surface in enumerate(branch):
            _UNIFIED_CHAIN_STATS["narrators_attempted"] += 1
            try:
                value = resolve_narrator(surface)
            except Exception as error:
                _UNIFIED_CHAIN_STATS["narrators_unresolved"] += 1
                _UNIFIED_CHAIN_STATS["rows_resolution_failed"] += 1
                raise UnresolvedNarratorError(
                    surface, branch_index, narrator_index,
                    f"resolver raised {type(error).__name__}",
                ) from error
            if value is None:
                _UNIFIED_CHAIN_STATS["narrators_unresolved"] += 1
                _UNIFIED_CHAIN_STATS["rows_resolution_failed"] += 1
                raise UnresolvedNarratorError(
                    surface, branch_index, narrator_index, "not found or ambiguous"
                )
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                _UNIFIED_CHAIN_STATS["narrators_invalid"] += 1
                _UNIFIED_CHAIN_STATS["rows_resolution_failed"] += 1
                raise UnresolvedNarratorError(
                    surface, branch_index, narrator_index,
                    f"invalid resolver value {value!r}",
                )
            if parsed <= 0:
                _UNIFIED_CHAIN_STATS["narrators_invalid"] += 1
                _UNIFIED_CHAIN_STATS["rows_resolution_failed"] += 1
                raise UnresolvedNarratorError(
                    surface, branch_index, narrator_index,
                    f"non-positive resolver value {parsed}",
                )
            resolved.append(parsed)
            _UNIFIED_CHAIN_STATS["narrators_resolved"] += 1
        resolved_branches.append(resolved)
    return resolved_branches


def _fallback_cell(fallback: object) -> str:
    if isinstance(fallback, str):
        return fallback.strip()
    if isinstance(fallback, (list, tuple)):
        if fallback and all(isinstance(item, (list, tuple)) for item in fallback):
            return "|".join(
                ",".join(str(value) for value in branch if str(value).strip())
                for branch in fallback
                if branch
            )
        return ",".join(str(value) for value in fallback if str(value).strip())
    return ""


def _compute_chain_indx(
    text_ar: Optional[str],
    fallback: object = None,
    resolve_narrator: Optional[Callable[[str], Optional[int]]] = None,
) -> str:
    """Return the loader's comma/pipe chain cell without guessing identities."""
    if not text_ar or not text_ar.strip():
        cell = _fallback_cell(fallback)
        if cell:
            _UNIFIED_CHAIN_STATS["fallback_used"] += 1
        return cell
    if resolve_narrator is None:
        raise ValueError("resolve_narrator is required when text_ar is present")
    resolved = resolve_branches_to_indxs(
        extract_isnad_branches(text_ar), resolve_narrator
    )
    return "|".join(",".join(str(value) for value in branch) for branch in resolved)


__all__ = [
    "_UNIFIED_CHAIN_STATS",
    "_compute_chain_indx",
    "IsnadExtractionLimitError",
    "MAX_ISNAD_BRANCHES",
    "UnresolvedNarratorError",
    "extract_isnad_branches",
    "is_name_token",
    "name_normalize",
    "reset_stats",
    "resolve_branches_to_indxs",
]
