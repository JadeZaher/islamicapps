"""Batch 001 (v3 outputs, already applied through the v3.1 tool) under the v3.2 tool: which of the 394 readings of `v3_1/batch-001/eligible_to_apply.txt` would now be held, and why.

    python -B -X utf8 v3_2/triage_v3_2.py --packets v3/batch-001/packets --pass-a v3/batch-001/outputs/pass-a --pass-b v3/batch-001/outputs/pass-b --out v3_2/batch-001/triage --reports v3/batch-001/private/reports.jsonl
    python -B -X utf8 v3_2/evaluate_batch001_v3_2.py                         (from chain-reader/)

Reads (read-only): v3/batch-001/{packets, private/reports.jsonl, triage}, v3_1/batch-001/{eligible_to_apply.txt, triage, retriage_batch001.py constants}, analysis-batch-001/{sample.tsv, v_dis.txt}.
Writes v3_2/batch-001/: RETRIAGE_V3_2.md, numbers.json, held_of_394.tsv. Verdicts are the first judge's (one model, not blind), adjusted to the owner's rulings of 2026-11-22 exactly as `retriage_batch001.py` does.
IN-SAMPLE for the holds that were measured on batch 001's own findings; the v3.2 holds were designed on tranche 01's sample, so batch 001 is a second, partly independent look.
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
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "v3_1" / "batch-001"))
from eval_lib_v3_2 import holds_of, pct, read_tsv, weighted_rate  # noqa: E402
from retriage_batch001 import RIGHT, ROUTES_END_VERDICT, RULING_ADJUSTED, group_of  # noqa: E402  (the first judge's constants; importing runs nothing)

B1 = ROOT / "v3" / "batch-001"
V31 = ROOT / "v3_1" / "batch-001"
OUT = HERE / "batch-001"
JUDGE = ROOT / "analysis-batch-001"
GROUPS = ("sunni six-book", "al-faqih", "other imami")


def main() -> None:
    v3, v31, v32 = read_tsv(B1 / "triage" / "triage.tsv"), read_tsv(V31 / "triage" / "triage.tsv"), read_tsv(OUT / "triage" / "triage.tsv")
    apply_ids = [line.strip() for line in (V31 / "eligible_to_apply.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    group = {i: group_of(r["work"]) for i, r in v32.items()}
    judge = read_tsv(JUDGE / "sample.tsv")
    dis = {"b1-" + line.split("|")[0]: line.split("|")[2] for line in (JUDGE / "v_dis.txt").read_text(encoding="utf-8").splitlines() if line.strip()}

    def verdict(i: str) -> str:
        """right | wrong | undecided | no_chain_right | no_chain_undecided | unjudged (the first judge's, under the owner's rulings)."""
        row = judge.get(i)
        if row and row["class"] == "empty-reading hold":
            return "no_chain_right" if row["reader"] == "empty reading: right" else "no_chain_undecided"
        if i in RULING_ADJUSTED:
            return RULING_ADJUSTED[i]
        if row:
            return "right" if row["reader"] in RIGHT else "wrong" if row["reader"] == "wrong" else "undecided"
        if i in ROUTES_END_VERDICT:
            return ROUTES_END_VERDICT[i]
        return "right" if dis.get(i, "").startswith("both right") else "unjudged"

    def figures(table: dict[str, dict]) -> dict:
        eligible = [r for r in table.values() if r["eligible"] == "True"]
        return {"valid_a": sum(r["valid_a"] == "True" for r in table.values()), "valid_b": sum(r["valid_b"] == "True" for r in table.values()), "agreed": sum(r["agree"] == "True" for r in table.values()),
                "eligible": len(eligible), "chain": sum(r.get("applies", "chain") == "chain" for r in eligible), "no_chain": sum(r.get("applies") == "no_chain" for r in eligible)}
    result: dict = {"counts": {"v3": figures(v3), "v3_1": figures(v31), "v3_2": figures(v32)}}
    # ---- variant groups ----
    result["variant_group"] = {"agreed_readings": sum(r["variant_group"] == "True" and r["agree"] == "True" for r in v32.values()),
                               "eligible_under_v3_1": sum(r["variant_group"] == "True" and v31[i]["eligible"] == "True" for i, r in v32.items()),
                               "of_the_394": sum(v32[i]["variant_group"] == "True" for i in apply_ids), "any_pass": sum(r["variant_group"] == "True" for r in v32.values())}
    # ---- the 394 ----
    still = [i for i in apply_ids if v32[i]["eligible"] == "True"]
    held = [i for i in apply_ids if v32[i]["eligible"] != "True"]
    by_hold: dict[str, list[str]] = defaultdict(list)
    for i in held:
        for code in holds_of(v32[i]) or ["not_agreed"]:
            by_hold[code].append(i)
    result["of_394"] = {"still_eligible": len(still), "held": len(held), "held_by_hold": {c: [i[3:] for i in ids] for c, ids in by_hold.items()},
                        "held_verdicts": dict(Counter(verdict(i) for i in held)), "held_ids_by_verdict": {v: [i[3:] for i in held if verdict(i) == v] for v in sorted({verdict(i) for i in held})}}
    lines = ["## 1. Triage figures", "", "| | valid A / B | agreed | eligible (chain + no chain) |", "|---|---|---|---|"]
    for name, f in result["counts"].items():
        lines.append(f"| {name.replace('_', '.')} | {f['valid_a']} / {f['valid_b']} | {f['agreed']} | {f['eligible']} = {f['chain']} + {f['no_chain']} |")
    lines += ["", f"Readings with a variant group in batch 001: {result['variant_group']['any_pass']} in at least one valid pass, {result['variant_group']['agreed_readings']} agreed, {result['variant_group']['eligible_under_v3_1']} eligible under v3.1, "
              f"{result['variant_group']['of_the_394']} of the 394."]
    lines += ["", f"## 2. The 394 readings of `eligible_to_apply.txt`: {len(held)} would now be held, {len(still)} stay eligible", "", "| hold | n | ids (judge verdict) |", "|---|---|---|"]
    for code, ids in sorted(by_hold.items()):
        lines.append(f"| `{code}` | {len(ids)} | " + ", ".join(f"{i[3:]} ({verdict(i)})" for i in ids) + " |")
    lines.append("")
    lines.append(f"Judge's verdict of the {len(held)} held: {result['of_394']['held_verdicts']}.")
    # ---- the variant routes v3.1 stored ----
    variant_rows = []
    for i in held:
        if "has_variant_group" not in holds_of(v32[i]):
            continue
        old = json.loads((V31 / "triage" / "readings" / f"{i}.json").read_text(encoding="utf-8"))["expanded_a"]
        stored_variants = [" > ".join(l["surface"] for l in r["links"] if l["kind"] != "compiler_head") for r in old["routes"] if r.get("variant")]
        new = json.loads((OUT / "triage" / "readings" / f"{i}.json").read_text(encoding="utf-8"))["expanded_a"]
        variant_rows.append({"id": i[3:], "verdict": verdict(i), "variant_routes_v3_1_would_store": stored_variants, "variant_remarks_v3_2": [r["quote"][:120] for r in new["variant_remarks"]]})
    result["variant_routes_in_the_394"] = variant_rows
    lines += ["", "### The variant remarks among the 394 (what v3.1 stores as a chain and v3.2 would not)", ""]
    for row in variant_rows:
        lines.append(f"- {row['id']} (judge: {row['verdict']}): v3.1 stores the extra route(s) {row['variant_routes_v3_1_would_store']}; remark: {row['variant_remarks_v3_2']}")
    # ---- right-rate among the judged chain readings of the 394 ----
    def table(ids: list[str]) -> dict:
        per_group = {}
        for g in GROUPS:
            members = [i for i in ids if group[i] == g and verdict(i) in ("right", "wrong", "undecided")]
            per_group[g] = (sum(verdict(i) == "right" for i in members), len(members))
        return per_group
    old_table, new_table = table(apply_ids), table(still)
    weights = {g: sum(1 for i in apply_ids if group[i] == g) for g in GROUPS}
    result["right_rate_judged_chain_readings_of_394"] = {}
    lines += ["", "## 3. Right-rate among the judged chain readings of the 394 (undecided counts as not right; the first judge's verdicts under the 2026-11-22 rulings)", "",
              "| | group | v3.1 (all 394) | v3.2 (those still eligible) |", "|---|---|---|---|"]
    for g in GROUPS:
        lines.append(f"| | {g} | {pct(*old_table[g])} | {pct(*new_table[g])} |")
        result["right_rate_judged_chain_readings_of_394"][g] = {"v3_1": pct(*old_table[g]), "v3_2": pct(*new_table[g])}
    p_old, ci_old = weighted_rate(old_table, weights)
    p_new, ci_new = weighted_rate(new_table, weights)
    lines.append(f"| | weighted by the 394's group sizes {weights} | {100 * p_old:.1f}% ({100 * ci_old[0]:.1f}-{100 * ci_old[1]:.1f}) | {100 * p_new:.1f}% ({100 * ci_new[0]:.1f}-{100 * ci_new[1]:.1f}) |")
    result["right_rate_judged_chain_readings_of_394"]["weighted"] = {"v3_1": f"{100 * p_old:.1f}%", "v3_2": f"{100 * p_new:.1f}%"}
    judged_wrong_in_394 = [i[3:] for i in apply_ids if verdict(i) == "wrong"]
    lines += ["", f"Judged wrong among the 394: {judged_wrong_in_394 or 'none'}. Judged undecided among the 394 chain readings: {[i[3:] for i in apply_ids if verdict(i) == 'undecided'] or 'none'}."]
    # ---- eligible under v3.2 but not in the 394 ----
    new_only = sorted(i for i, r in v32.items() if r["eligible"] == "True" and i not in set(apply_ids))
    result["eligible_v3_2_outside_the_394"] = {"n": len(new_only), "ids": [i[3:] for i in new_only]}
    lines += ["", f"Eligible under v3.2 but not in the 394 (rereads and withheld readings, plus the newly agreed): {len(new_only)}."]
    with (OUT / "held_of_394.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "group", "applies_v3_1", "holds_v3_2", "judge_verdict", "judge_quote"])
        for i in held:
            writer.writerow([i, group[i], v31[i]["applies"], v32[i]["holds"] or "not agreed", verdict(i), (judge[i]["quote"][:100] if i in judge else "")])
    (OUT / "RETRIAGE_V3_2.md").write_text("---\ntype: analysis\n---\n# Batch 001 under the v3.2 tool (generated by v3_2/evaluate_batch001_v3_2.py)\n\n" + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (OUT / "numbers.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
