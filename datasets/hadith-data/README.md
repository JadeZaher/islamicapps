# Hadith Dataset Documentation

This directory contains the compiled hadith datasets used by the IslamicApps application.
All active datasets are flat CSV files. Source pipelines and intermediate artifacts are
stored in subdirectories or archived under `archive/`.

---

## Dataset Inventory

### Active Files

| File | Rows | Size | Description |
|------|------|------|-------------|
| `all_hadiths_clean.csv` | 34,441 | ~38 MB | Primary dataset: Sunni only (Kutub al-Sittah). Zaydi/Ibadi stripped pending quality validation. |
| `all_hadiths_shia.csv` | ~33,817 | ~90 MB | Imami (Thaqalayn) dataset. Extended schema with grading fields. Not in git (too large). |
| `all_hadiths_shia.csv.gz` | ~33,817 | ~16 MB | Compressed version of above for git storage. |

### Zaydi Sub-directory (`zaydi-hadith/`)

| File | Rows | Description |
|------|------|-------------|
| `parsed_hadiths.json` | 699 | Authoritative JSON from OpenITI clean text. Source of truth. |
| `zaydi_hadiths_clean.csv` | 699 | Minimal CSV (id, source, tradition, bab, text_ar). |
| `zaydi_hadiths_full.csv` | 699 | Full schema CSV for unified dataset integration. |
| `PROVENANCE.json` | — | Transformation metadata (source URI, parse date, what changed). |

**Source**: OpenITI `0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1` (community-typed from Shamela al-Zaydiyya, NOT OCR).

### Ibadi Sub-directory (`ibadi-hadith/`)

| File | Rows | Description |
|------|------|-------------|
| `parsed_hadiths.json` | 1,004 | Authoritative JSON from OpenITI clean text. Includes al-Rabi commentary (138 hadiths). |
| `ibadi_hadiths_clean.csv` | 1,004 | Minimal CSV. |
| `ibadi_hadiths_full.csv` | 1,004 | Full schema CSV for unified dataset integration. |
| `PROVENANCE.json` | — | Transformation metadata. |

**Source**: OpenITI `0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1` (community-typed from Shamela al-Ibadiyya, NOT OCR).

> Both collections are parsed by `datasets/parse_openiti.py`. Old OCR-based scripts are archived in `datasets/archive/ocr-pipeline/`.

---

## Column Schemas

### `all_hadiths_clean.csv`

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Sequential global ID |
| `hadith_id` | str/int | Source-internal hadith number |
| `source` | str | Collection name (see collections table below) |
| `chapter_no` | int | Chapter number within collection |
| `hadith_no` | int/str | Hadith number within chapter |
| `chapter` | str | Chapter title (Arabic for Zaydi, transliterated for Sunni) |
| `chain_indx` | str | Comma-separated narrator node IDs (from scholar graph); blank for Zaydi |
| `text_ar` | str | Full Arabic text (sanad + matn for Sunni; matn-focused for Zaydi) |
| `text_en` | str | English translation |

### `all_hadiths_shia.csv` / `all_hadiths_shia.csv.gz`

All columns from the clean schema above plus:

| Column | Type | Description |
|--------|------|-------------|
| `volume` | int | Volume number |
| `category` | str | Top-level category / book name (Arabic) |
| `sanad` | str | Isnad chain text or Thaqalayn sanad reference |
| `matn_en` | str | English matn only (Thaqalayn field; blank for non-Thaqalayn sources) |
| `grading_majlisi` | str | Allama Majlisi's grading (Imami only) |
| `grading_mohseni` | str | Sheikh Mohseni's grading (Imami only) |
| `grading_behbudi` | str | Sheikh Behbudi's grading (Imami only) |
| `gradings_full` | str | Pipe-delimited full grading list: `Scholar: Grade (Reference)` |
| `url` | str | Thaqalayn source URL |

---

## Collections by Tradition

### Sunni — Kutub al-Sittah (~34,441 hadiths in `all_hadiths_clean.csv`)

