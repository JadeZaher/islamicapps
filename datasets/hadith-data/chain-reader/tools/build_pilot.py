"""Build the labelled pilot set and the blind packets (see ../README.md and ../AGENTS.md).

  python build_pilot.py ids   --out label_ids.json                 # hadith ids carrying a hand-read label
  node --env-file=.env.local fetch_labelled.cjs label_ids.json fetched.json   # read-only production snapshot
  python build_pilot.py build --fetched fetched.json --out-dir ../pilot

Labels come from chain-audit rounds 2-4 (`sample_check.csv`, hand-read rows only). Production is read only through the
snapshot file; this script never connects to a database.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from norm import fold_loose as fold, surface_in_text  # noqa: E402

AUDIT = Path(__file__).resolve().parents[2] / "chain-audit"
ROUNDS = ("round2", "round3", "round4")
SEED = "chain-reader-pilot-1"
PACKET_SIZE = 25
MAX_TEXT_CHARS = 6000
MAX_DEFECTIVE = 105
MIN_CORRECT_PER_WORK = 5
CHAIN_FIELD_WORKS = ("ahmad", "darimi", "muwatta")   # text_ar is matn only; the chain is the separate `sanad` field
def digest(*parts: str) -> str:
    return hashlib.md5("\u001f".join((SEED, *parts)).encode()).hexdigest()


def read_labels() -> list[dict]:
    """Hand-read chain and report labels from rounds 2-4, in round order (a later round overrides an earlier one)."""
    rows = []
    for round_name in ROUNDS:
        path = AUDIT / round_name / "sample_check.csv"
        for row in csv.DictReader(path.open(encoding="utf-8-sig", newline="")):
            if row["lane"].startswith("pair_") or row["judged_by"] != "read" or not row["hadith_id"]:
                continue
            verdict = {"ok": "correct", "correct": "correct", "defect": "defective"}.get(row["verdict"])
            if verdict is None:          # ok_unread, unverifiable: not a reading
                continue
            rows.append({"round": round_name, "lane": row["lane"], "stratum": row.get("stratum", ""),
                         "hadith_id": row["hadith_id"], "chain_id": row["chain_id"] or None, "verdict": verdict,
                         "kind": row["kind"], "note": row["note"].strip(),
                         "report_verdict": {"ok": "correct", "defect": "defective"}.get(row.get("report_verdict", ""))})
    return rows


def read_fixed_hadiths() -> set[str]:
    """Hadiths the round-3 re-judgement of the round-2 regression list calls fixed (an older defect label is stale)."""
    path = AUDIT / "round3" / "regress_rejudge.tsv"
    rows = csv.DictReader(path.open(encoding="utf-8", newline=""), delimiter="\t")
    return {r["hadith_id"] for r in rows if r["my_verdict"] in ("fixed", "fixed_confirmed", "fixed_unread", "already_correct")}


# A note «names the right reading» when it says an Arabic name is missing / lost / not stored.
LOST_NAME = re.compile(r"([ء-ي][ء-ي ]*[ء-ي])\s*(?:\([^)]*\)\s*)?(?:is\s+|are\s+)?(?:missing|not stored|not kept|lost|dropped|not attached)")


def expected_names(note: str, text: str, stored_surfaces: set[str]) -> list[str]:
    folded_text = fold(text)
    found = []
    for match in LOST_NAME.finditer(note):
        name = fold(match.group(1))
        if len(name) >= 3 and name in folded_text and name not in stored_surfaces and name not in found:
            found.append(name)
    return found


def label_state(entry: dict, chain: dict | None, fixed_hadiths: set[str]) -> str:
    """current: audited after the last builder change (round 4) or the quoted stored surface is still stored;
    stale_fixed: re-judged as fixed; unconfirmed: an older defect nothing in the stored chain confirms any more."""
    if entry["verdict"] == "correct":
        return "current" if entry["round"] == "round4" else "older"
    if entry["round"] == "round4":
        return "current"
    if entry["hadith_id"] in fixed_hadiths:
        return "stale_fixed"
    if chain is not None:
        stored = {fold(m[1]) for m in chain["mentions"]}
        quoted = [fold(q) for q in re.findall(r"«([^»]+)»", entry["note"])] + [fold(a) for a in re.findall(r"cut:\s*(.+?)\s*->", entry["note"])]
        if any(q in stored and len(q.split()) >= 3 for q in quoted) or any(a in stored for a in [fold(a) for a in re.findall(r"cut:\s*(.+?)\s*->", entry["note"])]):
            return "confirmed"
    return "unconfirmed"


def reader_text(hadith: dict) -> tuple[str, str]:
    """(text the reader sees, layout). Pure Canon works store the chain in `sanad` and only the matn in `text_ar`."""
    work = hadith["collection_id"].split(":")[-1]
    if work in CHAIN_FIELD_WORKS:
        sanad = (hadith.get("sanad") or "").strip()
        return (f"{sanad}\n\n{hadith['text_ar']}" if sanad else hadith["text_ar"]), "chain_field_then_matn"
    return hadith["text_ar"], "full_text"


def build(fetched_path: Path, out_dir: Path) -> None:
    snapshot = json.loads(fetched_path.read_text(encoding="utf-8"))
    rows, fetched_at = snapshot["rows"], snapshot["fetched_at"]
    fixed_hadiths = read_fixed_hadiths()
    by_hadith: dict[str, list[dict]] = defaultdict(list)
    for label in read_labels():
        by_hadith[label["hadith_id"]].append(label)

    excluded = Counter()
    candidates = []
    example_file = Path(__file__).resolve().parents[1] / "examples" / "examples.json"
    prompt_examples = {e["hadith_id"] for e in json.loads(example_file.read_text(encoding="utf-8"))} if example_file.is_file() else set()
    for hadith_id, labels in by_hadith.items():
        if hadith_id in prompt_examples:
            excluded["used_as_prompt_example"] += 1      # the reader has seen these in prompt.md: never part of the pilot
            continue
        row = rows.get(hadith_id)
        if not row or row["h"]["retired_at"]:
            excluded["hadith_retired_or_missing"] += 1
            continue
        hadith, chains = row["h"], row["chains"]
        collection = hadith["collection_id"]
        _, tradition, work = collection.split(":")
        if hadith["sanad_inherits_from"]:
            excluded[f"inherited_chain:{work}"] += 1      # the chain belongs to the parent report; a reader of this text alone cannot see it
            continue
        text, layout = reader_text(hadith)
        if not text.strip() or len(text) > MAX_TEXT_CHARS:
            excluded["text_empty_or_over_cap"] += 1
            continue
        chain_by_id = {c["id"]: c for c in chains}
        latest: dict[str, dict] = {}                      # chain id (or "" for a report-level label) -> latest round's label
        for label in labels:
            latest[label["chain_id"] or ""] = label
        stored = []
        usable = True
        for chain in chains:
            surfaces = [m[1] for m in sorted(chain["mentions"], key=lambda m: m[0])]
            entry = latest.get(chain["id"])
            record = {"chain_id": chain["id"], "branch": chain["branch"], "structure_status": chain["structure_status"],
                      "surfaces": surfaces, "surfaces_missing_from_text": sum(1 for x in surfaces if not surface_in_text(x, text)),
                      "verdict": "unlabelled", "kind": "", "note": "", "label_round": None, "label_state": None}
            if entry:
                record.update(verdict=entry["verdict"], kind=entry["kind"], note=entry["note"], label_round=entry["round"],
                              label_state=label_state(entry, chain, fixed_hadiths))
            stored.append(record)
        for chain_id, entry in latest.items():
            if chain_id and chain_id not in chain_by_id:
                excluded["labelled_chain_no_longer_live"] += 1
                usable = False
        if not usable:
            continue
        report_entry = latest.get("")
        report_labels = []
        if report_entry:
            report_labels.append({"verdict": report_entry["verdict"], "kind": report_entry["kind"], "note": report_entry["note"],
                                  "label_round": report_entry["round"], "label_state": label_state(report_entry, None, fixed_hadiths)})
        for entry in latest.values():                    # round 4 hand-read the report as a whole as well
            if entry["chain_id"] and entry["report_verdict"] == "defective" and entry["verdict"] == "correct":
                report_labels.append({"verdict": "defective", "kind": entry["kind"], "note": entry["note"], "label_round": entry["round"], "label_state": "current"})
        chain_labels = [s for s in stored if s["verdict"] != "unlabelled"]
        states = [s["label_state"] for s in chain_labels] + [r["label_state"] for r in report_labels]
        defective = any(s["verdict"] == "defective" for s in chain_labels) or any(r["verdict"] == "defective" for r in report_labels)
        if defective:
            live_defects = [s["label_state"] for s in chain_labels if s["verdict"] == "defective"] + [r["label_state"] for r in report_labels if r["verdict"] == "defective"]
            if all(state == "stale_fixed" for state in live_defects):
                excluded["defect_label_stale_fixed"] += 1
                continue
            rank = 0 if "current" in live_defects else 1 if "confirmed" in live_defects else 2
            report_verdict = "defective"
        else:
            if not states:
                excluded["no_usable_label"] += 1
                continue
            rank = 0 if all(s == "current" for s in states) else 1
            report_verdict = "correct"
        surfaces_seen = {fold(x) for s in stored for x in s["surfaces"]}
        names = []
        if defective:
            for s in chain_labels + report_labels:
                if s["verdict"] == "defective":
                    names += [n for n in expected_names(s["note"], text, surfaces_seen) if n not in names]
        candidates.append({"hadith_id": hadith_id, "tradition": tradition, "work": work, "collection_id": collection,
                           "text": text, "text_layout": layout, "stored_chains": stored, "report_labels": report_labels,
                           "report_verdict": report_verdict, "expected_names": names, "rank": rank,
                           "label_rounds": sorted({x["label_round"] for x in stored + report_labels if x.get("label_round")})})

    # Selection: every defective report with a current or confirmed label, unconfirmed ones (newest round first) up to the cap;
    # then, per work, as many correct reports as defective ones (never fewer than MIN_CORRECT_PER_WORK), freshest labels first.
    defective = sorted((c for c in candidates if c["report_verdict"] == "defective"), key=lambda c: (c["rank"], digest(c["hadith_id"])))
    firm = [c for c in defective if c["rank"] < 2]
    loose = sorted((c for c in defective if c["rank"] == 2), key=lambda c: (c["label_rounds"][-1] != "round3", digest(c["hadith_id"])))
    chosen_defective = firm + loose[:max(0, MAX_DEFECTIVE - len(firm))]
    per_work_defective = Counter(c["work"] for c in chosen_defective)
    pool = defaultdict(list)
    for c in candidates:
        if c["report_verdict"] == "correct":
            pool[c["work"]].append(c)
    chosen_correct = []
    for work, items in pool.items():
        want = max(per_work_defective.get(work, 0), MIN_CORRECT_PER_WORK)
        items.sort(key=lambda c: (c["rank"], digest(c["hadith_id"])))
        chosen_correct += items[:want]
    chosen = chosen_defective + chosen_correct

    chosen.sort(key=lambda c: digest(c["hadith_id"]))   # opaque, stratum-blind order: ids and packets carry no hint of verdict or work
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "packets").mkdir(exist_ok=True)
    for old in (out_dir / "packets").glob("packet-*.jsonl"):
        old.unlink()
    with (out_dir / "reports.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
        for index, c in enumerate(chosen, start=1):
            c["id"] = f"cr-{index:04d}"
            record = {"id": c["id"], "hadith_id": c["hadith_id"], "tradition": c["tradition"], "work": c["work"], "text": c["text"],
                      "text_layout": c["text_layout"], "stored_chains": c["stored_chains"], "report_verdict": c["report_verdict"],
                      "report_labels": c["report_labels"], "expected_names": c["expected_names"], "label_rounds": c["label_rounds"],
                      "evidence_rank": c["rank"], "snapshot_at": fetched_at}
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    for number, start in enumerate(range(0, len(chosen), PACKET_SIZE), start=1):
        with (out_dir / "packets" / f"packet-{number:02d}.jsonl").open("w", encoding="utf-8", newline="\n") as handle:
            for c in chosen[start:start + PACKET_SIZE]:
                handle.write(json.dumps({"id": c["id"], "text": c["text"]}, ensure_ascii=False) + "\n")

    table = Counter((c["tradition"] + ":" + c["work"], c["report_verdict"]) for c in chosen)
    works = sorted({w for w, _ in table})
    summary = {"snapshot_at": fetched_at, "reports": len(chosen), "defective": len(chosen_defective), "correct": len(chosen_correct),
               "defective_by_evidence": dict(Counter(c["rank"] for c in chosen_defective)),
               "per_work": {w: {"defective": table[(w, "defective")], "correct": table[(w, "correct")]} for w in works},
               "excluded_before_selection": dict(excluded), "candidates": len(candidates),
               "candidates_defective_not_chosen": len(defective) - len(chosen_defective),
               "defective_with_expected_names": sum(1 for c in chosen_defective if c["expected_names"]),
               "packets": -(-len(chosen) // PACKET_SIZE)}
    (out_dir / "pilot_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    ids = sub.add_parser("ids")
    ids.add_argument("--out", required=True)
    built = sub.add_parser("build")
    built.add_argument("--fetched", required=True)
    built.add_argument("--out-dir", required=True)
    args = parser.parse_args()
    if args.command == "ids":
        Path(args.out).write_text(json.dumps(sorted({label["hadith_id"] for label in read_labels()})), encoding="utf-8")
    else:
        build(Path(args.fetched), Path(args.out_dir))


if __name__ == "__main__":
    main()
