#!/usr/bin/env python3
"""
merge_zaydi_translations.py
============================
Merges English translations from zaydi_translated.jsonl back into
the parsed JSON and CSV files, then regenerates all output files.

Usage:
    python merge_zaydi_translations.py
"""

import csv
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
csv.field_size_limit(10 * 1024 * 1024)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_NAME = "Musnad al-Imam Zayd ibn Ali"

def main():
    translated_path = os.path.join(SCRIPT_DIR, 'zaydi_translated.jsonl')
    parsed_path = os.path.join(SCRIPT_DIR, 'parsed_zaydi_hadiths.json')

    if not os.path.exists(translated_path):
        print(f"ERROR: {translated_path} not found. Run translation first.")
        sys.exit(1)

    # Load translations into lookup
    translations = {}
    with open(translated_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            hid = row.get('id', '')
            text_en = row.get('text_en', '')
            if hid and text_en and '_translation_error' not in row:
                translations[hid] = text_en

    print(f"Loaded {len(translations)} translations")

    # Load parsed hadiths
    with open(parsed_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Merge translations
    merged = 0
    for h in data['hadiths']:
        hid = f"zayd_{h['hadith_no']:04d}"
        if hid in translations:
            h['text_english'] = translations[hid]
            merged += 1
        else:
            h.setdefault('text_english', '')

    print(f"Merged {merged}/{len(data['hadiths'])} translations")

    # Save updated JSON
    with open(parsed_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Updated {parsed_path}")

    # Regenerate CSVs
    hadiths = data['hadiths']

    # Full CSV
    full_path = os.path.join(SCRIPT_DIR, 'zaydi_hadiths_full.csv')
    full_fields = ['id', 'hadith_id', 'source', 'volume', 'chapter_no', 'hadith_no',
                   'chapter', 'category', 'chain_indx', 'text_ar', 'text_en',
                   'sanad', 'matn_en', 'grading_majlisi', 'grading_mohseni',
                   'grading_behbudi', 'gradings_full', 'url']
    with open(full_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=full_fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for h in hadiths:
            writer.writerow({
                'id': f"zayd_{h['hadith_no']:04d}",
                'hadith_id': h['hadith_no'],
                'source': SOURCE_NAME,
                'volume': 1,
                'chapter_no': h['chapter_no'],
                'hadith_no': h['hadith_no'],
                'chapter': h['chapter_name_ar'],
                'category': h['chapter_name_ar'],
                'chain_indx': '',
                'text_ar': h['text_arabic'],
                'text_en': h.get('text_english', ''),
                'sanad': h['sanad'],
                'matn_en': '',
                'grading_majlisi': '', 'grading_mohseni': '',
                'grading_behbudi': '', 'gradings_full': '', 'url': '',
            })
    print(f"Wrote {full_path}")

    # Clean CSV
    clean_path = os.path.join(SCRIPT_DIR, 'zaydi_hadiths_clean.csv')
    clean_fields = ['id', 'hadith_id', 'source', 'chapter_no', 'hadith_no',
                    'chapter', 'chain_indx', 'text_ar', 'text_en']
    with open(clean_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=clean_fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        for h in hadiths:
            writer.writerow({
                'id': f"zayd_{h['hadith_no']:04d}",
                'hadith_id': h['hadith_no'],
                'source': SOURCE_NAME,
                'chapter_no': h['chapter_no'],
                'hadith_no': h['hadith_no'],
                'chapter': h['chapter_name_ar'],
                'chain_indx': '',
                'text_ar': h['text_arabic'],
                'text_en': h.get('text_english', ''),
            })
    print(f"Wrote {clean_path}")

    print(f"\nDone! {merged} hadiths now have English translations.")
    print("Next: npx tsx src/scripts/reimport-zaydi.ts && npx tsx src/scripts/import-zaydi-collections.ts")

if __name__ == '__main__':
    main()
