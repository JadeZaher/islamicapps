"""Item 4: eligible readings in the whole tranche with an asker pattern or an inherited link / inherited-speaker opening."""
import re, json
from common_t1 import *
TR=triage();K=private();PK=packets()
elig=[i for i,r in TR.items() if r["eligible"]=="True"]
ASK=re.compile(r"^[\s\d\-–:\[\]/]*(?:و|ف)?\s*-?\s*(سأل|سئل|سأله|سألت|كتب|شكا|شكى|و سأل|و كتب)")
INH=re.compile(r"^[\s\d\-–:\[\]/]*(?:و|ف)?\s*-?\s*(قال|قضى|روي|عن|و عن|وعنه|و عنه|بهذا|وبهذا)\s*(عليه السلام|هذا|عنه|الإسناد|الاسناد)?")
out=[]
for i in elig:
    t=MARKS.sub("",K[i]["text"]).strip()
    rd=reading(i)["expanded_a"]
    inh=any(l["kind"]=="inherited" for r in rd["routes"] for l in r["links"])
    asker=bool(ASK.match(t))
    out.append((i,asker,inh,t[:70]))
A=[o for o in out if o[1]];I=[o for o in out if o[2]]
print("eligible",len(elig),"asker-opening",len(A),"with inherited link",len(I),"both",len([o for o in out if o[1] and o[2]]))
sel=sorted(set([o[0] for o in A]+[o[0] for o in I]))
print(len(sel))
open("ids_askinh.txt","w").write("\n".join(sel))
for o in out:
    if o[0] in sel: print(o[0][4:],"A" if o[1] else "-","I" if o[2] else "-",TR[o[0]]["work"].split(":")[1][:12],o[3])
