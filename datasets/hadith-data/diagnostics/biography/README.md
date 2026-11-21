# biography (job J8)

Defect flags about the narrator lexicon (`all_rawis.csv`, uncited vocabulary). They correct nothing and assert no date.

## Input (SHA-256)

`datasets/narrator-data/all_rawis.csv`: `d87c3af64d48b3cd585294ab5f6381536a51ff95a72a6707a7426ea483bf6c11`

## Command (~1 s)

```
python -B datasets/hadith-data/diagnostics/report_narrator_lexicon_defects.py
```

## Files and numbers

- `lexicon_defects.jsonl` (236 flags): inverted birth/death Hijri 38, birth Gregorian disagrees with Hijri by more than 3 years 50, death Gregorian disagrees 27, death Hijri equal to 0 (suspected sentinel) 121.
- `lexicon_defects_summary.json`: 24,326 rows; 20,363 (83.7%) have neither a Hijri birth nor death year; `death_reason = Natural` on 20,325 rows that have no death date at all (looks like a default); 18 death years where the count is at least 3 times the neighbouring years (for example 100: 123 narrators, 250: 71, 3: 87), which suggests round-number defaulting; 455 normalized Arabic names are shared by two or more scholar IDs (these stay ambiguous in exact lookup).
- `narrator_priority.csv` (24,326 rows): ranked by `teachers_inds` + `students_inds` count. This is registry graph degree, not resolved-chain frequency; refresh it once review decisions exist.
