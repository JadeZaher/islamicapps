# Narrator Biographical Enrichment

## Problem

The data readiness audit (2026-04-25) found critical gaps in Narrator node properties:

| Field | Populated | Missing | Coverage |
|---|---|---|---|
| name_arabic | 7,733 | 16,614 | 31.8% |
| death_year_hijri | 3,845 | 20,502 | 15.8% |
| geographic_region | 14 | 24,333 | 0.1% |
| birth_year_hijri | 386 | 23,961 | 1.6% |
| tradition | 19 | 24,328 | 0.08% |

Additionally, 16,614 narrators have empty Arabic names and ~200 narrators appear as duplicates ("no identity", "no Identity").

These gaps block:
- **GDS community detection**: geographic_region is needed for contextual interpretation
- **Temporal chain validation**: death_year_hijri required to check if student could have met teacher
- **Arabic fuzzy matching**: name_arabic needed for cross-referencing with external rijal databases
- **Cross-tradition analysis**: tradition assignment required to partition graph by madhab

## Goal

Enrich Narrator nodes from the existing `scholar_indx` foreign key (which maps to external rijal databases) and from chain context (tradition of source hadiths). Target coverage:
- name_arabic: >80%
- death_year_hijri: >50%
- geographic_region: >40%
- tradition: >95%

## Constraints

- Read-only on existing narrator data; only SET new properties, never overwrite existing non-null values
- Back up current narrator state before any writes
- All enrichment scripts must be idempotent and resumable
- Log all changes for audit trail

## Success Criteria

- Re-run data-readiness-audit.ts and see all narrator fields pass (>50% coverage)
- No new orphan nodes created
- Tradition assigned to >95% of narrators based on which Source/Hadith they connect to
