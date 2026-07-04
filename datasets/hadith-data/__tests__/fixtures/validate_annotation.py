"""
Validate annotated taḥwīl gold JSONL files.

Usage:
  python validate_annotation.py [--input <path>] [--strict] [--out <path>]
  python validate_annotation.py --promote --from <staging.jsonl> --to <gold.jsonl> [--strict]

--input defaults to tahweel-gold.jsonl (sibling file).
--strict turns V-4 warnings into hard fails.
Exit 0 if all rows pass at the requested level; 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import pathlib
from datetime import datetime
from typing import Literal

# ---------------------------------------------------------------------------
# Import shared helpers
# ---------------------------------------------------------------------------

_FIXTURES_DIR = pathlib.Path(__file__).resolve().parent
# _FIXTURES_DIR = .../islamicapps/datasets/hadith-data/__tests__/fixtures
# parents[0] = __tests__
# parents[1] = hadith-data
# parents[2] = datasets      ← classify_attribution.py lives here
# parents[3] = islamicapps
_DATASETS_DIR = _FIXTURES_DIR.parents[2]          # .../islamicapps/datasets/
_ALGO_DIR = _FIXTURES_DIR.parents[1] / "algo_candidates"   # datasets/hadith-data/algo_candidates

sys.path.insert(0, str(_DATASETS_DIR))
sys.path.insert(0, str(_ALGO_DIR))

from classify_attribution import _norm          # noqa: E402
from _common import MATN_ANCHORS                # noqa: E402

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

Status = Literal["PASS", "WARN", "FAIL"]


# ---------------------------------------------------------------------------
# V-1 through V-8 check functions
# ---------------------------------------------------------------------------

def check_v1(row: dict) -> tuple[Status, str]:
    """expected_branches is non-null and a list[list[str]]."""
    val = row.get("expected_branches", None)
    if val is None:
        return "FAIL", "expected_branches is null or missing"
    if not isinstance(val, list):
        return "FAIL", f"expected_branches must be a list, got {type(val).__name__}"
    for i, branch in enumerate(val):
        if not isinstance(branch, list):
            return "FAIL", f"expected_branches[{i}] must be a list, got {type(branch).__name__}"
        for j, item in enumerate(branch):
            if not isinstance(item, str):
                return "FAIL", (
                    f"expected_branches[{i}][{j}] must be a string, "
                    f"got {type(item).__name__}"
                )
    return "PASS", "expected_branches is a valid list[list[str]]"


_PUNCT_RE = re.compile(r"[،,.:؛!؟\"'\(\)\[\]‏‎،؛؟\-]+")


def _norm_v2(s: str) -> str:
    """Like _norm but also strips Arabic/Latin punctuation for substring matching."""
    s = _norm(s)
    s = _PUNCT_RE.sub(" ", s)
    # Collapse multiple spaces
    s = re.sub(r"\s+", " ", s).strip()
    return s


def check_v2(row: dict) -> tuple[Status, str]:
    """Every narrator surface in expected_branches appears verbatim in text_ar after _norm.

    Punctuation (Arabic comma etc.) is stripped before the substring check because
    the text uses commas of apposition (e.g. "أبو خيثمة، زهير بن حرب" is one person
    recorded as a single surface "أبو خيثمة زهير بن حرب").
    """
    branches = row.get("expected_branches")
    text_ar = row.get("text_ar", "")
    if not isinstance(branches, list):
        return "PASS", "skipped (V-1 already failed)"
    norm_text = _norm_v2(text_ar)
    for i, branch in enumerate(branches):
        if not isinstance(branch, list):
            continue
        for surface in branch:
            if not isinstance(surface, str):
                continue
            norm_surface = _norm_v2(surface)
            if norm_surface not in norm_text:
                return "FAIL", (
                    f"Surface \"{surface}\" (branch {i}) not found in text_ar after normalisation"
                )
    return "PASS", "all narrator surfaces found in text_ar"


def check_v3(row: dict) -> tuple[Status, str]:
    """len(expected_branches) == tahweel_count + 1, with difficulty-5 bypass."""
    branches = row.get("expected_branches")
    tahweel_count = row.get("tahweel_count")
    difficulty = row.get("difficulty")
    notes = row.get("notes", "")

    if not isinstance(branches, list):
        return "PASS", "skipped (V-1 already failed)"

    expected_len = (tahweel_count + 1) if isinstance(tahweel_count, int) else None

    if difficulty == 5 and isinstance(notes, str) and notes.strip():
        return "PASS", "bypass (difficulty 5 + notes)"

    if expected_len is None:
        return "FAIL", "tahweel_count is missing or not an integer"

    actual_len = len(branches)
    if actual_len != expected_len:
        return "FAIL", (
            f"expected_branches has {actual_len} branch(es), "
            f"expected {expected_len} (tahweel_count={tahweel_count} + 1)"
        )
    return "PASS", f"branch count {actual_len} == tahweel_count({tahweel_count}) + 1"


def check_v4(row: dict, strict: bool = False) -> tuple[Status, str]:
    """Convergence consistency: shared narrators preserve order across branches."""
    branches = row.get("expected_branches")
    if not isinstance(branches, list) or len(branches) < 2:
        return "PASS", "fewer than 2 branches, nothing to check"

    b0 = branches[0]
    b1 = branches[1]
    if not isinstance(b0, list) or not isinstance(b1, list):
        return "PASS", "skipped (non-list branch)"

    # Build normalised surface → first position in each branch
    def positions(branch: list) -> dict[str, int]:
        result: dict[str, int] = {}
        for pos, surface in enumerate(branch):
            if isinstance(surface, str):
                key = _norm(surface)
                if key not in result:
                    result[key] = pos
        return result

    pos0 = positions(b0)
    pos1 = positions(b1)

    shared = [k for k in pos0 if k in pos1]
    if len(shared) < 2:
        return "PASS", "fewer than 2 shared narrators, no order to check"

    # Check every pair of shared narrators for order consistency
    swaps: list[str] = []
    for ia, x in enumerate(shared):
        for y in shared[ia + 1:]:
            # In branch 0: x comes before y (pos0[x] < pos0[y])
            # In branch 1: x must also come before y
            order_b0 = pos0[x] < pos0[y]
            order_b1 = pos1[x] < pos1[y]
            if order_b0 != order_b1:
                # Find original surfaces for reporting
                x_surf = b0[pos0[x]] if pos0[x] < len(b0) else x
                y_surf = b0[pos0[y]] if pos0[y] < len(b0) else y
                swaps.append(f"\"{x_surf}\" and \"{y_surf}\" appear in swapped order across branches")

    if swaps:
        msg = "; ".join(swaps)
        if strict:
            return "FAIL", f"convergence order swap detected (strict mode): {msg}"
        return "WARN", f"possible convergence order swap: {msg}"
    return "PASS", "shared narrator ordering is consistent across branches"


def check_v5(row: dict) -> tuple[Status, str]:
    """No matn-internal text in expected_branches."""
    branches = row.get("expected_branches")
    text_ar = row.get("text_ar", "")
    if not isinstance(branches, list):
        return "PASS", "skipped (V-1 already failed)"

    norm_text = _norm(text_ar)
    m = MATN_ANCHORS.search(norm_text)
    if m is None:
        return "PASS", "no matn anchor found, nothing to check"

    anchor_pos = m.start()

    for i, branch in enumerate(branches):
        if not isinstance(branch, list):
            continue
        for surface in branch:
            if not isinstance(surface, str):
                continue
            norm_surface = _norm(surface)
            # Only check surfaces that appear in text at all (V-2 handles the rest)
            idx = norm_text.find(norm_surface)
            if idx == -1:
                continue  # V-2's problem
            if idx >= anchor_pos:
                return "FAIL", (
                    f"Surface \"{surface}\" (branch {i}) appears at/after the matn anchor "
                    f"position {anchor_pos} (anchor: \"{m.group()}\")"
                )
    return "PASS", "no expected_branches surface appears in matn region"


def check_v6(row: dict) -> tuple[Status, str]:
    """difficulty is an integer 1-5."""
    val = row.get("difficulty")
    if val is None:
        return "FAIL", "difficulty is null or missing"
    if not isinstance(val, int) or isinstance(val, bool):
        return "FAIL", f"difficulty must be an integer, got {type(val).__name__}"
    if val < 1 or val > 5:
        return "FAIL", f"difficulty must be 1-5, got {val}"
    return "PASS", f"difficulty={val} is valid"


def check_v7(row: dict) -> tuple[Status, str]:
    """annotator is a non-empty string."""
    val = row.get("annotator")
    if val is None:
        return "FAIL", "annotator field is missing"
    if not isinstance(val, str):
        return "FAIL", f"annotator must be a string, got {type(val).__name__}"
    if not val.strip():
        return "FAIL", "annotator is empty"
    return "PASS", f"annotator=\"{val}\""


def check_v8(row: dict) -> tuple[Status, str]:
    """annotated_at is a valid ISO-8601 timestamp."""
    val = row.get("annotated_at")
    if val is None:
        return "FAIL", "annotated_at field is missing"
    if not isinstance(val, str):
        return "FAIL", f"annotated_at must be a string, got {type(val).__name__}"
    # Tolerate trailing Z (Python <3.11 doesn't natively accept it)
    ts = val.replace("Z", "+00:00")
    try:
        datetime.fromisoformat(ts)
    except ValueError as e:
        return "FAIL", f"annotated_at is not a valid ISO-8601 timestamp: {e}"
    return "PASS", f"annotated_at=\"{val}\" is valid ISO-8601"


def check_v9(row: dict) -> tuple[Status, str]:
    """kit_version is a non-empty semver-shaped string (spec Q4).

    The annotator does NOT fill this field — the pull script and the promote
    flow stamp it. A missing or mismatched kit_version means the row predates
    a contract change; WARN rather than FAIL so legacy rows stay usable while
    surfacing the gap.
    """
    val = row.get("kit_version")
    if val is None:
        return "WARN", "kit_version field is missing (legacy row, pre-1.0.0)"
    if not isinstance(val, str) or not val.strip():
        return "FAIL", "kit_version must be a non-empty string"
    parts = val.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return "FAIL", f"kit_version must be semver-shaped (X.Y.Z), got {val!r}"
    return "PASS", f"kit_version=\"{val}\""


ALL_CHECKS = [check_v1, check_v2, check_v3, check_v4, check_v5, check_v6, check_v7, check_v8, check_v9]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_row(row: dict, strict: bool = False) -> dict[str, tuple[Status, str]]:
    """Returns {"V-1": (status, msg), ..., "V-9": (status, msg)}."""
    results: dict[str, tuple[Status, str]] = {}
    for i, fn in enumerate(ALL_CHECKS, start=1):
        key = f"V-{i}"
        if fn is check_v4:
            results[key] = check_v4(row, strict=strict)
        else:
            results[key] = fn(row)
    return results


def validate_file(path: pathlib.Path, strict: bool = False) -> list[dict]:
    """
    Validate every row in a JSONL file.

    Returns a list of dicts, one per row, each containing:
      - 'hadith_id'
      - 'overall_status': 'PASS' | 'WARN' | 'FAIL'
      - 'checks': dict[str, tuple[Status, str]]
    """
    rows_out: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as e:
                rows_out.append({
                    "hadith_id": f"<line {lineno}>",
                    "overall_status": "FAIL",
                    "checks": {f"V-?": ("FAIL", f"JSON parse error: {e}")},
                })
                continue

            checks = validate_row(row, strict=strict)
            statuses = [s for s, _ in checks.values()]
            if "FAIL" in statuses:
                overall = "FAIL"
            elif "WARN" in statuses:
                overall = "WARN"
            else:
                overall = "PASS"

            rows_out.append({
                "hadith_id": row.get("hadith_id", f"<line {lineno}>"),
                "overall_status": overall,
                "checks": checks,
            })
    return rows_out


# ---------------------------------------------------------------------------
# Markdown report renderer
# ---------------------------------------------------------------------------

def _render_report(
    results: list[dict],
    input_path: pathlib.Path,
    strict: bool,
    date_str: str,
) -> str:
    total = len(results)
    pass_count = sum(1 for r in results if r["overall_status"] == "PASS")
    warn_count = sum(1 for r in results if r["overall_status"] == "WARN")
    fail_count = sum(1 for r in results if r["overall_status"] == "FAIL")

    # Aggregate histogram
    fail_hist: dict[str, int] = {}
    warn_hist: dict[str, int] = {}
    for r in results:
        for key, (status, _) in r["checks"].items():
            if status == "FAIL":
                fail_hist[key] = fail_hist.get(key, 0) + 1
            elif status == "WARN":
                warn_hist[key] = warn_hist.get(key, 0) + 1

    lines = [
        f"# Validation Report — {date_str}",
        "",
        f"**Input:** {input_path}",
        f"**Rows:** {total}",
        f"**Pass rate:** {pass_count}/{total} ({100 * pass_count / total:.1f}%)" if total else "**Pass rate:** 0/0",
        f"**Mode:** {'strict' if strict else 'default'}",
        "",
        "## Aggregate failure histogram",
        "",
        "| Check | Fail count | Warn count |",
        "|---|---:|---:|",
    ]
    for i in range(1, 9):
        key = f"V-{i}"
        fc = fail_hist.get(key, 0)
        wc = warn_hist.get(key, 0)
        fc_str = str(fc) if fc else "0"
        wc_str = str(wc) if wc else "-"
        lines.append(f"| {key} | {fc_str} | {wc_str} |")

    lines.append("")
    lines.append("## Per-row results")
    lines.append("")

    for idx, r in enumerate(results, start=1):
        overall = r["overall_status"]
        hid = r["hadith_id"]
        lines.append(f"### Row {idx} — `hadith_id: {hid}` — {overall}")
        lines.append("")
        for key, (status, msg) in r["checks"].items():
            if status in ("FAIL", "WARN"):
                lines.append(f"- {key}: {status} (`{msg}`)")
            else:
                lines.append(f"- {key}: {status}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Promote mode
# ---------------------------------------------------------------------------

def promote(
    from_path: pathlib.Path,
    to_path: pathlib.Path,
    strict: bool = False,
) -> int:
    """
    Validate staging file and, if all rows pass, back up gold and append.

    Returns exit code (0 = success, 1 = failure).
    """
    print(f"Validating {from_path} before promotion...")
    results = validate_file(from_path, strict=strict)

    failures = [r for r in results if r["overall_status"] == "FAIL"]
    if failures:
        print(f"ERROR: {len(failures)} row(s) failed validation. Promotion aborted.")
        for r in failures:
            print(f"  - hadith_id={r['hadith_id']}: {r['overall_status']}")
            for key, (status, msg) in r["checks"].items():
                if status == "FAIL":
                    print(f"      {key}: {msg}")
        return 1

    # Back up target before appending (per [[feedback_no_delete_backup]])
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    if to_path.exists():
        backup_path = to_path.with_name(f"{to_path.name}.bak-{ts}")
        try:
            backup_data = to_path.read_bytes()
            backup_path.write_bytes(backup_data)
            print(f"Backup created: {backup_path}")
        except OSError as e:
            print(f"ERROR: backup failed ({e}). Promotion aborted to protect gold file.")
            return 1
    else:
        backup_path = None

    # Count existing rows in target
    existing_rows = 0
    if to_path.exists():
        with open(to_path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    existing_rows += 1

    # Append staging rows to gold
    staging_rows: list[str] = []
    with open(from_path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                staging_rows.append(line if line.endswith("\n") else line + "\n")

    with open(to_path, "a", encoding="utf-8") as fh:
        fh.writelines(staging_rows)

    new_total = existing_rows + len(staging_rows)
    print(f"Promotion complete.")
    print(f"  Rows promoted : {len(staging_rows)}")
    print(f"  Backup        : {backup_path or '(no prior gold file)'}")
    print(f"  New row count : {new_total}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _default_out(date_str: str) -> pathlib.Path:
    return _FIXTURES_DIR / f"validation-{date_str}.md"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate annotated taḥwīl gold JSONL files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--input",
        type=pathlib.Path,
        default=None,
        help="Path to the JSONL file to validate (default: tahweel-gold.jsonl sibling).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat V-4 warnings as hard fails.",
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=None,
        help="Path for the Markdown validation report.",
    )
    # Promote mode
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Promote mode: validate staging file and append to gold.",
    )
    parser.add_argument(
        "--from",
        dest="from_path",
        type=pathlib.Path,
        default=None,
        help="(promote) Staging JSONL to validate and promote.",
    )
    parser.add_argument(
        "--to",
        dest="to_path",
        type=pathlib.Path,
        default=None,
        help="(promote) Gold JSONL target to append to.",
    )

    args = parser.parse_args(argv)

    date_str = datetime.now().strftime("%Y-%m-%d")

    if args.promote:
        if not args.from_path or not args.to_path:
            print("ERROR: --promote requires --from and --to.", file=sys.stderr)
            return 1
        return promote(args.from_path, args.to_path, strict=args.strict)

    # Validation mode
    input_path = args.input or (_FIXTURES_DIR / "tahweel-gold.jsonl")
    if not input_path.exists():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        return 1

    results = validate_file(input_path, strict=args.strict)

    out_path = args.out or _default_out(date_str)
    report = _render_report(results, input_path, strict=args.strict, date_str=date_str)
    out_path.write_text(report, encoding="utf-8")
    print(f"Validation report written to: {out_path}")

    # Summary to stdout
    total = len(results)
    pass_count = sum(1 for r in results if r["overall_status"] == "PASS")
    warn_count = sum(1 for r in results if r["overall_status"] == "WARN")
    fail_count = sum(1 for r in results if r["overall_status"] == "FAIL")
    print(f"Results: {pass_count} PASS, {warn_count} WARN, {fail_count} FAIL / {total} rows")

    # Exit 0 if no FAILs (WARNs are OK at default level; strict was handled in check_v4)
    any_fail = any(r["overall_status"] == "FAIL" for r in results)
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
