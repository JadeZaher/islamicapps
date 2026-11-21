# Specification: Fix Hadith Data Integrity Issues

## Overview

Multiple data integrity issues cause broken filters, incorrect sort ordering, missing translations, and incorrect titles across the hadith platform. These issues stem from inconsistent source naming conventions across import scripts and the UI, string-based hadith number sorting, hadiths with zero-valued numbers producing bad titles, an unused CSV column useful for ordering, and two collections (Musnad al-Rabi and Musnad Ahmad) that are either broken or missing in the database.

## Background

The platform imports hadith data from CSV and JSONL files via three separate import scripts (`import-datasets.ts`, `import-pure-canon.ts`, `import-musnad.ts`). Each script independently defines source names, creating mismatches. The admin UI hardcodes yet another set of names in its filter dropdown. Additionally, `hadith_no` is stored as a string but sorted without integer conversion, and 31 hadiths have `hadith_no=0` producing meaningless titles.

## Functional Requirements

### FR-1: Canonical Source Name Registry
**Description:** Create a single, authoritative mapping of source names used by all import scripts, UI components, and queries. All scripts and UI must reference this registry instead of defining names locally.

**Acceptance Criteria:**
- A shared module exports the canonical name for every hadith collection
- `import-datasets.ts` source definitions use names from the registry
- `import-pure-canon.ts` `CLASSICAL_SOURCE_NAMES` map resolves to registry names
- `import-musnad.ts` `MUSNAD_SOURCE_NAME` uses the registry name
- Admin UI filter dropdown in `client.tsx` uses registry values (or dynamically queries DB)
- Running any import script after the fix uses consistent names that match DB Source nodes

**Priority:** P0 (Critical)

### FR-2: Fix Source Name Mismatches in Admin UI
**Description:** The admin hadith filter dropdown uses three source name values that do not match the database Source node names, causing those filters to return 0 results.

**Mismatches:**
| UI Value | DB Source Node Name |
|---|---|
| `Sunan Abu Dawud` | `Sunan Abi Da'ud` |
| `Jami at-Tirmidhi` | `Jami' al-Tirmidhi` |
| `Sunan an-Nasai` | `Sunan an-Nasa'i` |

**Acceptance Criteria:**
- Filtering by each of the six kutub al-sittah collections returns non-zero results
- Filter values exactly match the `name` property on the corresponding `Source` node in Neo4j
- The display label can differ from the filter value (human-readable label vs. DB key)

**Priority:** P0 (Critical)

### FR-3: Fix import-pure-canon.ts Source Name Alignment
**Description:** The `CLASSICAL_SOURCE_NAMES` mapping in `import-pure-canon.ts` uses names that diverge from the DB Source nodes created by `import-datasets.ts`, which would cause duplicate Source nodes or broken `FROM_SOURCE` relationships if run.

**Mismatches:**
| import-pure-canon.ts Name | import-datasets.ts (DB) Name |
|---|---|
| `Sahih al-Bukhari` | `Sahih Bukhari` |
| `Sunan Abi Dawud` | `Sunan Abi Da'ud` |
| `Sunan al-Nasa'i` | `Sunan an-Nasa'i` |

**Acceptance Criteria:**
- All names in `CLASSICAL_SOURCE_NAMES` match the canonical registry names
- Running `import-pure-canon.ts` does not create duplicate Source nodes
- `FROM_SOURCE` relationships connect correctly to existing Source nodes

**Priority:** P0 (Critical)

### FR-4: Fix Musnad al-Rabi Source Name Mismatch (Unicode vs ASCII)
**Description:** The `Source` node for Musnad al-Rabi is created with an ASCII name from `import-musnad.ts` (`MUSNAD_SOURCE_NAME`), but the CSV `source` column contains a Unicode transliteration. The `FROM_SOURCE` relationship links via `MUSNAD_SOURCE_NAME`, but `h.source` on the Hadith node gets the CSV value. This inconsistency breaks queries that filter by `h.source` and compare to the Source node name.

