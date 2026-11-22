"""The tool side of a v2 chain reading: levels to routes, offsets from surfaces, the compiler head, matn_start.

The reader writes {"groups": [{"levels": [[item, ...], ...]}, ...], "shared_tail": [[item, ...], ...] | null}; an item is
{"surface", "kind", "occurrence"?, "from"?}. Each level lists co-transmitters; a group is one family of routes (one taḥwīl
branch); the shared tail is what the text writes once after the groups meet. This module expands that to the stored shape
(routes of links with offsets) that v1's scorer and the fix pipeline use. See ../AGENTS.md section expand.
"""

from __future__ import annotations

import itertools
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from norm import MARKS, fold_loose  # noqa: E402

READER_KINDS = ("narrator", "unnamed", "back_reference", "relation", "imam_in_text", "inherited")
DERIVED_KINDS = ("compiler_head", "inherited")       # no offsets
MAX_EXPANSION = 400                                  # beyond this the reading is held, not expanded
ITEM_KEYS = {"surface", "kind", "occurrence", "from"}


def _stripped(text: str) -> tuple[str, list[int]]:
    kept = [i for i, ch in enumerate(text) if not MARKS.match(ch)]
    return "".join(text[i] for i in kept), kept


def _find(stripped: str, needle: str, cursor: int, occurrence: int | None) -> tuple[int, int] | None:
    """(start, end) in the stripped text of the first match at/after `cursor` (or the Nth match overall); words may be split by a comma or a space."""
    pattern = re.compile(r"[\s،,]+".join(re.escape(word) for word in needle.split()))
    matches = list(pattern.finditer(stripped))
    if occurrence:
        return (matches[occurrence - 1].start(), matches[occurrence - 1].end()) if len(matches) >= occurrence else None
    for match in matches:
        if match.start() >= cursor:
            return match.start(), match.end()
    return None


def _locate(item: dict, text: str, stripped: str, kept: list[int], cursor: int, where: str, errors: list[str]) -> dict | None:
    """The item as a link: offsets in `text` found from the surface (diacritics ignored), the first occurrence at/after `cursor` or the stated one."""
    kind = item["kind"]
    if kind == "inherited":
        return {"surface": item["surface"], "start": None, "end": None, "kind": "inherited", "from": item.get("from")}
    needle = "".join(ch for ch in item["surface"] if not MARKS.match(ch)).strip()
    if not needle:
        errors.append(f"surface: {where} is empty")
        return None
    occurrence = item.get("occurrence")
    found = _find(stripped, needle, cursor, occurrence)
    if found is None:
        anywhere = _find(stripped, needle, 0, occurrence)
        errors.append(f"occurrence: {where} {item['surface']!r} occurrence {occurrence} is not in the text" if anywhere is None and occurrence else
                      f"surface_not_in_text: {where} {item['surface']!r}" if anywhere is None else f"order: {where} {item['surface']!r} occurs only before the previous level")
        return None
    at, stop = found
    start, end = kept[at], kept[stop - 1] + 1
    while end < len(text) and MARKS.match(text[end]):
        end += 1
    return {"surface": text[start:end], "start": start, "end": end, "kind": kind}


def check_shape(output: dict) -> list[str]:
    errors = []
    if not isinstance(output.get("groups"), list):
        return ["shape: groups must be a list"]
    levels_lists = [("g%d" % g, group.get("levels") if isinstance(group, dict) else None) for g, group in enumerate(output["groups"])]
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
                elif item["kind"] == "inherited" and not item.get("from"):
                    errors.append(f"inherited: {at} needs `from` (the ref of the previous report it comes from)")
                elif "occurrence" in item and not (isinstance(item["occurrence"], int) and not isinstance(item["occurrence"], bool) and item["occurrence"] >= 1):
                    errors.append(f"occurrence: {at} must be a whole number from 1")
    return errors


def expand(output: dict, text: str, context: dict | None = None) -> tuple[dict | None, list[str]]:
    """(stored-shape reading, errors). The reading is None when the shape or a surface is wrong."""
    errors = check_shape(output)
    if errors:
        return None, errors
    stripped, kept = _stripped(text)
    group_routes: list[list[list[dict]]] = []
    furthest = 0
    for g, group in enumerate(output["groups"]):
        cursor, levels = 0, []
        for l, level in enumerate(group["levels"]):
            located = [_locate(item, text, stripped, kept, cursor, f"g{g}l{l}i{i}", errors) for i, item in enumerate(level)]
            if any(x is None for x in located):
                levels.append([])
                continue
            ends = [x["end"] for x in located if x["end"] is not None]
            if ends:
                cursor = len(_stripped(text[:max(ends)])[0])
            levels.append(located)
        furthest = max(furthest, cursor)
        group_routes.append(levels)
    tail_levels = []
    if output.get("shared_tail"):
        cursor = furthest
        for l, level in enumerate(output["shared_tail"]):
            located = []
            for i, item in enumerate(level):
                trial: list[str] = []
                link = _locate(item, text, stripped, kept, cursor, f"tail l{l}i{i}", trial) or _locate(item, text, stripped, kept, 0, f"tail l{l}i{i}", errors)
                located.append(link)
            if any(x is None for x in located):
                tail_levels.append([])
                continue
            ends = [x["end"] for x in located if x["end"] is not None]
            if ends:
                cursor = len(_stripped(text[:max(ends)])[0])
            tail_levels.append(located)
    if errors:
        return None, errors
    size = sum(_product_size(levels) for levels in group_routes) * max(1, _product_size(tail_levels) if tail_levels else 1)
    if size > MAX_EXPANSION:
        return None, [f"too_many_routes: the levels expand to {size} routes (limit {MAX_EXPANSION}); split the reading into groups or file it"]
    routes, seen = [], set()
    tails = list(itertools.product(*tail_levels)) if tail_levels else [()]
    for levels in group_routes:
        for head in itertools.product(*levels):
            for tail in tails:
                links = list(head) + list(tail)
                key = tuple((l["start"], l["end"], l["surface"]) for l in links)
                if key in seen:
                    continue
                seen.add(key)
                routes.append({"links": links, "shared_tail_from": len(head) if tail_levels else None})
    compiler = (((context or {}).get("work") or {}).get("compiler") or {})
    if compiler.get("head_of_every_chain") and compiler.get("ar"):
        for route in routes:
            if any(compiler["ar"] and fold_loose(compiler["ar"]) in fold_loose(link["surface"]) for link in route["links"] if link["start"] is not None):
                continue                                          # the text writes the compiler itself: that link stands
            route["links"].insert(0, {"surface": compiler["ar"], "start": None, "end": None, "kind": "compiler_head", "from": "work"})
            if route["shared_tail_from"] is not None:
                route["shared_tail_from"] += 1
    ends = [l["end"] for r in routes for l in r["links"] if l["end"] is not None and l["kind"] != "imam_in_text"]
    result = {"id": output.get("id"), "routes": routes, "matn_start": max(ends) if ends else 0, "notes": output.get("notes", [])}
    return result, []


def _product_size(levels: list[list]) -> int:
    size = 1
    for level in levels:
        size *= max(1, len(level))
    return size


def canonical(reading: dict) -> frozenset:
    """Order-free form of a reading for agreement: the set of routes, each the folded surfaces of its non-derived links."""
    return frozenset(tuple(fold_loose(l["surface"]) for l in route["links"] if l["kind"] not in DERIVED_KINDS) for route in reading["routes"])
