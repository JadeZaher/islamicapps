---
type: track-log
title: Bundle to Postgres loader log
tags: [bundle-to-postgres-loader_20261121]
resource: ./plan.md
---

# Log: bundle-to-postgres-loader

All outputs under `datasets/hadith-data/development/pg-load-2026-11-21/` (git-ignored). Nothing canonical was
modified or regenerated.

## 2026-11-21

- **Inputs.** The three repo-root curation files and also
  `development/incomplete-curation/curation_manifest.incomplete.json` are access-denied (not bypassed). The
  exporter's documented default needs no curation manifest: `--source-release-state unreviewed_local_snapshot`
  (`neo4j_export/AGENTS.md`, "Publication boundary"). Readable inputs: 37-column
  `all_hadiths_unified.incomplete.csv.gz` (`feeeb38d…`), `all_rawis.csv` (`d87c3af6…`), legacy master
  `all_hadiths_unified.csv.gz` (`f8b5cebf…`).
- **Bundle.** `export_bundle.py --input … --rawis … --output pg-load-2026-11-21/bundle` (default release state).
  `import_ready: true`, 0 errors, all 12 gates pass. `content_sha256 c4e5e12e…`. Every graph file is
  byte-identical to the July `hadith-graph-v2-final` except `nodes/sources.csv` (the `release_state` value).
- **Projection.** `pg_export/export_postgres.py` (new). Two runs into `projection/` and `projection-repeat/`:
  every file byte-identical (`projection.sha256` = `projection-repeat.sha256`). Canonical
  `content_sha256 30cd1c84…` (= `dataset_versions.id`). Earlier runs kept under `superseded/`.
- **Findings during projection.**
  - Legacy join: the 37-column file re-keyed `hadith_id` for Pure Canon and OpenITI works (`pc_9`, `rabi_0825`)
    while the legacy `hadith_id` is the hadith number; 16,884 false "conflicts" until the check also accepted
    legacy id = new `hadith_no` (still on top of the unique Arabic-hash join).
  - Where the legacy index and the per-mention exact resolver both name a narrator, they disagree on about half:
    tier 0 agree 2,868 / disagree 2,875; tier 1 333 / 319. Disagreements are short or common surfaces resolving
    to a homonym (`شعبة` -> rawi 29483 where the index says 20020; `مالك بن أنس` -> 17705 vs 20001). Rule added:
    conflicting automatic identities are withheld (3,195 mentions stay unresolved, labelled).
  - 756 mentions are a bare `و` (Thaqalayn, position 0) that normalizes to `''`. First load attempt refused on
    `chain_mentions.surface_normalized` NOT NULL and rolled back (version `f6f1981c…` left as `failed`). Fixed in
    the projection: a known-empty value is written as `""`, not NULL. The projection now refuses any NULL in a
    NOT NULL column with table, column and row id.
  - The resolver `regen_unified_csvs.py` was edited in the working tree by the data-gaps lane between projection
    runs (`c0064fb2…` -> `72270927…`, uncommitted). The loaded data uses `72270927…`. With it: tier 0 agrees with
    the legacy index on 2,514 mentions and disagrees on 789; tier 1 333 / 318; 1,108 mentions withheld.
- **Load 1** (`load-1.log`): new version `30cd1c84…`, 1,033,812 rows changed (incl. 128,561 facet rows), 336 s
  (COPY 163 s, merge 104 s, facets 25 s, checks 16 s, vacuum 25 s). All 21 checks pass.
- **Load 2, same bundle** (`load-2-reload.log`): mode `reload`, every table +0 ~0 derived 0 retired 0, facets 0,
  0 rows changed. All checks pass.
- **Heavy indexes** (`heavy-indexes.log`): `hadiths_text_ar_normalized_trgm_idx` 47 MB, valid, 5.9 s.
- **Sizes** (`sizes.log`): database 1,314 MB (includes dead space from the refused first attempt); hadiths 483 MB
  (heap 338, indexes 145), chain_mentions 482 MB (248 / 234), translations 145 MB, chains 66 MB. Railway
  `postgres-volume` is 50,000 MB, so the section 2.8 50-percent rule leaves about 23.7 GB.
- **Verification sweep**: `tsc --noEmit` clean; `eslint src/db/load` clean; `db:verify` OK; `verify-data-cli`
  20/20 PASS exit 0 (and exit 1 against a mismatched manifest); `test_export_postgres.py` 14 OK;
  `test_neo4j_graph_bundle` 3 OK; flow test 1/1 pass; no `load_test_*` schema or `load_*` table left.
