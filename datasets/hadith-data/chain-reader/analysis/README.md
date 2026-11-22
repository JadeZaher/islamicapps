---
type: analysis
---
# Pilot judged by reading: is the shared reading of two Haiku passes right?

Question: when run A and run B agree with each other and validate, how often is their shared reading right? Nothing here runs a model or
writes outside `analysis/`. Every verdict is mine, from reading the Arabic (single reader, no second human); each has a quote in
`cases.md` / `agreed_set.tsv`. Persons are not identified; each tradition is read in its own conventions.

## 1. The split (agreed set = both passes validate after offset repair and give the same set of routes)

| | reports |
|---|---|
| both validate and agree exactly | **223 / 284 = 79% (73-83)** |
| both validate, routes differ | 17 |
| an output fails validation | 44 (A 29, B 24, both 9) |

Labelled stored chains in the 223 (one report can hold several): **(a)** correct, reader matches stored **98**; **(b)** correct, reader differs **57**;
**(c)** defective, reader differs **71 items / 70 reports**; **(d)** defective, reader reproduces the stored chain **5**. Report mixes: a-only 92, b-only 55, c-only 67, d-only 2, a+d 3, a+c 2, a+b 1, b+c 1.

Validator reasons (outputs affected, repaired offsets): run A in_matn 25, matn_start 3, shared_tail 1; run B surface_mismatch 12, in_matn 9, overlap 6, order 3,
matn_start 2, shared_tail 1. In_matn/matn_start are the reader miscounting where the saying starts (not a wrong reading); B's surface_mismatch is a diacritic
copied wrongly on vocalised Imami text. **If offsets are ignored** (surfaces only) the passes agree on **259 / 284 = 91% (87-94)**; Of the 36 reports gained that way I read 12 at random (6.1).

## 2. What I read

| set | read | not read |
|---|---|---|
| (b) | all 57 | - |
| (d) | all 5 | - |
| (c) | random 40 of 69 (seed 20261122) | 29 |
| (a) | all 92 + 6 mixed = all 98 | - |
| disagreements (offsets ignored) | all 25 (17 valid + 8 with an invalid output) | - |
| invalid but surfaces agree | 12 random of 36 | 24 |

So 194 of the 223 agreed reports are read; the 29 unread are class (c) (labelled defective, reader differs) and are not counted anywhere except in the
"estimated" column, where they get the right-rate of the 40 read (29/40).

## 3. Results

**Class outcomes (verdict counts, reports):** (b) 57: right 23 (13 of these only because score.py throws away a stored name that is written with an attached «و», see 4), representation-only 24,
label wrong 2, reader wrong 8. (d) 5: right 3, wrong 2. (c) 40 read: right 28, representation-only 1, wrong 11. (a) 98: right 91, wrong 4, cannot tell 3.
**The 60% "correct reproduced exactly" is mostly representation and a scorer artifact**: with a substring test instead of whole-word for "stored name is in the text", 104/172 becomes 120/172 (70%); the (b) group is 49/57 right or representation-only.

**Decisive number.** Agreed reading right (right + representation-only + label-wrong; `cannot_tell` counted as not right):

| group | reports | agreed (yield, valid + exact) | yield ignoring offsets | agreed read | **right among read** (Wilson 95%) | right if the unread (c) are imputed | wrong or undecided |
|---|---|---|---|---|---|---|---|
| ALL | 284 | 223 = 79% (73-83) | 259 = 91% (87-94) | 194 | **168/194 = 87% (81-91)** | 189/223 = 85% (79-89) | 26 |
| Sunni | 136 | 116 = 85% (78-90) | 125 = 92% (86-95) | 100 | 86/100 = 86% (78-91) | 98/116 = 84% (77-90) | 14 |
| &nbsp; Sunni six-book | 117 | 98 = 84% (76-89) | 107 = 91% (85-95) | 83 | 71/83 = 86% (76-92) | 81/98 = 83% (74-89) | 12 |
| &nbsp; Pure Canon (Ahmad, Darimi, Muwatta) | 19 | 18 = 95% (75-99) | 18 | 17 | 15/17 = 88% (66-97) | 16/18 = 89% (67-97) | 2 (both cannot tell) |
| Imami | 133 | 93 = 70% (62-77) | 120 = 90% (84-94) | 81 | 72/81 = 89% (80-94) | 81/93 = 87% (79-92) | 9 |
| &nbsp; al-Kafi | 28 | 13 = 46% (30-64) | 24 = 86% (69-94) | 7 | 7/7 = 100% (65-100) | 11/13 = 85% (58-96) | 0 |
| &nbsp; al-Faqih | 20 | 13 = 65% (43-82) | 18 = 90% (70-97) | 10 | 10/10 = 100% (72-100) | 12/13 = 92% (67-99) | 0 |
| &nbsp; other Imami | 85 | 67 = 79% (69-86) | 78 = 92% (84-96) | 64 | 55/64 = 86% (75-92) | 57/67 = 85% (75-92) | 9 |
| al-Rabi' | 10 | 9 = 90% (60-98) | 9 | 8 | 5/8 = 62% (31-86) | 6/9 = 67% (35-88) | 3 |
| Zayd | 5 | 5 = 100% (57-100) | 5 | 5 | 5/5 = 100% (57-100) | 5/5 = 100% (57-100) | 0 |

