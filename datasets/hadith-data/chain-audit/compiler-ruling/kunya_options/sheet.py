import csv, json, sys, random
from analyze import rows, opt, share, carriers, OPENITI, S
csv.field_size_limit(2**31 - 1)
P = r"C:\Users\atooz\AppData\Local\Temp\claude\8b9ecadf913d98e6\95b7dde3-527e-49ce-8f56-83c964db48b2\scratchpad\proj-eval\canonical"

def load(t):
    with open(P + "\\" + t + ".csv", encoding="utf8", newline="") as h:
        return list(csv.DictReader(h))

_cache = {}
def ctx():
    if _cache:
        return _cache
    narr = {r["id"]: r for r in load("narrators")}
    prof = {r["narrator_id"]: r for r in load("narrator_lexicon_profiles")}
    by_chain = {}
    for m in load("chain_mentions"):
        by_chain.setdefault(m["chain_id"], []).append(m)
    for v in by_chain.values():
        v.sort(key=lambda m: int(m["position"]))
    hadith = {r["id"]: r for r in load("hadiths")}
    _cache.update(narr=narr, prof=prof, by_chain=by_chain, hadith=hadith)
    return _cache

def name(c, nid):
    if not nid:
        return "-"
    n = c["narr"].get(nid, {})
    d = c["prof"].get(nid, {}).get("death_year_hijri") or "?"
    return f"{(n.get('name_latin') or '')[:40]}|{(n.get('name_ar') or '')[:50]}|d{d}"

def show(r):
    c = ctx()
    chain = c["by_chain"][r["chain"]]
    parts = []
    for m in chain:
        mark = ">>" if m["id"] == r["mention_id"] else "  "
        parts.append(f"{mark}{m['position']}:{m['surface_ar']}")
    text = " ".join(c["hadith"][r["hadith_id"]]["text_ar"].split())[:90]
    print(f"### {r['mention_id']} [{r['tradition']} {r['work']}] «{r['surface']}» -> {name(c, r['standing'])} ({r['method']})")
    print(f"    share {share(r):.2f} carriers {carriers(r)} stats {[(a, m, t, d) for a, m, t, d, _ in r['stats']]} prev {r['prev']}:{name(c, r['prev_id'])} next {r['next']}:{name(c, r['next_id'])}")
    print("    chain: " + " | ".join(parts))
