# Hadith Dataset Documentation

This directory contains the compiled hadith datasets used by the IslamicApps application.
All active datasets are flat CSV files. Source pipelines and intermediate artifacts are
stored in subdirectories or archived under `archive/`.

---

## Dataset Inventory

### Active Files

**Gz-first convention.** The large derived CSVs listed below are stored as `.gz` in git (well under the 100 MB GitHub limit). Python streams either representation through `open_csv_input`; TypeScript streams it through `openDatasetStream`. Neither reader expands gzip into a canonical plain file. When both representations exist, their logical SHA-256 must match or the pipeline fails closed. Cloning the repo therefore requires no manual unzip step.

| File | Rows | Plain size | .gz size | Description |
|------|------|------|------|-------------|
| `all_hadiths_unified.csv` | 99,283 | 172 MB | 32 MB | **Current published master.** All traditions (Sunni 64,356 + Imami 33,225 + Ibadi 1,005 + Zaydi 691, counts of the corrected OpenITI parse; the 2026-11-21 load of it holds 99,447 reports, see `extraction-quality/fixed/`). Rebuilt by `python regen_unified_csvs.py`; publication is blocked unless Arabic, English, stable identity, and provenance gates pass. |
| `all_hadiths_clean.csv` | 66,058 | 60 MB | 14 MB | Sunni + Ibadi + Zaydi view (no Imami). Derived from `all_hadiths_unified.csv`. |
| `all_hadiths_shia.csv` | 34,927 | 95 MB | 18 MB | Imami + Rida + Ibadi + Zaydi view. Extended schema with grading fields. Derived from `all_hadiths_unified.csv` (and itself the input for Imami row loading via the Thaqalayn build at `shia-hadith/build_csv.py`). |

### Zaydi Sub-directory (`zaydi-hadith/`)

| File | Rows | Description |
|------|------|-------------|
| `parsed_hadiths.json` | 691 | Current authoritative JSON from OpenITI clean text (corrected parse, `datasets/parse_openiti.py`): adds `sanad_ar`, `matn_ar`, `split_confidence`, `sanad_inherits_from`, `footnotes`, `commentary`. Source of truth. |
| `zaydi_hadiths_clean.csv` | 691 | Stale derivative; regenerate and reconcile before release. |
| `zaydi_hadiths_full.csv` | 691 | Stale derivative; regenerate and reconcile before release. |
| `PROVENANCE.json` | — | Transformation metadata (source URI, parse date, what changed). |

**Source**: OpenITI `0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1` (community-typed from Shamela al-Zaydiyya, NOT OCR).

### Ibadi Sub-directory (`ibadi-hadith/`)

| File | Rows | Description |
|------|------|-------------|
| `parsed_hadiths.json` | 1,005 | Authoritative JSON from OpenITI clean text (corrected parse). Includes al-Rabi commentary and footnotes as separate lists (142 reports). |
| `ibadi_hadiths_clean.csv` | 1,005 | Minimal CSV. |
| `ibadi_hadiths_full.csv` | 1,005 | Full schema CSV for unified dataset integration. |
| `PROVENANCE.json` | — | Transformation metadata. |

**Source**: OpenITI `0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1` (community-typed from Shamela al-Ibadiyya, NOT OCR).

> Both collections are parsed by `datasets/parse_openiti.py`. Old OCR-based scripts are archived in `datasets/archive/ocr-pipeline/`.

---

## Column Schemas

### `all_hadiths_clean.csv`

| Column | Type | Description |
|--------|------|-------------|
| `id` | int | Sequential global ID |
| `hadith_id` | str/int | Source-internal hadith number |
| `source` | str | Collection name (see collections table below) |
| `chapter_no` | int | Chapter number within collection |
| `hadith_no` | int/str | Hadith number within chapter |
| `chapter` | str | Chapter title (Arabic for Zaydi, transliterated for Sunni) |
| `chain_indx` | str | Comma-separated narrator node IDs (from scholar graph); blank for Zaydi |
| `text_ar` | str | Full Arabic text (sanad + matn for Sunni; matn-focused for Zaydi) |
| `text_en` | str | English translation |

### `all_hadiths_shia.csv` / `all_hadiths_shia.csv.gz`

All columns from the clean schema above plus:

