#!/usr/bin/env python3
"""
clean_arabic_text.py
====================
Phase 1: Strip mechanical OCR artifacts from Zaydi hadith Arabic text.
Phase 2: Prepare JSONL for LLM-assisted cleanup of remaining garbled text.

Usage:
    python clean_arabic_text.py                # Phase 1: mechanical strip
    python clean_arabic_text.py --prepare-llm  # Phase 2: export for LLM cleanup
    python clean_arabic_text.py --merge-llm    # Phase 3: merge LLM results back
"""

import argparse
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PARSED_PATH = os.path.join(SCRIPT_DIR, 'parsed_zaydi_hadiths.json')
LLM_INPUT_PATH = os.path.join(SCRIPT_DIR, 'zaydi_for_cleanup.jsonl')
LLM_OUTPUT_PATH = os.path.join(SCRIPT_DIR, 'zaydi_cleaned.jsonl')


def strip_artifacts(text: str) -> str:
    """Remove mechanical OCR artifacts from Arabic text."""
    # Remove footnote markers: )١(‏ )1١(‏ )5( etc
    text = re.sub(r'\)\s*[٠-٩0-9]+\s*\(\s*‏?\s*', ' ', text)

    # Remove (؟) (؟") (") (0) (00) (001) (01) (1) (5) patterns
    text = re.sub(r'\(\s*[؟\?"0-9٠-٩]*\s*["\']?\s*\)', ' ', text)

    # Remove © symbol (OCR misread)
    text = text.replace('©', '')

    # Remove stray symbols: # * + _ | [ ] { } ^ ~ \
    text = re.sub(r'[#*+_|^~\\\[\]{}]', '', text)

    # Remove ٠‏ (Arabic zero + format mark, used as bullet/marker)
    text = text.replace('٠‏', '')
    text = text.replace('٠\u200f', '')

    # Remove standalone format marks
    text = text.replace('\u200f', '')  # RTL mark
    text = text.replace('\u200e', '')  # LTR mark
    text = text.replace('\u200c', '')  # ZWNJ
    text = text.replace('\u200b', '')  # ZWSP
    text = text.replace('\u200d', '')  # ZWJ
    text = text.replace('\u202c', '')  # PDF
    text = text.replace('\u202b', '')  # RLE
    text = text.replace('\u202a', '')  # LRE
    text = text.replace('\u2069', '')  # PDI
    text = text.replace('\u2068', '')  # FSI
    text = text.replace('\u2066', '')  # LRI
    text = text.replace('\u2067', '')  # RLI

    # Remove digit-only noise: standalone 3+ digit numbers (like 520, 000, 007)
    # But keep numbers that are part of hadith references (preceded by Arabic text)
    text = re.sub(r'\b0{2,}\b', '', text)  # 000, 0000
    text = re.sub(r'\b0\d{2,}\b', '', text)  # 007, 0353, 010, etc

    # Remove stray lone digits surrounded by spaces (OCR noise)
    # Be careful: Arabic text uses Eastern digits, but these are Western digit noise
    text = re.sub(r'\s[0-9]\s', ' ', text)

    # Clean up remaining stray digits in clearly wrong positions
    # e.g. "520 000" at end of text, or "29" mid-word
    text = re.sub(r'\s\d{3}\s\d{3}\b', '', text)  # "520 000" type patterns

    # Remove empty parentheses and quotes
    text = re.sub(r'\(\s*\)', '', text)
    text = re.sub(r'«\s*»', '', text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    # Remove leading/trailing punctuation artifacts
    text = text.strip('.,;:!? ')

    return text


def assess_quality(text: str) -> list[str]:
    """Check remaining quality issues after mechanical cleanup."""
    issues = []

    if len(text) < 30:
        issues.append('very_short')

    # Broken words: sequences of single Arabic chars separated by spaces
    # Like "ا و ت و ح م ة" instead of "أوتوحمة"
    singles = re.findall(r'(?:\s[\u0600-\u06FF]\s){3,}', text)
    if singles:
        issues.append('broken_words')

    # Garbled letter sequences (OCR misreads producing nonsense)
    # Check for excessive non-word patterns
    words = text.split()
    if words:
        short_garbled = sum(1 for w in words if len(w) <= 2 and re.match(r'^[\u0600-\u06FF]+$', w))
        if short_garbled > len(words) * 0.3:
            issues.append('excessive_fragments')

    # Remaining Western digits (shouldn't be in Arabic hadith text normally)
    remaining_digits = re.findall(r'[0-9]+', text)
    if remaining_digits:
        issues.append('remaining_digits')

    return issues


def phase1_mechanical_strip():
    """Strip mechanical artifacts from all hadiths."""
    with open(PARSED_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    cleaned = 0
    still_issues = 0
    issue_types = {}

    for h in data['hadiths']:
        old = h.get('text_arabic', '')
        new = strip_artifacts(old)
        if old != new:
            h['text_arabic'] = new
            cleaned += 1

        issues = assess_quality(new)
        if issues:
            still_issues += 1
            for iss in issues:
                issue_types[iss] = issue_types.get(iss, 0) + 1

    with open(PARSED_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Phase 1: Mechanical cleanup")
    print(f"  Cleaned: {cleaned}/{len(data['hadiths'])} hadiths modified")
    print(f"  Remaining issues: {still_issues} hadiths")
    for iss, cnt in sorted(issue_types.items(), key=lambda x: -x[1]):
        print(f"    {iss}: {cnt}")

    return data


def phase2_prepare_llm(data=None):
    """Export hadiths needing LLM cleanup to JSONL."""
    if data is None:
        with open(PARSED_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)

    to_clean = []
    for h in data['hadiths']:
        hid = f"zayd_{h['hadith_no']:04d}"
        issues = assess_quality(h['text_arabic'])
        if issues:
            to_clean.append({
                'id': hid,
                'hadith_no': h['hadith_no'],
                'text_ar': h['text_arabic'],
                'issues': issues,
            })

    with open(LLM_INPUT_PATH, 'w', encoding='utf-8') as f:
        for row in to_clean:
            f.write(json.dumps(row, ensure_ascii=False) + '\n')

    print(f"\nPhase 2: Prepared {len(to_clean)} hadiths for LLM cleanup")
    print(f"  Output: {LLM_INPUT_PATH}")
    print(f"\n  Run with:")
    print(f"    python datasets/translate_openrouter.py \\")
    print(f"      --input {LLM_INPUT_PATH} \\")
    print(f"      --output {LLM_OUTPUT_PATH} \\")
    print(f"      --source-field text_ar \\")
    print(f"      --dest-field text_ar_clean \\")
    print(f"      --prompt-file datasets/hadith-data/zaydi-hadith/cleanup_prompt.txt \\")
    print(f"      --model google/gemma-3-27b-it \\")
    print(f"      --resume")


def phase3_merge_llm():
    """Merge LLM-cleaned text back into parsed JSON."""
    if not os.path.exists(LLM_OUTPUT_PATH):
        print(f"ERROR: {LLM_OUTPUT_PATH} not found. Run LLM cleanup first.")
        sys.exit(1)

    # Load cleaned texts
    cleaned = {}
    with open(LLM_OUTPUT_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            hid = row.get('id', '')
            clean_text = row.get('text_ar_clean', '')
            if hid and clean_text and len(clean_text) > 20:
                cleaned[hid] = clean_text

    with open(PARSED_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    merged = 0
    for h in data['hadiths']:
        hid = f"zayd_{h['hadith_no']:04d}"
        if hid in cleaned:
            h['text_arabic'] = cleaned[hid]
            merged += 1

    with open(PARSED_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Phase 3: Merged {merged} LLM-cleaned hadiths back into parsed JSON")
    print(f"  Run fix_zaydi_data.py to regenerate CSVs")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--prepare-llm', action='store_true', help='Phase 2: export for LLM')
    parser.add_argument('--merge-llm', action='store_true', help='Phase 3: merge LLM results')
    args = parser.parse_args()

    if args.merge_llm:
        phase3_merge_llm()
    elif args.prepare_llm:
        phase2_prepare_llm()
    else:
        data = phase1_mechanical_strip()
        phase2_prepare_llm(data)


if __name__ == '__main__':
    main()
