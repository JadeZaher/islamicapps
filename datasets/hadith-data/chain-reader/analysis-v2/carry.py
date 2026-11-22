"""Which v2 agreed reports can inherit their v1 verdict (same non-derived routes as v1's agreed reading, no inherited link) and which must be read.

    python analysis-v2/carry.py          writes carry_v2.json {"carry": {id: v1 verdict}, "read": [ids]}
"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_v2 import *


def main():
    rows = json.loads((HERE / "states_v2.json").read_text(encoding="utf-8"))
    v1 = json.loads((ROOT / "analysis" / "classified.json").read_text(encoding="utf-8"))["rows"]
    v1_rows = {r["id"]: r for r in v1}
    v1_tsv = {l.split("\t")[0]: l.rstrip("\n").split("\t") for l in (ROOT / "analysis" / "agreed_set.tsv").read_text(encoding="utf-8").splitlines()[1:]}
    carry, read = {}, []
    for r in rows:
        if not r["agree"] or r["excluded"]:
            continue
        rid = r["id"]
        old = v1_rows[rid]
        has_inherited = any("inherited" in k for k in r["kinds_a"])
        same = old["state"] == "agree" and sorted(map(tuple, old["routes_a"])) == sorted(map(tuple, r["core_a"]))
        verdict = v1_tsv[rid][7] if rid in v1_tsv else ""
        if same and not has_inherited and verdict in ("right", "rep", "label_wrong", "wrong", "cannot_tell"):
            carry[rid] = verdict
        else:
            read.append(rid)
    (HERE / "carry_v2.json").write_text(json.dumps({"carry": carry, "read": read}, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(len(carry), Counter(carry.values()), len(read))


main()
