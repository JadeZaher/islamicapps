---
type: diagnostic
---
# Chain audit, round 2: independent re-check after the chain-builder fix

Read-only against production after commits `9600be3`, `ae0927b`, `40264df` (projection `2026.11.22.5`). Only this directory was written; nothing was deleted; no process is left running. Intermediate scratch (detector caches, ~290 MB) is in the session scratchpad, not the repo.

## Result in six lines

1. **Order is still right and the main defect class moved.** Flattened tahwil and Cartesian «جميعا» links are mostly gone; what replaced them is **routes that stop before the shared tail, headless tail chains, lost names and lost chains**.
2. **Sunni did not improve on the same definition**: strict defects 17/98 = 17.3% (Wilson 11.1-26.0) against the earlier lane's 10.7% (5.7-19.1); the mix changed (formula/seam errors down, truncated routes and trimmed-away narrators up). The 30 chains drawn from re-cut (seam) reports are defective 27/30 = 90%.
3. **Imami is better where the fix reached** (Kafi, Faqih) and unchanged elsewhere: strict defects 9/99 = 9.1% (4.9-16.4), earlier 15.5% (9.9-23.4). Whole defects of any kind 21-24/99 (14-33%).
4. **Rabi 7.5%, Zayd 0%, Rida 12.5%** of sampled chains (earlier 25%, 25%, 100%). But **190 Ibadi/Zaydi reports that opened with a written chain lost every chain** in the fix (Rabi 151 of 1,005, Zayd 44 of 691 by detector D5a; 306 OpenITI reports lost their chain, ~60% of 30 sampled had a written isnad), and a chain-level sample cannot see them.
5. **Regressions are real but small in the random samples and large in the changed populations** (table below): 162 Sunni mentions in 142 reports lost a named narrator to the formula trim; 2 Sunni reports lost their only chain; sampled false seams confirmed online.
6. Reruns of the three lanes' detectors still run but several now count the new representation, not defects (listed below).

## Method and coverage (what was read, what was not)

Seeded uniform samples (`sample.cjs`, `md5(chain_id || seed)` order), live chains only, excluding every hadith id in the three earlier `sample_check.csv` files. Each chain was read against `sanad_ar`/`text_ar` (parent text for inheriting reports) and, where possible, an online source.

| sample | drawn | read by eye | note |
|---|---|---|---|
| Sunni, 9 works | 100 (11-12 per work; 67 K6 text, 33 Pure Canon) | 100 | 70 were flagged by an alignment pre-judge (`auto.cjs`), those and 30 unflagged were read. Pure Canon (Ahmad, Darimi, Muwatta) stores matn only in `text_ar`: judged against the source's own `sanad` field, 2 left unverifiable |
| Imami, 21 works | 100 (al-Kafi 50, Faqih 12, 18 others 2-3 each; Rida excluded, it has its own sample) | 69: all 38 pre-judge flags + 31 of the 62 unflagged | the other 31 are `ok_unread` in `sample_check.csv`; a read unflagged chain had a defect in 3/31 (all minor), so 24/99 is the extrapolation |
| al-Rabi, Musnad Zayd, Sahifat al-Rida | 40 each | 40 each | Zayd: shape check on all 631 chains plus text alignment |
| changed populations | 30 each | 30 each | Sunni re-cut at a seam, Sunni trimmed (30) and dropped (30) mentions, Imami «جميعا», Imami each `suspension` value (3 x 30), Imami anonymous positions, Imami back-reference chains that were filled, al-Rabi inheriting reports |

"Before" files for the regression tests are the builder's own earlier projections (`development/chain-builder-r2-2026-11-22/projection-m2c` for Sunni, `projection-m1` for Imami, `development/openiti-fix-2026-11-21/projection-v6` for OpenITI). A chain counts as a regression only when its names are a strict sub-run of a chain that existed before (`regress.cjs`) or when I show before and after side by side.

## Rates now beside the earlier lane

Defect = my judgement of the stored chain against the Arabic. **Strict** = a missing link, false/merged/split route, non-narrator mention, concatenated or wrongly inherited chain; **any** adds names over-extended by a verb, footnote, honorific or date, truncated letters, non-isnad prose. The earlier lanes' definitions are closest to *strict*. All rates Wilson 95%.

