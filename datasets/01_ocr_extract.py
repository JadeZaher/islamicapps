#!/usr/bin/env python3
"""
01_ocr_extract.py
==================
OCR extraction from the scanned Musnad al-Imam al-Rabi' b. Habib PDF.
Uses pdf2image + easyocr to extract Arabic text page by page.

Output: raw_ocr_pages.json  (list of {page_num, pdf_page, part, text})

Usage:
    python 01_ocr_extract.py --pdf /path/to/ibadimusnad.pdf --output raw_ocr_pages.json
    python 01_ocr_extract.py --pdf /path/to/ibadimusnad.pdf --output raw_ocr_pages.json --start 11 --end 103
"""

import argparse
import json
import os
import sys
import time

import fitz  # PyMuPDF — no poppler needed

# ── PDF page ranges (1-indexed) ──────────────────────────────────────────
# From the index on PDF page 441:
#   Part 1: book pages 6–98   → PDF pages 11–103  (hadiths 1–391)
#   Part 2: book pages 99–189 → PDF pages 104–194 (hadiths 392–742)
#   Part 3: book pages 191–243→ PDF pages 196–248 (hadiths 743–882)
#   Part 4: book pages 244–273→ PDF pages 249–278 (hadiths 883–1005)
# Introductory pages (tanbīhāt): PDF pages 6–10
PART_RANGES = [
    (1, 11, 103),   # (part, start_pdf_page, end_pdf_page)
    (2, 104, 194),
    (3, 196, 248),
    (4, 249, 278),
]

# Some pages are section dividers / blank — skip them
SKIP_PAGES = {10, 104, 195}  # Part title pages


def get_part_for_page(pdf_page):
    """Return the part number (1-4) for a given PDF page."""
    for part, start, end in PART_RANGES:
        if start <= pdf_page <= end:
            return part
    return 0


def ocr_pages(pdf_path, output_path, start_page=None, end_page=None, dpi=300, batch_size=5):
    """Extract text from PDF pages using easyocr."""
    import easyocr

    # Determine page range
    if start_page is None:
        start_page = PART_RANGES[0][1]  # 11
    if end_page is None:
        end_page = PART_RANGES[-1][2]   # 278

    print(f"Initializing easyocr Arabic reader (CPU mode)...")
    reader = easyocr.Reader(['ar'], gpu=False, verbose=False)

    # Load existing progress if any
    results = []
    done_pages = set()
    if os.path.exists(output_path):
        with open(output_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
            done_pages = {r['pdf_page'] for r in results}
        print(f"Resuming: {len(done_pages)} pages already done.")

    pages_to_do = [p for p in range(start_page, end_page + 1)
                   if p not in done_pages and p not in SKIP_PAGES
                   and get_part_for_page(p) > 0]

    total = len(pages_to_do)
    print(f"Pages to OCR: {total} (PDF pages {start_page}–{end_page})")

    for batch_start in range(0, total, batch_size):
        batch_pages = pages_to_do[batch_start:batch_start + batch_size]
        first_p, last_p = batch_pages[0], batch_pages[-1]

        print(f"\n[Batch {batch_start // batch_size + 1}] "
              f"Converting PDF pages {first_p}–{last_p} to images (dpi={dpi})...")
        t0 = time.time()

        doc = fitz.open(pdf_path)
        zoom = dpi / 72
        mat = fitz.Matrix(zoom, zoom)

        # Map images to actual PDF page numbers
        page_image_map = []
        for pg in batch_pages:
            page = doc[pg - 1]  # fitz uses 0-indexed pages
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            page_image_map.append((pg, img_data))
        doc.close()

        print(f"  Converted {len(page_image_map)} images in {time.time()-t0:.1f}s")

        for pdf_page, img_bytes in page_image_map:
            part = get_part_for_page(pdf_page)
            book_page = pdf_page - 5  # PDF page offset (cover + intro)

            print(f"  OCR page {pdf_page} (book p.{book_page}, part {part})...", end=' ')
            t1 = time.time()

            # Save temp image
            tmp_img = os.path.join(os.environ.get('TEMP', '/tmp'), f'ocr_page_{pdf_page}.png')
            with open(tmp_img, 'wb') as tmp_f:
                tmp_f.write(img_bytes)

            # Run OCR in paragraph mode for coherent text blocks
            ocr_results = reader.readtext(tmp_img, detail=1, paragraph=True)

            # Sort by Y position (top to bottom), then extract text
            segments = []
            for item in ocr_results:
                if len(item) == 3:
                    bbox, text, conf = item
                elif len(item) == 2:
                    bbox, text = item
                    conf = 0.0
                else:
                    continue
                # Get top-left Y coordinate for sorting
                if isinstance(bbox, list) and len(bbox) >= 2:
                    y_pos = bbox[0][1] if isinstance(bbox[0], (list, tuple)) else bbox[1]
                else:
                    y_pos = 0
                segments.append((y_pos, text, conf))

            # Sort top-to-bottom
            segments.sort(key=lambda s: s[0])
            page_text = '\n'.join(seg[1] for seg in segments)

            elapsed = time.time() - t1
            print(f"{len(segments)} blocks, {len(page_text)} chars, {elapsed:.1f}s")

            results.append({
                'pdf_page': pdf_page,
                'book_page': book_page,
                'part': part,
                'text': page_text,
                'num_blocks': len(segments),
            })

            # Clean up
            os.remove(tmp_img)

        # Save progress after each batch
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"  Saved progress: {len(results)} pages total.")

    # Final sort by page number
    results.sort(key=lambda r: r['pdf_page'])
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\nDone! {len(results)} pages OCR'd → {output_path}")
    return results


def main():
    parser = argparse.ArgumentParser(description='OCR extract Arabic text from Musnad PDF')
    parser.add_argument('--pdf', required=True, help='Path to ibadimusnad.pdf')
    parser.add_argument('--output', default='raw_ocr_pages.json', help='Output JSON file')
    parser.add_argument('--start', type=int, default=None, help='Start PDF page (default: 11)')
    parser.add_argument('--end', type=int, default=None, help='End PDF page (default: 278)')
    parser.add_argument('--dpi', type=int, default=300, help='DPI for image conversion')
    parser.add_argument('--batch', type=int, default=5, help='Pages per batch')
    args = parser.parse_args()

    ocr_pages(args.pdf, args.output, args.start, args.end, args.dpi, args.batch)


if __name__ == '__main__':
    main()
