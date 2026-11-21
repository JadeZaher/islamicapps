#!/usr/bin/env python3
"""Stream a narrator-resolution audit without modifying corpus data."""

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import os
import sqlite3
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, TextIO


BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parents[1]
REGISTRY_PATH = PROJECT_DIR / "datasets" / "narrator-data" / "all_rawis.csv"
DEFAULT_INPUT = BASE_DIR / "all_hadiths_unified.csv.gz"
DEFAULT_AUDIT = BASE_DIR / "sanad_resolution_audit.json"
DEFAULT_CANDIDATES = BASE_DIR / "narrator_alias_candidates.json"
DIAGNOSTIC_DIR = BASE_DIR / "diagnostics" / "narrator-resolution"

UNRESOLVED_BUFFER_KEYS = 4_096
UNRESOLVED_BUFFER_BYTES = 2 * 1024 * 1024


class DiskFrequencyCounter:
    """Keep exact high-cardinality counts in a temporary SQLite database."""

    def __init__(
        self,
        *,
        max_pending_keys: int = UNRESOLVED_BUFFER_KEYS,
        max_pending_bytes: int = UNRESOLVED_BUFFER_BYTES,
    ) -> None:
        self._max_pending_keys = max_pending_keys
        self._max_pending_bytes = max_pending_bytes
        self._pending: Counter[tuple[str, str, str]] = Counter()
        self._pending_bytes = 0
        # An empty filename creates an automatically removed disk-backed database.
        self._database = sqlite3.connect("")
        self._database.execute("PRAGMA journal_mode = OFF")
        self._database.execute("PRAGMA synchronous = OFF")
        self._database.execute("PRAGMA temp_store = FILE")
        self._database.execute("PRAGMA cache_size = -2048")
        self._database.execute(
            """
            CREATE TABLE unresolved_counts (
                tradition TEXT COLLATE BINARY NOT NULL,
                source TEXT COLLATE BINARY NOT NULL,
                surface TEXT COLLATE BINARY NOT NULL,
                occurrences INTEGER NOT NULL,
                PRIMARY KEY (tradition, source, surface)
            ) WITHOUT ROWID
            """
        )
        self._database.execute(
            """
            CREATE TABLE unicode_candidates (
                surface TEXT COLLATE BINARY NOT NULL,
                scholar_indx TEXT COLLATE BINARY NOT NULL,
                normalized_surface TEXT COLLATE BINARY NOT NULL,
                first_input_row INTEGER NOT NULL,
                first_hadith_id TEXT NOT NULL,
                first_source TEXT NOT NULL,
                first_tradition TEXT NOT NULL,
                occurrences INTEGER NOT NULL,
                PRIMARY KEY (surface, scholar_indx)
            ) WITHOUT ROWID
            """
        )

    def increment(self, key: tuple[str, str, str]) -> None:
        """Add one occurrence and flush before the in-memory buffer can grow freely."""
        if key not in self._pending:
            self._pending_bytes += sum(len(value.encode("utf-8")) for value in key)
        self._pending[key] += 1
        if (
            len(self._pending) >= self._max_pending_keys
            or self._pending_bytes >= self._max_pending_bytes
        ):
            self._flush()

    def top(self, limit: int) -> list[tuple[str, str, str, int]]:
        """Return exact top counts with a stable binary tie-break order."""
        if limit < 0:
            raise ValueError("limit must be non-negative")
        self._flush()
        rows = self._database.execute(
            """
            SELECT tradition, source, surface, occurrences
            FROM unresolved_counts
            ORDER BY occurrences DESC, tradition ASC, source ASC, surface ASC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            (tradition, source, surface, int(occurrences))
            for tradition, source, surface, occurrences in rows
        ]

    def increment_candidate(
        self,
        *,
        surface: str,
        scholar_indx: str,
        normalized_surface: str,
        row_number: int,
        hadith_id: str,
        source: str,
        tradition: str,
    ) -> None:
        """Aggregate exact Unicode candidates on disk with stable first evidence."""
        self._database.execute(
            """
            INSERT INTO unicode_candidates (
                surface, scholar_indx, normalized_surface, first_input_row,
                first_hadith_id, first_source, first_tradition, occurrences
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT (surface, scholar_indx) DO UPDATE SET
                occurrences = occurrences + 1
            """,
            (
                surface,
                scholar_indx,
                normalized_surface,
                row_number,
                hadith_id,
                source,
                tradition,
            ),
        )

    def candidate_count(self) -> int:
        """Return the exact number of distinct candidate pairs."""
        row = self._database.execute("SELECT count(*) FROM unicode_candidates").fetchone()
        return int(row[0]) if row else 0

    def top_candidates(self, limit: int) -> list[dict[str, Any]]:
        """Return a bounded deterministic candidate slice ranked by occurrence."""
        if limit < 0:
            raise ValueError("limit must be non-negative")
        rows = self._database.execute(
            """
            SELECT surface, scholar_indx, normalized_surface, first_input_row,
                   first_hadith_id, first_source, first_tradition, occurrences
            FROM unicode_candidates
            ORDER BY occurrences DESC, surface ASC, scholar_indx ASC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            {
                "candidate_type": "unicode_normalization_equivalence",
                "status": "machine_audited_not_human_verified",
                "surface": surface,
                "normalized_surface": normalized_surface,
                "scholar_indx": scholar_indx,
                "evidence": {
                    "transforms": ["NFKC", "remove_unicode_format_controls"],
                    "registry_match": "exact_normalized_unique_identity",
                    "first_input_row": int(first_input_row),
                    "first_hadith_id": first_hadith_id,
                    "first_source": first_source,
                    "first_tradition": first_tradition,
                },
                "occurrences": int(occurrences),
            }
            for (
                surface,
                scholar_indx,
                normalized_surface,
                first_input_row,
                first_hadith_id,
                first_source,
                first_tradition,
                occurrences,
            ) in rows
        ]

    def close(self) -> None:
        """Release the temporary database and buffered keys."""
        self._pending.clear()
        self._pending_bytes = 0
        self._database.close()

    def _flush(self) -> None:
        if not self._pending:
            return
        self._database.executemany(
            """
            INSERT INTO unresolved_counts (
                tradition, source, surface, occurrences
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT (tradition, source, surface) DO UPDATE SET
                occurrences = occurrences + excluded.occurrences
            """,
            (
                (tradition, source, surface, occurrences)
                for (tradition, source, surface), occurrences in self._pending.items()
            ),
        )
        self._pending.clear()
        self._pending_bytes = 0


def open_csv_input(path: Path) -> TextIO:
    """Open an explicit plain CSV or a canonical gzip snapshot as text."""
    if path.suffix.casefold() == ".gz":
        return gzip.open(path, mode="rt", encoding="utf-8", newline="")
    return path.open(encoding="utf-8", newline="")


def scope_path(path: Path) -> str:
    """Render repository inputs relatively while retaining external explicit paths."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(PROJECT_DIR).as_posix()
    except ValueError:
        return resolved.as_posix()


def load_module(name: str, path: Path):
    """Import one adjacent pipeline module without relying on the caller's CWD."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    """Hash an input in fixed-size chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def legacy_index(regen: Any, registry_path: Path) -> dict[str, str]:
    """Build the pre-Unicode-normalization exact index for audit comparison."""
    from classify_attribution import _norm  # noqa: PLC0415

    index: dict[str, str] = {}
    duplicates: set[str] = set()

    def add(value: str, scholar_indx: str) -> None:
        normalized = _norm(value)
        if not normalized:
            return
        existing = index.get(normalized)
        if existing is not None and existing != scholar_indx:
            duplicates.add(normalized)
        else:
            index[normalized] = scholar_indx

    with registry_path.open(encoding="utf-8", errors="replace", newline="") as handle:
        for row in csv.DictReader(handle):
            scholar_indx = (row.get("scholar_indx") or "").strip()
            name = (row.get("name") or "").strip()
            if not scholar_indx or not name:
                continue
            add(name, scholar_indx)
            arabic_name = regen._extract_arabic_name(name)
            if arabic_name:
                add(arabic_name, scholar_indx)
    for normalized in duplicates:
        index.pop(normalized, None)
    return index


def ranked(counter: Counter, limit: int | None = None) -> list[dict[str, Any]]:
    """Return deterministic count records without relying on Counter insertion order."""
    entries = sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    if limit is not None:
        entries = entries[:limit]
    return [{"key": key, "count": count} for key, count in entries]


def build_audit(input_path: Path, registry_path: Path, top: int) -> tuple[dict, dict]:
    """Collect row, source, surface, and Unicode-exact candidate evidence."""
    sys.path[:0] = [str(PROJECT_DIR / "datasets"), str(BASE_DIR)]
    regen = load_module("regen_narrator_audit", BASE_DIR / "regen_unified_csvs.py")
    extractor = load_module("isnad_narrator_audit", BASE_DIR / "extract_isnad_unified.py")
    exact_index, blocked_index = regen.build_narrator_index(str(registry_path))
    old_exact = legacy_index(regen, registry_path)

    metrics: Counter = Counter()
    by_tradition: dict[str, Counter] = defaultdict(Counter)
    by_source: dict[tuple[str, str], Counter] = defaultdict(Counter)
    unresolved = DiskFrequencyCounter()

    try:
        with open_csv_input(input_path) as handle:
            for row_number, row in enumerate(csv.DictReader(handle), 2):
                tradition = (row.get("tradition") or "").strip() or "<missing>"
                source = (row.get("source") or "").strip() or "<missing>"
                key = (tradition, source)
                metrics["rows"] += 1
                by_tradition[tradition]["rows"] += 1
                by_source[key]["rows"] += 1
                try:
                    branches = extractor.extract_isnad_branches(row.get("text_ar") or "")
                except extractor.IsnadExtractionLimitError:
                    metrics["rows_extraction_limited"] += 1
                    by_tradition[tradition]["rows_extraction_limited"] += 1
                    by_source[key]["rows_extraction_limited"] += 1
                    continue
                if not branches:
                    metrics["rows_without_extracted_chain"] += 1
                    by_tradition[tradition]["rows_without_extracted_chain"] += 1
                    by_source[key]["rows_without_extracted_chain"] += 1
                    continue

                metrics["rows_with_extracted_chain"] += 1
                by_tradition[tradition]["rows_with_extracted_chain"] += 1
                by_source[key]["rows_with_extracted_chain"] += 1
                unresolved_here = False
                for branch in branches:
                    for surface in branch:
                        metrics["surfaces_attempted"] += 1
                        # This is the sole automatic-candidate path: a source
                        # surface must differ only under the documented Unicode
                        # normalization and then exactly equal one registry entry.
                        old_normalized = __import__("classify_attribution")._norm(surface)
                        new_normalized = regen.narrator_normalize(surface)
                        scholar_indx = exact_index.get(new_normalized)
                        if (old_normalized != new_normalized and scholar_indx
                                and old_normalized not in old_exact):
                            unresolved.increment_candidate(
                                surface=surface,
                                scholar_indx=scholar_indx,
                                normalized_surface=new_normalized,
                                row_number=row_number,
                                hadith_id=(row.get("hadith_id") or "").strip(),
                                source=source,
                                tradition=tradition,
                            )

                        if regen.resolve_narrator(surface, exact_index, blocked_index):
                            continue
                        unresolved_here = True
                        unresolved.increment((tradition, source, surface))
                        metrics["unresolved_surface_occurrences"] += 1
                        by_tradition[tradition]["unresolved_surface_occurrences"] += 1
                        by_source[key]["unresolved_surface_occurrences"] += 1

                if unresolved_here:
                    metrics["rows_with_unresolved_surface"] += 1
                    by_tradition[tradition]["rows_with_unresolved_surface"] += 1
                    by_source[key]["rows_with_unresolved_surface"] += 1
                else:
                    metrics["rows_fully_resolved"] += 1
                    by_tradition[tradition]["rows_fully_resolved"] += 1
                    by_source[key]["rows_fully_resolved"] += 1
        top_unresolved = unresolved.top(top)
        candidate_count_total = unresolved.candidate_count()
        candidate_hits = unresolved.top_candidates(top)
    finally:
        unresolved.close()

    audit = {
        "schema_version": 1,
        "scope": {
            "input": scope_path(input_path),
            "input_sha256": sha256_file(input_path),
            "narrator_registry": scope_path(registry_path),
            "narrator_registry_sha256": sha256_file(registry_path),
            "meaning": "diagnostic snapshot; not a curation manifest or publication claim",
        },
        "resolver_policy": {
            "atomic_rows": True,
            "branch_cap": extractor.MAX_ISNAD_BRANCHES,
            "automatic_identity_rule": "exact normalized unique registry identity only",
        },
        "metrics": dict(sorted(metrics.items())),
        "by_tradition": {
            tradition: dict(sorted(counts.items()))
            for tradition, counts in sorted(by_tradition.items())
        },
        "by_source": [
            {
                "tradition": tradition,
                "source": source,
                **dict(sorted(counts.items())),
            }
            for (tradition, source), counts in sorted(by_source.items())
        ],
        "top_unresolved_surfaces": [
            {"tradition": tradition, "source": source, "surface": surface, "count": count}
            for tradition, source, surface, count in top_unresolved
        ],
    }
    candidates = {
        "schema_version": 1,
        "scope": audit["scope"],
        "policy": "Only exact Unicode-normalization equivalences are emitted; this bounded diagnostic never asserts a scholarly alias or completes a chain.",
        "candidate_count_total": candidate_count_total,
        "candidate_count_emitted": len(candidate_hits),
        "truncated": candidate_count_total > len(candidate_hits),
        "candidates": candidate_hits,
    }
    return audit, candidates


def write_json(path: Path, value: dict) -> None:
    """Atomically replace a deterministic JSON diagnostic artifact."""
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    try:
        with os.fdopen(descriptor, mode="w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    finally:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass


def validate_output_paths(
    input_path: Path,
    registry_path: Path,
    audit_output: Path,
    candidate_output: Path,
) -> tuple[Path, Path]:
    """Restrict diagnostics to durable defaults or the isolated diagnostics tree."""
    protected = (input_path.expanduser().resolve(), registry_path.expanduser().resolve())
    base_lexical = Path(os.path.abspath(os.fspath(BASE_DIR.expanduser())))
    allowed_defaults = {
        Path(os.path.abspath(os.fspath(DEFAULT_AUDIT.expanduser()))),
        Path(os.path.abspath(os.fspath(DEFAULT_CANDIDATES.expanduser()))),
    }
    diagnostic_root_lexical = Path(os.path.abspath(os.fspath(DIAGNOSTIC_DIR.expanduser())))
    current = diagnostic_root_lexical
    while current != base_lexical:
        if current.is_symlink():
            raise ValueError(f"Narrator diagnostics tree cannot contain symlinks: {current}")
        if current.parent == current or base_lexical not in current.parents:
            raise ValueError("Narrator diagnostics tree must remain under the dataset directory")
        current = current.parent
    diagnostic_root = diagnostic_root_lexical.resolve()
    if diagnostic_root != diagnostic_root_lexical:
        raise ValueError("Narrator diagnostics root must not redirect outside its lexical path")
    lexical_outputs = [
        Path(os.path.abspath(os.fspath(audit_output.expanduser()))),
        Path(os.path.abspath(os.fspath(candidate_output.expanduser()))),
    ]
    if lexical_outputs[0] == lexical_outputs[1]:
        raise ValueError("Audit and candidate outputs must be distinct")
    outputs: list[Path] = []
    for lexical_output in lexical_outputs:
        if lexical_output.is_symlink():
            raise ValueError(f"Narrator audit output cannot be a symlink: {lexical_output}")
        output = lexical_output.resolve()
        outputs.append(output)
        if lexical_output.suffix.casefold() != ".json":
            raise ValueError("Narrator audit outputs must use the .json suffix")
        try:
            inside_diagnostics = (
                lexical_output.is_relative_to(diagnostic_root_lexical)
                and output.is_relative_to(diagnostic_root)
            )
        except AttributeError:
            inside_diagnostics = (
                (diagnostic_root_lexical == lexical_output or diagnostic_root_lexical in lexical_output.parents)
                and (diagnostic_root == output or diagnostic_root in output.parents)
            )
        is_default = lexical_output in allowed_defaults
        if is_default and output != lexical_output:
            raise ValueError(f"Durable narrator audit output must not redirect: {lexical_output}")
        if not is_default and not inside_diagnostics:
            raise ValueError(
                f"Narrator audit output must be a durable default or remain under {diagnostic_root}"
            )
        if output in protected:
            raise ValueError("Narrator audit output cannot replace an input or registry")
        if output.exists():
            if not output.is_file() or output.stat().st_nlink != 1:
                raise ValueError(f"Narrator audit output must be a regular, unlinked file: {output}")
            if any(os.path.samefile(output, item) for item in protected if item.exists()):
                raise ValueError("Narrator audit output cannot alias an input or registry")
    if all(output.exists() for output in outputs) and os.path.samefile(*outputs):
        raise ValueError("Audit and candidate outputs cannot be hard-link aliases")
    return outputs[0], outputs[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--registry", type=Path, default=REGISTRY_PATH)
    parser.add_argument("--audit-output", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--candidate-output", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--top", type=int, default=200)
    args = parser.parse_args()
    if args.top <= 0:
        parser.error("--top must be positive")
    args.audit_output, args.candidate_output = validate_output_paths(
        args.input,
        args.registry,
        args.audit_output,
        args.candidate_output,
    )
    args.audit_output.parent.mkdir(parents=True, exist_ok=True)
    args.candidate_output.parent.mkdir(parents=True, exist_ok=True)
    audit, candidates = build_audit(args.input, args.registry, args.top)
    write_json(args.audit_output, audit)
    write_json(args.candidate_output, candidates)
    print(json.dumps({
        "metrics": audit["metrics"],
        "candidate_count_total": candidates["candidate_count_total"],
        "candidate_count_emitted": candidates["candidate_count_emitted"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
