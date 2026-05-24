#!/usr/bin/env python3
"""
parse_musnad_zayd.py
====================
Parse the Musnad Zayd ibn Ali from Archive.org pre-extracted text into
structured hadith records and export to CSV.

Outputs:
  1. zaydi_hadiths.csv          — standalone subset (record_id, source, chapter_name_ar, text_arabic, hadith_number)
  2. zaydi_hadiths_full.csv     — full schema matching all_hadiths_shia.csv for integration
  3. parsed_zaydi_hadiths.json  — intermediate JSON for DB import scripts

Source text: musnad_zayd_arabic_text.txt (Archive.org djvu.txt from msnd_lmm_zyd)

Usage:
    python parse_musnad_zayd.py
    python parse_musnad_zayd.py --input musnad_zayd_arabic_text.txt --output-dir .
"""

import argparse
import csv
import json
import os
import re
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Increase CSV field size limit (some Shia hadiths have very large text fields)
csv.field_size_limit(10 * 1024 * 1024)  # 10 MB

# ── Constants ────────────────────────────────────────────────────────────────

SOURCE_NAME = "Musnad al-Imam Zayd ibn Ali"
SOURCE_NAME_AR = "مسند الإمام زيد بن علي"
SCHOOL = "Shia Zaydi"
COMPILER = "Abd al-Aziz ibn Ishaq al-Baghdadi"
COMPILER_AR = "عبد العزيز بن إسحاق البغدادي"

# The actual hadith content starts after the introduction.
# First real chapter heading (باب الغسل) is around line 2279.
# We skip everything before the first substantive باب heading.
CONTENT_START_LINE = 2200
CONTENT_END_LINE = 16070  # After this, it's table of contents / book index

# Default chapter for hadiths appearing before the first باب heading
DEFAULT_CHAPTER = "مقدمة"  # Introduction

# Regex patterns
BAB_PATTERN = re.compile(r'^[بد]اب\s+(.+)', re.UNICODE)  # OCR corrupts باب → داب
KITAB_PATTERN = re.compile(r'^كتاب\s+(.+)', re.UNICODE)  # كتاب headings are also chapter breaks

# Hadith chain starters — the text uses ( حدثني ) or حدثني or حدثنا
# OCR produces corrupted bracket prefixes: 2, 0, )0, ( و, ) , etc.
HADITH_START_PATTERN = re.compile(
    r'^[\(\)012٠١٢\s]{0,10}حد[ثتئ][^\s]{0,3}',  # Extended prefix tolerance for heavy OCR garbage
    re.UNICODE
)

# Additional hadith start patterns (sub-narrations and follow-ups)
HADITH_CONTINUATION_PATTERNS = [
    re.compile(r'^[\(\)012٠١٢\s]{0,6}و\s*حد[ثتئ]', re.UNICODE),   # وحدثني (and he narrated) — OCR-tolerant
    re.compile(r'^[\(\)012٠١٢\s]{0,6}و\s*سأل', re.UNICODE),       # وسألت (and I asked) — OCR-tolerant
    re.compile(r'^قال\s+زيد', re.UNICODE),             # قال زيد (Zayd said)
    re.compile(r'^\(?\s*وقال\s+زيد', re.UNICODE),      # وقال زيد
    re.compile(r'^\(?\s*سألت', re.UNICODE),             # سألت (bare, without و)
    re.compile(r'^\(?\s*قال\s*:?\s*سألت', re.UNICODE),  # قال : سألت
    re.compile(r'^\(?\s*قال\s+أبو\s*خالد', re.UNICODE), # قال أبو خالد (OCR variants)
    re.compile(r'^قال\s+وسمعت\s+زيداً?', re.UNICODE),  # قال وسمعت زيداً (unique Zaydi opener)
    re.compile(r'^\(?\s*قال\s+وسمعت', re.UNICODE),      # قال وسمعت (variant)
]

