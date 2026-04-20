#!/usr/bin/env python3
"""
Merge translated text_en from musnad_hadiths_en.jsonl back into musnad_hadiths.csv.
Overwrites the CSV in-place (backs up to .bak first).
"""
import csv
import json
import os
import shutil
import sys

CSV_PATH = os.path.join(os.path.dirname(__file__), "musnad_hadiths.csv")
JSONL_PATH = os.path.join(os.path.dirname(__file__), "musnad_hadiths_en.jsonl")
BACKUP_PATH = CSV_PATH + ".bak"


def main():
    if not os.path.exists(JSONL_PATH):
        print(f"ERROR: {JSONL_PATH} not found — run translation first.")
        sys.exit(1)

    # Load translations keyed by id
    translations = {}
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rid = obj.get("id", "")
            text_en = obj.get("text_en", "")
            if rid and text_en and not obj.get("_translation_error"):
                translations[rid] = text_en

    print(f"Loaded {len(translations)} translations from JSONL.")

    # Read CSV
    with open(CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Backup
    shutil.copy2(CSV_PATH, BACKUP_PATH)
    print(f"Backed up CSV to {BACKUP_PATH}")

    # Merge
    updated = 0
    for row in rows:
        rid = row.get("id", "")
        if rid in translations:
            row["text_en"] = translations[rid]
            updated += 1

    # Write back
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Updated {updated}/{len(rows)} rows in {CSV_PATH}")


if __name__ == "__main__":
    main()
