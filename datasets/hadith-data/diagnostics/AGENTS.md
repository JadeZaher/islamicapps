# diagnostics

Standalone, standard-library Python jobs for the data-gap plan (`.omc/research/pg-refactor/07-data-gaps.md`, section g). Each job reads canonical inputs and writes only new files under `diagnostics/<job-name>/`; each output directory has a README with input hashes, the command and how to read the numbers. Nothing here is a curation manifest, override, registry change or publication claim, and no job asserts an identity, alias, grade, date or translation.

## Modules

- `diagnostic_common.py`: paths, hashing, header object, output-path guard (writes cannot leave `diagnostics/`), corpus streaming, loaders for `regen_unified_csvs.py` and `extract_isnad_unified.py` (bytecode writing disabled so no `__pycache__` appears beside canonical modules).
- `narrator_surface_logic.py`: pure logic (surface categories, name-component parsing, candidate scoring, Tier-0 lookup rules). Tested by `test_narrator_surface_logic.py` (`python -B -m unittest test_narrator_surface_logic` from this directory).

## Job map

| Job | Script | Output directory |
| --- | --- | --- |
| J1 | `build_narrator_surface_census.py` | `narrator-resolution/` |
| J2 | `measure_tier0_resolver_delta.py` | `narrator-resolution/` |
| J3 | `rank_narrator_resolution_candidates.py` | `narrator-resolution/` |
| J4 | not built: needs network | |
| J5 | `sample_extractor_noise.py` | `extractor-noise/` |
| J6a | `parse_imami_gradings.py` | `grading/` |
| J6b | `extract_tirmidhi_compiler_statements.py` | `grading/` |
| J6c | `audit_pure_canon_ruling_label.py` | `grading/` |
| J7 | `triage_translation_leakage.py` | `translation/` |
| J7b | `build_translation_review_queue.py` | `translation/` |
| J8 | `report_narrator_lexicon_defects.py` | `biography/` |
| J9 | `project_row_publication_status.py` | `publication-status/` |

## Design notes

- The preserved snapshot has 26 columns and no `record_id`; rows are referenced by `id`, `hadith_id`, `source` and file line. `k6:<id>` candidate IDs join to `id` and verify against `arabic_sha256`.
- Resolution uses the audit's exact path (`extract_isnad_branches`, `narrator_normalize`, `build_narrator_index`), so totals reconcile with `sanad_resolution_audit.json`.
- Candidate scoring weights and thresholds are triage aids for reviewer attention. They are not confidence in identity.
