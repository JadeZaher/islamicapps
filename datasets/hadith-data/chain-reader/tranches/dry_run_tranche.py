"""Dry-run one tranche through the chain-fix pipeline, applying nothing (tranches/AGENTS.md §Dry run).

    python -B -X utf8 tranches/dry_run_tranche.py --tranche 01 --reader-prompt v3_1 [--variant-notes-supported] [--tool v3_3 --only <ids file> --label <name>]

Builds the envelopes with `v3_2/to_submission_v3_2.py`, checks each with `chain-fix-submit --check-only --database production` (read-only;
a refused fix is dropped and its reason kept, so one bad fix does not hide the others), records the clean ones in a SCRATCH store,
decides there, and rehearses the database apply (`chain-fix-apply.ts --dry-run --no-mirror`: every report's transaction is rolled
back). The real store, the overrides file and the database are never written. Everything lands in `development/tranche-dry-run-*`
(git-ignored); private ids stay there.
"""

from __future__ import annotations

import argparse
import gzip
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
READER = HERE.parent
ROOT = READER.parents[2]
NODE = ["node", "--import", "tsx"]
SUBMIT = str(ROOT / "reviews" / "ai" / "tools" / "chain-fix-submit.ts")
DECIDE = str(ROOT / "reviews" / "ai" / "tools" / "chain-fix-decide.ts")
APPLY = str(ROOT / "src" / "db" / "ops" / "chain-fix-apply.ts")
FAIL_LINE = re.compile(r"^FAIL fixes\[(\d+)\] \(([^)]*)\): (.*)$")


def run(command: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, encoding="utf-8")


def group_of(report: dict) -> str:
    if report["tradition"] == "sunni":
        return "six Sunni books"
    return "al-Faqih" if report["work"] == "man-la-yahduruhu-al-faqih" else "other Imami"


