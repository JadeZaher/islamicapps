"""Agreement split of the chain-reader pilot (see README.md in this directory).

    python analysis/classify.py            (run from chain-reader/; writes analysis/classified.json)

Reuses validate.py and score.py unchanged. For every report: do both passes validate (after offset repair) and agree exactly
(same set of routes of folded surfaces), and how does that shared reading compare with each labelled stored chain.
"""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from validate import check_directory, load_reports          # noqa: E402
from score import reader_routes, items_of, judge, stored_route, wilson   # noqa: E402


def tradition_group(report: dict) -> str:
    work = f"{report['tradition']}:{report['work']}"
    if report["tradition"] == "sunni":
        return "sunni six-book" if report["work"] in ("bukhari", "muslim", "abudawud", "tirmidhi", "nasai", "ibnmajah") else "pure canon"
    if work == "imami:al-kafi":
        return "al-kafi"
    if work == "imami:man-la-yahduruhu-al-faqih":
        return "al-faqih"
    if report["tradition"] == "imami":
        return "other imami"
    return {"ibadi": "al-rabi", "zaydi": "zayd"}[report["tradition"]]


def main() -> None:
    reports = load_reports(ROOT / "pilot" / "reports.jsonl")
    a = check_directory(reports, ROOT / "outputs" / "run-a", repair=True)
    b = check_directory(reports, ROOT / "outputs" / "run-b", repair=True)
    rows, reasons = [], Counter()
    for rid, rep in reports.items():
        row = {"id": rid, "tradition": rep["tradition"], "work": rep["work"], "group": tradition_group(rep),
               "report_verdict": rep["report_verdict"], "status_a": a[rid]["status"], "status_b": b[rid]["status"]}
        for tag, res in (("a", a), ("b", b)):
            if res[rid]["status"] != "valid":
                reasons[(tag, res[rid]["errors"][0].split(":")[0])] += 1
        row["routes_a"] = reader_routes(a[rid]["output"]) if a[rid]["status"] == "valid" else None
        row["routes_b"] = reader_routes(b[rid]["output"]) if b[rid]["status"] == "valid" else None
        if row["routes_a"] is None or row["routes_b"] is None:
            row["state"] = "invalid"
        else:
            row["state"] = "agree" if set(row["routes_a"]) == set(row["routes_b"]) else "disagree"
        row["items"] = []
        if row["state"] == "agree":
            routes = row["routes_a"]
            for item in items_of(rep):
                j = judge(item, routes)
                cls = {("correct", True): "a", ("correct", False): "b", ("defective", False): "c", ("defective", True): "d"}[(item["verdict"], j["exact"])]
                row["items"].append({"scope": item["scope"], "verdict": item["verdict"], "cls": cls, "loose": j["loose"], "kind": item["kind"],
                                     "state": item["state"], "note": item["note"], "stored": [list(r) for r in item["routes"]], "chain_id": item["chain_id"]})
        rows.append(row)
    (Path(__file__).parent / "classified.json").write_text(json.dumps({"rows": rows, "reasons": {f"{k[0]}:{k[1]}": v for k, v in reasons.items()}}, ensure_ascii=False, indent=1), encoding="utf-8")
    st = Counter(r["state"] for r in rows)
    print(st, dict(reasons))
    print("items", Counter(i["cls"] for r in rows for i in r["items"]))
    # distinct reports per class
    for c in "abcd":
        print(c, len({r["id"] for r in rows for i in r["items"] if i["cls"] == c}))

main()


def lenient_and_errors() -> None:
    """Validator reasons over ALL errors (not only the first) and agreement when offsets/matn are ignored (surfaces found in the text)."""
    import re
    from norm import fold_exact, fold_loose
    reports = load_reports(ROOT / "pilot" / "reports.jsonl")
    codes = {"a": Counter(), "b": Counter()}
    lenient = {}
    for tag, folder in (("a", "run-a"), ("b", "run-b")):
        res = check_directory(reports, ROOT / "outputs" / folder, repair=True)
        for rid, r in res.items():
            if r["status"] != "valid":
                for code in {e.split(":")[0] for e in r["errors"]}:
                    codes[tag][code] += 1
            raw = json.loads((ROOT / "outputs" / folder / f"{rid}.json").read_text(encoding="utf-8"))
            routes = []
            for route in raw.get("routes", []):
                names = tuple(fold_exact(l["surface"]) for l in route["links"]
                              if not (l["kind"] == "back_reference" and re.search(r"(?:ال)?[اإ]سناد|السند|بسنده", fold_loose(l["surface"]))))
                if names:
                    routes.append(names)
            lenient[(tag, rid)] = (routes, r["status"])
    summary = {"error_codes_any_error": {t: dict(c) for t, c in codes.items()}}
    both_valid = [rid for rid in reports if lenient[("a", rid)][1] == "valid" and lenient[("b", rid)][1] == "valid"]
    agree_len = [rid for rid in reports if set(lenient[("a", rid)][0]) == set(lenient[("b", rid)][0])]
    summary["agree_exact_valid_both"] = sum(1 for rid in both_valid if set(lenient[("a", rid)][0]) == set(lenient[("b", rid)][0]))
    summary["agree_ignoring_validity"] = len(agree_len)
    summary["agree_ignoring_validity_but_not_both_valid"] = sorted(set(agree_len) - set(both_valid))
    (Path(__file__).parent / "lenient.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in summary.items()}, ensure_ascii=False))


lenient_and_errors()
