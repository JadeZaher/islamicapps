# Implementation Plan: Fix Hadith Data Integrity Issues

## Overview

Eight verified issues affecting data integrity across the hadith platform. The plan is organized into four phases:

1. **Phase 1: Canonical Source Registry** -- Create the single source of truth, fix all name mismatches in code
2. **Phase 2: Sort Ordering and Title Fixes** -- Fix string sort, bad titles, import `hadith_id`
3. **Phase 3: DB Migration** -- Apply fixes to existing data in Neo4j without full re-import
4. **Phase 4: Collection Imports** -- Re-import Musnad al-Rabi, import Musnad Ahmad

Dependencies: Phase 3 depends on Phase 1. Phase 4 depends on Phases 1 and 3.

---

## Phase 1: Canonical Source Name Registry and Code Fixes

Goal: Establish a single source of truth for all source names and update every file that references them.

Tasks:

- [x] Task 1.1: Create canonical source registry module
  - Create `src/lib/constants/sources.ts`
  - Export a `CANONICAL_SOURCES` object mapping collection slugs to their canonical names, Arabic names, and display labels
  - Canonical names should match the existing DB Source node names from `import-datasets.ts` (e.g., `Sahih Bukhari`, `Sunan Abi Da'ud`, `Jami' al-Tirmidhi`, `Sunan an-Nasa'i`, `Sunan Ibn Majah`, `Sahih Muslim`)
  - Add entries for `Musnad Ahmad` and the Musnad al-Rabi collection (choose canonical ASCII name)
  - Export helper: `getCanonicalName(slug: string): string`
  - Export a `SOURCE_DISPLAY_LABELS` map for UI-friendly labels if they differ from DB names

- [x] Task 1.2: Update `import-datasets.ts` to use the registry
  - Replace the inline `sources` array (lines 231-280) to import names from `src/lib/constants/sources.ts`
  - Verify the generated Source node names match the registry exactly
  - Ensure `FROM_SOURCE` relationship creation (line 593) uses registry-consistent names

- [x] Task 1.3: Update `import-pure-canon.ts` to use the registry
  - Replace `CLASSICAL_SOURCE_NAMES` map (lines 40-51) to derive values from the registry
  - Fix the three mismatched names: `Sahih al-Bukhari` -> `Sahih Bukhari`, `Sunan Abi Dawud` -> `Sunan Abi Da'ud`, `Sunan al-Nasa'i` -> `Sunan an-Nasa'i`
  - Add mapping for `Musnad Ahmad` slug `ahmad`

- [x] Task 1.4: Update `import-musnad.ts` to use the registry
  - Replace `MUSNAD_SOURCE_NAME` constant (line 31) with the canonical name from the registry
  - Update the hadith creation query (line 447): ensure `h.source` is set to the canonical name, not `row.source` from CSV
  - The title template (line 445) should use a short display name, not the full Source node name

- [x] Task 1.5: Update admin UI filter dropdown
  - In `src/app/admin/hadith/client.tsx`, replace hardcoded source filter options (lines 132-142) with values from the canonical registry
  - Alternatively, make the dropdown dynamic by querying `MATCH (s:Source) RETURN s.name ORDER BY s.name` via a server action
  - Ensure filter `value` matches DB Source node `name` exactly
  - Display `label` can be human-friendly (e.g., "Sunan Abu Dawud" as label, `Sunan Abi Da'ud` as value)

- [x] Task 1.6: Search for any other hardcoded source name references
  - Grep the codebase for all six original source names and any variants
  - Update any remaining references to use the registry
  - Check: `graph-actions.ts`, `page.tsx` files, any other admin pages

- [x] Verification: Phase 1 completeness check [checkpoint marker]
  - Confirm no hardcoded source name strings remain outside the registry module
  - Confirm `import-datasets.ts`, `import-pure-canon.ts`, and `import-musnad.ts` all import from the registry
  - Confirm admin UI dropdown values match DB Source node names
  - Run TypeScript compilation (`npx tsc --noEmit`) to verify no type errors

