"""Numbers, sample.tsv and cases.md for batch 001.   python -X utf8 analysis-batch-001/numbers_b1.py   (from chain-reader/)

Reads the hand verdict files v_faqih.txt, v_other.txt, v_sunni_a/b.txt, v_empty.txt, v_dis.txt (id6|reader|stored|kind|tags|quote) and draw.json.
Reader: r right, p representation only, w wrong, c cannot tell.  Stored: r right, d defective (kind), c cannot tell.
Class: fix (reader right/rep, stored defective), both right, break (reader wrong, stored right), both wrong, cannot tell (either side).
"""
from __future__ import annotations
import json, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_b1 import *

D = json.loads((HERE / "draw.json").read_text(encoding="utf-8"))
T, K = triage(), private()


def load(name):
    out = {}
    for line in (HERE / name).read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        p = line.split("|")
        out["b1-" + p[0]] = {"reader": p[1], "stored": p[2], "kind": p[3], "tags": [t for t in p[4].split(",") if t], "quote": p[5] if len(p) > 5 else ""}
    return out


V = {}
for f in ("v_faqih.txt", "v_other.txt", "v_sunni_a.txt", "v_sunni_b.txt"):
    V.update(load(f))
E = load("v_empty.txt")
GROUPS = ["sunni six-book", "al-faqih", "other imami"]
ELIG = {g: len(v) for g, v in zip(GROUPS, [sorted(i for i, r in T.items() if r["eligible"] == "True" and group_of(r["work"]) == g) for g in GROUPS])}
POP = {g: sum(1 for r in T.values() if group_of(r["work"]) == g) for g in GROUPS}


def klass(v):
    r, s = v["reader"], v["stored"]
    if r == "c" or s == "c":
        return "cannot tell"
    if r in "rp" and s == "d":
        return "fix"
    if r in "rp" and s == "r":
        return "both right"
    if r == "w" and s == "r":
        return "break"
    return "both wrong"


for i, v in V.items():
    v["class"] = klass(v)
    v["group"] = group_of(T[i]["work"])
    if not v["quote"]:
        v["quote"] = MARKS.sub("", K[i]["text"])[:70].replace("\n", " ")
for i, v in E.items():
    v["group"] = group_of(T[i]["work"])
    v["work"] = T[i]["work"].split(":")[1]
    if not v["quote"]:
        v["quote"] = MARKS.sub("", K[i]["text"])[:70].replace("\n", " ")

out = {"eligible": ELIG, "population": POP, "groups": {}}
rows_group = {}
for g in GROUPS:
    xs = [v for v in V.values() if v["group"] == g]
    n = len(xs)
    c = Counter(v["class"] for v in xs)
    right = sum(1 for v in xs if v["reader"] in "rp")
    wrong = sum(1 for v in xs if v["reader"] == "w")
    unc = sum(1 for v in xs if v["reader"] == "c")
    srt = sum(1 for v in xs if v["stored"] == "r")
    sdef = sum(1 for v in xs if v["stored"] == "d")
    substantive = sum(1 for v in xs if v["class"] == "fix" and v["kind"] != "noise")
    kinds = Counter(v["kind"] for v in xs if v["stored"] == "d")
    q = Counter(t for v in xs for t in v["tags"])
    # sensitivity: asker is a link (Q1): readers that dropped the asker (Q1d) are wrong, the one that kept him (Q1k) is right
    right_b = right - sum(1 for v in xs if "Q1d" in v["tags"] and v["reader"] in "rp") + sum(1 for v in xs if "Q1k" in v["tags"] and v["reader"] == "w")
    out["groups"][g] = {"n": n, "classes": dict(c), "reader_right": pct(right, n), "reader_wrong": wrong, "reader_cannot_tell": unc,
                        "stored_right": pct(srt, n), "fix": pct(c["fix"], n), "fix_substantive": pct(substantive, n), "break": pct(c["break"], n),
                        "net_per_100": round(100 * (c["fix"] - c["break"]) / n, 1), "stored_defect_kinds": dict(kinds), "tags": dict(q),
                        "reader_right_if_asker_is_a_link": pct(right_b, n), "counts": {"right": right, "n": n, "stored_right": srt, "fix": c["fix"], "break": c["break"], "wrong": wrong, "unc": unc}}
    rows_group[g] = out["groups"][g]["counts"]
    lo_f, hi_f = wilson(c["fix"], n)
    lo_b, hi_b = wilson(c["break"], n)
    out["groups"][g]["net_range_per_100"] = [round(100 * (lo_f - hi_b), 1), round(100 * (hi_f - lo_b), 1)]
# overall: weights by eligible share
tot = sum(ELIG.values())


def weighted(key):
    p = sum(ELIG[g] / tot * rows_group[g][key] / rows_group[g]["n"] for g in GROUPS)
    return p


