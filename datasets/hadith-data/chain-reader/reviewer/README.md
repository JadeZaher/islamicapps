---
type: pilot
---
# Chain reviewer: the AI first pass of final review (owner ruling 2026-11-22)

A stronger model (Claude Opus, `claude-opus-5-5`) reviews, report by report, (i) readings HELD in the queue and (ii) readings already APPLIED and labelled "awaiting final review".
Its decision is recorded as **"AI reviewed", never "verified"**; a human decision always overrides it; a held reading it clears is applied. Built 2026-11-22, file side only: **no model
was run, no database written**, nothing outside `reviewer/` and `v3_4/` touched. Design notes: `AGENTS.md`; what the fix-pipeline owner must add: `INTEGRATION.md`.

| file | what |
|---|---|
| `prompt-reviewer-v1.md` | the system prompt (specialist `chain-reviewer` 1.0.0, output `shura-chain-review-output/1`); `prompt-reviewer-v1.json` records its sha256 **`46606e814f56efaeec0c0f7e45e455cbd9b2a819561ab8b13ccbe092c7968f77`** (11,017 letters), written by the builder on every run |
| `review_rules.py` | the decision vocabulary, every hold code in plain words with its clearable flag, and `outcome()`: the decision rule below as code |
| `build_review_packets.py` | packets and jobs: `--held`, `--applied`, `--sample N --seed S`, `--only`, `--pilot`, `--second-pass` |
| `validate_review.py` | mechanical checks of one output against its packet |
| `pilot-001/` | the pilot set (packets, `jobs.json`, `score_reviewer.py`; `private/` holds the id map and the judge's verdicts) |
| `tests/test_reviewer.py` | the validator (table-driven, real pilot items), the decision rule (table), packet isolation, the pilot's composition, the scorer |

## 1. What the reviewer sees and says

One packet = 10 reports (it reads slowly). Per report: the Arabic `text`; the source `context` unchanged (work and conventions, previous reports with `chain_text`, the sources' claims);
`status` (`held` / `applied`); the holds in plain words; both readers (their own `groups`, the tool's expanded `routes` with derived links marked by kind, `variant_groups` with ids `A.g1`,
notes, `needs_ruling`); `readers_agree`; the `stored_chain`. Never in a packet: the report's id or tranche, a judge's verdict, eligibility, the hadith id (a test checks).
The prompt carries every owner ruling (the two third-round rulings included) and the seven unruled questions, tells the reviewer plainly that **the two readers can share a mistake and
their agreement is not proof**, forbids identifying anyone or using outside knowledge, and requires an exact quote for every claim.

**Decision vocabulary** (one per report): `confirm_reading` · `confirm_with_correction` (with `corrected_reading` in the reader v3.4 format, validated like a reader's) ·
`prefer_reader_a` / `prefer_reader_b` (only when they differ) · `keep_stored` · `no_chain` · `refer_to_human` (with `question` naming the unruled question or what cannot be told).
Every review also carries `reasons` [{claim, source, quote}] (quotes exact substrings of `text`, `prevN`, `parent`, `context`, `reader_a`, `reader_b` or `stored`), an `uncertainty`
(`low` / `medium` / `high`, with a note), and a `variant_verdicts` entry for **every** variant group of either reader: `remark_about_another_version` or `route_of_this_saying`.

## 2. The decision rule (`review_rules.outcome`)

**Which holds the reviewer may clear** (owner, 2026-11-22). Clearable: shape holds (half route, both tail holds, comma, semicolon, nested «جميعا» / «؛», more than 8 routes, dropped head
across sayings, saying openings differ, back-reference-only, asker not a link, an empty reading with names before the saying, bracketed insertion), variant holds (`has_variant_group`,
`variant_only_reading`, `mutabaa_marker`, poem cue), single-reader flags (`flag_one_reader`) and disagreements between readers (`readers_differ`). **Not clearable**: an unruled owner question
(`needs_ruling` by both readers, `needs_ruling_prophet_no_transmitter`, `needs_ruling_faqih_route_statement`, `imami_single_narrator_without_source`, `empty_reading_unsettled_opening`),
a missing or doubtful previous report (`back_reference_without_previous_report`, `cannot_read_without_previous_report`, `inherited_from_far_report`), stale text, an invalid reader output,
and `two_sayings_not_supported` (a pipeline capability, not a reading question). Any code not in `review_rules.HOLDS` counts as not clearable.

**A HELD reading** (one review run unless stated):

| decision | condition | the pipeline | label on the page |
|---|---|---|---|
| any | a non-clearable hold stands | stays held; the review is recorded | unchanged |
| `confirm_reading` | readers agree | **applied** | "Read by model; AI reviewed (claude-opus-5-5), <date>; awaiting human review" (the owner's wording) |
| `prefer_reader_a` / `_b` | readers differ | that reader's reading **applied** (two independent models now agree: that reader and the reviewer) | "Read by model; AI reviewed (claude-opus-5-5), <date>; awaiting human review" |
| `confirm_with_correction` | a SECOND independent run gives the same corrected routes (`expand_v3_4.readings_agree`) | the corrected reading **applied** as a new fix | "Corrected by AI review (claude-opus-5-5, 2 runs), <date>; awaiting human review" (proposed) |
| `confirm_with_correction` | one run, or the runs differ | queued for a human with both readings and the correction(s) | unchanged |
| `no_chain` | the readers' agreed reading is empty | applied as "no chain" | "No chain is written in this report (read by model; AI reviewed (claude-opus-5-5), <date>; awaiting human review)" |
| `no_chain` | the readers wrote routes | as a correction: applied only if a second run also says `no_chain`, else queued | as above |
| `keep_stored` | | the reading is set aside (never applied); listed for a human | unchanged |
| `refer_to_human` | | stays held, with the named question | unchanged |

**An APPLIED reading** (already shown as "awaiting final review"):

| decision | the pipeline | label |
|---|---|---|
| `confirm_reading` (or `no_chain` on an applied "no chain") | stays applied | gains "; AI reviewed (claude-opus-5-5), <date>" |
| anything else | **reverted to the stored chain at once and listed for a human**; a `confirm_with_correction` / `no_chain` that a second run repeats is then applied in its place (the rules above) | the stored chain's own label, or the correction's |

A human review always wins: a human confirmation makes the fix `confirmed` ("Verified by <name>, <date>"), a human rejection rejects it, whatever the AI said. An AI review never produces
the word "verified" and never forms a teacher-student pair by itself (the pipeline's rule for model-read chains is unchanged).

**The risk, stated.** Clearing a hold puts a reading on the page that a rule flagged as likely wrong, on the word of one more model. Three failure modes: (1) **shared blind spots**: the
reviewer is a Claude model like the readers; a reading wrong in a way all three find natural (the 553df1 class: a restated name written as two links) passes; (2) **authority by fluency**:
a confident, well-quoted wrong review reads as proof; the exact-quote rule makes it checkable, not right; (3) **revert churn**: on applied readings any non-confirmation reverts at once, so a
reviewer that over-refers takes right chains off the page (the stored chain is wrong in about 3 of 4 judged reports). Mitigations: the clearable list excludes every unruled question
and every previous-report doubt; corrections need two independent runs; the pilot measures both directions before any production run. **Proposed gate** (the owner's to set): on the pilot,
the reviewer catches at least 14 of the 16 judge-wrong readings, and confirms at least 90% of the 61 judge-right ones (needless corrections and referrals counted against it).

## 3. Building packets

```
python -B -X utf8 reviewer/build_review_packets.py --source tranches/tranche-02 --held --batch t02-held-001                 # every held report with a valid reading
python -B -X utf8 reviewer/build_review_packets.py --source v3/batch-001 --applied --only <applied ids> --batch b1-applied-001
python -B -X utf8 reviewer/build_review_packets.py --source tranches/tranche-02 --applied --sample 50 --seed 20261701 --batch t02-applied-s50
python -B -X utf8 reviewer/build_review_packets.py --second-pass --batch <batch>                                           # after pass 1
python -B -X utf8 reviewer/validate_review.py --packet <batch>/packets/packet-01.json --output <batch>/outputs/pass-1/packet-01.output.json
```
The triage read is v3.3's when present, else v3.2's. `jobs.json` (`shura-chain-review-jobs/1`): one fresh `claude-opus-5-5` worker per packet, pass 1; each job's `instruction` is the whole
message (prompt path, version and hash; the one packet; where to write; the RUN.txt line). Pass 2 is built only after pass 1, from the reports whose valid first review is
`confirm_with_correction` (or `no_chain` against a reading with routes), into `packets-pass-2/` and `jobs-pass-2.json`, for NEW workers that never see pass 1.

## 4. Pilot (`pilot-001/`)

Tranche 02 (prompt v3.2, judged by `tranches/tranche-02/judge-v3_2/analysis/`): the 21 agreed readings held by shape holds that the judge read (`hold_verdicts.tsv`), the 30 variant-held
readings it read (`variant_verdicts.tsv`) and a random 30 of its eligible sample (`sample_verdicts.tsv`, the 244 minus the 51, `random.Random(20261601).sample`): **81 reports, 9 packets,
9 pass-1 jobs**. Status under the v3.3 triage: 49 held, 32 applied (3 shape-hold readings are eligible under v3.3's narrowed holds; 1 sampled reading is held under v3.3).

| set | judge: reading wrong | right | cannot tell |
|---|---|---|---|
| shape holds (21) | 12 | 6 | 3 |
| variant holds (30) | 4 (2 wrong with the group removed, 2 more whose group the judge found a genuine route) | 25 (2 of them with a spurious group) | 1 |
| eligible sample (30) | 0 | 30 | 0 |
| **total 81** | **16** | **61** | **4** |

`python -B -X utf8 reviewer/pilot-001/score_reviewer.py [--pass 1] [--out score.json]` reports: of the 16 judge-wrong, how many the reviewer catches (any decision but a confirmation) and
how; of the 61 judge-right, how many it confirms, wrongly rejects, needlessly corrects or refers; the cannot-tell ones; agreement with the judge; per set; the variant-group verdicts against
the judge's `group_is`; and what `outcome()` would do with each after one run. The eligible sample holds no judge-wrong reading, so it measures only the cost side on applied readings.

## 5. Tests

`python -B -X utf8 -m unittest discover -s reviewer/tests -p "test_*.py"` (9 tests). Flows: a valid confirmation, correction, referral and previous-report quote pass; 16 malformed reviews are
each refused for the stated reason (table); confirming a disagreement is refused and preferring a reader accepted; missing, doubled and wrong-version reviews; the owner's clearable list;
16 decision-rule cases (table); no packet carries an original id, a verdict or eligibility; the pilot's composition; a reviewer that rejects exactly the judge-wrong readings scores 16/16
and agreement 1.0, one that confirms everything catches 0.

## 6. Not built

- No reviewer run; the pilot is not scored; the gate is a proposal.
- The pipeline side (state transitions, `--ai` records with run id, labels, `/method`, registry): `INTEGRATION.md`, the integrator's.
- A reviewer packet for a report read under v3.4 with two sayings shows `sayings` per reader; none exists yet to test with.
- Choosing which applied ids are actually live (batch 001's 348) is the pipeline's list (`--only`); the builder treats a triage-eligible reading as applied.
