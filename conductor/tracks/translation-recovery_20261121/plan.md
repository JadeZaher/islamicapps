---
type: implementation-plan
title: Translation recovery plan
tags: [translation-recovery_20261121, planned]
resource: ./spec.md
---

# Implementation plan: Translation recovery

Track: `translation-recovery_20261121`. Spec: [./spec.md](./spec.md). Design steps: data, after 3.

## Phase 0 — Evidence

- [ ] Read J7 and J7b outputs.

Done when: bucket sizes and the review queue are known.

## Phase 1 — Provenance

- [ ] Owner sets `english_policy` per cleared work (Q5).
- [ ] Reconstruct provenance for the 29,915 classical recoveries, or label them unknown.

Done when: every row has a provenance state.

## Phase 2 — Leakage and defects

- [ ] Rule-based fixes for names-only leakage into a new candidate file.
- [ ] Dispositions for the source defects (07 section c.6).

Done when: each J7 bucket has a plan or a fix.

## Phase 3 — Review

- [ ] Stratified review; hash-bound overrides.
- [ ] r8 resume only after the regressions and a paid-pilot approval.

Done when: reviewed counts are tracked per work.
