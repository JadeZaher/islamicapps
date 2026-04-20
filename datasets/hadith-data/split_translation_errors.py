#!/usr/bin/env python3
"""
split_translation_errors.py
============================
Post-process translated JSONL to separate good translations from LLM refusals.
Safe to run while translation is still in progress — reads what's available.

Outputs:
  - classical_translations_clean.jsonl   (good translations)
  - classical_translations_refused.jsonl (LLM refusals, for re-translation)
  - classical_translations_failed.jsonl  (API failures / empty)

Usage:
    python datasets/hadith-data/split_translation_errors.py
    python datasets/hadith-data/split_translation_errors.py --input <path> --check-only
"""

import argparse
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_INPUT = os.path.join(SCRIPT_DIR, "classical_collections_translated.jsonl")
OUT_CLEAN = os.path.join(SCRIPT_DIR, "classical_translations_clean.jsonl")
OUT_REFUSED = os.path.join(SCRIPT_DIR, "classical_translations_refused.jsonl")
OUT_FAILED = os.path.join(SCRIPT_DIR, "classical_translations_failed.jsonl")

# Patterns that indicate the model refused to translate
REFUSAL_PATTERNS = [
    "i cannot",
    "i can't",
    "i'm unable",
    "i am unable",
    "i apologize",
    "i'm not able",
    "i cannot fulfill",
    "i can't fulfill",
    "i can't assist",
    "i cannot assist",
    "i'm sorry",
    "as an ai",
    "i can provide information",
    "could you please provide the complete",
    "i cannot translate",
    "i'm not going to",
    "this text contains",
    "i won't",
    "not appropriate",
    "content warning",
    "i must decline",
    "i need to flag",
]

# Patterns that indicate a hallucination / not a real translation
HALLUCINATION_PATTERNS = [
    "the prophet (peace be upon him) said:" * 3,  # repeated stock phrases
]


def is_refusal(text_en: str) -> bool:
    """Check if translation text is an LLM refusal."""
    lower = text_en.lower().strip()
    # Check first 200 chars for refusal patterns (refusals are always at the start)
    check_region = lower[:200]
    for pattern in REFUSAL_PATTERNS:
        if pattern in check_region:
            return True
    return False


def is_failed(row: dict) -> bool:
    """Check if translation failed at the API level."""
    if row.get("_translation_error"):
        return True
    if row.get("_skip_reason"):
        return True
    text_en = str(row.get("text_en", "")).strip()
    if not text_en:
        return True
    return False


def main():
    parser = argparse.ArgumentParser(description="Split translation output into clean/refused/failed")
    parser.add_argument("--input", default=DEFAULT_INPUT, help="Input translated JSONL")
    parser.add_argument("--check-only", action="store_true", help="Just print stats, don't write files")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)

    # Read all rows (skip corrupt lines)
    rows = []
    corrupt_lines = 0
    with open(args.input, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    corrupt_lines += 1
    if corrupt_lines:
        print(f"  WARNING: skipped {corrupt_lines} corrupt/unparseable lines")

    print(f"Read {len(rows):,} translated rows from {args.input}")

    # Classify
    clean = []
    refused = []
    failed = []

    for row in rows:
        if is_failed(row):
            failed.append(row)
        elif is_refusal(str(row.get("text_en", ""))):
            refused.append(row)
        else:
            clean.append(row)

    # Stats by source
    sources = {}
    for category, label in [(clean, "clean"), (refused, "refused"), (failed, "failed")]:
        for row in category:
            src = row.get("source_canonical", row.get("source", "unknown"))
            if src not in sources:
                sources[src] = {"clean": 0, "refused": 0, "failed": 0}
            sources[src][label] += 1

    # Print summary
    print(f"\n{'=' * 65}")
    print(f"TRANSLATION QUALITY REPORT")
    print(f"{'=' * 65}")
    print(f"\n  {'Source':<28s} {'Clean':>7s} {'Refused':>8s} {'Failed':>7s} {'Total':>7s}")
    print(f"  {'-'*28} {'-'*7} {'-'*8} {'-'*7} {'-'*7}")
    for src in sorted(sources.keys()):
        s = sources[src]
        total = s["clean"] + s["refused"] + s["failed"]
        print(f"  {src:<28s} {s['clean']:>7,} {s['refused']:>8,} {s['failed']:>7,} {total:>7,}")

    total_clean = len(clean)
    total_refused = len(refused)
    total_failed = len(failed)
    total_all = len(rows)
    print(f"  {'-'*28} {'-'*7} {'-'*8} {'-'*7} {'-'*7}")
    print(f"  {'TOTAL':<28s} {total_clean:>7,} {total_refused:>8,} {total_failed:>7,} {total_all:>7,}")

    if total_all > 0:
        print(f"\n  Clean rate: {100*total_clean/total_all:.1f}%")
        print(f"  Refusal rate: {100*total_refused/total_all:.1f}%")
        print(f"  Failure rate: {100*total_failed/total_all:.1f}%")

    # Sample refusals
    if refused:
        print(f"\n  Sample refusals:")
        for r in refused[:5]:
            text = str(r.get("text_en", ""))[:150]
            print(f"    [{r.get('id','')}] {text}")

    if args.check_only:
        print("\n  (--check-only mode, no files written)")
        return

    # Write output files
    print(f"\nWriting {len(clean):,} clean translations to {OUT_CLEAN}")
    with open(OUT_CLEAN, "w", encoding="utf-8") as f:
        for row in clean:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Writing {len(refused):,} refused translations to {OUT_REFUSED}")
    with open(OUT_REFUSED, "w", encoding="utf-8") as f:
        for row in refused:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Writing {len(failed):,} failed translations to {OUT_FAILED}")
    with open(OUT_FAILED, "w", encoding="utf-8") as f:
        for row in failed:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    if refused:
        print(f"\n  TIP: Re-translate refusals with a different model:")
        print(f"    python datasets/translate_ollama_generic.py \\")
        print(f"      --input {OUT_REFUSED} \\")
        print(f"      --output datasets/hadith-data/classical_refused_retranslated.jsonl \\")
        print(f"      --source-field text_ar --dest-field text_en \\")
        print(f"      --prompt-file datasets/hadith-data/classical_translation_prompt.txt \\")
        print(f"      --model llama3.1:8b --overwrite")


if __name__ == "__main__":
    main()
