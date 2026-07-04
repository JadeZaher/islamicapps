# Validation Report — 2026-06-20

**Input:** datasets\hadith-data\__tests__\fixtures\tahweel-gold.jsonl
**Rows:** 5
**Pass rate:** 0/5 (0.0%)
**Mode:** default

## Aggregate failure histogram

| Check | Fail count | Warn count |
|---|---:|---:|
| V-1 | 0 | - |
| V-2 | 0 | - |
| V-3 | 0 | - |
| V-4 | 0 | - |
| V-5 | 0 | - |
| V-6 | 5 | - |
| V-7 | 5 | - |
| V-8 | 5 | - |

## Per-row results

### Row 1 — `hadith_id: 30001` — FAIL

- V-1: PASS
- V-2: PASS
- V-3: PASS
- V-4: PASS
- V-5: PASS
- V-6: FAIL (`difficulty is null or missing`)
- V-7: FAIL (`annotator field is missing`)
- V-8: FAIL (`annotated_at field is missing`)

### Row 2 — `hadith_id: muslim-1` — FAIL

- V-1: PASS
- V-2: PASS
- V-3: PASS
- V-4: PASS
- V-5: PASS
- V-6: FAIL (`difficulty is null or missing`)
- V-7: FAIL (`annotator field is missing`)
- V-8: FAIL (`annotated_at field is missing`)

### Row 3 — `hadith_id: muslim-2` — FAIL

- V-1: PASS
- V-2: PASS
- V-3: PASS
- V-4: PASS
- V-5: PASS
- V-6: FAIL (`difficulty is null or missing`)
- V-7: FAIL (`annotator field is missing`)
- V-8: FAIL (`annotated_at field is missing`)

### Row 4 — `hadith_id: muslim-31` — FAIL

- V-1: PASS
- V-2: PASS
- V-3: PASS
- V-4: PASS
- V-5: PASS
- V-6: FAIL (`difficulty is null or missing`)
- V-7: FAIL (`annotator field is missing`)
- V-8: FAIL (`annotated_at field is missing`)

### Row 5 — `hadith_id: muslim-102` — FAIL

- V-1: PASS
- V-2: PASS
- V-3: PASS
- V-4: PASS
- V-5: PASS
- V-6: FAIL (`difficulty is null or missing`)
- V-7: FAIL (`annotator field is missing`)
- V-8: FAIL (`annotated_at field is missing`)
