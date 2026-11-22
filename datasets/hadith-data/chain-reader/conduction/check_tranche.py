"""Gate: every expected file exists and parses; every run_id has a RUN.txt line. Exit 1 on any gap."""
import argparse
import json
import pathlib
import sys

ap = argparse.ArgumentParser()
ap.add_argument("--jobs", required=True)
args = ap.parse_args()
problems = []
for job in json.loads(pathlib.Path(args.jobs).read_text(encoding="utf-8")):
    for name in job["expected_files"]:
        path = pathlib.Path(name)
        if not path.is_file():
            problems.append(f"missing {name}")
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except ValueError as error:
            problems.append(f"unparsable {name}: {error}")
    run_txt = pathlib.Path(job["run_txt"])
    text = run_txt.read_text(encoding="utf-8") if run_txt.is_file() else ""
    if f"run_id={job['run_id']} " not in text:
        problems.append(f"no RUN.txt line for {job['run_id']}")
print("\n".join(problems) or f"ok: all expected files present and parse")
sys.exit(1 if problems else 0)
