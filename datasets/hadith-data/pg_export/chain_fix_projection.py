"""Replay accepted chain fixes in the projection (AGENTS.md §Chain fixes; design docs/review/chain-fix-pipeline.md §Reload).

Two steps. `apply_overrides` runs after every chain builder and before the structure gate: it checks each override's binding
and marks the `set_status` / `annotate` reports; `replace_routes` reports keep their rule-built branches through the whole
projection, so every other row (K6 alignment, external claims, kunya carriers) is what it was. `rewrite_rows` runs after
the mention loop and swaps those reports' rows for the fix's, by the database apply's own rule. An absent or empty overrides
file changes nothing.
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
                    hadith_text: dict[str, str], chain_field: dict[str, str], counts: Counter) -> dict[str, dict]:
    """Check every override's binding (a broken one is dropped and counted); mark status-only reports; return the
    `replace_routes` overrides, by hadith id, for `rewrite_rows`. Marked branches carry `chain_fix` (fix id, status)."""
    replacing: dict[str, dict] = {}
    for hadith_id, row in sorted(overrides.items()):
        info = hadith_info.get(hadith_id)
        if info is None:
            counts["dropped:report_not_loaded"] += 1
            continue
        problem = replay.binding_problem(row, hadith_text[hadith_id], info["arabic_sha256"], chain_field.get(hadith_id))
        if problem:
            counts[f"dropped:{problem}"] += 1
            continue
        if row["effect"] == "replace_routes":
            replacing[hadith_id] = row
            continue
        for branch in branches_by_hadith.get(hadith_id, []):
            branch["chain_fix"] = {"fix_id": row["fix_id"],
                                   "structure_status": row["structure_status"] if row["effect"] == "set_status" else None}
        counts["reports_status_set" if row["effect"] == "set_status" else "reports_annotated"] += 1
    return replacing


def rewrite_rows(replacing: dict[str, dict], chains: list[list], mentions: list[list], identity_rows: list[list], verbatim,
                 counts: Counter) -> tuple[list[list], list[list], list[list]]:
    """The projection's chain, mention and candidate rows with every replaced report's rows swapped for its fix's
    (`replay.rewrite_rows`). An inherited name reads its cited mention from the rows as built (a rule-checked chain, never
    one a fix rewrote: the engine holds otherwise)."""
    if not replacing:
        return chains, mentions, identity_rows
    candidates_by_mention: dict[str, list[list]] = {}
    for candidate in identity_rows:
        candidates_by_mention.setdefault(candidate[1], []).append(candidate)
    written = {mention[0]: (mention, candidates_by_mention.get(mention[0], [])) for mention in mentions}
    old_chains: dict[str, list[list]] = {}
    old_mentions: dict[str, list[list]] = {}
    old_candidates: dict[str, list[list]] = {}
    for rows, into in ((chains, old_chains), (mentions, old_mentions), (identity_rows, old_candidates)):
        for item in rows:
            if item[1 if rows is chains else 2] in replacing:
                into.setdefault(item[1 if rows is chains else 2], []).append(item)
    new_chains, new_mentions, new_candidates = [], [], []
    for hadith_id, row in sorted(replacing.items()):
        rewritten = replay.rewrite_rows(row, old_chains.get(hadith_id, []), old_mentions.get(hadith_id, []),
                                        old_candidates.get(hadith_id, []), written, verbatim, counts)
        new_chains += rewritten[0]
        new_mentions += rewritten[1]
        new_candidates += rewritten[2]
    keep = lambda rows, at: [item for item in rows if item[at] not in replacing]  # noqa: E731
    return (keep(chains, 1) + new_chains, keep(mentions, 2) + new_mentions, keep(identity_rows, 2) + new_candidates)
