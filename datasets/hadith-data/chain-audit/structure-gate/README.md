---
type: diagnostic
---
# Chain structure gate (round 4): which stored chains a tested rule stands behind

Three rounds of builder rules left the Sunni strict chain-defect rate at 10.7% -> 17.3% -> 18.0% (`../round3/README.md`).
Round 4 changes the goal to the precision of what is asserted: a chain the detectors in
`datasets/hadith-data/pg_export/chain_structure.py` flag is stored and shown as read, marked `uncertain` with its reasons, and
forms no teacher-student pair. Everything here is measured on the re-checks' read verdicts, never on new reading.

Run (read-only): `python -I datasets/hadith-data/chain-audit/structure-gate/measure.py --read <projection 2026.11.22.8>
--before <projection-m3> --out results.json` (paths in the script's docstring). `fixtures.json` holds the real rows the
detector tests read.

## Labelled set

980 units, 119 strictly defective: the round-3 random sample (311 of the 320 drawn; 9 al-Rabi reports with no stored chain
assert nothing and are left out), the round-3 changed populations (237), and 432 round-2 items whose report's chains are
identical in projection-m3 and 2026.11.22.8 (round 2 read them; round 2 counts only its strict kinds). "Strict" is the
re-checks' definition (missing, false, merged or split link, non-narrator as a name, wrongly inherited chain).

## Detectors (all labelled units: flags on defective / on correct; chains flagged in production 2026.11.22.8)

| code | defective | correct | production chains | in the gate |
|---|---|---|---|---|
| many_routes | 31 | 30 | 7,930 | yes |
| not_a_name | 27 | 24 | 6,977 | yes |
| text_between_links | 27 | 8 | 5,515 | yes |
| text_names_more_after | 21 | 14 | 5,951 | yes |
| duplicated_link | 14 | 0 | 1,001 | yes |
| order_not_in_text | 12 | 23 | 2,519 | no |
| work_not_checked | 11 | 87 | 10,401 | yes |
| repeated_name | 10 | 1 | 1,216 | yes |
| joined_names | 8 | 0 | 678 | yes |
| short_beside_long | 4 | 0 | 448 | yes |
| ghayr_wahid_half | 4 | 0 | 103 | yes |
| crossed_routes | 2 | 0 | 143 | yes |
| unaccounted_route_marker | 2 | 7 | 1,011 | yes |
| long_chain | 2 | 0 | 281 | no |
| route_break_inside | 1 | 4 | 669 | no |
| prose_work (retired) | 4 | 3 | 238 | retired |
| chapter_heading (retired) | 1 | 0 | 20 | retired |

A unit may carry several codes, so the columns overlap. The greedy curve (`results.json` `curve_all_labelled`) adds one
detector at a time by defects removed per correct chain lost: 12.1% defective before any gate; 6.6% after the six cheap
shape detectors (correct kept 849/861); 3.3% after `text_names_more_after` and `not_a_name` (812/861); 2.6% after
`many_routes` (778/861); 2.1% after `work_not_checked` (700/861).

## Operating point and why

Every detector above except `order_not_in_text`, `route_break_inside` and `long_chain`. Those three removed at most 2 defects
the others had not already removed, at 4 to 20 correct chains each. `many_routes` and `work_not_checked` are blunt (half and
an eighth of their flags are defects) but they are what brings the random sample's K6 and Imami rates near 5%; the owner's
priority is the precision of the teacher and student lists. Removing a work from `UNCHECKED_WORKS` or raising `MANY_ROUTES`
reverses either at the next export.

## Result (strict defect rate; Wilson 95%)

| group | before the gate | share checked | among checked |
|---|---|---|---|
| **Round-3 random sample** | | | |
| Sunni, nine works | 18/100 = 18.0% (11.7-26.7) | 76/100 | 2/76 = 2.6% (0.7-9.1) |
| Sunni K6 text works | 17/67 = 25.4% (16.5-36.9) | 47/67 | 2/47 = 4.3% (1.2-14.2) |
| Sunni Pure Canon | 1/33 = 3.0% (0.5-15.3) | 29/33 | 0/29 = 0.0% (0.0-11.7) |
| Imami | 17/100 = 17.0% (10.9-25.5) | 63/100 | 2/63 = 3.2% (0.9-10.9) |
| al-Rabi (reports with a chain) | 5/31 = 16.1% (7.1-32.6) | 26/31 | 2/26 = 7.7% (2.1-24.1) |
| Musnad Zayd | 1/40 = 2.5% (0.4-12.9) | 39/40 | 0/39 = 0.0% (0.0-9.0) |
| Sahifat al-Rida | 0/40 = 0.0% (0.0-8.8) | 40/40 | 0/40 = 0.0% (0.0-8.8) |
| **All labelled units** | 119/980 = 12.1% (10.2-14.3) | 725/980 | 16/725 = 2.2% (1.4-3.6) |
| Sunni K6 | 65/226 = 28.8% (23.3-35.0) | 127/226 | 6/127 = 4.7% (2.2-9.9) |
| Imami | 38/391 = 9.7% (7.2-13.1) | 257/391 | 5/257 = 1.9% (0.8-4.5) |
| al-Rabi | 10/116 = 8.6% (4.7-15.1) | 105/116 | 3/105 = 2.9% (1.0-8.1) |

Plainly: **al-Rabi cannot be shown below 5%**: its two remaining defects (`rabi_0644`, `rabi_0229`) are a Companion's source
named in the matn («سمعتني أم الفضل»), which no shape rule sees, and 26 chains cannot bound the rate under 24%. The K6 and Imami
upper bounds on the random sample (14.2%, 10.9%) are also above 5%; the point estimates and the all-labelled rates are below.
The Sunni K6 gate keeps only 70% of chains; Sahih Muslim, the worst work, keeps under half (`results.json` and the projection
manifest's `counts.chain_structure`).

## What the gate does not see

Names lost after «أن X حدثه» when the text names no one with a link word; a Companion's source in the matn; concatenated Imami
isnads without a repeated name or a «ح»; the Imam convention gap (not a defect). Those stay in checked chains at the rates
above.
