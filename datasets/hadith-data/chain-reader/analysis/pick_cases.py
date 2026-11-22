"""Choose the reports to read (seeded) and dump them undiacritized for reading: python analysis/pick_cases.py > <dump>."""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from validate import load_reports, check_directory
from norm import MARKS

d = json.loads((Path(__file__).parent / "classified.json").read_text(encoding="utf-8"))
reps = load_reports(ROOT / "pilot" / "reports.jsonl")
rows = {r["id"]: r for r in d["rows"]}
agree = [r for r in d["rows"] if r["state"] == "agree"]
has = lambda r, c: any(i["cls"] == c for i in r["items"])
B = [r["id"] for r in agree if has(r, "b")]
D = [r["id"] for r in agree if has(r, "d")]
Cpool = sorted(r["id"] for r in agree if has(r, "c") and not has(r, "b") and not has(r, "d"))
rnd = random.Random(20261122)
C = sorted(rnd.sample(Cpool, 40))
from score import stored_route
Aonly, Aextra = [], []
for r in agree:
    if {i["cls"] for i in r["items"]} == {"a"}:
        st = set(stored_route(c, reps[r["id"]]["text"])[0] for c in reps[r["id"]]["stored_chains"]); st.discard(())
        (Aonly if st == set(tuple(x) for x in r["routes_a"]) else Aextra).append(r["id"])
Aspot = sorted(rnd.sample(sorted(Aonly), 15))
from norm import fold_exact, fold_loose
import re as _re
def lenient(folder, rid):
    raw = json.loads((ROOT / "outputs" / folder / f"{rid}.json").read_text(encoding="utf-8"))
    out = []
    for route in raw.get("routes", []):
        names = tuple(fold_exact(l["surface"]) for l in route["links"] if not (l["kind"] == "back_reference" and _re.search(r"(?:ال)?[اإ]سناد|السند|بسنده", fold_loose(l["surface"]))))
        if names: out.append(names)
    return out
LEN = {rid: (lenient("run-a", rid), lenient("run-b", rid)) for rid in reps}
DisS = sorted(rid for rid, (x, y) in LEN.items() if set(x) != set(y))
LENX = json.loads((Path(__file__).parent / "lenient.json").read_text(encoding="utf-8"))["agree_ignoring_validity_but_not_both_valid"]
LEN12 = sorted(rnd.sample(LENX, 12))
sel = {"Len12": LEN12, "B": B, "D": D, "C": C, "Cpool": Cpool, "Aextra": Aextra, "Aspot": Aspot, "Dis": DisS}
(Path(__file__).parent / "selection.json").write_text(json.dumps(sel, indent=1), encoding="utf-8")

def short(text, n):
    t = MARKS.sub("", text).replace("\n", " ⏎ ")
    return t[:n] + (" …" if len(t) > n else "")

def fmt(routes):
    return " || ".join(" > ".join(r) for r in routes)

def dump(ids, tag):
    for rid in ids:
        rep, row = reps[rid], rows[rid]
        print(f"=== {rid} [{tag}] {row['group']} {rep['work']} verdict={rep['report_verdict']}")
        print("TEXT:", short(rep["text"], 650))
        for c in rep["stored_chains"]:
            print(f"STORED[{c['verdict']}{'/'+c['kind'] if c['kind'] else ''}{' note='+c['note'] if c['note'] else ''}]:", " > ".join(c["surfaces"]))
        for l in rep["report_labels"]:
            print("REPORT-LABEL:", l["verdict"], l["kind"], l["note"])
        print("A:", fmt(LEN[rid][0]))
        if set(LEN[rid][0]) != set(LEN[rid][1]):
            print("B:", fmt(LEN[rid][1]))
        else:
            print("(B same)")
        print("classes:", [i["cls"] for i in row["items"]])

if __name__ == "__main__":
    which = sys.argv[1]
    dump(sel[which] if which in sel else [], which)
