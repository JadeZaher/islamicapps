---
type: runbook
---
# LOAD_STEPS: from the fixed parse to production

Nothing below has been run. Paths are relative to the repository root. The fixed parse is `fixed/parsed_hadiths.fixed.json`
(`works.rabi|zayd|rida`); `diff_report.md` has the counts. Order matters: steps 1-3 are files only, 4-5 change code, 6-9 touch the database.

## What changes in the data (numbers from `diff_summary.json`)

| | rabi | zayd | rida | total |
|---|---|---|---|---|
| records before -> after | 1,004 -> 1,005 | 698 -> 691 | 35 -> 205 | 1,737 -> 1,901 |
| `arabic_sha256` changes (same id, new text) | 98 | 624 | 33 | **755** |
| ids retired (absorbed into another report) | 0 | 8 | 1 | **9** (listed in `diff_report.md`) |
| new ids (`rabi_0881`, `#2`... split children) | 1 | 1 | 171 | **173** |

605 of the zayd hash changes are only the removed `=` / `V` / `*` markers: the Arabic is the same, the bytes are not.
Every record keeps its `record_id` (`openiti:<tradition>:<id>|<hadith_no>|<page_ref>`; the legacy `page_ref` is preserved on purpose).

## 1. Adopt the parse (files)

1. Back up, never delete (repo convention `parsed_hadiths.json.<timestamp>.bak`):
   `ibadi-hadith|zaydi-hadith|rida-hadith/parsed_hadiths.json`, `*_hadiths_clean.csv`, `*_hadiths_full.csv`, `PROVENANCE.json` under `datasets/hadith-data/`.
2. `python datasets/parse_openiti.py` (no flags). It overwrites exactly those four files per work (and nothing else) from the sources. The JSON gains
   `hadiths[].{sanad_ar, matn_ar, sanad_inherits_from, split_confidence, split_kind, footnotes, footnote_markers_without_text, commentary, commentary_kinds,
   absorbed_ids, prefix_from_id, split_from, page_start, line_start, line_end, legacy_id, kitab, section}` and top-level `verification`, `unassigned_blocks`.
   Note `commentary` was a *string* on 138 rabi records (attached to the wrong record); it is now a list of strings.
3. Check it equals the reviewed file: for each work, `json.load(live)['hadiths'] == fixed['works'][work]['hadiths']`, and
   `python -X utf8 -m pytest datasets/test_parse_openiti.py -q`.

## 2. Regenerate the unified dataset

`python datasets/hadith-data/regen_unified_csvs.py` (flags as for the last production build; add `--no-shia --shia-input <exact gz>` to reuse Thaqalayn,
`--allow-incomplete-curation` for a non-release build into `development/incomplete-curation/`). It reads the three `parsed_hadiths.json` (`load_openiti_hadiths`),
builds rows in `openiti_to_shia_row` (`regen_unified_csvs.py` ~l.1725: `text_ar`, `matn_ar`, `record_id`, `page_ref`), recomputes `chain_indx` and the Latin `sanad` from the new `text_ar`,
and rewrites `all_hadiths_unified.csv(.gz)`, `all_hadiths_clean.csv.gz`, `all_hadiths_shia.csv.gz`, `curation_manifest.json`, `curation_backlog.csv`.
Expect the release gate to block: `curation_manifest.json` binds the three `parsed_hadiths.json` by hash, and the 173 new ids have no English (release needs
`translation_status = complete`; see `datasets/hadith-data/AGENTS.md` "Translation release gate"). Translate the 755 changed and 173 new reports (`generate_hy_mt2_candidates.py`, about
US$0.04 at the recorded US$4.4e-5 per report), or accept the incomplete-curation build.

## 3. Rebuild what is bound to the old Arabic hash

All joins below are by `record_id` plus `arabic_sha256`; a changed hash makes them refuse or go stale. Counts are rows of the *current* files that reference an OpenITI
report whose hash changes or whose id is retired (computed against the production snapshot):

