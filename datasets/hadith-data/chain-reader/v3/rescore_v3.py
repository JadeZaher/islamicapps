"""Re-score the second pilot's existing outputs (no model run) under the v2 tool and under the v3 tool, with the judge's verdicts (analysis-v2/agreed_set.tsv).

    python -B -X utf8 v3/rescore_v3.py            (from chain-reader/; writes v3/rescore_v3.json, prints the tables)

What it isolates: the tool alone (same outputs, same verdicts). The v2 column is recomputed from the v2 modules (context/) and checked against the
judge's own table (223 agreed, 174 applied, 167 right); a mismatch aborts. A report agreed only under v3 has no hand verdict unless it is in the
judge's 30-report disagreement sample; it is counted as `unjudged` and the right-rate is given with those as wrong (floor) and as right (ceiling).
Notes on the verdict map are in README.md section 4.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CTX = ROOT / "context"
ANALYSIS = ROOT / "analysis-v2"
for path in (str(ROOT), str(HERE), str(CTX), str(ANALYSIS)):
    sys.path.insert(0, path)

import expand as expand_v2          # noqa: E402  (context/expand.py, read-only)
import holds as holds_v2            # noqa: E402  (context/holds.py, read-only)
import expand_v3                    # noqa: E402
import holds_v3                     # noqa: E402
from validate import load_reports, parse_output  # noqa: E402
from score import wilson            # noqa: E402
from verdicts_v2 import DIS         # noqa: E402  (the judge's hand verdicts for the 30 sampled disagreements)

RIGHT = ("right", "rep", "label_wrong")
EXTRA = {row["id"]: row["verdict"] for row in csv.DictReader(open(HERE / "extra_verdicts.tsv", encoding="utf-8", newline=""), delimiter="	")}
EXCLUDED = set((CTX / "pilot-v2" / "exclude_prompt_fragments.txt").read_text(encoding="utf-8").split())


def pct(k: int, n: int) -> str:
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.0f}% ({100 * lo:.0f}-{100 * hi:.0f})"


def load_packets() -> dict:
    packets = {}
    for path in sorted((CTX / "pilot-v2" / "packets").glob("packet-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                packets[row["id"]] = row
    return packets


def read_output(folder: str, report_id: str):
    path = CTX / "outputs-v2" / folder / f"{report_id}.json"
    if not path.is_file():
        return None
    try:
        parsed, _ = parse_output(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def judge_verdicts() -> dict:
    """id -> {verdict, tag, state, source} from the judge's table."""
    table = {}
    with open(ANALYSIS / "agreed_set.tsv", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            table[row["id"]] = row
    return table


def run_tool(tool: str, reports: dict, packets: dict) -> dict:
    """`tool` is v2 (v2 expand and holds), v3 (both v3) or v3x (v3 expand and agreement, v2 holds: the fold alone)."""
    """Per report: validity of A and B, agreement, tool holds (union of A and B), flags, the reading of A."""
    expand_fn = expand_v2.expand if tool == "v2" else expand_v3.expand
    canonical = expand_v2.canonical if tool == "v2" else expand_v3.canonical
    holds_with_v3 = tool == "v3"
    rows = {}
    for report_id, report in reports.items():
        context = json.loads(json.dumps(packets[report_id]["context"]))
        context.setdefault("work", {})["key"] = f"{report['tradition']}:{report['work']}"
        stored = [s for chain in report.get("stored_chains", []) for s in chain["surfaces"]]
        outputs = {t: read_output(folder, report_id) for t, folder in (("a", "run-a"), ("b", "run-b"))}
        readings, errors = {}, {}
        for tag, output in outputs.items():
            if output is None:
                errors[tag] = "not_json"
                continue
            reading, errs = expand_fn(output, report["text"], context)
            if reading is None:
                errors[tag] = errs[0].split(":")[0]
            else:
                readings[tag] = reading
        both = len(readings) == 2
        agree = both and canonical(readings["a"]) == canonical(readings["b"])
        flags = {t: bool(outputs[t] and outputs[t].get("needs_ruling")) for t in "ab"}
        codes: list[str] = []
        for tag, reading in readings.items():
            other = outputs["b" if tag == "a" else "a"]
            if not holds_with_v3:
                found = holds_v2.compute_holds(reading, outputs[tag], report["text"], context, stored)
            else:
                found = holds_v3.compute_holds(reading, outputs[tag], report["text"], context, stored, other)
            codes += [h["code"] for h in found if h["code"] != "needs_ruling"]
        if tool == "v3" and agree:
            pass
        rows[report_id] = {"valid_a": "a" in readings, "valid_b": "b" in readings, "both_valid": both, "agree": agree, "errors": errors, "flags": flags,
                           "tool_holds": sorted(set(codes)), "status_a": (outputs["a"] or {}).get("status"), "reading_a": readings.get("a"), "reading_b": readings.get("b")}
    return rows


def verdict_of(report_id: str, table: dict, tool: str, tool_rows: dict) -> tuple[str, str]:
    """(verdict, source): the judge's verdict for the agreed reading; compiler-duplicate wrongs revert to the reader's verdict when the tool no longer duplicates."""
    row = table[report_id]
    verdict, tag = row["verdict"], row["tag"]
    if row["state"] == "agree" and verdict:
        if tool != "v2" and tag.startswith("compiler_head_duplicated"):
            reading = tool_rows[report_id]["reading_a"]
            duplicated = any(r["links"] and r["links"][0]["kind"] == "compiler_head" for r in reading["routes"])   # the head was added although the text writes the compiler first
            reader_verdict = tag.rsplit("reader ", 1)[-1].strip()
            return (reader_verdict, "tool fix: compiler head no longer duplicated") if not duplicated else (verdict, "judge")
        if tool != "v2" and report_id == "cr-0144" and any("one link" in n for n in (tool_rows[report_id]["reading_a"] or {}).get("tool_notes", [])):
            return "right", "tool fix: «المعتمر» and «معتمر بن سليمان» merged into one link (the judge's wrong was the two links)"
        return verdict, "judge"
    disagreement = DIS.get(report_id)
    if disagreement:
        who = disagreement[1]
        if who.startswith("neither"):
            return "wrong", "judge (disagreement sample)"
        if who.startswith(("A", "B per rule", "both")) or who == "B":
            return "right", "judge (disagreement sample)"
    extra = EXTRA.get(report_id)
    if extra:
        return extra, "this task (single reader), v3/extra_verdicts.tsv"
    return "unjudged", ""


def summarise(tool: str, rows: dict, table: dict, scored: list[str], flag_rule: str) -> dict:
    agreed = [i for i in scored if rows[i]["agree"]]
    verdicts = {i: verdict_of(i, table, tool, rows) for i in agreed}

    def held(i: str) -> bool:
        if rows[i]["tool_holds"]:
            return True
        a, b = rows[i]["flags"]["a"], rows[i]["flags"]["b"]
        return {"either": a or b, "both": a and b, "none": False}[flag_rule]

    applied = [i for i in agreed if not held(i)]

    def stat(ids: list[str]) -> dict:
        judged = [i for i in ids if verdicts[i][0] not in ("abstain", "unjudged")]
        unjudged = [i for i in ids if verdicts[i][0] == "unjudged"]
        right = sum(verdicts[i][0] in RIGHT for i in judged)
        n = len(ids) - sum(verdicts[i][0] == "abstain" for i in ids)
        return {"reports": len(ids), "judged": len(judged), "unjudged": len(unjudged), "right": right, "wrong": len(judged) - right,
                "floor": pct(right, len(judged) + len(unjudged)), "ceiling": pct(right + len(unjudged), len(judged) + len(unjudged)), "judged_rate": pct(right, len(judged)), "n": n}

    return {"valid_a": sum(rows[i]["valid_a"] for i in scored), "valid_b": sum(rows[i]["valid_b"] for i in scored), "both_valid": sum(rows[i]["both_valid"] for i in scored),
            "agreed": pct(len(agreed), len(scored)), "agreed_n": len(agreed), "before_holds": stat(agreed),
            "after_tool_holds": stat([i for i in agreed if not rows[i]["tool_holds"]]), "applied": stat(applied), "applied_ids": applied, "agreed_ids": agreed,
            "yield": pct(len(applied), len(scored)), "verdicts": {i: v[0] for i, v in verdicts.items()}}


def hold_hits(rows: dict, agreed_ids: list[str], verdicts: dict) -> dict:
    hits: dict[str, dict] = defaultdict(lambda: {"agreed_hits": 0, "right": 0, "wrong": 0, "unjudged": 0, "ids": []})
    for i in agreed_ids:
        for code in rows[i]["tool_holds"]:
            entry = hits[code]
            entry["agreed_hits"] += 1
            verdict = verdicts.get(i, "unjudged")
            entry["right" if verdict in RIGHT else "wrong" if verdict not in ("abstain", "unjudged") else "unjudged"] += 1
            entry["ids"].append(i)
    return dict(hits)


def main() -> int:
    reports = {i: r for i, r in load_reports(ROOT / "pilot" / "reports.jsonl").items() if i not in EXCLUDED}
    packets = load_packets()
    table = judge_verdicts()
    scored = list(reports)
    out: dict = {"scored": len(scored)}
    runs = {tool: run_tool(tool, reports, packets) for tool in ("v2", "v3x", "v3")}
    v2 = summarise("v2", runs["v2"], table, scored, "either")
    # the baseline must be the judge's table
    assert v2["agreed_n"] == 223, ("v2 agreed", v2["agreed_n"])
    assert v2["applied"]["reports"] == 174 and v2["applied"]["right"] == 167, ("v2 applied", v2["applied"])
    out["v2"] = {k: v for k, v in v2.items() if k not in ("agreed_ids", "verdicts")}
    for rule in ("either", "both"):
        fold_only = summarise("v3x", runs["v3x"], table, scored, rule)
        out[f"v3x_fold_only_flags_{rule}"] = {k: v for k, v in fold_only.items() if k not in ("agreed_ids", "verdicts")}
        v3 = summarise("v3", runs["v3"], table, scored, rule)
        out[f"v3_flags_{rule}"] = {k: v for k, v in v3.items() if k not in ("agreed_ids", "verdicts")}
        if rule == "both":
            v3_both = v3
    # v2 tool with the "both" flag rule, for a like-for-like reading of the flag change alone
    v2_both = summarise("v2", runs["v2"], table, scored, "both")
    out["v2_flags_both"] = {k: v for k, v in v2_both.items() if k not in ("agreed_ids", "verdicts")}
    out["applied_not_right"] = {"v2_either": {i: v2["verdicts"][i] for i in v2["applied_ids"] if v2["verdicts"][i] not in RIGHT},
                                "v3_both": {i: v3_both["verdicts"][i] for i in v3_both["applied_ids"] if v3_both["verdicts"][i] not in RIGHT},
                                "v3_either": {i: v3["verdicts"][i] for i in v3["applied_ids"] if v3["verdicts"][i] not in RIGHT}}
    out["agreed_wrong_before_holds"] = {"v2": {i: v for i, v in v2["verdicts"].items() if v not in RIGHT and v != "abstain"}, "v3": {i: v for i, v in v3_both["verdicts"].items() if v not in RIGHT and v not in ("abstain",)}}
    out["v3_holds_of_agreed_wrong"] = {i: runs["v3"][i]["tool_holds"] + (["flags_both"] if all(runs["v3"][i]["flags"].values()) else []) for i in out["agreed_wrong_before_holds"]["v3"]}
    # the same without my nine extra verdicts (judge's verdicts only; the rest of the newly agreed are unjudged)
    saved = dict(EXTRA)
    EXTRA.clear()
    judge_only = summarise("v3", runs["v3"], table, scored, "both")
    EXTRA.update(saved)
    out["v3_flags_both_judge_only"] = {k: v for k, v in judge_only.items() if k not in ("agreed_ids", "verdicts")}
    # changes in who agrees
    v2_agreed, v3_agreed = set(v2["agreed_ids"]), set(v3_both["agreed_ids"])
    out["agreement_moves"] = {"newly_agreed": sorted(v3_agreed - v2_agreed), "lost_agreement": sorted(v2_agreed - v3_agreed)}
    out["newly_agreed_verdicts"] = Counter(v3_both["verdicts"][i] for i in v3_agreed - v2_agreed)
    # the right readings the tool changes lose from application (v2-applied right, v3-held), and the wrong ones it stops
    applied_v2, applied_v3 = set(v2["applied_ids"]), set(v3_both["applied_ids"])
    out["applied_moves"] = {
        "v2_applied_now_held": {i: {"verdict": v2["verdicts"][i], "holds": runs["v3"][i]["tool_holds"] or ["agreement lost" if i not in v3_agreed else "flag"]} for i in sorted(applied_v2 - applied_v3)},
        "newly_applied": {i: v3_both["verdicts"][i] for i in sorted(applied_v3 - applied_v2)}}
    # hold hits
    out["hold_hits_v2_tool"] = hold_hits(runs["v2"], v2["agreed_ids"], v2["verdicts"])
    out["hold_hits_v3_tool"] = hold_hits(runs["v3"], v3_both["agreed_ids"], v3_both["verdicts"])
    # needs_ruling flag rules on the v3 agreed set
    out["valid_error_codes_v2"] = Counter(e for i in scored for e in runs["v2"][i]["errors"].values())
    out["valid_error_codes_v3"] = Counter(e for i in scored for e in runs["v3"][i]["errors"].values())
    out["v3_tool_notes"] = {i: runs["v3"][i]["reading_a"].get("tool_notes") for i in v3_both["agreed_ids"] if runs["v3"][i]["reading_a"] and runs["v3"][i]["reading_a"].get("tool_notes")}
    (HERE / "rescore_v3.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=list), encoding="utf-8")
    for name in ("v2", "v2_flags_both", "v3x_fold_only_flags_either", "v3x_fold_only_flags_both", "v3_flags_either", "v3_flags_both", "v3_flags_both_judge_only"):
        block = out[name]
        print(name, "valid", block["valid_a"], block["valid_b"], block["both_valid"], "agreed", block["agreed"], "| before", block["before_holds"]["judged_rate"], block["before_holds"]["unjudged"],
              "| tool holds", block["after_tool_holds"]["reports"], block["after_tool_holds"]["judged_rate"], "| applied", block["yield"], block["applied"]["judged_rate"], "unjudged", block["applied"]["unjudged"],
              "floor", block["applied"]["floor"], "ceiling", block["applied"]["ceiling"])
    print("moves", json.dumps(out["agreement_moves"], ensure_ascii=False), out["newly_agreed_verdicts"])
    print("applied moves", json.dumps(out["applied_moves"], ensure_ascii=False, indent=1))
    print("NOT RIGHT applied", json.dumps(out["applied_not_right"], ensure_ascii=False)); print("agreed wrong v3 + holds", json.dumps(out["v3_holds_of_agreed_wrong"], ensure_ascii=False))
    print("hits v2", {k: (v["agreed_hits"], v["right"], v["wrong"]) for k, v in out["hold_hits_v2_tool"].items()})
    print("hits v3", {k: (v["agreed_hits"], v["right"], v["wrong"], v["unjudged"]) for k, v in out["hold_hits_v3_tool"].items()})
    print("errors", out["valid_error_codes_v2"], out["valid_error_codes_v3"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
