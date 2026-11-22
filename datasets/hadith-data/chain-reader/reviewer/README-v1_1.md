---
type: pilot
---
# Chain reviewer v1.1: after the pilot's adjudication

Built 2026-11-22, file side only: **no model was run, no database written**, nothing outside `reviewer/` touched. v1 (`README.md`, `AGENTS.md`, `INTEGRATION.md`, `prompt-reviewer-v1.md`, `review_rules.py`, `validate_review.py`, `build_review_packets.py`,
`pilot-001/`) is intact beside this; v1.1 files carry `_v1_1` / `-v1_1`. The pilot's adjudication (`pilot-001/adjudication/`, one Opus reader over 55 of 81 items; not blind, not human) is the evidence for every change below.

| file | what |
|---|---|
| `prompt-reviewer-v1_1.md` / `.json` | prompt 1.1.0, sha256 **`1136aec2c975aebd0f4b8f17cf14d6ad1410229c33b97e7d8382b8258cb735f6`**, 13,520 letters (v1: 11,017) |
| `review_rules_v1_1.py` | the decision rule (`outcome`), `stored_equals_reading`, `correction_is`, `needs_second_pass`; imports v1's hold table and adds one code |
| `validate_review_v1_1.py` | per-item validation; `review_io_v1_1.py` reads a batch's passes per item |
| `out_of_order_validator.py`, `FORMAT_GAP.md` | the format-gap proposal, implemented reviewer-side only |
| `build_review_packets_v1_1.py` | the six review sets, `--second-pass`, `--requeue`; `make_review_mission.py` (Conduction); `record_reviews_v1_1.py` (outcomes per item) |
| `pilot-001/rescore_v1_1.py`, `RESCORE_V1_1.md`, `rescore_v1_1.json` | the pilot re-scored under v1.1 against the adjudicated verdicts |
| `RUN.md`, `INTEGRATION-v1_1.md`, `SETS.json` | how to run; what the integrator changes; the set sizes |

## 1. Per item, not per packet

The pilot's packet 04 lost 9 right reviews (8 confirmations and a right correction) because one corrected reading was invalid. `validate_review_v1_1.validate_output` returns each item on its own: valid reviews are recorded, an invalid one is recorded invalid with its first reason and
re-queued (`build_review_packets_v1_1.py --requeue` writes fresh packets for exactly those), and a duplicate or missing review is that item's problem. Only a header problem (format, specialist, prompt version, packet id, not JSON) voids the whole output, since such an output cannot be trusted as a whole.
Under per-item validation the pilot has 80 valid items of 81; the one invalid item is cr1-750b73, the format gap (`FORMAT_GAP.md`).

## 2. The decision rule (`review_rules_v1_1.outcome`; (a) to (e) are the owner's amendments after the pilot)

The status at recording time (from the fix store, not the packet) picks the table. `pending` (cleared by the tool, waiting to be applied) behaves as held with no holds.

**(a) A correction equal to the reading is a confirmation.** If `confirm_with_correction`'s corrected routes equal the readers' agreed reading after the tool's canonical folds (`expand_v3_4.readings_agree`), the decision counts as `confirm_reading`; if the readers differ and it equals one reader's, as `prefer_reader_x`.
One tightening the tool does not have: its agreement ignores `inherited` links (derived), so a correction that changes only WHOM the report inherits would "agree"; `correction_is` also compares the inherited names, and the pilot's cr1-6dfc38 (right correction, readers inherited the asker) stays a correction.

**(b) An ALREADY-APPLIED reading is never reverted by a correction or a referral.** It stays applied, labelled "disputed; awaiting second review", and the correction is queued for pass 2. If a second independent review writes the same corrected routes, the correction replaces the reading (not the stored chain).

**(c) A HELD (or pending) reading:** a non-clearable hold stands whatever the reviewer says (`keep_held`); `confirm_reading` applies it; `prefer_reader_a/b` applies that reader; `confirm_with_correction` applies only with a second matching review, else `queue_for_human`; a referral keeps it held (with a partial `corrected_reading`: queued for a human, never applied);
`keep_stored` sets it aside.

**(d) `keep_stored` on an applied reading reverts only when the stored chain actually differs from the reading** (`stored_equals_reading is False`); equal or unknown: labelled disputed.

**(e) A human decision always wins** (`outcome(..., human="confirmed" | "rejected")` returns `human_decides`).

| status | decision (effective, after (a)) | outcome |
|---|---|---|
| held / pending | any, with a non-clearable hold | `keep_held` |
| | `confirm_reading` / `no_chain` on an agreed empty reading | `apply_reading` |
| | `prefer_reader_a` / `_b` (readers differ) | `apply_reader_a` / `_b` |
| | `confirm_with_correction` / `no_chain` against routes | second run agrees: `apply_correction` / `apply_no_chain`; else `queue_for_human` |
| | `keep_stored` | `discard_reading` |
| | `refer_to_human` | `keep_held` (`queue_for_human` with a partial correction) |
| applied | `confirm_reading` / `no_chain` on an applied "no chain" | `label_ai_reviewed` |
| | `confirm_with_correction` / `no_chain` against routes | second run agrees: `apply_correction` / `apply_no_chain` (replaces); else **`label_disputed`** |
| | `refer_to_human`, `prefer_*` | **`label_disputed`** |
| | `keep_stored` | `revert_to_stored` if the stored chain differs, else `label_disputed` |

Which holds the reviewer may clear is unchanged (v1 README §2) plus one new clearable code, `withheld_by_earlier_check` (a tool-cleared reading an earlier check set aside; shown without the verdict).

## 3. Prompt 1.1.0: what changed

