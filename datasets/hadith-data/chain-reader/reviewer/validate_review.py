"""Mechanical checks of one chain-reviewer output against its packet (reviewer/README.md §validation). It never judges a decision.

    python -B -X utf8 reviewer/validate_review.py --packet <packet.json> --output <output.json>

Checks: format, specialist, prompt version and packet id; one review per item, no unknown item; the decision vocabulary and its preconditions (confirm only an agreed
reading, prefer a reader only when they differ and that reader is valid); `question` for `refer_to_human`; at least one reason, each quote an EXACT substring of the
source it names (`text`, `prevN` / `parent`, `context`, `reader_a` / `reader_b`, `stored`); one verdict for every variant group of either reader, from the vocabulary,
quoting the text; `corrected_reading` for `confirm_with_correction` only, valid under the v3.4 reader validator (validate_v3_4); uncertainty from the vocabulary.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_4"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
from review_rules import DECISIONS, OUTPUT_FORMAT, SPECIALIST, UNCERTAINTY, VARIANT_VERDICTS  # noqa: E402
from validate_v3_4 import validate_chain  # noqa: E402

REVIEW_KEYS = {"id", "decision", "question", "reasons", "variant_verdicts", "corrected_reading", "uncertainty", "uncertainty_note"}


def strings(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for item in value.values() for s in strings(item)]
    if isinstance(value, list):
        return [s for item in value for s in strings(item)]
    return []


def quote_pool(item: dict, source: str) -> list[str] | None:
    """The strings a quote with this `source` must stand in (None: an unknown source)."""
    context = item.get("context") or {}
    if source == "text":
        return [item["text"]]
    if source.startswith("prev") or source == "parent":
        found = [p for p in context.get("previous_reports") or [] if p.get("ref") == source] + ([context["parent_report"]] if source == "parent" and context.get("parent_report") else [])
        return [s for p in found for s in (p.get("chain_text") or "", p.get("text_head") or "")] if found else None
    if source == "context":
        return strings(context)
    if source in ("reader_a", "reader_b"):
        reader = (item.get("readers") or {}).get(source[-1].upper()) or {}
        return strings({key: reader.get(key) for key in ("notes", "groups", "routes", "variant_groups")})
    if source == "stored":
        return strings(item.get("stored_chain"))
    return None


def check_quote(item: dict, source: object, quote: object, where: str) -> list[str]:
    if not isinstance(source, str) or not isinstance(quote, str) or not quote.strip():
        return [f"quote: {where} needs a source and a non-empty quote"]
    pool = quote_pool(item, source)
    if pool is None:
        return [f"quote_source: {where} {source!r} is not text, prevN, parent, context, reader_a, reader_b or stored (or that previous report is not in the packet)"]
    if not any(quote in s for s in pool):
        return [f"quote_not_exact: {where} is not an exact substring of {source}: {quote[:50]!r}"]
    return []


def validate_review(review: object, item: dict) -> list[str]:
    """Errors for one review of one packet item."""
    if not isinstance(review, dict):
        return ["shape: a review is an object"]
    at = review.get("id", "?")
    errors = [f"shape: {at} unexpected key {k}" for k in sorted(set(review) - REVIEW_KEYS)] + [f"shape: {at} missing key {k}" for k in sorted(REVIEW_KEYS - set(review))]
    if errors:
        return errors
    decision = review["decision"]
    readers = item.get("readers") or {}
    if decision not in DECISIONS:
        return [f"decision: {at} {decision!r} is not one of {', '.join(DECISIONS)}"]
    if decision == "confirm_reading" and not item.get("readers_agree"):
        errors.append(f"decision: {at} confirm_reading needs an agreed reading; the readers differ (prefer one, correct, or refer)")
    if decision in ("prefer_reader_a", "prefer_reader_b"):
        tag = decision[-1].upper()
        if item.get("readers_agree"):
            errors.append(f"decision: {at} {decision} is only for readers who differ")
        elif not (readers.get(tag) or {}).get("valid"):
            errors.append(f"decision: {at} {decision}: reader {tag}'s output is not valid")
    question = review["question"]
    if decision == "refer_to_human" and not (isinstance(question, str) and question.strip()):
        errors.append(f"question: {at} refer_to_human names the unruled question or what cannot be told")
    if decision != "refer_to_human" and question not in (None, ""):
        errors.append(f"question: {at} is null unless the decision is refer_to_human")
    if review["uncertainty"] not in UNCERTAINTY:
        errors.append(f"uncertainty: {at} {review['uncertainty']!r} is not one of {', '.join(UNCERTAINTY)}")
    if not isinstance(review["uncertainty_note"], str):
        errors.append(f"uncertainty_note: {at} is a string")
    reasons = review["reasons"]
    if not isinstance(reasons, list) or not reasons:
        errors.append(f"reasons: {at} needs at least one reason with a quote")
    else:
        for index, reason in enumerate(reasons):
            where = f"{at}.reasons[{index}]"
            if not isinstance(reason, dict) or set(reason) != {"claim", "source", "quote"} or not isinstance(reason.get("claim"), str) or not reason["claim"].strip():
                errors.append(f"reasons: {where} is {{claim, source, quote}} with a claim")
                continue
            errors += check_quote(item, reason["source"], reason["quote"], where)
    groups = {g["group"] for tag in ("A", "B") for g in (readers.get(tag) or {}).get("variant_groups") or []}
    verdicts = review["variant_verdicts"]
    if not isinstance(verdicts, list):
        errors.append(f"variant_verdicts: {at} is a list")
    else:
        named = [v.get("group") for v in verdicts if isinstance(v, dict)]
        for group in sorted(groups - set(named)):
            errors.append(f"variant_verdicts: {at} has no verdict for variant group {group}")
        for group in sorted(set(named) - groups):
            errors.append(f"variant_verdicts: {at} names {group!r}, which is not a variant group of either reader")
        if len(named) != len(set(named)):
            errors.append(f"variant_verdicts: {at} gives a group two verdicts")
        for index, verdict in enumerate(verdicts):
            where = f"{at}.variant_verdicts[{index}]"
            if not isinstance(verdict, dict) or set(verdict) != {"group", "verdict", "quote"}:
                errors.append(f"variant_verdicts: {where} is {{group, verdict, quote}}")
                continue
            if verdict["verdict"] not in VARIANT_VERDICTS:
                errors.append(f"variant_verdicts: {where} {verdict['verdict']!r} is not one of {', '.join(VARIANT_VERDICTS)}")
            errors += check_quote(item, "text", verdict["quote"], where)
    corrected = review["corrected_reading"]
    if decision == "confirm_with_correction":
        if not isinstance(corrected, dict):
            errors.append(f"corrected_reading: {at} confirm_with_correction gives the corrected reading")
        else:
            errors += [f"corrected_reading: {at} {e}" for e in validate_chain(corrected, item["text"], item["id"], item.get("context"))]
            if isinstance(corrected.get("groups"), list) and not corrected["groups"]:
                errors.append(f"corrected_reading: {at} an empty reading is `no_chain`, not a correction")
    elif corrected is not None:
        errors.append(f"corrected_reading: {at} is null unless the decision is confirm_with_correction")
    return errors


def validate_output(output: object, packet: dict, prompt_version: str = "1.0.0") -> list[str]:
    """Errors for a whole output against its packet; empty means accepted."""
    if not isinstance(output, dict):
        return ["shape: the output is not a JSON object"]
    errors = []
    expected = {"format": OUTPUT_FORMAT, "specialist_id": SPECIALIST, "prompt_version": prompt_version, "packet_id": packet["packet_id"]}
    errors += [f"header: {key} is {output.get(key)!r}, expected {value!r}" for key, value in expected.items() if output.get(key) != value]
    if set(output) - set(expected) - {"reviews"}:
        errors.append(f"shape: unexpected keys {sorted(set(output) - set(expected) - {'reviews'})}")
    reviews = output.get("reviews")
    if not isinstance(reviews, list):
        return errors + ["shape: reviews is a list"]
    items = {item["id"]: item for item in packet["items"]}
    seen: dict[str, int] = {}
    for review in reviews:
        report_id = review.get("id") if isinstance(review, dict) else None
        if report_id not in items:
            errors.append(f"item: {report_id!r} is not an item of the packet")
            continue
        seen[report_id] = seen.get(report_id, 0) + 1
        errors += validate_review(review, items[report_id])
    errors += [f"item: {i} is reviewed {n} times" for i, n in seen.items() if n > 1]
    errors += [f"item: {i} has no review" for i in items if i not in seen]
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--packet", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    try:
        output = json.loads(Path(args.output).read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        print(f"not_json\t{error}")
        return 1
    errors = validate_output(output, packet)
    for error in errors:
        print(error)
    print(f"{'valid' if not errors else 'invalid'}: {len(errors)} errors", file=sys.stderr)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
