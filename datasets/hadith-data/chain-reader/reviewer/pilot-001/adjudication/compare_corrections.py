"""Expand every pass-1 corrected reading with the reader tool and compare it to reader A's expanded reading (route keys, order-free).

    python -B -X utf8 reviewer/pilot-001/adjudication/compare_corrections.py      (from chain-reader/)

A correction whose expanded route keys equal reader A's (the packet's `routes`; back-reference links ignored, as score.py does) changes only representation (kinds, variant groups, notes); any route difference is printed.
See adjudication/README.md §method.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent
CHAIN_READER = PILOT.parent.parent
for path in (str(CHAIN_READER), str(CHAIN_READER / "v3_2"), str(CHAIN_READER / "v3_4")):
    if path not in sys.path:
        sys.path.insert(0, path)
import expand_v3_4  # noqa: E402


def route_keys(reading: dict) -> list[str]:
    return sorted(" > ".join(link["surface"] for link in route["links"] if link["kind"] not in ("compiler_head", "back_reference")) for route in reading["routes"])


def main() -> int:
    for packet_path in sorted((PILOT / "packets").glob("packet-*.json")):
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        output = json.loads((PILOT / "outputs" / "pass-1" / packet_path.name.replace(".json", ".output.json")).read_text(encoding="utf-8"))
        items = {item["id"]: item for item in packet["items"]}
        for review in output["reviews"]:
            if review["decision"] != "confirm_with_correction":
                continue
            item = items[review["id"]]
            c_reading, c_errors = expand_v3_4.expand(review["corrected_reading"], item["text"], item["context"])
            print("=" * 80)
            print(review["id"], packet_path.stem)
            if c_errors:
                print("  expand errors:", c_errors[:2])
                continue
            a_keys, c_keys = set(route_keys(item["readers"]["A"])), set(route_keys(c_reading))
            print(f"  same_routes={a_keys == c_keys}  routes A={len(a_keys)} corrected={len(c_keys)}")
            for key in sorted(a_keys - c_keys):
                print("  - A only:", key)
            for key in sorted(c_keys - a_keys):
                print("  + corrected only:", key)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
