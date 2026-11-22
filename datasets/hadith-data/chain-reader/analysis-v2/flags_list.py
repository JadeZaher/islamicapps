"""List every report where either pass set needs_ruling, with the first note: python -X utf8 analysis-v2/flags_list.py"""
from __future__ import annotations
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_v2 import *

rows = json.loads((HERE / "states_v2.json").read_text(encoding="utf-8"))
carry = json.loads((HERE / "carry_v2.json").read_text(encoding="utf-8"))["carry"]
reps = load_reports(ROOT / "pilot" / "reports.jsonl")
n = 0
for r in rows:
    if r["excluded"]:
        continue
    a, b = r.get("needs_ruling_a"), r.get("needs_ruling_b")
    if not (a or b):
        continue
    n += 1
    tag = "agree" if r["agree"] else "differ/invalid"
    notes = (r.get("notes_a") if a else r.get("notes_b")) or []
    pick = next((x for x in notes if "RULING" in x.upper() or "ruling" in x or "settle" in x), notes[0] if notes else "")
    print(r["id"], r["group"], tag, "carry" if r["id"] in carry else "", "A" if a else "-", "B" if b else "-", "|", MARKS.sub("", reps[r["id"]]["text"])[:90].replace("\n", " "), "|", pick[:260])
print(n)
