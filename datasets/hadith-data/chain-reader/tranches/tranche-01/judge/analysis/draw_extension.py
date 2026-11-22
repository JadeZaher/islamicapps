"""Extend the judge's sample with a fixed seed (20261301) from the eligible set: all remaining al-Faqih, other Imami up to 40, Sunni up to 104."""
import json, random, csv
from common_t1 import *
TR = triage(); idm = json.loads((T / "private" / "id_map.json").read_text(encoding="utf-8"))["ids"]
base = [r["id"] for r in csv.DictReader((T / "judge" / "sample.tsv").open(encoding="utf-8"), delimiter="\t")]
elig = {"sunni_six_books": [], "imami_faqih": [], "imami_other_not_kafi": []}
for i, r in TR.items():
    if r["eligible"] == "True":
        elig[idm[i]["stratum"]].append(i)
rng = random.Random(20261301)
target = {"sunni_six_books": 104, "imami_faqih": 10**6, "imami_other_not_kafi": 40}
ext = {}
for g, ids in elig.items():
    have = [i for i in base if i in ids]
    pool = sorted(set(ids) - set(have))
    need = max(0, min(len(ids), target[g]) - len(have))
    ext[g] = sorted(rng.sample(pool, need))
json.dump({"seed": 20261301, "base": base, "extension": ext, "eligible_counts": {g: len(v) for g, v in elig.items()}}, open(HERE / "draw_extension.json", "w"), indent=1)
open(HERE / "ids_base.txt", "w").write("\n".join(base))
for g in ext: open(HERE / f"ids_ext_{g}.txt", "w").write("\n".join(ext[g])); print(g, len(ext[g]))
for g in elig: open(HERE / f"ids_base_{g}.txt", "w").write("\n".join(i for i in base if i in elig[g]))
