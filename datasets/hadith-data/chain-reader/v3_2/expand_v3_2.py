"""The tool side of a v3.2 chain reading (copy of v3_1/expand_v3_1.py; v3_2/AGENTS.md §variant, §folds): levels to routes, offsets from surfaces, the compiler head, matn_start (see v3/AGENTS.md §expand).

The reader writes {"groups": [{"levels": [[item, ...], ...], "variant": true?}, ...], "shared_tail": [[item, ...], ...] | null}; an item is
{"surface", "kind", "occurrence"?, "from"?}. Changes from v2: surfaces are found after a spelling fold (alif-maqsura/ya, Persian letters, hamza carriers,
kunya case, a space after «و», diacritics) and returned in the text's own characters; a stray `occurrence` on a surface that stands once is ignored; the
compiler head is not added when the route's first written name is the compiler under any spelling of the work profile; the same man written twice in
succession is one link; a group may carry `"variant": true` (a remark that another version names a different transmitter).

v3.2: a `variant` group is NOT a transmission route. It never enters `routes`; it is kept in `variant_remarks` ({"group", "surfaces", "start", "end", "quote"}) and never takes part in agreement.
A link written inside «[ ... ]» (an editor's insertion) carries `bracketed: true` and is left out of `canonical()` (the triage holds a reading whose two passes handled it differently).
`readings_agree` is `canonical()` equality, or equality after pairing routes that differ in one slot by a restated shorter form of the same name («مخرمة» / «مخرمة بن بكير»).
"""

from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
from norm import MARKS  # noqa: E402
from norm_v3_2 import KUNYA_PATTERN, fold_chars, fold_v3, folded_cursor, link_key, same_man  # noqa: E402

READER_KINDS = ("narrator", "unnamed", "back_reference", "relation", "imam_in_text", "inherited")
DERIVED_KINDS = ("compiler_head", "inherited")       # no offsets
MAX_EXPANSION = 400                                  # beyond this the reading is held, not expanded
ITEM_KEYS = {"surface", "kind", "occurrence", "from"}
GROUP_KEYS = {"levels", "variant"}
PROFILES = {key: value for key, value in json.loads((HERE / "work_profiles_v3_2.json").read_text(encoding="utf-8")).items() if not key.startswith("_")}
IGNORED_IN_COMPARISON = ("الحديث",)                  # «بهذا الحديث» points at the saying, not at an isnad
CLOSING_ISNAD_WORDS = ("الاسناد", "السند")           # a closing «بهذا / في هذا الإسناد» (stored chains never carry it; score.py drops it too)


def _token_pattern(token: str) -> str:
    if token in KUNYA_PATTERN:
        return KUNYA_PATTERN[token]
    if len(token) > 2 and token.startswith("و"):
        return "و\\s?" + re.escape(token[1:])          # an attached «و» may stand apart in the text
    return re.escape(token)


def _needle_pattern(surface: str, joined: bool = False) -> re.Pattern | None:
    """The folded surface as a pattern over the folded text. `joined` lets the words touch («بنجعفر», «أبو الحسنموسى»: a typo, or a zero-width character where the text lost its space)."""
    folded, _ = fold_chars(surface)
    words = re.sub(r"[\s،,]+", " ", folded).strip().split()
    merged: list[str] = []
    for index, word in enumerate(words):                # a lone «و» belongs to the next word: «و بهذا» = «وبهذا»
        if merged and merged[-1] == "و":
            merged[-1] = "و" + word
        else:
            merged.append(word)
    if not merged:
        return None
    parts = [_token_pattern(word) for word in merged]
    if len(merged[0]) > 3 and merged[0].startswith("ال") and merged[0] not in KUNYA_PATTERN:
        parts[0] = "(?:ال|لل)" + re.escape(merged[0][2:])   # «للرضا» = ل + الرضا: the lam of the preposition swallows the article's alif
    return re.compile((r"[\s،,]*" if joined else r"[\s،,]+").join(parts))


