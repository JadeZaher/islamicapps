"""Build v3_2/examples/example-packets.jsonl: v3.1's four batch-001 example packets (unchanged) plus four real tranche-01 reports, shortened, that the judge named as reader errors.

    python -B -X utf8 v3_2/tools/build_example_packets_v3_2.py            (from chain-reader/)

Each new packet is {"id": "t01-xxxxxx", "text": <the real text cut at a stated phrase>, "context": {"work": ...}, "source": {"packet", "cut_after"}}: the text is a PREFIX of the packet's real text (a test checks it),
so every surface the example writes is words of the real report. See v3_2/AGENTS.md §prompt.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
V32 = HERE.parent
ROOT = V32.parent
TRANCHE = ROOT / "tranches" / "tranche-01" / "packets"
# report id -> the phrase the shown text ends with (kept inclusive); None keeps the whole text
CUTS = {"t01-30fa50": None, "t01-6d7565": "أن تجعل لله ندا وهو خلقك ‏\"‏‏.‏", "t01-05c2d0": "يمتحن بقول الله عز وجل", "t01-0706da": "قالت افتقدت النبي صلى الله عليه وسلم ذات ليلة"}


def main() -> None:
    packets = {}
    for path in sorted(TRANCHE.glob("packet-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row["id"] in CUTS:
                    packets[row["id"]] = row
    rows = [json.loads(line) for line in (V32 / "examples" / "example-packets-v3_1.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    for report_id, cut in CUTS.items():
        packet = packets[report_id]
        text = packet["text"]
        if cut is not None:
            end = text.index(cut) + len(cut)
            text = text[:end]
        work = {key: value for key, value in packet["context"]["work"].items() if key in ("key", "tradition")}
        rows.append({"id": report_id, "text": text, "context": {"work": {**packet["context"]["work"]}}, "source": {"packet": "tranches/tranche-01/packets", "cut_after": cut, "shown_work": work}})
    (V32 / "examples" / "example-packets.jsonl").write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8", newline="\n")
    print(f"{len(rows)} example packets")


if __name__ == "__main__":
    main()
