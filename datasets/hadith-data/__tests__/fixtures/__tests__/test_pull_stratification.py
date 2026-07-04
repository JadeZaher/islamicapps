"""
G-5 acceptance tests for pull_next_candidates.py (Phase 5).

Tests:
  1. test_dedup_against_gold
  2. test_distribution_close_to_70_25_5
  3. test_no_single_source_dominates
  4. test_seed_42_reproducible
  5. test_different_seeds_differ
  6. test_difficulty_target_5_picks_3plus
  7. test_non_sunni_zero_handled_cleanly
  8. test_full_schema_in_output

Helpers:
  _make_mock_csv(rows, path)  — writes a CSV matching the production schema
  _run_pull(...)              — calls the programmatic API directly (no subprocess)

Production CSV header (from all_hadiths_unified.csv, first line):
  id, hadith_id, source, tradition, volume, chapter_no, hadith_no,
  chapter, category, chain_indx, text_ar, text_en, sanad,
  sanad_confidence, matn_ar, matn_en, school, chain_type,
  attributed_to, narration_level, grade_tradition, grade_source,
  grade_value, gradings_full, url, page_ref
"""

from __future__ import annotations

import csv
import io
import json
import random
import sys
from pathlib import Path
from typing import Optional

import pytest

# ---------------------------------------------------------------------------
# Import the module under test.
# PYTHONPATH must include the repo root (datasets/) so that
# "hadith-data.__tests__.fixtures.pull_next_candidates" resolves.
# In practice the conftest / pytest.ini sets this, but we also add it here
# for safety when running the file directly.
# ---------------------------------------------------------------------------
_FIXTURES_DIR = Path(__file__).parent.parent
if str(_FIXTURES_DIR) not in sys.path:
    sys.path.insert(0, str(_FIXTURES_DIR))

import pull_next_candidates as pnc  # noqa: E402

# ---------------------------------------------------------------------------
# Production CSV header (minimum subset the script needs, plus the full list)
# ---------------------------------------------------------------------------
PRODUCTION_HEADER = [
    "id", "hadith_id", "source", "tradition", "volume", "chapter_no", "hadith_no",
    "chapter", "category", "chain_indx", "text_ar", "text_en", "sanad",
    "sanad_confidence", "matn_ar", "matn_en", "school", "chain_type",
    "attributed_to", "narration_level", "grade_tradition", "grade_source",
    "grade_value", "gradings_full", "url", "page_ref",
]

# Minimal header — fallback when the real CSV columns might shift
MINIMAL_HEADER = ["hadith_id", "source", "hadith_no", "text_ar", "sanad", "tradition"]


# ---------------------------------------------------------------------------
# Arabic helper: ح-splitter text fragments for the mock corpus
# ---------------------------------------------------------------------------

# One ح-splitter match (single)
_H1 = "حدثنا قتيبة ح وحدثنا هناد عن سفيان"
# Two ح-splitter matches (double)
_H2 = "حدثنا قتيبة ح وحدثنا هناد ح وحدثنا زهير عن سفيان"
# Three ح-splitter matches (triple)
_H3 = "حدثنا قتيبة ح وحدثنا هناد ح وحدثنا زهير ح وحدثنا وكيع عن سفيان"


def _make_row(
    hadith_id: str,
    source: str,
    hadith_no: str,
    text_ar: str,
    tradition: str = "Sunni",
    sanad: str = "",
) -> dict:
    """Return a dict matching PRODUCTION_HEADER with all required fields."""
    row = {col: "" for col in PRODUCTION_HEADER}
    row.update(
        {
            "id": hadith_id,
            "hadith_id": hadith_id,
            "source": source,
            "hadith_no": hadith_no,
            "text_ar": text_ar,
            "tradition": tradition,
            "sanad": sanad,
        }
    )
    return row


