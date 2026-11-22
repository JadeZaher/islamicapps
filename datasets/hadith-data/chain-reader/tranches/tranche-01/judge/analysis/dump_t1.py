"""python -X utf8 dump_t1.py <idfile|ids,comma> [lo hi] [width]   prints text, previous report, stored chains, reader routes."""
from __future__ import annotations
import sys
from common_t1 import *

arg = sys.argv[1]
ids = Path(arg).read_text().split() if Path(arg).exists() else arg.split(",")
lo, hi = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, len(ids))
width = int(sys.argv[4]) if len(sys.argv) > 4 else 420
TR, K, PK = triage(), private(), packets()
for i in ids[lo:hi]:
    i = i if i.startswith("t01-") else "t01-" + i
    kk, tr = K[i], TR[i]
    text = MARKS.sub("", kk["text"]).replace("\n", " / ")
    rd = reading(i)
    ms = rd["expanded_a"].get("matn_start") or 0
    cap = width
    if 0 < ms:
        cap = min(max(ms + 90, 140), width + 200)
    print(f"== {i[4:]} {group_of(tr['work'])} {tr['work'].split(':')[1][:14]} holds={tr['holds']} flag={tr['flag']} {tr['applies']}")
    print("T:", text[:cap] + (" …" if len(text) > cap else ""))
    inh = any(l["kind"] == "inherited" for r in rd["expanded_a"]["routes"] for l in r["links"])
    pr = PK[i]["context"].get("previous_reports") or []
    if pr and (inh or not rd["expanded_a"]["routes"] or True):
        for p in pr[:3]:
            print(f"PREV[{p['ref']}{'/'+p['supplies'] if p.get('supplies') else ''}]:", MARKS.sub("", (p.get("chain_text") or ""))[:150])
    for c in kk["stored_chains"][:3]:
        print(f"S[{c['structure_status'][:4]}]:", " > ".join(c["surfaces"])[:230])
    if len(kk["stored_chains"]) > 3:
        print(f"S: (+{len(kk['stored_chains']) - 3} chains)")
    print("R:", fmt_routes(rd["expanded_a"]["routes"]) or "(no routes: no chain)")
