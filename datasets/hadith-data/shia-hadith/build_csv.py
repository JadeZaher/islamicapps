"""
Transform ThaqalaynAPI V2 JSON files into a clean CSV.
Outputs: all_hadiths_shia.csv in the parent hadith-data directory.

Columns match the Sunni all_hadiths_clean.csv schema + bonus Shia-specific fields:
  id, hadith_id, source, volume, chapter_no, hadith_no, chapter, category,
  chain_indx, text_ar, text_en, sanad, matn_en,
  grading_majlisi, grading_mohseni, grading_behbudi, gradings_full, url
"""

import csv
import glob
import json
import os
import sys

INPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2_books")
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "all_hadiths_shia.csv")

COLUMNS = [
    "id",
    "hadith_id",
    "source",
    "volume",
    "chapter_no",
    "hadith_no",
    "chapter",
    "category",
    "chain_indx",
    "text_ar",
    "text_en",
    "sanad",
    "matn_en",
    "grading_majlisi",
    "grading_mohseni",
    "grading_behbudi",
    "gradings_full",
    "url",
]


def clean_text(text: str | None) -> str:
    if not text:
        return ""
    # Normalize whitespace but preserve Arabic/Unicode
    return " ".join(text.split())


def serialize_gradings(gradings_full: list | None) -> str:
    if not gradings_full:
        return ""
    parts = []
    for g in gradings_full:
        author = g.get("author", {}) or {}
        name = author.get("name_en") or author.get("name_ar") or "Unknown"
        grade = g.get("grade_en") or g.get("grade_ar") or ""
        ref = g.get("reference_en") or ""
        parts.append(f"{name}: {grade} ({ref})" if ref else f"{name}: {grade}")
    return " | ".join(parts)


def transform_hadith(h: dict, global_id: int) -> dict:
    return {
        "id": global_id,
        "hadith_id": h.get("id", ""),
        "source": h.get("book", ""),
        "volume": h.get("volume", ""),
        "chapter_no": h.get("categoryId", ""),
        "hadith_no": h.get("chapterInCategoryId", ""),
        "chapter": h.get("chapter", ""),
        "category": h.get("category", ""),
        "chain_indx": h.get("thaqalaynSanad", ""),
        "text_ar": clean_text(h.get("arabicText", "")),
        "text_en": clean_text(h.get("englishText", "")),
        "sanad": h.get("thaqalaynSanad", ""),
        "matn_en": clean_text(h.get("thaqalaynMatn", "")),
        "grading_majlisi": h.get("majlisiGrading", ""),
        "grading_mohseni": h.get("mohseniGrading", ""),
        "grading_behbudi": h.get("behbudiGrading", ""),
        "gradings_full": serialize_gradings(h.get("gradingsFull")),
        "url": h.get("URL", ""),
    }


def main():
    json_files = sorted(
        glob.glob(os.path.join(INPUT_DIR, "[0-9]*.json")),
        key=lambda x: int(os.path.basename(x).replace(".json", "")),
    )

    if not json_files:
        print(f"No JSON files found in {INPUT_DIR}. Run download_thaqalayn.py first.")
        sys.exit(1)

    print(f"Processing {len(json_files)} book files...")

    global_id = 0
    total_written = 0

    with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=COLUMNS, quoting=csv.QUOTE_ALL)
        writer.writeheader()

        for jf in json_files:
            fname = os.path.basename(jf)
            with open(jf, "r", encoding="utf-8") as f:
                hadiths = json.load(f)

            book_name = hadiths[0]["bookId"] if hadiths else fname
            count = 0

            for h in hadiths:
                global_id += 1
                row = transform_hadith(h, global_id)
                writer.writerow(row)
                count += 1

            total_written += count
            print(f"  {fname:10s} -> {book_name:55s} ({count:,} rows)")

    print(f"\nTotal rows written: {total_written:,}")
    print(f"Output: {os.path.abspath(OUTPUT_PATH)}")

    # Quick verification
    size_mb = os.path.getsize(OUTPUT_PATH) / (1024 * 1024)
    print(f"File size: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