| Artefact | Rows affected | Rebuild |
|---|---|---|
| `datasets/hadith-data/diagnostics/report-correspondence/output/report_correspondence_pairs.*`, `..._cluster_members.csv` (and `report-correspondence-v2/`) | 1,072 of the 4,571 pairs that involve an OpenITI report | `python datasets/hadith-data/diagnostics/report-correspondence/build_report_correspondence.py` |
| `datasets/hadith-data/quran/hadith_quran_citations.jsonl.gz` / `hadith_quran_phrases.jsonl.gz` | 89 of 249 / 139 of 291 | `python datasets/hadith-data/quran/build_quran_citations.py` (then `validate_citations.py`); quran review worksheets and readings that cite these ids are stale |
| `datasets/hadith-data/reconciled/external_report_crosswalk.jsonl.gz`, `hadith_kg_quran_citations.jsonl.gz` | 122 of 980 / 2 of 7 | `reconciled/build_external_report_crosswalk.py` (+ `build_external_identity_sidecars.py`) |
| `datasets/hadith-data/reconciled/structure/*` (`report_structure.jsonl.gz`, nodes, locator claims) | 764 of 1,737 OpenITI rows | `reconciled/structure/build_structure_sidecars.py` |
| Assessments (`assessments/hadith_assessments*.jsonl.gz`) | 0 OpenITI rows | none |
| `reconciled/no_chain_in_source`, `pure_canon_chain`, `k6_source_index` | 0 OpenITI rows | none |
| Review records / `curation` rows bound to these hashes (`commentary_hadiths.bound_arabic_sha256`, `cross_parallels`, `hadith_motif_tags`) | none exist for these works in the files; check the database before step 8 | the loader refuses a stale binding |
| Translations: `ibadi|zaydi|rida-hadith/translations.jsonl` (keyed by parsed id, 1,162 / 1,203 / 35 raw model outputs), `translation_overrides.jsonl` (absent) | none is published (no OpenITI `text_en` in `translations`) | retranslate the 755 + 173 from the new `text_ar` with `translation_review_status = machine_unreviewed`; never reuse an old output for a changed hash |

## 4. Code and schema changes required (nothing here exists yet)

1. **`sanad_ar`.** Add the column to `hadiths` (and to the `public_hadiths` view, which shares `hadithColumns()`): `src/db/schema/corpus.ts` (next to `sanad` / `matnAr`, ~l.177-179), then
   `npm run db:generate` (a new `drizzle/core/0012_*.sql`) and `npm run db:migrate`. Alternative: put the Arabic span into `hadiths.sanad` (today the Latin narrator list the app renders); that
   changes what the app shows and is an owner decision. Also add `sanad_ar`, `sanad_inherits_from`, `split_confidence` to the unified schema: `UNIFIED_COLS` / `SHIA_COLS` in
   `regen_unified_csvs.py` (~l.141) and the 37-column contract in `neo4j_export/contract.py`; `openiti_to_shia_row` must copy them from the parsed record; `pg_export/export_postgres.py`
   (hadiths column list ~l.832 and the row builder ~l.818) must emit them. The loader requires the CSV header to equal the live catalog's `csv` columns, so run
   `npx tsx src/db/load/dump-catalog.ts <dir>/catalog.json --database production --confirm-production` after the migration.
2. **`matn_ar`** needs no schema change. `accepted_matn()` (`export_postgres.py` l.593) still gates it with `MatnIsolator`: the new matn is a suffix of `text_ar`, so it should pass; read
   `counts["matn_ar"]` in the export manifest and compare with today's.
