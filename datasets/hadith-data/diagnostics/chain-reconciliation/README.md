# chain-reconciliation (diagnostic only)

Can the data already on disk reconcile the chain and narrator-identity gaps, and what would outside data add?
Every output here is **evidence and candidates, unreviewed**. A source id is the source's claim, not a verified
identity. Nothing in this directory asserts an identity, merges registry entries, fabricates a chain or changes a
canonical asset. Basis labels are listed under "Basis labels".

## Inputs (SHA-256, final sweep 2026-11-21T15:08Z, git HEAD `86d90e0f`)

| Input | SHA-256 |
| --- | --- |
| `datasets/hadith-data/all_hadiths_unified.csv.gz` (committed 26-col master) | `f8b5cebf8a379756f1f4703b46d94c5ca1186f9853e1b0ef7a5df0c8f84cc173` |
| `datasets/narrator-data/all_rawis.csv` | `d87c3af64d48b3cd585294ab5f6381536a51ff95a72a6707a7426ea483bf6c11` |
| `datasets/archive/datasets.7z` | `2822d053998fd52f9b8482478262ecc6238d9be3cad58e9518a76f74480df378` |
| member `datasets/hadith-data/all_hadiths_clean.csv` (original K6 download) | `a6800edb54d45a6e6c5228cf0342c0c72d90eca62a857bcbb5c61684e550db15` |
| `datasets/hadith-data/regen_unified_csvs.py` (canonical normalizer, imported at runtime) | `c0064fb29ffd4fbbc86a5f25f25862020dcd28de7991a59b74d927c632161435` |
| `__tests__/fixtures/all-tradition-isnad-gold-v1.jsonl` (excluded from the sample) | `28259581ffda5678ee43f1339e09e575c2689c5ff9978891fc5c72822ba6b430` |

The other inputs are Pure Canon `pure_canon.jsonl`, Thaqalayn `v2_books/*.json`, OpenITI `parsed_hadiths.json`, and
the external texts in `datasets/sources/external/`. Each JSON output's `header.inputs_sha256` carries their hashes.
The normalizer features present at run time were `narrator_fold_normalize`, `fold_kunya_case_forms`,
`kunya_fold_allowed`, `strip_blessing_formulas` and `_extract_arabic_name_raw`, i.e. the tiered resolver. The
baseline reproduces it exactly: 56,067 of 437,476 occurrences resolved, 569 rows complete, 57,490 distinct
unresolved surfaces.

## Commands (repo root, in order; about 5 minutes in total)

```
python -B datasets/hadith-data/diagnostics/chain-reconciliation/measure_source_index_agreement.py   # Q1, 52 s
python -B datasets/hadith-data/diagnostics/chain-reconciliation/measure_learned_candidates.py       # Q2, 52 s (needs Q1)
python -B datasets/hadith-data/diagnostics/chain-reconciliation/classify_chainless_reports.py      # Q3, 29 s
python -B datasets/hadith-data/diagnostics/chain-reconciliation/audit_reetl_field_carry.py         # Q4, 7 s
python -B datasets/hadith-data/diagnostics/chain-reconciliation/measure_imami_provider_sanad.py    # Q5, 21 s
python -B datasets/hadith-data/diagnostics/chain-reconciliation/measure_rijal_headword_coverage.py # Q5/Q6, 37 s
python -B datasets/hadith-data/diagnostics/chain-reconciliation/draw_validation_sample.py          # Q7, 33 s
python -B datasets/hadith-data/diagnostics/chain-reconciliation/inventory_local_assets.py          # Q0, 13 s
```

The original K6 CSV is streamed out of `datasets.7z` with Windows' bundled bsdtar (`C:\Windows\System32\tar.exe`,
override with `BSDTAR=`). Git Bash's GNU tar cannot read 7z.

## Method

- **Joins.** The first 34,441 master rows are the K6 original in the same order, with byte-identical Arabic
  (34,441 of 34,441 verified). K6 `id` is not unique (1,150 distinct values), so position plus exact Arabic is the
  key. Pure Canon, Thaqalayn and OpenITI join on exact stripped Arabic and require a unique match.
