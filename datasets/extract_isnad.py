#!/usr/bin/env python3
"""
extract_isnad.py — Extract isnad (chain of narration) and metadata from parsed hadiths
======================================================================================

Extracts narrator names from the Arabic text of each hadith, identifies the
isnad/matn boundary, and adds structured metadata:
  - sanad: list of narrator names in transmission order
  - matn_ar: the prophetic text (matn) separated from the isnad
  - school: geographic/intellectual school of the primary narrator
  - tradition_chain_type: e.g., "Alid chain", "Basran chain"

Works with output from parse_openiti.py (parsed_hadiths.json).

Usage:
    python extract_isnad.py --collection ibadi-hadith
    python extract_isnad.py --collection zaydi-hadith
    python extract_isnad.py --all
"""

import argparse
import json
import os
import re
import sys
from collections import Counter

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, 'hadith-data')


# ── Known narrators with metadata ──

KNOWN_NARRATORS = {
    # Ibadi chain
    "الربيع بن حبيب": {
        "name_en": "al-Rabi ibn Habib",
        "full_ar": "الربيع بن حبيب بن عمرو الأزدي البصري",
        "school": "Basra",
        "tradition": "Ibadi",
        "tabaqah": "TABI_TABI_IN",
        "death_hijri": 175,
        "role": "compiler",
    },
    "أبو عبيدة": {
        "name_en": "Abu Ubayda Muslim ibn Abi Karima",
        "full_ar": "أبو عبيدة مسلم بن أبي كريمة التميمي",
        "school": "Basra",
        "tradition": "Ibadi",
        "tabaqah": "TABI_UN",
        "death_hijri": 145,
    },
    "جابر بن زيد": {
        "name_en": "Jabir ibn Zayd al-Azdi",
        "full_ar": "جابر بن زيد الأزدي",
        "school": "Basra",
        "tradition": "Ibadi",
        "tabaqah": "TABI_UN",
        "death_hijri": 93,
    },
    # Zaydi chain (Ahl al-Bayt golden chain)
    "زيد بن علي": {
        "name_en": "Zayd ibn Ali",
        "full_ar": "زيد بن علي بن الحسين بن علي بن أبي طالب",
        "school": "Medina",
        "tradition": "Zaydi",
        "tabaqah": "TABI_TABI_IN",
        "death_hijri": 122,
        "role": "source imam",
    },
    "أبي": {  # "his father" — context-dependent
        "name_en": "(his father)",
        "contextual": True,
    },
    "جده": {  # "his grandfather" — context-dependent
        "name_en": "(his grandfather)",
        "contextual": True,
    },
    "علي بن الحسين": {
        "name_en": "Ali ibn al-Husayn (Zayn al-Abidin)",
        "full_ar": "علي بن الحسين بن علي بن أبي طالب",
        "school": "Medina",
        "tradition": "Zaydi",
        "tabaqah": "TABI_UN",
        "death_hijri": 94,
    },
    "الحسين بن علي": {
        "name_en": "al-Husayn ibn Ali",
        "full_ar": "الحسين بن علي بن أبي طالب",
        "school": "Medina",
        "tabaqah": "SAHABA",
        "death_hijri": 61,
    },
    "علي بن أبي طالب": {
        "name_en": "Ali ibn Abi Talib",
        "full_ar": "علي بن أبي طالب",
        "school": "Medina/Kufa",
        "tabaqah": "SAHABA",
        "death_hijri": 40,
    },
    # Rida chain
    "علي بن موسى": {
        "name_en": "Ali ibn Musa al-Rida",
        "full_ar": "علي بن موسى الكاظم بن جعفر الصادق",
        "school": "Medina",
        "tradition": "Zaydi",
        "tabaqah": "LATER_SCHOLAR",
        "death_hijri": 203,
    },
    "موسى بن جعفر": {
        "name_en": "Musa ibn Ja'far (al-Kazim)",
        "full_ar": "موسى بن جعفر الصادق",
        "school": "Medina",
        "tabaqah": "LATER_SCHOLAR",
        "death_hijri": 183,
    },
    "جعفر بن محمد": {
        "name_en": "Ja'far ibn Muhammad (al-Sadiq)",
        "full_ar": "جعفر بن محمد الباقر",
        "school": "Medina",
        "tabaqah": "TABI_TABI_IN",
        "death_hijri": 148,
    },
    "محمد بن علي": {
        "name_en": "Muhammad ibn Ali (al-Baqir)",
        "full_ar": "محمد بن علي زين العابدين",
        "school": "Medina",
        "tabaqah": "TABI_UN",
        "death_hijri": 114,
    },
    # Common Companions
    "ابن عباس": {
        "name_en": "Abdullah ibn Abbas",
        "full_ar": "عبد الله بن عباس",
        "school": "Mecca/Medina",
        "tabaqah": "SAHABA",
        "death_hijri": 68,
    },
    "أبي هريرة": {
        "name_en": "Abu Hurayra",
        "full_ar": "أبو هريرة عبد الرحمن بن صخر الدوسي",
        "school": "Medina",
        "tabaqah": "SAHABA",
        "death_hijri": 57,
    },
    "عائشة": {
        "name_en": "Aisha bint Abi Bakr",
        "full_ar": "عائشة بنت أبي بكر الصديق",
        "school": "Medina",
        "tabaqah": "SAHABA",
        "death_hijri": 58,
    },
    "أنس بن مالك": {
        "name_en": "Anas ibn Malik",
        "full_ar": "أنس بن مالك",
        "school": "Basra",
        "tabaqah": "SAHABA",
        "death_hijri": 93,
    },
    "أبي سعيد الخدري": {
        "name_en": "Abu Said al-Khudri",
        "full_ar": "أبو سعيد سعد بن مالك الخدري",
        "school": "Medina",
        "tabaqah": "SAHABA",
        "death_hijri": 74,
    },
    "عبد الله بن عمر": {
        "name_en": "Abdullah ibn Umar",
        "full_ar": "عبد الله بن عمر بن الخطاب",
        "school": "Medina",
        "tabaqah": "SAHABA",
        "death_hijri": 73,
    },
}

