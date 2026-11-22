# Imami isnad audit (order, ta'liq, co-transmitters, anonymous gaps)

Read-only audit of every active Imami chain in production (34721 chains, 33,395 reports, 169,728 mentions, 21 collections; 23,959 mentions (14.1%) carry an identity, every other mention is `unresolved`). Imami chains are judged by Imami conventions only (the compiler's shaykh at position 0, «عدة من أصحابنا», «جميعا» groups, ta'liq by «وبهذا الاسناد»); nothing was corrected from Sunni rijal and no narrator identity was proposed from memory.

Outputs: `corrections.jsonl` (13863 rows), `sample_check.csv` (220 sampled reports), `fetched/` (every page, header with URL, UTC time, intent), `test_detectors.cjs` + `fixtures/real_examples.json`. Scripts: `load_cache.cjs` (read-only dump), `run_all.cjs` (all detectors), `detectors.cjs`, `thaq_lib.cjs`/`thaq_all.cjs` (Thaqalayn English sanad comparison), `noor.cjs`/`check_noor.cjs` (Noor structured sanad comparison), `sample.cjs`, `make_outputs.cjs`, `make_readme.cjs`. Rerun: `node --env-file=.env.local load_cache.cjs <cache.json>`; `IMAMI_CACHE=<cache.json> node run_all.cjs`; `node make_outputs.cjs`; test: `node test_detectors.cjs` (21 checks on real rows: one confirmed chain per detector, 15, and 6 clean chains that must stay silent).

## Headline