- **Corroboration tiers** (`reconcile_common.name_tier`). They compare a text surface with the registry entry the
  index names at the same position, under the canonical fold plus the diagnostic name-invariant rules:
  - `resolver_same_id`
  - `full_name_key`
  - `relational_parent_attested` / `relational_grandparent_attested`: `أبيه`/`جده`, where the id is in the previous
    id's registry `parents` field
  - partial-name tiers `name_tokens_subsumed` (ordered), `name_tokens_all_present` (any order) and
    `ism_nasab_core_agrees` (the `X بن Y` core matches and extra nisbas are absent from the registry)
  - non-corroborating tiers `partial_token_overlap`, `no_token_overlap`, `relational_unattested`,
    `source_id_not_in_registry`

  Resolver conflicts are counted separately.
- **Classes.** For a single text branch, positions are compared one to one when lengths match. Otherwise, and for
  multi-branch rows, an order-preserving alignment (LCS) counts corroborated pairs.
- **Learned candidates.** Every corroborated position gives an observation `(fold key, teacher, student) -> id`.
  The rule takes the most specific unique context: teacher, then student, then the surface alone. Candidates are
  applied only to Sunni rows. Hits on Imami, Ibadi and Zaydi rows are reported as cross-tradition name matches and
  are never counted.

## Results

### Q1 Agreement matrix (`output/agreement_matrix.json`)

| Class | K6 source index (`chain_indx` in the original download) | Legacy master `chain_indx` (older local resolver; feeds the live links) |
| --- | ---: | ---: |
| full_agreement (same length, every position corroborated) | **11,523** | 5,426 |
| multi_branch_all_source_ids_aligned | **4,178** | 4,548 |
| same_length_name_mismatch | 3,927 | 6,271 |
| length_differs, source longer | 3,099 | 3,936 |
| length_differs, text longer | 8,215 | 26,848 |
| multi_branch_partial | 3,356 | 8,060 |
| no_text_chain | 19 | 6,848 |
| no_source_index / extraction_limit | 123 / 1 | 0 / 1 |
| **source ids corroborated by aligned text** | **155,514 / 175,695 (88.5%)** | 106,778 / 160,633 (66.5%) |

- **Key number.** 15,701 K6 reports (11,523 + 4,178) have every source-provided id corroborated by the Arabic text.
  This is `source_index_corroborated_by_text`. Only 5 of them are corroborated by full names alone, so the evidence
  is mostly name-consistency (`name_tokens_subsumed`): the text says `سفيان`, and the source says which Sufyan.
- **Resolver conflicts.** In equal-length rows the strict resolver resolves 15,941 surfaces. It agrees with K6 on
  7,904 and **disagrees on 8,037**, and in 7,427 of those disagreements the surface's name is consistent with the
  K6 id. The cause is bare-name registry stubs: `شعبة`, which K6 gives as Shu'bah b. al-Hajjaj (20020), resolves to
  29483 "Sh'bh Shykh" (1,236 times), and `حماد`, `عطاء` and `ثابت` behave the same way. Every bare `عبد الله`
  resolves to "'Abdullah ('Abd Rabb) bin Haq", because that name's nested parenthesis leaves `عبد الله` as its key.
  Pairs are in `resolver_conflicts.jsonl`.
- **Legacy index.** Of 34,324 K6 rows, 18,168 legacy rows equal the K6 index and 24,194 are subsets. Legacy Imami
  rows are partial: 9,313 of 10,688 are shorter than the text chain.
- 103 K6 ids (2,059 occurrences) are missing from `all_rawis.csv`.

### Q2 Cumulative coverage (`output/learned_candidates.json`)

Learned observations: 155,514 observations over 6,297 keys; 6,071 keys map to exactly one id. Of 226 keys with
several ids, 26,420 of their 49,700 observations fall in a teacher context that has a single id.

Leave-one-out agreement with the source's own id:

| Rule | Agrees with source id |
| --- | --- |
| teacher context | 99.5% (108,674 / 109,215) |
| student context | 98.9% |
| surface only | 99.5% |

This is consistency with the same source, not accuracy.

