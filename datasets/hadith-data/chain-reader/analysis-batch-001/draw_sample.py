"""Seeded stratified draw of the eligible readings to read, plus the empty-reading, disagreement and hold sets.   python -X utf8 analysis-batch-001/draw_sample.py

Eligible strata: sunni six-book 205, al-faqih 86, other imami 79. Draw: 85 / 80 / all 79 = 244 (>= 80 per group, all of a group that has fewer, 240+).
"""
from __future__ import annotations
import json, random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_b1 import *

T = triage()
elig = {g: sorted(i for i, r in T.items() if r["eligible"] == "True" and group_of(r["work"]) == g) for g in ("sunni six-book", "al-faqih", "other imami")}
SIZE = {"sunni six-book": 85, "al-faqih": 80, "other imami": 79}
rnd = random.Random(20261124)
sample = {g: sorted(rnd.sample(ids, min(SIZE[g], len(ids)))) for g, ids in elig.items()}
empty = sorted(i for i, r in T.items() if "reading_empty_stored_has_links" in r["holds"].split(","))
dis_all = sorted(i for i, r in T.items() if r["agree"] == "False")
dis = sorted(rnd.sample(dis_all, min(30, len(dis_all))))
routes_end = sorted(i for i, r in T.items() if "routes_end_at_different_links" in r["holds"].split(","))
ruling = sorted(i for i, r in T.items() if "needs_ruling" in r["holds"].split(","))
out = {"eligible_sizes": {g: len(v) for g, v in elig.items()}, "sample": sample, "empty": empty, "disagree_all": dis_all, "disagree_sample": dis, "routes_end": routes_end, "needs_ruling": ruling}
(HERE / "draw.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
print({k: (len(v) if not isinstance(v, dict) else {a: (len(b) if hasattr(b, "__len__") else b) for a, b in v.items()}) for k, v in out.items()})