3. **`footnotes` and `commentary`** (strings, never inside `text_ar`). `commentaries` / `commentary_hadiths` (`src/db/schema/commentary.ts`) are **not** in `PIPELINE_TABLES`
   (`src/db/load/tables.ts`), so there is no loader path today. Add a sidecar (suggested `reconciled/extraction/openiti_commentary.jsonl.gz`, hash-bound like the other sidecars, one row per string:
   `hadith_id`, `bound_arabic_sha256` of the new `text_ar`, `type` = `editor_footnote` | `compiler_comment` | `arranger_note` | `note`, `text_arabic`, `source_work`, `reference` = page and line from
   `page_start` / `line_start`, `origin` the pipeline origin, source code OITI), add both tables to `PIPELINE_TABLES` and the exporter. `commentaries.text` is NOT NULL (it is the English
   text): decide between a placeholder, a relaxed constraint or an Arabic-only table. Types map from `commentary_kinds`: `rabi_comment` and `gloss` = the compiler's comment (credit the compiler),
   `arranger_note` = the arranger's («تنبيه»), `footnotes` = the editor's. Credit every source (OpenITI, CC BY-NC-SA) as on the other OpenITI rows.
4. **Absorbed ids** (`absorbed_ids`, 9 retired ids). No column needed: the loader retires every report missing from a new projection (anti-join retirement, `src/db/load/AGENTS.md`;
   the load-flow test covers it). If the retired ids must stay resolvable, emit them as `quality_excluded = true`, `quality_exclusion_reason = 'merged_into:<id>'` rows (columns exist on `hadiths`) instead.
5. **Split children and recovered ids** appear as ordinary new `hadiths` rows (`id = hadith:` + `record_id`). `#` is part of the id: confirm no consumer URL-encodes or splits on it
   (`src/lib`, `src/app` routes that take a hadith id; the exporter's `id` and `record_id` handling).
6. **Docs that quote the old counts**: `datasets/hadith-data/README.md` (Ibadi 1,004, Zaydi 698), `datasets/sources/musnad-*-openiti.md`, `jami-sahih-rabi-openiti.md`, `zaydi-hadith/README.md`.

## 5. Bundle, projection, load

1. Bundle: `python datasets/hadith-data/neo4j_export/export_bundle.py --input <new unified csv.gz> --rawis datasets/narrator-data/all_rawis.csv --output <new empty dir> --source-release-state <state> --curation-manifest <manifest>`;
   check with `python datasets/hadith-data/neo4j_export/validate_bundle.py <dir>`.
2. Projection: `python datasets/hadith-data/pg_export/export_postgres.py --bundle <dir> --input <new unified csv.gz> --rawis datasets/narrator-data/all_rawis.csv --legacy-master datasets/hadith-data/all_hadiths_unified.csv.gz --catalog <dir>/catalog.json --output <new dir> --reconciled datasets/hadith-data/reconciled --correspondence datasets/hadith-data/diagnostics/report-correspondence/output`.
   It refuses any hadith whose `text_ar` does not hash to `arabic_sha256`, any stale sidecar row (hash mismatch) and any header drift; the `reconciled`/`correspondence` arguments are why step 3 must come first.
3. Load: development first, `npm run db:load -- --bundle <projection dir> --purpose openiti_extraction_fix`; then production with `--database production --confirm-production` after the data checks (`npm run db:verify-data`)
   pass. Expect: 173 inserted hadiths, 755 updated, 9 retired, facets refreshed; `source_text_status` / `chain_status` are loader-derived from the new text. Take the curation dump the loader's AGENTS.md asks for before touching a database that has curation rows.
4. Afterwards: re-run `npm run db:verify-data`, spot-check `rabi_0140`, `rabi_0881`, `zayd_0429`, `rida_0032` in the app, and run `python -X utf8 -m pytest datasets/test_parse_openiti.py datasets/hadith-data/extraction-quality/test_extraction_quality.py -q`.

## Decisions for the owner

- Arabic chain: new `sanad_ar` column or replace `hadiths.sanad` (step 4.1).
- Commentary storage and the NOT NULL `commentaries.text` (step 4.3).
- 370 reports (259 rabi, 53 zayd, 58 rida) have a null `sanad_ar` / `matn_ar` with `split_confidence = low`; the model scorer in `../score_with_model.py` (blocked on HTTP 402 when audited) or a curator can fill them from the verbatim `text_ar`.