Unresolved keys that receive at least one observation: 4,772 of 55,571 (canonical fold), covering 192,420 of
381,409 unresolved occurrences.

**View A: master `text_ar` as committed (the 437,476 baseline)**

| Strategy (cumulative) | Basis | Occurrences | Rows complete (atomic) |
| --- | --- | ---: | ---: |
| S0 strict resolver | `canonical_exact_resolver` | 56,067 | 569 |
| S1 + K6 index corroborated by text | `source_index_corroborated_by_text` / `source_index_aligned_partial` | 178,692 | 15,628 |
| S2 + learned, unique in context (Sunni only) | `learned_from_corroborated_context` | 207,173 | 18,402 |
| S3 + learned, unique for surface (Sunni only) | `learned_from_corroborated_context` | 207,960 | 18,639 |

By tradition at S3, occurrences then rows: Sunni K6 195,432 / 18,010; Pure Canon about 425 / 443; Imami 11,989 / 176;
Ibadi 110 / 6; Zaydi 4 / 4. Imami, Ibadi and Zaydi gain nothing. Their 19,172, 1,176 and 753 cross-tradition name
matches are withheld.

**View B: the Pure Canon `chain` field used as chain text (re-ETL)**

| Strategy | Occurrences | Rows complete |
| --- | ---: | ---: |
| S0 | 83,124 / 533,885 | 728 |
| S1 | 205,749 | 15,787 |
| S2 | 298,058 | 26,316 |
| S3 | 304,629 | **27,694** |

At S3: Musnad Ahmad 7,416 rows, Muwatta 1,216, Darimi 866.

View A's Pure Canon rows are extracted from matn text. Those 32,595 "occurrences" (13,909 Ahmad rows) are noise.
View B replaces them with 129,004 real chain occurrences.

### Q3 The 14,500 rows with no chain (`output/chainless_classification.json`, `chainless_samples.jsonl`)

| Class | Rows | Collections | A re-extraction fixes it? |
| --- | ---: | --- | --- |
| chain_in_separate_source_field_dropped_from_text_ar | 11,046 | Ahmad 9,519, Darimi 857, Muwatta 670 | **Yes**: re-ETL from `pure_canon.jsonl` `chain` |
| source_dataset_ships_no_chain | 1,136 | Shafi'i 1,012 (all), Ahmad 101, Muwatta 15, Darimi 8 | No: Pure Canon stripped them; needs another edition |
| work_without_isnad_by_design | 1,060 | Nahj al-Balagha | No (by design) |
| compiler_omitted_isnad (Faqih) | 541 | Man La Yahduruhu al-Faqih | No: the routes are in Saduq's Mashyakha, which is not on disk |
| no_transmission_wording_found | 395 | Imami and K6 fragments, birth/death notes | Mostly no; sample first |
| opens_with_attribution_no_isnad | 206 | mixed | No (mursal or omitted) |
| extractor misses (`transmission_wording_present` 33, `provider_english_sanad_has_chain` 22, `source_index_present` 19, `parser_sanad_present` 13) | 87 | mixed | Yes, by an extractor fix |
| isnad_by_reference_to_previous_report | 14 | Kafi, Mu'min, Ghayba | Model as a reference (`وبهذا الإسناد`) |
| text_missing / truncated | 15 | | No |

Re-extraction fixes **11,046 + 87 = 11,133** rows. Also, 1,200 of the 2,260 Nahj al-Balagha rows and 1,042 Shafi'i
rows get false "chains" from their matn.

### Q4 Re-ETL by source (`output/reetl_field_carry.json`)

| Source | Field lost or flattened | Re-ETL? | Gain / cost |
| --- | --- | --- | --- |
| K6 | Original `chain_indx`: overwritten in 16,156 rows, equal in 18,168. Only the 7z keeps it | **Yes**, as a sidecar, not as `chain_indx` | 175,695 attested links, 15,701 fully corroborated reports. Read-only, no network, about 1 minute |
| Pure Canon (Ahmad, Darimi, Muwatta) | `chain` is never in `text_ar`; only the extracted surfaces survive, in `sanad`. `shelf_no` is dropped | **Yes** | 11,046 chainless rows recovered; 129k chain occurrences; S3 rows 18,639 to 27,694 (+9,055). Small change in the classical loader |
| Pure Canon Shafi'i | None (the source has no chain) | No | Needs a different edition (OpenITI `0204Shafici`), with rights review |
| Thaqalayn | Nothing chain-bearing: the English sanad is kept verbatim in `sanad`, grading is kept, no ids exist upstream | No | 1,974 rows do not join on exact Arabic (text drift); refresh only for freshness |
| OpenITI Ibadi/Zaydi/Rida | `sanad_detail` (local parser output, with `tabaqah`) flattened to names | No (local, not source data) | |

