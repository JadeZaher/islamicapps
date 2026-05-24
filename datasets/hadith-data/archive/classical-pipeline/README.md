# Classical Sunni Hadith Translation Pipeline

Pipeline that extracted, translated, and enhanced the six canonical Sunni collections
(Bukhari, Muslim, Tirmidhi, Abu Dawud, Nasa'i, Ibn Majah) into the unified dataset.

## Pipeline Steps

1. `extract_classical_for_translation.py` — Extracted Arabic hadiths from source data into JSONL for translation
2. Translation via OpenRouter LLM → `classical_collections_translated.jsonl`
3. `split_translation_errors.py` — Separated clean, failed, and refused translations
4. Failed/refused retranslation → `classical_failed_retranslated.jsonl`, `classical_refused_retranslated.jsonl`
5. `parse_sanad.py` — Extracted isnad chains → `classical_sanad_parsed.jsonl`
6. Enhancement into CSV → `classical_canon_enhanced.csv`, `classical_canon_translated.csv`

## Key Files

| File | Description |
|------|-------------|
| `classical_collections_final.jsonl` | Final parsed hadiths before translation |
| `classical_collections_translated.jsonl` | All translations (63 MB) |
| `classical_translations_clean.jsonl` | Clean successful translations |
| `classical_translations_failed.jsonl` | Failed translations |
| `classical_translations_refused.jsonl` | Refused translations |
| `classical_sanad_parsed.jsonl` | Parsed isnad chains |
| `classical_canon_enhanced.csv` | Enhanced CSV with sanad + translations |
| `classical_canon_translated.csv` | Translated CSV output |
| `classical_translation_prompt.txt` | LLM prompt used for translation |

## Status

Completed. Output merged into `all_hadiths_clean.csv` (34,441 Sunni hadiths).
