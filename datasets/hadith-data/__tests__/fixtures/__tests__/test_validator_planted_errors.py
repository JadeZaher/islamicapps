"""
G-3 acceptance tests for validate_annotation.py.

These tests verify that the validator catches the canonical annotation bugs
described in spec FR-3.2 / G-3.

NOTE on test_existing_gold_all_pass:
    The existing 5 gold rows (tahweel-gold.jsonl) were hand-annotated before
    the validator schema was finalised. They lack the metadata fields
    `difficulty`, `annotator`, and `annotated_at` which are required by
    V-6, V-7, and V-8. This means V-6/V-7/V-8 FAIL on those rows — this is
    a REAL FINDING, not a test failure. The annotation-content checks
    (V-1 through V-5) all pass.

    Resolution: the gold rows need `difficulty`, `annotator`, and
    `annotated_at` fields added. Until then, the test asserts that only
    the metadata checks fail (not the content checks), confirming the
    validator correctly identifies the schema gap.
"""

from __future__ import annotations

import copy
import json
import pathlib
import re
import sys
import tempfile

import pytest

# ---------------------------------------------------------------------------
# Path setup — make validate_annotation importable
# ---------------------------------------------------------------------------

_FIXTURES_DIR = pathlib.Path(__file__).resolve().parents[1]
_DATASETS_DIR = _FIXTURES_DIR.parents[2]        # .../islamicapps/datasets/
_ALGO_DIR = _FIXTURES_DIR.parents[1] / "algo_candidates"

sys.path.insert(0, str(_FIXTURES_DIR))
sys.path.insert(0, str(_DATASETS_DIR))
sys.path.insert(0, str(_ALGO_DIR))

from validate_annotation import (  # noqa: E402
    ALL_CHECKS,
    check_v1,
    check_v2,
    check_v3,
    check_v4,
    check_v5,
    check_v6,
    check_v7,
    check_v8,
    validate_file,
    validate_row,
    promote,
)

_GOLD_PATH = _FIXTURES_DIR / "tahweel-gold.jsonl"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GOLD_ROWS: dict[str, dict] = {}


