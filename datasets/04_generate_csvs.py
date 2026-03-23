#!/usr/bin/env python3
"""
04_generate_csvs.py
====================
Generate musnad_hadiths.csv and musnad_rawis.csv from parsed/translated hadith data.
Outputs match the schema used by all_hadiths_clean.csv and all_rawis.csv.

Hadith schema:
    id, hadith_id, source, chapter_no, hadith_no, chapter, chain_indx, text_ar, text_en

Narrator schema:
    scholar_indx, name, grade, parents, spouse, siblings, children,
    birth_date_place, places_of_stay, death_date_place, teachers, students,
    area_of_interest, tags, books, students_inds, teachers_inds,
    birth_place, birth_date, birth_date_hijri, birth_date_gregorian,
    death_date_hijri, death_date_gregorian, death_place, death_reason

Usage:
    python 04_generate_csvs.py --input translated_hadiths.json
    python 04_generate_csvs.py --input parsed_hadiths.json  # (without translations)
"""

import argparse
import csv
import json
import os

SOURCE_NAME = "al-Jāmiʿ al-Ṣaḥīḥ — Musnad al-Imām al-Rabīʿ b. Ḥabīb"

# ── Chapter mapping ──────────────────────────────────────────────────────
# Based on the index (فهرسة الكتب) from PDF page 441
CHAPTERS = {
    # (chapter_no): (arabic_name, english_name, hadith_range_start, hadith_range_end)
    1: ('الأحكام', 'Rulings (al-Aḥkām)', 588, 623),
    2: ('الأذكار', 'Remembrance (al-Adhkār)', 490, 509),
    3: ('الأشربة', 'Drinks (al-Ashriba)', 624, 653),
    4: ('الإيمان والنذور', 'Faith & Vows (al-Īmān wa-l-Nudhūr)', 654, 742),
    5: ('البيوع', 'Sales (al-Buyūʿ)', 556, 587),
    6: ('الجنائز', 'Funerals (al-Janāʾiz)', 471, 489),
    7: ('الجهاد', 'Jihad (al-Jihād)', 445, 470),
    8: ('الحج', 'Pilgrimage (al-Ḥajj)', 392, 444),
    9: ('الزكاة', 'Almsgiving (al-Zakāh)', 331, 391),
    10: ('الصلاة', 'Prayer (al-Ṣalāh)', 175, 304),
    11: ('الصوم', 'Fasting (al-Ṣawm)', 305, 330),
    12: ('الطلاق', 'Divorce (al-Ṭalāq)', 529, 555),
    13: ('الطهارة', 'Purification (al-Ṭahāra)', 1, 174),
    14: ('النكاح', 'Marriage (al-Nikāḥ)', 510, 528),
}

# Sub-chapters (bab) for the introductory sections within Purification
INTRO_BABS = {
    1: ('في النية', 'al-Niyya (Intention)'),
    2: ('في ابتداء الوحي', 'Ibtidāʾ al-Waḥy (Beginning of Revelation)'),
    3: ('في ذكر القرآن', 'Dhikr al-Qurʾān (The Quran)'),
}


def get_chapter_info(hadith_no, parsed_chapter_no=None, parsed_chapter_name=None):
    """Determine chapter info for a hadith number."""
    # Use parsed info if reliable
    if parsed_chapter_no and parsed_chapter_name:
        ch_ar = parsed_chapter_name
        ch_en = ''
        for cno, (ar, en, s, e) in CHAPTERS.items():
            if ar == parsed_chapter_name or cno == parsed_chapter_no:
                ch_en = en
                break
        if ch_en:
            return parsed_chapter_no, f"{ch_en} — {ch_ar}"

    # Fallback: use hadith number range from index
    for ch_no, (ch_ar, ch_en, start, end) in CHAPTERS.items():
        if start <= hadith_no <= end:
            return ch_no, f"{ch_en} — {ch_ar}"

    # Parts 3-4
    if 743 <= hadith_no <= 882:
        return 0, "Part 3 — Supplementary Reports (الجزء الثالث)"
    elif 883 <= hadith_no <= 1005:
        return 0, "Part 4 — Mursal Reports (الجزء الرابع)"

    return 0, "Unknown"


