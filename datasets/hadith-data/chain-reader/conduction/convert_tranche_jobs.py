"""Convert tranches/tranche-NN/jobs.json (shura-chain-reader-jobs/1) to the flat list make_mission.py reads. Usage: convert_tranche_jobs.py <tranche jobs.json> <out.json>"""
import json
import pathlib
import sys

source = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
jobs = []
for job in source["jobs"]:
    out_dir = pathlib.Path(job["output_dir"])
    expected = [str(out_dir / name) for name in job["output_files"]]
    assert len(expected) == job["expected_files"], job["job_id"]
    jobs.append({
        "job_id": job["job_id"], "pass": job["pass"], "packets": job["packets"],
        "prompt_file": source["prompt"]["path"], "output_dir": job["output_dir"],
        "run_txt": job["run_file"], "run_id": job["run_id"],
        "expected_files": expected, "instruction": job["instruction"],
    })
pathlib.Path(sys.argv[2]).write_text(json.dumps(jobs, indent=1), encoding="utf-8", newline="\n")
print(f"{len(jobs)} jobs, {sum(len(j['expected_files']) for j in jobs)} expected files")
