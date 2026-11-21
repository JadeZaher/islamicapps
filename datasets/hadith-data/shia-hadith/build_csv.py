"""
Transform ThaqalaynAPI V2 JSON files into a clean CSV.
Outputs: all_hadiths_shia.csv in the parent hadith-data directory.

Columns match the Sunni all_hadiths_clean.csv schema + bonus Shia-specific fields:
  id, hadith_id, source, volume, chapter_no, hadith_no, chapter, category,
  chain_indx, text_ar, text_en, sanad, matn_en,
  grading_majlisi, grading_mohseni, grading_behbudi, gradings_full, url
"""

import argparse
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

_RESOLVER_IMPORT_ERROR = None

try:
    import extract_isnad_unified as _isnad_extractor
    from regen_unified_csvs import (
        build_narrator_index as _build_narrator_index,
        resolve_narrator as _resolve_narrator,
    )

    _compute_chain_indx = getattr(_isnad_extractor, "_compute_chain_indx")
    if not callable(_compute_chain_indx):
        raise ImportError("extract_isnad_unified._compute_chain_indx is not callable")
    _UNIFIED_CHAIN_STATS = getattr(_isnad_extractor, "_UNIFIED_CHAIN_STATS", {})
    if not hasattr(_UNIFIED_CHAIN_STATS, "get"):
        _UNIFIED_CHAIN_STATS = {}
    _ROW_LEVEL_EXTRACTOR_ERRORS = tuple(
        error_type
        for name in ("UnresolvedNarratorError", "IsnadExtractionLimitError")
        if isinstance(
            (error_type := getattr(_isnad_extractor, name, None)), type
        ) and issubclass(error_type, Exception)
    )

    _ALL_RAWIS_PATH = os.path.join(
        _DATASETS_DIR, "narrator-data", "all_rawis.csv"
    )

    def _load_resolver_indices():
        if not os.path.isfile(_ALL_RAWIS_PATH):
            raise FileNotFoundError(
                f"Narrator resolver source is missing: {_ALL_RAWIS_PATH}"
            )
        return _build_narrator_index(_ALL_RAWIS_PATH)

    def _make_resolver(exact_index, blocked_index, runtime_stats):
        """Bind indices and record resolver calls independently of telemetry."""
        def _resolve(name: str):
            runtime_stats["narrators_attempted"] += 1
            indx = _resolve_narrator(name, exact_index, blocked_index)
            if indx is None:
                return None
            try:
                resolved = int(indx)
            except (TypeError, ValueError):
                return None
            runtime_stats["narrators_resolved"] += 1
            return resolved
        return _resolve

    _RESOLVER_AVAILABLE = True
except (ImportError, AttributeError) as _e:
    _RESOLVER_AVAILABLE = False
    _RESOLVER_IMPORT_ERROR = _e
    _UNIFIED_CHAIN_STATS = {}  # type: ignore[assignment]
    _ROW_LEVEL_EXTRACTOR_ERRORS = ()

    def _compute_chain_indx(text_ar, fallback=None, resolve_narrator=None):  # type: ignore[misc]
        return ""

    def _load_resolver_indices():  # type: ignore[misc]
        return {}, {}

    def _make_resolver(  # type: ignore[misc]
        exact_index, blocked_index, runtime_stats
    ):
        return lambda name: None

# ---------------------------------------------------------------------------

INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2_books")
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "all_hadiths_shia.csv")

