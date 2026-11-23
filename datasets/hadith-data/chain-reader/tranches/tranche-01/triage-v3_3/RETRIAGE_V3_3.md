# Tranche 01 under the v3.3 tool

**Sample status: OUT OF SAMPLE for the v3.3 changes (designed on tranche 02), still IN-SAMPLE for the v3.2 holds (designed on tranche 01).**

## 1. Triage figures, v3.2 tool against v3.3 tool (same outputs, same packets)

| scope | tool | reports | valid A | valid B | both valid | agreed | eligible = chain + no chain |
|---|---|---|---|---|---|---|---|
| all | v3.2 | 980 | 965 | 973 | 960 | 863 (88.1%) | 734 = 721 + 13 (74.9%) |
| all | v3.3 | 980 | 965 | 973 | 960 | 863 (88.1%) | 733 = 720 + 13 (74.8%) |
| six Sunni books | v3.2 | 759 | 749 | 753 | 745 | 672 (88.5%) | 577 = 576 + 1 (76.0%) |
| six Sunni books | v3.3 | 759 | 749 | 753 | 745 | 672 (88.5%) | 578 = 577 + 1 (76.2%) |
| al-Faqih | v3.2 | 67 | 65 | 67 | 65 | 62 (92.5%) | 52 = 48 + 4 (77.6%) |
| al-Faqih | v3.3 | 67 | 65 | 67 | 65 | 62 (92.5%) | 50 = 46 + 4 (74.6%) |
| other Imami | v3.2 | 154 | 151 | 153 | 150 | 129 (83.8%) | 105 = 97 + 8 (68.2%) |
| other Imami | v3.3 | 154 | 151 | 153 | 150 | 129 (83.8%) | 105 = 97 + 8 (68.2%) |

## 2. Hits of every hold on agreed readings (overall; per group sunni / al-Faqih / other Imami), v3.2 tool then v3.3 tool

| hold | v3.2 hits | v3.2 per group | v3.3 hits | v3.3 per group |
|---|---|---|---|---|
| `asker_not_a_link` | 1 | 0 / 0 / 1 | 1 | 0 / 0 / 1 |
| `back_reference_only` | 0 | 0 / 0 / 0 | 0 | 0 / 0 / 0 |
| `back_reference_without_previous_report` | 27 | 25 / 0 / 2 | 27 | 25 / 0 / 2 |
| `bracketed_insertion_differs` | 1 | 0 / 0 / 1 | 1 | 0 / 0 / 1 |
| `empty_reading_transmission_name` | 0 | 0 / 0 / 0 | 0 | 0 / 0 / 0 |
| `empty_reading_unsettled_opening` | 2 | 1 / 1 / 0 | 2 | 1 / 1 / 0 |
| `first_links_split_by_comma` | 1 | 1 / 0 / 0 | 1 | 1 / 0 / 0 |
| `has_variant_group` | 49 | 49 / 0 / 0 | 49 | 49 / 0 / 0 |
| `imami_single_narrator_without_source` | 3 | 0 / 2 / 1 | 3 | 0 / 2 / 1 |
| `inherited_from_far_report` **(changed)** | 1 | 0 / 1 / 0 | 1 | 0 / 1 / 0 |
| `mutabaa_marker` **(changed)** | 0 | 0 / 0 / 0 | 0 | 0 / 0 / 0 |
| `needs_ruling` | 37 | 15 / 5 / 17 | 37 | 15 / 5 / 17 |
| `needs_ruling_faqih_route_statement` **(changed)** | 0 | 0 / 0 / 0 | 4 | 0 / 4 / 0 |
| `needs_ruling_prophet_no_transmitter` | 2 | 0 / 0 / 2 | 2 | 0 / 0 / 2 |
| `nested_jami` | 4 | 1 / 0 / 3 | 4 | 1 / 0 / 3 |
| `nested_semicolon` | 0 | 0 / 0 / 0 | 0 | 0 / 0 / 0 |
| `route_at_most_half_the_longest` **(changed)** | 6 | 6 / 0 / 0 | 5 | 5 / 0 / 0 |
| `route_ends_inside_another_route` **(changed)** | 0 | 0 / 0 / 0 | 4 | 4 / 0 / 0 |
| `routes_end_at_different_links` **(changed)** | 6 | 6 / 0 / 0 | 0 | 0 / 0 / 0 |
| `semicolon_in_multi_route_isnad` | 2 | 0 / 1 / 1 | 2 | 0 / 1 / 1 |
| `too_many_routes` | 3 | 2 / 0 / 1 | 3 | 2 / 0 / 1 |

