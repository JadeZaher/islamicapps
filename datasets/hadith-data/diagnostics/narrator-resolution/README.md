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
python -B datasets/hadith-data/diagnostics/measure_tier0_resolver_delta.py         # J2, ~35 s
python -B datasets/hadith-data/diagnostics/rank_narrator_resolution_candidates.py  # J3, ~52 s (needs J1 output)
```

## Files

| File | Rows | What it is |
| --- | ---: | --- |
| `surface_census.jsonl.gz` | 58,028 | One row per distinct unresolved normalized surface, ranked by occurrences, with cumulative share, category, per-tradition and per-source counts, top-10 teacher and student contexts, 5 example rows, prefix/kunya candidate count |
| `surface_curve.json` | 1 | Coverage curve, atomic row curve, categories, candidate availability, review-unit counts, reconciliation with `sanad_resolution_audit.json` (all 8 metrics equal) |
| `tier0_delta.json`, `tier0_matches.jsonl` (815), `tier0_ambiguity_collisions.jsonl` (32) | | Dry run of T0-b/c/d. Changes no resolver |
| `review_queue_surfaces.jsonl.gz` | 10,000 | Top-10,000 surfaces with cumulative coverage and up to 10 ranked candidates each (name-component score plus graph support) |
| `review_queue.jsonl` | 9,083 | Review units for the top-500 surfaces: (surface, context) at the 80% context cut, `decision: null`, ordered by `row_credit_if_scope_resolved` |
| `review_queue_top500_surfaces.csv` | 500 | Skim view for the owner |
| `review_queue_summary.json` | 1 | Candidate-availability buckets and graph-evidence counts |

## How to read the numbers

- **Coverage curve** (`occurrence_coverage_curve`): share of the 387,359 unresolved occurrences cleared if the top N surfaces each got a correct decision for every occurrence. Top 100: 145,552 (37.6%); 500: 227,986 (58.9%); 2,000: 284,584 (73.5%); 10,000: 330,875 (85.4%).
- **Row curve** (`row_curve_atomic_upper_bound`): rows that would become fully resolved under the atomic rule if every reviewed surface resolves in every context. It is an upper bound; ties between equally frequent surfaces make it move by up to ~50 rows with a different tie-break.
- **Unit**: `(surface, context)`. Context is the teacher (next surface in source order). For relational surfaces (`أبيه`, `و`, ...) the axis is the previous narrator (`context_axis: "student"`), because those refer back to it. The snapshot has no `source_work_id`, so the unit is not keyed by work; source counts are attached instead (keying by `(surface, source, teacher)` would need 18,761 units for the top 500 instead of 9,118).
- **Row credit** (`row_credit_if_scope_resolved`): each row that is completable if the whole top-500 scope is resolved gives 1/k to each of its k distinct unresolved surfaces. It is a sorting aid, not a count of rows a single decision unlocks.
- **Candidates**: `name_component_score` is matched component weights (ism 0.30, father 0.25, grandfather 0.10, kunya 0.15, nisba 0.15, containment +0.10/+0.05) minus conflict penalties. Graph boosts: exact teacher/student edge from `teachers_inds`/`students_inds` +0.5/+0.3; weak edge through an unresolved neighbour with at most 10 candidates +0.1/+0.05; a tabaqah gap outside 0..2 against a resolved teacher -0.3. `margin_top1_top2` near 0 means the evidence does not separate candidates. `derived_relation` candidates (`أبيه`/`جده`) come from the registry `parents` field of an exactly resolved previous narrator.
- **Tier 0** (`tier0_delta.json`): T0-b registry alias segments gain 8,671 occurrences but make 22 existing unique exact surfaces ambiguous (3,103 occurrences lost) and 4,576 of the gained occurrences are bare single-token segments. T0-c kunya-head fold gains 2,576. Combined T0-b+c+d: rows fully resolvable 527 to 551.
