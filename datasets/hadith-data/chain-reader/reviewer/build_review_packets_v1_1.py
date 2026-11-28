"""Chain reviewer v1.1: packets and jobs for the review sets, a second-pass builder and a re-queue builder (reviewer/README-v1_1.md §3). Nothing runs a model or writes a database.

    python -B -X utf8 reviewer/build_review_packets_v1_1.py --sets                 (from chain-reader/: builds A, B (t01, t02: eligible + held) and C)
    python -B -X utf8 reviewer/build_review_packets_v1_1.py --second-pass --batch review-t01/held
    python -B -X utf8 reviewer/build_review_packets_v1_1.py --requeue --batch review-t01/held [--pass 1]

Sets (each batch folder holds packets/, jobs.json, private/{manifest.json, id_map.json}, outputs/ once run): A `review-applied-b001/` (the 348 readings applied on production from batch 001, taken from
reviews/ai/records/chain-fixes/state.json, cross-checked against queue.json); B `review-t01/` and `review-t02/`, each with `eligible/` (cleared by the v3.3 triage and on the apply list, status
"pending") and `held/` (every other AGREED reading, with its hold codes; those the tool cleared but an earlier check set aside carry `withheld_by_earlier_check`); C `review-disagreements-t02/`
(tranche 02 reports whose two valid readings differ). v1's builder (build_review_packets.py, untouched) supplies the item, reader and id machinery.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT.parents[2]
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_4"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
import build_review_packets as v1  # noqa: E402
import review_io_v1_1 as io  # noqa: E402
import review_rules_v1_1 as rules  # noqa: E402

PROMPT = HERE / "prompt-reviewer-v1_1.md"
PER_PACKET = 10
FIX_STORE = REPO / "reviews" / "ai" / "records" / "chain-fixes"


def prompt_record() -> dict:
    """Path, version (front matter) and sha256 of the exact v1.1 prompt bytes; written beside it as prompt-reviewer-v1_1.json."""
    data = PROMPT.read_bytes()
    version = next(line.split(":", 1)[1].strip() for line in data.decode("utf-8").splitlines() if line.startswith("version:"))
    record = {"specialist": "chain-reviewer", "file": PROMPT.name, "path": str(PROMPT), "repo_path": "datasets/hadith-data/chain-reader/reviewer/prompt-reviewer-v1_1.md", "version": version,
              "sha256": hashlib.sha256(data).hexdigest(), "chars": len(data.decode("utf-8")), "model": rules.REVIEWER_MODEL}
    (HERE / "prompt-reviewer-v1_1.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return record


REPORT_ID = re.compile(r"(?<![0-9a-z])(?:t[0-9]{2}|b1)-[0-9a-f]{6}(?![0-9a-z])")           # a reader's note may cite another report by its original id ("as in t01-4b15c4"): the reviewer must not see original ids


def make_item(opaque: str, report_id: str, data: dict, status: str, extra_codes: tuple[str, ...] = ()) -> tuple[dict, dict]:
    """(packet item, private record) via v1's builder, with the status chosen here, v1.1 hold words, and the facts the decision rule needs kept privately."""
    item, private = v1.build_item(opaque, report_id, data)
    codes = list(private["holds"]) + [c for c in extra_codes if c not in private["holds"]]
    item["status"] = status
    for block in item["readers"].values():
        if isinstance(block.get("notes"), list):
            block["notes"] = [REPORT_ID.sub("[another report]", note) if isinstance(note, str) else note for note in block["notes"]]
    item["holds"] = [{"code": c, "plain": rules.plain(c)} for c in codes]
    private.update({"status": status, "holds": codes, "not_clearable": bool(rules.blocking_codes(codes)), "blocking_codes": rules.blocking_codes(codes),
                    "stored_equals_reading": rules.stored_equals_reading(item)})
    return item, private


