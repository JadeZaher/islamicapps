# Hadith Grade Normalization

## Problem

The audit found ~200+ distinct `display_grade` strings on Hadith nodes, with massive fragmentation:

| Category | Example grades | Count |
|---|---|---|
| Empty string | `""` | 53,676 |
| Sunni standard | `THABIT` | 29,917 |
| Shia detailed (Arabic) | `صحيح`, `حسن`, `ضعيف`, `موثق`, `مجهول`, `مرسل` | ~12,000 |
| Compound grades | `حسن كالصحيح`, `ضعيف على المشهور`, `مختلف فيه` | ~2,000 |
| Multi-chain grades | `صحيح وسنده الثاني حسن` | ~200 |
| NULL | — | 627 (Zaydi) |
| Romanized | `SAHIH`, `DAIF` | 4 |
| OCR/spacing variants | `ضعیف` vs `ضعيف`, `موثق على الظاه ر` vs `موثق على الظاهر` | ~100 |

This fragmentation makes it impossible to filter, aggregate, or use grades as features in any analytics pipeline.

## Goal

Create a two-tier grading system:
1. **`grade_canonical`** — normalized broad category: `sahih`, `hasan`, `da'if`, `mawdu'`, `mursal`, `majhul`, `mukhtalaf`, `ungraded`
2. **`grade_detail`** — cleaned version of original grade with OCR/spacing fixes, preserving scholarly nuance

Preserve original `display_grade` untouched.

## Constraints

- Never modify `display_grade` — it's the original source data
- Mapping must be tradition-aware (Shia grades like `موثق`/`معتبر` have no Sunni equivalent)
- Grade taxonomy should be extensible for future scholarly review
- Store mapping table as a reusable constant file

## Success Criteria

- Every hadith has a non-empty `grade_canonical`
- grade_canonical has <15 distinct values
- grade_detail has <50 distinct values (cleaned of spacing/OCR variants)
- Mapping table documented and reviewable
