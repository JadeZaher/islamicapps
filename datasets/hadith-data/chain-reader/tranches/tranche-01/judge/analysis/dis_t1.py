"""Item 5: random 40 of the both-valid-but-different reports (seed 20261401); dump text, stored, reading A and B."""
import random, sys
from common_t1 import *
TR=triage();K=private()
def routes_list(o):
    if not o or not isinstance(o.get("groups"),list): return []
    out=[];tail=o.get("shared_tail") or []
    for g in o["groups"]:
        lv=[[MARKS.sub("",x.get("surface","")) for x in L] for L in g.get("levels",[])+tail]
        for c in itertools.product(*lv): out.append(" > ".join(c))
    return out
dis=sorted(i for i,r in TR.items() if r["valid_a"]=="True" and r["valid_b"]=="True" and r["agree"]=="False")
if __name__=="__main__":
    print(len(dis))
    pick=sorted(random.Random(20261401).sample(dis,40))
    open(HERE/"ids_dis40.txt","w").write("\n".join(pick))
    lo,hi=int(sys.argv[1]),int(sys.argv[2]); width=int(sys.argv[3]) if len(sys.argv)>3 else 330
    for i in pick[lo:hi]:
        oa=json.loads((T/"outputs"/"pass-a"/f"{i}.json").read_text(encoding="utf-8")); ob=json.loads((T/"outputs"/"pass-b"/f"{i}.json").read_text(encoding="utf-8")); r={}
        t=MARKS.sub("",K[i]["text"]).replace("\n"," / ")
        ms=0
        cap=width
        print(f"== {i[4:]} {group_of(K[i]['work'])} {TR[i]['work'].split(':')[1][:12]} flag={TR[i]['flag']} holds={TR[i]['holds']}")
        print("T:",t[:cap]+(" …" if len(t)>cap else ""))
        for p in (PK:=packets())[i]["context"].get("previous_reports",[])[:2]:
            pass
        for c in K[i]["stored_chains"][:2]: print("S:"," > ".join(c["surfaces"])[:160])
        la,lb=routes_list(oa),routes_list(ob)
        print("A:",prod(oa)[:300]); print("B:",prod(ob)[:300])
        print("A-B:"," || ".join(x for x in la if x not in lb)[:400]); print("B-A:"," || ".join(x for x in lb if x not in la)[:400])
