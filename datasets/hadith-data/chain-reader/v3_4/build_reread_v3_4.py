"""Build the v3.4 re-read set: reports already read whose reading turns on the owner's third-round rulings (encounter, two sayings), as reader packets with jobs.

    python -B -X utf8 v3_4/build_reread_v3_4.py [--set reread-001] [--check]          (from chain-reader/)
    python -B -X utf8 v3_4/build_reread_v3_4.py --set reread-002 --exclude-set reread-001   (later: tranches triaged since, without the reports already in reread-001)

Sources: batch 001 and every tranche whose triage exists (v3.3's if present, else v3.2's); a tranche still being read has no triage and is reported as not covered.
A report enters for any of five reasons (several may apply; `private/reasons.tsv` lists them all):
  needs_ruling_both   both readers set `needs_ruling` (the triage flag `both`: the agreed reading is held as needs_ruling, or the passes differ and both flagged)
  flag_one_reader     one reader set `needs_ruling` (flag `a_only` / `b_only`)
  encounter_shape     ENCOUNTER: «كنت / كنا عند | مع | بين يدي», «دخلت / دخلنا على», «بينا / بينما أنا / نحن», «خرجت / خرجنا مع» in the first 600 letters, not followed by the Prophet
                      within three words (he ends a chain: nothing changes), and a «قال / فقال» within 300 letters after it
  two_sayings_shape   TWO_SAYINGS: after the isnad of any valid reading (+20 letters), «و / ف + حدثني / حدثنا / أخبرني / أخبرنا / حدثتني / سمعت» (optionally after «قال X»),
                      unless «نحوه / مثله / بمثله / بنحوه / بهذا الإسناد / بمعناه / نحو حديث / مثل حديث» follows within 200 letters (that is another route of the same saying)
  judge_cannot_tell   the three judgements' `cannot tell` on these two questions (JUDGE_CANNOT_TELL, each with its file)
Packets reuse the source packet's `text` and `context` unchanged (no context is rebuilt), 20 per packet, opaque ids `r4-xxxxxx` (salted hash; salt in private/id_map.json), order an md5 shuffle.
Writes <set>/packets/packet-NNN.jsonl, <set>/jobs.json (the shape of tranches/tranche-02/jobs-v3_2.json), <set>/manifest.json, <set>/private/{id_map.json, reasons.tsv}. See v3_4/AGENTS.md §re-read.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import secrets
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
from expand_v3_4 import expand  # noqa: E402
from norm_v3_2 import fold_v3  # noqa: E402
from validate import parse_output  # noqa: E402
from validate_v3_4 import validate_chain  # noqa: E402

PER_PACKET = 20
MODEL_TIER = "claude-haiku-5-5"
ENCOUNTER = re.compile(r"(?:^| )(?:ف|و|ثم )?(?:(?:كنت|كنا) (?:جالسا |جلوسا |يوما |قاعدا |قعودا )?(?:عند|مع|بين يدي)|(?:دخلت|دخلنا) علي|(?:بينا|بينما) (?:انا|نحن)|(?:خرجت|خرجنا) مع)(?= )")
PROPHET_NEAR = re.compile(r"^(?:\S+ ){0,3}?(?:رسول الله|النبي)(?= |$)")
SPEAKS = re.compile(r"(?:^| )(?:ف|و)?قال(?= )")
TWO_SAYINGS = re.compile(r"(?:^| )(?:قال (?:\S+ ){1,3})?(?:و|ف)(?:حدثني|حدثنا|اخبرني|اخبرنا|حدثتني|سمعت)(?= )")
SAME_SAYING = re.compile(r"نحوه|مثله|بمثله|بنحوه|بهذا الاسناد|بمعناه|نحو حديث|مثل حديث")
# the judges' `cannot tell` on the two questions: (source, id, judgement file, question)
JUDGE_CANNOT_TELL = [
    ("batch-001", "b1-b2ad9c", "analysis-batch-001/README.md Q4", "encounter"), ("batch-001", "b1-941f93", "analysis-batch-001/README.md Q4", "encounter"),
    ("batch-001", "b1-dcfca3", "analysis-batch-001/README.md Q4 (disagreement)", "encounter"), ("batch-001", "b1-cb13de", "analysis-batch-001/README.md Q5", "two_sayings"),
    ("tranche-01", "t01-a20cb6", "tranches/tranche-01/judge/analysis/sample_verdicts.tsv CT (Q4)", "encounter"),
    ("tranche-01", "t01-306ccd", "tranches/tranche-01/judge/analysis/README.md Q3/Q4 (disagreement)", "encounter"),
    ("tranche-01", "t01-2a5330", "tranches/tranche-01/judge/analysis/README.md Q3/Q4 (disagreement)", "encounter"),
    ("tranche-01", "t01-881857", "tranches/tranche-01/judge/analysis/README.md Q3/Q4 (disagreement)", "encounter"),
    ("tranche-02", "t02-3cacbd", "tranches/tranche-02/judge-v3_2/analysis/README.md §9 CT", "encounter"), ("tranche-02", "t02-fe8248", "tranches/tranche-02/judge-v3_2/analysis/README.md §9 CT", "encounter"),
    ("tranche-02", "t02-fecbb4", "tranches/tranche-02/judge-v3_2/analysis/README.md §9 CT", "two_sayings"), ("tranche-02", "t02-c3900f", "tranches/tranche-02/judge-v3_2/analysis/README.md §5 CT", "two_sayings"),
    ("tranche-02", "t02-3ac3df", "tranches/tranche-02/judge-v3_2/analysis/README.md §7 (the Imam's act described)", "encounter"),
    ("tranche-02", "t02-f3cf19", "tranches/tranche-02/judge-v3_2/analysis/README.md §7 (Umar inside Anas's account)", "encounter"),
]


def sources() -> list[dict]:
    """Batch 001 and tranches 01-10 with the paths the set reads; `triage` is None for a source not yet triaged."""
    found = []
    batch = {"name": "batch-001", "packets": ROOT / "v3" / "batch-001" / "packets", "outputs": ROOT / "v3" / "batch-001" / "outputs"}
    batch["triage"] = next((p for p in (ROOT / "v3_3" / "batch-001" / "triage", ROOT / "v3_2" / "batch-001" / "triage") if (p / "triage.tsv").is_file()), None)
    found.append(batch)
    for number in range(1, 11):
        tranche = ROOT / "tranches" / f"tranche-{number:02d}"
        triage = next((tranche / name for name in ("triage-v3_3", "triage-v3_2") if (tranche / name / "triage.tsv").is_file()), None)
        found.append({"name": f"tranche-{number:02d}", "packets": tranche / "packets", "outputs": tranche / "outputs", "triage": triage})
    return found


def load_packets(directory: Path) -> dict[str, dict]:
    rows = {}
    for path in sorted(directory.glob("packet-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                rows[row["id"]] = {"row": row, "file": path.name}
    return rows


def load_triage(directory: Path) -> dict[str, dict]:
    lines = (directory / "triage.tsv").read_text(encoding="utf-8").splitlines()
    header = lines[0].split("\t")
    return {cells[0]: dict(zip(header, cells)) for cells in (line.split("\t") for line in lines[1:] if line.strip())}


def isnad_end(report_id: str, packet: dict, outputs: Path) -> int | None:
    """End of the isnad by the readers: the furthest end of a written link of any valid pass (None when neither pass is valid)."""
    ends = []
    for tag in ("a", "b"):
        path = outputs / f"pass-{tag}" / f"{report_id}.json"
        if not path.is_file():
            continue
        try:
            output, _ = parse_output(path.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if not isinstance(output, dict) or validate_chain(output, packet["text"], report_id, packet.get("context")):
            continue
        reading, _ = expand(output, packet["text"], packet.get("context"))
        ends += [l["end"] for r in reading["routes"] for l in r["links"] if l["end"] is not None and l["kind"] != "imam_in_text"]
    return max(ends) if ends else None


def encounter_shape(text: str) -> str | None:
    folded = fold_v3(text)
    for match in ENCOUNTER.finditer(folded[:600]):
        after = folded[match.end():].lstrip()
        if PROPHET_NEAR.match(after):
            continue
        if SPEAKS.search(folded[match.end(): match.end() + 300]):
            return match.group(0).strip()
    return None


def two_sayings_shape(text: str, end: int | None) -> str | None:
    if end is None:
        return None
    folded = fold_v3(text[end + 20:])
    for match in TWO_SAYINGS.finditer(folded):
        if not SAME_SAYING.search(folded[match.end(): match.end() + 200]):
            return match.group(0).strip()
    return None


def collect() -> tuple[list[dict], dict]:
    """Every report of the set with its reasons, and the coverage per source."""
    chosen: dict[tuple[str, str], dict] = {}
    coverage = {}
    judged = {(source, report_id): (where, question) for source, report_id, where, question in JUDGE_CANNOT_TELL}
    for source in sources():
        if not source["packets"].is_dir():
            continue
        if source["triage"] is None:
            coverage[source["name"]] = "not covered: no triage yet (being read or not started)"
            continue
        packets = load_packets(source["packets"])
        triage = load_triage(source["triage"])
        coverage[source["name"]] = f"covered: {len(packets)} reports, triage {source['triage'].relative_to(ROOT).as_posix()}"
        for report_id, entry in packets.items():
            packet, row = entry["row"], triage.get(report_id, {})
            reasons = []
            flag = row.get("flag") or ""
            if flag == "both":
                reasons.append("needs_ruling_both")
            elif flag in ("a_only", "b_only"):
                reasons.append("flag_one_reader")
            encounter = encounter_shape(packet["text"])
            if encounter:
                reasons.append("encounter_shape")
            second = two_sayings_shape(packet["text"], isnad_end(report_id, packet, source["outputs"]))
            if second:
                reasons.append("two_sayings_shape")
            if (source["name"], report_id) in judged:
                reasons.append("judge_cannot_tell")
            if reasons:
                chosen[(source["name"], report_id)] = {"source": source["name"], "id": report_id, "packet_file": entry["file"], "packets_dir": source["packets"].relative_to(ROOT).as_posix(),
                                                       "reasons": reasons, "flag": flag, "agree": row.get("agree"), "holds": row.get("holds", ""), "encounter_cue": encounter, "two_sayings_cue": second,
                                                       "judge": judged.get((source["name"], report_id)), "text": packet["text"], "context": packet.get("context")}
    missing = [key for key in judged if key not in chosen and coverage.get(key[0], "").startswith("covered")]
    assert not missing, f"judged ids not found in their packets: {missing}"
    return list(chosen.values()), coverage


def opaque_ids(items: list[dict], salt: str) -> None:
    seen = set()
    for item in sorted(items, key=lambda i: (i["source"], i["id"])):
        digest = hashlib.sha256(f"{salt}:{item['source']}:{item['id']}".encode()).hexdigest()
        length = 6
        while "r4-" + digest[:length] in seen:
            length += 1
        item["opaque"] = "r4-" + digest[:length]
        seen.add(item["opaque"])


def instruction(prompt: dict, packet_paths: list[str], output_dir: str, run_file: str, run_id: str, packet_numbers: list[str]) -> str:
    """The reader instruction of tranches/build_tranches.py (copied word for word so the re-read jobs are the tranche jobs' twin)."""
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
    """Pass A: (1,2) (3,4) ...; pass B shifted by one: (1) (2,3) (4,5) ... (tranches/build_tranches.py)."""
    numbers = [f"{n:03d}" for n in range(1, packet_count + 1)]
    return {"a": [numbers[i:i + 2] for i in range(0, packet_count, 2)], "b": [numbers[:1]] + [numbers[i:i + 2] for i in range(1, packet_count, 2)]}


def expected(jobs: list[dict], files: int) -> dict:
    """The tranche jobs' `expected` block; with an even packet count pass B has one job more (its first packet alone), stated in two extra keys rather than miscounted."""
    per_pass = {label: sum(1 for j in jobs if j["pass"] == label) for label in ("a", "b")}
    block = {"jobs": len(jobs), "jobs_per_pass": per_pass["a"], "files_per_pass": files, "run_txt_lines_per_pass": per_pass["a"]}
    if per_pass["b"] != per_pass["a"]:
        block.update({"jobs_pass_b": per_pass["b"], "run_txt_lines_pass_b": per_pass["b"]})
    return block


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--set", default="reread-001")
    parser.add_argument("--check", action="store_true", help="print the counts, write nothing")
    parser.add_argument("--exclude-set", action="append", default=[], help="an earlier set (reread-001): its reports are left out (for a later set over newly triaged tranches)")
    args = parser.parse_args(argv)
    items, coverage = collect()
    done = {(v["source"], v["id"]) for name in args.exclude_set for v in json.loads((HERE / name / "private" / "id_map.json").read_text(encoding="utf-8"))["ids"].values()}
    items = [i for i in items if (i["source"], i["id"]) not in done]
    by_source = Counter(i["source"] for i in items)
    by_reason = Counter(r for i in items for r in i["reasons"])
    by_source_reason = {s: dict(Counter(r for i in items if i["source"] == s for r in i["reasons"])) for s in sorted(by_source)}
    only_shape = Counter(i["reasons"][0] for i in items if len(i["reasons"]) == 1)
    print(json.dumps({"reports": len(items), "by_source": by_source, "by_reason": by_reason, "by_source_reason": by_source_reason, "single_reason": only_shape, "coverage": coverage}, ensure_ascii=False, indent=1))
    if args.check:
        return 0
    out = HERE / args.set
    private = out / "private"
    private.mkdir(parents=True, exist_ok=True)
    id_map_path = private / "id_map.json"
    salt = json.loads(id_map_path.read_text(encoding="utf-8"))["salt"] if id_map_path.is_file() else secrets.token_hex(16)
    opaque_ids(items, salt)
    items.sort(key=lambda i: hashlib.md5(f"{salt}:{i['opaque']}".encode()).hexdigest())
    packets_dir = out / "packets"
    packets_dir.mkdir(parents=True, exist_ok=True)
    for old in packets_dir.glob("packet-*.jsonl"):
        old.unlink()
    prompt_record = json.loads((HERE / "prompt-v3_4.json").read_text(encoding="utf-8"))
    prompt = {"path": str(HERE / "prompt-v3_4.md"), "version": prompt_record["version"], "sha256": prompt_record["sha256"]}
    chunks = [items[i:i + PER_PACKET] for i in range(0, len(items), PER_PACKET)]
    packet_info = {}
    for n, chunk in enumerate(chunks, start=1):
        name = f"packet-{n:03d}.jsonl"
        for item in chunk:
            item["reread_packet"] = name
        body = "\n".join(json.dumps({"id": i["opaque"], "text": i["text"], "context": i["context"]}, ensure_ascii=False, separators=(",", ":")) for i in chunk) + "\n"
        (packets_dir / name).write_text(body, encoding="utf-8", newline="\n")
        packet_info[name] = {"reports": len(chunk), "line_chars": len(body), "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()}
    jobs = []
    for label, pairs in pairings(len(chunks)).items():
        for pair in pairs:
            run_id = f"r4-{args.set}-{label}-" + "-".join(pair)
            files = [str(packets_dir / f"packet-{n}.jsonl") for n in pair]
            output_dir, run_file = str(out / "outputs" / f"pass-{label}"), str(out / "outputs" / f"pass-{label}" / "RUN.txt")
            ids = [i["opaque"] for n in pair for i in chunks[int(n) - 1]]
            text = instruction(prompt, files, output_dir, run_file, run_id, pair)
            jobs.append({"job_id": run_id, "pass": label, "packets": pair, "packet_files": files, "output_dir": output_dir, "output_files": [f"{i}.json" for i in ids], "run_file": run_file,
                         "run_id": run_id, "expected_files": len(ids), "input_chars": len(text) + prompt_record["chars"] + sum(packet_info[f"packet-{n}.jsonl"]["line_chars"] for n in pair), "instruction": text})
    jobs_doc = {"format": "shura-chain-reader-jobs/1", "tranche": args.set, "prompt": prompt,
                "model_tier": f"{MODEL_TIER} for every job of the whole run; pass A and pass B use the same tier and different agents (v3/batch-001/RUN.md)",
                "run_line_format": "run_id={RUNID} | packets={P1},{P2} | model=<model id> | start=<UTC start> | end=<UTC end> | files=<number of files you wrote>",
                "output_file_format": "one <id>.json per packet line, exactly the JSON object the prompt describes (no fence, no commentary), in output_dir",
                "expected": expected(jobs, len(items)), "jobs": jobs,
                "prompt_note": "prompt v3.4 (v3_4/prompt-v3_4.md): the v3.4 re-read of reports turning on the third-round rulings; built by v3_4/build_reread_v3_4.py"}
    (out / "jobs.json").write_text(json.dumps(jobs_doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    manifest = {"format": "shura-chain-reader-reread/1", "set": args.set, "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "prompt": {"version": prompt["version"], "sha256": prompt["sha256"]},
                "builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "reports": len(items), "per_packet": PER_PACKET, "packets": packet_info,
                "by_source": dict(by_source), "by_reason": dict(by_reason), "by_source_reason": by_source_reason, "coverage": coverage,
                "note": "text and context are the source packets' own, unchanged; which report is which, and why it is here, is in private/ only"}
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    id_map = {"salt": salt, "ids": {i["opaque"]: {"source": i["source"], "id": i["id"], "source_packet": f"{i['packets_dir']}/{i['packet_file']}", "reread_packet": i["reread_packet"]} for i in items}}
    id_map_path.write_text(json.dumps(id_map, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    lines = ["opaque\tsource\tid\treasons\tflag\tagree\tholds\tencounter_cue\ttwo_sayings_cue\tjudge"]
    for i in sorted(items, key=lambda i: (i["source"], i["id"])):
        lines.append("\t".join([i["opaque"], i["source"], i["id"], ",".join(i["reasons"]), i["flag"], str(i["agree"] or ""), i["holds"], i["encounter_cue"] or "", i["two_sayings_cue"] or "", " | ".join(i["judge"]) if i["judge"] else ""]))
    (private / "reasons.tsv").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(items)} reports, {len(chunks)} packets, {len(jobs)} jobs -> {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