def get_part(hadith_no):
    """Determine which part (juzʾ) a hadith belongs to."""
    if hadith_no <= 391:
        return 1
    elif hadith_no <= 742:
        return 2
    elif hadith_no <= 882:
        return 3
    else:
        return 4


def generate_hadith_csv(hadiths, output_path):
    """Generate musnad_hadiths.csv matching all_hadiths_clean.csv schema."""
    fieldnames = ['id', 'hadith_id', 'source', 'chapter_no', 'hadith_no',
                  'chapter', 'chain_indx', 'text_ar', 'text_en']

    rows = []
    for h in hadiths:
        h_no = h['hadith_no']
        ch_no, chapter_label = get_chapter_info(
            h_no,
            h.get('chapter_no'),
            h.get('chapter_name')
        )
        part = get_part(h_no)

        # Build chain_indx string
        chain = h.get('chain_indx', '')
        if not chain:
            # Default chain for Parts 1-2: al-Rabi' -> Abu 'Ubayda -> Jabir
            if part <= 2:
                chain = '60003,60002,60001'
            else:
                chain = '60003'

        # Build English text placeholder if not translated
        text_en = h.get('text_en', '')
        if not text_en:
            text_en = (f"Hadith {h_no} — Part {part} — "
                       f"{chapter_label} — "
                       f"Chain: al-Rabīʿ → Abū ʿUbayda → Jābir b. Zayd")

        row = {
            'id': f"musnad_{h_no:04d}",
            'hadith_id': h_no,
            'source': SOURCE_NAME,
            'chapter_no': ch_no,
            'hadith_no': h_no,
            'chapter': chapter_label,
            'chain_indx': chain,
            'text_ar': h.get('text_ar', ''),
            'text_en': text_en,
        }
        rows.append(row)

    # Sort by hadith number
    rows.sort(key=lambda r: r['hadith_no'])

    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} hadiths → {output_path}")
    return rows