| Column | Type | Description |
|--------|------|-------------|
| `provider_file_id` | str | Numeric Thaqalayn `v2_books` filename; durable book coordinate |
| `provider_book_id` | str | Thaqalayn API `bookId`; retained independently of the display title |
| `volume` | int | Volume number |
| `category` | str | Top-level category / book name (Arabic) |
| `sanad` | str | Isnad chain text or Thaqalayn sanad reference |
| `matn_en` | str | English matn only (Thaqalayn field; blank for non-Thaqalayn sources) |
| `grading_majlisi` | str | Allama Majlisi's grading (Imami only) |
| `grading_mohseni` | str | Sheikh Mohseni's grading (Imami only) |
| `grading_behbudi` | str | Sheikh Behbudi's grading (Imami only) |
| `gradings_full` | str | Pipe-delimited full grading list: `Scholar: Grade (Reference)` |
| `url` | str | Thaqalayn source URL |

### Curation and provenance columns

The next publishable regeneration appends `record_id`, `source_record_id`,
`provenance_source`, `translation_status`, `translation_source`,
`translation_model`, and `translation_review_status` to the master and both
views. `record_id` is the durable graph key; numeric `id` remains row order.
See [`AGENTS.md`](./AGENTS.md) for the complete load contract.

### Uniform isnad validation assets

`extract_isnad_unified.py` is the canonical Arabic source-surface extractor.
It supports comma-separated narrator IDs within a branch and `|` between
taḥwīl branches through `_compute_chain_indx`. It preserves pronouns and
collective source wording rather than inventing narrator identities.
Co-transmitters at one level become parallel branches, never adjacent
teacher/student IDs. Resolution is atomic: one unresolved or invalid surface
empties the row chain and increments failure telemetry, so no partial chain can
look complete. Cartesian/co-transmitter and taḥwīl stitching expansion is
bounded at 64 branches before allocation. Over-limit rows raise a typed
`IsnadExtractionLimitError`; regeneration emits an empty whole-row chain with
`rows_extraction_failed` telemetry. The staged Thaqalayn builder applies the
same row-level policy while still aborting unexpected extractor interface bugs.

The release-quality fixture is
`__tests__/fixtures/tahweel-gold.jsonl`: 32 manually read local records across
Sunni, Imami, Ibadi, and Zaydi inputs, each with a durable/local source key and
provenance path. Full records are compared byte-for-byte to the declared asset;
the two K6 excerpts carry exact start/end bounds. OpenITI identities compose
parsed ID, hadith number, and page reference. `test_extract_isnad_unified.py`
uses only the Python standard library. `algo_evaluate.py` requires at least 30
fixtures and gates overall branch count, Jaccard, ordered edit similarity, and
per-tradition quality under `.omc/research/uniform-isnad/`; evaluation must pass
before regenerated chain data can be treated as curated.

---

## Collections by Tradition

### Sunni — Kutub al-Sittah (~34,441 hadiths in `all_hadiths_clean.csv`)

| Collection | Source field value |
|------------|--------------------|
| Sahih al-Bukhari | `Sahih Bukhari` |
| Sahih Muslim | `Sahih Muslim` |
| Sunan al-Nasa'i | `Sunan an-Nasa'i` |
| Sunan Abi Dawud | `Sunan Abi Da'ud` |
| Jami' al-Tirmidhi | `Jami' al-Tirmidhi` |
| Sunan Ibn Majah | `Sunan Ibn Majah` |

Source: Parsed from a legacy public corpus. The current published K6 layer has
853 blank English cells and eight blank Arabic cells; these are release blockers
until recovered from a cited source or translated and reviewed.
Isnad chains parsed by `archive/classical-pipeline/parse_sanad.py`.

### Zaydi — Musnad al-Imam Zayd ibn Ali (627 hadiths)

- **Source field value**: `Musnad al-Imam Zayd ibn Ali`
- **Compiler**: Abd al-Aziz ibn Ishaq al-Baghdadi
- **Source**: Arabic text extracted from Archive.org digitization (djvu.txt) of the Musnad, then OCR-parsed.
- **Translations**: LLM-translated via OpenRouter. 258 hadiths required a retranslation pass.
- Present in both `all_hadiths_clean.csv` and `all_hadiths_shia.csv`.

### Imami — Thaqalayn API (~33,817 hadiths in `all_hadiths_shia.csv`)

- **Source**: ThaqalaynAPI V2 JSON files (34 books in `shia-hadith/v2_books/`)
- **Grading**: Per-hadith grades from Majlisi, Mohseni, and Behbudi where available
- **Isnad**: Thaqalayn sanad field included
- Not present in `all_hadiths_clean.csv` (separate file due to schema differences and size)

---

## Data Flow / Pipeline

```
[Sources]
  Kutub al-Sittah (public corpus)
  ThaqalaynAPI V2 JSON (34 books)
  Musnad Zayd PDF (Archive.org OCR)
  SheikhAhmad Pure Canon (four additional classical Sunni collections only)

