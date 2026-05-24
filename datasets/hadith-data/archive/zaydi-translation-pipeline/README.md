# Zaydi Hadith Translation Pipeline

Translation pipeline for Musnad al-Imam Zayd ibn Ali (Zaydi tradition).
Arabic text was OCR-parsed from PDF, then translated via OpenRouter LLM.

## Pipeline Steps

1. `prepare_zaydi_jsonl.py` → `zaydi_for_translation.jsonl` (627 hadiths for translation)
2. `run_zaydi_translation.sh` + `translate_openrouter.py` → `zaydi_translated.jsonl`
3. Refusal detection → `refused_ids.txt` (258 IDs)
4. Retranslation → `zaydi_retranslated.jsonl` (258 re-done, 0 failures)
5. `fix_zaydi_data.py` — Merged retranslations + cleaned 75 OCR-corrupted chapter names

## Key Files

| File | Description |
|------|-------------|
| `zaydi_for_translation.jsonl` | Input for translation (627 hadiths) |
| `zaydi_retranslated.jsonl` | 258 retranslated previously-refused hadiths |
| `refused_ids.txt` | IDs that were initially refused by the LLM |
| `zaydi_translation_prompt.txt` | LLM prompt used for translation |
| `run_zaydi_translation.sh` | Shell script to run translation batch |
| `musnad_zayd_arabic_text.txt` | Raw Arabic text extract from PDF |
| `zaydi-hadith.zip` | Backup zip of Zaydi hadith directory |

## Status

Completed. All 627 hadiths translated, 75 chapter names fixed.
Active data lives in `zaydi-hadith/` (parent directory).