### Q5 Imami identity (`output/imami_provider_sanad.json`, `imami_surface_lexicon.jsonl.gz`, `rijal_headword_coverage.json`)

- Thaqalayn ships **no narrator ids and no rijal endpoint**. Its V2 endpoints are books, query, random and
  ingredients.
- The Arabic chains hold 171,124 occurrences over 21,015 distinct keys and 43,787 teacher-student edges. The top
  500 keys cover 71.7% of occurrences.
- Pairing the English sanad with Arabic (same length, 11,890 reports) yields English forms for 7,071 keys, covering
  86.1% of Imami occurrences. 5,185 keys have a single English form.
- That gives a **surface lexicon with graph context**, not a registry. It cannot by itself say that two `محمد بن يحيى`
  are one person.
- The 11,989 Imami occurrences the strict resolver resolves today point into the Sunni-centred lexicon and are
  largely wrong. `سعد بن عبد الله` resolves to a Companion 1,518 times, and `حماد`/`حريز` resolve to "Shykh" stubs.
- With the downloaded Najashi, Tusi Rijal and Fihrist, 58.7% of unresolved Imami occurrences match at least one
  entry headword (72.1% of the top 500). Only 8,657 occurrences match exactly one entry. The others are homonyms:
  2-5 entries for 38,586 occurrences and 6 or more for 46,279.

### Q6 External datasets (captures in `research/`)

| Rank | Dataset | Adds | Size, format | Licence | Join to our ids | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | OpenITI rijal: Najashi, Tusi Rijal and Fihrist, Kashshi/Ikhtiyar, Taqrib, Tahdhib al-Kamal | Imami entity space (absent today); Sunni teacher/student lists | 0.4-25 MB, mARkdown | CC BY-NC-SA 4.0 (Zenodo 17767721) | Headword match plus context; Imami ids keyed by work and entry | **Downloaded** to `datasets/sources/external/` |
| 2 | hadith-kg (emadjumaah, HF) | 577,024 complete chains with narrator ids; 49,819 biographies with tabaqa and dates; 127,863 jarh statements | 1.6 GB SQLite | CC BY 4.0 | Text alignment of our K6/PC rows | Not fetched (over 300 MB) |
| 3 | Riwayat corpus (Zenodo 23630501) | 924,787 hadith including about 37K Shi'i; 4.87M mentions with asserted ids; `id_method`; precision 0.98 against MIDS | 577 MB `.db.xz` (4.7 GB unpacked) | CC0 for its own layer; texts inherit hadith-kg CC BY | Text alignment; its `N…` ids | Not fetched (over 300 MB) |
| 4 | Cross-Source Hadith Narrator ER (Zenodo 21019693) | Sanadset names linked to Hawramani and **muslimscholars.info**, the origin of `scholar_indx` | 138 MB zip | **none stated** | Direct join to `scholar_indx` | Not fetched: licence unclear; ask the authors |
| 5 | Sanadset 650K (Mendeley 10.17632/5xth87zwb5.5) | 650,986 hadith with `<NAR>` tags (names, no ids) | 1.43 GB CSV | CC BY 4.0 | Surface forms only | Not fetched (over 300 MB) |
| 6 | isnad-chrono (HF HeshamHaroon) | narrators/chains parquet derived from hdith.com | 25 MB parquet | CC BY 4.0 (card) | hdith.com ids | Not fetched; upstream rights unclear, and parquet needs a non-stdlib reader |
| 7 | Thaqalayn API, sunnah.com | No narrator data / no bulk licence | | | | Nothing to fetch |

