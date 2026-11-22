"""Re-triage batch 001 with the v3.1 tool (no model run) and measure it against the batch-001 judge's verdicts.

    python -B -X utf8 v3_1/batch-001/retriage_batch001.py            (from chain-reader/)

Reads (read-only): v3/batch-001/{packets,outputs,private/reports.jsonl,triage/triage.tsv}, analysis-batch-001/{sample.tsv,v_dis.txt}.
Writes here: triage/ (the v3.1 triage of the existing outputs: triage.tsv, readings/, eligible.txt, no_chain.txt, summary.json), retriage.json, RETRIAGE.md,
eligible_to_apply.txt (agreed, unheld under v3.1, untouched by the new rulings: can be applied now), reread_under_v3_1.txt (the readings the asker ruling makes wrong and every
report whose text opens as an asker, an inherited speaker or a bare «وعن»: they are read again under v3.1 packets and prompt, not applied).

Verdicts are the judge's (one Arabic reader, not blind; analysis-batch-001/README.md). Where a verdict turns on the owner's rulings of 2026-11-22 it is adjusted as `RULING_ADJUSTED` says.
"""

from __future__ import annotations

import csv
import json
import math
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V31 = HERE.parent
ROOT = V31.parent
B1 = ROOT / "v3" / "batch-001"
JUDGE_DIR = ROOT / "analysis-batch-001"
for path in (str(ROOT), str(V31)):
    sys.path.insert(0, path)

import holds_v3_1  # noqa: E402
import triage_v3_1  # noqa: E402

GROUPS = ("sunni six-book", "al-faqih", "other imami")
RIGHT = {"right", "representation only"}
# The judge's Q1d (the readers dropped a third-person asker: right under the ruling as given, wrong now) and Q1k (a reader kept the writer of the question: wrong then, right now).
ASKER_NOW_WRONG = ("1507aa", "2fd814", "5d1972", "7b9421", "9fc153", "b348c8", "b9039f", "b908c9", "f03941")
RULING_ADJUSTED = {**{"b1-" + short: "wrong" for short in ASKER_NOW_WRONG}, "b1-4cbe02": "right"}
# Judged by the batch-001 judge outside sample.tsv: routes_end_at_different_links on agreed readings (cases.md section 5), and the disagreements read (v_dis.txt: "both right").
ROUTES_END_VERDICT = {"b1-160be9": "wrong", "b1-162ebe": "wrong", "b1-21210d": "right", "b1-3c59ef": "right", "b1-844adb": "wrong", "b1-d2bb6c": "wrong", "b1-ee5c9a": "wrong"}


def group_of(work: str) -> str:
    return "sunni six-book" if work.startswith("sunni") else "al-faqih" if "faqih" in work else "other imami"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def pct(k: int, n: int) -> str:
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f}% ({100 * lo:.0f}-{100 * hi:.0f})"


def read_tsv(path: Path) -> dict[str, dict]:
    return {row["id"]: row for row in csv.DictReader(path.open(encoding="utf-8"), delimiter="\t")}


