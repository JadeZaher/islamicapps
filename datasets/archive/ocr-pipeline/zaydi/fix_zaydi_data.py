#!/usr/bin/env python3
"""
fix_zaydi_data.py
=================
1. Merges retranslated hadiths into the main translated JSONL
2. Cleans OCR-corrupted chapter names in parsed JSON
3. Regenerates all output files (CSVs)

Usage:
    python fix_zaydi_data.py
"""

import csv
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
csv.field_size_limit(10 * 1024 * 1024)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_NAME = "Musnad al-Imam Zayd ibn Ali"

# ── Chapter name corrections ──
# Maps OCR-corrupted names → cleaned Arabic names
CHAPTER_FIXES = {
    # Remove stray punctuation / parenthetical OCR artifacts
    'مقدمة': 'مقدمة',
    'باب أوقات الصلاهة': 'باب أوقات الصلاة',
    'باب الاضحى وأيام النحصر والتشريق': 'باب الأضحى وأيام النحر والتشريق',
    'باب البيوع وفضل الكسب من الحلال,': 'باب البيوع وفضل الكسب من الحلال',
    'باب التسيبح والدعاعء': 'باب التسبيح والدعاء',
    'باب التكبير في \'الصلاة': 'باب التكبير في الصلاة',
    'باب الدمين والددئة': 'باب الأيمان والأدلة',
    'باب الخنثى \'': 'باب الخنثى',
    'باب السهو قي الصلاة': 'باب السهو في الصلاة',
    'باب الصياح )١(\u200F والتوح': 'باب الصياح والنوح',
    'باب العدب يجده الرجل بامرأته': 'باب العيب يجده الرجل بامرأته',
    'باب العدل بين الثسساء': 'باب العدل بين النساء',
    'باب الامام يتجى في رعيته': 'باب الإمام يتجنى في رعيته',
    'باب مسائل ميع الصلاة': 'باب مسائل جميع الصلاة',
    'باب الحدض والاستحاضة والنفاس': 'باب الحيض والاستحاضة والنفاس',
    'باب صلاخ الخمسين': 'باب صلاة الخمسين',
    'باب اليقرة تند )1١١\u200F والبعدر': 'باب البقرة تند والبعير',
    'باب ذكاح الاماء والعد:د': 'باب نكاح الإماء والعبيد',
    'باب الاجارة )١(\u200F': 'باب الإجارة',
    'باب الاولوية )١(\u200F والرايات': 'باب الأولوية والرايات',
    'باب الدعاء عند الحح )١(\u200F': 'باب الدعاء عند الحج',
    'باب الدعاء في دبر الصلاة )١(\u200F وعثد انفلاق الصبح': 'باب الدعاء في دبر الصلاة وعند انفلاق الصبح',
    'باب الشفعة )١(\u200F': 'باب الشفعة',
    'باب الصلاة على الطفل )١(\u200F وعلى الصبي الصذير': 'باب الصلاة على الطفل وعلى الصبي الصغير',
    'باب المزارعة والمعاملة )١(\u200F': 'باب المزارعة والمعاملة',
    'باب اللقطة )١(\u200F واللقيطة ("»': 'باب اللقطة واللقيطة',
    'باب صلاة الضحى )١(\u200F': 'باب صلاة الضحى',
    'باب قطاع الطريق )١(\u200F': 'باب قطاع الطريق',
    'باب في فغمل الصلاة )١(\u200F على النيي صلى الله عليه وسلم وعلى آله الطاهرين': 'باب في فضل الصلاة على النبي صلى الله عليه وسلم وعلى آله الطاهرين',
    'كتاب الصلاة ياب الاذان (؟")': 'كتاب الصلاة باب الأذان',
    'كتاب المعارف وايو هلال العسكري في كتاب الأوائل أن أول من وضع': 'كتاب المعارف وأبو هلال العسكري في كتاب الأوائل أن أول من وضع',
    'باب الغسل )١(\u200F الواجب والسنة': 'باب الغسل الواجب والسنة',
    'باب المزدلفة والددوت بها': 'باب المزدلفة والمبيت بها',
    'باب الصلاة في السقر': 'باب الصلاة في السفر',
    'باب غسل اميت (")': 'باب غسل الميت',
    'باب بيع الرطب يالتمر': 'باب بيع الرطب بالتمر',
    'باب بيع المدير (") وآمهات الاولاد': 'باب بيع المدبر وأمهات الأولاد',
    'باب حد الساحي والزتديق )١(\u200F': 'باب حد الساحر والزنديق',
    'باب الرجل يحج (") عن الرجل': 'باب الرجل يحج عن الرجل',
    'باب صلاذة الجمعة )١(\u200F': 'باب صلاة الجمعة',
    'باب صلاذة العيدين': 'باب صلاة العيدين',
    'باب صاذة التطوع': 'باب صلاة التطوع',
    'باب كيف وضع المدت في اللحد': 'باب كيف وضع الميت في اللحد',
    'باب ما دئبغي أن يجتنب في الصلاة': 'باب ما ينبغي أن يجتنب في الصلاة',
    'باب ما يتقض الصيام وما لا بنقضه': 'باب ما ينقض الصيام وما لا ينقضه',
    'باب ما يقل المحرم من الهوام والدواب': 'باب ما يقتل المحرم من الهوام والدواب',
    'باب مائع الزكاة': 'باب مانع الزكاة',
    'باب من لا بحل نكاحه من قرابات الزوج وائراة': 'باب من لا يحل نكاحه من قرابات الزوج والمرأة',
    'باب من لا قحل له الصدقة ومن تحل له الصدقة': 'باب من لا تحل له الصدقة ومن تحل له الصدقة',
    'باب من نكره الصلاة عليه ومن لاباأس بالصلاة عليه': 'باب من تكره الصلاة عليه ومن لا بأس بالصلاة عليه',
    'باب من يوم الناس ومن أحق بذلك': 'باب من يؤم الناس ومن أحق بذلك',
    'باب ها بيقسد الماع': 'باب ما يفسد الماء',
    'باب ها تقضي الحا نض من المئاسك': 'باب ما تقضي الحائض من المناسك',
    'باب السير بالجنازة والقيام اليها وكبف يفعل من لقدها': 'باب السير بالجنازة والقيام إليها وكيف يفعل من لقيها',
    'باب صلاة المريض وامقمى عليه وصلاة العريان': 'باب صلاة المريض والمغمى عليه وصلاة العريان',
    'باب ديع المرايحة': 'باب بيع المرابحة',
    'باب صدقة القفطر': 'باب صدقة الفطر',
    'باب جلود الاضحدة': 'باب جلود الأضحية',
    'باب الغزو والسور': 'باب الغزو والسير',
    'باب الخصب والضمان': 'باب الغصب والضمان',
    'باب الولاع': 'باب الولاء',
    'باب الوصانا': 'باب الوصايا',
    'باب الهية والصدقة': 'باب الهبة والصدقة',
    'باب طواف الصدرن': 'باب طواف الصدر',
    'باب اليدنة )6١\u200F والهدي': 'باب البدنة والهدي',
    'باب في الرعاف والنوم () والحجامة': 'باب في الرعاف والنوم والحجامة',
    'باب في المرأة توم النساء': 'باب في المرأة تؤم النساء',
    'باب قتال آهل البغي من آهل القبلة': 'باب قتال أهل البغي من أهل القبلة',
    'باب مقدار ما يتوضا به للصلاة وما يكفي الغسل': 'باب مقدار ما يتوضأ به للصلاة وما يكفي الغسل',
    'باب من أحق أن يصلي على امراة': 'باب من أحق أن يصلي على الميت',
    'باب العيد الماذون له في التجارة': 'باب العبد المأذون له في التجارة',
    'باب أكل الريا وعظم اثمه والحلف على البيع': 'باب أكل الربا وعظم إثمه والحلف على البيع',
    'باب الدهن والطيب والحجامة للمحرم': 'باب الدهن والطيب والحجامة للمحرم',
    'كتاب كفارة الايمان': 'كتاب كفارة الأيمان',
    'باب الرجل يضحى قبل أن يصلى الامام': 'باب الرجل يضحي قبل أن يصلي الإمام',
    'باب جعل الآيق': 'باب جعل الآبق',
    'باب الغرقى والهدمى': 'باب الغرقى والهدمى',
    'باب صوم التطوع': 'باب صوم التطوع',
    'باب دعاء الوثر': 'باب دعاء الوتر',
}


