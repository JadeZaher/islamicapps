"""Re-score the pilot under the v1.1 rules against the ADJUDICATED verdicts (adjudication/items.tsv), per item (reviewer/README-v1_1.md §5).

    python -B -X utf8 reviewer/pilot-001/rescore_v1_1.py [--out reviewer/pilot-001/rescore_v1_1.json] [--markdown reviewer/pilot-001/RESCORE_V1_1.md]      (from chain-reader/)

The pilot ran under prompt v1.0.0, so its outputs are validated per item against prompt_version 1.0.0 with the v1.1 per-item validator (an invalid item is recorded invalid and would be re-queued).
For each item: the adjudicated truth (`actual`), the reviewer's decision, its effective decision (a correction equal to the reading is a confirmation), what the v1.1 rule does with it
(apply / label / queue / hold / requeue) and whether that outcome is right; beside it what v1's rule would have done. Nothing is run or written beyond the two output files.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REVIEWER = HERE.parent
sys.path.insert(0, str(REVIEWER))
import review_rules  # noqa: E402  (v1, for the comparison)
import review_rules_v1_1 as rules  # noqa: E402
from validate_review_v1_1 import validate_output  # noqa: E402


def assess(actual: str, status: str, action: str, blocked: list[str]) -> str:
    """Is the outcome right, given the adjudicated truth about the reading? right / contained / wrong."""
    shown = status == "applied"
    if actual in ("right", "assumed_right"):
        if action in ("apply_reading", "label_ai_reviewed"):
            return "right"
        if action == "requeue" and shown:
            return "right (stays as it was; re-queued)"
        if action in ("keep_held", "queue_for_human") and blocked:
            return "held by design (a non-clearable hold stands: only a human clears it)"
        return "wrong: a right reading is " + {"keep_held": "left held", "queue_for_human": "queued, not applied", "label_disputed": "labelled disputed", "revert_to_stored": "reverted", "discard_reading": "set aside", "requeue": "left held (re-queued)"}.get(action, action)
    if actual == "wrong":
        if action in ("apply_reading", "label_ai_reviewed", "apply_reader_a", "apply_reader_b"):
            return "wrong: a wrong reading is confirmed"
        if action in ("keep_held", "queue_for_human", "discard_reading", "requeue") and not shown:
            return "right (a wrong reading stays off the page)"
        if action == "label_disputed":
            return "contained (the wrong reading stays on the page, labelled disputed; correction queued)"
        if action == "revert_to_stored":
            return "contained (reverted to the stored chain)"
        return "contained (wrong reading stays on the page, unlabelled until the re-run)" if shown else "right (a wrong reading stays off the page)"
    if actual == "unruled":
        return "right (held; the owner's question is open)" if action in ("keep_held", "queue_for_human") else "wrong: an unruled reading is " + action
    return "?"


def rescore() -> dict:
    with (HERE / "adjudication" / "items.tsv").open(encoding="utf-8", newline="") as handle:
        truth = {row["opaque"]: row for row in csv.DictReader(handle, delimiter="\t")}
    items, validity, reviews = {}, {}, {}
    for packet_path in sorted((HERE / "packets").glob("packet-*.json")):
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        output = json.loads((HERE / "outputs" / "pass-1" / packet_path.name.replace(".json", ".output.json")).read_text(encoding="utf-8"))
        items.update({item["id"]: item for item in packet["items"]})
        result = validate_output(output, packet, "1.0.0")
        for i in [item["id"] for item in packet["items"]]:
            validity[i] = result["items"][i]
        reviews.update({r["id"]: r for r in output["reviews"]})
    rows = []
    for opaque, item in sorted(items.items()):
        t, review = truth[opaque], reviews[opaque]
        codes = [h["code"] for h in item["holds"]]
        agreed_empty = bool(item["readers_agree"] and item["readers"]["A"].get("valid") and not item["readers"]["A"].get("routes"))
        valid = not validity[opaque]
        has_correction = valid and isinstance(review["corrected_reading"], dict)
        is_ = rules.correction_is(item, review["corrected_reading"]) if has_correction else None
        stored_same = rules.stored_equals_reading(item)
        if valid:
            action = rules.outcome(item["status"], review["decision"], codes, item["readers_agree"], agreed_empty, None, stored_equals_reading=stored_same, correction_is=is_, has_correction=has_correction)
            old = review_rules.outcome(item["status"], review["decision"], codes, item["readers_agree"], agreed_empty, None)
            effective = rules.effective_decision(review["decision"], item["readers_agree"], is_)
        else:
            action, old, effective = "requeue", "requeue (the whole packet was lost)", "invalid"
        # what a faithful second run (same routes) would add, for the corrections that need one
        second = None
        if valid and rules.needs_second_pass(review["decision"], is_, agreed_empty, has_correction):
            second = rules.outcome(item["status"], review["decision"], codes, item["readers_agree"], agreed_empty, True, stored_equals_reading=stored_same, correction_is=is_, has_correction=has_correction)
        rows.append({"opaque": opaque, "status": item["status"], "actual": t["actual"], "decision": review["decision"], "valid": valid, "effective": effective, "correction_check": t["correction_check"],
                     "stored_equals_reading": stored_same, "v1_1_outcome": action, "v1_1_class": "requeue" if action == "requeue" else rules.ACTION_CLASS[action], "v1_1_assessment": assess(t["actual"], item["status"], action, rules.blocking_codes(codes)), "blocking_holds": rules.blocking_codes(codes),
                     "v1_outcome": old, "after_matching_second_run": second, "invalid_reason": "" if valid else validity[opaque][0]})
    by = lambda a: [r for r in rows if r["actual"] in a]  # noqa: E731
    wrong, right, unruled = by(("wrong",)), by(("right", "assumed_right")), by(("unruled",))
    confirmed = lambda r: r["effective"] == "confirm_reading"  # noqa: E731
    summary = {
        "items": len(rows), "valid_items": sum(r["valid"] for r in rows), "invalid_items": [(r["opaque"], r["invalid_reason"]) for r in rows if not r["valid"]],
        "actually_wrong": {"n": len(wrong), "caught (any non-confirmation; an invalid item stays as it was)": sum(not confirmed(r) for r in wrong), "confirmed (missed)": sum(confirmed(r) for r in wrong),
                           "by_decision": dict(Counter(r["decision"] if r["valid"] else "invalid (re-queued)" for r in wrong))},
        "actually_right": {"n": len(right), "confirmed (incl. corrections with the readers' own routes)": sum(confirmed(r) for r in right),
                           "of which cosmetic corrections counted as confirmations": sum(confirmed(r) and r["decision"] == "confirm_with_correction" for r in right),
                           "corrected substantively": sum(r["effective"] == "confirm_with_correction" for r in right), "referred": sum(r["effective"] == "refer_to_human" for r in right)},
        "unruled": {"n": len(unruled), "referred": sum(r["decision"] == "refer_to_human" for r in unruled)},
        "outcome_class_by_truth": {f"{a}: {c}": n for (a, c), n in sorted(Counter((("right" if r["actual"] == "assumed_right" else r["actual"]), r["v1_1_class"]) for r in rows).items())},
        "outcome_assessment": dict(Counter(r["v1_1_assessment"] for r in rows).most_common()),
        "v1_1_outcomes": dict(Counter(f"{r['actual']}: {r['v1_1_outcome']}" for r in rows).most_common()),
        "v1_outcomes": dict(Counter(f"{r['actual']}: {r['v1_outcome']}" for r in rows).most_common()),
        "applied_items_not_confirmed": [{k: r[k] for k in ("opaque", "actual", "decision", "effective", "stored_equals_reading", "v1_outcome", "v1_1_outcome", "v1_1_assessment")} for r in rows if r["status"] == "applied" and r["effective"] != "confirm_reading"],
        "after_matching_second_run": dict(Counter(f"{r['correction_check'] or '-'} -> {r['after_matching_second_run']}" for r in rows if r["after_matching_second_run"])),
        "rows": rows,
    }
    return summary


def markdown(s: dict) -> str:
    lines = ["# Pilot 001 re-scored under reviewer v1.1 (per item, against the adjudicated verdicts)", "",
             f"{s['items']} items; {s['valid_items']} valid reviews under per-item validation; invalid: {s['invalid_items']}.", "",
             "| adjudicated | item | status | reviewer | effective | v1 rule | v1.1 rule | assessment |", "|---|---|---|---|---|---|---|---|"]
    for r in sorted(s["rows"], key=lambda r: (r["actual"], r["opaque"])):
        if r["actual"] == "assumed_right" and r["effective"] == "confirm_reading":
            continue
        lines.append(f"| {r['actual']} | {r['opaque']} | {r['status']} | {r['decision'] if r['valid'] else 'invalid'} | {r['effective']} | {r['v1_outcome']} | {r['v1_1_outcome']} | {r['v1_1_assessment']} |")
    lines += ["", "26 items both the judge and the reviewer called right and the adjudicator did not read (`assumed_right`) are confirmed and omitted above: all apply or get the AI-reviewed label.", ""]
    for key in ("actually_wrong", "actually_right", "unruled", "outcome_class_by_truth", "outcome_assessment", "applied_items_not_confirmed", "after_matching_second_run"):
        lines += [f"## {key}", "```", json.dumps(s[key], ensure_ascii=False, indent=1), "```", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out")
    parser.add_argument("--markdown")
    args = parser.parse_args(argv)
    result = rescore()
    if args.out:
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    if args.markdown:
        Path(args.markdown).write_text(markdown(result), encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
