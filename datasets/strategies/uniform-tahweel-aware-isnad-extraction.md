---
id: uniform-tahweel-aware-isnad-extraction
name: Uniform Taḥwīl-Aware Isnad Extraction (Tier 1)
status: active
introduced: 2026-06-09
last_reviewed: 2026-06-16

problem_domain: |
  Classical hadith isnads frequently converge: a single matn (main report
  text) can be transmitted via multiple parallel chains that merge at a
  shared narrator partway up the chain. The convergence point is marked
  in the manuscript with the letter ح (taḥwīl, "switch"). A naive parser
  that ignores ح collapses what are in reality N independent chains into
  one corrupted sequence, which then poisons downstream mutawātir
  detection, narrator-reliability inference, and chain-grading.
applies_to_traditions:
  - sunni
  - shia-imami
  - zaydi
  - ibadi
consumes_sources:
  - openiti
  - sunnah-com
  - thaqalayn-api
  - sheikahmad-pure-canon

paths:
  - datasets/hadith-data/extract_isnad_unified.py
  - datasets/hadith-data/regen_unified_csvs.py
  - datasets/hadith-data/algo_candidates/
  - datasets/hadith-data/algo_evaluate.py
  - datasets/hadith-data/audit_tahweel_stats.py
  - conductor/tracks/uniform_isnad_extraction_20260609/spec.md

evaluation_method: |
  Hand-annotated gold-set of 120 hadiths (30 per tradition, balanced
  across 0/1/2/3+ taḥwīl-branch counts). Three candidate algorithms
  baked off (A: greedy split, B: regex-anchor, C: LCS-suffix). Metrics:
  branch-count accuracy (exact match to gold), per-branch Jaccard
  overlap on narrator sequences (median + p10/p90).
evaluation_results: |
  Candidate C (LCS-suffix) selected:
    branch-count accuracy: 1.000
    Jaccard median:        0.845
    Jaccard p90:           0.730
    Jaccard p10:           0.972
  Candidate A: 0.71 branch-count accuracy (lost branches on nested ح).
  Candidate B: 0.94 branch-count accuracy but Jaccard median 0.61
    (false-positive splits on non-taḥwīl ح).
evaluation_artifacts:
  - .omc/research/uniform-isnad/algo-evaluation.md
  - .omc/research/uniform-isnad/

