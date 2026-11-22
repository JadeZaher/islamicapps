"""Tables of one `dry_run_tranche.py` run, per group (tranches/AGENTS.md §Dry run): eligible in, recorded, refused (reasons), held by the
pipeline (codes), would be applied (by kind), and what would touch `narrator_transmissions`.

    python -B -X utf8 tranches/dry_run_report.py --tranche 01 --variant without|with  [--settings settings.json]

Reads `development/tranche-dry-run-2026-11-22/t<NN>-<variant>/` and the tranche's private reports (for the group of each report). Prints
JSON to stdout and writes `report.json` beside the run.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
READER = HERE.parent
ROOT = READER.parents[2]
GROUPS = ("six Sunni books", "al-Faqih", "other Imami")


def group_of(report: dict) -> str:
    if report["tradition"] == "sunni":
        return "six Sunni books"
    return "al-Faqih" if report["work"] == "man-la-yahduruhu-al-faqih" else "other Imami"


def reason_class(message: str) -> str:
    """A refusal message reduced to its kind (the first clause, ids and hashes removed)."""
    message = re.sub(r"\(hash [0-9a-f]+, packet [0-9a-f]+\)|sha [0-9a-f]+", "", message)
    for marker in ("stale text", "is not a live report", "stored chain repeats names", "inherited reading", "evidence", "second reading", "surface_mismatch", "order", "overlap"):
        if marker in message:
            return marker
    return message.split(":")[0][:80]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tranche", required=True)
    parser.add_argument("--variant", choices=("without", "with"), required=True)
    parser.add_argument("--out", default=str(ROOT / "datasets" / "hadith-data" / "development" / "tranche-dry-run-2026-11-22"))
    args = parser.parse_args()
    scratch = Path(args.out) / f"t{args.tranche}-{args.variant}"
    reports = {row["id"]: row for row in (json.loads(l) for l in (READER / "tranches" / f"tranche-{args.tranche}" / "private" / "reports.jsonl")
                                          .read_text(encoding="utf-8").splitlines() if l.strip())}
    by_hadith = {row["hadith_id"]: row for row in reports.values()}
    eligible: dict[str, str] = {}
    for envelope in sorted(scratch.glob("packet-*.envelope.json")):
        if ".clean" in envelope.name:
            continue
        for fix in json.loads(envelope.read_text(encoding="utf-8"))["fixes"]:
            eligible[(fix.get("reader_output_v3") or fix["output"])["id"]] = "no_chain" if ".no_chain." in envelope.name else "chain"
    refused = json.loads((scratch / "refused.json").read_text(encoding="utf-8"))
    store = scratch / "store"
    submissions: dict[str, dict] = {}
    for file in sorted((store / "submissions").glob("*.jsonl")):
        for line in file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                submissions.setdefault(row["packet_item_id"], row)
    states = {state["fix_id"]: state for state in json.loads((store / "state.json").read_text(encoding="utf-8"))["fixes"]}
    overrides = {}
    if (scratch / "overrides.jsonl.gz").is_file():
        with gzip.open(scratch / "overrides.jsonl.gz", "rt", encoding="utf-8") as handle:
            overrides = {row["fix_id"]: row for row in (json.loads(l) for l in handle if l.strip())}
    plan = json.loads((scratch / "apply-plan.json").read_text(encoding="utf-8")) if (scratch / "apply-plan.json").is_file() else {"reports": [], "skipped": []}
    applied = {item["fix_id"]: item for item in plan["reports"]}
    skipped = {item["fix_id"]: item["why"] for item in plan["skipped"]}

    table: dict[str, dict] = {group: defaultdict(int) for group in GROUPS}
    reasons: dict[str, Counter] = {group: Counter() for group in GROUPS}
    holds: dict[str, Counter] = {group: Counter() for group in GROUPS}
    skip_reasons: dict[str, Counter] = {group: Counter() for group in GROUPS}
    touches: list[dict] = []
    for item_id, kind in eligible.items():
        group = group_of(reports[item_id])
        row = table[group]
        row["eligible_in"] += 1
        if item_id in refused:
            row["refused"] += 1
            reasons[group][reason_class(refused[item_id])] += 1
            continue
        submission = submissions.get(item_id)
        if submission is None:
            row["not_recorded"] += 1
            continue
        row["accepted_by_submit"] += 1
        state = states[submission["fix_id"]]
        if state["state"] == "held":
            row["held"] += 1
            for code in state["holds"]:
                holds[group][code] += 1
            continue
        if state["state"] != "accepted":
            row["other_state:" + state["state"]] += 1
            continue
        row["accepted_state"] += 1
        override = overrides.get(submission["fix_id"])
        if override is None:
            row["accepted_without_override"] += 1
            continue
        if submission["fix_id"] in skipped:
            row["apply_skipped"] += 1
            skip_reasons[group][re.sub(r"chain-fix:[0-9a-f]+: ", "", skipped[submission["fix_id"]])[:90]] += 1
            continue
        if submission["fix_id"] not in applied:
            row["apply_not_run"] += 1
            continue
        row["would_apply"] += 1
        planned = override.get("planned") or {"chains": []}
        kinds = []
        if override.get("disposition"):
            kinds.append("no_chain")
        elif override["effect"] == "replace_routes":
            kinds.append("routes_rewritten")
        elif override["effect"] == "set_status":
            kinds.append("stored_chain_confirmed")
        else:
            kinds.append("annotated_only")
        mentions = [m for chain in planned["chains"] for m in chain["mentions"]]
        if any(m.get("inherited_from_mention_id") for m in mentions):
            row["with_inherited_links"] += 1
        if any(m.get("reader_kind") == "imam_in_text" for m in mentions):
            row["with_source_named_in_text"] += 1
        if override.get("variant_remarks"):
            row["with_variant_remark"] += 1
        row["kind:" + kinds[0]] += 1
        statuses = {chain.get("structure_status") for chain in submission["base"]["chains"]}
        if statuses & {"checked_by_rule", None, "verified_by_reviewer"}:
            touches.append({"fix_id": submission["fix_id"], "hadith_id": submission["hadith_id"], "base_statuses": sorted(map(str, statuses)), "group": group})
    out = {"label": scratch.name, "groups": {group: {**dict(table[group]), "refusal_reasons": dict(reasons[group]), "hold_codes": dict(holds[group]),
                                                    "apply_skip_reasons": dict(skip_reasons[group])} for group in GROUPS},
           "feeds_lists_if_applied": touches, "plan_total": plan.get("total"), "plan_by_effect": plan.get("by_effect")}
    (scratch / "report.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
