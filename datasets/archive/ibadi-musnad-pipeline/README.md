# Ibadi Musnad Pipeline

OCR extraction and translation pipeline for Musnad al-Imam al-Rabi' ibn Habib (Ibadi tradition).

## Pipeline Steps

1. `01_ocr_extract_extracthadithfrompdf.py` — OCR extraction from `ibadimusnad.pdf` → `raw_ocr_pages.json`
2. `02_parse_hadiths.py` — Parse OCR output into structured hadiths → `parsed_hadiths.json`
3. `03_translate_ollama_eng_to_arabic.py` — Arabic-to-English translation via Ollama
4. `04_generate_csvs.py` — Generate `musnad_hadiths.csv` and `musnad_rawis.csv`
5. `merge_musnad_translations.py` — Merge translations back into source data

## Supporting Scripts

| File | Description |
|------|-------------|
| `run_pipeline.py` | Full pipeline runner |
| `dedup_jsonl.py` | Deduplication utility |
| `extract_xlsx_to_jsonl.py` | Excel to JSONL converter |
| `merge_translated_to_xlsx.py` | Merge translations back to Excel |
| `translate_ollama_generic.py` | Generic Ollama translation wrapper |

## Key Data Files

| File | Description |
|------|-------------|
| `ibadimusnad.pdf` | Source PDF (Musnad al-Rabi') |
| `raw_ocr_pages.json` | Raw OCR output |
| `parsed_hadiths.json` | Structured parsed hadiths |
| `parsed_hadiths_regex.json` | Regex-based parse variant |
| `parsed_hadiths_llm_test.json` | LLM-assisted parse variant |
| `musnad_hadiths.jsonl` | JSONL export |
| `musnad_hadiths_en.jsonl` | English translations |
| `musnad_hadiths.csv.bak` | CSV backup |

## Status

Completed. Output merged into `all_hadiths_clean.csv` as part of the Sunni collections.
Active CSV is at `datasets/musnad_hadiths.csv`.
