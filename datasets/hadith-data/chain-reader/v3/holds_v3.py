"""Deterministic holds of the v3 tool: reasons a reading is queued for review instead of applied (copy of context/holds.py; see v3/AGENTS.md §holds, v3/HOLDS.md).

    holds = compute_holds(reading, output, text, context, stored_surfaces, other_output)

A hold never changes a reading and never rejects it. Changes from v2: `drops_stored_name` removed (it fired on 23 agreed readings, 20 right, and queued
exactly the corrections the pipeline exists for); added `routes_end_at_different_links`, `back_reference_only`, `second_isnad_not_same_saying`;
`needs_ruling` holds only when BOTH readers set the flag (`other_output` is the other pass's output); back-reference detection widened.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from expand_v3 import DERIVED_KINDS  # noqa: E402
from norm_v3 import fold_v3, link_key  # noqa: E402

MAX_ROUTES = 8
# On the folded text (marks and hamza folded, punctuation one space). Keep in step with OPENING in v3/build_context_v3.cjs; tests/backref_cases.json runs both.
OPENING = re.compile(
    r"^(?:\d+ )?(?:ح )?(?:و ?)?(?:"
    r"(?P<pronoun>عنهما|عنهم|عنها|عنه)(?= |$)|"
    r"(?P<isnad_phrase>بهذا (?:الاسناد|السند)|بنفس (?:الاسناد|السند)|بالاسناد|باسناده|باسنادهم|باسنادها|بالسند|بسنده|بسندهم)(?= |$)|"
    r"(?P<bare_an>عن )"
    r")")
FIRST_160 = re.compile(r"بهذا (?:الاسناد|السند)")
JAMI = re.compile(r"جميعا|كلهم")
SEMICOLON = re.compile(r"[؛;]")
VERBS = re.compile(r"(?:^| )(?:حدثنا|حدثني|اخبرنا|اخبرني|انبانا|انبانا|سمعت|ثنا|روي|حدثه|اخبره)(?= )")
POEM_CUES = ("انشد", "شعر", "قصيد", "بيت", "ابيات", "الراجز", "حكي", "حكاي")
SECOND_ISNAD_GAP = 60                                  # folded characters of saying between the first isnad and a later group


def folded(text: str) -> str:
    return fold_v3(text)


def opens_with_back_reference(text: str) -> bool:
    """The report opens with a pronoun or a phrase that points back (عنه، وعنه، وبهذا الإسناد، وبإسناده، بالإسناد الأول، و/عن …) or says «بهذا الإسناد» in its first 160 letters."""
    value = folded(text)
    return bool(OPENING.match(value)) or bool(FIRST_160.search(value[:160]))


def opening_form(text: str) -> str | None:
    """Which opening: pronoun | isnad_phrase | bare_an | in_first_160 | None (for the corpus census)."""
    value = folded(text)
    match = OPENING.match(value)
    if match:
        return match.lastgroup
    return "in_first_160" if FIRST_160.search(value[:160]) else None


def written_chain(item: dict) -> bool:
    """A previous report carries names: the packet says so (`has_written_chain`), else its chain text does not itself open with a back reference and has a transmission verb or two «عن»."""
    if "has_written_chain" in item:
        return bool(item["has_written_chain"])
    value = folded(item.get("chain_text") or "")
    return not OPENING.match(value) and (bool(VERBS.search(" " + value)) or value.count(" عن ") >= 1 and len(value.split()) >= 5)


def has_usable_previous(context: dict) -> bool:
    return bool(context.get("parent_report")) or any(written_chain(item) for item in context.get("previous_reports") or [])


def _written(route: dict) -> list[dict]:
    return [l for l in route["links"] if l["kind"] not in DERIVED_KINDS]


def route_link_keys(route: dict) -> tuple[str, ...]:
    """Keys of the route's written links, a trailing back reference and derived links left out."""
    return tuple(link_key(l["surface"]) for l in _written(route) if l["kind"] != "back_reference")


def unexplained_end_signatures(routes: list[dict]) -> set[frozenset]:
    """Last-link signatures of routes that should end alike. Routes with the same links but the last form one level of co-transmitters at the end
    («عن أبي جعفر وأبي عبد الله»; «|» alternatives) and count as one signature; every other route is its own signature."""
    by_prefix: dict[tuple[str, ...], set[str]] = {}
    keyed = [route_link_keys(r) for r in routes]
    for keys in keyed:
        if keys:
            by_prefix.setdefault(keys[:-1], set()).add(keys[-1])
    signatures: set[frozenset] = set()
    for keys in keyed:
        if keys:
            signatures.add(frozenset(by_prefix[keys[:-1]]))
    # two groups of alternatives that name the same ends are one signature
    return signatures


