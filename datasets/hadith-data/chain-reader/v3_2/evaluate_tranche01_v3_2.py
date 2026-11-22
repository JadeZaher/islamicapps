"""Tranche 01 under the v3.2 tool, beside the v3.1 figures and against the judge's verdicts (IN-SAMPLE: the new holds were designed on this same sample).

    python -B -X utf8 v3_2/triage_v3_2.py --packets tranches/tranche-01/packets --pass-a tranches/tranche-01/outputs/pass-a --pass-b tranches/tranche-01/outputs/pass-b \\
        --out tranches/tranche-01/triage-v3_2 --reports tranches/tranche-01/private/reports.jsonl
    python -B -X utf8 v3_2/evaluate_tranche01_v3_2.py                       (from chain-reader/)

Reads (read-only): tranches/tranche-01/{triage, triage-v3_2, private/id_map.json, judge/analysis/{sample_verdicts.tsv, draw_extension.json, v_dis40.txt}}.
Writes tranches/tranche-01/judge-v3_2/: tables.md, numbers.json, hold_hits.tsv, caught_by_new_holds.tsv, still_eligible_not_right.tsv, newly_eligible.tsv.
The judge's verdicts are one model's, not blind (judge/analysis/README.md). A reading is `right` when the verdict is R or RO; undecided (CT) counts as not right.
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
sys.path.insert(0, str(HERE))
from eval_lib_v3_2 import GROUPS, RIGHT, holds_of, pct, read_tsv, weighted_rate  # noqa: E402

T = ROOT / "tranches" / "tranche-01"
ANALYSIS = T / "judge" / "analysis"
OUT = T / "judge-v3_2"
NEW_CODES = ("has_variant_group", "variant_only_reading", "route_at_most_half_the_longest", "first_links_split_by_comma", "semicolon_in_multi_route_isnad", "imami_single_narrator_without_source",
             "inherited_from_far_report", "needs_ruling_prophet_no_transmitter", "bracketed_insertion_differs")
LABEL = {"sunni_six_books": "six Sunni books", "imami_faqih": "al-Faqih", "imami_other_not_kafi": "other Imami"}
# the three judged-wrong readings that are one mechanism (a variant group stored as a chain): the judge's own statement is that without the variant route they are right (analysis/README.md sections 2 and 8)
VARIANT_WRONG = ("t01-30fa50", "t01-c93705", "t01-e3f7d5")


def main() -> None:
    old, new = read_tsv(T / "triage" / "triage.tsv"), read_tsv(T / "triage-v3_2" / "triage.tsv")
    stratum = {i: v["stratum"] for i, v in json.loads((T / "private" / "id_map.json").read_text(encoding="utf-8"))["ids"].items()}
    verdicts = read_tsv(ANALYSIS / "sample_verdicts.tsv")
    draw = json.loads((ANALYSIS / "draw_extension.json").read_text(encoding="utf-8"))
    sampled = set(draw["base"]) | {i for ids in draw["extension"].values() for i in ids}
    dis = {"t01-" + line.split("|")[0]: line.split("|")[1] for line in (ANALYSIS / "v_dis40.txt").read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")}
    result: dict = {}
    lines: list[str] = []

    # ---- 1. the triage figures, overall and by group ----
    def figures(table: dict[str, dict], ids: list[str]) -> dict:
        rows = [table[i] for i in ids]
        eligible = [r for r in rows if r["eligible"] == "True"]
        return {"reports": len(rows), "valid_a": sum(r["valid_a"] == "True" for r in rows), "valid_b": sum(r["valid_b"] == "True" for r in rows),
                "both_valid": sum(r["valid_a"] == "True" and r["valid_b"] == "True" for r in rows), "agreed": sum(r["agree"] == "True" for r in rows), "eligible": len(eligible),
                "eligible_chain": sum(r["applies"] == "chain" for r in eligible), "eligible_no_chain": sum(r["applies"] == "no_chain" for r in eligible)}
    everything = sorted(old)
    scopes = {"all": everything, **{g: [i for i in everything if stratum[i] == g] for g in GROUPS}}
    result["triage"] = {name: {"v3_1": figures(old, ids), "v3_2": figures(new, ids)} for name, ids in scopes.items()}
    lines += ["## 1. Triage figures, v3.1 tool against v3.2 tool (same outputs, same packets)", "", "| scope | reports | valid A | valid B | both valid | agreed | eligible (chain + no chain) |", "|---|---|---|---|---|---|---|"]
    for name, both in result["triage"].items():
        for tool in ("v3_1", "v3_2"):
            f = both[tool]
            n = f["reports"]
            lines.append(f"| {LABEL.get(name, name)} {tool.replace('_', '.')} | {n} | {f['valid_a']} ({100 * f['valid_a'] / n:.1f}%) | {f['valid_b']} ({100 * f['valid_b'] / n:.1f}%) | {f['both_valid']} ({100 * f['both_valid'] / n:.1f}%) | "
                         f"{f['agreed']} ({100 * f['agreed'] / n:.1f}%) | {f['eligible']} = {f['eligible_chain']} + {f['eligible_no_chain']} ({100 * f['eligible'] / n:.1f}%) |")

    # ---- 2. hold hits ----
    def hits(table: dict[str, dict], code: str, only: set[str] | None = None) -> list[str]:
        return sorted(i for i, r in table.items() if r["agree"] == "True" and code in holds_of(r) and (only is None or i in only))
    old_eligible = {i for i, r in old.items() if r["eligible"] == "True"}
    judged_right = {i for i, v in verdicts.items() if v["reader"] in RIGHT and i in sampled}
    judged_wrong = {i for i, v in verdicts.items() if v["reader"] == "W" and i in sampled}
    judged_ct = {i for i, v in verdicts.items() if v["reader"] == "CT" and i in sampled}
    hold_rows = []
    for code in sorted({c for r in new.values() for c in holds_of(r)}, key=lambda c: (c not in NEW_CODES, c)):
        agreed_hits = hits(new, code)
        on_v31_eligible = [i for i in agreed_hits if i in old_eligible]
        row = {"code": code, "new_in_v3_2": code in NEW_CODES, "hits_on_agreed": len(agreed_hits), "hits_on_v3_1_eligible": len(on_v31_eligible),
               "judged_wrong_caught": sorted(i[4:] for i in on_v31_eligible if i in judged_wrong), "judged_right_caught": sorted(i[4:] for i in on_v31_eligible if i in judged_right),
               "judged_cannot_tell_caught": sorted(i[4:] for i in on_v31_eligible if i in judged_ct), "v3_1_hits_on_agreed": len(hits(old, code))}
        hold_rows.append(row)
    result["holds"] = hold_rows
    lines += ["", "## 2. Each hold: hits (agreed readings; of them eligible under v3.1) and what the judge found among them", "",
              "| hold | new | hits on agreed (v3.1: same code) | of which eligible under v3.1 | judged wrong caught | judged right caught | judged undecided caught |", "|---|---|---|---|---|---|---|"]
    for r in hold_rows:
        lines.append(f"| `{r['code']}` | {'yes' if r['new_in_v3_2'] else ''} | {r['hits_on_agreed']} ({r['v3_1_hits_on_agreed']}) | {r['hits_on_v3_1_eligible']} | {', '.join(r['judged_wrong_caught']) or '-'} | "
                     f"{len(r['judged_right_caught'])} {', '.join(r['judged_right_caught'])} | {', '.join(r['judged_cannot_tell_caught']) or '-'} |")
    with (OUT / "hold_hits.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "group", "code", "eligible_in_v3_1", "judge_verdict"])
        for r in hold_rows:
            for i in hits(new, r["code"]):
                writer.writerow([i, stratum[i], r["code"], i in old_eligible, verdicts[i]["reader"] if i in verdicts and i in sampled else ""])

    # ---- 3. the right-rate among eligible readings the judge read ----
    judged = [i for i in verdicts if i in sampled]
    weights_old = {g: sum(1 for i in old_eligible if stratum[i] == g) for g in GROUPS}
    new_eligible = {i for i, r in new.items() if r["eligible"] == "True"}
    weights_new = {g: sum(1 for i in new_eligible if stratum[i] == g) for g in GROUPS}

    def rate(eligible_ids: set[str], flip_to_right: tuple[str, ...] = ()) -> tuple[dict, dict]:
        per_group, detail = {}, {}
        for g in GROUPS:
            members = [i for i in judged if stratum[i] == g and i in eligible_ids]
            right = sum(1 for i in members if verdicts[i]["reader"] in RIGHT or i in flip_to_right)
            per_group[g] = (right, len(members))
            detail[g] = {"judged": len(members), "right": right, "wrong": sum(1 for i in members if verdicts[i]["reader"] == "W" and i not in flip_to_right),
                         "undecided": sum(1 for i in members if verdicts[i]["reader"] == "CT"), "rate": pct(right, len(members))}
        return per_group, detail

    scenarios = {"v3_1": (old_eligible, weights_old, ()), "v3_2": (new_eligible, weights_new, ()),
                 "v3_2_variant_notes_supported": (new_eligible | set(VARIANT_WRONG), weights_new, VARIANT_WRONG)}
    result["right_rate"] = {}
    lines += ["", "## 3. Right-rate among the eligible readings the judge read (in-sample for v3.2)", "",
              "Undecided counts as not right. Weights for the weighted row are each group's eligible readings under that tool (v3.1: 589 / 57 / 101 as the judge used).", "",
              "| tool | group | judged eligible | right | wrong | undecided | right (Wilson 95%) |", "|---|---|---|---|---|---|---|"]
    for name, (eligible_ids, weights, flip) in scenarios.items():
        per_group, detail = rate(eligible_ids, flip)
        p, (lo, hi) = weighted_rate(per_group, weights)
        total_right, total_n = sum(k for k, _ in per_group.values()), sum(n for _, n in per_group.values())
        result["right_rate"][name] = {"groups": detail, "weights": weights, "weighted": f"{100 * p:.1f}% ({100 * lo:.1f}-{100 * hi:.1f})", "unweighted": pct(total_right, total_n)}
        for g in GROUPS:
            d = detail[g]
            lines.append(f"| {name.replace('_', '.', 1).replace('_', ' ')} | {LABEL[g]} | {d['judged']} | {d['right']} | {d['wrong']} | {d['undecided']} | {d['rate']} |")
        lines.append(f"| {name.replace('_', '.', 1).replace('_', ' ')} | **weighted** {weights} | {total_n} | {total_right} | | | **{100 * p:.1f}% ({100 * lo:.1f}-{100 * hi:.1f})**; unweighted {pct(total_right, total_n)} |")
    lines += ["", "`v3.2 variant notes supported`: the three variant-group readings (" + ", ".join(i[4:] for i in VARIANT_WRONG) + ") are eligible and, as the judge states (README sections 2 and 8: without the variant route the reading is right), counted right; **not re-read by me**."]

    # ---- 4. readings the new holds catch, and the judged readings still eligible that are not right ----
    caught = sorted(i for i in judged if i in old_eligible and i not in new_eligible)
    still_bad = sorted(i for i in judged if i in new_eligible and verdicts[i]["reader"] not in RIGHT)
    with (OUT / "caught_by_new_holds.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "group", "judge", "v3_2_holds"])
        for i in caught:
            writer.writerow([i, stratum[i], verdicts[i]["reader"], new[i]["holds"]])
    with (OUT / "still_eligible_not_right.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "group", "judge", "applies", "quote"])
        for i in still_bad:
            writer.writerow([i, stratum[i], verdicts[i]["reader"], new[i]["applies"], verdicts[i]["quote"]])
    result["caught"] = {"judged_right_caught": [i[4:] for i in caught if verdicts[i]["reader"] in RIGHT], "judged_wrong_caught": [i[4:] for i in caught if verdicts[i]["reader"] == "W"],
                        "judged_undecided_caught": [i[4:] for i in caught if verdicts[i]["reader"] == "CT"], "judged_wrong_or_undecided_still_eligible": [(i[4:], verdicts[i]["reader"]) for i in still_bad]}
    lines += ["", "## 4. Judged readings the v3.2 tool no longer lets through, and judged readings still eligible that are not right", "",
              f"Caught (eligible under v3.1, held under v3.2): {len(caught)}: " + ", ".join(f"{i[4:]} ({verdicts[i]['reader']}: {new[i]['holds']})" for i in caught),
              "", f"**Judged-right readings caught: {len(result['caught']['judged_right_caught'])}** ({', '.join(result['caught']['judged_right_caught']) or 'none'}).",
              "", f"Judged readings still eligible and not right ({len(still_bad)}): " + ", ".join(f"{i[4:]} ({verdicts[i]['reader']}; {verdicts[i]['quote'][:70]})" for i in still_bad)]

    # ---- 5. readings newly eligible (agreement now holds, or an output now valid) ----
    newly = sorted(i for i in new_eligible if i not in old_eligible)
    with (OUT / "newly_eligible.tsv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["id", "group", "applies", "v3_1_agree", "v3_1_valid_a", "v3_1_valid_b", "judge_which_pass_right_among_the_40"])
        for i in newly:
            writer.writerow([i, stratum[i], new[i]["applies"], old[i]["agree"], old[i]["valid_a"], old[i]["valid_b"], dis.get(i, "")])
    newly_by_group = Counter(stratum[i] for i in newly)
    in_forty = [i for i in newly if i in dis]
    result["newly_eligible"] = {"total": len(newly), "by_group": dict(newly_by_group), "of_the_judge_40_disagreements": {i[4:]: dis[i] for i in in_forty},
                                "not_judged": len(newly) - len(in_forty)}
    lines += ["", "## 5. Eligible under v3.2 only", "", f"{len(newly)} readings ({dict(newly_by_group)}): {len(in_forty)} are among the judge's 40 random disagreements and were judged `both` (the two passes were equivalent), "
              f"{len(newly) - len(in_forty)} were not read. They are NOT in the right-rate above (they were not drawn from the eligible set)."]
    lost = sorted(i for i in old_eligible if i not in new_eligible)
    by_code = Counter(c for i in lost for c in holds_of(new[i]) if c in NEW_CODES)
    lines += ["", f"Eligible under v3.1 and held under v3.2: {len(lost)} ({100 * len(lost) / len(old_eligible):.1f}% of {len(old_eligible)}); of them judged {len([i for i in lost if i in judged])}; by new hold: {dict(by_code)}."]
    result["lost"] = {"total": len(lost), "judged": len([i for i in lost if i in judged]), "by_new_hold": dict(by_code)}
    (OUT / "tables.md").write_text("---\ntype: analysis\n---\n# Tranche 01 under the v3.2 tool (generated by v3_2/evaluate_tranche01_v3_2.py; in-sample)\n\n" + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    (OUT / "numbers.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    main()
