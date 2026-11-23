"""Step A numbers of the v3.4 re-read set: validate, triage (plain and --sayings-supported), saying labels, encounter endings, ruling flags. Run from chain-reader/."""
import csv, json, pathlib, subprocess, sys, re, collections
PY = [sys.executable, "-B", "-X", "utf8"]
SET = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "v3_4/reread-001")
def run(a): return subprocess.run(PY + a, capture_output=True, text=True, encoding="utf-8")
for p in "ab":
    r = run(["v3_4/validate_v3_4.py", "--packets", f"{SET}/packets", "--outputs", f"{SET}/outputs/pass-{p}"])
    print("validate", p, (r.stdout + r.stderr).strip().splitlines()[-1])
for name, extra in (("triage-v3_4", []), ("triage-v3_4-sayings", ["--sayings-supported"])):
    r = run(["v3_4/triage_v3_4.py", "--packets", f"{SET}/packets", "--pass-a", f"{SET}/outputs/pass-a", "--pass-b", f"{SET}/outputs/pass-b", "--out", f"{SET}/{name}"] + extra)
    s = json.loads((SET / name / "summary.json").read_text(encoding="utf-8"))
    print(name, {k: s[k] for k in ("reports", "valid_a", "valid_b", "agreed", "eligible", "applies_chain", "applies_no_chain", "agreed_with_two_or_more_sayings")})
    print("  holds", s["holds"])
rows = {r["id"]: r for r in csv.DictReader((SET / "triage-v3_4/triage.tsv").open(encoding="utf-8"), delimiter="\t")}
reasons = {r["opaque"]: r for r in csv.DictReader((SET / "private/reasons.tsv").open(encoding="utf-8"), delimiter="\t")}
out = {p: {} for p in "ab"}
for p in "ab":
    for f in (SET / f"outputs/pass-{p}").glob("r4-*.json"):
        try: out[p][f.stem] = json.loads(f.read_text(encoding="utf-8"))
        except ValueError: pass
lab = {p: {i for i, d in out[p].items() if any("saying" in g for g in d.get("groups") or [])} for p in "ab"}
print("labelled readings a", len(lab["a"]), "b", len(lab["b"]), "either", len(lab["a"] | lab["b"]), "both", len(lab["a"] & lab["b"]))
agreed_lab = [i for i in lab["a"] & lab["b"] if rows[i]["agree"] == "True"]
print("labelled by both and agreed:", len(agreed_lab), "| labelled by exactly one:", len(lab["a"] ^ lab["b"]))
# encounter: agreed readings of encounter-cue reports whose some route ends at an imam_in_text / non-Prophet speaker
enc = [i for i, r in reasons.items() if "encounter_shape" in r["reasons"]]
ends = 0
for i in enc:
    rp = SET / "triage-v3_4/readings" / f"{i}.json"
    if rows[i]["agree"] == "True" and rp.exists():
        rd = json.loads(rp.read_text(encoding="utf-8"))["expanded_a"]
        if any(rt["links"] and rt["links"][-1]["kind"] == "imam_in_text" for rt in rd["routes"]): ends += 1
print("encounter-shape reports", len(enc), "agreed with a route ending at an imam_in_text link (proxy for 'speaker in the encounter'):", ends)
both = [i for i, r in reasons.items() if "needs_ruling_both" in r["reasons"]]
cl = collections.Counter()
still = []
for i in both:
    fa, fb = bool(out["a"].get(i, {}).get("needs_ruling")), bool(out["b"].get(i, {}).get("needs_ruling"))
    cl["neither" if not (fa or fb) else "both" if fa and fb else "one"] += 1
    if fa or fb: still.append((i, fa, fb))
print("needs_ruling_both reports", len(both), dict(cl))
json.dump([{"id": i, "a": out["a"].get(i, {}).get("needs_ruling"), "b": out["b"].get(i, {}).get("needs_ruling"), "notes_a": out["a"].get(i, {}).get("notes"), "notes_b": out["b"].get(i, {}).get("notes")} for i, _, _ in still], (SET / "triage-v3_4/still_flagged_notes.json").open("w", encoding="utf-8"), ensure_ascii=False, indent=1)
