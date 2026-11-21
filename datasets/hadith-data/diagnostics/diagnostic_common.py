"""Shared helpers for the data-gap diagnostic jobs (see diagnostics/AGENTS.md).

Every job reads canonical inputs and writes only new files under
datasets/hadith-data/diagnostics/<job-name>/.
"""

import csv
import datetime
import functools
import gzip
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # never create __pycache__ beside canonical modules

DIAGNOSTICS_DIR = Path(__file__).resolve().parent
HADITH_DATA_DIR = DIAGNOSTICS_DIR.parent
DATASETS_DIR = HADITH_DATA_DIR.parent
PROJECT_DIR = DATASETS_DIR.parent
CORPUS_PATH = HADITH_DATA_DIR / "all_hadiths_unified.csv.gz"
REGISTRY_PATH = DATASETS_DIR / "narrator-data" / "all_rawis.csv"

csv.field_size_limit(1 << 30)

for _path in (str(DATASETS_DIR), str(HADITH_DATA_DIR)):
    if _path not in sys.path:
        sys.path.append(_path)


def sha256_file(path: Path) -> str:
    """Hash a file in fixed-size chunks."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head() -> str:
    """Read-only `git rev-parse HEAD`; 'unknown' when git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=PROJECT_DIR, capture_output=True,
            text=True, timeout=20, check=True,
        )
        return result.stdout.strip()
    except Exception:  # noqa: BLE001 - header metadata only
        return "unknown"


def relative_path(path: Path) -> str:
    """Repository-relative POSIX path for headers and READMEs."""
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(PROJECT_DIR).as_posix()
    except ValueError:
        return resolved.as_posix()


def load_module(name: str, path: Path):
    """Import one adjacent pipeline module by file path."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_regen():
    return load_module("regen_unified_csvs_diag", HADITH_DATA_DIR / "regen_unified_csvs.py")


def load_extractor():
    return load_module("extract_isnad_unified_diag", HADITH_DATA_DIR / "extract_isnad_unified.py")


def output_directory(job_name: str) -> Path:
    """Create diagnostics/<job_name>/ and refuse anything that escapes diagnostics/."""
    target = (DIAGNOSTICS_DIR / job_name)
    if target.is_symlink():
        raise RuntimeError(f"{target} is a symlink")
    target.mkdir(parents=True, exist_ok=True)
    resolved = target.resolve()
    if DIAGNOSTICS_DIR not in resolved.parents:
        raise RuntimeError(f"{resolved} is outside {DIAGNOSTICS_DIR}")
    return resolved


def open_output(directory: Path, name: str, binary: bool = False, gzipped: bool = False):
    """Open a NEW-or-own output file inside a job directory (never elsewhere)."""
    path = (directory / name).resolve()
    if directory.resolve() not in path.parents:
        raise RuntimeError(f"{path} escapes {directory}")
    if path.is_symlink():
        raise RuntimeError(f"{path} is a symlink")
    if gzipped:
        # mtime=0 keeps the gzip bytes deterministic.
        raw = open(path, "wb")
        return gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0), raw
    if binary:
        return open(path, "wb"), None
    return open(path, "w", encoding="utf-8", newline="\n"), None


def write_json(directory: Path, name: str, value) -> Path:
    handle, _ = open_output(directory, name)
    with handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=False)
        handle.write("\n")
    return directory / name


def write_jsonl(directory: Path, name: str, rows, gzipped: bool = False) -> int:
    """Write an iterable of dicts as JSON lines; returns the row count."""
    handle, raw = open_output(directory, name, gzipped=gzipped)
    count = 0
    try:
        for row in rows:
            line = json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            handle.write(line.encode("utf-8") if gzipped else line)
            count += 1
    finally:
        handle.close()
        if raw is not None:
            raw.close()
    return count


def input_fingerprints(*paths: Path) -> dict:
    return {relative_path(p): sha256_file(p) for p in paths}


def header_object(job: str, command: str, inputs: dict) -> dict:
    """Provenance header recorded in every JSON output."""
    return {
        "job": job,
        "command": command,
        "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "git_head": git_head(),
        "inputs_sha256": inputs,
        "status": "diagnostic_only_unreviewed",
        "meaning": "candidate/diagnostic evidence; asserts no narrator identity, alias, grade, date or translation",
    }


def iter_corpus_rows(path: Path = CORPUS_PATH):
    """Stream corpus rows as (row_number, dict); row_number counts the header as line 1."""
    with gzip.open(path, mode="rt", encoding="utf-8", newline="") as handle:
        for row_number, row in enumerate(csv.DictReader(handle), 2):
            yield row_number, row


def clean(value) -> str:
    return (value or "").strip()


def row_reference(row_number: int, row: dict) -> dict:
    """Stable pointer back to a snapshot row (the snapshot has no record_id column)."""
    return {
        "id": clean(row.get("id")),
        "hadith_id": clean(row.get("hadith_id")),
        "source": clean(row.get("source")),
        "line": row_number,
    }


def build_resolver(regen):
    """(resolve, exact_index, blocked_index): resolve(surface) is the canonical tiered regen.resolve_narrator, memoized."""
    exact_index, blocked_index = regen.build_narrator_index(str(REGISTRY_PATH))

    @functools.lru_cache(maxsize=None)
    def resolve(surface: str):
        return regen.resolve_narrator(surface, exact_index, blocked_index)

    return resolve, exact_index, blocked_index