1. `corrected_reading` is allowed with `refer_to_human` (the part the rulings settle is corrected; the open question is named). Three of the pilot's ten referrals (d695ec, 5415bf, b567d7) bundled an error the rulings settle with a question they do not.
2. When the holds already name an unruled question, review the STRUCTURE anyway and say, in the reasons, whether the reading would be right if the question went either way; `question` may name the unruled question on any decision (the pilot's five al-Faqih referrals decided nothing: the hold already kept them held).
3. Representation is no reason to correct (kinds, notes, variant-group placement, where a back reference stands): routes equal the readers' -> `confirm_reading` (the pilot's three cosmetic corrections).
4. Rulings 9 (narrated encounter: the one who speaks is the last link; present-only «علي ابنه» stays out; two speakers keep their own chains) and 10 (two sayings: a real example, «وأخبرني خارجة بن زيد بن ثابت …») are explicit with one example each.
5. **Ruling 11, a working rule the owner has not ruled** (the adjudicator's uncovered case): a fully written chain after the text ending «مثله» / «نحوه» is a ROUTE of this saying when it writes its own transmitters («حَدَّثَنِي مُحَمَّدُ بْنُ جَعْفَرٍ … عَنْ أَبِي الْحَسَنِ الثَّالِثِ مِثْلَهُ»); a bare «بمثل حديث فلان» stays a remark (ruling 6).
   It is also listed under "Still unruled", and the reviewer names it in `question` while reviewing as if the rule holds.
6. A connecting chain written AFTER the names it connects to cannot be written in the format: `refer_to_human`, `question` begins "format: connecting chain after the names", the route in words (until `FORMAT_GAP.md` is adopted).
7. `status` gains `pending`; "every item is reviewed on its own". Header and output skeleton say 1.1.0.

## 4. The pilot re-scored under v1.1, against the adjudicated verdicts (`pilot-001/RESCORE_V1_1.md`, per item)

26 wrong, 52 right (26 read by the adjudicator, 26 assumed), 3 unruled (al-Faqih route statements). Corrections with the readers' own routes count as confirmations; the invalid item stays as it was.

| truth | reviewer | n | what v1.1's rule does | right outcome? |
|---|---|---|---|---|
| wrong (26): caught 26 of 26, confirmed 0 | corrected 18, referred 7, 1 invalid (750b73: format gap, re-queued) | 26 | kept held 10 (6 referrals, 4 corrections under a non-clearable hold); correction queued, no second run yet, 13; **applied and labelled disputed 2** (80cd84, d695ec); re-queued 1 | 24 stay off the page; 2 stay on the page, labelled; 0 confirmed. v1 would have reverted both to a stored chain identical to the reading (`stored_equals_reading` true): no gain |
| right (52): confirmed 52 of 52 | confirmed 49, cosmetic correction 3 (593d35, cd74d5 held; e87ace applied) | 52 | applied 19; labelled AI reviewed 30; held by a non-clearable hold 3 | 49 right, 3 held by design (only a human clears them). v1 queued two cosmetic corrections and **reverted e87ace to a worse stored chain** |
| unruled (3) | referred 3 | 3 | stay held | right |
| the 18 substantive valid corrections, after a faithful second run (same routes; the 3 cosmetic are confirmations, 750b73 is invalid) | corrected 18 | 18 | 14 `apply_correction` (12 right, 2 right at medium confidence, all adjudicated right); 4 stay held by a non-clearable hold (2 right, 2 right at medium) | all right |

Against the proposed gate (v1 README §2, 14 of 16 judge-wrong caught, 90% of right confirmed): 26 of 26 wrong caught; 52 of 52 right confirmed (49 outright, 3 cosmetic counted by rule (a)). Harmful outcomes: 0 (a wrong reading applied or confirmed; a right reading removed). Limits: the adjudicator is one more Opus reader; 26 right items were not read; no person has checked;
the applied sample (32) holds no wrong reading the judge found, so "right reading disputed on an applied page" is measured on 1 cosmetic case only.

## 5. Sets, running, integration

`RUN.md` (sizes in §1, how to run, validate and map outcomes). Sizes: A 348 readings / 35 jobs; t01 eligible 730 / 73, held 133 / 14; t02 eligible 695 / 70, held 167 / 17; C 107 / 11; 2,180 readings, 220 jobs, 17.5 million packet characters. `INTEGRATION-v1_1.md`: what the pipeline owner changes.

## 6. Tests

`python -B -X utf8 -m unittest discover -s reviewer/tests -p "test_*.py"` (from `chain-reader/`): v1's 9 and v1.1's 14. Flows: per-item validation on the pilot's real packet 04 (one invalid, nine stand; a header problem voids all; missing and doubled reviews); the v1.1 vocabulary; the rule as a 20-row table (a to e);
`correction_is` on the pilot's real corrections (3 cosmetic equal, 4 substantive not, 6dfc38 not); `stored_equals_reading` on 80cd84, d695ec, e87ace; the format extension on cr1-750b73 (v3.4 refuses, flagged accepts with the route in order, five misdeclarations refused, the reviewer validator only with the flag);
the built sets (counts, jobs against packets and prompt hash, no original id or verdict in any packet, statuses, withheld counts, the applied set equal to the fix store); second pass, re-queue and record end to end on the pilot's packets and outputs.

## 7. Not built

- No reviewer run; v1.1 is not measured: the re-score replays v1.0.0 outputs under the new rule, not the new prompt.
- The pipeline side: `INTEGRATION-v1_1.md`. The reader toolchain's out-of-order change: `FORMAT_GAP.md`.
- Ruling 11 is a working rule, not the owner's; the sets reviewed under it carry its question in `question`.
- Pass-2 packets and re-queue packets are built only after pass 1 exists.