[Processing]
  1. Extract → JSONL
  2. Translate (OpenRouter LLM)
  3. Parse isnad chains (parse_sanad.py)
  4. Join classical English by immutable pc_* source id
  5. Validate identity, provenance, Arabic, English, and source counts

[Output]
  all_hadiths_clean.csv         ← Sunni + Zaydi (minimal schema)
  all_hadiths_shia.csv(.gz)     ← Imami + Ibadi + Zaydi (full schema)
```

### Regeneration

`regen_unified_csvs.py` rebuilds the master and both views:

1. Optionally regenerates the Imami source CSV from Thaqalayn `v2_books/` JSON into a staging directory; curation never mutates the canonical projection.
2. Loads K6, four Pure Canon classical collections, Ibadi, Zaydi, and Rida inputs.
   Every chain path uses the canonical Arabic extractor and shared narrator
   resolver. The K6 sidecar supplies display `sanad`/`matn_ar` only.
3. Restores classical English from the enhanced CSV, with a narrow clean-JSONL fallback, by `pc_*` id plus exact Arabic equality.
4. Applies source-reviewed `translation_overrides.jsonl` entries only when their stable record ID and Arabic SHA-256 still match.
5. Hashes provenance-only `curation_dispositions.jsonl` into the manifest; these reference corrections and legal-workflow decisions never satisfy a text gate.
6. Preserves the validated tradition on every source-work label; the Neo4j release preflight separately blocks unresolved registry labels and never defaults them to Sunni.
7. Writes `curation_backlog.csv` plus aggregated manifest gates for text, explicit translation review, provenance, every-row `chain_indx`, narrator references, and canonical source-work alignment.
   The chain gate includes present/missing/invalid/unknown-reference counts by
   tradition for local review assets.
8. Reads the K6 snapshot transparently from `.csv` or `.csv.gz`, stages and verifies the master and both projections, and emits deterministic gzip companions for all three.
9. Replaces a ready data bundle under a bounded process-wide lock with rollback protection and swaps the bound manifest last. `--allow-incomplete-curation` writes only ignored `.incomplete` artifacts under `development/incomplete-curation/`; it cannot overwrite canonical CSV, GZIP, backlog, candidate-manifest, or active-manifest files.

Run regeneration and graph dry-runs locally first. A ready manifest is necessary
but not sufficient for uniform-isnad release: the saved evaluator must also
clear overall branch-count/Jaccard/ordered gates and the 0.80 per-tradition
floors. Any production Railway cutover requires separate approval after local
evidence, environment confirmation, cost estimate, and rollback review.

`--no-shia` has a deliberately exact reuse contract: when the tracked
`all_hadiths_shia.csv.gz` exists, it is authoritative and the ignored plain CSV
cache is bypassed even if the pair diverges. `--shia-input <path>` selects a
different exact CSV/GZIP asset and is valid only with `--no-shia`. Ordinary
CSV/GZIP discovery remains fail-closed when both representations exist with
different logical content. The manifest hashes the exact reuse asset selected.

`curation_manifest.json` is the active publication commit and is never replaced
by a failed attempt when it remains valid and bound to the current CSV/GZIP.
Every attempt also writes `curation_candidate_manifest.json`; on failure it
contains the new gate evidence, while a repository without a valid active
manifest may additionally receive the same non-ready manifest as bootstrap
state. The backlog always describes the latest candidate, not necessarily the
active published dataset.

---

## Archive Documentation

All archived directories are under `archive/`. They are kept for reproducibility and
debugging; the data they contain has been merged into the active CSVs.

### `archive/classical-pipeline/`

Translation pipeline for the six Sunni collections. Archived April 28, 2026.

| File | Description |
|------|-------------|
| `classical_collections_final.jsonl` | 67,232-line JSONL of parsed Sunni hadiths before translation |
| `classical_collections_translated.jsonl` | Full translation output (63 MB) |
| `classical_translations_clean.jsonl` | Successful translations |
| `classical_translations_failed.jsonl` | Failed translations (retranslated separately) |
| `classical_translations_refused.jsonl` | LLM-refused translations |
| `classical_sanad_parsed.jsonl` | Parsed isnad chains |
| `classical_canon_enhanced.csv` | Enhanced CSV (32 MB) — final output before unification |
| `extract_classical_for_translation.py` | Extracts Arabic hadiths for LLM translation |
| `parse_sanad.py` | Parses isnad chains into node IDs |
| `split_translation_errors.py` | Separates clean/failed/refused translation output |

### `archive/consolidation-logs/`

Hourly status snapshots and analysis from the April 20, 2026 dataset consolidation session.
Includes `CONSOLIDATION_LOG.txt` (full log), hourly `CONSOLIDATION_STATUS_*.txt` files,
`PHASE10_OPTIMIZATION_ANALYSIS_2026-04-20.txt`, `audit_report.txt`, and two enhancement
scripts (`phase9_shia_enhancement.py`, `phase9_shia_sanad_extraction.py`) that were run
during consolidation.

### `archive/sheikahmad-pure-canon/`

Processing pipeline for the "Hadith Pure Canon Authentica" and "Green Book of Sahih Hadith"
Excel datasets from SheikhAhmad / NabiMuhammad.com. The four classical source collections
(Ahmad, Darimi, Shafi'i, and Muwatta) contribute 29,915 rows to the current master. The
remaining anthology/authentication rows are not primary hadith nodes and require a cited
scholarship-layer model rather than blind appending.

| File | Records | Description |
|------|---------|-------------|
| `pure_canon.jsonl` | ~100,216 | Full Pure Canon dataset |
| `green_book.jsonl` | ~35,452 | Green Book of Sahih Hadith |
| `pure_canon_en.jsonl` | partial | English translations |
| `import-pure-canon.ts` | — | Neo4j import script |
| `canon-normalize.ts` | — | Source name normalization |
| `rename-anthology-sources.ts` | — | Anthology source renaming |
| `scholar-graph-actions.ts` | — | Scholar graph relationship actions |

Source Excel files remain in `sheikahmad/` at the top of this directory.

### `archive/unified-snapshots/`

Point-in-time snapshots of the consolidated dataset from April 20, 2026, before the Zaydi
collection was added and before chapter name cleanup. Not the authoritative current state.

| File | Description |
|------|-------------|
| `unified_hadith_consolidated.csv` | Full consolidated CSV (140 MB, all traditions) |
| `unified_hadith_consolidated.csv.gz` | Compressed version (32 MB) |
| `unified_hadith_collection_2026-04-20_enhanced.xlsx` | Excel export with enhanced metadata (41 MB) |
| `cross_reference_mapping.csv` | Cross-tradition parallel hadith mapping (~44,084 mappings) |

### `archive/zaydi-translation-pipeline/`

Translation pipeline artifacts for the Zaydi collection. Archived after completion.

| File | Description |
|------|-------------|
| `zaydi_for_translation.jsonl` | 627 hadiths prepared for LLM translation |
| `zaydi_retranslated.jsonl` | 258 hadiths retranslated after initial refusals |
| `refused_ids.txt` | 258 hadith IDs initially refused by the LLM |
| `zaydi_translation_prompt.txt` | LLM prompt used for translation |
| `musnad_zayd_arabic_text.txt` | Raw Arabic OCR text from Archive.org PDF |

### `archive/logs/`

`translate_classical.log` — Full log from the Sunni translation run (April 14, 2026).

---

## Data Quality Notes

The archived enhanced workbook contains 97,550 rows and 18 columns, so it is
1,733 rows and eight columns behind the current published master. It is not a
load source. The curation manifest is the current machine-readable readiness
report; a non-empty backlog means the dataset is not releaseable.

### Zaydi (Musnad al-Imam Zayd ibn Ali)

- **OCR artifacts**: The source PDF was digitized by Archive.org as djvu.txt. Heavy OCR
  corruption is present in the Arabic text: garbled letters, stray punctuation (`#`, `+`,
  `_`, `٠‏`), footnote markers embedded in text, and `داب` for `باب` (chapter headings).
