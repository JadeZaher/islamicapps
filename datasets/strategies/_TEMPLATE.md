---
# ─── Identity ─────────────────────────────────────────
id: short-kebab-case-slug                       # required, must match filename
name: Human-readable methodology name           # required
status: active | superseded | experimental | proposed
introduced: YYYY-MM-DD                          # when this strategy landed
last_reviewed: YYYY-MM-DD                       # when we last validated it

# ─── Scope ────────────────────────────────────────────
problem_domain: |                               # one sentence: what problem this solves
  E.g. "Splitting hadiths with ح transmission-convergence markers into
  independent isnad branches without losing the shared post-convergence chain."
applies_to_traditions:                          # tradition tags it applies to
  - sunni
  - shia-imami
  - zaydi
  - ibadi
  - cross-tradition
consumes_sources:                               # slugs from datasets/sources/
  - openiti
  - sunnah-com

# ─── Implementation ───────────────────────────────────
paths:                                          # in-repo files that implement it
  - datasets/hadith-data/extract_isnad_unified.py
  - src/scripts/lib/regen/...

# ─── Evaluation ───────────────────────────────────────
evaluation_method: |                            # how we know it works
  E.g. "Hand-annotated gold-set of N=120 fixtures, bake-off against
  three candidate algorithms, evaluated on branch-count accuracy and
  per-branch Jaccard overlap with the gold."
evaluation_results: |                           # key numbers
  E.g. "Selected candidate C: branch-count accuracy 1.000,
  Jaccard median 0.845, p90 0.730."
evaluation_artifacts:                           # where the evidence lives
  - .omc/research/uniform-isnad/algo-evaluation.md

# ─── Citation ─────────────────────────────────────────
# BibTeX for any prior work this strategy builds on. Multi-entry is fine.
bibtex: |
  @misc{shortkey-YYYY,
    title  = {Prior work this builds on},
    author = {{Author}},
    year   = {YYYY},
    url    = {https://...}
  }
---

# {Strategy name}

## Problem

What is the actual problem being solved, in plain language? Why is the
naive approach insufficient? A reader who has never seen this code should
be able to understand within two paragraphs *why this strategy exists*.

## Approach

The core idea in one or two paragraphs. Resist the urge to dump
pseudocode here — link the implementation instead. This section is
about *the shape of the solution*: what it observes, what it produces,
what invariants it maintains.

## Why we picked this over alternatives

The candidates we evaluated, in order of how seriously we considered
them, with the reason each was rejected (or accepted). If a formal
bake-off was run, link the evaluation artifact in the front-matter and
summarize the headline numbers here.

| Candidate | Result | Why we (didn't) pick it |
| --- | --- | --- |

## Evaluation

How we know this works:

- **Method:** brief description of evaluation procedure.
- **Headline numbers:** ...
- **Failure modes still present:** the ones we know about.

## Known limits & future work

What this strategy explicitly *doesn't* do, and what would have to change
for it to do those things. This is where contributors look when they ask
"could I extend this for X?"

## Prior work

Short narrative crediting any prior algorithms, papers, or classical
methodologies this builds on. The BibTeX front-matter is the
machine-readable form; this section is the human-readable form.

## Related

- Sources this strategy consumes: [[source-slug]]
- Strategies it depends on or composes with: [[other-strategy-slug]]
- Strategies it supersedes (if any): [[old-strategy-slug]]