# ── Narrator data ────────────────────────────────────────────────────────
NARRATORS = [
    {
        'scholar_indx': 60001,
        'name': 'Jābir b. Zayd al-Azdī (Abū al-Shaʿthāʾ) ( جابر بن زيد الأزدي )',
        'grade': "Follower(Tabi')",
        'birth_date_place': 'Firq, Oman (فرق، عمان)',
        'places_of_stay': 'Basra, Iraq; Mecca (during Hajj)',
        'death_date_place': 'Basra, Iraq',
        'teachers': 'Ibn ʿAbbās, ʿĀʾisha, Anas b. Mālik, Abū Hurayra, Abū Saʿīd al-Khudrī, Ibn ʿUmar, Jābir b. ʿAbd Allāh, Ṣuḥār b. al-ʿAbbās al-ʿAbdī',
        'students': 'Abū ʿUbayda Muslim b. Abī Karīma, Ḍumām b. al-Sāʾib, ʿAmr b. Dīnār, Qatāda, ʿAmāra b. Ḥayyān',
        'area_of_interest': 'Fiqh, Hadith, Legal Opinions, Ibāḍī founding scholarship',
        'tags': 'Ibāḍī leader, Tābiʿī, Basran scholar, Omani origin, central authority in the Musnad, al-Imām al-Ḥujja',
        'books': 'al-Jāmiʿ al-Ṣaḥīḥ (source authority)',
        'students_inds': '60002,60015',
        'teachers_inds': '60004,60005,60006,60007,60008,60012,60013,60020',
        'birth_place': 'Firq, Oman',
        'death_date_hijri': '93 AH (some say 96, 103, 104)',
        'death_date_gregorian': '711-712 CE',
        'death_place': 'Basra, Iraq',
    },
    {
        'scholar_indx': 60002,
        'name': 'Abū ʿUbayda Muslim b. Abī Karīma al-Tamīmī ( أبو عبيدة مسلم بن أبي كريمة التميمي )',
        'grade': "Follower(Tabi')",
        'birth_date_place': 'Basra, Iraq',
        'places_of_stay': 'Basra, Iraq',
        'death_date_place': 'Basra, Iraq',
        'teachers': 'Jābir b. Zayd al-Azdī',
        'students': 'al-Rabīʿ b. Ḥabīb al-Farāhīdī, Abū Sufyān Maḥbūb b. al-Ruḥayl',
        'area_of_interest': 'Ibāḍī leadership, Fiqh, Hadith',
        'tags': 'Second Ibāḍī leader after Jābir, Basran, key link in golden chain of the Musnad',
        'students_inds': '60003,60009',
        'teachers_inds': '60001',
        'birth_place': 'Basra',
        'death_date_hijri': 'shortly after 150 AH',
        'death_date_gregorian': 'c. 767 CE',
        'death_place': 'Basra, Iraq',
    },
    {
        'scholar_indx': 60003,
        'name': 'al-Rabīʿ b. Ḥabīb b. ʿAmr al-Farāhīdī al-Azdī ( الربيع بن حبيب بن عمرو الفراهيدي الأزدي )',
        'grade': '3rd generation',
        'birth_date_place': 'Basra, Iraq (Omani origin)',
        'places_of_stay': 'Basra, Iraq; Oman',
        'death_date_place': 'Oman',
        'teachers': 'Abū ʿUbayda Muslim b. Abī Karīma, Ḍumām b. al-Sāʾib, ʿAbd al-Aʿlā b. Dāwūd, Yaḥyā b. Kathīr',
        'students': 'Abū Sufyān Maḥbūb b. al-Ruḥayl, Mūsā b. Abī Jābir, Bashīr b. al-Mundhir, Aflah b. ʿAbd al-Wahhāb',
        'area_of_interest': 'Hadith compilation, Fiqh, Ibāḍī scholarship',
        'tags': 'Compiler of the Musnad, al-Imām al-Kāmil, Ibāḍī muhaddith, Basran-Omani',
        'books': 'al-Jāmiʿ al-Ṣaḥīḥ (Musnad al-Rabīʿ b. Ḥabīb)',
        'students_inds': '60009,60014',
        'teachers_inds': '60002,60015,60016',
        'birth_place': 'Basra (Omani family)',
        'death_date_hijri': '175-180 AH',
        'death_date_gregorian': '791-796 CE',
        'death_place': 'Oman',
    },
    {
        'scholar_indx': 60004,
        'name': 'ʿAbd Allāh b. ʿAbbās ( عبدالله بن عباس )',
        'grade': 'Companion(Sahabi)',
        'parents': "al-ʿAbbās b. ʿAbd al-Muṭṭalib",
        'birth_date_place': 'Mecca',
        'places_of_stay': 'Mecca, Medina, Basra, Ṭāʾif',
        'death_date_place': 'Ṭāʾif',
        'teachers': 'Prophet Muḥammad ﷺ, ʿUmar b. al-Khaṭṭāb, ʿAlī b. Abī Ṭālib',
        'students': 'Jābir b. Zayd, ʿIkrima, Mujāhid, Saʿīd b. Jubayr, ʿAṭāʾ b. Abī Rabāḥ',
        'area_of_interest': 'Tafsīr, Fiqh, Hadith',
        'tags': 'Ḥibr al-Umma, Tarjumān al-Qurʾān, Companion, cousin of the Prophet, most cited Companion in Parts 1-2',
        'teachers_inds': '60001',
        'birth_place': 'Mecca',
        'birth_date': '3 years before Hijra',
        'birth_date_gregorian': 'c. 619 CE',
        'death_date_hijri': '68 AH',
        'death_date_gregorian': '687 CE',
        'death_place': 'Ṭāʾif',
    },
    {
        'scholar_indx': 60005,
        'name': "ʿĀʾisha bt. Abī Bakr ( عائشة بنت أبي بكر )",
        'grade': 'Companion(Sahabi)',
        'birth_date_place': 'Mecca',
        'places_of_stay': 'Mecca, Medina',
        'death_date_place': 'Medina',
        'teachers': 'Prophet Muḥammad ﷺ',
        'students': 'Jābir b. Zayd, ʿUrwa b. al-Zubayr, al-Qāsim b. Muḥammad',
        'area_of_interest': 'Hadith, Fiqh, Tafsīr',
        'tags': 'Umm al-Muʾminīn, major Companion narrator',
        'teachers_inds': '',
        'birth_place': 'Mecca',
        'death_date_hijri': '58 AH',
        'death_date_gregorian': '678 CE',
        'death_place': 'Medina',
    },
    {
        'scholar_indx': 60006,
        'name': "Abū Saʿīd al-Khudrī ( أبو سعيد الخدري )",
        'grade': 'Companion(Sahabi)',
        'birth_date_place': 'Medina',
        'places_of_stay': 'Medina',
        'death_date_place': 'Medina',
        'teachers': 'Prophet Muḥammad ﷺ',
        'students': 'Jābir b. Zayd, Abū Salama, ʿAṭāʾ b. Yasār',
        'area_of_interest': 'Hadith',
        'tags': 'Companion, Anṣārī, prolific narrator',
        'death_date_hijri': '74 AH',
        'death_date_gregorian': '693 CE',
        'death_place': 'Medina',
    },
    {
        'scholar_indx': 60007,
        'name': "Abū Hurayra ( أبو هريرة )",
        'grade': 'Companion(Sahabi)',
        'birth_date_place': 'Yemen',
        'places_of_stay': 'Medina',
        'death_date_place': 'Medina',
        'teachers': 'Prophet Muḥammad ﷺ',
        'students': 'Jābir b. Zayd, Saʿīd b. al-Musayyib, Abū Salama',
        'area_of_interest': 'Hadith',
        'tags': 'Companion, most prolific narrator overall, frequently cited in the Musnad',
        'death_date_hijri': '57 AH',
        'death_date_gregorian': '676-677 CE',
        'death_place': 'Medina',
    },
    {
        'scholar_indx': 60008,
        'name': "Anas b. Mālik ( أنس بن مالك )",
        'grade': 'Companion(Sahabi)',
        'birth_date_place': 'Medina',
        'places_of_stay': 'Medina, Basra',
        'death_date_place': 'Basra',
        'teachers': 'Prophet Muḥammad ﷺ',
        'students': 'Jābir b. Zayd, Qatāda, Thābit al-Bunānī',
        'area_of_interest': 'Hadith',
        'tags': 'Companion, khādim al-Nabī (servant of the Prophet), long-lived',
        'death_date_hijri': '93 AH',
        'death_date_gregorian': '711-712 CE',
        'death_place': 'Basra',
    },
    {
        'scholar_indx': 60009,
        'name': "Abū Sufyān Maḥbūb b. al-Ruḥayl ( أبو سفيان محبوب بن الرحيل )",
        'grade': '4th generation',
        'birth_date_place': 'Basra, Iraq',
        'places_of_stay': 'Basra, Iraq',
        'death_date_place': 'Basra, Iraq',
        'teachers': 'al-Rabīʿ b. Ḥabīb, Abū ʿUbayda Muslim b. Abī Karīma',
        'students': '',
        'area_of_interest': 'Hadith transmission',
        'tags': 'Transmitter of al-Rabīʿ\'s Musnad, Basran',
        'teachers_inds': '60003,60002',
        'death_date_hijri': 'c. 200 AH',
        'death_date_gregorian': 'c. 815 CE',
        'death_place': 'Basra, Iraq',
    },
    {
        'scholar_indx': 60010,
        'name': "ʿUmar b. al-Khaṭṭāb ( عمر بن الخطاب )",
        'grade': 'Companion(Sahabi)',
        'birth_date_place': 'Mecca',
        'places_of_stay': 'Mecca, Medina',
        'death_date_place': 'Medina',
        'teachers': 'Prophet Muḥammad ﷺ',
        'students': 'Jābir b. Zayd, Ibn ʿAbbās, Ibn ʿUmar',
        'area_of_interest': 'Fiqh, Hadith, Governance',
        'tags': 'al-Fārūq, Second Caliph, Companion',
        'death_date_hijri': '23 AH',
        'death_date_gregorian': '644 CE',
        'death_place': 'Medina',
        'death_reason': 'Martyred',
    },
    {
        'scholar_indx': 60011,
        'name': "ʿAlī b. Abī Ṭālib ( علي بن أبي طالب )",
        'grade': 'Companion(Sahabi)',
        'birth_date_place': 'Mecca',
        'places_of_stay': 'Mecca, Medina, Kufa',
        'death_date_place': 'Kufa',
        'teachers': 'Prophet Muḥammad ﷺ',
        'students': 'Jābir b. Zayd, Ibn ʿAbbās',
        'area_of_interest': 'Fiqh, Hadith, Quranic Sciences',
        'tags': 'Fourth Caliph, Companion, cousin and son-in-law of the Prophet',
        'death_date_hijri': '40 AH',
        'death_date_gregorian': '661 CE',
        'death_place': 'Kufa',
        'death_reason': 'Martyred',
    },
    {
        'scholar_indx': 60012,
        'name': "ʿAbd Allāh b. ʿUmar ( عبدالله بن عمر )",
        'grade': 'Companion(Sahabi)',
        'birth_date_place': 'Mecca',
        'places_of_stay': 'Mecca, Medina',
        'death_date_place': 'Mecca',
        'teachers': 'Prophet Muḥammad ﷺ, ʿUmar b. al-Khaṭṭāb',
        'students': 'Jābir b. Zayd, Nāfiʿ, Sālim b. ʿAbd Allāh',
        'area_of_interest': 'Hadith, Fiqh',
        'tags': 'Companion, prolific narrator, known for strict adherence to Sunna',
        'death_date_hijri': '73 AH',
        'death_date_gregorian': '693 CE',
        'death_place': 'Mecca',
    },
    {
        'scholar_indx': 60013,
        'name': "Jābir b. ʿAbd Allāh al-Anṣārī ( جابر بن عبد الله الأنصاري )",
        'grade': 'Companion(Sahabi)',
        'birth_date_place': 'Medina',
        'places_of_stay': 'Medina',
        'death_date_place': 'Medina',
        'teachers': 'Prophet Muḥammad ﷺ',
        'students': 'Jābir b. Zayd, Abū al-Zubayr, ʿAmr b. Dīnār',
        'area_of_interest': 'Hadith',
        'tags': 'Companion, Anṣārī, prolific narrator',
        'death_date_hijri': '78 AH',
        'death_date_gregorian': '697 CE',
        'death_place': 'Medina',
    },
    {
        'scholar_indx': 60014,
        'name': "Aflah b. ʿAbd al-Wahhāb ( أفلح بن عبد الوهاب )",
        'grade': '4th generation',
        'birth_date_place': 'Oman',
        'places_of_stay': 'Oman',
        'death_date_place': 'Oman',
        'teachers': 'al-Rabīʿ b. Ḥabīb',
        'area_of_interest': 'Hadith transmission',
        'tags': 'Ibāḍī scholar, transmitter of Part 4 content',
        'teachers_inds': '60003',
    },
    {
        'scholar_indx': 60015,
        'name': "Ḍumām b. al-Sāʾib ( ضمام بن السائب )",
        'grade': "Follower(Tabi')",
        'birth_date_place': 'Basra/Oman',
        'places_of_stay': 'Basra, Iraq; Oman',
        'death_date_place': 'Basra or Oman',
        'teachers': 'Jābir b. Zayd al-Azdī',
        'students': 'al-Rabīʿ b. Ḥabīb',
        'area_of_interest': 'Hadith, Ibāḍī scholarship',
        'tags': 'Ibāḍī scholar, additional chain in the Musnad alongside Abū ʿUbayda',
        'students_inds': '60003',
        'teachers_inds': '60001',
    },
    {
        'scholar_indx': 60016,
        'name': "ʿAbd al-Aʿlā b. Dāwūd ( عبد الأعلى بن داود )",
        'grade': '3rd generation',
        'teachers': 'various',
        'students': 'al-Rabīʿ b. Ḥabīb',
        'area_of_interest': 'Hadith',
        'tags': 'Additional teacher of al-Rabīʿ, appears in Part 3 chains',
        'students_inds': '60003',
    },
    {
        'scholar_indx': 60017,
        'name': "Abū Yaqūb Yūsuf b. Ibrāhīm al-Warjlānī ( أبو يعقوب يوسف بن إبراهيم الوارجلاني )",
        'grade': '6th century AH scholar',
        'places_of_stay': 'Wargla (Algeria), North Africa',
        'teachers': 'Ibāḍī scholarly tradition',
        'area_of_interest': 'Tafsīr, Hadith arrangement, Fiqh',
        'tags': 'Arranger (murattib) of the Musnad into its current chapter order, author of al-Dalīl wa-l-Burhān',
        'books': 'al-Dalīl wa-l-Burhān (commentary on the Musnad)',
    },
    {
        'scholar_indx': 60020,
        'name': "Ṣuḥār b. al-ʿAbbās al-ʿAbdī ( صحار بن العباس العبدي )",
        'grade': 'Companion(Sahabi)',
        'places_of_stay': 'Oman',
        'teachers': 'Prophet Muḥammad ﷺ',
        'students': 'Jābir b. Zayd',
        'area_of_interest': 'Hadith',
        'tags': 'Omani Companion, teacher of Jābir b. Zayd',
        'students_inds': '60001',
    },
]

