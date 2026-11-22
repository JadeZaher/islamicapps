"""Mechanical checks of chain-reviewer v1.1 outputs, PER ITEM (reviewer/README-v1_1.md §1). One invalid review never voids its packet: each item is valid or invalid on its own.

    python -B -X utf8 reviewer/validate_review_v1_1.py --packet <packet.json> --output <output.json> [--allow-out-of-order]

Differences from validate_review.py (v1, untouched): prompt version 1.1.0; `question` may also be a note on a non-referral (an unruled question the item touches); `corrected_reading`
is also allowed with `refer_to_human` (the part the rulings settle); `--allow-out-of-order` validates corrected readings with out_of_order_validator.py (FORMAT_GAP.md) instead of the
reader validator. Header problems (format, specialist, version, packet id, not JSON) make every item of that output invalid: such an output cannot be trusted as a whole.
Quotes (v1.1.1, see reviewer/AGENTS.md §quote rule): an exact substring, or a substring once ONLY Arabic vowel marks, Qur'anic annotation marks and tatweel are folded out and whitespace is normalised (letters match
exactly). A quote that matches only so is valid, its stored text becomes the TEXT's own characters, and the review carries `quote_refolded: n` (n quotes changed).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_4"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
from review_rules_v1_1 import DECISIONS, OUTPUT_FORMAT, PROMPT_VERSION, SPECIALIST, UNCERTAINTY, VARIANT_VERDICTS  # noqa: E402
from validate_review import REVIEW_KEYS, quote_pool  # noqa: E402  (v1's source pools: text, prevN, context, reader_a/b, stored)
import out_of_order_validator  # noqa: E402
import validate_v3_4  # noqa: E402


# Vowel marks only: harakat U+064B-0652, superscript alef U+0670, tatweel U+0640, Qur'anic annotation marks. NOT hamza/alef/ya/ta marbuta folds (those are different words in a quote).
MARKS = re.compile("[" + "".join(chr(code) for first, last in ((0x064B, 0x0652), (0x0670, 0x0670), (0x0640, 0x0640), (0x06D6, 0x06DC), (0x06DF, 0x06E4), (0x06E7, 0x06E8), (0x06EA, 0x06ED)) for code in range(first, last + 1)) + "]")


def _folded(value: str) -> tuple[str, list[int]]:
    """`value` without marks, whitespace runs as one space, with the original index of each kept character."""
    kept, index, previous_space = [], [], False
    for position, char in enumerate(value):
        if MARKS.match(char):
            continue
        if char.isspace():
            if previous_space:
                continue
            char, previous_space = " ", True
        else:
            previous_space = False
        kept.append(char)
        index.append(position)
    return "".join(kept), index


def find_quote(quote: str, pool: list[str]) -> str | None:
    """The characters of the pool's own text that `quote` stands for: the quote itself when it is an exact substring of a pool string, else the contiguous span of a pool string whose folded form
    (marks out, whitespace normalised) contains the folded quote; None when neither."""
    if any(quote in s for s in pool):
        return quote
    needle = _folded(quote)[0].strip()
    if not needle:
        return None
    for source in pool:
        folded, index = _folded(source)
        at = folded.find(needle)
        if at >= 0:
            start, end = index[at], index[at + len(needle) - 1] + 1
            while end < len(source) and MARKS.match(source[end]):                 # the marks on the quote's last letter belong to it
                end += 1
            return source[start:end]
    return None


def check_quote(item: dict, source: object, quote: object, where: str) -> list[str]:
    """Errors for one quote; see find_quote for the rule."""
    return _check(item, source, quote, where)[0]


def _check(item: dict, source: object, quote: object, where: str) -> tuple[list[str], str | None]:
    if not isinstance(source, str) or not isinstance(quote, str) or not quote.strip():
        return [f"quote: {where} needs a source and a non-empty quote"], None
    pool = quote_pool(item, source)
    if pool is None:
        return [f"quote_source: {where} {source!r} is not text, prevN, parent, context, reader_a, reader_b or stored (or that previous report is not in the packet)"], None
    found = find_quote(quote, pool)
    if found is None:
        return [f"quote_not_exact: {where} is not an exact substring of {source} (vowel marks, tatweel and whitespace aside): {quote[:50]!r}"], None
    return [], found


def refold_quotes(review: dict, item: dict) -> tuple[dict, int]:
    """A copy of a VALID review whose quotes are the packet text's own characters, and how many quotes were changed (marked `quote_refolded` on the copy when above 0)."""
    changed = 0

    def own(source, quote):
        nonlocal changed
        found = _check(item, source, quote, "")[1]
        if found is not None and found != quote:
            changed += 1
            return found
        return quote
    copy = {**review, "reasons": [{**r, "quote": own(r["source"], r["quote"])} for r in review["reasons"]],
            "variant_verdicts": [{**v, "quote": own("text", v["quote"])} for v in review["variant_verdicts"]]}
    return ({**copy, "quote_refolded": changed} if changed else copy), changed


