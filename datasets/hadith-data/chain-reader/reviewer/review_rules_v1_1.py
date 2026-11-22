"""Reviewer v1.1: the decision rule after the pilot's adjudication (reviewer/README-v1_1.md §2). v1's vocabulary and hold table are imported (review_rules.py, untouched); this file adds
the rule's changes: a correction equal to the reading is a confirmation; an applied reading is labelled "disputed", never reverted by a correction or a referral; keep_stored reverts only
when the stored chain differs; a human decision always wins; a referral may carry a partial correction; `pending` (cleared, not yet applied) behaves as held without holds."""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_4"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
from review_rules import DECISIONS, HOLDS as HOLDS_V1, JOBS_FORMAT, OUTPUT_FORMAT, PACKET_FORMAT, REVIEWER_MODEL, SPECIALIST, UNCERTAINTY, VARIANT_VERDICTS  # noqa: E402,F401

PROMPT_VERSION = "1.1.0"
STATUSES = ("held", "applied", "pending")          # pending: the tool cleared the reading and it waits to be applied (not yet shown)

# v1.1 adds one code: a reading the tool cleared but an earlier check set aside for a reason no rule can name. The reviewer may clear it (it decides on the Arabic).
HOLDS: dict[str, tuple[str, bool]] = {**HOLDS_V1,
    "withheld_by_earlier_check": ("an earlier reading of this report set the reading aside before it was applied; the reason is not given: decide it on the Arabic", True)}

LABEL_AI_REVIEWED = "Read by model; AI reviewed (claude-opus-5-5), <date>; awaiting human review"
LABEL_DISPUTED = "Read by model; disputed by AI review (claude-opus-5-5), <date>; awaiting second review"
LABEL_CORRECTED = "Corrected by AI review (claude-opus-5-5, 2 runs), <date>; awaiting human review"

ACTION_CLASS = {"apply_reading": "apply", "apply_reader_a": "apply", "apply_reader_b": "apply", "apply_correction": "apply", "apply_no_chain": "apply",
                "label_ai_reviewed": "label", "label_disputed": "label", "queue_for_human": "queue", "keep_held": "hold", "discard_reading": "hold",
                "revert_to_stored": "revert", "human_decides": "human"}


def plain(code: str) -> str:
    return HOLDS.get(code, (f"tool hold «{code}»", False))[0]


def clearable(code: str) -> bool:
    """Unknown codes are not clearable."""
    return HOLDS.get(code, ("", False))[1]


def blocking_codes(codes: list[str]) -> list[str]:
    return [c for c in codes if not clearable(c)]


def needs_second_pass(decision: str, correction_is: str | None, agreed_empty: bool, has_correction: bool) -> bool:
    """A correction a second independent review must repeat: confirm_with_correction that is not the readers' own routes, or no_chain against a reading with routes. A referral's partial correction is never applied without a human, so it gets no second pass."""
    if decision == "confirm_with_correction":
        return correction_is is None
    return decision == "no_chain" and not agreed_empty


def effective_decision(decision: str, readers_agree: bool, correction_is: str | None) -> str:
    """Rule (a): a correction whose routes equal the readers' reading (after the tool's folds) is a confirmation (or the preference for the reader it equals)."""
    if decision == "confirm_with_correction" and correction_is == "reading" and readers_agree:
        return "confirm_reading"
    if decision == "confirm_with_correction" and correction_is in ("reader_a", "reader_b") and not readers_agree:
        return "prefer_" + correction_is
    return decision


