"""Dump reports for reading.   python -X utf8 analysis-batch-001/dump_b1.py <set> [lo hi]    set: sunni|faqih|other|empty|dis|routes_end|needs_ruling"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_b1 import *

D = json.loads((HERE / "draw.json").read_text(encoding="utf-8"))
T, P, K = triage(), packets(), private()
which = sys.argv[1]
ids = {"sunni": D["sample"]["sunni six-book"], "faqih": D["sample"]["al-faqih"], "other": D["sample"]["other imami"], "empty": D["empty"],
       "dis": D["disagree_sample"], "routes_end": D["routes_end"], "needs_ruling": D["needs_ruling"]}[which]
lo, hi = (int(sys.argv[2]), int(sys.argv[3])) if len(sys.argv) > 3 else (0, len(ids))
width = int(sys.argv[4]) if len(sys.argv) > 4 else 420
for i in ids[lo:hi]:
    pk, kk, tr = P[i], K[i], T[i]
    text = MARKS.sub("", kk["text"]).replace("\n", " / ")
    cap = width
    try:
        rd = reading(i)
        ms = rd["expanded_a"].get("matn_start") or 0
        if 0 < ms:
            cap = min(max(ms + 60, 140), width + 160)
    except Exception:
        rd = None
    print(f"== {i[3:]} {group_of(tr['work'])[:6]} {tr['work'].split(':')[1][:12]} holds={tr['holds']} flag={tr['flag']}")
    print("T:", text[:cap] + (" …" if len(text) > cap else ""))
    pr = pk["context"].get("previous_reports") or []
    if pr and (rd and any(l["kind"] == "inherited" for r in rd["expanded_a"]["routes"] for l in r["links"]) or text.lstrip("0123456789 -–").startswith(("و بهذا", "وبهذا", "بهذا", "عنه", "وعنه", "و عنه", "وعن", "وبالاسناد", "وبالإسناد"))):
        print("PREV:", MARKS.sub("", pr[0].get("chain_text", ""))[:170])
    for c in kk["stored_chains"][:3]:
        print(f"S[{c['structure_status'][:4]}]:", " > ".join(c["surfaces"])[:220])
    if len(kk["stored_chains"]) > 3:
        print(f"S: (+{len(kk['stored_chains']) - 3} chains)")
    if rd:
        print("R:", fmt_routes(rd["expanded_a"]["routes"]) or "(no routes)")
    if which in ("dis", "routes_end", "needs_ruling"):
        import itertools
        def prod(o):
            if not o or not isinstance(o, dict) or not isinstance(o.get("groups"), list):
                return "(none)"
            out = []
            tail = o.get("shared_tail") or []
            for g in o["groups"]:
                lv = [[MARK.get(x.get("kind"), "") + MARKS.sub("", x.get("surface", "")) for x in L] for L in g.get("levels", []) + tail]
                for c in itertools.product(*lv):
                    out.append(" > ".join(c))
            return " || ".join(out[:4]) + (f" (+{len(out) - 4})" if len(out) > 4 else "") + (" [needs_ruling]" if o.get("needs_ruling") else "")
        try:
            r0 = json.loads((B / "triage" / "readings" / f"{i}.json").read_text(encoding="utf-8"))
        except Exception:
            r0 = {}
        if which == "dis" or not rd:
            oa = r0.get("output_a") or json.loads((B / "outputs" / "pass-a" / f"{i}.json").read_text(encoding="utf-8"))
            ob = r0.get("output_b") or json.loads((B / "outputs" / "pass-b" / f"{i}.json").read_text(encoding="utf-8"))
            print("A:", prod(oa)); print("B:", prod(ob))
        else:
            ob = r0.get("output_b"); oa = r0.get("output_a")
            print("flags A/B:", bool(oa and oa.get("needs_ruling")), bool(ob and ob.get("needs_ruling")))
            for o, nm in ((oa, "A"), (ob, "B")):
                if o and o.get("needs_ruling") and o.get("notes"):
                    print("N" + nm + ":", MARKS.sub("", o["notes"][0])[:230])
        print("valid", tr["valid_a"], tr["valid_b"], tr["problems"][:120])
