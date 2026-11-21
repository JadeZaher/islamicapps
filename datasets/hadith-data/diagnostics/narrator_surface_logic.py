"""Pure logic for narrator-surface diagnostics: categories, name components, candidate scoring.

Nothing here asserts identity. Scoring produces RANKED CANDIDATES with the evidence that
produced them; see diagnostics/AGENTS.md. Surfaces are expected to be already normalized
with regen.narrator_normalize (NFKC, no diacritics/tatweel, alef and ya folded).
"""

import re
from dataclasses import dataclass, field

ARABIC_RUN = re.compile(r"[ء-ي]+")
KUNYA_HEADS = {"ابو", "ابي", "ابا", "ام"}
CONNECTORS = {"بن", "ابن", "بنت"}
NO_NISBA = {"الله", "الدين"}

# Surfaces that denote a relation or fragment, never a registry identity on their own.
RELATIONAL_TOKENS = {
    "ابيه", "ابي", "ابوه", "ابنه", "جده", "جدي", "امه", "اخيه", "عمه", "خاله", "اخوه",
    "عنه", "عنها", "ابيها", "ابنها", "جدته", "جدها", "ابويه", "ابوي", "ابي", "ابن", "بن",
}
COLLECTIVE_MARKERS = ("عده", "بعض", "رجل", "رجال", "اصحابنا", "اصحاب", "غير واحد", "جماعه",
                      "نفر", "ابائه", "اباءه", "قوم", "شيخ", "امراه", "ناس", "اهل")

CATEGORY_ORDER = (
    "relational_or_fragment", "collective_or_anonymous", "kunya_only", "ibn_nasab_only",
    "single_ism_or_laqab", "ism_nasab", "other_multi_token",
)

# Weights of name components when a candidate corroborates what the surface states.
WEIGHTS = {"ism": 0.30, "father": 0.25, "grandfather": 0.10, "kunya": 0.15, "nisba": 0.15}
CONFLICT_PENALTY = {"father": 0.25, "grandfather": 0.10, "kunya": 0.10, "nisba": 0.10}


def arabic_tokens(text: str) -> list[str]:
    """Arabic letter runs only; punctuation and Latin text are dropped."""
    return ARABIC_RUN.findall(text or "")


def categorize_surface(norm: str) -> str:
    """Heuristic bucket for a normalized surface (a triage label, not a claim)."""
    tokens = norm.split()
    if not tokens or (len(tokens) == 1 and (len(tokens[0]) <= 1 or tokens[0] in RELATIONAL_TOKENS)):
        return "relational_or_fragment"
    text = " ".join(tokens)
    padded = f" {text} "
    if any(f" {marker} " in padded for marker in COLLECTIVE_MARKERS) and "بن" not in tokens:
        return "collective_or_anonymous"
    if tokens[0] in KUNYA_HEADS and "بن" not in tokens and len(tokens) <= 4:
        return "kunya_only"
    if tokens[0] in ("ابن", "بن", "بنت") and len(tokens) <= 4:
        return "ibn_nasab_only"
    if len(tokens) == 1:
        return "single_ism_or_laqab"
    if "بن" in tokens[1:] or "بنت" in tokens[1:]:
        return "ism_nasab"
    return "other_multi_token"


def compare_fold(text: str) -> str:
    """Comparison-only fold (ta marbuta to ha, kunya case forms); never used for exact lookup."""
    return (text or "").replace("ة", "ه")


@dataclass
class NameComponents:
    units: list = field(default_factory=list)
    ism: str | None = None
    kunya: str | None = None
    nasab: list = field(default_factory=list)
    nisbas: list = field(default_factory=list)
    other: list = field(default_factory=list)


def merge_units(tokens: list[str]) -> list[str]:
    """Join compound names ('عبد' + 'الله') and fold kunya case (ابي/ابا to ابو) into units."""
    units: list[str] = []
    index = 0
    while index < len(tokens):
        token = compare_fold(tokens[index])
        if token == "عبد" and index + 1 < len(tokens):
            units.append(f"عبد {compare_fold(tokens[index + 1])}")
            index += 2
            continue
        if token in ("ابي", "ابا"):
            token = "ابو"
        units.append(token)
        index += 1
    return units


def _is_nisba(unit: str) -> bool:
    return unit.startswith("ال") and len(unit) > 3 and unit not in NO_NISBA


def parse_components(norm: str) -> NameComponents:
    """Split a name into ism, kunya, nasab chain (father, grandfather, ...), nisba(s)."""
    units = merge_units(arabic_tokens(norm))
    parsed = NameComponents(units=units)
    connector_seen = False
    index = 0
    while index < len(units):
        unit = units[index]
        if unit in ("بن", "ابن", "بنت"):
            connector_seen = True
            index += 1
            if index < len(units):
                member = units[index]
                if member == "ابو" and index + 1 < len(units):
                    member = f"ابو {units[index + 1]}"
                    index += 1
                parsed.nasab.append(member)
                index += 1
            continue
        if not connector_seen and unit == "ابو" and index + 1 < len(units) \
                and units[index + 1] not in ("بن", "ابن", "بنت"):
            parsed.kunya = f"ابو {units[index + 1]}"
            index += 2
            continue
        if _is_nisba(unit):
            parsed.nisbas.append(unit)
        elif not connector_seen and parsed.ism is None:
            parsed.ism = unit
        else:
            parsed.other.append(unit)
        index += 1
    return parsed