## 3. The changed and new holds: hits on agreed readings and the judge's verdict among them

R = judged right, W = judged wrong, CT = cannot tell, - = not judged. 'Eligible under v3.2' = the readings this hold would take out of the apply list.

| hold | hits on agreed | of them eligible under v3.2 | judged W | judged R | judged CT | not judged |
|---|---|---|---|---|---|---|
| `mutabaa_marker` | 0 | 0 | 0  | 0  | 0  | 0 |
| `route_ends_inside_another_route` | 4 | 1 | 0  | 0  | 0  | 4 |
| `route_at_most_half_the_longest` | 5 | 0 | 0  | 0  | 0  | 5 |
| `inherited_from_far_report` | 1 | 0 | 0  | 0  | 1 b36519 | 0 |
| `needs_ruling_faqih_route_statement` | 4 | 2 | 1 eb2b15 | 2 34aad2 d8ce40 | 0  | 1 |

Released by v3.3 (eligible under v3.3, held or not agreed under v3.2): 2; judged: 6d7565 W

Newly held by v3.3 (eligible under v3.2, held under v3.3): 3; judged: 34aad2 R (needs_ruling_faqih_route_statement), d8ce40 R (needs_ruling_faqih_route_statement)

## 4. Right-rate among the eligible readings the judge read (undecided counts as not right; Wilson 95%; weights = each group's eligible readings under the tool)

| tool | six Sunni books | al-Faqih | other Imami | weighted |
|---|---|---|---|---|
| v3.2 | 98/99 = 99.0% (94.5-99.8) | 52/52 = 100.0% (93.1-100.0) | 38/39 = 97.4% (86.8-99.5) | **98.8% (95.6-99.7)** (190 judged) |
| v3.3 | 98/100 = 98.0% (93.0-99.4) | 50/50 = 100.0% (92.9-100.0) | 38/39 = 97.4% (86.8-99.5) | **98.1% (94.2-99.4)** (189 judged) |

Judged reading set: 201 sampled readings of the judge (the random draws); 208 readings judged in all (adds the judge's hold, variant and scan reads). **Sample status: OUT OF SAMPLE for the v3.3 changes (designed on tranche 02), still IN-SAMPLE for the v3.2 holds (designed on tranche 01).**

## 5. Judged readings that go the wrong way

**Judged wrong or undecided and still eligible under v3.3: 3**

- t01-0706da W (six Sunni books; sample_verdicts; eligible under v3.2: True)
- t01-6d7565 W (six Sunni books; sample_verdicts; eligible under v3.2: False)
- t01-a20cb6 CT (other Imami; sample_verdicts; eligible under v3.2: True)

**Judged right and eligible under v3.2, held under v3.3: 2** (judged right and not eligible under v3.3 for any reason: 2)

- t01-34aad2 R (al-Faqih; sample_verdicts): needs_ruling_faqih_route_statement
- t01-d8ce40 R (al-Faqih; sample_verdicts): needs_ruling_faqih_route_statement

## 6. al-Faqih route statements («و ما كان فيه عن X فقد رويته عن ...»)

Tagged `faqih_route_statement`: 5 reports, 4 agreed, 2 eligible under v3.2 (the number the new hold removes). Judged: 34aad2 R, d8ce40 R, eb2b15 W.

