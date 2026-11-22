"""Merge the hand verdict files (v_*.txt) with the draw, write sample_verdicts.tsv and numbers_t1.json (Wilson 95% intervals, per group and weighted)."""
import json, csv
from common_t1 import *
TR=triage(); idm=json.loads((T/"private"/"id_map.json").read_text(encoding="utf-8"))["ids"]
D=json.loads((HERE/"draw_extension.json").read_text()); base=set(D["base"])
ELIG={"sunni_six_books":589,"imami_faqih":57,"imami_other_not_kafi":101}; TOTAL=sum(ELIG.values())
rows=[]
for f in ["v_sunni.txt","v_faqih.txt","v_other.txt","v_nochain.txt"]:
    for line in (HERE/f).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"): continue
        i,reader,stored,cls,quote=line.split("|",4); i="t01-"+i
        g=idm[i]["stratum"]
        rows.append(dict(id=i,group=g,work=idm[i]["work"],source="base" if i in base else "extension",applies=TR[i]["applies"],reader=reader,stored=("right" if stored=="R" else "defective"),stored_kind=stored[2:] if stored.startswith("D:") else "",cls=cls,quote=quote))
# the no-chain readings of the census (15) that are in the sample or not
ids=[r["id"] for r in rows]; assert len(ids)==len(set(ids)),"duplicate verdict"
with open(HERE/"sample_verdicts.tsv","w",encoding="utf-8",newline="") as h:
    w=csv.writer(h,delimiter="\t",lineterminator="\n"); w.writerow(["id","group","work","source","applies","reader","stored","stored_kind","class","quote"])
    for r in sorted(rows,key=lambda r:(r["group"],r["id"])): w.writerow([r[k] for k in ["id","group","work","source","applies","reader","stored","stored_kind","cls","quote"]])
def stats(rs):
    n=len(rs); right=sum(r["reader"] in("R","RO") for r in rs); wrong=sum(r["reader"]=="W" for r in rs); ct=sum(r["reader"]=="CT" for r in rs)
    sr=sum(r["stored"]=="right" for r in rs); fix=sum(r["cls"] in("FIX","JUNK") for r in rs); br=sum(r["cls"]=="BREAK" for r in rs)
    return dict(n=n,right=right,wrong=wrong,cannot_tell=ct,stored_right=sr,fixes=fix,fix_junk=sum(r["cls"]=="JUNK" for r in rs),breaks=br,both_right=sum(r["cls"]=="BOTHR" for r in rs),both_wrong=sum(r["cls"]=="BOTHW" for r in rs))
out={}
for g in ELIG:
    sel=[r for r in rows if r["group"]==g and r["source"] in("base","extension") and (r["id"] in {x for x in ids})]
    # no-chain rows not in the sample (read as a census, reported separately)
    sample=[r for r in sel if (r["applies"]=="chain") or True]
    out[g]=stats(sample)
# the census rows outside the sample: the 15 no-chain eligible; 'source' marks base/extension only for sampled ids, others are census
sampled={i for i in D["base"]}|{i for g in D["extension"].values() for i in g}
for g in ELIG:
    sel=[r for r in rows if r["group"]==g and r["id"] in sampled]
    out[g]=stats(sel)
    chain=[r for r in sel if r["applies"]=="chain"]; out[g+"_chain_only"]=stats(chain)
def w(k,ci=True):
    return sum(ELIG[g]/TOTAL*(out[g][k]/out[g]["n"]) for g in ELIG)
res={"eligible":ELIG,"groups":out,"weighted":{k:w(k) for k in ["right","wrong","cannot_tell","stored_right","fixes","breaks","both_wrong"]}}
# no-chain census
nc=[r for r in rows if r["applies"]=="no_chain"]
res["no_chain_census"]=dict(n=len(nc),right=sum(r["reader"] in("R","RO") for r in nc),cannot_tell=sum(r["reader"]=="CT" for r in nc),wrong=sum(r["reader"]=="W" for r in nc))
json.dump(res,open(HERE/"numbers_t1.json","w"),indent=1)
def line(label,s):
    n=s["n"]
    return f"| {label} | {n} | {pct(s['right'],n)} | {pct(s['stored_right'],n)} | {pct(s['fixes'],n)} | {s['breaks']}/{n} ({100*wilson(s['breaks'],n)[0]:.1f}-{100*wilson(s['breaks'],n)[1]:.1f}) | {100*(s['fixes']-s['breaks'])/n:+.1f} | w{s['wrong']} / ct{s['cannot_tell']} |"
print("| group | read | reader right | stored right | fixes | breaks | net/100 | wrong / cannot tell |"); 
for g in ELIG: print(line(g,out[g]))
for g in ELIG: print(line(g+" (chain readings only)",out[g+"_chain_only"]))
print(json.dumps(res["weighted"],indent=1)); print(res["no_chain_census"])
# pooled weighted interval by delta/normal approx on weighted proportions
import math
def wi(k):
    p=sum(ELIG[g]/TOTAL*(out[g][k]/out[g]["n"]) for g in ELIG)
    var=sum((ELIG[g]/TOTAL)**2*((out[g][k]/out[g]["n"])*(1-out[g][k]/out[g]["n"])/out[g]["n"]) for g in ELIG)
    return p,var
for k in ["right","stored_right","fixes","breaks","wrong"]:
    p,var=wi(k); print(k,f"{100*p:.1f}% (normal approx {100*(p-1.96*math.sqrt(var)):.1f} to {100*(p+1.96*math.sqrt(var)):.1f})")
