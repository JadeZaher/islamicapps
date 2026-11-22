"""Decisive numbers and the per-report table for the agreement analysis (see README.md in this directory).

    python analysis/classify.py && python analysis/pick_cases.py none && python analysis/numbers.py     (run from chain-reader/)

Reads classified.json / lenient.json / selection.json (written by the two scripts above) and the hand verdicts in verdicts.py and
disagreement_verdicts.py. Writes agreed_set.tsv and numbers.json. No model is run and nothing outside analysis/ is written.
"""
from __future__ import annotations
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))
from validate import load_reports, check_directory       # noqa: E402
from score import wilson, stored_route, reader_routes     # noqa: E402
from norm import MARKS, fold_loose, fold_exact            # noqa: E402
from verdicts import V, LENIENT_ONLY                      # noqa: E402
from disagreement_verdicts import D                       # noqa: E402

RIGHT = ("right", "rep", "label_wrong")      # the reader's reading is right (label_wrong: the stored chain was the wrong one)


def pct(k, n):
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.0f}% ({100 * lo:.0f}-{100 * hi:.0f})"


def main() -> None:
    reps = load_reports(ROOT / "pilot" / "reports.jsonl")
    data = json.loads((HERE / "classified.json").read_text(encoding="utf-8"))
    rows = {r["id"]: r for r in data["rows"]}
    sel = json.loads((HERE / "selection.json").read_text(encoding="utf-8"))
    lenient = json.loads((HERE / "lenient.json").read_text(encoding="utf-8"))
    lenient_extra = set(lenient["agree_ignoring_validity_but_not_both_valid"])
    agreed = [r for r in data["rows"] if r["state"] == "agree"]
    cpool_unread = set(sel["Cpool"]) - set(sel["C"])

    def verdict_of(rid: str):
        if rid in V:
            return V[rid][0], V[rid][1], V[rid][2], V[rid][3], V[rid][4]
        if rid in cpool_unread:
            return "unread", "", "", "", "agreed set, class (c) (labelled defective, reader differs), not in the random 40"
        text = MARKS.sub("", reps[rid]["text"]).replace("\n", " ")
        return "right", "plain_match", "", text[:70], "reader's routes equal the stored chains; re-read against the text"

    # ---- agreed set verdicts -------------------------------------------------------------------------------------
    for r in agreed:
        r["verdict"], r["tag"], r["fix"], r["quote"], r["why"] = verdict_of(r["id"])
        r["classes"] = "".join(sorted({i["cls"] for i in r["items"]}))

    # ---- split (a)-(d) ---------------------------------------------------------------------------------------------
    items = Counter(i["cls"] for r in agreed for i in r["items"])
    reports_by_class = {c: sorted({r["id"] for r in agreed for i in r["items"] if i["cls"] == c}) for c in "abcd"}
    combo = Counter(r["classes"] for r in agreed)

    # ---- scorer artifact: stored name written with an attached «و» is dropped by score.surface_in_text -----------------
    def in_text_loose(surface: str, text: str) -> bool:
        needle = fold_loose(surface)
        return bool(needle) and needle in fold_loose(text)

    def stored_route_substring(chain: dict, text: str):
        return tuple(fold_exact(s) for s in chain["surfaces"] if fold_exact(s) and in_text_loose(s, text))

    adj = Counter()
    a_run = check_directory(reps, ROOT / "outputs" / "run-a", repair=True)
    b_run = check_directory(reps, ROOT / "outputs" / "run-b", repair=True)
    errs = {rid: "A:" + ",".join(sorted({e.split(":")[0] for e in a_run[rid]["errors"]}) or ["ok"]) + " B:" + ",".join(sorted({e.split(":")[0] for e in b_run[rid]["errors"]}) or ["ok"]) for rid in reps}
    for rid, rep in reps.items():
        if a_run[rid]["status"] != "valid":
            continue
        routes = reader_routes(a_run[rid]["output"])
        for chain in rep["stored_chains"]:
            if chain["verdict"] != "correct":
                continue
            old = stored_route(chain, rep["text"])[0] in routes
            new = stored_route_substring(chain, rep["text"]) in routes
            adj["n"] += 1
            adj["old"] += old
            adj["new"] += new
    # ---- per group tables ---------------------------------------------------------------------------------------------
    groups = ["sunni six-book", "pure canon", "al-kafi", "al-faqih", "other imami", "al-rabi", "zayd"]
    traditions = {"sunni": ["sunni six-book", "pure canon"], "imami": ["al-kafi", "al-faqih", "other imami"], "ibadi": ["al-rabi"], "zaydi": ["zayd"]}
    all_ids = list(rows)

    def members(group):
        if group == "ALL":
            return all_ids
        if group in traditions:
            return [i for i in all_ids if rows[i]["group"] in traditions[group]]
        return [i for i in all_ids if rows[i]["group"] == group]

    out = {"split": {"items": dict(items), "reports": {c: len(v) for c, v in reports_by_class.items()}, "report_class_combinations": dict(combo)},
           "scorer_artifact": dict(adj), "groups": {}}
    table = []
    for g in ["ALL", "sunni", "imami", "sunni six-book", "pure canon", "al-kafi", "al-faqih", "other imami", "al-rabi", "zayd"]:
        ids = members(g)
        n = len(ids)
        agree_ids = [i for i in ids if rows[i]["state"] == "agree"]
        len_agree = [i for i in ids if rows[i]["state"] == "agree" or i in lenient_extra]
        state = Counter(rows[i]["state"] for i in ids)
        read = [rows_i for rows_i in agreed if rows_i["id"] in set(agree_ids) and rows_i["verdict"] != "unread"]
        right = sum(1 for x in read if x["verdict"] in RIGHT)
        right_strict = sum(1 for x in read if x["verdict"] == "right")
        cannot = sum(1 for x in read if x["verdict"] == "cannot_tell")
        wrong = sum(1 for x in read if x["verdict"] == "wrong")
        unread = sum(1 for i in agree_ids if verdict_of(i)[0] == "unread")
        # stratified estimate: unread class-(c) reports get the right-rate of the c sample that was read in the same group (all groups pooled if < 5)
        c_read = [x for x in agreed if x["id"] in sel["C"] and x["id"] in set(ids)]
        c_ok = sum(1 for x in c_read if x["verdict"] in RIGHT)
        if len(c_read) < 5:
            c_read = [x for x in agreed if x["id"] in sel["C"]]
            c_ok = sum(1 for x in c_read if x["verdict"] in RIGHT)
        lo_c, hi_c = wilson(c_ok, len(c_read)) if c_read else (0, 1)
        est = (right + unread * (c_ok / len(c_read) if c_read else 0)) / max(1, len(read) + unread)
        est_lo = (right + unread * lo_c) / max(1, len(read) + unread)
        est_hi = (right + unread * hi_c) / max(1, len(read) + unread)
        # strata by the stored side's report label
        def stratum(label):
            xs = [x for x in read if reps[x["id"]]["report_verdict"] == label]
            return len(xs), sum(1 for x in xs if x["verdict"] not in RIGHT)
        n_cor, w_cor = stratum("correct")
        n_def, w_def = stratum("defective")
        rec = {"reports": n, "valid_both": sum(1 for i in ids if rows[i]["status_a"] == "valid" and rows[i]["status_b"] == "valid"),
               "agree": len(agree_ids), "disagree": state["disagree"], "invalid": state["invalid"], "agree_lenient": len(len_agree),
               "read": len(read), "unread": unread, "right_or_rep": right, "right_exact": right_strict, "wrong": wrong, "cannot_tell": cannot,
               "right_rate_read": pct(right, len(read)), "right_rate_cannot_tell_as_right": pct(right + cannot, len(read)),
               "yield_strict": pct(len(agree_ids), n), "yield_lenient": pct(len(len_agree), n),
               "stratified_estimate": f"{100 * est:.0f}% ({100 * est_lo:.0f}-{100 * est_hi:.0f})",
               "estimate_all_agreed_wilson": pct(round(est * (len(read) + unread)), len(read) + unread),
               "stored_correct_agreed": [n_cor, w_cor], "stored_defective_agreed": [n_def, w_def]}
        out["groups"][g] = rec
        table.append((g, rec))

    # ---- the validator's reasons, with counts ------------------------------------------------------------------------------
    reasons = lenient["error_codes_any_error"]
    first = data["reasons"]
    out["validator_reasons_outputs_affected"] = reasons
    out["validator_first_reason"] = first

    # ---- gate: skip reports whose text opens with a back reference (inherited chain) -------------------------------------------
    gate = re.compile(r"^\W*\d*\W*(?:و\s*)?(?:بهذا\s+(?:ال)?[اإ]سناد|ب(?:ال)?[اإ]سناد\s+الاول|عنه|عن\b)")
    gated = [x for x in agreed if x["verdict"] != "unread" and gate.match(fold_loose(reps[x["id"]]["text"]))]
    kept = [x for x in agreed if x["verdict"] != "unread" and x not in gated]
    out["gate_back_reference_opening"] = {"gated": len(gated), "gated_wrong": sum(1 for x in gated if x["verdict"] == "wrong"),
                                          "kept_read": len(kept), "kept_right": pct(sum(1 for x in kept if x["verdict"] in RIGHT), len(kept)),
                                          "kept_wrong_tags": dict(Counter(x["tag"] for x in kept if x["verdict"] == "wrong"))}
    # ---- taxonomy of the agreed-but-wrong ----------------------------------------------------------------------------------------
    tax = defaultdict(list)
    for x in agreed:
        if x["verdict"] in ("wrong", "cannot_tell"):
            tax[x["tag"]].append(x["id"])
    out["taxonomy_agreed_wrong"] = {k: {"n": len(v), "ids": v, "fix": V[v[0]][2]} for k, v in tax.items()}
    dis = defaultdict(list)
    for rid, (cls, who, fix, quote, what) in D.items():
        dis[cls].append((rid, who))
    out["taxonomy_disagreements"] = {k: {"n": len(v), "ids": [i for i, _ in v], "who_right": dict(Counter(w for _, w in v))} for k, v in dis.items()}

    # ---- reader error on a realistic mix versus the stored error, with and without the back-reference gate ----------------------
    stored_rate = {"ALL": None, "sunni": 0.083, "imami": 0.040, "sunni six-book": 0.106, "al-kafi": 0.0, "al-faqih": 0.20, "al-rabi": 0.05,
                   "pure canon": None, "other imami": None, "zayd": None}
    compare = {}
    for g in ["sunni", "imami", "sunni six-book", "pure canon", "al-kafi", "al-faqih", "other imami", "al-rabi", "zayd", "ALL"]:
        ids = set(members(g))
        rec = {}
        for label, use_gate in (("no_gate", False), ("gate", True)):
            xs = [x for x in agreed if x["id"] in ids and x["verdict"] != "unread"]
            if use_gate:
                xs = [x for x in xs if not gate.match(fold_loose(reps[x["id"]]["text"]))]
            cor = [x for x in xs if reps[x["id"]]["report_verdict"] == "correct"]
            dfc = [x for x in xs if reps[x["id"]]["report_verdict"] == "defective"]
            wc = sum(1 for x in cor if x["verdict"] not in RIGHT)
            wd = sum(1 for x in dfc if x["verdict"] not in RIGHT)
            entry = {"n_read": len(xs), "right": pct(sum(1 for x in xs if x["verdict"] in RIGHT), len(xs)),
                     "stored_correct": pct(len(cor) - wc, len(cor)), "reader_wrong_where_stored_correct": pct(wc, len(cor)),
                     "stored_defective": [len(dfc), wd], "reader_wrong_where_stored_defective": pct(wd, len(dfc))}
            pr = stored_rate[g]
            if pr is not None and cor and dfc:
                e_cor, e_def = wc / len(cor), wd / len(dfc)
                entry["stored_defect_rate_given"] = pr
                entry["reader_error_at_that_mix"] = round(pr * e_def + (1 - pr) * e_cor, 4)
                lo_d, hi_d = wilson(wd, len(dfc)); lo_c2, hi_c2 = wilson(wc, len(cor))
                entry["reader_error_range"] = [round(pr * lo_d + (1 - pr) * lo_c2, 4), round(pr * hi_d + (1 - pr) * hi_c2, 4)]
            rec[label] = entry
        gated_n = sum(1 for x in agreed if x["id"] in ids and gate.match(fold_loose(reps[x["id"]]["text"])))
        rec["agreed_gated_out"] = gated_n
        compare[g] = rec
    out["compare"] = compare

    # ---- verdict tallies per class and tag ------------------------------------------------------------------------------------------
    per_class = {}
    for c in "abcd":
        ids = set(reports_by_class[c])
        vs = Counter(x["verdict"] for x in agreed if x["id"] in ids)
        per_class[c] = dict(vs)
    out["verdicts_by_class"] = per_class
    tags_b = Counter((x["verdict"], x["tag"]) for x in agreed if x["id"] in set(reports_by_class["b"]))
    out["class_b_tags"] = {f"{k[0]}/{k[1]}": v for k, v in tags_b.items()}
    tags_c = Counter((x["verdict"], x["tag"]) for x in agreed if x["id"] in set(sel["C"]))
    out["class_c_read_tags"] = {f"{k[0]}/{k[1]}": v for k, v in tags_c.items()}
    out["lenient_only_read"] = dict(Counter(v[0] for v in LENIENT_ONLY.values()))
    (HERE / "numbers.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- agreed_set.tsv: one row per report -------------------------------------------------------------------------------------------
    header = ["id", "tradition_group", "work", "report_label", "state", "reason_or_note", "classes_abcd", "verdict", "tag", "fix", "quote", "why"]
    lines = ["\t".join(header)]
    for rid in sorted(rows):
        r = rows[rid]
        rep = reps[rid]
        if r["state"] == "agree":
            v = next(x for x in agreed if x["id"] == rid)
            fields = [v["classes"], v["verdict"], v["tag"], v["fix"], v["quote"], v["why"]]
            note = ""
        elif r["state"] == "disagree":
            cls, who, fix, quote, what = D[rid]
            fields = ["", "disagree:" + who, cls, fix, quote, what]
            note = f"valid in both, routes differ"
        else:
            if rid in LENIENT_ONLY:
                vv, tag, quote, why = LENIENT_ONLY[rid]
                fields = ["", "invalid_but_agree_read:" + vv, tag, "", quote, why]
                note = errs[rid]
            elif rid in D:
                cls, who, fix, quote, what = D[rid]
                fields = ["", "invalid_and_differ:" + who, cls, fix, quote, what]
                note = errs[rid]
            else:
                kind = "invalid_but_agree_unread" if rid in lenient_extra else "invalid_unread"
                fields = ["", kind, "", "", "", ""]
                note = errs[rid]
        lines.append("\t".join([rid, r["group"], rep["work"], rep["report_verdict"], r["state"], note] + [f.replace("\t", " ").replace("\n", " ") for f in fields]))
    (HERE / "agreed_set.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    # ---- console summary ----------------------------------------------------------------------------------------------------------
    print(json.dumps(out["split"], ensure_ascii=False))
    print("scorer artifact", dict(adj))
    for g, rec in table:
        print(g, json.dumps(rec, ensure_ascii=False))
    print("gate", json.dumps(out["gate_back_reference_opening"], ensure_ascii=False))
    print("tax", json.dumps({k: v["n"] for k, v in out["taxonomy_agreed_wrong"].items()}, ensure_ascii=False))
    print("dis", json.dumps({k: v["n"] for k, v in out["taxonomy_disagreements"].items()}, ensure_ascii=False))
    print("lenient read", out["lenient_only_read"])


main()
