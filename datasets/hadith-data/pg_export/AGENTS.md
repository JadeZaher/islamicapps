# pg_export — bundle to Postgres projection

`export_postgres.py` turns a **validated** Neo4j-format bundle (`neo4j_export/`) into one COPY-ready CSV per launch
pipeline table (`canonical/`) and a candidate stream (`candidates/`), each with a hash-bound manifest. Design:
`docs/architecture/data-architecture.md` §4.4, §6.2. Loader: `src/db/load/`.

```
npx tsx src/db/load/dump-catalog.ts <dir>/catalog.json
python datasets/hadith-data/pg_export/export_postgres.py --bundle <bundle> \
  --input datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz \
  --rawis datasets/narrator-data/all_rawis.csv --legacy-master datasets/hadith-data/all_hadiths_unified.csv.gz \
  --catalog <dir>/catalog.json --output <new dir> [--reconciled datasets/hadith-data/reconciled]
  [--correspondence datasets/hadith-data/diagnostics/report-correspondence/output]
python -I datasets/hadith-data/pg_export/test_export_postgres.py
python -I datasets/hadith-data/pg_export/test_transliteration.py      # transliteration and mention spans
python -I datasets/hadith-data/pg_export/test_identity_rules.py       # provider English, Imam kunyas, the tier
```

Since projection `2026.11.21.4` the catalog must come from a database migrated to `0011`
(`npx tsx src/db/load/dump-catalog.ts <out.json> --database production --confirm-production`; read-only).

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
- **Chains** (projection `2026.11.21.2`). The bundle's text extraction, then the reconciled sidecars
  (`reconciled/README.md`), each file hash-checked against its build manifest and each row bound to the hadith's
  exact Arabic (a mismatch refuses): `no_chain_in_source` with `suppress_extracted_chain` drops every chain of that
  report (Shafi'i, Nahj al-Balagha); `pure_canon_chain` replaces the chains extracted from matn-only `text_ar` with
  the canonical extraction of the source's own `chain` field (`extraction_method = source_chain_field`, same
  `chain:`/`mention:` id scheme, empty branches dropped before numbering).
- **Identity candidates** (`chain_mention_candidates`; owner decisions 2026-11-21, `src/db/AGENTS.md` §Identity
  candidates). Per mention, every candidate is emitted with its basis; none is preferred:
  - Sunni reports only: `resolve_narrator` tier 0 -> `name_exact`, tiers 1-2 -> `name_spelling_fold`; otherwise
    `kunya_only_candidate` -> `name_kunya_only`. Imami, Ibadi and Zaydi reports get no name candidate.
  - K6 source index (`reconciled/k6_source_index.jsonl.gz`), only where the sidecar's `text_branches` equal the
    extracted branches exactly: at every `aligned_positions` entry (the positions the Arabic corroborates), basis
    `source_index_confirmed_by_text` when the report's basis is `source_index_corroborated_by_text`, else
    `source_index`; `detail` is the agreement class. A tahwil branch inherits the source id of a corroborated twin
    whose opening surfaces are identical up to that position (`:shared_trunk`); convergences are not inherited
    (`align_source_index`).
  - Placeholder rows are never a target (a source-index claim on one is dropped and counted); the only placeholder
    target is a kunya-only row through `name_kunya_only`.
- **`chain_mentions.narrator_id`** (the machine-reviewed identity; never called verified) is set only for an uncontested
  `source_index_confirmed_by_text` candidate (`verified_narrator`): `resolution = source_index`, `resolution_basis =
  source_index`, confidence 1.0. A `name_kunya_only` candidate never contests it (owner, 2026-11-21). Every
  other mention is `unresolved`. The bundle's `RESOLVES_TO` and the legacy master's `chain_indx` are no longer read
  for identity: the first is an older name match (and touched non-Sunni rows), the second differs from the K6
  source's own index on 16,156 of 34,324 comparable rows.
