#!/usr/bin/env python3
"""
ocr_arabic_pdf.py — Composable Arabic OCR library
==================================================
Reusable library for OCR of scanned Arabic hadith manuscripts.
Uses PyMuPDF for rendering + easyocr for recognition.

Library usage:
    from ocr_arabic_pdf import ArabicOCR

    ocr = ArabicOCR(dpi=400, enhance=True, gpu=False)
    pages = ocr.ocr_pdf("manuscript.pdf", start=1, end=50)
    ocr.save_json(pages, "output/raw_ocr_pages.json")
    ocr.save_text(pages, "output/raw_ocr_text.txt")

    # Single page:
    result = ocr.ocr_page("manuscript.pdf", page_num=42)

    # Just preprocessing:
    enhanced = ArabicOCR.preprocess(img_bytes, contrast=1.5, threshold=140)

CLI usage:
    python ocr_arabic_pdf.py --pdf file.pdf --output-dir output/
    python ocr_arabic_pdf.py --pdf file.pdf --output-dir output/ --dpi 400 --start 1 --end 50
"""

import argparse
import io
import json
import os
import sys
import time
import unicodedata
from dataclasses import dataclass, field, asdict
from typing import Optional

import fitz  # PyMuPDF

try:
    from PIL import Image, ImageEnhance, ImageFilter
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

try:
    import cv2
    import numpy as np
    _HAS_CV2 = True
except ImportError:
    _HAS_CV2 = False


# ── Data types ──

@dataclass
class OCRSegment:
    """A single recognized text block with position and confidence."""
    text: str
    y: float
    x: float
    confidence: float

@dataclass
class OCRPageResult:
    """OCR result for a single page."""
    page: int
    text: str
    num_blocks: int
    avg_confidence: float
    char_count: int
    blocks: list = field(default_factory=list)  # raw segments if requested

    def to_dict(self) -> dict:
        return {
            'page': self.page,
            'text': self.text,
            'num_blocks': self.num_blocks,
            'avg_confidence': self.avg_confidence,
            'char_count': self.char_count,
        }


# ── Core library ──

