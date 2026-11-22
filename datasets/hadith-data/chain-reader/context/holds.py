"""Deterministic holds: reasons a reading is queued for review instead of applied (documented in HOLDS.md).

    holds = compute_holds(reading, output, text, context, stored_surfaces)

A hold never changes a reading and never rejects it: the decide step reads `holds` and queues the report. Computed by the
tool, not by the reader. `stored_surfaces` (the archive's stored chain, as surface strings) is only used here, never shown to a reader.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from norm import fold_loose  # noqa: E402

MAX_ROUTES = 8
OPENING = re.compile(r"^(?:\d+ )?(?:و ?)?(?:عنه|عنها|عنهم|بهذا الاسناد|باسناده|باسنادهم|بالاسناد|عن )")   # on fold_loose text
JAMI = re.compile(r"جميعا|جميعاً|كلهم")
SEMICOLON = re.compile(r"[؛;]")


def opens_with_back_reference(text: str) -> bool:
    folded = fold_loose(text)
    return bool(OPENING.match(folded)) or "بهذا الاسناد" in folded[:160]


def _words(value: str) -> str:
    return " " + fold_loose(re.sub(r"^\s*و(?=\S)", "", value.strip())) + " "


def _name_in(needle: str, haystack: str) -> bool:
    return needle in haystack or haystack in needle


def compute_holds(reading: dict | None, output: dict, text: str, context: dict | None, stored_surfaces: list[str] | None = None) -> list[dict]:
    """The holds, each {"code", "detail"}; empty when the reading may go to the ordinary decide step."""
    context = context or {}
    holds: list[dict] = []

    def hold(code: str, detail: str) -> None:
        holds.append({"code": code, "detail": detail})

    if output.get("status") == "cannot_read_without_previous_report":
        hold("cannot_read_without_previous_report", "the reader could not read the report without the previous report's chain")
    if output.get("needs_ruling"):
        hold("needs_ruling", "the reader marked a point the owner's rulings do not settle (subject or source of the event, a title, a placement)")
    has_previous = bool(context.get("previous_reports") or context.get("parent_report"))
    if opens_with_back_reference(text) and not has_previous:
        hold("back_reference_without_previous_report", "the report opens with a back reference and the packet carried no previous report")
    if reading is None:
        return holds
    routes = reading["routes"]
    if len(routes) > MAX_ROUTES:
        hold("too_many_routes", f"{len(routes)} routes after expansion (limit {MAX_ROUTES})")
    region = text[: reading["matn_start"]] if reading["matn_start"] else text
    jami, semicolons = len(JAMI.findall(region)), len(SEMICOLON.findall(region))
    if jami >= 2 or (jami >= 1 and semicolons >= 1):
        hold("nested_jami", f"«جميعا» {jami} times and «؛» {semicolons} times in the chain: nested convergence, not read right in any of 5 audited reports")
    if semicolons >= 2:
        hold("nested_semicolon", f"{semicolons} semicolons in the chain: several isnads joined by «؛»")
    if stored_surfaces is not None:
        written = [_words(l["surface"]) for r in routes for l in r["links"] if l["start"] is not None]
        full = " " + fold_loose(text) + " "
        if not routes and stored_surfaces:
            hold("reading_empty_stored_has_links", f"the reading has no link; the stored chain has {len(stored_surfaces)}")
        dropped = []
        for surface in stored_surfaces:
            needle = _words(surface)
            present = re.search(r"(?:^|\s)و?" + re.escape(needle.strip()) + r"(?:\s|$)", full)    # whole words; an attached «و» is allowed
            if len(needle.strip()) < 2 or not present:
                continue                                           # a stored name the text does not write cannot be "dropped"
            if not any(_name_in(needle, w) for w in written):
                dropped.append(surface)
        if dropped and routes:
            hold("drops_stored_name", "the reading leaves out stored name(s) the text writes: " + "، ".join(dict.fromkeys(dropped))[:200])
    return holds
