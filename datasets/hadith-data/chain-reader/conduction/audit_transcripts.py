"""Audit the TOOL BOUNDS of every worker transcript of a chain-reader Conduction run.

Usage (from the repo root):
  python -B -X utf8 datasets/hadith-data/chain-reader/conduction/audit_transcripts.py \
      --jobs datasets/hadith-data/chain-reader/conduction/jobs-cr-t03.json \
      --transcripts .agentgraph/runs/<factory-run>-readers/transcripts [--tranche 03] [--write-contaminated]

A worker may: Read the prompt file, its own packets, its own just-written outputs; Write only its own expected files;
Bash only `date -u ...` and appending to / reading its own RUN.txt; call ToolSearch and the agentgraph graph_* tools.
Findings are tiered: CONTAMINATING (read private/, the other pass, another job's outputs), OTHER (any other out-of-bounds
read/write/shell, network use, unknown tool). With --write-contaminated the ids of contaminating jobs' expected files go to
tranches/tranche-NN/contaminated.txt (nothing is deleted).
"""
import argparse
import collections
import json
import pathlib
import re
import sys

CHAIN_READER = pathlib.Path(__file__).resolve().parents[1]
TOOL_LINE = re.compile(r"^\*\*→ (\S+)\*\* `(.*)`\s*$")
BENIGN_TOOLS = {"ToolSearch", "mcp__agentgraph__graph_claim", "mcp__agentgraph__graph_emit", "mcp__agentgraph__graph_query"}
NETWORK = re.compile(r"\b(curl|wget|Invoke-WebRequest|Invoke-RestMethod|iwr|irm|nc|ssh|scp|ftp|psql|git|npm|npx|pip)\b", re.I)


def norm(path):
    text = str(path).replace("\\", "/").rstrip("/").lower()
    return re.sub(r"^/([a-z])/", lambda m: m.group(1) + ":/", text)  # git-bash /c/... -> c:/...


def tool_calls(transcript):
    for line in transcript.read_text(encoding="utf-8").splitlines():
        match = TOOL_LINE.match(line)
        if not match:
            continue
        try:
            yield match.group(1), json.loads(match.group(2))
        except ValueError:
            yield match.group(1), {"_unparsed": match.group(2)}


