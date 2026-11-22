"""Reviewer v1.1 outputs, per item, with the outcome of `review_rules_v1_1.outcome` for the fix's CURRENT state (AGENTS.md §AI review).

    python -I review_bridge.py < request.json > response.json

Request `{"batch": "<reviewer set folder>", "prompt_version": "1.1.0", "allow_out_of_order": false, "facts": {"<opaque id>": {"status", "codes",
"stored_equals_reading", "human"}}}`. Response `{"items": [{"opaque", "valid", "problem", "review", "pass_label", "packet", "packet_sha256", "run",
"second", "decision", "effective", "outcome", "action_class", "second_pass", "second_run", "correction_is", "has_correction", "readers_agree",
"agreed_empty", "codes"}]}`. Items without facts get no outcome (not in the fix store). Validation, the second-run comparison and the rule are the
reviewer's own modules (`chain-reader/reviewer/`), imported, never re-implemented.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REVIEWER = HERE.parent / "chain-reader" / "reviewer"
for extra in (REVIEWER, REVIEWER.parent / "v3_4", REVIEWER.parent / "v3_2", REVIEWER.parent):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))
import record_reviews_v1_1 as recorder  # noqa: E402
import review_io_v1_1 as io  # noqa: E402
import review_rules_v1_1 as rules  # noqa: E402

RUN_LINE = re.compile(r"run_id=(?P<run_id>\S+) \| packet=(?P<packet>\S+) \| model=(?P<model>\S+) \| start=(?P<start>\S+) \| end=(?P<end>\S+)")


def run_lines(out: Path, label: str) -> dict[str, dict]:
    """Packet number -> the run that reviewed it (RUN.txt of the pass), the last line for a packet winning."""
    runs: dict[str, dict] = {}
    path = io.outputs_dir(out, label) / "RUN.txt"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            match = RUN_LINE.search(line)
            if match:
                runs[match["packet"]] = {"run_id": match["run_id"], "model_id": match["model"], "started_at": match["start"], "finished_at": match["end"]}
    return runs


def provenance(out: Path, opaque: str, label: str) -> dict:
    """Packet file, its hash and the run of the packet an item was reviewed in."""
    for packet_path in sorted(io.packets_dir(out, label).glob("packet-*.json")):
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        if any(item["id"] == opaque for item in packet["items"]):
            number = re.search(r"packet-(\w+)\.json", packet_path.name)[1]
            return {"packet": packet_path.as_posix(), "packet_sha256": hashlib.sha256(packet_path.read_bytes()).hexdigest(),
                    "run": run_lines(out, label).get(number) or run_lines(out, label).get(number.lstrip("0"))}
    return {"packet": None, "packet_sha256": None, "run": None}


def bridge(request: dict) -> dict:
    out = Path(request["batch"])
    manifest = json.loads((out / "private" / "manifest.json").read_text(encoding="utf-8"))
    first = io.collect(out, "1", request.get("prompt_version", rules.PROMPT_VERSION), bool(request.get("allow_out_of_order")))
    second = io.collect(out, "2", request.get("prompt_version", rules.PROMPT_VERSION), bool(request.get("allow_out_of_order"))) if io.packets_dir(out, "2").is_dir() else None
    second_dir = {opaque: out for opaque in (second or {}).get("reviews", {})}
    # Batch-shaped folders whose pass-2 reviews count as second runs too (record_reviews_v1_1.record `extra_second_dirs`); the batch's own win.
    for extra in map(Path, request.get("extra_second_dirs") or []):
        if not io.packets_dir(extra, "2").is_dir():
            continue
        more = io.collect(extra, "2", request.get("prompt_version", rules.PROMPT_VERSION), bool(request.get("allow_out_of_order")))
        second_dir = {**{opaque: extra for opaque in more["reviews"]}, **second_dir}
        second = more if second is None else {**second, "items": {**more["items"], **second["items"]}, "reviews": {**more["reviews"], **second["reviews"]}}
    facts = request.get("facts") or {}
    items = []
    for opaque in first["ids"]:
        record = manifest["items"][opaque]
        entry = {"opaque": opaque, "readers_agree": bool(record["readers_agree"]), "agreed_empty": bool(record["agreed_empty"]), "valid": False, "problem": None,
                 "review": None, "pass_label": None, "packet": None, "packet_sha256": None, "run": None, "second": None, "outcome": None}
        if opaque not in first["reviews"]:
            entry["problem"] = first["problems"].get(opaque, "no review")
            items.append(entry)
            continue
        review, label = first["reviews"][opaque]
        item = first["items"][opaque]
        has_correction = isinstance(review["corrected_reading"], dict)
        correction = rules.correction_is(item, review["corrected_reading"]) if has_correction else None
        needs_second = rules.needs_second_pass(review["decision"], correction, entry["agreed_empty"], has_correction)
        second_review = second["reviews"].get(opaque) if second else None
        agrees = recorder.second_run_agrees(item, review, second_review[0] if second_review else None) if needs_second else None
        entry.update(valid=True, review=review, pass_label=label, **provenance(out, opaque, label), has_correction=has_correction, correction_is=correction,
                     second_pass=needs_second, second_run=agrees, effective=rules.effective_decision(review["decision"], entry["readers_agree"], correction),
                     decision=review["decision"])
        if second_review:
            entry["second"] = {"review": second_review[0], "pass_label": second_review[1], **provenance(second_dir.get(opaque, out), opaque, second_review[1])}
        fact = facts.get(opaque)
        if fact is not None:
            # The CURRENT state of the fix (the store's), never the packet's: an applied reading is labelled, a held one may be applied.
            action = rules.outcome(fact["status"], review["decision"], fact["codes"], entry["readers_agree"], entry["agreed_empty"], agrees,
                                   stored_equals_reading=fact.get("stored_equals_reading"), correction_is=correction, has_correction=has_correction,
                                   human=fact.get("human"))
            entry.update(outcome=action, action_class=rules.ACTION_CLASS[action], codes=fact["codes"],
                         blocking_codes=rules.blocking_codes(fact["codes"]))
            if action in ("apply_correction", "apply_no_chain"):
                entry.update(text=item["text"], context=item.get("context"))     # the correction is planned through the engine on the text the reviewer read
        entry["text_sha256"] = hashlib.sha256(item["text"].encode("utf-8")).hexdigest()
        items.append(entry)
    return {"items": items, "prompt_version": request.get("prompt_version", rules.PROMPT_VERSION), "clearable": sorted(code for code, (_, ok) in rules.HOLDS.items() if ok)}


def main() -> int:
    request = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    sys.stdout.buffer.write(json.dumps(bridge(request), ensure_ascii=False).encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
