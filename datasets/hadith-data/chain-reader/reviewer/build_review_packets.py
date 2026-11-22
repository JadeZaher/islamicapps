"""Build chain-reviewer packets and jobs from a read batch: the report, its context, both readers' readings, the tool's holds in plain words and the stored chain (reviewer/README.md).

    python -B -X utf8 reviewer/build_review_packets.py --source tranches/tranche-02 --held    --batch t02-held-001   [--sample N --seed S] [--only ids.txt]
    python -B -X utf8 reviewer/build_review_packets.py --source tranches/tranche-02 --applied --batch t02-applied-001 [--sample N --seed S] [--only ids.txt]
    python -B -X utf8 reviewer/build_review_packets.py --pilot                       (reviewer/pilot-001: tranche 02's judged held and applied readings, with the judge's verdicts as a private key)
    python -B -X utf8 reviewer/build_review_packets.py --second-pass --batch <batch> (after pass 1: the reports whose first review was a correction, for a second independent review)
(from chain-reader/). `--source` is a directory with packets/, outputs/pass-a|b/ and private/reports.jsonl; the triage is <source>/triage-v3_3 (else triage-v3_2), for batch 001
(`--source v3/batch-001`) v3_3/batch-001/triage (else v3_2's); `--triage` overrides. `--held`: every report not eligible with at least one valid reading (agreed and held, the readers
differ, one reader valid); `--applied`: every eligible report (`--only` the ids actually applied, when known). `--sample N --seed S` draws N of them (random.Random(S)).
Writes <batch>/packets/packet-NN.json (`shura-chain-review-packet/1`, 10 items each, ids `cr1-xxxxxx`), <batch>/jobs.json (`shura-chain-review-jobs/1`: one Opus worker per packet, pass 1),
<batch>/private/{manifest.json, id_map.json}. Nothing a reviewer must not see (the original id, the work's tranche, a verdict, eligibility) is in a packet.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(ROOT / "v3_4"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
from expand_v3_4 import expand  # noqa: E402
from review_rules import JOBS_FORMAT, PACKET_FORMAT, REVIEWER_MODEL, plain  # noqa: E402
from validate import parse_output  # noqa: E402
from validate_review import validate_output  # noqa: E402
from validate_v3_4 import validate_chain  # noqa: E402

PER_PACKET = 10
PROMPT = HERE / "prompt-reviewer-v1.md"
JUDGE = ROOT / "tranches" / "tranche-02" / "judge-v3_2" / "analysis"
PILOT_SAMPLE_SEED = 20261601
PILOT_SAMPLE_SIZE = 30


def prompt_record() -> dict:
    """Path, version (front matter) and sha256 of the exact prompt bytes; written beside it as prompt-reviewer-v1.json."""
    data = PROMPT.read_bytes()
    version = next(line.split(":", 1)[1].strip() for line in data.decode("utf-8").splitlines() if line.startswith("version:"))
    record = {"specialist": "chain-reviewer", "file": PROMPT.name, "path": str(PROMPT), "repo_path": "datasets/hadith-data/chain-reader/reviewer/prompt-reviewer-v1.md", "version": version,
              "sha256": hashlib.sha256(data).hexdigest(), "chars": len(data.decode("utf-8")), "model": REVIEWER_MODEL}
    (HERE / "prompt-reviewer-v1.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return record


def triage_dir(source: Path) -> Path:
    candidates = [source / "triage-v3_3", source / "triage-v3_2"]
    if source.resolve() == (ROOT / "v3" / "batch-001").resolve():
        candidates = [ROOT / "v3_3" / "batch-001" / "triage", ROOT / "v3_2" / "batch-001" / "triage"]
    found = next((c for c in candidates if (c / "triage.tsv").is_file()), None)
    if found is None:
        raise SystemExit(f"no triage for {source}: run triage_v3_3 (or v3_2) first")
    return found


def load_source(source: Path, triage: Path | None) -> dict:
    packets = {}
    for path in sorted((source / "packets").glob("packet-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                packets[row["id"]] = row
    triage = triage or triage_dir(source)
    with (triage / "triage.tsv").open(encoding="utf-8", newline="") as handle:
        rows = {row["id"]: row for row in csv.DictReader(handle, delimiter="\t")}
    reports = {}
    for line in (source / "private" / "reports.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            reports[row["id"]] = row
    return {"source": source, "triage": triage, "packets": packets, "rows": rows, "reports": reports}


def reader_block(tag: str, output: dict | None, packet: dict) -> dict:
    """One reader as the reviewer sees it: the output's groups, the tool's routes (surface and kind), the variant groups with ids, notes and the flag."""
    if output is None:
        return {"valid": False, "problem": "no output"}
    errors = validate_chain(output, packet["text"], packet["id"], packet.get("context"))
    block = {"valid": not errors, "groups": output.get("groups"), "notes": output.get("notes"), "needs_ruling": output.get("needs_ruling")}
    if errors:
        block["problem"] = errors[0][:160]
        return block
    reading, _ = expand(output, packet["text"], packet.get("context"))
    block["routes"] = [{**({"saying": r["saying"]} if r.get("saying") else {}), "links": [{"surface": l["surface"], "kind": l["kind"], **({"from": l["from"]} if l.get("from") and l["kind"] == "inherited" else {})} for l in r["links"]]} for r in reading["routes"]]
    block["variant_groups"] = [{"group": f"{tag}.g{m['group']}", "names": m["surfaces"], "remark": m["quote"]} for m in reading.get("variant_remarks") or []]
    if reading.get("sayings"):
        block["sayings"] = [{"saying": s["saying"], "opens": s["opens"]} for s in reading["sayings"]]
    return block


def read_output(directory: Path, report_id: str) -> dict | None:
    path = directory / f"{report_id}.json"
    if not path.is_file():
        return None
    try:
        parsed, _ = parse_output(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    return parsed if isinstance(parsed, dict) else None


def build_item(opaque: str, report_id: str, data: dict) -> tuple[dict, dict]:
    """(packet item, private record)."""
    packet = dict(data["packets"][report_id], id=opaque)
    row = data["rows"].get(report_id) or {}
    outputs = {tag: read_output(data["source"] / "outputs" / f"pass-{tag.lower()}", report_id) for tag in ("A", "B")}
    for output in outputs.values():
        if output is not None:
            output["id"] = opaque                                     # the reader's id is the report's private id: the reviewer sees the opaque one
    readers = {tag: reader_block(tag, outputs[tag], packet) for tag in ("A", "B")}
    agree = row.get("agree") == "True"
    eligible = row.get("eligible") == "True"
    codes = [c for c in (row.get("holds") or "").split(",") if c]
    if not agree and readers["A"]["valid"] and readers["B"]["valid"]:
        codes.append("readers_differ")
    if readers["A"]["valid"] != readers["B"]["valid"]:
        codes.append("one_reader_invalid")
    if row.get("flag") in ("a_only", "b_only"):
        codes.append("flag_one_reader")
    report = data["reports"].get(report_id) or {}
    stored = [{"branch": chain.get("branch"), "surfaces": chain.get("surfaces")} for chain in report.get("stored_chains") or []]
    item = {"id": opaque, "text": packet["text"], "context": packet.get("context"), "status": "applied" if eligible else "held",
            "holds": [{"code": c, "plain": plain(c)} for c in codes], "readers": readers, "readers_agree": agree, "stored_chain": stored}
    agreed_empty = agree and readers["A"]["valid"] and not readers["A"].get("routes")
    private = {"source": str(data["source"].relative_to(ROOT).as_posix()), "id": report_id, "hadith_id": report.get("hadith_id"), "triage": data["triage"].relative_to(ROOT).as_posix(),
               "status": item["status"], "holds": codes, "readers_agree": agree, "agreed_empty": bool(agreed_empty), "applies": row.get("applies") or None}
    return item, private


def opaque_ids(keys: list[str], salt: str) -> dict[str, str]:
    result, seen = {}, set()
    for key in sorted(keys):
        digest = hashlib.sha256(f"{salt}:{key}".encode()).hexdigest()
        length = 6
        while "cr1-" + digest[:length] in seen:
            length += 1
        result[key] = "cr1-" + digest[:length]
        seen.add(result[key])
    return result


def instruction(prompt: dict, packet_path: str, output_path: str, run_file: str, run_id: str, packet_number: str) -> str:
    """The orchestrator's whole message to one reviewer worker (reviews/ai/README.md §Isolation)."""
    return ("You are the chain reviewer. Your instructions are the file\n"
            f"  {prompt['path']}\n"
            f"(version {prompt['version']}, sha256 {prompt['sha256']}). Read all of it before you start.\n\n"
            f"Your input is ONE packet file:\n  {packet_path}\n"
            "Read only this file and your instructions: no other packet, no output of another review, nothing under the batch's private folder, no database, no web, no memory of other work.\n\n"
            f"Write exactly the JSON object your instructions define (no fence, no commentary) to\n  {output_path}\n"
            "Review every item of the packet yourself; do not write a program that produces the reviews.\n\n"
            f"Then append ONE line to\n  {run_file}\n"
            "exactly in this form (UTC times like 2026-11-23T09:00:00Z; the model id is the exact id your runtime reports; take the start time before you read the packet):\n"
            f"  run_id={run_id} | packet={packet_number} | model=<model id> | start=<UTC start> | end=<UTC end> | items=<number of reviews you wrote>\n"
            "Then answer with the number of reviews only.")