| work | earlier lane (random half) | now, strict | now, any |
|---|---|---|---|
| Sunni, all nine | 9/84 = 10.7% (5.7-19.1) | 17/98 = 17.3% (11.1-26.0) | 24/98 = 24.5% (17.0-33.9) |
| Sunni K6 text works only | not reported | 14/67 = 20.9% (12.9-32.1) | 18/67 = 26.9% (17.7-38.5) |
| Sunni Pure Canon (judged vs source `sanad` field only) | not reported | 3/31 = 9.7% (3.3-24.9) | 6/31 = 19.4% (9.2-36.3) |
| Sunni by work, any defect (n=11 each, indicative) | 0-20% | Muslim 6/11, Nasai 4/11, Abu Dawud 3/11, Muwatta 3/9, Bukhari 2/12, Tirmidhi 2/11, Ahmad 2/11, Ibn Majah 1/11, Darimi 1/11 | |
| Imami | link-corrupting 17/110 = 15.5% (9.9-23.4); any 36/110 = 32.7% (24.7-41.9) | 9/99 = 9.1% (4.9-16.4) (unread = clean) | 21/99 = 21.2% (14.3-30.3) unread = clean; 24/99 = 24.2% (16.9-33.5) extrapolated. By work: Kafi 7/32 read, Faqih 1/8, other 18 works 13/28 |
| Musnad al-Rabi | 11/44 = 25.0% (14.6-39.4) | 1/40 = 2.5% (0.4-12.9) | 3/40 = 7.5% (2.6-19.9) |
| Musnad Zayd | 11/44 = 25.0% (14.6-39.4) | 0/40 (0-8.8) | 0/40 |
| Sahifat al-Rida | 44/44 = 100% (92-100) | 5/40 = 12.5% (5.5-26.1) | 5/40 |

Chain-level samples miss reports that have **no chain**: Rabi 151/1,005 = 15.0% (12.9-17.4) and Zayd 44/691 = 6.4% (4.8-8.4) open with a written chain and now store none (before the fix: 2 and 3). Taking both into account the Rabi report-level failure is about 21% (0.15 + 0.85 x 0.075), not 7.5%.

## Changed populations: defective now, and how many the fix made worse

"Worse" = a judged defect whose stored names are a strict sub-run of a chain that existed before (`regress_classified.json`), restricted to missing-link / wrong-split / false-seam kinds. "Unchanged" = identical to the earlier projection, i.e. a miss, not a regression.

| population (30 each unless noted) | defective now | made worse by the fix | unchanged (miss) | main kinds |
|---|---|---|---|---|
| Sunni chains re-cut at a seam | 27/30 = 90% (74-97); 20 of 23 distinct reports (7 of the 30 are one 192-chain report) | 10/30 = 33% (19-51); 17/30 if any sub-run counts | 5 | truncated or headless routes 11, non-narrator 9, false seam 2, merged names 2 |
| Sunni trimmed mentions | 2/30 lost a named person (6.7%, 1.8-21.3) | 162 mentions in 142 reports found over the whole population of 3,843 trimmed (4.2%, lower bound) | | «X سمعا Y», «X حدثتني Y» keep X and drop Y |
| Sunni dropped mentions | 3/30 belong to reports that lost every chain | 2 reports (`pc_20809`, `k6:21409`) had a real source chain, none now | | the rest were `اللفظ لـ`, `تابعه`, grading asides, correctly dropped |
| Imami «جميعا» chains | 9/30 = 30% (17-48); 3 are deferred concatenated isnads | 2/30 | 3 | false cross-group link 2, missing tail 2, concatenated 3 |
| Imami `route_given_elsewhere` (Faqih «و روى X», 3,635 chains) | 5/30 = 16.7% (7.3-33.6) | 2/30 | 0 | matn after the Imam, «غير واحد» split, Imam not stored |
| Imami `mid_chain_start` (824) | 4/30 = 13.3% (5.3-29.7) | 0/30 | 4 | matn words stored after the Imam |
| Imami `back_reference` (1,886) | 5/30 = 16.7% (7.3-33.6) | 0/30 | 5 | matn/Qur'an words stored after the Imam |
| Imami anonymous positions (2,589 mentions) | 4/30 = 13.3% (5.3-29.7) | 0/30 on the strict kinds (2 changed for the worse in other ways) | 1 | matn «الرجل» stored as anonymous (one report has 183+ chains), Persian-ya loss |
| Imami back-reference chains filled from the previous report (424 chains) | 3/29 = 10.3% (3.6-26.4); the fill itself was right in 26/29 | 0/29 | | defects are parent defects carried down (Persian-ya, «يقال له الهروي»); 1 unverifiable (inherited chain runs past the named speaker) |
| al-Rabi inheriting reports | 1/30 = 3.3% (0.6-16.7) | 0/30 | | source text repeats «أبو عبيدة عن جابر», copied to the child |

