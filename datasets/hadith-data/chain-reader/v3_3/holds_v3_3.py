"""Deterministic holds of the v3.3 tool: reasons a reading is queued for review instead of applied (copy of v3_2/holds_v3_2.py; see v3_3/AGENTS.md §holds, v3_3/HOLDS.md).

    holds = compute_holds(reading, output, text, context, stored_surfaces, other_output)

A hold never changes a reading and never rejects it. v3.3 changes v3.2 by the out-of-sample judgement of tranche 02: new `mutabaa_marker`; `routes_end_at_different_links` replaced by
`route_ends_inside_another_route`; `route_at_most_half_the_longest` and `inherited_from_far_report` narrowed; new `needs_ruling_faqih_route_statement` (the owner has not ruled). Every other v3.2 hold is unchanged.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "v3_2"))
from expand_v3_2 import DERIVED_KINDS, restated_short_form  # noqa: E402  (expand, validate, norm are v3_2's unchanged)
from norm import MARKS  # noqa: E402
from norm_v3_2 import fold_chars, fold_v3, link_key  # noqa: E402

MAX_ROUTES = 8
# On the folded text (marks and hamza folded, punctuation one space). Keep in step with OPENING in v3/build_context_v3.cjs; tests/backref_cases.json runs both.
OPENING = re.compile(
    r"^(?:\d+ )?(?:ح )?(?:و ?)?(?:"
    r"(?P<pronoun>عنهما|عنهم|عنها|عنه)(?= |$)|"
    r"(?P<isnad_phrase>بهذا (?:الاسناد|السند)|بنفس (?:الاسناد|السند)|بالاسناد|باسناده|باسنادهم|باسنادها|بالسند|بسنده|بسندهم)(?= |$)|"
    r"(?P<bare_an>عن )"
    r")")
FIRST_160 = re.compile(r"بهذا (?:الاسناد|السند)")
# Openings that lean on the previous report or name an asker (owner rulings 1 and 2). Same folded text; keep in step with ../v3_1/backref_lib_v3_1.cjs (the packet builder: v3.2 does not rebuild packets).
LEAD = r"^(?:[0-9]+ )?(?:ح )?(?:و ?)?"
ASKER = re.compile(LEAD + r"(?P<verb>ساله|سال|كتب|شكا|شكي|سيل)(?= |$)(?P<rest>.*)")
IMPLICIT_SPEAKER = re.compile(LEAD + r"(?:قال|قضي) (?:عليه|عليهما|عليهم|ع) ?(?:السلام)?(?= |$)")
FIRST_PERSON = re.compile(LEAD + r"قال قلت(?= |$)")
COLLECTIVE = re.compile(LEAD + r"روي عن (?:الايمه|الائمه)(?= |$)")
# v3.2: «و مع قوله عليه السلام: «...»» speaks like «وقال عليه السلام» but takes nothing from the earlier report (not in INHERITING, so no packet change): an empty reading of it is held (case 2973ea).
QUOTED_SAYING = re.compile(LEAD + r"مع (?:قوله|قولهم|قول) (?:عليه|عليهما|عليهم|ع|صلي)(?= |$)")
# v3.2: the Prophet as the speaker of a report whose text names no transmitter: «وقال صلى الله عليه وآله», «ونهى صلى الله عليه وآله», «كما روي عن النبي», «وصلى رسول الله» (unruled).
PROPHET_OPENING = re.compile(LEAD + r"(?:(?:كما )?(?:و ?)?(?:روي|رويت|قال|نهي|امر|قضي|صلي)\s+(?:عن )?)?(?:النبي|رسول الله|صلي الله عليه)")
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
    """The opening of a report: pronoun | isnad_phrase | bare_an | asker_pronoun | asker_named | implicit_speaker | quoted_saying | first_person | collective | None (v3's three back references first)."""
    value = folded(text)
    match = OPENING.match(value)
    if match:
        return match.lastgroup
    form = asker_form(value)
    if form:
        return form
    for name, pattern in (("implicit_speaker", IMPLICIT_SPEAKER), ("quoted_saying", QUOTED_SAYING), ("first_person", FIRST_PERSON), ("collective", COLLECTIVE)):
        if pattern.match(value):
            return name
    return None


def inherits_from_previous(text: str) -> bool:
    """The report leans on the earlier report: a back reference (v3's test, including «بهذا الإسناد» in the first 160 letters) or, in v3.2, an asker with a pronoun / «وقال عليه السلام»."""
    return opening_class(text) in INHERITING or bool(FIRST_160.search(folded(text)[:160]))


def opens_with_back_reference(text: str) -> bool:
    """v3's test: a pronoun or phrase that points back (عنه، وعنه، وبهذا الإسناد، وبإسناده، بالإسناد الأول، و/عن …) or «بهذا الإسناد» in the first 160 letters. See `inherits_from_previous` for v3.2."""
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


# ---- empty readings (owner ruling 3 of the v3.2 brief): "this report has no isnad" is applicable unless the text writes a transmission word and a name before the saying ----
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
    ("prophet_no_transmitter", why) held (v3.2: unruled, every work); ("applicable", "") = "this report has no isnad by reading"."""
    tokens = saying_region(text)
    if transmission_name(tokens):
        return "transmission_name", "the text writes a transmission word and a name before the saying: «" + " ".join(tokens[:12]) + "»"
    kind = opening_class(text)
    if kind in ("asker_pronoun", "asker_named", "implicit_speaker", "quoted_saying", "first_person", "collective", "pronoun", "isnad_phrase", "bare_an"):
        return "unsettled_opening", f"the text opens as {kind}: v3.2 reads such an opening as a link (asker) or inherits from the earlier report"
    if name_before_saying(tokens):
        return "unsettled_opening", "a name stands before the saying: «" + " ".join(tokens[:12]) + "»"
    if PROPHET_OPENING.match(folded(text)):
        return "prophet_no_transmitter", "the Prophet is the speaker and the text names no transmitter (unruled): «" + " ".join(tokens[:12]) + "»"
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
    statement = faqih_route_statement(text, context)
    if statement:
        hold("needs_ruling_faqih_route_statement", statement)
    if reading is None:
        return holds
    routes = reading["routes"]
    if reading.get("variant_remarks"):
        hold("has_variant_group", "the reader marked a remark about another version (variant): " + " | ".join(remark["quote"][:80] for remark in reading["variant_remarks"])[:240]
             + "; no route is stored for it, and the fix pipeline cannot yet carry the remark as a note")
    if reading.get("only_variant_groups"):
        hold("variant_only_reading", "every group the reader wrote is a variant remark: nothing is left that could be stored as the chain")
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
    inside = route_ends_inside_another_route(routes, text)
    if inside:
        hold("route_ends_inside_another_route", inside)
    if len(routes) > 1:
        marker = mutabaa_marker(text)
        if marker:
            hold("mutabaa_marker", f"the text carries the mutaba'a marker «{marker}» and the reading has {len(routes)} routes: the marked isnad is a remark about another version, never a route of this saying")
    poem = _second_isnad_not_same_saying(routes, text)
    if poem:
        hold("second_isnad_not_same_saying", poem)
    shape = short_route_detail(routes)
    if shape:
        hold("route_at_most_half_the_longest", shape)
    split = first_links_split_by_comma(routes, text)
    if split:
        hold("first_links_split_by_comma", split)
    if len(routes) >= 2 and "؛" in text[: reading["matn_start"] or 400]:
        hold("semicolon_in_multi_route_isnad", f"«؛» inside the isnad of a reading with {len(routes)} routes: co-transmitters grouped after it often lose their shared tail")
    lone = single_narrator_without_source(routes, context)
    if lone:
        hold("imami_single_narrator_without_source", lone)
    far = inherited_from_far_report(routes, context, text)
    if far:
        hold("inherited_from_far_report", far)
    if not routes and output.get("status") == "read":
        state, why = empty_reading_state(text)
        if state == "transmission_name":
            hold("empty_reading_transmission_name", why)
        elif state == "unsettled_opening":
            hold("empty_reading_unsettled_opening", why)
        elif state == "prophet_no_transmitter":
            hold("needs_ruling_prophet_no_transmitter", why)
    offset = named_asker_offset(text) if routes else None
    if offset is not None and not any(l["start"] is not None and offset <= l["start"] <= offset + 8 and l["kind"] in ("narrator", "unnamed") for r in routes for l in r["links"]):
        hold("asker_not_a_link", "the report opens with an asker («سأل / سأله / كتب / شكا X») and no route has a link at his name; owner ruling: the one who asks or writes is a link")
    return holds


# ---- v3.2 shape holds, measured on tranche 01's judge sample (tranches/tranche-01/judge/analysis/proposed_holds.py is the definition) ----
def judged_links(route: dict) -> list[dict]:
    """The judge's view of a route: every link but the compiler's head (an inherited link counts)."""
    return [l for l in route["links"] if l["kind"] != "compiler_head"]


def last_link_key(route: dict) -> str | None:
    """Key of the route's last written link, a trailing back reference left out (it points at an isnad, it is no person)."""
    keys = route_link_keys(route)
    return keys[-1] if keys else None


def short_route_detail(routes: list[dict]) -> str | None:
    """A route at most half as long as the longest of the same report, the longest having 4 links or more, AND the shorter route's last link differs from the last link of every longest route:
    a shared head or tail was dropped (case 6d7565). Two routes that end at the same man are two heads of one chain, not a lost tail (tranche 02's 1552aa)."""
    lengths = [len(judged_links(r)) for r in routes]
    if len(routes) < 2 or max(lengths) < 4:
        return None
    longest_ends = {last_link_key(r) for r, n in zip(routes, lengths) if n == max(lengths)}
    for route, length in zip(routes, lengths):
        if length <= max(lengths) * 0.5 and last_link_key(route) not in longest_ends:
            return f"route lengths {sorted(lengths)}: the shortest is at most half the longest and ends at a different link, so a shared head or tail was probably dropped"
    return None


def route_ends_inside_another_route(routes: list[dict], text: str = "") -> str | None:
    """A route's last link stands inside another route of the same report, not at its end, and the other route ends elsewhere: a shared tail was dropped from this route (tranche 02's 1061e3, d02f9f,
    facedc, 181bd0, b88276, 30b092, 883658). «X» counts as standing inside a route that has «X بن Y» there (d02f9f: «هشام» / «هشام بن عروة») unless both routes end at that same name
    (a2c20f: three routes end at «عبد الله», one has «عبد الله بن مرة» inside). Exempt, as v3.1's broad hold was: a route that ends in a back reference («سهيل، بهذا الإسناد»: 8b0565), a route of a later
    isnad written after the saying and a route the text abbreviates («بمثله»): tranche 01's dd8d9b, 0c66ee, 610c03, 31cf87, judged right."""
    checked = [r for r in routes if not r.get("variant") and _in_first_isnad_region(r, routes, text) and not _abbreviated(r, text)] if text else routes
    for route in checked:
        written = _written(route)
        keys = route_link_keys(route)
        if not keys or written[-1]["kind"] == "back_reference":
            continue
        for other_route in routes:
            other = route_link_keys(other_route)
            if other_route is route or not other or other[-1] == keys[-1] or restated_short_form(keys[-1], other[-1]) or restated_short_form(other[-1], keys[-1]):
                continue
            for position, key in enumerate(other[:-1]):
                if key == keys[-1] or restated_short_form(keys[-1], key):
                    return f"the route ending at «{keys[-1]}» stops at a man who stands inside another route (position {position + 1} of {len(other)}): the shared tail was dropped from it"
    return None


# (patterns run on the folded text, where alif maqsura is ya: «على» is «علي»)
# a mutaba'a: another narrator is said to have followed the one just named («تابعه قتيبة», «وتابعه», «وقد تابع ابن جريج على ذلك»); on the folded text
MUTABAA = re.compile(r"(?:^| )(?:ف|و)?(?:قد )?(?P<form>تابعه|تابعها|تابعهم|تابعهما)(?= |$)|(?:^| )(?:وقد |و)(?P<verb>تابع) (?:\S+ ){1,3}?علي(?= )")


def mutabaa_marker(text: str) -> str | None:
    """The marker found («تابعه» and its close forms; «وقد تابع X على ...»), None when the text has none."""
    match = MUTABAA.search(folded(text))
    return (match.group("form") or match.group("verb")) if match else None


# al-Faqih's «و ما كان فيه عن X فقد رويته عن ...»: the compiler states his routes to a source and writes no saying; the owner has not ruled whether that is an isnad
FAQIH_ROUTE_STATEMENT = re.compile(r"^(?:\d+ )?(?:و ?)?(?:كل ?)?ما (?:كان|كنت) (?:فيه|في هذا الكتاب)(?: من| عن) .{1,200}?فقد (?:رويته|رويت|رويتها)(?= )")


def faqih_route_statement(text: str, context: dict | None) -> str | None:
    """Imami works only: the report opens as the compiler's statement of his routes to a source («و ما كان فيه عن X فقد رويته عن Y»). Unruled: held as needs-ruling until the owner decides."""
    if not is_imami(context) or not FAQIH_ROUTE_STATEMENT.match(folded(text)):
        return None
    return "the report is the compiler's statement of his routes to a source («ما كان فيه عن X فقد رويته عن ...») with no saying: the owner has not ruled whether that is an isnad"


COMMA_GAP = re.compile(r"[\s]*[،,][\s]*")


def first_links_split_by_comma(routes: list[dict], text: str) -> str | None:
    """Two routes identical except for the first link, the two first links adjacent in the text with only a comma between: a kunya and a name read as two men (case 05c2d0)."""
    keyed = [(judged_links(r), tuple(link_key(l["surface"]) for l in judged_links(r))) for r in routes]
    for a in range(len(keyed)):
        for b in range(a + 1, len(keyed)):
            (links_a, keys_a), (links_b, keys_b) = keyed[a], keyed[b]
            if len(keys_a) < 2 or keys_a[1:] != keys_b[1:] or keys_a[0] == keys_b[0]:
                continue
            first, second = sorted((links_a[0], links_b[0]), key=lambda l: l["start"] if l["start"] is not None else -1)
            if first["start"] is None or first["end"] is None or second["start"] is None or second["start"] < first["end"]:
                continue
            gap = MARKS.sub("", text[first["end"]:second["start"]])
            if "،" in gap or "," in gap:
                if COMMA_GAP.fullmatch(gap):
                    return f"«{first['surface']}» and «{second['surface']}» stand side by side separated only by a comma: one man (kunya and name) read as two routes"
    return None


# ---- v3.2 Imami holds (the al-Faqih findings of tranche 01) ----
IMAM_WORDS = frozenset({"الصادق", "الباقر", "الكاظم", "الرضا", "الجواد", "الهادي", "العسكري", "السجاد", "القايم"})
IMAM_KUNYAS = ("ابو عبد الله", "ابو جعفر", "ابو الحسن", "ابو محمد", "ابو ابراهيم", "امير المومنين")


def is_imami(context: dict | None) -> bool:
    work = (context or {}).get("work") or {}
    return work.get("tradition") == "imami" or str(work.get("key") or "").startswith("imami:")


def is_imam_surface(surface: str) -> bool:
    key = link_key(surface)
    return bool(IMAM_WORDS & set(key.split())) or any(key == kunya or key.startswith(kunya + " ") for kunya in IMAM_KUNYAS)


def single_narrator_without_source(routes: list[dict], context: dict | None) -> str | None:
    """An Imami reading whose only link is one narrator: no Imam, no source and no inherited link (cases 07d717 «و قال الحلبي: و سألته», f14c39 «و- في رواية جميل أنه قال»)."""
    if not is_imami(context) or len(routes) != 1:
        return None
    links = judged_links(routes[0])
    if len(links) == 1 and links[0]["kind"] == "narrator" and not is_imam_surface(links[0]["surface"]):
        return f"the whole reading is the single link «{links[0]['surface']}»: no Imam or source, nothing inherited (first-person «سألته» / «أنه قال» with the Imam left out)"
    return None


NUMBERED = re.compile(r"^\W*(\d+)\s*[-–]")
MAX_INHERITED_GAP = 3


def only_pass_through_between(ref: str, number: str, current_number: int | None, previous: dict[str, dict]) -> bool:
    """Every report between this one and the source report is in the packet, writes no chain, names no speaker and opens with a back reference («وبإسناده», «وبهذا الإسناد»):
    the walk back passes through reports that only carry the source's chain on (tranche 02's 5505a6). A report missing from the packet is unknown, so it does not count as pass-through (b36519)."""
    if not (ref.startswith("prev") and ref[4:].isdigit()):
        return False
    nearer = [item for name, item in previous.items() if name and name.startswith("prev") and name[4:].isdigit() and int(name[4:]) < int(ref[4:])]
    if number.isdigit() and current_number is not None:
        wanted = set(range(min(current_number, int(number)) + 1, max(current_number, int(number))))
        present = {int(item["number"]) for item in nearer if str(item.get("number") or "").isdigit()}
        if not wanted <= present:
            return False
    return all(not item.get("has_written_chain") and opens_with_back_reference(item.get("chain_text") or "") for item in nearer)


def inherited_from_far_report(routes: list[dict], context: dict | None, text: str) -> str | None:
    """An inherited link taken from a report more than 3 reports back (case b36519: five back, nothing in the text confirms it), unless every report in between is a pass-through («وبإسناده»,
    «وبهذا الإسناد»: no chain of its own, no other speaker), when distance alone does not hold (5505a6). The gap is the difference of the two report numbers when both are plain numbers
    (the packet's previous reports are not always adjacent), else the index of the ref («prev4» = 4)."""
    previous = {item.get("ref"): item for item in (context or {}).get("previous_reports") or []}
    current = NUMBERED.match(MARKS.sub("", text))
    for ref in sorted({l.get("from") for r in routes for l in r["links"] if l["kind"] == "inherited" and l.get("from")}):
        number = str((previous.get(ref) or {}).get("number") or "")
        if current and number.isdigit():
            gap = abs(int(current.group(1)) - int(number))
        elif ref.startswith("prev") and ref[4:].isdigit():
            gap = int(ref[4:])
        else:
            continue
        if gap > MAX_INHERITED_GAP:
            if only_pass_through_between(ref, number, int(current.group(1)) if current else None, previous):
                continue
            return f"the reading inherits from {ref}, {gap} reports back (more than {MAX_INHERITED_GAP}) and a report between them writes its own chain, names another speaker or is not in the packet: nothing in the text confirms that the earlier speaker is still the one"
    return None


ABBREVIATED = re.compile(r"^(?:فذكر|ثم ذكر|بنحوه|بمثله|نحوه|مثله|بنحو|بمثل|نحو|مثل|بمعناه|بمعني)(?= |$)")


def _abbreviated(route: dict, text: str) -> bool:
    """The text abbreviates this route right after its last name («الأعمش، فذكر نحوه», «بمثله»): it is short on purpose."""
    end = _last_end(route)
    return end is not None and bool(ABBREVIATED.match(fold_v3(text[end: end + 40])))


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
