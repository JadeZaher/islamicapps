"""Mechanical acceptance of one chain-reader output (see AGENTS.md §validate).

    python validate.py --reports pilot/reports.jsonl --outputs outputs/<run> [--repair]

A reader output passes when it is valid JSON of the `shura-chain-reader-output/1` shape, every link surface equals
`text[start:end]`, the links of a route follow the text order (a declared shared tail excepted), no two links of a route
overlap, no link lies in the matn, every kind is in the vocabulary and every declared shared tail is really shared.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

KINDS = ("narrator", "unnamed", "back_reference", "relation")
OUTPUT_KEYS = {"id", "routes", "matn_start", "notes"}
ROUTE_KEYS = {"links", "shared_tail_from"}
LINK_KEYS = {"surface", "start", "end", "kind"}
FENCE = re.compile(r"^\s*```(?:json)?\s*\n(.*?)\n\s*```\s*$", re.DOTALL)


def parse_output(raw: str) -> tuple[object, list[str]]:
    """JSON from the reader's raw answer; one surrounding markdown fence is stripped and reported as a warning."""
    warnings = []
    fenced = FENCE.match(raw)
    if fenced:
        raw, warnings = fenced.group(1), ["fenced"]
    return json.loads(raw), warnings


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def validate(output: object, text: str, expected_id: str | None = None) -> list[str]:
    """Error strings `code: detail` for one parsed output; an empty list means accepted."""
    if not isinstance(output, dict):
        return ["shape: output is not a JSON object"]
    errors: list[str] = []
    for key in sorted(set(output) - OUTPUT_KEYS):
        errors.append(f"shape: unexpected key {key}")
    for key in sorted(OUTPUT_KEYS - set(output)):
        errors.append(f"shape: missing key {key}")
    if errors:
        return errors
    if not isinstance(output["id"], str) or (expected_id is not None and output["id"] != expected_id):
        errors.append(f"id: {output['id']!r} is not {expected_id!r}")
    matn_start = output["matn_start"]
    if not _is_int(matn_start) or not 0 <= matn_start <= len(text):
        errors.append(f"matn_start: {matn_start!r} is not an offset inside the text")
        matn_start = None
    if not isinstance(output["notes"], list) or not all(isinstance(note, str) for note in output["notes"]):
        errors.append("notes: must be a list of strings")
    routes = output["routes"]
    if not isinstance(routes, list):
        return errors + ["shape: routes is not a list"]

    spans_of: list[list[tuple[int, int]] | None] = []      # per route, (start, end) of each link when the route is well formed
    tails: list[int | None] = []
    for r, route in enumerate(routes):
        where = f"r{r}"
        if not isinstance(route, dict) or set(route) != ROUTE_KEYS or not isinstance(route["links"], list) or not route["links"]:
            errors.append(f"shape: {where} must be an object with a non-empty links list and shared_tail_from")
            spans_of.append(None)
            tails.append(None)
            continue
        links, tail = route["links"], route["shared_tail_from"]
        if tail is not None and not (_is_int(tail) and 0 <= tail < len(links)):
            errors.append(f"shared_tail: {where} shared_tail_from {tail!r} is not an index of its links")
            tail = None
        spans, well_formed = [], True
        for l, link in enumerate(links):
            at = f"{where}l{l}"
            if not isinstance(link, dict) or set(link) != LINK_KEYS:
                errors.append(f"shape: {at} must have exactly surface, start, end, kind")
                well_formed = False
                continue
            surface, start, end, kind = link["surface"], link["start"], link["end"], link["kind"]
            if kind not in KINDS:
                errors.append(f"kind: {at} {kind!r} is not one of {', '.join(KINDS)}")
            if not (isinstance(surface, str) and _is_int(start) and _is_int(end)) or not 0 <= start < end <= len(text):
                errors.append(f"offsets: {at} start/end {start!r}/{end!r} are not a span inside the text")
                well_formed = False
                continue
            if not surface.strip():
                errors.append(f"surface: {at} is empty")
            elif text[start:end] != surface:
                errors.append(f"surface_mismatch: {at} {surface!r} != text[{start}:{end}] {text[start:end]!r}")
            if matn_start is not None and end > matn_start:
                errors.append(f"in_matn: {at} ends at {end}, matn starts at {matn_start}")
            spans.append((start, end))
        spans_of.append(spans if well_formed else None)
        tails.append(tail)
        if not well_formed:
            continue
        head = range(0, tail if tail is not None else len(links))
        rest = range(tail, len(links)) if tail is not None else range(0)
        for group in (head, rest):
            for a, b in zip(group, list(group)[1:]):
                if spans[b][0] < spans[a][1]:
                    code = "order" if spans[b][1] <= spans[a][0] else "overlap"
                    errors.append(f"{code}: {where} link {b} starts at {spans[b][0]} before link {a} ends at {spans[a][1]}")
        for a in head:                                           # the tail may sit anywhere, but never on top of the route's own links
            for b in rest:
                if spans[a][0] < spans[b][1] and spans[b][0] < spans[a][1]:
                    errors.append(f"overlap: {where} tail link {b} overlaps link {a}")
    # a declared shared tail must be the same occurrences in another route that declares one
    for r, tail in enumerate(tails):
        spans = spans_of[r]
        if tail is None or spans is None:
            continue
        for l in range(tail, len(spans)):
            if not any(o != r and tails[o] is not None and spans_of[o] is not None and spans[l] in spans_of[o][tails[o]:] for o in range(len(routes))):
                errors.append(f"shared_tail: r{r}l{l} is not written once for another route (no other route's tail has span {spans[l]})")
    seen = {}
    for r, spans in enumerate(spans_of):
        if spans is None:
            continue
        key = tuple(spans)
        if key in seen:
            errors.append(f"duplicate_route: r{r} repeats r{seen[key]}")
        seen[key] = r
    return errors