---

## Phase 2: Sort Ordering, Titles, and Dataset Row ID

Goal: Fix lexicographic sort, handle hadith_no=0 titles, and import the `hadith_id` column.

Tasks:

- [x] Task 2.1: Fix ORDER BY in graph-actions.ts
  - Line 245 (`getAllHadiths`): change `ORDER BY h.hadith_no` to `ORDER BY toInteger(h.hadith_no)`
  - Line 907 (filtered query): change `ORDER BY h.hadith_no` to `ORDER BY toInteger(h.hadith_no)`
  - Grep for any other `ORDER BY h.hadith_no` across the codebase and fix them
  - Handle edge case: hadiths with non-numeric `hadith_no` (use `CASE WHEN h.hadith_no =~ '^[0-9]+$' THEN toInteger(h.hadith_no) ELSE 999999 END`)

- [x] Task 2.2: Fix title generation for hadith_no=0
  - In `import-datasets.ts` line 523: update title template to handle `hadith_no === '0'` or empty
  - Proposed logic: if `hadith_no` is `'0'` or empty, use `"${source} - ${chapter || 'Introduction'}"` instead of `"${source} 0"`
  - Apply same logic in `import-musnad.ts` title generation (line 445) for consistency

- [x] Task 2.3: Import `hadith_id` column from CSV
  - In `import-datasets.ts`, read the `hadith_id` column from each CSV row
  - Store as `h.dataset_row_id` (integer) on the Hadith node
  - This provides a global sequential ordering key
  - Add to the MERGE/SET clause in the hadith creation query

- [x] Task 2.4: Add Neo4j index for sort performance
  - In `src/lib/db/schema.ts`, add index: `CREATE INDEX hadith_dataset_row_id IF NOT EXISTS FOR (h:Hadith) ON (h.dataset_row_id)`
  - Consider also adding: `CREATE INDEX hadith_hadith_no IF NOT EXISTS FOR (h:Hadith) ON (h.hadith_no)` if not already present
  - Run `npm run db:init` to apply

- [x] Verification: Phase 2 correctness check [checkpoint marker]
  - Confirm `ORDER BY` uses integer conversion in all query locations
  - Confirm title template handles `hadith_no=0` gracefully
  - Confirm `hadith_id` column is mapped in `import-datasets.ts`
  - Run TypeScript compilation

---

## Phase 3: Database Migration (In-Place Fixes)

Goal: Fix existing data in Neo4j without requiring a full re-import of the six main collections.

Tasks:

- [x] Task 3.1: Create migration script `src/scripts/migrate-source-names.ts`
  - Write a script that runs Cypher queries to fix source name inconsistencies on existing Hadith nodes
  - Fix `h.source` property on any Hadith nodes that use non-canonical names
  - Fix Source node names if any duplicates were created by prior `import-pure-canon.ts` runs
  - Merge duplicate Source nodes if found (transfer all relationships before deleting the duplicate)
  - Script must be idempotent

- [x] Task 3.2: Fix titles for hadith_no=0 hadiths in DB
  - Cypher query to find all hadiths where `h.hadith_no = '0'`
  - Update their titles using chapter info: `SET h.title = h.source + ' - ' + COALESCE(h.chapter, 'Introduction')`
  - Log the count of affected hadiths per source

- [x] Task 3.3: Backfill dataset_row_id on existing hadiths
  - Write a migration that reads `all_hadiths_clean.csv`, matches each row to existing Hadith nodes by `h.source` + `h.hadith_no` + `h.chapter_no` (composite key), and sets `h.dataset_row_id`
  - Handle the 31 zero-numbered hadiths carefully (may need text matching as fallback)
  - Log match rate to verify data quality

