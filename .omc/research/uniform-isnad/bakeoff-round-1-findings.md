# Bake-off Round 1 — findings & next iteration plan

**Run:** 2026-06-11
**Fixtures:** 5 annotated rows in `tahweel-gold.jsonl` (Tirmidhi #1 + Muslim #1/2/31/102)
**Candidates:** A_simple_set, B_name_span, C_lcs_suffix, D_position_anchored, E_no_stitch
**Full results:** `algo-evaluation.md`

## Headline numbers

| Candidate | branch-count acc | Jaccard median | Pass FR-0.5.4? |
|---|---:|---:|---|
| A_simple_set | 1.000 | 0.500 | ❌ (Jaccard < 0.80) |
| B_name_span | 1.000 | 0.500 | ❌ |
| C_lcs_suffix | 1.000 | 0.536 | ❌ |
| D_position_anchored | 1.000 | 0.500 | ❌ |
| E_no_stitch | 1.000 | 0.500 | ❌ |

**No candidate clears the FR-0.5.4 bar.** But every candidate hits 100% branch-count, and **candidate B perfectly extracts the canary (Tirmidhi #1, Jaccard 1.0 + 1.0).**

## The Jaccard-fail is NOT an algorithm problem

Investigation revealed three orthogonal causes for the low Jaccard, none of which the candidate-choice decision can fix:

### Cause 1 — Name-cleaner extracts trailing connectives

Examples from B's output on muslim-1:
- Algorithm emits `أبو بكر بن أبي شيبة أيضا` (with "أيضا" = "also")
- Algorithm emits `شعبة وسفيان` (with "و" = "and" + co-transmitter)
- Algorithm emits `المغيرة بن شعبة قالا` (with `قالا` = "they said")

The `_common.py` cleaner uses the inherited `extract_classical_isnad` regexes which don't strip these trailing/leading connective particles. **Fix: extend `clean_segment` to strip `أيضا`, leading `و` on the second co-transmitter, and trailing `قالا/قالت/قال`.** Applies to ALL candidates equally; not a bake-off discriminator.

### Cause 2 — MATN_ANCHORS regex incomplete

muslim-31's matn is `يقول لا يحدث عن رسول الله صلى الله عليه وسلم إلا الثقات` — starts with `يقول` (a quotation marker) rather than `قال رسول الله`. The `MATN_ANCHORS` regex in `_common.py` doesn't match `يقول لا يحدث`, so the matn bleeds into branch 1's name list. **Fix: add `يقول|قال سمعت|سمعت يقول` to the anchors.**

### Cause 3 — Gold annotation has an unrecoverable expectation

muslim-102 Branch B's text says `حدثنا أبي` (= "my father told us") referring to معاذ (the father of عبيد الله بن معاذ). The gold expects `معاذ` — but **no algorithm can recover that name from the text alone**, because the text genuinely just says "my father". This is a name-resolution problem (lexicon lookup by relationship), not an extraction problem.

**Fix: update the gold annotation for muslim-102 to expect `أبي` (matching what the text actually says), with a note that scholar resolution upstream is responsible for translating `أبي` → معاذ via the (عبيد الله بن معاذ).parent relationship in `all_rawis.csv`.**

### Cause 4 — `split_on_tahweel` verb-position bug on muslim-1

When the same compiler-narrator (أبو بكر بن أبي شيبة) appears at the START of both ح-branches, the verb-skipper in `_common.split_on_tahweel` may misalign the split point, causing Branch A's tail (الحكم → عبد الرحمن → سمرة) to leak into Branch B's head. **Fix: in `split_on_tahweel`, after locating ح, advance past whitespace and the لـ `حدثنا/أخبرنا/etc.` verb explicitly rather than using regex search inside the slice.**

## What the round-1 results DO tell us decisively

- **The ح-detection regex is solid** (100% branch-count across all candidates).
- **Candidate B's "loose name matching" approach is correct** — it gets the canary perfectly, and would get the other 4 cases right too once Causes 1–4 are fixed.
- **Candidate E (no_stitch) loses 1+ narrator per branch on the matn-attaching segment** — confirms stitching is needed, not optional.
- **Candidate C (LCS) doesn't differentially help over B for our cases**, but its lower edit-distance (median 0.5 vs 1.5) suggests it produces output that's positionally aligned with the gold when it works — useful as a tiebreaker or backup when B's intersection fails.

## Next iteration plan

**Round 2** — apply Causes 1, 2, 3, 4 fixes in `_common.py` only (no algorithm changes), then re-run bake-off.

1. Extend `clean_segment` with the connective-stripping regexes.
2. Extend `MATN_ANCHORS` with the missing matn-cue patterns.
3. Fix `split_on_tahweel`'s verb-position calculation (use a deterministic post-ح offset, not regex-search inside the match window).
4. Update muslim-102 gold annotation to expect `أبي` not `معاذ`.

Expected outcome: B and C both clear the 0.80 Jaccard median bar. If both do, pick **B** for simpler implementation (FR-0.5.4 tiebreaker).

If round 2 still doesn't clear the bar:
- **Round 3** — annotate 10 MORE fixtures by hand and look for systematic patterns the current algorithms can't handle. May indicate a need for a hybrid (try B first; on empty intersection, fall back to C's LCS).

## Decision

**Do not lock the winner yet.** Proceed to Round 2. The bake-off is doing exactly the job it was designed to do: eliminating the 30%-overlap red herring from Phase 0 / T-0.3 and identifying the real surface-cleaner issues that would have shipped silently if we'd skipped this phase.
