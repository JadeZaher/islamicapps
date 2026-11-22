---
type: analysis
---
# Batch 001 re-triaged with the v3.1 tool (no model run)

Existing v3 outputs of both passes, the v3 packets, the v3.1 tool (folds, holds, empty readings, asker rule). Verdicts are the batch-001 judge's (`analysis-batch-001/`), adjusted where the owner's rulings of 2026-11-22 change them (the nine third-person askers, `b1-4cbe02`).

## Agreed, eligible

| | v3 | v3.1 |
|---|---|---|
| valid outputs A / B | 493 / 493 | 497 / 497 |
| agreed | 450 | 457 |
| eligible (agreed, readable, no hold) | 370 | 402 (chain 366, no chain by reading 36) |

Newly valid: 6e0cb4, ab0a95, b50f75, c44673, d8f54e. Newly agreed: 1b65ce, 83044c, ab0a95, b43223, c44673, d8f54e, de6e12.

## Right-rate among the eligible chain readings the judge read

| tool and rulings | group | judged | right | wrong | undecided | right (Wilson 95%) | eligible in group |
|---|---|---|---|---|---|---|---|
| v3 as judged (rulings as given then) | sunni six-book | 85 | 85 | 0 | 0 | 85/85 = 100.0% (96-100) | 205 |
| v3 as judged (rulings as given then) | al-faqih | 80 | 78 | 1 | 1 | 78/80 = 97.5% (91-99) | 86 |
| v3 as judged (rulings as given then) | other imami | 79 | 76 | 0 | 3 | 76/79 = 96.2% (89-99) | 79 |
| v3 as judged (rulings as given then) | **overall** | 244 | 239 | | | 239/244 = 98.0% (95-99); weighted by eligible share 98.6% | |
| v3 outputs applied under the new rulings | sunni six-book | 85 | 85 | 0 | 0 | 85/85 = 100.0% (96-100) | 205 |
| v3 outputs applied under the new rulings | al-faqih | 80 | 70 | 9 | 1 | 70/80 = 87.5% (78-93) | 86 |
| v3 outputs applied under the new rulings | other imami | 79 | 76 | 0 | 3 | 76/79 = 96.2% (89-99) | 79 |
| v3 outputs applied under the new rulings | **overall** | 244 | 231 | | | 231/244 = 94.7% (91-97); weighted by eligible share 96.3% | |
| v3.1 tool | sunni six-book | 90 | 90 | 0 | 0 | 90/90 = 100.0% (96-100) | 210 |
| v3.1 tool | al-faqih | 71 | 70 | 0 | 1 | 70/71 = 98.6% (92-100) | 75 |
| v3.1 tool | other imami | 80 | 77 | 0 | 3 | 77/80 = 96.2% (90-99) | 81 |
| v3.1 tool | **overall** | 241 | 237 | | | 237/241 = 98.3% (96-99); weighted by eligible share 98.9% | |

The v3.1 row includes 6 readings the judge read outside sample.tsv that the tool now lets through: 1b65ce (right), 21210d (right), 3c59ef (right), b43223 (right), d8f54e (right), de6e12 (right).
Eligible chain readings: v3 370, v3.1 366 (235 in sample.tsv, 6 read elsewhere, 125 not read by the judge).

## Asker ruling

12 v3-eligible readings are made wrong by the ruling (the reader dropped the asker): 9 judged (Q1d) and 3 not read, every one of the same shape (`و سأل X Y`). `b1-4cbe02` (the writer of the question kept as a link) is right now.

## Empty readings

36 of the judge's 57 empty readings are now applicable as "no chain by reading" (judge's verdicts of those: {'empty reading: right': 36}); 21 are held: {'cat:asker': 10, 'cat:implicit': 7, 'cat:collective': 1, 'cat:narrative': 1, 'cat:asker-first-person': 1, 'cat:clear-no-name': 1}. Applicable but not judged: 0.

## Holds (hits on agreed readings)

| hold | v3 hits | v3.1 hits | right / wrong among hits |
|---|---|---|---|
| `routes_end_at_different_links` | 7 | 4 | v3 2 / 5; v3.1 0 / 4; released 21210d, 3c59ef, ee5c9a |
| `reading_empty_stored_has_links` | 55 | 0 | 46 right as no-chain, 9 undecided, 0 wrong, of 55 hits |
| `empty_reading_transmission_name` | 0 | 0 |  |
| `empty_reading_unsettled_opening` | 0 | 19 | empty readings the rulings touch: {'cat:asker': 9, 'cat:implicit': 7, 'cat:narrative': 1, 'cat:asker-first-person': 1, 'cat:clear-no-name': 1} |
| `asker_not_a_link` | 0 | 13 | all wrong under the ruling (judged: 9; the others are the same shape) |
| `back_reference_without_previous_report` | 10 | 28 | the extra hits are the new openings in the v3 packets, which carry no previous report; the v3.1 builder supplies one |
| `back_reference_only` | 1 | 1 |  |
| `needs_ruling` | 8 | 8 |  |
| `nested_jami` | 5 | 5 |  |
| `nested_semicolon` | 3 | 3 |  |

## Lists

- `eligible_to_apply.txt`: 394 readings (agreed, unheld under v3.1, outside every ruling), 36 of them "no chain by reading"; withheld although eligible: 6 the judge read as undecided or turning on a point not yet ruled (550aae, 57c34c, 86d128, 941f93, b2ad9c, cb13de).
- `reread_under_v3_1.txt`: 39 reports: {'asker_pronoun': 13, 'implicit_speaker': 6, 'asker_named': 19, 'bare_an': 1}; 3 of them are agreed and unheld (a pattern match whose v3 reading is consistent with the ruling) and are read again anyway.
- Not in either list: 1 «روي عن الأئمة» report (not ruled; stays held).
