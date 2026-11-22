"""Decisive numbers for the v2 pilot, v1 beside v2, holds before/after, what changed. Writes numbers_v2.json and agreed_set.tsv.

    python -X utf8 analysis-v2/build_v2.py && python -X utf8 analysis-v2/carry.py && python -X utf8 analysis-v2/numbers_v2.py     (from chain-reader/)
Scored set: the 279 reports of the scorer (the five reports quoted in the v2 prompt are left out: cr-0029, 0090, 0138, 0237, 0258).
"""
from __future__ import annotations
import json, re, sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common_v2 import *
from verdicts_v2 import V2, DIS
from holds import opens_with_back_reference

GATE = re.compile(r"^\W*\d*\W*(?:و\s*)?(?:بهذا\s+(?:ال)?[اإ]سناد|ب(?:ال)?[اإ]سناد\s+الاول|عنه|عن\b)")     # the v1 analysis gate
GROUPS = ["sunni six-book", "pure canon", "al-kafi", "al-faqih", "other imami", "al-rabi", "zayd"]
TRAD = {"sunni": ["sunni six-book", "pure canon"], "imami": ["al-kafi", "al-faqih", "other imami"]}
STORED = {"sunni": 0.083, "sunni six-book": 0.106, "imami": 0.040, "al-kafi": 0.0, "al-faqih": 0.20, "al-rabi": 0.05}
# needs_ruling flags I judged: 'settled' = the owner rulings or the prompt's own rule settle the case; 'real' = the text or the rules leave it open
FLAG_JUDGE = {"cr-0008": "real", "cr-0026": "settled", "cr-0047": "real", "cr-0060": "settled", "cr-0069": "settled", "cr-0091": "real", "cr-0095": "settled",
              "cr-0111": "real", "cr-0122": "settled", "cr-0131": "settled", "cr-0132": "settled", "cr-0134": "settled", "cr-0144": "real", "cr-0158": "real",
              "cr-0187": "real", "cr-0190": "real", "cr-0192": "settled", "cr-0202": "settled", "cr-0280": "real"}


