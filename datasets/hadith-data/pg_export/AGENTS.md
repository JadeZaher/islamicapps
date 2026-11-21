# pg_export — bundle to Postgres projection

`export_postgres.py` turns a **validated** Neo4j-format bundle (`neo4j_export/`) into one COPY-ready CSV per launch
pipeline table (`canonical/`) and a candidate stream (`candidates/`), each with a hash-bound manifest. Design:
`docs/architecture/data-architecture.md` §4.4, §6.2. Loader: `src/db/load/`.

```
npx tsx src/db/load/dump-catalog.ts <dir>/catalog.json
python datasets/hadith-data/pg_export/export_postgres.py --bundle <bundle> \
  --input datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz \
  --rawis datasets/narrator-data/all_rawis.csv --legacy-master datasets/hadith-data/all_hadiths_unified.csv.gz \
  --catalog <dir>/catalog.json --output <new dir> [--legacy-source-index]
python -I datasets/hadith-data/pg_export/test_export_postgres.py
```

## Refusals

No `import_ready: true`; validation report and manifest naming different bundles; any bundle file whose bytes or
SHA-256 differ from its manifest; a recomputed `content_sha256` that differs; a unified CSV or rawi file whose hash
differs from the bundle's inputs; a CSV header that is not exactly the live catalog's loadable columns; any hadith
whose `text_ar` does not hash to its `arabic_sha256`; an unknown tradition, narration level, translation review state
or `grade_value`; non-contiguous mention positions.

## Rules

- **Determinism.** Rows sorted by primary key, LF, UTF-8, no timestamps, `QUOTE_NOTNULL` (every non-null cell is
  quoted, so no value can be read as COPY's `\.` end marker). NULL is an unquoted empty cell; blank text is NULL.
  The manifest binds the resolver (`regen_unified_csvs.py`), `classify_attribution.py` and this script by SHA-256,
  because a change to any of them changes the output.
- **Arabic is never trimmed or rewritten.** `text_ar_normalized` and `name_ar_normalized` use
  `classify_attribution._norm` (search only).
- **Narrator names.** `io.ts` reads `name_english`/`name_arabic` columns that `all_rawis.csv` does not have, so the
  design's "port io.ts" would leave both null. `name_ar` is the resolver's `_extract_arabic_name_raw`; `name_en` is the
  text before the first parenthesised Arabic block. A string split, not an identity claim.
- **Mention resolution, in precedence order:** the bundle's atomic `RESOLVES_TO` (`report_atomic`); the canonical
  resolver `resolve_narrator` per mention (`mention_exact`, `extraction_method = name_invariant_tier0|1|2`); the
  legacy `chain_indx` (`source_index`, only with `--legacy-source-index`). Confidence is 1.0 for all three.
- **Legacy `source_index` join** (owner question 1): unique (canonical source, SHA-256 of exact Arabic) on both sides;
  the legacy `hadith_id` must equal the new `hadith_id` or, for works re-keyed in the 37-column file (`pc_9`,
  `rabi_0825`), the new `hadith_no`; never Imami; every rawi id must exist; branch count and every branch length
  must equal the extracted chains. Rejections are counted by reason in the manifest.
- **Conflicting automatic identities are withheld.** Where the legacy index and the mention-exact resolver name
  different narrators for one mention, the mention stays `unresolved` with
  `extraction_method = withheld_conflicting_automatic_identities`. The bundle's atomic resolution is kept over the
  legacy index.
- **Assessments.** Pure Canon `grade_value = ثابت` is `collection_label` (never a grade). `gradings_full` segments
  are `cited_ruling` rows; `grade_canonical` and `grade_detail` port `grade-taxonomy.ts`; the parenthesised citation
  is split into work, volume and page.
- **Translations.** Bundle `review_state` `source_provided` and `source_status_unknown` both map to `state =
  source_provided`; the raw value stays in `review_state_raw`. Leading whitespace is trimmed from English only.
- **Candidates.** `machine_unreviewed` English goes to `candidates/translation_candidates.csv` (`machine_unreviewed`
  when a model is named, else `unknown_provenance`). The table is not migrated yet, so the loader does not read it.
- **Review units** are SHA-256 over `\x1f`-joined parts, NULL context as `''`: coarse (surface, teacher, work), fine
  (surface, teacher, student, work).
- `slice_projection.py` cuts a referentially closed slice of real rows for the loader flow test.
