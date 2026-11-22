"""Tables for README: base-100 only, extended sample, weighted overall with Wilson on the effective n; sensitivity (cannot tell counted wrong, noise-only stored defects, relation-prefix)."""
import csv, json, math
from common_t1 import *
ELIG={"sunni_six_books":589,"imami_faqih":57,"imami_other_not_kafi":101}; TOT=sum(ELIG.values())
rows=list(csv.DictReader(open(HERE/"sample_verdicts.tsv",encoding="utf-8"),delimiter="\t"))
D=json.load(open(HERE/"draw_extension.json")); sampled=set(D["base"])|{i for g in D["extension"].values() for i in g}
def S(rs):
    n=len(rs); r=lambda x:x["reader"] in("R","RO")
    return dict(n=n,right=sum(map(r,rs)),wrong=sum(x["reader"]=="W" for x in rs),ct=sum(x["reader"]=="CT" for x in rs),
        stored=sum(x["stored"]=="right" for x in rs),fix=sum(x["class"] in("FIX","JUNK") for x in rs),
        fix_noise=sum(x["class"] in("FIX","JUNK") and x["stored_kind"]=="noise" for x in rs),
        brk=sum(x["class"]=="BREAK" for x in rs),bothw=sum(x["class"]=="BOTHW" for x in rs))
def weighted(sub,key,mult=1):
    p=0;var=0
    for g,N in ELIG.items():
        s=S([x for x in sub if x["group"]==g]); n=s["n"]; k=s[key]
        p+=N/TOT*k/n; var+=(N/TOT)**2*(k/n)*(1-k/n)/n
    return p,var
def wil_eff(p,var):
    if var==0: return (None,None)
    neff=p*(1-p)/var; return wilson(p*neff,neff)
def show(name,sub):
    print("###",name)
    for g in ELIG:
        s=S([x for x in sub if x["group"]==g]); n=s["n"]
        print(f"{g}: n={n} right {pct(s['right'],n)} | wrong {s['wrong']} ct {s['ct']} | stored right {pct(s['stored'],n)} | fixes {pct(s['fix'],n)} (noise-only {s['fix_noise']}) | breaks {s['brk']} | both wrong {s['bothw']}")
    for k in ("right","stored","fix","wrong"):
        p,v=weighted(sub,k); lo,hi=wil_eff(p,v)
        print(f"  weighted {k}: {100*p:.1f}%"+(f" (Wilson on n_eff {100*lo:.1f}-{100*hi:.1f})" if lo is not None else ""))
    # right counting cannot tell as wrong already; noise-excluded fix
    p=sum(ELIG[g]/TOT*(S([x for x in sub if x['group']==g])['fix']-S([x for x in sub if x['group']==g])['fix_noise'])/S([x for x in sub if x['group']==g])['n'] for g in ELIG)
    print(f"  weighted fixes beyond noise-only defects: {100*p:.1f}%")
base=[x for x in rows if x["source"]=="base"]
show("base 100 (pre-drawn, seed 20261201)",[x for x in rows if x["id"] in set(D["base"])])
show("extended sample (read)",[x for x in rows if x["id"] in sampled])
show("chain readings only, extended",[x for x in rows if x["id"] in sampled and x["applies"]=="chain"])
print("wrong:",[(x["id"],x["group"],x["source"]) for x in rows if x["reader"]=="W"])
print("ct:",[(x["id"],x["group"],x["source"],x["applies"]) for x in rows if x["reader"]=="CT"])
