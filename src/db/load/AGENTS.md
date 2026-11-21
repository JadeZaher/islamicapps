# src/db/load — bundle-to-Postgres loader

Design: `docs/architecture/data-architecture.md` §4.3 (reload), §4.4 (projection), §11.4 (gates), §12 step 5.
Track: `conductor/tracks/bundle-to-postgres-loader_20261121/`. Producer: `datasets/hadith-data/pg_export/`.

## Files

| File | What |
| --- | --- |
| `tables.ts` | The load contract: 20 pipeline tables in merge (FK) order, key columns, loader-derived columns |
| `catalog.ts` | Reads `information_schema` and classifies each column (`csv`, `bookkeeping`, `generated`, `loader_derived`) |
| `dump-catalog.ts` | Writes that classification as JSON for `export_postgres.py --catalog` |
| `manifest.ts` | Re-checks the projection manifest (file hashes, headers, content hash, source bundle `import_ready`, input hash) |
| `copy.ts` | `COPY ... FROM STDIN (format csv, header match)` into `UNLOGGED load_<table>` |
| `merge.ts` | Guarded upsert by stable id, anti-join retirement, derived mention columns |
| `verify-data.ts` | Section 11.4 data invariants; `verify-data-cli.ts` runs them on demand and exits 1 on failure |
| `load.ts` | The orchestrator; `load-bundle.ts` is the `npm run db:load` CLI |
| `run-heavy-indexes.ts` | Executes `src/db/ops/indexes-heavy.sql` outside a transaction and prints the index size |
| `__tests__/load-flow.test.ts` | Flow test: a real four-tradition slice into a throwaway schema (`load_test_<hex>`): load, zero-row reload, a cross-tradition correspondence pair bound to both hashes, then a second slice that retires one report and changes another (one updated row). A missing projection fails the test; it never skips |

## Order of a load (load.ts)

1. Verify the projection manifest (refuses on any hash, header or bundle mismatch).
2. One session, `max 1`, no idle or lifetime recycling, so the session-level `pg_advisory_lock(DATA_WRITE_LOCK_KEY)`
   (shared with the migrator) holds for the whole load.
3. Header check against the live catalog: CSV columns must equal, as a set, the columns classified `csv`.
4. `dataset_versions` row: `new` (insert `loading`), `resume` (an earlier attempt of the same content), or `reload`
   (already current and complete: the load must change zero rows or it rolls back).
5. COPY every table into staging, outside the transaction; staged count must equal the manifest row count.
6. One transaction: refuse if live `narrator_surface_decisions` exist (replay is not implemented); merge each table;
   `refresh_publication_facets` over every hadith; flip `is_current`; `refresh_network()` (only when rows changed);
   section 11.4 checks; mark `complete` with counts. Any failure rolls back and marks the version `failed`.
7. Drop staging, `vacuum (analyze)` changed tables, release the lock.

## Decisions

- **The version id is the projection content hash.** Loading identical content twice is therefore a `reload` of the
  same row, which is how idempotence is proven: zero inserted, updated, derived-updated, retired and facet rows.
- **Derived mention columns are written from staging only where `decision_id is null`** (section 4.1); the content
  upsert never compares them, so a future human decision is never overwritten by an automatic one.
- **`name_en_folded` is computed in the merge** (`lower(unaccent(name_en))`), never shipped in the CSV.
- **Staging tables are `create table as select <csv columns> ... with no data`**: live types, no constraints, so the
  server's own type parsing is the first gate and the merge is the second.
- **ANALYZE inside the load transaction** (added 2026-11-21). After the merge, every changed table is analyzed in the
  same transaction (ANALYZE counts the transaction's own inserted rows) before facets, the network refresh and the
  checks. The first load into an empty production database had no statistics and the `narrator_transmissions` refresh
  ran 12 minutes without finishing (the development database's first load had taken 5.6 minutes in total); it was
  cancelled, rolled back (version marked `failed`, zero rows, lock released) and rerun with this step.
- **Disk budget (§2.8)** runs only when `LOAD_VOLUME_BYTES` is set: the volume size is not visible from SQL.
- **No parallel query in the load session** (added 2026-11-21, `connection.ts`). The first load of projection
  `2026.11.21.4` into production failed after the merge with `could not resize shared memory segment ... No space left on
  device`: a parallel hash join takes a dynamic shared-memory segment in `/dev/shm`, which the Railway container keeps
  small. The transaction rolled back (version marked `failed`, nothing changed, lock released); the loader now sets
  `max_parallel_workers_per_gather = 0` and `max_parallel_maintenance_workers = 0` for its own session only.
- **External identity** (0010): `narrator_source_profiles`, `narrator_external_ids` and `narrator_link_candidates` merge
  right after `narrators`. Six checks guard the owner's rules (`src/db/AGENTS.md` §External identity); `reported` adds
  `standing_identity` (mentions per tradition and evidence), `latin_names` and `narrators_by_authority`.
- **No curation dump before the load (§4.3 step 2).** No `pg_dump` 18 on the operator machine; the development
  database has no curation rows. Required before any load into a database with curation data.
- **Orphan-FK check is generic**: every single-column FK declared in `public`, anti-joined in the session's schema,
  so the same check covers the throwaway test schema (which has no FK constraints).
- **Section 11.4 server-settings checks** (`max_connections = 20`, `shared_buffers = 64MB`) are reported, not fatal,
  until `ops/railway-tuning.sql` exists.
- **`chain_mention_candidates` merges like any pipeline table** (after `chain_mentions`, by `id`); a candidate whose
  mention or narrator leaves the projection retires with it. Four checks guard the owner decisions of 2026-11-21
  (`verify-data.ts`, `src/db/AGENTS.md` §Identity candidates); `reported.identity_candidates` counts candidates per
  tradition and basis.
- **Report correspondences** (`report_correspondence_candidates` by `id`, `report_correspondence_cluster_members` by
  (`method_version`, `hadith_id`)) merge after `hadith_assessments`. A new method version retires the old pairs by
  anti-join; reviewer decisions live in a curation table and are untouched. Three checks: both reports live and
  distinct, ordered in byte order, bound to the loaded Arabic; members name live reports and cover every pair; one live
  decision per pair. `reported.report_correspondences` counts pairs and shown pairs per scope and class.
- **Matn and non-rulings** (review 2026-11-21): a stored `matn_ar` must sit inside its own text (Arabic letters
  compared), and no non-ruling term is an assessment. The SQL list of non-ruling terms mirrors
  `diagnostics/grading-recovery/build_hadith_assessment_rows.py` `NON_RULING_CLASSES` (folded keys); change both together.
- **First load with these rules** (`load-6`, version `e2430eae…`): 14,214 hadiths updated (matn cleared), 1,328 mentions
  gained a machine-reviewed identity (kunya-only no longer contests), 1,813 non-ruling assessments retired, 135,825 pairs
  and 54,769 members inserted. Reload (`load-7-reload`) changed 0 rows.

## Production (2026-11-21)

`npm run db:load -- --bundle <projection dir> --database production --confirm-production` (`src/db/target-database.ts`);
without both flags every CLI here refuses the production database. `--bundle` is the projection directory (the one
holding `canonical/`), not `canonical/` itself. Production was loaded from the same `projection-v3` the development
database holds (version `e2430eae…`, `prod-load-2.log` beside the development logs; `prod-load-1.log` is the cancelled
first attempt), so both databases carry one content hash.

## Known limits

- The loader refuses to run while any live `narrator_surface_decisions` row exists: decision replay
  (`apply_decision(unit_id)`) is not written yet. Correspondence decisions do not block a load.
