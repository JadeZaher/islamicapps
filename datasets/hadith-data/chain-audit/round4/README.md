---
type: diagnostic
---
# Chain audit, round 4: out-of-sample check of the structure gate (`chains.structure_status`, commit `83c5e2f`)

Read-only against production (`retired_at is null`); only this directory was written; nothing deleted; no process left running. I was not involved in the gate. Every sampled item (310 checked chains, 60 uncertain chains, 150 pairs) was read by me against `text_ar`, `sanad_ar` (OpenITI works), the source's own `sanad` field (Ahmad, Darimi, Muwatta: judged against it, as in rounds 2 and 3) or the parent's text (inherited chains); none was counted clean unread. "Strict" is `../round3/README.md`: a missing, false, merged or split link, a non-narrator stored as a name, a wrongly inherited chain. The primary unit is the sampled chain (as the gate's own table); a second column gives the report-level rate (any chain of the sampled report). No online source was used (Turath/Noor not queried); everything is reading against the Arabic.

Samples: seeded (`round4-seed-1`, md5 order, `sample4.cjs`), one chain per hadith, excluding the 1,698 hadith ids and 1,088 chain ids in every earlier `sample_check.csv` / `verdicts.tsv`. Stratified as asked: 85 K6 (Muslim 20, the other five 13 each) + 35 Pure Canon (Ahmad 15, Darimi 10, Muwatta 10); Imami 70 al-Kafi / 20 Faqih / 10 Thawab; 40 al-Rabi; 25 Zayd; 25 Rida. Per-item readings: `sample_check.csv` (all 520), `verdicts.tsv`; figures are produced by `build_outputs4.py` (`summary.json`).

## 1. Claim versus measured (strict defect rate among CHECKED chains; Wilson 95%)

| group | gate README (in-sample) | round 4, sampled chain | round 4, any chain of the report |
|---|---|---|---|
| Sunni, nine works | 2/76 = 2.6% (0.7-9.1) | **10/120 = 8.3% (4.6-14.7)** | 15/120 = 12.5% (7.7-19.6) |
| Sunni K6 text works | 2/47 = 4.3% (1.2-14.2) | **9/85 = 10.6% (5.7-18.9)** | 14/85 = 16.5% (10.1-25.8) |
| - Muslim | (worst work, under half kept) | 1/20 = 5.0% (0.9-23.6) | 3/20 = 15.0% (5.2-36.0) |
| - K6 without the 2 judgment items | | 7/83 = 8.4% (4.1-16.4) | |
| Sunni Pure Canon | 0/29 = 0.0% (0.0-11.7) | 1/35 = 2.9% (0.5-14.5) | 1/35 |
| Imami | 2/63 = 3.2% (0.9-10.9) | **4/100 = 4.0% (1.6-9.8)** | 6/100 = 6.0% (2.8-12.5) |
| - al-Kafi | | 0/70 = 0.0% (0.0-5.2) | 1/70 |
| - Man la yahduruhu al-Faqih | | **4/20 = 20.0% (8.1-41.6)** | 5/20 |
| - Thawab al-Amal | | 0/10 (0.0-27.8) | 0/10 |
| al-Rabi | 2/26 = 7.7% (2.1-24.1), reports with a chain | 2/40 = 5.0% (1.4-16.5) | 2/40 |
| Musnad Zayd | 0/39 = 0.0% (0.0-9.0) | 0/25 = 0.0% (0.0-13.3) | 0/25 |
| Sahifat al-Rida | 0/40 = 0.0% (0.0-8.8) | 1/25 = 4.0% (0.7-19.5) | 1/25 |

Reading: the Sunni claim is optimistic (K6 claim 4.3% lies below my interval; point estimate 2.5x). Imami, Rabi, Zayd, Rida are compatible with the claim (small n; Rida 1 defect, Rabi 2). The Imami figure hides one bad work: Faqih 4/20. Stratified weighting by checked-chain population (K6 30,914 chains; Bukhari 4/13 has most weight) would give K6 about 12% and Imami about 4%; I report the unweighted rates because the strata are the gate's own. The 17 chain-level defects: 11 missing link, 3 merged names, 3 non-narrator stored as a name; none is a mid-chain loss (all lost links are at the tail), which is why pairs hold up (section 3).

Report-level defects that are not chain-level (7): 4 are in a sibling chain the gate had already marked `uncertain` (Muslim 4247 b0, Abu Dawud 3213 b0, Kafi 129 b1, Faqih 57 b1; verified with `q5.cjs`), 3 are second isnads written in the text with no chain stored (Muslim 5071, Tirmidhi 2302, Bukhari 7501).

Judgment calls (flagged `companion_in_matn_judgment` in the CSV): a Companion named in the matn as the speaker or source and not stored, same rule as round 3's `rabi_0644` / `rabi_0229` (Bukhari 5450, Tirmidhi 2308, Rabi `rabi_0423`; uncertain Tirmidhi 1000, Ibn Majah 4091). Dropping them is the "K6 without judgment" row. Pure Canon chains whose source field itself loops (uncertain `pc_67566`, `pc_41350`) were counted correct against the source.

## 2. Cost of the gate: UNCERTAIN chains that are correct (60 drawn uniformly: 40 Sunni, 20 Imami)

Correct (sampled chain has no strict defect): **40/60 = 66.7% (54.1-77.3)**; Sunni 25/40 = 62.5% (47.0-75.8), Imami 15/20 = 75.0% (53.1-88.8). Applied to the live uncertain counts (Sunni 20,441 chains, Imami 12,881), about 12,800 (9,600-15,500) Sunni and 9,700 (6,800-11,400) Imami correct chains are withheld. A chain counts under each reason it carries; "alone" = that reason only.

| reason | correct / n (any) | correct / n (alone) |
|---|---|---|
| work_not_checked | 13/14 = 92.9% (68.5-98.7) | 12/12 = 100% (75.7-100) |
| not_a_name | 9/10 = 90.0% (59.6-98.2) | 6/7 |
| text_names_more_after | 6/8 = 75.0% (40.9-92.9) | 5/7 |
| many_routes | 9/13 = 69.2% (42.4-87.3) | 7/9 |
| unaccounted_route_marker | 2/4 | 1/2 |
| repeated_name | 2/3 | 1/1 |
| text_between_links | 4/15 = 26.7% (10.9-52.0) | 2/10 = 20.0% (5.7-51.0) |
| joined_names | 1/1 | 1/1 |
| duplicated_link | 0/1 | 0/1 |
| short_beside_long | 0/1 | 0/1 |

So `work_not_checked`, `not_a_name` (the matches I read were glosses such as «يعني ابن سعد», «سعيد هو ابن أبي أيوب», a quoted verse after a correct name) and `many_routes` discard mostly correct chains; `text_between_links` is the only detector whose flags were mostly right (11/15 defective: lost link between neighbours, Qur'anic words as links, truncated routes). Defects among the 20 uncertain-and-wrong: 8 non-narrator stored (Qur'anic phrases «فاغسلوا», «العزى», «لكل جعلنا موالي»), 5 missing link, 3 truncated route (e.g. Muslim 5506 stored only «يحيى بن يحيى»), 1 duplicated, 1 false link, 1 concatenated isnads, 1 merged. n per reason is 1-15: only the `work_not_checked` and `text_between_links` rows are firm.

## 3. Pair precision (`narrator_transmissions`, what readers see)

150 rows drawn uniformly from the 25,465 rows of the view (100 whose supports include a Sunni report, 50 Imami), one random supporting checked chain each (adjacent standing identities, same filters as the view's SQL, `pairs_sample.cjs`). Criterion: the text says the student transmits directly from the teacher (adjacent in one route, right direction).

- **149/150 = 99.3% (96.3-99.9)**: Sunni 100/100 (96.3-100), Imami 49/50 = 98.0% (89.5-99.6).
- The one wrong pair: `chain:thaqalayn:a8e6abfbf823602d7a6c46f9:0001` (al-Kafi 186), stored `... محمد بن إسماعيل > [حنان بن سدير > عن محمد بن الفضيل] > أبي الصباح > أبي عبد الله`; text «عن حنان بن سدير عن أبي جعفر (عليه السلام) وعن محمد بن الفضيل عن أبي الصباح عن أبي عبد الله (عليه السلام) قالا نهانا». Two routes joined by «وعن»; the pair makes Hannan b. Sudayr the student of the head of the second route.
- Why pairs beat chains: of the 17 chain defects found, none sits between two stored neighbours; a lost tail link or a non-name with no identity forms no pair (the 299 checked mentions whose surface contains «/» all have `narrator_id` null, 0 pairs). The pair-wrong shapes are flattened/crossed routes and lost mid-chain links, which `text_between_links` / `short_beside_long` / `crossed_routes` catch. The upper bound for a pair error rate is 3.7%.
- **Identity note** (judged only from the text and the stored names): 2 of 150 are right links with an evidently different person by the text: `pc_80726` (Ahmad 831) source field «سالم ابن أبي الجعد يحدث» against narrator record «سالم بن رافع»; `chain:k6:24476:0000` (Nasai 36) text «عن الأشعث بن عبد الله، عن الحسن» against record «أشعث بن عبد الملك». 2 more differ in nasab strings without the text settling it («حبيب ابن أبي ثابت» against «حبيب بن قيس بن دينار» in Ahmad 5; «محمد بن محصن» against «محمد بن إسحاق ... بن محصن» in Ibn Majah 51). So 1.3% (0.4-4.7) strong, 2.7% (1.0-6.7) with the weak ones, all Sunni.

## 4. Missed patterns (checked chains), ordered by estimated number of checked chains

"Estimate" = sample rate x live checked chains (Wilson range). "Query" = `counts4.cjs` / `counts.json` on all 77,630 checked chains, a regex candidate count, precision only spot-read (examples read: yes / no noted), so a lower bound for the shape it names, not for the pattern.

1. **K6: a named source after the last stored link is lost** (8 of 85 K6 chains: `k6:14467`, `k6:1326`, `k6:18933`, `k6:25022`, `k6:1277`, `k6:1708`, `k6:5215`, `k6:22632`). Estimate 9.4% (4.9-17.5) of 30,914 = **about 2,900 (1,500-5,400)**. Query for the hearing-verb shape alone: 87 chains in 84 hadiths. Detector: `text_names_more_after` (`AFTER_LAST`) exists but reads only a link word + name or «سالت/سمعت» + a nasab-shaped name. It misses third-person «سمع», «قرأت على», «نظر إلى», «نشهد على» (4 of the 8 are of that kind: adding those verbs would catch them); bare «قال X قال Y» / «قلت من حدثك قال X» (2 of 8) has no detector; a Companion named in the matn as speaker (2 of 8, judgment) cannot be caught by a shape rule.
   - Muslim 7229, `chain:k6:14467:0000`: stored `سعيد بن منصور > يعقوب > أبو حازم > عبيد الله بن مقسم`; text «عن عبيد الله بن مقسم، أنه نظر إلى عبد الله بن عمر كيف يحكي رسول الله».
   - Bukhari 1373, `chain:k6:1326:0000`: stored `... > ابن شهاب > عروة بن الزبير`; text «أخبرني عروة بن الزبير، أنه سمع أسماء بنت أبي بكر رضى الله عنهما تقول».
   - Also: `chain:k6:1708:0000` stored `عثمان بن الهيثم > ابن جريج`, text «قال عمرو بن دينار قال ابن عباس»; `chain:k6:5215:0000` text «عن عمرو، قال كان أبو نهيك رجلا أكولا فقال له ابن عمر إن رسول الله صلى الله عليه وسلم قال» (judgment).
2. **al-Faqih: matn or two people stored as the link** (4 of 20 Faqih chains). Estimate 20% (8.1-41.6) of 4,102 = **about 820 (330-1,700)**. Query: 88 single-link chains whose link has 3+ words and no nasab word, 30 chains with an asker and an Imam in one link («أخاه», «العبد الصالح»), 85 chains in the three Imami works with a 4+-word link without nasab words (most are Faqih). Detector: `not_a_name` needs six words with no nasab word (4-word clauses pass) and `joined_names` fires only on «و»; Faqih is not in `UNCHECKED_WORKS` (round 3 sampled 12 Faqih chains, 2 defective; now 4/20).
   - `chain:thaqalayn:79ed28cbd09d4b084046689d:0000` (Faqih 175): text «5813 - الدال على الخير كفاعله»; stored single link «الدال على الخير كفاعله».
   - `chain:thaqalayn:05511b17dc9665d7e37e63d8:0000` (Faqih 20): text «و قال أبو جعفر عليه السلام : «البر و الصدقة ينفيان الفقر ...»; stored link «صاحبهما سبعين ميتة سوء».
   - Merged: `chain:thaqalayn:6170bd3f7dd702e5d70ec60f:0000` (Faqih 24), text «و سأل علي بن جعفر أخاه موسى بن جعفر عليه السلام: عن الميت يغسل في الفضاء», stored `علي بن جعفر أخاه موسى بن جعفر`; `chain:thaqalayn:5d638b2449dce025adfae737:0000` (Faqih 40) «سليمان بن جعفر الجعفري العبد الصالح موسى بن جعفر».
3. **Pure Canon: «تابع/» stored as a narrator link** (sample 1/35, `pc_12480`). Query (exact surface): **290 checked chains in 258 hadiths** with a surface containing «/» (277 are «تابع/»); all have no identity, so no pair; shown as a link. Detector: `not_a_name` passes a single 4-letter word; the artefact comes from the source field (`sanad` «تابع/, روح, عبد الصمد ...»).
4. **Imami: two routes joined by «وعن» into one chain** (the wrong pair above). Sample 1/100 (0.2-5.5) = about 200 (40-1,100); query 11 chains in 9 hadiths with an Imam blessing followed by «وعن». Detector: `crossed_routes` lists only four al-Kafi pairs; `text_between_links` is switched off because the Imam named in the gap is stored by a sibling chain (`report_names` exemption in `_gap_says_more`).
   - `chain:thaqalayn:cc6427c9e7be849e01cae759:0001` (Kafi 85): stored `أحمد بن محمد الكوفي > ابن جمهور > أبيه > محمد بن سنان > مفضل بن عمر > عن عبد الله بن عبد الرحمن الأصم > حريز > محمد بن مسلم > أبي عبد الله`; text «... عن مفضل بن عمر عن أبي عبد الله (عليه السلام) وعن عبد الله بن عبد الرحمن الأصم عن حريز عن محمد بن مسلم».
   - `chain:thaqalayn:ce989a8e3b5a820f60c48d70:0001` (Kafi 139): stored `... > محمد بن مسلم > عن الساباطي > أبي عبد الله أنهم سألوهما`; text «عن أبي جعفر (عليه السلام) وعن الساباطي وعن زرارة عن أبي عبد الله».
5. **al-Rabi: source «عنه» unresolved, Companion in the matn** (2 of 40: `rabi_0369`, `rabi_0423`). Estimate 5% (1.4-16.5) of 799 = about 40 (11-130); query for the pronoun shape: 3 candidates, 1 read (`rabi_0369`; `rabi_0982` is an aside, not a defect). Detector: `LABEL` exempts «عنه»; no check of one-link chains.
   - `chain:openiti:ibadi:rabi_0369|369|V01P093:0000`: text «أبو عبيدة عنه أيضا قال:» stored `أبو عبيدة` alone.
   - `rabi_0423`: text «أبو عبيدة عن جابر بن زيد قال: سئل أسامة بن زيد: كيف كان رسول الله صلى الله عليه وسلم يسير ... قال: كان يسير العنق» stored `أبو عبيدة > جابر بن زيد` (judgment).
6. **Rida: an inherited continuation names a further source in its own text** (1 of 25: `rida_0016#3`). Estimate about 8 (1-40) of 204; query (strict regex) 3, 1 read defective. Detector: `assess` blanks inherited chains (`written = []`), so the continuation's own words «قال حدثتني اسماء بنت عميس» are never read.
   - `chain:openiti:imami:rida_0016#3|16|V01P463:0000`: text «وباسناده قال: حدثني أبي علي بن الحسين، قال حدثتني اسماء بنت عميس قالت»; stored the master isnad up to «أبي علي بن الحسين».
7. **K6: two people and a verb in one link** (1 of 85). Query (exact shape): **2 checked chains**. Detector: `not_a_name` tests `NOT_NAME_WORD`, which does not hold «حدثناه».
   - `chain:k6:30303:0000` (Ibn Majah 89): link «أبو الحسن القطان حدثناه خازم بن يحيى»; `chain:k6:30662:0000` (Ibn Majah 448): «أبو الحسن بن سلمة حدثناه أبو حاتم».
8. Not a chain defect, for completeness: second isnads written after the matn with only one chain stored: 16 K6 hadiths by query (Muslim 5071, Tirmidhi 2302, Bukhari 7501 read).

## 5. What I could not check

- Identity (only text and stored names, section 3).
- Pure Canon is judged against its own `sanad` field; if the field is wrong the chain is "right".
- The pair sample draws one supporting report per pair; a pair with several supports is judged on one.
- Query counts in section 4 are regex candidates; only the examples were read. `counts4b.cjs` (a broader "named source before the Prophet" count) flagged 11,685 of 30,914 K6 chains because first-person Companion narratives match, so I discarded it; no figure from it is used.
- Per-reason uncertain rates rest on 1-15 chains each.
- Population estimates multiply unweighted stratum rates by population; weights are noisy (Bukhari 4/13).
- No online edition was consulted; the three judgment items would change K6 to 8.4% if all were dropped.

## Files

`sample_check.csv`, `verdicts.tsv`, `summary.json`, `counts.json` (query counts and examples); scripts `sample4.cjs` (samples), `dump4.cjs` / `pairdump.cjs` (the views I read), `pairs_sample.cjs`, `counts4.cjs`, `build_outputs4.py`, `q0-q6.cjs` (schema, view definition, one-off checks); raw readings `v_main.txt`, `v_override.txt` (item 231), `u_main.txt`, `p_main.txt`; id lists `sample_ids.json`, `sample_ids_uncertain.json`, `pair_ids.json`. Run: `node --env-file=.env.local datasets/hadith-data/chain-audit/round4/sample4.cjs`, then `dump4.cjs sample_ids.json <from> <to> [chars]`.
