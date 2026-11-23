"""Extra v3.4 numbers of one tranche (run from chain-reader/): agreement with and without the saying label, saying labels per pass, needs_ruling by both, routes ending at an imam_in_text link.

    python -B -X utf8 conduction/extra_tranche_v3_4.py NN        (after post_tranche_v3_4.py wrote tranches/tranche-NN/triage-v3_4 and triage-v3_4-sayings)
"""
import csv
import json
import pathlib
import sys

CHAIN = pathlib.Path(__file__).resolve().parents[1]
for sub in ("", "v3_2", "v3_4"):
    sys.path.insert(0, str(CHAIN / sub) if sub else str(CHAIN))
from expand_v3_4 import expand, readings_agree, strip_sayings  # noqa: E402
from triage_v3_4 import read_pass  # noqa: E402
from validate_v3_4 import validate_v3_4, with_default_fixes  # noqa: E402

nn = sys.argv[1]
tdir = CHAIN / "tranches" / f"tranche-{nn}"
packets = {}
for path in sorted((tdir / "packets").glob("packet-*.jsonl")):
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            packets[row["id"]] = row
plain = {r["id"]: r for r in csv.DictReader((tdir / "triage-v3_4/triage.tsv").open(encoding="utf-8"), delimiter="\t")}
outs = {tag: {} for tag in "ab"}
for tag in "ab":
    for rid in packets:
        out, _ = read_pass(tdir / "outputs" / f"pass-{tag}", rid)
        outs[tag][rid] = with_default_fixes(out)


def labelled(output):
    return bool(output) and any(isinstance(g, dict) and "saying" in g for g in output.get("groups") or [])


lab = {tag: {r for r, o in outs[tag].items() if labelled(o)} for tag in "ab"}
both_valid = [r for r in packets if plain[r]["valid_a"] == "True" and plain[r]["valid_b"] == "True"]
agreed_plain = {r for r in packets if plain[r]["agree"] == "True"}
route_only = set()
for rid in both_valid:
    text, context = packets[rid]["text"], packets[rid].get("context") or {}
    readings = []
    for tag in "ab":
        stripped = strip_sayings(outs[tag][rid])
        if validate_v3_4(stripped, text, rid, context):
            break
        readings.append(expand(stripped, text, context)[0])
    if len(readings) == 2 and readings_agree(readings[0], readings[1]):
        route_only.add(rid)
total = len(packets)
print(f"reports {total}; jointly valid {len(both_valid)}; agreed (labels count) {len(agreed_plain)} = {100 * len(agreed_plain) / total:.1f}%; agreed on routes alone (labels ignored) {len(route_only)} = {100 * len(route_only) / total:.1f}%")
print(f"saying label: pass a {len(lab['a'])}, pass b {len(lab['b'])}, either {len(lab['a'] | lab['b'])}, both {len(lab['a'] & lab['b'])}, both and agreed {len(lab['a'] & lab['b'] & agreed_plain)}, exactly one pass {len(lab['a'] ^ lab['b'])}")
print(f"  of the exactly-one-pass reports, agreed on routes alone: {len((lab['a'] ^ lab['b']) & route_only)}; agreed with labels: {len((lab['a'] ^ lab['b']) & agreed_plain)}; route-only agreed but label-disagreed overall: {len(route_only - agreed_plain)}")
nr = {tag: {r for r, o in outs[tag].items() if o and o.get("needs_ruling")} for tag in "ab"}
print(f"needs_ruling flag: a {len(nr['a'])}, b {len(nr['b'])}, both {len(nr['a'] & nr['b'])}, either {len(nr['a'] | nr['b'])}")
ends = ends_all = 0
for rid in agreed_plain:
    path = tdir / "triage-v3_4" / "readings" / f"{rid}.json"
    if not path.is_file():
        continue
    routes = json.loads(path.read_text(encoding="utf-8"))["expanded_a"]["routes"]
    kinds = [route["links"][-1]["kind"] for route in routes if route["links"]]
    ends += any(kind == "imam_in_text" for kind in kinds)
    ends_all += bool(kinds) and all(kind == "imam_in_text" for kind in kinds)
print(f"agreed readings whose route ends at an imam_in_text link: any route {ends}, every route {ends_all}")
sayings_tsv = {r["id"]: r for r in csv.DictReader((tdir / "triage-v3_4-sayings/triage.tsv").open(encoding="utf-8"), delimiter="\t")}
print(f"agreed readings with 2+ sayings: {sum(int(r['sayings']) >= 2 for r in sayings_tsv.values())}")
