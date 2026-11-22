"""Two passes of a batch to a decision list (copy of v3_3/triage_v3_3.py with the v3.4 modules: saying labels; see v3_4/AGENTS.md §triage). Nothing is applied here.

    python -B -X utf8 v3_4/triage_v3_4.py --packets <dir> --pass-a <dir> --pass-b <dir> --out <dir> [--reports private/reports.jsonl]
                                      [--sayings-supported] [--variant-notes-supported] [--release-variant-readings]

As v3.3, plus: outputs validate with validate_v3_4 and expand with expand_v3_4; two readings agree when they label the same sayings and each saying's routes agree;
`two_sayings_not_supported` holds a labelled reading until the fix pipeline stores the label (`--sayings-supported` lifts it, listed in `suppressed`);
`saying_openings_differ` holds an agreed labelled reading whose two passes open a saying at different places in the text (pass A's label would be shown).
`triage.tsv` gains a `sayings` column (the number of labelled sayings of the agreed reading), `summary.json` the saying counts.
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
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_3"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
from expand_v3_4 import expand, readings_agree, variant_keys  # noqa: E402
from holds_v3_4 import BASE, compute_holds, faqih_route_statement, ruling_flag_state  # noqa: E402
from validate import parse_output  # noqa: E402
from validate_v3_4 import validate_v3_4, with_default_fixes  # noqa: E402


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


def opening_starts(reading: dict) -> dict:
    return {s["saying"]: s["start"] for s in reading.get("sayings") or []}


def triage_one(report_id: str, packet: dict, outputs: dict, stored: list[str] | None, sayings_supported: bool = False, release_variant_readings: bool = False) -> dict:
    """One report: `outputs` is {"a": output or None, "b": ...} (None with a problem string under "problem_a" / "problem_b")."""
    text, context = packet["text"], packet.get("context") or {}
    row = {"id": report_id, "packet": packet.get("_packet_file", ""), "work": (context.get("work") or {}).get("key"), "reading": None}
    readings, problems = {}, {}
    for tag in ("a", "b"):
        output = with_default_fixes(outputs.get(tag))
        outputs[tag] = output
        if output is None:
            problems[tag] = outputs.get(f"problem_{tag}", "missing")
            continue
        errors = validate_v3_4(output, text, report_id, context)
        if errors:
            problems[tag] = errors[0][:120]
            continue
        reading, _ = expand(output, text, context)
        readings[tag] = reading
    both = len(readings) == 2
    agree = both and readings_agree(readings["a"], readings["b"])
    codes: list[str] = []
    for tag, reading in readings.items():
        other = outputs["b" if tag == "a" else "a"]
        codes += [h["code"] for h in compute_holds(reading, outputs[tag], text, context, stored, other)]
    if agree and not readings_agree(readings["a"], readings["b"], include_bracketed=True):
        codes.append("bracketed_insertion_differs")
    if agree and opening_starts(readings["a"]) != opening_starts(readings["b"]):
        codes.append("saying_openings_differ")
    suppressed = []
    if release_variant_readings and "has_variant_group" in codes:
        codes = [c for c in codes if c != "has_variant_group"]
        suppressed.append("has_variant_group")
    if sayings_supported and "two_sayings_not_supported" in codes:
        codes = [c for c in codes if c != "two_sayings_not_supported"]
        suppressed.append("two_sayings_not_supported")
    flag = ruling_flag_state(outputs["a"], outputs["b"])
    statuses = {t: (outputs[t] or {}).get("status") for t in ("a", "b")}
    sayings = len(readings["a"].get("sayings") or []) if agree else 0
    row.update({"valid_a": "a" in readings, "valid_b": "b" in readings, "problems": problems, "agree": agree, "holds": sorted(set(codes)), "suppressed": suppressed, "flag": flag,
                "tags": ["faqih_route_statement"] if faqih_route_statement(text, context) else [], "status": statuses, "sayings": sayings,
                "variant_group": any(r.get("variant_remarks") for r in readings.values()), "variant_remarks_agree": both and variant_keys(readings["a"]) == variant_keys(readings["b"]),
                "eligible": bool(agree and not codes and statuses["a"] == "read" and statuses["b"] == "read")})
    row["applies"] = (("no_chain" if not readings["a"]["routes"] else "chain") if row["eligible"] else None)
    if agree:
        row["reading"] = {"expanded_a": readings["a"], "output_a": outputs["a"], "output_b": outputs["b"]}
    row["readings"] = readings
    return row


def triage(packets: dict[str, dict], dir_a: Path, dir_b: Path, stored: dict[str, list[str]] | None = None, variant_notes_supported: bool = False, release_variant_readings: bool = False,
           sayings_supported: bool = False) -> list[dict]:
    if release_variant_readings and not variant_notes_supported:
        raise ValueError("--release-variant-readings needs --variant-notes-supported: a released reading must carry its remark as a note")
    rows = []
    for report_id, packet in packets.items():
        outputs = {}
        for tag, directory in (("a", dir_a), ("b", dir_b)):
            output, problem = read_pass(directory, report_id)
            outputs[tag], outputs[f"problem_{tag}"] = output, problem
        row = triage_one(report_id, packet, outputs, (stored or {}).get(report_id), sayings_supported, release_variant_readings)
        row.pop("readings", None)
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--packets", required=True)
    parser.add_argument("--pass-a", required=True)
    parser.add_argument("--pass-b", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--reports", help="private reports.jsonl (stored chains for the holds that compare with them)")
    parser.add_argument("--sayings-supported", action="store_true", help="the fix pipeline stores each route's saying label: do not hold a reading for carrying two sayings")
    parser.add_argument("--variant-notes-supported", action="store_true", help="recorded only (as v3.3)")
    parser.add_argument("--release-variant-readings", action="store_true", help="explicit, off by default, needs --variant-notes-supported")
    args = parser.parse_args(argv)
    if args.release_variant_readings and not args.variant_notes_supported:
        parser.error("--release-variant-readings needs --variant-notes-supported")
    packets = load_packets(Path(args.packets))
    stored = None
    if args.reports:
        stored = {}
        for line in Path(args.reports).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                stored[row["id"]] = [s for chain in row.get("stored_chains", []) for s in chain["surfaces"]]
    rows = triage(packets, Path(args.pass_a), Path(args.pass_b), stored, args.variant_notes_supported, args.release_variant_readings, args.sayings_supported)
    out = Path(args.out)
    (out / "readings").mkdir(parents=True, exist_ok=True)
    lines = ["id\tpacket\twork\tvalid_a\tvalid_b\tagree\tflag\tholds\teligible\tapplies\tproblems\tvariant_group\ttags\tsayings"]
    for row in rows:
        lines.append("\t".join([row["id"], row["packet"], row["work"] or "", str(row["valid_a"]), str(row["valid_b"]), str(row["agree"]), row["flag"] or "", ",".join(row["holds"]), str(row["eligible"]),
                                row["applies"] or "", json.dumps(row["problems"], ensure_ascii=False), str(row["variant_group"]), ",".join(row["tags"]), str(row["sayings"])]))
        if row["reading"]:
            (out / "readings" / f"{row['id']}.json").write_text(json.dumps(row["reading"], ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    (out / "triage.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    eligible = [r["id"] for r in rows if r["eligible"]]
    (out / "eligible.txt").write_text("\n".join(eligible) + ("\n" if eligible else ""), encoding="utf-8", newline="\n")
    no_chain = [r["id"] for r in rows if r["applies"] == "no_chain"]
    (out / "no_chain.txt").write_text("\n".join(no_chain) + ("\n" if no_chain else ""), encoding="utf-8", newline="\n")
    sample = [r["id"] for r in rows if r["agree"] and r["flag"] in ("a_only", "b_only")]
    (out / "review_sample.txt").write_text("\n".join(sample) + ("\n" if sample else ""), encoding="utf-8", newline="\n")
    summary = {"tool": "v3_4", "base_holds": BASE, "reports": len(rows), "valid_a": sum(r["valid_a"] for r in rows), "valid_b": sum(r["valid_b"] for r in rows),
               "both_valid": sum(r["valid_a"] and r["valid_b"] for r in rows), "agreed": sum(r["agree"] for r in rows), "eligible": len(eligible),
               "applies_chain": sum(r["applies"] == "chain" for r in rows), "applies_no_chain": len(no_chain), "sayings_supported": args.sayings_supported,
               "agreed_with_two_or_more_sayings": sum(r["sayings"] >= 2 for r in rows), "variant_group": sum(r["variant_group"] for r in rows),
               "holds": dict(Counter(c for r in rows if r["agree"] for c in r["holds"])), "flag_state_among_agreed": dict(Counter(r["flag"] for r in rows if r["agree"]))}
    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: summary[k] for k in ("reports", "both_valid", "agreed", "eligible", "agreed_with_two_or_more_sayings", "holds")}, ensure_ascii=False), file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
