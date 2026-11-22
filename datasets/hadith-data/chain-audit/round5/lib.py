"""Round-5 recalibration helpers: labelled units (tuning = rounds 2/3, held-out = round 4) and the gate evaluated on them.

Read-only. Run from the repository root with `python -I`; see README.md in this directory.
"""

from __future__ import annotations

import collections
import csv
import importlib.util
import math
import pickle
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
AUDIT = ROOT / "datasets/hadith-data/chain-audit"
DEV = ROOT / "datasets/hadith-data/development"
sys.path[:0] = [str(ROOT / "datasets/hadith-data/pg_export"), str(ROOT / "datasets/hadith-data"), str(ROOT / "datasets"),
                str(AUDIT / "structure-gate")]
import measure  # noqa: E402  (round 4's loader and labelled units, reused unchanged)
import chain_structure as cs  # noqa: E402

READ_R3 = DEV / "chain-builder-r3-2026-11-22/projection-b2"          # 2026.11.22.8: what rounds 2/3 read
BEFORE_R2 = DEV / "chain-builder-r2-2026-11-22/projection-m3"
READ_R4 = DEV / "chain-structure-gate-2026-11-22/projection"        # 2026.11.22.9: what round 4 read (production)
ROUND4_COMMIT = "83c5e2f"


def load_round4_gate():
    """The gate as committed in round 4 (git), loaded under another module name, for before -> after."""
    source = subprocess.run(["git", "show", f"{ROUND4_COMMIT}:datasets/hadith-data/pg_export/chain_structure.py"], cwd=ROOT,
                            capture_output=True, check=True).stdout
    path = Path(tempfile.mkdtemp()) / "chain_structure_r4.py"
    path.write_bytes(source)
    spec = importlib.util.spec_from_file_location("chain_structure_r4", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def cached(path: Path, build):
    if path.exists():
        return pickle.loads(path.read_bytes())
    value = build()
    path.write_bytes(pickle.dumps(value))
    return value


def held_out_units(reports: dict) -> list[dict]:
    """Round 4's 370 chain readings (310 sampled among chains the round-4 gate checked, 60 among those it withheld)."""
    units = []
    for row in csv.DictReader((AUDIT / "round4/sample_check.csv").open(encoding="utf-8-sig")):
        if row["lane"].startswith("pair_"):
            continue
        report = reports[row["hadith_id"]]
        units.append({"set": "held_out", "hadith_id": row["hadith_id"], "chain_id": row["chain_id"], "group": measure.group_of(row["hadith_id"]),
                      "defect": row["verdict"] == "defect", "round4_stratum": "withheld" if row["lane"].startswith("u_") else "checked",
                      "work": report["collection"].split(":", 1)[1], "kind": row["kind"], "note": row["note"]})
    return units


def wilson(k: int, n: int, z: float = 1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - m), min(1, c + m))


def fmt(k: int, n: int) -> str:
    if n == 0:
        return "0/0"
    low, high = wilson(k, n)
    return f"{k}/{n} = {100 * k / n:.1f}% ({100 * low:.1f}-{100 * high:.1f})"


def assess_units(module, reports: dict, units: list[dict]) -> dict:
    """Per unit: set of reason codes (measured-only included) from `module` on its projection's report; retire counts."""
    assessed = {}
    for hadith_id in {unit["hadith_id"] for unit in units}:
        report = reports[hadith_id]
        tradition = next(name for prefix, name in measure.TRADITION.items() if report["collection"].startswith(prefix))
        work = report["collection"].split(":", 1)[1]
        reasons = module.assess(module.ReportChains(report["detection"], [c["surfaces"] for c in report["chains"]], tradition,
                                                    [c["inherited"] for c in report["chains"]], hadith_id.startswith("hadith:thaqalayn:"),
                                                    work, report["from_text"]), measure_all=True)
        assessed[hadith_id] = {"retire": module.retire_reason(work, tradition, report["text"], report["from_text"]),
                               "reasons": {c["id"]: set(r) for c, r in zip(report["chains"], reasons)}}
    return assessed


def unit_reasons(unit: dict, assessed: dict) -> set[str]:
    result = assessed[unit["hadith_id"]]
    if result["retire"]:
        return {result["retire"]}
    if unit["chain_id"]:
        return result["reasons"][unit["chain_id"]]
    return set().union(*result["reasons"].values())
