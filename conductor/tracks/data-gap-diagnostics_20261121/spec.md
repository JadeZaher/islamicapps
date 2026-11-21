---
type: track-spec
title: Data-gap diagnostics (jobs J1 to J9)
tags: [data-gap-diagnostics_20261121, in_progress]
resource: ./metadata.json
---

# Data-gap diagnostics

Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) section 12 step 3.
Research: [../../../.omc/research/pg-refactor/07-data-gaps.md](../../../.omc/research/pg-refactor/07-data-gaps.md) section (g) (job table,
common inputs, rules), section (b.0) (surface tables), section (f) (facets
for J9).

## Goal

Run jobs J1 to J9 (including J6a, J6b, J6c and J7b). Their outputs exist, and
J9 gives the owner the per-row picture.

## Scope

- Each job reads the canonical inputs and writes only new files under
  `datasets/hadith-data/diagnostics/<job>/`; J4 writes under
  `datasets/narrator-data/imami-rijal/` (fetch and hash only).
- Every output header records both input SHA-256s and the git HEAD.
- Reuse the path checks of `audit_narrator_resolution.py` (no symlinks, no
  hardlinks, no input and output collisions).

## Out of scope

Any resolver policy change, override, evidence claim, paid API call or r8
resume. Those belong to the four curation tracks.

## Acceptance checks

- Every job's output file exists with its header.
- J1 reports 58,028 distinct normalized surfaces, or the difference is explained.
- Deterministic jobs re-run byte-identically.
- J9 `summary.json` gives counts per facet and what would publish under the
  section (f) model.

## Open owner questions (section 14)

None block the jobs. J9 is the evidence for Q1, Q3, Q5, Q11 and Q13.