def write_batch(out: Path, items: list[tuple[dict, dict]], batch: str, prompt: dict, label: str, pass_label: str = "1", extra_private: dict | None = None) -> dict:
    """Packets (10 items), jobs and the private manifest of one pass; one fresh claude-opus-5-5 worker per packet."""
    packets_dir = io.packets_dir(out, pass_label)
    packets_dir.mkdir(parents=True, exist_ok=True)
    for old in packets_dir.glob("packet-*.json"):
        old.unlink()
    chunks = [items[i:i + PER_PACKET] for i in range(0, len(items), PER_PACKET)]
    jobs, characters = [], 0
    for n, chunk in enumerate(chunks, start=1):
        number = f"{n:02d}"
        body = {"format": rules.PACKET_FORMAT, "packet_id": f"{batch}-p{pass_label}-{number}", "batch": batch, "pass": pass_label, "items": [item for item, _ in chunk]}
        path = packets_dir / f"packet-{number}.json"
        text = json.dumps(body, ensure_ascii=False, indent=1) + "\n"
        path.write_text(text, encoding="utf-8", newline="\n")
        output_dir = io.outputs_dir(out, pass_label)
        run_id = f"{batch.replace('/', '-')}-review-p{pass_label}-{number}"
        message = v1.instruction(prompt, str(path), str(output_dir / f"packet-{number}.output.json"), str(output_dir / "RUN.txt"), run_id, number)
        characters += len(text)
        jobs.append({"job_id": run_id, "pass": pass_label, "packet": number, "packet_file": str(path), "packet_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                     "output_file": str(output_dir / f"packet-{number}.output.json"), "run_file": str(output_dir / "RUN.txt"), "run_id": run_id, "items": len(chunk),
                     "expected_items": [item["id"] for item, _ in chunk], "not_clearable_items": [item["id"] for item, record in chunk if record.get("not_clearable")],
                     "input_chars": len(message) + prompt["chars"] + len(text), "instruction": message})
    doc = {"format": rules.JOBS_FORMAT, "batch": batch, "pass": pass_label, "what": label, "prompt": {"path": prompt["path"], "version": prompt["version"], "sha256": prompt["sha256"]},
           "model": f"{rules.REVIEWER_MODEL} for every job; one fresh worker per packet, nothing shared between workers (reviews/ai/README.md §Isolation)",
           "run_line_format": "run_id={RUNID} | packet={NN} | model=<model id> | start=<UTC start> | end=<UTC end> | items=<number of reviews>",
           "output_file_format": "one JSON object per packet (shura-chain-review-output/1, prompt_version 1.1.0), exactly as the prompt describes, at output_file",
           "after": "record per item: python -B -X utf8 reviewer/record_reviews_v1_1.py --batch " + batch + "; then --second-pass for corrections and --requeue for invalid items (reviewer/RUN.md)",
           "decision_rule": "reviewer/review_rules_v1_1.py outcome()",
           "expected": {"jobs": len(jobs), "items": len(items), "run_txt_lines": len(jobs), "packet_characters": characters, "input_characters": sum(j["input_chars"] for j in jobs)}, "jobs": jobs}
    name = "jobs.json" if pass_label == "1" else f"jobs-pass-{pass_label}.json"
    (out / name).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    private = out / "private"
    private.mkdir(parents=True, exist_ok=True)
    manifest = {"batch": batch, "pass": pass_label, "what": label, "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "prompt": doc["prompt"],
                "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "items": {item["id"]: record for item, record in items}, **(extra_private or {})}
    (private / ("manifest.json" if pass_label == "1" else f"manifest-pass-{pass_label}.json")).write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return doc


def build_set(out: Path, batch: str, chosen: list[tuple[str, str, tuple[str, ...]]], data: dict, prompt: dict, label: str, extra: dict) -> dict:
    """`chosen`: (report id, status, extra hold codes). Deterministic: the salt survives in private/id_map.json."""
    salt = v1.salt_for(out)
    mapping = v1.opaque_ids([r for r, _, _ in chosen], salt)
    items = v1.shuffled([make_item(mapping[r], r, data, status, codes) for r, status, codes in chosen], salt)
    v1.write_id_map(out, salt, mapping)
    return write_batch(out, items, batch, prompt, label, extra_private=extra)


def agreed_ids(data: dict) -> list[str]:
    return [i for i, row in data["rows"].items() if row.get("agree") == "True" and row.get("valid_a") == "True" and row.get("valid_b") == "True"]


def applied_b001() -> tuple[list[str], dict]:
    """The readings applied on production from batch 001: state.json (derived by chain-fix-decide.ts) fixes with database == "applied", their earliest submission reading ids
    through the stored submissions (matching computeStates earliest-first representative selection), cross-checked against queue.json's awaiting_final_review, scoped to b1-*. Read only."""
    state = json.loads((FIX_STORE / "state.json").read_text(encoding="utf-8"))["fixes"]
    queue = json.loads((FIX_STORE / "queue.json").read_text(encoding="utf-8"))
    fix_to_reading = {}
    for path in sorted((FIX_STORE / "submissions").glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                fix_to_reading.setdefault(row["fix_id"], row["reading"]["id"])
    applied = sorted(f["fix_id"] for f in state if f.get("database") == "applied")
    assert set(applied) == set(queue["awaiting_final_review"]), "state.json and queue.json disagree on the applied set"
    assert all(f in fix_to_reading for f in applied), "an applied fix has no submission reading id"
    ids = sorted(fix_to_reading[f] for f in applied if fix_to_reading[f].startswith("b1-"))
    return ids, {"applied_from": ["reviews/ai/records/chain-fixes/state.json (fixes with database == applied)", "reviews/ai/records/chain-fixes/queue.json (awaiting_final_review, same fix ids)",
                                  "reviews/ai/records/chain-fixes/submissions/*.jsonl (earliest submission reading id per fix id, scoped to b1-*)"],
                 "state_fixes": len(state), "applied_fixes": len(applied), "b001_applied_fixes": len(ids)}


def sets(prompt: dict) -> int:
    summary = {}
    # A: applied, batch 001
    ids, provenance = applied_b001()
    data = load(ROOT / "v3" / "batch-001", None)
    missing = [i for i in ids if i not in data["rows"] or data["rows"][i].get("agree") != "True"]
    assert not missing, f"applied readings that are not agreed in the triage: {missing[:5]}"
    out = HERE / "review-applied-b001"
    doc = build_set(out, "review-applied-b001", [(i, "applied", ()) for i in ids], data, prompt, "A: the readings applied on production from batch 001 (status applied; v3.3 triage holds shown)",
                    {"source": "v3/batch-001", "triage": data["triage"].relative_to(ROOT).as_posix(), **provenance})
    (out / "private" / "applied_ids.txt").write_text("\n".join(ids) + "\n", encoding="utf-8", newline="\n")
    summary["review-applied-b001"] = {"readings": len(ids), "jobs": len(doc["jobs"]), **doc["expected"]}
    # B: tranches 01 through 10, every agreed reading, split eligible / held
    for number in [f"{n:02d}" for n in range(1, 11)]:
        source = ROOT / "tranches" / f"tranche-{number}"
        data = load(source, None)
        eligible_path = data["triage"] / "eligible_v3_3.txt"
        if not eligible_path.is_file():
            eligible_path = data["triage"] / "eligible.txt"
        eligible = set(eligible_path.read_text(encoding="utf-8").split())
        withheld_path = data["triage"] / "withheld_by_judge.txt"
        withheld = {line.split()[0] for line in withheld_path.read_text(encoding="utf-8").splitlines() if line.strip()} if withheld_path.is_file() else set()
        agreed = agreed_ids(data)
        assert eligible <= set(agreed), f"tranche-{number}: an apply-list reading is not agreed"
        lists = {"eligible": [(i, "pending", ()) for i in sorted(eligible)],
                 "held": [(i, "held", ("withheld_by_earlier_check",) if i in withheld else ()) for i in sorted(agreed) if i not in eligible]}
        for name, chosen in lists.items():
            batch = f"review-t{number}-{name}"
            out = HERE / f"review-t{number}" / name
            doc = build_set(out, batch, chosen, data, prompt, f"B: tranche {number}, agreed readings, {name} ({'cleared by triage and on the apply list' if name == 'eligible' else 'every other agreed reading, with its holds'})",
                            {"source": f"tranches/tranche-{number}", "triage": data["triage"].relative_to(ROOT).as_posix(), "list": name, "withheld_by_earlier_check": sorted(withheld & {i for i, _, _ in chosen})})
            summary[f"review-t{number}/{name}"] = {"readings": len(chosen), "jobs": len(doc["jobs"]), **doc["expected"],
                                                   "not_clearable": sum(1 for r in json.loads((out / "private" / "manifest.json").read_text(encoding="utf-8"))["items"].values() if r["not_clearable"])}
    # C: tranche 02 disagreements
    data = load(ROOT / "tranches" / "tranche-02", None)
    differ = sorted(i for i, row in data["rows"].items() if row.get("valid_a") == "True" and row.get("valid_b") == "True" and row.get("agree") != "True")
    out = HERE / "review-disagreements-t02"
    doc = build_set(out, "review-disagreements-t02", [(i, "held", ()) for i in differ], data, prompt, "C: tranche 02 reports whose two valid readings differ", {"source": "tranches/tranche-02", "triage": data["triage"].relative_to(ROOT).as_posix()})
    summary["review-disagreements-t02"] = {"readings": len(differ), "jobs": len(doc["jobs"]), **doc["expected"]}
    (HERE / "SETS.json").write_text(json.dumps({"prompt": prompt, "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "sets": summary}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    return 0


def load(source: Path, triage: Path | None) -> dict:
    if triage is None and source.resolve() != (ROOT / "v3" / "batch-001").resolve():
        for candidate in (source / "triage-v3_4", source / "triage-v3_3", source / "triage-v3_2"):
            if (candidate / "triage.tsv").is_file():
                triage = candidate
                break
    return v1.load_source(source, triage)


def second_pass(batch: str, prompt: dict, base: Path = HERE, prompt_version: str = rules.PROMPT_VERSION, into: Path | None = None, skip_reviewed: bool = False) -> int:
    """Pass 2: the items whose valid pass-1 review is a correction a second independent review must repeat (rules.needs_second_pass), for NEW workers (same item content).
    `into`: build the packets in another folder (packet ids and run ids then carry `-refolded`); `skip_reviewed`: leave out items that already have a valid pass-2 review (reviewer/AGENTS.md §quote rule)."""
    out = base / batch
    manifest = json.loads((out / "private" / "manifest.json").read_text(encoding="utf-8"))
    got = io.collect(out, "1", prompt_version)
    done = set(io.collect(out, "2", prompt_version)["reviews"]) if skip_reviewed and io.packets_dir(out, "2").is_dir() else set()
    chosen = []
    for i in got["ids"]:
        if i not in got["reviews"] or i in done:
            continue
        review, _ = got["reviews"][i]
        record = manifest["items"][i]
        has_correction = isinstance(review["corrected_reading"], dict)
        if rules.needs_second_pass(review["decision"], rules.correction_is(got["items"][i], review["corrected_reading"]), bool(record["agreed_empty"]), has_correction):
            chosen.append((got["items"][i], record))
    target = into or out
    if into is not None:
        (into / "private").mkdir(parents=True, exist_ok=True)
    name = manifest["batch"] + ("-refolded" if into is not None else "")
    doc = write_batch(target, chosen, name, prompt, f"pass 2 of {name}: {len(chosen)} reports whose first valid review was a correction" + (" and who have no second review yet" if skip_reviewed else ""), "2")
    print(f"pass 2: {len(chosen)} items, {len(doc['jobs'])} jobs ({len(got['problems'])} pass-1 items without a valid review are for --requeue)", file=sys.stderr)
    return 0


def requeue(batch: str, base: str, prompt: dict, root: Path = HERE, prompt_version: str = rules.PROMPT_VERSION) -> int:
    """A re-queue round: the items of pass `base` still without a valid review (invalid, missing, or a packet whose output is unusable), in fresh packets."""
    out = root / batch
    manifest = json.loads((out / ("private/manifest.json" if base == "1" else f"private/manifest-pass-{base}.json")).read_text(encoding="utf-8"))
    got = io.collect(out, base, prompt_version)
    label = io.next_requeue_label(out, base)
    chosen = [(got["items"][i], manifest["items"][i]) for i in got["ids"] if i not in got["reviews"]]
    if not chosen:
        print(f"nothing to re-queue for pass {base}", file=sys.stderr)
        return 0
    doc = write_batch(out, chosen, manifest["batch"], prompt, f"re-queue round {label} of {manifest['batch']}: {len(chosen)} items with no valid review in pass {base}", label)
    print(f"re-queue {label}: {len(chosen)} items, {len(doc['jobs'])} jobs", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--sets", action="store_true")
    mode.add_argument("--second-pass", action="store_true")
    mode.add_argument("--requeue", action="store_true")
    parser.add_argument("--batch", help="batch folder under reviewer/ (review-applied-b001, review-t01/held, ...)")
    parser.add_argument("--into", help="second pass only: build into this folder instead of the batch's own (relative to reviewer/)")
    parser.add_argument("--skip-reviewed", action="store_true", help="second pass only: leave out items that already have a valid pass-2 review")
    parser.add_argument("--pass", dest="base", default="1", help="the pass to re-queue (1 or 2)")
    args = parser.parse_args(argv)
    prompt = prompt_record()
    if args.sets:
        return sets(prompt)
    if not args.batch:
        parser.error("--batch is required")
    return second_pass(args.batch, prompt, into=HERE / args.into if args.into else None, skip_reviewed=args.skip_reviewed) if args.second_pass else requeue(args.batch, args.base, prompt)


if __name__ == "__main__":
    raise SystemExit(main())
