"""Deterministic sidecar writing for reconciled/ (see README.md): fixed JSON layout, gzip mtime 0, no timestamps."""

import gzip
import hashlib
import json
import sys
from pathlib import Path

RECONCILED_DIR = Path(__file__).resolve().parent
HADITH_DATA_DIR = RECONCILED_DIR.parent
RECONCILE_DIR = HADITH_DATA_DIR / "diagnostics" / "chain-reconciliation"
sys.dont_write_bytecode = True
sys.path.insert(0, str(RECONCILE_DIR))
import reconcile_common as rc  # noqa: E402

common = rc.common


def dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _target(name: str) -> Path:
    path = (RECONCILED_DIR / name).resolve()
    if path.parent != RECONCILED_DIR or path.is_symlink():
        raise RuntimeError(f"{path} must be a plain file directly inside {RECONCILED_DIR}")
    return path


def write_jsonl_gz(name: str, rows) -> dict:
    """Write rows as gzip JSON lines with fixed bytes; returns {rows, sha256} of the written file."""
    path = _target(name)
    count = 0
    with open(path, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as handle:
        for row in rows:
            handle.write((dumps(row) + "\n").encode("utf-8"))
            count += 1
    return {"file": name, "rows": count, "sha256": common.sha256_file(path)}


def write_manifest(name: str, manifest: dict) -> None:
    with open(_target(name), "w", encoding="utf-8", newline="\n") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")


def code_fingerprints(*paths: Path) -> dict:
    return {common.relative_path(p): common.sha256_file(p) for p in paths}