COLUMNS = [
    "id",
    "hadith_id",
    "provider_file_id",
    "provider_book_id",
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
    provider_file_id: str,
    exact_index: dict,
    blocked_index: dict,
    chain_stats: dict,
    resolver,
    allow_empty_chain_dev: bool = False,
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
    try:
        chain_indx_str = _compute_chain_indx(
            text_ar=arabic_text or None,
            fallback=None,
            resolve_narrator=resolver,
        )
    except _ROW_LEVEL_EXTRACTOR_ERRORS as error:
        stat = (
            "rows_extraction_failed"
            if type(error).__name__ == "IsnadExtractionLimitError"
            else "rows_resolution_failed"
        )
        chain_stats[stat] = chain_stats.get(stat, 0) + 1
        chain_indx_str = ""
    except Exception as error:
        if not allow_empty_chain_dev:
            raise RuntimeError(
                "Thaqalayn isnad extractor contract failed for "
                f"provider_file_id={provider_file_id!r}, hadith_id={h.get('id')!r}; "
                "check the resolver callback signature and extractor imports: "
                f"{type(error).__name__}: {error}"
            ) from error
        chain_stats["extractor_failures_ignored"] += 1
        chain_indx_str = ""
    if not isinstance(chain_indx_str, str):
        if not allow_empty_chain_dev:
            raise RuntimeError(
                "Thaqalayn isnad extractor returned a non-string chain_indx for "
                f"provider_file_id={provider_file_id!r}, hadith_id={h.get('id')!r}: "
                f"{chain_indx_str!r}"
            )
        chain_stats["extractor_failures_ignored"] += 1
        chain_indx_str = ""
    if arabic_text:
        chain_stats["rows_with_arabic_text"] += 1
    else:
        chain_stats["rows_empty_arabic_text"] += 1
    if raw_sanad:
        chain_stats["rows_with_thaqalayn_sanad"] += 1

    return {
        "id": global_id,
        "hadith_id": h.get("id", ""),
        "provider_file_id": provider_file_id,
        "provider_book_id": h.get("bookId", ""),
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


def main(allow_empty_chain_dev: bool = False):
    json_files = sorted(
        glob.glob(os.path.join(INPUT_DIR, "[0-9]*.json")),
        key=lambda x: int(os.path.basename(x).replace(".json", "")),
    )

    if not json_files:
        print(f"No JSON files found in {INPUT_DIR}. Run download_thaqalayn.py first.")
        return 1

    print(f"Processing {len(json_files)} book files...")

    # Build resolver indices once (bilingual rawi lexicon).
    if not _RESOLVER_AVAILABLE and not allow_empty_chain_dev:
        detail = (
            f"{type(_RESOLVER_IMPORT_ERROR).__name__}: {_RESOLVER_IMPORT_ERROR}"
            if _RESOLVER_IMPORT_ERROR is not None
            else "unknown import error"
        )
        raise RuntimeError(
            "Canonical Thaqalayn rebuild requires the unified isnad extractor "
            f"and narrator resolver; dependency import failed: {detail}"
        ) from _RESOLVER_IMPORT_ERROR

    if _RESOLVER_AVAILABLE:
        print("Building narrator resolver indices...")
        try:
            exact_index, blocked_index = _load_resolver_indices()
        except (OSError, ValueError) as error:
            if not allow_empty_chain_dev:
                raise RuntimeError(
                    "Canonical Thaqalayn rebuild could not load narrator "
                    f"resolver indices: {type(error).__name__}: {error}"
                ) from error
            print(
                "  DEVELOPMENT FALLBACK: narrator indices unavailable; "
                f"chain_indx may be empty ({type(error).__name__}: {error})."
            )
            exact_index, blocked_index = {}, {}
        if (not exact_index or not blocked_index) and not allow_empty_chain_dev:
            raise RuntimeError(
                "Canonical Thaqalayn rebuild requires non-empty narrator "
                f"resolver indices; loaded exact={len(exact_index):,}, "
                f"blocked={len(blocked_index):,}."
            )
        print(f"  Resolver ready: {len(exact_index):,} exact entries, "
              f"{len(blocked_index):,} block buckets.")
    else:
        exact_index, blocked_index = {}, {}
        print(
            "  DEVELOPMENT FALLBACK: resolver import unavailable; "
            f"chain_indx will be empty ({type(_RESOLVER_IMPORT_ERROR).__name__}: "
            f"{_RESOLVER_IMPORT_ERROR})."
        )

    resolver_stats = {
        "narrators_attempted": 0,
        "narrators_resolved": 0,
    }
    resolver = _make_resolver(exact_index, blocked_index, resolver_stats)

    chain_stats = {
        "rows_with_arabic_text": 0,
        "rows_empty_arabic_text": 0,
        "rows_with_thaqalayn_sanad": 0,
        "rows_resolution_failed": 0,
        "rows_extraction_failed": 0,
        "extractor_failures_ignored": 0,
    }

    global_id = 0
    total_written = 0

    output_dir = os.path.dirname(os.path.abspath(OUTPUT_PATH))
    os.makedirs(output_dir, exist_ok=True)
    staged_output = os.path.join(
        output_dir, f".{os.path.basename(OUTPUT_PATH)}.{os.getpid()}.tmp"
    )
    try:
        with open(staged_output, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(
                csvfile, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL
            )
            writer.writeheader()

            for jf in json_files:
                fname = os.path.basename(jf)
                provider_file_id = os.path.splitext(fname)[0]
                with open(jf, "r", encoding="utf-8") as f:
                    hadiths = json.load(f)

                book_name = hadiths[0]["bookId"] if hadiths else fname
                count = 0

                for h in hadiths:
                    global_id += 1
                    row = transform_hadith(
                        h,
                        global_id,
                        provider_file_id,
                        exact_index,
                        blocked_index,
                        chain_stats,
                        resolver,
                        allow_empty_chain_dev=allow_empty_chain_dev,
                    )
                    writer.writerow(row)
                    count += 1

                total_written += count
                print(f"  {fname:10s} -> {book_name:55s} ({count:,} rows)")

        if (
            chain_stats["rows_with_arabic_text"]
            and resolver_stats["narrators_attempted"] == 0
            and not allow_empty_chain_dev
        ):
            raise RuntimeError(
                "Canonical Thaqalayn rebuild processed non-empty Arabic text "
                "but the extractor never invoked the narrator resolver; the "
                "extractor implementation is unavailable or incompatible."
            )
        os.replace(staged_output, OUTPUT_PATH)
    finally:
        if os.path.exists(staged_output):
            os.remove(staged_output)

    print(f"\nTotal rows written: {total_written:,}")
    print(f"Output: {os.path.abspath(OUTPUT_PATH)}")

    # Quick verification
    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"File size: {size_mb:.1f} MB")

    # Correctness uses local resolver-call stats; extractor telemetry is optional.
    # FR-3.2 (uniform_isnad_extraction Phase 2): chain_indx is now driven by
    # the Arabic isnad in `arabicText`, not the English `thaqalaynSanad`.
    print(
        f"\nThaqalayn chain_indx: "
        f"{resolver_stats['narrators_resolved']:,} narrators resolved / "
        f"{resolver_stats['narrators_attempted']:,} attempted; "
        f"{chain_stats['rows_with_arabic_text']:,} rows with arabicText, "
        f"{chain_stats['rows_empty_arabic_text']:,} rows empty, "
        f"{chain_stats['rows_with_thaqalayn_sanad']:,} rows had English thaqalaynSanad (now sanad column only); "
        f"{chain_stats['rows_resolution_failed']:,} row-level resolution failures, "
        f"{chain_stats['rows_extraction_failed']:,} branch-limit failures."
    )
    if _UNIFIED_CHAIN_STATS:
        print(f"  Extractor telemetry: {dict(_UNIFIED_CHAIN_STATS)}")
    if chain_stats["extractor_failures_ignored"]:
        print(
            "  DEVELOPMENT FALLBACK ignored "
            f"{chain_stats['extractor_failures_ignored']:,} extractor failures."
        )
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-empty-chain-dev",
        action="store_true",
        help=(
            "Development only: allow missing/broken isnad resolver dependencies "
            "and emit empty chain_indx values"
        ),
    )
    sys.exit(main(allow_empty_chain_dev=parser.parse_args().allow_empty_chain_dev))
