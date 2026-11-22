"""Record a batch's reviews per item and say what the v1.1 decision rule does with each (reviewer/RUN.md §4). Reads outputs/pass-1 (+ its re-queue rounds) and pass-2; writes private/outcomes.tsv,
private/summary.json and private/requeue.txt. Applies nothing: the pipeline owner's tools do that from outcomes.tsv.

    python -B -X utf8 reviewer/record_reviews_v1_1.py --batch review-t01/held [--allow-out-of-order]        (from chain-reader/)
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_4"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
import expand_v3_4  # noqa: E402
import review_io_v1_1 as io  # noqa: E402
import review_rules_v1_1 as rules  # noqa: E402


def second_run_agrees(item: dict, first: dict, second: dict | None) -> bool | None:
    """Do two independent reviews write the same corrected routes (or both say no_chain)? None when no valid second review exists."""
    if second is None:
        return None
    if first["decision"] == "no_chain":
        return second["decision"] == "no_chain"
    if second["decision"] != "confirm_with_correction" or not isinstance(first["corrected_reading"], dict):
        return False
    a, ea = expand_v3_4.expand(first["corrected_reading"], item["text"], item.get("context"))
    b, eb = expand_v3_4.expand(second["corrected_reading"], item["text"], item.get("context"))
    return bool(a is not None and b is not None and not ea and not eb and expand_v3_4.readings_agree(a, b))


def record(out: Path, allow_out_of_order: bool = False, prompt_version: str = rules.PROMPT_VERSION, write_to: Path | None = None, extra_second_dirs: tuple[Path, ...] = ()) -> dict:
    """`write_to`: where outcomes.tsv, summary.json and requeue.txt go (default out/private). `extra_second_dirs`: batch-shaped folders (packets-pass-2/, outputs/pass-2/) whose pass-2 reviews count as second runs too."""
    manifest = json.loads((out / "private" / "manifest.json").read_text(encoding="utf-8"))
    id_map = json.loads((out / "private" / "id_map.json").read_text(encoding="utf-8"))["ids"]
    first = io.collect(out, "1", prompt_version, allow_out_of_order)
    second = io.collect(out, "2", prompt_version, allow_out_of_order) if io.packets_dir(out, "2").is_dir() else None
    for extra in extra_second_dirs:
        more = io.collect(extra, "2", prompt_version, allow_out_of_order)
        second = more if second is None else {**second, "items": {**more["items"], **second["items"]}, "reviews": {**more["reviews"], **second["reviews"]}}
    rows = []
    for opaque in first["ids"]:
        record_ = manifest["items"][opaque]
        item = first["items"][opaque]
        stored_same = record_["stored_equals_reading"] if "stored_equals_reading" in record_ else rules.stored_equals_reading(item)      # v1 manifests (the pilot) lack the v1.1 facts
        not_clearable = record_["not_clearable"] if "not_clearable" in record_ else bool(rules.blocking_codes(record_["holds"]))
        row = {"opaque": opaque, "id": id_map.get(opaque, ""), "status": record_["status"], "holds": ",".join(record_["holds"]), "not_clearable": not_clearable,
               "quote_refolded": first["reviews"][opaque][0].get("quote_refolded", 0) if opaque in first["reviews"] else 0}
        if opaque not in first["reviews"]:
            rows.append({**row, "valid": False, "decision": "", "effective": "", "outcome": "requeue", "action_class": "requeue", "second_pass": False, "second_run": "", "uncertainty": "",
                         "question": "", "problem": first["problems"].get(opaque, "no review")})
            continue
        review, _ = first["reviews"][opaque]
        has_correction = isinstance(review["corrected_reading"], dict)
        is_ = rules.correction_is(item, review["corrected_reading"]) if has_correction else None
        needs_second = rules.needs_second_pass(review["decision"], is_, bool(record_["agreed_empty"]), has_correction)
        second_review = second["reviews"].get(opaque, (None,))[0] if second else None
        agrees = second_run_agrees(item, review, second_review) if needs_second else None
        action = rules.outcome(record_["status"], review["decision"], record_["holds"], record_["readers_agree"], bool(record_["agreed_empty"]), agrees,
                               stored_equals_reading=stored_same, correction_is=is_, has_correction=has_correction)
        rows.append({**row, "valid": True, "decision": review["decision"], "effective": rules.effective_decision(review["decision"], record_["readers_agree"], is_), "outcome": action,
                     "action_class": rules.ACTION_CLASS[action], "second_pass": needs_second, "second_run": "" if agrees is None else str(agrees), "uncertainty": review["uncertainty"],
                     "question": (review["question"] or "").replace("\t", " ").replace("\n", " "), "problem": ""})
    summary = {"batch": manifest["batch"], "items": len(rows), "valid": sum(r["valid"] for r in rows), "invalid_or_missing (re-queue)": sum(not r["valid"] for r in rows),
               "invalid_outputs": first["invalid_outputs"], "decisions": dict(Counter(r["decision"] for r in rows if r["valid"])), "effective_decisions": dict(Counter(r["effective"] for r in rows if r["valid"])),
               "outcomes": dict(Counter(r["outcome"] for r in rows)), "by_class": dict(Counter(r["action_class"] for r in rows)),
               "second_pass_needed": sum(r["second_pass"] for r in rows), "second_pass_done": sum(1 for r in rows if r["second_run"] != ""),
               "by_status_outcome": {f"{s}: {o}": n for (s, o), n in sorted(Counter((r["status"], r["outcome"]) for r in rows).items())},
               "not_clearable_items": sum(r["not_clearable"] for r in rows), "quote_refolded_items": sum(1 for r in rows if r["quote_refolded"])}
    private = write_to or out / "private"
    private.mkdir(parents=True, exist_ok=True)
    columns = ["opaque", "id", "status", "holds", "not_clearable", "valid", "decision", "effective", "outcome", "action_class", "second_pass", "second_run", "uncertainty", "question", "problem", "quote_refolded"]
    (private / "outcomes.tsv").write_text("\t".join(columns) + "\n" + "\n".join("\t".join(str(r[c]) for c in columns) for r in rows) + "\n", encoding="utf-8", newline="\n")
    (private / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    (private / "requeue.txt").write_text("".join(f"{r['opaque']}\t{r['problem']}\n" for r in rows if not r["valid"]), encoding="utf-8", newline="\n")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--batch", required=True)
    parser.add_argument("--allow-out-of-order", action="store_true")
    parser.add_argument("--prompt-version", default=rules.PROMPT_VERSION, help="the version the outputs must carry (1.0.0 for the pilot's)")
    args = parser.parse_args(argv)
    print(json.dumps(record(HERE / args.batch, args.allow_out_of_order, args.prompt_version), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