bibtex: |
  @misc{brown-hadith-2009,
    title     = {Hadith: {Muhammad}'s {Legacy} in the {Medieval} and {Modern} {World}},
    author    = {Brown, Jonathan A.C.},
    year      = {2009},
    publisher = {Oneworld Publications},
    note      = {Classical reference for isnad structure and tahweel conventions.}
  }
  @misc{musa-isnad-2008,
    title     = {{Hadith} as {Scripture}: {Discussions} on the {Authority} of
                 {Prophetic} {Traditions}},
    author    = {Musa, Aisha Y.},
    year      = {2008},
    publisher = {Palgrave Macmillan}
  }
---

# Uniform Taḥwīl-Aware Isnad Extraction (Tier 1)

## Problem

A hadith isnad is the chain of transmitters who passed the report down to the collector. Most hadiths have *one* chain; many — especially in the canonical Sunni six and the Imami four-books — have *several*, and the manuscript notation that signals this is the single Arabic letter ح ("ḥāʾ", short for *taḥwīl*, "switch").

The conventional manuscript reads: *Narrator A reported to me from Narrator B from the Prophet — ح — and Narrator C also reported to me from Narrator B from the Prophet.* Two chains share a common upstream subsequence (`B → Prophet`) but diverge in the downstream portion (`A` vs `C`). The ح marker is the seam.

A parser that treats the isnad as a flat sequence loses this structure. Concretely, it produces a single chain `A → B → Prophet → C → B → Prophet` that is both incorrect as transmission history and damaging downstream:

- **Mutawātir detection** (a hadith with N independent corroborating chains crosses a reliability threshold) silently undercounts.
- **Narrator-reliability inference** double-attributes positions to narrators.
- **Visualization** renders nonsense graphs at the convergence point.

The problem compounds because ح is also a regular Arabic letter — it appears in narrator names, in particles, in the body text. A regex that splits on every ح ruins the data in the other direction. The strategy below threads that needle.

## Approach

The Tier-1 parser is a **rule-based** (not LLM) chain extractor that splits a flat isnad string into N independent chain branches. The algorithm has three phases:

1. **Detect** ح occurrences that are *transmission-context* ح (surrounded by transmission verbs / proper names) rather than *lexical* ح (part of a word). The detector is a regex with positive and negative lookaround — the patterns live in `audit_tahweel_stats.py` and are calibrated against the audit's per-source distribution tables.
2. **Split** the isnad at each detected ح into a pre-convergence prefix and the remainder.
3. **Reconstruct** each branch by finding the **longest common suffix** between the prefix and the post-convergence chain (LCS over narrator tokens), then emitting `prefix + shared_suffix` as a full branch. This is the "candidate C" algorithm that won the bake-off.

Output: each hadith row in `all_hadiths_unified.csv` gets a `chain_indx` field that is a `|`-delimited list of branches, one per detected chain. A hadith with no ح gets a single-branch list — no downstream caller needs to special-case "branchless" rows.

Implementation: [`datasets/hadith-data/extract_isnad_unified.py`](../hadith-data/extract_isnad_unified.py) (the standalone algorithm) is invoked from [`datasets/hadith-data/regen_unified_csvs.py`](../hadith-data/regen_unified_csvs.py)'s `_compute_chain_indx()` during the regen pipeline.

## Why we picked this over alternatives

| Candidate | Branch-count accuracy | Jaccard median | Why we (didn't) pick it |
| --- | --- | --- | --- |
| A: Greedy left-to-right split | 0.71 | 0.79 | Loses branches on nested ح (e.g. three-way convergence). |
| B: Regex-anchor on transmission verbs | 0.94 | 0.61 | High branch recall but false-positive splits on lexical ح inside narrator names — corrupts ~6% of branches. |
| **C: LCS-suffix (selected)** | **1.000** | **0.845** | Correct branch count on every gold-set fixture; suffix-recovery is robust to varying verb forms. |

The bake-off lives at [`.omc/research/uniform-isnad/algo-evaluation.md`](../../.omc/research/uniform-isnad/algo-evaluation.md). The candidates themselves are checked in under [`datasets/hadith-data/algo_candidates/`](../hadith-data/algo_candidates/) and re-runnable via [`algo_evaluate.py`](../hadith-data/algo_evaluate.py) — anyone proposing a new algorithm should add it there and re-run the bake-off rather than swap the production parser in-place.

## Evaluation

- **Method:** 120-fixture hand-annotated gold-set, balanced 30-per-tradition × {0, 1, 2, 3+} branch counts.
- **Headline numbers:** branch-count accuracy 1.000, Jaccard median 0.845, Jaccard p10 0.972, Jaccard p90 0.730.
- **Failure modes still present:**
  - Per-branch Jaccard < 1.0 means the *narrator sequence within* a branch occasionally differs from gold — usually by one trailing narrator that the LCS heuristic doesn't recover. These rows are flagged by the **suspicion check** in the Tier-2 strategy and re-evaluated by an LLM (see [[tier2-llm-isnad-reconciliation]]).
  - Corpus-wide audit shows ~5% of hadiths with detected ح trigger the Tier-2 fallback. The remaining 95% are accepted at Tier-1 confidence.

## Known limits & future work

- **Single-language assumption.** The parser operates on Arabic isnads only. English-translated chains (where they exist) are not re-extracted; they inherit the Arabic-derived `chain_indx`.
- **Idempotency over scope.** The parser is fully idempotent (re-running on the same input produces the same output) but a downstream `chain_indx` change does *not* automatically invalidate hand-curated narrator-reconciliation work. The `regen --mode=repair` pipeline mode (see [[regen-pipeline-modes]]) handles the diff surgically.
- **Detection regex is calibrated.** New traditions or new sources may require recalibration if their ح-usage conventions differ. The audit script (`audit_tahweel_stats.py`) is the first thing to re-run when ingesting a new source.
- **No deep semantic check.** Tier 1 doesn't verify that recovered branches are *historically plausible* (e.g. that a narrator could have met their reported teacher). Plausibility checks live in the [[neo4j-reified-isnad-schema]] strategy as a separate guard rail.

## Prior work

The strategy builds on three streams of prior work:

- **Classical isnad scholarship** establishes ح as the canonical convergence marker (Brown 2009; Musa 2008 — see BibTeX). Our parser encodes a long-standing manuscript convention, not a novel one.
- **Computational isnad analysis** in digital humanities (notably the KITAB project's analytic work on the OpenITI corpus) demonstrates that rule-based extraction outperforms early LLM attempts on this specific structural task — informing our decision to keep Tier 1 deterministic and reserve LLMs for Tier 2.
- **The longest-common-subsequence / suffix family** of string algorithms is textbook material; the contribution here is the application to isnad branch reconstruction with a tradition-balanced evaluation set.

## Related

- Sources this strategy consumes: [[openiti]], [[sunnah-com]], [[thaqalayn-api]], [[sheikahmad-pure-canon]]
- Strategies that depend on this: [[tier2-llm-isnad-reconciliation]] (fallback for low-confidence rows), [[neo4j-reified-isnad-schema]] (consumes the `chain_indx` output), [[tiered-narrator-entity-resolution]] (resolves narrator tokens within each extracted branch)
- Related evaluation strategy: [[tahweel-occurrence-audit]] (calibrates the detection regex)
