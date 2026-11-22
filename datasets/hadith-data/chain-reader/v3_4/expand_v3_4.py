"""The tool side of a v3.4 chain reading: v3.2's expansion (v3_2/expand_v3_2.py, unchanged and imported) plus the saying label of owner ruling (b); see v3_4/AGENTS.md §sayings.

A group may carry `"saying": N` and `"saying_opens": "<the first words of that saying>"` (prompt v3.4 rule 4a). Then every non-variant group carries both, `shared_tail` is null,
groups of one saying name the same opening, and the openings stand in the text in the order of their numbers. Each route of the expanded reading carries `saying` (None when
the reading is unlabelled), each variant remark the saying of its group when labelled, and the reading carries `sayings`: [{"saying", "label", "opens", "start", "end", "groups"}].
Agreement (`readings_agree`) is v3.2's per saying: the same saying numbers, and each saying's routes agree; an unlabelled reading is one saying (None).
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
import expand_v3_2 as base  # noqa: E402  (v3.3 changed holds and triage only and imports this module unchanged; re-base here when a later expansion exists)
from norm_v3_2 import fold_v3  # noqa: E402

DERIVED_KINDS = base.DERIVED_KINDS
SAYING_KEYS = ("saying", "saying_opens")
OPENING_WORDS = (2, 12)                      # the prompt asks for 3 to 8 words; the tool accepts 2 to 12
ORDINALS = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth"}
variant_keys = base.variant_keys
route_keys = base.route_keys
restated_short_form = base.restated_short_form


def saying_label(number: int) -> str:
    """The page wording of a saying's chain: «Chain of the first saying»."""
    return f"Chain of the {ORDINALS.get(number, f'saying {number}')} saying" if number in ORDINALS else f"Chain of saying {number}"


def strip_sayings(output: object) -> object:
    """The output without saying labels (what v3.2's expansion and validator read)."""
    if not isinstance(output, dict) or not isinstance(output.get("groups"), list):
        return output
    result = copy.deepcopy(output)
    for group in result["groups"]:
        if isinstance(group, dict):
            for key in SAYING_KEYS:
                group.pop(key, None)
    return result


def labelled(output: object) -> bool:
    return isinstance(output, dict) and isinstance(output.get("groups"), list) and any(isinstance(g, dict) and any(k in g for k in SAYING_KEYS) for g in output["groups"])


def saying_shape_errors(output: object) -> list[str]:
    """Shape of the labels: both keys together, a whole number from 1, an opening of 2-12 words; all non-variant groups labelled when one is; no shared tail; one opening per number."""
    if not labelled(output):
        return []
    errors: list[str] = []
    openings: dict[int, str] = {}
    for g, group in enumerate(output["groups"]):
        if not isinstance(group, dict):
            continue
        has = [key in group for key in SAYING_KEYS]
        if not any(has):
            if not group.get("variant"):
                errors.append(f"saying: g{g} has no `saying`; when one group carries it, every non-variant group does (rule 4a)")
            continue
        if not all(has):
            errors.append(f"saying: g{g} needs both `saying` and `saying_opens`")
            continue
        number, opens = group["saying"], group["saying_opens"]
        if not isinstance(number, int) or isinstance(number, bool) or number < 1:
            errors.append(f"saying: g{g} `saying` must be a whole number from 1")
            continue
        if not isinstance(opens, str) or not (OPENING_WORDS[0] <= len(fold_v3(opens).split()) <= OPENING_WORDS[1]):
            errors.append(f"saying: g{g} `saying_opens` must be {OPENING_WORDS[0]} to {OPENING_WORDS[1]} words copied from the text")
            continue
        if number in openings and fold_v3(openings[number]) != fold_v3(opens):
            errors.append(f"saying: g{g} saying {number} names another opening than an earlier group of the same saying")
        openings.setdefault(number, opens)
    numbers = sorted(openings)
    for first, second in zip(numbers, numbers[1:]):
        if fold_v3(openings[first]) == fold_v3(openings[second]):
            errors.append(f"saying: sayings {first} and {second} name the same opening")
    if output.get("shared_tail") is not None:
        errors.append("saying: `shared_tail` must be null when groups carry `saying`; write the shared names in each group (rule 4a)")
    return errors


def _written(route: dict) -> list[dict]:
    return [l for l in route["links"] if l["start"] is not None and l["kind"] not in DERIVED_KINDS]