def compute_holds(reading: dict | None, output: dict, text: str, context: dict | None, stored_surfaces: list[str] | None = None, other_output: dict | None = None) -> list[dict]:
    """The holds, each {"code", "detail"}; empty when the reading may go to the ordinary decide step."""
    context = context or {}
    holds: list[dict] = []

    def hold(code: str, detail: str) -> None:
        holds.append({"code": code, "detail": detail})

    if output.get("status") == "cannot_read_without_previous_report":
        hold("cannot_read_without_previous_report", "the reader could not read the report without the previous report's chain")
    if output.get("needs_ruling") and other_output is not None and other_output.get("needs_ruling"):
        hold("needs_ruling", "both readers marked a point the rules do not settle (subject or source of the event, a placement)")
    opens = opens_with_back_reference(text)
    usable = has_usable_previous(context)
    if opens and not usable:
        hold("back_reference_without_previous_report", "the report opens with a back reference and the packet carried no previous report with a written chain")
    if reading is None:
        return holds
    routes = reading["routes"]
    if len(routes) > MAX_ROUTES:
        hold("too_many_routes", f"{len(routes)} routes after expansion (limit {MAX_ROUTES})")
    region = text[: reading["matn_start"]] if reading["matn_start"] else text
    jami, semicolons = len(JAMI.findall(folded(region))), len(SEMICOLON.findall(region))
    if jami >= 2 or (jami >= 1 and semicolons >= 1):
        hold("nested_jami", f"«جميعا» {jami} times and «؛» {semicolons} times in the chain: nested convergence, not read right in any of 5 audited reports")
    if semicolons >= 2:
        hold("nested_semicolon", f"{semicolons} semicolons in the chain: several isnads joined by «؛»")
    if routes and all(l["kind"] in ("back_reference", "compiler_head") for r in routes for l in r["links"]):
        hold("back_reference_only", "the reading is made only of back references")
    elif OPENING.match(folded(text)) and usable and routes and not any(l["kind"] == "inherited" for r in routes for l in r["links"]) and output.get("status") == "read":
        hold("back_reference_only", "the text opens with a back reference and a previous report with names was supplied, but no inherited link was taken")
    ends = unexplained_end_signatures([r for r in routes if not r.get("variant") and _in_first_isnad_region(r, routes, text)])
    if len(ends) > 1:
        hold("routes_end_at_different_links", "routes of one report end at different last links without the text saying so: " + "؛ ".join(sorted("/".join(sorted(e)) for e in ends))[:200])
    poem = _second_isnad_not_same_saying(routes, text)
    if poem:
        hold("second_isnad_not_same_saying", poem)
    if stored_surfaces is not None and not routes and stored_surfaces:
        hold("reading_empty_stored_has_links", f"the reading has no link; the stored chain has {len(stored_surfaces)}")
    return holds


def _first_start(route: dict) -> int | None:
    starts = [l["start"] for l in _written(route) if l["start"] is not None]
    return min(starts) if starts else None


def _last_end(route: dict) -> int | None:
    ends = [l["end"] for l in _written(route) if l["end"] is not None]
    return max(ends) if ends else None


def _group_spans(routes: list[dict]) -> dict[int, tuple[int, int]]:
    spans: dict[int, tuple[int, int]] = {}
    for route in routes:
        start, end = _first_start(route), _last_end(route)
        if start is None or end is None:
            continue
        low, high = spans.get(route.get("group", 0), (start, end))
        spans[route.get("group", 0)] = (min(low, start), max(high, end))
    return spans


def _in_first_isnad_region(route: dict, routes: list[dict], text: str) -> bool:
    """False for a route of a later group that begins well after the first group's last name: a second isnad after the saying may end elsewhere."""
    spans = _group_spans(routes)
    group = route.get("group", 0)
    if group == min(spans, default=0) or group not in spans:
        return True
    first_end = max(end for g, (start, end) in spans.items() if g == min(spans))
    start = spans[group][0]
    return start <= first_end or len(fold_v3(text[first_end:start])) <= SECOND_ISNAD_GAP


def _second_isnad_not_same_saying(routes: list[dict], text: str) -> str | None:
    """A later group that opens after the saying with a poem or story cue («وأنشدني …») is not a route of the same saying (cue words only: a poem, not every anecdote)."""
    spans = _group_spans(routes)
    if len(spans) < 2:
        return None
    first = min(spans)
    first_end = spans[first][1]
    for group, (start, _) in spans.items():
        if group == first or any(r.get("variant") for r in routes if r.get("group") == group):
            continue
        before = fold_v3(text[max(first_end, start - 70):start])
        if len(fold_v3(text[first_end:start])) > SECOND_ISNAD_GAP and any(cue in before for cue in POEM_CUES):
            return f"group {group} opens after the saying with a poem or story cue: «{before[-60:]}»"
    return None


def ruling_flag_state(output_a: dict | None, output_b: dict | None) -> str | None:
    """`both` holds the report; `a_only` / `b_only` go to the review sample, not to a hold; None when neither set it."""
    a, b = bool(output_a and output_a.get("needs_ruling")), bool(output_b and output_b.get("needs_ruling"))
    return "both" if a and b else "a_only" if a else "b_only" if b else None
