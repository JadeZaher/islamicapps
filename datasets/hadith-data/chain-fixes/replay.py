"""Projection replay of accepted chain fixes (see AGENTS.md §replay). Imported by pg_export at integration; pure otherwise.

`accepted_overrides.jsonl.gz` holds one row per report whose chain the projection must take from an accepted fix. Each row
is bound to the report's `arabic_sha256` and to the SHA-256 of the exact text the readers read; a row whose binding no
longer holds is dropped, counted, and stays queued in the store (the fix is re-read, never silently re-applied).
"""

from __future__ import annotations

import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

OVERRIDES_FORMAT = "shura-chain-fix-override/1"
DEFAULT_PATH = Path(__file__).resolve().parent / "accepted_overrides.jsonl.gz"
EFFECTS = ("replace_routes", "set_status", "annotate")
STATUSES = ("read_by_model", "verified_by_reviewer")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def reader_text(layout: str, text_ar: str, sanad: str | None) -> str:
    """The exact string the readers read (chain-reader/tools/build_pilot.py `reader_text`)."""
    if layout == "chain_field_then_matn" and (sanad or "").strip():
        return f"{sanad.strip()}\n\n{text_ar}"
    return text_ar


def load_overrides(path: Path = DEFAULT_PATH) -> dict[str, dict]:
    """hadith id -> override row; an absent file means no fixes. Refuses a malformed or duplicated row."""
    if not path.is_file():
        return {}
    rows: dict[str, dict] = {}
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("format") != OVERRIDES_FORMAT or row.get("effect") not in EFFECTS or row.get("structure_status") not in STATUSES + (None,):
                raise ValueError(f"{path}:{number}: not a {OVERRIDES_FORMAT} row")
            if row["hadith_id"] in rows:
                raise ValueError(f"{path}:{number}: second override for {row['hadith_id']}")
            rows[row["hadith_id"]] = row
    return rows


def binding_problem(row: dict, text_ar: str, arabic_sha256: str, sanad: str | None) -> str | None:
    """Why an override no longer applies to the loaded report, or None."""
    if row["arabic_sha256"] != arabic_sha256 or sha256_text(text_ar) != arabic_sha256:
        return "arabic_changed"
    if sha256_text(reader_text(row["text_layout"], text_ar, sanad)) != row["reader_text_sha256"]:
        return "reader_text_changed"
    return None


def replay_branches(row: dict, old_branches: list[dict], counts: Counter) -> list[dict] | None:
    """Branches in export_postgres's shape for a `replace_routes` row; None when the row only sets a status or annotates.

    `origins` follow a kept name from the stored branch it was read from, so the K6 source-index claim and an edition
    identification move with it (the same mechanism the Sunni builder uses); a new name has no origin and gets no source claim.
    """
    if row["effect"] != "replace_routes":
        return None
    origin_of: dict[str, object] = {}
    for branch in old_branches:
        for position, (mention_id, _surface, _normalized) in enumerate(branch["mentions"]):
            origins = branch.get("origins")
            origin_of[mention_id] = origins[position] if origins else (branch["branch"], position)
    sanad_confidence = old_branches[0]["sanad_confidence"] if old_branches else None
    branches = []
    for chain in row["planned"]["chains"]:
        branches.append({
            "id": chain["id"], "branch": chain["branch"], "resolved": False, "extraction_method": chain["extraction_method"],
            "sanad_confidence": sanad_confidence, "suspension": chain["suspension"],
            "mentions": [(m["id"], m["surface_ar"], m["surface_normalized"]) for m in chain["mentions"]],
            "origins": [origin_of.get(m["kept_mention_id"]) if m["kept_mention_id"] else None for m in chain["mentions"]],
            "chain_fix": {"fix_id": row["fix_id"], "structure_status": row["structure_status"]},
        })
        counts["mentions_kept"] += sum(1 for m in chain["mentions"] if m["kept_mention_id"])
        counts["mentions_new"] += sum(1 for m in chain["mentions"] if not m["kept_mention_id"])
    counts["reports_replaced"] += 1
    return branches


def mention_id_map(row: dict) -> dict[str, str]:
    """Stored mention id -> new mention id for every kept name, so external claims follow the name; others are dropped and counted."""
    if row["effect"] != "replace_routes":
        return {}
    mapping: dict[str, str] = {}
    for chain in row["planned"]["chains"]:
        for mention in chain["mentions"]:
            if mention["kept_mention_id"] and mention["kept_mention_id"] not in mapping:
                mapping[mention["kept_mention_id"]] = mention["id"]
    return mapping
