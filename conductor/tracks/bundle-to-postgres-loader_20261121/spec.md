---
type: track-spec
title: Bundle to Postgres loader
tags: [bundle-to-postgres-loader_20261121, planned]
resource: ./metadata.json
---

# Bundle to Postgres loader

Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) section 12 step 5; section 4 (ownership, identifiers,
reload strategy, projection); section 6.2 (bundle files to tables); section
11.2 and 11.4 (facets and the kept gates); section 2.8 (disk budget).

Carries forward archived track
[hadith_dataset_consolidation_20260723](../../archive/2026-11-21-neo4j-era/tracks/hadith_dataset_consolidation_20260723/spec.md):
its exporter and validator are now the source format; its Phase 3 (offline
`neo4j-admin` import) becomes this track ("Postgres schema and COPY load",
design 13.5); its Phase 4 integrated verification folds into phase 5 here.

## Goal

Load the validated bundle into Postgres through a deterministic projection,
with every section 11.4 check passing and counts matching section 6.2.

## Scope

`export_postgres.py` with both streams (`canonical/`, `candidates/`); COPY
into staging; anti-join merge by stable ID; `verify.ts`; `indexes-heavy.sql`;
measurement of database and index sizes. The load target is the Railway
database (see postgres-foundation), so the section 2.8 50-percent disk check
runs before every COPY.

## Out of scope

Curation data from Neo4j (neo4j-curation-export); query modules; production
cutover steps.

## Acceptance checks

- The projection refuses a bundle without `import_ready: true` and with a
  mismatched input hash.
- Two projections of one bundle are byte-identical.
- All section 11.4 checks pass; counts match section 6.2.
- A second load of the same bundle changes zero rows.
- Disk and index sizes recorded for section 2.8.

## Open owner questions (section 14)

- Q1: load legacy `chain_indx` as `source_index`? (flag, default off)
- Q11: do mention-exact links count as transmissions?
- Q13: may the `development_nonrelease` bundle be served publicly?
- Q2: with no `cleared` `collection_rights` row, public views are empty.