**ASCII (script):** `al-Jami' al-Sahih -- Musnad al-Imam al-Rabi' b. Habib`
**Unicode (CSV):** `al-Jaami' al-Sahih -- Musnad al-Imam al-Rabi' b. Habib` (with diacritics)

**Acceptance Criteria:**
- A single canonical name is chosen for the Musnad al-Rabi collection
- The Source node `name`, all Hadith node `source` properties, and the UI dropdown value all match
- `FROM_SOURCE` relationships are intact after re-import
- The admin UI filter for Musnad al-Rabi returns the correct count of hadiths

**Priority:** P0 (Critical)

### FR-5: Fix hadith_no String Sort Ordering
**Description:** `ORDER BY h.hadith_no` in `graph-actions.ts` performs lexicographic sort because `hadith_no` is stored as a string. This causes "10" to sort before "2", "100" before "11", etc.

**Locations:**
- `graph-actions.ts` line 245: `getAllHadiths`
- `graph-actions.ts` line 907: filtered hadith query

**Acceptance Criteria:**
- Hadiths sort in correct numerical order (1, 2, 3, ..., 10, 11, ...)
- Hadiths with non-numeric `hadith_no` values (if any) sort after numeric ones
- No runtime errors from the integer conversion for edge-case values

**Priority:** P1 (High)

