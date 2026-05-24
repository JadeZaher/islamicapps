#!/usr/bin/env python3
"""
prepare_zaydi_jsonl.py
======================
Reads parsed_zaydi_hadiths.json and writes zaydi_for_translation.jsonl.

Each output line is a JSON object with:
  id         - "zayd_NNNN" (zero-padded to 4 digits)
  hadith_no  - integer hadith number
  text_ar    - full Arabic text (text_arabic field)
  source     - "Musnad al-Imam Zayd ibn Ali"
  chapter    - Arabic chapter name (chapter_name_ar field)

Run from the repo root or from this directory:
    python datasets/hadith-data/zaydi-hadith/prepare_zaydi_jsonl.py
"""
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_PATH = os.path.join(SCRIPT_DIR, "parsed_zaydi_hadiths.json")
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "zaydi_for_translation.jsonl")

print(f"Reading: {INPUT_PATH}")
with open(INPUT_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

hadiths = data["hadiths"]
print(f"Found {len(hadiths)} hadiths.")

with open(OUTPUT_PATH, "w", encoding="utf-8") as out:
    for h in hadiths:
        n = h["hadith_no"]
        obj = {
            "id": f"zayd_{n:04d}",
            "hadith_no": n,
            "text_ar": h.get("text_arabic", ""),
            "source": "Musnad al-Imam Zayd ibn Ali",
            "chapter": h.get("chapter_name_ar", ""),
        }
        out.write(json.dumps(obj, ensure_ascii=False) + "\n")

print(f"Written: {OUTPUT_PATH}  ({len(hadiths)} lines)")