- [x] Task 3.4: Fix Musnad al-Rabi source name in DB
  - Update all Hadith nodes with the Unicode source name to use the canonical name
  - Update the Source node name if it exists with the wrong name
  - Verify `FROM_SOURCE` relationships are intact after the rename
  - Cypher: `MATCH (h:Hadith) WHERE h.source CONTAINS 'Musnad' AND h.source CONTAINS 'Rabi' SET h.source = $canonicalName`

- [x] Verification: Phase 3 migration validation [checkpoint marker]
  - Run: `MATCH (s:Source) RETURN s.name, count{(h:Hadith)-[:FROM_SOURCE]->(s)} AS count ORDER BY s.name` -- verify all sources have expected counts
  - Run: `MATCH (h:Hadith) WHERE h.hadith_no = '0' RETURN h.title LIMIT 10` -- verify titles are fixed
  - Run: `MATCH (h:Hadith) WHERE h.dataset_row_id IS NOT NULL RETURN count(h)` -- verify backfill count
  - Run: `MATCH (h:Hadith) RETURN h.source, count(h) ORDER BY h.source` -- verify no orphaned source names

---

## Phase 4: Collection Imports

Goal: Re-import Musnad al-Rabi with real translations and import Musnad Ahmad.

Tasks:

- [x] Task 4.1: Re-import Musnad al-Rabi
  - Run the purge function in `import-musnad.ts` to clean existing Musnad data
  - Run the import with the updated script (from Phase 1 Task 1.4) using `datasets/musnad_hadiths.csv`
  - Verify all 853 hadiths are imported with English translations
  - Verify `FROM_SOURCE` relationships point to the correct Source node
  - Verify `text_english` is populated: `MATCH (h:Hadith) WHERE h.source = $musnadName AND h.text_english = '' RETURN count(h)` should return 0

- [ ] Task 4.2: ~~Investigate and import Musnad Ahmad~~ — MOVED to separate track `import_musnad_ahmad_20260418`

- [x] Task 4.3: Update admin UI to include all collections
  - Verify the admin dropdown includes entries for Musnad Ahmad and Musnad al-Rabi
  - If Task 1.5 made the dropdown dynamic, verify these new collections appear automatically
  - If static, add entries from the canonical registry

- [ ] Verification: Phase 4 final validation [checkpoint marker]
  - Admin UI: filter by Musnad al-Rabi shows ~853 results with English text
  - Admin UI: filter by Musnad Ahmad shows non-zero results
  - Admin UI: all source filters return non-zero results
  - Sort order is correct (hadith 1, 2, 3, ... not 1, 10, 100, ...)
  - No hadith titles contain "... 0"
  - `MATCH (s:Source) RETURN s.name, count{(h:Hadith)-[:FROM_SOURCE]->(s)} ORDER BY s.name` shows all sources with correct counts

---

## Summary of Files Modified

| File | Changes |
|---|---|
| `src/lib/constants/sources.ts` | NEW -- canonical source name registry |
| `src/scripts/import-datasets.ts` | Use registry, fix title for hadith_no=0, import hadith_id |
| `src/scripts/import-pure-canon.ts` | Use registry names instead of local constants |
| `src/scripts/import-musnad.ts` | Use registry name, fix h.source assignment |
| `src/scripts/migrate-source-names.ts` | NEW -- one-time DB migration script |
| `src/app/actions/graph-actions.ts` | Fix ORDER BY to use integer conversion |
| `src/app/admin/hadith/client.tsx` | Fix filter dropdown values |
| `src/lib/db/schema.ts` | Add index for dataset_row_id |

## Risk Notes

- **Musnad Ahmad size:** The `pure_canon.jsonl` file may contain a large number of hadiths (Musnad Ahmad has ~27,000+). Import may take time; use batch processing.
- **Composite key matching for backfill:** Matching CSV rows to existing DB nodes by source+hadith_no+chapter_no may not be 100% unique. The migration script should log unmatched/ambiguous rows.
- **import-pure-canon.ts scope:** This script may import other collections beyond Musnad Ahmad. Review its file discovery logic before running to avoid unintended imports.
