---
type: implementation-plan
title: Query port and action switch plan
tags: [query-port-and-action-switch_20261121, planned]
resource: ./spec.md
---

# Implementation plan: Query port and action switch

Track: `query-port-and-action-switch_20261121`. Spec: [./spec.md](./spec.md). Design steps: 6.

## Phase 0 — Scaffolding

- [x] `sql-helpers.ts`, `mappers.ts` (section 3.2 rule 3), `health.ts` and `/api/health`.
- [x] ESLint import restriction for `src/app/**`.

Done when: lint enforces the layering and the health route answers.

## Phase 1 — Hadith and isnad

- [x] `hadith.ts`, `isnad.ts`, search (section 7); switch their actions.

Done when: hadith detail and search run on Postgres.

## Phase 2 — Narrator and assessment

- [x] `narrator.ts`, `assessment.ts`; `searchNarratorsTypeahead`; switch actions.

Done when: narrator detail and lists run on Postgres.

## Phase 3 — History, location, commentary

- [x] Query modules and actions; explicit update allowlists (section 3.2 rule 5).

Done when: the admin CRUD flows for these areas run on Postgres.

## Phase 4 — Comparative

- [ ] `comparative.ts`, `research.ts`, `commit-parallel.ts`; research route rewrite.

Done when: comparative pages and the research route run on Postgres.

## Phase 5 — Curation actions

- [x] Every section 9.3 action with `requireCurator()`, audit row and load guard.

Done when: each action is driven by a flow test.

## Phase 6 — UI co-changes (after ui-polish lanes B, C, D close)

- [x] Section 9.4 contract changes in the named UI files.

Done when: no UI reads a field the mapper no longer provides.

## Phase 7 — Tests and end to end

- [ ] Port the release-gate and parity tests; replace the source-text test.
- [ ] Run the end-to-end flows with Neo4j variables unset.

Done when: section 12 step 6 done-when holds.
