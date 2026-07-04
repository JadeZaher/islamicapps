# IAA Tooling — Operator Guide

This document is written for the person responsible for **running** inter-annotator agreement (IAA) checks in this project. It assumes you have already read the annotation guide (`tahweel-annotation-guide.md`) and understand what annotators are filling in. This doc is not a tutorial on annotation itself; it is a technical runbook for the quality-measurement tooling.

---

## §1 — Purpose

IAA answers one question: **are two qualified annotators following the same guide producing meaningfully similar outputs on the same rows?**

If the answer is yes (α ≥ 0.80), the gold set is reproducible — the annotations capture something real and stable about how the text is structured, not just one person's reading preferences. If the answer is no, one of two things is true: either the guide has a gap (a case type it fails to resolve unambiguously), or the row itself is genuinely hard to call (difficulty 5). IAA gives you a number for "are we drifting?" and a disagreement table that points directly at which rows are causing the drift.

Without IAA, a gold set authored by a single annotator is one author bug away from incorrect ground truth. The algorithm bake-off and calibration tooling both assume the gold set is correct. A measured agreement score, with a second qualified annotator, is the minimum evidence that the gold set deserves that trust.

---

## §2 — When to run it

**Standard cadence:**

- After ≥2 annotators have each annotated ≥20 of the **same** hadith_ids. Fewer than 20 shared rows makes the estimates too noisy to act on — the tool will emit a warning in the report header, but it will still compute.
- Quarterly as the gold set grows. A growing corpus changes the distribution of case types; agreement that held at 30 rows may slip at 150 if the new rows are heavier on edge cases.

**Trigger-based checks:**

- **When admitting a new annotator.** Run IAA between their first batch (≥20 rows) and the existing gold set, treating the gold as "annotator B." This is a sharper test than the calibration score alone, because it measures agreement on fresh rows the new annotator has not seen before, not on the 5-row calibration test they may have memorised.
- **After a guide revision.** Any change to §3 (canonical case types) or §4 (decision tree) can shift annotators' judgments on existing rows. Run IAA on the rows that the revised section addresses.
- **After a disputed annotation.** If an annotator flags a row as difficulty 5 (genuinely ambiguous), re-annotate it independently and run IAA on that row alone (the tool accepts a JSONL with a single row per annotator).

---

## §3 — The two metrics

### Krippendorff's α (primary)

The **unit of analysis** is the `(hadith_id, branch_index, position)` triple — a single narrator slot in the structured output. Distance is binary: two annotators either wrote the same narrator surface (after stripping Arabic diacritics and unifying alef variants) or they did not.

This metric handles missing data natively. When one annotator's branch is shorter than the other's — whether because they disagree on branch count or because one branch has fewer narrators — the missing slots are treated as a distinct value ("MISSING") rather than silently dropped. This means disagreements about chain length are counted as disagreements, not ignored.

α ranges from −1 to +1. The threshold in this project is **0.80**. Values between 0.67 and 0.80 are marginal and warrant investigation of the disagreement table. Values below 0.67 indicate substantial disagreement and should trigger a guide revision or annotator re-calibration before any new rows are committed to the gold set.

α is the load-bearing metric because it was designed for reliability measurement with ordinal and nominal data, properly handles different numbers of annotators (the tool computes all pairwise values and also an aggregate over all coders simultaneously), and is the standard in computational linguistics annotation work.

### Cohen's κ (secondary)

The **unit of analysis** is the `hadith_id` — a whole row. The value per (annotator, row) pair is the unordered set of unique narrator surfaces (after normalisation) across all branches. Two annotators agree on a row if they produced exactly the same set of narrator names, regardless of how they split them across branches.

κ is a familiar metric for readers more comfortable with pairwise agreement. It serves as a sanity check on α: if α and κ diverge significantly, that usually signals that disagreements are concentrated in branch-structure (one annotator split the chain differently) rather than in surface-form choices. The same **0.80** threshold applies.

For more than two annotators, the tool computes κ for every pair and reports the mean as the aggregate κ. All per-pair κ values appear in the report's per-pair table.

---

## §4 — How to run it

From the repository root:

```
cd c:/Users/atooz/Programming/experiments/islamicapps
python datasets/hadith-data/__tests__/fixtures/compute_iaa.py \
    --annotators path/to/ann1.jsonl path/to/ann2.jsonl \
    --out docs/annotation/iaa-report-2026-Q3.md
```

The `--annotators` flag accepts two or more JSONL files. Each file must contain rows with at least `hadith_id` and `expected_branches` fields (the same schema as `tahweel-gold.jsonl`). Extra fields (`notes`, `annotator`, `difficulty`, etc.) are ignored.

The `--out` flag specifies where to write the Markdown report. If omitted, the default is `docs/annotation/iaa-report-<YYYY-MM-DD>.md`.

The `--threshold` flag sets the pass/fail cutoff (default: 0.80). The tool exits with code **0** if both α ≥ threshold and κ ≥ threshold, and with code **1** if either metric falls below. Exit code **2** signals an input error (missing file, no shared rows, malformed JSONL).

**Self-test (same file as both annotators):**

```
python datasets/hadith-data/__tests__/fixtures/compute_iaa.py \
    --annotators datasets/hadith-data/__tests__/fixtures/tahweel-gold.jsonl \
                 datasets/hadith-data/__tests__/fixtures/tahweel-gold.jsonl \
    --out c:/tmp/iaa-self-test.md
```

Both α and κ should be exactly 1.0. Exit code should be 0. Run this after any code change to confirm the tool is functioning correctly.

---

## §5 — How to interpret the report

The report opens with the aggregate α and κ, each with an explicit PASS/FAIL label at the 0.80 threshold.

**Per-pair table.** When there are more than two annotators, the per-pair table shows which specific pairs agree most and least. A single pair with low agreement is usually a sign that one of those two annotators has drifted; cross-check with their individual calibration scores. Uniform low agreement across all pairs points to a guide gap rather than an annotator problem.

**Aggregate section.** The "triples in full agreement" count tells you what fraction of slots were uncontested. High α with many disagreements in absolute terms is common on large row counts; what matters is the ratio.

**Disagreement table.** This is the most actionable part of the report. Each row in the table is a `(hadith_id, branch_index, position)` triple where at least two annotators were present and wrote different values. Work through the rows in order:

- **Guide gap.** Both annotators are plausible given the text, but the guide does not specify which reading to prefer. Patch the guide and re-annotate the affected rows.
- **Difficulty-5 ambiguity.** The text itself is genuinely underdetermined (pronoun with no referent, broken chain). Mark both annotators' rows `difficulty: 5`, document the ambiguity in `notes`, and exclude the row from α/κ comparisons until a domain expert adjudicates.
- **Annotator error.** One annotator clearly misread the text. Re-run calibration on that annotator before they annotate further rows.

If the table is capped at 50 rows, the footer notes how many additional disagreements exist. Run with a narrow set of hadith_ids to investigate specific rows.

---

## §6 — Edge cases

**Fewer than 20 shared hadith_ids.** The tool still computes and reports α and κ, but the report header includes a WARN line. Do not make pass/fail decisions on fewer than 20 shared rows; the variance on α is too high to be meaningful.

**Different branch counts across annotators.** If annotator A found 2 branches and annotator B found 1, the extra branch's narrator slots appear in the unit map with MISSING on annotator B's side. These MISSING-vs-real-value pairs count as disagreements in α. The κ metric uses the narrator set view, so it will also penalise this: a different set of narrators means κ = 0 on that row. Both metrics naturally flag branch-count disagreements as a signal to investigate.

**Same file submitted as both annotators (intentional sanity check).** α and κ should both be exactly 1.0. The automated test suite (`test_iaa_synthetic.py`, test 1) exercises this. Run this manually after any code change to the tool.

**Three or more annotators.** The tool handles this natively. Aggregate α is computed over all coders simultaneously. Aggregate κ is the mean of all pairwise κ values. All per-pair scores are reported in the table so you can identify which pairs diverge.

**Annotator file contains rows not in the gold set.** Extra rows are not penalised; only rows present in ≥2 annotator files contribute to the metrics. The report notes the count of shared hadith_ids explicitly.