(al-Kafi's low strict yield is the validator: 13 of its 28 have an output that fails on offsets. 12 reports agreed only after ignoring offsets were read: 8 right, 3 representation-only, 1 cannot tell.)

**Agreement is informative.** On the 25 reports where the passes differ I could say: both right 6 (surface scope), exactly one right 11 (A 9, B 2), neither right 6, cannot tell 2.
So a pass is right on 8-15 of 25 (32-60%) when they disagree, against 87% when they agree.

**The population matters.** The pilot is 37% defective; the live archive is about 10%. Reader error splits by what the stored chain was:

| | stored chain labelled correct: reader wrong | stored chain labelled defective: reader wrong |
|---|---|---|
| ALL | 12/148 = 8% (5-14) | 14/46 = 30% (19-45) |
| Sunni | 4/70 = 6% (2-14) | 10/30 = 33% (19-51) |
| Imami | 6/68 = 9% (4-18) | 3/13 = 23% (8-50) |

Putting that on the stored defect rates you gave (reader error among agreed readings = p*e_def + (1-p)*e_cor; range from the Wilson bounds of the two terms):

| tradition | stored defect rate (out of sample, checked by rule) | reader error at that mix | verdict |
|---|---|---|---|
| Sunni | 8.3% | 8.0% (3.7-16.9) | **not shown either way** |
| Sunni six-book | 10.6% | 7.1% (3.2-16.8) | not shown (point estimate lower) |
| Imami, v1 prompt as is | 4.0% | **9.4% (4.3-19.2)** | **worse** (interval 4.3-19.2 barely excludes 4.0) |
| Imami, with the back-reference gate (7 below; chosen after seeing the errors, so in-sample) | 4.0% | 0.8% (0.2-8.6) | not shown either way |
| al-Kafi | 0 of 70 | reader 0/3 wrong where stored correct, 0/4 where defective | not shown; stored cannot be beaten at 0 |
| al-Faqih | 20% | 0% (0-39) from 10 reports (+4 of 4 right among the invalid-but-agree) | point estimate better, **not shown** |
| al-Rabi' | 5.0% | 40% (11-77), n=8; all three errors are the «بلغني» convention | **worse as the prompt stands**, n too small |
| Pure Canon | no figure (stored = the source's own field) | 2 undecided of 17 | not shown |
| Zayd | no figure | 0/5 wrong | not shown (5 correct chains; no defective one) |

Two agreeing Haiku readings are therefore **not shown better** than the stored chains anywhere; they are **worse for Imami as the prompt stands** (the inherited-chain reports) and
**worse for al-Rabi'** (one missing convention); the only place a better-than-stored result looks plausible is al-Faqih, on 10-14 reports.
Expected yield and error if auto-applied to this pilot with the v1 prompt: 79% of reports get a reading (91% with offsets ignored); about 15% of those readings are wrong
or undecided (26 read + about 8 expected among the unread 29), i.e. about 12% of all reports would be written wrong. At the live 10% mix: 10.3% reader error among agreed readings, 7.1% with the gate; stored is about 10%.

## 4. Why "correct chains reproduced" is 60% and what is behind it

Of the 57 reports where a labelled-correct stored chain was not reproduced:
- 13 **scorer artifact**: the stored name is written «وأحمد بن عبدة» (و attached) and `stored_route` drops it as "not in text" (`score.py:52` uses `surface_in_text` on whole words), so the reduced stored route lacks a name the reader rightly has. Example cr-0001: text «حدثنا عبيد الله بن عمر القواريري، وأحمد بن عبدة»; reader has both routes.
- 24 **representation only**: glosses the stored surface keeps (cr-0022 «علي هو ابن مسهر»), honorifics (cr-0200 «الرضا ع»), connective «وعن» (cr-0043), relation words (cr-0203 «جده يعلى بن مرة» vs «يعلى بن مرة»), orthography «عبدالله», a back_reference link `score.py` drops (cr-0151, cr-0168), noise words in the stored surface (cr-0267 «محمد بن علي من»).
- 10 **reader adds a link the text names and the stored chain lacks**: Imam named after the chain as source (cr-0273 «قلت لأبي عبد الله», cr-0176 «قال أبو الحسن الأول ع»; the owner ruling), «سمعت X» (cr-0167), Companion who addresses them (cr-0283). Right by the prompt's rule 2/5 and the ruling.
- 2 **label wrong**: cr-0163 stored skips «أبو عبد الله محمد بن إبراهيم …النعماني الكاتب» that the text writes between two names; cr-0234 stored joins the two isnads across «؛».
- 8 **reader wrong**: inherited chain 5 (cr-0008, 0126, 0164, 0193, 0201), «بلغني» 2 (cr-0013, 0039), appended second isnad 1 (cr-0266).

## 5. Error taxonomy

**5a. Both passes agree and the reading is wrong or undecided (26 of the 194 read)**

| class | n | examples (text; reading) | fix |
|---|---|---|---|
| inherited chain: text opens «وبهذا الإسناد» / «بهذا الإسناد» and the stored chain is completed from the previous report | 6 | cr-0126 «15 - وبهذا الاسناد، قال: قال الصادق جعفر بن محمد»: reader «الصادق جعفر بن محمد», stored six names, applying it replaces six links by one. cr-0193 «330 - بهذا الإسناد عن النبي صلى الله عليه وآله»: reader no name, stored eleven | (ii) previous report, or (iii) gate: never apply a reading to a text that opens with a back reference |
| second isnad after the matn, or right after the first with no matn between (prompt rule 9 excludes it) | 5 | cr-0213 «قال محمد بن رافع وأخبرنا محمد بن بشر أخبرنا علي بن نزار عن نزار عن عكرمة»: reader gives only the first route. cr-0108 «وحدثنا آدم حدثنا شعبة حدثنا أبو إسحاق الهمداني عن البراء»: lies before the saying, still dropped | (i) prompt rule 9 and the validator's no-link-after-matn_start check |
| unnamed gap not written: «بلغني», «بإسناده يرفعه إلى», «أخبرني من سمع رسول الله» | 5 | cr-0013 «قال: بلغني عن أبي هريرة»: reader «أبو عبيدة > جابر بن زيد > أبي هريرة», stored has «بلغني» as an anonymous link. cr-0102 «فقال أخبرني من سمع رسول الله»: reader «أحمد > سليم > مطير» | (i) rule + examples |
| source or Imam named in the story omitted (rule 2) | 4 | cr-0258 «أتوا حذيفة … فقال: سمعت رسول الله (ص) يقول»: reader ends at بلال بن يحيى. cr-0255 «كنت أنا و يونس بن ظبيان … جلوسا عند أبي عبد الله (ع)»: reader ends at الحسين بن ثوير (the passes add the Imam in other reports: inconsistent) | (i) |
| subject of the event or source of the saying? | 3 cannot tell | cr-0237 «أن عمر بن الخطاب، رأى حلة سيراء عند باب المسجد». cr-0015 «أن عبد الله ابن عمر كان لا يقرأ في الصلاة على الجنازة» (reader omits; cr-0051 adds a named speaker) | owner policy, then (i) |
| narrative-embedded chain misread | 2 | cr-0010 «حدثني نبيه بن وهب، أن عمر بن عبيد الله … فنهاه أبان بن عثمان … وحدث عن عثمان بن عفان»: reader stops at نبيه, worse than stored. cr-0090 «قال سأل شباك إبراهيم فحدثنا عن علقمة»: rule 5 over-applied, شباك made a transmitter | (i) examples |
| many ح groups with shared tails | 1 | cr-0141 five ح groups, «جميعا عن أبي معشر»: reader drops أبي معشر from route one and splits «عبدة بن سليمان … ابن أبي عروبة» | (iv) not fixable by a reader; structured output helps |

**5b. The two passes disagree (all 25 read)**

| class | n | examples (both readings) | right | fix |
|---|---|---|---|---|
| relation word kept as its own link (one run does, the other not) | 4 | cr-0049 «عن علي بن جعفر عن أخيه أبي الحسن»: A «أبي الحسن», B «أخيه > أبي الحسن». cr-0029 «عن عمه محمد بن أبي القاسم»: A name alone, B «عمه > محمد بن أبي القاسم» | A in all 4 | (i) and (iii): drop a relation link directly before a named link |
| surface scope (nisba, mawla phrase, title, which of two mentions of one man) | 7 | cr-0160 A «عيسى بن حماد», B «عيسى بن حماد المصري». cr-0101 A «حبيب», B «حبيب مولى عروة» | both right in 6, undecided 1 | (iii) fold: name equals name if one is a contiguous word run of the other |
| Imam / source named in text (owner ruling, rule 5) | 3 | cr-0069 «وصفت لأبي عبد الله رجلا»: A adds the Imam, B ends at حمران بن أعين. cr-0146 «رأى سالم ابن عبد الله»: A adds, B keeps the field | A in 3 | (i) |
| shared tail after ح / «قالا» | 3 | cr-0170 «حدثنا محمد بن جعفر، ح وحدثنيه يحيى بن حبيب … قالا حدثنا شعبة»: A gives شعبة to the first two routes, B not. cr-0157: B continues the first route to «معاوية بن عمار», A ends it at «ابن أبي عمير» | A 1, B 2 | (i) and (iii) |
| route explosion truncated or Imams chained | 2 | cr-0059 18 routes: A all 18, B stops after 6. cr-0075 «عن أبي جعفر و أبي عبد الله (ع) قالا»: A chains the Imams in sequence, B writes them as parallel but only five of eight routes | A 1, neither 1 | (iii) levels output, tool expands |
| nested ';' and «جميعا» multi-isnads, concatenated reports | 5 | cr-0187 «حدثني إياس بن الحارث بن المعيقيب، وجده، من قبل أمه أبو ذباب عن جده»: A «إياس > وجده > أبو ذباب > جده», B «… > جده > أبو ذباب > جده», both a sequence where the text has two parallel narrators. cr-0065: first isnad of 12 combinations mostly lost by both | neither in 5 | (iv) |
| title as a first link | 1 | cr-0137 «الإمام عن أبي غانم الخراساني»: A has «الإمام», B starts at «أبي غانم» | cannot tell | (i) after a ruling |

Co-transmitter expansion is **not** a disagreement source: the set of consecutive teacher-to-student pairs plus route ends is equal on 259 reports, the same 259 as the route-set rule. What differs is substance and surface scope.

## 6. Recommendations, in order

1. **Drop offsets from the reader output, and compute them by tool.** Validity as given is 72%; the 29 failures of A are all `in_matn`/`matn_start` (the reader miscounting where the matn starts), B's 12 are diacritics copied wrongly. Ask for surfaces only; the tool finds each on the folded text (`norm.fold_exact`) and sets `matn_start` after the last link. This lifts agreement from 223 to 259 (79% to 91%); of the 12 I read at random from the 36 gained, 8 right and 3 representation-only, 1 undecided (cr-0139), 0 wrong. Remove the "no link may lie at or after matn_start" rule or it contradicts prompt rule 2 (a Companion named inside the story is a link).
2. **Gate on a back-reference opening** (text begins, after the number, with «وبهذا الإسناد», «بهذا الإسناد», «وبالإسناد الأول», «عنه», «وعن»): never auto-apply; hand it the previous report's chain (ii) and ask only for the links this text adds. In the pilot it holds back 20 of the 223 agreed reports (19 read: 12 right or representation-only, 7 wrong: the 6 inherited-chain cases and cr-0258). Without it Imami agreed readings are 89% right with 9% regressions on correct chains; with it 97% (89-99) and 0/52 regressions (0-7%). In-sample: gate chosen after the errors were seen; re-test on fresh reports.
3. **Prompt rules, largest first**: (a) second isnads are routes (after the matn, or after «.» before «نحوه / مثله»): 5 agreed-wrong and 3 stored-label defects; (b) «بلغني», «بإسناده يرفعه إلى», «أخبرني من سمع», «عمن ذكره» = an `unnamed` link (5; all of al-Rabi's 3); (c) the Imam named after the chain, a speaker of the saying, «سمعت / قلت لـ / كنا عند X» = last link, with two worked examples (4 wrong + 2 disagreements) and an owner policy for "subject of the event" (3 undecided); (d) «عمه / أخيه / أبيه + name» = one link, the name alone; bare «أبيه» alone = a `relation` link (4 disagreements); (e) say that «سأل X Y» (rule 5) does not make an asker a transmitter when the report is Y's (cr-0090). Do not put the compiler convention in the prompt: the reader cannot know the work; prepend the compiler by work in post-processing (iii). (cr-0197 shows the reader naming him when the text does, which the owner ruling wants.)
4. **Levels instead of route lists** for reports with many co-transmitters: `links` as ordered levels of alternatives (`[[A,B],[C],[D,E]]`) plus the shared-tail start; the tool expands to routes. It removes truncation (cr-0059, cr-0075 B) and lets the agreement test run on levels. Keep route lists for the output stored.
5. **Agreement rule: exact route-set after tool folds**, not edge-set. The edge-set rule (pairs plus route ends) equals the route-set rule on this pilot (259 and 259), so it buys nothing. Fold names (strip leading «و», honorifics, a title, a relation link before a named link, a mawla / nisba phrase as a contiguous word run) before comparing: +7 agreements (266/284 = 94%), of which 5 both right, 1 undecided, 1 both wrong (cr-0187: both read two parallel narrators as a sequence). So loosening the rule costs about one wrong pair in seven; keep exact for auto-apply and use the folded rule to size the review queue.
6. **Further deterministic holds before applying** (each seen in the pilot): reading drops a stored name that is present in the text (cr-0010 loses عثمان بن عفان); reading has no link while the stored chain has; more than 8 routes; a second-isnad marker after the matn («وحدثنيه», «ح», «رواه»); nested «جميعا» at two levels.
7. **Do not auto-apply yet:** al-Rabi' (convention missing, n=10); Pure Canon (the stored chain is the source's field; the reader adds a matn-named source in cr-0051 and cr-0140 and omits one in cr-0015 and cr-0027, and the two passes split on cr-0146: owner policy first); al-Kafi (stored out-of-sample defect 0 of 70, reader evidence 7 reports, nothing to gain); every back-reference opening in any work; Sunni reports with a second isnad (Muslim, Bukhari, Tirmidhi: 5 of the 11 Sunni wrong readings) and multi-«ح» reports with shared tails; anything with an invalid output or no agreement. **Candidates for a first limited run** (after a fresh labelled sample of 100+ per work, because 10 reports cannot show 20% vs 0%): al-Faqih and the non-inherited other Imami works, then Sunni six-book once rules 3a and 3c are in.

## 7. What I could not judge

- The 29 agreed class-(c) reports outside my random 40, and 24 of the 36 invalid-but-agree reports.
- Whether a person named only as the subject of an event is a link (cr-0237, 0015, 0027), the title «الإمام» (cr-0137), the placement of «عن أم مبشر» (cr-0139): need an owner ruling.
- Nested «جميعا» / «؛» structures (cr-0032, 0065, 0143, 0219): the correct nesting is not decidable from the punctuation.
- The pilot's stored chains are mostly rule-built, uncertain or defective-labelled; the live target (uncertain chains) is a different population: the table above compares with the checked-by-rule defect rates you gave, not with the uncertain set.
- Single reader of Arabic (a model, not a scholar); no second human check; my verdicts on judgement items are marked `cannot_tell` rather than forced.

## Files

`agreed_set.tsv` (all 284 reports: state, classes a-d, verdict, tag, fix, quote; for the 87 plain matches the quote is the first 70 characters of the text, the reader's routes equal the stored chains),
`cases.md` (every read case with text quote, stored chain, reader routes, reason), `verdicts.py` and `disagreement_verdicts.py` (the hand verdicts, source of both),
`classify.py` (agreement and the a-d split), `pick_cases.py` (seeded selection and dump), `numbers.py` (intervals, tables, `numbers.json`), `edge_agreement.py` (agreement under weaker rules, `edge_agreement.json`),
`build_cases.py` (writes `cases.md`). Run from `chain-reader/`: `classify.py`, `pick_cases.py none`, `numbers.py`, `edge_agreement.py`, `build_cases.py`.