def audit_job(job, transcript, tranche_dir):
    own_outputs = {norm(p) for p in job["expected_files"]}
    own_output_dir = norm(job["output_dir"])
    run_txt = norm(job["run_txt"])
    prompt_file = norm(job["prompt_file"])
    packets_dir = pathlib.Path(job["output_dir"]).parent.parent / "packets"  # <set>/outputs/pass-x -> <set>/packets (tranche or re-read set)
    own_packets = {norm(packets_dir / f"packet-{number}.jsonl") for number in job["packets"]}
    own_pass = job["pass"]
    findings = []  # (tier, text)
    counts = collections.Counter()
    for tool, args in tool_calls(transcript):
        counts[tool] += 1
        if tool in BENIGN_TOOLS:
            continue
        if tool == "Read":
            path = norm(args.get("file_path", ""))
            if path == prompt_file or path in own_packets or path in own_outputs or path == run_txt:
                continue
            if "/private/" in path or path.endswith("/private"):
                findings.append(("CONTAMINATING", f"Read private: {path}"))
            elif path.startswith(own_output_dir + "/"):
                findings.append(("CONTAMINATING", f"Read another job's output (same pass): {path}"))
            elif "/outputs/pass-" in path:
                findings.append(("CONTAMINATING", f"Read the other pass / other outputs: {path}"))
            else:
                findings.append(("OTHER", f"Read outside bounds: {path}"))
        elif tool in ("Write", "Edit", "NotebookEdit"):
            path = norm(args.get("file_path", ""))
            if tool == "Write" and path in own_outputs:
                continue
            findings.append(("OTHER", f"{tool} outside own outputs: {path}"))
        elif tool == "Bash":
            command = args.get("command", "")
            pieces = [piece.strip() for piece in re.split(r"[;\n]|&&", command) if piece.strip()]
            ok = bool(pieces)
            for piece in pieces:
                if re.fullmatch(r"(\w+=)?\$?\(?date -u[^|<>]*\)?", piece):
                    continue
                if re.fullmatch(r"\w+=\$\(date -u[^)]*\)", piece):
                    continue
                if re.fullmatch(r"echo [\w .$\"'-]*", piece):  # a bare `echo done`
                    continue
                if re.match(r"echo\b", piece) and ">>" in piece:
                    target = norm(piece.rsplit(">>", 1)[1].strip().strip("\"'"))
                    if target == run_txt or target.endswith("/run.txt") and target.startswith(own_output_dir):
                        continue
                if re.match(r"(cat|tail|head|grep|type|Get-Content)\b", piece) and run_txt in norm(piece):
                    continue
                ok = False
            if not ok:
                tier = "OTHER"
                findings.append((tier, ("Network-capable " if NETWORK.search(command) else "") + f"Bash beyond bounds: {command[:160]!r}"))
        elif tool in ("WebFetch", "WebSearch"):
            findings.append(("OTHER", f"Network tool {tool}"))
        else:
            findings.append(("OTHER", f"Unexpected tool {tool}"))
    return findings, counts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--transcripts", required=True)
    ap.add_argument("--tranche", help="NN; needed for --write-contaminated and to locate packets (default: from the job ids)")
    ap.add_argument("--write-contaminated", action="store_true")
    args = ap.parse_args()
    jobs = json.loads(pathlib.Path(args.jobs).read_text(encoding="utf-8"))
    match = re.match(r"t(\d+)-", jobs[0]["job_id"])
    tranche = args.tranche or (match.group(1) if match else None)
    tranche_dir = CHAIN_READER / "tranches" / f"tranche-{tranche}"  # only used by --write-contaminated
    transcripts = pathlib.Path(args.transcripts)
    totals = collections.Counter()
    contaminated_ids = []
    missing = []
    for job in jobs:
        transcript = transcripts / f"read-{job['pass']}-{job['job_id']}.md"
        if not transcript.is_file():
            missing.append(job["job_id"])
            continue
        findings, counts = audit_job(job, transcript, tranche_dir)
        totals.update(counts)
        tiers = {tier for tier, _ in findings}
        for tier, text in findings:
            print(f"{job['job_id']}\t{tier}\t{text}")
        if "CONTAMINATING" in tiers:
            contaminated_ids.append(job)
    print(f"audited {len(jobs) - len(missing)} transcripts, missing {missing}")
    print("tool calls:", dict(totals))
    run_log = transcripts.parent / "run.jsonl"  # Conduction's own event log: cost and refused writes
    if run_log.is_file():
        cost, refused = 0.0, collections.Counter()
        for line in run_log.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)["event"]
            if event["type"] == "claim.violated":
                refused[event["payload"]["worker"]] += 1
            data = event["payload"].get("object", {}).get("data", {}) if event["type"] == "object.created" else {}
            if "cost_usd" in data:
                cost += float(data["cost_usd"])
        print(f"conduction cost USD {cost:.2f}; Writes refused by the claim ledger: {sum(refused.values())} {dict(refused)}")
    flagged = len(contaminated_ids)
    print(f"contaminated jobs: {flagged}")
    if args.write_contaminated and contaminated_ids:
        path = tranche_dir / "contaminated.txt"
        ids = sorted(pathlib.Path(p).stem for job in contaminated_ids for p in job["expected_files"])
        path.write_text("\n".join(ids) + ("\n" if ids else ""), encoding="utf-8", newline="\n")
        print(f"wrote {path} ({len(ids)} ids)")
    sys.exit(1 if flagged or missing else 0)


if __name__ == "__main__":
    main()
