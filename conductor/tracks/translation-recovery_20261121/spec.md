---
type: track-spec
title: Translation recovery
tags: [translation-recovery_20261121, planned]
resource: ./metadata.json
---

# Translation recovery

Research: [../../../.omc/research/pg-refactor/07-data-gaps.md](../../../.omc/research/pg-refactor/07-data-gaps.md) section (c), gap 2 of
section (a).
Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) sections 5.3 and 5.3.1 (`translations`,
`translation_candidates`), 11 (public English rules).

Folds in: archived
[translate_classical_collections_20260418](../../archive/2026-11-21-neo4j-era/tracks/translate_classical_collections_20260418/spec.md)
(the 29,915 classical recoveries with no model identity are likely its
output; reconstruct their provenance) and the refusal and OCR parts of
[text_cleanup_embedding_prep_20260425](../../archive/2026-11-21-neo4j-era/tracks/text_cleanup_embedding_prep_20260425/spec.md).

## Goal

Every English text shown publicly is either reviewed or provider English
under a recorded per-work policy.

## Scope

Provenance-first states (Thaqalayn, K6, classical recoveries); leakage triage
from J7 into a new candidate file, never in place; the review queue from J7b,
stratified by risk; overrides authored one by one, bound by hash; the 853
missing K6 rows; dispositions for source defects. Resume r8 only after prompt
and validator regressions for `k6:17921` and `k6:18013`, within the $12
guardrail, with a paid-pilot approval.

## Out of scope

Bulk acceptance of machine output; any public display of
`translation_candidates`.

## Acceptance checks

- Each public English row has `human_verified`, `source_verified` or a
  recorded `english_policy` for its work.
- Leakage bucket counts from J7 reconciled with fixes made.

## Open owner questions (section 14)

Q3 (machine English never public), Q5 (provider English per work), Q2
(rights per work).
