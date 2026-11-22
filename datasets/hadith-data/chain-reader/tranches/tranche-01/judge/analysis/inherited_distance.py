"""Item 4: distance (report numbers) between an inherited reading and the previous report it takes from; order of prev refs."""
import re, json
from common_t1 import *
TR=triage();K=private();PK=packets()
num=lambda s:(lambda m:int(m.group(1)) if m else None)(re.match(r"^\W*(\d+)",MARKS.sub("",s or "")))
rows=[]
for i,r in TR.items():
    if r["eligible"]!="True": continue
    rd=reading(i)["expanded_a"]
    refs={l.get("from") for rt in rd["routes"] for l in rt["links"] if l["kind"]=="inherited"}
    if not refs: continue
    n=num(K[i]["text"])
    prevs=PK[i]["context"]["previous_reports"]
    pn=[num(p.get("text_head") or p.get("chain_text")) for p in prevs]
    used=[(p["ref"],num(p.get("text_head") or p.get("chain_text")),p.get("supplies")) for p in prevs if p["ref"] in refs]
    anomaly = any(a is not None and b is not None and a>b for a,b in zip(pn,pn[1:]))
    rows.append((i[4:],n,pn,used,anomaly))
    print(i[4:],"n=",n,"prevs",pn,"used",used,"ORDER-ANOMALY" if anomaly else "")
