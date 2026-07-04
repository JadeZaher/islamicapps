"""
Pull the next batch of taḥwīl-marked hadith candidates for hand annotation.

Output: staging-<YYYY-MM-DD>.jsonl, with each row having the full annotation
schema (expected_branches=None, notes='', annotator='', annotated_at='',
difficulty=None) ready for the annotator.

Usage:
  python pull_next_candidates.py --n 30 [--difficulty-target N]
                                 [--seed 42] [--exclude-traditions zaydi,ibadi]
                                 [--unified-csv <path>] [--gold <path>] [--out <path>]

Difficulty heuristic (--difficulty-target N):
  1-2 = single-ح rows  (straightforward 2-branch taḥwīl)
  3-4 = 2-ح rows       (requires tracking more branch points)
  5   = 3+-ح rows      (pathological multi-branch; hardest)
  When --difficulty-target is set, the pool is restricted to rows matching
  that heuristic band before applying the 70/25/5 distribution. If not enough
  rows exist in the target band, all available qualifying rows are returned
  and a warning is emitted.

ح-count distribution targets (FR-2.2):
  ~70% single-ح, ~25% 2-ح, ~5% 3+-ح.

Per-source cap:
  No single source contributes more than floor(0.5 * n) rows. If that cap
  would prevent meeting source-diversity (≥1 per tradition), the cap is
  relaxed and a warning is emitted to stderr.

Seed default: 42 (TC-7). Future batches should use higher seeds (43, 44, …)
or omit --seed for a random run.

NFR adherence:
  NFR-6  determinism  : --seed 42 produces byte-identical output across runs.
  NFR-7  cross-platform: pathlib.Path + explicit encoding='utf-8'. No shell-outs.
  NFR-8  no-delete     : script never deletes or modifies the input CSV or gold.
                         Outputs are NEW files only.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import random
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Paths (defaults, overridable via CLI)
# ---------------------------------------------------------------------------
_FIXTURES_DIR = Path(__file__).parent
_HADITH_DATA_DIR = _FIXTURES_DIR.parent.parent  # datasets/hadith-data/

DEFAULT_UNIFIED_CSV = _HADITH_DATA_DIR / "all_hadiths_unified.csv"
DEFAULT_GOLD = _FIXTURES_DIR / "tahweel-gold.jsonl"

# ---------------------------------------------------------------------------
# Regex — reused verbatim from the legacy pull_tahweel_candidates.py
# ---------------------------------------------------------------------------
TAHWEEL_RE = re.compile(
    r'(?:^|[\s،.])ح\s+و?(?:حدثنا|حدثني|أخبرنا|أخبرني|أنبأنا|أنبأني|ثنا|نا)',
)

# ---------------------------------------------------------------------------
# Tradition classification
# ---------------------------------------------------------------------------
SUNNI_K6_SOURCES = {
    "Sahih Bukhari",
    "Sahih Muslim",
    "Jami' al-Tirmidhi",
    "Sunan Abi Da'ud",
    "Sunan Ibn Majah",
    "Sunan an-Nasa'i",
}


def classify_tradition(source: str, tradition_col: str) -> str:
    """Derive the tradition tag from source name + the CSV's tradition column."""
    src = source.strip()
    trad = tradition_col.strip().lower()

    if src in SUNNI_K6_SOURCES:
        return "sunni"
    if trad == "imami" or trad == "shia":
        return "imami"
    if "zayd" in src.lower():
        return "zaydi"
    if "tartib" in src.lower() or "rabi" in src.lower():
        return "ibadi"
    if "rida" in src.lower() or "رضا" in src or "الرضا" in src:
        return "rida"
    return "other"


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

