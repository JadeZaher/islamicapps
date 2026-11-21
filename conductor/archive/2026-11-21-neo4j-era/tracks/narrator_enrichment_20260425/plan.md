# Narrator Enrichment — Implementation Plan

## Phase 1: Audit & Source Identification (2 tasks)

### Task 1.1: Analyze scholar_indx mapping
- Query Neo4j for narrator scholar_indx distribution
- Identify which external rijal database the indices map to
- Determine what biographical data is available from those sources

### Task 1.2: Analyze chain-based tradition inference
- For each narrator, check which tradition's hadiths they appear in via Chain->Hadith->Source paths
- Script: query narrators with their connected hadith traditions
- Output: mapping of narrator_id -> inferred tradition(s)

## Phase 2: Arabic Name Backfill (3 tasks)

### Task 2.1: Extract Arabic names from chain text
- Many narrators have Arabic names embedded in the isnad text (classical_sanad_parsed.jsonl)
- Cross-reference: narrator's English name -> find Arabic equivalent in chain raw text
- Script: `src/scripts/enrich-narrator-arabic-names.ts`

### Task 2.2: Match against external rijal datasets
- Use scholar_indx to look up Arabic names from source data files
- Check datasets/hadith-data/shia-hadith/ and other source files for Arabic narrator metadata

### Task 2.3: Batch update Neo4j
- Idempotent MERGE script that sets name_arabic WHERE currently null
- Log all changes

## Phase 3: Death Year & Birth Year Enrichment (2 tasks)

### Task 3.1: Extract temporal data from source datasets
- Parse death/birth years from any rijal metadata in existing dataset files
- Cross-reference with scholar_indx

### Task 3.2: Batch update death/birth years
- Script: SET death_year_hijri, birth_year_hijri WHERE currently null
- Validate: no death_year < birth_year

## Phase 4: Geographic Region Assignment (2 tasks)

### Task 4.1: Infer regions from known narrator data
- Classical narrators often have nisba (geographical epithet) in their name
- Parse English names for known nisbas: al-Madani, al-Kufi, al-Basri, al-Shami, al-Makki, al-Misri, etc.
- Map to regions: Medina, Kufa, Basra, Damascus, Mecca, Egypt, etc.

### Task 4.2: Batch update geographic_region
- SET geographic_region based on nisba parsing
- Validate against existing Location nodes (368 exist)

## Phase 5: Tradition Assignment & Deduplication (3 tasks)

### Task 5.1: Assign tradition from connected hadiths
- Cypher: For each narrator, find majority tradition of connected hadiths
- If narrator appears in chains from only Sunni hadiths -> tradition = 'Sunni'
- If mixed, use dominant tradition

### Task 5.2: Clean up empty/duplicate narrators
- Investigate 16,614 narrators with empty name_arabic
- Investigate "no identity" / "no Identity" duplicates (182 + 19 nodes)
- Merge true duplicates, flag unknowns

### Task 5.3: Batch update tradition property
- SET tradition WHERE currently null
- Verify: re-run tradition distribution query

## Phase 6: Verification & Metrics (1 task)

### Task 6.1: Re-run data readiness audit
- Run `npx tsx src/scripts/data-readiness-audit.ts`
- Verify all narrator fields improved
- Document final coverage in this plan
