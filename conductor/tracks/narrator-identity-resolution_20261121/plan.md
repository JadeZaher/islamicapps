---
type: implementation-plan
title: Narrator identity resolution plan
tags: [narrator-identity-resolution_20261121, planned]
resource: ./spec.md
---

# Implementation plan: Narrator identity resolution

Track: `narrator-identity-resolution_20261121`. Spec: [./spec.md](./spec.md). Design steps: data, after 3.

## Phase 0 — Evidence

- [ ] Read J1, J2, J3 outputs from data-gap-diagnostics.

Done when: the Tier-0 delta and review-queue size are known.

## Phase 1 — Tier 0

- [ ] Owner sign-off on the policy amendment, citing J2.
- [ ] Implement T0-b to T0-d in the resolver with tests (including one ambiguous kunya that must not resolve).

Done when: the measured delta matches J2.

## Phase 2 — Tier 1 candidates

- [ ] Load J3 units as `resolution_review_units`.

Done when: reviewers can see ranked units in reviewer mode.

## Phase 3 — Tier 2 decisions

- [ ] Review the top units; decisions replay on reload.

Done when: decisions survive a reload and are visible as links.

## Phase 4 — Imami authority

- [ ] License review for the J4 texts; then authority parsing and `narrator_same_as`.

Done when: Imami surfaces have an authority to resolve against, or the gap is documented.
