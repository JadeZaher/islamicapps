# publication-status (job J9)

Per-row projection of the finding-07 section f facets from the preserved 26-column snapshot. It describes state; it is not a publication decision and asserts no grade, identity or translation.

## Inputs (SHA-256)

| File | SHA-256 |
| --- | --- |
| `datasets/hadith-data/all_hadiths_unified.csv.gz` | `f8b5cebf8a379756f1f4703b46d94c5ca1186f9853e1b0ef7a5df0c8f84cc173` |
| `datasets/narrator-data/all_rawis.csv` | `d87c3af64d48b3cd585294ab5f6381536a51ff95a72a6707a7426ea483bf6c11` |
| `datasets/hadith-data/curation_dispositions.jsonl` | `3ef63a35b7fa0b7ebade85245d980e2d2872292693145957713fd4c4e03ecba6` |
| `datasets/sources/*.md` front matter | license fields read |

## Command (~49 s)

```
python -B datasets/hadith-data/diagnostics/project_row_publication_status.py
```

## Files

- `row_status.csv.gz` (99,283 rows): `id, hadith_id, tradition, source, upstream_family, rights_status, source_text_status, arabic_letters, translation_state, translation_issue, chain_status, chain_branches, chain_links, chain_links_exact_resolved, chain_absence_hint, grading_status, has_cited_grading, disposition_on_file, ...if_rights_cleared flags, publishable_today_current_gate`.
- `summary.json`: facet totals, per-tradition tables, scenario counts, licenses as stated, method notes.
- `summary_by_collection.csv` (32 collections): every facet value counted per (tradition, source).

## What the numbers mean

- The snapshot has no `record_id`, `source_work_id`, `translation_source` or `translation_review_status`. Upstream family is inferred from tradition, source and URL; translation provenance is inferred from family. `id` is unique (0 duplicates) and joins to `k6:<id>` candidates with a matching `arabic_sha256`.
- `rights_status` is `pending_no_clearance_recorded` for all 99,283 rows: no source document records a cleared right. Every "if rights cleared" figure is a scenario, not today's state. Publishable today under the current gate: 0.
- Scenario if every work's rights were cleared: Arabic displayable 99,260; Arabic with the chain as written 84,778; English shown (source-provided Thaqalayn, clean) 32,433; Arabic with at least one exactly resolved link 29,085; complete exact chain 527; Arabic + English + complete chain 172; rows with cited Imami gradings 14,902.
- `chain_status`: complete_exact 527, partial 28,985, unresolved 55,269, no_chain_extracted 14,500, extraction_failed 2. `source_text_status` is stricter than the plan: fewer than 3 Arabic letters counts as `missing` (23 rows: 8 blank, 15 stubs such as `s`).
- `grading_status`: cited_assessments_present 14,902 (Imami; `لم يخرجه` entries are included, see `../grading/`), collection_label_only_not_a_grade 29,915, compiler_criterion_candidate 14,966 (Bukhari, Muslim), none_recorded_in_corpus 39,500.
- `translation_state` reflects the snapshot: none 30,768 (29,915 classical rows plus 853 K6), present_defective 11,569, present_clean_source_provided_unreviewed 32,433, present_clean_source_status_unknown 22,933, present_clean_provenance_unrecorded 1,580. No row reaches a reviewed state.
- 61,938 snapshot rows carry a non-blank legacy `chain_indx`; this is not the strict candidate's 204 complete chains and is never counted here.
