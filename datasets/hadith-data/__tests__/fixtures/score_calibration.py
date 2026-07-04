"""
Score a calibration test submission against the hidden gold answer key.

Usage:
  python score_calibration.py --submission <annotator.jsonl> [--gold <path>] [--out <path>]

Default gold: docs/annotation/.calibration-gold.jsonl  (relative to repo root)
Default out:  docs/annotation/calibration-result-<annotator-id>-<date>.md

Per-row score: average across (annotator_branch_i, gold_branch_i) pairs
matched by index. Per-branch score: similarity (intersection over union)
on surface-form sets after _norm normalization. Aggregate: mean across rows.

Threshold: 0.85.
"""

import argparse
import json
import pathlib
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

# ---------------------------------------------------------------------------
# Import _norm from datasets/classify_attribution.py
# File layout:
#   datasets/hadith-data/__tests__/fixtures/score_calibration.py  ← this file
#   datasets/classify_attribution.py                               ← _norm lives here
# parents[0] = fixtures/, parents[1] = __tests__/, parents[2] = hadith-data/,
# parents[3] = datasets/
# ---------------------------------------------------------------------------
_DATASETS_DIR = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_DATASETS_DIR))
from classify_attribution import _norm  # noqa: E402

# ---------------------------------------------------------------------------
# Default paths (relative to repo root, which is parents[4] of this file)
# ---------------------------------------------------------------------------
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[4]
_DEFAULT_GOLD = _REPO_ROOT / "docs" / "annotation" / ".calibration-gold.jsonl"
_DEFAULT_OUT_DIR = _REPO_ROOT / "docs" / "annotation"

PASS_THRESHOLD = 0.85


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class BranchScore:
    branch_index: int
    your_surfaces: list
    gold_surfaces: list
    matched: int
    total_unique: int
    score: float


@dataclass
class RowScore:
    hadith_id: str
    branch_scores: list = field(default_factory=list)
    row_score: float = 0.0
    skipped: bool = False  # True when submission has expected_branches=null


@dataclass
class ScoreReport:
    annotator: str
    submission_path: pathlib.Path
    gold_path: pathlib.Path
    rows: list = field(default_factory=list)
    aggregate: float = 0.0
    passed: bool = False


# ---------------------------------------------------------------------------
# Core scoring logic
# ---------------------------------------------------------------------------

def _branch_similarity(sub_branch: list, gold_branch: list) -> BranchScore:
    """Compute similarity between two lists of narrator surface forms.

    Uses set intersection / union on _norm()-normalised forms (diacritics
    stripped, alef variants unified).  Internal variable names use 'jaccard'
    for clarity; user-facing output never does.
    """
    sub_set = {_norm(n) for n in sub_branch}
    gold_set = {_norm(n) for n in gold_branch}

    intersection = sub_set & gold_set
    union = sub_set | gold_set

    if not union:
        jaccard = 1.0  # both empty → perfect match
    elif not sub_set and not gold_set:
        jaccard = 1.0
    else:
        jaccard = len(intersection) / len(union)

    return BranchScore(
        branch_index=-1,  # caller fills this in
        your_surfaces=list(sub_branch),
        gold_surfaces=list(gold_branch),
        matched=len(intersection),
        total_unique=len(union),
        score=jaccard,
    )


def _score_row(hadith_id: str, sub_branches, gold_branches) -> RowScore:
    """Score one row.  sub_branches may be None (unanswered → 0.0)."""
    row = RowScore(hadith_id=hadith_id)

    if sub_branches is None:
        row.skipped = True
        row.row_score = 0.0
        return row

    n = max(len(sub_branches), len(gold_branches))
    branch_scores = []
    for i in range(n):
        sub_b = sub_branches[i] if i < len(sub_branches) else []
        gold_b = gold_branches[i] if i < len(gold_branches) else []
        bs = _branch_similarity(sub_b, gold_b)
        bs.branch_index = i
        branch_scores.append(bs)

    row.branch_scores = branch_scores
    row.row_score = sum(bs.score for bs in branch_scores) / n if n > 0 else 1.0
    return row


def _load_jsonl(path: pathlib.Path) -> dict:
    """Load a .jsonl file, return {hadith_id: row_dict}."""
    rows = {}
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSON parse error at {path}:{lineno}: {exc}") from exc
            hid = obj.get("hadith_id")
            if not hid:
                raise ValueError(f"Missing hadith_id at {path}:{lineno}")
            rows[hid] = obj
    return rows


def _extract_annotator(submission_rows: dict) -> str:
    """Return first non-empty annotator field, sanitised for use in filenames."""
    for row in submission_rows.values():
        name = (row.get("annotator") or "").strip()
        if name:
            sanitised = re.sub(r"[^a-zA-Z0-9]+", "-", name.lower()).strip("-")
            return sanitised or "anonymous"
    return "anonymous"