def write_batch(out: Path, items: list[tuple[dict, dict]], batch: str, prompt: dict, label: str, extra_private: dict | None = None, pass_number: int = 1) -> dict:
    """Packets (10 items), jobs and the private manifest of one pass."""
    packets_dir = out / ("packets" if pass_number == 1 else f"packets-pass-{pass_number}")
    packets_dir.mkdir(parents=True, exist_ok=True)
    for old in packets_dir.glob("packet-*.json"):
        old.unlink()
    chunks = [items[i:i + PER_PACKET] for i in range(0, len(items), PER_PACKET)]
    jobs = []
    for n, chunk in enumerate(chunks, start=1):
        number = f"{n:02d}"
        packet_id = f"{batch}-p{pass_number}-{number}"
        body = {"format": PACKET_FORMAT, "packet_id": packet_id, "batch": batch, "pass": pass_number, "items": [item for item, _ in chunk]}
        path = packets_dir / f"packet-{number}.json"
        text = json.dumps(body, ensure_ascii=False, indent=1) + "\n"
        path.write_text(text, encoding="utf-8", newline="\n")
        output_dir = out / "outputs" / f"pass-{pass_number}"
        run_id = f"{batch}-review-p{pass_number}-{number}"
        message = instruction(prompt, str(path), str(output_dir / f"packet-{number}.output.json"), str(output_dir / "RUN.txt"), run_id, number)
        jobs.append({"job_id": run_id, "pass": pass_number, "packet": number, "packet_file": str(path), "packet_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                     "output_file": str(output_dir / f"packet-{number}.output.json"), "run_file": str(output_dir / "RUN.txt"), "run_id": run_id, "items": len(chunk),
                     "input_chars": len(message) + prompt["chars"] + len(text), "instruction": message})
    jobs_doc = {"format": JOBS_FORMAT, "batch": batch, "pass": pass_number, "what": label, "prompt": {"path": prompt["path"], "version": prompt["version"], "sha256": prompt["sha256"]},
                "model": f"{REVIEWER_MODEL} for every job; one fresh worker per packet, nothing shared between workers (reviews/ai/README.md §Isolation)",
                "run_line_format": "run_id={RUNID} | packet={NN} | model=<model id> | start=<UTC start> | end=<UTC end> | items=<number of reviews>",
                "output_file_format": "one JSON object per packet (shura-chain-review-output/1), exactly as the prompt describes, at output_file",
                "after": ("validate each output: python -B -X utf8 reviewer/validate_review.py --packet <packet_file> --output <output_file>; then build pass 2: "
                          f"python -B -X utf8 reviewer/build_review_packets.py --second-pass --batch {batch}" if pass_number == 1 else
                          "validate each output; a correction (or a no-chain verdict against a reading with routes) is applied only where pass 2 gives the same routes (reviewer/README.md)"),
                "second_pass_rule": "pass 2 re-reviews, with a new worker, only the reports whose pass-1 decision is confirm_with_correction, or no_chain where the readers' reading has routes",
                "expected": {"jobs": len(jobs), "items": len(items), "run_txt_lines": len(jobs)}, "jobs": jobs}
    name = "jobs.json" if pass_number == 1 else f"jobs-pass-{pass_number}.json"
    (out / name).write_text(json.dumps(jobs_doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    private = out / "private"
    private.mkdir(parents=True, exist_ok=True)
    manifest = {"batch": batch, "pass": pass_number, "what": label, "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "prompt": jobs_doc["prompt"],
                "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "items": {item["id"]: record for item, record in items}, **(extra_private or {})}
    (private / ("manifest.json" if pass_number == 1 else f"manifest-pass-{pass_number}.json")).write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    return jobs_doc


def shuffled(items: list[tuple[dict, dict]], salt: str) -> list[tuple[dict, dict]]:
    return sorted(items, key=lambda pair: hashlib.md5(f"{salt}:{pair[0]['id']}".encode()).hexdigest())


def salt_for(out: Path) -> str:
    path = out / "private" / "id_map.json"
    return json.loads(path.read_text(encoding="utf-8"))["salt"] if path.is_file() else secrets.token_hex(16)


def write_id_map(out: Path, salt: str, mapping: dict[str, str]) -> None:
    (out / "private").mkdir(parents=True, exist_ok=True)
    (out / "private" / "id_map.json").write_text(json.dumps({"salt": salt, "ids": {v: k for k, v in mapping.items()}}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")


def tsv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def pilot(prompt: dict) -> int:
    """reviewer/pilot-001: tranche 02's agreed readings the judge read while they were held (21 shape holds, 30 variant), plus 30 of the judge's eligible sample (seed 20261601)."""
    data = load_source(ROOT / "tranches" / "tranche-02", None)
    holds, variants, sample = tsv(JUDGE / "hold_verdicts.tsv"), tsv(JUDGE / "variant_verdicts.tsv"), tsv(JUDGE / "sample_verdicts.tsv")
    key: dict[str, dict] = {}
    for row in holds:
        key[row["id"]] = {"set": "shape_hold", "judge_reader": row["reader"], "judge_group": "", "judge_quote": row["quote"], "holds_when_judged": row["holds"]}
    for row in variants:
        entry = key.setdefault(row["id"], {"set": "variant_hold", "judge_reader": row["reading_without_group"], "judge_group": "", "judge_quote": row["quote"], "holds_when_judged": "has_variant_group"})
        if entry["set"] != "variant_hold":
            entry["set"] += "+variant_hold"
        entry["judge_group"] = row["group_is"]
    eligible = sorted(row["id"] for row in sample if row["id"] not in key)
    drawn = random.Random(PILOT_SAMPLE_SEED).sample(eligible, PILOT_SAMPLE_SIZE)
    for report_id in drawn:
        row = next(r for r in sample if r["id"] == report_id)
        key[report_id] = {"set": "eligible_sample", "judge_reader": row["reader"], "judge_group": "", "judge_quote": row["quote"], "holds_when_judged": ""}
    missing = sorted(i for i in key if i not in data["packets"])
    assert not missing, f"judged ids not in tranche 02's packets: {missing}"
    out = HERE / "pilot-001"
    salt = salt_for(out)
    mapping = opaque_ids(list(key), salt)
    items = shuffled([build_item(mapping[report_id], report_id, data) for report_id in key], salt)
    for item, record in items:
        record.update(key[record["id"]])
    write_id_map(out, salt, mapping)
    label = ("pilot: tranche 02's agreed readings the judge read while held (hold_verdicts.tsv 21, variant_verdicts.tsv 30) and a random 30 of the judge's eligible sample "
             f"(sample_verdicts.tsv, seed {PILOT_SAMPLE_SEED}); scored against the judge by pilot-001/score_reviewer.py")
    jobs = write_batch(out, items, "pilot-001", prompt, label, {"pilot_sample_seed": PILOT_SAMPLE_SEED})
    lines = ["opaque\tid\tset\tstatus\tjudge_reader\tjudge_group\tholds_now\tholds_when_judged\tjudge_quote"]
    for item, record in sorted(items, key=lambda pair: pair[1]["id"]):
        lines.append("\t".join([item["id"], record["id"], record["set"], record["status"], record["judge_reader"], record["judge_group"], ",".join(record["holds"]), record["holds_when_judged"], record["judge_quote"].replace("\t", " ")]))
    (out / "private" / "key.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    sets = {name: sum(1 for _, r in items if r["set"] == name) for name in sorted({r["set"] for _, r in items})}
    verdicts = {name: sum(1 for _, r in items if r["judge_reader"] == name) for name in sorted({r["judge_reader"] for _, r in items})}
    print(json.dumps({"items": len(items), "sets": sets, "judge_reader": verdicts, "status": {s: sum(1 for i, _ in items if i["status"] == s) for s in ("held", "applied")}, "jobs": len(jobs["jobs"])}, ensure_ascii=False))
    return 0


def second_pass(batch: str, prompt: dict) -> int:
    """Pass 2: the items whose valid pass-1 review is a correction, or no_chain against a reading with routes, re-reviewed by new workers (same item content)."""
    out = HERE / batch
    manifest = json.loads((out / "private" / "manifest.json").read_text(encoding="utf-8"))
    chosen, problems = [], []
    for packet_path in sorted((out / "packets").glob("packet-*.json")):
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        output_path = out / "outputs" / "pass-1" / packet_path.name.replace(".json", ".output.json")
        if not output_path.is_file():
            problems.append(f"{packet_path.name}: no pass-1 output")
            continue
        output = json.loads(output_path.read_text(encoding="utf-8"))
        errors = validate_output(output, packet, prompt["version"])
        if errors:
            problems.append(f"{packet_path.name}: invalid pass-1 output ({errors[0]})")
            continue
        items = {item["id"]: item for item in packet["items"]}
        for review in output["reviews"]:
            record = manifest["items"][review["id"]]
            if review["decision"] == "confirm_with_correction" or (review["decision"] == "no_chain" and not record["agreed_empty"]):
                chosen.append((items[review["id"]], record))
    for problem in problems:
        print("SKIP", problem, file=sys.stderr)
    jobs = write_batch(out, chosen, batch, prompt, f"pass 2 of {batch}: {len(chosen)} reports whose first review was a correction", pass_number=2)
    print(f"pass 2: {len(chosen)} items, {len(jobs['jobs'])} jobs ({len(problems)} packets skipped)", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--held", action="store_true")
    mode.add_argument("--applied", action="store_true")
    mode.add_argument("--pilot", action="store_true")
    mode.add_argument("--second-pass", action="store_true")
    parser.add_argument("--source", help="a tranche directory (tranches/tranche-02) or v3/batch-001")
    parser.add_argument("--triage", help="the triage directory (default: v3.3's, else v3.2's)")
    parser.add_argument("--batch", help="output folder name under reviewer/")
    parser.add_argument("--only", help="ids file: keep only these reports (e.g. the readings actually applied)")
    parser.add_argument("--sample", type=int)
    parser.add_argument("--seed", type=int)
    args = parser.parse_args(argv)
    prompt = prompt_record()
    if args.pilot:
        return pilot(prompt)
    if not args.batch:
        parser.error("--batch is required")
    if args.second_pass:
        return second_pass(args.batch, prompt)
    if not args.source:
        parser.error("--source is required with --held / --applied")
    if (args.sample is None) != (args.seed is None):
        parser.error("--sample and --seed go together")
    data = load_source(ROOT / args.source, ROOT / args.triage if args.triage else None)
    only = {line.strip() for line in Path(args.only).read_text(encoding="utf-8").splitlines() if line.strip()} if args.only else None
    chosen = []
    for report_id, row in data["rows"].items():
        if only is not None and report_id not in only:
            continue
        eligible = row.get("eligible") == "True"
        if args.applied and eligible or args.held and not eligible and (row.get("valid_a") == "True" or row.get("valid_b") == "True"):
            chosen.append(report_id)
    if args.sample is not None:
        chosen = random.Random(args.seed).sample(sorted(chosen), min(args.sample, len(chosen)))
    out = HERE / args.batch
    salt = salt_for(out)
    mapping = opaque_ids(chosen, salt)
    items = shuffled([build_item(mapping[report_id], report_id, data) for report_id in chosen], salt)
    write_id_map(out, salt, mapping)
    label = f"{'held' if args.held else 'applied'} readings of {args.source}" + (f", a random {args.sample} (seed {args.seed})" if args.sample is not None else "")
    jobs = write_batch(out, items, args.batch, prompt, label, {"source": args.source, "sample": args.sample, "seed": args.seed})
    print(f"{len(items)} items, {len(jobs['jobs'])} jobs -> {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
