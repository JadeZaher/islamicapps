"""Hand agreed-and-unheld readings to the fix pipeline: reader outputs to `shura-chain-fix-envelope/1` envelopes with provenance (copy of v3_2/to_submission_v3_2.py; v3_3/AGENTS.md §submission).

    python -B -X utf8 v3_3/to_submission_v3_3.py --packets <tranche>/packets --reports <tranche>/private/reports.jsonl
        --pass-a <tranche>/outputs/pass-a --pass-b <tranche>/outputs/pass-b --out <tranche>/submissions [--batch t01]
        [--only <ids file>] [--reader-prompt v3|v3_1|v3_2] [--variant-notes-supported] [--release-variant-readings]

Everything of v3_2/to_submission_v3_2.py holds (read its docstring for the envelope), with these differences. The triage is v3_3's (`triage_v3_3`, holds of `holds_v3_3`); `run.tool_version` is `v3_3`
(the fix pipeline's engine must register `v3_3` before it accepts such an envelope: v3_3/README.md section 7).
`--variant-notes-supported` only CARRIES the variant remark of a reading (nothing is released by it). A reading with a variant remark is submitted only with the separate, explicit
`--release-variant-readings` (off by default; it requires `--variant-notes-supported`): the judge found 3 of 30 variant groups to be genuine routes.
The prompt files are v3_2's (the prompt does not change in v3.3).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "v3_2"))
sys.path.insert(0, str(HERE))
from triage_v3_3 import load_packets, triage  # noqa: E402
from to_submission_v3_2 import inherited_from, parse_run_lines, quote_of, run_for, utc_now, v1_shape, variant_notes  # noqa: E402,F401

ENVELOPE_FORMAT = "shura-chain-fix-envelope/1"
NO_CHAIN_FORMAT = "shura-chain-no-chain-envelope/1"
KEPT_KINDS = {"narrator": "narrator", "imam_in_text": "narrator", "unnamed": "unnamed", "back_reference": "back_reference", "relation": "relation"}
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--packets", required=True)
    parser.add_argument("--reports", required=True)
    parser.add_argument("--pass-a", required=True)
    parser.add_argument("--pass-b", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--batch", default="t01")
    parser.add_argument("--only", help="ids file: submit only these reports")
    parser.add_argument("--reader-prompt", choices=("v3", "v3_1", "v3_2"), default="v3_2", help="the prompt the outputs were read under")
    parser.add_argument("--variant-notes-supported", action="store_true", help="the fix pipeline carries variant remarks as notes (carried only: a reading with a remark stays held)")
    parser.add_argument("--release-variant-readings", action="store_true", help="explicit, off by default, needs --variant-notes-supported: submit readings that carry a variant remark")
    args = parser.parse_args(argv)
    if args.release_variant_readings and not args.variant_notes_supported:
        parser.error("--release-variant-readings needs --variant-notes-supported")
    prompt_file = {"v3_2": ROOT / "v3_2" / "prompt-v3_2.json", "v3_1": ROOT / "v3_1" / "prompt-v3_1.json", "v3": ROOT / "v3" / "prompt-v3.json"}[args.reader_prompt]
    prompt = json.loads(prompt_file.read_text(encoding="utf-8"))
    prompt_path = {"v3_2": "datasets/hadith-data/chain-reader/v3_2/prompt-v3_2.md", "v3_1": "datasets/hadith-data/chain-reader/v3_1/prompt-v3_1.md", "v3": "datasets/hadith-data/chain-reader/v3/prompt-v3.md"}[args.reader_prompt]
    only = {line.strip() for line in Path(args.only).read_text(encoding="utf-8").splitlines() if line.strip()} if args.only else None
    packets = load_packets(Path(args.packets))
    stored, previous = {}, {}
    for line in Path(args.reports).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            stored[row["id"]] = [s for chain in row.get("stored_chains", []) for s in chain["surfaces"]]
            previous[row["id"]] = {p["ref"]: p for p in row.get("previous_reports") or []}
    if only is not None:
        packets = {report_id: packet for report_id, packet in packets.items() if report_id in only}
    rows = triage(packets, Path(args.pass_a), Path(args.pass_b), stored, args.variant_notes_supported, args.release_variant_readings)
    runs = {"a": parse_run_lines(Path(args.pass_a) / "RUN.txt"), "b": parse_run_lines(Path(args.pass_b) / "RUN.txt")}
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    skipped: list[tuple[str, str]] = []
    by_packet: dict[str, list[dict]] = {}
    for row in rows:
        if not row["eligible"]:
            why = "not valid in both passes" if not (row["valid_a"] and row["valid_b"]) else "readings differ" if not row["agree"] else "held: " + ",".join(row["holds"]) if row["holds"] else "status is not read"
            skipped.append((row["id"], why))
            continue
        expanded = row["reading"]["expanded_a"]
        text = packets[row["id"]]["text"]
        if row["applies"] == "no_chain":
            by_packet.setdefault(row["packet"], []).append({"row": row, "no_chain": True, "quote": text[:120].rsplit(" ", 1)[0] if len(text) > 120 else text})
            continue
        shaped, reason = v1_shape(expanded)
        taken = inherited_from(expanded, previous.get(row["id"], {}))
        if shaped is None and not taken:
            skipped.append((row["id"], reason or "not submittable"))
            continue
        quote = quote_of(text, shaped) if shaped else text[:120].rsplit(" ", 1)[0]
        by_packet.setdefault(row["packet"], []).append({"row": row, "no_chain": False, "shaped": shaped, "quote": quote, "inherited_from": taken})
    written = {"chain": 0, "no_chain": 0}
    for packet_file, items in sorted(by_packet.items()):
        run_a, run_b = run_for(runs["a"], packet_file, "a", args.batch), run_for(runs["b"], packet_file, "b", args.batch)
        problems = []
        if run_a is None or run_b is None:
            problems.append("no RUN.txt line names this packet in pass " + ("a" if run_a is None else "b"))
        elif not run_a["model_id"] or not run_a["started_at"] or not run_a["finished_at"]:
            problems.append("pass a RUN.txt line lacks model, start or end")
        elif not SAFE_NAME.match(run_a["run_id"]):
            problems.append(f"run id {run_a['run_id']!r} is not letters, digits, dot, dash, underscore")
        if problems:
            skipped += [(item["row"]["id"], "; ".join(problems)) for item in items]
            continue
        run = {"model_id": run_a["model_id"], "provider_runtime": f"Claude Code subagent, fresh context, packets of the chain reader {prompt['version']} (text and context)", "run_id": run_a["run_id"],
               "started_at": run_a["started_at"], "finished_at": run_a["finished_at"], "prompt_sha256": prompt["sha256"], "view": "text_and_context",
               "prompt_version": prompt["version"], "prompt_file": prompt_path, "tool_version": "v3_3", "packet_id": packet_file.replace(".jsonl", ""),
               "second_reader": {"model_id": run_b["model_id"], "run_id": run_b["run_id"], "started_at": run_b["started_at"], "finished_at": run_b["finished_at"]},
               "agreement": "readings_agree in both passes (non-variant routes), no hold (v3_3/holds_v3_3.py)", "built_at": utc_now()}
        packet_path = str(Path(args.packets) / packet_file).replace("\\", "/")
        chain_items = [i for i in items if not i["no_chain"]]
        empty_items = [i for i in items if i["no_chain"]]
        if chain_items:
            envelope = {"format": ENVELOPE_FORMAT, "run": run, "packet": packet_path,
                        "fixes": [{"output": item["shaped"], "reason": f"Two independent readers (runs {run_a['run_id']} and {run_b['run_id']}, prompt {prompt['version']}) read the same routes from the text and its context; no hold fired.",
                                   "evidence": [{"quote": item["quote"]}], "external_citation": None, "reader_output_v3": item["row"]["reading"]["output_a"],
                                   "reader_output_v3_b": item["row"]["reading"]["output_b"],
                                   **({"inherited_from": item["inherited_from"]} if item["inherited_from"] else {}),
                                   **({"variant_remarks": [{"surfaces": r["surfaces"], "quote": r["quote"]} for r in item["row"]["reading"]["expanded_a"]["variant_remarks"]]} if item["row"]["reading"]["expanded_a"].get("variant_remarks") else {})} for item in chain_items]}
            (out / f"{packet_file.replace('.jsonl', '')}.envelope.json").write_text(json.dumps(envelope, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
            written["chain"] += len(chain_items)
        if empty_items:
            envelope = {"format": NO_CHAIN_FORMAT, "run": run, "packet": packet_path,
                        "fixes": [{"output": item["row"]["reading"]["output_a"], "disposition": "no_chain_by_reading",
                                   "reason": f"Two independent readers (runs {run_a['run_id']} and {run_b['run_id']}, prompt {prompt['version']}) read no isnad in this report: the text writes no transmission word and name before the saying, and does not open as an asker or an inherited speaker; the stored chain is the saying's own words.",
                                   "evidence": [{"quote": item["quote"]}], "stored_chain_surfaces": stored.get(item["row"]["id"], []), "external_citation": None} for item in empty_items]}
            (out / f"{packet_file.replace('.jsonl', '')}.no_chain.envelope.json").write_text(json.dumps(envelope, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
            written["no_chain"] += len(empty_items)
    (out / "not_submitted.tsv").write_text("id\treason\n" + "".join(f"{i}\t{why}\n" for i, why in skipped), encoding="utf-8", newline="\n")
    print(f"submittable chain {written['chain']}, no-chain {written['no_chain']}, not submitted {len(skipped)} of {len(rows)} (envelopes in {out})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