def _contiguous(needle: list, haystack: list) -> bool:
    size = len(needle)
    return size > 0 and any(haystack[i:i + size] == needle for i in range(len(haystack) - size + 1))


def score_candidate(surface: NameComponents, registry: NameComponents,
                    registry_alias_units: list | None = None) -> tuple[float, list, list]:
    """Return (score, evidence, conflicts). Absolute scale: matched weights minus conflict penalties.

    A candidate is never an identity: kunya/prefix/containment evidence only ranks reviewer attention.
    """
    evidence: list[str] = []
    conflicts: list[str] = []
    if surface.units and surface.units == registry.units:
        return 1.0, ["exact_normalized_equal"], conflicts
    if registry_alias_units and surface.units == registry_alias_units:
        return 0.9, ["registry_declared_alias_segment_equal"], conflicts

    score = 0.0
    if surface.ism and registry.ism and surface.ism == registry.ism:
        score += WEIGHTS["ism"]
        evidence.append(f"ism={surface.ism}")
    for depth, key in enumerate(("father", "grandfather")):
        if len(surface.nasab) > depth:
            if len(registry.nasab) > depth and surface.nasab[depth] == registry.nasab[depth]:
                score += WEIGHTS[key]
                evidence.append(f"{key}={surface.nasab[depth]}")
            elif len(registry.nasab) > depth:
                score -= CONFLICT_PENALTY[key]
                conflicts.append(f"{key}_conflict:{surface.nasab[depth]}!={registry.nasab[depth]}")
    if surface.kunya:
        if registry.kunya == surface.kunya:
            score += WEIGHTS["kunya"]
            evidence.append(f"kunya={surface.kunya}")
        elif registry.kunya:
            score -= CONFLICT_PENALTY["kunya"]
            conflicts.append(f"kunya_conflict:{surface.kunya}!={registry.kunya}")
    if surface.nisbas:
        overlap = set(surface.nisbas) & set(registry.nisbas)
        if overlap:
            score += WEIGHTS["nisba"]
            evidence.append("nisba=" + "|".join(sorted(overlap)))
        elif registry.nisbas:
            score -= CONFLICT_PENALTY["nisba"]
            conflicts.append("nisba_conflict")
    if _contiguous(surface.units, registry.units):
        score += 0.10
        evidence.append("surface_contiguous_in_registry_name")
        if registry.units[:len(surface.units)] == surface.units:
            score += 0.05
            evidence.append("registry_name_starts_with_surface")
    return max(0.0, min(1.0, round(score, 4))), evidence, conflicts


def parse_indx_list(text: str) -> set:
    """Parse a registry teachers_inds/students_inds cell ('3, 4, 5' or 'NA')."""
    return {part.strip() for part in (text or "").split(",") if part.strip().isdigit()}


_GENERATION = re.compile(r"\[(\d+)(?:st|nd|rd|th)\s+generation\]", re.IGNORECASE)


def parse_generation(grade: str) -> int | None:
    """Tabaqah number from '[6th generation]'; bare 'Comp.(RA)' is generation 1; otherwise unknown."""
    match = _GENERATION.search(grade or "")
    if match:
        return int(match.group(1))
    if (grade or "").strip().startswith("Comp.(RA)"):
        return 1
    return None


def parse_father_indx(parents: str) -> str | None:
    """First bracketed id in the father half of the registry 'parents' cell ('Name [500] / Mother')."""
    father_half = (parents or "").split("/")[0]
    match = re.search(r"\[(\d+)\]", father_half)
    return match.group(1) if match else None


# --- Tier-0 lookup-side rules (diagnostic dry run only) -------------------------------------

_SEGMENT_SPLIT = re.compile(r"\s+-\s+|،|/")
_HONORIFIC_SUFFIX = re.compile(
    r"\s+(?:رضي الله عنه(?:ا|ما|م|ن)?|عليه(?:ما|م)? السلام|عليها السلام|صلي الله عليه(?: واله)? وسلم|رحمه الله|ع|ص)$"
)


_NON_ARABIC_KEEP_SEPARATORS = re.compile(r"[^؀-ۿ\s/،-]")


def registry_alias_segments(name_field: str) -> list[str]:
    """T0-b: Arabic segments of a RAW registry name field split on ' - ', '،' and '/' (needs 2+).

    Works on the raw field because regen._extract_arabic_name drops the ' - ' separator.
    """
    arabic_only = _NON_ARABIC_KEEP_SEPARATORS.sub(" ", name_field or "")
    segments = []
    for part in _SEGMENT_SPLIT.split(arabic_only):
        part = " ".join(part.split())
        if len(re.findall(r"[ء-ي]", part)) >= 3:
            segments.append(part)
    return segments if len(segments) >= 2 else []


def fold_kunya_head(norm: str) -> str:
    """T0-c: fold a leading ابي/ابا to ابو, only when at least one name token follows."""
    tokens = norm.split()
    if len(tokens) >= 2 and tokens[0] in ("ابي", "ابا"):
        return " ".join(["ابو"] + tokens[1:])
    return norm


def strip_trailing_honorific(norm: str) -> str:
    """T0-d: remove a trailing honorific formula (token-bounded), keeping at least one token."""
    stripped = _HONORIFIC_SUFFIX.sub("", norm)
    return stripped if stripped.split() else norm
