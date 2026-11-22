# Batch 001 under the v3.3 tool

**Sample status: OUT OF SAMPLE for the v3.3 changes. The judged readings (301) were drawn from the readings eligible under v3 (the first judge), before any v3.2 or v3.3 hold existed.**

## 1. Triage figures, v3.2 tool against v3.3 tool (same outputs, same packets)

| scope | tool | reports | valid A | valid B | both valid | agreed | eligible = chain + no chain |
|---|---|---|---|---|---|---|---|
| all | v3.2 | 500 | 497 | 497 | 494 | 462 (92.4%) | 387 = 354 + 33 (77.4%) |
| all | v3.3 | 500 | 497 | 497 | 494 | 462 (92.4%) | 378 = 345 + 33 (75.6%) |
| six Sunni books | v3.2 | 250 | 248 | 250 | 248 | 229 (91.6%) | 203 = 203 + 0 (81.2%) |
| six Sunni books | v3.3 | 250 | 248 | 250 | 248 | 229 (91.6%) | 206 = 206 + 0 (82.4%) |
| al-Faqih | v3.2 | 150 | 150 | 150 | 150 | 143 (95.3%) | 100 = 71 + 29 (66.7%) |
| al-Faqih | v3.3 | 150 | 150 | 150 | 150 | 143 (95.3%) | 88 = 59 + 29 (58.7%) |
| other Imami | v3.2 | 100 | 99 | 97 | 96 | 90 (90.0%) | 84 = 80 + 4 (84.0%) |
| other Imami | v3.3 | 100 | 99 | 97 | 96 | 90 (90.0%) | 84 = 80 + 4 (84.0%) |

## 2. Hits of every hold on agreed readings (overall; per group sunni / al-Faqih / other Imami), v3.2 tool then v3.3 tool

| hold | v3.2 hits | v3.2 per group | v3.3 hits | v3.3 per group |
|---|---|---|---|---|
| `asker_not_a_link` | 13 | 0 / 13 / 0 | 13 | 0 / 13 / 0 |
| `back_reference_only` | 1 | 0 / 0 / 1 | 1 | 0 / 0 / 1 |
| `back_reference_without_previous_report` | 28 | 7 / 18 / 3 | 28 | 7 / 18 / 3 |
| `empty_reading_unsettled_opening` | 19 | 0 / 19 / 0 | 19 | 0 / 19 / 0 |
| `has_variant_group` | 11 | 11 / 0 / 0 | 11 | 11 / 0 / 0 |
| `imami_single_narrator_without_source` | 3 | 0 / 2 / 1 | 3 | 0 / 2 / 1 |
| `needs_ruling` | 8 | 4 / 3 / 1 | 8 | 4 / 3 / 1 |
| `needs_ruling_faqih_route_statement` **(changed)** | 0 | 0 / 0 / 0 | 19 | 0 / 19 / 0 |
| `needs_ruling_prophet_no_transmitter` | 3 | 0 / 3 / 0 | 3 | 0 / 3 / 0 |
| `nested_jami` | 5 | 2 / 3 / 0 | 5 | 2 / 3 / 0 |
| `nested_semicolon` | 3 | 0 / 3 / 0 | 3 | 0 / 3 / 0 |
| `route_at_most_half_the_longest` **(changed)** | 6 | 6 / 0 / 0 | 4 | 4 / 0 / 0 |
| `route_ends_inside_another_route` **(changed)** | 0 | 0 / 0 / 0 | 2 | 2 / 0 / 0 |
| `routes_end_at_different_links` **(changed)** | 4 | 4 / 0 / 0 | 0 | 0 / 0 / 0 |
| `second_isnad_not_same_saying` | 0 | 0 / 0 / 0 | 0 | 0 / 0 / 0 |
| `semicolon_in_multi_route_isnad` | 7 | 0 / 7 / 0 | 7 | 0 / 7 / 0 |

## 3. The changed and new holds: hits on agreed readings and the judge's verdict among them

R = judged right, W = judged wrong, CT = cannot tell, - = not judged. 'Eligible under v3.2' = the readings this hold would take out of the apply list.

