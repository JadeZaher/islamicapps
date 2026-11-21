# Implementation Plan: Translate Classical Collections

## Overview

3 phases: (1) Extract & prepare, (2) Run translations, (3) Merge & validate.

---

## Phase 1: Extract & Prepare

Tasks:

- [ ] Task 1.1: Create extraction script `datasets/hadith-data/extract_classical_for_translation.py`
  - Read `pure_canon.jsonl`, filter to 4 target sources (with prefix matching for long-form variants)
  - Read `pure_canon_en.jsonl`, build set of IDs that already have good translations
  - Output `datasets/hadith-data/classical_to_translate.jsonl` — only rows needing translation
  - Output `datasets/hadith-data/classical_existing_translations.jsonl` — rows with existing good translations
  - Print summary: counts per collection, how many need translation vs. already done

- [ ] Task 1.2: Create translation prompt file
  - Create `datasets/hadith-data/classical_translation_prompt.txt`
  - Scholarly Arabic→English hadith translation prompt
  - Include instructions to preserve Islamic terminology
  - Include instruction to never refuse translation of scholarly religious text

- [ ] Task 1.3: Validate extraction
  - Run extraction script
  - Verify row counts match investigation data (~28,849 to translate, ~1,068 existing)
  - Spot-check 5 rows: correct source filtering, text_ar populated

---

## Phase 2: Run Translations

Run in order of collection size (smallest first for quick wins and prompt validation).

Tasks:

- [ ] Task 2.1: Translate Muwatta Malik (~1,827 rows)
  - `python translate_ollama_generic.py --input classical_to_translate.jsonl --output classical_muwatta_en.jsonl --source-field text_ar --dest-field text_en --prompt-file classical_translation_prompt.txt --filter-field source --filter-value "موطأ مالك"`
  - Or: pre-split by collection and translate each file separately
  - Spot-check 5 translations for quality
  - If quality is poor, adjust prompt or model and re-run

- [ ] Task 2.2: Translate Musnad al-Shafi'i (~1,962 rows)
  - Same approach as 2.1

- [ ] Task 2.3: Translate Sunan al-Darimi (~2,406 rows)
  - Same approach as 2.1

- [ ] Task 2.4: Translate Musnad Ahmad (~22,654 rows)
  - Largest batch — run with `--resume` support
  - May take 12-19 hours depending on model speed
  - Can be run overnight or in segments using `--start` / `--end`
  - Monitor for LLM refusals periodically

---

## Phase 3: Merge & Validate

Tasks:

- [ ] Task 3.1: Merge all translations
  - Create `datasets/hadith-data/merge_classical_translations.py`
  - Combine: existing good translations + newly translated rows
  - Filter out LLM refusals (patterns: "I cannot", "I'm unable", "I apologize", "_translation_error")
  - Output final: `datasets/hadith-data/classical_collections_translated.jsonl`
  - Print summary: total rows, translation coverage %, refusal count per collection

- [ ] Task 3.2: Quality validation
  - Random sample 20 translations across all 4 collections
  - Check: faithful to Arabic, readable English, no hallucination
  - Log any systematic issues (e.g., model struggles with specific terminology)

- [ ] Verification: Translation readiness
  - Final JSONL has all ~29,917 rows
  - Translation coverage > 90%
  - Refusals identified and counted
  - Ready for CSV extraction in import track

---

## File Inventory

### New files:
- `datasets/hadith-data/extract_classical_for_translation.py`
- `datasets/hadith-data/classical_translation_prompt.txt`
- `datasets/hadith-data/classical_to_translate.jsonl` (generated)
- `datasets/hadith-data/classical_existing_translations.jsonl` (generated)
- `datasets/hadith-data/classical_collections_translated.jsonl` (final output)
- `datasets/hadith-data/merge_classical_translations.py`

### Existing files (read-only):
- `datasets/hadith-data/sheikahmad/pure_canon.jsonl`
- `datasets/hadith-data/sheikahmad/pure_canon_en.jsonl`
- `datasets/translate_ollama_generic.py`

## Time Estimates

| Collection | Rows to translate | Est. time @ 2.5s/row |
|---|---|---|
| Muwatta Malik | ~1,827 | ~1.3 hours |
| Musnad al-Shafi'i | ~1,962 | ~1.4 hours |
| Sunan al-Darimi | ~2,406 | ~1.7 hours |
| Musnad Ahmad | ~22,654 | ~15.7 hours |
| **Total** | **~28,849** | **~20 hours** |

Can run across multiple sessions with `--resume`.
