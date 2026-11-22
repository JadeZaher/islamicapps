"""Replay accepted chain fixes in the projection (AGENTS.md §Chain fixes; design docs/review/chain-fix-pipeline.md §Reload).

Runs after every chain builder and before the structure gate. An absent or empty overrides file changes nothing.
"""

from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHAIN_FIXES_DIR = HERE.parent / "chain-fixes"
REPLAY_PATH = CHAIN_FIXES_DIR / "replay.py"
OVERRIDES_PATH = CHAIN_FIXES_DIR / "accepted_overrides.jsonl.gz"

_spec = importlib.util.spec_from_file_location("chain_fix_replay", REPLAY_PATH)
replay = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(replay)


def apply_overrides(overrides: dict[str, dict], branches_by_hadith: dict[str, list[dict]], hadith_info: dict[str, dict],
                    hadith_text: dict[str, str], chain_field: dict[str, str], external, counts: Counter) -> None:
    """Replace or mark the branches of every report an accepted fix names; a broken binding drops the row (counted).

    Replaced branches carry `chain_fix` (fix id and status): the structure gate is not run on them and their status is the fix's.
    External claims on a kept name follow it to its new mention id; claims on a dropped name are dropped and counted.
    """
    for hadith_id, row in sorted(overrides.items()):
        info = hadith_info.get(hadith_id)
        if info is None:
            counts["dropped:report_not_loaded"] += 1
            continue
        problem = replay.binding_problem(row, hadith_text[hadith_id], info["arabic_sha256"], chain_field.get(hadith_id))
        if problem:
            counts[f"dropped:{problem}"] += 1
            continue
        old = sorted(branches_by_hadith.get(hadith_id, []), key=lambda branch: branch["branch"])
        if row["effect"] == "replace_routes":
            new = replay.replay_branches(row, old, counts)
            mapping = replay.mention_id_map(row)
            old_ids = [mention_id for branch in old for mention_id, _, _ in branch["mentions"]]
            moved, dropped = external.remap_report_claims(old_ids, mapping)
            counts["external_claims_moved"] += moved
            counts["external_claims_dropped"] += dropped
            if new:
                branches_by_hadith[hadith_id] = new
            else:
                branches_by_hadith.pop(hadith_id, None)
            continue
        for branch in old:
            branch["chain_fix"] = {"fix_id": row["fix_id"],
                                   "structure_status": row["structure_status"] if row["effect"] == "set_status" else None}
        counts["reports_status_set" if row["effect"] == "set_status" else "reports_annotated"] += 1
