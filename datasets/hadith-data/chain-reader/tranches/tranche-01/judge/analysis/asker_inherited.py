"""Item 4: the eligible readings with an asker opening or an inherited link: type, whether the asker is written, where the inherited names come from, distance, verdict."""
import re, json, csv
from common_t1 import *
TR=triage();K=private();PK=packets()
V={}
for f in ["v_faqih.txt","v_other.txt","v_sunni.txt","v_inherited5.txt","v_nochain.txt"]:
    for line in (HERE/f).read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.startswith("#"):
            i,reader,stored,cls,quote=line.split("|",4); V["t01-"+i]=(reader,stored,cls,quote)
num=lambda s:(lambda m:int(m.group(1)) if m else None)(re.match(r"^\W*(\d+)",MARKS.sub("",s or "")))
ids=open(HERE/"ids_askinh.txt").read().split()
out=[]
for i in ids:
    t=MARKS.sub("",K[i]["text"]).strip(); rd=reading(i)["expanded_a"]
    kinds=[l["kind"] for r in rd["routes"] for l in r["links"]]
    inh=[(l.get("from"),l["surface"]) for r in rd["routes"] for l in r["links"] if l["kind"]=="inherited"]
    if re.match(r"^[\s\d\-–]*(?:و|ف)?\s*-?\s*(سأل|كتب|شكا)\s+(?!إليه|ه\b)",t): typ="asker named"
    elif re.match(r"^[\s\d\-–]*(?:و)?\s*-?\s*(سأله|كتب إليه|سئل\b)",t) and not inh: typ="asker/asked only"
    elif re.match(r"^[\s\d\-–]*(?:و)?\s*-?\s*(سأله|كتب إليه)",t): typ="asker pronoun (+inherited Imam)"
    elif re.match(r"^[\s\d\-–]*(?:و)?\s*-?\s*سئل\s*:",t): typ="passive, asker unnamed (+inherited Imam)"
    elif re.match(r"^[\s\d\-–]*(?:و)?\s*-?\s*قال عليه السلام",t): typ="«وقال عليه السلام» (inherited speaker)"
    elif re.match(r"^[\s\d\-–]*(?:و|ف)?\s*-?\s*(بهذا|وبهذا|و بهذا)",t): typ="«وبهذا الإسناد» (inherited chain)"
    elif re.match(r"^[\s\d\-–]*(?:و)?\s*-?\s*(عنه|و عنه|عن)",t): typ="«وعنه» (inherited chain)"
    else: typ="other"
    prevs=PK[i]["context"].get("previous_reports") or []; used=[p for p in prevs if p["ref"] in {x[0] for x in inh}]
    n=num(K[i]["text"]); pn=num((used[0].get("text_head") or used[0].get("chain_text"))) if used else None
    gap=(n-pn) if (n is not None and pn is not None) else None
    v=V.get(i,("?","?","?",""))
    out.append((i[4:],TR[i]["work"].split(":")[1][:16],typ,used[0]["ref"] if used else "",gap if gap is not None else "",len(inh),v[0],v[3][:150]))
with open(HERE/"asker_inherited.tsv","w",encoding="utf-8",newline="") as h:
    w=csv.writer(h,delimiter="\t",lineterminator="\n"); w.writerow(["id","work","type","inherited_from","report_gap","inherited_links","reader_verdict","quote_and_note"]); w.writerows(out)
import collections
c=collections.Counter((o[2],o[6]) for o in out)
for k,v in sorted(c.items()): print(v,k)
print(len(out))