- **Manifest.** `inputs.reconciled_sidecars` binds the three sidecar files; `counts.identity_candidates` gives
  candidates per tradition and basis, mentions by agreement, verified links, confirmed-but-contested mentions and
  dropped claims; `counts.k6_sidecar_built_with_current_resolver` is false once `regen_unified_csvs.py` changes
  (rebuild the sidecar when the change affects resolution).
- **Matn** (projection `2026.11.21.3`). `matn_ar` is stored only when `diagnostics/report-correspondence/matn_isolation.py`
  (imported, not copied: `MatnIsolator` with no sidecars) accepts the column as the report's own matn: its Arabic
  letters occur inside the report's own text and it does not start where the text starts with three or more
  transmission links. Otherwise no matn is stored and `counts.matn_ar` records why and by work (1,597
  `matn_column_not_in_text`, 12,617 `matn_column_includes_chain`, all K6). Real-row test: Tirmidhi `k6:23658`.
- **Assessments.** Non-rulings in `gradings_full` (`لم يخرجه` 1,736, `سكت عنه` 46, back-references 24, 7 others) are
  excluded and counted (`gradings_full:non_ruling_excluded:<reason>`), using `NON_RULING_CLASSES` and `fold` imported
  from `diagnostics/grading-recovery/build_hadith_assessment_rows.py`. Pure Canon `grade_value = ثابت` is
  `collection_label` (never a grade). `gradings_full` segments
  are `cited_ruling` rows; `grade_canonical` and `grade_detail` port `grade-taxonomy.ts`; the parenthesised citation
  is split into work, volume and page.