### Q7 Validation sample (`output/validation_sample_200.jsonl`, `.csv`)

200 reports, deterministic (seed `chain-reconciliation-validation-v1`), with the 32 gold rows excluded:

- Quotas: Sunni 80, Imami 70, Ibadi 25, Zaydi 25.
- Strata: round-robin over collection × chain length (none, 1-3, 4-6, 7+) × single or branched.
- Pure Canon rows carry their `chain` field as the text.

All annotation fields are null. `extractor_output_reviewer_aid_not_gold` is labelled as an aid only.

## Basis labels

| Label | Meaning |
| --- | --- |
| `canonical_exact_resolver` | The strict tiered resolver (may be wrong; see resolver conflicts) |
| `source_index` | K6 `chain_indx` as shipped |
| `source_index_corroborated_by_text` | K6 id where every position of the report is name-consistent with the Arabic |
| `source_index_aligned_partial` | K6 id at an aligned, name-consistent position in a report that is not fully corroborated |
| `learned_from_corroborated_context` | Id observed for this surface in a teacher/student context in corroborated K6 rows |
| `provider_english_sanad_alignment` | Thaqalayn English name paired with an Arabic surface (translation, not identity) |
| `rijal_headword_name_match` | Surface equals a rijal-work headword key (candidate only) |

## Files

| File | What |
| --- | --- |
| `reconcile_common.py` | Loaders, canonical import, corroboration tiers, alignment |
| `output/agreement_reports.jsonl.gz` | Per report and index: class, ids, branches, per-position tiers, aligned pairs |
| `output/source_index_attested_links.jsonl.gz` | 155,514 per-position K6 links with basis, `review_state: unreviewed` (staged evidence) |
| `output/corroborated_observations.jsonl.gz`, `output/learned_candidate_keys.jsonl.gz` | Learned candidate evidence |
| `output/resolver_conflicts.jsonl` | Strict resolver vs K6 conflicts (first 3,000) |
| `output/local_asset_inventory.json` | Asset table: bytes, SHA-256, rows, columns, chain-field coverage |
| `research/` | Raw API captures (URL in file name; fetched 2026-11-21, generic client, unauthenticated) |

## Addendum 2026-11-21: resolver fix and empty-branch correction (supersedes the numbers above where they differ)

- **Empty branches.** The extractor can return `[[]]`. Earlier counts (this README, and also J1 `surface_curve.json`
  and `sanad_resolution_audit.json`) treated such a row as having a chain and as vacuously "fully resolved".
  427 rows are affected (Sunni 253, Imami 168, Zaydi 4, Ibadi 2). `reconcile_common.Canon.extract` now drops empty
  branches. The real pre-fix baseline is **142** fully resolved rows, not 569, and 14,927 rows have no chain.
- **Resolver fix** (`regen_unified_csvs.py`; contract in `../../AGENTS.md` §Narrator identity lookup).
  - 866 placeholder registry rows are never targets: 446 `Shykh`-marked, 235 kunya-only, 137 bare one-token,
    48 without an Arabic name.
  - An inner alternative keeps the whole Arabic name.
  - `measure_resolver_fix_diff.py` writes `output/resolver-fix/`: `resolution_diff.jsonl` (every surface whose
    resolution changed), `excluded_placeholder_entries.csv`, and `resolver_fix_summary.json` (the diff by class,
    atomic rows before/after, the K6 regression, and the tradition guard, which is measured but not adopted).
- After the fix, `measure_learned_candidates.py` gives:

  | Level | View A rows (master `text_ar`) | View B rows (Pure Canon `chain` field) |
  | --- | ---: | ---: |
  | S0 strict resolver | 72 | 115 |
  | S1 + K6 index corroborated by text | 15,002 | 15,045 |
  | S2 + learned, unique in context | 17,765 | 24,717 |
  | S3 + learned, unique for surface | 18,050 | 26,083 |

  Occurrences under View B: 53,435 → 188,237 → 292,023 → 298,969 of 533,885.
- The `learned_from_corroborated_context` channel is now part of the J3 queue
  (`../narrator-resolution/review_queue.jsonl`).
