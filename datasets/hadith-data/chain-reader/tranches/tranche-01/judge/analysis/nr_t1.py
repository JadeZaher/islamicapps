import sys
from common_t1 import *
TR=triage();K=private()
ids=sorted(i for i,r in TR.items() if "needs_ruling" in r["holds"] and r["agree"]=="True")
open(HERE/"ids_needs_ruling.txt","w").write("\n".join(ids))
if __name__=="__main__":
    lo,hi=int(sys.argv[1]),int(sys.argv[2])
    for i in ids[lo:hi]:
        r=reading(i); oa=r["output_a"]; ob=r["output_b"]
        t=MARKS.sub("",K[i]["text"]).replace("\n"," / ")
        print(f"== {i[4:]} {group_of(K[i]['work'])} {TR[i]['work'].split(':')[1][:14]} holds={TR[i]['holds']}")
        print("T:",t[:int(sys.argv[3]) if len(sys.argv)>3 else 360])
        print("R:",fmt_routes(r["expanded_a"]["routes"],2)[:330])
        for nm,o in (("NA",oa),("NB",ob)):
            if o and o.get("notes"): print(nm+":",MARKS.sub("",o["notes"][0])[:240])
