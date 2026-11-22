"""Item 8: candidate holds, evaluated on every sampled verdict (right / wrong) and counted over all 747 eligible readings of the tranche. Nothing is applied: these are measurements."""
import csv, json, re
from common_t1 import *
TR=triage(); K=private(); idm=json.loads((T/"private"/"id_map.json").read_text(encoding="utf-8"))["ids"]
V={r["id"]:r for r in csv.DictReader(open(HERE/"sample_verdicts.tsv",encoding="utf-8"),delimiter="\t")}
elig=[i for i,r in TR.items() if r["eligible"]=="True" and r["applies"]=="chain"]
def routes(i):
    rd=reading(i)["expanded_a"]; out=[]
    for r in rd["routes"]:
        if r.get("variant"): continue
        out.append([MARKS.sub("",l["surface"]) for l in r["links"] if l["kind"]!="compiler_head"])
    return out, rd.get("matn_start") or 0
def h_routes_end_differ(i):
    rs,_=routes(i); ends={r[-1] for r in rs if r}; return len(rs)>1 and len(ends)>1
def h_short_route(i,frac=0.5,minmax=4):
    rs,_=routes(i)
    if len(rs)<2: return False
    L=[len(r) for r in rs]; return max(L)>=minmax and min(L)<=max(L)*frac
def h_single_link_route(i):
    rs,_=routes(i); return len(rs)>1 and any(len(r)==1 for r in rs)
def h_semicolon_in_chain(i):
    rs,ms=routes(i); t=MARKS.sub("",K[i]["text"]); head=t[: ms if ms else 400]
    return "؛" in head and len(rs)>=2
def h_kunya_pair(i):
    # two routes identical but for the first link, and the text writes «أبو X، Y» (no «و») for them
    rs,_=routes(i); t=MARKS.sub("",K[i]["text"])
    for a in range(len(rs)):
        for b in range(a+1,len(rs)):
            if rs[a][1:]==rs[b][1:] and rs[a][0]!=rs[b][0]:
                p=t.find(rs[a][0].split("،")[0])
                if p>=0 and re.match(rf"\s*،\s*{re.escape(rs[b][0][:6])}", t[p+len(rs[a][0]):p+len(rs[a][0])+12]): return True
    return False
H={"routes_end_at_different_links (before the v3.1 exemption)":h_routes_end_differ,"route at most half as long as the longest":h_short_route,"a one-link route next to longer ones":h_single_link_route,"«؛» inside the isnad of a multi-route reading":h_semicolon_in_chain,"kunya, name read as two routes":h_kunya_pair}
res={}
for name,f in H.items():
    hit=[i for i in elig if f(i)]
    inS=[i for i in hit if i in V and V[i]["applies"]=="chain"]
    wr=[i[4:] for i in inS if V[i]["reader"]=="W"]; rt=[i[4:] for i in inS if V[i]["reader"] in("R","RO")]; ct=[i[4:] for i in inS if V[i]["reader"]=="CT"]
    res[name]=dict(hits_total=len(hit),hits_in_sample=len(inS),wrong_caught=wr,right_caught=len(rt),right_caught_ids=rt,ct=ct)
    print(f"{name}: {len(hit)} of {len(elig)} eligible chain readings; in the read sample {len(inS)}: wrong caught {wr}, right caught {len(rt)}, cannot tell {ct}")
allw=[i[4:] for i,v in V.items() if v["reader"]=="W"]
print("all wrong in sample:",allw)
json.dump(res,open(HERE/"proposed_holds.json","w"),indent=1)
