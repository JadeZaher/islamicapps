"""Hand agreed-and-unheld readings to the fix pipeline (copy of v3_3/to_submission_v3_3.py with the v3.4 triage and the saying labels; v3_4/AGENTS.md §submission).

    python -B -X utf8 v3_4/to_submission_v3_4.py --packets <tranche>/packets --reports <tranche>/private/reports.jsonl
        --pass-a <tranche>/outputs/pass-a --pass-b <tranche>/outputs/pass-b --out <tranche>/submissions [--batch t07]
        [--only <ids file>] [--reader-prompt v3_2|v3_4] [--sayings-supported] [--variant-notes-supported] [--release-variant-readings]

Everything of v3_2/to_submission_v3_2.py holds (its docstring describes the envelope), with: `run.tool_version` `v3_4`; the default reader prompt v3.4 (v3_4/prompt-v3_4.json).
A reading that stores two sayings is submitted only with `--sayings-supported` (the triage holds it otherwise). Its fix then carries
    "sayings": [{"saying": 1, "label": "Chain of the first saying", "opens": "<exact words of the text>", "routes": [0, 1]}, ...]
where `routes` index `output.routes` (the v1-shaped copy, whose routes stay plain v1 routes), and `output.notes` gains one line per saying. The page shows each route under its label.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
from triage_v3_4 import load_packets, triage  # noqa: E402
from to_submission_v3_2 import KEPT_KINDS, inherited_from, parse_run_lines, quote_of, run_for, utc_now, variant_notes  # noqa: E402

ENVELOPE_FORMAT = "shura-chain-fix-envelope/1"
NO_CHAIN_FORMAT = "shura-chain-no-chain-envelope/1"
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
PROMPTS = {"v3_4": ("v3_4/prompt-v3_4.json", "datasets/hadith-data/chain-reader/v3_4/prompt-v3_4.md"), "v3_2": ("v3_2/prompt-v3_2.json", "datasets/hadith-data/chain-reader/v3_2/prompt-v3_2.md")}


def v1_shape(expanded: dict) -> tuple[dict | None, list[dict], str | None]:
    """(v1-shaped output, sayings with route indices, reason). v3.2's shaping (compiler head and inherited links dropped, imam_in_text as narrator); a route that
    stands in two sayings is kept once and listed under both."""
    routes, index_of, sayings_of = [], {}, []
    for route in expanded["routes"]:
        links = [{"surface": l["surface"], "start": l["start"], "end": l["end"], "kind": KEPT_KINDS[l["kind"]]} for l in route["links"] if l["kind"] in KEPT_KINDS]
        if not links:
            continue
        key = tuple((l["start"], l["end"]) for l in links)
        if key in index_of:
            if route.get("saying") not in sayings_of[index_of[key]]:
                sayings_of[index_of[key]].append(route.get("saying"))
            continue
        index_of[key] = len(routes)
        sayings_of.append([route.get("saying")])
        tail = route.get("shared_tail_from")
        dropped_before_tail = sum(1 for l in route["links"][: tail or 0] if l["kind"] not in KEPT_KINDS) if isinstance(tail, int) else 0
        new_tail = tail - dropped_before_tail if isinstance(tail, int) else None
        routes.append({"links": links, "shared_tail_from": new_tail if new_tail is not None and 0 <= new_tail < len(links) else None})
    if not routes:
        return None, [], "no route with a written link"
    sayings = [{"saying": s["saying"], "label": s["label"], "opens": s["opens"], "routes": [i for i, numbers in enumerate(sayings_of) if s["saying"] in numbers]} for s in expanded.get("sayings") or []]
    notes = list(expanded.get("notes") or []) + variant_notes(expanded) + [f"{s['label']} («{s['opens']}»): routes {', '.join(str(i + 1) for i in s['routes'])}" for s in sayings]
    ends = [l["end"] for r in routes for l in r["links"]]
    return {"id": expanded["id"], "routes": routes, "matn_start": max(ends), "notes": notes}, sayings, None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--packets", required=True)
    parser.add_argument("--reports", required=True)
    parser.add_argument("--pass-a", required=True)
    parser.add_argument("--pass-b", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--batch", default="t01")
    parser.add_argument("--only", help="ids file: submit only these reports")
    parser.add_argument("--reader-prompt", choices=tuple(PROMPTS), default="v3_4", help="the prompt the outputs were read under")
    parser.add_argument("--sayings-supported", action="store_true", help="the fix pipeline stores `sayings` on a fix: submit readings that carry two sayings")
    parser.add_argument("--variant-notes-supported", action="store_true")
    parser.add_argument("--release-variant-readings", action="store_true")
    args = parser.parse_args(argv)
    if args.release_variant_readings and not args.variant_notes_supported:
        parser.error("--release-variant-readings needs --variant-notes-supported")
    prompt_json, prompt_path = PROMPTS[args.reader_prompt]
    prompt = json.loads((ROOT / prompt_json).read_text(encoding="utf-8"))
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
    rows = triage(packets, Path(args.pass_a), Path(args.pass_b), stored, args.variant_notes_supported, args.release_variant_readings, args.sayings_supported)
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
        shaped, sayings, reason = v1_shape(expanded)
        taken = inherited_from(expanded, previous.get(row["id"], {}))
        if shaped is None and not taken:
            skipped.append((row["id"], reason or "not submittable"))
            continue
        quote = quote_of(text, shaped) if shaped else text[:120].rsplit(" ", 1)[0]
        by_packet.setdefault(row["packet"], []).append({"row": row, "no_chain": False, "shaped": shaped, "sayings": sayings, "quote": quote, "inherited_from": taken})
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
               "prompt_version": prompt["version"], "prompt_file": prompt_path, "tool_version": "v3_4", "packet_id": packet_file.replace(".jsonl", ""),
               "second_reader": {"model_id": run_b["model_id"], "run_id": run_b["run_id"], "started_at": run_b["started_at"], "finished_at": run_b["finished_at"]},
               "agreement": "readings_agree per saying in both passes (non-variant routes), no hold (v3_4/holds_v3_4.py)", "built_at": utc_now()}
        packet_path = str(Path(args.packets) / packet_file).replace("\\", "/")
        chain_items = [i for i in items if not i["no_chain"]]
        empty_items = [i for i in items if i["no_chain"]]
        if chain_items:
            fixes = []
            for item in chain_items:
                expanded = item["row"]["reading"]["expanded_a"]
                fix = {"output": item["shaped"], "reason": f"Two independent readers (runs {run_a['run_id']} and {run_b['run_id']}, prompt {prompt['version']}) read the same routes from the text and its context; no hold fired.",
                       "evidence": [{"quote": item["quote"]}], "external_citation": None, "reader_output_v3": item["row"]["reading"]["output_a"], "reader_output_v3_b": item["row"]["reading"]["output_b"]}
                if item["inherited_from"]:
                    fix["inherited_from"] = item["inherited_from"]
                if expanded.get("variant_remarks"):
                    fix["variant_remarks"] = [{"surfaces": r["surfaces"], "quote": r["quote"], **({"saying": r["saying"]} if r.get("saying") else {})} for r in expanded["variant_remarks"]]
                if item["sayings"]:
                    fix["sayings"] = item["sayings"]
                fixes.append(fix)
            envelope = {"format": ENVELOPE_FORMAT, "run": run, "packet": packet_path, "fixes": fixes}
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