def validate_review(review: object, item: dict, allow_out_of_order: bool = False) -> list[str]:
    """Errors for one review of one packet item (empty: valid)."""
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
    if question is not None and not isinstance(question, str):
        errors.append(f"question: {at} is null or a string")
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
        errors += [f"variant_verdicts: {at} has no verdict for variant group {g}" for g in sorted(groups - set(named))]
        errors += [f"variant_verdicts: {at} names {g!r}, which is not a variant group of either reader" for g in sorted(set(named) - groups)]
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
    if decision == "confirm_with_correction" and not isinstance(corrected, dict):
        errors.append(f"corrected_reading: {at} confirm_with_correction gives the corrected reading")
    elif corrected is not None and decision not in ("confirm_with_correction", "refer_to_human"):
        errors.append(f"corrected_reading: {at} is null unless the decision is confirm_with_correction or refer_to_human")
    elif corrected is not None and not isinstance(corrected, dict):
        errors.append(f"corrected_reading: {at} is null or a reader output")
    elif isinstance(corrected, dict):
        check = out_of_order_validator.validate_chain if allow_out_of_order else validate_v3_4.validate_chain
        errors += [f"corrected_reading: {at} {e}" for e in check(corrected, item["text"], item["id"], item.get("context"))]
        if isinstance(corrected.get("groups"), list) and not corrected["groups"]:
            errors.append(f"corrected_reading: {at} an empty reading is `no_chain`, not a correction")
    return errors


def validate_output(output: object, packet: dict, prompt_version: str = PROMPT_VERSION, allow_out_of_order: bool = False) -> dict:
    """{"header_errors": [...], "items": {item id: [errors]}, "valid": [ids], "invalid": [ids], "reviews": {valid id: review, quotes in the text's own characters}, "refolded": {id: quotes changed},
    "unknown": [ids not in the packet]}; each item stands on its own."""
    ids = [item["id"] for item in packet["items"]]
    items = {item["id"]: item for item in packet["items"]}
    result = {"header_errors": [], "items": {i: [] for i in ids}, "unknown": []}
    header = []
    if not isinstance(output, dict):
        header.append("shape: the output is not a JSON object")
    else:
        expected = {"format": OUTPUT_FORMAT, "specialist_id": SPECIALIST, "prompt_version": prompt_version, "packet_id": packet["packet_id"]}
        header += [f"header: {key} is {output.get(key)!r}, expected {value!r}" for key, value in expected.items() if output.get(key) != value]
        if set(output) - set(expected) - {"reviews"}:
            header.append(f"shape: unexpected keys {sorted(set(output) - set(expected) - {'reviews'})}")
        if not isinstance(output.get("reviews"), list):
            header.append("shape: reviews is a list")
    if header:
        result["header_errors"] = header
        for i in ids:
            result["items"][i] = [f"packet: output unusable as a whole ({header[0]})"]
    else:
        seen: dict[str, list] = {}
        for review in output["reviews"]:
            report_id = review.get("id") if isinstance(review, dict) else None
            if report_id in items:
                seen.setdefault(report_id, []).append(review)
            else:
                result["unknown"].append(report_id)
        for i in ids:
            reviews = seen.get(i, [])
            if not reviews:
                result["items"][i] = [f"item: {i} has no review"]
            elif len(reviews) > 1:
                result["items"][i] = [f"item: {i} is reviewed {len(reviews)} times"]
            else:
                result["items"][i] = validate_review(reviews[0], items[i], allow_out_of_order)
    result["valid"] = [i for i in ids if not result["items"][i]]
    result["invalid"] = [i for i in ids if result["items"][i]]
    result["reviews"], result["refolded"] = {}, {}
    for r in (output.get("reviews") if isinstance(output, dict) and not header else []):
        if isinstance(r, dict) and r.get("id") in result["valid"]:
            result["reviews"][r["id"]], changed = refold_quotes(r, items[r["id"]])
            if changed:
                result["refolded"][r["id"]] = changed
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--packet", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--allow-out-of-order", action="store_true")
    args = parser.parse_args(argv)
    packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
    try:
        output = json.loads(Path(args.output).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as error:
        output = None
        print(f"not_json\t{error}")
    result = validate_output(output, packet, allow_out_of_order=args.allow_out_of_order)
    for i in result["invalid"]:
        print(f"invalid\t{i}\t{result['items'][i][0]}")
    print(f"{len(result['valid'])} of {len(packet['items'])} items valid; {len(result['invalid'])} invalid, to be re-queued", file=sys.stderr)
    return 0 if not result["invalid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
