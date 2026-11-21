---
type: implementation-plan
title: Bundle to Postgres loader plan
tags: [bundle-to-postgres-loader_20261121, planned]
resource: ./spec.md
---

# Implementation plan: Bundle to Postgres loader

Track: `bundle-to-postgres-loader_20261121`. Spec: [./spec.md](./spec.md). Design steps: 5.

## Phase 0 — Preconditions

- [ ] Confirm a validated bundle exists with `import_ready: true` (the archived consolidation plan never ticked phases 1 and 2).
- [ ] Read `io.ts` lines 117 to 141 and the unified CSV header (section 15 assumptions).

Done when: the input bundle and its hashes are recorded.

## Phase 1 — Projection

- [ ] `export_postgres.py`: canonical and candidate streams, manifest bound to the bundle (section 4.4).
- [ ] Per-mention exact resolution, review-unit IDs, normalized search text.
- [ ] Table-driven tests for the projection rules.

Done when: two runs are byte-identical.

## Phase 2 — COPY and merge

- [ ] `src/db/load/copy.ts` and `merge.ts` (section 4.3); advisory lock shared with the migrator.
- [ ] `src/scripts/db/load-bundle.ts`.

Done when: a load completes and a reload changes zero rows.

## Phase 3 — Verify and heavy indexes

- [ ] `src/db/load/verify.ts` with every section 11.4 check; `src/scripts/db/verify.ts`.
- [ ] `src/db/ops/indexes-heavy.sql`; run it in a load window.

Done when: all section 11.4 checks pass.

## Phase 4 — Measure

- [ ] Record database, table and index sizes; compare with section 2.8.

Done when: section 12 step 5 done-when holds.

## Phase 5 — Integrated verification

- [ ] Python hadith suite and the new loader tests, once.
