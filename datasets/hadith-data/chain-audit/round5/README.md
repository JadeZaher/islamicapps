---
type: diagnostic
---
# Gate recalibration (round 5): the structure gate re-tuned on a split

Read-only measurement. The only code change is `pg_export/chain_structure.py` (and the wording that reads it). Method:
`recalibrate.py` (-> `results.json`), real-row tests `fixtures.json` / `test_chain_structure.py`, pair check `new_pairs.py`.

## 1. The correction that matters

Round 4 (`../round4/README.md`) read 520 items drawn at random from production after the gate existed. Strict defects among chains
the gate passed (Wilson 95%): Sunni 8.3% (4.6-14.7), six-books text works 10.6% (5.7-18.9), Pure Canon 2.9% (0.5-14.5), Imami 4.0%
(1.6-9.8; al-Kafi 0/70, al-Faqih 4/20), al-Rabi 5.0% (1.4-16.5), Zayd 0/25, Rida 1/25 (4.0%). The figures
`../structure-gate/README.md` first published (Sunni 2.6%, six-books 4.3%, Imami 3.2%, al-Rabi 7.7%) were measured on the same readings
the rules were tuned on and were too low. `/method` (`src/lib/review/procedures.ts`, `chain-structure-gate`) and that README now state
the out-of-sample rates, the pair precision (149/150 = 99.3%, 96.3-99.9), the share of withheld chains that are correct (40/60 = 66.7%,
54.1-77.3), and that the recalibrated gate below has no out-of-sample rate yet.

## 2. The split and the rule for keeping a change

- **Tuning set**: round 3's sample and changed populations plus round 2's unchanged items (980 units, 119 strictly defective;
  `../structure-gate/`), read on projection 2026.11.22.8.
- **Held-out set**: round 4's 370 chain readings (310 drawn among chains the round-4 gate passed, 60 among those it withheld; 37
  defective), read on projection 2026.11.22.9. Pairs are kept apart (section 6).
- Operating point, in the owner's order: (1) pair precision stays at or above 99%; (2) the defect rate among checked chains on the
  held-out set is no worse than the round-4 gate's, per tradition; (3) then the share checked is as large as (2) allows. A loosening is
  kept only when the tuning set does not contradict it; a tightening when its cost on the tuning set is a handful of correct chains.