Imami regressions in the strict sense are rarer than misses: of 21 judged-defective Imami sample chains, 15 are byte-identical to the pre-fix projection (the builder never touched them) and 6 changed. The Sunni sample is the opposite: the seam re-cut creates defects.

## Remaining defect patterns, ordered by expected count

Counts: "population" is a production count (rule stated), "estimate" is sample rate x population with the sample's Wilson range. Rates from 1-6 hits are indicative only. By expected defective chains the order is 1 (~7,000), 3 (~5,500 mentions), 2 (~2,000), 4 (~1,900 mentions), 5 (500-1,000), 6 and 8 (hundreds), then 7, 9-13 (100-400 each); the numbering below is by theme within that.

1. **Sunni routes that stop before their shared tail, and headless tail chains** (the seam rule: "each earlier route continues along the last one after the name it converges on, else ends there"). Population proxy: 817 K6 hadiths have a chain of 3 or fewer mentions beside a sibling of 5 or more (1,421 chains). Sample: 10/67 K6 random chains (15%, 8-25%), i.e. about 7,000 of 47,009 K6 chains (range 3,900-11,800).
   - `hadith:k6:7805` (Muslim 436), chain `chain:k6:7805:0000` = [محمد بن المثنى] only. Text «حدثني محمد بن المثنى، وابن بشار قال ابن المثنى حدثنا محمد بن جعفر، حدثنا شعبة عن قتادة ... أبا العالية ... ابن عباس»; printed edition: https://api.turath.io/search (saved `fetched/turath_109223d629.json`) «[١٦٥] حدثني محمد بن المثنى، وابن بشار، قال ابن المثنى: حدثنا محمد بن جعفر، حدثنا شعبة عن قتادة قال: سمعت أبا العالية».
   - `hadith:k6:16725` (Abu Dawud 1765): `[إبراهيم بن موسى الرازي > عيسى]` ends where «عن ثور، عن راشد بن سعد ...» begins; the tail is the headless chain b1 `[ثور > راشد بن سعد > ...]`. Text «حدثنا إبراهيم بن موسى الرازي، أخبرنا عيسى، ح وحدثنا مسدد، أخبرنا عيسى ... عن ثور».
   - `hadith:k6:11239` (Muslim 3931): `[زهير بن حرب > إسماعيل]`; text «وحدثني زهير بن حرب، وعلي بن حجر، قالا حدثنا إسماعيل، ح ... جميعا عن أيوب، عن نافع، عن ابن عمر».
2. **Sunni narrator after «سمعا / حدثتني / أخبرته / أن X أخبره» lost** (trim and never-stored). Demonstrated: 162 mentions in 142 reports (lost names listed in `regressions.jsonl`, kind `name_lost_by_trim`); sample: 3 of 67 K6 chains lose the Companion (about 2,000 chains, range 700-5,600).
   - `hadith:k6:7852`: before «عبد الملك بن سعيد سمعا الشعبي يخبر», now `عبد الملك بن سعيد` with no mention of الشعبي.
   - `hadith:k6:13589`: «أبو سلمة بن عبد الرحمن أنهما سمعا أبا هريرة» becomes «أبو سلمة بن عبد الرحمن أنهما», أبو هريرة in no mention.
   - `hadith:k6:25756` (Nasai 1309): chain ends at «عروة بن الزبير»; text «أخبرني عروة بن الزبير، أن عائشة، أخبرته أن رسول الله».
