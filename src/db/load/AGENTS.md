# src/db/load — bundle-to-Postgres loader

Design: `docs/architecture/data-architecture.md` §4.3 (reload), §4.4 (projection), §11.4 (gates), §12 step 5.
Track: `conductor/tracks/bundle-to-postgres-loader_20261121/`. Producer: `datasets/hadith-data/pg_export/`.

## Files

| File | What |
| --- | --- |
| `tables.ts` | The load contract: 17 pipeline tables in merge (FK) order, key columns, loader-derived columns |
| `catalog.ts` | Reads `information_schema` and classifies each column (`csv`, `bookkeeping`, `generated`, `loader_derived`) |
| `dump-catalog.ts` | Writes that classification as JSON for `export_postgres.py --catalog` |
| `manifest.ts` | Re-checks the projection manifest (file hashes, headers, content hash, source bundle `import_ready`, input hash) |
| `copy.ts` | `COPY ... FROM STDIN (format csv, header match)` into `UNLOGGED load_<table>` |
| `merge.ts` | Guarded upsert by stable id, anti-join retirement, derived mention columns |
| `verify-data.ts` | Section 11.4 data invariants; `verify-data-cli.ts` runs them on demand and exits 1 on failure |
| `load.ts` | The orchestrator; `load-bundle.ts` is the `npm run db:load` CLI |
| `run-heavy-indexes.ts` | Executes `src/db/ops/indexes-heavy.sql` outside a transaction and prints the index size |
| `__tests__/load-flow.test.ts` | Flow test: a real four-tradition slice into a throwaway schema (`load_test_<hex>`) |

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
- **Disk budget (§2.8)** runs only when `LOAD_VOLUME_BYTES` is set: the volume size is not visible from SQL.
- **No curation dump before the load (§4.3 step 2).** No `pg_dump` 18 on the operator machine; the development
  database has no curation rows. Required before any load into a database with curation data.
- **Orphan-FK check is generic**: every single-column FK declared in `public`, anti-joined in the session's schema,
  so the same check covers the throwaway test schema (which has no FK constraints).
- **Section 11.4 server-settings checks** (`max_connections = 20`, `shared_buffers = 64MB`) are reported, not fatal,
  until `ops/railway-tuning.sql` exists.
