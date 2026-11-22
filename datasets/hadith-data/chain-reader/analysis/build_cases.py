"""Write analysis/cases.md from the hand verdicts (verdicts.py, disagreement_verdicts.py) and the classified agreed set.

    python analysis/build_cases.py            (run from chain-reader/, after classify.py and pick_cases.py)
"""
from __future__ import annotations
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from validate import load_reports                         # noqa: E402
from norm import MARKS                                    # noqa: E402
from verdicts import V, LENIENT_ONLY                      # noqa: E402
from disagreement_verdicts import D                       # noqa: E402

reps = load_reports(ROOT / "pilot" / "reports.jsonl")
data = json.loads((HERE / "classified.json").read_text(encoding="utf-8"))
rows = {r["id"]: r for r in data["rows"]}
sel = json.loads((HERE / "selection.json").read_text(encoding="utf-8"))


def reader(rid: str, limit: int = 2) -> str:
    routes = rows[rid]["routes_a"] or []
    shown = " || ".join(" > ".join(r) for r in routes[:limit])
    return shown + (f"  (+{len(routes) - limit} more routes)" if len(routes) > limit else "")


def stored(rid: str) -> str:
    out = []
    for c in reps[rid]["stored_chains"][:2]:
        tag = c["verdict"] + (f"/{c['kind']}" if c["kind"] else "")
        out.append(f"[{tag}] " + " > ".join(c["surfaces"]))
    return " || ".join(out)


def block(rid: str, entry) -> list[str]:
    verdict, tag, fix, quote, why = entry
    lines = [f"### {rid}  {rows[rid]['group']} / {reps[rid]['work']}  ->  **{verdict}** ({tag})" + (f"  fix: {fix}" if fix else ""),
             f"- text: «{quote}»", f"- stored: {stored(rid)}", f"- reader (both passes): {reader(rid)}", f"- why: {why}", ""]
    return lines


def main() -> None:
    agreed = {r["id"]: r for r in data["rows"] if r["state"] == "agree"}
    cls = lambda rid, c: any(i["cls"] == c for i in agreed[rid]["items"])
    out = ["# Read cases", "",
           "Every case below was read against the Arabic text (diacritics stripped for reading; quotes are from the text). Verdicts: **right**, **rep** (representation only: same links, differs in a gloss, honorific, verb, relation word, orthography, back-reference link or a noise word in the stored surface), **wrong**, **label_wrong** (reader right, human label wrong), **cannot_tell**.",
           "`fix`: i prompt rule, ii context from sources, iii deterministic post-processing, iv not fixable by a reader.", ""]
    out += ["## Class (d): labelled defective, reader reproduces the stored chain (5 reports, all read)", ""]
    for rid in sorted(agreed):
        if cls(rid, "d"):
            out += block(rid, V[rid])
    out += ["## Class (b): labelled correct, reader differs (57 reports, all read)", ""]
    for rid in sorted(agreed):
        if cls(rid, "b"):
            out += block(rid, V[rid])
    out += ["## Class (c): labelled defective, reader differs: random 40 of 69 read (seed 20261122) plus cr-0266 (in (b) above)", ""]
    for rid in sel["C"]:
        out += block(rid, V[rid])
    out += ["## Class (c), not read (29 reports): in the agreed set, labelled defective, reader differs; no verdict is given for them", "",
            ", ".join(sorted(set(sel["Cpool"]) - set(sel["C"]))), ""]
    out += ["## Class (a) reports read, with a call to make", ""]
    for rid in ("cr-0015", "cr-0027", "cr-0138", "cr-0237", "cr-0258"):
        out += block(rid, V[rid])
    plain = sorted(rid for rid in agreed if rid not in V and rid not in set(sel["Cpool"]))
    out += [f"## Class (a) reports read and judged right with no comment ({len(plain)})", "",
            "Reader's routes equal the stored routes, and I re-read each against the text (the 17 whose reader routes contain more routes than the labelled chain, because the other stored chains of the report were unlabelled, included). Ids:", "",
            ", ".join(plain), ""]
    out += ["## Disagreements between the two passes: all 25 read (offsets ignored; 17 valid in both, 8 with an invalid output)", ""]
    for rid in sorted(D):
        cls_, who, fix, quote, what = D[rid]
        out += [f"### {rid}  {rows[rid]['group']} / {reps[rid]['work']}  ->  class **{cls_}**, right: **{who}**" + (f"  fix: {fix}" if fix else ""),
                f"- text: «{quote}»", f"- difference: {what}", ""]
    out += ["## Agreed only when offsets are ignored (36 reports; 12 read at random)", ""]
    for rid, (verdict, tag, quote, why) in sorted(LENIENT_ONLY.items()):
        out += [f"### {rid}  {rows[rid]['group']} / {reps[rid]['work']}  ->  **{verdict}** ({tag})", f"- text: «{quote}»", f"- why: {why}", ""]
    (HERE / "cases.md").write_text("\n".join(out), encoding="utf-8", newline="\n")
    print(len(out), "lines;", len(plain), "plain")


main()
