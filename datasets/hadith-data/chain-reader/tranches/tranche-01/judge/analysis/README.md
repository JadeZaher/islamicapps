---
type: analysis
---
# Tranche 01 (980 reports, prompt v3.1, two Haiku passes) judged by reading

I am a single model reader (not a scholar). I read the Arabic of every report below, wrote what its chain is, then compared with the agreed reading and with the stored chain. **I was not blind**: the dump shows the reading and the stored chain together, so my verdict on the stored chain was formed with the reading in view. I ran no model, changed nothing outside `judge/analysis/`, and identified nobody: each tradition is read in its own conventions. Every verdict has a text quote in `sample_verdicts.tsv` / `cases.md`.
Definitions are batch 001's (`../../../../analysis-batch-001/README.md`): reader right = right + representation only; undecided (`CT`) counts as not right; `stored right` needs the same persons in the same order (a stored link that carries gloss or connective words is `defective: noise`; a relation word kept with a name, «أخيه علي», counted right: 3 of 201, sensitivity below); classes FIX (reader right, stored defective), JUNK (stored has no real link: a subclass, counted in "fixes"), BOTHR, BREAK, BOTHW, CT. The owner rulings of the brief are applied as given (asker is a link; the one asked or answering is the last link; scene persons are not; compiler heads every chain; the Prophet is not a link; the unruled list is `cannot_tell`).

## 1. What was read

| set | read | how drawn |
|---|---|---|
| the 100 pre-drawn eligible readings (`../sample.tsv`, seed 20261201) | 79 Sunni, 8 al-Faqih, 13 other Imami (2 "no chain") | given |
| extension (`draw_extension.py`, seed 20261301, from the eligible set minus the 100) | +24 Sunni, +49 al-Faqih, +27 other Imami | fixed seed |
| **total read** | **104 Sunni, 57 al-Faqih (all eligible: a census), 40 other Imami = 201** (al-Faqih + other Imami 97, Sunni 104) | |
| eligible readings in the tranche | 589 / 57 / 101 = 747 (78.8% / 7.6% / 13.5%) | triage |
| also read | all 15 eligible "no chain" readings; all 45 eligible readings with an asker opening or an inherited link; a random 40 of the 133 valid-but-different reports; all 35 `needs_ruling` agreed readings | |
Not read: about 534 of the 747 eligible readings (485 Sunni, 61 other Imami, minus the 12 outside the sample that I read for items 4 and 7), 93 of the 133 differing reports (I scanned the diffs of the 22 non-Sunni ones), all other non-agreed reports, and every matn past the first 90-330 letters (I scanned the rest of each sampled text for transmission verbs after the isnad, `later_isnad_scan.py`: no missed second isnad).

## 2. Per group, beside batch 001 (Wilson 95%)

Net per 100 applied = fixes minus breaks per 100 applied readings.

| group | read | **reader right** | stored right | reader fixes a defective stored chain | breaks a correct stored chain | net per 100 | wrong / cannot tell |
|---|---|---|---|---|---|---|---|
| **Sunni six books, tranche 01** | 104 | **98/104 = 94.2% (88.0-97.3)** | 24/104 = 23.1% (16.0-32.0) | 74/104 = 71.2% (61.8-79.0) | 0/104 (0-3.6) | +71.2 | 6 / 0 |
| batch 001 | 85 | 85/85 = 100% (96-100) | 18/85 = 21% (14-31) | 67/85 = 79% (69-86) | 0/85 (0-4) | +78.8 | 0 / 0 |
| **al-Faqih, tranche 01** (census) | 57 | **52/57 = 91.2% (81.1-96.2)** | 0/57 = 0% (0-6.3) | 52/57 = 91.2% (81.1-96.2) | 0/57 (0-6.3) | +91.2 | 1 / 4 |
| batch 001 | 80 | 78/80 = 98% (91-99) | 9/80 = 11% (6-20) | 69/80 = 86% (77-92) | 0/80 (0-5) | +86.2 | 1 / 1 |
| **other Imami, tranche 01** | 40 | **38/40 = 95.0% (83.5-98.6)** | 6/40 = 15.0% (7.1-29.1) | 32/40 = 80.0% (65.2-89.5) | 0/40 (0-8.8) | +80.0 | 0 / 2 |
| batch 001 | 79 | 76/79 = 96% (89-99) | 6/79 = 8% (4-16) | 70/79 = 89% (80-94) | 0/79 (0-5) | +88.6 | 0 / 3 |
| **overall, weighted 78.8 / 7.6 / 13.5** | 201 | **94.1% (89.2-96.8)** | 20.2% (14.5-27.5) | 73.9% (66.3-80.3) | 0/201 (0-1.9) | **+73.9** (+63.8 if noise-only stored defects are not counted) | 7 / 6 (4.7% / 1.2%) |
| batch 001 overall (weights 55 / 23 / 21) | 244 | 98.6% (96.8-99.4) | 16.0% (11.4-21.9) | 82.6% (76.7-87.3) | 0 | +82.6 (about +68 without noise) | 1 / 4 |

