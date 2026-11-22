"""Shared loading for the tranche-01 judgement (read-only on everything outside analysis/)."""
from __future__ import annotations
import csv, json, math, re, sys, itertools
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
T = HERE.parent.parent  # tranche-01
MARKS = re.compile(r"[ً-ٰۖ-ۭـ​-‏‪-‮﻿]")
MARK = {"imam_in_text": "[M]", "inherited": "[I]", "unnamed": "[U]", "relation": "[R]", "back_reference": "[B]", "compiler_head": "[C]"}


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def pct(k, n):
    if n == 0:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f}% ({100 * lo:.1f}-{100 * hi:.1f})"


def group_of(work):
    if work.startswith("sunni"):
        return "sunni"
    if "faqih" in work:
        return "faqih"
    return "imami"


def triage():
    return {r["id"]: r for r in csv.DictReader((T / "triage" / "triage.tsv").open(encoding="utf-8"), delimiter="\t")}


def private():
    return {r["id"]: r for r in (json.loads(l) for l in (T / "private" / "reports.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())}


def packets():
    out = {}
    for p in sorted((T / "packets").glob("packet-*.jsonl")):
        for l in p.read_text(encoding="utf-8").splitlines():
            if l.strip():
                r = json.loads(l)
                out[r["id"]] = r
    return out


def reading(i):
    return json.loads((T / "triage" / "readings" / f"{i}.json").read_text(encoding="utf-8"))


def fmt_routes(routes, limit=4):
    out = []
    for r in routes[:limit]:
        out.append(" > ".join(MARK.get(l["kind"], "") + MARKS.sub("", l["surface"]) for l in r["links"] if l["kind"] != "compiler_head"))
    return " || ".join(out) + (f"  (+{len(routes) - limit} routes)" if len(routes) > limit else "")


def prod(o):
    if not o or not isinstance(o, dict) or not isinstance(o.get("groups"), list):
        return "(none)"
    out = []
    tail = o.get("shared_tail") or []
    for g in o["groups"]:
        lv = [[MARK.get(x.get("kind"), "") + MARKS.sub("", x.get("surface", "")) for x in L] for L in g.get("levels", []) + tail]
        for c in itertools.product(*lv):
            out.append(" > ".join(c))
    return " || ".join(out[:4]) + (f" (+{len(out) - 4})" if len(out) > 4 else "") + (" [needs_ruling]" if o.get("needs_ruling") else "")
