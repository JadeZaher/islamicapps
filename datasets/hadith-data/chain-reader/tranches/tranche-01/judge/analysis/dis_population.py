"""Item 5, whole population of the 133 valid-but-different reports: automatic heuristics (not a substitute for the 40 read)."""
import json, re, collections
from common_t1 import *
from dis_t1 import routes_list, dis
TR=triage();K=private();idm=json.loads((T/"private"/"id_map.json").read_text(encoding="utf-8"))["ids"]
ASK=re.compile(r"^[\s\d\-–:\[\]/]*(?:و|ف)?\s*-?\s*(سأل|سئل|سأله|كتب|شكا|شكى)")
INH=re.compile(r"^[\s\d\-–:\[\]/]*(?:و|ف)?\s*-?\s*(قال|قضى)\s+(عليه السلام|الصادق|الرضا)|^[\s\d\-–:\[\]/]*(?:و)?\s*(عن|بهذا)")
def toks(x): return set(re.sub(r"[،,\[\]()]"," ",x).split())
def linkseq(r): return [l.strip() for l in r.split(" > ")]
def surf_equal(ra,rb):
    if len(ra)!=len(rb): return False
    return all(toks(a)<=toks(b) or toks(b)<=toks(a) for a,b in zip(ra,rb))
cnt=collections.Counter(); by=collections.defaultdict(list); grp=collections.Counter(); flags=collections.Counter(); ask=inh=0
for i in dis:
    oa=json.loads((T/"outputs"/"pass-a"/f"{i}.json").read_text(encoding="utf-8")); ob=json.loads((T/"outputs"/"pass-b"/f"{i}.json").read_text(encoding="utf-8"))
    A=[linkseq(x) for x in routes_list(oa)]; B=[linkseq(x) for x in routes_list(ob)]
    g=idm[i]["stratum"]; grp[g]+=1
    flags[(bool(oa.get("needs_ruling")),bool(ob.get("needs_ruling")))]+=1
    t=MARKS.sub("",K[i]["text"]).strip()
    if ASK.match(t): ask+=1; by["asker-opening"].append(i)
    if INH.match(t): inh+=1; by["inherited-opening"].append(i)
    # classification, first match
    if len(A)==len(B) and all(surf_equal(a,b) for a,b in zip(A,B)): c="surface_only"
    elif len(A)==len(B) and all(len(a)==len(b) for a,b in zip(A,B)) is False and all((a[:len(b)]==b or b[:len(a)]==a or surf_equal(a[:min(len(a),len(b))],b[:min(len(a),len(b))])) for a,b in zip(A,B)): c="one_route_set_is_prefix_of_the_other(shared tail or last link)"
    elif len(A)!=len(B): c="different_number_of_routes(variant/unnamed/co-transmitter)"
    else: c="other"
    cnt[c]+=1; by[c].append(i)
print("groups",dict(grp)); print("needs_ruling flags (A,B)",dict(flags)); print("asker-opening",ask,"inherited-style opening",inh)
for k,v in cnt.most_common(): print(v,k)
json.dump(by,open(HERE/"dis_population.json","w"),indent=1)
