# Implementation Plan: Import Classical Musnad & Sunan Collections

## Overview

3 phases: (1) Data extraction & CSV generation (Python), (2) Source registry + import updates (TypeScript), (3) Import execution & verification.

**Key insight:** The heavy lifting is a Python preprocessing script that produces a CSV matching the existing schema. The Neo4j import then reuses the existing pipeline.

---

## Phase 1: Data Extraction & CSV Generation (Python)

Goal: Extract 4 classical collections from `pure_canon.jsonl`, map sanad to existing narrator IDs, merge translations, output clean CSV.

Tasks:

- [ ] Task 1.1: Create Arabic-to-slug mapping in extraction script
  - Map known Arabic source names to canonical English names:
    - `"مسند حنبل"` → `Musnad Ahmad`
    - `"سنن الدارمي"` → `Sunan al-Darimi`
    - `"شافعي"` → `Musnad al-Shafi'i`
    - `"موطأ مالك"` → `Muwatta' Malik`
  - Handle long bibliographic variant strings (some entries have full book metadata as source)
  - Skip entries matching the 6 kutub al-sittah and all anthology sources

- [ ] Task 1.2: Build narrator name matcher
  - Load `datasets/narrator-data/all_rawis.csv` (or `datasets/hadith-data/all_rawis.csv`) to get existing `scholar_indx` → `name` mappings
  - Parse Arabic `chain` field: split on transmission verbs (`حدثنا`, `أخبرنا`, `عن`, etc.)
  - For each extracted narrator name:
    - Normalize Arabic (strip diacritics, normalize alif/hamza variants)
    - Attempt match against existing narrators
    - If matched → use their `scholar_indx`
    - If unmatched → assign new ID from range 70001+
  - Output `chain_indx` as comma-separated `scholar_indx` values
  - Log match statistics and save unmatched names for manual review

- [ ] Task 1.3: Merge English translations from translation track
  - Read `datasets/hadith-data/classical_collections_translated.jsonl` (output of translation track)
  - Build `id → text_en` lookup map
  - For each classical hadith row, look up translation by `id`
  - Skip entries where `text_en` is empty or contains refusal patterns
  - Log translation coverage rate per collection
  - **Dependency:** `translate_classical_collections_20260418` track must be complete

- [ ] Task 1.4: Generate output CSV
  - Create `datasets/hadith-data/hadith_classical_musnad.csv`
  - Schema: `id,hadith_id,source,chapter_no,hadith_no,chapter,chain_indx,text_ar,text_en`
  - `id`: sequential from 0 within this file
  - `hadith_id`: continue from max in `all_hadiths_clean.csv` (34441+)
  - `chapter`: from `topics` field
  - Sort by source, then hadith_no
  - Generate summary report: row counts per source, translation coverage, narrator match rate

- [ ] Task 1.5: Generate new narrators CSV (if any unmatched)
  - If new narrators were created (scholar_indx 70001+), output to `datasets/narrator-data/classical_musnad_rawis.csv`
  - Schema matching `all_rawis.csv`
  - These can be imported alongside the hadiths

- [ ] Verification: Phase 1 data quality check
  - CSV has ~29,915 rows
  - All 4 sources represented with expected counts
  - `chain_indx` populated for Ahmad, Darimi, and Muwatta (which have chain data)
  - **Shafi'i note:** chain_indx will be empty (source data has no isnads). `hadith_no` derived from `shelf_no`. See `shafii-research.md` for future enrichment plan.
  - Spot-check 10 rows: source names correct, hadith_no populated, text_ar non-empty
  - Translation coverage documented per collection

---

## Phase 2: Source Registry & Import Updates (TypeScript)

Goal: Add source tier labeling and prepare the import pipeline for the new CSV.

Tasks:

- [ ] Task 2.1: Add `tier` field to source registry
  - In `src/lib/constants/sources.ts`, add `tier: 'KUTUB_AL_SITTAH' | 'CLASSICAL_MUSNAD' | 'IBADI_CANON'` to `SourceEntry`
  - Set tier for existing entries:
    - bukhari, muslim, abudawud, tirmidhi, nasai, ibnmajah → `KUTUB_AL_SITTAH`
    - ahmad, darimi, shafii, muwatta → `CLASSICAL_MUSNAD`
    - musnad_rabi → `IBADI_CANON`
  - Update `getSourceFilterOptions()` to optionally group by tier

- [ ] Task 2.2: Add npm script for importing the new CSV
  - Add `package.json` script: `"db:import:classical": "tsx src/scripts/import-datasets.ts --input datasets/hadith-data/hadith_classical_musnad.csv"`
  - Or: extend `import-datasets.ts` to accept an `--input` flag for the CSV path (currently hardcoded)
  - Ensure Source nodes for the 4 new collections are created (extend `createSources()` to include them)

- [ ] Task 2.3: Store `source_tier` on Hadith and Source nodes
  - During import, set `h.source_tier` from the registry's tier value
  - Update the `createSources()` function to set `s.source_tier` on Source nodes
  - Add index in `schema.ts`: `{ label: 'Hadith', prop: 'source_tier' }`

- [ ] Verification: Phase 2 code readiness
  - TypeScript compiles cleanly
  - Source registry has tier labels for all entries
  - Import script can accept the new CSV path

---

## Phase 3: Import Execution & Verification

Goal: Import the CSV into Neo4j and verify everything works end-to-end.

Tasks:

- [ ] Task 3.1: Apply schema updates
  - Run `npm run db:init` to create the new `source_tier` index

- [ ] Task 3.2: Import new narrators (if any)
  - If Task 1.5 produced a new narrators CSV, import those first
  - Use the narrator import section of `import-datasets.ts` or a dedicated mini-script

- [ ] Task 3.3: Import classical musnad hadiths
  - Run the import script against `hadith_classical_musnad.csv`
  - Monitor progress — ~30k rows, expect batched execution
  - Verify no duplicate hadith IDs or source name mismatches

- [ ] Task 3.4: Verify in admin UI
  - Filter by each of the 4 new collections — non-zero results
  - Sort order correct (numeric)
  - Hadith detail pages load with Arabic text
  - Isnad chain visualization renders where chain_indx is populated

- [ ] Verification: Phase 3 final acceptance
  - `MATCH (h:Hadith) WHERE h.source_tier = 'CLASSICAL_MUSNAD' RETURN h.source, count(h) ORDER BY h.source` shows all 4 collections
  - `MATCH (s:Source) RETURN s.name, s.source_tier, count{(h:Hadith)-[:FROM_SOURCE]->(s)} ORDER BY s.name` shows correct counts
  - Admin UI filters work for all collections

---

## File Inventory

### New files:
- `datasets/hadith-data/extract_classical_musnad.py` — Python extraction script
- `datasets/hadith-data/hadith_classical_musnad.csv` — output CSV (generated)
- `datasets/narrator-data/classical_musnad_rawis.csv` — new narrators (generated, if any)

### Modified files:
- `src/lib/constants/sources.ts` — add `tier` field
- `src/lib/db/schema.ts` — add `source_tier` index
- `src/scripts/import-datasets.ts` — accept `--input` flag, create Source nodes for new collections
- `package.json` — add `db:import:classical` script

### Data files (read-only):
- `datasets/hadith-data/sheikahmad/pure_canon.jsonl`
- `datasets/hadith-data/sheikahmad/pure_canon_en.jsonl`
- `datasets/hadith-data/all_hadiths_clean.csv` (read for max hadith_id)
- `datasets/narrator-data/all_rawis.csv` (read for narrator matching)
