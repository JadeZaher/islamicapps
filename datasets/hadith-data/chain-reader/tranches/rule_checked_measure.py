"""MEASURE (no behaviour change): the readings held as `stored_chain_checked_by_rule`: what the agreed reading does to the report's
rule-checked chains and to the teacher-student pairs they feed. Owner decision pending (reviews/ai/AGENTS.md §Chain fixes).

    python -B -X utf8 tranches/rule_checked_measure.py --stores batch001=<store> t01=<scratch store> t02=<scratch store> --out <dir>

Reads submissions only (the held ones whose hold codes include `stored_chain_checked_by_rule`), the reports' texts (private reports
files) and, read-only, production's mentions, chains and `narrator_transmissions` through `prod_query.ts` (kept beside this file's
caller in the scratchpad: any script that prints those rows as JSON works). Writes `measure.json` and `examples.json`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
READER = HERE.parent
ROOT = READER.parents[2]
sys.path.insert(0, str(ROOT / "datasets" / "hadith-data" / "chain-fixes"))
import chain_fix_engine as engine  # noqa: E402  (comparison_key: the pipeline's own fold)

STANDING = ("source_index", "human_verified", "derived_relation_verified")


def group_of(tradition: str, work: str) -> str:
    if tradition == "sunni":
        return "six Sunni books"
    return "al-Faqih" if work.endswith("man-la-yahduruhu-al-faqih") else "other Imami"


def held_submissions(store: Path) -> list[dict]:
    states = {state["fix_id"]: state for state in json.loads((store / "state.json").read_text(encoding="utf-8"))["fixes"]}
    seen: dict[str, dict] = {}
    for file in sorted((store / "submissions").glob("*.jsonl")):
        for line in file.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                seen.setdefault(row["fix_id"], row)
    return [{**row, "state": states[fix_id]} for fix_id, row in seen.items()
            if fix_id in states and "stored_chain_checked_by_rule" in states[fix_id]["holds"]]


def query(script: str, payload: dict, scratch: Path) -> dict:
    (scratch / "q_in.json").write_text(json.dumps(payload), encoding="utf-8")
    done = subprocess.run(["node", "--import", "tsx", script, str(scratch / "q_in.json"), str(scratch / "q_out.json")], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    if done.returncode:
        raise SystemExit(done.stderr)
    return json.loads((scratch / "q_out.json").read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stores", nargs="+", required=True, help="name=store directory")
    parser.add_argument("--texts", nargs="+", required=True, help="name=private reports.jsonl (text and hadith id by report)")
    parser.add_argument("--query", required=True, help="the read-only production query script")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    texts: dict[str, str] = {}
    for spec in args.texts:
        for line in Path(spec.split("=", 1)[1]).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                texts[row["hadith_id"]] = row["text"]
    fixes: list[dict] = []
    for spec in args.stores:
        name, store = spec.split("=", 1)
        fixes += [{**row, "source": name} for row in held_submissions(Path(store))]
    unique = {fix["fix_id"]: fix for fix in fixes}
    fixes = sorted(unique.values(), key=lambda fix: fix["hadith_id"])

    chain_ids = [chain["chain_id"] for fix in fixes for chain in fix["base"]["chains"] if chain["structure_status"] == "checked_by_rule"]
    first = query(args.query, {"chainIds": chain_ids, "pairs": []}, out)
    chains = {row["id"]: row for row in first["chains"]}
    mentions: dict[str, list[dict]] = defaultdict(list)
    for row in first["mentions"]:
        mentions[row["chain_id"]].append(row)

    def standing(row: dict) -> bool:
        return bool(row["narrator_id"]) and row["resolution"] in STANDING and row["link_kind"] not in ("anonymous", "not_a_narrator")

    def pairs_of(chain_id: str) -> set[tuple[str, str]]:
        rows = {row["position"]: row for row in mentions[chain_id]}
        found = {(rows[p]["narrator_id"], rows[p + 1]["narrator_id"]) for p in rows if p + 1 in rows and standing(rows[p]) and standing(rows[p + 1])
                 and rows[p]["resolution_basis"] == rows[p + 1]["resolution_basis"] and rows[p]["resolution_basis"] in ("source_index", "human_decision")}
        chain = chains.get(chain_id)
        if chain and chain["compiler_narrator_id"] and chain["compiler_link"] == "direct" and not chain["suspension"] and 0 in rows and standing(rows[0]):
            found.add((chain["compiler_narrator_id"], rows[0]["narrator_id"]))
        return {(s, t) for s, t in found if s != t}

    candidate_pairs = sorted({pair for chain_id in chain_ids for pair in pairs_of(chain_id)})
    second = query(args.query, {"chainIds": [], "pairs": [list(pair) for pair in candidate_pairs]}, out)
    in_view = {(row["student_id"], row["teacher_id"]): row for row in second.get("transmissions", [])}

    per_fix, examples_pool = [], []
    for fix in fixes:
        keys_read = [tuple(engine.comparison_key(m["surface_ar"]) for m in chain["mentions"]) for chain in fix["planned"]["chains"]]
        checked = [chain for chain in fix["base"]["chains"] if chain["structure_status"] == "checked_by_rule"]
        identical, changed = [], []
        for chain in checked:
            key = tuple(engine.comparison_key(m["surface_ar"]) for m in chain["mentions"])
            (identical if key in keys_read else changed).append(chain["chain_id"])
        old_pairs = {pair for chain in checked for pair in pairs_of(chain["chain_id"])} & set(in_view)
        sole = {pair for pair in old_pairs if in_view[pair]["hadith_count"] == 1}
        # Pairs the reading's routes would form if they fed the lists: only between names that keep their identity (both neighbours unchanged).
        old_position = {m["id"]: (chain["chain_id"], m["position"]) for chain in fix["base"]["chains"] for m in chain["mentions"]}
        identity_of = {row["id"]: row for rows in mentions.values() for row in rows}
        kept_pairs, new_pairs = set(), 0
        for chain in fix["planned"]["chains"]:
            for a, b in zip(chain["mentions"], chain["mentions"][1:]):
                if not (a["carry_identity"] and b["carry_identity"] and a.get("kept_mention_id") and b.get("kept_mention_id")):
                    continue
                (ca, pa), (cb, pb) = old_position[a["kept_mention_id"]], old_position[b["kept_mention_id"]]
                ra, rb = identity_of.get(a["kept_mention_id"]), identity_of.get(b["kept_mention_id"])
                if not (ra and rb and standing(ra) and standing(rb)):
                    continue
                # Position p is the student of p + 1 in the stored chain; the reading keeps the pair when its two names were adjacent so there.
                if ca == cb and pb == pa + 1:
                    kept_pairs.add((ra["narrator_id"], rb["narrator_id"]))
                else:
                    new_pairs += 1
        record = {"fix_id": fix["fix_id"], "hadith_id": fix["hadith_id"], "source": fix["source"], "group": group_of(fix["tradition"], fix["source_work_id"].split(":")[-1]),
                  "fix_kinds": fix["fix_kinds"], "holds": fix["state"]["holds"], "checked_chains": len(checked), "uncertain_chains": len(fix["base"]["chains"]) - len(checked),
                  "checked_identical": len(identical), "checked_changed": len(changed), "pairs_now": len(old_pairs), "pairs_only_this_report": len(sole),
                  "pairs_kept_by_reading": len(kept_pairs & old_pairs), "pairs_appearing_if_admitted": new_pairs,
                  "_pairs": sorted(old_pairs), "_sole": sorted(sole), "_kept": sorted(kept_pairs & old_pairs)}
        per_fix.append(record)
        if changed:
            base_chain = next(chain for chain in checked if chain["chain_id"] in changed)
            text = texts.get(fix["hadith_id"], "")
            examples_pool.append({**record, "stored_chain": [m["surface_ar"] for m in base_chain["mentions"]],
                                  "reading": [[m["surface_ar"] for m in chain["mentions"]] for chain in fix["planned"]["chains"]],
                                  "text_quote": (fix["evidence"][0]["quote"] if fix.get("evidence") else text[:200])})

    summary: dict[str, dict] = defaultdict(Counter)
    for record in per_fix:
        for key in (record["source"], "all"):
            row = summary[key]
            row["reports"] += 1
            row["reports_every_checked_chain_identical"] += record["checked_changed"] == 0
            row["reports_a_checked_chain_changed"] += record["checked_changed"] > 0
            row["checked_chains"] += record["checked_chains"]
            row["checked_chains_identical"] += record["checked_identical"]
            row["checked_chains_changed"] += record["checked_changed"]
            row["pairs_now"] += record["pairs_now"]
            row["pairs_only_this_report"] += record["pairs_only_this_report"]
            row["pairs_kept_by_reading"] += record["pairs_kept_by_reading"]
            row["pairs_appearing_if_admitted"] += record["pairs_appearing_if_admitted"]
            row["reports_with_a_pair_lost"] += record["pairs_only_this_report"] > 0
            row[f"group:{record['group']}"] += 1
    for key in sorted({record["source"] for record in per_fix} | {"all"}):
        chosen_records = [r for r in per_fix if key == "all" or r["source"] == key]
        summary[key]["distinct_pairs_now"] = len({tuple(p) for r in chosen_records for p in r["_pairs"]})
        summary[key]["distinct_pairs_only_these_reports"] = len({tuple(p) for r in chosen_records for p in r["_sole"]})
        summary[key]["distinct_pairs_kept_by_readings"] = len({tuple(p) for r in chosen_records for p in r["_kept"]})
    (out / "measure.json").write_text(json.dumps({"summary": {k: dict(v) for k, v in summary.items()}, "per_fix": [{k: v for k, v in r.items() if not k.startswith("_")} for r in per_fix]}, ensure_ascii=False, indent=1), encoding="utf-8")
    # Ten examples spread over groups and fix kinds, in a fixed order (no hand picking).
    buckets: dict[tuple, list[dict]] = defaultdict(list)
    for example in sorted(examples_pool, key=lambda e: e["hadith_id"]):
        buckets[(example["group"], example["fix_kinds"][0])].append(example)
    chosen: list[dict] = []
    while len(chosen) < 10 and any(buckets.values()):
        for key in sorted(buckets):
            if buckets[key] and len(chosen) < 10:
                chosen.append(buckets[key].pop(0))
    (out / "examples.json").write_text(json.dumps(chosen, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: dict(v) for k, v in summary.items()}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