def main() -> None:
    reps = load_reports(ROOT / "pilot" / "reports.jsonl")
    rows = {r["id"]: r for r in json.loads((HERE / "states_v2.json").read_text(encoding="utf-8"))}
    carry = json.loads((HERE / "carry_v2.json").read_text(encoding="utf-8"))["carry"]
    v1 = {r["id"]: r for r in json.loads((ROOT / "analysis" / "classified.json").read_text(encoding="utf-8"))["rows"]}
    v1_tsv = {l.split("\t")[0]: l.rstrip("\n").split("\t") for l in (ROOT / "analysis" / "agreed_set.tsv").read_text(encoding="utf-8").splitlines()[1:]}
    scored = [i for i in rows if not rows[i]["excluded"]]

    def members(g):
        if g == "ALL":
            return scored
        if g in TRAD:
            return [i for i in scored if rows[i]["group"] in TRAD[g]]
        return [i for i in scored if rows[i]["group"] == g]

    # ---- verdicts of agreed reports ----------------------------------------------------------------------------------------
    verdict, tag = {}, {}
    for i in scored:
        r = rows[i]
        if not r["agree"]:
            continue
        if i in V2:
            verdict[i], tag[i] = V2[i][0], V2[i][1]
        elif i in carry:
            verdict[i], tag[i] = carry[i], "carried_from_v1"
        else:
            raise SystemExit(f"no verdict for {i}")
    # ---- compiler head written twice: the tool adds him although the text already names him (expand.py compares the short name with the surface) ----
    alias = {"الصدوق": ["بابويه"], "الكليني": ["الكليني"], "المفيد": ["المفيد"], "الطوسي": ["الطوسي"], "النعماني": ["النعماني"], "ابن قولويه": ["قولويه"],
             "الحسين بن سعيد الأهوازي": ["الحسين بن سعيد"], "مسلم": [], "البخاري": [], "مالك بن أنس": []}
    dup = []
    for i in scored:
        r = rows[i]
        if not r["agree"]:
            continue
        for rt, ks in zip(r["routes_a"], r["kinds_a"]):
            if ks and ks[0] == "compiler_head" and len(rt) > 1 and any(a in fold_loose(rt[1]) for a in alias.get(rt[0], [])):
                dup.append(i)
                break
    for i in dup:
        verdict_before = verdict[i]
        verdict[i], tag[i] = "wrong", "compiler_head_duplicated (tool); reader " + verdict_before
    # ---- holds ---------------------------------------------------------------------------------------------------------------------
    def tool_holds(i):
        r = rows[i]
        return sorted({h for t in "ab" for h in r.get(f"holds_{t}", []) if h != "needs_ruling"})

    def held(i, rule):
        r = rows[i]
        if tool_holds(i):
            return True
        a, b = r.get("needs_ruling_a"), r.get("needs_ruling_b")
        return {"tool_only": False, "either": bool(a or b), "both": bool(a and b), "a_only": bool(a)}[rule]

    def stat(ids):
        xs = [i for i in ids if verdict[i] != "abstain"]
        right = sum(1 for i in xs if verdict[i] in RIGHT)
        return len(ids), len(xs), right

    out = {"verdict_counts": dict(Counter(verdict.values())), "groups": {}, "rules": {}}
    agreed_all = [i for i in scored if rows[i]["agree"]]
    # ---- split (a)-(d) -----------------------------------------------------------------------------------------------------------------
    out["split"] = {"items": dict(Counter(c for i in agreed_all for c in rows[i]["items"])), "report_classes": dict(Counter(rows[i]["classes"] for i in agreed_all)),
                    "both_valid": sum(rows[i]["both_valid"] for i in scored), "agree": len(agreed_all), "scored": len(scored),
                    "valid_a": sum(rows[i]["state_a"] == "valid" for i in scored), "valid_b": sum(rows[i]["state_b"] == "valid" for i in scored)}
    # ---- per group ------------------------------------------------------------------------------------------------------------------------
    for g in ["ALL", "sunni", "imami"] + GROUPS:
        ids = members(g)
        ag = [i for i in ids if rows[i]["agree"]]
        entry = {"reports": len(ids), "both_valid": sum(rows[i]["both_valid"] for i in ids), "agreed": pct(len(ag), len(ids))}
        n, nread, right = stat(ag)
        entry["agreed_right"] = pct(right, nread)
        entry["agreed_abstain"] = n - nread
        for rule in ("tool_only", "either", "both"):
            ok = [i for i in ag if not held(i, rule)]
            n2, nread2, right2 = stat(ok)
            entry[f"applied_{rule}"] = {"n": len(ok), "yield": pct(len(ok), len(ids)), "right": pct(right2, nread2),
                                         "wrong_ids": sorted(i for i in ok if verdict[i] not in RIGHT and verdict[i] != "abstain")}
        # strata and expected error at the stored mix, rule "either"
        for rule in ("none", "either"):
            ok = ag if rule == "none" else [i for i in ag if not held(i, rule)]
            ok = [i for i in ok if verdict[i] != "abstain"]
            cor = [i for i in ok if rows[i]["label"] == "correct"]
            dfc = [i for i in ok if rows[i]["label"] == "defective"]
            wc = sum(1 for i in cor if verdict[i] not in RIGHT)
            wd = sum(1 for i in dfc if verdict[i] not in RIGHT)
            e = {"stored_correct": [len(cor), wc], "stored_defective": [len(dfc), wd], "wrong_where_correct": pct(wc, len(cor)), "wrong_where_defective": pct(wd, len(dfc))}
            p = STORED.get(g)
            if p is not None and cor and dfc:
                lo_d, hi_d = wilson(wd, len(dfc))
                lo_c, hi_c = wilson(wc, len(cor))
                r_at = p * wd / len(dfc) + (1 - p) * wc / len(cor)
                y = len(ok) / len(ids)
                e.update({"stored_rate": p, "reader_error_among_applied": round(r_at, 4), "range": [round(p * lo_d + (1 - p) * lo_c, 4), round(p * hi_d + (1 - p) * hi_c, 4)],
                          "applied_share": round(y, 3), "net_error_if_applied": round(y * r_at + (1 - y) * p, 4),
                          "net_range": [round(y * (p * lo_d + (1 - p) * lo_c) + (1 - y) * p, 4), round(y * (p * hi_d + (1 - p) * hi_c) + (1 - y) * p, 4)]})
            entry[f"mix_{rule}"] = e
        out["groups"][g] = entry
    # ---- hold rules: numbers over all agreed reports ----------------------------------------------------------------------------------------
    for rule in ("tool_only", "either", "both", "a_only"):
        ok = [i for i in agreed_all if not held(i, rule)]
        hl = [i for i in agreed_all if held(i, rule) and verdict[i] != "abstain"]
        n, nread, right = stat(ok)
        out["rules"][rule] = {"applied": len(ok), "applied_right": pct(right, nread), "applied_wrong": nread - right,
                              "held_wrong_caught": sum(1 for i in hl if verdict[i] not in RIGHT), "held_right_lost": sum(1 for i in hl if verdict[i] in RIGHT), "held_total": len(hl)}
    base = {i for i in agreed_all if not held(i, "tool_only")}
    for rule in ("either", "both", "a_only"):
        removed = [i for i in base if held(i, rule) and verdict[i] != "abstain"]
        out["rules"][rule]["incremental_over_tool_holds"] = {"removed": len(removed), "wrong": sum(verdict[i] not in RIGHT for i in removed), "right": sum(verdict[i] in RIGHT for i in removed)}
    # ---- holds by code, with verdict ---------------------------------------------------------------------------------------------------------------
    codes = defaultdict(lambda: Counter())
    for i in agreed_all:
        for h in tool_holds(i) + (["needs_ruling"] if (rows[i].get("needs_ruling_a") or rows[i].get("needs_ruling_b")) else []):
            codes[h]["n"] += 1
            codes[h]["wrong" if verdict[i] not in RIGHT and verdict[i] != "abstain" else ("abstain" if verdict[i] == "abstain" else "right")] += 1
    out["hold_codes"] = {k: dict(v) for k, v in codes.items()}
    # ---- flags ---------------------------------------------------------------------------------------------------------------------------------------
    fl = {"valid_outputs_a": sum(rows[i]["state_a"] == "valid" for i in scored), "valid_outputs_b": sum(rows[i]["state_b"] == "valid" for i in scored),
          "flag_a": sum(bool(rows[i].get("needs_ruling_a")) for i in scored), "flag_b": sum(bool(rows[i].get("needs_ruling_b")) for i in scored),
          "flag_both": sum(bool(rows[i].get("needs_ruling_a") and rows[i].get("needs_ruling_b")) for i in scored),
          "flag_either_any_report": sum(bool(rows[i].get("needs_ruling_a") or rows[i].get("needs_ruling_b")) for i in scored)}
    flagged_agreed = [i for i in agreed_all if rows[i].get("needs_ruling_a") or rows[i].get("needs_ruling_b")]
    fl["agreed_flagged_either"] = len(flagged_agreed)
    fl["agreed_flagged_both"] = sum(1 for i in flagged_agreed if rows[i].get("needs_ruling_a") and rows[i].get("needs_ruling_b"))
    fl["agreed_flagged_wrong"] = sorted(i for i in flagged_agreed if verdict[i] not in RIGHT and verdict[i] != "abstain")
    fl["agreed_unflagged_wrong"] = sorted(i for i in agreed_all if i not in flagged_agreed and verdict[i] not in RIGHT and verdict[i] != "abstain")
    fl["judged"] = dict(Counter(FLAG_JUDGE.get(i, "unjudged") for i in flagged_agreed))
    fl["unjudged_ids"] = [i for i in flagged_agreed if i not in FLAG_JUDGE]
    out["flags"] = fl
    # ---- back-reference openings -----------------------------------------------------------------------------------------------------------------------
    back = [i for i in scored if opens_with_back_reference(reps[i]["text"])]
    b = {"opening_back_reference": len(back), "with_previous_report": sum(rows[i]["has_prev"] for i in back), "needs_previous_flag": sum(rows[i]["needs_prev"] for i in back),
         "without_previous_and_not_flagged": [i for i in back if not rows[i]["has_prev"] and not rows[i]["needs_prev"]], "rows": {}}
    for i in back:
        r = rows[i]
        b["rows"][i] = {"has_prev": r["has_prev"], "needs_prev": r["needs_prev"], "agree": r["agree"], "verdict": verdict.get(i, ""), "tool_holds": tool_holds(i) if r["agree"] else [],
                        "inherited_links": any("inherited" in k for ks in r.get("kinds_a", []) for k in ks), "v1": v1_tsv[i][7] if i in v1_tsv else ""}
    b["hold_code_present_in_either_output"] = {i: any("back_reference_without_previous_report" in rows[i].get(f"holds_{t}", []) for t in "ab") for i in b["without_previous_and_not_flagged"]}
    out["back_reference"] = b
    imam = [i for i in agreed_all if any("imam_in_text" in ks for ks in rows[i]["kinds_a"])]
    out["imam_in_text_agreed"] = {"reports": len(imam), "verdicts": dict(Counter(verdict[i] for i in imam))}
    ext = []
    for i in scored:
        r = rows[i]
        if r["both_valid"] and not r["agree"]:
            ca, cb = set(r["canon_a"]), set(r["canon_b"])
            for x, y, who in ((ca, cb, "A"), (cb, ca, "B")):
                if x != y and len(x) == len(y) and all(any(q.startswith(z + "|") or q == z for z in y) for q in x) and all(not any(z.startswith(q + "|") for z in y) or True for q in x):
                    pass
            def extends(x, y):
                return len(x) == len(y) and x != y and all(any(q.startswith(z + "|") for z in y) or q in y for q in x)
            if extends(ca, cb):
                ext.append((i, "A extends B"))
            elif extends(cb, ca):
                ext.append((i, "B extends A"))
    out["pairs_differing_by_extension"] = ext
    out["compiler_duplicates"] = dup
    # ---- v1 on the same 279 --------------------------------------------------------------------------------------------------------------------------------------------
    v1side = {}
    for g in ["ALL", "sunni", "imami"] + GROUPS:
        ids = members(g)
        ag = [i for i in ids if v1[i]["state"] == "agree"]
        vv = {i: v1_tsv[i][7] for i in ag}
        read = [i for i in ag if vv[i] != "unread"]
        right = sum(1 for i in read if vv[i] in RIGHT)
        gated = [i for i in read if not GATE.match(fold_loose(reps[i]["text"]))]
        rg = sum(1 for i in gated if vv[i] in RIGHT)
        cor = [i for i in read if rows[i]["label"] == "correct"]
        dfc = [i for i in read if rows[i]["label"] == "defective"]
        cor_g = [i for i in gated if rows[i]["label"] == "correct"]
        dfc_g = [i for i in gated if rows[i]["label"] == "defective"]
        e = {}
        for nm, cc, dd in (("no_gate", cor, dfc), ("gate", cor_g, dfc_g)):
            wc = sum(1 for i in cc if vv[i] not in RIGHT)
            wd = sum(1 for i in dd if vv[i] not in RIGHT)
            p = STORED.get(g)
            ent = {"wrong_where_correct": pct(wc, len(cc)), "wrong_where_defective": pct(wd, len(dd))}
            if p is not None and cc and dd:
                lo_d, hi_d = wilson(wd, len(dd)); lo_c, hi_c = wilson(wc, len(cc))
                r_at = p * wd / len(dd) + (1 - p) * wc / len(cc)
                y = (len(gated) if nm == "gate" else len(ag)) / len(ids)
                ent.update({"reader_error_among_applied": round(r_at, 4), "range": [round(p * lo_d + (1 - p) * lo_c, 4), round(p * hi_d + (1 - p) * hi_c, 4)],
                            "applied_share": round(y, 3), "net_error_if_applied": round(y * r_at + (1 - y) * p, 4)})
            e[nm] = ent
        imputed_k = right + round((len(ag) - len(read)) * 29 / 40)
        v1side[g] = {"imputed": pct(imputed_k, len(ag)), "agreed": pct(len(ag), len(ids)), "read": len(read), "unread": len(ag) - len(read), "right_of_read": pct(right, len(read)),
                     "gated": {"n": len(gated), "yield": pct(len(gated), len(ids)), "right": pct(rg, len(gated))}, "mix": e}
    out["v1"] = v1side
    # ---- verdict changes between the pilots ----------------------------------------------------------------------------------------------------------------------------------
    chg = {"fixed": [], "broke": [], "same_right": 0, "same_wrong": [], "newly_agreed": defaultdict(list), "lost_agreement": defaultdict(list), "v1_unread_now": []}
    def v1v(i):
        row = v1_tsv.get(i)
        if not row:
            return None
        s = row[7]
        return s.split(":")[-1] if s.startswith("invalid_but_agree_read") else (s if v1[i]["state"] == "agree" else None)
    for i in scored:
        o = v1v(i)
        n = verdict.get(i)
        if rows[i]["agree"] and v1[i]["state"] == "agree" and o in RIGHT + ("wrong", "cannot_tell") and n:
            if o in RIGHT and n in RIGHT:
                chg["same_right"] += 1
            elif o not in RIGHT and n in RIGHT:
                chg["fixed"].append(i)
            elif o in RIGHT and n in ("wrong", "cannot_tell"):
                chg["broke"].append(i)
            elif n != "abstain":
                chg["same_wrong"].append(i)
            else:
                chg["broke"].append(i)
        elif rows[i]["agree"] and v1[i]["state"] != "agree":
            chg["newly_agreed"][n].append(i)
        elif not rows[i]["agree"] and v1[i]["state"] == "agree":
            chg["lost_agreement"][o or "unread"].append(i)
        elif rows[i]["agree"] and o == "unread" or (rows[i]["agree"] and o is None):
            chg["v1_unread_now"].append((i, n))
    chg["newly_agreed"] = {k: v for k, v in chg["newly_agreed"].items()}
    chg["lost_agreement"] = {k: v for k, v in chg["lost_agreement"].items()}
    out["changes"] = chg
    # ---- invalid outputs: tool-fixable? ---------------------------------------------------------------------------------------------------------------------------------------
    inv = Counter()
    for i in scored:
        for t in "ab":
            if rows[i][f"state_{t}"] == "invalid":
                e = rows[i][f"err_{t}"]
                inv[e.split(":")[0]] += 1
    out["invalid_reasons"] = dict(inv)
    (HERE / "numbers_v2.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=list), encoding="utf-8")

    # ---- agreed_set.tsv ------------------------------------------------------------------------------------------------------------------------------------------------------------
    head = ["id", "group", "work", "label", "state", "classes_abcd", "verdict", "tag", "tool_holds", "needs_ruling_A", "needs_ruling_B", "default_hold", "v1_verdict", "source_of_verdict", "quote", "why"]
    lines = ["\t".join(head)]
    for i in sorted(rows):
        r = rows[i]
        st = "excluded_prompt_fragment" if r["excluded"] else ("agree" if r["agree"] else ("differ" if r["both_valid"] else "invalid"))
        q = why = src = ""
        if r["agree"] and not r["excluded"]:
            if i in V2:
                q, why, src = V2[i][3], V2[i][4], "read in v2"
            else:
                src = "carried from v1 (same routes, no inherited link; read in v1)"
                q = MARKS.sub("", reps[i]["text"])[:70].replace("\n", " ")
                why = "see ../analysis/cases.md"
        elif i in DIS:
            q, why, src = DIS[i][3], DIS[i][4], "disagreement sample read: " + DIS[i][0] + ", right: " + DIS[i][1]
        v = verdict.get(i, "")
        lines.append("\t".join([i, r["group"], r["work"], r["label"], st, r.get("classes", ""), v, tag.get(i, ""), ",".join(tool_holds(i)) if r["agree"] else "",
                                 str(bool(r.get("needs_ruling_a"))), str(bool(r.get("needs_ruling_b"))), str(held(i, "either")) if r["agree"] else "",
                                 (v1v(i) or v1_tsv[i][4]) if i in v1_tsv else "", src, q, why]).replace("\n", " "))
    (HERE / "agreed_set.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out["split"], ensure_ascii=False))
    print(out["verdict_counts"])
    for g, e in out["groups"].items():
        print(g, e["reports"], "agreed", e["agreed"], "right", e["agreed_right"], "| either:", e["applied_either"]["n"], e["applied_either"]["yield"], e["applied_either"]["right"], e["applied_either"]["wrong_ids"])
    print(json.dumps(out["rules"], ensure_ascii=False))
    print(json.dumps(out["flags"], ensure_ascii=False))
    print(json.dumps(out["hold_codes"], ensure_ascii=False))
    print("compiler dup", dup)
    print("back", {k: v for k, v in out["back_reference"].items() if k != "rows"})
    print("invalid", dict(inv))


main()
