# Specification: Translate Classical Musnad & Sunan Collections

## Overview

Bulk-translate ~29,917 Arabic hadiths from 4 classical collections into English using the existing Ollama translation pipeline (`translate_ollama_generic.py`). This is a prerequisite for the classical import track — translations must be ready before generating the import CSV.

## Current Translation Coverage

| Collection | Arabic Source | Total | Existing Translations | Coverage |
|---|---|---|---|---|
| Musnad Ahmad | `مسند حنبل` | 23,529 | 875 | 3.7% |
| Sunan al-Darimi | `سنن الدارمي` | 2,478 | 72 | 2.9% |
| Musnad al-Shafi'i | `شافعي` | 2,054 | 92 | 4.5% |
| Muwatta Malik | `موطأ مالك` | 1,856 | 29 | 1.6% |
| **Total** | | **29,917** | **1,068** | **3.6%** |

Remaining to translate: ~28,849 hadiths.

## Data Pipeline

```
pure_canon.jsonl
    → filter to 4 classical collections
    → extract_for_translation.py → classical_to_translate.jsonl (Arabic-only, ~29k rows)
    → translate_ollama_generic.py → classical_translated.jsonl (with text_en)
    → merge existing good translations from pure_canon_en.jsonl
    → final output: classical_collections_translated.jsonl
```

## Functional Requirements

### FR-1: Extract Classical Hadiths for Translation

Create a Python script that:
- Reads `pure_canon.jsonl`
- Filters to rows where `source` matches the 4 target collections (including long-form variants)
- Skips rows that already have good translations in `pure_canon_en.jsonl`
- Outputs a JSONL file ready for `translate_ollama_generic.py`

### FR-2: Translation Prompt

Create a hadith-specific translation prompt that:
- Instructs faithful, scholarly translation of classical Arabic hadith text
- Preserves Islamic terminology (e.g., keep "salah" not "prayer", "wudu" not "ablution" — or use both)
- Handles vocalized/tashkeel text correctly
- Does NOT refuse to translate any content (override LLM safety filters for scholarly text)
- Keeps translation concise and readable

### FR-3: Run Translations via Ollama

Use `translate_ollama_generic.py` with:
- `--source-field text_ar --dest-field text_en`
- `--resume` support for the long Ahmad run (~23k)
- Recommended model: `gemma3:12b` or similar capable Arabic→English model
- Batch by collection (smallest first): Muwatta → Shafi'i → Darimi → Ahmad

### FR-4: Merge and Quality Check

- Merge new translations with existing good ones from `pure_canon_en.jsonl`
- Filter out LLM refusals ("I cannot fulfill...", "I'm unable to translate...")
- Spot-check 20 random translations for accuracy
- Output final merged JSONL: `datasets/hadith-data/classical_collections_translated.jsonl`

## Acceptance Criteria

1. All ~29,917 hadiths have a `text_en` field (even if some are empty after filtering bad translations)
2. Translation coverage > 90% across all 4 collections
3. LLM refusals identified and logged (expected for some content)
4. Final JSONL is ready for the CSV extraction script in the import track

## Technical Notes

- **Time estimate:** At ~2-3 seconds per translation with Ollama local, Ahmad alone (~23k) would take ~15-19 hours. Run overnight or across multiple sessions using `--resume`.
- **Model choice:** `gemma3:12b` is already referenced in the translate script. Consider `qwen2.5:14b` or `llama3.1:8b` as alternatives if Arabic quality is poor.
- **Existing translations:** The 1,068 existing translations in `pure_canon_en.jsonl` should be preserved (they're already decent quality). Only translate the ~28,849 missing ones.
- **LLM refusal pattern:** Some translations in the existing file contain refusal text. The merge step must detect patterns like "I cannot", "I'm unable", "_translation_error" and mark those as needing re-translation.

## Out of Scope

- Translating anthology collections (Albani, Talidi, Ghumari)
- Translating the kutub al-sittah (already have translations in `all_hadiths_clean.csv`)
- Human review of translations (can be done incrementally later)
