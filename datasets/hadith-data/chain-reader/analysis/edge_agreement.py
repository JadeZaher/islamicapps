"""How many pairs agree under weaker equality rules than 'same set of routes' (surfaces only, offsets ignored).

    python analysis/edge_agreement.py            (run from chain-reader/)

Rules: route-set (what score.py uses); edge-set (set of consecutive teacher->student pairs plus first and last link of every route);
edge-set after name folding (a leading «و» stripped, a name equals another if one is a contiguous word run of the other).
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from validate import load_reports                       # noqa: E402
from norm import fold_exact, fold_loose                 # noqa: E402
from disagreement_verdicts import D                     # noqa: E402

ISNAD = re.compile(r"(?:ال)?[اإ]سناد|السند|بسنده")


def routes_of(folder: str, rid: str) -> list[tuple[str, ...]]:
    raw = json.loads((ROOT / "outputs" / folder / f"{rid}.json").read_text(encoding="utf-8"))
    out = []
    for route in raw.get("routes", []):
        names = tuple(fold_exact(l["surface"]) for l in route["links"] if not (l["kind"] == "back_reference" and ISNAD.search(fold_loose(l["surface"]))))
        if names:
            out.append(names)
    return out


def canon(name: str) -> str:
    words = fold_loose(name).split()
    if words and words[0].startswith("و") and len(words[0]) > 2:
        words[0] = words[0][1:]
    return " ".join(words)


def contiguous(small: list[str], large: list[str]) -> bool:
    return bool(small) and any(large[i:i + len(small)] == small for i in range(len(large) - len(small) + 1))


def same_name(a: str, b: str) -> bool:
    x, y = canon(a).split(), canon(b).split()
    return x == y or contiguous(x, y) or contiguous(y, x)


def edges(routes, fold=False):
    key = canon if fold else (lambda s: s)
    pairs = {(key(a), key(b)) for r in routes for a, b in zip(r, r[1:])}
    ends = {("^", key(r[0])) for r in routes} | {(key(r[-1]), "$") for r in routes}
    return pairs | ends


def _match(x, o) -> bool:
    if x[0] == "^":
        return o[0] == "^" and same_name(x[1], o[1])
    if x[1] == "$":
        return o[1] == "$" and same_name(x[0], o[0])
    return o[0] != "^" and o[1] != "$" and same_name(x[0], o[0]) and same_name(x[1], o[1])


def edge_equal_folded(ra, rb) -> bool:
    ea, eb = edges(ra, True), edges(rb, True)
    return all(any(_match(x, o) for o in eb) for x in ea) and all(any(_match(x, o) for o in ea) for x in eb)


def main() -> None:
    reps = load_reports(ROOT / "pilot" / "reports.jsonl")
    counts = {"route_set": [], "edge_set": [], "edge_set_folded": []}
    for rid in reps:
        ra, rb = routes_of("run-a", rid), routes_of("run-b", rid)
        if set(ra) == set(rb):
            counts["route_set"].append(rid)
        if edges(ra) == edges(rb):
            counts["edge_set"].append(rid)
        if edge_equal_folded(ra, rb):
            counts["edge_set_folded"].append(rid)
    out = {k: len(v) for k, v in counts.items()}
    gained = sorted(set(counts["edge_set_folded"]) - set(counts["route_set"]))
    out["gained_by_folded_edge_set"] = gained
    out["gained_verdicts"] = {rid: D[rid][1] if rid in D else "unread" for rid in gained}
    out["disagreements_still_apart_under_folded_edge_set"] = sorted(set(D) - set(counts["edge_set_folded"]))
    (HERE / "edge_agreement.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


main()
