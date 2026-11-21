---
type: track-spec
title: Evidence and biography curation
tags: [evidence-and-biography-curation_20261121, planned]
resource: ./metadata.json
---

# Evidence and biography curation

Research: [../../../.omc/research/pg-refactor/07-data-gaps.md](../../../.omc/research/pg-refactor/07-data-gaps.md) section (e), gaps 3, 7
and 8 of section (a).
Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) sections 5.7 to 5.9 (biography, evidence, history), 9.3
(`setBioStatus`), 11 (hidden until cited).

Folds in: the death-year and region parts of archived
[narrator_enrichment_20260425](../../archive/2026-11-21-neo4j-era/tracks/narrator_enrichment_20260425/spec.md)
(now cited claims, not lexicon backfill) and the commentary part of
[scholarly_metadata_layer_20260425](../../archive/2026-11-21-neo4j-era/tracks/scholarly_metadata_layer_20260425/spec.md).

## Goal

Every biographical, historical and source-work claim shown is cited to an
edition and page.

## Scope

- Quick win: about 32 source-work compiler claims (closes gap 7).
- The 21 Phase-0 bios get edition and page locators, or stay hidden.
- Claim extraction from one cited work per tradition, `candidate_only` until
  a reviewer promotes it; `biographical_assertions` and
  `temporal_assertions` ship with the first claims.
- History: seed events hidden until cited; source the `Egypt` mapping;
  `epochs` ships with its first writer.

## Out of scope

Showing lexicon dates as claims; filling Ibadi and Zaydi gaps without sources.

## Acceptance checks

- J8 defects never render.
- Every published claim has a live, reviewed citation.

## Open owner questions (section 14)

Q4 (lexicon dates), Q9 (Phase-0 verdict tradition), Q10 (commentary
publication), Q12 (off-machine archive of curation).