def strict_chars(text: str) -> tuple[str, list[int]]:
    """v2's view of the text: only marks and tatweel removed, letters as written."""
    kept = [i for i, ch in enumerate(text) if not MARKS.match(ch)]
    return "".join(text[i] for i in kept), kept


def _strict_pattern(surface: str) -> re.Pattern | None:
    words = "".join(ch for ch in surface if not MARKS.match(ch)).split()
    return re.compile(r"[\s،,]+".join(re.escape(word) for word in words)) if words else None


def _find(view: str, pattern: re.Pattern, cursor: int, occurrence: int | None) -> tuple[tuple[int, int] | None, str]:
    """((start, end) in the view, note). The first match at/after `cursor`, or the Nth match overall; a stray occurrence is ignored when the surface stands once."""
    matches = list(pattern.finditer(view))
    if occurrence:
        if len(matches) >= occurrence:
            return (matches[occurrence - 1].start(), matches[occurrence - 1].end()), ""
        if len(matches) == 1:
            return (matches[0].start(), matches[0].end()), f"occurrence {occurrence} ignored: the surface stands once"
        return None, ""
    for match in matches:
        if match.start() >= cursor:
            return (match.start(), match.end()), ""
    return None, ""


class TextViews:
    """The text twice: as written (marks removed: v2's reading, tried first, so an `occurrence` counts the reader's own spelling) and folded (the fallback for a spelling the text does not use)."""

    def __init__(self, text: str):
        self.text = text
        self.strict, self.strict_index = strict_chars(text)
        self.folded, self.folded_index = fold_chars(text)

    def locate(self, surface: str, cursor: int, occurrence: int | None) -> tuple[tuple[int, int] | None, str, bool]:
        """((start, end) in the original text, note, found anywhere). `cursor` is an offset in the original text. Tried in turn: as written, folded, folded with the words allowed to touch."""
        anywhere = False
        for view, index, pattern in ((self.strict, self.strict_index, _strict_pattern(surface)), (self.folded, self.folded_index, _needle_pattern(surface)),
                                     (self.folded, self.folded_index, _needle_pattern(surface, joined=True))):
            if pattern is None:
                return None, "", False
            found, note = _find(view, pattern, folded_cursor(index, cursor), occurrence)
            if found:
                return (index[found[0]], index[found[1] - 1] + 1), note, True
            if _find(view, pattern, 0, None)[0] is not None:
                anywhere = True
        return None, "", anywhere


BRACKETS = re.compile(r"\[[^\[\]]*\]")
REMARK_BOUNDARY = re.compile(r"[.\n]")
REMARK_REACH = 160                                   # letters either side of a variant remark's names searched for the end of its sentence


def bracketed_spans(text: str) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in BRACKETS.finditer(text)]


def remark_span(text: str, start: int, end: int) -> tuple[int, int, str]:
    """The sentence of a variant remark: from the last full stop or line break before its first name to the next one after its last (each at most REMARK_REACH letters away)."""
    low = max(0, start - REMARK_REACH)
    cut = max((m.end() for m in REMARK_BOUNDARY.finditer(text[low:start])), default=0)
    first = low + cut
    after = text[end:end + REMARK_REACH]
    match = REMARK_BOUNDARY.search(after)
    last = end + (match.start() if match else len(after))
    return first, last, text[first:last].strip()


def _locate(item: dict, views: TextViews, cursor: int, where: str, errors: list[str], notes: list[str]) -> dict | None:
    """The item as a link: offsets in the text found from the surface (as written first, then folded), the first occurrence at/after `cursor` (an original offset) or the stated one; the surface is the text's own characters."""
    kind = item["kind"]
    if kind == "inherited":
        return {"surface": item["surface"], "start": None, "end": None, "kind": "inherited", "from": item.get("from")}
    if not "".join(ch for ch in item["surface"] if not MARKS.match(ch)).strip():
        errors.append(f"surface: {where} is empty")
        return None
    occurrence = item.get("occurrence")
    found, note, anywhere = views.locate(item["surface"], cursor, occurrence)
    if found is None:
        errors.append(f"occurrence: {where} {item['surface']!r} occurrence {occurrence} is not in the text" if not anywhere and occurrence else
                      f"surface_not_in_text: {where} {item['surface']!r}" if not anywhere else f"order: {where} {item['surface']!r} occurs only before the previous level")
        return None
    if note:
        notes.append(f"{where} {item['surface']!r}: {note}")
    start, end = found
    text = views.text
    while end < len(text) and MARKS.match(text[end]):
        end += 1
    return {"surface": text[start:end], "start": start, "end": end, "kind": kind}