# Footnote patterns: lines starting with (N) where N is Arabic or Latin digit
FOOTNOTE_PATTERN = re.compile(
    r'^\s*\([\d١٢٣٤٥٦٧٨٩٠]+\)\s',
    re.UNICODE
)

# Page number pattern: standalone numbers
PAGE_NUM_PATTERN = re.compile(r'^\s*\d{1,3}\s*$')

# Sanad/matn boundary markers
MATN_START_MARKERS = [
    'قال :',
    'قال:',
    'قال رسول الله',
    'قال النبي',
    'أن النبي',
    'أن رسول الله',
    'عن النبي',
    'عليه السلام قال',
    'رضي الله عنه قال',
    'رضي الله عنهم قال',
    'رضوان الله عليه قال',
    'رضوان الله عليهم قال',
    'كرم الله وجهه قال',
]


def clean_text(text: str) -> str:
    """Normalize whitespace while preserving Arabic/Unicode."""
    if not text:
        return ""
    # Remove excessive whitespace but keep single spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def is_footnote_line(line: str) -> bool:
    """Check if a line is a footnote/commentary (not hadith text)."""
    stripped = line.strip()
    if not stripped:
        return False
    # Lines starting with (N) are footnotes
    if FOOTNOTE_PATTERN.match(stripped):
        return True
    # Lines that are just page numbers
    if PAGE_NUM_PATTERN.match(stripped):
        return True
    return False


def is_commentary_block(line: str) -> bool:
    """Detect commentary/editorial text that's not hadith content."""
    stripped = line.strip()
    # Common commentary indicators
    commentary_markers = [
        'قال المؤلف',       # The author said
        'قال الشارح',       # The commentator said
        'قال في الشفاء',    # He said in al-Shifa
        'ذكره في',          # He mentioned in
        'أخرجه',            # Narrated by (cross-reference)
        'والحديث يدل',      # The hadith indicates (commentary)
        'قال النووي',       # al-Nawawi said
        'قال الحافظ',       # al-Hafiz said
        '( مسألة )',        # Legal question (fiqh discussion)
        'مسألة',            # Legal question
    ]
    return any(stripped.startswith(m) for m in commentary_markers)


def split_sanad_matn(text: str) -> tuple[str, str]:
    """Split hadith text into sanad (chain) and matn (body).

    The Zaydi chain typically ends at the Companion level (Ali, the Prophet, etc.)
    followed by a قال. We need to find the LAST قال after the chain terminus,
    not the first one (since the chain itself may contain قال for sub-narrators).

    Returns (sanad, matn). If can't split, returns (text, '').
    """
    # The chain terminus markers — the matn starts after these + قال
    chain_end_markers = [
        'عن النبي',
        'رسول الله',
        'النبي صلى الله عليه',
        'النبي ص',
        'النبي ل',
        'النبي متي',
        'عليه السلام',
        'عليهم السلام',
        'رضي الله عنه',
        'رضي الله عنهم',
        'رضوان الله عليه',
        'رضوان الله عليهم',
        'كرم الله وجهه',
        'أبي طالب',
    ]

    # Find the last chain terminus marker
    last_terminus_pos = -1
    for marker in chain_end_markers:
        pos = text.rfind(marker)
        if pos != -1 and pos > last_terminus_pos:
            last_terminus_pos = pos

    if last_terminus_pos != -1:
        # Find the first قال after the last terminus
        search_start = last_terminus_pos
        qal_pos = text.find('قال', search_start)
        if qal_pos != -1:
            # Include قال in the matn
            sanad = text[:qal_pos].strip()
            matn = text[qal_pos:].strip()
            return sanad, matn

    # Fallback: find first standalone قال : pattern
    qal_match = re.search(r'قال\s*:', text)
    if qal_match:
        sanad = text[:qal_match.start()].strip()
        matn = text[qal_match.start():].strip()
        return sanad, matn

    return text, ''