| Collection | Source field value |
|------------|--------------------|
| Sahih al-Bukhari | `Sahih Bukhari` |
| Sahih Muslim | `Sahih Muslim` |
| Sunan al-Nasa'i | `Sunan an-Nasa'i` |
| Sunan Abi Dawud | `Sunan Abi Da'ud` |
| Jami' al-Tirmidhi | `Jami' al-Tirmidhi` |
| Sunan Ibn Majah | `Sunan Ibn Majah` |

Source: Parsed from public corpus; translations via OpenRouter LLM (April 2026).
Isnad chains parsed by `archive/classical-pipeline/parse_sanad.py`.

### Zaydi — Musnad al-Imam Zayd ibn Ali (627 hadiths)

- **Source field value**: `Musnad al-Imam Zayd ibn Ali`
- **Compiler**: Abd al-Aziz ibn Ishaq al-Baghdadi
- **Source**: Arabic text extracted from Archive.org digitization (djvu.txt) of the Musnad, then OCR-parsed.
- **Translations**: LLM-translated via OpenRouter. 258 hadiths required a retranslation pass.
- Present in both `all_hadiths_clean.csv` and `all_hadiths_shia.csv`.

### Imami — Thaqalayn API (~33,817 hadiths in `all_hadiths_shia.csv`)

- **Source**: ThaqalaynAPI V2 JSON files (34 books in `shia-hadith/v2_books/`)
- **Grading**: Per-hadith grades from Majlisi, Mohseni, and Behbudi where available
- **Isnad**: Thaqalayn sanad field included
- Not present in `all_hadiths_clean.csv` (separate file due to schema differences and size)

---

## Data Flow / Pipeline

```
[Sources]
  Kutub al-Sittah (public corpus)
  ThaqalaynAPI V2 JSON (34 books)
  Musnad Zayd PDF (Archive.org OCR)
  SheikhAhmad XLSX (Pure Canon + Green Book)

[Processing]
  1. Extract → JSONL
  2. Translate (OpenRouter LLM)
  3. Parse isnad chains (parse_sanad.py)
  4. Merge & deduplicate

[Output]
  all_hadiths_clean.csv         ← Sunni + Zaydi (minimal schema)
  all_hadiths_shia.csv(.gz)     ← Imami + Zaydi (full schema)
```

### Regeneration

`regen_unified_csvs.py` in this directory rebuilds both CSVs from scratch:
1. Calls `shia-hadith/build_csv.py` to regenerate the Imami CSV from `v2_books/` JSON
2. Appends Zaydi hadiths (read from `zaydi-hadith/parsed_zaydi_hadiths.json`)
3. Writes `all_hadiths_shia.csv` (full schema) and `all_hadiths_clean.csv` (minimal schema)

---

## Archive Documentation

All archived directories are under `archive/`. They are kept for reproducibility and
debugging; the data they contain has been merged into the active CSVs.

### `archive/classical-pipeline/`

Translation pipeline for the six Sunni collections. Archived April 28, 2026.

| File | Description |
|------|-------------|
| `classical_collections_final.jsonl` | 67,232-line JSONL of parsed Sunni hadiths before translation |
| `classical_collections_translated.jsonl` | Full translation output (63 MB) |
| `classical_translations_clean.jsonl` | Successful translations |
| `classical_translations_failed.jsonl` | Failed translations (retranslated separately) |
| `classical_translations_refused.jsonl` | LLM-refused translations |
| `classical_sanad_parsed.jsonl` | Parsed isnad chains |
| `classical_canon_enhanced.csv` | Enhanced CSV (32 MB) — final output before unification |
| `extract_classical_for_translation.py` | Extracts Arabic hadiths for LLM translation |
| `parse_sanad.py` | Parses isnad chains into node IDs |
| `split_translation_errors.py` | Separates clean/failed/refused translation output |

### `archive/consolidation-logs/`

Hourly status snapshots and analysis from the April 20, 2026 dataset consolidation session.
Includes `CONSOLIDATION_LOG.txt` (full log), hourly `CONSOLIDATION_STATUS_*.txt` files,
`PHASE10_OPTIMIZATION_ANALYSIS_2026-04-20.txt`, `audit_report.txt`, and two enhancement
scripts (`phase9_shia_enhancement.py`, `phase9_shia_sanad_extraction.py`) that were run
during consolidation.

### `archive/sheikahmad-pure-canon/`

Processing pipeline for the "Hadith Pure Canon Authentica" and "Green Book of Sahih Hadith"
Excel datasets from SheikhAhmad / NabiMuhammad.com. Imported directly into Neo4j; not
merged into the CSV files.

| File | Records | Description |
|------|---------|-------------|
| `pure_canon.jsonl` | ~100,216 | Full Pure Canon dataset |
| `green_book.jsonl` | ~35,452 | Green Book of Sahih Hadith |
| `pure_canon_en.jsonl` | partial | English translations |
| `import-pure-canon.ts` | — | Neo4j import script |
| `canon-normalize.ts` | — | Source name normalization |
| `rename-anthology-sources.ts` | — | Anthology source renaming |
| `scholar-graph-actions.ts` | — | Scholar graph relationship actions |

Source Excel files remain in `sheikahmad/` at the top of this directory.

### `archive/unified-snapshots/`

Point-in-time snapshots of the consolidated dataset from April 20, 2026, before the Zaydi
collection was added and before chapter name cleanup. Not the authoritative current state.

| File | Description |
|------|-------------|
| `unified_hadith_consolidated.csv` | Full consolidated CSV (140 MB, all traditions) |
| `unified_hadith_consolidated.csv.gz` | Compressed version (32 MB) |
| `unified_hadith_collection_2026-04-20_enhanced.xlsx` | Excel export with enhanced metadata (41 MB) |
| `cross_reference_mapping.csv` | Cross-tradition parallel hadith mapping (~44,084 mappings) |

### `archive/zaydi-translation-pipeline/`

Translation pipeline artifacts for the Zaydi collection. Archived after completion.

| File | Description |
|------|-------------|
| `zaydi_for_translation.jsonl` | 627 hadiths prepared for LLM translation |
| `zaydi_retranslated.jsonl` | 258 hadiths retranslated after initial refusals |
| `refused_ids.txt` | 258 hadith IDs initially refused by the LLM |
| `zaydi_translation_prompt.txt` | LLM prompt used for translation |
| `musnad_zayd_arabic_text.txt` | Raw Arabic OCR text from Archive.org PDF |

### `archive/logs/`

`translate_classical.log` — Full log from the Sunni translation run (April 14, 2026).

---

## Data Quality Notes

### Zaydi (Musnad al-Imam Zayd ibn Ali)

- **OCR artifacts**: The source PDF was digitized by Archive.org as djvu.txt. Heavy OCR
  corruption is present in the Arabic text: garbled letters, stray punctuation (`#`, `+`,
  `_`, `٠‏`), footnote markers embedded in text, and `داب` for `باب` (chapter headings).