| hold | hits on agreed | of them eligible under v3.2 | judged W | judged R | judged CT | not judged |
|---|---|---|---|---|---|---|
| `mutabaa_marker` | 0 | 0 | 0  | 0  | 0  | 0 |
| `route_ends_inside_another_route` | 2 | 0 | 0  | 0  | 0  | 2 |
| `route_at_most_half_the_longest` | 4 | 0 | 0  | 0  | 0  | 4 |
| `inherited_from_far_report` | 0 | 0 | 0  | 0  | 0  | 0 |
| `needs_ruling_faqih_route_statement` | 19 | 12 | 0  | 14 03a20 05d58 0b019 20cad 28814 6d360 70d33 735be 97cae bea49 c320a f0528 fe523 ffeb4 | 0  | 5 |

Released by v3.3 (eligible under v3.3, held or not agreed under v3.2): 3; judged: none

Newly held by v3.3 (eligible under v3.2, held under v3.3): 12; judged: 70d33 R (needs_ruling_faqih_route_statement), bea49 R (needs_ruling_faqih_route_statement), 6d360 R (needs_ruling_faqih_route_statement), 97cae R (needs_ruling_faqih_route_statement), 20cad R (needs_ruling_faqih_route_statement), 0b019 R (needs_ruling_faqih_route_statement), 03a20 R (needs_ruling_faqih_route_statement), 28814 R (needs_ruling_faqih_route_statement), 05d58 R (needs_ruling_faqih_route_statement), 735be R (needs_ruling_faqih_route_statement), ffeb4 R (needs_ruling_faqih_route_statement)

## 4. Right-rate among the eligible readings the judge read (undecided counts as not right; Wilson 95%; weights = each group's eligible readings under the tool)

| tool | six Sunni books | al-Faqih | other Imami | weighted |
|---|---|---|---|---|
| v3.2 | 83/83 = 100.0% (95.6-100.0) | 94/96 = 97.9% (92.7-99.4) | 79/82 = 96.3% (89.8-98.7) | **98.7% (96.9-99.4)** (261 judged) |
| v3.3 | 83/83 = 100.0% (95.6-100.0) | 83/85 = 97.6% (91.8-99.4) | 79/82 = 96.3% (89.8-98.7) | **98.6% (96.9-99.4)** (250 judged) |

Judged reading set: 301 sampled readings of the judge (the random draws); 301 readings judged in all (adds the judge's hold, variant and scan reads). **Sample status: OUT OF SAMPLE for the v3.3 changes. The judged readings (301) were drawn from the readings eligible under v3 (the first judge), before any v3.2 or v3.3 hold existed.**

## 5. Judged readings that go the wrong way

**Judged wrong or undecided and still eligible under v3.3: 5**

- b1-4cbe02 W (al-Faqih; sample.tsv; eligible under v3.2: True)
- b1-550aae CT (al-Faqih; sample.tsv; eligible under v3.2: True)
- b1-941f93 CT (other Imami; sample.tsv; eligible under v3.2: True)
- b1-b2ad9c CT (other Imami; sample.tsv; eligible under v3.2: True)
- b1-cb13de CT (other Imami; sample.tsv; eligible under v3.2: True)

**Judged right and eligible under v3.2, held under v3.3: 11** (judged right and not eligible under v3.3 for any reason: 41)

- b1-170d33 R (al-Faqih; sample.tsv): needs_ruling_faqih_route_statement
- b1-1bea49 R (al-Faqih; sample.tsv): needs_ruling_faqih_route_statement
- b1-26d360 R (al-Faqih; sample.tsv): needs_ruling_faqih_route_statement
- b1-297cae R (al-Faqih; sample.tsv): needs_ruling_faqih_route_statement
- b1-520cad R (al-Faqih; sample.tsv): needs_ruling_faqih_route_statement
- b1-60b019 R (al-Faqih; sample.tsv): needs_ruling_faqih_route_statement
- b1-703a20 R (al-Faqih; sample.tsv): needs_ruling_faqih_route_statement
- b1-928814 R (al-Faqih; sample.tsv): needs_ruling_faqih_route_statement
- b1-a05d58 R (al-Faqih; sample.tsv): needs_ruling_faqih_route_statement
- b1-a735be R (al-Faqih; sample.tsv): needs_ruling_faqih_route_statement
- b1-fffeb4 R (al-Faqih; sample.tsv): needs_ruling_faqih_route_statement

## 6. al-Faqih route statements («و ما كان فيه عن X فقد رويته عن ...»)

Tagged `faqih_route_statement`: 20 reports, 19 agreed, 12 eligible under v3.2 (the number the new hold removes). Judged: c320a R, 70d33 R, bea49 R, 6d360 R, 97cae R, fe523 R, 20cad R, 0b019 R, 03a20 R, 28814 R, f0528 R, 05d58 R, 735be R, ffeb4 R.

