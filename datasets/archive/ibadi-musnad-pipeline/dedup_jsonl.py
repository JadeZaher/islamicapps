#!/usr/bin/env python3
"""
dedup_jsonl.py — Remove duplicate rows from a JSONL file, keeping first occurrence.
Usage: python dedup_jsonl.py --input file.jsonl --id-field id
"""
import argparse, io, json, os, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--id-field", default="id")
    args = parser.parse_args()

    seen = set()
    kept = []
    dupes = 0
    with open(args.input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rid = str(obj.get(args.id_field, ""))
            if rid in seen:
                dupes += 1
            else:
                seen.add(rid)
                kept.append(line)

    # Write back in place
    with open(args.input, "w", encoding="utf-8") as f:
        for line in kept:
            f.write(line + "\n")

    print(f"Kept {len(kept)} unique rows, removed {dupes} duplicates.")


if __name__ == "__main__":
    main()
