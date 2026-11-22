"""v3.3 re-triage against the judges' verdicts, and the apply lists (read-only on everything it reads; see v3_3/README.md, v3_3/APPLY_LISTS.md).

    python -B -X utf8 v3_3/evaluate_v3_3.py                    (from chain-reader/; the three v3.3 triages must exist, see README section 6)

Writes tranches/tranche-NN/triage-v3_3/{RETRIAGE_V3_3.md, numbers.json, hold_hits.tsv, eligible_v3_3.txt, withheld_by_judge.txt} for 01 and 02,
and v3_3/batch-001/{RETRIAGE_V3_3.md, numbers.json, hold_hits.tsv, would_hold_of_applied.tsv, would_release_of_held.tsv}.
A reading is `right` when the verdict is R or RO; undecided (CT) counts as not right. Judges' verdicts are one model's, not blind.
Sample status of each figure (the v3.3 changes were designed on tranche 02's judgement, so tranche 02 is IN-SAMPLE for them, tranche 01 and batch 001 are out of sample for them;
the v3.2 holds were designed on tranche 01, so tranche 01 stays in-sample for those).
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "v3_2"))
from eval_lib_v3_2 import GROUPS, holds_of, pct, read_tsv, weighted_rate  # noqa: E402

TAB, NEWLINE = chr(9), chr(10)
LABEL = {"sunni_six_books": "six Sunni books", "imami_faqih": "al-Faqih", "imami_other_not_kafi": "other Imami"}
REPO = ROOT.parents[2]
V33_CHANGED = ("mutabaa_marker", "route_ends_inside_another_route", "route_at_most_half_the_longest", "inherited_from_far_report", "needs_ruling_faqih_route_statement")
V32_ONLY = ("routes_end_at_different_links",)
# readings the judge of tranche 02 found wrong by scans outside the random sample (analysis/README.md sections 5 and 9); not counted in any rate, only in the lists
T02_EXTRA = {"t02-cf6189": "W", "t02-d02f9f": "W", "t02-883658": "W"}


def group_of(work: str) -> str:
    if work.startswith("sunni:"):
        return "sunni_six_books"
    return "imami_faqih" if work == "imami:man-la-yahduruhu-al-faqih" else "imami_other_not_kafi"


def right_of(code: str) -> str:
    return "R" if code in ("R", "RO", "right", "empty reading: right", "representation only") else "W" if code in ("W", "wrong") else "CT"


def load_verdicts(name: str) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
    """(sampled verdicts, all judged verdicts, where each came from) as R / W / CT keyed by id."""
    sampled: dict[str, str] = {}
    everything: dict[str, str] = {}
    source: dict[str, str] = {}
    if name == "t02":
        base = ROOT / "tranches" / "tranche-02" / "judge-v3_2" / "analysis"
        for i, row in read_tsv(base / "sample_verdicts.tsv").items():
            sampled[i] = right_of(row["reader"])
            source[i] = "sample_verdicts"
        everything.update(sampled)
        for i, row in read_tsv(base / "hold_verdicts.tsv").items():
            if i not in everything:
                everything[i] = right_of(row["reader"])
                source[i] = "hold_verdicts"
        for i, v in T02_EXTRA.items():
            if i not in everything:
                everything[i] = v
                source[i] = "scan finds (README sections 5, 9)"
    elif name == "t01":
        base = ROOT / "tranches" / "tranche-01" / "judge" / "analysis"
        draw = json.loads((base / "draw_extension.json").read_text(encoding="utf-8"))
        drawn = set(draw["base"]) | {i for ids in draw["extension"].values() for i in ids}
        for i, row in read_tsv(base / "sample_verdicts.tsv").items():
            everything[i] = right_of(row["reader"])
            source[i] = "sample_verdicts"
            if i in drawn:
                sampled[i] = everything[i]
    else:
        for i, row in read_tsv(ROOT / "analysis-batch-001" / "sample.tsv").items():
            sampled[i] = right_of(row["reader"])
            source[i] = "sample.tsv"
        everything.update(sampled)
    return sampled, everything, source


def figures(rows: list[dict]) -> dict:
    eligible = [r for r in rows if r["eligible"] == "True"]
    return {"reports": len(rows), "valid_a": sum(r["valid_a"] == "True" for r in rows), "valid_b": sum(r["valid_b"] == "True" for r in rows),
            "both_valid": sum(r["valid_a"] == "True" and r["valid_b"] == "True" for r in rows), "agreed": sum(r["agree"] == "True" for r in rows), "eligible": len(eligible),
            "eligible_chain": sum(r["applies"] == "chain" for r in eligible), "eligible_no_chain": sum(r["applies"] == "no_chain" for r in eligible)}


def evaluate(name: str, old_path: Path, new_path: Path, out: Path, title: str, status: str) -> dict:
    old, new = read_tsv(old_path), read_tsv(new_path)
    group = {i: group_of(r["work"]) for i, r in new.items()}
    sampled, judged, source = load_verdicts(name)
    result: dict = {"dataset": name, "status": status}
    lines = [f"# {title}", "", status, ""]

    # ---- 1. triage figures ----
    scopes = {"all": sorted(new), **{g: [i for i in sorted(new) if group[i] == g] for g in GROUPS}}
    result["triage"] = {scope: {"v3_2": figures([old[i] for i in ids]), "v3_3": figures([new[i] for i in ids])} for scope, ids in scopes.items()}
    lines += ["## 1. Triage figures, v3.2 tool against v3.3 tool (same outputs, same packets)", "", "| scope | tool | reports | valid A | valid B | both valid | agreed | eligible = chain + no chain |", "|---|---|---|---|---|---|---|---|"]
    for scope, both in result["triage"].items():
        for tool in ("v3_2", "v3_3"):
            f = both[tool]
            n = f["reports"]
            lines.append(f"| {LABEL.get(scope, scope)} | {tool.replace('_', '.')} | {n} | {f['valid_a']} | {f['valid_b']} | {f['both_valid']} | {f['agreed']} ({100 * f['agreed'] / n:.1f}%) | "
                         f"{f['eligible']} = {f['eligible_chain']} + {f['eligible_no_chain']} ({100 * f['eligible'] / n:.1f}%) |")

    # ---- 2. every hold's hits on agreed readings, overall and per group ----
    def agreed_hits(table: dict[str, dict], code: str) -> list[str]:
        return [i for i, r in sorted(table.items()) if r["agree"] == "True" and code in holds_of(r)]
    codes = sorted({c for t in (old, new) for r in t.values() for c in holds_of(r)})
    lines += ["", "## 2. Hits of every hold on agreed readings (overall; per group sunni / al-Faqih / other Imami), v3.2 tool then v3.3 tool", "", "| hold | v3.2 hits | v3.2 per group | v3.3 hits | v3.3 per group |", "|---|---|---|---|---|"]
    result["holds"] = {}
    for code in codes:
        o, n = agreed_hits(old, code), agreed_hits(new, code)
        per = lambda ids: " / ".join(str(sum(group[i] == g for i in ids)) for g in GROUPS)  # noqa: E731
        result["holds"][code] = {"v3_2": len(o), "v3_3": len(n), "v3_2_per_group": per(o), "v3_3_per_group": per(n)}
        mark = " **(changed)**" if code in V33_CHANGED or code in V32_ONLY else ""
        lines.append(f"| `{code}`{mark} | {len(o)} | {per(o)} | {len(n)} | {per(n)} |")

    # ---- 3. the changed holds, judged ----
    old_eligible = {i for i, r in old.items() if r["eligible"] == "True"}
    new_eligible = {i for i, r in new.items() if r["eligible"] == "True"}
    lines += ["", "## 3. The changed and new holds: hits on agreed readings and the judge's verdict among them", "",
              "R = judged right, W = judged wrong, CT = cannot tell, - = not judged. 'Eligible under v3.2' = the readings this hold would take out of the apply list.", "",
              "| hold | hits on agreed | of them eligible under v3.2 | judged W | judged R | judged CT | not judged |", "|---|---|---|---|---|---|---|"]
    result["changed_holds"] = {}
    for code in V33_CHANGED:
        hits = agreed_hits(new, code)
        cost = [i for i in hits if i in old_eligible]
        verdict = lambda ids, v: sorted(i[4:] for i in ids if judged.get(i) == v)  # noqa: E731
        row = {"hits": len(hits), "eligible_v3_2": len(cost), "W": verdict(hits, "W"), "R": verdict(hits, "R"), "CT": verdict(hits, "CT"), "not_judged": sorted(i[4:] for i in hits if i not in judged),
               "eligible_v3_2_W": verdict(cost, "W"), "eligible_v3_2_R": verdict(cost, "R"), "eligible_v3_2_CT": verdict(cost, "CT")}
        result["changed_holds"][code] = row
        lines.append(f"| `{code}` | {len(hits)} | {len(cost)} | {len(row['W'])} {' '.join(row['W'])} | {len(row['R'])} {' '.join(row['R'])} | {len(row['CT'])} {' '.join(row['CT'])} | {len(row['not_judged'])} |")
    # readings the changes RELEASE (held by v3.2, eligible under v3.3)
    released = sorted(i for i in new_eligible - old_eligible)
    lines += ["", f"Released by v3.3 (eligible under v3.3, held or not agreed under v3.2): {len(released)}; judged: " + (", ".join(f"{i[4:]} {judged[i]}" for i in released if i in judged) or "none"), ""]
    result["released"] = {"count": len(released), "judged": {i[4:]: judged[i] for i in released if i in judged}}
    newly_held = sorted(old_eligible - new_eligible)
    lines += [f"Newly held by v3.3 (eligible under v3.2, held under v3.3): {len(newly_held)}; judged: " + (", ".join(f"{i[4:]} {judged[i]} ({'+'.join(holds_of(new[i]))})" for i in newly_held if i in judged) or "none"), ""]
    result["newly_held"] = {"count": len(newly_held), "judged": {i[4:]: [judged[i], holds_of(new[i])] for i in newly_held if i in judged}, "all": {i[4:]: holds_of(new[i]) for i in newly_held}}

    # ---- 4. right-rate among judged eligible readings ----
    def rate(eligible: set[str]) -> dict:
        weights = {g: sum(1 for i in eligible if group[i] == g) for g in GROUPS}
        per_group, detail = {}, {}
        for g in GROUPS:
            members = [i for i in sampled if i in eligible and group[i] == g]
            right = sum(sampled[i] == "R" for i in members)
            per_group[g] = (right, len(members))
            detail[g] = {"judged": len(members), "right": right, "wrong": sum(sampled[i] == "W" for i in members), "undecided": sum(sampled[i] == "CT" for i in members), "text": pct(right, len(members))}
        p, (lo, hi) = weighted_rate({g: v for g, v in per_group.items() if v[1]}, weights)
        return {"per_group": detail, "weighted": {"p": round(100 * p, 1), "lo": round(100 * lo, 1), "hi": round(100 * hi, 1), "judged": sum(v[1] for v in per_group.values())}, "weights": weights}
    result["right_rate"] = {"v3_2": rate(old_eligible), "v3_3": rate(new_eligible)}
    lines += ["## 4. Right-rate among the eligible readings the judge read (undecided counts as not right; Wilson 95%; weights = each group's eligible readings under the tool)", "",
              "| tool | six Sunni books | al-Faqih | other Imami | weighted |", "|---|---|---|---|---|"]
    for tool in ("v3_2", "v3_3"):
        r = result["right_rate"][tool]
        w = r["weighted"]
        lines.append(f"| {tool.replace('_', '.')} | " + " | ".join(r["per_group"][g]["text"] for g in GROUPS) + f" | **{w['p']}% ({w['lo']}-{w['hi']})** ({w['judged']} judged) |")
    lines += ["", f"Judged reading set: {len(sampled)} sampled readings of the judge (the random draws); {len(judged)} readings judged in all (adds the judge's hold, variant and scan reads). {status}", ""]

    # ---- 5. judged-wrong still eligible, judged-right now held ----
    wrong_eligible = sorted((i, judged[i]) for i in new_eligible if judged.get(i) in ("W", "CT"))
    right_held = sorted(i for i in judged if judged[i] == "R" and i in new and i not in new_eligible and i in old_eligible)
    right_held_all = sorted(i for i in judged if judged[i] == "R" and i in new and i not in new_eligible)
    lines += ["## 5. Judged readings that go the wrong way", "", f"**Judged wrong or undecided and still eligible under v3.3: {len(wrong_eligible)}**", ""]
    for i, v in wrong_eligible:
        lines.append(f"- {i} {v} ({LABEL[group[i]]}; {source.get(i, '')}; eligible under v3.2: {i in old_eligible})")
    lines += ["", f"**Judged right and eligible under v3.2, held under v3.3: {len(right_held)}** (judged right and not eligible under v3.3 for any reason: {len(right_held_all)})", ""]
    for i in right_held:
        lines.append(f"- {i} R ({LABEL[group[i]]}; {source.get(i, '')}): {', '.join(holds_of(new[i])) or 'not agreed'}")
    result["still_eligible_not_right"] = [[i, v] for i, v in wrong_eligible]
    result["right_now_held"] = {i: holds_of(new[i]) for i in right_held}
    result["right_not_eligible_any_reason"] = len(right_held_all)

    # ---- 6. al-Faqih route statements ----
    tagged = [i for i, r in sorted(new.items()) if "faqih_route_statement" in (r.get("tags") or "").split(",")]
    result["faqih_route_statement"] = {"reports": len(tagged), "agreed": sum(new[i]["agree"] == "True" for i in tagged), "eligible_under_v3_2": sum(i in old_eligible for i in tagged),
                                      "judged": {i[4:]: judged[i] for i in tagged if i in judged}}
    lines += ["", "## 6. al-Faqih route statements («و ما كان فيه عن X فقد رويته عن ...»)", "",
              f"Tagged `faqih_route_statement`: {len(tagged)} reports, {result['faqih_route_statement']['agreed']} agreed, {result['faqih_route_statement']['eligible_under_v3_2']} eligible under v3.2 (the number the new hold removes). "
              f"Judged: {', '.join(f'{i[4:]} {judged[i]}' for i in tagged if i in judged) or 'none'}.", ""]
    out.mkdir(parents=True, exist_ok=True)
    (out / "released_vs_v3_2.txt").write_text("".join(f"{i}{TAB}{judged.get(i, chr(45))}{TAB}{new[i][chr(97) + chr(112) + chr(112) + chr(108) + chr(105) + chr(101) + chr(115)]}{NEWLINE}" for i in released), encoding="utf-8", newline=NEWLINE)
    rows_out = [TAB.join(["id", "agreed", "eligible_v3_2", "other_holds_v3_3", "judge_verdict"])] + [TAB.join([i, new[i]["agree"], str(i in old_eligible), ",".join(c for c in holds_of(new[i]) if c != "needs_ruling_faqih_route_statement"), judged.get(i, "")]) for i in tagged]
    (out / "faqih_route_statements.tsv").write_text(NEWLINE.join(rows_out) + NEWLINE, encoding="utf-8", newline=NEWLINE)
    with (out / "hold_hits.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "group", "code", "eligible_v3_2", "eligible_v3_3", "judge_verdict"])
        for code in V33_CHANGED:
            for i in agreed_hits(new, code):
                writer.writerow([i, group[i], code, i in old_eligible, i in new_eligible, judged.get(i, "")])
    (out / "RETRIAGE_V3_3.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (out / "numbers.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    result["_new_eligible"], result["_judged"], result["_source"], result["_new"] = new_eligible, judged, source, new
    return result


def apply_list(result: dict, out: Path) -> dict:
    """eligible_v3_3.txt = eligible under v3.3 minus judged wrong / cannot tell; withheld_by_judge.txt = those, with the reason."""
    judged, source, new = result["_judged"], result["_source"], result["_new"]
    withheld = sorted(i for i in result["_new_eligible"] if judged.get(i) in ("W", "CT"))
    apply = sorted(i for i in result["_new_eligible"] if i not in set(withheld))
    (out / "eligible_v3_3.txt").write_text("\n".join(apply) + "\n", encoding="utf-8", newline="\n")
    (out / "withheld_by_judge.txt").write_text("".join(f"{i}\t{'wrong' if judged[i] == 'W' else 'cannot tell'}\t{source.get(i, '')}\t{new[i]['applies']}\n" for i in withheld), encoding="utf-8", newline="\n")
    return {"eligible_v3_3": len(result["_new_eligible"]), "apply": len(apply), "apply_chain": sum(new[i]["applies"] == "chain" for i in apply), "apply_no_chain": sum(new[i]["applies"] == "no_chain" for i in apply),
            "withheld": len(withheld), "withheld_wrong": sum(judged[i] == "W" for i in withheld), "withheld_ct": sum(judged[i] == "CT" for i in withheld)}


def batch_lists(out: Path, new: dict[str, dict], old: dict[str, dict]) -> dict:
    """Which of the 348 applied readings of batch 001 v3.3 would hold, which of the 46 held ones it would release (the fix store's queue; fix ids to reading ids through the submissions)."""
    store = REPO / "reviews" / "ai" / "records" / "chain-fixes"
    queue = json.loads((store / "queue.json").read_text(encoding="utf-8"))
    reading_of: dict[str, str] = {}
    for path in sorted((store / "submissions").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                reading_of[row["fix_id"]] = row["reading"]["id"]
    applied = {reading_of[f]: [] for f in queue["awaiting_final_review"]}
    held = {reading_of[h["fix_id"]]: h["holds"] for h in queue["held"]}
    with (out / "would_hold_of_applied.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "v3_3_holds", "of_which_new_in_v3_3"])
        would_hold = []
        for i in sorted(applied):
            if new[i]["eligible"] != "True":
                codes = holds_of(new[i])
                would_hold.append(i)
                writer.writerow([i, ",".join(codes) or "not agreed", ",".join(c for c in codes if c in ("mutabaa_marker", "route_ends_inside_another_route", "needs_ruling_faqih_route_statement"))])
    tool_codes = {"has_variant_group", "route_at_most_half_the_longest", "semicolon_in_multi_route_isnad", "needs_ruling_prophet_no_transmitter", "imami_single_narrator_without_source", "routes_end_at_different_links"}
    released = []
    with (out / "would_release_of_held.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=TAB, lineterminator=NEWLINE)
        writer.writerow(["id", "queue_holds", "tool_side_holds_in_queue", "v3_3_eligible", "v3_3_holds", "pipeline_holds_that_remain"])
        for i in sorted(held):
            tool_side = [c for c in held[i] if c in tool_codes]
            remaining = [c for c in held[i] if c not in tool_codes]
            if tool_side and new[i]["eligible"] == "True":
                released.append((i, remaining))
            writer.writerow([i, ",".join(held[i]), ",".join(tool_side), new[i]["eligible"], ",".join(holds_of(new[i])), ",".join(remaining)])
    tags = Counter(c for i in would_hold for c in holds_of(new[i]))
    return {"applied": len(applied), "held": len(held), "would_hold": sorted(would_hold), "would_hold_codes": dict(tags), "would_release": released,
            "would_release_free": [i for i, remaining in released if not remaining]}


def main() -> None:
    summary: dict = {}
    for name, number, title, status in (("t02", "02", "Tranche 02 under the v3.3 tool", "**Sample status: IN-SAMPLE for the v3.3 changes (they were designed on tranche 02's judgement); the judge's draw of 244 is the same sample.**"),
                                        ("t01", "01", "Tranche 01 under the v3.3 tool", "**Sample status: OUT OF SAMPLE for the v3.3 changes (designed on tranche 02), still IN-SAMPLE for the v3.2 holds (designed on tranche 01).**")):
        base = ROOT / "tranches" / f"tranche-{number}"
        result = evaluate(name, base / "triage-v3_2" / "triage.tsv", base / "triage-v3_3" / "triage.tsv", base / "triage-v3_3", title, status)
        summary[name] = {"apply_list": apply_list(result, base / "triage-v3_3"), "right_rate": result["right_rate"], "faqih_route_statement": result["faqih_route_statement"]}
    out = HERE / "batch-001"
    result = evaluate("b1", ROOT / "v3_2" / "batch-001" / "triage" / "triage.tsv", out / "triage" / "triage.tsv", out, "Batch 001 under the v3.3 tool",
                      "**Sample status: OUT OF SAMPLE for the v3.3 changes. The judged readings (301) were drawn from the readings eligible under v3 (the first judge), before any v3.2 or v3.3 hold existed.**")
    summary["b1"] = {"lists": batch_lists(out, result["_new"], read_tsv(ROOT / "v3_2" / "batch-001" / "triage" / "triage.tsv")), "right_rate": result["right_rate"], "faqih_route_statement": result["faqih_route_statement"]}
    (HERE / "summary_v3_3.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: v.get("apply_list") or {kk: (vv if not isinstance(vv, list) else len(vv)) for kk, vv in v["lists"].items() if kk != "would_hold_codes"} for k, v in summary.items()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