- **What the split cannot do.** The brief names the shapes to add (Faqih sayings, «تابع/», «حدثناه», hearing verbs, «وعن», inherited
  tails) *from round 4's own readings*. Those tightenings are therefore in-sample on the held-out set: their held-out gain (17 -> 4
  defects among checked) is by construction, not a rate we claim. What the split does test is their cost and recall on the tuning set,
  which did not design them: together they flag 1 defective chain (Rida 16#3) and 7 correct ones there (section 4), so no recall evidence
  and a small cost. Two changes were chosen after seeing tuning data (`sibling_skips_link`, the Pure Canon-only gloss exemption) and say
  so. The only out-of-sample figure that exists is round 4's, for the old gate; the new gate needs a round 6 on fresh readings.

## 3. Before -> after (strict defect rate among checked chains; Wilson 95%)

| group | tuning: checked, round 4 gate -> now | tuning: defects among checked, round 4 -> now | held-out: checked, round 4 gate -> now | held-out: defects among checked, round 4 -> now |
|---|---|---|---|---|
| All read units | 725/980 -> 802/980 | 16/725 = 2.2% (1.4-3.6) -> 18/802 = 2.2% (1.4-3.5) | 310/370 -> 319/370 | 17/310 = 5.5% (3.5-8.6) -> 4/319 = 1.3% (0.5-3.2) |
| Sunni | 182/290 -> 181/290 | 6/182 = 3.3% (1.5-7.0) -> 6/181 = 3.3% (1.5-7.0) | 120/160 -> 122/160 | 10/120 = 8.3% (4.6-14.7) -> 2/122 = 1.6% (0.5-5.8) |
| - six-books text works | 127/226 -> 125/226 | 6/127 = 4.7% (2.2-9.9) -> 6/125 = 4.8% (2.2-10.1) | 85/112 -> 78/112 | 9/85 = 10.6% (5.7-18.9) -> 2/78 = 2.6% (0.7-8.9) |
| - Pure Canon | 55/64 -> 56/64 | 0/55 = 0.0% (0.0-6.5) -> 0/56 = 0.0% (0.0-6.4) | 35/48 -> 44/48 | 1/35 = 2.9% (0.5-14.5) -> 0/44 = 0.0% (0.0-8.0) |
| Imami | 257/391 -> 336/391 | 5/257 = 1.9% (0.8-4.5) -> 8/336 = 2.4% (1.2-4.6) | 100/120 -> 108/120 | 4/100 = 4.0% (1.6-9.8) -> 0/108 = 0.0% (0.0-3.4) |
| al-Rabi | 105/116 -> 105/116 | 3/105 = 2.9% (1.0-8.1) -> 3/105 = 2.9% (1.0-8.1) | 40/40 -> 40/40 | 2/40 = 5.0% (1.4-16.5) -> 2/40 = 5.0% (1.4-16.5) |
| Musnad Zayd | 93/95 -> 93/95 | 0/93 = 0.0% (0.0-4.0) -> 0/93 = 0.0% (0.0-4.0) | 25/25 -> 25/25 | 0/25 = 0.0% (0.0-13.3) -> 0/25 = 0.0% (0.0-13.3) |
| Sahifat al-Rida | 88/88 -> 87/88 | 2/88 = 2.3% (0.6-7.9) -> 1/87 = 1.1% (0.2-6.2) | 25/25 -> 24/25 | 1/25 = 4.0% (0.7-19.5) -> 0/24 = 0.0% (0.0-13.8) |

Held-out counts are over both strata (the checked-stratum chains the new gate still passes plus withheld-stratum chains it now passes).
Re-weighted to the population (round 4 drew 310 passed and 60 withheld chains; the withheld stratum is 30% of chains but 16% of the sample),
point estimate and 95% bootstrap range (`results.json` `held_out_weighted_point_low_high`): Sunni 8.3% (4.2-13.3) -> 1.6% (0.0-4.1); six-books
10.6% (4.7-17.6) -> 2.6% (0.0-6.6); Imami 4.0% (1.0-8.0) -> 0.0% (no defect in any resample).

Share of all stored chains checked in production (projection 2026.11.22.9): 77,630 of 110,999 (69.9%) -> 88,349 (79.6%). Sunni 55,821
(73.2%) -> 58,287 (76.4%; six-books text works 68.0% -> 67.6%, Pure Canon 80.9% -> 89.4%); Imami 20,348 (61.2%) -> 28,602 (86.1%; al-Kafi
91.3% -> 91.3%, al-Faqih 83.9% -> 81.2%, the 15 small works 0% -> 58-93%); al-Rabi 95.0% -> 94.9%; Zayd 99.3% -> 99.3%; Rida 99.5% -> 98.5%.
11,925 chains are released and 1,206 newly withheld.

## 4. Per change: what each flags or releases

"Flagged" = the final gate withholds a chain the gate without this change would check (a tightening: the defective count is the good
column). "Released" = the reverse. Each row reverses one change of the final gate (`recalibrate.py` ablations), on each set and over all
110,999 production chains.

| change | tuning: flagged defective / correct | tuning: released defective / correct | held-out: flagged d / c | held-out: released d / c | production chains flagged | production chains released |
|---|---|---|---|---|---|---|
| `asker_and_imam_in_one_link` | 0 / 3 | 0 / 0 | 2 / 1 | 0 / 0 | 376 | 0 |
| `gloss_beside_name` | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 6 | 0 | 1,762 |
| `hadathanah` | 0 / 2 | 0 / 0 | 1 / 0 | 0 / 0 | 87 | 0 |
| `inherited_tail` | 1 / 0 | 0 / 0 | 1 / 0 | 0 / 0 | 2 | 0 |
| `label_formula` | 0 / 0 | 0 / 11 | 0 / 0 | 0 / 1 | 0 | 628 |
| `pure_canon_tail_exempt` | 0 / 0 | 0 / 6 | 0 / 0 | 0 / 5 | 0 | 1,722 |
| `saying_as_single_link` | 0 / 0 | 0 / 0 | 2 / 0 | 0 / 0 | 158 | 0 |
| `tabi_slash` | 0 / 1 | 0 / 0 | 1 / 0 | 0 / 0 | 357 | 0 |
| `tail_hearing_shapes` | 0 / 0 | 0 / 0 | 6 / 0 | 0 / 0 | 55 | 0 |
| `waan_between_links` | 0 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 29 | 0 |
| `work_not_checked_blanket` (round 4's list of 15 works) | 0 / 0 | 3 / 78 | 0 / 0 | 0 / 12 | 0 | 8,293 |
| `sibling_skips_link` | 2 / 3 | 0 / 0 | 0 / 0 | 0 / 0 | 489 | 0 |
| `many_routes` at 4 (not adopted) | 2 / 14 | 0 / 0 | 2 / 4 | 0 / 0 | 2,578 | 0 |
| `many_routes` at 5 (not adopted) | 3 / 24 | 0 / 0 | 2 / 4 | 0 / 0 | 3,923 | 0 |
| `many_routes` off (not adopted) | 5 / 28 | 0 / 0 | 2 / 7 | 0 / 0 | 4,935 | 0 |

Production counts are chains that the change alone decides (a chain several tests flag is not counted for each). Decisions, each
against the rule of section 2:

- **`work_not_checked` (a)**: removed. Round 4: 13 of 14 withheld chains of these works were correct. Of the 98 labelled tuning chains in
  the 15 works (11 defective), the other tests still withhold 17 (8 defective); 3 defective and 78 correct are released, and 12 correct
  held-out chains. The labelled n per work is 0 to 11, so a per-work rate is not defensible (table below); pooled, the released tuning
  chains are 3.7% defective (3 of 81) and held-out 0 of 12. The defects no shape rule sees there: a Companion named in the matn (Amali
  al-Saduq) and a first link lost before «عمه» (Khisal 8). Kitab al-Duafa and Risalat al-Huquq stay retired. To reverse: put the works back
  in `UNCHECKED_WORKS`.
- **`not_a_name` (b)**: the gloss exemption («يعني X», «هو ابن X») is kept for Pure Canon only (`routes_from_text` false: the chain is the
  source's own field, and the glosses are the source's). For text-built chains the same glosses stand in three tuning chains, all
  defective (a missing link or lost name beside the gloss), so no exemption there. New: «/» in a link (357 production chains; round 4
  counted 290 «تابع/» chains), «حدثناه»/«حدثنيه» in a link (87), a whole saying as the only link (158; I read 25 of the 401 candidate
  single-link chains with three or more words and no nasab word: 23 were plainly not names), an asker and an Imam in one link (376; the
  words «أخاه», «أخيه», «العبد الصالح»), and the label formulas «وبهذا الإسناد», «عمن حدثه» no longer fire (628 chains; 11 correct, 0
  defective on tuning).
- **`many_routes` (c)**: unchanged at three. Narrowing to four releases 18 correct and 4 defective labelled chains (18% defective, against
  2-5% among checked chains); five 28 and 5; off 35 and 7. None is a good trade, so it stays; nine of 13 flagged being correct (round 4)
  is what the unchecked share costs.
- **`text_names_more_after` (c)**: hearing and reading shapes after the last stored link, «سمع», «نظر إلى», «قرأت على», «نشهد على»,
  «من حدثك قال X», «قال X قال Y», each needing a nasab-shaped name (or «عائشة») and never the Prophet or an Imam; first-person «قال سمعت
  البراء» is a stored link and is not flagged (tests). 55 production chains. Not done: a Companion named only in the matn (judgment) and a
  bare «قال X قال Y» with single-word names.
- **«وعن» (d)**: «وعن» between two stored neighbours is a `text_between_links` reason, Thaqalayn reports only (the locator absorbs the
  waw into the right neighbour, so the test reads the text up to its end). In Sunni reports the same words introduce a route the sibling
  chain stores: 98 Sunni chains would be flagged and the 12 I read all looked like correct parallel routes, so Sunni is excluded. Al-Kafi 186 and 85 are now
  flagged; 29 production chains in all.
- **Inherited chains (e)**: an inherited chain's own continuation is read for a hearing verb («حدثني», «حدثتني», «أخبرنا») naming a further
  source, never for a bare «عن» (it stands in the matn: the first try withheld correct al-Rida and al-Rabi chains). Rida 16#3 is flagged; 2
  production chains.
- **Extra, from the evidence**: `pure_canon_tail_exempt` (Pure Canon text is the source's chain field, whose later routes are not a lost
  tail: 11 of 11 withheld on the two sets were correct; 1,722 chains released) and `sibling_skips_link` (two routes of one report that
  differ by one interior link; 2 defective and 3 correct tuning chains; designed on the tuning defects).

Per small Imami work (final gate; counts are labelled units):

| work | production chains | checked before -> now | tuning: units, defective, checked now, defective among them | held-out: same |
|---|---|---|---|---|
| al-khisal | 1,515 | 0 -> 1,202 | 9, 2, 6, 1 | 1, 0, 1, 0 |
| al-amali-saduq | 1,175 | 0 -> 982 | 7, 1, 7, 1 | 1, 0, 1, 0 |
| uyun-akhbar-al-rida | 1,102 | 0 -> 864 | 11, 0, 10, 0 | 1, 1, 0, 0 |
| maani-al-akhbar | 985 | 0 -> 785 | 6, 0, 6, 0 | 3, 0, 3, 0 |
| kitab-al-ghayba-tusi | 741 | 0 -> 543 | 6, 2, 3, 0 | 1, 0, 0, 0 |
| kamil-al-ziyarat | 895 | 0 -> 665 | 5, 1, 4, 0 | 0, 0, 0, 0 |
| kamal-al-din | 887 | 0 -> 685 | 9, 0, 9, 0 | 2, 0, 2, 0 |
| al-tawhid-saduq | 724 | 0 -> 597 | 11, 1, 10, 0 | 1, 0, 1, 0 |
| mujam-al-ahadith-al-mutabara | 730 | 0 -> 644 | 8, 1, 8, 1 | 0, 0, 0, 0 |
| kitab-al-ghayba-numani | 616 | 0 -> 429 | 9, 2, 4, 0 | 1, 0, 1, 0 |
| al-amali-mufid | 408 | 0 -> 342 | 5, 0, 5, 0 | 1, 0, 1, 0 |
| kitab-al-zuhd | 306 | 0 -> 285 | 2, 0, 1, 0 | 1, 0, 1, 0 |
| kitab-al-mumin | 198 | 0 -> 176 | 4, 0, 4, 0 | 0, 0, 0, 0 |
| sifat-al-shia | 74 | 0 -> 68 | 3, 0, 3, 0 | 1, 0, 1, 0 |
| fadail-al-shia | 45 | 0 -> 26 | 3, 1, 1, 0 | 0, 0, 0, 0 |

## 5. Reasons, as round 4 found them on the withheld sample

`text_between_links` 11 of 15 flagged were defective (it earns its place); `work_not_checked` 13/14 correct (gone), `not_a_name` 9/10
correct (the glosses; now exempted where the chain is the source's own), `text_names_more_after` 6/8 correct, `many_routes` 9/13 correct (kept,
section 4).

## 6. Pair precision

- The 150-pair sample (round 4): 149/150 = 99.3% (96.3-99.9). Its one wrong pair, al-Kafi 186, is now withheld.
- The new gate adds at most 502 pairs (346 Pure Canon, 156 Imami) to the 25,465 of the view and removes at most 75 (`new_pairs.py`:
  adjacent mentions with a standing identity in released or newly withheld chains; the view's seam and basis guards only remove). I read
  70 of the 502 (40 Imami, 30 Pure Canon, seeded): the text between the two stored names holds only link words («عن», «حدثنا», «قال
  حدثنا») in 70 of 70. Wilson upper bound for the new pairs 5.2%; they are 2.0% of the view, so the view's pair error rate moves by at most
  0.1 point. Identity (whether the stored name is that person) is not re-read.

## 7. Not done

- No fresh out-of-sample reading of the recalibrated gate (round 6): no rate is claimed for it.
- A source named only in the matn, a Companion named by judgment, concatenated Imami isnads, and a first link lost before a relation word
  («عمه») have no shape rule.
- `many_routes` is not narrowed: separating its correct from its defective chains needs more labelled reports than exist.
- Per-work rates for the 15 small Imami works (n 0-11 each).

## Files

`lib.py` (units, round-4 gate from git, helpers), `recalibrate.py` -> `results.json`, `make_fixtures.py` -> `fixtures.json`,
`new_pairs.py`, `pairs_snapshot.cjs` (view pairs with traditions), `q0.cjs` (view columns). Production status of every chain before and
after: `datasets/hadith-data/development/gate-recalibration-2026-11-22/production_status.json` (not committed).
