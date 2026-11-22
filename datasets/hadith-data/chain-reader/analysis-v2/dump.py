"""Dump reports for reading: python analysis-v2/dump.py <list-name|ids...>   lists: read (agreed, to read), dis (non-agreed valid/invalid)."""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_v2 import *

MARK = {"imam_in_text": "[M]", "inherited": "[I]", "unnamed": "[U]", "relation": "[R]", "back_reference": "[B]", "compiler_head": "[C]"}


def fmt(routes, kinds, limit=3):
    out = []
    for r, k in list(zip(routes, kinds))[:limit]:
        out.append(" > ".join((MARK.get(kk, "") + s) for s, kk in zip(r, k) if kk != "compiler_head"))
    more = f"  (+{len(routes) - limit} routes)" if len(routes) > limit else ""
    return " || ".join(out) + more


def main():
    reps = load_reports(ROOT / "pilot" / "reports.jsonl")
    pk = load_packets()
    rows = {r["id"]: r for r in json.loads((HERE / "states_v2.json").read_text(encoding="utf-8"))}
    v1 = {r["id"]: r for r in json.loads((ROOT / "analysis" / "classified.json").read_text(encoding="utf-8"))["rows"]}
    v1_tsv = {l.split("\t")[0]: l.rstrip("\n").split("\t") for l in (ROOT / "analysis" / "agreed_set.tsv").read_text(encoding="utf-8").splitlines()[1:]}
    which = sys.argv[1]
    if which == "read":
        ids = json.loads((HERE / "carry_v2.json").read_text(encoding="utf-8"))["read"]
    elif which == "nonagree":
        ids = [r["id"] for r in rows.values() if not r["agree"] and not r["excluded"]]
    else:
        ids = sys.argv[1:]
    lo, hi = (int(sys.argv[2]), int(sys.argv[3])) if which in ("read", "nonagree") and len(sys.argv) > 3 else (0, len(ids))
    for rid in ids[lo:hi]:
        r, rep, ctx = rows[rid], reps[rid], pk[rid]["context"]
        t = MARKS.sub("", rep["text"]).replace("\n", " / ")
        print(f"== {rid} {r['group']} {rep['work']} label={r['label']} classes={r.get('classes','')} holdsA={r.get('holds_a')} holdsB={r.get('holds_b')} nrA={r.get('needs_ruling_a')} nrB={r.get('needs_ruling_b')} stA={r.get('status_a')}")
        print("T:", t[:520])
        if ctx.get("previous_reports"):
            print("PREV:", MARKS.sub("", ctx["previous_reports"][0].get("chain_text", ""))[:200])
        for c in rep["stored_chains"][:2]:
            print(f"S[{c['verdict']}{'/' + c['kind'] if c['kind'] else ''}]:", " > ".join(c["surfaces"])[:230])
        if r["state_a"] == "valid":
            print("A:", fmt(r["routes_a"], r["kinds_a"]))
        else:
            print("A: INVALID", r["err_a"][:100])
        if not r["agree"]:
            if r["state_b"] == "valid":
                print("B:", fmt(r["routes_b"], r["kinds_b"]))
            else:
                print("B: INVALID", r["err_b"][:100])
        for tag in "ab":
            n = r.get(f"notes_{tag}") or []
            if n and (r.get(f"needs_ruling_{tag}") or which == "nonagree"):
                print(f"N{tag}:", n[0][:200])
        o = v1[rid]
        if o["state"] == "agree" and rid in v1_tsv:
            print("V1:", v1_tsv[rid][7], "|", " || ".join(" > ".join(x) for x in o["routes_a"][:2])[:200])
        else:
            print("V1:", o["state"], v1_tsv.get(rid, ["", "", "", "", "", "", "", ""])[7])


main()
