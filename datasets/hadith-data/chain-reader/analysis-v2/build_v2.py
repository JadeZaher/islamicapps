"""Expand both v2 passes, compute validity, agreement, classes (a)-(d), holds. Writes states_v2.json.

    python analysis-v2/build_v2.py          (from chain-reader/)
Class of an agreed report's labelled item: compared with the stored chain with imam_in_text dropped OR kept (either equal counts as a match),
derived links (compiler head, inherited) dropped, as score_v2.py does.
"""
from __future__ import annotations
import json, sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_v2 import *


def main():
    reps = load_reports(ROOT / "pilot" / "reports.jsonl")
    packets = load_packets()
    rows = []
    for rid, rep in reps.items():
        ctx = packets[rid]["context"]
        row = {"id": rid, "group": tradition_group(rep), "tradition": rep["tradition"], "work": rep["work"], "label": rep["report_verdict"],
               "excluded": rid in EXCLUDED, "has_prev": bool(ctx.get("previous_reports") or ctx.get("parent_report")), "needs_prev": bool(ctx.get("needs_previous_report"))}
        stored = [s for c in rep["stored_chains"] for s in c["surfaces"]]
        for tag, folder in (("a", "run-a"), ("b", "run-b")):
            out, err = read_output(folder, rid)
            row[f"err_{tag}"] = err
            if out is None:
                row[f"state_{tag}"] = "invalid"
                continue
            reading, errors = expand(out, rep["text"], ctx)
            row[f"needs_ruling_{tag}"] = bool(out.get("needs_ruling"))
            row[f"status_{tag}"] = out.get("status")
            row[f"notes_{tag}"] = out.get("notes", [])
            if reading is None:
                row[f"state_{tag}"] = "invalid"
                row[f"err_{tag}"] = errors[0][:120]
                continue
            row[f"state_{tag}"] = "valid"
            row[f"routes_{tag}"] = [[l["surface"] for l in r["links"]] for r in reading["routes"]]
            row[f"kinds_{tag}"] = [[l["kind"] for l in r["links"]] for r in reading["routes"]]
            row[f"core_{tag}"] = [list(x) for x in v1_routes(reading, "keep")]
            row[f"core_noimam_{tag}"] = [list(x) for x in v1_routes(reading, "drop")]
            row[f"canon_{tag}"] = sorted("|".join(x) for x in canonical(reading))
            row[f"holds_{tag}"] = [h["code"] for h in compute_holds(reading, out, rep["text"], ctx, stored)]
        both = row["state_a"] == "valid" and row["state_b"] == "valid"
        row["both_valid"] = both
        row["agree"] = both and row["canon_a"] == row["canon_b"]
        if row["agree"]:
            routes = [tuple(x) for x in row["core_noimam_a"]]
            routes_k = [tuple(x) for x in row["core_a"]]
            cls = []
            for item in items_of(rep):
                exact = judge(item, routes)["exact"] or judge(item, routes_k)["exact"]
                cls.append({("correct", True): "a", ("correct", False): "b", ("defective", False): "c", ("defective", True): "d"}[(item["verdict"], exact)])
            row["classes"] = "".join(sorted(set(cls)))
            row["items"] = cls
        rows.append(row)
    (HERE / "states_v2.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    sc = [r for r in rows if not r["excluded"]]
    print("all", Counter((r["both_valid"], r["agree"]) for r in rows))
    print("279", Counter((r["both_valid"], r["agree"]) for r in sc))
    print("valid a", sum(r["state_a"] == "valid" for r in sc), "valid b", sum(r["state_b"] == "valid" for r in sc))
    print("classes", Counter(r.get("classes") for r in sc if r["agree"]))
    print("items", Counter(c for r in sc if r["agree"] for c in r["items"]))
    print(Counter(r["err_a"][:40] for r in sc if r["state_a"] == "invalid"), Counter(r["err_b"][:40] for r in sc if r["state_b"] == "invalid"))


main()
