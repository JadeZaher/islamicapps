#!/usr/bin/env python3
"""
run_ocr_jobs.py — Run OCR on both Zaydi and Ibadi PDFs
======================================================
Long-running script. Run directly in a terminal:

    python datasets/run_ocr_jobs.py              # Both PDFs
    python datasets/run_ocr_jobs.py --zaydi-only  # Just Zaydi
    python datasets/run_ocr_jobs.py --ibadi-only  # Just Ibadi
    python datasets/run_ocr_jobs.py --test        # Test mode (5 pages each)

Each job saves progress after every batch — safe to interrupt and resume.
"""

import argparse
import json
import os
import sys
import time

# Add parent to path so we can import the OCR library
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ocr_arabic_pdf import ArabicOCR, _cli_progress


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

JOBS = {
    'zaydi': {
        'pdf': os.path.join(BASE_DIR, 'hadith-data', 'zaydi-hadith', 'musnad_zayd.pdf'),
        'output_dir': os.path.join(BASE_DIR, 'hadith-data', 'zaydi-hadith', 'ocr_v2'),
        'start': 1,
        'end': None,  # all pages
        'skip_pages': set(),
    },
    'ibadi': {
        'pdf': os.path.join(BASE_DIR, 'archive', 'ibadi-musnad-pipeline', 'ibadimusnad.pdf'),
        'output_dir': os.path.join(BASE_DIR, 'archive', 'ibadi-musnad-pipeline', 'ocr_v2'),
        'start': 11,   # content starts at page 11
        'end': 278,     # content ends at page 278
        'skip_pages': {10, 104, 195},  # section dividers
    },
}


def run_job(name: str, job: dict, ocr: ArabicOCR, test_pages: int = 0):
    """Run a single OCR job."""
    pages_json = os.path.join(job['output_dir'], 'raw_ocr_pages.json')
    text_out = os.path.join(job['output_dir'], 'raw_ocr_text.txt')
    os.makedirs(job['output_dir'], exist_ok=True)

    total = ocr.page_count(job['pdf'])
    end = job['end'] or total
    if test_pages:
        end = min(job['start'] + test_pages - 1, end)

    print(f"\n{'='*60}")
    print(f"OCR Job: {name}")
    print(f"PDF: {job['pdf']} ({total} pages)")
    print(f"Range: {job['start']}-{end}")
    print(f"Output: {job['output_dir']}")
    print(f"{'='*60}")

    existing = ArabicOCR.load_json(pages_json)
    if existing:
        print(f"Resuming: {len(existing)} pages already done")

    incremental = []

    def progress(result, done, total_count, elapsed, times):
        _cli_progress(result, done, total_count, elapsed, times)
        incremental.append(result.to_dict())
        if done % 5 == 0:
            all_so_far = existing + incremental
            with open(pages_json, 'w', encoding='utf-8') as _f:
                json.dump(all_so_far, _f, ensure_ascii=False, indent=2)

    t0 = time.time()
    pages = ocr.ocr_pdf(
        job['pdf'],
        start=job['start'],
        end=end,
        skip_pages=job['skip_pages'],
        batch_size=5,
        on_page=progress,
        resume_from=existing,
    )

    ArabicOCR.save_json(pages, pages_json)
    ArabicOCR.save_text(pages, text_out)

    elapsed = time.time() - t0
    total_chars = sum(p.char_count for p in pages)
    avg_conf = sum(p.avg_confidence for p in pages) / max(len(pages), 1)

    print(f"\n{name} complete: {len(pages)} pages, {total_chars} chars, "
          f"avg_conf={avg_conf:.2f}, {elapsed/60:.1f} min")
    print(f"  JSON: {pages_json}")
    print(f"  Text: {text_out}")
    return pages


def main():
    parser = argparse.ArgumentParser(description='Run OCR on hadith PDFs')
    parser.add_argument('--zaydi-only', action='store_true')
    parser.add_argument('--ibadi-only', action='store_true')
    parser.add_argument('--test', action='store_true', help='Test mode: 5 pages each')
    parser.add_argument('--dpi', type=int, default=400)
    parser.add_argument('--gpu', action='store_true')
    args = parser.parse_args()

    print("Initializing ArabicOCR (easyocr model load may take a minute)...")
    ocr = ArabicOCR(dpi=args.dpi, enhance=True, gpu=args.gpu)
    # Force model load
    _ = ocr.reader
    print("Model loaded.\n")

    test_pages = 5 if args.test else 0

    jobs_to_run = []
    if args.zaydi_only:
        jobs_to_run = [('zaydi', JOBS['zaydi'])]
    elif args.ibadi_only:
        jobs_to_run = [('ibadi', JOBS['ibadi'])]
    else:
        jobs_to_run = list(JOBS.items())

    for name, job in jobs_to_run:
        run_job(name, job, ocr, test_pages)

    print("\nAll jobs complete.")


if __name__ == '__main__':
    main()