# Isnad termination markers — where the matn begins
MATN_MARKERS = re.compile(
    r'(?:قال:\s*[«"]|أن(?:ه)?\s+قال|'
    r'قال:\s*قال\s+رسول\s+الله|'
    r'أن\s+رسول\s+الله|'
    r'أن\s+النبي[ءئ]?\s|'
    r'قال:\s*سمعت)',
    re.UNICODE,
)

# Isnad connector verbs
CONNECTOR = re.compile(
    r'\b(?:عن|حدثني|حدثنا|أخبرنا|أخبرني|قال)\b',
    re.UNICODE,
)


def extract_isnad_ibadi(text: str) -> dict:
    """Extract isnad from Ibadi hadith text.

    The standard Ibadi chain is: al-Rabi → Abu Ubayda → Jabir → Companion → Prophet
    """
    sanad = []
    matn = text

    # The Rabi/Abu Ubayda/Jabir chain is almost always present
    # Split on عن to get chain segments
    parts = re.split(r'\bعن\b', text, maxsplit=10)

    # Find matn boundary — look for قال: «, أنه قال, etc.
    matn_match = MATN_MARKERS.search(text)
    if matn_match:
        isnad_text = text[:matn_match.start()].strip()
        matn = text[matn_match.start():].strip()
    else:
        # Fallback: isnad is first 30% of text
        split_point = len(text) // 3
        isnad_text = text[:split_point]
        matn = text[split_point:]

    # Extract narrator names from isnad
    for key, info in KNOWN_NARRATORS.items():
        if key in isnad_text and not info.get('contextual'):
            sanad.append({
                "name_ar": key,
                "name_en": info["name_en"],
                "school": info.get("school", ""),
                "tabaqah": info.get("tabaqah", ""),
            })

    return {
        "sanad": sanad,
        "sanad_text": isnad_text,
        "matn_ar": matn,
        "chain_type": "Basran (Ibadi)" if sanad else "unknown",
    }


def extract_isnad_zaydi(text: str) -> dict:
    """Extract isnad from Zaydi hadith text.

    The standard Zaydi chain is: Zayd → his father → his grandfather → Ali → Prophet
    """
    sanad = []
    matn = text

    # Find matn boundary
    matn_match = MATN_MARKERS.search(text)
    if matn_match:
        isnad_text = text[:matn_match.start()].strip()
        matn = text[matn_match.start():].strip()
    else:
        split_point = len(text) // 3
        isnad_text = text[:split_point]
        matn = text[split_point:]

    # The Zaydi "golden chain": Zayd → أبيه → جده → علي
    # Resolve contextual narrators based on Zaydi chain
    zaydi_father_chain = {
        "أبيه": {"name_en": "Ali ibn al-Husayn (Zayn al-Abidin)", "school": "Medina",
                 "tabaqah": "TABI_UN"},
        "جده": {"name_en": "al-Husayn ibn Ali", "school": "Medina",
                "tabaqah": "SAHABA"},
        "آبائه": {"name_en": "his forefathers (Ahl al-Bayt)", "school": "Medina",
                  "tabaqah": "SAHABA"},
    }

    for key, info in KNOWN_NARRATORS.items():
        if key in isnad_text and not info.get('contextual'):
            sanad.append({
                "name_ar": key,
                "name_en": info["name_en"],
                "school": info.get("school", ""),
                "tabaqah": info.get("tabaqah", ""),
            })

    # Resolve contextual "his father" / "his grandfather" for Zaydi chain
    if "زيد بن علي" in isnad_text:
        for key, info in zaydi_father_chain.items():
            if key in isnad_text:
                sanad.append({
                    "name_ar": key,
                    "name_en": info["name_en"],
                    "school": info["school"],
                    "tabaqah": info["tabaqah"],
                })

    return {
        "sanad": sanad,
        "sanad_text": isnad_text,
        "matn_ar": matn,
        "chain_type": "Alid (Zaydi)" if "زيد بن علي" in isnad_text else "unknown",
    }