def merge_retranslations():
    """Merge retranslated.jsonl into translated.jsonl, replacing refused entries."""
    translated_path = os.path.join(SCRIPT_DIR, 'zaydi_translated.jsonl')
    retranslated_path = os.path.join(SCRIPT_DIR, 'zaydi_retranslated.jsonl')

    # Load all original translations
    originals = {}
    with open(translated_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            originals[row['id']] = row

    # Load retranslations
    retranslated = {}
    with open(retranslated_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            retranslated[row['id']] = row

    # Merge: retranslated overwrites originals
    replaced = 0
    for hid, row in retranslated.items():
        if hid in originals:
            originals[hid]['text_en'] = row['text_en']
            replaced += 1
        else:
            originals[hid] = row

    print(f"Replaced {replaced} translations from retranslated file")

    # Check how many still look refused
    still_refused = 0
    for row in originals.values():
        en = row.get('text_en', '')
        if is_refused(en):
            still_refused += 1
            print(f"  Still refused: {row['id']}: {en[:80]}...")

    print(f"Still refused after merge: {still_refused}")

    # Write merged file back
    with open(translated_path, 'w', encoding='utf-8') as f:
        for hid in sorted(originals.keys()):
            f.write(json.dumps(originals[hid], ensure_ascii=False) + '\n')

    print(f"Updated {translated_path} with {len(originals)} entries")
    return originals


def is_refused(text):
    """Check if a translation looks like a refusal."""
    lower = text.lower()[:100]
    refusal_phrases = [
        'i cannot', 'i can\'t', 'i\'m not able', 'i am not able',
        'i\'m unable', 'i am unable', 'as an ai',
    ]
    return any(phrase in lower for phrase in refusal_phrases)


def clean_chapter_name(name):
    """Apply chapter name fixes."""
    if name in CHAPTER_FIXES:
        return CHAPTER_FIXES[name]
    # Generic cleanup: remove stray artifacts
    name = re.sub(r'\s*\)\d+\(\s*\u200F?\s*', ' ', name)  # Remove )١(\u200F patterns
    name = re.sub(r'\s*\(\?\"\)\s*', '', name)  # Remove (؟")
    name = re.sub(r'\s*\(\"\)\s*', ' ', name)  # Remove (")
    name = re.sub(r'\s*\(""?\)\s*', ' ', name)  # Remove ("") patterns
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.rstrip(',').rstrip("'").strip()
    return name


def main():
    print("=" * 60)
    print("Step 1: Merge retranslations")
    print("=" * 60)
    translations = merge_retranslations()

    print()
    print("=" * 60)
    print("Step 2: Clean chapter names in parsed JSON")
    print("=" * 60)

    parsed_path = os.path.join(SCRIPT_DIR, 'parsed_zaydi_hadiths.json')
    with open(parsed_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    fixed_chapters = 0
    chapter_map = {}
    for h in data['hadiths']:
        old_name = h.get('chapter_name_ar', '')
        new_name = clean_chapter_name(old_name)
        if old_name != new_name:
            fixed_chapters += 1
            if old_name not in chapter_map:
                chapter_map[old_name] = new_name
                print(f"  {old_name}  →  {new_name}")
        h['chapter_name_ar'] = new_name

    print(f"Fixed {fixed_chapters} chapter name entries ({len(chapter_map)} unique corrections)")

    # Merge translations into parsed data
    print()
    print("=" * 60)
    print("Step 3: Merge translations into parsed JSON")
    print("=" * 60)
    merged = 0
    for h in data['hadiths']:
        hid = f"zayd_{h['hadith_no']:04d}"
        if hid in translations:
            en = translations[hid].get('text_en', '')
            if en and not is_refused(en):
                h['text_english'] = en
                merged += 1
            else:
                h.setdefault('text_english', '')
        else:
            h.setdefault('text_english', '')

    print(f"Merged {merged}/{len(data['hadiths'])} translations")

    # Save updated JSON
    with open(parsed_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Updated {parsed_path}")

    # Regenerate CSVs
    print()
    print("=" * 60)
    print("Step 4: Regenerate CSVs")
    print("=" * 60)
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

    # Summary
    print()
    print("=" * 60)
    print("Summary")
    print("=" * 60)
    with_en = sum(1 for h in hadiths if h.get('text_english', '').strip())
    unique_chapters = len(set(h['chapter_name_ar'] for h in hadiths))
    print(f"Total hadiths: {len(hadiths)}")
    print(f"With English translation: {with_en}")
    print(f"Without English translation: {len(hadiths) - with_en}")
    print(f"Unique chapters (after cleanup): {unique_chapters}")


if __name__ == '__main__':
    main()