def parse_text_file(filepath: str) -> list[dict]:
    """Parse the Musnad Zayd text file into structured hadith records."""

    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    print(f"Loaded {len(lines)} lines from {filepath}")

    # Only process content after the introduction and before the table of contents
    content_lines = lines[CONTENT_START_LINE:CONTENT_END_LINE]

    hadiths = []
    current_chapter = DEFAULT_CHAPTER
    current_chapter_no = 0
    hadith_no = 0

    # State machine: collect lines for current hadith
    current_hadith_lines = []
    in_hadith = False
    in_footnote = False
    expect_hadith_after_bab = False

    for line_idx, line in enumerate(content_lines, start=CONTENT_START_LINE):
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            if in_hadith and current_hadith_lines:
                # Empty line might be paragraph break within hadith
                pass
            continue

        # Skip page numbers
        if PAGE_NUM_PATTERN.match(stripped):
            continue

        # Check for chapter heading (باب or كتاب, including OCR variant داب)
        bab_match = BAB_PATTERN.match(stripped) or KITAB_PATTERN.match(stripped)
        if bab_match:
            # Save any in-progress hadith
            if in_hadith and current_hadith_lines:
                hadith_text = clean_text(' '.join(current_hadith_lines))
                if len(hadith_text) > 30:  # Skip tiny fragments
                    hadith_no += 1
                    sanad, matn = split_sanad_matn(hadith_text)
                    hadiths.append({
                        'hadith_no': hadith_no,
                        'chapter_no': current_chapter_no,
                        'chapter_name_ar': current_chapter,
                        'text_arabic': hadith_text,
                        'sanad': sanad,
                        'matn_ar': matn,
                        'source_line': line_idx,
                    })
                current_hadith_lines = []
                in_hadith = False

            current_chapter_no += 1
            # Determine prefix: كتاب for kitab headings, باب for everything else
            prefix = 'كتاب' if KITAB_PATTERN.match(stripped) else 'باب'
            current_chapter = f"{prefix} {bab_match.group(1).strip()}"
            # Remove footnote markers from chapter name
            current_chapter = re.sub(r'\s*\([١٢٣٤٥٦٧٨٩٠\d]+\)\s*', ' ', current_chapter).strip()
            expect_hadith_after_bab = True
            continue

        # Check for hadith start (primary or continuation patterns)
        is_primary_start = HADITH_START_PATTERN.match(stripped)
        is_continuation = any(p.match(stripped) for p in HADITH_CONTINUATION_PATTERNS)

        if is_primary_start or is_continuation:
            # Save previous hadith
            if in_hadith and current_hadith_lines:
                hadith_text = clean_text(' '.join(current_hadith_lines))
                if len(hadith_text) > 30:
                    hadith_no += 1
                    sanad, matn = split_sanad_matn(hadith_text)
                    hadiths.append({
                        'hadith_no': hadith_no,
                        'chapter_no': current_chapter_no,
                        'chapter_name_ar': current_chapter,
                        'text_arabic': hadith_text,
                        'sanad': sanad,
                        'matn_ar': matn,
                        'source_line': line_idx,
                    })

            current_hadith_lines = [stripped]
            in_hadith = True
            in_footnote = False
            expect_hadith_after_bab = False
            continue

        # Skip footnotes and commentary when inside a hadith
        if is_footnote_line(stripped):
            in_footnote = True
            continue

        if is_commentary_block(stripped):
            in_footnote = True
            continue

        # If we were in a footnote and hit non-footnote text,
        # check if it's continuing commentary or returning to hadith
        if in_footnote:
            if not HADITH_START_PATTERN.match(stripped) and not BAB_PATTERN.match(stripped):
                # Exit footnote if line is long enough OR contains narration markers
                narration_markers = ['عن أبيه', 'عن جده', 'زيد بن علي', 'زيد بن على',
                                     'زيداً', 'رسول الله', 'عليه السلام', 'رضي الله',
                                     'النبي', 'قال :', 'سألت']
                if len(stripped) < 80 and not any(m in stripped for m in narration_markers):
                    continue
                else:
                    in_footnote = False

        # Post-bab fallback: if we expect a hadith after a bab heading and
        # encounter a non-empty, non-footnote, non-page-number line that
        # didn't match any pattern above, treat it as a new hadith start.
        if expect_hadith_after_bab and not in_hadith:
            current_hadith_lines = [stripped]
            in_hadith = True
            in_footnote = False
            expect_hadith_after_bab = False
            continue

        # Accumulate hadith text
        if in_hadith:
            current_hadith_lines.append(stripped)

            # Check for inline hadith starts within accumulated text (Bug 4)
            # Some hadiths have حدثني appearing after 10+ chars of other text
            if not is_primary_start and not is_continuation:
                inline_match = re.search(r'(?:حد[ثتئ][نيتـبى]|و\s*حد[ثتئ])', stripped)
                if inline_match and inline_match.start() > 10:
                    # Split: before goes to current hadith, after starts new one
                    before = stripped[:inline_match.start()].strip()
                    after = stripped[inline_match.start():].strip()
                    # Remove the full line we just appended, replace with before-part
                    current_hadith_lines.pop()
                    if before:
                        current_hadith_lines.append(before)
                    # Save current hadith
                    hadith_text = clean_text(' '.join(current_hadith_lines))
                    if len(hadith_text) > 30:
                        hadith_no += 1
                        sanad, matn = split_sanad_matn(hadith_text)
                        hadiths.append({
                            'hadith_no': hadith_no,
                            'chapter_no': current_chapter_no,
                            'chapter_name_ar': current_chapter,
                            'text_arabic': hadith_text,
                            'sanad': sanad,
                            'matn_ar': matn,
                            'source_line': line_idx,
                        })
                    current_hadith_lines = [after]
                    continue

    # Don't forget the last hadith
    if in_hadith and current_hadith_lines:
        hadith_text = clean_text(' '.join(current_hadith_lines))
        if len(hadith_text) > 30:
            hadith_no += 1
            sanad, matn = split_sanad_matn(hadith_text)
            hadiths.append({
                'hadith_no': hadith_no,
                'chapter_no': current_chapter_no,
                'chapter_name_ar': current_chapter,
                'text_arabic': hadith_text,
                'sanad': sanad,
                'matn_ar': matn,
                'source_line': line_idx,
            })

    return hadiths


