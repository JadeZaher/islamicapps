"""Hand agreed-and-unheld readings to the fix pipeline: reader outputs to `shura-chain-fix-envelope/1` envelopes with provenance.

    python -B -X utf8 v3/to_submission.py --packets batch-001/packets --reports batch-001/private/reports.jsonl
        --pass-a batch-001/outputs/pass-a --pass-b batch-001/outputs/pass-b --out batch-001/submissions [--batch b1]

Per packet one envelope `<out>/<packet>.envelope.json`, to be submitted with
    npx tsx reviews/ai/tools/chain-fix-submit.ts --envelope <envelope> --reports batch-001/private/reports.jsonl [--check-only]
Only reports that are eligible (v3/triage_v3.py: both valid, canonical-equal, status read, no hold) and submittable enter an envelope; the rest are listed in
<out>/not_submitted.tsv with the reason. Provenance in each envelope's `run`: model id from the pass's RUN.txt (one line per agent run; the packet's line), run id, prompt version
and sha256 (checked against v3/prompt-v3.json), packet id, UTC times, the second pass's run id; each fix also carries `reader_output_v3` (the unchanged output of pass A).

What the submit tool does not take yet (v3/AGENTS.md §submission): it pins the v1 prompt hash (`run.prompt_sha256` = chain-reader/prompt.md), its views are text_only and
text_and_stored_chain (these readers saw text and context: `view` is `text_and_context`), it reads v1-shaped `output` (routes with offsets; this converter writes that shape from the
v3 reading: compiler head dropped, `imam_in_text` as `narrator`), and it refuses a stored chain that repeats earlier names; readings with inherited links are therefore not submitted.
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
import validate as v1  # noqa: E402  (the submit tool's own reader validator, read-only)
from triage_v3 import load_packets, triage  # noqa: E402

ENVELOPE_FORMAT = "shura-chain-fix-envelope/1"
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


def v1_shape(expanded: dict) -> tuple[dict | None, str | None]:
    """The reading as the v1 reader output the submit tool validates: compiler head and inherited links dropped (None, reason when a route has inherited links), imam_in_text as narrator."""
    routes, seen = [], set()
    for route in expanded["routes"]:
        if any(link["kind"] == "inherited" for link in route["links"]):
            return None, "inherited links: the submit tool refuses chains that repeat earlier names"
        links = [{"surface": l["surface"], "start": l["start"], "end": l["end"], "kind": KEPT_KINDS[l["kind"]]} for l in route["links"] if l["kind"] != "compiler_head"]
        if not links:
            continue
        key = tuple((l["start"], l["end"]) for l in links)
        if key in seen:
            continue
        seen.add(key)
        tail = route.get("shared_tail_from")
        dropped_before_tail = sum(1 for l in route["links"][: tail or 0] if l["kind"] == "compiler_head") if isinstance(tail, int) else 0
        new_tail = tail - dropped_before_tail if isinstance(tail, int) else None
        routes.append({"links": links, "shared_tail_from": new_tail if new_tail is not None and 0 <= new_tail < len(links) else None})
    if not routes:
        return None, "no route with a written link"
    ends = [l["end"] for r in routes for l in r["links"]]
    return {"id": expanded["id"], "routes": routes, "matn_start": max(ends), "notes": list(expanded.get("notes") or [])}, None


def quote_of(text: str, reading: dict) -> str:
    """An exact stretch of the text that covers the chain, at most 200 characters, cut at a word boundary."""
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
    parser.add_argument("--batch", default="b1")
    args = parser.parse_args(argv)
    prompt = json.loads((HERE / "prompt-v3.json").read_text(encoding="utf-8"))
    packets = load_packets(Path(args.packets))
    stored = {}
    for line in Path(args.reports).read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            stored[row["id"]] = [s for chain in row.get("stored_chains", []) for s in chain["surfaces"]]
    rows = triage(packets, Path(args.pass_a), Path(args.pass_b), stored)
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
        shaped, reason = v1_shape(row["reading"]["expanded_a"])
        if shaped is None:
            skipped.append((row["id"], reason or "not submittable"))
            continue
        text = packets[row["id"]]["text"]
        invalid = v1.validate(shaped, text, row["id"])
        if invalid:
            skipped.append((row["id"], "fails the submit tool's validator: " + invalid[0][:120]))
            continue
        by_packet.setdefault(row["packet"], []).append({"row": row, "shaped": shaped, "quote": quote_of(text, shaped)})
    written = 0
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
        envelope = {
            "format": ENVELOPE_FORMAT,
            "run": {"model_id": run_a["model_id"], "provider_runtime": "Claude Code subagent, fresh context, packets of the v3 chain reader (text and context)", "run_id": run_a["run_id"],
                    "started_at": run_a["started_at"], "finished_at": run_a["finished_at"], "prompt_sha256": prompt["sha256"], "view": "text_and_context",
                    "prompt_version": prompt["version"], "prompt_file": "datasets/hadith-data/chain-reader/v3/prompt-v3.md", "packet_id": packet_file.replace(".jsonl", ""),
                    "second_reader": {"model_id": run_b["model_id"], "run_id": run_b["run_id"], "started_at": run_b["started_at"], "finished_at": run_b["finished_at"]},
                    "agreement": "canonical() equal in both passes, no hold (v3/holds_v3.py)", "built_at": utc_now()},
            "packet": str(Path(args.packets) / packet_file).replace("\\", "/"),
            "fixes": [{"output": item["shaped"], "reason": f"Two independent readers (runs {run_a['run_id']} and {run_b['run_id']}, prompt {prompt['version']}) read the same routes from the text and its context; no hold fired.",
                       "evidence": [{"quote": item["quote"]}], "external_citation": None, "reader_output_v3": item["row"]["reading"]["output_a"]} for item in items],
        }
        (out / f"{packet_file.replace('.jsonl', '')}.envelope.json").write_text(json.dumps(envelope, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        written += len(items)
    (out / "not_submitted.tsv").write_text("id\treason\n" + "".join(f"{i}\t{why}\n" for i, why in skipped), encoding="utf-8", newline="\n")
    print(f"submittable {written}, not submitted {len(skipped)} of {len(rows)} (envelopes in {out})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