3. **Sunni surfaces still carrying verbs, asides and clauses** (`non_name_surface` rerun: 10,248 -> 5,940; my regex 5,491 mentions; 1,318 end in «ح» or a dash; sample 7/98). Examples: `hadith:k6:27269` (Nasai 2818) a whole route whose only head is «أنا أسمع»; `hadith:k6:24036` (Tirmidhi 3583) «كانت من المهاجرات» as a narrator and «وغير واحد» split into «غير» and «احد» (8 branches for one route); `hadith:k6:21664` «زرارة بن أوفى يحدث».
4. **Imami bare conjunction and report verbs stored as narrators**: 785 mentions that are exactly «و» (`hadith:thaqalayn:9dec2b996ad72f438d6910a3`, Kamil al-Ziyarat 27: `[و > محمد بن جعفر الرزاز > ...]`, text «وَ حَدَّثَنِي مُحَمَّدُ بْنُ جَعْفَرٍ»); 81 mentions open with a report verb the cleaner missed («و قد روى», `hadith:thaqalayn:2c8be8488724f439fc0556b2`); 459 mentions carry «حدثنی / حدثنا / أخبرنا»; 549 end in «ره». All identical in `projection-m1`, so these are misses.
5. **Imami Persian-ya texts lose narrators** (Thawab al-Amal, 1,100 of 1,106 reports use ی): `hadith:thaqalayn:f02c69a82883b8f2aa7763ce` text «أَبِی ره قَالَ حَدَّثَنِی سَعْدُ بْنُ عَبْدِ اللَّهِ عَنْ مُحَمَّدِ بْنِ عَرَفَهَ» stored `[أبی ره > محمد بن عرفه > الرضا ع > المنکر فلیأذن]` (سعد missing, matn last); `hadith:thaqalayn:1cee22846aab05dfbd59a888`: «حَدَّثَنِی عَلِیُّ بْنُ مُوسَی» missing. 4 of the 5 Thawab chains I read were defective; the same verb check shows gap words in 56% of Thawab chains against 26% in al-Kafi (pre-judge only). Population 1,137 chains; estimate 500-1,000 defective.
6. **Imami matn stored as chains**: `hadith:thaqalayn:b0c303b331dd554a8f3ea875` (Amali al-Saduq 93) has 183+ chains, e.g. `[الثور > البدنة > الجزور > الكبش > الرجل > ثلث يهدى]`; `hadith:thaqalayn:66402f30edd9dfec327485dd` (Faqih 150) `[سبعة نفر بالأمصار و بمنى > البدنة تجزي > الكبش يجزي > الرجل]`. Population: 420 anonymous «الرجل/رجل» mentions, D05 matn after the Imam 246 mentions in 165 reports, 17 matn/Qur'an tails in my ~190 pop chains. Also Kitab al-Duafa (237 chains) and Risalat al-Huquq (23) are rijal entries and prose stored as isnads (`hadith:thaqalayn:b441452c63687840798d7bf4`, `...be8d3dc07e75dcc7462f4c56`).
7. **Ibadi/Zaydi reports with a written chain and no chain** (regression): 190 reports (Rabi ~151, Zayd ~44), e.g. `hadith:openiti:ibadi:rabi_0094|94|V01P029` «ابو عبيده عن جابر بن زيد قال بلغني عن رسول الله ...». Listed in `regressions.jsonl`, kind `chain_lost_written_chain_present`. About 60% of the 306 reports that lost a chain have a written isnad; the rest are statements with none.
8. **Imami false cross-group links when «جميعا» is written with commas or the shaykh is a collective**: detector D06c 351 mentions in 130 reports (down from 1,346), 89 chains of shape `أبيه > الفضل بن شاذان / سهل بن زياد`, 34 chains with «عدة من أصحابنا» hung under a named opener. Sample 3/30 «جميعا» chains (10%; about 200 reports).
   - `hadith:thaqalayn:1adbb3bc592355214cdb0be0` (Kafi 19): stored `[علي بن إبراهيم > أبيه > سهل بن زياد ...]` and `[علي بن إبراهيم > عدة من أصحابنا > سهل بن زياد ...]`; Noor lists `الكليني > علي بن إبراهيم > أبيه > ابن محبوب` and `الكليني > عدة من أصحابنا > سهل بن زياد > ابن محبوب`: https://hadith.inoor.ir/service/api/hadith/HadithRejalList/v2?hadithId=118532 (identical before and after the fix).
   - `hadith:thaqalayn:a38d215bee8c93fe2a02f810` (Kafi 43) and `hadith:thaqalayn:f324c6f008626b3fe13da974` (Mujam 8): `علي بن إبراهيم > أبيه > الفضل بن شاذان` and `علي بن إبراهيم > محمد بن إسماعيل > الفضل بن شاذان`; the audit's own exemplar (Kafi 3/4/16/1) now matches Noor (`fetched/noor_rejal_108787.json`: two routes meeting at حماد بن عيسى), so the fix works on the diacritised form only.