def _load_gold() -> dict[str, dict]:
    global _GOLD_ROWS
    if not _GOLD_ROWS:
        with open(_GOLD_PATH, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    row = json.loads(line)
                    _GOLD_ROWS[row["hadith_id"]] = row
    return _GOLD_ROWS


def _make_row(modifications: dict, base_hadith_id: str = "30001") -> dict:
    """Load a gold row by hadith_id, apply modifications, return a copy."""
    gold = _load_gold()
    row = copy.deepcopy(gold[base_hadith_id])
    row.update(modifications)
    return row


def _fully_annotated(base_hadith_id: str = "30001", **extra) -> dict:
    """Return a gold row with required metadata fields filled in."""
    return _make_row(
        {
            "difficulty": 2,
            "annotator": "JZ",
            "annotated_at": "2026-06-12T10:00:00+00:00",
            **extra,
        },
        base_hadith_id=base_hadith_id,
    )


# ---------------------------------------------------------------------------
# Test 1: existing gold all 9 content checks pass after Phase 7 backfill
# ---------------------------------------------------------------------------

def test_existing_gold_content_checks_pass():
    """All content checks (V-1, V-2, V-3, V-5, V-6, V-7, V-8, V-9) PASS on
    the existing 5 gold rows after Phase 7 backfill of annotator /
    annotated_at / difficulty / kit_version metadata. V-4 may WARN
    legitimately on convergence ordering (no FAIL at default level).
    """
    results = validate_file(_GOLD_PATH)
    assert len(results) == 5

    content_checks = ("V-1", "V-2", "V-3", "V-5", "V-6", "V-7", "V-8", "V-9")
    for r in results:
        for key in content_checks:
            status, msg = r["checks"][key]
            assert status == "PASS", (
                f"hadith_id={r['hadith_id']}: {key} expected PASS, "
                f"got {status}: {msg}"
            )
        v4_status, v4_msg = r["checks"]["V-4"]
        assert v4_status in ("PASS", "WARN"), (
            f"hadith_id={r['hadith_id']}: V-4 expected PASS/WARN, "
            f"got {v4_status}: {v4_msg}"
        )


# ---------------------------------------------------------------------------
# Test 2: V-2 wrong surface form flagged
# ---------------------------------------------------------------------------

def test_v2_wrong_surface_form_flagged():
    """
    Changing a narrator surface to a name not in text_ar must cause V-2 FAIL.
    """
    row = _fully_annotated()
    # Replace first narrator of branch 0 with a name not in text_ar
    row["expected_branches"][0][0] = "some-name-not-in-text"
    status, msg = check_v2(row)
    assert status == "FAIL"
    assert "some-name-not-in-text" in msg or "branch 0" in msg


# ---------------------------------------------------------------------------
# Test 3: V-3 branch count mismatch flagged
# ---------------------------------------------------------------------------

def test_v3_branch_count_mismatch_flagged():
    """
    Tirmidhi #1 has tahweel_count=1 → expects 2 branches.
    Dropping one branch (leaving 1) must cause V-3 FAIL.
    """
    row = _fully_annotated()
    assert row["tahweel_count"] == 1
    # Drop one branch → 1 branch, but expected 2
    row["expected_branches"] = [row["expected_branches"][0]]
    status, msg = check_v3(row)
    assert status == "FAIL"
    assert "1" in msg and "2" in msg


# ---------------------------------------------------------------------------
# Test 4: V-3 difficulty-5 bypass works
# ---------------------------------------------------------------------------

def test_v3_difficulty_5_bypass_works():
    """
    With difficulty=5 and non-empty notes, V-3 allows branch count mismatch.
    """
    row = _fully_annotated(
        difficulty=5,
        notes="genuinely ambiguous — ح may be حديث not تحويل",
    )
    # Drop one branch → normally would FAIL V-3
    row["expected_branches"] = [row["expected_branches"][0]]
    status, msg = check_v3(row)
    assert status == "PASS"
    assert "bypass" in msg.lower()


# ---------------------------------------------------------------------------
# Test 5: V-4 position swap warned at default level
# ---------------------------------------------------------------------------

def _make_swap_row() -> dict:
    """
    Build a synthetic row where two shared narrators (شعبة, منصور) appear
    in swapped order across branches — V-4 should warn.

    Based on muslim-2 structure but with order deliberately swapped in branch 1.
    """
    return {
        "hadith_id": "synthetic-v4-swap",
        "source": "Sahih Muslim",
        "hadith_no": "999",
        "tahweel_count": 1,
        "text_ar": (
            "حدثنا زيد حدثنا شعبة عن منصور ح وحدثنا عمرو حدثنا منصور عن شعبة عن انس"
        ),
        "expected_branches": [
            ["زيد", "شعبة", "منصور"],     # branch 0: شعبة before منصور
            ["عمرو", "منصور", "شعبة"],     # branch 1: منصور before شعبة — SWAPPED
        ],
        "notes": "synthetic test row",
        "difficulty": 2,
        "annotator": "test",
        "annotated_at": "2026-06-12T10:00:00+00:00",
    }


def test_v4_position_swap_warned():
    """
    Two convergence narrators in swapped order across branches must produce V-4 WARN
    at default level (not FAIL).
    """
    row = _make_swap_row()
    status, msg = check_v4(row, strict=False)
    assert status == "WARN", f"Expected WARN, got {status}: {msg}"
    assert "swap" in msg.lower() or "swapped" in msg.lower()


# ---------------------------------------------------------------------------
# Test 6: V-4 position swap fails under strict mode
# ---------------------------------------------------------------------------

def test_v4_position_swap_fails_under_strict():
    """
    Same row as test 5, but with strict=True → V-4 must FAIL.
    """
    row = _make_swap_row()
    status, msg = check_v4(row, strict=True)
    assert status == "FAIL", f"Expected FAIL under strict, got {status}: {msg}"


# ---------------------------------------------------------------------------
# Test 7: V-5 matn text in chain flagged
# ---------------------------------------------------------------------------

def test_v5_matn_text_in_chain_flagged():
    """
    Appending a word that appears AFTER the matn anchor in text_ar to
    expected_branches[0] must cause V-5 FAIL.

    Tirmidhi #1 text_ar ends with: "عن النبي صلى الله عليه وسلم قال ..."
    The matn anchor is "عن النبي". We add "النبي" as a surface in branch 0
    — it appears in text_ar at/after the matn anchor position.
    """
    row = _fully_annotated()
    text_ar = row["text_ar"]
    # Verify "النبي" appears after the matn anchor in this text
    # The anchor "عن النبي" should match; النبي comes after.
    # Add a word that's definitely in the matn region.
    # The matn is "لا تقبل صلاة بغير طهور" — "صلاة" is a safe matn word.
    # But to pick something that will appear after the anchor, we use "طهور"
    # which is after "عن النبي صلى الله عليه وسلم قال" in the text.
    # Append it to branch 0.
    row["expected_branches"][0].append("طهور")
    status, msg = check_v5(row)
    assert status == "FAIL", f"Expected FAIL, got {status}: {msg}"
    assert "طهور" in msg or "matn" in msg.lower() or "anchor" in msg.lower()


# ---------------------------------------------------------------------------
# Test 8: V-7 empty annotator flagged
# ---------------------------------------------------------------------------

def test_v7_empty_annotator_flagged():
    """
    A row with annotator="" must cause V-7 FAIL.
    """
    row = _fully_annotated(annotator="")
    status, msg = check_v7(row)
    assert status == "FAIL"
    assert "empty" in msg.lower() or "annotator" in msg.lower()


# ---------------------------------------------------------------------------
# Test 9: V-8 bad timestamp flagged
# ---------------------------------------------------------------------------

def test_v8_bad_timestamp_flagged():
    """
    A row with annotated_at="not-a-date" must cause V-8 FAIL.
    """
    row = _fully_annotated(annotated_at="not-a-date")
    status, msg = check_v8(row)
    assert status == "FAIL"
    assert "ISO-8601" in msg or "not a valid" in msg.lower() or "invalid" in msg.lower()


# ---------------------------------------------------------------------------
# Test 10: promote atomic refuses partial failure
# ---------------------------------------------------------------------------

def test_promote_atomic_refuses_partial_failure(tmp_path: pathlib.Path):
    """
    If any row in the staging file fails, promote must refuse ALL rows.
    The gold target must remain byte-identical; no backup must be created.
    """
    # Build a gold target with 5 existing valid rows (fully annotated copies)
    gold_target = tmp_path / "tahweel-gold.jsonl"
    gold_rows = []
    with open(_GOLD_PATH, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            row.update({
                "difficulty": 2,
                "annotator": "JZ",
                "annotated_at": "2026-06-12T10:00:00+00:00",
            })
            gold_rows.append(row)
    with open(gold_target, "w", encoding="utf-8") as fh:
        for row in gold_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    gold_original_bytes = gold_target.read_bytes()

    # Build staging file: row 1 valid, row 2 V-2 failure, row 3 valid
    def _valid_staging_row(hadith_id: str) -> dict:
        return {
            "hadith_id": hadith_id,
            "source": "Test",
            "hadith_no": hadith_id,
            "tahweel_count": 1,
            "text_ar": "حدثنا زيد عن عمرو ح وحدثنا بكر عن خالد عن النبي قال",
            "expected_branches": [["زيد", "عمرو"], ["بكر", "خالد"]],
            "notes": "test row",
            "difficulty": 2,
            "annotator": "JZ",
            "annotated_at": "2026-06-12T10:00:00+00:00",
        }

    staging_rows = [
        _valid_staging_row("stg-1"),
        {**_valid_staging_row("stg-2"), "expected_branches": [["NOT-IN-TEXT"], ["بكر", "خالد"]]},
        _valid_staging_row("stg-3"),
    ]
    staging_file = tmp_path / "staging.jsonl"
    with open(staging_file, "w", encoding="utf-8") as fh:
        for row in staging_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Run promote — expect failure
    exit_code = promote(staging_file, gold_target, strict=False)
    assert exit_code == 1, "promote should return exit code 1 on partial failure"

    # Gold target must be unchanged
    assert gold_target.read_bytes() == gold_original_bytes, (
        "Gold file must remain byte-identical after failed promotion"
    )

    # No backup file should exist
    backups = list(tmp_path.glob("tahweel-gold.jsonl.bak-*"))
    assert len(backups) == 0, (
        f"No backup should be created on failed promotion, found: {backups}"
    )


# ---------------------------------------------------------------------------
# Test 11: promote success creates backup and appends
# ---------------------------------------------------------------------------

def test_promote_success_creates_backup_and_appends(tmp_path: pathlib.Path):
    """
    A staging file with 1 valid row promoted to an existing gold file must:
    - Grow the target file by exactly 1 row.
    - Create a backup matching pattern tahweel-gold.jsonl.bak-YYYYMMDD-HHMMSS.
    - The backup must be byte-identical to the pre-promotion target.
    """
    # Build a gold target with the 5 existing rows (fully annotated)
    gold_target = tmp_path / "tahweel-gold.jsonl"
    with open(_GOLD_PATH, encoding="utf-8") as fh:
        original_lines = [l.strip() for l in fh if l.strip()]
    with open(gold_target, "w", encoding="utf-8") as fh:
        for line in original_lines:
            row = json.loads(line)
            row.update({
                "difficulty": 2,
                "annotator": "JZ",
                "annotated_at": "2026-06-12T10:00:00+00:00",
            })
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    pre_promotion_bytes = gold_target.read_bytes()
    pre_row_count = len(original_lines)  # 5 rows

    # Build 1-row staging file (valid)
    staging_row = {
        "hadith_id": "stg-good",
        "source": "Test",
        "hadith_no": "9999",
        "tahweel_count": 1,
        "text_ar": "حدثنا زيد عن عمرو ح وحدثنا بكر عن خالد عن النبي قال",
        "expected_branches": [["زيد", "عمرو"], ["بكر", "خالد"]],
        "notes": "valid staging row",
        "difficulty": 3,
        "annotator": "JZ",
        "annotated_at": "2026-06-12T12:00:00+00:00",
    }
    staging_file = tmp_path / "staging.jsonl"
    with open(staging_file, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(staging_row, ensure_ascii=False) + "\n")

    # Run promote — expect success
    exit_code = promote(staging_file, gold_target, strict=False)
    assert exit_code == 0, "promote should return exit code 0 on success"

    # Target must have grown by 1 row
    with open(gold_target, encoding="utf-8") as fh:
        new_rows = [l.strip() for l in fh if l.strip()]
    assert len(new_rows) == pre_row_count + 1, (
        f"Expected {pre_row_count + 1} rows after promotion, got {len(new_rows)}"
    )

    # The last row should be the promoted row
    last_row = json.loads(new_rows[-1])
    assert last_row["hadith_id"] == "stg-good"

    # A backup must exist matching tahweel-gold.jsonl.bak-YYYYMMDD-HHMMSS
    backups = list(tmp_path.glob("tahweel-gold.jsonl.bak-*"))
    assert len(backups) == 1, f"Expected exactly 1 backup, found {len(backups)}: {backups}"
    backup_name = backups[0].name
    pattern = re.compile(r"^tahweel-gold\.jsonl\.bak-\d{8}-\d{6}$")
    assert pattern.match(backup_name), (
        f"Backup name '{backup_name}' does not match expected pattern"
    )

    # Backup must be byte-identical to the pre-promotion target
    assert backups[0].read_bytes() == pre_promotion_bytes, (
        "Backup must be byte-identical to the pre-promotion gold file"
    )


# ---------------------------------------------------------------------------
# Additional sanity: V-8 accepts trailing Z (UTC)
# ---------------------------------------------------------------------------

def test_v8_accepts_trailing_z():
    """annotated_at with trailing Z (UTC) should PASS after Z→+00:00 substitution."""
    row = _fully_annotated(annotated_at="2026-06-12T10:00:00Z")
    status, msg = check_v8(row)
    assert status == "PASS", f"Expected PASS for Z-suffixed timestamp, got {status}: {msg}"


# ---------------------------------------------------------------------------
# Additional sanity: V-1 fails on non-list-of-lists
# ---------------------------------------------------------------------------

def test_v1_fails_on_wrong_type():
    """V-1 must FAIL when expected_branches is a list of strings (not list-of-lists)."""
    row = _fully_annotated()
    row["expected_branches"] = ["زيد", "عمرو"]  # flat list, not list-of-lists
    status, msg = check_v1(row)
    assert status == "FAIL"