def main() -> None:
    packets = triage_v3_1.load_packets(B1 / "packets")
    stored = {row["id"]: [s for chain in row["stored_chains"] for s in chain["surfaces"]]
              for row in (json.loads(line) for line in (B1 / "private" / "reports.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())}
    out = HERE / "triage"
    triage_v3_1.main(["--packets", str(B1 / "packets"), "--pass-a", str(B1 / "outputs" / "pass-a"), "--pass-b", str(B1 / "outputs" / "pass-b"), "--out", str(out), "--reports", str(B1 / "private" / "reports.jsonl")])
    old = read_tsv(B1 / "triage" / "triage.tsv")
    new = read_tsv(out / "triage.tsv")
    judge = read_tsv(JUDGE_DIR / "sample.tsv")
    dis = {"b1-" + line.split("|")[0]: line.split("|")[2] for line in (JUDGE_DIR / "v_dis.txt").read_text(encoding="utf-8").splitlines() if line.strip()}
    work = {i: packets[i]["context"]["work"]["key"] for i in packets}
    group = {i: group_of(work[i]) for i in packets}
    chain_judged = {i: r for i, r in judge.items() if r["class"] != "empty-reading hold"}
    empty_judged = {i: r for i, r in judge.items() if r["class"] == "empty-reading hold"}

    def verdict(i: str, ruled: bool) -> str:
        """right | wrong | undecided for a judged chain reading; `ruled` applies the owner's rulings of 2026-11-22."""
        if ruled and i in RULING_ADJUSTED:
            return RULING_ADJUSTED[i]
        read = chain_judged[i]["reader"]
        return "right" if read in RIGHT else "wrong" if read == "wrong" else "undecided"

    def rate_table(ids_by_verdict: dict[str, str], shares: dict[str, int]) -> dict:
        rows, weighted_num, weighted_den = {}, 0.0, 0
        for g in GROUPS:
            members = [i for i in ids_by_verdict if group[i] == g]
            right = sum(1 for i in members if ids_by_verdict[i] == "right")
            rows[g] = {"judged": len(members), "right": right, "wrong": sum(1 for i in members if ids_by_verdict[i] == "wrong"), "undecided": sum(1 for i in members if ids_by_verdict[i] == "undecided"),
                       "rate": pct(right, len(members)), "eligible": shares[g]}
            if members:
                weighted_num += shares[g] * right / len(members)
                weighted_den += shares[g]
        allids = list(ids_by_verdict)
        rows["overall_unweighted"] = {"judged": len(allids), "right": sum(v == "right" for v in ids_by_verdict.values()), "rate": pct(sum(v == "right" for v in ids_by_verdict.values()), len(allids))}
        rows["overall_weighted_by_eligible_share"] = f"{100 * weighted_num / weighted_den:.1f}%"
        return rows

    # eligible readings with chain links, before (v3) and after (v3.1)
    def eligible_chain(table: dict[str, dict], applies: bool) -> list[str]:
        return [i for i, r in table.items() if r["eligible"] == "True" and (not applies or r["applies"] == "chain")]

    old_eligible = eligible_chain(old, False)
    new_eligible = eligible_chain(new, True)
    shares_old = Counter(group[i] for i in old_eligible)
    shares_new = Counter(group[i] for i in new_eligible)

    before = {i: verdict(i, False) for i in old_eligible if i in chain_judged}
    before_ruled = {i: verdict(i, True) for i in old_eligible if i in chain_judged}
    after: dict[str, str] = {i: verdict(i, True) for i in new_eligible if i in chain_judged}
    outside = {}                                                   # judged outside sample.tsv, now eligible
    for i in new_eligible:
        if i in chain_judged:
            continue
        if i in ROUTES_END_VERDICT:
            outside[i] = ROUTES_END_VERDICT[i]
        elif dis.get(i, "").startswith("both right"):
            outside[i] = "right"
    after_all = {**after, **outside}

    # empty readings
    empties_apply = [i for i in empty_judged if new[i]["applies"] == "no_chain"]
    empties_held = [i for i in empty_judged if new[i]["applies"] != "no_chain"]
    empty_verdicts = Counter(empty_judged[i]["reader"] for i in empties_apply)
    empties_by_category = Counter(empty_judged[i]["owner_question_tags"].split(",")[0] for i in empties_held)
    unjudged_empty_applies = [i for i in new if new[i]["applies"] == "no_chain" and i not in empty_judged]

    # holds: hits on agreed readings, old and new
    def hits(table: dict[str, dict], code: str) -> list[str]:
        return sorted(i for i, r in table.items() if r["agree"] == "True" and code in r["holds"].split(","))

    hold_rows = {}
    for code in ("routes_end_at_different_links", "reading_empty_stored_has_links", "empty_reading_transmission_name", "empty_reading_unsettled_opening", "asker_not_a_link",
                 "back_reference_without_previous_report", "back_reference_only", "needs_ruling", "nested_jami", "nested_semicolon"):
        hold_rows[code] = {"v3_hits": len(hits(old, code)), "v3_1_hits": len(hits(new, code))}
    routes_old, routes_new = hits(old, "routes_end_at_different_links"), hits(new, "routes_end_at_different_links")
    hold_rows["routes_end_at_different_links"].update({
        "v3_right_wrong": [sum(ROUTES_END_VERDICT.get(i) == "right" for i in routes_old), sum(ROUTES_END_VERDICT.get(i) == "wrong" for i in routes_old)],
        "v3_1_right_wrong": [sum(ROUTES_END_VERDICT.get(i) == "right" for i in routes_new), sum(ROUTES_END_VERDICT.get(i) == "wrong" for i in routes_new)],
        "released": sorted(set(routes_old) - set(routes_new)), "still_held": sorted(routes_new)})
    unsettled = hits(new, "empty_reading_unsettled_opening")
    categories = Counter(empty_judged[i]["owner_question_tags"].split(",")[0] if i in empty_judged else "not judged" for i in unsettled)
    hold_rows["empty_reading_unsettled_opening"]["by_category"] = dict(categories)
    asker_hits = hits(new, "asker_not_a_link")
    hold_rows["asker_not_a_link"].update({"judged_Q1d": sum(i[3:] in ASKER_NOW_WRONG for i in asker_hits), "not_judged_eligible_in_v3": sorted(i for i in asker_hits if old[i]["eligible"] == "True" and i not in chain_judged),
                                          "not_eligible_in_v3": sorted(i for i in asker_hits if old[i]["eligible"] != "True"), "all_wrong_under_ruling": True})
    old_empty_hits = hits(old, "reading_empty_stored_has_links")
    hold_rows["reading_empty_stored_has_links"]["judged"] = {"right_as_no_chain": sum(empty_judged[i]["reader"] == "empty reading: right" for i in old_empty_hits if i in empty_judged),
                                                             "undecided": sum(empty_judged[i]["reader"] == "empty reading: cannot tell" for i in old_empty_hits if i in empty_judged), "wrong": 0, "of": len(old_empty_hits)}

    # reports the rulings touch
    classes = {i: holds_v3_1.opening_class(packets[i]["text"]) for i in packets}
    pattern_ids = sorted(i for i, c in classes.items() if c in ("asker_named", "asker_pronoun", "implicit_speaker", "bare_an", "first_person"))
    made_wrong = sorted(i for i in old_eligible if "asker_not_a_link" in new[i]["holds"].split(","))
    reread = sorted(set(pattern_ids) | set(made_wrong))
    eligible_ids = sorted(i for i, r in new.items() if r["eligible"] == "True")
    unruled_tags = ("Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q9")                     # points the owner has NOT ruled on (the brief's item 4): a judged reading that turns on one is withheld
    withheld = sorted(i for i in eligible_ids if i in judge and (judge[i]["reader"] == "cannot tell" or any(tag in judge[i]["owner_question_tags"].split(",") for tag in unruled_tags)))
    to_apply = [i for i in eligible_ids if i not in set(reread) and i not in set(withheld)]
    matched_but_eligible = [i for i in reread if new[i]["eligible"] == "True"]

    (HERE / "eligible_to_apply.txt").write_text("\n".join(to_apply) + "\n", encoding="utf-8", newline="\n")
    (HERE / "reread_under_v3_1.txt").write_text("\n".join(reread) + "\n", encoding="utf-8", newline="\n")

    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    result = {
        "tool": "v3.1 tool on the v3 outputs of batch 001 (500 reports, prompt v3.0.0, packets without the new previous reports)",
        "counts": {"v3": {"valid_a": sum(r["valid_a"] == "True" for r in old.values()), "valid_b": sum(r["valid_b"] == "True" for r in old.values()), "agreed": sum(r["agree"] == "True" for r in old.values()), "eligible": sum(r["eligible"] == "True" for r in old.values())},
                   "v3_1": {"valid_a": summary["valid_a"], "valid_b": summary["valid_b"], "agreed": summary["agreed"], "eligible": summary["eligible"], "applies_chain": summary["applies_chain"], "applies_no_chain": summary["applies_no_chain"]}},
        "newly_agreed": sorted(i for i in new if new[i]["agree"] == "True" and old[i]["agree"] != "True"),
        "newly_valid": sorted(i for i in new if (new[i]["valid_a"] == "True" and old[i]["valid_a"] != "True") or (new[i]["valid_b"] == "True" and old[i]["valid_b"] != "True")),
        "right_rate_among_eligible_judged": {"before_v3_as_judged": rate_table(before, shares_old), "v3_outputs_under_the_new_rulings_no_tool_change": rate_table(before_ruled, shares_old),
                                             "after_v3_1_tool": rate_table(after_all, shares_new)},
        "after_judged_outside_sample_tsv": outside,
        "eligible_chain_readings": {"v3": len(old_eligible), "v3_1": len(new_eligible), "v3_1_judged": len(after), "v3_1_not_judged": len(new_eligible) - len(after) - len(outside)},
        "empties": {"judged": len(empty_judged), "made_applicable": len(empties_apply), "judge_verdict_of_those": dict(empty_verdicts), "held_or_reread": len(empties_held), "held_by_category": dict(empties_by_category),
                    "applicable_not_judged": unjudged_empty_applies},
        "holds": hold_rows,
        "asker_ruling": {"eligible_v3_readings_made_wrong": len(made_wrong), "of_which_judged": sum(i[3:] in ASKER_NOW_WRONG for i in made_wrong), "ids": made_wrong},
        "eligible_to_apply": len(to_apply), "withheld_judged_undecided_or_unruled": withheld, "reread_under_v3_1": len(reread),
        "reread_by_opening": dict(Counter(classes[i] or "asker ruling (other)" for i in reread)), "reread_matched_but_eligible_and_consistent": matched_but_eligible,
        "not_reread_but_unruled": sorted(i for i, c in classes.items() if c == "collective"),
    }
    (HERE / "retriage.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    rt = result["right_rate_among_eligible_judged"]
    lines = ["---", "type: analysis", "---", "# Batch 001 re-triaged with the v3.1 tool (no model run)", "",
             "Existing v3 outputs of both passes, the v3 packets, the v3.1 tool (folds, holds, empty readings, asker rule). Verdicts are the batch-001 judge's (`analysis-batch-001/`), adjusted where the owner's rulings of 2026-11-22 change them (the nine third-person askers, `b1-4cbe02`).", "",
             "## Agreed, eligible", "", "| | v3 | v3.1 |", "|---|---|---|",
             f"| valid outputs A / B | 493 / 493 | {summary['valid_a']} / {summary['valid_b']} |", f"| agreed | {result['counts']['v3']['agreed']} | {summary['agreed']} |",
             f"| eligible (agreed, readable, no hold) | {result['counts']['v3']['eligible']} | {summary['eligible']} (chain {summary['applies_chain']}, no chain by reading {summary['applies_no_chain']}) |", "",
             f"Newly valid: {', '.join(i[3:] for i in result['newly_valid'])}. Newly agreed: {', '.join(i[3:] for i in result['newly_agreed'])}.", "",
             "## Right-rate among the eligible chain readings the judge read", "", "| tool and rulings | group | judged | right | wrong | undecided | right (Wilson 95%) | eligible in group |", "|---|---|---|---|---|---|---|---|"]
    for name, key in (("v3 as judged (rulings as given then)", "before_v3_as_judged"), ("v3 outputs applied under the new rulings", "v3_outputs_under_the_new_rulings_no_tool_change"), ("v3.1 tool", "after_v3_1_tool")):
        for g in GROUPS:
            r = rt[key][g]
            lines.append(f"| {name} | {g} | {r['judged']} | {r['right']} | {r['wrong']} | {r['undecided']} | {r['rate']} | {r['eligible']} |")
        r = rt[key]["overall_unweighted"]
        lines.append(f"| {name} | **overall** | {r['judged']} | {r['right']} | | | {r['rate']}; weighted by eligible share {rt[key]['overall_weighted_by_eligible_share']} | |")
    lines += ["", f"The v3.1 row includes {len(outside)} readings the judge read outside sample.tsv that the tool now lets through: {', '.join(f'{i[3:]} ({v})' for i, v in sorted(outside.items()))}.",
              f"Eligible chain readings: v3 {len(old_eligible)}, v3.1 {len(new_eligible)} ({len(after)} in sample.tsv, {len(outside)} read elsewhere, {len(new_eligible) - len(after) - len(outside)} not read by the judge).", "",
              "## Asker ruling", "", f"{len(made_wrong)} v3-eligible readings are made wrong by the ruling (the reader dropped the asker): {sum(i[3:] in ASKER_NOW_WRONG for i in made_wrong)} judged (Q1d) and {len(made_wrong) - sum(i[3:] in ASKER_NOW_WRONG for i in made_wrong)} not read, every one of the same shape (`و سأل X Y`). `b1-4cbe02` (the writer of the question kept as a link) is right now.", "",
              "## Empty readings", "", f"{result['empties']['made_applicable']} of the judge's 57 empty readings are now applicable as \"no chain by reading\" (judge's verdicts of those: {dict(empty_verdicts)}); {len(empties_held)} are held: {dict(empties_by_category)}. Applicable but not judged: {len(unjudged_empty_applies)}.", "",
              "## Holds (hits on agreed readings)", "", "| hold | v3 hits | v3.1 hits | right / wrong among hits |", "|---|---|---|---|"]
    for code, row in hold_rows.items():
        note = ""
        if code == "routes_end_at_different_links":
            note = f"v3 {row['v3_right_wrong'][0]} / {row['v3_right_wrong'][1]}; v3.1 {row['v3_1_right_wrong'][0]} / {row['v3_1_right_wrong'][1]}; released {', '.join(i[3:] for i in row['released'])}"
        elif code == "reading_empty_stored_has_links":
            note = f"{row['judged']['right_as_no_chain']} right as no-chain, {row['judged']['undecided']} undecided, {row['judged']['wrong']} wrong, of {row['judged']['of']} hits"
        elif code == "empty_reading_unsettled_opening":
            note = f"empty readings the rulings touch: {row['by_category']}"
        elif code == "asker_not_a_link":
            note = "all wrong under the ruling (judged: 9; the others are the same shape)"
        elif code == "back_reference_without_previous_report":
            note = "the extra hits are the new openings in the v3 packets, which carry no previous report; the v3.1 builder supplies one"
        lines.append(f"| `{code}` | {row['v3_hits']} | {row['v3_1_hits']} | {note} |")
    lines += ["", "## Lists", "", f"- `eligible_to_apply.txt`: {len(to_apply)} readings (agreed, unheld under v3.1, outside every ruling), {sum(new[i]['applies'] == 'no_chain' for i in to_apply)} of them \"no chain by reading\"; withheld although eligible: {len(withheld)} the judge read as undecided or turning on a point not yet ruled ({', '.join(i[3:] for i in withheld)}).",
              f"- `reread_under_v3_1.txt`: {len(reread)} reports: {result['reread_by_opening']}; {len(matched_but_eligible)} of them are agreed and unheld (a pattern match whose v3 reading is consistent with the ruling) and are read again anyway.",
              f"- Not in either list: {len(result['not_reread_but_unruled'])} «روي عن الأئمة» report (not ruled; stays held)."]
    (HERE / "RETRIAGE.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({k: result[k] for k in ("counts", "eligible_chain_readings", "eligible_to_apply", "reread_under_v3_1", "reread_by_opening")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
