"""Turn a reviewer jobs file (shura-chain-review-jobs/1) into a Conduction factory: one wave, one fresh reviewer per packet (reviewer/RUN.md). The reader tranches' scripts in
conduction/ are imported, not edited: their factory builder and gate are reused; only the job shape (one packet and one output per job) and the model differ.

    python -X utf8 reviewer/make_review_mission.py reviewer/review-t01/held/jobs.json --slug rv-t01-held [--sdk agy] [--model gemini-3-flash] [--concurrency 6] [--max-turns 60]
    -> reviewer/review-t01/held/conduction-jobs.json (flat list, the reader jobs' shape) and reviewer/review-t01/held/factory-<slug>.json
then, with the dashboard up:  python -X utf8 datasets/hadith-data/chain-reader/conduction/run_tranche.py --factory <that factory path relative to the repository root>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CONDUCTION = HERE.parent / "conduction"
REPO = HERE.parents[3]
sys.path.insert(0, str(CONDUCTION))
import make_mission  # noqa: E402  (conduction/make_mission.py: build_factory, CLAIM_ADDENDUM; unchanged)

SDK = "agy"
MODEL = "gemini-3-flash"
REVIEWER_MODEL = MODEL


def flat_jobs(doc: dict) -> list[dict]:
    """The reader jobs' flat shape: `packets` is the one packet file, `expected_files` its one output file (check_tranche.py reads exactly these keys)."""
    jobs = []
    for job in doc["jobs"]:
        jobs.append({"job_id": job["job_id"], "pass": str(job["pass"]), "packets": [job["packet_file"]], "prompt_file": doc["prompt"]["path"], "output_dir": str(Path(job["output_file"]).parent),
                     "run_txt": job["run_file"], "run_id": job["run_id"], "expected_files": [job["output_file"]], "instruction": job["instruction"]})
    return jobs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("jobs")
    parser.add_argument("--slug", required=True, help="[A-Za-z0-9._-]{1,64}; also the factory run id prefix")
    parser.add_argument("--sdk", default=SDK, help=f"Conduction agent SDK (default: {SDK})")
    parser.add_argument("--model", default=MODEL, help=f"Model name (default: {MODEL}; pass empty string to omit)")
    parser.add_argument("--concurrency", type=int, default=6, help="at most 12 (Conduction's cap); reviewer workers read ~30k tokens each, so 6 by default")
    parser.add_argument("--max-turns", type=int, default=60)
    args = parser.parse_args(argv)
    if args.concurrency > 12:
        sys.exit("concurrency is capped at 12")
    jobs_path = Path(args.jobs).resolve()
    doc = json.loads(jobs_path.read_text(encoding="utf-8"))
    if doc.get("format") != "shura-chain-review-jobs/1":
        sys.exit(f"{args.jobs} is not a shura-chain-review-jobs/1 file")
    jobs = flat_jobs(doc)
    for job in jobs:
        Path(job["output_dir"]).mkdir(parents=True, exist_ok=True)           # graph_claim needs the parent to exist
    flat_path = jobs_path.with_name("conduction-jobs.json" if str(doc["pass"]) == "1" else f"conduction-jobs-pass-{doc['pass']}.json")
    flat_path.write_text(json.dumps(jobs, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    factory = make_mission.build_factory(jobs, args.slug, str(flat_path), args.concurrency, args.max_turns, sdk=args.sdk, model=args.model)
    model_label = f"{args.sdk}/{args.model}" if args.model else args.sdk
    factory["description"] = f"chain reviewer {args.slug} (pass {doc['pass']}): {len(jobs)} {model_label} reviewer jobs, {doc['expected']['items']} reports"
    for agent in factory["waves"][0]["agents"]:
        agent["name"] = agent["name"].replace("read-", "review-", 1)
        agent["tools"] = ["Read", "Write", "Bash"]
    factory["waves"][0]["slug"] = "reviewers"
    out = flat_path.with_name(f"factory-{args.slug}.json")
    out.write_text(json.dumps(factory, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"wrote {flat_path.relative_to(REPO).as_posix()} and {out.relative_to(REPO).as_posix()} ({len(jobs)} agents, concurrency {args.concurrency}, model {model_label})")
    print(f"run: python -X utf8 datasets/hadith-data/chain-reader/conduction/run_tranche.py --factory {out.relative_to(REPO).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
