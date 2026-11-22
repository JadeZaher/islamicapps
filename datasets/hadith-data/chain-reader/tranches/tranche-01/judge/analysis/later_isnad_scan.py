"""Scan sampled reports for transmission verbs after the reader's matn start (a second isnad the dump cut off)."""
import re
from common_t1 import *
K=private()
V=re.compile(r"(حدثنا|أخبرنا|حدثني|أخبرني|أنبأنا|وحدثنا|ثنا|أنا )")
ids=[]
for f in ["ids_sunni_all.txt","ids_other_all.txt","ids_faqih_all.txt"]:
    ids+= [x for x in open(HERE/f).read().split() if x]
for i in ids:
    t=MARKS.sub("",K[i]["text"]);rd=reading(i)["expanded_a"];ms=rd.get("matn_start") or 0
    later=[m.start() for m in V.finditer(t) if m.start()>ms+30]
    if later:
        print(i[4:],group_of(K[i]["work"]),len(rd["routes"]),"routes; later verbs at",later[:4],"|",t[max(0,later[0]-40):later[0]+120].replace("\n"," "))
