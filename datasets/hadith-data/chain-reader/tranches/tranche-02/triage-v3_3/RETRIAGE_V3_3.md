# Tranche 02 under the v3.3 tool

**Sample status: IN-SAMPLE for the v3.3 changes (they were designed on tranche 02's judgement); the judge's draw of 244 is the same sample.**

## 1. Triage figures, v3.2 tool against v3.3 tool (same outputs, same packets)

| scope | tool | reports | valid A | valid B | both valid | agreed | eligible = chain + no chain |
|---|---|---|---|---|---|---|---|
| all | v3.2 | 980 | 970 | 977 | 969 | 862 (88.0%) | 706 = 695 + 11 (72.0%) |
| all | v3.3 | 980 | 970 | 977 | 969 | 862 (88.0%) | 700 = 689 + 11 (71.4%) |
| six Sunni books | v3.2 | 759 | 751 | 757 | 750 | 670 (88.3%) | 549 = 549 + 0 (72.3%) |
| six Sunni books | v3.3 | 759 | 751 | 757 | 750 | 670 (88.3%) | 548 = 548 + 0 (72.2%) |
| al-Faqih | v3.2 | 66 | 65 | 66 | 65 | 60 (90.9%) | 48 = 40 + 8 (72.7%) |
| al-Faqih | v3.3 | 66 | 65 | 66 | 65 | 60 (90.9%) | 42 = 34 + 8 (63.6%) |
| other Imami | v3.2 | 155 | 154 | 154 | 154 | 132 (85.2%) | 109 = 106 + 3 (70.3%) |
| other Imami | v3.3 | 155 | 154 | 154 | 154 | 132 (85.2%) | 110 = 107 + 3 (71.0%) |

## 2. Hits of every hold on agreed readings (overall; per group sunni / al-Faqih / other Imami), v3.2 tool then v3.3 tool

| hold | v3.2 hits | v3.2 per group | v3.3 hits | v3.3 per group |
|---|---|---|---|---|
| `back_reference_only` | 4 | 0 / 1 / 3 | 4 | 0 / 1 / 3 |
| `back_reference_without_previous_report` | 32 | 31 / 0 / 1 | 32 | 31 / 0 / 1 |
| `empty_reading_transmission_name` | 1 | 0 / 0 / 1 | 1 | 0 / 0 / 1 |
| `empty_reading_unsettled_opening` | 0 | 0 / 0 / 0 | 0 | 0 / 0 / 0 |
| `first_links_split_by_comma` | 0 | 0 / 0 / 0 | 0 | 0 / 0 / 0 |
| `has_variant_group` | 77 | 75 / 0 / 2 | 77 | 75 / 0 / 2 |
| `imami_single_narrator_without_source` | 3 | 0 / 3 / 0 | 3 | 0 / 3 / 0 |
| `inherited_from_far_report` **(changed)** | 1 | 0 / 0 / 1 | 0 | 0 / 0 / 0 |
| `mutabaa_marker` **(changed)** | 0 | 0 / 0 / 0 | 3 | 3 / 0 / 0 |
| `needs_ruling` | 36 | 15 / 6 / 15 | 36 | 15 / 6 / 15 |
| `needs_ruling_faqih_route_statement` **(changed)** | 0 | 0 / 0 / 0 | 10 | 0 / 10 / 0 |
| `nested_jami` | 4 | 1 / 3 / 0 | 4 | 1 / 3 / 0 |
| `nested_semicolon` | 5 | 0 / 4 / 1 | 5 | 0 / 4 / 1 |
| `route_at_most_half_the_longest` **(changed)** | 9 | 9 / 0 / 0 | 8 | 8 / 0 / 0 |
| `route_ends_inside_another_route` **(changed)** | 0 | 0 / 0 / 0 | 5 | 4 / 0 / 1 |
| `routes_end_at_different_links` **(changed)** | 8 | 7 / 0 / 1 | 0 | 0 / 0 / 0 |
| `semicolon_in_multi_route_isnad` | 5 | 0 / 4 / 1 | 5 | 0 / 4 / 1 |
| `too_many_routes` | 1 | 1 / 0 / 0 | 1 | 1 / 0 / 0 |

## 3. The changed and new holds: hits on agreed readings and the judge's verdict among them

R = judged right, W = judged wrong, CT = cannot tell, - = not judged. 'Eligible under v3.2' = the readings this hold would take out of the apply list.

| hold | hits on agreed | of them eligible under v3.2 | judged W | judged R | judged CT | not judged |
|---|---|---|---|---|---|---|
| `mutabaa_marker` | 3 | 2 | 2 1061e3 cf6189 | 0  | 0  | 1 |
| `route_ends_inside_another_route` | 5 | 1 | 5 181bd0 30b092 b88276 d02f9f facedc | 0  | 0  | 0 |
| `route_at_most_half_the_longest` | 8 | 0 | 8 03f4b1 0aec9d 181bd0 56b32a 80403f b88276 dee88c facedc | 0  | 0  | 0 |
| `inherited_from_far_report` | 0 | 0 | 0  | 0  | 0  | 0 |
| `needs_ruling_faqih_route_statement` | 10 | 6 | 2 0a8f48 6da700 | 8 0bcea2 1531a8 397ef7 46c4c6 65b393 94355c 9a44c0 beb57a | 0  | 0 |

Released by v3.3 (eligible under v3.3, held or not agreed under v3.2): 3; judged: 1552aa R, 5505a6 R, 89130e R

Newly held by v3.3 (eligible under v3.2, held under v3.3): 9; judged: 0bcea2 R (needs_ruling_faqih_route_statement), 1061e3 W (mutabaa_marker), 1531a8 R (needs_ruling_faqih_route_statement), 397ef7 R (needs_ruling_faqih_route_statement), 46c4c6 R (needs_ruling_faqih_route_statement), 94355c R (needs_ruling_faqih_route_statement), beb57a R (needs_ruling_faqih_route_statement), cf6189 W (mutabaa_marker), d02f9f W (route_ends_inside_another_route)

## 4. Right-rate among the eligible readings the judge read (undecided counts as not right; Wilson 95%; weights = each group's eligible readings under the tool)

| tool | six Sunni books | al-Faqih | other Imami | weighted |
|---|---|---|---|---|
| v3.2 | 153/156 = 98.1% (94.5-99.3) | 47/48 = 97.9% (89.1-99.6) | 38/40 = 95.0% (83.5-98.6) | **97.6% (94.7-98.9)** (244 judged) |
| v3.3 | 153/155 = 98.7% (95.4-99.6) | 41/42 = 97.6% (87.7-99.6) | 38/40 = 95.0% (83.5-98.6) | **98.1% (95.4-99.2)** (237 judged) |

Judged reading set: 244 sampled readings of the judge (the random draws); 268 readings judged in all (adds the judge's hold, variant and scan reads). **Sample status: IN-SAMPLE for the v3.3 changes (they were designed on tranche 02's judgement); the judge's draw of 244 is the same sample.**

## 5. Judged readings that go the wrong way

**Judged wrong or undecided and still eligible under v3.3: 5**

- t02-0dfb7f CT (al-Faqih; sample_verdicts; eligible under v3.2: True)
- t02-3cacbd CT (other Imami; sample_verdicts; eligible under v3.2: True)
- t02-553df1 W (six Sunni books; sample_verdicts; eligible under v3.2: True)
- t02-fe8248 CT (other Imami; sample_verdicts; eligible under v3.2: True)
- t02-fecbb4 CT (six Sunni books; sample_verdicts; eligible under v3.2: True)

**Judged right and eligible under v3.2, held under v3.3: 6** (judged right and not eligible under v3.3 for any reason: 9)

- t02-0bcea2 R (al-Faqih; sample_verdicts): needs_ruling_faqih_route_statement
- t02-1531a8 R (al-Faqih; sample_verdicts): needs_ruling_faqih_route_statement
- t02-397ef7 R (al-Faqih; sample_verdicts): needs_ruling_faqih_route_statement
- t02-46c4c6 R (al-Faqih; sample_verdicts): needs_ruling_faqih_route_statement
- t02-94355c R (al-Faqih; sample_verdicts): needs_ruling_faqih_route_statement
- t02-beb57a R (al-Faqih; sample_verdicts): needs_ruling_faqih_route_statement

## 6. al-Faqih route statements («و ما كان فيه عن X فقد رويته عن ...»)

Tagged `faqih_route_statement`: 13 reports, 10 agreed, 6 eligible under v3.2 (the number the new hold removes). Judged: 0a8f48 W, 0bcea2 R, 1531a8 R, 397ef7 R, 46c4c6 R, 65b393 R, 6da700 W, 94355c R, 9a44c0 R, beb57a R.