Weighted intervals are Wilson on the effective n of the weighted proportion (`numbers_t1.py`). The pre-drawn 100 alone: 95/100 right (Sunni 75/79 = 94.9%, al-Faqih 8/8, other Imami 12/13), weighted 95.0% (88.8-97.8).
Chain readings only (without the 5 al-Faqih and 3 other-Imami "no chain" readings): Sunni 98/104, al-Faqih 48/52 = 92.3% (81.8-97.0), other Imami 36/37 = 97.3% (86.2-99.5), weighted 94.5% (89.6-97.2). Cannot-tell out of the denominator: weighted 95.3%.
Breaks: 0 of the 30 reports whose stored chain was right (Wilson 0-11.4%) and 0 of 201. The wrong readings all replaced a defective stored chain, never a right one.
Stored defects (all groups, 171 defective): missing link 68, junk link 48, merged names 27, noise 20, route 8.
Rule-checked stored chains: 19 of the 201 reports carry one (55 of the 747 eligible). In 12 the checked chain equals a reader route; in **6 it is itself defective** (598a9d: checked chain is the word «ينبغي»; 3e8919: «ابن مبارك > هب بن منبه», drops معمر and the gap; 8d9d06: «عن يونس» in the name; the checked chains of 9c66d7, a43bb8 and cf634a are the compiler's commentary); 1 more (e3f7d5) is right but the reader adds a variant route. The reader never contradicted a right checked chain.

**Does tranche 01 confirm batch 001? Partly.** Confirmed: no break, a large net gain (+73.9 per 100 against +82.6), stored chains right only about one in five (20% against 16%). **Not confirmed: the right-rate.** 94.1% (89.2-96.8) against 98.6% (96.8-99.4): 7 wrong readings in 201 against 1 in 244 (Fisher two-sided p = 0.025; Sunni alone 6/104 against 0/85, p = 0.033), and the point estimate is under the 95% gate of `RUN.md` section 3 (the pre-drawn 100 sit exactly on it, 95/100). Three of the 7 wrong readings are one mechanism (section 8): a `variant: true` group that the submission stores as a chain. If the pipeline dropped variant groups, weighted right would be 96.4%; with the four proposed holds below the read sample would be 98.0% on the 195 left (in-sample tuned, so not a measurement).
Not for any group: apply nothing before the variant-route decision (section 9).

## 3. Breaks

None. No reading broke a correct stored chain; the 30 right stored chains (24 Sunni, 6 other Imami, none al-Faqih) were all re-read correctly (list in `cases.md` section 2). Nearest to a break: **a20cb6** (other Imami, `CT`, stored defective): «قال: كنت عند أبي عبد الله عليه السلام في فسطاطه بمنى، فنظر إلى الناس فقال: يأكلون الحرام» is a narrated encounter where the Imam looks and speaks (unruled); the reading writes him as the last link. And **e3f7d5** (Sunni): the stored checked chain is right, the reader's reading is right plus a spurious variant route «حفصة > أم عطية» from «زاد في حديث حفصة عن أم عطية بنحو هذا».

## 4. The asker ruling and the al-Faqih openers (new in v3.1)

All 45 eligible readings in the tranche with an asker opening (31) or an inherited link (26; 12 are both) were judged (`asker_inherited.tsv`, `find_asker_inherited.py`). Every asker opening is al-Faqih; none is Sunni.
- **Asker written as a link: 26 of 26** readings whose text names the asker (18 «و سأل X Y» / «و كتب X إلى Y» / «و شكا» and 8 «و سأله X» with the Imam a pronoun). Examples: «و سأل علي بن جعفر أخاه موسى بن جعفر» gives `علي بن جعفر > [M]موسى بن جعفر` (17ad1f, 130ab8, a3eaae, 9d76c5, f7be5a, 88fb34, bb5e28, e6d27a, 3c445a, d8c7b3); «و كتب البزنطي إلى أبي الحسن» gives البزنطي then أبي الحسن (d60451; the shape of batch 001's one miss, cr-4cbe02, comes out right); «و شكا هشام بن إبراهيم إلى أبي الحسن الرضا» (f124f1, held for another reason). The stored chain is defective in all 18 (the asker and the question fused or junk; a6c31e also has a right checked chain). `asker_not_a_link` fired on 1 report of the tranche and not on any eligible one.
- Unnamed asker, the Imam only (1511ec «و كتب إليه», c22e6d, 909bb3 «و سأله: عن الخلاخل», 795ecb «و سئل: عن رجل», eb30a7 «و سئل الصادق»): the reading writes the Imam and no asker, per the prompt. Plausibly the same asker as the report before (909bb3 follows «و سأل علي بن جعفر ...») but the text does not say, so I count them right; an owner may want the asker inherited too.
- **Inherited Imam or chain: 25 of 26 taken from the right report**, 1 undecided. Speaker openers: «وقال عليه السلام» takes «الصادق» from the report before in 598a9d (prev1 898 «وقال الصادق عليه السلام»), 931265, 918cf2, 73a5fd; 80a548 takes أبي عبد الله from 2510 and a83e6a takes «أمير المؤمنين» from 4362 across a report about the Prophet (4363), both under the ruling but with a doubt: in 80a548 the packet lists 2509 as prev1 and 2510 as prev2 for report 2511 (not nearest-first: the report order in the data is out of sequence), and in a83e6a the intervening report names the Prophet. «وسأله X» takes the Imam from 1 to 3 reports back (037ef5 from 4157 across 4159 «قال: و سألته» and 4158 «و في رواية عبد الله بن سنان عن أبي عبد الله»; c22e6d from 3884 across two «و كتب إليه»; 233038 from the nearest, 1912 «و في رواية الحلبي عن أبي عبد الله», not from 1911 which names another Imam). «وبهذا الإسناد» / «وعنه» take the chain names before the new name (faa2f4 eight names from report 17, bae550 five from 20, 1f3dcd two, 16d95e two, 6b5a69 four, 50837b three, bc40ec and b99548 the teacher). Of the 21 cases whose reports carry numbers, 20 are 1-3 reports back; the exception is **b36519**: «و سأله سماعة بن مهران» (report 1071) inherits «أبو جعفر» from 1066 («وقال أبو جعفر عليه السلام: سلم عمار على رسول الله»), five reports back; nothing in the text confirms it (`CT`). A hold on a gap greater than 3 catches 1 reading of 26 (b36519) and 0 right ones (`inherited_distance.py`).
- Observation outside the question: an unnamed asker is not written, so the inherited-Imam reading is a single link: the stored chain was junk in all of these, so they are fixes.

## 5. Why agreement fell (91.4% to 83.8%)

By group (all reports / both valid / agreed): tranche Sunni 759 / 741 / 636 (83.8%), al-Faqih 67 / 65 / 62 (92.5%), other Imami 154 / 148 / 123 (79.9%); batch 001 under the same v3.1 tool Sunni 250 / 248 / 224 (89.6%), al-Faqih 150 / 150 / 143 (95.3%), other Imami 100 / 96 / 90 (90.0%).
Decomposition of the 7.6 points: **2.1 points are invalid outputs** (26 reports have an invalid output in at least one pass, against 3 of 500; pass A 21 outputs: 8 `surface_not_in_text`, 6 `order`, 6 `shape: missing key fixes`, 1 `inherited`; pass B 7: 3 `order`, 2 `not_json`, 2 `surface_not_in_text`; the six missing `fixes` keys are fixable in the tool by reading a missing key as `[]`); **5.6 points are valid-but-different readings** (133 of 980 against 40 of 500). Of the 5.6, composition explains 0.7 (the tranche is 77% Sunni, batch 001 was 50%) and 4.9 are within-group: Sunni differ-rate 9.6% to 13.8%, other Imami 6.0% to 16.2%, al-Faqih flat (4.7% to 4.5%).
The 133 are 105 Sunni, 25 other Imami, 3 al-Faqih. A random 40 read (`v_dis40.txt`, `cases.md` section 4; seed 20261401): the pass that is right A 11, B 14, both 11, neither 1, cannot tell 3. Causes (primary):

| cause | n of 40 | which pass | fixable in |
|---|---|---|---|
| equivalent readings that fail to compare equal: epithet or title in the surface («أبا مرة، مولى أم هانئ», «أم المؤمنين، عائشة», «أمير المؤمنين علي», «أبا عمر صاحب أبي العباس ثعلب», restated «مخرمة» / «مخرمة بن بكير»), 10 + 1 | 11 | both right | **tool** (fold a trailing «، مولى X» / title / restated shorter form) |
| shared tail dropped from a route (3b10bc, 434301, 570d61, 5dc04b, 6cef3d, 75e2df, 770271, 98cb64, 3e5548) | 9 | A 3 times, B 6 times; the existing `routes_end_at_different_links` fires on 3 | tool hold exists; prompt example |
| a variant remark written as a route («أرسله ابن عون وعطاء بن السائب», «بالإسنادين جميعا», «وروى الزهري الكلام الأول عن سعيد فأرسله», «وقد روى بعضهم هذا الحديث عن ثابت ... مرسلا», «من غير هذا الوجه»), 5 + 1 | 6 | the pass that does not | prompt |
| co-transmitter or name grouping (kunya split in two links, three men fused in one link, restated «ابن علية» written twice) | 3 | A, B, B | prompt / tool check |
| the one who speaks or answers added, omitted or flagged (cb56aa «بال جرير ... فقال نعم رأيت»; 2aea01; 26bb55 confirmer added) | 3 | the pass that adds him, twice | prompt (rule 6 boundary) |
| unruled Q3 / Q4 (306ccd, 2a5330, 881857) | 3 | cannot tell | owner |
| bracketed editorial insertion «[عن أبيه]», «[قال حدثنا بكر ...]» handled differently by the two passes (54c186, dfff83) | 2 | one pass each | prompt (brackets are text) |
| unnamed co-transmitter «وذكر آخر» / its placement (8b6d16, fb4b56) | 2 | B / cannot tell | prompt |
| a remark about who mentions «عن أبيه» (c1d4c5) | 1 | cannot tell | owner |
Whole-population cross-check on all 133 (`dis_population.py`, crude): surface-only 25, one route set a prefix of the other 38, different number of routes 47, other 23; of the 22 non-Sunni differing reports I did not draw, about half are artefacts (surface or laqab 6, e.g. «المعروف بغلام أبي علي بن جعفر ...» and «أخبرني من سمع» against «من سمع»; the compiler named in the text and written 2; an unnamed gap «يرفعه» / «بلغه» written or not 2; a bracketed name 1), the rest are a different last link (5, three flagged by both), co-transmitter grouping (2), a dropped tail (1), an extra route (1) and chain against no chain (2).
**The v3.1 prompt changes did not split the passes.** Asker opening: 1 of the 133, inherited-style opening: 1. The narrowed `needs_ruling` shows in the flags (a flag by one pass only: 24 of 133) and coincides with a reading difference in 6 of the 40: 3 of them (26bb55, 2a5330, 2aea01) sit on the "the one who is asked or answers" / "narrated encounter" boundary (rule 6 against rule 11), the other 3 are variant remarks (3c440f, e8c24c) and a first-person narrative (a9947f). That boundary (with 881857 and cb56aa, 4-5 of 40) is the only v3.1-prompt effect I can see. Most of the fall is the validity rate (2.1 points), the tool's comparison (about 27% of differing pairs, 25-37 reports, 2.6-3.8 points of agreement would come back by folding epithets and titles) and route errors in Sunni texts that v3 had too.

## 6. The 35 `needs_ruling` agreed readings (both readers flagged)

All 35 read (`cases.md` section 5, `v_needs_ruling.txt`). One question each, so the owner can rule once:

| question | n | examples | what the agreed reading assumes |
|---|---|---|---|
| Two sayings (or a second saying, act or isnad) in one report: which is the report? | 14 | 520f51 «قال الزهري وأخبرني عروة، عن عائشة»; ee2483 «فسألت أبي ماذا قال ... فقال كلهم من قريش» | the first saying only |
| A narrated encounter where the Imam or source speaks, inside the narrator's story: last link? | 9 | a66588 «كنا يوما بين يدي علي بن موسى الرضا عليه السلام فقال»; bc2612 «قال يا ابن عمر إني سائلك ... قال نعم» | 8 stop at the narrator, 091ef3 writes the Imam. If the owner rules that whoever speaks in the story is the last link, up to 8 of the 9 need him added |
| A first-person narrative with an unnamed speaker or implicit transmission | 6 | fc183c «و سئل أبو إبراهيم ... قلت جعلت فداك»; f124f1 «قال محمد بن راشد و كنت دائم العلة» | the named link only |
| The Prophet speaks a one-sentence report with no transmitter | 3 | 05abba «لا صدقة و ذو رحم محتاج»; 7cf670 «كما روي عن النبي» | no chain |
| The author or title of a cited book, and a rescript from an Imam | 2 | 27423c «رجال الكشي: حكى بعض الثقات بنيسابور أنه خرج ... من أبي محمد عليه السلام توقيع»; 81867d «في كتاب (قرب الاسناد)» | the book is not a link (in 81867d the flag changes nothing) |
| A source known only by a title | 1 | 236b13 «سمعت منادي النبي صلى الله عليه وسلم يقول حى على الصلاة» | the unnamed Thaqafi man is last |
Flags that change no reading: 81867d, baf058 (a dash gloss and a second act), 1face9 (a trailing «و روي عن الصادق»): 3 of 35. The cases the owner already ruled that are flagged anyway: f124f1's opening («و شكا هشام ... إلى أبي الحسن الرضا») and 091ef3 (the Imam answers) are settled by the asker and answers rulings.

## 7. The 15 eligible "no chain by reading"

All 15 read (`cases.md` section 3): al-Faqih 5, Tusi's Ghayba 5, al-Khisal 2, Maani al-Akhbar 1, Bukhari 1, ... Right as "no isnad in this report": **13**; cannot tell: **2**; wrong: 0. The stored chain is junk in all 15 (the saying's words as links: «نفسك > من تعول إلى», «الناس معادن كمعادن الذهب»).
Right: no name before the saying («5763 - اليد العليا خير من اليد السفلى», «و في خبر آخر قال: «لا بأس بأن تدفع عن نفسك»»), the compiler's own argument in Tusi («فأما من خالف في موت أمير المؤمنين وذكر أنه حي باق فهو مكابر», «وأما وقت خروجه عليه السلام فليس بمعلوم لنا»), a statement of belief («26-15 والكبائر محرمة»), and three fragments whose isnad belongs to the report before (da93d0 «ثم أنطقه الله تعالى، فقال: يا محمد»; 8fa210 «فقصتها حفصة على النبي صلى الله عليه وسلم فقال»; 63e2ee «27-10 ونحن باب الغوث»): "no isnad here" is literally right under the rule (no personal name before the saying).
Cannot tell: **cf634a** «وقال صلى الله عليه وآله: لا تعضية في ميراث» (the Prophet as speaker with no transmitter: unruled, yet applied as no chain, while the same shape in al-Faqih is held by `needs_ruling` in 05abba, 1ec535); **2973ea** «5719 - و مع قوله عليه السلام: «الإسلام يعلو و لا يعلى عليه»» (an implicit speaker like «وقال عليه السلام»; no previous report supplied; the opener list of `empty_reading_unsettled_opening` has «وقال / وقضى» but not «و مع قوله»).

## 8. Wrong readings, classes, fixes, and what each proposed hold would also catch

7 wrong (and 6 undecided) of 201. The right readings caught are counted over the read sample (`proposed_holds.py`, `proposed_holds.json`); the holds were written after reading these cases, so the hit counts are in-sample.

| class | n | example (quote) | fix | proposed hold: tranche hits (of 732 eligible chain readings) / sample wrong caught / **sample right caught** |
|---|---|---|---|---|
| a `variant: true` group stored as a chain (a one- or three-link route for «بمثل حديث ...», a restated name, a partial «زاد في حديث ...») | 3 (30fa50, c93705, e3f7d5) | 30fa50 «قالت عائشة أرق رسول الله ... بمثل حديث سليمان بن بلال» gives a route `سليمان بن بلال`; c93705 «قال ابن المثنى حدثنا مغيرة بن سلمة المخزومي، وأبو هشام حدثنا وهيب» gives `ابن المثنى > مغيرة ...`; e3f7d5 «زاد في حديث حفصة عن أم عطية» gives `حفصة > أم عطية` | prompt (a variant needs a line of transmission written in the text; a restated name is not one); the submission must not store `variant` groups (grep: `to_submission_v3_1.py` and `chain-fix-*.ts` do not mention it, so I believe variant routes are applied as chains: not run) | `variant_route_in_eligible_reading`: **24** / 3 of 3 / **0** (every variant reading in the read sample is wrong; 21 unread) |
| shared head dropped from a later route | 1 (6d7565) | «عن عبد الله،. قال وحدثني واصل، عن أبي وائل، عن عبد الله»: the third route starts at واصل, it should be مسدد > يحيى > سفيان > واصل ... | prompt example | route at most half as long as the longest (max length 4 or more): 2 / 1 of 1 / **0** |
| kunya and name of one man read as two routes | 1 (05c2d0) | «حدثني أبو الطاهر، أحمد بن عمرو بن سرح أخبرنا ابن وهب»: no «و» between them | prompt example (a name after a kunya and «،» is the same man) | two routes identical except the first link, written «X، Y» with no «و»: 1 / 1 of 1 / **0** |
| co-transmitters of one man grouped after «؛» with the shared tail dropped (al-Faqih) | 1 (eb2b15) | «عن سعد بن عبد الله، عن، محمد بن عيسى بن عبيد؛ و يعقوب بن يزيد، عن زياد بن مروان القندي»: both passes read `... > محمد بن عيسى` and `يعقوب > زياد` | prompt example (the v3.1 `routes_end` exemption lets it through: no end name stands inside another route) | «؛» in the isnad of a multi-route reading: 1 / 1 of 1 / **0**. Do not reinstate `routes_end` without the exemption: 19 hits, 5 in the sample, 1 wrong and **4 right** |
| the one asked answers and relays, and is omitted | 1 (0706da) | «قال قلت لعطاء كيف تقول أنت في الركوع قال أما سبحانك ... فأخبرني ابن أبي مليكة عن عائشة»: the reading goes `ابن جريج > ابن أبي مليكة` | prompt example (rule 6: the asked person who then says «فأخبرني») | none: a regex on «قلت لـX» hit 12 tranche readings, 1 wrong, 11 unrelated; not holdable |
| undecided: first-person «سألته» or «أنه قال» with no named Imam (07d717 «و قال الحلبي : و سألته», f14c39 «و- في رواية جميل أنه قال») | 2 `CT` | reading is a single narrator link | prompt (rule 11 first-person) | Imami reading whose only link is a narrator: 2 / 2 `CT` / **0** |
| undecided: inherited Imam five reports back (b36519); implicit speaker opener «و مع قوله عليه السلام» (2973ea); Q4 encounter written with the Imam (a20cb6); Prophet no-transmitter applied as no chain (cf634a) | 4 `CT` | see section 4, 7, 3 | gap greater than 3: 1 hit; add «و مع قوله» to the opener list; owner rules Q4 and the Prophet case | gap greater than 3: 1 / 1 `CT` / **0** |
Combined (the four holds of rows 1-4): 28 of 732 eligible chain readings (3.8%); in the read sample they catch 6 of the 7 wrong and 0 of the 182 right chain readings (193 chain readings read: 7 wrong, 4 undecided). Without them the Sunni rate is 94.2%; with them, 98.0% weighted on what is left (in-sample).
Not caught by any hold I could build: 0706da.

## 9. Verdict per group

| group | verdict | why |
|---|---|---|
| Sunni six books | **apply with a named hold**: any eligible reading with a `variant: true` group (24 of 747 eligible), plus the two narrow route-shape holds in section 8 | 98/104 = 94.2% (88.0-97.3) as it stands, 0 breaks (0-3.6%), stored right 23%; 3 of the 6 wrong are variant groups the submission would store, the other 3 are one-offs; 6/104 against 0/85 in batch 001 is a real change (p = 0.033) |
| al-Faqih | **apply with named holds**: «؛» in a multi-route isnad; Imami readings whose only link is a narrator (07d717, f14c39); inherited Imam more than 3 reports back (b36519); add «و مع قوله» to the empty-reading openers | 52/57 = 91.2% (81.1-96.2), 1 wrong, 4 undecided (all four are in the three holds), stored right 0/57; the asker and opener rules work (section 4); the 5 "no chain" readings are right 4 of 5 |
| other Imami (without al-Kafi) | **apply** (the Q4 encounters stay held by the readers' own flags; a20cb6 is the one that slipped through with one flag) | 38/40 = 95.0% (83.5-98.6), 0 wrong, 2 undecided; 40 of 101 eligible read |
The tranche as a whole sits under the 95% gate on my count (94.1%, borderline: the pre-drawn 100 alone are 95/100): the gate is met by the sample only if the variant-route hold is adopted first. I would not run `chain-fix-submit` for tranche 01 until the owner decides that and the rulings in section 6; nothing here broke a right chain.

## 10. What I could not judge

- The 546 unread eligible readings; the 93 unread differing reports; matn past the first 90-330 letters (only scanned for later isnads); names against any lexicon (no «who is X»).
- The five unruled categories keep their `CT`: a20cb6 (Q4), cf634a (Prophet, no transmitter), 07d717 and f14c39 (first person), b36519 (inherited from five reports back), 2973ea (implicit speaker).
- c1d4c5 and fb4b56 (differing reports) have no pass I could call right; 306ccd, 2a5330, 881857 turn on Q3 / Q4.
- Whether the pipeline really stores `variant` groups as chains: grep only, not run.
- Sensitivity: counting the 3 relation-prefix stored chains (8e4c03 and 9550b7 «عن أخيه علي», 856447 «عن أخيه، عباد بن أبي سعيد») as defective lowers weighted stored right from 20.2% by about 1.4 points and raises fixes by the same.
- My verdicts are one model's, not blind, and the extension of the sample was drawn by me (seed 20261301); the 100 pre-drawn are the given random sample.

## Files

`sample_verdicts.tsv` (201 read readings and the 15 "no chain" readings: id, group, work, source base/extension, applies, reader, stored, stored kind, class, quote), `cases.md` (wrong and undecided, both right, the no-chain readings, the 40 disagreements, the 35 holds grouped), `asker_inherited.tsv` (45 readings, type, gap, verdict), hand verdict files `v_sunni.txt v_faqih.txt v_other.txt v_nochain.txt v_inherited5.txt v_dis40.txt v_needs_ruling.txt`, `numbers_t1.json` / `proposed_holds.json` / `dis_population.json`, `draw_extension.json` (seed 20261301).
Scripts (run from this directory with `python -X utf8 <script>`; read-only on everything above `analysis/`): `common_t1.py`, `draw_extension.py`, `dump_t1.py`, `prev_t1.py`, `build_tables.py` (writes `sample_verdicts.tsv`), `numbers_t1.py` (tables and intervals), `later_isnad_scan.py`, `find_asker_inherited.py`, `inherited_distance.py`, `asker_inherited.py`, `dis_t1.py` (the 40), `dis_population.py` (the 133), `nr_t1.py` (the 35), `proposed_holds.py`, `build_cases_t1.py`.