NARRATOR_FIELDS = [
    'scholar_indx', 'name', 'grade', 'parents', 'spouse', 'siblings', 'children',
    'birth_date_place', 'places_of_stay', 'death_date_place', 'teachers', 'students',
    'area_of_interest', 'tags', 'books', 'students_inds', 'teachers_inds',
    'birth_place', 'birth_date', 'birth_date_hijri', 'birth_date_gregorian',
    'death_date_hijri', 'death_date_gregorian', 'death_place', 'death_reason',
]


def generate_narrator_csv(output_path):
    """Generate musnad_rawis.csv."""
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=NARRATOR_FIELDS)
        writer.writeheader()
        for narrator in NARRATORS:
            row = {field: narrator.get(field, '') for field in NARRATOR_FIELDS}
            writer.writerow(row)

    print(f"Wrote {len(NARRATORS)} narrators → {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Generate CSVs from parsed hadith data')
    parser.add_argument('--input', default='parsed_hadiths.json', help='Input JSON')
    parser.add_argument('--hadith-csv', default=None, help='Output hadith CSV path')
    parser.add_argument('--narrator-csv', default=None, help='Output narrator CSV path')
    parser.add_argument('--output-dir', default='.', help='Output directory')
    args = parser.parse_args()

    # Determine output paths
    if args.hadith_csv is None:
        args.hadith_csv = os.path.join(args.output_dir, 'musnad_hadiths.csv')
    if args.narrator_csv is None:
        args.narrator_csv = os.path.join(args.output_dir, 'musnad_rawis.csv')

    # Load hadiths
    print(f"Loading hadiths from {args.input}...")
    with open(args.input, 'r', encoding='utf-8') as f:
        hadiths = json.load(f)
    print(f"Loaded {len(hadiths)} hadiths.")

    # Generate CSVs
    generate_hadith_csv(hadiths, args.hadith_csv)
    generate_narrator_csv(args.narrator_csv)

    # Summary
    print(f"\nSummary:")
    print(f"  Hadiths CSV: {args.hadith_csv}")
    print(f"  Narrators CSV: {args.narrator_csv}")
    print(f"  Total hadiths: {len(hadiths)}")
    print(f"  Total narrators: {len(NARRATORS)}")


if __name__ == '__main__':
    main()