def check_shape(output: dict) -> list[str]:
    errors = []
    if not isinstance(output.get("groups"), list):
        return ["shape: groups must be a list"]
    levels_lists = [("g%d" % g, group.get("levels") if isinstance(group, dict) else None) for g, group in enumerate(output["groups"])]
    for g, group in enumerate(output["groups"]):
        if isinstance(group, dict) and (set(group) - GROUP_KEYS or "levels" not in group or ("variant" in group and not isinstance(group["variant"], bool))):
            errors.append(f"shape: g{g} must be an object with levels (and optionally variant: true)")
    if output.get("shared_tail") is not None:
        levels_lists.append(("tail", output["shared_tail"]))
    for name, levels in levels_lists:
        if not isinstance(levels, list) or not levels:
            errors.append(f"shape: {name} needs a non-empty list of levels")
            continue
        for l, level in enumerate(levels):
            if not isinstance(level, list) or not level:
                errors.append(f"shape: {name}l{l} needs a non-empty list of items")
                continue
            for i, item in enumerate(level):
                at = f"{name}l{l}i{i}"
                if not isinstance(item, dict) or not {"surface", "kind"} <= set(item) or not set(item) <= ITEM_KEYS:
                    errors.append(f"shape: {at} must be an object with surface and kind (occurrence, from optional)")
                elif item["kind"] not in READER_KINDS:
                    errors.append(f"kind: {at} {item['kind']!r} is not one of {', '.join(READER_KINDS)}")
                elif not isinstance(item["surface"], str):
                    errors.append(f"shape: {at} surface must be a string")
                elif item["kind"] == "inherited" and not item.get("from"):
                    errors.append(f"inherited: {at} needs `from` (the ref of the previous report it comes from)")
                elif "occurrence" in item and not (isinstance(item["occurrence"], int) and not isinstance(item["occurrence"], bool) and item["occurrence"] >= 1):
                    errors.append(f"occurrence: {at} must be a whole number from 1")
    return errors


def profile_for(context: dict | None) -> dict:
    """The work profile (compiler aliases) for a packet: by `context.work.key`; otherwise only the packet's own compiler name."""
    work = ((context or {}).get("work") or {})
    profile = PROFILES.get(work.get("key") or "")
    if profile:
        return profile
    compiler = work.get("compiler") or {}
    return {"compiler_head": bool(compiler.get("head_of_every_chain")), "compiler_ar": compiler.get("ar"), "compiler_aliases": [compiler["ar"]] if compiler.get("ar") else [],
            "compiler_alias_runs": [], "compiler_alias_scope": "first"}


def compiler_written(route_links: list[dict], profile: dict) -> bool:
    """True when the route's first written name (or any written name, for scope 'any') is the compiler under some spelling of the profile."""
    aliases = {link_key(a) for a in [profile.get("compiler_ar"), *(profile.get("compiler_aliases") or [])] if a}
    runs = [" " + link_key(r) + " " for r in profile.get("compiler_alias_runs") or []]
    written = [l for l in route_links if l["start"] is not None and l["kind"] not in DERIVED_KINDS]
    for link in (written[:1] if profile.get("compiler_alias_scope", "first") == "first" else written):
        if link["kind"] not in ("narrator", "imam_in_text"):
            continue
        key = link_key(link["surface"])
        if key in aliases or any(run in " " + key + " " for run in runs):
            return True
    return False


