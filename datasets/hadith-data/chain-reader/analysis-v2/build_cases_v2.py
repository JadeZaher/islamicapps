"""Write analysis-v2/cases.md: every v2 agreed report read in this pass, the 30 disagreements, the changes, the carried ids.   python -X utf8 analysis-v2/build_cases_v2.py"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_v2 import *
from verdicts_v2 import V2, DIS

reps = load_reports(ROOT / "pilot" / "reports.jsonl")
rows = {r["id"]: r for r in json.loads((HERE / "states_v2.json").read_text(encoding="utf-8"))}
carry = json.loads((HERE / "carry_v2.json").read_text(encoding="utf-8"))["carry"]
num = json.loads((HERE / "numbers_v2.json").read_text(encoding="utf-8"))
MARK = {"imam_in_text": "[M]", "inherited": "[I]", "unnamed": "[U]", "relation": "[R]", "back_reference": "[B]"}


def reading(r, tag="a", limit=2):
    routes, kinds = r.get(f"routes_{tag}") or [], r.get(f"kinds_{tag}") or []
    shown = [" > ".join(MARK.get(k, "") + MARKS.sub("", s) for s, k in zip(rt, ks) if k != "compiler_head") for rt, ks in list(zip(routes, kinds))[:limit]]
    return " || ".join(shown) + (f"  (+{len(routes) - limit} routes)" if len(routes) > limit else "")


def main() -> None:
    out = ["# Read cases (v2 pilot)", "",
           "Verdicts: **right**, **rep** (representation only), **wrong**, **label_wrong**, **cannot_tell**, **abstain** (both readers answered cannot_read_without_previous_report). Markers in readings: [M] imam_in_text, [I] inherited, [U] unnamed, [R] relation, [B] back_reference; the compiler head the tool adds is not shown.",
           "`fix`: i prompt wording, ii packet/context, iii tool or hold, iv not fixable by a reader.", ""]
    dup = set(num["compiler_duplicates"])
    out += [f"## A. Agreed reports read in this pass ({len(V2)})", ""]
    for rid in sorted(V2):
        v, t, fix, quote, why = V2[rid]
        r = rows[rid]
        if rid in dup:
            v, t = "wrong", t + " + compiler head duplicated (tool)"
        out += [f"### {rid}  {r['group']} / {reps[rid]['work']}  label={r['label']}  ->  **{v}** ({t})" + (f"  fix: {fix}" if fix else ""),
                f"- text: «{quote}»", f"- reading (both passes): {reading(r)}", f"- needs_ruling A/B: {bool(r.get('needs_ruling_a'))}/{bool(r.get('needs_ruling_b'))}; holds: {sorted(set(r.get('holds_a', []) + r.get('holds_b', [])))}",
                f"- why: {why}", ""]
    out += [f"## B. Agreed reports whose verdict is carried from v1 ({len(carry)})", "",
            "Their expanded non-derived routes equal the agreed reading I read in v1 and no inherited link is involved, so v1's verdict and quote stand (`../analysis/cases.md`, `../analysis/agreed_set.tsv`). The compiler head and the imam_in_text links were re-checked in this pass: two of them write the compiler twice (see the README). Ids:", "",
            ", ".join(sorted(carry)), ""]
    out += ["### Carried reports with a derived-link duplicate (tool)", ""]
    for rid in sorted(dup):
        out += [f"- {rid}: {reading(rows[rid], limit=1)}"]
    out += ["", f"## C. Disagreements: random 30 of {len(json.loads((HERE / 'dis_sample_v2.json').read_text(encoding='utf-8'))['all'])} (seed 20261123), all read", ""]
    for rid in sorted(DIS):
        cls, who, fix, quote, what = DIS[rid]
        r = rows[rid]
        out += [f"### {rid}  {r['group']} / {reps[rid]['work']}  ->  class **{cls}**, right: **{who}**  fix: {fix}", f"- text: «{quote}»", f"- difference: {what}", ""]
    out += ["## D. Changes of verdict between the pilots", "", "```", json.dumps(num["changes"], ensure_ascii=False, indent=1), "```", ""]
    (HERE / "cases.md").write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(len(out), "lines")


main()
