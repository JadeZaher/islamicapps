"""Score the chain reviewer's pilot decisions against the tranche-02 judge (reviewer/README.md §pilot).

    python -B -X utf8 reviewer/pilot-001/score_reviewer.py [--pass 1] [--out reviewer/pilot-001/score.json]      (from chain-reader/)

Reads packets/, outputs/pass-N/packet-NN.output.json (each validated with validate_review.py; an invalid output is counted, never scored) and private/key.tsv (the judge's verdicts).
The judge's verdict on a reading: right (R, RO), wrong (W) or cannot tell (CT). A variant-held reading also counts as wrong when the judge found its variant group a genuine
route (`group_is` = genuine_route): applying it would drop a real route. The reviewer "accepts" a reading with `confirm_reading` (or `no_chain` on an agreed empty reading) and
"rejects" it with any other decision; `refer_to_human` is reported apart as well. Reported: agreement per outcome; of the judge-wrong readings, how many the reviewer catches;
of the judge-right, how many it wrongly rejects, needlessly corrects, or refers; the cannot-tell ones; the variant-group verdicts against the judge's `group_is`; and what
the decision rule (review_rules.outcome) would do with each, with the judge's verdict beside it.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEWER = HERE.parent
sys.path.insert(0, str(REVIEWER))
from review_rules import outcome  # noqa: E402
from validate_review import validate_output  # noqa: E402

VARIANT_WORD = {"remark": "remark_about_another_version", "genuine_route": "route_of_this_saying"}       # the judge's `group_is`; `spurious` (no remark in the text) is not scored


def judge_class(row: dict) -> str:
    if row["judge_reader"] == "W" or row["judge_group"] == "genuine_route":
        return "wrong"
    if row["judge_reader"] in ("R", "RO"):
        return "right"
    return "cannot_tell"


def accepts(review: dict, item: dict) -> bool:
    agreed_empty = item["readers_agree"] and item["readers"]["A"].get("valid") and not item["readers"]["A"].get("routes")
    return review["decision"] == "confirm_reading" or (review["decision"] == "no_chain" and bool(agreed_empty))


def score(base: Path, pass_number: int) -> dict:
    with (base / "private" / "key.tsv").open(encoding="utf-8", newline="") as handle:
        key = {row["opaque"]: row for row in csv.DictReader(handle, delimiter="\t")}
    reviews, items, invalid = {}, {}, []
    for packet_path in sorted((base / "packets").glob("packet-*.json")):
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        items.update({item["id"]: item for item in packet["items"]})
        output_path = base / "outputs" / f"pass-{pass_number}" / packet_path.name.replace(".json", ".output.json")
        if not output_path.is_file():
            invalid.append(f"{packet_path.name}: no output")
            continue
        output = json.loads(output_path.read_text(encoding="utf-8"))
        errors = validate_output(output, packet)
        if errors:
            invalid.append(f"{packet_path.name}: {len(errors)} errors, first: {errors[0]}")
            continue
        reviews.update({review["id"]: review for review in output["reviews"]})
    table = Counter()
    rows = []
    variant = Counter()
    for opaque, review in reviews.items():
        row, item = key[opaque], items[opaque]
        judged = judge_class(row)
        accepted = accepts(review, item)
        table[(judged, review["decision"])] += 1
        codes = [h["code"] for h in item["holds"]]
        agreed_empty = bool(item["readers_agree"] and item["readers"]["A"].get("valid") and not item["readers"]["A"].get("routes"))
        rule = outcome(item["status"], review["decision"], codes, item["readers_agree"], agreed_empty, None)
        rows.append({"opaque": opaque, "id": row["id"], "set": row["set"], "status": item["status"], "judge": judged, "decision": review["decision"], "accepted": accepted,
                     "rule_outcome_one_run": rule, "uncertainty": review["uncertainty"]})
        if row["judge_group"] in VARIANT_WORD:
            verdicts = {v["verdict"] for v in review["variant_verdicts"]}
            variant[("agree" if VARIANT_WORD[row["judge_group"]] in verdicts and len(verdicts) == 1 else "differ", row["judge_group"])] += 1
    by = lambda judged: [r for r in rows if r["judge"] == judged]  # noqa: E731
    wrong, right, cannot = by("wrong"), by("right"), by("cannot_tell")
    result = {
        "pass": pass_number, "items": len(key), "scored": len(rows), "invalid_outputs": invalid,
        "judge_wrong": {"n": len(wrong), "caught (not confirmed)": sum(not r["accepted"] for r in wrong), "confirmed (missed)": sum(r["accepted"] for r in wrong),
                        "by_decision": dict(Counter(r["decision"] for r in wrong))},
        "judge_right": {"n": len(right), "confirmed": sum(r["accepted"] for r in right), "wrongly rejected (keep_stored / no_chain / prefer)": sum(r["decision"] in ("keep_stored", "no_chain", "prefer_reader_a", "prefer_reader_b") and not r["accepted"] for r in right),
                        "needlessly corrected": sum(r["decision"] == "confirm_with_correction" for r in right), "referred to a human": sum(r["decision"] == "refer_to_human" for r in right)},
        "judge_cannot_tell": {"n": len(cannot), "by_decision": dict(Counter(r["decision"] for r in cannot))},
        "agreement_with_judge": round((sum(r["accepted"] for r in right) + sum(not r["accepted"] for r in wrong)) / max(1, len(right) + len(wrong)), 3),
        "by_set": {s: dict(Counter((r["judge"], r["decision"]) for r in rows if r["set"] == s).most_common()) for s in sorted({r["set"] for r in rows})},
        "variant_group_verdicts_vs_judge": {f"{a} ({g})": n for (a, g), n in variant.items()},
        "rule_outcomes_after_one_run": dict(Counter(f"{r['judge']}: {r['rule_outcome_one_run']}" for r in rows)),
        "confusion": {f"{j} / {d}": n for (j, d), n in sorted(table.items())},
        "rows": rows,
    }
    result["by_set"] = {s: {f"{j} / {d}": n for (j, d), n in counts.items()} for s, counts in result["by_set"].items()}
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pass", dest="pass_number", type=int, default=1)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    result = score(HERE, args.pass_number)
    text = json.dumps(result, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
