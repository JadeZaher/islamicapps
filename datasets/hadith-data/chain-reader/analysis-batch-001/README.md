---
type: analysis
---
# Batch 001 (500 out-of-sample uncertain reports, prompt v3) judged by reading

There are no human labels here: my reading is the measurement. I read the Arabic of every sampled report, wrote down what its chain is, then compared with (i) the agreed reading and (ii) the stored chain.
I did not run a model, did not write outside `analysis-batch-001/`, and did not touch `private/` for anything but the text and the stored chains. Persons are not identified; each tradition is read in its own conventions.
Verdicts have a quote in `sample.tsv` / `cases.md`. Same limits as before: one Arabic reader (a model, not a scholar), and I saw the reading while judging the stored chain.

## 1. Sample and method

Eligible readings (agreed, readable, no hold): Sunni six-book 205, al-Faqih 86, other Imami 79 = 370. Drawn with seed 20261124: **85 / 80 / all 79 = 244**, every one read (`draw_sample.py`).
Also read: all **57** `reading_empty_stored_has_links` reports (the triage's 55 plus two that carry another hold too), 30 random of the **50** non-agreed reports, all **15** reports with `routes_end_at_different_links`, all **13** with `needs_ruling`.
Not read: the other 126 eligible readings, 20 of the non-agreed reports.
Rulings applied as given: the person whose words are relayed is the last link, including the Imam or source asked or answering and a Companion quoted as hearing the Prophet; someone only in the scene, whose action is described, at whose place it was heard, or who comments, is not; compiler heads every chain; the Prophet is not a link; a second isnad counts only for the same saying.
I judged the stored chain by the same rules, except that the compiler head is left out (stored chains never carry it). A stored surface with gloss or connective words («و روى X», «و يكنى أبا إسماعيل») is `defective: noise`: the names are right, the surface is not. I report fixes with and without that kind.
Where a verdict turns on a point the owner has not ruled on it carries a tag Q1..Q9 (section 7); the headline uses the ruling as given and the table shows the other way.

## 2. Per group (eligible readings, my verdicts)

| group | read | reader right (Wilson 95%) | stored right | reader fixes a defective stored chain | of which stored defect is more than noise | reader breaks a correct stored chain | net per 100 applied (range) |
|---|---|---|---|---|---|---|---|
| Sunni six-book (205 eligible) | 85 | **85/85 = 100% (96-100)** | 18/85 = 21% (14-31) | 67/85 = 79% (69-86) | 59/85 = 69% (59-78) | **0/85 (0-4)** | **+78.8** (+65 to +86) |
| al-Faqih (86) | 80 | **78/80 = 98% (91-99)** (1 wrong, 1 cannot tell) | 9/80 = 11% (6-20) | 69/80 = 86% (77-92) | 54/80 = 68% (57-77) | **0/80 (0-5)** | **+86.2** (+73 to +92) |
| other Imami (79) | 79 | **76/79 = 96% (89-99)** (3 cannot tell) | 6/79 = 8% (4-16) | 70/79 = 89% (80-94) | 53/79 = 67% (56-76) | **0/79 (0-5)** | **+88.6** (+75 to +94) |
| **overall, weighted by eligible share** (55% / 23% / 21%) | 244 | **98.6% (96.8-99.4)** | **16.0% (11.4-21.9)** | 82.6% (76.7-87.3) | about 68% | 0.0% (upper bound about 1.6% pooled) | **+82.6** (about +68 if noise-only stored defects are not counted) |

Net per 100 = fixes minus breaks per 100 applied readings. Classes (reports): Sunni: fix 67, both right 18. al-Faqih: fix 69, both right 9, both wrong 1, cannot tell 1. Other Imami: fix 70, both right 6, cannot tell 3. No report fell in "reader breaks a correct stored chain".
Stored defects seen (all groups): missing link 68, merged names 48, noise 42, junk link 37, route 15. Examples. Sunni «حدثنا أبو كامل … ح وحدثنا أحمد بن منيع»: stored chain one is «أبو كامل > يزيد» and stops (route). al-Faqih «و سمع زرارة أبا جعفر عليه السلام يقول»: stored is one link «و سمع زرارة أبا جعفر» (merged), reader «زرارة > [أبا جعفر]». other Imami «قال: قال أمير المؤمنين عليه السلام: لأنسبن الا»: stored stops at «الصادق … آبائه», the Imam is missing.

**Reader wrong or undecided in the eligible sample (5 of 244):** cr-4cbe02 (wrong: «و كتب البزنطي إلى أبي الحسن» keeps the writer of a question as a link while the readers drop the asker everywhere else, Q1); cannot tell: 550aae (Q2), b2ad9c and 941f93 (Q4), cb13de (Q5).
**Sensitivity to the asker question (Q1).** The readers drop a third-person asker («و سأل علي بن جعفر أخاه موسى بن جعفر»; 9 reports, all al-Faqih). If the owner rules that the asker is a link those 9 become wrong and 4cbe02 becomes right: al-Faqih 70/80 = 88% (78-93), overall weighted 96.3%. Count cannot-tell as wrong as well and it is the same figure.
In all 9 the stored chain is defective either way (the asker and the question words fused: «علي بن جعفر أخاه موسى بن جعفر > الرجل الجنب هل يجزيه»).

**Share of ALL uncertain reports with a right chain, before and after applying the eligible readings** (the non-eligible stay as stored; their stored correctness is unmeasured, so a range: they are all wrong / they are right as often as the eligible ones):

| group (batch size, eligible share) | before | after the eligible readings | gain in points | and if agreed empty readings were also applied (section 3) |
|---|---|---|---|---|
| Sunni six-book (250, 82%) | 17-21% | **82-86%** | +65 | n/a |
| al-Faqih (150, 57%) | 6-11% | **56-61%** | +49 | 78-83% with the 33 clear empties, 85-90% with the 11 asker cases too |
| other Imami (100, 79%) | 6-8% | **76-78%** | +70 | +4 (commentary readings) |

## 3. The 57 `reading_empty_stored_has_links` holds (both readers say there is no chain, we store one)

Stored chains in all 57 are junk (the saying's own words stored as links: «العائد في هبته كالعائد في قيئه», «و في خبر آخر», «ثواب المؤمن من»).
Who is right, by category (53 al-Faqih, 3 Ghayba of al-Tusi, 1 Maani al-Akhbar):

| category | n | reader (empty) | example |
|---|---|---|---|
| the text names no person: a bare saying, «و روي», «و في خبر آخر», a compiler's commentary, a ritual instruction | 33 | **right** | cr-2c405e «5808 - العائد في هبته كالعائد في قيئه»; cr-5429d7 «قال أبو جعفر مصنف هذا الكتاب: الدليل على عصمة الامام» (compiler commentary); cr-732efc, 8fe920, de4807 (Tusi's commentary) |
| the Prophet speaks or acts and no transmitter is written | 3 | right (the Prophet ends the chain) | cr-a2dfb1 «و نهى صلى الله عليه و آله عن السوم» |
| «و سأله X: عن …» / «و كتب إليه» with the Imam only a pronoun | 11 | right if the asker is not a link (Q1e), otherwise wrong; two flagged by both readers, one first-person | cr-37cb37 «و سأله الحلبي: عن صيد الحيتان»; cr-7425f4 «قال قلت فتفلت عليه دابته» |
| «وقال عليه السلام» / «و قضى عليه السلام» with the Imam named only in an earlier report; «روي عن الأئمة» | 8 | undecided (Q8, Q7): a back-reference link is arguably the right reading | cr-0fcaaf «وقال عليه السلام: «إذا أراد أحدكم أن يتزوج»» |
| a first-person narrative with an implicit transmission | 1 | undecided (Q9) | cr-549073 «قال محمد بن راشد … فلما سمعت ذلك من هشام عملت به» |
| the readers miss a written chain | 0 | | |
| the eligible-but-empty pronoun case with no name at all | 1 | right | cr-eb1e57 «و سأله: عن الخلاخل» |

**Per work.** al-Faqih: 53 empties: 33 certainly right (62%), 11 right if the asker is not a link (10 third-person askers, 1 first-person), 8 undecided (Q7, Q8), 1 undecided (Q9), **0 wrong**. Ghayba (Tusi) 3 and Maani 1: all right (commentary). The hold is therefore blocking correct "no chain" readings in at least 37 of 57 (65%), and in 48 of 57 (84%) if the asker is not a link; in none of the 57 did the readers miss a written chain.
**Recommendation:** make an agreed empty reading applicable (the stored chain is replaced by "no chain") for al-Faqih when the text contains no personal name before the saying and does not begin «و سأل / و سأله / و كتب / و سئل / و قال عليه السلام / و قضى / روي عن الأئمة»; for the Ghayba and Maani commentary readings; keep the asker, implicit-speaker and first-person patterns held until Q1, Q7, Q8, Q9 are ruled.
One caution from the sample: 9 of the eligible 80 reports carry the same «و سأل X Y» shape and are right only under the asker ruling; the empty readings and those reports stand or fall together.

## 4. Disagreements (30 of 50 read), `routes_end_at_different_links` (15), `needs_ruling` (13)

**Disagreements.** Which pass is right: A 6 (+2 on the asker ruling), B 8, both 9, B closer 1, core right in both with different extras 1, neither 1, cannot tell 2: no pass is better.

| class | n | which is right | fix |
|---|---|---|---|
| surface scope (case ending «جابر/جابرا», epithet «الرضا / أبو الحسن الرضا», comma inside a name, «في هذا الإسناد») | 5 | both | tool: fold in `canonical()` |
| tool or typo: surface not found (text «بنجعفر» / «أبو الحسنموسى» / attached «للرضا»), a reader typo («السابطي»), an invalid evidence quote | 5 | both right (4), A (1) | tool: fold; `validate` ignores an unfound `fixes` quote |
| shared tail dropped from a route by one pass | 4 | B 3, A 1 | the v3 rule is there and one pass still misses it: the hold is right |
| speaker or source omitted by one pass («فقال حذيفة أنت كنت تفعل ذلك», «فقال حدثني أبو مالك الأشعري», «لو كنت أنا لقتلتهم») | 4 | the pass that adds him | prompt example |
| variant remarks or a later partial isnad written as routes («بمثل حديث إسماعيل بن جعفر», «رواه ابن إسحاق») | 3 | the pass that does not | prompt |
| parallel pair misparsed or a restated name crossed («حدثنا أبو الوليد، حدثنا أبو عوانة، كلاهما عن أبي بشر») | 2 | the other pass | prompt example |
| asker written or not (Q1) | 2 | A per ruling | owner |
| an unnamed gap «رفعه» omitted (1), a pronoun «إليه» written as the Imam (1), nested «؛» (1), an Imam inside a narrated scene (1), a second man named or not (1) | 5 | B, B, neither, cannot tell, cannot tell | prompt (the pronoun); owner (Q4) |

Agreement is informative: in none of the 30 are the two passes both confidently right with different chains; the differences are tails, variants, speakers, scope and the tool.

**`routes_end_at_different_links` (15):** seven of them are agreed readings: **5 wrong** (cr-160be9, 162ebe, 844adb, d2bb6c, ee5c9a: each drops a tail written once, or is a nested «؛» structure) and **2 right** (cr-21210d, where the text abbreviates «فذكر نحوه»; cr-3c59ef, two isnads that end at different Companions).
The other eight are disagreements (the hold fires on one pass's reading); in each of the six where one pass is closer or right, the pass with the shorter routes is the wrong one. The hold is right 5 of 7 on agreed readings.
**`needs_ruling` by both (13):** eight are agreed readings: **2 wrong** (cr-162ebe, the same shared-tail error; cr-63a547, «قال لهم تنفر»: ابن عباس answers and the reading ends at عكرمة), **3 right** (cr-d6d6e1, e262e1, eb1e57) and **3 undecided** (cr-223908, 549073, 7425f4). About half of the 13 flags are on cases a ruling or the tail rule already settles (cr-162ebe, 8a1368, e262e1, eb1e57); the rest are real.

## 5. Wrong eligible readings, their classes, the fix, and what each proposed hold would also catch

There is one wrong eligible reading and four undecided ones in 244.

| class | n | example | fix | right eligible readings the proposed hold would also catch |
|---|---|---|---|---|
| asker kept as a link in one report, dropped in the other nine («و كتب X إلى Y»), Q1k | 1 | cr-4cbe02 | prompt: one rule for «سأل / كتب / شكا» | a hold on a text that opens «و سأل / و سأله / و كتب» would catch it **and 9 right readings** (ruling as given): 9 of 80 al-Faqih, precision 1 in 10; do not build it unless the owner rules that the asker is a link, in which case all 10 become wrong and the hold is right 10 of 10 |
| an Imam inside a narrated encounter, a judgment («قضى أمير المؤمنين»), two sayings in one report, a partial lower variant (Q2, Q4, Q5, Q6) | 4 undecided + 1 right | cr-550aae, 941f93, b2ad9c, cb13de | owner rulings, then prompt | no deterministic cue: not holdable |
| the book's author written as a link (Q3) | 1 right-by-assumption | cr-86d128 «و في نوادر إبراهيم بن هاشم» | owner | n/a |

Nothing else was found in 244 readings: no dropped tail, no omitted speaker, no inherited chain mistaken (the sample holds one inherited-chain reading, cr-2e0f3a, which takes six names from the second report back and checks against it; the other back references are closing «بإسناده» phrases). The holds of v3 did their work: the wrong readings of this batch are the 7 held ones above (5 routes-end, 2 needs-ruling) and the disagreements.
Two limits of this finding: I read each report's chain and the first 260 characters of the saying for a named speaker, not every matn to its end; and the eligible set is what the holds let through, so it is selected for easy shapes.

## 6. Verdict per group and the corpus

| group | verdict | numbers |
|---|---|---|
| Sunni six-book | **apply now** (v3 holds as they are) | 0 wrong in 85 (upper bound 4%); stored right in 21%, so 79 of 100 applied readings fix a stored chain; eligible yield 82% |
| al-Faqih | **apply with a named extra hold**: the asker pattern («و سأل / و سأله / و كتب / و سئل») until the owner rules on Q1; apply the empty readings that have no name (section 3) | 78/80 right, 1 wrong and 1 undecided; 9 of 80 turn on Q1; stored right in 11%; eligible yield 57% (86/150), 35% of the group are empties |
| other Imami (without al-Kafi) | **apply now** (encounter narratives, Q4 and Q5, are 4 of 79 and have no cue; send reports whose text has «حدثنا … قلت لسيدي» style scenes to the review sample) | 76/79 right, 3 undecided, 0 wrong; stored right in 8% |

**Does this justify the remaining ~13,300 uncertain reports?** Yes, for these three groups. Expected yield: about 74% eligible (about 9,800 reports), reader right about 98.6% (96.8-99.4) with the asker ruling as given and about 96% if not, against 16% (11-22) stored right; about 83 of 100 applied readings fix a stored chain and about 68 do so beyond surface noise; no break in 244. Hold and empty readings add the rest.
What this does not show: al-Kafi and the works outside the three groups (not drawn); the matn tails; how the holds behave on the 26 other works. Run the corpus in tranches of about 1,000, label a 100-report random sample of each tranche's applied readings, and stop on any break.

## 7. Judgements the owner has not ruled on (the verdict turns on them)

| tag | question | reports |
|---|---|---|
| Q1 | Is a person who only asks («و سأل X Y», «و كتب X إلى Y», «و سأله X») a link? (the readers say no; first-person «قال قلت» may differ) | 9 eligible al-Faqih + 1 wrong + 11 empties + disagreements cr-58aac5, 747357 |
| Q2 | «قضى أمير المؤمنين … في» with no transmitter: is he the one whose words are relayed? | 550aae |
| Q3 | Is the author of a cited book («في نوادر إبراهيم بن هاشم») a link? | 86d128 |
| Q4 | A narrated encounter where the Imam speaks and acts: is he the last link? | b2ad9c, 941f93, disagreement dcfca3 |
| Q5 | Two sayings in one report, the second with its own isnad: which is the report? | cb13de |
| Q6 | A remark «ورواه X عن Y فلم يرفعه» (partial, lower): a route or a variant? | 57c34c |
| Q7 | «روي عن الأئمة عليه السلام»: a collective Imam as a link? | 3fe7a2 |
| Q8 | «وقال عليه السلام» with the Imam named only earlier: empty reading or a back-reference link? | 7 empties |
| Q9 | A first-person narrative with an implicit transmission: a chain or none? | 549073 |
| (new) | When the Prophet is the speaker and the transmitter is unnamed in a one-sentence report, is the reading empty or a back reference? | 3 empties |

## 8. What I could not judge

- The other 126 eligible readings and 20 non-agreed reports; the matn beyond 260 characters; names against any lexicon.
- Whether a stored chain with surface noise only counts as "defective" for the pipeline (I report both figures).
- The 10 undecided empty readings and the 5 undecided eligible ones (section 7).
- Inherited chains: only one eligible reading in the sample carries them (cr-2e0f3a), so the previous-report mechanism is barely tested here.
- My verdicts were not blind: I saw the reading while judging the stored chain, and I am the only reader.

## Files

`sample.tsv` (the 244 eligible reports and the 57 empties: both verdicts, class, owner-question tags, quote), `cases.md` (non-right readings, stored-right ids, every empty reading, the 30 disagreements, the 15 and 13 holds, the owner questions), `draw_sample.py` (seeded draw, seed 20261124), `common_b1.py`, `dump_b1.py` (the reading dumps), `numbers_b1.py` (tables and intervals, `numbers_b1.json`), `build_cases_b1.py`, and the hand verdict files `v_sunni_a.txt`, `v_sunni_b.txt`, `v_faqih.txt`, `v_other.txt`, `v_empty.txt`, `v_dis.txt`.
Run from `chain-reader/` with `python -X utf8`: `draw_sample.py`, `numbers_b1.py`, `build_cases_b1.py`.
