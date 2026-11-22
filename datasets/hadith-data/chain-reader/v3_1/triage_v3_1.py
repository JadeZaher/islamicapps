"""Two passes of a batch to a decision list: validate, expand, agree, hold. Nothing is applied here (copy of v3/triage_v3.py, v3.1 tool; see v3_1/AGENTS.md §triage).

    python -B -X utf8 v3_1/triage_v3_1.py --packets batch-001/packets --pass-a batch-001/outputs/pass-a --pass-b batch-001/outputs/pass-b --out batch-001/triage
                                      [--reports batch-001/private/reports.jsonl]

For every report: both outputs validate (validate_v3_1), expand (expand_v3_1), agree when canonical() is equal, and the holds (holds_v3_1) of both readings are united. A report is
`eligible` when both are valid, they agree, status is `read` and no hold fired. An eligible reading with routes `applies` as a `chain`; an eligible reading with NO route (the report has no isnad: v3.1 holds
an empty reading only when the text writes a transmission word and a name before the saying, or opens as an asker / inherited speaker) `applies` as `no_chain`: the stored chain is retired and the report marked as having no chain by reading. `--reports` (the private hidden half) adds the stored chain to the holds that need it.
Writes <out>/triage.tsv, <out>/readings/<id>.json (the expanded agreed reading), <out>/eligible.txt, <out>/no_chain.txt, <out>/review_sample.txt (a flag set by one reader only), <out>/summary.json.
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
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from expand_v3_1 import canonical, expand  # noqa: E402
from holds_v3_1 import compute_holds, ruling_flag_state  # noqa: E402
from validate import parse_output  # noqa: E402
from validate_v3_1 import validate_v3_1  # noqa: E402


def load_packets(directory: Path) -> dict[str, dict]:
    packets = {}
    for path in sorted(directory.glob("packet-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                row["_packet_file"] = path.name
                packets[row["id"]] = row
    return packets


def read_pass(directory: Path, report_id: str) -> tuple[dict | None, str]:
    path = directory / f"{report_id}.json"
    if not path.is_file():
        return None, "missing"
    try:
        parsed, _ = parse_output(path.read_text(encoding="utf-8"))
    except ValueError as error:
        return None, f"not_json: {error}"
    return (parsed, "") if isinstance(parsed, dict) else (None, "not_object")


def triage(packets: dict[str, dict], dir_a: Path, dir_b: Path, stored: dict[str, list[str]] | None = None) -> list[dict]:
    rows = []
    for report_id, packet in packets.items():
        text, context = packet["text"], packet.get("context") or {}
        row = {"id": report_id, "packet": packet["_packet_file"], "work": (context.get("work") or {}).get("key"), "reading": None}
        outputs, readings, problems = {}, {}, {}
        for tag, directory in (("a", dir_a), ("b", dir_b)):
            output, problem = read_pass(directory, report_id)
            outputs[tag] = output
            if output is None:
                problems[tag] = problem
                continue
            errors = validate_v3_1(output, text, report_id, context)
            if errors:
                problems[tag] = errors[0][:120]
                continue
            reading, _ = expand(output, text, context)
            readings[tag] = reading
        both = len(readings) == 2
        agree = both and canonical(readings["a"]) == canonical(readings["b"])
        codes: list[str] = []
        for tag, reading in readings.items():
            other = outputs["b" if tag == "a" else "a"]
            codes += [h["code"] for h in compute_holds(reading, outputs[tag], text, context, (stored or {}).get(report_id), other)]
        flag = ruling_flag_state(outputs["a"], outputs["b"])
        statuses = {t: (o or {}).get("status") for t, o in outputs.items()}
        row.update({"valid_a": "a" in readings, "valid_b": "b" in readings, "problems": problems, "agree": agree, "holds": sorted(set(codes)), "flag": flag, "status": statuses,
                    "eligible": bool(agree and not codes and statuses["a"] == "read" and statuses["b"] == "read")})
        row["applies"] = (("no_chain" if not readings["a"]["routes"] else "chain") if row["eligible"] else None)
        if agree:
            row["reading"] = {"expanded_a": readings["a"], "output_a": outputs["a"], "output_b": outputs["b"]}
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--packets", required=True)
    parser.add_argument("--pass-a", required=True)
    parser.add_argument("--pass-b", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--reports", help="private reports.jsonl (stored chains for the holds that compare with them)")
    args = parser.parse_args(argv)
    packets = load_packets(Path(args.packets))
    stored = None
    if args.reports:
        stored = {}
        for line in Path(args.reports).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                stored[row["id"]] = [s for chain in row.get("stored_chains", []) for s in chain["surfaces"]]
    rows = triage(packets, Path(args.pass_a), Path(args.pass_b), stored)
    out = Path(args.out)
    (out / "readings").mkdir(parents=True, exist_ok=True)
    lines = ["id\tpacket\twork\tvalid_a\tvalid_b\tagree\tflag\tholds\teligible\tapplies\tproblems"]
    for row in rows:
        lines.append("\t".join([row["id"], row["packet"], row["work"] or "", str(row["valid_a"]), str(row["valid_b"]), str(row["agree"]), row["flag"] or "", ",".join(row["holds"]), str(row["eligible"]), row["applies"] or "", json.dumps(row["problems"], ensure_ascii=False)]))
        if row["reading"]:
            (out / "readings" / f"{row['id']}.json").write_text(json.dumps(row["reading"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    (out / "triage.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    eligible = [r["id"] for r in rows if r["eligible"]]
    (out / "eligible.txt").write_text("\n".join(eligible) + ("\n" if eligible else ""), encoding="utf-8", newline="\n")
    no_chain = [r["id"] for r in rows if r["applies"] == "no_chain"]
    (out / "no_chain.txt").write_text("\n".join(no_chain) + ("\n" if no_chain else ""), encoding="utf-8", newline="\n")
    sample = [r["id"] for r in rows if r["agree"] and r["flag"] in ("a_only", "b_only")]
    (out / "review_sample.txt").write_text("\n".join(sample) + ("\n" if sample else ""), encoding="utf-8", newline="\n")
    summary = {"reports": len(rows), "valid_a": sum(r["valid_a"] for r in rows), "valid_b": sum(r["valid_b"] for r in rows), "both_valid": sum(r["valid_a"] and r["valid_b"] for r in rows),
               "agreed": sum(r["agree"] for r in rows), "eligible": len(eligible), "applies_chain": sum(r["applies"] == "chain" for r in rows), "applies_no_chain": len(no_chain), "holds": dict(Counter(c for r in rows if r["agree"] for c in r["holds"])), "flag_state_among_agreed": dict(Counter(r["flag"] for r in rows if r["agree"])),
               "by_work": {w: {"reports": sum(1 for r in rows if r["work"] == w), "agreed": sum(1 for r in rows if r["work"] == w and r["agree"]), "eligible": sum(1 for r in rows if r["work"] == w and r["eligible"])} for w in sorted({r["work"] for r in rows if r["work"]})}}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: summary[k] for k in ("reports", "valid_a", "valid_b", "both_valid", "agreed", "eligible", "applies_chain", "applies_no_chain", "holds")}, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
