"""Mechanical acceptance of a v3 chain reader output (copy of context/validate_v2.py without the text checker; see v3/AGENTS.md §validate).

    python validate_v3_1.py --packets batch-001/packets --outputs batch-001/outputs/pass-a

Chain output (shura-chain-reader-output/3 = /2 plus an optional `variant: true` on a group): levels and groups, no offsets (expand_v3_1.py computes them),
plus `status`, `needs_ruling`, `fixes`. A surface the tool cannot find after the spelling fold is the only surface error; the rest is v2's rules.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import validate as v1  # noqa: E402  (v1: parse_output only; offsets are gone from v2 chain outputs)
sys.path.insert(0, str(HERE))
from expand_v3_1 import expand  # noqa: E402
from norm import fold_loose  # noqa: E402

CHAIN_KEYS = {"id", "status", "groups", "shared_tail", "needs_ruling", "notes", "fixes"}
CHAIN_STATUS = ("read", "cannot_read_without_previous_report")
TEXT_KEYS = {"id", "text_check", "metadata_check", "fixes", "notes"}
STATUSES = ("matches", "differs", "not_checked")
CONFIDENCE = ("low", "medium", "high")
SOURCE_CODES = ("K6I", "HKG", "RWY", "THQ", "NMC", "OITI", "MSD", "SUN", "RIJ", "SWI")
CHAIN_FIX_KINDS = ("chain_differs_from_source", "wrong_identity", "lexicon_date_impossible", "lexicon_records_look_like_one_person",
                   "text_garbled", "translation_contradicts_arabic", "data_problem_other")
TEXT_FIX_KINDS = ("text_differs_from_source", "text_truncated_or_merged")
METADATA_FIX_KINDS = ("wrong_number", "wrong_book_or_chapter", "grading_missing_or_misattributed", "locator_missing")
ALL_FIX_KINDS = CHAIN_FIX_KINDS + TEXT_FIX_KINDS + METADATA_FIX_KINDS


def _strings(value) -> list[str]:
    """Every string inside a JSON value."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [str(value)]
    if isinstance(value, dict):
        return [s for item in value.values() for s in _strings(item)]
    if isinstance(value, list):
        return [s for item in value for s in _strings(item)]
    return []


