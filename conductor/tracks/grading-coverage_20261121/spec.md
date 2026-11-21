---
type: track-spec
title: Grading coverage
tags: [grading-coverage_20261121, planned]
resource: ./metadata.json
---

# Grading coverage

Research: [../../../.omc/research/pg-refactor/07-data-gaps.md](../../../.omc/research/pg-refactor/07-data-gaps.md) section (d), gap 4 of
section (a).
Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) section 5.6 (assessments), section 4.4 (grades the
projection adds), section 9.4 (`assessments` contract).

Folds in: archived
[grade_normalization_20260425](../../archive/2026-11-21-neo4j-era/tracks/grade_normalization_20260425/spec.md)
(`grade_canonical` in the assessment contract replaces the two-tier scalar),
[scholarly_metadata_layer_20260425](../../archive/2026-11-21-neo4j-era/tracks/scholarly_metadata_layer_20260425/spec.md)
(ScholarVerdict becomes tradition-scoped `narrator_assessments`), and Wave 1
of [data_acquisition_20260521](../../archive/2026-11-21-neo4j-era/tracks/data_acquisition_20260521/spec.md) (K6
grades, blocked on sunnah.com rights).

## Goal

Every grade shown is cited and tradition-scoped; placeholders and collection
labels are never shown as grades.

## Scope

No placeholder assessment rows; the Sunni `ثابت` label reclassified as
`collection_label` once J6c confirms; the 14,902 Imami cited gradings as
structured, cited assessments (J6a); Tirmidhi in-text rulings as
`compiler_statement` after review (J6b); Bukhari and Muslim as
`compiler_criterion`; Ibadi and Zaydi show "no assessment recorded".

## Out of scope

Importing a grade across traditions; scraping sunnah.com before rights clear.

## Acceptance checks

- `collection_label` rows never render as a grade.
- Imami parse failures from J6a are listed, not silently dropped.

## Open owner questions (section 14)

Q9 (tradition of the Phase-0 verdicts), Q2 (rights, including sunnah.com
grades).