def outcome(status: str, decision: str, codes: list[str], readers_agree: bool, agreed_empty: bool, second_run_agrees: bool | None, *, stored_equals_reading: bool | None = None,
            correction_is: str | None = None, has_correction: bool = False, human: str | None = None) -> str:
    """What the pipeline does with one VALID reviewer decision. `second_run_agrees`: None when no second run exists. `correction_is`: "reading" / "reader_a" / "reader_b" when the corrected routes
    equal that reading after the folds, else None. `stored_equals_reading`: None when unknown. `human`: "confirmed" / "rejected" when a person has decided (always wins).
    Returns one of ACTION_CLASS's keys."""
    if human:
        return "human_decides"
    decision = effective_decision(decision, readers_agree, correction_is)
    if status in ("held", "pending"):
        if blocking_codes(codes):
            return "keep_held"
        if decision == "refer_to_human":
            return "queue_for_human" if has_correction else "keep_held"
        if decision == "confirm_reading":
            return "apply_reading" if readers_agree else "queue_for_human"
        if decision in ("prefer_reader_a", "prefer_reader_b"):
            return ("apply_" + decision[len("prefer_"):]) if not readers_agree else "queue_for_human"
        if decision == "no_chain" and readers_agree and agreed_empty:
            return "apply_reading"
        if decision in ("confirm_with_correction", "no_chain"):
            return ("apply_correction" if decision == "confirm_with_correction" else "apply_no_chain") if second_run_agrees else "queue_for_human"
        if decision == "keep_stored":
            return "discard_reading"
        raise ValueError(decision)
    if status == "applied":
        if decision == "confirm_reading" or (decision == "no_chain" and agreed_empty):
            return "label_ai_reviewed"
        if decision in ("confirm_with_correction", "no_chain") and second_run_agrees:
            return "apply_correction" if decision == "confirm_with_correction" else "apply_no_chain"
        if decision == "keep_stored" and stored_equals_reading is False:
            return "revert_to_stored"
        return "label_disputed"
    raise ValueError(status)


# ---- comparisons the rule needs (the same folds the reader tool uses) ----

def _route_keys(routes: list[dict], drop_inherited: bool) -> frozenset:
    from norm_v3_2 import link_key
    keyed = set()
    for route in routes:
        links = [l for l in route["links"] if l["kind"] != "compiler_head" and not (drop_inherited and l["kind"] == "inherited") and l["kind"] != "back_reference"]
        keys: list[str] = []
        for link in links:
            key = link_key(link["surface"])
            if key and (not keys or keys[-1] != key or len(key.split()) < 2):
                keys.append(key)
        keyed.add(tuple(keys))
    return frozenset(keyed)


def stored_equals_reading(item: dict) -> bool | None:
    """The stored chain's branches equal the (reader A's) reading's routes after the folds, derived links aside. None when the reading has no valid routes."""
    from norm_v3_2 import link_key
    block = (item.get("readers") or {}).get("A") or {}
    if not block.get("valid") or block.get("routes") is None:
        return None
    stored = set()
    for chain in item.get("stored_chain") or []:
        keys: list[str] = []
        for surface in chain.get("surfaces") or []:
            key = link_key(surface)
            if key and (not keys or keys[-1] != key or len(key.split()) < 2):
                keys.append(key)
        stored.add(tuple(keys))
    stored = frozenset(stored)
    return stored == _route_keys(block["routes"], False) or stored == _route_keys(block["routes"], True)


def correction_is(item: dict, corrected: dict | None) -> str | None:
    """"reading" when the corrected routes equal the agreed reading, "reader_a" / "reader_b" when the readers differ and they equal that reader's, else None (also None if the correction does not expand)."""
    if not isinstance(corrected, dict):
        return None
    import expand_v3_4
    reading, errors = expand_v3_4.expand(corrected, item["text"], item.get("context"))
    if errors or reading is None:
        return None
    for tag in ("A", "B"):
        block = (item.get("readers") or {}).get(tag) or {}
        if not block.get("valid") or block.get("routes") is None:
            continue
        other = _packet_reading(block)
        if expand_v3_4.readings_agree(reading, other) and _inherited_keys(reading) == _inherited_keys(other):
            return "reading" if item.get("readers_agree") else "reader_" + tag.lower()
    return None


def _packet_reading(block: dict) -> dict:
    """A packet's reader block as a reading the comparison functions accept (links carry no offsets there)."""
    routes = [{**route, "links": [{**link, "start": None, "end": None} for link in route["links"]]} for route in block["routes"]]
    return {"routes": routes, "variant_remarks": [], "matn_start": 0}


def _inherited_keys(reading: dict) -> frozenset:
    """The names a reading inherits from an earlier report. The tool's agreement ignores `inherited` links (derived), so two readings that inherit different men would "agree": a correction that changes
    only whom the report inherits (pilot cr1-6dfc38) is a real correction, never a confirmation."""
    from norm_v3_2 import link_key
    return frozenset(link_key(l["surface"]) for r in reading["routes"] for l in r["links"] if l["kind"] == "inherited")