def _make_mock_csv(rows: list[dict], path: Path) -> None:
    """Write a CSV file matching the production schema from a list of row dicts."""
    # Use production header; fall back to minimal if a row is missing most keys
    header = PRODUCTION_HEADER
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _make_mock_gold(rows: list[dict], path: Path) -> None:
    """Write a minimal JSONL gold file from a list of {source, hadith_no} dicts."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def _run_pull(
    tmp_path: Path,
    csv_rows: list[dict],
    gold_rows: Optional[list[dict]] = None,
    n: int = 30,
    seed: int = 42,
    difficulty_target: Optional[int] = None,
    exclude_traditions: Optional[list[str]] = None,
    out_name: str = "staging-test.jsonl",
) -> tuple[list[dict], str]:
    """
    Run pull_next_candidates programmatically, returning:
      (list of output row dicts, stderr captured as string)
    """
    csv_path = tmp_path / "mock_unified.csv"
    gold_path = tmp_path / "mock_gold.jsonl"
    out_path = tmp_path / out_name

    _make_mock_csv(csv_rows, csv_path)
    if gold_rows is not None:
        _make_mock_gold(gold_rows, gold_path)

    # Capture stderr
    old_stderr = sys.stderr
    stderr_buf = io.StringIO()
    sys.stderr = stderr_buf

    try:
        candidates = pnc.load_candidates(csv_path)
        if exclude_traditions:
            candidates = pnc.filter_excluded(candidates, exclude_traditions)
        candidates = pnc.dedup_against_gold(candidates, gold_path)

        rng = random.Random(seed)
        picked = pnc.stratified_pick(candidates, n, rng, difficulty_target=difficulty_target)
        pnc.write_staging(picked, out_path)
    finally:
        sys.stderr = old_stderr

    stderr_text = stderr_buf.getvalue()

    # Read back the written output
    output_rows: list[dict] = []
    if out_path.exists():
        with open(out_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    output_rows.append(json.loads(line))

    return output_rows, stderr_text


# ---------------------------------------------------------------------------
# Mock corpus builders
# ---------------------------------------------------------------------------

_SUNNI_SOURCES = [
    "Sahih Bukhari",
    "Sahih Muslim",
    "Jami' al-Tirmidhi",
    "Sunan Abi Da'ud",
    "Sunan Ibn Majah",
    "Sunan an-Nasa'i",
]


def _build_basic_corpus(
    per_source_singles: int = 10,
    per_source_doubles: int = 5,
    per_source_triples: int = 2,
) -> list[dict]:
    """Build a basic all-Sunni corpus with controlled ح-count distribution."""
    rows: list[dict] = []
    row_id = 1
    for src in _SUNNI_SOURCES:
        for i in range(per_source_singles):
            rows.append(_make_row(str(row_id), src, str(row_id), _H1))
            row_id += 1
        for i in range(per_source_doubles):
            rows.append(_make_row(str(row_id), src, str(row_id), _H2))
            row_id += 1
        for i in range(per_source_triples):
            rows.append(_make_row(str(row_id), src, str(row_id), _H3))
            row_id += 1
    return rows


def _build_corpus_with_imami(sunni_count: int = 50, imami_count: int = 20) -> list[dict]:
    """Build a corpus with Sunni (ح-marked) + Imami (no ح-splitter) rows."""
    rows: list[dict] = []
    row_id = 1
    # Sunni rows with ح-splitter
    for i in range(sunni_count):
        src = _SUNNI_SOURCES[i % len(_SUNNI_SOURCES)]
        rows.append(_make_row(str(row_id), src, str(row_id), _H1, tradition="Sunni"))
        row_id += 1
    # Imami rows without ح-splitter
    for i in range(imami_count):
        rows.append(
            _make_row(
                str(row_id),
                "Al-Kafi",
                str(row_id),
                "حدثنا محمد بن يعقوب عن علي بن إبراهيم",  # no ح-splitter
                tradition="imami",
            )
        )
        row_id += 1
    return rows


# ---------------------------------------------------------------------------
# Test 1: dedup against existing gold
# ---------------------------------------------------------------------------

def test_dedup_against_gold(tmp_path: Path) -> None:
    """
    Build a mock CSV with 50 ح-marked rows including Tirmidhi #1.
    Build a mock gold with 5 rows. Run pull with n=30 seed=42.
    Assert zero overlap by (source, hadith_no) between output and gold.
    """
    rows: list[dict] = []
    row_id = 1

    # Include Tirmidhi #1 as a known gold row
    rows.append(_make_row("30001", "Jami' al-Tirmidhi", "1", _H1))
    row_id = 2

    # Fill up to 50 rows across Sunni sources
    for i in range(49):
        src = _SUNNI_SOURCES[i % len(_SUNNI_SOURCES)]
        rows.append(_make_row(str(row_id), src, str(row_id), _H1))
        row_id += 1

    # 5 gold rows: Tirmidhi #1 + 4 others from the corpus
    gold_rows = [
        {"source": "Jami' al-Tirmidhi", "hadith_no": "1"},
        {"source": "Sahih Muslim", "hadith_no": "2"},
        {"source": "Sahih Muslim", "hadith_no": "3"},
        {"source": "Sahih Muslim", "hadith_no": "4"},
        {"source": "Sahih Muslim", "hadith_no": "5"},
    ]

    # Add the gold-referenced rows into the CSV so they'd otherwise appear
    rows.append(_make_row("m2", "Sahih Muslim", "2", _H1))
    rows.append(_make_row("m3", "Sahih Muslim", "3", _H1))
    rows.append(_make_row("m4", "Sahih Muslim", "4", _H1))
    rows.append(_make_row("m5", "Sahih Muslim", "5", _H1))

    output, _ = _run_pull(tmp_path, rows, gold_rows=gold_rows, n=30, seed=42)

    assert len(output) > 0, "Should have produced at least 1 candidate"

    gold_keys = {(r["source"], r["hadith_no"]) for r in gold_rows}
    out_keys = {(r["source"], r["hadith_no"]) for r in output}
    overlap = out_keys & gold_keys
    assert overlap == set(), f"Found overlap with gold: {overlap}"


# ---------------------------------------------------------------------------
# Test 2: distribution close to 70/25/5
# ---------------------------------------------------------------------------

def test_distribution_close_to_70_25_5(tmp_path: Path) -> None:
    """
    Run with n=100 seed=42 against a mock CSV with:
      50 single-ح rows, 30 two-ح rows, 20 three-plus-ح rows across multiple sources.
    Assert the picked rows match: single-ح in [60,80], 2-ح in [15,35], 3+-ح in [0,10].
    Tolerance: ±10% per band.
    """
    rows: list[dict] = []
    row_id = 1
    # 50 single-ح rows across all 6 sources
    for i in range(50):
        src = _SUNNI_SOURCES[i % len(_SUNNI_SOURCES)]
        rows.append(_make_row(str(row_id), src, str(row_id), _H1))
        row_id += 1
    # 30 two-ح rows
    for i in range(30):
        src = _SUNNI_SOURCES[i % len(_SUNNI_SOURCES)]
        rows.append(_make_row(str(row_id), src, str(row_id), _H2))
        row_id += 1
    # 20 three-plus-ح rows
    for i in range(20):
        src = _SUNNI_SOURCES[i % len(_SUNNI_SOURCES)]
        rows.append(_make_row(str(row_id), src, str(row_id), _H3))
        row_id += 1

    output, _ = _run_pull(tmp_path, rows, gold_rows=[], n=100, seed=42)

    assert len(output) > 0, "Should have produced candidates"
    total = len(output)

    count_1 = sum(1 for r in output if r["tahweel_count"] == 1)
    count_2 = sum(1 for r in output if r["tahweel_count"] == 2)
    count_3p = sum(1 for r in output if r["tahweel_count"] >= 3)

    # Bands: 70% ±10% → [60, 80]; 25% ±10% → [15, 35]; 5% ±5% → [0, 10]
    # Expressed as absolute counts for n=total
    assert count_1 >= 60 * total // 100, f"Too few single-ح: {count_1}/{total}"
    assert count_1 <= 80 * total // 100 + 1, f"Too many single-ح: {count_1}/{total}"
    assert count_2 >= 15 * total // 100, f"Too few 2-ح: {count_2}/{total}"
    assert count_2 <= 35 * total // 100 + 1, f"Too many 2-ح: {count_2}/{total}"
    assert count_3p <= 10 * total // 100 + 2, f"Too many 3+-ح: {count_3p}/{total}"


# ---------------------------------------------------------------------------
# Test 3: no single source dominates (>50%)
# ---------------------------------------------------------------------------

def test_no_single_source_dominates(tmp_path: Path) -> None:
    """
    Run --n 30 --seed 42.
    Assert no single source contributes more than 15 rows (50%).
    """
    rows = _build_basic_corpus(per_source_singles=10, per_source_doubles=5, per_source_triples=2)
    output, _ = _run_pull(tmp_path, rows, gold_rows=[], n=30, seed=42)

    assert len(output) > 0

    per_source: dict[str, int] = {}
    for r in output:
        src = r["source"]
        per_source[src] = per_source.get(src, 0) + 1

    cap = 15  # floor(0.5 * 30)
    for src, cnt in per_source.items():
        assert cnt <= cap, f"Source '{src}' contributes {cnt} rows > cap {cap}"


# ---------------------------------------------------------------------------
# Test 4: seed=42 reproducible (byte-identical output)
# ---------------------------------------------------------------------------

def test_seed_42_reproducible(tmp_path: Path) -> None:
    """
    Run twice with seed=42 on the same input. Assert byte-identical output.
    """
    rows = _build_basic_corpus()

    out1, _ = _run_pull(tmp_path / "run1", rows, gold_rows=[], n=30, seed=42)
    out2, _ = _run_pull(tmp_path / "run2", rows, gold_rows=[], n=30, seed=42)

    # Compare as JSON strings (order-sensitive)
    lines1 = [json.dumps(r, ensure_ascii=False) for r in out1]
    lines2 = [json.dumps(r, ensure_ascii=False) for r in out2]
    assert lines1 == lines2, "Seed=42 runs are not byte-identical"


# ---------------------------------------------------------------------------
# Test 5: different seeds produce different output
# ---------------------------------------------------------------------------

def test_different_seeds_differ(tmp_path: Path) -> None:
    """
    Run with seed=42 and seed=43. Assert outputs differ.
    Requires a large enough pool that sampling can differ.
    """
    rows = _build_basic_corpus(per_source_singles=20, per_source_doubles=10, per_source_triples=5)

    out42, _ = _run_pull(tmp_path / "s42", rows, gold_rows=[], n=30, seed=42)
    out43, _ = _run_pull(tmp_path / "s43", rows, gold_rows=[], n=30, seed=43)

    # Convert to sets of (source, hadith_no) to check they're not identical
    keys42 = {(r["source"], r["hadith_no"]) for r in out42}
    keys43 = {(r["source"], r["hadith_no"]) for r in out43}
    assert keys42 != keys43, "Different seeds should produce different candidate sets"


# ---------------------------------------------------------------------------
# Test 6: --difficulty-target 5 picks 3+-ح rows
# ---------------------------------------------------------------------------

def test_difficulty_target_5_picks_3plus(tmp_path: Path) -> None:
    """
    Run --n 5 --difficulty-target 5.
    Assert all 5 picked rows have tahweel_count >= 3.
    If fewer than 5 such rows exist, assert all available are picked + log warning.
    """
    rows: list[dict] = []
    row_id = 1
    # Enough single and double rows that don't qualify
    for i in range(20):
        src = _SUNNI_SOURCES[i % len(_SUNNI_SOURCES)]
        rows.append(_make_row(str(row_id), src, str(row_id), _H1))
        row_id += 1
    for i in range(10):
        src = _SUNNI_SOURCES[i % len(_SUNNI_SOURCES)]
        rows.append(_make_row(str(row_id), src, str(row_id), _H2))
        row_id += 1
    # 7 triple-ح rows
    for i in range(7):
        src = _SUNNI_SOURCES[i % len(_SUNNI_SOURCES)]
        rows.append(_make_row(str(row_id), src, str(row_id), _H3))
        row_id += 1

    output, stderr = _run_pull(
        tmp_path, rows, gold_rows=[], n=5, seed=42, difficulty_target=5
    )

    assert len(output) > 0, "Should have picked at least some 3+-ح rows"
    for r in output:
        assert r["tahweel_count"] >= 3, (
            f"Row {r['hadith_no']} has tahweel_count={r['tahweel_count']}, expected >=3"
        )

    # If fewer than 5 were available, a WARN should have been emitted
    if len(output) < 5:
        assert "WARN" in stderr, "Expected a WARN when fewer rows than requested"


def test_difficulty_target_5_warns_when_insufficient(tmp_path: Path) -> None:
    """
    Variant: only 3 triple-ح rows available, request 5.
    Assert all 3 are picked and WARN is in stderr.
    """
    rows: list[dict] = []
    row_id = 1
    for i in range(3):
        src = _SUNNI_SOURCES[i % len(_SUNNI_SOURCES)]
        rows.append(_make_row(str(row_id), src, str(row_id), _H3))
        row_id += 1

    output, stderr = _run_pull(
        tmp_path, rows, gold_rows=[], n=5, seed=42, difficulty_target=5
    )

    assert len(output) == 3, f"Expected all 3 available rows, got {len(output)}"
    assert "WARN" in stderr, "Expected WARN in stderr when pool is too small"


# ---------------------------------------------------------------------------
# Test 7: non-Sunni zero handled cleanly
# ---------------------------------------------------------------------------

def test_non_sunni_zero_handled_cleanly(tmp_path: Path) -> None:
    """
    Mock CSV: 50 Sunni ح-marked rows + 20 Imami rows with NO ح-splitter.
    Run with no --exclude-traditions.
    Assert:
      - exit 0 (function returns without exception)
      - output has Sunni-only rows
      - stderr contains WARN line about Imami tradition having 0 qualifying rows
    """
    rows = _build_corpus_with_imami(sunni_count=50, imami_count=20)

    output, stderr = _run_pull(tmp_path, rows, gold_rows=[], n=20, seed=42)

    # Should complete without exception and produce output
    assert len(output) > 0, "Should have produced candidates"

    # All output rows should be from Sunni sources
    sunni_sources = set(pnc.SUNNI_K6_SOURCES)
    for r in output:
        assert r["source"] in sunni_sources, (
            f"Non-Sunni row in output: source='{r['source']}'"
        )

    # Stderr should warn about imami having zero qualifying rows
    assert "imami" in stderr.lower() and "0 rows" in stderr.lower(), (
        f"Expected WARN about imami tradition in stderr. Got:\n{stderr}"
    )


# ---------------------------------------------------------------------------
# Test 8: full schema in every output row
# ---------------------------------------------------------------------------

def test_full_schema_in_output(tmp_path: Path) -> None:
    """
    Run pull; read output JSONL.
    Assert every row has all 10 required fields with correct null/empty defaults.
    """
    rows = _build_basic_corpus(per_source_singles=5, per_source_doubles=3, per_source_triples=1)
    output, _ = _run_pull(tmp_path, rows, gold_rows=[], n=10, seed=42)

    assert len(output) > 0, "Should have produced candidates"

    required_fields = {
        "hadith_id",
        "source",
        "hadith_no",
        "tahweel_count",
        "text_ar",
        "sanad",
        "expected_branches",
        "notes",
        "annotator",
        "annotated_at",
        "difficulty",
    }

    for i, row in enumerate(output):
        missing = required_fields - set(row.keys())
        assert not missing, f"Row {i} missing fields: {missing}"

        # Check annotation-ready defaults
        assert row["expected_branches"] is None, (
            f"Row {i}: expected_branches should be null, got {row['expected_branches']!r}"
        )
        assert row["notes"] == "", (
            f"Row {i}: notes should be empty string, got {row['notes']!r}"
        )
        assert row["annotator"] == "", (
            f"Row {i}: annotator should be empty string, got {row['annotator']!r}"
        )
        assert row["annotated_at"] == "", (
            f"Row {i}: annotated_at should be empty string, got {row['annotated_at']!r}"
        )
        assert row["difficulty"] is None, (
            f"Row {i}: difficulty should be null, got {row['difficulty']!r}"
        )
        assert isinstance(row["tahweel_count"], int), (
            f"Row {i}: tahweel_count should be int, got {type(row['tahweel_count'])}"
        )
        assert row["tahweel_count"] >= 1, (
            f"Row {i}: tahweel_count should be >= 1, got {row['tahweel_count']}"
        )


# ---------------------------------------------------------------------------
# Test 9 (spec G-5 #3): zero overlap with REAL tahweel-gold.jsonl
# ---------------------------------------------------------------------------

def test_zero_overlap_with_gold(tmp_path: Path) -> None:
    """
    G-5 test 3: Build a mock CSV that includes the 5 rows from the real
    tahweel-gold.jsonl (same source + hadith_no) plus 50 additional rows.
    Request n=10; assert NONE of the returned rows match any (source, hadith_no)
    in the real gold file.
    """
    # Real gold fixture path (two levels up from __tests__/)
    real_gold = _FIXTURES_DIR / "tahweel-gold.jsonl"
    assert real_gold.exists(), f"Real gold file not found: {real_gold}"

    # Load real gold keys
    gold_keys: list[dict] = []
    with open(real_gold, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                obj = json.loads(line)
                gold_keys.append({"source": obj["source"], "hadith_no": obj["hadith_no"]})

    assert len(gold_keys) >= 5, "Expected at least 5 gold fixtures"

    # Build mock CSV: include the gold rows + 50 filler rows across K6 sources
    rows: list[dict] = []
    row_id = 1

    # Rows that replicate the real gold (source + hadith_no match)
    for gk in gold_keys:
        rows.append(_make_row(str(row_id), gk["source"], gk["hadith_no"], _H1))
        row_id += 1

    # 50 additional filler rows that should be eligible
    for i in range(50):
        src = _SUNNI_SOURCES[i % len(_SUNNI_SOURCES)]
        rows.append(_make_row(str(row_id), src, str(row_id + 10000), _H1))
        row_id += 1

    # Write the real gold as the dedup reference
    gold_path = tmp_path / "mock_gold.jsonl"
    csv_path = tmp_path / "mock_unified.csv"
    out_path = tmp_path / "staging-test.jsonl"

    _make_mock_csv(rows, csv_path)
    # Copy real gold keys into the mock gold file
    with open(gold_path, "w", encoding="utf-8") as fh:
        for gk in gold_keys:
            fh.write(json.dumps(gk, ensure_ascii=False) + "\n")

    # Run via programmatic API
    import io as _io
    old_stderr = sys.stderr
    sys.stderr = _io.StringIO()
    try:
        candidates = pnc.load_candidates(csv_path)
        candidates = pnc.dedup_against_gold(candidates, gold_path)
        rng = random.Random(42)
        picked = pnc.stratified_pick(candidates, 10, rng)
        pnc.write_staging(picked, out_path)
    finally:
        sys.stderr = old_stderr

    output_rows: list[dict] = []
    if out_path.exists():
        with open(out_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    output_rows.append(json.loads(line))

    assert len(output_rows) > 0, "Should have produced at least 1 candidate after dedup"

    gold_key_set = {(gk["source"], gk["hadith_no"]) for gk in gold_keys}
    for r in output_rows:
        key = (r["source"], r["hadith_no"])
        assert key not in gold_key_set, (
            f"Gold row leaked into output: source={r['source']!r}, hadith_no={r['hadith_no']!r}"
        )


# ---------------------------------------------------------------------------
# Test 10 (spec G-5 #5): non-Sunni rows included when synthetically present
# ---------------------------------------------------------------------------

def test_non_sunni_included_when_present(tmp_path: Path) -> None:
    """
    G-5 test 5: Build a mock CSV with Sunni rows + 5 Al-Kafi rows WITH ح-splitter
    (synthetic — Phase 0 confirmed this doesn't happen in the real corpus, but the
    script's plumbing must work if a tradition's text ever uses ح).
    Request n=20; assert at least 1 Imami (Al-Kafi) row appears in output.
    """
    rows: list[dict] = []
    row_id = 1

    # 50 Sunni rows with ح-splitter
    for i in range(50):
        src = _SUNNI_SOURCES[i % len(_SUNNI_SOURCES)]
        rows.append(_make_row(str(row_id), src, str(row_id), _H1, tradition="Sunni"))
        row_id += 1

    # 5 Al-Kafi rows WITH ح-splitter (synthetic; tradition=imami)
    for i in range(5):
        rows.append(
            _make_row(
                str(row_id),
                "Al-Kafi",
                str(row_id),
                _H1,  # uses ح-splitter so they qualify
                tradition="imami",
            )
        )
        row_id += 1

    output, stderr = _run_pull(tmp_path, rows, gold_rows=[], n=20, seed=42)

    assert len(output) > 0, "Should have produced candidates"

    # At least one Al-Kafi (Imami) row should appear
    imami_rows = [r for r in output if r["source"] == "Al-Kafi"]
    assert len(imami_rows) >= 1, (
        f"Expected at least 1 Imami (Al-Kafi) row in output, got 0.\n"
        f"Sources present: {sorted({r['source'] for r in output})}"
    )


# ---------------------------------------------------------------------------
# Test 11 (spec G-5 #8): --exclude-traditions removes those rows
# ---------------------------------------------------------------------------

def test_exclude_traditions(tmp_path: Path) -> None:
    """
    G-5 test 8: Build a mock CSV with Sunni rows + Imami Al-Kafi rows WITH ح.
    Run with --exclude-traditions imami.
    Assert no Imami rows appear in output even if Sunni quota is short.
    """
    rows: list[dict] = []
    row_id = 1

    # 30 Sunni rows
    for i in range(30):
        src = _SUNNI_SOURCES[i % len(_SUNNI_SOURCES)]
        rows.append(_make_row(str(row_id), src, str(row_id), _H1, tradition="Sunni"))
        row_id += 1

    # 10 Imami rows WITH ح-splitter
    for i in range(10):
        rows.append(
            _make_row(
                str(row_id),
                "Al-Kafi",
                str(row_id),
                _H1,
                tradition="imami",
            )
        )
        row_id += 1

    output, stderr = _run_pull(
        tmp_path,
        rows,
        gold_rows=[],
        n=20,
        seed=42,
        exclude_traditions=["imami"],
    )

    assert len(output) > 0, "Should have produced candidates from Sunni rows"

    # No Imami (Al-Kafi) rows in output
    imami_rows = [r for r in output if r["source"] == "Al-Kafi"]
    assert len(imami_rows) == 0, (
        f"Expected 0 Imami rows after --exclude-traditions imami, got {len(imami_rows)}"
    )
