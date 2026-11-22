import json, random, csv
from analyze import *
from sheet import ctx, name
loss=[r for r in rows if not r["now_standing"] and r["work"] not in OPENITI]
prior={l.split("\t")[0] for l in open(r"C:\Users\atooz\Programming\experiments\islamicapps\datasets\hadith-data\chain-audit\compiler-ruling\kunya_lost.tsv",encoding="utf8")}
def chron(r): return r["prev"]!="conflict" and r["next"]!="conflict" and (r["prev"] in("possible","attested") or r["next"] in ("possible","attested"))
def stratum(r):
    s=share(r)
    return ("A" if s>=.98 else "B" if s>=.95 else "C" if s>=.90 else "D")+("c" if chron(r) else "n")
size={"Dn":30}
rng=random.Random(20261122+7)
out=[]
by={}
for r in sorted(loss,key=lambda r:r["mention_id"]):
    if r["mention_id"] in prior: continue
    by.setdefault(stratum(r),[]).append(r)
for k in sorted(by):
    pick=rng.sample(by[k], size.get(k,15))
    for r in pick: out.append((k,r))
json.dump([(k,r) for k,r in out],open("sample.json","w",encoding="utf8"),ensure_ascii=False)
print({k:len(v) for k,v in by.items()}, len(out))