# weighted Wilson: effective n via the weighted variance
def weighted_interval(key):
    p = weighted(key)
    var = sum((ELIG[g] / tot) ** 2 * (rows_group[g][key] / rows_group[g]["n"]) * (1 - rows_group[g][key] / rows_group[g]["n"]) / rows_group[g]["n"] for g in GROUPS)
    neff = p * (1 - p) / var if var > 0 else 1e9
    lo, hi = wilson(p * neff, neff)
    return p, lo, hi


out["overall_weighted"] = {}
for key, label in (("right", "reader_right"), ("stored_right", "stored_right"), ("fix", "fixes"), ("break", "breaks"), ("wrong", "reader_wrong"), ("unc", "reader_cannot_tell")):
    p, lo, hi = weighted_interval(key)
    out["overall_weighted"][label] = f"{100 * p:.1f}% ({100 * lo:.1f}-{100 * hi:.1f})"
net = weighted("fix") - weighted("break")
out["overall_weighted"]["net_per_100"] = round(100 * net, 1)
# empty readings
cat = defaultdict(Counter)
for i, v in E.items():
    c0 = next(t for t in v["tags"] if t.startswith("cat:"))
    cat[v["group"]][c0] += 1
byc = Counter(next(t for t in v["tags"] if t.startswith("cat:")) for v in E.values())
out["empty"] = {"total": len(E), "by_category": dict(byc), "by_group": {g: dict(c) for g, c in cat.items()},
                "by_work": dict(Counter(v["work"] for v in E.values())),
                "clear_no_chain_right": sum(1 for v in E.values() if v["reader"] == "r"), "undecided": sum(1 for v in E.values() if v["reader"] == "c")}
# holds
HOLD_ROUTES_END = {"160be9": "agreed w", "162ebe": "agreed w", "21210d": "agreed r", "21b3e7": "disagree B", "398b6f": "disagree A", "3c59ef": "agreed r", "41356f": "disagree B",
                   "844adb": "agreed w", "a22a43": "disagree B", "aa60d7": "disagree neither", "c47be8": "disagree neither", "cc4d10": "disagree B", "d2bb6c": "agreed w", "d55665": "disagree B", "ee5c9a": "agreed w"}
HOLD_RULING = {"162ebe": "agreed w", "223908": "agreed c", "549073": "agreed c", "5e3cb7": "disagree c", "63a547": "agreed w", "7425f4": "agreed c", "747357": "disagree Q1",
               "8a1368": "disagree A", "aa60d7": "disagree neither", "c47be8": "disagree neither", "d6d6e1": "agreed r", "e262e1": "agreed r", "eb1e57": "agreed r"}
out["holds"] = {"routes_end": dict(Counter(v.split()[0] + " " + v.split()[1] for v in HOLD_ROUTES_END.values())), "needs_ruling": dict(Counter(v.split()[0] + " " + v.split()[1] for v in HOLD_RULING.values()))}
dis = [l.split("|") for l in (HERE / "v_dis.txt").read_text(encoding="utf-8").splitlines() if l.strip()]
out["disagreements"] = {"n": len(dis), "by_class": dict(Counter(d[1] for d in dis)), "right": dict(Counter(d[2].split(" ")[0] + " " + (d[2].split(" ")[1] if len(d[2].split(" ")) > 1 else "") for d in dis))}
(HERE / "numbers_b1.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

# sample.tsv
head = ["id", "group", "work", "reader", "stored", "stored_kind", "class", "owner_question_tags", "quote"]
lines = ["\t".join(head)]
names = {"r": "right", "p": "representation only", "w": "wrong", "c": "cannot tell"}
snames = {"r": "right", "d": "defective", "c": "cannot tell"}
for g in GROUPS:
    for i in D["sample"][g]:
        v = V[i]
        lines.append("\t".join([i, g, T[i]["work"].split(":")[1], names[v["reader"]], snames[v["stored"]], v["kind"], v["class"], ",".join(v["tags"]), v["quote"]]))
for i in D["empty"]:
    v = E[i]
    lines.append("\t".join([i, v["group"], v["work"], "empty reading: " + names[v["reader"]], "defective (junk)", "junk", "empty-reading hold", ",".join(v["tags"]), v["quote"]]))
(HERE / "sample.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(json.dumps({k: out[k] for k in ("eligible", "overall_weighted", "empty", "holds", "disagreements")}, ensure_ascii=False, indent=1))
for g, e in out["groups"].items():
    print(g, e["n"], "reader", e["reader_right"], "| stored", e["stored_right"], "| fix", e["fix"], "subst", e["fix_substantive"], "| break", e["break"], "| net", e["net_per_100"], e["net_range_per_100"], "| wrong", e["reader_wrong"], "unc", e["reader_cannot_tell"], "| askerB", e["reader_right_if_asker_is_a_link"])
    print("   ", e["classes"], e["stored_defect_kinds"], e["tags"])
