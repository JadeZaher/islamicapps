#!/usr/bin/env python3
"""
extract_classical_for_translation.py
=====================================
Extract 4 classical collections from pure_canon.jsonl for translation.
Merges any existing good translations from pure_canon_en.jsonl.

Outputs:
  - classical_to_translate.jsonl  (rows needing translation)
  - classical_already_translated.jsonl (rows with existing good translations)

Usage:
    python datasets/hadith-data/extract_classical_for_translation.py
"""

import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "sheikahmad", "pure_canon.jsonl")
EN_PATH = os.path.join(SCRIPT_DIR, "sheikahmad", "pure_canon_en.jsonl")
OUT_TO_TRANSLATE = os.path.join(SCRIPT_DIR, "classical_to_translate.jsonl")
OUT_ALREADY = os.path.join(SCRIPT_DIR, "classical_already_translated.jsonl")

# Arabic source prefixes -> canonical English names
TARGET_SOURCES = {
    "مسند حنبل": "Musnad Ahmad",
    "سنن الدارمي": "Sunan al-Darimi",
    "شافعي": "Musnad al-Shafi'i",
    "موطأ مالك": "Muwatta' Malik",
}

# Patterns that indicate a bad/refused translation
REFUSAL_PATTERNS = [
    "I cannot",
    "I'm unable",
    "I apologize",
    "I can't fulfill",
    "I can't assist",
    "I cannot fulfill",
    "_translation_error",
    "I can provide information",
    "Could you please provide the complete",
]


def match_source(source_value: str) -> str | None:
    """Match Arabic source string to canonical name via prefix."""
    for prefix, canonical in TARGET_SOURCES.items():
        if source_value.startswith(prefix):
            return canonical
    return None


def is_good_translation(text_en: str) -> bool:
    """Check if a translation is usable (not a refusal or empty)."""
    if not text_en or len(text_en.strip()) < 10:
        return False
    for pattern in REFUSAL_PATTERNS:
        if pattern.lower() in text_en.lower():
            return False
    return True


def main():
    # Step 1: Load existing translations
    print("Loading existing translations...")
    existing_translations: dict[str, str] = {}
    if os.path.exists(EN_PATH):
        with open(EN_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                row_id = obj.get("id", "")
                text_en = str(obj.get("text_en", ""))
                if row_id and is_good_translation(text_en):
                    existing_translations[row_id] = text_en
        print(f"  {len(existing_translations):,} good existing translations loaded")
    else:
        print(f"  WARNING: {EN_PATH} not found, proceeding without existing translations")

    # Step 2: Extract classical collections
    print(f"\nExtracting from {INPUT_PATH}...")
    stats: dict[str, dict] = {}
    to_translate = []
    already_translated = []

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            source = obj.get("source", "")
            canonical = match_source(source)
            if canonical is None:
                continue

            if canonical not in stats:
                stats[canonical] = {"total": 0, "has_translation": 0, "needs_translation": 0}

            stats[canonical]["total"] += 1
            row_id = obj.get("id", "")

            # Add canonical source name for downstream use
            obj["source_canonical"] = canonical

            if row_id in existing_translations:
                obj["text_en"] = existing_translations[row_id]
                already_translated.append(obj)
                stats[canonical]["has_translation"] += 1
            else:
                to_translate.append(obj)
                stats[canonical]["needs_translation"] += 1

    # Step 3: Write output files
    print(f"\nWriting {len(to_translate):,} rows to {OUT_TO_TRANSLATE}")
    with open(OUT_TO_TRANSLATE, "w", encoding="utf-8") as f:
        for row in to_translate:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Writing {len(already_translated):,} rows to {OUT_ALREADY}")
    with open(OUT_ALREADY, "w", encoding="utf-8") as f:
        for row in already_translated:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # Step 4: Summary
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    total_all = 0
    total_need = 0
    total_have = 0
    for canonical in ["Musnad Ahmad", "Sunan al-Darimi", "Musnad al-Shafi'i", "Muwatta' Malik"]:
        s = stats.get(canonical, {"total": 0, "has_translation": 0, "needs_translation": 0})
        total_all += s["total"]
        total_need += s["needs_translation"]
        total_have += s["has_translation"]
        pct = 100 * s["has_translation"] / s["total"] if s["total"] else 0
        print(f"  {canonical:25s}  total={s['total']:>6,}  translated={s['has_translation']:>5,}  need={s['needs_translation']:>6,}  ({pct:.1f}% done)")

    print(f"\n  {'TOTAL':25s}  total={total_all:>6,}  translated={total_have:>5,}  need={total_need:>6,}")
    print(f"\n  Output: {OUT_TO_TRANSLATE}")
    print(f"  Output: {OUT_ALREADY}")


if __name__ == "__main__":
    main()
