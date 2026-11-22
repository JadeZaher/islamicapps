"""Paths and read-only readers shared by the hadith-kg / Riwayat sidecar builders (README.md §External sources).

The two SQLite files are opened `mode=ro&immutable=1` and only queried; nothing in their directories is executed.
"""

from __future__ import annotations

import csv
import gzip
import json
import os
import pathlib
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sidecar_io as io_  # noqa: E402

rc, common = io_.rc, io_.common
sys.path.insert(0, str(common.DIAGNOSTICS_DIR / "report-correspondence"))
import matn_isolation as isolation  # noqa: E402

EXTERNAL = common.DATASETS_DIR / "sources" / "external"
HADITH_KG = EXTERNAL / "hadith-kg" / "hadith-kg.db"
RIWAYAT = EXTERNAL / "riwayat-corpus" / "hadith_master.db"
# The record_id-bearing corpus the Postgres bundle was built from (same input as report-correspondence).
CORPUS = common.HADITH_DATA_DIR / "development" / "incomplete-curation" / "all_hadiths_unified.incomplete.csv.gz"
WORK_REGISTRY = common.HADITH_DATA_DIR / "neo4j_export" / "source_work_registry.json"
# The projection actually loaded (mention ids and today's identity candidates); read only.
# EXTERNAL_SIDECAR_PROJECTION points at another projection's `canonical/` (the interim one built for a corpus change).
PROJECTION = Path(os.environ.get("EXTERNAL_SIDECAR_PROJECTION") or (
    common.HADITH_DATA_DIR / "development" / "pg-load-2026-11-21" / "projection-candidates" / "canonical"))
CROSSWALK = "external_report_crosswalk.jsonl.gz"

LICENCE = {
    "hadith_kg": ("CC BY 4.0. hadith-kg, \"الجامع — Hadith Knowledge Graph\" by emadjumaah, "
                  "https://huggingface.co/datasets/emadjumaah/hadith-kg (revision 8ae7e3d5), "
                  "https://creativecommons.org/licenses/by/4.0/. Changed: rows re-keyed to this project's reports and "
                  "mentions, names compared with this project's normalization; unreviewed."),
    "riwayat": ("CC0 1.0 for the authors' layer (identifications, parses, labels): Abdullah Ansar, \"Riwāyāt: A Corpus "
                "of Sunni and Shīʿī Hadith Transmission\", v1, Zenodo 2026, https://doi.org/10.5281/zenodo.23630501. "
                "Embedded texts and inherited annotations keep their sources' licences (hadith-kg CC BY 4.0; "
                "ThaqalaynData for the Shi'i texts and Thaqalayn narrator annotations)."),
}


def connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(pathlib.Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.execute("pragma cache_size = -262144")   # 256 MB page cache for the per-report lookups
    return connection


def progress(started: float, message: str) -> None:
    print(f"[{time.time() - started:7.1f}s] {message}", flush=True)


def work_ids() -> dict:
    registry = json.loads(WORK_REGISTRY.read_text(encoding="utf-8"))
    return {(w["tradition"], w["canonical_source"]): w["source_work_id"] for w in registry["source_works"]}


def iter_corpus():
    """Corpus rows with stripped tradition/source and the durable source_work_id filled from the registry."""
    works = work_ids()
    with gzip.open(CORPUS, "rt", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            row["tradition"] = row["tradition"].strip()
            row["source"] = row["source"].strip()
            row["record_id"] = row["record_id"].strip()
            row["source_work_id"] = row["source_work_id"].strip() or works.get((row["tradition"], row["source"]), "")
            yield row


def read_jsonl_gz(path: Path):
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def iter_projection(name: str):
    with open(PROJECTION / name, encoding="utf-8", newline="") as handle:
        yield from csv.DictReader(handle)
