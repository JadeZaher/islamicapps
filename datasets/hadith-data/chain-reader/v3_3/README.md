---
type: pilot
---
# Chain reader v3.3: the tool after tranche 02's out-of-sample judgement

Version 3.3 revises the TOOL only (holds, triage, submission) for the findings of the judge of tranche 02 (`../tranches/tranche-02/judge-v3_2/analysis/`: reader right 97.6% weighted (94.7-98.9) on 244 read eligible readings, zero breaks). **The prompt does not change: v3.2 stays for every remaining tranche** so tranches stay comparable. No model was run, nothing was written to a database, nothing outside `v3_3/` and the new `tranches/tranche-0{1,2}/triage-v3_3/` was written; `v3_2/` and earlier, `reviews/ai/`, `chain-fixes/`, judge folders and reader outputs are untouched. Modules reused unchanged from `v3_2/`: `expand_v3_2`, `validate_v3_2`, `norm_v3_2`. Holds: `HOLDS.md`; design: `AGENTS.md`; the pipeline owner's lists: `APPLY_LISTS.md`.

## 1. What changed, with the hits and the judge's verdicts among them

| change | tranche 02 (IN-SAMPLE) | tranche 01 (out of sample for v3.3) |
|---|---|---|
| 1. NEW `mutabaa_marker` | 3 hits on agreed, 2 eligible under v3.2: **W 2 (1061e3, cf6189), R 0**; third hit 888bb4 is a variant remark, held anyway | 0 hits (batch 001: 0) |
| 2. `routes_end_at_different_links` REPLACED by `route_ends_inside_another_route` | 5 hits (1 eligible under v3.2): **W 5 (d02f9f, facedc, 181bd0, b88276, 30b092), R 0**. Old hold: 8 hits, 6 W, 2 R (89130e now eligible; 8b0565 still held by `back_reference_without_previous_report`) | 4 hits (1 eligible under v3.2), none judged; old hold 6 hits. The four judged-right two-isnad readings of v3.2's tests (dd8d9b, 0c66ee, 610c03, 31cf87) stay eligible |
| 3. `route_at_most_half_the_longest` NARROWED | 8 hits, **W 8, R 0**; 1552aa (R) released | 5 hits (v3.2: 6): **6d7565 (W) released**, see section 4 |
| 4. `inherited_from_far_report` NARROWED | 0 hits (v3.2: 1): 5505a6 (R) released | 1 hit, b36519 (CT) **still held** |
| 5. variant switch | `--variant-notes-supported` only carries the notes; `--release-variant-readings` (off by default) releases. 77 held, unchanged | 49 held, unchanged |
| 7. NEW `needs_ruling_faqih_route_statement` (tag `faqih_route_statement`) | 13 tagged, 10 agreed, 6 eligible under v3.2: **R 8 of the 10 hits judged right, W 2** | 5 tagged, 4 agreed, 2 eligible under v3.2 (34aad2 R, d8ce40 R; eb2b15 W is also held by the semicolon hold) |

Not added (the judge rejected them): a transmission verb after the matn, a one-pass `needs_ruling` flag, the restated-name regex. Kept: `has_variant_group`, `semicolon_in_multi_route_isnad`, `imami_single_narrator_without_source`, the nested and back-reference holds, `needs_ruling` by both readers.