def locate_sayings(output: dict, reading: dict, text: str) -> tuple[list[dict], list[str], list[str]]:
    """(sayings, errors, notes). Each opening is looked for after its saying's last written link, then after its first link, then anywhere (the last two with a tool note)."""
    views = base.TextViews(text)
    by_number: dict[int, dict] = {}
    for g, group in enumerate(output["groups"]):
        if isinstance(group, dict) and "saying" in group:
            entry = by_number.setdefault(group["saying"], {"saying": group["saying"], "opens_written": group["saying_opens"], "groups": []})
            entry["groups"].append(g)
    errors, notes, sayings = [], [], []
    for number in sorted(by_number):
        entry = by_number[number]
        links = [l for r in reading["routes"] if r["group"] in entry["groups"] for l in _written(r)]
        links += [{"start": m["start"], "end": m["end"]} for m in reading.get("variant_remarks") or [] if m["group"] in entry["groups"]]
        tries = ([max(l["end"] for l in links), min(l["start"] for l in links)] if links else []) + [0]
        found = None
        for attempt, cursor in enumerate(tries):
            found, _, _ = views.locate(entry["opens_written"], cursor, None)
            if found:
                if attempt and links:
                    notes.append(f"saying {number}: the opening stands before the saying's last link")
                break
        if not found:
            errors.append(f"saying_opens_not_in_text: saying {number} {entry['opens_written']!r}")
            continue
        sayings.append({"saying": number, "label": saying_label(number), "opens": text[found[0]:found[1]], "start": found[0], "end": found[1], "groups": entry["groups"]})
    for first, second in zip(sayings, sayings[1:]):
        if second["start"] <= first["start"]:
            errors.append(f"saying_order: saying {second['saying']} opens at or before saying {first['saying']}; number the sayings in the text's order")
    return sayings, errors, notes


def expand(output: dict, text: str, context: dict | None = None) -> tuple[dict | None, list[str]]:
    """(reading, errors): v3.2's expansion of the output without labels, then the labels located and carried onto routes and remarks."""
    shape = saying_shape_errors(output)
    reading, errors = base.expand(strip_sayings(output), text, context)
    if shape or errors:
        return None, shape + errors
    reading["sayings"] = []
    for route in reading["routes"]:
        route["saying"] = None
    if not labelled(output):
        return reading, []
    sayings, errors, notes = locate_sayings(output, reading, text)
    if errors:
        return None, errors
    number_of = {g: s["saying"] for s in sayings for g in s["groups"]}
    for route in reading["routes"]:
        route["saying"] = number_of.get(route["group"])
    for remark in reading.get("variant_remarks") or []:
        if remark["group"] in number_of:
            remark["saying"] = number_of[remark["group"]]
    if len(sayings) == 1:
        notes.append(f"one saying labelled ({sayings[0]['saying']}): the label is kept")
    reading["sayings"] = sayings
    reading["tool_notes"] = sorted(set(reading["tool_notes"]) | set(notes))
    return reading, []


def by_saying(reading: dict) -> dict:
    """{saying number or None: the sub-reading of that saying's routes} (matn_start recomputed per saying)."""
    parts: dict = {}
    for route in reading["routes"]:
        parts.setdefault(route.get("saying"), []).append(route)
    result = {}
    for number, routes in parts.items():
        ends = [l["end"] for r in routes for l in r["links"] if l["end"] is not None and l["kind"] != "imam_in_text"]
        result[number] = {**reading, "routes": routes, "matn_start": max(ends) if ends else 0,
                          "variant_remarks": [m for m in reading.get("variant_remarks") or [] if m.get("saying") == number] if number is not None else list(reading.get("variant_remarks") or [])}
    return result


def canonical(reading: dict, include_bracketed: bool = False) -> frozenset:
    """Order-free form: the set of (saying, route keys)."""
    return frozenset((number, keys) for number, part in by_saying(reading).items() for keys in base.canonical(part, include_bracketed))


def readings_agree(first: dict, second: dict, include_bracketed: bool = False) -> bool:
    """The same saying numbers, and v3.2's `readings_agree` within each saying (an unlabelled reading is the single saying None)."""
    a, b = by_saying(first), by_saying(second)
    if set(a) != set(b):
        return False
    return all(base.readings_agree(a[n], b[n], include_bracketed) for n in a)