def clean_envelope(envelope: Path, reports: Path, flag: list[str], scratch: Path, refused: dict[str, str]) -> Path | None:
    """The envelope without the fixes the check refuses (one round of `--check-only` per drop, until it passes); None when nothing is left."""
    document = json.loads(envelope.read_text(encoding="utf-8"))
    current = envelope
    for round_number in range(8):
        result = run([*NODE, SUBMIT, "--envelope", str(current), "--reports", str(reports), "--database", "production", "--store", str(scratch / "check-store"),
                      "--check-only", *flag])
        if result.returncode == 0:
            return current if document["fixes"] else None
        failures = [FAIL_LINE.match(line) for line in result.stderr.splitlines()]
        failures = [m for m in failures if m]
        if not failures:                                          # a whole-envelope problem: every fix in it is refused
            reason = next((line for line in result.stderr.splitlines() if line.startswith("FAIL")), result.stderr.strip()[:200])
            for fix in document["fixes"]:
                refused[fix.get("reader_output_v3", {}).get("id") or fix["output"]["id"]] = reason
            return None
        drop = {int(m.group(1)) for m in failures}
        for m in failures:
            refused[m.group(2)] = m.group(3)
        # An index is the fix's place in the file just checked: keep the file in step.
        document["fixes"] = [fix for index, fix in enumerate(document["fixes"]) if index not in drop]
        if not document["fixes"]:
            return None
        current = scratch / f"{envelope.stem}.clean{round_number}.json"
        current.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tranche", required=True)
    parser.add_argument("--reader-prompt", choices=("v3", "v3_1", "v3_2"), required=True)
    parser.add_argument("--variant-notes-supported", action="store_true")
    parser.add_argument("--out", default=str(ROOT / "datasets" / "hadith-data" / "development" / "tranche-dry-run-2026-11-22"))
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--tool", choices=("v3_2", "v3_3"), default="v3_2", help="the reader tool that builds the envelopes (v3_3: the pipeline engine runs its corrected holds)")
    parser.add_argument("--only", help="ids file: build envelopes for these readings only (an apply list)")
    parser.add_argument("--label", help="scratch folder name (default t<NN>-with|without)")
    parser.add_argument("--baseline", help="a finished run of the same tranche (the 'without' run): only the fixes it did not have are rehearsed, its plan stands for the rest")
    args = parser.parse_args()
    label = args.label or f"t{args.tranche}-{'with' if args.variant_notes_supported else 'without'}"
    scratch = Path(args.out) / label
    scratch.mkdir(parents=True, exist_ok=True)
    tranche = READER / "tranches" / f"tranche-{args.tranche}"
    reports = tranche / "private" / "reports.jsonl"
    flag = ["--variant-notes-supported"] if args.variant_notes_supported else []
    only = ["--only", str(Path(args.only).resolve())] if args.only else []
    built = run([sys.executable, "-B", "-X", "utf8", f"{args.tool}/to_submission_{args.tool}.py", "--packets", str(tranche / "packets"), "--reports", str(reports),
                 "--pass-a", str(tranche / "outputs" / "pass-a"), "--pass-b", str(tranche / "outputs" / "pass-b"), "--out", str(scratch),
                 "--batch", f"t{args.tranche}", "--reader-prompt", args.reader_prompt, *flag, *only], cwd=READER)
    print(built.stderr.strip(), file=sys.stderr)
    report_rows = {row["id"]: row for row in (json.loads(l) for l in reports.read_text(encoding="utf-8").splitlines() if l.strip())}
    envelopes = sorted(scratch.glob("packet-*.envelope.json"))
    eligible = {}                                                  # id -> envelope kind
    for envelope in envelopes:
        for fix in json.loads(envelope.read_text(encoding="utf-8"))["fixes"]:
            eligible[(fix.get("reader_output_v3") or fix["output"])["id"]] = "no_chain" if ".no_chain." in envelope.name else "chain"
    refused: dict[str, str] = {}
    (scratch / "check-store").mkdir(exist_ok=True)
    with ThreadPoolExecutor(args.jobs) as pool:
        cleaned = list(pool.map(lambda e: clean_envelope(e, reports, flag, scratch, refused), envelopes))
    store = scratch / "store"
    overrides = scratch / "overrides.jsonl.gz"

    def record(envelope: Path) -> str:
        done = run([*NODE, SUBMIT, "--envelope", str(envelope), "--reports", str(reports), "--database", "production", "--store", str(store), *flag])
        return done.stderr if done.returncode else ""

    with ThreadPoolExecutor(args.jobs) as pool:
        problems = [p for p in pool.map(record, [c for c in cleaned if c]) if p]
    decided = run([*NODE, DECIDE, "--store", str(store), "--overrides", str(overrides)])
    rehearse = overrides
    inherited_plan: dict = {"reports": [], "skipped": []}
    if args.baseline:
        base_dir = Path(args.baseline)
        with gzip.open(base_dir / "overrides.jsonl.gz", "rt", encoding="utf-8") as handle:
            known = {row["fix_id"]: row for row in (json.loads(l) for l in handle if l.strip())}
        with gzip.open(overrides, "rt", encoding="utf-8") as handle:
            current = [json.loads(l) for l in handle if l.strip()]
        same = {row["fix_id"] for row in current if row["fix_id"] in known and known[row["fix_id"]] == row}
        rehearse = scratch / "overrides-delta.jsonl.gz"
        with gzip.open(rehearse, "wt", encoding="utf-8") as handle:
            handle.write("".join(json.dumps(row, ensure_ascii=False) + chr(10) for row in current if row["fix_id"] not in same))
        base_plan = json.loads((base_dir / "apply-plan.json").read_text(encoding="utf-8"))
        inherited_plan = {"reports": [r for r in base_plan["reports"] if r["fix_id"] in same], "skipped": [r for r in base_plan["skipped"] if r["fix_id"] in same]}
    applied = run([*NODE, APPLY, "--database", "production", "--confirm-production", "--dry-run", "--no-mirror", "--store", str(store),
                   "--overrides", str(rehearse), "--plan", str(scratch / "apply-plan.json")])
    if args.baseline and applied.returncode == 0:
        delta = json.loads((scratch / "apply-plan.json").read_text(encoding="utf-8"))
        delta["reports"] = inherited_plan["reports"] + delta["reports"]
        delta["skipped"] = inherited_plan["skipped"] + delta["skipped"]
        delta["merged_with_baseline"] = str(args.baseline)
        (scratch / "apply-plan.json").write_text(json.dumps(delta, ensure_ascii=False, indent=1), encoding="utf-8")
    (scratch / "apply.log").write_text(applied.stdout + applied.stderr, encoding="utf-8")
    (scratch / "decide.log").write_text(decided.stdout + decided.stderr, encoding="utf-8")
    (scratch / "refused.json").write_text(json.dumps(refused, ensure_ascii=False, indent=1), encoding="utf-8")
    (scratch / "submit-problems.txt").write_text("\n".join(problems), encoding="utf-8")
    print(f"{label}: eligible {len(eligible)}, refused {len(refused)}, decide exit {decided.returncode}, apply exit {applied.returncode}", file=sys.stderr)
    return 0 if decided.returncode == 0 and applied.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