class ArabicOCR:
    """Composable Arabic OCR engine."""

    def __init__(self, dpi: int = 400, enhance: bool = True,
                 contrast: float = 1.5, threshold: int = 140,
                 gpu: bool = False, languages: list = None):
        self.dpi = dpi
        self.enhance = enhance
        self.contrast = contrast
        self.threshold = threshold
        self.gpu = gpu
        self.languages = languages or ['ar']
        self._reader = None

    @property
    def reader(self):
        """Lazy-load easyocr reader."""
        if self._reader is None:
            import easyocr
            self._reader = easyocr.Reader(
                self.languages, gpu=self.gpu, verbose=False
            )
        return self._reader

    # ── Image preprocessing ──

    @staticmethod
    def preprocess(img_bytes: bytes, contrast: float = 1.5,
                   threshold: int = 140, use_clahe: bool = True) -> bytes:
        """Preprocess page image for better Arabic OCR.

        Uses OpenCV CLAHE + adaptive thresholding when available (better
        for manuscripts with uneven lighting/yellowed paper). Falls back
        to PIL simple threshold.

        Args:
            img_bytes: Raw PNG image bytes
            contrast: Contrast factor (PIL) or CLAHE clipLimit (OpenCV)
            threshold: Binarization threshold (PIL fallback only)
            use_clahe: Prefer OpenCV CLAHE pipeline when available

        Returns:
            Processed PNG image bytes
        """
        if _HAS_CV2 and use_clahe:
            arr = np.frombuffer(img_bytes, dtype=np.uint8)
            img = cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE)
            if img is None:
                return img_bytes

            # Denoise
            img = cv2.fastNlMeansDenoising(img, h=10,
                                           templateWindowSize=7,
                                           searchWindowSize=21)
            # CLAHE for contrast
            clahe = cv2.createCLAHE(clipLimit=contrast, tileGridSize=(8, 8))
            img = clahe.apply(img)

            # Adaptive threshold (better for manuscripts than global)
            img = cv2.adaptiveThreshold(
                img, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=15,
                C=8,
            )

            _, buf = cv2.imencode('.png', img)
            return buf.tobytes()

        if not _HAS_PIL:
            return img_bytes

        img = Image.open(io.BytesIO(img_bytes))
        img = img.convert('L')
        img = ImageEnhance.Contrast(img).enhance(contrast)
        img = img.filter(ImageFilter.SHARPEN)
        img = img.point(lambda x: 0 if x < threshold else 255, '1')
        img = img.convert('L')

        buf = io.BytesIO()
        img.save(buf, format='PNG')
        return buf.getvalue()

    # ── Page rendering ──

    def render_page(self, pdf_path: str, page_num: int) -> bytes:
        """Render a single PDF page to PNG bytes at configured DPI."""
        doc = fitz.open(pdf_path)
        zoom = self.dpi / 72
        mat = fitz.Matrix(zoom, zoom)
        page = doc[page_num - 1]
        pix = page.get_pixmap(matrix=mat)
        img_bytes = pix.tobytes("png")
        doc.close()

        if self.enhance:
            img_bytes = self.preprocess(
                img_bytes, contrast=self.contrast, threshold=self.threshold
            )
        return img_bytes

    # ── OCR single page ──

    def ocr_page(self, pdf_path: str, page_num: int,
                 keep_blocks: bool = False) -> OCRPageResult:
        """OCR a single page and return structured result."""
        img_bytes = self.render_page(pdf_path, page_num)

        tmp_img = os.path.join(
            os.environ.get('TEMP', '/tmp'), f'_ocr_{page_num}.png'
        )
        try:
            with open(tmp_img, 'wb') as f:
                f.write(img_bytes)

            ocr_results = self.reader.readtext(
                tmp_img, detail=1, paragraph=False,
                decoder='beamsearch', beamWidth=5,
                text_threshold=0.7, mag_ratio=1.5,
            )
        finally:
            if os.path.exists(tmp_img):
                os.remove(tmp_img)

        segments = self._parse_segments(ocr_results)
        lines = self._segments_to_lines(segments)
        page_text = '\n'.join(lines)
        avg_conf = (
            sum(s.confidence for s in segments) / len(segments)
            if segments else 0.0
        )

        return OCRPageResult(
            page=page_num,
            text=page_text,
            num_blocks=len(segments),
            avg_confidence=round(avg_conf, 3),
            char_count=len(page_text),
            blocks=[asdict(s) for s in segments] if keep_blocks else [],
        )

    # ── OCR full PDF ──

    def ocr_pdf(self, pdf_path: str, start: int = 1, end: int = None,
                skip_pages: set = None, batch_size: int = 5,
                on_page: callable = None,
                resume_from: list = None) -> list[OCRPageResult]:
        """OCR a range of pages from a PDF.

        Args:
            pdf_path: Path to PDF file
            start: First page (1-indexed)
            end: Last page (None = last page of PDF)
            skip_pages: Set of page numbers to skip
            batch_size: Pages per batch (controls memory)
            on_page: Callback(page_result, done_count, total_count) for progress
            resume_from: List of existing OCRPageResult dicts to skip

        Returns:
            List of OCRPageResult for all processed pages
        """
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()

        if end is None or end > total_pages:
            end = total_pages
        if skip_pages is None:
            skip_pages = set()

        # Resume support
        done_pages = set()
        results = []
        if resume_from:
            for r in resume_from:
                if isinstance(r, dict):
                    results.append(OCRPageResult(**{
                        k: r[k] for k in
                        ['page', 'text', 'num_blocks', 'avg_confidence', 'char_count']
                    }))
                    done_pages.add(r['page'])
                elif isinstance(r, OCRPageResult):
                    results.append(r)
                    done_pages.add(r.page)

        pages_to_do = [
            p for p in range(start, end + 1)
            if p not in done_pages and p not in skip_pages
        ]
        remaining = len(pages_to_do)

        if remaining == 0:
            return results

        times = []
        for batch_start in range(0, remaining, batch_size):
            batch = pages_to_do[batch_start:batch_start + batch_size]

            for pg in batch:
                t0 = time.time()
                result = self.ocr_page(pdf_path, pg)
                elapsed = time.time() - t0
                times.append(elapsed)

                results.append(result)
                done_count = len(done_pages) + batch_start + batch.index(pg) + 1
                total_count = len(done_pages) + remaining

                if on_page:
                    on_page(result, done_count, total_count, elapsed, times)

            done_pages.update(batch)

        results.sort(key=lambda r: r.page)
        return results

    # ── Segment parsing ──

    def _parse_segments(self, ocr_results: list) -> list[OCRSegment]:
        """Parse easyocr output into OCRSegments."""
        segments = []
        for item in ocr_results:
            if len(item) >= 3:
                bbox, text, conf = item[0], item[1], item[2]
            elif len(item) == 2:
                bbox, text = item[0], item[1]
                conf = 0.0
            else:
                continue

            if not text.strip():
                continue

            if isinstance(bbox, list) and len(bbox) >= 2:
                if isinstance(bbox[0], (list, tuple)):
                    y_pos = (bbox[0][1] + bbox[2][1]) / 2
                    x_pos = (bbox[0][0] + bbox[1][0]) / 2
                else:
                    y_pos = bbox[1]
                    x_pos = bbox[0]
            else:
                y_pos = 0
                x_pos = 0

            # NFKC normalize Arabic presentation forms to base codepoints
            clean_text = unicodedata.normalize('NFKC', text.strip())
            segments.append(OCRSegment(
                text=clean_text,
                y=y_pos,
                x=x_pos,
                confidence=round(conf, 3),
            ))

        segments.sort(key=lambda s: (s.y, -s.x))
        return segments

    def _segments_to_lines(self, segments: list[OCRSegment]) -> list[str]:
        """Group segments into lines based on Y proximity (Arabic RTL)."""
        if not segments:
            return []

        line_threshold = self.dpi * 0.04
        lines = []
        current_line = []
        last_y = None

        for seg in segments:
            if last_y is not None and abs(seg.y - last_y) > line_threshold:
                current_line.sort(key=lambda s: -s.x)
                lines.append(' '.join(s.text for s in current_line))
                current_line = []
            current_line.append(seg)
            last_y = seg.y

        if current_line:
            current_line.sort(key=lambda s: -s.x)
            lines.append(' '.join(s.text for s in current_line))

        return lines

    # ── I/O helpers ──

    @staticmethod
    def save_json(pages: list[OCRPageResult], path: str):
        """Save page results to JSON."""
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        data = [p.to_dict() if isinstance(p, OCRPageResult) else p for p in pages]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def save_text(pages: list[OCRPageResult], path: str):
        """Save concatenated text with page markers."""
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            for p in sorted(pages, key=lambda x: x.page if isinstance(x, OCRPageResult) else x['page']):
                pg = p.page if isinstance(p, OCRPageResult) else p['page']
                conf = p.avg_confidence if isinstance(p, OCRPageResult) else p['avg_confidence']
                text = p.text if isinstance(p, OCRPageResult) else p['text']
                f.write(f"--- PAGE {pg} (conf={conf:.2f}) ---\n")
                f.write(text)
                f.write('\n\n')

    @staticmethod
    def load_json(path: str) -> list[dict]:
        """Load previously saved OCR results for resume."""
        if not os.path.exists(path):
            return []
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @staticmethod
    def page_count(pdf_path: str) -> int:
        """Get total page count of a PDF."""
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count


