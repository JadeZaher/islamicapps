---
type: implementation-plan
title: Data-gap diagnostics (jobs J1 to J9) plan
tags: [data-gap-diagnostics_20261121, in_progress]
resource: ./spec.md
---

# Implementation plan: Data-gap diagnostics (jobs J1 to J9)

Track: `data-gap-diagnostics_20261121`. Spec: [./spec.md](./spec.md). Design steps: 3.

## Phase 0 — Harness

- [ ] Shared header writer (input hashes, git HEAD) and path checks.

Done when: one job can be added without repeating safety code.

## Phase 1 — Independent jobs

- [ ] J1 surface census.
- [ ] J8 lexicon defect report and narrator priority.
- [ ] J6a Imami grading parse; J6b Tirmidhi in-text rulings; J6c Pure Canon label audit.
- [ ] J7 translation leakage triage; J7b translation review packets.

Done when: these outputs exist (07 section g).

## Phase 2 — Jobs that need J1

- [ ] J2 Tier-0 dry run.
- [ ] J3 candidate ranking (`status: candidate_only`).
- [ ] J5 extractor-noise samples.

Done when: J2, J3 and J5 outputs exist.

## Phase 3 — Network fetch

- [ ] J4 Imami rijal acquisition with `.meta.md` per file.

Done when: files are fetched and hashed; no parsing.

## Phase 4 — Owner packet

- [ ] J9 per-row status projection and `summary.json`.
- [ ] One-page owner summary linking J9 to section 14 questions.

Done when: section 12 step 3 done-when holds.