### FR-6: Fix Hadiths with hadith_no=0 (Bad Titles)
**Description:** 31 hadiths have `hadith_no=0` (26 in Sahih Muslim, 5 in Sunan Abi Da'ud). Their titles are generated as `"${source} 0"` (e.g., "Sahih Muslim 0"), which is meaningless and misleading.

**Acceptance Criteria:**
- Hadiths with `hadith_no=0` are identified and flagged for review
- Title generation handles `hadith_no=0` gracefully (e.g., uses chapter info or "Introduction" suffix)
- Import script is updated to handle zero-valued hadith numbers in future imports
- Existing hadiths in DB with `hadith_no=0` have their titles corrected

**Priority:** P1 (High)

### FR-7: Import hadith_id from CSV for Deterministic Ordering
**Description:** The `hadith_id` column in `all_hadiths_clean.csv` contains a global sequential integer but is currently discarded during import. This column would provide deterministic, stable ordering independent of `hadith_no` (which can be 0 or duplicated across sources).

**Acceptance Criteria:**
- `import-datasets.ts` reads the `hadith_id` column and stores it as a property on Hadith nodes (e.g., `h.dataset_row_id`)
- The property is stored as an integer (not string)
- The property can be used as a secondary sort key
- A Neo4j index exists on the new property for query performance

**Priority:** P2 (Medium)

### FR-8: Re-import Musnad al-Rabi with Real Translations
**Description:** `datasets/musnad_hadiths.csv` now contains 853 verified English translations. The import script `import-musnad.ts` needs to be re-run to populate the database with this data, replacing any existing placeholder data.

**Acceptance Criteria:**
- Running `import-musnad.ts` imports all 853 hadiths with English translations
- `text_english` is populated (not empty) for all imported hadiths
- Existing Musnad al-Rabi data is cleanly replaced (the script already has a purge function)
- Source name uses the canonical registry name (FR-4)
- `FROM_SOURCE` relationships are intact

**Priority:** P1 (High)

### FR-9: Import Musnad Ahmad Collection
**Description:** Musnad Ahmad data exists in `datasets/hadith-data/sheikahmad/pure_canon.jsonl` but shows 0 results in the UI, suggesting `import-pure-canon.ts` was never run for this collection (or source name mismatch prevents display).

**Acceptance Criteria:**
- Musnad Ahmad hadiths are present in the database
- The source name matches the canonical registry
- Admin UI filter for "Musnad Ahmad" returns the correct hadith count
- `FROM_SOURCE` relationships link to the correct Source node

**Priority:** P1 (High)

## Non-Functional Requirements

### NFR-1: Data Migration Safety
- All data-modifying operations must be idempotent (safe to re-run)
- Import scripts use `MERGE` (not `CREATE`) to prevent duplicates
- Backup guidance documented before destructive re-imports
- Never delete data files; back up or move instead

### NFR-2: Performance
- Sorting queries must not cause full-collection scans; use appropriate Neo4j indexes
- A Neo4j index on `hadith_no` (or a new integer sort field) should support efficient ORDER BY
- Batch processing for bulk updates (500+ nodes)

### NFR-3: Consistency
- A single source of truth for all source names (the canonical registry module)
- No string literals for source names in UI components or query files -- all reference the registry

## User Stories

### US-1: Admin Filters All Collections
**As** an admin user browsing hadiths,
**I want** every source filter option to return matching results,
**So that** I can review hadiths from any collection without encountering empty results.

**Given** the admin is on the hadith management page
**When** they select "Sunan Abi Da'ud" from the source filter
**Then** the list shows hadiths from that collection (non-zero count)

### US-2: Correct Sort Order
**As** a user browsing hadiths,
**I want** hadiths sorted in correct numerical order by hadith number,
**So that** I can sequentially read through a collection without jumbled ordering.

**Given** the user views a list of hadiths from Sahih Bukhari
**When** the list is sorted by hadith number
**Then** hadith 2 appears before hadith 10, and hadith 10 appears before hadith 100

### US-3: Meaningful Titles
**As** a user viewing a hadith,
**I want** every hadith to have a meaningful title,
**So that** I can identify it at a glance without seeing nonsensical labels like "Sahih Muslim 0".

### US-4: Musnad al-Rabi Accessible
**As** a researcher,
**I want** to browse the Musnad al-Rabi collection with English translations,
**So that** I can study Ibadi hadith scholarship alongside Sunni collections.

### US-5: Musnad Ahmad Accessible
**As** a researcher,
**I want** to browse Musnad Ahmad hadiths,
**So that** I can access one of the largest classical hadith compilations.

## Technical Considerations

- **Canonical name module location:** `src/lib/constants/sources.ts` -- single file, imported by all scripts and UI components
- **Neo4j integer sort:** Use `toInteger()` in Cypher or store a separate integer property; Cypher `ORDER BY toInteger(h.hadith_no)` works but is less efficient than indexing an integer property
- **Musnad re-import:** `import-musnad.ts` already has a `purgeMusnadData()` function; use it before re-import
- **Dynamic filter dropdown:** Consider querying `MATCH (s:Source) RETURN s.name` instead of hardcoding, to automatically pick up new collections
- **DB migration for existing data:** Write a one-time Cypher script to fix source names and titles on existing nodes rather than requiring full re-import for all collections

## Out of Scope

- Changing the Neo4j schema beyond adding the `dataset_row_id` property and indexes
- Modifying hadith text content (Arabic or English)
- Adding new collections beyond Musnad Ahmad and Musnad al-Rabi
- UI redesign of the admin hadith page beyond fixing filter values
- Grading or authentication of hadiths
- Changes to the comparative/cross-cultural pipeline

## Open Questions

1. **Canonical name authority:** Should the DB names match traditional romanization standards (e.g., Library of Congress) or keep the current informal transliterations? Current plan: keep existing `import-datasets.ts` names as canonical since they are already in production DB.
2. **hadith_no=0 strategy:** Should these hadiths be assigned sequential negative IDs (to sort first as "introductions"), or should they get chapter-based titles? Recommendation: use "Introduction" suffix.
3. **Full re-import vs. migration:** For the six main collections, should we do a DB migration (update in place) or a full re-import? Recommendation: in-place migration Cypher for name fixes; re-import only for Musnad al-Rabi and Musnad Ahmad.
