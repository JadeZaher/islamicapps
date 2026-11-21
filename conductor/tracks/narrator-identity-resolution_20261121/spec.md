---
type: track-spec
title: Narrator identity resolution
tags: [narrator-identity-resolution_20261121, planned]
resource: ./metadata.json
---

# Narrator identity resolution

Research: [../../../.omc/research/pg-refactor/07-data-gaps.md](../../../.omc/research/pg-refactor/07-data-gaps.md) section (b) (tiers 0 to
2, expected coverage), gap 1 of section (a).
Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) sections 5.4 and 5.5 (narrators, mentions, surface
decisions, same-as), 9.3 (`decideSurfaceUnit`), 11 (per-link publication).

Folds in: phase 4 of archived
[uniform_isnad_extraction_20260609](../../archive/2026-11-21-neo4j-era/tracks/uniform_isnad_extraction_20260609/plan.md)
(unique-kunya alias indexing becomes Tier-0 rules T0-b to T0-d), and the
deduplication and tradition parts of
[narrator_enrichment_20260425](../../archive/2026-11-21-neo4j-era/tracks/narrator_enrichment_20260425/spec.md).

## Goal

Raise verified chain links measurably, without ever inventing identity.

## Scope

- Tier 0: measure with J2 before any policy change; amend the exact-only
  resolver policy in `datasets/hadith-data/AGENTS.md` only on that evidence
  and owner sign-off.
- Tier 1: candidate ranking (J3) loaded as `resolution_review_units`
  (candidate stream; the table ships with this first writer).
- Tier 2: human decisions through `decideSurfaceUnit`, attributed to a named
  curator.
- Imami authority: J4 rijal texts parsed into an authority only after license
  review; cross-authority identity only through `narrator_same_as`.

## Out of scope

LLM branch reconciliation (parked, see `conductor/tracks.md`); biography
claims (evidence-and-biography-curation).

## Acceptance checks

- J2 delta recorded before and after each Tier-0 rule.
- Coverage curve measured against 07 section (b.4).
- No mention is linked without `exact_registry`, a human decision or a
  verified derived relation.

## Open owner questions (section 14)

Q1 (legacy `chain_indx`), Q11 (mention-exact transmissions), Q14 (named
curators); section 15: the database is the system of record for decisions.
