"""Cost sizing of a full run over the live uncertain population (reports, packets, reader runs for two passes, characters). No model is run.

    python -B -X utf8 v3/sizing_v3.py                (from chain-reader/; reads batch-001/private/population.jsonl and batch-001/packets)

Measured: the reader text of every uncertain report (population.jsonl, exact) and the mean context size per work group in batch-001's packets (3,000-character cap, previous reports
on top). Estimated: groups that batch-001 did not sample (al-Kafi, Ahmad/Darimi/Muwatta, Ibadi, Zaydi) take the mean of the nearest sampled group; that is stated in the output.
Packets of 20, two passes, two packets (40 reports) per reader agent, the prompt read once per agent run. Characters, not tokens: Arabic text with diacritics costs roughly
1 token per 2.5-3 characters in the pilot's measurements (README of context/), so tokens are shown as a range.
"""

from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BATCH = HERE / "batch-001"
GROUP = {"sunni:bukhari": "sunni_six", "sunni:muslim": "sunni_six", "sunni:nasai": "sunni_six", "sunni:tirmidhi": "sunni_six", "sunni:abudawud": "sunni_six", "sunni:ibnmajah": "sunni_six",
         "imami:man-la-yahduruhu-al-faqih": "faqih", "imami:al-kafi": "kafi"}
NEAREST = {"kafi": "imami_other", "sunni_other": "sunni_six", "ibadi_zaydi": "imami_other"}
PACKET_SIZE, PACKETS_PER_AGENT, PASSES = 20, 2, 2


def group_of(work: str) -> str:
    if work in GROUP:
        return GROUP[work]
    if work.startswith("sunni:"):
        return "sunni_other"
    if work.startswith(("ibadi:", "zaydi:")):
        return "ibadi_zaydi"
    return "imami_other"


def main() -> int:
    population = [json.loads(line) for line in (BATCH / "private" / "population.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    manifest = json.loads((BATCH / "packets" / "manifest.json").read_text(encoding="utf-8"))
    context_by_group: dict[str, list[int]] = defaultdict(list)
    bytes_by_group: dict[str, list[int]] = defaultdict(list)
    for path in sorted((BATCH / "packets").glob("packet-*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                group = group_of(row["context"]["work"]["key"])
                context_by_group[group].append(len(json.dumps(row["context"], ensure_ascii=False)))
                bytes_by_group[group].append(len(line.encode("utf-8")))
    sampled = {g: sum(v) / len(v) for g, v in context_by_group.items()}
    reports_by_group: dict[str, int] = defaultdict(int)
    text_by_group: dict[str, int] = defaultdict(int)
    for row in population:
        group = group_of(row["work"])
        reports_by_group[group] += 1
        text_by_group[group] += row["reader_chars"]
    rows, total_context, total_text = {}, 0, 0
    for group in sorted(reports_by_group):
        basis = group if group in sampled else NEAREST[group]
        context_chars = round(sampled[basis] * reports_by_group[group])
        rows[group] = {"reports": reports_by_group[group], "text_chars": text_by_group[group], "mean_text_chars": round(text_by_group[group] / reports_by_group[group]), "context_chars_per_report": round(sampled[basis]),
                       "context_chars": context_chars, "context_basis": "measured in batch-001" if group in sampled else f"estimated from {basis}"}
        total_context += context_chars
        total_text += text_by_group[group]
    reports = len(population)
    packets = math.ceil(reports / PACKET_SIZE)
    agent_runs_per_pass = math.ceil(packets / PACKETS_PER_AGENT)
    prompt_chars = json.loads((HERE / "prompt-v3.json").read_text(encoding="utf-8"))["chars"]
    per_pass_chars = total_text + total_context + prompt_chars * agent_runs_per_pass
    out = {"population_reports": reports, "by_group": rows, "packets_of_20": packets, "packets_per_agent": PACKETS_PER_AGENT, "reports_per_agent": PACKET_SIZE * PACKETS_PER_AGENT, "passes": PASSES,
           "reader_agent_runs_per_pass": agent_runs_per_pass, "reader_agent_runs_two_passes": agent_runs_per_pass * PASSES, "prompt_chars": prompt_chars,
           "characters_read_per_pass": {"report_text": total_text, "context": total_context, "prompt_across_runs": prompt_chars * agent_runs_per_pass, "total": per_pass_chars},
           "characters_read_two_passes": per_pass_chars * PASSES, "tokens_two_passes_range": [round(per_pass_chars * PASSES / 3), round(per_pass_chars * PASSES / 2.5)],
           "packet_bytes_utf8": {"batch_001_mean_per_report": round(manifest["total_bytes"] / manifest["reports"]), "full_population_estimate": round(manifest["total_bytes"] / manifest["reports"] * reports)},
           "batch_001": {"reports": manifest["reports"], "packets": manifest["packets"], "reader_agent_runs_two_passes": math.ceil(manifest["packets"] / PACKETS_PER_AGENT) * PASSES}}
    (HERE / "sizing_v3.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