- **Translations.** Bundle `review_state` `source_provided` and `source_status_unknown` both map to `state =
  source_provided`; the raw value stays in `review_state_raw`. Leading whitespace is trimmed from English only.
  `english_quality`: the bundle's `arabic_leakage` becomes `complete` when the only Arabic-script characters are the
  honorific symbols ﷺ ﷻ ﷽ and ؐ-ؓ (10,650 Sunni, 9 Imami in `2026.11.21.4`); real Arabic stays held. The rule belongs
  in `regen_unified_csvs.translation_issue` too (not changed here: the resolver's hash binds the K6 sidecar).
- **Candidates.** `machine_unreviewed` English goes to `candidates/translation_candidates.csv` (`machine_unreviewed`
  when a model is named, else `unknown_provenance`). The table is not migrated yet, so the loader does not read it.
- **Review units** are SHA-256 over `\x1f`-joined parts, NULL context as `''`: coarse (surface, teacher, work), fine
  (surface, teacher, student, work).
- **Report correspondences** (`--correspondence`, default `diagnostics/report-correspondence/output`). Refused when
  the output is missing or its `summary.json` names another unified CSV than `--input`; every pair's id, order, method,
  class, scope and basis is checked. A pair whose report is not loaded or whose Arabic hash differs from the loaded
  text is dropped and counted (`counts.report_correspondences`; 0 on 2026-11-21). The manifest binds the pair, member
  and summary files, `matn_isolation.py`, the extractor and the non-ruling rule by SHA-256.
- `slice_correspondence_fixture.py` cuts the report-family flow-test fixture (real rows, typed from the catalog).
- `slice_projection.py` cuts a referentially closed slice of real rows for the loader flow test, choosing reports
  with a verified link, a disagreement and a kunya-only candidate, and closing narrators over the candidates.
- **Tests.** `test_export_postgres.py` covers the pure rules, the sidecar rules on real sidecar rows, and real
  mentions read back from the projection under `development/pg-load-2026-11-21/projection-candidates` (`PG_PROJECTION`
  overrides; skipped when absent).

## External identity (projection `2026.11.21.4`; `src/db/AGENTS.md` §External identity)

`external_identity.py` reads the reconciled sidecars (`reconciled/README.md` §External sources), each file checked against
its build manifest, and refuses a claim whose mention, surface or report Arabic differs from the projection's. Rows:

- **narrators**: every hadith-kg or Riwayat record a claim or link names (`narrator:hadith-kg:<id>`,
  `narrator:riwayat:<N id>`), name as the dataset writes it, its transliteration (`name_latin`), placeholder reason
  (stubs: `hadith_kg_stub_narrator`); the twelve Imams from `imam_kunya_conventions.json` (`narrator:imam:<n>`).
- **narrator_source_profiles** (`dataset_assertions` verbatim; `label_reason` from `riwayat_label_reason`: placeholder,
  a name held by two or more ids each with at least 3 mentions and a tenth of the name's total, Riwayat's merge or junk
  flag, a bare `ابن X`), **narrator_external_ids** (Riwayat's crosswalk), **narrator_link_candidates** (the sidecar's lexicon
  links whose lexicon row is loaded and not a placeholder; one link per external record or the build refuses).
- **chain_mention_candidates**: one per claim (`candidate_id`), `source_position` the external list index, `source_ref`
  `hadith-kg:hadith:<id>` / `riwayat:<H id>`, `source_assertion_origin` `dataset_index` or Riwayat's origin.

**The tier** (`standing_identity`, table-tested in `test_identity_rules.py`). Evidence, strongest first: K6
`source_index_confirmed_by_text`; `two_sources_agree` (a K6 claim and a hadith-kg claim whose person keys meet: K6 and
hadith-kg are independent compilations; Riwayat's Sunni ids are hadith-kg's own and never a second source);
`source_hadith_kg_confirmed_by_text`; `source_riwayat_confirmed_by_text` when its origin is an annotation (never
`riwayat_automatic_linking`) and the record is not label-like; `imam_kunya_convention`. The mention must be uncontested
(`contests`): no two contesting candidates name different person keys within one registry. Person keys
(`PersonKeys.key`): a record's lexicon link, else a Riwayat record's single hadith-kg crosswalk id (and that record's
link), else itself. The same rule is the load invariant and the chain read (`PERSON_KEY_SQL`).

**Imam kunyas** (`imam_kunya.py`, data `imam_kunya_conventions.json`, owner-reviewable). Imami reports only; the surface
is exactly a listed kunya, optionally followed by one listed qualifier, with the honorific marker at the end of the
surface or right after the name in the report text (`mention_text.PlainText.honorific_after`). Unshared kunya or a
qualifier naming one Imam: `imam_kunya_convention`; a shared kunya with no qualifier: `imam_kunya_candidate` for each Imam
who shares it (a label, never a contest); other words after the kunya: nothing.

## Latin names (`transliteration.py`, `mention_text.py`, `provider_english.py`)

Per mention, first that applies: (a) `provider_english`, Imami Thaqalayn reports only: the dominant English form of the
name's folded key in `diagnostics/chain-reconciliation/output/imami_surface_lexicon.jsonl.gz` (hash-bound), spelling
variants pooled, at least half the pairings, a name and not a clause, and it must render the Arabic (first consonant, and
the last Arabic word heard after the first English word): this refuses alignments shifted by one name (بكر بن عبد الله بن
حبيب paired with "Tamim ibn Buhlool"); (b) `identity_name`: the English of the standing identity, or of the one person every
contesting candidate names (the lexicon's Latin run, as the page shows it, or the Imam register's name); (c) a
transliteration of the name as written in the glossary's scheme (`TRANSLITERATION_NOTE`): from the vowel marks of the
mention's own span in the report text (`locate_mentions`; the stored surface has no marks), a word without full marks
read from the curated table; or (d) the table alone when every word is in it. Otherwise none: Arabic alone. The table
leaves out spellings with two customary readings (معمر, عبيدة, حصين, حجر, حبان, سلام, عقيل) and non-name words.
`counts.latin_names` gives coverage by tradition and basis.
