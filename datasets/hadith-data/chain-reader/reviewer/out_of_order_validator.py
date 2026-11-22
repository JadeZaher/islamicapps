"""Reviewer-side copy of the reader validator that also accepts a connecting chain written AFTER the names it connects to (reviewer/FORMAT_GAP.md). The reader toolchain is untouched.

Extension (opt-in, exactly two new keys): an item may carry `"out_of_order": true`, and its group then carries `"connecting_span": "<exact words of the text>"`.
Levels still run in route order (compiler's shaykh to last link). Every item of the first flagged level, and the levels after it, are written BEFORE the span (in text order among
themselves); every level before the flagged one is written INSIDE the span. Without the two keys the behaviour is v3.4's validator, unchanged.
    «وروى ابن مهدي، عن عكرمة، نحو … حدثنا بذلك إسحاق بن منصور حدثنا ابن مهدي»  ->  levels [إسحاق] [ابن مهدي (occurrence 2)] [عكرمة, out_of_order], connecting_span «حدثنا بذلك … ابن مهدي»
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_4"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
import expand_v3_2 as base_expand  # noqa: E402
import expand_v3_4 as expand_module  # noqa: E402
import validate_v3_4 as base_validate  # noqa: E402


def flagged(output: object) -> bool:
    groups = output.get("groups") if isinstance(output, dict) else None
    return isinstance(groups, list) and any(isinstance(g, dict) and ("connecting_span" in g or any(isinstance(i, dict) and "out_of_order" in i for lv in g.get("levels") or [] if isinstance(lv, list) for i in lv)) for g in groups)


def shape_errors(output: dict) -> list[str]:
    errors = []
    for g, group in enumerate(output.get("groups") or []):
        if not isinstance(group, dict):
            continue
        levels = [lv for lv in group.get("levels") or [] if isinstance(lv, list)]
        marks = [[isinstance(i, dict) and i.get("out_of_order") is True for i in lv] for lv in levels]
        bad_values = [i for lv in levels for i in lv if isinstance(i, dict) and "out_of_order" in i and i["out_of_order"] is not True]
        flagged_levels = [n for n, m in enumerate(marks) if any(m)]
        has_span = "connecting_span" in group
        if bad_values:
            errors.append(f"out_of_order: g{g} out_of_order is true or absent")
        if not flagged_levels and has_span:
            errors.append(f"out_of_order: g{g} has a connecting_span but no out_of_order item")
        if not flagged_levels:
            continue
        if group.get("variant"):
            errors.append(f"out_of_order: g{g} a variant remark has no route to connect")
        if len(flagged_levels) != 1:
            errors.append(f"out_of_order: g{g} flags {len(flagged_levels)} levels; exactly one level starts the part written before the span")
        elif flagged_levels[0] == 0:
            errors.append(f"out_of_order: g{g} the first level cannot be out of order (nothing is connected to it)")
        elif not all(marks[flagged_levels[0]]):
            errors.append(f"out_of_order: g{g}l{flagged_levels[0]} every item of the flagged level carries out_of_order")
        if not (isinstance(group.get("connecting_span"), str) and group["connecting_span"].strip()):
            errors.append(f"out_of_order: g{g} needs connecting_span, the exact words of the text that connect to the flagged level")
    return errors


def proxy(output: dict) -> tuple[dict, dict[int, dict]]:
    """The output in text order for the base tool (flagged levels moved first, keys removed), and per group: {level count before the flag, the span}."""
    result, info = copy.deepcopy(output), {}
    for g, group in enumerate(result["groups"]):
        levels = group["levels"]
        flagged_at = next((n for n, lv in enumerate(levels) if any(isinstance(i, dict) and i.get("out_of_order") is True for i in lv)), None)
        span = group.pop("connecting_span", None)
        for lv in levels:
            for i in lv:
                if isinstance(i, dict):
                    i.pop("out_of_order", None)
        if flagged_at is not None:
            info[g] = {"connector_levels": flagged_at, "span": span}
            group["levels"] = levels[flagged_at:] + levels[:flagged_at]
    return result, info


def expand(output: dict, text: str, context: dict | None = None) -> tuple[dict | None, list[str]]:
    """Like expand_v3_4.expand; flagged groups' routes run connector first, then the part written earlier (those links carry `out_of_order: True`)."""
    if not flagged(output):
        return expand_module.expand(output, text, context)
    errors = shape_errors(output)
    if errors:
        return None, errors
    ordered, info = proxy(output)
    reading, expand_errors = expand_module.expand(ordered, text, context)
    if reading is None or expand_errors:
        return None, expand_errors
    for g, detail in info.items():
        span = detail["span"]
        at = text.find(span)
        if at < 0:
            errors.append(f"connecting_span: g{g} {span[:40]!r} is not an exact substring of the text")
            continue
        low, high = at, at + len(span)
        for route in [r for r in reading["routes"] if r.get("group") == g]:
            written = [l for l in route["links"] if l["start"] is not None]
            earlier = [l for l in written if l["end"] <= low]
            inside = [l for l in written if l["start"] >= low]
            if len(earlier) + len(inside) != len(written) or not inside or not earlier:
                errors.append(f"out_of_order: g{g} the levels before the flag must stand inside the span and the flagged levels before it: {[l['surface'] for l in written]}")
                break
            if any(l["end"] > high for l in inside):
                errors.append(f"out_of_order: g{g} a connecting link lies after the span: {[l['surface'] for l in inside if l['end'] > high]}")
                break
            derived = [l for l in route["links"] if l["start"] is None]
            head = [l for l in derived if l["kind"] == "compiler_head"]
            rest = [l for l in derived if l["kind"] != "compiler_head"]
            route["links"] = head + rest + inside + [{**l, "out_of_order": True} for l in earlier]
            route["connecting_span"] = span
    return (None, errors) if errors else (reading, [])


def validate_chain(output: object, text: str, expected_id: str | None = None, context: dict | None = None) -> list[str]:
    """Error strings `code: detail`; empty means accepted. Unflagged outputs are validated exactly as validate_v3_4 does."""
    if not flagged(output):
        return base_validate.validate_chain(output, text, expected_id, context)
    if not isinstance(output, dict):
        return ["shape: output is not a JSON object"]
    errors = shape_errors(output)
    if errors:
        return errors
    ordered, _ = proxy(output)
    errors = base_validate.validate_chain(ordered, text, expected_id, context)
    if errors:
        return errors
    return expand(output, text, context)[1]