def repair_offsets(output: dict, text: str) -> dict:
    """A copy whose link offsets are re-found from the surfaces (first occurrence at or after the previous link of the route).

    Language models cannot count characters reliably; this separates a wrong reading from a wrong count. A link whose
    surface is not in the text is left alone (it then fails validation as before). Identical claimed tails repair identically.
    """
    fixed = copy.deepcopy(output)
    memo: dict[tuple[str, int, int], tuple[int, int]] = {}
    for route in fixed.get("routes", []) if isinstance(fixed, dict) else []:
        if not isinstance(route, dict) or not isinstance(route.get("links"), list):
            continue
        tail = route.get("shared_tail_from")
        cursor = 0
        for index, link in enumerate(route["links"]):
            if not isinstance(link, dict) or not isinstance(link.get("surface"), str) or not link["surface"]:
                continue
            surface, claimed = link["surface"], (link["surface"], link.get("start"), link.get("end"))
            if _is_int(tail) and index >= tail:
                if claimed not in memo:
                    hits = [m.start() for m in re.finditer(re.escape(surface), text)]
                    if not hits:
                        continue
                    near = min(hits, key=lambda h: abs(h - link["start"]) if _is_int(link.get("start")) else h)
                    memo[claimed] = (near, near + len(surface))
                link["start"], link["end"] = memo[claimed]
                continue
            found = text.find(surface, cursor)
            if found < 0:
                continue
            link["start"], link["end"] = found, found + len(surface)
            cursor = found + len(surface)
    return fixed


def load_reports(path: Path) -> dict[str, dict]:
    return {row["id"]: row for row in (json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip())}


def check_directory(reports: dict[str, dict], outputs: Path, repair: bool = False) -> dict[str, dict]:
    """Per report id: {'status': 'missing'|'not_json'|'invalid'|'valid', 'errors': [...], 'output': parsed or None, 'warnings': [...]}."""
    result = {}
    for report_id, report in reports.items():
        path = outputs / f"{report_id}.json"
        if not path.is_file():
            result[report_id] = {"status": "missing", "errors": ["missing: no output file"], "output": None, "warnings": []}
            continue
        try:
            parsed, warnings = parse_output(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeDecodeError) as error:
            result[report_id] = {"status": "not_json", "errors": [f"not_json: {error}"], "output": None, "warnings": []}
            continue
        if repair and isinstance(parsed, dict):
            parsed = repair_offsets(parsed, report["text"])
        errors = validate(parsed, report["text"], report_id)
        result[report_id] = {"status": "invalid" if errors else "valid", "errors": errors, "output": parsed, "warnings": warnings}
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--reports", required=True, help="pilot/reports.jsonl")
    parser.add_argument("--outputs", required=True, help="directory of <report id>.json")
    parser.add_argument("--repair", action="store_true", help="re-find offsets from surfaces before validating")
    args = parser.parse_args(argv)
    checked = check_directory(load_reports(Path(args.reports)), Path(args.outputs), args.repair)
    for report_id, outcome in checked.items():
        if outcome["status"] != "valid":
            print(f"{report_id}\t{outcome['status']}\t{outcome['errors'][0]}")
    valid = sum(1 for o in checked.values() if o["status"] == "valid")
    print(f"valid {valid}/{len(checked)}", file=sys.stderr)
    return 0 if valid == len(checked) else 1


if __name__ == "__main__":
    raise SystemExit(main())
