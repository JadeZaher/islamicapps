"""Build v3_4/examples/example-packets.jsonl: the v3.2 example packets prompt v3.4 keeps (unchanged) plus three real reports of the third-round rulings, shortened at a stated phrase.

    python -B -X utf8 v3_4/tools/build_example_packets_v3_4.py            (from chain-reader/)

A new packet is {"id", "text": <the real text cut after a stated phrase>, "context": {"work"}, "source": {"packet", "cut_after"}}: the text is a PREFIX of the real text (a test checks it),
so every surface an example writes is words of the real report. See v3_4/AGENTS.md §prompt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V34 = HERE.parent
ROOT = V34.parent
KEPT_V3_2 = ("t01-6d7565", "b1-05f29e")
# report id -> (tranche, the phrase the shown text ends with, kept inclusive; None keeps the whole text)
NEW = {"t02-1061e3": ("02", None),                                     # a mutaba'a written as a route by both passes (tranche-02 judge)
       "t01-a20cb6": ("01", "فقال: يأكلون الحرام"),   # the owner's narrated encounter
       "t01-520f51": ("01", None)}                                     # two sayings, each with its own isnad


def tranche_packets(tranche: str, wanted: set[str]) -> dict[str, dict]:
    found = {}
    for path in sorted((ROOT / "tranches" / f"tranche-{tranche}" / "packets").glob("packet-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row["id"] in wanted:
                    found[row["id"]] = row
    return found


def main() -> None:
    old = {row["id"]: row for row in (json.loads(line) for line in (ROOT / "v3_2" / "examples" / "example-packets.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())}
    rows = [old[report_id] for report_id in KEPT_V3_2]
    for report_id, (tranche, cut) in NEW.items():
        packet = tranche_packets(tranche, {report_id})[report_id]
        text = packet["text"] if cut is None else packet["text"][: packet["text"].index(cut) + len(cut)]
        rows.append({"id": report_id, "text": text, "context": {"work": dict(packet["context"]["work"])}, "source": {"packet": f"tranches/tranche-{tranche}/packets", "cut_after": cut}})
    (V34 / "examples").mkdir(exist_ok=True)
    (V34 / "examples" / "example-packets.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(rows)} example packets")


if __name__ == "__main__":
    main()