1. **Order is right.** Position 0 is the compiler's shaykh and the last position is the Imam wherever the Imam is a mention. No chain stores the Imam at position 0 of a multi-link chain (D01: 0 hits), the Thaqalayn English sanad lists the same names in the same order for 88.1% of al-Kafi reports (12201/13847; the rest are English-parse limits plus the defects below) and the order-reversal test found 0 candidates in all 23314 compared reports.
2. **The real defect is structural, not directional.** The extractor expands «A عن B و C عن D جميعا عن E» as a Cartesian product, so **a name from one sub-chain is stored as the teacher or student of a name in the other**: e.g. al-Kafi 3/4/16/1 stores «علي بن إبراهيم عن أبيه عن الفضل بن شاذان» and «علي بن إبراهيم عن محمد بن إسماعيل عن الفضل» where the text (and Noor's own sanad list) has two sub-chains meeting at Ḥammād. 1346 false links in 473 reports (al-Kafi 1328).
3. **Report-formula and matn text is stored as narrators**: 3873 «و روى X» / «وقال الصادق» mentions (Faqih 3513), 2621 clauses, 432 numerals from dates, 497 Mujam citation labels, 138 matn mentions after the Imam.
4. **Ta'liq is stored as a first narrator** in 2,239 chains (al-Kafi 1,111) and only 77 of those pronouns carry a person identity.

## Detectors (rule, counts)

All counts are mentions (one correction row per mention and detector); a report with several branches repeats a mention per branch. Kind/action are the schema values of `corrections.jsonl`.

| detector | rows | reports | top collections |
|---|---|---|---|
| D04_not_a_narrator_verb_prefixed | 3873 | 3791 | faqih 3513, sahifat-al-imam-ali-al-rida 153, kitab-al-ghayba-tusi 103, al-kafi 33, maani-al-akhbar 21 |
| D04_not_a_narrator_clause | 2621 | 1697 | faqih 1339, al-kafi 419, al-amali-saduq 295, kitab-al-ghayba-tusi 156, maani-al-akhbar 73 |
| D02_taliq_pronoun | 2239 | 2089 | al-kafi 1111, uyun-akhbar-al-rida 342, thawab-al-amal 212, kitab-al-ghayba-tusi 133, kamil-al-ziyarat 78 |
| D06c_cartesian_across_jamian_groups | 1346 | 473 | al-kafi 1328, kitab-al-ghayba-numani 8, kitab-al-ghayba-tusi 4, al-amali-mufid 2, al-tawhid-saduq 2 |
| D03b_irsal_marked_surface | 1045 | 929 | al-kafi 802, al-khisal 46, kamil-al-ziyarat 44, maani-al-akhbar 41, thawab-al-amal 19 |
| D06b_fused_cotransmitters | 675 | 581 | al-kafi 216, kamal-al-din 138, faqih 128, kamil-al-ziyarat 120, thawab-al-amal 17 |
| D13_source_label_in_surface | 497 | 423 | mujam-al-ahadith-al-mutabara 497 |
| D04c_footnote_in_surface | 482 | 235 | al-amali-saduq 323, mujam-al-ahadith-al-mutabara 142, faqih 9, al-kafi 4, al-khisal 1 |
| D12_numeral_as_narrator | 432 | 81 | al-amali-saduq 161, kitab-al-ghayba-numani 140, uyun-akhbar-al-rida 40, faqih 37, al-kafi 16 |
| D07_repeat_in_chain | 274 | 168 | al-kafi 168, faqih 23, maani-al-akhbar 22, uyun-akhbar-al-rida 15, kamal-al-din 13 |
| D02b_midchain_start | 192 | 192 | al-kafi 192 |
| D05_imam_nonfinal | 138 | 100 | al-kafi 84, faqih 34, al-tawhid-saduq 9, maani-al-akhbar 5, mujam-al-ahadith-al-mutabara 2 |
| D08_pair_both_directions | 29 | 29 | al-kafi 29 |
| D06a_waw_between_adjacent_mentions | 19 | 14 | kitab-al-ghayba-numani 9, al-kafi 8, al-amali-saduq 1, uyun-akhbar-al-rida 1 |
| D03a_collective_resolved | 1 | 1 | al-kafi 1 |

By kind and confidence:

| kind | confidence | rows |
|---|---|---|
| anonymous_gap | high | 1045 |
| branch_seam | high | 1346 |
| branch_seam | medium | 303 |
| co_transmitter | high | 694 |
| misidentified | high | 1 |
| not_a_narrator | high | 7064 |
| not_a_narrator | medium | 482 |
| other | high | 497 |
| suspended_chain | high | 2239 |
| suspended_chain | medium | 192 |

Detector rules (all in `run_all.cjs`, surface folding in `lib.cjs` `fold`, categories in `detectors.cjs`):
- **D02 ta'liq pronoun**: position 0 matches «عنه / وعنه / وبهذا الاسناد / وباسناده / وبالاسناد الاول / به». High: it is a back-reference, not a shaykh. D02b: al-Kafi position 0 is not a shaykh of the compiler and the same name occurs >=20 times mid-chain and <20% of the time first, and the report text starts with it (medium; the reports continue an earlier chain, e.g. «أحمد بن محمد عن محمد بن سنان» after a «محمد بن يحيى عن أحمد بن محمد» report).
- **D03b irsal marker inside the surface** («رفعه», «عمن ذكره», «عن رجل ... سماه»): the named narrator did not hear from the next mention; no pair may be formed across (high). D03a collective/anonymous surface with an identity: 1 row.
- **D04 not a narrator**: surface opens with a report verb or quotation («و روى», «قال», «وسئل الصادق»), or is a clause (function words, or >=12 tokens without a nasab). D04c: footnote digit/text in the surface. D12: a year or number word split from «سنة ثلاث وسبعين ومائتين». D13: «3/45 معاني الاخبار» citation prefix (Mujam).
- **D05 Imam then matn**: a resolved Imam or a strict Imam kunya followed by a mention that is not an Imam/prophet/«أبيه / آبائه» link and reads as matn (the «أنه سئل عن ...» object). An Imam followed by a named narrator (Imam relating from a companion) is legitimate and is **not** a correction.
- **D06a / D06b co-transmitters**: two successive mentions joined only by «و» in the report text, or one mention holding both names («أبي و محمد بن الحسن»).
- **D06c Cartesian across جميعا**: mentions aligned to the report text; the text before «جميعا عن» is split into groups; a stored link that skips a group boundary is a false link (high).
- **D07 repeat**: the same identity or full name twice in one chain = two isnads of one report concatenated (medium; English translation shows the same repeat).
- **D08 pair in both directions**: only the minority direction is emitted (29, all al-Kafi); every sampled one sat inside a D06c structure, so it is a symptom (medium).
- **D09 wrong Imam for the students around him, D10 «أبيه» resolved inconsistently, D11 generation inversion from the data**: implemented, **0 hits**. Only 44 narrators have >=20 resolved occurrences before an Imam row, and no «أبيه»/«جده» mention is resolved to a person (0), so there is nothing to test yet. They become useful when more mentions are resolved.

## Answers to the six questions

1. **Order.** Chains ending in an Imam row or kunya, and chains where the Imam is named in the text right after the last mention (the «قال سمعت أبا عبد الله» form, which is not stored as a mention, so the companion is last):

```
al-kafi                          16905 49.7% imam-last 31.9% imam-named-right-after-last
man-la-yahduruhu-al-faqih        5668 25.6% imam-last 21.8% imam-named-right-after-last
al-khisal                        1523 39.0% imam-last 7.0% imam-named-right-after-last
al-amali-saduq                   1391 24.6% imam-last 12.6% imam-named-right-after-last
uyun-akhbar-al-rida              1114 16.5% imam-last 26.4% imam-named-right-after-last
thawab-al-amal                   1104 42.8% imam-last 15.9% imam-named-right-after-last
maani-al-akhbar                  1072 27.9% imam-last 21.5% imam-named-right-after-last
kitab-al-ghayba-tusi             841 13.3% imam-last 19.5% imam-named-right-after-last
al-tawhid-saduq                  753 30.1% imam-last 30.3% imam-named-right-after-last
kamil-al-ziyarat                 751 48.7% imam-last 30.8% imam-named-right-after-last
mujam-al-ahadith-al-mutabara     694 41.1% imam-last 32.9% imam-named-right-after-last
kitab-al-ghayba-numani           677 46.1% imam-last 31.2% imam-named-right-after-last
kamal-al-din                     673 33.0% imam-last 25.1% imam-named-right-after-last
al-amali-mufid                   418 28.0% imam-last 7.2% imam-named-right-after-last
kitab-al-zuhd                    316 56.0% imam-last 20.3% imam-named-right-after-last
kitab-al-duafa                   257 18.7% imam-last 1.9% imam-named-right-after-last
sahifat-al-imam-ali-al-rida      209 1.4% imam-last 0.0% imam-named-right-after-last
kitab-al-mumin                   199 12.6% imam-last 11.6% imam-named-right-after-last
sifat-al-shia                    72 52.8% imam-last 30.6% imam-named-right-after-last
fadail-al-shia                   45 46.7% imam-last 20.0% imam-named-right-after-last
risalat-al-huquq                 39 0.0% imam-last 0.0% imam-named-right-after-last
```
   al-Kafi position 0: shaykh set (the compiler's attested shaykhs listed in the brief) 13264 (78.5%), ta'liq pronoun 1111 (6.6%), other 2530 (15.0%; the frequent ones, e.g. «علي بن محمد» 421, «أحمد بن محمد» 353, «احمد بن ادريس» 122, open chains mostly first-position; whether each is a direct shaykh of the compiler is not asserted here; the mid-chain starts are isolated by D02b = 192). The two conventions for the Imam (a mention in «عن أبي عبد الله», no mention in «قال سألت أبا عبد الله») are mixed inside one collection, so companion->Imam links are missing for about a third of al-Kafi chains; this is a convention gap, not an order error, and is not in `corrections.jsonl`.
2. **Ta'liq.** 2265 pronoun mentions; D02 rows above. They create no collector link because the compiler is never a mention, but the first name of such a chain is wrong as an opening and `narrator_transmissions` loses the antecedent chain. Thaqalayn's English text supplies the referent in some cases (Kamil al-Ziyarat 1/2/9: «وعنه» is «Hukaym ibn Dawud» in the English), which is evidence the antecedent is recoverable from the previous report.
3. **Collectives and irsal.** «عدة من أصحابنا» appears as one mention (3,138 times); one is resolved to a person (D03a). «ابيه» is never resolved. Irsal-marked surfaces: 1,045 (al-Kafi 802); a pair is formed across the gap only when both neighbours are resolved (verified pairs affected: 28).
4. **Co-transmitters.** The extractor does branch for plain «A و B عن C» (correct). It breaks on «A عن B و C عن D جميعا» (D06c), on fused mentions (D06b 675), and on two isnads of one report (D07 274).
5. **Duplicates, direction, Imam.** Pairs present in both directions: 16 (of 3047 distinct resolved pairs; minority direction emitted); same narrator twice: D07; Imam in a non-final position: D05 (138 matn tails kept; Imam-then-named-narrator excluded as legitimate). Wrong Imam for a kunya: no evidence (D09: 0; the bare «أبي جعفر / أبي الحسن» kunyas are candidates, not identities, so they are not tested).
6. **Chronology without dates.** Not assertable from the data: external narrators have no lifespans and the resolved set is too thin for the generational-depth test (D11 0 hits). Flagged nothing.

## Online verification

Sources tried (all fetched pages are in `fetched/` with header):
- **Thaqalayn public API** (`thaqalayn-api.net/api/v2/<bookId>`): works, no rate limit seen. Each report carries `thaqalaynSanad`, a human English rendering of the chain. It verifies **names and order**, not group structure, and for most Saduq books the English sanad carries only the first link («to us my father - may Allah be pleased with him - Muhammad bin Hasan»), so those collections are **unverifiable** this way. Compared against all stored chains: see table.
- **Noor Hadith** (`hadith.inoor.ir/service/api`, the site's own JSON): `elastic/v2/ElasticHadithList` (search by opening words) and `hadith/HadithRejalList/v2?hadithId=` return the site's **structured sanad list**, one entry per sub-chain with the compiler as order 0. This is the only source that shows group structure. The search endpoint is rate limited (HTTP 429, Retry-After about 1.9 h after roughly 100 requests); the page and rejal GETs were not limited. Noor outcomes of the (partial) first search run, by status: {"disagree":4,"noor_no_hit":52,"noor_no_matching_volume":5}; only 2 Noor comparisons are usable (a search hit whose text differs from ours was discarded as a mismatch, except the D05 Faqih 4/1/50 row whose names match Noor's list exactly and whose text differs only in a leading «و في رواية»). A second run of 84 reports was queued behind the 429 reset (08:13 UTC) and was **cancelled unrun**; the files `sample_round9.json` and `results_round1.json` show what was and was not done.
- Not usable: `al-islam.org` (HTTP 403), `shiaonlinelibrary.com` (DNS failure), `ar.wikishia.net` (timeout), `thaqalayn.net/hadith/...` pages (404 to a non-browser client; the API serves the same data), `lib.eshia.ir` (reachable, no per-report structured chain), `noorlib` not tried (Noor Hadith links to it).

Thaqalayn English comparison over every stored report (agree = all our names appear in order in the English, tolerance 15%):

| collection | compared | agree | order-reversal suspects |
|---|---|---|---|
| al-kafi | 13847 | 12201 (88.1%) | 0 |
| man-la-yahduruhu-al-faqih | 2025 | 1615 (79.8%) | 0 |
| al-khisal | 1241 | 257 (20.7%) | 0 |
| al-amali-saduq | 976 | 48 (4.9%) | 0 |
| kamil-al-ziyarat | 743 | 381 (51.3%) | 0 |
| uyun-akhbar-al-rida | 719 | 355 (49.4%) | 0 |
| maani-al-akhbar | 627 | 36 (5.7%) | 0 |
| kamal-al-din | 559 | 308 (55.1%) | 0 |
| thawab-al-amal | 545 | 209 (38.3%) | 0 |
| mujam-al-ahadith-al-mutabara | 529 | 442 (83.6%) | 0 |
| kitab-al-ghayba-tusi | 409 | 262 (64.1%) | 0 |
| kitab-al-ghayba-numani | 403 | 321 (79.7%) | 0 |
| kitab-al-zuhd | 269 | 248 (92.2%) | 0 |
| kitab-al-mumin | 178 | 170 (95.5%) | 0 |
| al-tawhid-saduq | 110 | 41 (37.3%) | 0 |
| sifat-al-shia | 49 | 19 (38.8%) | 0 |
| al-amali-mufid | 46 | 30 (65.2%) | 0 |
| fadail-al-shia | 35 | 22 (62.9%) | 0 |
| kitab-al-duafa | 3 | 2 (66.7%) | 0 |
| risalat-al-huquq | 1 | 0 (0.0%) | 0 |

Low agreement in Saduq collections (al-Khisal, al-Amali, Maani) is the English truncation, not our order; `sample_check.csv` marks those rows `unverifiable_english_truncated`.

Noor confirmations (structured sanads, exact):
- al-kafi  (manual_probe): our false pairs: ابيه <- الفضل بن شاذان ; علي بن ابراهيم <- محمد بن اسماعيل. Noor sanads: علي بن إبراهيم <- أبيه <- حماد بن عيسى <- حريز <- زرارة <- أبي جعفر عليه السلام || محمد بن إسماعيل <- الفضل بن شاذان <- حماد بن عيسى <- حريز <- زرارة <- أبي جعفر عليه السلام. https://hadith.inoor.ir/service/api/hadith/HadithRejalList/v2?hadithId=108787
- man-la-yahduruhu-al-faqih 4/1/50 (detector:D05_imam_nonfinal): our false pairs: أبي عبد الله <- الجسور أ يضمن أهلها شيئا. Noor sanads: يونس بن عبد الرحمن <- رجل من أصحابنا <- أبي عبد الله عليه السلام. https://hadith.inoor.ir/service/api/hadith/HadithRejalList/v2?hadithId=103319
- al-Kafi 3/4/16/1 (probe, `results_round0.json`): Noor lists two sanads, «علي بن إبراهيم <- أبيه <- حماد بن عيسى <- حريز <- زرارة <- أبي جعفر» and «محمد بن إسماعيل <- الفضل بن شاذان <- حماد بن عيسى <- ...». We store «... أبيه <- الفضل بن شاذان» and «علي بن إبراهيم <- محمد بن إسماعيل» (2 false links) and drop the second sub-chain's own first narrator. https://hadith.inoor.ir/service/api/hadith/HadithRejalList/v2?hadithId=108787

## Sample and measured error rate

220 reports in three rounds (round 1: 60, round 2: 100, round 3: 60), half drawn from detector hits (stratified by detector), half uniformly at random (al-Kafi 50%, other collections equally; Sahifat al-Rida (OpenITI), Kitab al-Duafa and Risalat al-Huquq have no usable online chain, so they are not in the sample). Rounds 1 and 2 produced detectors D06c, D12, the D05 and D02b refinements and the fused-regex fix; round 3 added only D13 (Mujam citation prefix); no further round was run (see "Not checked").

Random half (n=110), a report counts as defective when at least one detector found it. Every Thaqalayn disagreement and every detector-half hit of rounds 1 and 2 was read against the Arabic text; the random-half findings of round 3 and the random-half rows that agreed with Thaqalayn were not each re-read, so the rate is the detectors' rate, not an independently adjudicated one:
- any structural finding (includes ta'liq and mid-chain starts): 36/110 = 32.7% (Wilson 95% 24.7-41.9%);
- finding that creates a false teacher/student link or a non-narrator node (branch_seam, co_transmitter, not_a_narrator, anonymous_gap, misidentified): 17/110 = 15.5% (Wilson 95% 9.9-23.4%);
- post-stratified by collection size: any 39.5%, link-corrupting 25.8% (small per-collection n; treat as indicative);
- 15 random reports were unverifiable online and had no finding; they are counted as clean, so the rates are lower bounds.

| collection | sampled | any finding | link-corrupting |
|---|---|---|---|
| al-kafi | 56 | 18 | 10 |
| al-tawhid-saduq | 4 | 0 | 0 |
| al-khisal | 4 | 0 | 0 |
| kamal-al-din | 4 | 1 | 1 |
| thawab-al-amal | 4 | 1 | 0 |
| man-la-yahduruhu-al-faqih | 4 | 3 | 3 |
| kitab-al-ghayba-tusi | 4 | 2 | 1 |
| kamil-al-ziyarat | 3 | 1 | 0 |
| maani-al-akhbar | 3 | 0 | 0 |
| al-amali-mufid | 3 | 2 | 0 |
| kitab-al-ghayba-numani | 3 | 1 | 0 |
| uyun-akhbar-al-rida | 3 | 2 | 0 |
| kitab-al-zuhd | 3 | 0 | 0 |
| sifat-al-shia | 2 | 1 | 0 |
| fadail-al-shia | 2 | 1 | 1 |
| kitab-al-mumin | 2 | 0 | 0 |
| mujam-al-ahadith-al-mutabara | 3 | 3 | 1 |
| al-amali-saduq | 3 | 0 | 0 |

Detector half precision (manual reading against the Arabic and the English/Noor chain, rounds 1 and 2): D06c, D06a, D06b, D07, D12, D04, D04c, D03b, D02 every sampled hit was a real defect of the kind named; D05 (before tightening) produced false positives when the Imam kunya pattern matched «أبو الحسن علي بن محمد بن حبيش» and when an Imam narrates from a companion, which is why the final D05 is restricted to matn tails; D08 hits were all symptoms of D06c. No sample row showed a reversed order.

## Ordered fix list for the integrator (expected impact)

1. **Re-parse «جميعا» groups** in `extract_isnad_unified.py` (D06c): split the text before «جميعا عن» into sub-chains at each «و» that follows a link, join each sub-chain to the merge point. Removes 1346 false links in 473 reports and restores the second sub-chain's own opening (the compiler's second shaykh). Verified-pair impact today: 27 distinct verified pairs; it grows with identity coverage.
2. **Drop non-narrator mentions** (D04, D04c, D12, D13, D05 matn tails): 3873 + 2621 + 482 + 432 + 497 + 138. Faqih's «و روى X» should start the chain at X (a suspended chain by design: Saduq gives the tariq in the mashyakha). Biggest visible quality gain in Faqih (3513 verb-prefixed + 1339 clause mentions).
3. **Mark ta'liq chains** (D02 2,239, D02b 192) `suspended` and, where the previous report in the same chapter is parsed, carry its opening forward; keep the pronoun as a label, never as a narrator.
4. **Never form a pair across an irsal-marked mention** (D03b 1,045): the surface «X رفعه / عمن ذكره» should become X plus an anonymous gap node; today 28 verified pairs span such gaps.
5. **Split concatenated isnads** (D07 274, D08 29): when the same narrator re-opens inside a report, start a new chain.
6. **Split fused co-transmitters** (D06a/D06b 694): «أبي و محمد بن الحسن» is two mentions at one level.
7. **Imam convention**: decide whether «قال سألت أبا عبد الله» yields an Imam mention (about a third of al-Kafi chains lack the companion->Imam link). Not a correction row.
8. Re-run D09-D11 once more mentions carry identities.

## Not checked

- **Identities of external Riwayat/hadith-kg rows were not verified**: only 23,959 of 169,728 mentions are resolved, and the audit never asserts who a narrator "really" is.
- Sahifat al-Rida (OpenITI, 209 chains), Kitab al-Duafa, Risalat al-Huquq: no usable online chain; only text-pattern detectors ran.
- Group structure was confirmed online only through Noor, and only on the reports that fit the Noor search budget; Thaqalayn English cannot show structure. The search quota (HTTP 429) cut the Noor sample short.
- Saduq-book chains are largely unverifiable against Thaqalayn English (truncated); they were read against the Arabic text and detectors only.
- The sample loop stopped after round 3 (rate limit and effort), not because a round added nothing: round 3 did add one pattern (D13).
- Detectors measure only patterns they name; the rates above are lower bounds. «علي» / «محمد» bare given names at position 0 (ta'liq by a single name) are counted only through D02b where the ratio test applies.
- No pair was checked chronologically (no lifespans for external narrators).
