# Hadith Grade Normalization — Implementation Plan

## Phase 1: Grade Taxonomy Design (2 tasks)

### Task 1.1: Export and analyze all grade variants
- Query: `MATCH (h:Hadith) RETURN h.display_grade, h.tradition, count(*) ORDER BY count(*) DESC`
- Group by tradition (Sunni, Shia Imami, Ibadi, Zaydi)
- Identify OCR/spacing duplicates (e.g., `ضعیف` vs `ضعيف`)

### Task 1.2: Design canonical grade taxonomy
- Create grade mapping file: `src/lib/constants/grade-taxonomy.ts`
- Sunni canonical: sahih, hasan, da'if, mawdu', mursal, ungraded
- Shia canonical: sahih, hasan, muwaththaq, da'if, majhul, mursal, mu'tabar, mukhtalaf, ungraded
- Ibadi canonical: thabit (maps to sahih), ungraded
- Map compound grades to primary grade (e.g., `حسن كالصحيح` -> sahih)
- Document each mapping decision with scholarly justification

## Phase 2: Mapping Script (2 tasks)

### Task 2.1: Build grade normalizer
- Script: `src/scripts/normalize-grades.ts`
- Input: display_grade string + tradition
- Output: { grade_canonical, grade_detail }
- Handle: Arabic spacing normalization, OCR char fixes, compound grade parsing

### Task 2.2: Dry-run and review
- Run normalizer in dry-run mode
- Output CSV: hadith_id, display_grade, tradition, grade_canonical, grade_detail
- Review unmapped grades (should be <5% of total)

## Phase 3: Apply Normalization (2 tasks)

### Task 3.1: Batch update Neo4j
- SET h.grade_canonical and h.grade_detail for all hadiths
- Batched UNWIND for performance
- Create index on grade_canonical

### Task 3.2: Update schema.ts
- Add index for `Hadith.grade_canonical`
- Add index for `Hadith.grade_detail`

## Phase 4: Verification (1 task)

### Task 4.1: Validate grade distribution
- Query grade_canonical distribution per tradition
- Verify: <15 canonical values, no NULLs
- Verify: grade_detail cleaned of OCR variants
- Update data-readiness-audit.ts to check new fields
