"""Reading a batch's review passes per item (reviewer/README-v1_1.md §1): a pass is "1", "2" or a re-queue round of one ("1r", "1r2", ...). Used by the builder (second pass, re-queue) and the recorder."""

from __future__ import annotations

import json
import re
from pathlib import Path

from review_rules_v1_1 import PROMPT_VERSION
from validate_review_v1_1 import validate_output


def packets_dir(out: Path, label: str) -> Path:
    return out / ("packets" if label == "1" else f"packets-pass-{label}")


def outputs_dir(out: Path, label: str) -> Path:
    return out / "outputs" / f"pass-{label}"


def labels(out: Path, base: str) -> list[str]:
    """The pass `base` and its re-queue rounds that have packets, in order: ["1", "1r", "1r2"]."""
    found = [base] if packets_dir(out, base).is_dir() else []
    n = 1
    while packets_dir(out, f"{base}r{'' if n == 1 else n}").is_dir():
        found.append(f"{base}r{'' if n == 1 else n}")
        n += 1
    return found


def collect(out: Path, base: str, prompt_version: str = PROMPT_VERSION, allow_out_of_order: bool = False) -> dict:
    """Per item of the base pass: its first valid review over the pass and its re-queue rounds, else why it is invalid.
    {"items": {id: packet item}, "reviews": {id: (review, label)}, "problems": {id: reason}, "invalid_outputs": [...], "ids": [ids of the base pass in packet order]}"""
    items, reviews, problems, invalid_outputs, ids = {}, {}, {}, [], []
    for number, label in enumerate(labels(out, base)):
        for packet_path in sorted(packets_dir(out, label).glob("packet-*.json")):
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            output_path = outputs_dir(out, label) / packet_path.name.replace(".json", ".output.json")
            for item in packet["items"]:
                items.setdefault(item["id"], item)
                if number == 0:
                    ids.append(item["id"])
            try:
                output = json.loads(output_path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                output = None
                for item in packet["items"]:
                    if item["id"] not in reviews:
                        problems[item["id"]] = f"pass {label}: no output file"
                continue
            except json.JSONDecodeError as error:
                invalid_outputs.append(f"{label}/{packet_path.name}: not JSON ({error})")
                for item in packet["items"]:
                    if item["id"] not in reviews:
                        problems[item["id"]] = f"pass {label}: output is not JSON"
                continue
            result = validate_output(output, packet, prompt_version, allow_out_of_order)
            if result["header_errors"]:
                invalid_outputs.append(f"{label}/{packet_path.name}: {result['header_errors'][0]}")
            for item in packet["items"]:
                i = item["id"]
                if i in reviews:
                    continue
                if result["items"][i]:
                    problems[i] = f"pass {label}: {result['items'][i][0]}"
                else:
                    reviews[i] = (result["reviews"][i], label)
                    problems.pop(i, None)
    return {"items": items, "reviews": reviews, "problems": {i: p for i, p in problems.items() if i not in reviews}, "invalid_outputs": invalid_outputs, "ids": ids}


def next_requeue_label(out: Path, base: str) -> str:
    existing = labels(out, base)
    n = len(existing)                                   # base only -> "1r"; base + 1r -> "1r2"
    return f"{base}r" if n == 1 else f"{base}r{n}"


def pass_of(label: str) -> int:
    return int(re.match(r"\d+", label).group())