9. **Imami concatenated isnads (D07)**: 400 mentions in 181 reports (up from 274 in the earlier run; deferred in the fix). `hadith:thaqalayn:7e8a2ee0956c2aa7694198df` (Faqih 231): `[أبي > علي ابن إبراهيم > أبيه > محمد بن أبي عمير > محمد بن حمران و رويته > محمد بن الحسن > ...]`.
10. **Imami «غير واحد» split** into «غير» and «احد»: 413 mentions (Sunni 233): `hadith:thaqalayn:d4b7d1dc574f1227818536e9`, `hadith:thaqalayn:a1472a2b00e9f4b54e31e78f`.
11. **Sahifat al-Rida chains inherited past the named speaker** (3/40 = 7.5%, about 15 of 202): `hadith:openiti:imami:rida_0031#23|31|V01P490` text «وباسناده قال: قال علي بن الحسين» stored with the full chain through الحسين and علي بن أبي طالب; `hadith:openiti:imami:rida_0035#5|35|V01P505` «سئل محمد بن علي بن الحسين» stored with four more links; `hadith:openiti:imami:rida_0031#13|31|V01P490` parent prefix of 6 then «أبي جعفر».
12. **al-Rabi**: `hadith:openiti:ibadi:rabi_0581|581|V01P155` stops at ابن عباس («عن ابن عباس عن أبي رافع مولى رسول الله»); «ابن عمر يروي», «الإمام روي» keep the verb. Expected about 3-8% of 720 chains.
13. **Sunni 192-chain explosion**: `hadith:k6:11006` (Muslim 3689) has 192 chains with surfaces «الزهري أما ابن منصور فقال», «سفيان مرة», «قال زهير»; two more reports have more than 30 chains (3 reports, 259 chains in total).

