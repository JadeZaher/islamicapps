"""
Transform ThaqalaynAPI V2 JSON files into a clean CSV.
Outputs: all_hadiths_shia.csv in the parent hadith-data directory.

Columns match the Sunni all_hadiths_clean.csv schema + bonus Shia-specific fields:
  id, hadith_id, source, volume, chapter_no, hadith_no, chapter, category,
  chain_indx, text_ar, text_en, sanad, matn_en,
  grading_majlisi, grading_mohseni, grading_behbudi, gradings_full, url
"""

import csv
import glob
import json
import os
import sys

# ---------------------------------------------------------------------------
# Resolver imports (optional — graceful fallback if run standalone outside pipeline)
# ---------------------------------------------------------------------------
if True:  # scope guard so the sys.path manipulation is clearly bounded
    _HERE = os.path.dirname(os.path.abspath(__file__))
    _HADITH_DATA_DIR = os.path.dirname(_HERE)
    _DATASETS_DIR = os.path.dirname(_HADITH_DATA_DIR)
    for _p in (_HADITH_DATA_DIR, _DATASETS_DIR):
        if _p not in sys.path:
            sys.path.insert(0, _p)

try:
    from extract_isnad_unified import _compute_chain_indx, _UNIFIED_CHAIN_STATS
    from regen_unified_csvs import (
        build_narrator_index as _build_narrator_index,
        resolve_narrator as _resolve_narrator,
    )

    _ALL_RAWIS_PATH = os.path.join(
        _DATASETS_DIR, "narrator-data", "all_rawis.csv"
    )

    def _load_resolver_indices():
        if os.path.exists(_ALL_RAWIS_PATH):
            return _build_narrator_index(_ALL_RAWIS_PATH)
        return {}, {}

    def _make_resolver(exact_index, blocked_index):
        """Bind the (exact_index, blocked_index) dicts into the resolver
        callable expected by `_compute_chain_indx` from
        `extract_isnad_unified`. Mirrors the closure in regen_unified_csvs.
        """
        def _resolve(name: str):
            indx = _resolve_narrator(name, exact_index, blocked_index)
            if indx is None:
                return None
            try:
                return int(indx)
            except (TypeError, ValueError):
                return None
        return _resolve

    _RESOLVER_AVAILABLE = True
except ImportError as _e:
    _RESOLVER_AVAILABLE = False
    _UNIFIED_CHAIN_STATS = {}  # type: ignore[assignment]

    def _compute_chain_indx(text_ar, fallback=None, resolve_narrator=None):  # type: ignore[misc]
        return ""

    def _load_resolver_indices():  # type: ignore[misc]
        return {}, {}

    def _make_resolver(exact_index, blocked_index):  # type: ignore[misc]
        return lambda name: None

# ---------------------------------------------------------------------------

INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2_books")
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "all_hadiths_shia.csv")

COLUMNS = [
    "id",
    "hadith_id",
    "source",
    "volume",
    "chapter_no",
    "hadith_no",
    "chapter",
    "category",
    "chain_indx",
    "text_ar",
    "text_en",
    "sanad",
    "matn_en",
    "grading_majlisi",
    "grading_mohseni",
    "grading_behbudi",
    "gradings_full",
    "url",
]


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    # Normalize whitespace but preserve Arabic/Unicode
    return " ".join(text.split())


def serialize_gradings(gradings_full: list | None) -> str:
    if not gradings_full:
        return ""
    parts = []
    for g in gradings_full:
        author = g.get("author", {}) or {}
        name = author.get("name_en") or author.get("name_ar") or "Unknown"
        grade = g.get("grade_en") or g.get("grade_ar") or ""
        ref = g.get("reference_en") or ""
        parts.append(f"{name}: {grade} ({ref})" if ref else f"{name}: {grade}")
    return " | ".join(parts)


