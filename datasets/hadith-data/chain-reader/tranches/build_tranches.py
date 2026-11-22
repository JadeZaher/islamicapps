"""Cut the live uncertain population of the three judged groups into tranches, build each tranche's packets with the v3.1 builder, and write the manifests and jobs.

    python -B -X utf8 tranches/build_tranches.py [--seed 20261123] [--target 1000] [--packet-size 20] [--plan-only]     (from chain-reader/; needs .env.local at the repository root)

Population: reports with at least one non-retired chain with structure_status = 'uncertain' (read-only production) in the six Sunni books, Man la Yahduruhu al-Faqih and the other Imami works
except al-Kafi. Batch 001's 500 are excluded except the reports in v3_1/batch-001/reread_under_v3_1.txt, which are forced into tranche 01.
Tranches (see tranches/AGENTS.md): T = round(N / target) tranches of whole packets, stratified by work with a largest-deficit deal over the work-sorted list, so every tranche mirrors the population
within one report per work; order inside a tranche is shuffled (packets mix works). Opaque ids `tNN-` + six hex of a salted hash, unique across tranches.
Per tranche: packets/ (what a reader gets), private/ (id_map.json, sample.json, reports.jsonl: never given to a reader), manifest.json, jobs.json, outputs/pass-a|pass-b/ (empty).
The dataset version is read before and after the build; if it changed the build is repeated (up to three times) and the manifest records both reads.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                                   # chain-reader/
V31 = ROOT / "v3_1"
REPO = ROOT.parents[2]
SIX_BOOKS = ("sunni:bukhari", "sunni:muslim", "sunni:nasai", "sunni:tirmidhi", "sunni:abudawud", "sunni:ibnmajah")
FAQIH = "imami:man-la-yahduruhu-al-faqih"
NOT_OTHER_IMAMI = ("imami:al-kafi", FAQIH)
MODEL_TIER = "claude-haiku-5-5"
PROMPT = V31 / "prompt-v3_1.md"
CHARS_PER_TOKEN = (2.5, 3.0)                         # diacritised Arabic with JSON (v3/README.md section 5)


def group_of(work: str) -> str | None:
    if work in SIX_BOOKS:
        return "sunni_six_books"
    if work == FAQIH:
        return "imami_faqih"
    if work.startswith("imami:") and work not in NOT_OTHER_IMAMI:
        return "imami_other_not_kafi"
    return None


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def node(args: list[str]) -> str:
    """Run a node script from the repository root with .env.local (read-only queries; DATABASE_URL_PRODUCTION is never printed)."""
    result = subprocess.run(["node", "--env-file=.env.local", *args], cwd=REPO, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise SystemExit(f"node {args[0]} failed:\n{result.stderr[-1500:]}")
    return result.stdout.strip().splitlines()[-1]


def dataset_version() -> dict:
    return json.loads(node([str(V31 / "draw_population_v3_1.cjs"), "--version-only"]))["dataset_version"]


def plan_tranches(population: list[dict], forced: set[str], excluded: set[str], seed: int, target: int, packet_size: int) -> tuple[list[list[dict]], dict]:
    """Assign every report to a tranche: forced reports to tranche 1, the rest by a largest-deficit deal over the list sorted by (work, random key)."""
    pool = [r for r in population if group_of(r["work"]) and (r["hadith_id"] not in excluded or r["hadith_id"] in forced)]
    total = len(pool)
    tranche_count = max(1, round(total / target))
    packets = math.ceil(total / packet_size)
    packets_per = [packets // tranche_count + (1 if t < packets % tranche_count else 0) for t in range(tranche_count)]
    capacity = [p * packet_size for p in packets_per]
    capacity[-1] -= sum(capacity) - total                 # the last tranche takes the short packet
    rng = random.Random(seed)
    keyed = sorted(pool, key=lambda r: (r["work"], r["hadith_id"]))
    keys = {r["hadith_id"]: rng.random() for r in keyed}
    ordered = sorted(keyed, key=lambda r: (r["work"], keys[r["hadith_id"]]))
    counts = [0] * tranche_count
    tranches: list[list[dict]] = [[] for _ in range(tranche_count)]
    for position, row in enumerate(ordered, start=1):
        if row["hadith_id"] in forced:
            chosen = 0
        else:
            deficits = [(capacity[t] * position / total - counts[t]) if counts[t] < capacity[t] else -1e9 for t in range(tranche_count)]
            chosen = max(range(tranche_count), key=lambda t: (deficits[t], -t))
        counts[chosen] += 1
        tranches[chosen].append(row)
    for t, rows in enumerate(tranches):
        rng.shuffle(rows)                                 # packets mix works; position tells nothing
    plan = {"reports": total, "tranches": tranche_count, "packets": packets, "packets_per_tranche": packets_per, "capacity": capacity, "sizes": [len(r) for r in tranches]}
    return tranches, plan


def opaque_ids(tranches: list[list[dict]], seed: int) -> tuple[str, list[list[tuple[str, dict]]]]:
    salt = hashlib.sha256(f"tranches-{seed}".encode()).hexdigest()[:32]
    seen: set[str] = set()
    result: list[list[tuple[str, dict]]] = []
    for t, rows in enumerate(tranches, start=1):
        named = []
        for row in rows:
            digest = hashlib.sha256((salt + row["hadith_id"]).encode()).hexdigest()
            length = 6
            while f"t{t:02d}-" + digest[:length] in seen:      # a 6-hex collision inside a tranche: this report's id takes the next hex digit
                length += 1
            opaque = f"t{t:02d}-" + digest[:length]
            seen.add(opaque)
            named.append((opaque, row))
        result.append(named)
    return salt, result


def instruction(prompt: dict, packet_paths: list[str], output_dir: str, run_file: str, run_id: str, packet_numbers: list[str]) -> str:
    """The reader instruction of v3/batch-001/RUN.md section 1 for this job, placeholders filled (the whole task text, nothing else)."""
    inputs = "two packet files" if len(packet_paths) == 2 else "one packet file"
    files = "\n".join(f"  {p}" for p in packet_paths)
    return (
        "You are a chain reader. Your instructions are the file\n"
        f"  {prompt['path']}\n"
        f"(version {prompt['version']}, sha256 {prompt['sha256']}). Read all of it before you start.\n\n"
        f"Your input is {inputs}, JSON lines, each line {{\"id\", \"text\", \"context\"}}:\n{files}\n\n"
        "For EVERY line write one file named after that line's id:\n"
        f"  {output_dir}\\<id>.json\n"
        "holding exactly the JSON object the prompt describes for that report: no markdown fence, no commentary, no other keys. Read each report yourself, from its text and its context;\n"
        "do not write a program that produces the readings. Never skip an id: a report you cannot read still gets its file (status, groups and notes as the prompt says).\n\n"
        "Read nothing else: not the other pass's outputs, nothing under the tranche's private folder, no other packet, no database, no web. Do not edit any packet or any file but your own outputs.\n\n"
        "When every file is written, append ONE line to\n"
        f"  {run_file}\n"
        "exactly in this form (UTC times like 2026-11-23T09:00:00Z; the model id is the exact id your runtime reports; take the start time before you read the first packet):\n"
        f"  run_id={run_id} | packets={','.join(packet_numbers)} | model=<model id> | start=<UTC start> | end=<UTC end> | files=<number of files you wrote>\n"
        "Then answer with the number of files only."
    )


def pairings(packet_count: int) -> dict[str, list[list[str]]]:
    """Pass A: (1,2) (3,4) ...; pass B shifted by one: (1) (2,3) (4,5) ... so no agent reads the same pair twice."""
    numbers = [f"{n:03d}" for n in range(1, packet_count + 1)]
    pass_a = [numbers[i:i + 2] for i in range(0, packet_count, 2)]
    pass_b = [numbers[:1]] + [numbers[i:i + 2] for i in range(1, packet_count, 2)]
    return {"a": pass_a, "b": pass_b}


def packet_stats(directory: Path) -> dict:
    """Bytes, characters and context coverage of a tranche's packets, from the packet files themselves."""
    per_packet, chars_text, chars_context, kinds = {}, 0, 0, Counter()
    previous = Counter()
    for path in sorted(directory.glob("packet-*.jsonl")):
        text_chars = context_chars = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            context = row.get("context") or {}
            text_chars += len(row["text"])
            context_chars += len(json.dumps(context, ensure_ascii=False))
            for key in context:
                if key not in ("work", "omitted_for_size"):
                    kinds[key] += 1
            for item in context.get("previous_reports") or []:
                if item.get("has_written_chain"):
                    previous["supplied_" + (item.get("supplies") or "chain")] += 1
            if context.get("previous_reports"):
                previous["reports_with_previous_reports"] += 1
        per_packet[path.name] = {"bytes": path.stat().st_size, "text_chars": text_chars, "context_chars": context_chars, "line_chars": len(path.read_text(encoding="utf-8"))}
        chars_text += text_chars
        chars_context += context_chars
    return {"per_packet": per_packet, "text_chars": chars_text, "context_chars": chars_context, "packet_bytes": sum(p["bytes"] for p in per_packet.values()),
            "packet_line_chars": sum(p["line_chars"] for p in per_packet.values()), "context_coverage": dict(kinds), "previous_reports": dict(previous)}


