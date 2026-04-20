# Specification: Import Classical Musnad & Sunan Collections (non-Kutub al-Sittah)

## Overview

Extract 4 classical hadith collections from `pure_canon.jsonl` into a clean CSV dataset, then import into Neo4j using the existing pipeline. These collections complement the kutub al-sittah already in the database.

## Target Collections

| Arabic Source | Slug | Canonical Name | Count | Category |
|---|---|---|---|---|
| `مسند حنبل` | `ahmad` | `Musnad Ahmad` | ~23,529 | CLASSICAL_MUSNAD |
| `سنن الدارمي` | `darimi` | `Sunan al-Darimi` | ~2,477 | CLASSICAL_MUSNAD |
| `شافعي` | `shafii` | `Musnad al-Shafi'i` | ~2,054 | CLASSICAL_MUSNAD |
| `موطأ مالك` | `muwatta` | `Muwatta' Malik` | ~1,855 | CLASSICAL_MUSNAD |

**Total: ~29,915 hadiths**

## Out of Scope (separate track)

Authentication anthologies (al-Albani ~35k, al-Talidi ~9k, al-Ghumari ~489) are modern scholarly authentication compilations, not primary hadith collections. They will be handled in a dedicated "scholarly analysis" track with different data modeling (ScholarVerdict nodes linked to existing hadiths, not standalone Hadith nodes).

## Data Pipeline

```
pure_canon.jsonl → extract-classics.py → hadith_classical_musnad.csv → import-datasets.ts → Neo4j
                         ↓
              pure_canon_en.jsonl (merge translations)
                         ↓
              all_rawis.csv (map sanad to existing scholar_indx IDs)
```

### Source JSONL Structure

Each line is a JSON object:
- `id`: unique row identifier (e.g., `"pc_9"`)
- `text_ar`: Arabic matn (hadith body text)
- `chain`: Arabic isnad text (e.g., `"حدثنا موسى ابن داود حدثنا إبراهيم..."`)
- `ruling`: Arabic grading term
- `source`: Arabic source name (e.g., `"مسند حنبل"`)
- `topics`: comma-separated Arabic topic tags
- `hadith_no`: hadith number within collection

### Output CSV Schema

Match `all_hadiths_clean.csv` schema:
```
id,hadith_id,source,chapter_no,hadith_no,chapter,chain_indx,text_ar,text_en
```

- `id`: sequential integer (starting from 0 within this file)
- `hadith_id`: globally sequential (continue from max in `all_hadiths_clean.csv`)
- `source`: canonical English name from registry
- `chapter_no`: derived from `topics` field or set to 0
- `hadith_no`: from JSONL `hadith_no` field
- `chapter`: from `topics` field (Arabic topic tags)
- `chain_indx`: comma-separated `scholar_indx` values mapped from parsed sanad names, using existing IDs from `all_rawis.csv` where possible
- `text_ar`: Arabic matn
- `text_en`: English translation from `pure_canon_en.jsonl` (empty if translation failed)

### File Location

`datasets/hadith-data/hadith_classical_musnad.csv` (alongside `all_hadiths_clean.csv`)

## Functional Requirements

### FR-1: Arabic-to-Slug Mapping

Create a mapping module that translates Arabic `source` field values to canonical English slugs. Must handle the variant source names found in the JSONL (some entries have long bibliographic strings instead of short names).

### FR-2: Sanad/Narrator Mapping

Parse the Arabic `chain` field to extract narrator names, then map them to existing `scholar_indx` IDs from `all_rawis.csv`:
- Exact match on `name_arabic` → use existing `scholar_indx`
- Fuzzy match (normalized Arabic, stripped diacritics) → use existing `scholar_indx`
- No match → assign new `scholar_indx` (starting from a high range like 70001+) and append to a separate narrators CSV

### FR-3: Translation Merging

Merge English translations from `pure_canon_en.jsonl` by matching on `id` field. Rows where `text_en` contains `_translation_error` or is empty → leave `text_en` blank in output CSV.

### FR-4: CSV Generation

Output a CSV file matching the `all_hadiths_clean.csv` schema exactly, so the existing `import-datasets.ts` can ingest it with minimal changes.

### FR-5: Source Tier Labeling

Add a `source_tier` or `source_category` property to distinguish these from the kutub al-sittah:
- `KUTUB_AL_SITTAH` — Bukhari, Muslim, Abu Dawud, Tirmidhi, Nasa'i, Ibn Majah
- `CLASSICAL_MUSNAD` — Ahmad, Darimi, Shafi'i, Muwatta

This should be added to the canonical source registry (`src/lib/constants/sources.ts`).

### FR-6: Neo4j Import

Import the generated CSV using the existing pipeline (either extend `import-datasets.ts` to accept a second CSV or create a thin wrapper).

## Acceptance Criteria

1. `hadith_classical_musnad.csv` exists with ~29,915 rows matching the `all_hadiths_clean.csv` schema
2. `chain_indx` column is populated where sanad parsing succeeded, using existing `scholar_indx` IDs
3. English translations are merged where available
4. Admin UI shows results when filtering by each of the 4 collections
5. Hadiths sort correctly by `hadith_no` (numeric)
6. `source_tier` property distinguishes these from kutub al-sittah in queries/UI

## Technical Considerations

- **Python preprocessing**: The extraction script should be Python (like the existing `datasets/*.py` scripts) since it's data preprocessing, not application code
- **Narrator matching**: Arabic name matching is imprecise. Log match rates and create a report of unmatched names for manual review
- **hadith_id continuity**: The `hadith_id` column should continue from the max value in `all_hadiths_clean.csv` (currently ~34,441) to maintain global ordering
- **Never delete data files**: Back up or move instead
