import sys
from common_t1 import *
PK=packets()
for i in sys.argv[1].split(","):
    i = i if i.startswith("t01-") else "t01-"+i
    print("==",i)
    for p in PK[i]["context"].get("previous_reports") or []:
        print(f" {p['ref']} {p.get('supplies')} W={p.get('has_written_chain')}:", MARKS.sub("", p.get("text_head") or p.get("chain_text") or "")[:int(sys.argv[2]) if len(sys.argv)>2 else 260])