def _items_with_source(context: dict, code: str) -> list:
    """Context items (dicts anywhere inside) whose `source` is `code`."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("source") == code:
                found.append(node)
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(context)
    return found


def quote_in(quote: str, haystacks: list[str]) -> bool:
    """A quote counts when it is an exact substring, or its letters-only form (norm.fold_loose) is inside one."""
    needle = fold_loose(quote)
    return bool(needle) and any(quote in h or needle in fold_loose(h) for h in haystacks)


def check_evidence(evidence: object, text: str, context: dict, where: str) -> list[str]:
    errors = []
    if not isinstance(evidence, list) or not evidence:
        return [f"evidence: {where} needs a non-empty evidence list"]
    for index, item in enumerate(evidence):
        at = f"{where}.evidence[{index}]"
        if not isinstance(item, dict) or not isinstance(item.get("source"), str) or not isinstance(item.get("quote"), str) or not item["quote"].strip():
            errors.append(f"evidence: {at} must be an object with a source and a non-empty quote")
            continue
        source, quote = item["source"], item["quote"]
        if source == "text":
            if not quote_in(quote, [text]):
                errors.append(f"evidence_quote: {at} quote is not in the text: {quote[:40]!r}")
        elif source == "online":
            locator = item.get("url") or item.get("locator")
            if not isinstance(locator, str) or not locator.strip():
                errors.append(f"evidence_online: {at} online evidence needs a url or an edition/volume/page locator")
        elif source in SOURCE_CODES:
            pool = _strings(_items_with_source(context, source)) or []
            if not quote_in(quote, pool):
                errors.append(f"evidence_quote: {at} quote is not in the {source} context item: {quote[:40]!r}")
        else:
            errors.append(f"evidence_source: {at} {source!r} is not 'text', 'online' or a source code")
    return errors


def validate_fixes(fixes: object, text: str, context: dict, allowed: tuple[str, ...] = ALL_FIX_KINDS) -> list[str]:
    if not isinstance(fixes, list):
        return ["fixes: must be a list"]
    errors = []
    for index, fix in enumerate(fixes):
        where = f"fix{index}"
        if not isinstance(fix, dict) or set(fix) != {"kind", "reason", "evidence", "confidence"}:
            errors.append(f"fix_shape: {where} must have exactly kind, reason, evidence, confidence")
            continue
        if fix["kind"] not in allowed:
            errors.append(f"fix_kind: {where} {fix['kind']!r} is not one of {', '.join(allowed)}")
        if not isinstance(fix["reason"], str) or not fix["reason"].strip():
            errors.append(f"fix_reason: {where} needs a reason")
        if fix["confidence"] not in CONFIDENCE:
            errors.append(f"fix_confidence: {where} {fix['confidence']!r} is not one of {', '.join(CONFIDENCE)}")
        errors += check_evidence(fix["evidence"], text, context, where)
    return errors


def validate_chain(output: object, text: str, expected_id: str | None = None, context: dict | None = None) -> list[str]:
    """Error strings `code: detail` for one chain-reader output (levels format, no offsets); empty means accepted."""
    context = context or {}
    if not isinstance(output, dict):
        return ["shape: output is not a JSON object"]
    errors = [f"shape: unexpected key {k}" for k in sorted(set(output) - CHAIN_KEYS)] + [f"shape: missing key {k}" for k in sorted(CHAIN_KEYS - set(output))]
    if errors:
        return errors
    if not isinstance(output["id"], str) or (expected_id is not None and output["id"] != expected_id):
        errors.append(f"id: {output['id']!r} is not {expected_id!r}")
    if output["status"] not in CHAIN_STATUS:
        errors.append(f"status: {output['status']!r} is not one of {', '.join(CHAIN_STATUS)}")
    if not isinstance(output["needs_ruling"], bool):
        errors.append("needs_ruling: must be true or false")
    if not isinstance(output["notes"], list) or not all(isinstance(n, str) for n in output["notes"]):
        errors.append("notes: must be a list of strings")
    flagged = bool(context.get("needs_previous_report"))
    if output["status"] == "cannot_read_without_previous_report":
        if not flagged:
            errors.append("status: cannot_read_without_previous_report is only for a packet flagged needs_previous_report")
        if output["groups"] != [] or output["shared_tail"] is not None:
            errors.append("status: cannot_read_without_previous_report must have groups [] and shared_tail null")
    elif flagged:
        errors.append("needs_previous_report: the packet flags this report; return status cannot_read_without_previous_report, not a short chain")
    if output["status"] == "read" or not errors:
        reading, expand_errors = expand(output, text, context)
        errors += expand_errors
        refs = {item.get("ref"): item for key in ("previous_reports",) for item in context.get(key, []) or []}
        if context.get("parent_report"):
            refs["parent"] = context["parent_report"]
        for levels in [g.get("levels", []) for g in output["groups"] if isinstance(g, dict)] + [output["shared_tail"] or []]:
            for level in levels:
                for item in level if isinstance(level, list) else []:
                    if isinstance(item, dict) and item.get("kind") == "inherited":
                        source = refs.get(item.get("from"))
                        if source is None:
                            errors.append(f"inherited: from {item.get('from')!r} is not a previous_reports/parent_report ref of the context")
                        elif not quote_in(item.get("surface", ""), [source.get("chain_text", ""), source.get("text_head", "")]):
                            errors.append(f"inherited: {item.get('surface')!r} is not in the text of {item.get('from')}")
        if reading is not None:
            for r, route in enumerate(reading["routes"]):
                for l, link in enumerate(route["links"]):
                    if link["kind"] == "imam_in_text":
                        if (context.get("work") or {}).get("tradition") not in (None, "imami"):
                            errors.append(f"imam_in_text: r{r}l{l} is for Imami reports only")
                        if l != len(route["links"]) - 1:
                            errors.append(f"imam_in_text: r{r}l{l} must be the last link of its route")
    errors += validate_fixes(output["fixes"], text, context)
    return errors


def validate_v3_1(output: object, text: str, expected_id: str | None = None, context: dict | None = None) -> list[str]:
    return validate_chain(output, text, expected_id, context)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--packets", required=True, help="directory of packet-NN.jsonl (the packets the readers were given)")
    parser.add_argument("--outputs", required=True)
    args = parser.parse_args(argv)
    packets = {}
    for path in sorted(Path(args.packets).glob("packet-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                packets[row["id"]] = row
    bad = 0
    for report_id, row in packets.items():
        path = Path(args.outputs) / f"{report_id}.json"
        if not path.is_file():
            print(f"{report_id}	missing")
            bad += 1
            continue
        try:
            parsed, _ = v1.parse_output(path.read_text(encoding="utf-8"))
        except ValueError as error:
            print(f"{report_id}	not_json	{error}")
            bad += 1
            continue
        errors = validate_v3_1(parsed, row["text"], report_id, row.get("context"))
        if errors:
            bad += 1
            print(f"{report_id}	invalid	{errors[0]}")
    print(f"valid {len(packets) - bad}/{len(packets)}", file=sys.stderr)
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
