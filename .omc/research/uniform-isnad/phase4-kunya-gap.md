# Phase 4 T-4.1 — Kunya-Gap Audit

Source: `datasets/hadith-data/sunni_isnad.jsonl` (K6 sidecar, 34,441 hadith rows).
Resolver: `build_narrator_index` + `resolve_narrator` from
`datasets/hadith-data/regen_unified_csvs.py`.

Methodology: every distinct narrator surface form in the sidecar's `sanad[]`
arrays is fed through `resolve_narrator`. Misses are bucketed by the shape
of the post-`_norm` surface.

Audit script: `.omc/research/uniform-isnad/_phase4_audit.py` (re-runnable).

## Overall (pre-fix → post-T-4.2)

| Metric | Pre-Phase-4 | Post-T-4.2 (unique-kunya aliasing) | Δ |
| :--- | ---: | ---: | ---: |
| Distinct surface forms | 16,079 | 16,079 | — |
| Total occurrences | 111,072 | 111,072 | — |
| Resolved occurrences | 31,747 (28.58%) | 37,400 (33.67%) | **+5,653 (+5.09 pp)** |
| Distinct missed surface forms | 12,216 | 11,868 | -348 |

The K6-sidecar resolution rate (28.58%) is higher than the full-pipeline
22% figure (27,711/125,394) cited in the Phase-2 smoke because that figure
includes additional sources (Muwatta, Nasai) whose chains carry more
abbreviated surface forms. The directional gain on K6 should translate
to a similar absolute lift on the full pipeline — see the Phase-2 smoke
re-run in this phase's report for the actual number.

## Miss categorization — post-T-4.2 (distinct surface forms)

| Category | Distinct misses | Total occurrences | Example surfaces (first 5) |
| :--- | ---: | ---: | :--- |
| multitoken_arabic | 10,991 | 58,744 | `الحميدي عبد الله بن الزبير` · `سفيان` · `محمد بن إبراهيم التيمي` · `ه سمع علقمة بن وقاص الليثي` · `سمعت عمر بن الخطاب` |
| kunya_only | 860 | 10,917 | `ابن عباس` · `أبي صالح` · `أبي هريرة عن` · `أبي قال` · `أبو بردة بن عبد الله بن أبي بردة` |
| pronoun_elided | 3 | 3,865 | `قال` · `أبي` · `أبى` |
| other_garbage | 14 | 146 | `عن` · `إن` · `ذر` · `من` · `أن` |

## Pre-fix categorization (for delta clarity)

| Category | Distinct misses (pre) | Distinct misses (post) | Resolved by T-4.2 |
| :--- | ---: | ---: | ---: |
| multitoken_arabic | 10,991 | 10,991 | 0 |
| kunya_only | 1,208 | 860 | **348 unique kunyas** |
| pronoun_elided | 3 | 3 | 0 |
| other_garbage | 14 | 14 | 0 |

## Notes on scope

- Phase 4 T-4.2 implements **unique-kunya aliasing** only. Aliases that
  map to ≥2 scholars are intentionally left unresolved (no guessing —
  FR-5.2). The 860 remaining `kunya_only` misses are dominated by famous
  ambiguous kunyas (`ابن عباس`, `أبي صالح`, etc.) whose disambiguation
  needs the death-date / teacher-student heuristic that the plan defers
  to a future track.
- The plan's T-4.3 ambiguous-kunya disambiguator is deferred.
- `multitoken_arabic` (10,991 distinct, 58,744 occ) is the **dominant gap**
  and is out of scope for this phase. Sample inspection suggests it is a
  mix of (a) chains with leading verbs (`سمعت عمر بن الخطاب`,
  `أخبرني محمد …`), (b) noisy OCR (`ه سمع علقمة …`), (c) names that
  exist in `all_rawis.csv` but with a slightly different surface
  (e.g. `الحميدي عبد الله بن الزبير` vs. canonical
  `عبد الله بن الزبير الحميدي` reorder). This warrants a dedicated
  follow-up track — see **Follow-ups** below.
- `pronoun_elided` (3 distinct, 3,865 occ) is dominated by `أبي` /
  `أبى` (= "my father") which is **correctly unresolved** by design —
  resolving requires consulting the previous narrator's biography for
  the father's identity (context-sensitive resolution).

## Follow-up track suggestions

1. **Multi-token Arabic surface normalization** (largest remaining gap;
   58,744 occ). Hypotheses: (a) leading verbal-prefix stripping
   (`سمعت X`, `أخبرني X`, `حدثني X` → `X`); (b) token-reorder tolerant
   matching (`الحميدي عبد الله بن الزبير` ↔ `عبد الله بن الزبير الحميدي`).
2. **Ambiguous-kunya disambiguator** (plan T-4.3 deferred). Use
   death-date proximity to adjacent resolved narrators, or
   teacher-student adjacency from the rawi graph, to pick among the
   ≥2 candidates that the current unique-only filter rejects. Targets
   the remaining 860 distinct / 10,917 occ kunya_only bucket.
3. **Father-pronoun resolution** (`أبي` / `أبى`, 3,865 occ). Resolve by
   looking up the preceding narrator's father from `all_rawis.csv`'s
   `parents` field, then re-resolving.