def collapse_repeats(links: list[dict], tail_from: int | None, notes: list[str]) -> tuple[list[dict], int | None]:
    """One link for the same man written twice in succession (two narrator links whose names are one name, or the short and the full form)."""
    result: list[dict] = []
    origins: list[int] = []                                   # index in `links` where each kept link began
    for position, link in enumerate(links):
        previous = result[-1] if result else None
        if previous and previous["kind"] == "narrator" and link["kind"] == "narrator" and previous["start"] is not None and link["start"] is not None                 and same_man(previous["surface"], link["surface"]):
            notes.append(f"one link: {previous['surface']!r} and {link['surface']!r} are one man written twice")
            if len(link_key(link["surface"])) > len(link_key(previous["surface"])):
                result[-1] = link
            continue
        result.append(link)
        origins.append(position)
    new_tail = None if tail_from is None else sum(1 for origin in origins if origin < tail_from)
    return result, new_tail


def expand(output: dict, text: str, context: dict | None = None) -> tuple[dict | None, list[str]]:
    """(stored-shape reading, errors). The reading is None when the shape or a surface is wrong."""
    errors = check_shape(output)
    if errors:
        return None, errors
    views = TextViews(text)
    notes: list[str] = []
    group_routes: list[list[list[dict]]] = []
    variant_groups: list[bool] = []
    furthest = 0
    for g, group in enumerate(output["groups"]):
        cursor, levels = 0, []
        for l, level in enumerate(group["levels"]):
            located = [_locate(item, views, cursor, f"g{g}l{l}i{i}", errors, notes) for i, item in enumerate(level)]
            if any(x is None for x in located):
                levels.append([])
                continue
            ends = [x["end"] for x in located if x["end"] is not None]
            if ends:
                cursor = max(ends)
            levels.append(located)
        furthest = max(furthest, cursor)
        group_routes.append(levels)
        variant_groups.append(bool(group.get("variant")))
    tail_levels = []
    if output.get("shared_tail"):
        cursor = furthest
        for l, level in enumerate(output["shared_tail"]):
            located = []
            for i, item in enumerate(level):
                trial: list[str] = []
                link = _locate(item, views, cursor, f"tail l{l}i{i}", trial, notes) or _locate(item, views, 0, f"tail l{l}i{i}", errors, notes)
                located.append(link)
            if any(x is None for x in located):
                tail_levels.append([])
                continue
            ends = [x["end"] for x in located if x["end"] is not None]
            if ends:
                cursor = max(ends)
            tail_levels.append(located)
    if errors:
        return None, errors
    size = sum(_product_size(levels) for g, levels in enumerate(group_routes) if not variant_groups[g]) * max(1, _product_size(tail_levels) if tail_levels else 1)
    if size > MAX_EXPANSION:
        return None, [f"too_many_routes: the levels expand to {size} routes (limit {MAX_EXPANSION}); split the reading into groups or file it"]
    routes, seen = [], set()
    tails = list(itertools.product(*tail_levels)) if tail_levels else [()]
    remarks = []
    for group_index, levels in enumerate(group_routes):
        if variant_groups[group_index]:                           # v3.2: a remark about another version, never a route
            written = [link for level in levels for link in level]
            starts, finish = [l["start"] for l in written if l["start"] is not None], [l["end"] for l in written if l["end"] is not None]
            if starts and finish:
                first, last, quote = remark_span(views.text, min(starts), max(finish))
                remarks.append({"group": group_index, "surfaces": [[l["surface"] for l in level] for level in levels], "start": first, "end": last, "quote": quote})
            continue
        for head in itertools.product(*levels):
            for tail in tails:
                links, tail_from = collapse_repeats(list(head) + list(tail), len(head) if tail_levels else None, notes)
                key = tuple((l["start"], l["end"], l["surface"]) for l in links)
                if key in seen:
                    continue
                seen.add(key)
                routes.append({"links": links, "shared_tail_from": tail_from, "group": group_index, "variant": False})
    profile = profile_for(context)
    if profile.get("compiler_head") and profile.get("compiler_ar"):
        for route in routes:
            if compiler_written(route["links"], profile):
                continue                                          # the text writes the compiler itself, under some spelling: that link stands
            route["links"].insert(0, {"surface": profile["compiler_ar"], "start": None, "end": None, "kind": "compiler_head", "from": "work"})
            if route["shared_tail_from"] is not None:
                route["shared_tail_from"] += 1
    spans = bracketed_spans(text)
    for route in routes:
        for link in route["links"]:
            if link["start"] is not None and any(low <= link["start"] and link["end"] <= high for low, high in spans):
                link["bracketed"] = True
    ends = [l["end"] for r in routes for l in r["links"] if l["end"] is not None and l["kind"] != "imam_in_text"]
    result = {"id": output.get("id"), "routes": routes, "variant_remarks": remarks, "only_variant_groups": bool(remarks) and not routes, "matn_start": max(ends) if ends else 0,
              "notes": output.get("notes", []), "tool_notes": sorted(set(notes))}
    return result, []


