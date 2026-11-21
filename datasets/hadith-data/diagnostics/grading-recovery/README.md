# grading-recovery

Load-ready `hadith_assessments` candidate rows and measurements of grading content in local data. Each row names a grader or compiler, is scoped to one tradition, keeps the verbatim Arabic, is `unreviewed`, and has `grade_canonical: null` (no scale mapping, no computed or aggregated grade). The dataset-wide `ثابت` label is never a `grade_raw`; `mine_grading_sources.py` scans the outputs and records the result under `d5_thabit`.

## Inputs (SHA-256)

| File | SHA-256 |
| --- | --- |
| `datasets/hadith-data/all_hadiths_unified.csv.gz` | `f8b5cebf8a379756f1f4703b46d94c5ca1186f9853e1b0ef7a5df0c8f84cc173` |
| `datasets/hadith-data/diagnostics/grading/imami_gradings_structured.jsonl` | `87d08de21628c3b87f5be9f54a9d19ab9a536a82fbb3d38314454b3acbcd85be` |
| `datasets/hadith-data/diagnostics/grading/tirmidhi_compiler_statements.jsonl` | `fe82f63b506fa049406de24cc89f7b92e73d6df0f21be07f9973d0a914fe581c` |
| `datasets/hadith-data/sheikahmad/Hadith-Pure-Canon-Authentica.xlsx` | `2189b0a511d78d1ef05ad3a4bb3c9ca16fccfbdfe415ed910af66ed8aa26cca0` |
| `datasets/hadith-data/shia-hadith/v2_books/*.json` | per-file hashes in `../provenance-recovery/provenance_summary.json` |

## Commands (3 s and 16 s, repository root)

```
python -B datasets/hadith-data/diagnostics/grading-recovery/build_hadith_assessment_rows.py   # D1, D3
python -B datasets/hadith-data/diagnostics/grading-recovery/mine_grading_sources.py          # D2, D4, D5
```

## Files

| File | Rows | Contents |
| --- | ---: | --- |
| `hadith_assessments_imami_cited_ruling.jsonl` | 15,022 | D1. `kind = cited_ruling`, grader (Majlisi 13,866, Mohseni 822, Behbudi 232, Najafi 102), Arabic term, cited work, volume, page, verbatim entry |
| `imami_non_rulings_excluded.jsonl` | 1,813 | D1. Excluded: `لم يخرجه` 1,734, `سكت عنه` 46, back-references 24, and 9 other non-rulings |
| `hadith_assessments_tirmidhi_compiler_statement.jsonl` | 2,707 | D1. `kind = compiler_statement` after `قال أبو عيسى`, with `char_start`/`char_end` into `text_ar` |
| `tirmidhi_statements_held_back.jsonl` | 785 | D1. No grade term (64), speaker not marked as Abu 'Isa (708), another authority quoted (13) |
| `compiler_criterion_basis.jsonl` | 2 | D3. Work-level basis for the two Sahihs; the criterion text itself needs a citation |
| `compiler_criterion_row_links.jsonl.gz` | 14,966 | D3. One link per Bukhari (7,370) and Muslim (7,596) report to its basis; never a verdict |
| `inline_compiler_statement_candidates.jsonl.gz` | 268 | D4. Speaker phrase plus grade term in the Arabic of other Sunan, the two Sahihs, and Imami/Ibadi works; every one needs review |
| `pure_canon_closing_statement_candidates.jsonl` | 5,354 | D4. Closing statements (workbook column L) that `pure_canon.jsonl` drops; Tirmidhi 2,612 |
| `grading_sources_census.json`, `hadith_assessment_summary.json` | | D2 and D5 numbers |

## Caveats

- `record_id` is not in the preserved snapshot; rows carry `snapshot_id`, `hadith_id`, `source`, `snapshot_line` and (K6) `record_id_candidate = k6:<id>`. The loader rewrites `candidate_id` into `assessment:<record_id>:...`.
- Pure Canon `L`/`K` rows belong to Pure Canon record IDs, not to the K6 rows in the unified CSV; joining them needs a numbering reconciliation that was not attempted.
- The same grader appears twice on one report once (3 entries in one row); the loader keys assessments by (hadith, tradition, grader) and would merge them (`batch-loaders.ts:534`).
