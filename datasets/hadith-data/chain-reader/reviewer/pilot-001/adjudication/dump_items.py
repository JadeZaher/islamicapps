"""Print every pilot item with the judge's verdict and the reviewer's pass-1 review, for a human (or model) adjudicator to read.

    python -B -X utf8 reviewer/pilot-001/adjudication/dump_items.py [--only cr1-xxxx,...] [--packet 04] > out.txt      (from chain-reader/)

Reads packets/, outputs/pass-1/, private/key.tsv. Each review of packet 04 is validated alone (validate_review), so one invalid corrected reading does not hide the other nine.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent
sys.path.insert(0, str(PILOT.parent))
from validate_review import validate_review  # noqa: E402


def judge_class(row: dict) -> str:
    if row["judge_reader"] == "W" or row["judge_group"] == "genuine_route":
        return "wrong"
    if row["judge_reader"] in ("R", "RO"):
        return "right"
    return "cannot_tell"


def route_text(route: dict) -> str:
    return " > ".join(f"{link['surface']}" + (f"[{link['kind']}]" if link["kind"] not in ("narrator", "compiler_head") else "") for link in route["links"][1:])


def levels_text(reading: dict) -> list[str]:
    out = []
    for index, group in enumerate(reading.get("groups") or []):
        flags = " ".join(f"{k}={group[k]}" for k in ("variant", "saying", "saying_opens") if k in group)
        levels = " > ".join(" | ".join(i["surface"] + (f"[{i['kind']}]" if i.get("kind") != "narrator" else "") + (f"#{i['occurrence']}" if "occurrence" in i else "") for i in level) for level in group["levels"])
        out.append(f"  g{index} {flags}: {levels}")
    tail = reading.get("shared_tail")
    if tail:
        out.append("  tail: " + " > ".join(" | ".join(i["surface"] for i in level) for level in tail))
    return out


def load():
    with (PILOT / "private" / "key.tsv").open(encoding="utf-8", newline="") as handle:
        key = {row["opaque"]: row for row in csv.DictReader(handle, delimiter="\t")}
    items, reviews, packet_of = {}, {}, {}
    for packet_path in sorted((PILOT / "packets").glob("packet-*.json")):
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        number = packet_path.stem.split("-")[1]
        for item in packet["items"]:
            items[item["id"]] = item
            packet_of[item["id"]] = number
        output = json.loads((PILOT / "outputs" / "pass-1" / f"packet-{number}.output.json").read_text(encoding="utf-8"))
        for review in output["reviews"]:
            reviews[review["id"]] = review
    return key, items, reviews, packet_of


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only")
    parser.add_argument("--packet")
    args = parser.parse_args(argv)
    key, items, reviews, packet_of = load()
    only = set(args.only.split(",")) if args.only else None
    for opaque, item in items.items():
        if only and opaque not in only:
            continue
        if args.packet and packet_of[opaque] != args.packet:
            continue
        row, review = key[opaque], reviews.get(opaque)
        errors = validate_review(review, item) if review else ["no review"]
        print("=" * 100)
        print(f"{opaque} packet {packet_of[opaque]} set={row['set']} status={item['status']} JUDGE={judge_class(row)} ({row['judge_reader']}/{row['judge_group']}) agree={item['readers_agree']}")
        print(f"judge quote: {row['judge_quote']}")
        print(f"holds: {[h['code'] for h in item['holds']]}")
        work = item["context"]["work"]
        print(f"work: {work['name']} | {work.get('convention', '')}")
        for prev in item["context"].get("previous_reports", [])[:2]:
            print(f"  {prev.get('ref')}: {str(prev.get('chain_text', ''))[:300]}")
        print("TEXT:", item["text"])
        for name in ("A", "B"):
            reader = item["readers"][name]
            if name == "B" and item["readers_agree"]:
                print("B: (agrees)")
                continue
            print(f"{name}: valid={reader.get('valid')} needs_ruling={reader.get('needs_ruling')}")
            for route in reader.get("routes") or []:
                print("   R:", route_text(route))
            for group in reader.get("variant_groups") or []:
                print("   V:", json.dumps(group, ensure_ascii=False)[:300])
            for note in reader.get("notes") or []:
                print("   note:", note[:400])
        print("stored:", [" > ".join(b["surfaces"]) for b in item["stored_chain"] or []])
        print(f"REVIEW: {review['decision']} unc={review['uncertainty']} q={review.get('question')} valid={'yes' if not errors else errors}")
        for reason in review["reasons"]:
            print(f"   - {reason['claim']} [{reason['source']}: «{reason['quote']}»]")
        for verdict in review["variant_verdicts"]:
            print(f"   vv {verdict['group']}: {verdict['verdict']} «{verdict['quote']}»")
        if review.get("corrected_reading"):
            print("   CORRECTED:")
            print("\n".join(levels_text(review["corrected_reading"])))
            for note in review["corrected_reading"].get("notes") or []:
                print("     cnote:", note[:400])
        if review.get("uncertainty_note"):
            print("   unc_note:", review["uncertainty_note"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