def _product_size(levels: list[list]) -> int:
    size = 1
    for level in levels:
        size *= max(1, len(level))
    return size


def route_keys(reading: dict, include_bracketed: bool = False) -> list[tuple[str, ...]]:
    """Each route as the comparison keys of its non-derived links (a back reference to the saying, «بهذا الحديث», dropped; a CLOSING back reference to the isnad
    («بهذا / في هذا الإسناد») dropped; the same man twice is one; v3.2: a link inside «[ ... ]» dropped unless `include_bracketed`)."""
    keyed = []
    for route in reading["routes"]:
        keys: list[str] = []
        written = [l for l in route["links"] if l["kind"] not in DERIVED_KINDS and (include_bracketed or not l.get("bracketed"))]
        for position, link in enumerate(written):
            words = link_key(link["surface"]).split()
            if link["kind"] == "back_reference" and (any(word in words for word in IGNORED_IN_COMPARISON) or (position == len(written) - 1 and position > 0 and any(word in words for word in CLOSING_ISNAD_WORDS))):
                continue
            key = link_key(link["surface"])
            if key and (not keys or keys[-1] != key or len(key.split()) < 2):
                keys.append(key)
        keyed.append(tuple(keys))
    return keyed


def canonical(reading: dict, include_bracketed: bool = False) -> frozenset:
    """Order-free form of a reading for agreement: the set of routes (variant remarks are not routes), each the link keys of its non-derived, non-bracketed links (v3: nisba, epithets, attached «و», spelling folded; v3.2: titles, patrons)."""
    return frozenset(route_keys(reading, include_bracketed))


def variant_keys(reading: dict) -> frozenset:
    """The variant remarks of a reading as sets of link keys (compared separately from the routes, never blocking agreement)."""
    return frozenset(tuple(sorted(link_key(s) for level in remark["surfaces"] for s in level)) for remark in reading.get("variant_remarks") or [])


def restated_short_form(short: str, long_: str) -> bool:
    """`short` is the first words of `long_` and the next word of `long_` is «بن» («مخرمة» / «مخرمة بن بكير»): the same man written short once and full once."""
    a, b = short.split(), long_.split()
    return 0 < len(a) < len(b) and b[:len(a)] == a and b[len(a)] == "بن"


def routes_equal_in_slot(first: tuple[str, ...], second: tuple[str, ...]) -> bool:
    """Same links in the same order except at most ONE slot where one side is the restated short form of the other's name (all neighbours equal)."""
    if len(first) != len(second):
        return False
    different = [(a, b) for a, b in zip(first, second) if a != b]
    return len(different) <= 1 and all(restated_short_form(a, b) or restated_short_form(b, a) for a, b in different)


def readings_agree(first: dict, second: dict, include_bracketed: bool = False) -> bool:
    """The two readings are one reading: equal canonical forms, or routes that pair off one to one (exact first, then differing in one restated-short-form slot)."""
    a, b = canonical(first, include_bracketed), canonical(second, include_bracketed)
    if a == b:
        return True
    if len(a) != len(b):
        return False
    rest_a, rest_b = sorted(a - b), sorted(b - a)
    for route in rest_a:
        match = next((other for other in rest_b if routes_equal_in_slot(route, other)), None)
        if match is None:
            return False
        rest_b.remove(match)
    return not rest_b