def extract_isnad_rida(text: str) -> dict:
    """Extract isnad from Rida appendix hadiths.

    Chain: Ali al-Rida → Musa al-Kazim → Ja'far al-Sadiq → ... → Ali → Prophet
    """
    sanad = []
    matn = text

    matn_match = MATN_MARKERS.search(text)
    if matn_match:
        isnad_text = text[:matn_match.start()].strip()
        matn = text[matn_match.start():].strip()
    else:
        isnad_text = text[:len(text) // 3]
        matn = text[len(text) // 3:]

    for key, info in KNOWN_NARRATORS.items():
        if key in isnad_text and not info.get('contextual'):
            sanad.append({
                "name_ar": key,
                "name_en": info["name_en"],
                "school": info.get("school", ""),
                "tabaqah": info.get("tabaqah", ""),
            })

    return {
        "sanad": sanad,
        "sanad_text": isnad_text,
        "matn_ar": matn,
        "chain_type": "Alid (Rida)" if "وباسناده" in text[:30] else "unknown",
    }


def enrich_collection(collection_dir: str, tradition: str):
    """Extract isnad and enrich metadata for a collection."""
    input_path = os.path.join(BASE_DIR, collection_dir, 'parsed_hadiths.json')
    if not os.path.exists(input_path):
        print(f"  ERROR: {input_path} not found")
        return

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    extractors = {
        "Ibadi": extract_isnad_ibadi,
        "Zaydi": extract_isnad_zaydi,
        "Rida": extract_isnad_rida,
    }
    extractor = extractors.get(tradition, extract_isnad_zaydi)

    narrator_stats = Counter()
    chain_types = Counter()
    has_sanad = 0

    for h in data['hadiths']:
        result = extractor(h['text_ar'])

        h['sanad'] = [n['name_en'] for n in result['sanad']]
        h['sanad_detail'] = result['sanad']
        h['matn_ar'] = result['matn_ar']
        h['chain_type'] = result['chain_type']

        if result['sanad']:
            has_sanad += 1
            # Assign school based on first narrator's school
            schools = [n['school'] for n in result['sanad'] if n.get('school')]
            h['school'] = schools[0] if schools else ''

        chain_types[result['chain_type']] += 1
        for n in result['sanad']:
            narrator_stats[n['name_en']] += 1

    # Write back
    with open(input_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    total = len(data['hadiths'])
    print(f"\n  {collection_dir}: {total} hadiths")
    print(f"  Isnad extracted: {has_sanad}/{total} ({has_sanad/total*100:.0f}%)")
    print(f"  Chain types: {dict(chain_types)}")
    print(f"  Top narrators:")
    for name, count in narrator_stats.most_common(10):
        print(f"    [{count:4d}] {name}")


def main():
    parser = argparse.ArgumentParser(description='Extract isnad and metadata from hadith collections')
    parser.add_argument('--collection', type=str,
                        help='Collection directory (ibadi-hadith, zaydi-hadith, rida-hadith)')
    parser.add_argument('--all', action='store_true', help='Process all collections')
    args = parser.parse_args()

    print("=" * 60)
    print("Isnad Extraction & Metadata Enrichment")
    print("=" * 60)

    if args.all or not args.collection:
        enrich_collection('ibadi-hadith', 'Ibadi')
        enrich_collection('zaydi-hadith', 'Zaydi')
        enrich_collection('rida-hadith', 'Rida')
    else:
        tradition_map = {
            'ibadi-hadith': 'Ibadi',
            'zaydi-hadith': 'Zaydi',
            'rida-hadith': 'Rida',
        }
        enrich_collection(args.collection, tradition_map.get(args.collection, 'Zaydi'))

    print("\nDone.")


if __name__ == '__main__':
    main()
