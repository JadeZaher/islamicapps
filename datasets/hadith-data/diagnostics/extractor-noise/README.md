# extractor-noise (job J5)

Stratified samples of suspicious unresolved surfaces for gold-set expansion. Does not touch `__tests__/fixtures`. Labels are unreviewed hints.

## Input (SHA-256)

`datasets/hadith-data/diagnostics/narrator-resolution/surface_census.jsonl.gz` (J1 output): `sha256` recorded in `summary.json`; the row text comes from `all_hadiths_unified.csv.gz` (`f8b5cebf8a379756f1f4703b46d94c5ca1186f9853e1b0ef7a5df0c8f84cc173`).

## Command (~3 s)

```
python -B datasets/hadith-data/diagnostics/sample_extractor_noise.py
```

## Files and numbers

- `samples.jsonl` (180, not 200: only 21 relational surfaces and 29 singleton single-token surfaces exist for their quotas): relational_or_fragment 21, other_multi_token singletons 100, collective_or_anonymous singletons 30, single-token singletons 29. Each has the row reference, raw surface, the surrounding Arabic (`context_ar`, found for 131 of 180) and noise hints.
- `summary.json`: hint counts over the whole census. Surfaces with 8 or more tokens: 6,014 `other_multi_token` and 2,878 `ism_nasab` (likely run-on spans); `other_multi_token` surfaces containing a transmission or speech word: 435 (809 occurrences); one- or two-character surfaces: 57 single-token plus 6 relational (762 occurrences).
