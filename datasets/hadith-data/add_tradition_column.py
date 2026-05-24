import csv
import sys
import tempfile
import os

csv.field_size_limit(10 * 1024 * 1024)

SOURCE_TRADITION_MAP = {
    "Sahih Muslim": "Sunni",
    "Sahih Bukhari": "Sunni",
    "Sunan an-Nasa'i": "Sunni",
    "Sunan Abi Da'ud": "Sunni",
    "Sunan Ibn Majah": "Sunni",
    "Jami' al-Tirmidhi": "Sunni",
    "Musnad al-Imam Zayd ibn Ali": "Zaydi",
}

INPUT_FILE = os.path.join(os.path.dirname(__file__), "all_hadiths_clean.csv")

def main():
    rows = []
    fieldnames = None

    with open(INPUT_FILE, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames[:]
        for row in reader:
            rows.append(row)

    if "tradition" not in fieldnames:
        fieldnames.append("tradition")

    tradition_counts = {}
    unmapped_sources = set()

    for row in rows:
        source = row.get("source", "").strip()
        tradition = SOURCE_TRADITION_MAP.get(source, "Unknown")
        if tradition == "Unknown" and source:
            unmapped_sources.add(source)
        row["tradition"] = tradition
        tradition_counts[tradition] = tradition_counts.get(tradition, 0) + 1

    tmp_path = INPUT_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    os.replace(tmp_path, INPUT_FILE)

    print(f"Done. {len(rows)} rows written to {INPUT_FILE}")
    print("\nTradition counts:")
    for tradition, count in sorted(tradition_counts.items()):
        print(f"  {tradition}: {count}")

    if unmapped_sources:
        print(f"\nUnmapped sources (assigned 'Unknown'):")
        for s in sorted(unmapped_sources):
            print(f"  {s}")
    else:
        print("\nAll sources mapped successfully.")

if __name__ == "__main__":
    main()
