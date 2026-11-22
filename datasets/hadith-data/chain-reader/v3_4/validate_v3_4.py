"""Mechanical acceptance of a v3.4 chain reader output: v3.2's validator (v3_2/validate_v3_2.py, imported) on the output without saying labels, then the labels (v3_4/AGENTS.md §sayings).

    python -B -X utf8 v3_4/validate_v3_4.py --packets <dir> --outputs <dir>

Output format `shura-chain-reader-output/3.4` = v3.2's format plus an optional `saying` + `saying_opens` on a group. A v3.2 tool rejects a labelled output (unknown group key):
read v3.4 outputs with v3.4 modules only. An unlabelled v3.4 output is a valid v3.2 output and the reverse.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for path in (str(ROOT), str(ROOT / "v3_2"), str(HERE)):
    if path not in sys.path:
        sys.path.insert(0, path)
import validate as v1  # noqa: E402
import validate_v3_2 as base  # noqa: E402
from expand_v3_4 import expand, saying_shape_errors, strip_sayings  # noqa: E402

with_default_fixes = base.with_default_fixes
quote_in = base.quote_in


def validate_chain(output: object, text: str, expected_id: str | None = None, context: dict | None = None) -> list[str]:
    """Error strings `code: detail`; empty means accepted."""
    output = with_default_fixes(output)
    errors = base.validate_chain(strip_sayings(output), text, expected_id, context) + saying_shape_errors(output)
    if errors or not isinstance(output, dict) or output.get("status") != "read":
        return errors
    _, expand_errors = expand(output, text, context)
    return [e for e in expand_errors if e.startswith("saying")]


def validate_v3_4(output: object, text: str, expected_id: str | None = None, context: dict | None = None) -> list[str]:
    return validate_chain(output, text, expected_id, context)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--packets", required=True)
    parser.add_argument("--outputs", required=True)
    args = parser.parse_args(argv)
    packets = {}
    for path in sorted(Path(args.packets).glob("packet-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                packets[row["id"]] = row
    bad = 0
    for report_id, row in packets.items():
        path = Path(args.outputs) / f"{report_id}.json"
        if not path.is_file():
            print(f"{report_id}\tmissing")
            bad += 1
            continue
        try:
            parsed, _ = v1.parse_output(path.read_text(encoding="utf-8"))
        except ValueError as error:
            print(f"{report_id}\tnot_json\t{error}")
            bad += 1
            continue
        errors = validate_v3_4(parsed, row["text"], report_id, row.get("context"))
        if errors:
            bad += 1
            print(f"{report_id}\tinvalid\t{errors[0]}")
    print(f"valid {len(packets) - bad}/{len(packets)}", file=sys.stderr)
    return 0 if not bad else 1


if __name__ == "__main__":
    raise SystemExit(main())
