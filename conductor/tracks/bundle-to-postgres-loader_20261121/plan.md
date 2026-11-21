---
type: implementation-plan
title: Bundle to Postgres loader plan
tags: [bundle-to-postgres-loader_20261121, in-progress]
resource: ./spec.md
---

# Implementation plan: Bundle to Postgres loader

Track: `bundle-to-postgres-loader_20261121`. Spec: [./spec.md](./spec.md). Design steps: 5. Log: [./log.md](./log.md).

Paths differ from the hypothesis partition: the projection lives in `datasets/hadith-data/pg_export/` (new
directory, orchestrator brief), the CLI in `src/db/load/load-bundle.ts` (`npm run db:load`), the checks in
`src/db/load/verify-data.ts` with `verify-data-cli.ts`. No `src/scripts/db/` files were needed.

## Phase 0 — Preconditions

- [x] Confirm a validated bundle exists with `import_ready: true`: a fresh one was exported to
  `development/pg-load-2026-11-21/bundle` (`c4e5e12e…`, 12 gates pass).
- [x] Read `io.ts` lines 117 to 141 and the unified CSV header (section 15 assumptions). Finding: `io.ts` reads
  `name_english`, `name_arabic`, `bio`, `tabaqah`, `geographic_region`, which `all_rawis.csv` does not have.

Done when: the input bundle and its hashes are recorded. **Done** (log.md).

## Phase 1 — Projection

- [x] `export_postgres.py`: canonical and candidate streams, manifest bound to the bundle (section 4.4).
- [x] Per-mention exact resolution, review-unit IDs, normalized search text.
- [x] Table-driven tests for the projection rules (`pg_export/test_export_postgres.py`, 14 tests).

Done when: two runs are byte-identical. **Done** (`projection.sha256` = `projection-repeat.sha256`).

## Phase 2 — COPY and merge

- [x] `src/db/load/copy.ts` and `merge.ts` (section 4.3); advisory lock shared with the migrator.
- [x] `src/db/load/load-bundle.ts` (`npm run db:load -- --bundle <projection>`).

Done when: a load completes and a reload changes zero rows. **Done** (load-1: 1,033,812 rows; load-2: 0).

## Phase 3 — Verify and heavy indexes

- [x] `src/db/load/verify-data.ts` with every section 11.4 check; on demand via `verify-data-cli.ts` (exit 1 on failure).
- [x] `src/db/ops/indexes-heavy.sql` run in a load window (`run-heavy-indexes.ts`): 47 MB, valid.

Done when: all section 11.4 checks pass. **Done** (21 in-load, 20 standalone).

## Phase 4 — Measure

- [x] Record database, table and index sizes; compare with section 2.8 (log.md).

Done when: section 12 step 5 done-when holds. **Done**: database 1,314 MB against a 50,000 MB volume.

## Phase 5 — Integrated verification

- [x] Python projection tests and bundle tests, the loader flow test, `tsc`, `db:verify`, once.

## Open (not in this track's lane)

- [ ] Rendering `source_index` links with a label (owner Q1) needs the verified-link predicate changed in
  `drizzle/core/0003_views.sql` and `0004_functions.sql` (schema lane).
- [ ] Decision replay / `apply_decision`; the loader refuses while live decisions exist.
- [ ] `translation_candidates` table (not migrated); the candidate CSV is produced but not loaded.
- [ ] Curation dump before load (`pg_dump` 18) for databases holding curation rows.
