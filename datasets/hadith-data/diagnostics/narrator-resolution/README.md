# narrator-resolution (jobs J1, J2, J3)

Diagnostic only. Nothing here asserts a narrator identity, alias, grade, date or translation. Every candidate row is `candidate_only` / `unreviewed`; kunya, prefix, containment and graph-edge matches only rank reviewer attention.

## Inputs (SHA-256)

| File | SHA-256 |
| --- | --- |
| `datasets/hadith-data/all_hadiths_unified.csv.gz` | `f8b5cebf8a379756f1f4703b46d94c5ca1186f9853e1b0ef7a5df0c8f84cc173` |
| `datasets/narrator-data/all_rawis.csv` | `d87c3af64d48b3cd585294ab5f6381536a51ff95a72a6707a7426ea483bf6c11` |

Git HEAD at run time: `af2f90b82da7b7ca8be29a4b8cbb2bb1c2736c46`. Each JSON output also carries a header with these hashes.

## Commands (run from the repo root, in this order)

```
python -B datasets/hadith-data/diagnostics/build_narrator_surface_census.py        # J1, ~47 s
python -B datasets/hadith-data/diagnostics/measure_tier0_resolver_delta.py         # J2, ~50 s (name-invariant dry run)
python -B datasets/hadith-data/diagnostics/rank_narrator_resolution_candidates.py  # J3, ~52 s (needs J1 output)
```

## Files

| File | Rows | What it is |
| --- | ---: | --- |
| `surface_census.jsonl.gz` | 58,028 | One row per distinct unresolved normalized surface, ranked by occurrences, with cumulative share, category, per-tradition and per-source counts, top-10 teacher and student contexts, 5 example rows, prefix/kunya candidate count |
| `surface_curve.json` | 1 | Coverage curve, atomic row curve, categories, candidate availability, review-unit counts, reconciliation with `sanad_resolution_audit.json` (all 8 metrics equal) |
| `name_invariant_delta.json`, `name_invariant_matches.jsonl` (744), `name_invariant_spotcheck_sample.jsonl` (100), `name_invariant_registry_collisions.jsonl` (104) | | Dry run of the name-invariant lookup (rules in `../name_invariant.py`). Changes no resolver |
| `review_queue_surfaces.jsonl.gz` | 10,000 | Top-10,000 surfaces with cumulative coverage and up to 10 ranked candidates each (name-component score plus graph support) |
| `review_queue.jsonl` | 9,083 | Review units for the top-500 surfaces: (surface, context) at the 80% context cut, `decision: null`, ordered by `row_credit_if_scope_resolved` |
| `review_queue_top500_surfaces.csv` | 500 | Skim view for the owner |
| `review_queue_summary.json` | 1 | Candidate-availability buckets and graph-evidence counts |

## State after adoption (2026-11-21)

The canonical resolver now uses the tiered lookup in `datasets/hadith-data/AGENTS.md` ("Narrator identity lookup"). All J1-J3 outputs here are computed with it, so the baseline is the post-adoption one (569 fully resolvable rows, 381,409 unresolved occurrences in 57,490 distinct surfaces). `resolver_adoption_diff.json` and `sanad_resolution_audit_after_adoption.json` hold the before/after proof (`sanad_resolution_audit.json` is untouched).

Command for the proof: `python -B datasets/hadith-data/diagnostics/compare_resolver_before_after.py` (~45 s). Audit: `python -B datasets/hadith-data/audit_narrator_resolution.py --audit-output datasets/hadith-data/diagnostics/narrator-resolution/sanad_resolution_audit_after_adoption.json --candidate-output datasets/hadith-data/diagnostics/narrator-resolution/narrator_alias_candidates_after_adoption.json`.

## How to read the numbers

- **Coverage curve** (`occurrence_coverage_curve`): share of the 381,409 unresolved occurrences cleared if the top N surfaces each got a correct decision for every occurrence. Top 100: 144,253 (37.8%); 500: 225,316 (59.1%); 2,000: 280,707 (73.6%); 10,000: 325,924 (85.5%).
- **Row curve** (`row_curve_atomic_upper_bound`): rows that become fully resolved under the atomic rule if every reviewed surface resolves in every context; an upper bound. 0: 569; 100: 5,755; 500: 17,467; 2,000: 32,020; 10,000: 47,433.
- **Unit**: `(surface, context)`. Context is the teacher (next surface in source order); for relational surfaces (`أبيه`, `و`, ...) it is the previous narrator (`context_axis: "student"`). The snapshot has no `source_work_id`, so source counts are attached instead of keyed.
- **Row credit** (`row_credit_if_scope_resolved`): each row completable if the whole top-500 scope is resolved gives 1/k to each of its k unresolved surfaces; a sorting aid, not a count one decision unlocks.
- **Candidates**: `name_component_score` is matched component weights (ism 0.30, father 0.25, grandfather 0.10, kunya 0.15, nisba 0.15, containment +0.10/+0.05) minus conflict penalties. Graph boosts: exact teacher/student edge +0.5/+0.3; weak edge through an unresolved neighbour with at most 10 candidates +0.1/+0.05; a tabaqah gap outside 0..2 against a resolved teacher -0.3. `margin_top1_top2` near 0 means the evidence does not separate candidates.
- **Remaining diagnostics-only rules** (`name_invariant_delta.json`): hamza on waw/ya carriers and ta marbuta to ha, measured over the canonical baseline: together 24 surfaces, 46 occurrences, 0 rows, 11 registry collision keys. They were not adopted. `name_invariant_spotcheck_sample.jsonl` holds all 24 matches for scholar review.