def generate_standalone_csv(hadiths: list[dict], output_path: str):
    """Generate the standalone Zaydi CSV (user's original request)."""
    fieldnames = ['record_id', 'source', 'chapter_name_ar', 'text_arabic', 'hadith_number']

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        for h in hadiths:
            writer.writerow({
                'record_id': f"zayd_{h['hadith_no']:04d}",
                'source': SOURCE_NAME_AR,
                'chapter_name_ar': h['chapter_name_ar'],
                'text_arabic': h['text_arabic'],
                'hadith_number': h['hadith_no'],
            })

    print(f"Standalone CSV: {len(hadiths)} rows -> {output_path}")


def generate_full_csv(hadiths: list[dict], output_path: str):
    """Generate full CSV matching all_hadiths_shia.csv schema for integration."""
    # Schema: id, hadith_id, source, volume, chapter_no, hadith_no, chapter, category,
    #          chain_indx, text_ar, text_en, sanad, matn_en,
    #          grading_majlisi, grading_mohseni, grading_behbudi, gradings_full, url
    fieldnames = [
        'id', 'hadith_id', 'source', 'volume', 'chapter_no', 'hadith_no',
        'chapter', 'category', 'chain_indx', 'text_ar', 'text_en',
        'sanad', 'matn_en', 'grading_majlisi', 'grading_mohseni',
        'grading_behbudi', 'gradings_full', 'url',
    ]

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        for h in hadiths:
            writer.writerow({
                'id': f"zayd_{h['hadith_no']:04d}",
                'hadith_id': h['hadith_no'],
                'source': SOURCE_NAME,
                'volume': 1,  # Single volume
                'chapter_no': h['chapter_no'],
                'hadith_no': h['hadith_no'],
                'chapter': h['chapter_name_ar'],
                'category': h['chapter_name_ar'],
                'chain_indx': '',
                'text_ar': h['text_arabic'],
                'text_en': '',  # No translation yet
                'sanad': h['sanad'],
                'matn_en': '',
                'grading_majlisi': '',
                'grading_mohseni': '',
                'grading_behbudi': '',
                'gradings_full': '',
                'url': '',
            })

    print(f"Full CSV: {len(hadiths)} rows -> {output_path}")


