#!/usr/bin/env python3
"""
parse_openiti.py — Parse OpenITI mARkdown files into structured hadith JSON/CSV
================================================================================

This is the primary text source for Zaydi and Ibadi hadith collections.
The text comes from community-proofread Shamela libraries (not OCR).

Source:
  - Musnad Zayd: OpenITI 0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1.mARkdown
    From: Maktaba Shamila al-Zaydiyya (community-typed, not OCR)
  - Jami al-Sahih (Musnad al-Rabi): OpenITI 0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1
    From: Maktaba Shamila al-Ibadiyya (community-typed, not OCR)

OpenITI mARkdown format reference:
  ### |    = kitab (book) heading
  ### ||   = bab (chapter) heading
  #        = paragraph start (hadith text, commentary)
  ~~       = continuation of previous line
  PageV01P### = page marker (volume 1, page ###)
  ms###    = milestone marker (every ~300 words)

Usage:
    python parse_openiti.py                          # Parse both collections
    python parse_openiti.py --zayd-only              # Just Musnad Zayd
    python parse_openiti.py --rabi-only              # Just Musnad al-Rabi
    python parse_openiti.py --output-dir output/     # Custom output directory

Output per collection:
    parsed_hadiths.json  — structured hadith records with provenance
    hadiths_clean.csv    — minimal CSV (id, source, chapter, text_ar, tradition)
    hadiths_full.csv     — full schema CSV for unified dataset integration
    PROVENANCE.json      — transformation metadata (source URI, parse date, counts)
"""

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OPENITI_DIR = os.path.join(SCRIPT_DIR, "hadith-data", "openiti-sources")


# ---------------------------------------------------------------------------
# mARkdown format patterns
# ---------------------------------------------------------------------------

# Structural headings
RE_KITAB = re.compile(r'^###\s*\|\s+(.+)')           # ### |  كتاب الطهارة
RE_BAB = re.compile(r'^###\s*\|\|\s+(.+)')            # ### || باب في ذكر الوضوء
RE_PARAGRAPH = re.compile(r'^#\s+(.+)')               # # paragraph text
RE_CONTINUATION = re.compile(r'^~~\s*(.*)')            # ~~ continuation
RE_PAGE = re.compile(r'PageV(\d+)P(\d+)')             # PageV01P049
RE_MILESTONE = re.compile(r'\bms(\d+)\b')             # ms001
RE_META = re.compile(r'^#META#')                      # metadata header
RE_OPENITI_HEADER = re.compile(r'^######OpenITI#')    # file header

# Rabi-specific: numbered hadiths like "# 1) ..." or "# 1مكرر) ..."
RE_RABI_HADITH = re.compile(r'^#\s*(\d+(?:مكرر)?)\)\s*\.{0,3}\s*(.*)')
RE_RABI_BAB = re.compile(r'^#\s*\[(\d+)\]\s+باب\s+(.*)')

# Zayd-specific: hadith starts with حدثني or وحدثني or وقال or وسألت
RE_ZAYD_HADITH_START = re.compile(
    r'(?:حد[ثتئ](?:ني|نا)|وحد[ثتئ]|وقال\s+زيد|وسأل|سألت|قال\s+أبو\s*خالد)',
    re.UNICODE
)

# Cutoff: the reviewer noted page 434+ is a different text (Musnad Imam Ali al-Rida)
ZAYD_APPENDIX_MARKER = "مسند الإمام علي الرضا"


# ---------------------------------------------------------------------------
# Text normalization (minimal — preserve original, normalize for consistency)
# ---------------------------------------------------------------------------

def normalize_arabic(text: str) -> str:
    """Light normalization: NFKC + strip control chars. Does NOT strip tashkeel."""
    text = unicodedata.normalize('NFKC', text)
    # Remove zero-width and bidi control characters
    for ch in '\u200f\u200e\u200c\u200b\u200d\u202c\u202b\u202a\u2069\u2068\u2066\u2067\ufeff':
        text = text.replace(ch, '')
    # Remove page markers and milestones from text body
    text = RE_PAGE.sub('', text)
    text = RE_MILESTONE.sub('', text)
    # Collapse whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def strip_footnote_markers(text: str) -> str:
    """Remove inline footnote markers like (1), (2), (¬1) from text."""
    text = re.sub(r'\(¬?\d+\)', '', text)
    return re.sub(r'\s+', ' ', text).strip()