def score(
    submission_path: pathlib.Path,
    gold_path: pathlib.Path = _DEFAULT_GOLD,
) -> ScoreReport:
    """Score a submission against the gold answer key.

    This function contains all the logic; the CLI is a thin wrapper.
    Returns a ScoreReport dataclass.
    """
    submission_rows = _load_jsonl(submission_path)
    gold_rows = _load_jsonl(gold_path)

    sub_ids = set(submission_rows)
    gold_ids = set(gold_rows)
    if sub_ids != gold_ids:
        extra_sub = sub_ids - gold_ids
        extra_gold = gold_ids - sub_ids
        if extra_sub:
            print(f"[WARNING] Submission has hadith_id(s) not in gold: {extra_sub}", file=sys.stderr)
        if extra_gold:
            print(f"[WARNING] Gold has hadith_id(s) not in submission: {extra_gold}", file=sys.stderr)

    annotator = _extract_annotator(submission_rows)
    report = ScoreReport(
        annotator=annotator,
        submission_path=submission_path,
        gold_path=gold_path,
    )

    # Score in gold order so output is deterministic
    for hid, gold_row in gold_rows.items():
        sub_row = submission_rows.get(hid, {})
        sub_branches = sub_row.get("expected_branches")  # may be None if row missing
        gold_branches = gold_row.get("expected_branches", [])
        row_score = _score_row(hid, sub_branches, gold_branches)
        report.rows.append(row_score)

    n_rows = len(report.rows)
    report.aggregate = sum(r.row_score for r in report.rows) / n_rows if n_rows else 0.0
    report.passed = report.aggregate >= PASS_THRESHOLD
    return report


# ---------------------------------------------------------------------------
# Markdown report rendering
# ---------------------------------------------------------------------------

def _render_report(report: ScoreReport) -> str:
    today = date.today().isoformat()
    pass_label = "PASS" if report.passed else "FAIL"
    pct = report.aggregate * 100

    lines = [
        f"# Calibration Result — {report.annotator} — {today}",
        "",
        f"**Aggregate:** {report.aggregate:.3f} ({pass_label} at {PASS_THRESHOLD})",
        f"**In plain terms:** you matched {pct:.1f}% of the gold narrators per branch on average.",
        "",
        "## Per-row breakdown",
        "",
        "| hadith_id | branch scores | row score |",
        "| --- | --- | --- |",
    ]

    for row in report.rows:
        if row.skipped:
            branch_col = "*(not answered)*"
        else:
            parts = []
            for bs in row.branch_scores:
                label = f"Branch {'ABCDEFGH'[bs.branch_index]}"
                parts.append(
                    f"{label}: {bs.score:.3f} "
                    f"({bs.matched} of {bs.total_unique} unique narrators matched)"
                )
            branch_col = "; ".join(parts) if parts else "—"
        lines.append(f"| {row.hadith_id} | {branch_col} | {row.row_score:.3f} |")

    lines.append("")
    lines.append("## What to do next")
    lines.append("")

    if report.passed:
        lines.append(
            f"**Pass (score {report.aggregate:.3f} ≥ {PASS_THRESHOLD}):** "
            "you are admitted to contribute real annotations. "
            "Contact the project coordinator to receive your first annotation batch."
        )
        if report.aggregate >= 0.95:
            lines.append(
                "\nYour score is 0.95 or above — you will not need to re-take the calibration "
                "when the guide is updated."
            )
    else:
        lowest = min(report.rows, key=lambda r: r.row_score)
        lines.append(
            f"**Below threshold (score {report.aggregate:.3f} < {PASS_THRESHOLD}):** "
            "re-read the annotation guide §3 (case types) and §4 (decision tree), "
            "then re-take the test with a new working file "
            f"(`<your-name>-calibration-v2.jsonl`). "
            f"\n\nLowest-scoring row was: **{lowest.hadith_id}** "
            f"(row score {lowest.row_score:.3f}). Pay close attention to that hadith."
        )

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_out_path(annotator: str, out_dir: pathlib.Path) -> pathlib.Path:
    today = date.today().isoformat()
    fname = f"calibration-result-{annotator}-{today}.md"
    return out_dir / fname


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Score a tahweel calibration submission."
    )
    parser.add_argument(
        "--submission", required=True, type=pathlib.Path,
        help="Path to annotator's submission .jsonl file.",
    )
    parser.add_argument(
        "--gold", type=pathlib.Path, default=_DEFAULT_GOLD,
        help=f"Path to gold answer key (default: {_DEFAULT_GOLD}).",
    )
    parser.add_argument(
        "--out", type=pathlib.Path, default=None,
        help="Path to write Markdown report (default: docs/annotation/calibration-result-<annotator>-<date>.md).",
    )
    args = parser.parse_args(argv)

    report = score(args.submission, args.gold)

    markdown = _render_report(report)

    out_path = args.out if args.out else _build_out_path(report.annotator, _DEFAULT_OUT_DIR)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(markdown)

    # Also print to stdout for convenience
    print(markdown)
    print(f"Report written to: {out_path}")

    sys.exit(0 if report.passed else 1)


if __name__ == "__main__":
    main()
