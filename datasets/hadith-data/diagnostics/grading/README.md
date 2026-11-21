# grading (jobs J6a, J6b, J6c)

Quotes and counts only. No term is mapped to a scale, no grade is assigned, nothing is imported.

## Inputs (SHA-256)

| File | SHA-256 |
| --- | --- |
| `datasets/hadith-data/all_hadiths_unified.csv.gz` | `f8b5cebf8a379756f1f4703b46d94c5ca1186f9853e1b0ef7a5df0c8f84cc173` |
| `datasets/hadith-data/archive/sheikahmad-pure-canon/pure_canon.jsonl` (J6c) | `0cb5ec01959b326c895a6063574955997067e8646c103863285403c3ba6550ac` |
| `datasets/hadith-data/archive/sheikahmad-pure-canon/green_book.jsonl` (J6c) | `3da853cc8694897c0667242a06a8bbc294bd5b5cb8393d6bc777f3b8030eb588` |
| `datasets/sources/sheikahmad-pure-canon.md` (J6c) | `6a91d372b87ec28f6621b3b121588a68336ad0b469a578f959fd60b2737ea966` |

## Commands (each 3-4 s)

```
python -B datasets/hadith-data/diagnostics/parse_imami_gradings.py
python -B datasets/hadith-data/diagnostics/extract_tirmidhi_compiler_statements.py
python -B datasets/hadith-data/diagnostics/audit_pure_canon_ruling_label.py
```

## Files and numbers

- J6a `imami_gradings_structured.jsonl` (16,835 entries from 14,902 rows) with `parse_failures.jsonl` (0). Fields: row reference, grader, `term_ar` (verbatim), `cited_work`, `volume`, `page`, `raw`. 14,275 entries have a volume/page locator; 854 rows have none (typically a work-level citation such as `(Sahih al-Kafi)`). Graders: Majlisi 13,942, Behbudi 1,966, Mohseni 825, Najafi 102. 362 distinct terms (spelling variants such as `ضعیف` with a Persian ya are separate). Caution: `لم يخرجه` ("he did not include it", 1,734 entries), `سكت عنه` (46) and the back-reference `كالسابق` (21) are not rulings, so "row has a cited grading" (14,902) overstates rows with a ruling.
- J6b `tirmidhi_compiler_statements.jsonl` (3,492 statements in 3,401 of 4,214 Tirmidhi rows). Regex-detected, quoted verbatim with `char_start`/`char_end` into `text_ar`; 2,730 follow `قال أبو عيسى`; 25 carry a hint that another authority is being quoted. Term sets (in source order): `حسن صحيح` 1,613, `حسن غريب` 550, `غريب` 385, `حسن` 374, `حسن صحيح غريب` 248, `صحيح` 98. Every hit needs review.
- J6c `pure_canon_label_audit.json`: the upstream field `ruling` has the single value `ثابت` on all 100,217 `pure_canon.jsonl` rows, including Sahih al-Bukhari (6,273), Sahih Muslim (4,805) and the Albani anthology (35,487). The snapshot copies it into `grade_tradition`, `grade_source` and `grade_value` on exactly the 29,915 rows of Ahmad (23,529), Darimi (2,477), Shafi'i (2,054) and Muwatta (1,855), matching the upstream counts. It carries no per-hadith information.