- **Mechanical cleanup**: `clean_arabic_text.py` strips the most common artifacts.
- **LLM purification pipeline** (`purify_arabic_text.py`): In progress. Sends hadiths to
  Gemma for Arabic text reconstruction with a confidence score (1=clean, 4=heavily garbled).
  `zaydi_for_purification.jsonl` contains all 627 hadiths prepared; `zaydi_cleaned.jsonl`
  has 23 merged results so far.
- **Translation refusals**: 258 of 627 hadiths were initially refused by the LLM during
  translation (likely due to garbled text). All 258 were successfully retranslated.
- Chapter names were cleaned post-parse: 75 OCR-corrupted chapter headings were fixed by
  `fix_zaydi_data.py`.

### Sunni Collections

- Translations were LLM-generated (OpenRouter, April 2026). A small number of hadiths in
  `classical_translations_refused.jsonl` may have incomplete translations in the final CSV.
- Isnad chains are stored as comma-separated scholar graph node IDs in `chain_indx`.
  The raw isnad text is preserved in `text_ar`.

### Imami (Thaqalayn)

- Grading fields (`grading_majlisi`, `grading_mohseni`, `grading_behbudi`) are present
  only where the Thaqalayn API provides them; many records have empty grading fields.
- `matn_en` is the Thaqalayn-specific English matn field and may differ from `text_en`
  (which is the full hadith English text).

---

## Scripts

### Active Scripts (this directory)

| Script | Purpose |
|--------|---------|
| `regen_unified_csvs.py` | Rebuild `all_hadiths_clean.csv` and `all_hadiths_shia.csv` from source data |
| `add_tradition_column.py` | Add/update `tradition` column to `all_hadiths_clean.csv` |

### Active Scripts (`shia-hadith/`)

| Script | Purpose |
|--------|---------|
| `build_csv.py` | Build `all_hadiths_shia.csv` from Thaqalayn V2 JSON files |
| `download_thaqalayn.py` | Download Thaqalayn API JSON into `v2_books/` |

### Active Scripts (`zaydi-hadith/`)

| Script | Purpose |
|--------|---------|
| `parse_musnad_zayd.py` | Parse Arabic OCR text into structured hadith records; produces `zaydi_hadiths.csv`, `zaydi_hadiths_full.csv`, `parsed_zaydi_hadiths.json` |
| `clean_arabic_text.py` | Phase 1 mechanical OCR artifact removal; Phase 2 prep for LLM cleanup |
| `purify_arabic_text.py` | LLM-assisted Arabic text purification via Gemma with confidence scoring |
| `fix_zaydi_data.py` | Merge retranslations, fix 75 OCR-corrupted chapter names, regenerate CSVs |
| `merge_zaydi_translations.py` | Merge LLM translation output back into parsed JSON |
| `prepare_zaydi_jsonl.py` | Prepare JSONL input for the translation pipeline |
