"""After a Conduction tranche run under prompt v3.4: verify, audit tool bounds, validate, triage, draw judge samples, append the PROGRESS.md row.

Usage (repo root): python -B -X utf8 datasets/hadith-data/chain-reader/conduction/post_tranche.py NN <factory_run_id> [--note TEXT]
Prints one summary line per step; exit 1 when a stop-rule condition holds (agreed < 82.0%, valid per pass < 95%, contaminated, files missing).
"""
import argparse
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[4]
CHAIN = REPO / "datasets/hadith-data/chain-reader"
PY = [sys.executable, "-B", "-X", "utf8"]
STOP_AGREED = 88.0 - 6  # tranche 02 agreed 88.0%


def run(args, cwd):
    return subprocess.run(PY + args, cwd=cwd, capture_output=True, text=True, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tranche")
    ap.add_argument("run_id")
    ap.add_argument("--note", default="")
    ap.add_argument("--rerun-jobs", type=int, default=0)
    ap.add_argument("--rerun-usd", type=float, default=0.0)
    args = ap.parse_args()
    nn = args.tranche
    tranche = CHAIN / "tranches" / f"tranche-{nn}"
    rel = f"tranches/tranche-{nn}"
    jobs_path = CHAIN / "conduction" / f"jobs-cr-t{nn}.json"
    jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
    state = json.loads((REPO / ".agentgraph/factory-runs" / args.run_id / "state.json").read_text(encoding="utf-8"))
    run_dir = REPO / ".agentgraph/runs" / f"{args.run_id}-readers"
    ended = [json.loads(line)["event"]["timestamp"] for line in (run_dir / "run.jsonl").read_text(encoding="utf-8").splitlines() if '"mission.completed"' in line]
    problems = []

    # 1. files and RUN.txt
    expected = parsed = 0
    for job in jobs:
        for name in job["expected_files"]:
            expected += 1
            try:
                json.loads(pathlib.Path(name).read_text(encoding="utf-8"))
                parsed += 1
            except (OSError, ValueError):
                problems.append(f"missing/unparsable {name}")
    run_lines = 0
    for pass_name in ("a", "b"):
        lines = (tranche / "outputs" / f"pass-{pass_name}" / "RUN.txt").read_text(encoding="utf-8").splitlines()
        run_lines += len(lines)
        for line in lines:
            if "model=claude-haiku-5-5 " not in line:
                problems.append(f"RUN.txt line without model=claude-haiku-5-5: {line[:80]}")
    for job in jobs:
        if f"run_id={job['run_id']} " not in pathlib.Path(job["run_txt"]).read_text(encoding="utf-8"):
            problems.append(f"no RUN.txt line for {job['run_id']}")
    print(f"files parsed {parsed}/{expected}; RUN.txt lines {run_lines}/{len(jobs)}; problems {len(problems)}")

    # 2. tool bounds
    audit = run(["datasets/hadith-data/chain-reader/conduction/audit_transcripts.py", "--jobs", str(jobs_path), "--transcripts", str(run_dir / "transcripts"), "--tranche", nn, "--write-contaminated"], REPO)
    print(audit.stdout.strip())
    contaminated = int(re.search(r"contaminated jobs: (\d+)", audit.stdout).group(1))
    usd = re.search(r"cost USD ([\d.]+)", audit.stdout).group(1)
    refused = re.search(r"refused by the claim ledger: (\d+)", audit.stdout).group(1)

    # 3. validate and triage
    valid = {}
    for pass_name in ("a", "b"):
        result = run(["v3_4/validate_v3_4.py", "--packets", f"{rel}/packets", "--outputs", f"{rel}/outputs/pass-{pass_name}"], CHAIN)
        valid[pass_name] = int(re.search(r"valid (\d+)/", result.stdout + result.stderr).group(1))
    triage_args = ["--packets", f"{rel}/packets", "--pass-a", f"{rel}/outputs/pass-a", "--pass-b", f"{rel}/outputs/pass-b", "--reports", f"{rel}/private/reports.jsonl"]
    # no variant release flags; plain triage (two sayings held) and sayings-supported triage (reported both)
    plain = run(["v3_4/triage_v3_4.py"] + triage_args + ["--out", f"{rel}/triage-v3_4"], CHAIN)
    sayings = run(["v3_4/triage_v3_4.py"] + triage_args + ["--out", f"{rel}/triage-v3_4-sayings", "--sayings-supported"], CHAIN)
    print("triage plain", plain.stdout.strip()[-300:], plain.stderr.strip()[-400:])
    print("triage sayings", sayings.stdout.strip()[-300:], sayings.stderr.strip()[-400:])
    summary = json.loads((tranche / "triage-v3_4/summary.json").read_text(encoding="utf-8"))
    summary_s = json.loads((tranche / "triage-v3_4-sayings/summary.json").read_text(encoding="utf-8"))
    import csv
    with (tranche / "triage-v3_4-sayings/triage.tsv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="	"))
    labelled = sum(1 for r in rows if (r.get("sayings") or "0") not in ("", "0"))
    print("saying-labelled readings (agreed readings with a saying label):", labelled, "columns:", list(rows[0].keys()))

    # 4. judge samples
    for extra in (["--base-seed", "20261200"], ["--base-seed", "20261300", "--exclude", f"{rel}/judge-v3_4/sample.tsv", "--out-name", "extension"]):
        result = run(["conduction/draw_judge_sample_v3_4.py", "--tranche", nn] + extra, CHAIN)
        print("draw", extra[:2], result.returncode, result.stdout.strip()[-200:], result.stderr.strip()[-200:])

    # 5. PROGRESS row
    reports = summary["reports"]
    agreed_pct = 100 * summary["agreed"] / reports
    holds = ", ".join(f"{k} {v}" for k, v in summary["holds"].items())
    holds_s = ", ".join(f"{k} {v}" for k, v in summary_s["holds"].items())
    start, end = state["started_at"].replace("2026-11-22T", ""), (ended[-1] if ended else "?").replace("2026-11-22T", "")
    note = args.note or ("gate passed" if state["status"] == "completed" else f"state {state['status']}")
    note += f"; {refused} Writes refused by the claim ledger"
    row = (f"| {nn} | {args.run_id} | {start} | {end} | {len(jobs)} / 0 / {args.rerun_jobs} | {parsed} / {expected} | a {reports - valid['a']} / b {reports - valid['b']} | "
           f"{summary['agreed']} ({agreed_pct:.1f}%) | {summary['eligible']} ({summary['applies_chain']} links + {summary['applies_no_chain']} no chain); with --sayings-supported {summary_s['eligible']} | prompt v3.4; plain: {holds}; sayings-supported: {holds_s}; saying-labelled readings {labelled} | {contaminated} | {usd}{f' + {args.rerun_usd:.2f} rerun' if args.rerun_usd else ''} | {note} |\n")
    progress = CHAIN / "tranches/PROGRESS.md"
    with progress.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(row)
    print(f"agreed {agreed_pct:.1f}%  valid a {valid['a']}/{reports} b {valid['b']}/{reports}  eligible {summary['eligible']}  USD {usd}  start {start} end {end}")
    print("holds:", holds)
    print("holds (sayings-supported):", holds_s, "| eligible", summary_s["eligible"])
    stop = []
    if agreed_pct < STOP_AGREED:
        stop.append(f"agreed {agreed_pct:.1f}% < {STOP_AGREED}")
    if min(valid.values()) / reports < 0.95:
        stop.append("valid per pass < 95%")
    if contaminated:
        stop.append("contaminated workers")
    if problems:
        stop.append("file problems: " + "; ".join(problems[:5]))
    print("STOP: " + "; ".join(stop) if stop else "stop rule: clear")
    sys.exit(1 if stop else 0)


if __name__ == "__main__":
    main()