Not a defect by my reading (sampled, left alone): Kafi chains that omit the Imam when the text says «قال سمعت أبا عبد الله» (convention gap), al-Rabi «بلغني» as an anonymous link, Zayd chains starting at Zayd (the book's transmitters are not stored by design), Faqih chains that stop at the narrator who addresses the Imam.

## Online sources

| source | result |
|---|---|
| `api.turath.io/search` | worked (3 searches, no rate limit hit). Muslim 436 and Bukhari 4720/4975 text confirmed above; Bukhari 4720 prints «حدثنا إسماعيل بن إبراهيم، حدثنا عوف» with no «و», so the builder's split at «وحدثنا عوف» in our K6 text is false (`hadith:k6:4489`, chain `chain:k6:4489:0001` = `[عوف > أبو رجاء > سمرة]`, route one cut at `[مؤمل > إسماعيل]`; `fetched/turath_3e4ca6bf21.json`). Bukhari 4975 prints «حدثنا إسحاق بن منصور قال: وحدثنا عبد الرزاق» (`hadith:k6:4794`: stored `[إسحاق بن منصور]` alone, and a headless `[عبد الرزاق > ...]`; `fetched/turath_541c231731.json`) |
| Noor `HadithRejalList/v2` | worked as a GET; the search endpoint worked once (al-Kafi source 1348, `fetched/noor_search_kafi19.json`). Mapping a report to a Noor id needs a search per report, so only 2 reports were compared (the exemplar and Kafi 19) |
| Thaqalayn English sanad (public API JSON) | re-used the earlier lane's saved pages (same URLs, `chain-audit/imami/fetched/book_*.json`), not re-fetched. 86 of 100 sampled reports matched, 60 agree on names and order, 26 disagree (13 of the 26 are chains I judged correct: group structure and co-transmitters the English cannot show). Agreement is no evidence of absence of defects: 9 of my 21 defective chains "agree" |
| `cdn.jsdelivr.net` hadith-api | fetched (2 saved pages) but its numbering differs from our K6 `hadith_no`, so it could not be used |
| OpenITI raw (Zayd, Rida) | not re-fetched; reused the lane's saved editions for the Rida shape check (`rida_0001` prints the full Imam chain and each «وبإسناده» follows it) |
| sunnah.com, dorar | not tried (403 in the earlier lane) |

## Detector reruns (copies of the lane scripts run against production, outputs in scratchpad)

| lane | detector | earlier -> now | reading |
|---|---|---|---|
| Sunni | `seam_in_chain` | 543 -> 50 | true drop; it cannot see truncated routes, orphans or the 192-chain report |
| Sunni | `non_name_surface` | 10,248 -> 5,940 | real drop; 5,940 still verb/aside/long surfaces |
| Sunni | `gap_has_unstored_words` | 2,841 -> 3,053 | rises with the lost-name regression (names fall in the gap now) |
| Sunni | `chrono_contradiction` 604 -> 233, `repeated_narrator` 151 -> 87, `text_order_mismatch` 11 -> 6, `tahwil_marker_vs_chain_count` 530 -> 393, `truncated_before_companion` 474 -> 458, `bare_relation_resolved` 2,496 -> 2,490, `prophet_as_mention` 105 -> 105, `length_outlier` 2,834 -> 2,981 | | |
| Imami | `D06c` Cartesian across «جميعا» | 1,346 -> 351 (130 reports) | still fires; partly misfires on label chains |
| Imami | `D02` ta'liq pronoun | 2,239 -> 1,883 | **misfires**: the pronoun is now a deliberate `not_a_narrator` label under `suspension`; D02b 192 -> 197 likewise |
| Imami | `D03b` irsal marker | 1,045 -> 152 | true drop (anonymous gap mention) |
| Imami | `D04` verb-prefixed | 3,873 -> 2 | **blind**: its regex misses «و قد روى», 81 such mentions remain |
| Imami | `D07` repeat 274 -> 400, `D05` Imam non-final 138 -> 246 | | rise: concatenated isnads and matn tails were deferred or only partly handled |
| Imami | `D06b` 675 -> 63, `D08` 29 -> 16, `D06a` 19 -> 6; `D04` clause, `D04c`, `D12`, `D13` 0 | | |
| Ibadi/Zaydi | `D3a` relation_as_mention (Zayd) 661 -> 629 / 1,247 (the lane prints two tables, reports and hits) | **misfires**: «أبيه/جده» are now resolved identities, still literal surfaces |
| Ibadi/Zaydi | `D2a` order_reversed (Rida) 0 -> 33 / 37 (same two tables) | **misfires** on inherited mentions (positions come from the parent) |
| Ibadi/Zaydi | `D5a` missing_chain 2/3 -> 151 (Rabi) / 44 (Zayd) | **real**, the 190 lost chains above |
| Ibadi/Zaydi | `D1b` inherited_chain_missing 27/202 -> 7/6; `D5c` 7 (Rabi), 3 (Rida) | fixed, small remainder |

## Not checked

- Who a narrator is. Identities were compared with the surface only (the dump marks a mention whose resolved name shares no token with its surface; one clear case: `hadith:k6:29819`, b1, «عبد الله» carries «محمد بن يحيى بن محمد بن كثير» in an orphan chain).
- 31 of the 62 unflagged Imami chains (not read); Pure Canon chains against a printed edition; any report with no chain, except OpenITI (v6 diff + D5a) and the Sunni/Imami diffs of reports that lost every chain (11 Sunni, 453 Imami; the 30 Imami ones I read are statements or commentary with no isnad, mostly Faqih «و قال الصادق»/«و روي», so that is by design).
- Imami sample chain `chain:thaqalayn:8a5b2230a00a4e2927e2b69d:0001` (Kafi 7: «محمد بن يحيى عن أحمد بن محمد وعدة من أصحابنا عن سهل بن زياد» without «جميعا») has two readings and Noor could not be reached for it; marked `unverifiable`, not counted. Its twin Kafi 19 was resolved through Noor (pattern 8).
- Zayd and Rida were not compared with a freshly fetched independent edition.
- Hadith-level regression for Sunni reports whose chain survived but lost routes (only the 817-report proxy).

## Files

| file | what |
|---|---|
| `sample_check.csv` | 320 random chains (verdict, kind, `judged_by` read or auto, note, online source) + 240 population chains |
| `regressions.jsonl` | 372 rows: `name_lost_by_trim` 162, `chain_lost_written_chain_present` 190, judged chains made worse (`missing_link` 11, `wrong_split` 6, `false_seam` 2), `chain_lost` 2 |
| `summary.json`, `verdicts.tsv`, `pop_verdicts.tsv` | counts, intervals, my per-chain verdicts |
| scripts | `sample.cjs` (draw), `dump.cjs` (stored chain vs text), `lib.cjs` + `auto.cjs` (alignment pre-judge), `pops.cjs`, `diff_m2c_m3.py` + `diff2.py` + `lost.cjs` (Sunni trim/drop/lost names), `nochain.py` + `d5a.cjs` (lost chains), `before_after*.py` + `regress.cjs` (regression test), `counts*.cjs` (production counts), `thaq_compare.cjs`, `turath.cjs`, `noor*.cjs`, `build_outputs.cjs`, `append_regressions.cjs` |
| `fetched/` | every page fetched this round with URL, UTC time and intent (`turath_*`, `noor_*`, `hadithapi_*`) |

Run: `node --env-file=.env.local datasets/hadith-data/chain-audit/round2/sample.cjs`, then `dump.cjs <ids.json> <from> <to> [chars]`.
