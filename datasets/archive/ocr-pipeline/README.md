# Archived OCR Pipeline Scripts

These scripts were used for the initial OCR-based extraction of hadith text from scanned PDFs.
They are **superseded** by `datasets/parse_openiti.py` which uses clean, community-typed text
from the OpenITI project (Maktaba Shamila al-Zaydiyya and al-Ibadiyya).

## Why superseded

| Metric | OCR Pipeline (these scripts) | OpenITI Pipeline (current) |
|--------|------------------------------|---------------------------|
| Zayd hadith count | 627 | 699 |
| OCR artifacts | Hundreds (©, garbled chars, footnote noise) | 0 |
| Text source | EasyOCR on scanned PDF (CER ~0.20) | Community-proofread Shamela |
| Ibadi hadiths | Never parsed | 1,004 |

## Contents

### Top-level scripts
- `ocr_arabic_pdf.py` — EasyOCR wrapper with Arabic preprocessing (400 DPI, grayscale, beamsearch)
- `run_ocr_jobs.py` — Batch OCR runner for multiple PDFs
- `translate_openrouter.py` — OpenRouter API translation helper

### zaydi/ subdirectory
- `parse_musnad_zayd.py` — Original regex parser for OCR'd Zayd text
- `clean_arabic_text.py` — Mechanical Arabic text cleanup (regex-based)
- `purify_arabic_text.py` — LLM-assisted Arabic purification via Gemma/LM Studio
- `fix_zaydi_data.py` — Data fixup script
- `fix_chapter_names.py` — Chapter name cleanup (OCR artifacts in headings)
- `merge_zaydi_translations.py` — Merge LLM translations back into dataset
- `prepare_zaydi_jsonl.py` — Prepare JSONL for translation pipeline
- `cleanup_prompt.txt` — LLM prompt for Arabic text cleanup
- Various `.jsonl` intermediate files from the translation/cleanup pipeline

## Current pipeline

Use `datasets/parse_openiti.py` instead. It reads OpenITI mARkdown files from
`datasets/hadith-data/openiti-sources/` and produces clean structured output.