- **Mechanical cleanup**: `clean_arabic_text.py` strips the most common artifacts.
- **LLM purification pipeline** (`purify_arabic_text.py`): In progress. Sends hadiths to
  Gemma for Arabic text reconstruction with a confidence score (1=clean, 4=heavily garbled).
  `zaydi_for_purification.jsonl` contains all 627 hadiths prepared; `zaydi_cleaned.jsonl`
  has 23 merged results so far.
- **Translation refusals**: 258 of 627 hadiths were initially refused by the LLM during
  translation (likely due to garbled text). All 258 were successfully retranslated.
- Chapter names were cleaned post-parse: 75 OCR-corrupted chapter headings were fixed by
  `fix_zaydi_data.py`.

### Sunni Collections

- The published master accidentally discarded all 29,915 classical English values. The
  generator recovers 29,888 from the enhanced archive and the final 27 Shafi'i rows from
  `classical_translations_clean.jsonl`, requiring immutable ID plus exact Arabic equality.
  The remaining 853 K6 blanks require official source recovery or an explicitly labeled,
  reviewed translation override.
- Repeated JSONL translation attempts are preserved as evidence but are not merged merely
  because they are non-empty; conflicting attempts require explicit review.
- Isnad chains are stored as comma-separated scholar graph node IDs in `chain_indx`.
  The raw isnad text is preserved in `text_ar`.

