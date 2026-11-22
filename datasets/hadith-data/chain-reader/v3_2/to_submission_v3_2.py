"""Hand agreed-and-unheld readings to the fix pipeline: reader outputs to `shura-chain-fix-envelope/1` envelopes with provenance (copy of v3_1/to_submission_v3_1.py; v3_2/AGENTS.md §submission).

    python -B -X utf8 v3_2/to_submission_v3_2.py --packets <tranche>/packets --reports <tranche>/private/reports.jsonl
        --pass-a <tranche>/outputs/pass-a --pass-b <tranche>/outputs/pass-b --out <tranche>/submissions [--batch t01]
        [--only <ids file>] [--reader-prompt v3|v3_1|v3_2] [--variant-notes-supported]

`--only` keeps the reports listed (one id per line); `--reader-prompt v3` / `v3_1` records that the outputs were read under that prompt (`v3/prompt-v3.json`, `v3_1/prompt-v3_1.json`), while this tool (v3.2)
expanded and held them: the envelope's `run.prompt_sha256` is the prompt the reader ran, `run.tool_version` is `v3_2` (the fix pipeline stores both).
v3.2: a variant remark is never a route. A fix carries it as `variant_remarks` ([{surfaces, quote}], pass A's, informational) and as a line in `output.notes`; the second pass's unchanged output rides as
`reader_output_v3_b`, from which the submit tool (engine) computes the stored remarks: the union of both passes, each marked with the pass that wrote it, the routes of the two checked equal.
Until the fix pipeline accepts notes the triage holds such a reading (`has_variant_group`); `--variant-notes-supported` lifts that hold here and in `chain-fix-submit.ts`.

Per packet one envelope `<out>/<packet>.envelope.json` (a reading with chain links) and, when the packet has any, `<out>/<packet>.no_chain.envelope.json` (agreed EMPTY readings: "this report has no
isnad"), to be submitted with
    npx tsx reviews/ai/tools/chain-fix-submit.ts --envelope <envelope> --reports <tranche>/private/reports.jsonl [--check-only]
Only reports that are eligible (v3_2/triage_v3_2.py: both valid, canonical-equal, status read, no hold) enter an envelope; the rest are listed in <out>/not_submitted.tsv with the reason.
Provenance in each envelope's `run`: model id from the pass's RUN.txt (one line per agent run; the packet's line), run id, prompt version and sha256 (v3_2/prompt-v3_2.json), packet id, UTC times,
the second pass's run id; each fix also carries `reader_output_v3` (the unchanged output of pass A).

Inherited readings (owner ruling 2) are submitted: each such fix carries `inherited_from`, one entry per previous report it takes names from: {"ref", "previous_report_id" (the hadith id, from the
private reports file), "surfaces"}. `output` is the v1-shaped copy (compiler head and inherited links dropped, `imam_in_text` as `narrator`); it is null when no route has a written link.
The no-chain envelope (`format: shura-chain-no-chain-envelope/1`): its fixes carry `disposition: "no_chain_by_reading"`, the two readers' empty output and the stored chain's surfaces;
the fix pipeline retires the stored chain and marks the report (v3_2/AGENTS.md §submission).
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
sys.path.insert(0, str(HERE))
from triage_v3_2 import load_packets, triage  # noqa: E402

ENVELOPE_FORMAT = "shura-chain-fix-envelope/1"
NO_CHAIN_FORMAT = "shura-chain-no-chain-envelope/1"
KEPT_KINDS = {"narrator": "narrator", "imam_in_text": "narrator", "unnamed": "unnamed", "back_reference": "back_reference", "relation": "relation"}
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")


def parse_run_lines(path: Path) -> list[dict]:
    """One dict per RUN.txt line: model, start, end, packets (numbers), run_id when written as run_id=...; tolerant of `key=value`, `key: value` and `key value`."""
    runs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        model = re.search(r"model\s*[=:]?\s*([A-Za-z0-9._-]*\d[A-Za-z0-9._-]*)", line)
        start = re.search(r"start(?:\s+UTC)?\s*[=:]?\s*(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)", line)
        end = re.search(r"end(?:\s+UTC)?\s*[=:]?\s*(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)", line)
        run_id = re.search(r"run_id\s*[=:]\s*([A-Za-z0-9._-]+)", line)
        numbers = {int(n) for n in re.findall(r"packet-?\s*0*(\d+)", line)}
        listed = re.search(r"packets?\s*[=:]?\s*((?:\d+|and|,|&|\s)+)", line)           # «packets 05,06», «packets=01,02», «packets 01 and 02»
        if listed:
            numbers |= {int(n) for n in re.findall(r"\d+", listed.group(1))}
        numbers = sorted(numbers)
        runs.append({"model_id": model.group(1) if model else None, "started_at": start.group(1) if start else None, "finished_at": end.group(1) if end else None,
                     "run_id": run_id.group(1) if run_id else None, "packets": numbers, "line": line.strip()})
    return runs


def run_for(runs: list[dict], packet_file: str, label: str, batch: str) -> dict | None:
    number = int(re.search(r"(\d+)", packet_file).group(1))
    for run in runs:
        if number in run["packets"]:
            return {**run, "run_id": run["run_id"] or f"{batch}-{label}-p{min(run['packets']):03d}"}
    return None


def variant_notes(expanded: dict) -> list[str]:
    """One note per variant remark: it is about another version of the saying and names the transmitters that version gives; it is not a route."""
    return [f"variant remark (not a route of this saying): «{remark['quote']}» names " + " > ".join("/".join(level) for level in remark["surfaces"]) for remark in expanded.get("variant_remarks") or []]


def v1_shape(expanded: dict) -> tuple[dict | None, str | None]:
    """The reading as a v1-shaped output: compiler head and inherited links dropped, imam_in_text as narrator (None, reason when no route has a written link)."""
    routes, seen = [], set()
    for route in expanded["routes"]:
        links = [{"surface": l["surface"], "start": l["start"], "end": l["end"], "kind": KEPT_KINDS[l["kind"]]} for l in route["links"] if l["kind"] in KEPT_KINDS]
        if not links:
            continue
        key = tuple((l["start"], l["end"]) for l in links)
        if key in seen:
            continue
        seen.add(key)
        tail = route.get("shared_tail_from")
        dropped_before_tail = sum(1 for l in route["links"][: tail or 0] if l["kind"] not in KEPT_KINDS) if isinstance(tail, int) else 0
        new_tail = tail - dropped_before_tail if isinstance(tail, int) else None
        routes.append({"links": links, "shared_tail_from": new_tail if new_tail is not None and 0 <= new_tail < len(links) else None})
    if not routes:
        return None, "no route with a written link"
    ends = [l["end"] for r in routes for l in r["links"]]
    return {"id": expanded["id"], "routes": routes, "matn_start": max(ends), "notes": list(expanded.get("notes") or []) + variant_notes(expanded)}, None


def inherited_from(expanded: dict, previous: dict[str, dict]) -> list[dict]:
    """One entry per previous report the reading takes names from: its ref, the hadith id of that report (private reports file) and the inherited surfaces, in order."""
    taken: dict[str, list[str]] = {}
    for route in expanded["routes"]:
        for link in route["links"]:
            if link["kind"] == "inherited":
                names = taken.setdefault(link.get("from") or "", [])
                if link["surface"] not in names:
                    names.append(link["surface"])
    return [{"ref": ref, "previous_report_id": (previous.get(ref) or {}).get("hadith_id"), "supplies": (previous.get(ref) or {}).get("supplies"), "surfaces": names} for ref, names in taken.items()]


def quote_of(text: str, reading: dict) -> str:
    """An exact stretch of the text that covers the chain, at most 200 letters, cut at a word boundary."""
    starts = [l["start"] for r in reading["routes"] for l in r["links"]]
    ends = [l["end"] for r in reading["routes"] for l in r["links"]]
    span = text[min(starts): max(ends)]
    if len(span) > 200:
        span = span[:200].rsplit(" ", 1)[0]
    return span


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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
    parser.add_argument("--variant-notes-supported", action="store_true", help="the fix pipeline carries variant remarks as notes: do not hold a reading for having one")
    args = parser.parse_args(argv)
    prompt_file = {"v3_2": HERE / "prompt-v3_2.json", "v3_1": ROOT / "v3_1" / "prompt-v3_1.json", "v3": ROOT / "v3" / "prompt-v3.json"}[args.reader_prompt]
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
    rows = triage(packets, Path(args.pass_a), Path(args.pass_b), stored, args.variant_notes_supported)
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
               "prompt_version": prompt["version"], "prompt_file": prompt_path, "tool_version": "v3_2", "packet_id": packet_file.replace(".jsonl", ""),
               "second_reader": {"model_id": run_b["model_id"], "run_id": run_b["run_id"], "started_at": run_b["started_at"], "finished_at": run_b["finished_at"]},
               "agreement": "readings_agree in both passes (non-variant routes), no hold (v3_2/holds_v3_2.py)", "built_at": utc_now()}
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