# ── CLI ──

def _cli_progress(result, done, total, elapsed, times):
    """Default CLI progress callback."""
    avg = sum(times[-20:]) / len(times[-20:])
    eta_s = avg * (total - done)
    eta = f"{eta_s/60:.0f}m" if eta_s > 60 else f"{eta_s:.0f}s"
    print(f"  [{done}/{total}] Page {result.page}: "
          f"{result.num_blocks} blocks, {result.char_count} chars, "
          f"conf={result.avg_confidence:.2f}, {elapsed:.1f}s (ETA: {eta})")


def main():
    parser = argparse.ArgumentParser(description='OCR Arabic PDF with easyocr')
    parser.add_argument('--pdf', required=True, help='Path to PDF file')
    parser.add_argument('--output-dir', required=True, help='Output directory')
    parser.add_argument('--start', type=int, default=1, help='Start page (1-indexed)')
    parser.add_argument('--end', type=int, default=None, help='End page')
    parser.add_argument('--dpi', type=int, default=400, help='DPI for rendering')
    parser.add_argument('--contrast', type=float, default=1.5, help='Contrast factor')
    parser.add_argument('--threshold', type=int, default=140, help='Binarization threshold')
    parser.add_argument('--batch', type=int, default=5, help='Pages per batch')
    parser.add_argument('--skip-pages', type=str, default='', help='Comma-separated pages to skip')
    parser.add_argument('--no-enhance', action='store_true', help='Skip preprocessing')
    parser.add_argument('--gpu', action='store_true', help='Use GPU')
    args = parser.parse_args()

    skip = set()
    if args.skip_pages:
        skip = {int(p.strip()) for p in args.skip_pages.split(',') if p.strip()}

    os.makedirs(args.output_dir, exist_ok=True)
    pages_json = os.path.join(args.output_dir, "raw_ocr_pages.json")
    text_out = os.path.join(args.output_dir, "raw_ocr_text.txt")

    ocr = ArabicOCR(
        dpi=args.dpi,
        enhance=not args.no_enhance,
        contrast=args.contrast,
        threshold=args.threshold,
        gpu=args.gpu,
    )

    total = ocr.page_count(args.pdf)
    print(f"PDF: {args.pdf} ({total} pages)")
    print(f"DPI={args.dpi}, enhance={not args.no_enhance}, "
          f"contrast={args.contrast}, threshold={args.threshold}")
    print("Initializing easyocr...")

    # Resume
    existing = ArabicOCR.load_json(pages_json)
    if existing:
        print(f"Resuming: {len(existing)} pages already done.")

    def save_progress(result, done, total_count, elapsed, times):
        _cli_progress(result, done, total_count, elapsed, times)
        # Save every 5 pages
        if done % 5 == 0:
            ArabicOCR.save_json(pages, pages_json)

    pages = ocr.ocr_pdf(
        args.pdf,
        start=args.start,
        end=args.end,
        skip_pages=skip,
        batch_size=args.batch,
        on_page=save_progress,
        resume_from=existing,
    )

    ArabicOCR.save_json(pages, pages_json)
    ArabicOCR.save_text(pages, text_out)

    total_chars = sum(p.char_count for p in pages)
    avg_conf = sum(p.avg_confidence for p in pages) / max(len(pages), 1)
    print(f"\nDone! {len(pages)} pages, {total_chars} chars, avg_conf={avg_conf:.2f}")
    print(f"  JSON: {pages_json}")
    print(f"  Text: {text_out}")


if __name__ == '__main__':
    main()
