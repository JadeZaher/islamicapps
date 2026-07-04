"""
G-2 acceptance tests for score_calibration.py.

Tests use planted errors against the tahweel-gold.jsonl fixtures to verify
the scorer behaves correctly at all boundary conditions specified in the spec.
"""

import json
import pathlib
import sys

import pytest

# ---------------------------------------------------------------------------
# Path setup: add fixtures dir (where score_calibration.py lives) to sys.path,
# and add datasets/ so classify_attribution._norm can be imported.
# Layout:
#   datasets/hadith-data/__tests__/fixtures/__tests__/   ← this file
#   datasets/hadith-data/__tests__/fixtures/             ← score_calibration.py
#   datasets/                                            ← classify_attribution.py
# ---------------------------------------------------------------------------
_FIXTURES_DIR = pathlib.Path(__file__).resolve().parent.parent
_REPO_ROOT = _FIXTURES_DIR.parents[3]  # datasets/hadith-data/__tests__/fixtures → 4 levels up
_DATASETS_DIR = _REPO_ROOT / "datasets"

sys.path.insert(0, str(_FIXTURES_DIR))
sys.path.insert(0, str(_DATASETS_DIR))

from score_calibration import score, ScoreReport  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_GOLD_PATH = _REPO_ROOT / "docs" / "annotation" / ".calibration-gold.jsonl"
_GOLD_JSONL = _FIXTURES_DIR / "tahweel-gold.jsonl"


def _load_gold() -> dict:
    """Return gold rows as {hadith_id: dict}."""
    rows = {}
    with open(_GOLD_JSONL, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                obj = json.loads(line)
                rows[obj["hadith_id"]] = obj
    return rows


def _make_submission(modifications: dict, tmp_path: pathlib.Path) -> pathlib.Path:
    """
    Copy the gold rows into a tmp submission file, applying per-hadith-id
    modifications.

    modifications: {hadith_id: {field: new_value, ...}}

    Returns path to the written .jsonl file.
    """
    gold_rows = _load_gold()
    out = tmp_path / "submission.jsonl"
    with open(out, "w", encoding="utf-8") as fh:
        for hid, row in gold_rows.items():
            row_copy = dict(row)
            # Ensure all required submission fields are present
            row_copy.setdefault("annotator", "test")
            row_copy.setdefault("annotated_at", "2026-06-14T00:00:00Z")
            row_copy.setdefault("difficulty", 3)
            row_copy.setdefault("notes", "")
            if hid in modifications:
                row_copy.update(modifications[hid])
            fh.write(json.dumps(row_copy, ensure_ascii=False) + "\n")
    return out


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_perfect_submission_scores_1_0(tmp_path):
    """Submitting the gold itself should yield aggregate == 1.0."""
    # Use .calibration-gold.jsonl (the dotfile) as the submission.
    # It is byte-identical to tahweel-gold.jsonl, so every branch matches.
    report: ScoreReport = score(_GOLD_PATH, gold_path=_GOLD_PATH)
    assert report.aggregate == pytest.approx(1.0, abs=1e-9), (
        f"Perfect submission should score 1.0, got {report.aggregate}"
    )
    assert report.passed is True


def test_swapped_branches_drops_below_threshold(tmp_path):
    """Swapping Branch A and Branch B on Tirmidhi #1 (hadith_id='30001')
    while keeping all other 4 rows perfect should drop aggregate below 0.85
    AND the per-row report should flag '30001' as the lowest-scoring row.
    """
    gold_rows = _load_gold()
    tirmidhi = gold_rows["30001"]
    original_branches = tirmidhi["expected_branches"]
    assert len(original_branches) >= 2, "Test assumption: 30001 has ≥2 branches"

    # Swap Branch A and B
    swapped = [original_branches[1], original_branches[0]] + original_branches[2:]

    sub_path = _make_submission(
        {"30001": {"expected_branches": swapped}},
        tmp_path,
    )
    report = score(sub_path, gold_path=_GOLD_PATH)

    assert report.aggregate < 0.85, (
        f"Swapped branches should push aggregate below 0.85, got {report.aggregate}"
    )

    lowest_row = min(report.rows, key=lambda r: r.row_score)
    assert lowest_row.hadith_id == "30001", (
        f"Tirmidhi #1 (30001) should be the lowest-scoring row, "
        f"got {lowest_row.hadith_id} (score {lowest_row.row_score})"
    )


def test_missing_branch_penalized(tmp_path):
    """Dropping Branch B entirely on Tirmidhi #1 (gold has 2 branches)
    while keeping Branch A perfect should yield row_score = 0.5
    (one perfect branch averaged with one missing → 0.0).
    """
    gold_rows = _load_gold()
    tirmidhi = gold_rows["30001"]
    original_branches = tirmidhi["expected_branches"]
    assert len(original_branches) == 2, "Test assumption: 30001 has exactly 2 branches"

    # Keep only Branch A
    one_branch = [original_branches[0]]

    sub_path = _make_submission(
        {"30001": {"expected_branches": one_branch}},
        tmp_path,
    )
    report = score(sub_path, gold_path=_GOLD_PATH)

    tirmidhi_row = next(r for r in report.rows if r.hadith_id == "30001")
    assert tirmidhi_row.row_score == pytest.approx(0.5, abs=1e-9), (
        f"One perfect branch + one missing branch should average to 0.5, "
        f"got {tirmidhi_row.row_score}"
    )


def test_wrong_surface_form_penalized(tmp_path):
    """Replacing 'سفيان' with Latin 'Sufyan' in muslim-31 Branch A
    should lower that row's per-branch score (Latin form won't match after _norm).
    """
    gold_rows = _load_gold()
    muslim31 = gold_rows["muslim-31"]
    original_branches = muslim31["expected_branches"]

    # Replace سفيان with Latin transliteration in Branch A
    branch_a_modified = [
        "Sufyan" if "سفيان" in name else name
        for name in original_branches[0]
    ]
    modified_branches = [branch_a_modified] + list(original_branches[1:])

    sub_path = _make_submission(
        {"muslim-31": {"expected_branches": modified_branches}},
        tmp_path,
    )
    report = score(sub_path, gold_path=_GOLD_PATH)

    muslim31_row = next(r for r in report.rows if r.hadith_id == "muslim-31")

    # Branch A score should be below 1.0 because سفيان was replaced with Sufyan
    branch_a_score = muslim31_row.branch_scores[0].score
    assert branch_a_score < 1.0, (
        f"Latin transliteration 'Sufyan' should not match Arabic 'سفيان' after _norm; "
        f"Branch A score was {branch_a_score} (expected < 1.0)"
    )


def test_null_submission_scores_zero(tmp_path):
    """A row with expected_branches=null should contribute 0.0 to the aggregate."""
    sub_path = _make_submission(
        {"30001": {"expected_branches": None}},
        tmp_path,
    )
    report = score(sub_path, gold_path=_GOLD_PATH)

    tirmidhi_row = next(r for r in report.rows if r.hadith_id == "30001")
    assert tirmidhi_row.row_score == pytest.approx(0.0, abs=1e-9), (
        f"null expected_branches should score 0.0, got {tirmidhi_row.row_score}"
    )
    assert tirmidhi_row.skipped is True, (
        "Row with null expected_branches should be marked skipped"
    )
    # The other 4 rows are perfect, so aggregate = (0 + 1+1+1+1) / 5 = 0.8
    assert report.aggregate == pytest.approx(0.8, abs=1e-9), (
        f"Aggregate with one null row should be 0.8, got {report.aggregate}"
    )