def transform_hadith(
    h: dict,
    global_id: int,
    exact_index: dict,
    blocked_index: dict,
    chain_stats: dict,
    resolver,
) -> dict:
    """Build one Imami CSV row from a Thaqalayn V2 hadith dict.

    FR-3.2 (uniform_isnad_extraction Phase 2): chain_indx is now produced
    by `_compute_chain_indx(text_ar=arabicText, ...)`, NOT from the English
    `thaqalaynSanad` field. The Arabic isnad in `arabicText` is the canonical
    source for taḥwīl-aware extraction; the English narrative sanad is
    preserved verbatim in the `sanad` column for downstream readers.
    """
    raw_sanad = h.get("thaqalaynSanad", "")
    arabic_text = clean_text(h.get("arabicText", ""))
    chain_indx_str = _compute_chain_indx(
        text_ar=arabic_text or None,
        fallback=None,
        resolve_narrator=resolver,
    )
    if arabic_text:
        chain_stats["rows_with_arabic_text"] += 1
    else:
        chain_stats["rows_empty_arabic_text"] += 1
    if raw_sanad:
        chain_stats["rows_with_thaqalayn_sanad"] += 1

    return {
        "id": global_id,
        "hadith_id": h.get("id", ""),
        "source": h.get("book", ""),
        "volume": h.get("volume", ""),
        "chapter_no": h.get("categoryId", ""),
        "hadith_no": h.get("chapterInCategoryId", ""),
        "chapter": h.get("chapter", ""),
        "category": h.get("category", ""),
        "chain_indx": chain_indx_str,
        "text_ar": arabic_text,
        "text_en": clean_text(h.get("englishText", "")),
        "sanad": raw_sanad,
        "matn_en": clean_text(h.get("thaqalaynMatn", "")),
        "grading_majlisi": h.get("majlisiGrading", ""),
        "grading_mohseni": h.get("mohseniGrading", ""),
        "grading_behbudi": h.get("behbudiGrading", ""),
        "gradings_full": serialize_gradings(h.get("gradingsFull")),
        "url": h.get("URL", ""),
    }


def main():
    json_files = sorted(
        glob.glob(os.path.join(INPUT_DIR, "[0-9]*.json")),
        key=lambda x: int(os.path.basename(x).replace(".json", "")),
    )

    if not json_files:
        print(f"No JSON files found in {INPUT_DIR}. Run download_thaqalayn.py first.")
        sys.exit(1)

    print(f"Processing {len(json_files)} book files...")

    # Build resolver indices once (bilingual rawi lexicon)
    if _RESOLVER_AVAILABLE:
        print("Building narrator resolver indices...")
        exact_index, blocked_index = _load_resolver_indices()
        print(f"  Resolver ready: {len(exact_index):,} exact entries, "
              f"{len(blocked_index):,} block buckets.")
    else:
        exact_index, blocked_index = {}, {}
        print("  WARNING: Resolver not available — chain_indx will be empty.")

    resolver = _make_resolver(exact_index, blocked_index)

    chain_stats = {
        "rows_with_arabic_text": 0,
        "rows_empty_arabic_text": 0,
        "rows_with_thaqalayn_sanad": 0,
    }

    global_id = 0
    total_written = 0

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        for jf in json_files:
            fname = os.path.basename(jf)
            with open(jf, "r", encoding="utf-8") as f:
                hadiths = json.load(f)

            book_name = hadiths[0]["bookId"] if hadiths else fname
            count = 0

            for h in hadiths:
                global_id += 1
                row = transform_hadith(
                    h, global_id, exact_index, blocked_index, chain_stats, resolver,
                )
                writer.writerow(row)
                count += 1

            total_written += count
            print(f"  {fname:10s} -> {book_name:55s} ({count:,} rows)")

    print(f"\nTotal rows written: {total_written:,}")
    print(f"Output: {os.path.abspath(OUTPUT_PATH)}")

    # Quick verification
    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"File size: {size_mb:.1f} MB")

    # Chain_indx resolution summary — sourced from unified extractor telemetry.
    # FR-3.2 (uniform_isnad_extraction Phase 2): chain_indx is now driven by
    # the Arabic isnad in `arabicText`, not the English `thaqalaynSanad`.
    print(
        f"\nThaqalayn chain_indx: "
        f"{_UNIFIED_CHAIN_STATS.get('narrators_resolved', 0):,} narrators resolved / "
        f"{_UNIFIED_CHAIN_STATS.get('narrators_attempted', 0):,} attempted; "
        f"{chain_stats['rows_with_arabic_text']:,} rows with arabicText, "
        f"{chain_stats['rows_empty_arabic_text']:,} rows empty, "
        f"{chain_stats['rows_with_thaqalayn_sanad']:,} rows had English thaqalaynSanad (now sanad column only)."
    )


if __name__ == "__main__":
    main()