def generate_clean_csv(hadiths: list[dict], output_path: str):
    """Generate CSV matching all_hadiths_clean.csv schema."""
    # Schema: id, hadith_id, source, chapter_no, hadith_no, chapter, chain_indx, text_ar, text_en
    fieldnames = [
        'id', 'hadith_id', 'source', 'chapter_no', 'hadith_no',
        'chapter', 'chain_indx', 'text_ar', 'text_en',
    ]

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
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
                'text_en': '',
            })

    print(f"Clean CSV: {len(hadiths)} rows -> {output_path}")


def generate_json(hadiths: list[dict], output_path: str):
    """Save parsed hadiths as JSON for DB import scripts."""
    output = {
        'source': SOURCE_NAME,
        'source_ar': SOURCE_NAME_AR,
        'school': SCHOOL,
        'compiler': COMPILER,
        'compiler_ar': COMPILER_AR,
        'total_hadiths': len(hadiths),
        'hadiths': hadiths,
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"JSON: {len(hadiths)} hadiths -> {output_path}")


def append_to_shia_csv(hadiths: list[dict], csv_path: str):
    """Append Zaydi hadiths to all_hadiths_shia.csv.

    First removes any existing Zaydi entries (idempotent), then appends.
    """
    import tempfile
    import shutil

    # Read existing, filter out any previous Zaydi entries
    existing_rows = []
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row.get('source') != SOURCE_NAME:
                existing_rows.append(row)

    # Find the max existing id to continue numbering
    max_id = 0
    for row in existing_rows:
        try:
            max_id = max(max_id, int(row.get('id', 0)))
        except (ValueError, TypeError):
            pass

    # Write back with Zaydi appended
    tmp_path = csv_path + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(existing_rows)

        for h in hadiths:
            max_id += 1
            writer.writerow({
                'id': max_id,
                'hadith_id': h['hadith_no'],
                'source': SOURCE_NAME,
                'volume': 1,
                'chapter_no': h['chapter_no'],
                'hadith_no': h['hadith_no'],
                'chapter': h['chapter_name_ar'],
                'category': h['chapter_name_ar'],
                'chain_indx': '',
                'text_ar': h['text_arabic'],
                'text_en': '',
                'sanad': h['sanad'],
                'matn_en': '',
                'grading_majlisi': '',
                'grading_mohseni': '',
                'grading_behbudi': '',
                'gradings_full': '',
                'url': '',
            })

    shutil.move(tmp_path, csv_path)
    print(f"Appended {len(hadiths)} Zaydi hadiths to {csv_path} (total: {max_id})")


