"""Mechanical acceptance of a v2 reader output: v1's rules plus derived link kinds and the fix / text_check / metadata_check parts.

    python validate_v2.py --kind chain|text --packets pilot-v2/packets --outputs outputs/<run> 

Chain output (shura-chain-reader-output/2): levels and groups, no offsets (expand.py computes them), plus `status`, `needs_ruling`, `fixes`. Text output
(shura-text-checker-output/1): {id, text_check, metadata_check, fixes, notes}. Design notes: AGENTS.md section validate_v2.
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
from expand import expand  # noqa: E402
from norm import fold_exact, fold_loose  # noqa: E402

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


def _check_part(part: object, name: str, text: str, context: dict, fixes: list, fix_kinds: tuple[str, ...], ours_pools: list[str]) -> list[str]:
    errors = []
    if not isinstance(part, dict) or not {"status", "compared", "differences"} <= set(part) or not set(part) <= {"status", "compared", "differences", "reason"}:
        return [f"{name}: must be an object with status, compared, differences (and reason when not_checked)"]
    status = part["status"]
    if status not in STATUSES:
        return [f"{name}_status: {status!r} is not one of {', '.join(STATUSES)}"]
    if not isinstance(part["compared"], list) or not all(isinstance(c, str) for c in part["compared"]):
        errors.append(f"{name}_compared: must be a list of source codes and/or URLs")
    if status == "not_checked":
        if not isinstance(part.get("reason"), str) or not part["reason"].strip():
            errors.append(f"{name}_reason: not_checked needs a reason")
        if part["differences"]:
            errors.append(f"{name}_differences: not_checked cannot list differences")
        return errors
    if not part["compared"]:
        errors.append(f"{name}_compared: {status} must say what was compared")
    for c in part["compared"] if isinstance(part["compared"], list) else []:
        if isinstance(c, str) and c not in SOURCE_CODES and not re.match(r"https?://", c):
            errors.append(f"{name}_compared: {c!r} is neither a source code nor a URL")
    if status == "matches" and part["differences"]:
        errors.append(f"{name}_differences: matches cannot list differences")
    if status == "differs":
        if not part["differences"]:
            errors.append(f"{name}_differences: differs needs at least one difference")
        if not any(isinstance(f, dict) and f.get("kind") in fix_kinds for f in fixes if isinstance(f, dict)):
            errors.append(f"{name}_fix: differs needs a proposed fix of kind {', '.join(fix_kinds)}")
    for index, diff in enumerate(part["differences"] if isinstance(part["differences"], list) else []):
        at = f"{name}.differences[{index}]"
        if not isinstance(diff, dict) or not {"ours", "theirs", "source"} <= set(diff) or not set(diff) <= {"ours", "theirs", "source", "field", "url"}:
            errors.append(f"difference_shape: {at} needs ours, theirs, source (field and url optional)")
            continue
        source = diff["source"]
        if not isinstance(diff["ours"], str) or not isinstance(diff["theirs"], str) or not diff["ours"].strip() and not diff["theirs"].strip():
            errors.append(f"difference_quote: {at} ours/theirs must be quoted strings")
            continue
        if diff["ours"].strip() and not quote_in(diff["ours"], ours_pools):
            errors.append(f"difference_quote: {at} ours is not in the stored text/metadata: {diff['ours'][:40]!r}")
        if source == "online":
            if not (isinstance(diff.get("url"), str) and diff["url"].strip()):
                errors.append(f"difference_online: {at} an online claim needs the url (or edition, volume, page) of the page")
        elif source in SOURCE_CODES:
            if diff["theirs"].strip() and not quote_in(diff["theirs"], _strings(_items_with_source(context, source))):
                errors.append(f"difference_quote: {at} theirs is not in the {source} context item: {diff['theirs'][:40]!r}")
        else:
            errors.append(f"difference_source: {at} {source!r} is not 'online' or a source code")
    return errors


def validate_text(output: object, text: str, expected_id: str | None = None, context: dict | None = None) -> list[str]:
    """Error strings for one text/metadata checker output."""
    context = context or {}
    if not isinstance(output, dict):
        return ["shape: output is not a JSON object"]
    errors = [f"shape: unexpected key {k}" for k in sorted(set(output) - TEXT_KEYS)] + [f"shape: missing key {k}" for k in sorted(TEXT_KEYS - set(output))]
    if errors:
        return errors
    if not isinstance(output["id"], str) or (expected_id is not None and output["id"] != expected_id):
        errors.append(f"id: {output['id']!r} is not {expected_id!r}")
    if not isinstance(output["notes"], list) or not all(isinstance(n, str) for n in output["notes"]):
        errors.append("notes: must be a list of strings")
    fixes = output["fixes"]
    meta = (context.get("text_and_metadata") or {}).get("metadata", {})
    errors += _check_part(output["text_check"], "text_check", text, context, fixes, TEXT_FIX_KINDS, [text])
    errors += _check_part(output["metadata_check"], "metadata_check", text, context, fixes, METADATA_FIX_KINDS, _strings(meta.get("ours", {})) + _strings(meta.get("gradings", [])) + [text])
    errors += validate_fixes(fixes, text, context, TEXT_FIX_KINDS + METADATA_FIX_KINDS + ("data_problem_other", "text_garbled", "translation_contradicts_arabic"))
    return errors


def validate_v2(kind: str, output: object, text: str, expected_id: str | None = None, context: dict | None = None) -> list[str]:
    return (validate_chain if kind == "chain" else validate_text)(output, text, expected_id, context)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kind", choices=("chain", "text"), required=True)
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
            print(f"{report_id}\tmissing")
            bad += 1
            continue
        try:
            parsed, _ = v1.parse_output(path.read_text(encoding="utf-8"))
        except ValueError as error:
            print(f"{report_id}\tnot_json\t{error}")
            bad += 1
            continue
        errors = validate_v2(args.kind, parsed, row["text"], report_id, row.get("context"))
        if errors:
            bad += 1
            print(f"{report_id}\tinvalid\t{errors[0]}")
    print(f"valid {len(packets) - bad}/{len(packets)}", file=sys.stderr)
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