### Rejected historical translation candidates

A 2026-07-20 recovery audit found 19 historical OpenITI backup rows whose IDs
and Arabic matched the current parsed records: 15 Zaydi `no_english_text`
rows, one Ibadi `no_english_text` row, and three Ibadi `same_as_arabic` rows.
Inspection of the complete backup `text_en` values rejected all 19. They contain
prompt/meta discussion, self-correction or missing-input messages, or a
translation of different Arabic. Consequently no `translation_overrides.jsonl`
entry was created and the projected blocker reduction is zero. A future
recovery must provide a clean full translation bound to the same immutable ID
and Arabic hash; extracting a plausible fragment from these contaminated model
responses is not an acceptable recovery.

### Imami (Thaqalayn)

- Grading fields (`grading_majlisi`, `grading_mohseni`, `grading_behbudi`) are present
  only where the Thaqalayn API provides them; many records have empty grading fields.
- `matn_en` is the Thaqalayn-specific English matn field and may differ from `text_en`
  (which is the full hadith English text).

---

## Scripts

### Active Scripts (this directory)

| Script | Purpose |
|--------|---------|
| `regen_unified_csvs.py` | Rebuild `all_hadiths_clean.csv` and `all_hadiths_shia.csv` from source data |
| `add_tradition_column.py` | Add/update `tradition` column to `all_hadiths_clean.csv` |

### Active Scripts (`shia-hadith/`)

| Script | Purpose |
|--------|---------|
| `build_csv.py` | Build `all_hadiths_shia.csv` from Thaqalayn V2 JSON files |
| `download_thaqalayn.py` | Download Thaqalayn API JSON into `v2_books/` |

### Active Scripts (`zaydi-hadith/`)

| Script | Purpose |
|--------|---------|
| `parse_musnad_zayd.py` | Parse Arabic OCR text into structured hadith records; produces `zaydi_hadiths.csv`, `zaydi_hadiths_full.csv`, `parsed_zaydi_hadiths.json` |
| `clean_arabic_text.py` | Phase 1 mechanical OCR artifact removal; Phase 2 prep for LLM cleanup |
| `purify_arabic_text.py` | LLM-assisted Arabic text purification via Gemma with confidence scoring |
| `fix_zaydi_data.py` | Merge retranslations, fix 75 OCR-corrupted chapter names, regenerate CSVs |
| `merge_zaydi_translations.py` | Merge LLM translation output back into parsed JSON |
| `prepare_zaydi_jsonl.py` | Prepare JSONL input for the translation pipeline |
