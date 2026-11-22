---
type: pilot
---
# Chain reader v3.2: the tool after tranche 01's judgement, and a draft prompt

Version 3.2 fixes the TOOL (validity, agreement, holds, submission) for the findings of the independent judgement of tranche 01 (`../tranches/tranche-01/judge/analysis/`: reader right 94.1% weighted on 201 read eligible readings, against batch 001's 98.6%; no break of a correct stored chain; 7 wrong readings in named classes), and drafts a prompt v3.2 for the readings still to be made. **No model was run, nothing was written to a database, nothing outside `v3_2/` and the two new tranche-01 folders was written** (`v3/`, `v3_1/`, `reviews/ai/`, `chain-fixes/`, every existing triage, judge and reader output are untouched). Design reasons: `AGENTS.md`; holds: `HOLDS.md`; folds: `FOLDS.md`.
**The v3.2 holds and folds were designed on tranche 01's judge sample, so every figure for them on that sample is in-sample.** Tranche 02 is the out-of-sample test (section 7).

## 1. What changed from v3.1

| | change | the judge's finding it answers | where |
|---|---|---|---|
| Variant groups | a group the reader marks `variant: true` never becomes a route: it is kept in `variant_remarks` (surfaces, the sentence of the remark); agreement is on the non-variant routes only; a reading that carries one is held (`has_variant_group`) until the fix pipeline accepts notes (`--variant-notes-supported` lifts it); a reading of only variant groups is always held; the envelope carries the remark in `fixes[].variant_remarks` and a line in `output.notes` | 3 of the 7 wrong readings are a variant group stored as a chain (30fa50, c93705, e3f7d5) | `expand_v3_2.py`, `holds_v3_2.py`, `triage_v3_2.py`, `to_submission_v3_2.py` |
| Shape holds | `route_at_most_half_the_longest` (6d7565), `first_links_split_by_comma` (05c2d0), `semicolon_in_multi_route_isnad` (eb2b15); v3.1's `routes_end_at_different_links` is kept with its exemptions | the proposed holds, section 8 of the judge | `holds_v3_2.py`, `HOLDS.md` |
| Imami holds | `imami_single_narrator_without_source` (07d717, f14c39), `inherited_from_far_report` (b36519), «و مع قوله» opens an implicit-speaker empty reading (2973ea), `needs_ruling_prophet_no_transmitter` in every work (cf634a) | al-Faqih findings; the Prophet case applied in one group and held in another | `holds_v3_2.py` |
| Validity | a missing `fixes` key reads as `[]` | 6 outputs invalid for that alone | `validate_v3_2.with_default_fixes` |
| Agreement | titles, a patron, a companion and a relation appended to a name, a restated short form at the same slot, and an editor's «[ ... ]» insertion compare equal (the last held when the passes differ) | 11 of the 40 disagreements were equivalent readings | `norm_v3_2.py`, `expand_v3_2.py`, `FOLDS.md` |
| Prompt | a DRAFT: examples for four reader-error classes (section 6) | the reader-error classes | `prompt-v3_2.md`, `tools/` |

## 2. Readings that carry a variant group

| | pass A | pass B | reports with one in at least one valid pass | agreed | eligible under v3.1 | of the 394 applied |
|---|---|---|---|---|---|---|
| tranche 01 (980 reports) | 47 of 965 valid readings (57 groups) | 51 of 973 (63 groups) | **64** | 49 | **27** (24 stored a variant route: the judge's 24) | n/a |
| batch 001 (500 reports) | 10 of 497 (15 groups) | 10 of 497 (18 groups) | **12** | 11 | 5 | **4** |

In tranche 01, 23 of the 27 are held by `has_variant_group`; the other 4 no longer agree (one pass writes the group as a variant, the other as a route). `--variant-notes-supported` would make the 23 eligible with their variant routes dropped.

## 3. Tranche 01 under the v3.1 tool and the v3.2 tool (same outputs, same packets; `../tranches/tranche-01/triage-v3_2/`, `judge-v3_2/tables.md`)

| scope | tool | valid A | valid B | both valid | agreed | eligible (chain + no chain) |
|---|---|---|---|---|---|---|
| all 980 | v3.1 | 959 (97.9%) | 973 (99.3%) | 954 (97.3%) | 821 (83.8%) | 747 = 732 + 15 (76.2%) |
| | **v3.2** | 965 (98.5%) | 973 (99.3%) | 960 (98.0%) | 863 (88.1%) | 734 = 721 + 13 (74.9%) |
| six Sunni books 759 | v3.1 / **v3.2** | 745 / 749 | 753 / 753 | 741 / 745 | 636 (83.8%) / 672 (88.5%) | 589 = 588 + 1 / 577 = 576 + 1 |
| al-Faqih 67 | v3.1 / **v3.2** | 65 / 65 | 67 / 67 | 65 / 65 | 62 (92.5%) / 62 (92.5%) | 57 = 52 + 5 / 52 = 48 + 4 |
| other Imami 154 | v3.1 / **v3.2** | 149 / 151 | 153 / 153 | 148 / 150 | 123 (79.9%) / 129 (83.8%) | 101 = 92 + 9 / 105 = 97 + 8 |

Eligible under v3.2 only: 23 (18 Sunni, 5 other Imami; 11 are among the judge's 40 disagreements, all judged "both right"; 12 were not read). Eligible under v3.1 and held under v3.2: 36 (4.8%): 27 variant, 2 half-route, 2 single narrator, 1 each comma / far inheritance / Prophet / semicolon (the 27 variant readings are the price of the hold; with `--variant-notes-supported` they come back).
Agreement rose 83.8% to 88.1% (+42 reports: 47 gained, 5 lost; of the 47, 6 outputs became valid, about 23 no longer differ on a variant remark, about 18 are equivalent names, `FOLDS.md`); eligible fell by 13.

Right-rate among the eligible readings the judge read (undecided counts as not right; Wilson 95%; the weights are each group's eligible readings under the tool; **v3.2 is in-sample**):

| tool | six Sunni books | al-Faqih | other Imami | weighted |
|---|---|---|---|---|
| v3.1 | 98/104 = 94.2% (88.0-97.3) | 52/57 = 91.2% (81.1-96.2) | 38/40 = 95.0% (83.5-98.6) | **94.1% (89.2-96.8)** (201 judged) |
| **v3.2** | 98/99 = 99.0% (94.5-99.8) | 52/52 = 100% (93.1-100) | 38/39 = 97.4% (86.8-99.5) | **98.8% (95.6-99.7)** (190 judged) |
| v3.2 with `--variant-notes-supported` (the 3 variant readings counted right on the judge's own statement, **not re-read**) | 101/102 = 99.0% (94.7-99.8) | 52/52 | 38/39 | 98.9% (95.7-99.7) (193 judged) |

**Judged-right readings the new holds catch: 0 of 190.** Judged-wrong or undecided caught: 11 (6 wrong: 30fa50, c93705, e3f7d5, 05c2d0, 6d7565, eb2b15; 5 undecided: 07d717, f14c39, b36519, cf634a, 2973ea). **Judged readings still eligible and not right: 2**: 0706da (wrong: the one asked who answers is dropped; no cue a regex can use) and a20cb6 (undecided: a narrated encounter where the Imam speaks, unruled). Lists: `judge-v3_2/caught_by_new_holds.tsv`, `still_eligible_not_right.tsv`, `newly_eligible.tsv`, `hold_hits.tsv`.

## 4. Each new hold (details and the batch-001 cost: `HOLDS.md`)

| hold | tranche 01 hits on agreed (eligible under v3.1) | judged wrong caught | judged right caught |
|---|---|---|---|
| `has_variant_group` | 49 (23) | 3 | 0 |
| `route_at_most_half_the_longest` | 6 (2) | 1 (6d7565) | 0 |
| `first_links_split_by_comma` | 1 (1) | 1 (05c2d0) | 0 |
| `semicolon_in_multi_route_isnad` | 2 (1) | 1 (eb2b15) | 0 |
| `imami_single_narrator_without_source` | 3 (2) | 0 (2 undecided: 07d717, f14c39) | 0 |
| `inherited_from_far_report` | 1 (1) | 0 (1 undecided: b36519) | 0 |
| `needs_ruling_prophet_no_transmitter` | 2 (1) | 0 (1 undecided: cf634a) | 0 |
| «و مع قوله» opener (`empty_reading_unsettled_opening`) | 2 (1) | 0 (1 undecided: 2973ea) | 0 |
| `bracketed_insertion_differs` | 1 (0) | none eligible (54c186) | 0 |

Opener variants: the packets of all 10 tranches and batch 001 (10,284 reports) hold ONE report that opens «و مع قوله / قول» + a blessing (2973ea). «و في قوله», «و من قوله», «و لقوله», «و قوله / قولهم», «مع ذلك» open none: no variant is added (nothing to justify one).

## 5. Batch 001 against the first judge (`batch-001/RETRIAGE_V3_2.md`, `held_of_394.tsv`, `numbers.json`)

| | v3 | v3.1 | v3.2 |
|---|---|---|---|
| valid A / B | 493 / 493 | 497 / 497 | 497 / 497 |
| agreed | 450 | 457 | 462 |
| eligible | 370 | 402 = 366 + 36 | 387 = 354 + 33 |

Of the 394 readings of `../v3_1/batch-001/eligible_to_apply.txt`, **379 stay eligible and 15 would now be held** (ids are `b1-` + the six letters):

| hold | ids (first judge's verdict) |
|---|---|
| `has_variant_group` (4) | 244c94, ca3dad, ef706c (not judged), 88802d (right) |
| `route_at_most_half_the_longest` (3) | 2c5437, bb2042, cb35a4 (not judged) |
| `semicolon_in_multi_route_isnad` (3) | 0c320a, 3fe523, 9f0528 (all right) |
| `imami_single_narrator_without_source` (2) | a6d33f, dbf175 (both right) |
| `needs_ruling_prophet_no_transmitter` (3) | a2dfb1, b8346e, dadc56 (all right as "no chain") |

Right-rate among the judged chain readings of the 394: 233/233 under v3.1 and 227/227 under v3.2 (`RETRIAGE_V3_2.md` section 3): the 394 were chosen to exclude every judged-wrong reading, so the v3.2 holds can only remove right ones here (6 chain readings, plus the 3 Prophet "no chain" readings).
**For the pipeline owner, which already-applied readings to look at** (nothing here is a judge verdict unless said):
- **Variant routes stored as chains (v3.1 stores them): 244c94** (extra route «الأعمش > سالما > جابرا» from «تابعه الأعمش ...»), **ca3dad** («ابن عيينة > الزهري > أنس» from «بمثل حديث ابن عيينة ...»), **ef706c** (five extra routes from «وروى الثوري ... وروى شعبة ... وروى إسرائيل ...»); **88802d** was judged right and adds «إسماعيل بن جعفر > مالك > ... > قتادة بن النعمان» from «زاد إسماعيل بن جعفر ... أخبرني أخي قتادة»: a real extra isnad of an extended text, which v3.2 would hold as a remark. Revert the extra route of the first three; 88802d is the owner's call.
- **Probably wrong (my reading of the texts, not the judge's): 2c5437 and cb35a4** (the second route drops its shared head: «قال دلهم وحدثنيه أيضا الأسود ...» and «قال وأخبرني ابن طاوس ...» give routes that start at the new name) and **bb2042** (the second route «هناد > المحاربي > ليث > مجاهد» drops ابن عباس). All three are the 6d7565 class. Look at them first.
- The 9 judged-right readings (3 semicolon, 2 single narrator, 3 Prophet "no chain", 1 variant) need no action; they show the cost of the broad holds (2.3% of the 394). Two holds could be narrowed if the owner prefers (`HOLDS.md` "Why not more").

## 6. Prompt v3.2: a DRAFT (`prompt-v3_2.md`, `prompt-v3_2.json`)

sha256 **`6ae86867b88c21a6a9b7f2ba056a0098198439fd3fa2eeb5bfb2f9f762e380d8`**, 27,023 letters (v3.1: 27,173; the build fails above it). Built by `tools/make_prompt_v3_2.py` (every example validated against its real text, 21 quoted fragments found, 8 pilot readings expanded as the rule says); **not run, not to be used on existing outputs**.
Examples, 8 in all (replace, not append: v3.1's 2 al-Kafi imam, 3 `وبهذا الإسناد` inherited, 4 `cannot_read_without_previous_report` and 7 «وقال عليه السلام» were dropped; their rules stay in the text and example 7 still shows an `inherited` Imam):
1. v2's cx-0001: two taḥwīl groups and a shared tail (kept).
2. **a remark about another version is a `variant` group, never a route** (t01-30fa50 «بمثل حديث سليمان بن بلال»).
3. **«قال وحدثني X» continues with the shared head** (t01-6d7565: the second route keeps مسدد > يحيى > سفيان).
4. **a kunya, a comma and a name are ONE man** (t01-05c2d0 «أبو الطاهر، أحمد بن عمرو بن سرح»).
5. **the one who is asked and answers is a link** (t01-0706da «قلت لعطاء ... فأخبرني ابن أبي مليكة»).
6-8. v3.1's asker («و كتب X إلى Y»), pronoun asker with an inherited Imam, and the empty reading (kept). The four new texts are real tranche-01 reports shortened at a stated phrase (`examples/example-packets.jsonl`, a test checks each is a prefix of the real text). The body has three one-line additions (rules 4, 6, 7).
A prompt change is not an expansion of the output format: the same JSON, so every v3.2 tool module reads outputs read under v3, v3.1 or v3.2.

**Which tranches with which prompt.** Tranche 01 was read under v3.1 and stays so: re-triage it with the v3.2 tool (done, section 3); a re-read would be an owner decision (`to_submission_v3_2.py --reader-prompt v3_1`). Tranches 02-10 are unread: read them with prompt v3.2 only after the owner approves the draft, otherwise with v3.1 and the v3.2 tool (the tool fixes are independent of the prompt). **`tranches/tranche-NN/jobs.json` points at prompt v3.1; for v3.2 it must be regenerated into a NEW file** (the packets are unchanged: the prompt changed only in examples and three lines of rules, the packet builder and its openers are untouched, so no packet is rebuilt):

```
python -B -X utf8 v3_2/make_jobs_v3_2.py --tranche all            # tranches 02-10 -> tranches/tranche-NN/jobs-v3_2.json (originals untouched)
python -B -X utf8 v3_2/make_jobs_v3_2.py --tranche 02 --check     # print only
```
It swaps the prompt path, version and sha in `prompt` and every `instruction`, and moves `input_chars` by -150 (27,023 against 27,173 letters per job). I did not write these files (outside my write limits); a test converts tranche 02's jobs in memory and checks that only `instruction` and `input_chars` change.

## 7. Tranche 02 is the out-of-sample test

Draw (nobody picks): seed = 20261200 + 2 = **20261202**, 100 eligible readings split over the three groups in proportion to the tranche's eligible readings, after tranche 02 has been read and triaged with the v3.2 tool. Extension (the same method as tranche 01's): seed **20261302**, another 100, disjoint from the first draw. Commands (from `chain-reader/`):

```
T=tranches/tranche-02
python -B -X utf8 v3_2/validate_v3_2.py --packets $T/packets --outputs $T/outputs/pass-a        # and pass-b
python -B -X utf8 v3_2/triage_v3_2.py --packets $T/packets --pass-a $T/outputs/pass-a --pass-b $T/outputs/pass-b --out $T/triage-v3_2 --reports $T/private/reports.jsonl
python -B -X utf8 v3_2/draw_judge_sample_v3_2.py --tranche 02                                  # seed 20261202 -> $T/judge-v3_2/{sample.tsv, draw.json, dump.jsonl}
python -B -X utf8 v3_2/draw_judge_sample_v3_2.py --tranche 02 --base-seed 20261300 --exclude $T/judge-v3_2/sample.tsv --out-name extension      # seed 20261302 -> extension-*.tsv/json/jsonl
python -B -X utf8 v3_2/to_submission_v3_2.py --packets $T/packets --reports $T/private/reports.jsonl --pass-a $T/outputs/pass-a --pass-b $T/outputs/pass-b --out $T/submissions --batch t02 [--reader-prompt v3_2] [--variant-notes-supported]
```
(`RUN.md` section 2 names the v3.1 modules; these are their v3.2 equivalents.) What the judge should report for the holds: each new hold's hits, and for each hit whether the reading was right or wrong; a hold that catches a right reading in tranche 02 is a cost, one that catches a wrong reading is the out-of-sample confirmation; the right-rate among eligible readings against the 95% gate of `RUN.md` section 3 (the in-sample figure, 98.8%, is not the expectation: expect the v3.1 rate (94.1%) plus what the holds remove, minus the new classes tranche 02 will show).

## 8. Tests (from `datasets/hadith-data/chain-reader/`)

```
python -B -X utf8 -m unittest discover -s v3_2/tests -p "test_*.py"            # 27 tests: folds with negatives, variant handling, the judge's real cases through the whole tool, openers, shape-hold boundaries, prompt, jobs, envelope
python -B -X utf8 v3_2/triage_v3_2.py --packets tranches/tranche-01/packets --pass-a tranches/tranche-01/outputs/pass-a --pass-b tranches/tranche-01/outputs/pass-b --out tranches/tranche-01/triage-v3_2 --reports tranches/tranche-01/private/reports.jsonl
python -B -X utf8 v3_2/evaluate_tranche01_v3_2.py                               # judge-v3_2/
python -B -X utf8 v3_2/triage_v3_2.py --packets v3/batch-001/packets --pass-a v3/batch-001/outputs/pass-a --pass-b v3/batch-001/outputs/pass-b --out v3_2/batch-001/triage --reports v3/batch-001/private/reports.jsonl
python -B -X utf8 v3_2/evaluate_batch001_v3_2.py                                # batch-001/
python -B -X utf8 v3_2/tools/build_example_packets_v3_2.py && python -B -X utf8 v3_2/tools/make_prompt_v3_2.py     # the prompt
```
`v3_1/tests` and `v3/tests` are untouched and pass.

## 9. Deferred / not built

- **The fix pipeline cannot carry variant notes**: until the owner switches it on (`--variant-notes-supported`) every reading with a variant remark stays held (27 of tranche 01's 747 v3.1-eligible readings: 23 held, 4 no longer agree).
- An epithet the applied reading (pass A's) wrote stays in the stored surface («أبا النضر، مولى عمر بن عبيد الله»): the comparison folds it, the envelope does not trim it. Trim in `to_submission` or let the pipeline's resolver strip it; trigger: the first tranche applied with v3.2.
- The restated-name dedupe of 871527 («ابن علية» + «إسماعيل ابن علية»), the three-men-in-one-link check (69ae9b) and the reader typo repair are not built.
- 0706da (the one asked answers, dropped) and a20cb6 (a narrated encounter) have no tool cue; the prompt example (v3.2) is the only guard and the draft has not run.
- `imami_single_narrator_without_source` and `semicolon_in_multi_route_isnad` are as broad as the judge measured them and each caught judged-right readings of batch 001 (2 and 3): narrowing options are in `HOLDS.md`.
- The tranche-02 draw cannot be run before tranche 02 is read; `jobs-v3_2.json` files are not written.
- No run of prompt v3.2; the batch-001 "probably wrong" readings (2c5437, bb2042, cb35a4) are my reading, not a judge's.
