"""v3.3 holds as the fix pipeline runs them: v3.3's holds with `route_at_most_half_the_longest` taken back to v3.2's un-narrowed rule (owner, 2026-11-22; AGENTS.md §pipeline correction).

    holds = compute_holds(reading, output, text, context, stored_surfaces, other_output)

Same signature and attributes as `holds_v3_3` (so `holds_v3_4` can take it as its base). Nothing else differs from v3.3.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
for path in (str(HERE), str(HERE.parent), str(HERE.parent / "v3_2")):
    if path not in sys.path:
        sys.path.insert(0, path)
import holds_v3_2  # noqa: E402
import holds_v3_3  # noqa: E402

CORRECTED_CODE = "route_at_most_half_the_longest"
ruling_flag_state = holds_v3_3.ruling_flag_state
faqih_route_statement = holds_v3_3.faqih_route_statement


def compute_holds(reading: dict | None, output: dict, text: str, context: dict | None, stored_surfaces: list[str] | None = None, other_output: dict | None = None) -> list[dict]:
    """v3.3's holds, the half-route hold decided by v3.2's `short_route_detail` (fires whatever the short route's last link)."""
    holds = [hold for hold in holds_v3_3.compute_holds(reading, output, text, context, stored_surfaces, other_output) if hold["code"] != CORRECTED_CODE]
    if reading is None:
        return holds
    detail = holds_v3_2.short_route_detail(reading["routes"])
    if detail:
        holds.append({"code": CORRECTED_CODE, "detail": detail + " (v3.2 rule: the v3.3 narrowing is not used by the pipeline)"})
    return holds
