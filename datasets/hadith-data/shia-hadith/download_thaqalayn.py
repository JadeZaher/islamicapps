"""
Download Shia hadith data from ThaqalaynAPI V2 GitHub repo.
Source: https://github.com/MohammedArab1/ThaqalaynAPI/tree/main/V2/ThaqalaynData
"""

import json
import os
import sys
import time
import requests

BASE_URL = "https://raw.githubusercontent.com/MohammedArab1/ThaqalaynAPI/main/V2/ThaqalaynData"
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
BOOKS_DIR = os.path.join(OUTPUT_DIR, "v2_books")

# V2 uses numbered files (1.json - 39.json) + BookNames.json
FILES_TO_DOWNLOAD = ["BookNames.json"] + [f"{i}.json" for i in range(1, 40)]


def download_file(filename: str, output_dir: str) -> bool:
    url = f"{BASE_URL}/{filename}"
    output_path = os.path.join(output_dir, filename)

    if os.path.exists(output_path):
        size = os.path.getsize(output_path)
        if size > 0:
            print(f"  [SKIP] {filename} already exists ({size:,} bytes)")
            return True

    print(f"  [GET]  {filename}...", end=" ", flush=True)
    try:
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        print(f"OK ({len(resp.content):,} bytes)")
        return True
    except requests.RequestException as e:
        print(f"FAILED: {e}")
        return False


def main():
    os.makedirs(BOOKS_DIR, exist_ok=True)

    print(f"Downloading ThaqalaynAPI V2 data to: {BOOKS_DIR}")
    print(f"Files to download: {len(FILES_TO_DOWNLOAD)}")
    print()

    succeeded = 0
    failed = []

    for filename in FILES_TO_DOWNLOAD:
        if download_file(filename, BOOKS_DIR):
            succeeded += 1
        else:
            failed.append(filename)
        time.sleep(0.3)  # Be polite to GitHub CDN

    print()
    print(f"Done: {succeeded}/{len(FILES_TO_DOWNLOAD)} files downloaded")
    if failed:
        print(f"Failed: {failed}")
        sys.exit(1)

    # Print summary from BookNames.json
    booknames_path = os.path.join(BOOKS_DIR, "BookNames.json")
    if os.path.exists(booknames_path):
        with open(booknames_path, "r", encoding="utf-8") as f:
            books = json.load(f)
        print(f"\nBooks index: {len(books)} entries")
        for b in books:
            print(f"  {b.get('bookId', '?'):50s}  hadiths: {b.get('idRangeMin',0)}-{b.get('idRangeMax','?')}")


if __name__ == "__main__":
    main()