**«تابعه» forms** (folded text, whole reports, tranches 01-10 and batch 001): «تابعه» 44 reports, «وتابعه» 10 (53 distinct reports); «تابعها», «تابعهم», «تابعهما»: 0; the verb with an object, «وقد تابع ابن جريج على ذلك» and «وتابع يونس على قوله»: 2 (t04-a70647, t02-387652). By tranche: 01 2, 02 8, 03 6, 04 5, 05 6, 06 2, 07 4, 08 6, 09 7, 10 6, batch 001 3. Not markers (checked in context, no hold): «تابع للحق» (5 reports), «تابع» as «follower» (b1-3a02fe), «وتابع» in «رضي وتابع فقيل» (t02-6c36f8), «متابعته», «تتابع», «تابعا», «تابعين».
**al-Faqih route statements** («و ما كان فيه عن X فقد رويته عن ...»): tranche 01 5 reports, tranche 02 13, batch 001 20 (38 in all; 33 agreed). Eligible under v3.2 and therefore removed from the apply lists by the new hold: tranche 02 **6** (the judge's six), tranche 01 2, batch 001 12 (all 12 are among the 348 applied). Every judged one is right under the judge's ruling («the person whose words are relayed is the last link»), so the hold costs 6 + 2 + 11 judged-right readings until the owner rules; if the owner says a statement of routes is not an isnad of a saying they become wrong (al-Faqih tranche 02: 41/48 = 85.4%). The other 4 of tranche 02's 10 agreed statements (0a8f48, 6da700 W; 65b393, 9a44c0 R) were already held by the semicolon hold. Lists: `faqih_route_statements.tsv` in each triage folder.

## 2. Re-triage with the v3.3 tool (same outputs, same packets; no model)

Each folder holds `RETRIAGE_V3_3.md` (valid, agreed, eligible by group; every hold's hits overall and per group, v3.2 beside v3.3; the changed holds' verdicts), `numbers.json`, `hold_hits.tsv`, `faqih_route_statements.tsv`, `released_vs_v3_2.txt`.

| set | sample status of the figures | agreed | eligible v3.2 (chain + no chain) | eligible **v3.3** | right-rate among judged eligible, weighted: v3.2 | **v3.3** |
|---|---|---|---|---|---|---|
| tranche 02 `tranches/tranche-02/triage-v3_3/` (valid A 970, B 977, both 969, unchanged) | **in-sample** for the v3.3 changes (and the judge's 244 are the sample they were designed on) | 862 | 706 = 695 + 11 | **700 = 689 + 11** | 97.6% (94.7-98.9), 244 judged (out of sample for v3.2) | **98.1% (95.4-99.2)**, 237 judged |
| tranche 01 `tranches/tranche-01/triage-v3_3/` (valid A 965, B 973, both 960) | out of sample for the v3.3 changes; **in-sample for the v3.2 holds** (designed on it) | 863 | 734 = 721 + 13 | **733 = 720 + 13** | 98.8% (95.6-99.7), 190 judged | **98.1% (94.2-99.4)**, 189 judged |
| batch 001 `v3_3/batch-001/triage/` (valid A 497, B 497, both 494) | out of sample for v3.3; the 301 judged readings were drawn under v3, before any later hold | 462 | 387 = 354 + 33 | **378 = 345 + 33** | 98.7% (96.9-99.4), 261 judged | **98.6% (96.9-99.4)**, 250 judged |

Per group (judged right / judged eligible under v3.3, Wilson 95%):

| set | six Sunni books | al-Faqih | other Imami |
|---|---|---|---|
| tranche 02 (eligible v3.2 549/48/109 -> v3.3 548/42/110) | 153/155 = 98.7% (95.4-99.6) | 41/42 = 97.6% (87.7-99.6) | 38/40 = 95.0% (83.5-98.6) |
| tranche 01 (eligible v3.2 577/52/105 -> v3.3 578/50/105) | 98/100 = 98.0% (93.0-99.4) | 50/50 = 100% (92.9-100) | 38/39 = 97.4% (86.8-99.5) |
| batch 001 (eligible v3.2 203/100/84 -> v3.3 206/88/84) | 83/83 = 100% (95.6-100) | 83/85 = 97.6% (91.8-99.4) | 79/82 = 96.3% (89.8-98.7) |

Hits of every hold, overall and per group, are in each `RETRIAGE_V3_3.md` section 2. Batch 001's judged set includes the judge's empty ("no chain") readings (the first judge's headline 98.6% is its 244 chain readings).
Read the in-sample figures as what the tool was fitted to: tranche 02's rise from 97.6% to 98.1% is 1061e3 (W) and d02f9f/cf6189 (W, outside the sample) held, while 6 judged-right readings are lost to the new faqih hold. Only tranche 01 and batch 001 are a test of the v3.3 changes, and they show no gain and no loss beyond the faqih hold and the narrowing (section 4).

**Judged wrong or undecided and still eligible under v3.3** (not held by any hold; they are on the withheld lists): tranche 02: 553df1 (W, restated name, no cue), 0dfb7f, 3cacbd, fe8248, fecbb4 (CT); tranche 01: 0706da (W, the one asked answers), 6d7565 (W, **newly eligible through the narrowing**), a20cb6 (CT); batch 001: 4cbe02 (W), 550aae, 941f93, b2ad9c, cb13de (CT).
**Judged right and now held** (all by the faqih hold): tranche 02 0bcea2, 1531a8, 397ef7, 46c4c6, 94355c, beb57a; tranche 01 34aad2, d8ce40; batch 001 170d33, 1bea49, 26d360, 297cae, 520cad, 60b019, 703a20, 928814, a05d58, a735be, fffeb4. Nothing else judged right is held (v3.2 had the same property in-sample on tranche 01).

## 3. Tests

`python -B -X utf8 -m unittest discover -s v3_3/tests -p "test_*.py"` (from `chain-reader/`): 17 tests, OK (also `v3_2/tests`: 27, OK). Flows: the judge's tranche-02 cases through validate, expand, agree and the v3.3 holds on the real pass outputs (each change with the readings it must hold, judged wrong, and spare, judged right: 1061e3, cf6189; d02f9f, facedc, 181bd0, b88276, 30b092 against 89130e; the eight half-route W against 1552aa; 5505a6; the six faqih statements; the variant hold with and without the release flag, and the `ValueError` for a release without notes), tranche 01's pins (b36519 held; dd8d9b, 0c66ee, 610c03, 31cf87 eligible; the v3.2 wrong cases still held; 6d7565 eligible, pinned on purpose), and table-driven units for the mutaba'a forms and non-forms, the route-end boundaries (same end, back reference, short form, same short form at the end), the half-route boundary, and the pass-through / own chain / other speaker / unknown report cases of the far inheritance.

## 4. What the narrowing costs, and what I did not build

`route_at_most_half_the_longest` narrowed as asked (a shorter route held only when its last link differs) releases 1552aa (R) and **three more readings of the same shape that read wrong: 6d7565 (W, judged, tranche 01, the reading the v3.2 hold was designed on), b1-2c5437 and b1-cb35a4 (batch 001, not judged; the v3.2 README read them as the 6d7565 class)**. All four are a short route that starts with a new head and ends where the long routes end. In the four texts the only separator is the «ح» that precedes the short route in 1552aa («ح وحدثني أبو عثمان») and is absent before the other three («قال وحدثني», «قال وأخبرني», «قال دلهم وحدثنيه»). A rule «same last link and a «ح» before the short route: do not hold» would keep all three held and release 1552aa; **not built** (four readings, and the instruction was the last-link rule), trigger: the owner's word or one more released case. Until then 6d7565 is on tranche 01's withheld list and 2c5437 and cb35a4 should be looked at by hand if v3.3 releases them (`would_release_of_held.tsv`).
Also not built: `imami_pronoun_asker_no_imam` (1 hit, CT, not asked); the 1061e3-shape route-end catch (it is held by the mutaba'a hold; the exemptions that spare dd8d9b also spare it); a Persian/other-spelling extension of the mutaba'a forms (none found).

## 5. Batch 001 against what is applied (`v3_3/batch-001/`, `APPLY_LISTS.md`)

Of the 348 applied readings v3.3 would hold **12, all by the new faqih route-statement hold** (`would_hold_of_applied.tsv`; 11 judged right by the first judge, d752cd not judged): 170d33, 1bea49, 26d360, 297cae, 520cad, 60b019, 703a20, 928814, a05d58, a735be, d752cd, fffeb4. The other new holds hit none of the 348. Of the 46 held, v3.3 would release **2 on the tool side: b1-2c5437 and b1-cb35a4** (the narrowing; both probably wrong, section 4); the other 13 tool-held readings (4 variant, 3 semicolon, 3 Prophet, 2 single-narrator, bb2042) stay held. The other 31 of the 46 are held by pipeline codes only (`stored_chain_checked_by_rule`, `cited_by_later_report`, `inherited_source_chain_uncertain`) that no tool version changes.

## 6. Commands for later tranches (prompt v3.2, judge draw unchanged)

```
T=tranches/tranche-NN          # from chain-reader/
python -B -X utf8 v3_2/validate_v3_2.py --packets $T/packets --outputs $T/outputs/pass-a     # and pass-b (unchanged)
python -B -X utf8 v3_3/triage_v3_3.py --packets $T/packets --pass-a $T/outputs/pass-a --pass-b $T/outputs/pass-b --out $T/triage-v3_3 --reports $T/private/reports.jsonl
python -B -X utf8 v3_2/triage_v3_2.py --packets $T/packets --pass-a $T/outputs/pass-a --pass-b $T/outputs/pass-b --out $T/triage-v3_2 --reports $T/private/reports.jsonl   # the draw reads this folder
python -B -X utf8 v3_2/draw_judge_sample_v3_2.py --tranche NN        # unchanged
python -B -X utf8 v3_3/to_submission_v3_3.py --packets $T/packets --reports $T/private/reports.jsonl --pass-a $T/outputs/pass-a --pass-b $T/outputs/pass-b --out $T/submissions --batch tNN --reader-prompt v3_2 [--only <ids file>]
python -B -X utf8 v3_3/evaluate_v3_3.py                              # tranches 01, 02 and batch 001 only (needs the three v3.3 triages)
```
Variant readings: `--variant-notes-supported` alone carries nothing and releases nothing; only `--variant-notes-supported --release-variant-readings` submits them.
The judge draw is unchanged and therefore draws from the readings eligible under v3.2 (it reads `triage-v3_2`); the readings the v3.3 holds would remove are then in the judged sample, so the judge's verdicts test each new hold out of sample with no extra reading.
Judge brief for a tranche: read each v3.3 hold's hits and say right or wrong (a hold that catches a right reading is a cost); the right-rate among eligible readings against `RUN.md` section 3; read every `needs_ruling_faqih_route_statement` hit only until the owner rules.

## 7. For the pipeline owner (outside this folder, not touched)

- `chain-fixes/chain_fix_engine.py` registers tools `v3`, `v3_1`, `v3_2` (`TOOLS`, `TOOLS_FOR_FORMAT`) and recomputes the holds of the tool named in the envelope. `to_submission_v3_3.py` writes `run.tool_version: "v3_3"`, which the engine refuses until `v3_3` is registered (`(validate_v3_2, expand_v3_2, holds_v3_3.compute_holds)`, the same `v3_2`-only branches for variant remarks extended to `v3_3`). If envelopes are written with `"v3_2"` instead, the engine re-holds with the v3.2 holds: the 3 readings v3.3 releases in tranche 02 (1552aa, 5505a6, 89130e) and 479600 of tranche 01 would be held again, and none of the v3.3-only holds would run (they are already excluded from the lists).
- `chain-fix-submit.ts --variant-notes-supported` lifts `has_variant_group` inside the engine (`chain_fix_engine.py` line 517) independently of this tool. v3.3's triage never lets a variant reading into an envelope without `--release-variant-readings`, but an envelope built by hand and submitted with that engine flag would be released. Pass the engine flag only with an explicit release decision.
