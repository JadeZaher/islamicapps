"""Holds of the v3.4 tool: v3.3's holds (v3_3/holds_v3_3.py, imported; v3.2's when v3.3 is absent) with the shape holds judged per saying (v3_4/AGENTS.md §holds).

    holds = compute_holds(reading, output, text, context, stored_surfaces, other_output)

A reading that stores two sayings (owner ruling b) has routes that need not share a head or a tail: the shape holds that compare routes (SHAPE_CODES) run on each
saying's routes alone. Every other hold runs on the whole reading as before. Two holds are new:
`two_sayings_not_supported` (the reading labels routes by saying and the fix pipeline cannot store the label yet; the triage lifts it with `--sayings-supported`) and
`saying_route_starts_inside_another_route` (a later saying's route starts at a man who stands inside an earlier saying's route: the shared head was dropped, «قال بكير وحدثني ...»).
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_3"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
try:
    import holds_v3_3 as base  # noqa: E402
    BASE = "v3_3"
except ImportError:                                   # pragma: no cover - only before v3.3 exists
    import holds_v3_2 as base  # noqa: E402
    BASE = "v3_2"
from expand_v3_4 import by_saying, route_keys  # noqa: E402

ruling_flag_state = base.ruling_flag_state
faqih_route_statement = getattr(base, "faqih_route_statement", lambda text, context: None)
# holds that compare the routes of one reading with each other: judged inside one saying only
SHAPE_CODES = frozenset({"route_at_most_half_the_longest", "routes_end_at_different_links", "route_ends_inside_another_route", "first_links_split_by_comma",
                         "semicolon_in_multi_route_isnad", "nested_jami", "nested_semicolon"})


def head_dropped(reading: dict) -> str | None:
    """A route of a later saying whose first written name stands inside (not at the head of) a route of an earlier saying."""
    parts = {n: p for n, p in by_saying(reading).items() if n is not None}
    numbers = sorted(parts)
    for index, number in enumerate(numbers[1:], start=1):
        earlier = [keys for n in numbers[:index] for keys in route_keys(parts[n])]
        for keys in route_keys(parts[number]):
            if keys and any(keys[0] in other[1:] for other in earlier):
                return f"saying {number}: a route starts at «{keys[0]}», who stands inside the chain of an earlier saying: the shared head was probably dropped («قال X وحدثني Y» keeps it)"
    return None


def compute_holds(reading: dict | None, output: dict, text: str, context: dict | None, stored_surfaces: list[str] | None = None, other_output: dict | None = None) -> list[dict]:
    """The holds, each {"code", "detail"}."""
    if reading is None or not reading.get("sayings"):
        return base.compute_holds(reading, output, text, context, stored_surfaces, other_output)
    holds = [h for h in base.compute_holds(reading, output, text, context, stored_surfaces, other_output) if h["code"] not in SHAPE_CODES]
    for number, part in sorted(by_saying(reading).items(), key=lambda item: (item[0] is None, item[0] or 0)):
        for hold in base.compute_holds(part, output, text, context, stored_surfaces, other_output):
            if hold["code"] in SHAPE_CODES:
                holds.append({"code": hold["code"], "detail": f"saying {number}: {hold['detail']}"})
    dropped = head_dropped(reading)
    if dropped:
        holds.append({"code": "saying_route_starts_inside_another_route", "detail": dropped})
    holds.append({"code": "two_sayings_not_supported", "detail": "the reading stores the chains of " + ", ".join(s["label"].replace("Chain of the ", "") for s in reading["sayings"])
                  + "; the fix pipeline cannot yet label a route with its saying"})
    return holds
