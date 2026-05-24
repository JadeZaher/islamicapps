# Zaydi Hadith Pipeline

Source: **Musnad al-Imam Zayd ibn Ali** (مسند الإمام زيد بن علي)
Compiler: Abd al-Aziz ibn Ishaq al-Baghdadi
School: Shia Zaydi
Total hadiths: **627**

The Musnad Zayd is one of the earliest surviving hadith collections in Islam, attributed to Zayd ibn Ali ibn al-Husayn (d. 122 AH), the great-grandson of Ali ibn Abi Talib. It covers fiqh topics ranging from tahara and salah through mu'amalat, hudud, and inheritance.

---

## Pipeline Execution Order

Run scripts in the following sequence to reproduce the processed dataset from scratch.

### 1. `parse_musnad_zayd.py`
Parses the raw Arabic text file (`musnad_zayd_arabic_text.txt`) into structured JSON.
Extracts chapter names, hadith numbers, sanad (chain of transmission), and matn (hadith body).
Output: `parsed_zaydi_hadiths.json`

### 2. `prepare_zaydi_jsonl.py`
Converts `parsed_zaydi_hadiths.json` into JSONL format suitable for translation and downstream processing.
Assigns stable IDs (`zayd_0001` ... `zayd_0627`), maps chapter metadata, and writes one record per line.
Output: `zaydi_for_cleanup.jsonl`

### 3. `clean_arabic_text.py`
Mechanical, regex-based cleanup of OCR artifacts in the Arabic text fields.
Removes stray diacritics, normalises ligatures, strips non-Arabic noise introduced during OCR.
Input: `zaydi_for_cleanup.jsonl`
Output: `zaydi_cleaned.jsonl`

### 4. `purify_arabic_text.py`
LLM-based Arabic text purification using a local Gemma model served via LM Studio.
Sends each hadith's Arabic text to the model with a structured prompt (`cleanup_prompt.txt`) to produce clean, readable classical Arabic.
Input: `zaydi_cleaned.jsonl`
Output: `zaydi_for_purification.jsonl` (batched input), `zaydi_purified.jsonl` (purified output)
Requires: LM Studio running locally with a Gemma model loaded.

### 5. `fix_zaydi_data.py`
Data corrections and integrity fixes applied after purification.
Handles edge cases such as empty records, malformed JSON, and field normalisation.
Input/Output: operates on the purified JSONL and updates `parsed_zaydi_hadiths.json`

### 6. `fix_chapter_names.py`
Cleans OCR artifacts from chapter name fields specifically.
Removes printed-book footnote markers (e.g., `‏)١(‏`), stray parenthetical junk (`(؟")`), and fixes the common OCR misread `ياب` → `باب`.
Input/Output (in-place): `zaydi_translated.jsonl`, `parsed_zaydi_hadiths.json`
Safe to re-run; idempotent.

### 7. `merge_zaydi_translations.py`
Merges English translations back into the main dataset alongside the cleaned Arabic text.
Produces the final unified file used by the import scripts.
Input: `zaydi_purified.jsonl` + translation JSONL
Output: `zaydi_translated.jsonl`

---

## Output Files

| File | Description |
|------|-------------|
| `parsed_zaydi_hadiths.json` | Structured JSON with full metadata, sanad/matn split, and chapter info |
| `zaydi_translated.jsonl` | Final JSONL — 627 records with Arabic text, English translation, chapter, and source fields |
| `zaydi_hadiths.csv` | CSV export for spreadsheet review |
| `zaydi_hadiths_clean.csv` | CSV with cleaned Arabic text (post purification) |
| `zaydi_hadiths_full.csv` | CSV including all intermediate fields |
| `zaydi_cleaned.jsonl` | Arabic text after mechanical regex cleanup (pre-LLM) |
| `zaydi_purified.jsonl` | Arabic text after LLM-based purification |
| `zaydi_for_cleanup.jsonl` | Input batch prepared for `clean_arabic_text.py` |
| `zaydi_for_purification.jsonl` | Input batch prepared for `purify_arabic_text.py` |
| `cleanup_prompt.txt` | System prompt used for LLM purification |
| `musnad_zayd.pdf` | Original scanned PDF source |

---

## Notes

- Chapter names in the source PDF carry printed footnote markers (e.g., `‏)١(‏`) that OCR renders as garbage. `fix_chapter_names.py` handles all known patterns.
- The Arabic text contains significant OCR noise from the scanned PDF. The two-stage cleanup (regex + LLM) reduces but does not eliminate all noise; matn text should be treated as approximate.
- Import into the main database is handled by `src/scripts/reimport-zaydi.ts`.
