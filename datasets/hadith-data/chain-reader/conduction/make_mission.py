"""Turn a jobs file into a Conduction factory (one wave, one reader per job). See README.md."""
import argparse
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
PYTHON = r"C:\Program Files\Python312\python.exe"
SDK = "agy"
MODEL = "gemini-3-flash"
JOB_KEYS = ("job_id", "pass", "packets", "prompt_file", "output_dir", "run_txt", "run_id", "expected_files", "instruction")

CLAIM_ADDENDUM = """

--- Harness notes (Conduction, not part of the reading task) ---
Writes are enforced by a claim ledger. Before you write anything, call the `graph_claim` tool ONCE with exactly these paths (and nothing else), then write each file with the Write tool:
{paths}
Append the RUN.txt line with Bash only (`echo "<line>" >> <RUN.txt path>`); take UTC times with `date -u +%Y-%m-%dT%H:%M:%SZ`. Use no other shell command, and run no program that produces readings."""


def load_jobs(path):
    jobs = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    ids = set()
    for job in jobs:
        missing = [k for k in JOB_KEYS if k not in job]
        if missing:
            sys.exit(f"job {job.get('job_id')}: missing keys {missing}")
        key = f"{job['pass']}-{job['job_id']}"
        if key in ids:
            sys.exit(f"duplicate job {key}")
        ids.add(key)
    return jobs


def build_factory(jobs, slug, jobs_path, concurrency, max_turns, sdk=SDK, model=MODEL):
    agents = []
    for job in jobs:
        paths = "\n".join("  " + p.replace("\\", "/") for p in job["expected_files"])
        agent = {
            "name": f"read-{job['pass']}-{job['job_id']}",
            "brief": job["instruction"].rstrip() + CLAIM_ADDENDUM.format(paths=paths),
            "tools": ["Read", "Write", "Bash"],
            "sdk": sdk,
            "owns": [p.replace("\\", "/") for p in job["expected_files"]],
        }
        if model:
            agent["model"] = model
        agents.append(agent)
    gate = {"command": {"argv": [PYTHON, "-X", "utf8", "-B", str(HERE / "check_tranche.py"), "--jobs", str(pathlib.Path(jobs_path).resolve())], "timeout": 300}}
    model_label = f"{sdk}/{model}" if model else sdk
    return {
        "slug": slug,
        "description": f"chain-reader tranche {slug}: {len(jobs)} {model_label} reader jobs",
        "waves": [{"slug": "readers", "agents": agents, "gate": gate, "max_turns": max_turns, "max_concurrency": concurrency}],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("jobs")
    ap.add_argument("--slug", required=True, help="tranche slug, [A-Za-z0-9._-]{1,64}; also the factory run id prefix")
    ap.add_argument("--sdk", default=SDK, help=f"Conduction agent SDK (default: {SDK})")
    ap.add_argument("--model", default=MODEL, help=f"Model name (default: {MODEL}; pass empty string to omit)")
    ap.add_argument("--concurrency", type=int, default=12)
    ap.add_argument("--max-turns", type=int, default=150)
    args = ap.parse_args()
    if args.concurrency > 12:
        sys.exit("concurrency is capped at 12")
    jobs = load_jobs(args.jobs)
    for job in jobs:
        pathlib.Path(job["output_dir"]).mkdir(parents=True, exist_ok=True)  # graph_claim needs the parent to exist
    out = HERE / f"factory-{args.slug}.json"
    out.write_text(json.dumps(build_factory(jobs, args.slug, args.jobs, args.concurrency, args.max_turns, sdk=args.sdk, model=args.model), indent=1), encoding="utf-8", newline="\n")
    repo = HERE.parents[3]
    print(f"wrote {out} ({len(jobs)} agents, concurrency {args.concurrency})")
    print(f'run: python -X utf8 {HERE / "run_tranche.py"} --factory {out.relative_to(repo).as_posix()}')


if __name__ == "__main__":
    main()