def build(args: argparse.Namespace) -> dict:
    out_root = HERE
    private_root = out_root / "private"
    private_root.mkdir(exist_ok=True)
    version_before = dataset_version()
    population_file = private_root / "population.jsonl"
    drawn = json.loads(node([str(V31 / "draw_population_v3_1.cjs"), "--out", str(population_file)]))
    population = [json.loads(line) for line in population_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    b1_ids = json.loads((ROOT / "v3" / "batch-001" / "private" / "id_map.json").read_text(encoding="utf-8"))["ids"]
    reread_short = [line.strip() for line in (V31 / "batch-001" / "reread_under_v3_1.txt").read_text(encoding="utf-8").splitlines() if line.strip()]
    excluded = {entry["hadith_id"] for entry in b1_ids.values()}
    forced_rows = {b1_ids[i]["hadith_id"]: b1_ids[i] for i in reread_short}
    in_population = {r["hadith_id"] for r in population}
    forced = set(forced_rows)
    for hadith_id, entry in forced_rows.items():            # a re-read report that is no longer 'uncertain' still goes into tranche 01
        if hadith_id not in in_population:
            population.append({"hadith_id": hadith_id, "work": entry["work"], "uncertain_chains": 0, "reader_chars": 0, "opening": entry.get("opening")})
    tranches, plan = plan_tranches(population, forced, excluded, args.seed, args.target, args.packet_size)
    plan["reread_forced_into_tranche_01"] = len(forced)
    plan["reread_not_in_population"] = sorted(h for h in forced if h not in in_population)
    plan["batch_001_excluded"] = len(excluded)
    plan["population_live_uncertain"] = len(in_population)
    plan["population_in_scope_before_exclusion"] = sum(1 for r in population if group_of(r["work"]))
    if args.plan_only:
        return {"plan": plan, "version_before": version_before, "population": drawn}
    salt, named = opaque_ids(tranches, args.seed)
    for old in HERE.glob("tranche-*"):
        if old.is_dir():
            shutil.rmtree(old)
    stats = {}
    for t, rows in enumerate(named, start=1):
        tdir = out_root / f"tranche-{t:02d}"
        (tdir / "private").mkdir(parents=True)
        (tdir / "outputs" / "pass-a").mkdir(parents=True)
        (tdir / "outputs" / "pass-b").mkdir(parents=True)
        sample = [{"id": opaque, "hadith_id": row["hadith_id"]} for opaque, row in rows]
        (tdir / "private" / "sample.json").write_text(json.dumps(sample, ensure_ascii=False, indent=0) + "\n", encoding="utf-8", newline="\n")
        id_map = {opaque: {"hadith_id": row["hadith_id"], "work": row["work"], "stratum": group_of(row["work"]), "opening": row.get("opening"), "reread_batch_001": row["hadith_id"] in forced} for opaque, row in rows}
        (tdir / "private" / "id_map.json").write_text(json.dumps({"salt": salt, "seed": args.seed, "ids": id_map}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        summary = node([str(V31 / "build_context_v3_1.cjs"), "--sample", str(tdir / "private" / "sample.json"), "--out-dir", str(tdir / "packets"), "--packet-size", str(args.packet_size),
                        "--reports-out", str(tdir / "private" / "reports.jsonl")])
        stats[t] = json.loads(summary)
        print(f"tranche {t:02d}: {len(rows)} reports, {stats[t]['packets']} packets, context median {stats[t]['median']} p95 {stats[t]['p95']}", file=sys.stderr)
    version_after = dataset_version()
    return {"plan": plan, "version_before": version_before, "version_after": version_after, "population": drawn, "named": named, "builder": stats, "salt_sha256": hashlib.sha256(salt.encode()).hexdigest()}


def write_tranche_files(result: dict, args: argparse.Namespace) -> dict:
    prompt_record = json.loads((V31 / "prompt-v3_1.json").read_text(encoding="utf-8"))
    prompt = {"path": str(PROMPT), "version": prompt_record["version"], "sha256": prompt_record["sha256"]}
    assert hashlib.sha256(PROMPT.read_bytes()).hexdigest() == prompt["sha256"], "prompt-v3_1.md does not match prompt-v3_1.json: rebuild it (v3_1/tools/make_prompt_v3_1.py)"
    prompt_chars = len(PROMPT.read_text(encoding="utf-8"))
    summary = {"tranches": []}
    for t, rows in enumerate(result["named"], start=1):
        tdir = HERE / f"tranche-{t:02d}"
        packets = tdir / "packets"
        stats = packet_stats(packets)
        builder_manifest = json.loads((packets / "manifest.json").read_text(encoding="utf-8"))
        forced_ids = set(result.get("forced", []))
        works = Counter(row["work"] for _, row in rows)
        groups = Counter(group_of(row["work"]) for _, row in rows)
        packet_count = builder_manifest["packets"]
        jobs = []
        for label, pairs in pairings(packet_count).items():
            for pair in pairs:
                run_id = f"t{t:02d}-{label}-" + "-".join(pair)
                files = [str(packets / f"packet-{n}.jsonl") for n in pair]
                output_dir, run_file = str(tdir / "outputs" / f"pass-{label}"), str(tdir / "outputs" / f"pass-{label}" / "RUN.txt")
                ids = [json.loads(line)["id"] for f in files for line in Path(f).read_text(encoding="utf-8").splitlines() if line.strip()]
                text = instruction(prompt, files, output_dir, run_file, run_id, pair)
                packet_chars = sum(stats["per_packet"][f"packet-{n}.jsonl"]["line_chars"] for n in pair)
                jobs.append({"job_id": run_id, "pass": label, "packets": pair, "packet_files": files, "output_dir": output_dir, "output_files": [f"{i}.json" for i in ids], "run_file": run_file, "run_id": run_id,
                             "expected_files": len(ids), "input_chars": len(text) + prompt_chars + packet_chars, "instruction": text})
        expected_pass = sum(j["expected_files"] for j in jobs if j["pass"] == "a")
        jobs_doc = {"format": "shura-chain-reader-jobs/1", "tranche": f"{t:02d}", "prompt": prompt, "model_tier": f"{MODEL_TIER} for every job of the whole run; pass A and pass B use the same tier and different agents (v3/batch-001/RUN.md)",
                    "run_line_format": "run_id={RUNID} | packets={P1},{P2} | model=<model id> | start=<UTC start> | end=<UTC end> | files=<number of files you wrote>",
                    "output_file_format": "one <id>.json per packet line, exactly the JSON object the prompt describes (no fence, no commentary), in output_dir",
                    "expected": {"jobs": len(jobs), "jobs_per_pass": len(jobs) // 2, "files_per_pass": expected_pass, "run_txt_lines_per_pass": len([j for j in jobs if j["pass"] == "a"])}, "jobs": jobs}
        (tdir / "jobs.json").write_text(json.dumps(jobs_doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        covered = {k: v for k, v in stats["context_coverage"].items()}
        manifest = {"format": "shura-chain-tranche-manifest/1", "tranche": f"{t:02d}", "built_at_utc": builder_manifest["built_at_utc"], "reports": len(rows), "packets": packet_count, "packet_size": args.packet_size,
                    "counts_by_work": dict(sorted(works.items())), "counts_by_group": dict(sorted(groups.items())), "reread_batch_001": sum(1 for _, row in rows if row["hadith_id"] in forced_ids),
                    "context_coverage": {"reports": len(rows), "reports_with_kind": covered, "share": {k: round(v / len(rows), 3) for k, v in covered.items()}, "previous_reports": stats["previous_reports"],
                                         "omitted_for_size": builder_manifest.get("omitted_for_size"), "builder_previous_reports": builder_manifest.get("previous_reports")},
                    "bytes": {"packets_total": stats["packet_bytes"], "per_packet": {k: v["bytes"] for k, v in stats["per_packet"].items()}},
                    "chars": {"text": stats["text_chars"], "context": stats["context_chars"], "packet_lines": stats["packet_line_chars"], "context_median": builder_manifest["context_chars"]["median"],
                              "context_p95": builder_manifest["context_chars"]["p95"], "context_max": builder_manifest["context_chars"]["max"]},
                    "dataset_version": {"at_population_draw": result["version_before"], "at_packet_build": builder_manifest["inputs"].get("production_dataset_version"), "after_build": result["version_after"]},
                    "not_found_in_production": builder_manifest.get("not_found_in_production"), "prompt": {"version": prompt["version"], "sha256": prompt["sha256"]},
                    "inputs": {k: builder_manifest["inputs"][k] for k in ("work_profiles_sha256", "builder_sha256", "backref_lib_sha256", "sidecars", "external_databases")},
                    "jobs": {"count": len(jobs), "per_pass": len(jobs) // 2, "files_per_pass": expected_pass}}
        (tdir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        summary["tranches"].append({"tranche": f"{t:02d}", "reports": len(rows), "packets": packet_count, "jobs": len(jobs), "packet_bytes": stats["packet_bytes"], "text_chars": stats["text_chars"],
                                    "context_chars": stats["context_chars"], "packet_line_chars": stats["packet_line_chars"], "job_input_chars": sum(j["input_chars"] for j in jobs), "job_input_chars_list": [j["input_chars"] for j in jobs], "by_group": dict(groups),
                                    "by_work": dict(works)})
    return summary


def sizing(summary: dict, result: dict) -> dict:
    """Population per group, tranche count, jobs per tranche, characters per job and the expected token load (both passes; input = prompt + packets + instruction per job; output measured on batch 001)."""
    outputs = [p.stat().st_size for p in (ROOT / "v3" / "batch-001" / "outputs" / "pass-a").glob("b1-*.json")]
    out_chars = [len(p.read_text(encoding="utf-8")) for p in (ROOT / "v3" / "batch-001" / "outputs" / "pass-a").glob("b1-*.json")]
    reports = sum(t["reports"] for t in summary["tranches"])
    jobs = sum(t["jobs"] for t in summary["tranches"])
    per_pass_input = sum(t["job_input_chars"] for t in summary["tranches"]) / 2
    output_chars_per_pass = reports * (sum(out_chars) / max(1, len(out_chars)))
    total_chars_in, total_chars_out = 2 * per_pass_input, 2 * output_chars_per_pass
    job_chars = [c for t in summary["tranches"] for c in t["job_input_chars_list"]]
    by_group = Counter()
    for t in summary["tranches"]:
        by_group.update(t["by_group"])
    return {"reports": reports, "population_by_group": dict(by_group), "tranches": len(summary["tranches"]), "jobs_total": jobs, "jobs_per_tranche": [t["jobs"] for t in summary["tranches"]],
            "characters_per_job": {"mean": round(sum(job_chars) / len(job_chars)), "min": round(min(job_chars)), "max": round(max(job_chars))},
            "prompt_chars": len(PROMPT.read_text(encoding="utf-8")), "packet_bytes_total": sum(t["packet_bytes"] for t in summary["tranches"]), "input_chars_per_pass": round(per_pass_input), "input_chars_two_passes": round(total_chars_in),
            "output_chars_per_report_batch_001_pass_a": round(sum(out_chars) / max(1, len(out_chars))), "output_chars_two_passes": round(total_chars_out),
            "tokens_two_passes": {"input": [round(total_chars_in / CHARS_PER_TOKEN[1]), round(total_chars_in / CHARS_PER_TOKEN[0])], "output": [round(total_chars_out / CHARS_PER_TOKEN[1]), round(total_chars_out / CHARS_PER_TOKEN[0])]},
            "assumption": "2.5 to 3 characters per token for diacritised Arabic with JSON; every job reads the whole prompt once; the output is the reading JSON measured on batch 001's pass A (chars per report)"}


def write_run_md(summary: dict, manifest: dict) -> None:
    """tranches/RUN.md from run_template.md: the commands and a table of the tranches just built."""
    retriage = json.loads((V31 / "batch-001" / "retriage.json").read_text(encoding="utf-8"))
    after = retriage["right_rate_among_eligible_judged"]["after_v3_1_tool"]["overall_unweighted"]
    rows = ["| tranche | reports | packets | jobs (A + B) | files per pass | six Sunni books | al-Faqih | other Imami | packet bytes |", "|---|---|---|---|---|---|---|---|---|"]
    for t in summary["tranches"]:
        g = t["by_group"]
        rows.append(f"| {t['tranche']} | {t['reports']} | {t['packets']} | {t['jobs']} | {t['reports']} | {g.get('sunni_six_books', 0)} | {g.get('imami_faqih', 0)} | {g.get('imami_other_not_kafi', 0)} | {t['packet_bytes']:,} |")
    text = (HERE / "run_template.md").read_text(encoding="utf-8")
    for key, value in {"__TRANCHE_COUNT__": str(len(summary["tranches"])), "__REPORTS__": f"{sum(t['reports'] for t in summary['tranches']):,}", "__PROMPT_SHA__": manifest["prompt"], "__MODEL__": MODEL_TIER,
                       "__REREAD__": str(retriage["reread_under_v3_1"]), "__ELIGIBLE_TO_APPLY__": str(retriage["eligible_to_apply"]), "__RATE__": after["rate"], "__TABLE__": chr(10).join(rows)}.items():
        text = text.replace(key, value)
    (HERE / "RUN.md").write_text(text, encoding="utf-8", newline=chr(10))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=20261123)
    parser.add_argument("--target", type=int, default=1000)
    parser.add_argument("--packet-size", type=int, default=20)
    parser.add_argument("--plan-only", action="store_true", help="draw the population and print the plan; build nothing")
    args = parser.parse_args(argv)
    result: dict = {}
    for attempt in range(1, 4):
        result = build(args)
        if args.plan_only:
            print(json.dumps(result, ensure_ascii=False, indent=1))
            return 0
        if result["version_before"] == result["version_after"]:
            break
        print(f"dataset version changed during the build (attempt {attempt}): {result['version_before']} -> {result['version_after']}; rebuilding", file=sys.stderr)
    else:
        raise SystemExit("the dataset version kept changing during the build; stop the load or build later")
    first = json.loads((HERE / "tranche-01" / "private" / "id_map.json").read_text(encoding="utf-8"))["ids"]
    result["forced"] = sorted(v["hadith_id"] for v in first.values() if v["reread_batch_001"])
    summary = write_tranche_files(result, args)
    size = sizing(summary, result)
    manifest = {"format": "shura-chain-tranches-manifest/1", "built_at_utc": utc_now(), "seed": args.seed, "target_reports_per_tranche": args.target, "packet_size": args.packet_size, "plan": result["plan"],
                "dataset_version": {"before_draw": result["version_before"], "after_build": result["version_after"], "unchanged": result["version_before"] == result["version_after"]},
                "population_file_sha256": hashlib.sha256((HERE / "private" / "population.jsonl").read_bytes()).hexdigest(), "prompt": json.loads((V31 / "prompt-v3_1.json").read_text(encoding="utf-8"))["sha256"],
                "tranches": summary["tranches"], "sizing": size}
    (HERE / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    write_run_md(summary, manifest)
    (HERE / "sizing.json").write_text(json.dumps(size, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"plan": result["plan"], "version": manifest["dataset_version"], "sizing": size}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
