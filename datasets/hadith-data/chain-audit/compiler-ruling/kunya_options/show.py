import json, sys
from analyze import share, carriers
from sheet import ctx, name
c=ctx()
S=json.load(open("sample.json",encoding="utf8"))
lo,hi=int(sys.argv[1]),int(sys.argv[2])
def nm(nid):
    if not nid: return "-"
    n=c["narr"].get(nid,{}); d=c["prof"].get(nid,{}).get("death_year_hijri") or "?"
    return f"{(n.get('name_latin') or n.get('name_ar') or n.get('name') or '')[:42]} d{d}"
for i,(k,r) in enumerate(S):
    if not lo<=i<hi: continue
    chain=c["by_chain"][r["chain"]]; p=r["position"]
    win=[]
    for m in chain:
        q=int(m["position"])
        if p-2<=q<=p+2:
            win.append(("[[%s]]" if q==p else "%s")%m["surface_ar"][:28])
    print(f"{i} {k} {r['work'][-14:]} s={share(r):.2f}/{carriers(r)} :: {' < '.join(win)} => {nm(r['standing'])} || prev {r['prev'][:4]} {nm(r['prev_id'])} | next {r['next'][:4]} {nm(r['next_id'])}")