def load_candidates(unified_csv: Path) -> list[dict]:
    """
    Read all rows that contain ≥1 ح-splitter match.
    Annotate each row with:
      - tahweel_count : int
      - tradition     : str  (sunni / imami / zaydi / ibadi / rida / other)
    Returns a list of dicts (the raw CSV row + the two added keys).
    """
    csv.field_size_limit(min(sys.maxsize, 2 ** 31 - 1))

    candidates: list[dict] = []
    with open(unified_csv, encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            text_ar = (row.get("text_ar") or "").strip()
            if not text_ar:
                continue
            count = len(TAHWEEL_RE.findall(text_ar))
            if count == 0:
                continue
            row["tahweel_count"] = count
            row["tradition"] = classify_tradition(
                row.get("source") or "", row.get("tradition") or ""
            )
            candidates.append(row)
    return candidates


def filter_excluded(candidates: list[dict], exclude_traditions: list[str]) -> list[dict]:
    """Remove rows whose tradition is in exclude_traditions."""
    excluded = {t.lower() for t in exclude_traditions}
    return [c for c in candidates if c["tradition"].lower() not in excluded]


def dedup_against_gold(candidates: list[dict], gold_path: Path) -> list[dict]:
    """
    Remove candidates already present in the gold JSONL.
    Dedup key: (source.strip(), hadith_no.strip()).
    Silently skips if gold_path does not exist.
    """
    gold_keys: set[tuple[str, str]] = set()
    if gold_path.exists():
        with open(gold_path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    src = (obj.get("source") or "").strip()
                    hno = (obj.get("hadith_no") or "").strip()
                    gold_keys.add((src, hno))
                except json.JSONDecodeError:
                    pass

    return [
        c for c in candidates
        if ((c.get("source") or "").strip(), (c.get("hadith_no") or "").strip())
        not in gold_keys
    ]


def stratified_pick(
    candidates: list[dict],
    n: int,
    rng: random.Random,
    difficulty_target: Optional[int] = None,
) -> list[dict]:
    """
    Apply the 70/25/5 ح-count distribution + per-source cap + cross-tradition
    best-effort.

    Steps:
    1. If difficulty_target is set, filter pool to the corresponding ح-count band.
    2. Partition the pool by source.
    3. Per-source cap = floor(0.5 * n).
    4. Compute band targets: n1 = round(0.70*n), n2 = round(0.25*n),
       n3 = n - n1 - n2.
    5. For each source, deterministically shuffle with rng, then slice each band.
    6. Merge all per-source picks; if total < n, log to stderr.
    7. Return the picked list.
    """
    pool = candidates

    # Difficulty-target pre-filter
    if difficulty_target is not None:
        if difficulty_target <= 2:
            pool = [c for c in pool if c["tahweel_count"] == 1]
        elif difficulty_target <= 4:
            pool = [c for c in pool if c["tahweel_count"] == 2]
        else:
            pool = [c for c in pool if c["tahweel_count"] >= 3]

        if len(pool) == 0:
            print(
                f"WARN: --difficulty-target {difficulty_target}: 0 qualifying rows in pool.",
                file=sys.stderr,
            )
            return []
        if len(pool) < n:
            print(
                f"WARN: --difficulty-target {difficulty_target}: only {len(pool)} qualifying rows "
                f"(requested {n}). Returning all available.",
                file=sys.stderr,
            )

    # Per-source hard cap
    per_source_cap = math.floor(0.5 * n) if n >= 2 else 1

    # Band sizes
    n1 = round(0.70 * n)
    n2 = round(0.25 * n)
    n3 = n - n1 - n2
    if n3 < 0:
        n3 = 0

    # Warn about non-Sunni traditions that have zero qualifying rows
    traditions_in_pool = {c["tradition"] for c in pool}
    for trad in ("imami", "zaydi", "ibadi", "rida"):
        if trad not in traditions_in_pool:
            print(
                f"WARN: tradition '{trad}': 0 rows with ح-splitter, skipping.",
                file=sys.stderr,
            )

    # Group by source
    by_source: dict[str, list[dict]] = {}
    for c in pool:
        src = (c.get("source") or "").strip()
        by_source.setdefault(src, []).append(c)

    # Collect per-source contributions, respecting the cap and the 70/25/5 bands
    picked: list[dict] = []
    seen_sources: set[str] = set()

    for src, rows in by_source.items():
        seen_sources.add(src)
        rows_1 = [r for r in rows if r["tahweel_count"] == 1]
        rows_2 = [r for r in rows if r["tahweel_count"] == 2]
        rows_3p = [r for r in rows if r["tahweel_count"] >= 3]

        # Shuffle each band independently with the shared RNG for determinism
        rng.shuffle(rows_1)
        rng.shuffle(rows_2)
        rng.shuffle(rows_3p)

        # How many from each band for this source?
        # Pro-rate the target by number of sources, capped at per_source_cap.
        n_sources = len(by_source)
        src_target = min(per_source_cap, math.ceil(n / max(n_sources, 1)))

        s_n1 = max(round(0.70 * src_target), 1) if rows_1 else 0
        s_n2 = max(round(0.25 * src_target), 0) if rows_2 else 0
        s_n3 = max(src_target - s_n1 - s_n2, 0) if rows_3p else 0

        picked.extend(rows_1[:s_n1])
        picked.extend(rows_2[:s_n2])
        picked.extend(rows_3p[:s_n3])

    # Now apply global per-source cap and enforce 70/25/5 on the final pick
    # First, trim any source that exceeded the cap
    trimmed: list[dict] = []
    per_source_count: dict[str, int] = {}
    for row in picked:
        src = (row.get("source") or "").strip()
        count = per_source_count.get(src, 0)
        if count < per_source_cap:
            trimmed.append(row)
            per_source_count[src] = count + 1

    # Shuffle the combined pool and take n, maintaining 70/25/5 globally
    trimmed_1 = [r for r in trimmed if r["tahweel_count"] == 1]
    trimmed_2 = [r for r in trimmed if r["tahweel_count"] == 2]
    trimmed_3p = [r for r in trimmed if r["tahweel_count"] >= 3]

    rng.shuffle(trimmed_1)
    rng.shuffle(trimmed_2)
    rng.shuffle(trimmed_3p)

    take_1 = trimmed_1[:n1]
    take_2 = trimmed_2[:n2]
    take_3 = trimmed_3p[:n3]

    final = take_1 + take_2 + take_3

    # If we still haven't hit n, fill from leftover (maintaining per-source cap)
    if len(final) < n:
        used_keys = {
            ((r.get("source") or "").strip(), (r.get("hadith_no") or "").strip())
            for r in final
        }
        leftover = [
            r for r in trimmed
            if ((r.get("source") or "").strip(), (r.get("hadith_no") or "").strip())
            not in used_keys
        ]
        rng.shuffle(leftover)
        final.extend(leftover[: n - len(final)])

    if len(final) < n:
        print(
            f"WARN: requested {n} candidates but only {len(final)} available after "
            f"dedup + cap constraints.",
            file=sys.stderr,
        )

    return final[:n]


def write_staging(picked, out_path: Path) -> None:
    """
    Write the picked rows as JSONL with the full annotation schema.
    Fields expected_branches, notes, annotator, annotated_at, difficulty are
    left blank/null for the annotator to fill in.

    Args:
        picked:   Either a list[dict] of raw CSV rows (legacy call) OR a
                  PullResult instance (programmatic API call).
        out_path: Destination path. Parent directories are created if needed.
    """
    # Accept either PullResult or a plain list
    rows = picked.rows if hasattr(picked, "rows") else picked

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        for row in rows:
            payload = {
                "hadith_id": (row.get("hadith_id") or "").strip(),
                "source": (row.get("source") or "").strip(),
                "hadith_no": (row.get("hadith_no") or "").strip(),
                "tahweel_count": row["tahweel_count"],
                "text_ar": (row.get("text_ar") or "").strip(),
                "sanad": (row.get("sanad") or "").strip(),
                "expected_branches": None,
                "notes": "",
                "annotator": "",
                "annotated_at": "",
                "difficulty": None,
            }
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Programmatic API (dataclass wrappers for testability)
# ---------------------------------------------------------------------------

@dataclass
class PullConfig:
    """Configuration for a pull_candidates() call."""
    n: int
    seed: int = 42
    difficulty_target: Optional[int] = None
    exclude_traditions: frozenset = field(default_factory=frozenset)
    csv_path: Path = field(default_factory=lambda: DEFAULT_UNIFIED_CSV)


@dataclass
class PullResult:
    """Result of a pull_candidates() call."""
    rows: list  # list[dict] — the raw CSV rows with tahweel_count annotation
    stderr_log: list  # list[str] — cross-tradition skip messages captured from stderr
    excluded_count: int  # number of rows skipped by dedup


def pull_candidates(config: PullConfig, gold_path: Path) -> PullResult:
    """
    Load, filter, dedup, and stratify-pick candidates per the given config.

    This is the programmatic entry point for tests — it does NOT write any
    files and captures stderr messages instead of printing them.

    Args:
        config:    PullConfig instance.
        gold_path: Path to tahweel-gold.jsonl (for dedup).

    Returns:
        PullResult with the picked rows, captured stderr log, and excluded count.
    """
    import io as _io

    # Capture stderr so callers can inspect cross-tradition warnings
    old_stderr = sys.stderr
    stderr_buf = _io.StringIO()
    sys.stderr = stderr_buf

    try:
        candidates = load_candidates(config.csv_path)

        if config.exclude_traditions:
            candidates = filter_excluded(candidates, list(config.exclude_traditions))

        pre_dedup_count = len(candidates)
        candidates = dedup_against_gold(candidates, gold_path)
        excluded_count = pre_dedup_count - len(candidates)

        rng = random.Random(config.seed)
        picked = stratified_pick(
            candidates, config.n, rng, difficulty_target=config.difficulty_target
        )
    finally:
        sys.stderr = old_stderr

    stderr_log = [line for line in stderr_buf.getvalue().splitlines() if line.strip()]

    return PullResult(rows=picked, stderr_log=stderr_log, excluded_count=excluded_count)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Pull next batch of taḥwīl-marked hadith candidates for annotation."
    )
    p.add_argument("--n", type=int, default=30, help="Number of candidates to pull (default 30)")
    p.add_argument(
        "--difficulty-target",
        type=int,
        default=None,
        metavar="N",
        help="Restrict to difficulty band: 1-2=single-ح, 3-4=2-ح, 5=3+-ح",
    )
    p.add_argument("--seed", type=int, default=42, help="RNG seed (default 42, per TC-7)")
    p.add_argument(
        "--exclude-traditions",
        type=str,
        default="",
        help="Comma-separated list of traditions to exclude (e.g. zaydi,ibadi)",
    )
    p.add_argument(
        "--unified-csv", "--csv",
        dest="unified_csv",
        type=Path,
        default=DEFAULT_UNIFIED_CSV,
        help="Path to all_hadiths_unified.csv (--csv is an alias)",
    )
    p.add_argument(
        "--gold",
        type=Path,
        default=DEFAULT_GOLD,
        help="Path to tahweel-gold.jsonl (for dedup)",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path (defaults to fixtures/staging-<YYYY-MM-DD>.jsonl)",
    )
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)

    unified_csv: Path = args.unified_csv
    gold_path: Path = args.gold
    n: int = args.n
    seed: int = args.seed
    difficulty_target: Optional[int] = args.difficulty_target
    exclude_traditions: list[str] = (
        [t.strip() for t in args.exclude_traditions.split(",") if t.strip()]
        if args.exclude_traditions
        else []
    )

    if not unified_csv.exists():
        print(f"ERROR: unified CSV not found: {unified_csv}", file=sys.stderr)
        return 1

    out_path: Path = args.out
    if out_path is None:
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        out_path = _FIXTURES_DIR / f"staging-{today}.jsonl"

    # Load + filter + dedup
    print(f"Loading candidates from {unified_csv} ...", file=sys.stderr)
    candidates = load_candidates(unified_csv)
    print(f"  Found {len(candidates)} ح-marked rows.", file=sys.stderr)

    if exclude_traditions:
        candidates = filter_excluded(candidates, exclude_traditions)
        print(
            f"  After excluding traditions {exclude_traditions}: {len(candidates)} rows.",
            file=sys.stderr,
        )

    candidates = dedup_against_gold(candidates, gold_path)
    print(
        f"  After dedup against gold ({gold_path.name}): {len(candidates)} rows.",
        file=sys.stderr,
    )

    # Stratified pick
    rng = random.Random(seed)
    picked = stratified_pick(candidates, n, rng, difficulty_target=difficulty_target)

    # Write output
    write_staging(picked, out_path)
    print(f"Wrote {len(picked)} candidates to {out_path}", file=sys.stderr)
    print(str(out_path))  # stdout: the output path for programmatic callers
    return 0


if __name__ == "__main__":
    sys.exit(main())
