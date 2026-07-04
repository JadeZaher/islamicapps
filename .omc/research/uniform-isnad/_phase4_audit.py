"""Phase 4 T-4.1: Categorize unresolved narrator surface forms.

Reads sunni_isnad.jsonl (K6 sidecar), runs every distinct narrator surface
through the existing resolver, and bucketises the misses. Emits a Markdown
table under .omc/research/uniform-isnad/phase4-kunya-gap.md.

Categories:
    1. kunya_only        : starts with ابو/ابي/ام/ابن/بنت (post-_norm) AND is short
    2. en_translit       : ASCII alphabetic characters present
    3. multitoken_arabic : multi-token Arabic without a kunya prefix
    4. pronoun_elided    : ابي/اخبرني/عنه/هو alone or other elided refs
    5. other_garbage     : digits, very short (<3 chars), non-name strings
"""
from __future__ import annotations

import json
import pathlib
import sys
from collections import Counter, defaultdict

_HERE = pathlib.Path(__file__).resolve().parent
_REPO = _HERE.parents[2]  # .omc/research/uniform-isnad/ -> repo root

sys.path.insert(0, str(_REPO / "datasets"))
sys.path.insert(0, str(_REPO / "datasets" / "hadith-data"))

from classify_attribution import _norm  # noqa: E402
from regen_unified_csvs import build_narrator_index, resolve_narrator  # noqa: E402

ALL_RAWIS = _REPO / "datasets" / "narrator-data" / "all_rawis.csv"
SIDECAR = _REPO / "datasets" / "hadith-data" / "sunni_isnad.jsonl"
OUT = _HERE / "phase4-kunya-gap.md"

# Normalized kunya prefixes (post-_norm: ابو/ابي/ام/ابن/بنت)
_KUNYA_PREFIXES_NORM = ("ابو", "ابي", "ام", "ابن", "بنت")
_PRONOUNS_NORM = {"ابي", "اخبرني", "عنه", "هو", "حدثنا", "اخبرنا", "قال", "عن"}


def _has_ascii_letter(s: str) -> bool:
    return any("a" <= c.lower() <= "z" for c in s)


def _has_digit(s: str) -> bool:
    return any(c.isdigit() for c in s)


def _categorize(surface: str) -> str:
    norm = _norm(surface).strip()
    if not norm:
        return "other_garbage"
    if _has_digit(norm):
        return "other_garbage"
    if len(norm) < 3:
        return "other_garbage"

    # English transliteration first (ASCII letters dominate)
    if _has_ascii_letter(surface):
        return "en_translit"

    tokens = norm.split()
    first = tokens[0] if tokens else ""

    # Pronoun / elided ref (single token that's a pronoun OR a bare kunya word)
    if len(tokens) == 1 and norm in _PRONOUNS_NORM:
        return "pronoun_elided"

    # Kunya-only: starts with a kunya prefix
    if first in _KUNYA_PREFIXES_NORM:
        return "kunya_only"

    # Multi-token Arabic with no kunya prefix
    if len(tokens) >= 2:
        return "multitoken_arabic"

    # Single Arabic token, not a pronoun, not a kunya prefix
    return "multitoken_arabic"  # treat single-name as same bucket


def main() -> int:
    if not SIDECAR.exists():
        print(f"missing: {SIDECAR}", file=sys.stderr)
        return 1
    if not ALL_RAWIS.exists():
        print(f"missing: {ALL_RAWIS}", file=sys.stderr)
        return 1

    print("Building narrator index (current/pre-fix)...", file=sys.stderr)
    exact_index, blocked_index = build_narrator_index(str(ALL_RAWIS))
    print(f"  exact_index: {len(exact_index):,}, blocked_index: {len(blocked_index):,}",
          file=sys.stderr)

    print("Scanning sidecar for surface forms...", file=sys.stderr)
    surface_counts: Counter[str] = Counter()
    with SIDECAR.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            for s in obj.get("sanad", []) or []:
                if isinstance(s, str):
                    surface_counts[s.strip()] += 1

    print(f"  distinct surface forms: {len(surface_counts):,}", file=sys.stderr)
    print(f"  total surface occurrences: {sum(surface_counts.values()):,}",
          file=sys.stderr)

    resolved_count = 0
    miss_count = 0
    miss_by_cat: dict[str, list[str]] = defaultdict(list)
    miss_total_occurrences: dict[str, int] = defaultdict(int)
    distinct_miss_by_cat: dict[str, int] = defaultdict(int)

    for surface, count in surface_counts.items():
        indx = resolve_narrator(surface, exact_index, blocked_index)
        if indx:
            resolved_count += count
        else:
            miss_count += count
            cat = _categorize(surface)
            distinct_miss_by_cat[cat] += 1
            miss_total_occurrences[cat] += count
            if len(miss_by_cat[cat]) < 5:
                miss_by_cat[cat].append(surface)

    total_occ = resolved_count + miss_count
    print(f"  resolved occurrences: {resolved_count:,} / {total_occ:,} "
          f"({100*resolved_count/total_occ:.2f}%)", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Phase 4 T-4.1 — Kunya-Gap Audit",
        "",
        "Source: `datasets/hadith-data/sunni_isnad.jsonl` (K6 sidecar).",
        "Resolver: `build_narrator_index` + `resolve_narrator` from "
        "`datasets/hadith-data/regen_unified_csvs.py` (pre-Phase-4 state).",
        "",
        "## Overall",
        "",
        f"- Distinct surface forms scanned: **{len(surface_counts):,}**",
        f"- Total occurrences across sanads: **{total_occ:,}**",
        f"- Resolved occurrences: **{resolved_count:,}** "
        f"({100*resolved_count/total_occ:.2f}%)",
        f"- Missed occurrences: **{miss_count:,}** "
        f"({100*miss_count/total_occ:.2f}%)",
        f"- Distinct missed surface forms: **{sum(distinct_miss_by_cat.values()):,}**",
        "",
        "## Miss categorization (distinct surface forms)",
        "",
        "| Category | Distinct misses | Total occurrences | Example surfaces (first 5) |",
        "| :--- | ---: | ---: | :--- |",
    ]
    order = sorted(distinct_miss_by_cat.keys(),
                   key=lambda k: -distinct_miss_by_cat[k])
    for cat in order:
        n_distinct = distinct_miss_by_cat[cat]
        n_occ = miss_total_occurrences[cat]
        examples = " · ".join(f"`{s}`" for s in miss_by_cat[cat])
        lines.append(f"| {cat} | {n_distinct:,} | {n_occ:,} | {examples} |")

    lines += [
        "",
        "## Notes on scope",
        "",
        "- Phase 4 T-4.2 implements **unique-kunya aliasing** only. Aliases that",
        "  map to ≥2 scholars are intentionally left unresolved (no guessing).",
        "- The plan's T-4.3 ambiguous-kunya disambiguator (death-date proximity,",
        "  teacher-student adjacency) is deferred to a future track.",
        "- `en_translit` and `pronoun_elided` are OUT OF SCOPE for this phase",
        "  and should be filed as follow-up tracks if their counts are material.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Written: {OUT}", file=sys.stderr)

    # Print a concise stdout summary
    print("\n=== Miss-by-category (distinct surface forms) ===")
    for cat in order:
        print(f"  {cat:20s} {distinct_miss_by_cat[cat]:>7,} distinct  "
              f"{miss_total_occurrences[cat]:>9,} occ")
    print(f"\nResolution rate (occurrences): "
          f"{100*resolved_count/total_occ:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
