"""
fix_chapter_names.py
====================
Cleans OCR artifacts from chapter names in:
  - zaydi_translated.jsonl   (field: "chapter")
  - parsed_zaydi_hadiths.json (field: "chapter_name_ar" inside each hadith)

OCR artifacts targeted:
  - Parenthetical footnote markers like )١(‏  )6١‏  )١١‏  (inherited from printed text)
  - Arabic question mark junk: (؟") (؟) ("»  ("»
  - Stray quotation marks:  '"  '  '
  - Unicode LEFT-TO-RIGHT MARK / RIGHT-TO-LEFT MARK (U+200F, U+200E)
  - Common misread: leading ياب → باب
  - Trailing whitespace after cleanup
"""

import json
import re
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BASE = Path(__file__).parent

JSONL_FILE = BASE / "zaydi_translated.jsonl"
JSON_FILE  = BASE / "parsed_zaydi_hadiths.json"


def clean_chapter(name: str) -> str:
    if not name:
        return name

    original = name

    # Remove Unicode direction marks (U+200F RIGHT-TO-LEFT MARK, U+200E LEFT-TO-RIGHT MARK)
    name = name.replace("\u200f", "").replace("\u200e", "")

    # Remove printed-book footnote markers of the form )digit(  e.g. )١(  )٦١(  )١١(  )6١(  )1١١(
    # These appear as  )digit(‏  where ‏ is U+200F already stripped above
    # Digits may be a mix of ASCII (0-9) and Arabic-Indic (٠-٩ / ۰-۹)
    name = re.sub(r"\)\s*[0-9\u0660-\u0669\u06F0-\u06F9]+\s*\(", "", name)
    # Also handle orphaned opening-paren-only footnote markers: )digit  (no closing paren)
    # e.g. ")6١ والهدي" → " والهدي"
    name = re.sub(r"\)\s*[0-9\u0660-\u0669\u06F0-\u06F9]+\s*(?=[^\u0660-\u0669\u06F0-\u06F90-9(])", " ", name)

    # Remove parenthetical OCR junk containing ؟ or "
    # Patterns: (؟") (؟) (" ("»
    name = re.sub(r'\([؟"\u201c\u201d\u00ab\u00bb»«]*؟?["\u201c\u201d\u00ab\u00bb»«]*\)', "", name)

    # Remove stray trailing quote sequences  ("»  ("  "»  »  '
    name = re.sub(r'[\s]*[\(\u0028]?["\u201c\u201d\u00ab\u00bb»«\']+[\)\u0029]?$', "", name)

    # Remove stray leading quote/paren artifacts
    name = re.sub(r'^[\(\u0028]*["\u201c\u201d\u00ab\u00bb»«\']+[\)\u0029]*\s*', "", name)

    # Fix common OCR error: ياب (yaa-alif-baa) → باب (baa-alif-baa)
    # Covers: leading position and mid-string after a space (e.g. "كتاب الصلاة ياب الاذان")
    if name.startswith("ياب ") or name == "ياب":
        name = "باب" + name[3:]
    # Mid-string: " ياب " → " باب "
    name = re.sub(r"(?<= )ياب(?= )", "باب", name)

    # Collapse multiple spaces
    name = re.sub(r"  +", " ", name)

    # Strip surrounding whitespace
    name = name.strip()

    return name


def fix_jsonl(path: Path):
    """Read, clean chapter names, write back in place. Returns (records, changes)."""
    with open(path, encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    changes = {}
    for rec in records:
        original = rec.get("chapter", "")
        cleaned = clean_chapter(original)
        if original != cleaned:
            changes[original] = cleaned
            rec["chapter"] = cleaned

    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return records, changes


def fix_json(path: Path, chapter_map: dict):
    """Apply the same chapter name corrections to parsed_zaydi_hadiths.json."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    json_changes = {}
    for hadith in data.get("hadiths", []):
        original = hadith.get("chapter_name_ar", "")
        # Apply same clean function independently
        cleaned = clean_chapter(original)
        if original != cleaned:
            json_changes[original] = cleaned
            hadith["chapter_name_ar"] = cleaned

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return json_changes


def main():
    print("=== Zaydi Chapter Name Fixer ===\n")

    # --- Fix JSONL ---
    print(f"Processing: {JSONL_FILE.name}")
    records, jsonl_changes = fix_jsonl(JSONL_FILE)
    if jsonl_changes:
        print(f"  Fixed {len(jsonl_changes)} unique chapter name(s):")
        for old, new in sorted(jsonl_changes.items()):
            print(f"    BEFORE: {old!r}")
            print(f"    AFTER:  {new!r}")
            print()
    else:
        print("  No chapter name changes needed.")

    # --- Fix JSON ---
    print(f"Processing: {JSON_FILE.name}")
    json_changes = fix_json(JSON_FILE, jsonl_changes)
    if json_changes:
        print(f"  Fixed {len(json_changes)} unique chapter name(s):")
        for old, new in sorted(json_changes.items()):
            print(f"    BEFORE: {old!r}")
            print(f"    AFTER:  {new!r}")
            print()
    else:
        print("  No chapter name changes needed.")

    # --- Summary ---
    total = len(set(list(jsonl_changes.keys()) + list(json_changes.keys())))
    print(f"\nSummary: {total} unique chapter name(s) cleaned across both files.")
    print(f"  {JSONL_FILE.name}: {len(records)} records total, {len(jsonl_changes)} chapter names fixed.")
    print(f"  {JSON_FILE.name}: chapter_name_ar fields fixed in hadiths array.")


if __name__ == "__main__":
    main()
