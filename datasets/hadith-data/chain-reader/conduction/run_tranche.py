"""Launch (or resume) a factory on a running Conduction server and wait for it. See README.md."""
import argparse
import json
import pathlib
import sys
import time
import urllib.request

REPO = pathlib.Path(__file__).resolve().parents[4]


def call(base, path, body=None):
    request = urllib.request.Request(base + path, data=None if body is None else json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read())


ap = argparse.ArgumentParser()
ap.add_argument("--factory", help="factory path relative to the repo root (make_mission.py prints it)")
ap.add_argument("--resume", help="factory_run_id to resume instead of launching")
ap.add_argument("--base", default="http://127.0.0.1:8000")
ap.add_argument("--timeout-min", type=int, default=40)
args = ap.parse_args()
if args.resume:
    run_id = args.resume
    print(call(args.base, f"/api/factory/runs/{run_id}/resume", {}))
else:
    launched = call(args.base, "/api/factory/runs", {"target_repo": str(REPO), "factory_path": args.factory})
    run_id = launched["factory_run_id"]
    print("launched", run_id)
deadline = time.time() + args.timeout_min * 60
state = {}
while time.time() < deadline:
    state = call(args.base, f"/api/factory/runs/{run_id}")
    status = state.get("status")
    print(time.strftime("%H:%M:%S"), status, [w.get("status") for w in state.get("waves", [])], flush=True)
    if status in ("completed", "failed", "interrupted"):
        break
    time.sleep(20)
else:
    print(f"not finished after {args.timeout_min} min; interrupt with POST /api/factory/runs/{run_id}/interrupt")
    sys.exit(2)
print(json.dumps(state, indent=1)[:3000])
sys.exit(0 if state.get("status") == "completed" else 1)
