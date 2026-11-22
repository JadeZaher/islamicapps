"""Deterministic holds of the v3.1 tool: reasons a reading is queued for review instead of applied (copy of v3/holds_v3.py; see v3_1/AGENTS.md §holds, v3_1/HOLDS.md).

    holds = compute_holds(reading, output, text, context, stored_surfaces, other_output)

A hold never changes a reading and never rejects it. Changes from v3 (owner rulings of 2026-11-22, v3_1/AGENTS.md): the asker is a link (`asker_not_a_link`); an agreed EMPTY reading is applicable
as "no chain by reading" unless `empty_reading_transmission_name` or `empty_reading_unsettled_opening` holds it (the blanket `reading_empty_stored_has_links` is gone); `routes_end_at_different_links`
does not fire on an abbreviated route or on independent isnads; openings that lean on the earlier report (asker with a pronoun, «وقال عليه السلام», «وعن X») are back references.
Changes from v2: `drops_stored_name` removed (it fired on 23 agreed readings, 20 right, and queued
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
from expand_v3_1 import DERIVED_KINDS  # noqa: E402
from norm_v3_1 import fold_chars, fold_v3, link_key  # noqa: E402

MAX_ROUTES = 8
# On the folded text (marks and hamza folded, punctuation one space). Keep in step with OPENING in v3/build_context_v3.cjs; tests/backref_cases.json runs both.
OPENING = re.compile(
    r"^(?:\d+ )?(?:ح )?(?:و ?)?(?:"
    r"(?P<pronoun>عنهما|عنهم|عنها|عنه)(?= |$)|"
    r"(?P<isnad_phrase>بهذا (?:الاسناد|السند)|بنفس (?:الاسناد|السند)|بالاسناد|باسناده|باسنادهم|باسنادها|بالسند|بسنده|بسندهم)(?= |$)|"
    r"(?P<bare_an>عن )"
    r")")
FIRST_160 = re.compile(r"بهذا (?:الاسناد|السند)")
# v3.1 openings that lean on the previous report or name an asker (owner rulings 1 and 2). Same folded text; keep in step with backref_lib_v3_1.cjs (tests/opening_cases_v3_1.json runs both).
LEAD = r"^(?:[0-9]+ )?(?:ح )?(?:و ?)?"
ASKER = re.compile(LEAD + r"(?P<verb>ساله|سال|كتب|شكا|شكي|سيل)(?= |$)(?P<rest>.*)")
IMPLICIT_SPEAKER = re.compile(LEAD + r"(?:قال|قضي) (?:عليه|عليهما|عليهم|ع) ?(?:السلام)?(?= |$)")
FIRST_PERSON = re.compile(LEAD + r"قال قلت(?= |$)")
COLLECTIVE = re.compile(LEAD + r"روي عن (?:الايمه|الائمه)(?= |$)")
INHERITING = ("pronoun", "isnad_phrase", "bare_an", "asker_pronoun", "implicit_speaker")    # the earlier report supplies what the opening leaves out
JAMI = re.compile(r"جميعا|كلهم")
SEMICOLON = re.compile(r"[؛;]")
VERBS = re.compile(r"(?:^| )(?:حدثنا|حدثني|اخبرنا|اخبرني|انبانا|انبانا|سمعت|ثنا|روي|حدثه|اخبره)(?= )")
POEM_CUES = ("انشد", "شعر", "قصيد", "بيت", "ابيات", "الراجز", "حكي", "حكاي")
SECOND_ISNAD_GAP = 60                                  # folded characters of saying between the first isnad and a later group


def folded(text: str) -> str:
    return fold_v3(text)


def asker_form(value: str) -> str | None:
    """asker_pronoun («وسأله X», «وكتب إليه», «وسئل: عن …»: the one asked is not named) | asker_named («وسأل X Y», «وكتب X إلى Y») | None; `value` is the folded text."""
    match = ASKER.match(value)
    if not match:
        return None
    verb, rest = match.group("verb"), match.group("rest").strip().split()
    following = rest[0] if rest else ""
    if verb == "ساله" or verb == "سيل":
        return "asker_pronoun" if verb == "ساله" or following in ("", "عن") else "asker_named"     # «وسئل الصادق عليه السلام عن …» names the one asked
    if verb in ("كتب", "شكا", "شكي"):
        return "asker_pronoun" if following in ("اليه", "اليها") else "asker_named"
    return "asker_pronoun" if following in ("", "عن") else "asker_named"


def opening_class(text: str) -> str | None:
    """The opening of a report: pronoun | isnad_phrase | bare_an | asker_pronoun | asker_named | implicit_speaker | first_person | collective | None (v3's three back references first)."""
    value = folded(text)
    match = OPENING.match(value)
    if match:
        return match.lastgroup
    form = asker_form(value)
    if form:
        return form
    for name, pattern in (("implicit_speaker", IMPLICIT_SPEAKER), ("first_person", FIRST_PERSON), ("collective", COLLECTIVE)):
        if pattern.match(value):
            return name
    return None


def inherits_from_previous(text: str) -> bool:
    """The report leans on the earlier report: a back reference (v3's test, including «بهذا الإسناد» in the first 160 letters) or, in v3.1, an asker with a pronoun / «وقال عليه السلام»."""
    return opening_class(text) in INHERITING or bool(FIRST_160.search(folded(text)[:160]))


def opens_with_back_reference(text: str) -> bool:
    """v3's test: a pronoun or phrase that points back (عنه، وعنه، وبهذا الإسناد، وبإسناده، بالإسناد الأول، و/عن …) or «بهذا الإسناد» in the first 160 letters. See `inherits_from_previous` for v3.1."""
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


# ---- empty readings (owner ruling 3 of the v3.1 brief): "this report has no isnad" is applicable unless the text writes a transmission word and a name before the saying ----
STRICT_VERBS = frozenset({"حدثنا", "حدثني", "اخبرنا", "اخبرني", "انبانا", "انباني", "ثنا", "حدثه", "اخبره"})    # a name always follows
SOFT_VERBS = frozenset({"سمعت", "روي", "رواه", "عن"})                                                      # a name follows only when one is there
SPEECH_VERBS = frozenset({"قال", "قضي", "ساله", "سال", "كتب", "شكا", "شكي", "سيل", "قلت"})
NASAB, KUNYA_WORDS = frozenset({"بن", "ابن", "بنت"}), frozenset({"ابو", "ام", "اخو"})
TITLES = frozenset({"الصادق", "الباقر", "الكاظم", "الرضا", "الجواد", "الهادي", "العسكري", "السجاد", "القائم"})
REGION_END = re.compile(r"[«\"“:]")
REGION_LIMIT = 200


def saying_region(text: str) -> list[str]:
    """Folded tokens of the text before the saying: up to the first quote or colon (at most 200 letters), the leading report number dropped."""
    head = re.sub(r"^\s*\d+\s*[-–.ـ]\s*", "", text)
    cut = REGION_END.search(head)
    return fold_v3(head[: cut.start() if cut else REGION_LIMIT][:REGION_LIMIT]).split()


def name_at(tokens: list[str], start: int, strict: bool) -> bool:
    """A personal name begins at tokens[start]: any word after a transmission verb (strict), or a nasab («X بن Y» within three words), a kunya, an Imam's laqab or «أمير المؤمنين»."""
    if start >= len(tokens):
        return False
    if strict:
        return True
    first = tokens[start]
    if first in KUNYA_WORDS and start + 1 < len(tokens) or first in TITLES or tokens[start: start + 2] == ["امير", "المومنين"]:
        return True
    return any(tokens[j] in NASAB and j + 1 < len(tokens) for j in range(start + 1, min(start + 4, len(tokens))))


def transmission_name(tokens: list[str]) -> bool:
    """A transmission word followed by a name before the saying («حدثنا X», «روى X», «عن X بن Y», «سمعت أبا Y»)."""
    return any((tok in STRICT_VERBS and name_at(tokens, i + 1, True)) or (tok in SOFT_VERBS and name_at(tokens, i + 1, False)) for i, tok in enumerate(tokens))


def name_before_saying(tokens: list[str]) -> bool:
    """A speech or transmission word followed by a name before the saying; the compiler speaking of his own book («قال أبو جعفر مصنف هذا الكتاب») is no name."""
    for i, tok in enumerate(tokens):
        if tok in STRICT_VERBS and name_at(tokens, i + 1, True):
            return True
        if (tok in SOFT_VERBS or tok in SPEECH_VERBS) and name_at(tokens, i + 1, False) and "مصنف" not in tokens[i + 1: i + 7]:
            return True
    return False


def empty_reading_state(text: str) -> tuple[str, str]:
    """For an agreed reading with no link: ("transmission_name", why) held; ("unsettled_opening", why) held (the opening is an asker, an inherited speaker or a name, which v3.1 reads as a link);
    ("applicable", "") = "this report has no isnad by reading"."""
    tokens = saying_region(text)
    if transmission_name(tokens):
        return "transmission_name", "the text writes a transmission word and a name before the saying: «" + " ".join(tokens[:12]) + "»"
    kind = opening_class(text)
    if kind in ("asker_pronoun", "asker_named", "implicit_speaker", "first_person", "collective", "pronoun", "isnad_phrase", "bare_an"):
        return "unsettled_opening", f"the text opens as {kind}: v3.1 reads such an opening as a link (asker) or inherits from the earlier report"
    if name_before_saying(tokens):
        return "unsettled_opening", "a name stands before the saying: «" + " ".join(tokens[:12]) + "»"
    return "applicable", ""


ASKER_RAW = re.compile(r"^\s*(?:\d+\s*[-–.ـ]\s*)?(?:ح\s*)?(?:و\s?)?(?:ساله|سال|كتب|شكا|شكي)\s+(?!اليه|اليها|عن(?:\s|$))")


def named_asker_offset(text: str) -> int | None:
    """Offset in `text` where the asker's own name begins («و سأل X Y», «و سأله X», «و كتب X إلى Y»), None when no asker is named («وكتب إليه», «وسئل: عن»)."""
    chars, index = fold_chars(text)
    match = ASKER_RAW.match(chars)
    return index[match.end()] if match and match.end() < len(index) else None


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
    opens = inherits_from_previous(text)
    usable = has_usable_previous(context)
    if opens and not usable:
        hold("back_reference_without_previous_report", f"the report leans on the earlier report ({opening_class(text) or 'back reference'}) and the packet carried no previous report that writes its chain or names its speaker")
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
    elif opening_class(text) in INHERITING and usable and routes and not any(l["kind"] == "inherited" for r in routes for l in r["links"]) and output.get("status") == "read":
        hold("back_reference_only", "the text opens with a back reference or an inherited speaker and a previous report was supplied, but no inherited link was taken")
    considered = [r for r in routes if not r.get("variant") and _in_first_isnad_region(r, routes, text) and not _abbreviated(r, text)]
    ends = unexplained_end_signatures(considered)
    if len(ends) > 1 and not _independent_isnads(considered):
        hold("routes_end_at_different_links", "routes of one report end at different last links without the text saying so: " + "؛ ".join(sorted("/".join(sorted(e)) for e in ends))[:200])
    poem = _second_isnad_not_same_saying(routes, text)
    if poem:
        hold("second_isnad_not_same_saying", poem)
    if not routes and output.get("status") == "read":
        state, why = empty_reading_state(text)
        if state == "transmission_name":
            hold("empty_reading_transmission_name", why)
        elif state == "unsettled_opening":
            hold("empty_reading_unsettled_opening", why)
    offset = named_asker_offset(text) if routes else None
    if offset is not None and not any(l["start"] is not None and offset <= l["start"] <= offset + 8 and l["kind"] in ("narrator", "unnamed") for r in routes for l in r["links"]):
        hold("asker_not_a_link", "the report opens with an asker («سأل / سأله / كتب / شكا X») and no route has a link at his name; owner ruling: the one who asks or writes is a link")
    return holds


ABBREVIATED = re.compile(r"^(?:فذكر|ثم ذكر|بنحوه|بمثله|نحوه|مثله|بنحو|بمثل|نحو|مثل|بمعناه|بمعني)(?= |$)")


def _abbreviated(route: dict, text: str) -> bool:
    """The text abbreviates this route right after its last name («الأعمش، فذكر نحوه», «بمثله»): it is short on purpose."""
    end = _last_end(route)
    return end is not None and bool(ABBREVIATED.match(fold_v3(text[end: end + 40])))


def _independent_isnads(routes: list[dict]) -> bool:
    """Routes that end at different links because they are separate isnads, each ending at its own source («سمرة بن جندب» / «المغيرة بن شعبة»): every end is a named narrator written in
    one group only, no route ends in a back reference, relation or gap, and no end name stands inside another route (a name that does is the meeting point of a dropped shared tail)."""
    ends: dict[str, set[int]] = {}
    keyed = []
    for route in routes:
        written = _written(route)
        if not written or written[-1]["kind"] not in ("narrator", "imam_in_text"):
            return False
        keys = [link_key(l["surface"]) for l in written]
        keyed.append(keys)
        ends.setdefault(keys[-1], set()).add(route.get("group", 0))
    if len(ends) < 2 or any(ends[a] & ends[b] for a in ends for b in ends if a < b):
        return False
    return not any(end in keys[:-1] for keys in keyed for end in ends)


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