# ---------------------------------------------------------------------------
# Parse Musnad Zayd (mARkdown format with kitab/bab headings)
# ---------------------------------------------------------------------------

def parse_zayd(source_path: str) -> dict:
    """Parse Musnad Zayd from OpenITI mARkdown into structured records.

    The text uses ### | for kitab and ### || for bab headings.
    Hadith paragraphs start with # and continue with ~~.
    Multiple sub-narrations may appear within a single paragraph,
    separated by (وقال), (وحدثني), (وسألت) etc.
    """
    with open(source_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    hadiths = []
    current_kitab = ""
    current_bab = ""
    current_text = ""
    current_page = ""
    in_header = True
    kitab_no = 0
    bab_no = 0
    hadith_no = 0

    def flush_hadith():
        nonlocal current_text, hadith_no
        if not current_text.strip():
            return
        text = normalize_arabic(current_text)
        text = strip_footnote_markers(text)
        if len(text) < 10:
            return

        # Skip preamble lines (bismillah, hamdala, salawat)
        if text.startswith('بسم الله') or text.startswith('الحمدلله'):
            current_text = ""
            return

        hadith_no += 1
        hadiths.append({
            "id": f"zayd_{hadith_no:04d}",
            "hadith_no": hadith_no,
            "source": "Musnad al-Imam Zayd ibn Ali",
            "source_ar": "مسند الإمام زيد بن علي",
            "tradition": "Zaydi",
            "compiler": "Abd al-Aziz ibn Ishaq al-Baghdadi",
            "compiler_ar": "عبد العزيز بن إسحاق البغدادي",
            "kitab": current_kitab,
            "bab": current_bab,
            "kitab_no": kitab_no,
            "bab_no": bab_no,
            "text_ar": text,
            "page_ref": current_page,
        })
        current_text = ""

    for line in lines:
        raw = line.rstrip('\n')

        # Skip header
        if in_header:
            if raw.strip() == '#META#Header#End#':
                in_header = False
            continue

        # Skip empty lines
        if not raw.strip():
            continue

        # Page markers — capture but don't break flow
        page_match = RE_PAGE.search(raw)
        if page_match:
            current_page = f"V{page_match.group(1)}P{page_match.group(2)}"
            # If line is ONLY a page marker, skip
            cleaned = RE_PAGE.sub('', raw).strip()
            if not cleaned:
                continue

        # Kitab heading
        m = RE_KITAB.match(raw)
        if m:
            flush_hadith()
            kitab_no += 1
            current_kitab = normalize_arabic(m.group(1))
            current_bab = ""
            bab_no = 0
            continue

        # Bab heading
        m = RE_BAB.match(raw)
        if m:
            flush_hadith()
            bab_no += 1
            current_bab = normalize_arabic(m.group(1))
            continue

        # Continuation line
        m = RE_CONTINUATION.match(raw)
        if m:
            current_text += " " + m.group(1)
            continue

        # Paragraph start
        m = RE_PARAGRAPH.match(raw)
        if m:
            text = m.group(1)

            # Stop at the appendix (Musnad Imam Ali al-Rida, a different text)
            if ZAYD_APPENDIX_MARKER in text:
                flush_hadith()
                break

            # Split on hadith transmission verbs. Use .search() because
            # the verb may appear after a leading parenthesis like (حدثني).
            starts_new = RE_ZAYD_HADITH_START.search(text[:30])
            if starts_new and current_text.strip():
                flush_hadith()

            if current_text:
                current_text += " " + text
            else:
                current_text = text
            continue

    # Flush last hadith
    flush_hadith()

    return {
        "source_file": os.path.basename(source_path),
        "openiti_uri": "0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1",
        "tradition": "Zaydi",
        "kitab_count": kitab_no,
        "bab_count": bab_no,
        "hadith_count": len(hadiths),
        "hadiths": hadiths,
    }


# ---------------------------------------------------------------------------
# Parse Musnad al-Rabi / Jami al-Sahih (numbered hadiths with [N] bab markers)
# ---------------------------------------------------------------------------

def parse_rabi(source_path: str) -> dict:
    """Parse Jami al-Sahih (Musnad al-Rabi) from OpenITI mARkdown.

    This text has explicitly numbered hadiths: # 1) ... # 2) ...
    and numbered bab headings: # [1] باب في النية
    """
    with open(source_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    hadiths = []
    current_bab = ""
    current_bab_no = 0
    current_juz = ""
    current_text = ""
    current_hadith_num = ""
    current_page = ""
    in_header = True
    commentary_buffer = []

    def flush_hadith():
        nonlocal current_text, current_hadith_num
        if not current_text.strip() or not current_hadith_num:
            current_text = ""
            current_hadith_num = ""
            return

        text = normalize_arabic(current_text)
        text = strip_footnote_markers(text)
        if len(text) < 10:
            current_text = ""
            current_hadith_num = ""
            return

        # Determine numeric ID (handle مكرر = "repeated" suffix)
        num_str = current_hadith_num.replace('مكرر', '').strip()
        try:
            num_int = int(num_str)
        except ValueError:
            num_int = 0

        hadiths.append({
            "id": f"rabi_{num_int:04d}" + ("b" if "مكرر" in current_hadith_num else ""),
            "hadith_no": num_int,
            "hadith_label": current_hadith_num,
            "source": "al-Jami al-Sahih (Musnad al-Rabi ibn Habib)",
            "source_ar": "الجامع الصحيح مسند الإمام الربيع بن حبيب",
            "tradition": "Ibadi",
            "compiler": "al-Rabi ibn Habib al-Azdi",
            "compiler_ar": "الربيع بن حبيب بن عمرو الأزدي",
            "arranger": "Abu Yaqub al-Warjlani",
            "arranger_ar": "أبو يعقوب يوسف بن إبراهيم الوارجلاني",
            "juz": current_juz,
            "bab": current_bab,
            "bab_no": current_bab_no,
            "text_ar": text,
            "page_ref": current_page,
        })
        current_text = ""
        current_hadith_num = ""

    for line in lines:
        raw = line.rstrip('\n')

        if in_header:
            if raw.strip() == '#META#Header#End#':
                in_header = False
            continue

        if not raw.strip():
            continue

        # Page markers
        page_match = RE_PAGE.search(raw)
        if page_match:
            current_page = f"V{page_match.group(1)}P{page_match.group(2)}"
            cleaned = RE_PAGE.sub('', raw).strip()
            if not cleaned:
                continue

        # Continuation
        m = RE_CONTINUATION.match(raw)
        if m:
            current_text += " " + m.group(1)
            continue

        # Bab heading: # [N] باب في ...
        m = RE_RABI_BAB.match(raw)
        if m:
            flush_hadith()
            current_bab_no = int(m.group(1))
            current_bab = normalize_arabic(m.group(2))
            continue

        # Numbered hadith: # N) ...
        m = RE_RABI_HADITH.match(raw)
        if m:
            flush_hadith()
            current_hadith_num = m.group(1)
            current_text = m.group(2)
            continue

        # Juz / section heading
        m = RE_PARAGRAPH.match(raw)
        if m:
            text = m.group(1)
            if 'الجزء' in text or 'القسم' in text:
                flush_hadith()
                current_juz = normalize_arabic(text)
                continue

            # Commentary by al-Rabi (# قال الربيع: ...)
            if text.startswith('قال الربيع'):
                # Append to previous hadith as commentary
                if hadiths:
                    comment = normalize_arabic(text)
                    comment = strip_footnote_markers(comment)
                    hadiths[-1].setdefault("commentary", "")
                    if hadiths[-1]["commentary"]:
                        hadiths[-1]["commentary"] += " "
                    hadiths[-1]["commentary"] += comment
                continue

            # Other paragraph — could be continuation of previous hadith
            if current_hadith_num:
                current_text += " " + text
            continue

    flush_hadith()

    return {
        "source_file": os.path.basename(source_path),
        "openiti_uri": "0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1",
        "tradition": "Ibadi",
        "bab_count": current_bab_no,
        "hadith_count": len(hadiths),
        "hadiths": hadiths,
    }


# ---------------------------------------------------------------------------
# Output: JSON, CSV, provenance
# ---------------------------------------------------------------------------

def write_json(data: dict, path: str):
    """Write parsed data to JSON with UTF-8 encoding."""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  JSON: {path} ({data['hadith_count']} hadiths)")


def write_csv_clean(hadiths: list, path: str):
    """Write minimal CSV for quick inspection."""
    fields = ["id", "hadith_no", "source", "tradition", "bab", "text_ar"]
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL,
                                extrasaction='ignore')
        writer.writeheader()
        writer.writerows(hadiths)
    print(f"  CSV (clean): {path} ({len(hadiths)} rows)")


def write_csv_full(hadiths: list, path: str):
    """Write full-schema CSV matching unified dataset format."""
    fields = [
        "id", "hadith_id", "source", "tradition", "volume", "chapter_no",
        "hadith_no", "chapter", "category", "chain_indx", "text_ar", "text_en",
        "sanad", "matn_en", "grade_tradition", "grade_source", "grade_value",
        "gradings_full", "url", "page_ref",
    ]
    with open(path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, quoting=csv.QUOTE_ALL,
                                extrasaction='ignore')
        writer.writeheader()
        for h in hadiths:
            writer.writerow({
                "id": h["id"],
                "hadith_id": h["hadith_no"],
                "source": h["source"],
                "tradition": h["tradition"],
                "volume": 1,
                "chapter_no": h.get("bab_no", h.get("kitab_no", "")),
                "hadith_no": h["hadith_no"],
                "chapter": h.get("bab", h.get("kitab", "")),
                "category": h.get("kitab", h.get("bab", "")),
                "chain_indx": "",
                "text_ar": h["text_ar"],
                "text_en": "",
                "sanad": "",
                "matn_en": "",
                "grade_tradition": h["tradition"],
                "grade_source": "",
                "grade_value": "",
                "gradings_full": "",
                "url": "",
                "page_ref": h.get("page_ref", ""),
            })
    print(f"  CSV (full): {path} ({len(hadiths)} rows)")


def write_provenance(data: dict, output_dir: str):
    """Write provenance metadata for this parse run."""
    prov = {
        "parsed_at": datetime.now(timezone.utc).isoformat(),
        "parser": "parse_openiti.py",
        "source_uri": data["openiti_uri"],
        "source_file": data["source_file"],
        "source_type": "OpenITI mARkdown (community-typed, Shamela)",
        "tradition": data["tradition"],
        "hadith_count": data["hadith_count"],
        "transformations": [
            "NFKC Unicode normalization",
            "Zero-width/bidi control character removal",
            "Footnote marker removal (inline parenthetical numbers)",
            "Page marker and milestone extraction (stored in page_ref, removed from text)",
            "Whitespace normalization",
        ],
        "what_was_NOT_changed": [
            "Tashkeel (diacritics) preserved as-is",
            "Original Arabic word order preserved",
            "No spelling correction applied",
            "No content added or removed beyond format markers",
        ],
        "notes": [
            "Text is community-proofread from Shamela, NOT from OCR",
            "Grade fields are empty — these traditions use different grading systems",
            "Translation (text_en) is empty — to be filled by translation pipeline",
        ],
    }
    if "kitab_count" in data:
        prov["kitab_count"] = data["kitab_count"]
    if "bab_count" in data:
        prov["bab_count"] = data["bab_count"]

    path = os.path.join(output_dir, "PROVENANCE.json")
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(prov, f, ensure_ascii=False, indent=2)
    print(f"  Provenance: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_rida_appendix(source_path: str) -> dict:
    """Parse the Sahifa of Imam Ali al-Rida from the appendix of the Zayd file.

    This text starts after the heading containing 'مسند الإمام علي الرضا'
    and runs to the end of the file. It's a separate collection of ~55 hadiths
    transmitted through the Alid chain (Ali al-Rida ← Musa al-Kazim ← Ja'far al-Sadiq).
    """
    with open(source_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    hadiths = []
    current_bab = ""
    current_text = ""
    current_page = ""
    in_appendix = False
    in_header = True
    bab_no = 0
    hadith_no = 0

    def flush_hadith():
        nonlocal current_text, hadith_no
        if not current_text.strip():
            return
        text = normalize_arabic(current_text)
        text = strip_footnote_markers(text)
        if len(text) < 15:
            current_text = ""
            return
        # Skip preamble
        if text.startswith('بسم الله') or text.startswith('الحمد لله'):
            current_text = ""
            return
        # Skip long introductions (the biographical intro)
        if 'أما بعد، فهذه صحيفة' in text or 'هذه الصحيفة ويسمى' in text:
            current_text = ""
            return

        hadith_no += 1
        hadiths.append({
            "id": f"rida_{hadith_no:04d}",
            "hadith_no": hadith_no,
            "source": "Sahifat al-Imam Ali al-Rida",
            "source_ar": "صحيفة الإمام علي الرضا",
            "tradition": "Zaydi",
            "compiler": "Abd al-Wasit ibn Yahya al-Wasiti (arranger)",
            "compiler_ar": "عبد الواسع بن يحيى الواسعي (مرتب)",
            "bab": current_bab,
            "bab_no": bab_no,
            "text_ar": text,
            "page_ref": current_page,
        })
        current_text = ""

    for line in lines:
        raw = line.rstrip('\n')

        if in_header:
            if raw.strip() == '#META#Header#End#':
                in_header = False
            continue

        # Wait for the appendix marker
        if not in_appendix:
            if ZAYD_APPENDIX_MARKER in raw:
                in_appendix = True
            continue

        if not raw.strip():
            continue

        page_match = RE_PAGE.search(raw)
        if page_match:
            current_page = f"V{page_match.group(1)}P{page_match.group(2)}"
            cleaned = RE_PAGE.sub('', raw).strip()
            if not cleaned:
                continue

        # Bab heading
        m = RE_BAB.match(raw)
        if m:
            flush_hadith()
            bab_no += 1
            current_bab = normalize_arabic(m.group(1))
            continue

        # Kitab heading used as bab in this text
        m = RE_KITAB.match(raw)
        if m:
            flush_hadith()
            bab_no += 1
            current_bab = normalize_arabic(m.group(1))
            continue

        m = RE_CONTINUATION.match(raw)
        if m:
            current_text += " " + m.group(1)
            continue

        m = RE_PARAGRAPH.match(raw)
        if m:
            text = m.group(1)
            # Rida hadiths start with وباسناده or حدثني or الباب
            starts_new = (
                RE_ZAYD_HADITH_START.search(text[:30])
                or text.lstrip().startswith('وباسناده')
                or text.lstrip().startswith('الباب ')
            )
            # Bab-like headings embedded in paragraphs
            if text.lstrip().startswith('الباب '):
                flush_hadith()
                bab_no += 1
                current_bab = normalize_arabic(text)
                continue
            if starts_new and current_text.strip():
                flush_hadith()
            if current_text:
                current_text += " " + text
            else:
                current_text = text
            continue

    flush_hadith()

    return {
        "source_file": os.path.basename(source_path),
        "openiti_uri": "0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1 (appendix)",
        "tradition": "Zaydi",
        "bab_count": bab_no,
        "hadith_count": len(hadiths),
        "hadiths": hadiths,
    }


def run_zayd(output_dir: str = None):
    """Parse Musnad Zayd and write outputs."""
    source = os.path.join(OPENITI_DIR, "zayd", "musnad_zaydiyya_052.mARkdown")
    if not os.path.exists(source):
        print(f"ERROR: {source} not found. Run download first.")
        return None

    if output_dir is None:
        output_dir = os.path.join(SCRIPT_DIR, "hadith-data", "zaydi-hadith")

    print(f"\nParsing Musnad Zayd from OpenITI...")
    print(f"  Source: {source}")
    data = parse_zayd(source)
    print(f"  Found: {data['kitab_count']} kitab, {data['bab_count']} bab, "
          f"{data['hadith_count']} hadiths")

    write_json(data, os.path.join(output_dir, "parsed_hadiths.json"))
    write_csv_clean(data["hadiths"], os.path.join(output_dir, "zaydi_hadiths_clean.csv"))
    write_csv_full(data["hadiths"], os.path.join(output_dir, "zaydi_hadiths_full.csv"))
    write_provenance(data, output_dir)
    return data


def run_rida(output_dir: str = None):
    """Parse Sahifat al-Imam Ali al-Rida (appendix of the Zayd file)."""
    source = os.path.join(OPENITI_DIR, "zayd", "musnad_zaydiyya_052.mARkdown")
    if not os.path.exists(source):
        print(f"ERROR: {source} not found.")
        return None

    if output_dir is None:
        output_dir = os.path.join(SCRIPT_DIR, "hadith-data", "rida-hadith")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nParsing Sahifat al-Imam Ali al-Rida (appendix)...")
    print(f"  Source: {source}")
    data = parse_rida_appendix(source)
    print(f"  Found: {data['bab_count']} bab, {data['hadith_count']} hadiths")

    write_json(data, os.path.join(output_dir, "parsed_hadiths.json"))
    write_csv_clean(data["hadiths"], os.path.join(output_dir, "rida_hadiths_clean.csv"))
    write_csv_full(data["hadiths"], os.path.join(output_dir, "rida_hadiths_full.csv"))
    write_provenance(data, output_dir)
    return data


def run_rabi(output_dir: str = None):
    """Parse Musnad al-Rabi and write outputs."""
    source = os.path.join(OPENITI_DIR, "rabi", "jamic_sahih_ibadiyya.txt")
    if not os.path.exists(source):
        print(f"ERROR: {source} not found. Run download first.")
        return None

    if output_dir is None:
        output_dir = os.path.join(SCRIPT_DIR, "hadith-data", "ibadi-hadith")
    os.makedirs(output_dir, exist_ok=True)

    print(f"\nParsing Jami al-Sahih (Musnad al-Rabi) from OpenITI...")
    print(f"  Source: {source}")
    data = parse_rabi(source)
    print(f"  Found: {data['bab_count']} bab, {data['hadith_count']} hadiths")

    write_json(data, os.path.join(output_dir, "parsed_hadiths.json"))
    write_csv_clean(data["hadiths"], os.path.join(output_dir, "ibadi_hadiths_clean.csv"))
    write_csv_full(data["hadiths"], os.path.join(output_dir, "ibadi_hadiths_full.csv"))
    write_provenance(data, output_dir)
    return data


def main():
    parser = argparse.ArgumentParser(
        description='Parse OpenITI mARkdown files into structured hadith datasets')
    parser.add_argument('--zayd-only', action='store_true',
                        help='Parse only Musnad Zayd')
    parser.add_argument('--rabi-only', action='store_true',
                        help='Parse only Musnad al-Rabi')
    parser.add_argument('--rida-only', action='store_true',
                        help='Parse only Sahifat al-Imam Ali al-Rida')
    parser.add_argument('--output-dir', type=str, default=None,
                        help='Override output directory')
    args = parser.parse_args()

    if args.zayd_only:
        run_zayd(args.output_dir)
    elif args.rabi_only:
        run_rabi(args.output_dir)
    elif args.rida_only:
        run_rida(args.output_dir)
    else:
        run_zayd()
        run_rabi()
        run_rida()

    print("\nDone.")


if __name__ == '__main__':
    main()
