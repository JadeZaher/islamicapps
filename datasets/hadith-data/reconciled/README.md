# reconciled (non-destructive re-ETL sidecars)

Source data the canonical pipeline drops, recovered from the original files and keyed by the canonical
`record_id`. Nothing here writes `chain_indx`, `text_ar` or any canonical CSV, GZIP or manifest, and nothing here is a
release input. A source-provided id is the source's claim, not a verified identity. Every row carries
`review_state: unreviewed`.

## Build (repository root; deterministic: identical inputs give byte-identical outputs)

```
python -B datasets/hadith-data/reconciled/build_k6_source_index_sidecar.py     # about 1 minute
python -B datasets/hadith-data/reconciled/build_pure_canon_chain_sidecar.py    # about 1 minute
```

The scripts reuse `diagnostics/chain-reconciliation/reconcile_common.py` (corroboration tiers, alignment) and import
the canonical normalizer and extractor at run time. The output layout is fixed: JSON with sorted keys, gzip mtime 0,
and no timestamps. Input and code SHA-256 values, output hashes and counts are in each `*.manifest.json`.

## Files

| File | Key | Contents |
| --- | --- | --- |
| `k6_source_index.jsonl.gz` | `k6:<id>` (the canonical K6 key from `all_hadiths_clean.csv.gz`) | Original K6 `chain_indx` from `archive/datasets.7z` as an ordered id list, `agreement_class` against the Arabic, `basis`, per-position name tiers or aligned positions, ids missing from the registry, `arabic_sha256` for join verification |
| `pure_canon_chain.jsonl.gz` | `pure-canon:<pc id>` | The source's separate `chain` text byte-for-byte, `chain_sha256`, the canonical extractor's branches, `chain_status`, and how many surfaces a `text_ar` extraction would invent (`text_ar` is matn only for these works) |
| `no_chain_in_source.jsonl.gz` | `pure-canon:<pc id>` or the canonical `thaqalayn:` key | Reports whose source has no isnad (`source_dataset_ships_no_chain`: Pure Canon rows without `chain`, all of Shafi'i; `work_without_isnad_by_design`: Nahj al-Balagha). `suppress_extracted_chain: true`: never show a chain extracted from their text |

## Basis labels (K6)

| `basis` | When |
| --- | --- |
| `source_index_corroborated_by_text` | `full_agreement` (same length, every position name-consistent) or `multi_branch_all_source_ids_aligned` |
| `source_index_<class>` | Any other class: `same_length_name_mismatch`, `length_differs_source_longer`, `length_differs_text_longer`, `multi_branch_partial`, `no_text_chain`, `extraction_limit` |
| `no_source_index` | The original row had no ids |

Corroboration tiers and the alignment rule are described in `diagnostics/chain-reconciliation/README.md` §Method.
Corroboration uses the resolver at build time, so rebuild after any resolver change.

## Joins

- **K6.** The original CSV's `id` is not unique, so rows join by file position. The Arabic and the source label must
  be byte-identical to the canonical input; a mismatch aborts the build.
- **Pure Canon.** Rows come straight from `pure_canon.jsonl` for the four ingested works. The key is the loader's own
  `pure-canon:<id>`.
- **Nahj al-Balagha.** The key is built with `regen.apply_thaqalayn_identity` from the provider file id and the
  upstream hadith id.

## Not carried

The Pure Canon closing compiler statements (workbook column L) and edition header rows are already extracted by
`diagnostics/grading-recovery/` and `diagnostics/provenance-recovery/`. The Companion-named column was not attempted.
