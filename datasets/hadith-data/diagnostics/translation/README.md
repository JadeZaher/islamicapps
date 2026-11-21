# translation (jobs J7, J7b)

Offline, no model calls. English is never copied into outputs (J7b stores hashes and lengths only). Nothing here is a translation override or review decision.

## Inputs (SHA-256)

| File | SHA-256 |
| --- | --- |
| `datasets/hadith-data/all_hadiths_unified.csv.gz` | `f8b5cebf8a379756f1f4703b46d94c5ca1186f9853e1b0ef7a5df0c8f84cc173` |
| `machine_translation_candidates/local_lmstudio_candidates.jsonl` | `67b3715e226e211ee257d5cd9421e51caaba59e7a3a4b682bab4851409ddd7a1` |
| `machine_translation_candidates/openrouter_gemini_2_5_flash_v7_full_resilient3_2026-07-22.jsonl` | `de9a9e5e04c33d9ad32e246789d213b9b72a7aa5a1927a4b7710b0c21960b616` |
| `machine_translation_candidates/openrouter_gemini_2_5_flash_v8_suffix_2026-07-22.jsonl` | `387eaa16c8fcd42f40bbd9fab72754266ed8f4b886b8ee51046352fa2369a891` |

## Commands (J7 first; J7b uses its glyph bucket)

```
python -B datasets/hadith-data/diagnostics/triage_translation_leakage.py        # ~21 s
python -B datasets/hadith-data/diagnostics/build_translation_review_queue.py    # ~3 s
```

## Files

| File | Rows | Meaning |
| --- | ---: | --- |
| `leakage_buckets.jsonl` | 11,544 | Every snapshot row whose English has Arabic-script characters, with bucket, Arabic-letter ratio, longest Arabic run and the first Arabic span |
| `other_translation_issues.jsonl` | 30,793 | missing 30,768, same_as_arabic 14, placeholder 10, suspiciously_short 1 |
| `summary.json` | 1 | Issue counts and leakage buckets by tradition and collection |
| `review_queue.jsonl` | 5,006 | One row per record with an accepted machine candidate, ordered by risk stratum, with candidate pointers (artifact path, line, text hash) |
| `review_queue_summary.json` | 1 | Strata, sources, per-file event counts, glyph cross-check |

## What the numbers mean

- Leakage buckets: honorific_glyph_or_mark_only 10,666 (92.4%; the English contains only the ﷺ ligature and no Arabic letters), names_or_terms_only 555, partial_untranslated 304, fully_arabic 19. By tradition: Sunni 10,650 (all glyph-only), Imami 752, Zaydi 105, Ibadi 37.
- The snapshot total (11,544) is below the report's 11,953 because the snapshot carries no recovered classical English and the strict candidate differs.
- Review queue: 5,024 accepted candidate events over 5,006 records (18 records have two candidates). All are Sunni K6 (Abu Dawud 3,950, Tirmidhi 533, Muslim 350, Bukhari 173). `arabic_sha256` matches the snapshot Arabic for 5,024 of 5,024 events. Strata: doctrinal_or_legal_marker 499, sampled_general 441 (sha256(record_id) % 10 == 0), general_remainder 4,066; there are no Imami candidates, so the Imami stratum is empty. Marker lists are triage hints only.
- 4,418 of the 5,006 queued records had only the ﷺ ligature as their Arabic-script leakage in the snapshot.