def append_to_clean_csv(hadiths: list[dict], csv_path: str):
    """Append Zaydi hadiths to all_hadiths_clean.csv (idempotent)."""
    import shutil

    existing_rows = []
    with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            if row.get('source') != SOURCE_NAME:
                existing_rows.append(row)

    max_id = 0
    for row in existing_rows:
        try:
            max_id = max(max_id, int(row.get('id', 0)))
        except (ValueError, TypeError):
            pass

    tmp_path = csv_path + '.tmp'
    with open(tmp_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(existing_rows)

        for h in hadiths:
            max_id += 1
            writer.writerow({
                'id': max_id,
                'hadith_id': h['hadith_no'],
                'source': SOURCE_NAME,
                'chapter_no': h['chapter_no'],
                'hadith_no': h['hadith_no'],
                'chapter': h['chapter_name_ar'],
                'chain_indx': '',
                'text_ar': h['text_arabic'],
                'text_en': '',
            })

    shutil.move(tmp_path, csv_path)
    print(f"Appended {len(hadiths)} Zaydi hadiths to {csv_path} (total: {max_id})")


def print_summary(hadiths: list[dict]):
    """Print a summary of the parsed data."""
    chapters = set()
    for h in hadiths:
        chapters.add((h['chapter_no'], h['chapter_name_ar']))

    chapters_sorted = sorted(chapters, key=lambda x: x[0])

    print(f"\n{'='*60}")
    print(f"  Musnad Zayd ibn Ali — Parse Summary")
    print(f"{'='*60}")
    print(f"  Total hadiths:  {len(hadiths)}")
    print(f"  Total chapters: {len(chapters_sorted)}")
    print(f"  With sanad:     {sum(1 for h in hadiths if h['sanad'])}")
    print(f"  With matn:      {sum(1 for h in hadiths if h['matn_ar'])}")
    print()

    # Chapter breakdown
    print("  Chapters:")
    for ch_no, ch_name in chapters_sorted[:30]:
        count = sum(1 for h in hadiths if h['chapter_no'] == ch_no)
        # Truncate long names
        display = ch_name[:60] + '...' if len(ch_name) > 60 else ch_name
        print(f"    {ch_no:3d}. {display:65s} ({count} hadiths)")
    if len(chapters_sorted) > 30:
        print(f"    ... and {len(chapters_sorted) - 30} more chapters")
    print()


def main():
    parser = argparse.ArgumentParser(description='Parse Musnad Zayd ibn Ali into structured CSV')
    parser.add_argument('--input', default=None, help='Input text file')
    parser.add_argument('--output-dir', default=None, help='Output directory')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))

    if args.input is None:
        args.input = os.path.join(script_dir, 'musnad_zayd_arabic_text.txt')
    if args.output_dir is None:
        args.output_dir = script_dir

    if not os.path.exists(args.input):
        print(f"ERROR: Input file not found: {args.input}")
        print("Run download first or provide --input path.")
        sys.exit(1)

    # Parse
    print(f"Parsing {args.input}...")
    hadiths = parse_text_file(args.input)

    if not hadiths:
        print("ERROR: No hadiths extracted!")
        sys.exit(1)

    print_summary(hadiths)

    # Generate outputs
    standalone_csv = os.path.join(args.output_dir, 'zaydi_hadiths.csv')
    full_csv = os.path.join(args.output_dir, 'zaydi_hadiths_full.csv')
    clean_csv = os.path.join(args.output_dir, 'zaydi_hadiths_clean.csv')
    json_path = os.path.join(args.output_dir, 'parsed_zaydi_hadiths.json')

    generate_standalone_csv(hadiths, standalone_csv)
    generate_full_csv(hadiths, full_csv)
    generate_clean_csv(hadiths, clean_csv)
    generate_json(hadiths, json_path)

    # Append to unified CSVs in parent directory
    parent_dir = os.path.join(args.output_dir, '..')
    shia_csv = os.path.join(parent_dir, 'all_hadiths_shia.csv')
    clean_unified_csv = os.path.join(parent_dir, 'all_hadiths_clean.csv')

    if os.path.exists(shia_csv):
        append_to_shia_csv(hadiths, shia_csv)
    if os.path.exists(clean_unified_csv):
        append_to_clean_csv(hadiths, clean_unified_csv)

    print(f"\nAll outputs written to {args.output_dir}")


if __name__ == '__main__':
    main()
