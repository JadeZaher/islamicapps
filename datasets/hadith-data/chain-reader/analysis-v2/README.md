---
type: analysis
---
# Pilot 2 (prompt v2 + source context) judged by reading, beside pilot 1

Same method as `../analysis/`: I read the Arabic against the agreed reading (single reader, no second human); persons are not identified; every verdict has a quote
in `cases.md` / `agreed_set.tsv`. Nothing was run (no model, no database write); nothing outside `analysis-v2/` was written (`context/` is imported read-only).
Scored set = the scorer's **279 reports** (cr-0029, 0090, 0138, 0237, 0258 are quoted in the v2 prompt and are left out). **v1 numbers below are recomputed on the same 279.**

## 1. Agreed set after expansion, and the holds

| | reports |
|---|---|
| valid output: A 266/279 = 95%, B 264/279 = 95% | both valid 260 |
| **both valid and `expand.canonical()` equal (agreed)** | **223 / 279 = 80% (75-84)** |
| both valid, readings differ | 37 |
| an output invalid | 19 (28 outputs: `surface_not_in_text` 20, `occurrence` 5, `order` 3) |

The scorer's 232/259 uses v1's comparison with `imam_in_text` dropped; with `canonical()` (Imam kept) it is 223/260. **27 of the 28 invalid outputs are a spelling problem the tool could fold**
(text «على» / Persian «ی» / «أبي» for «أبو» or the reverse, «و بهذا» with a space, a wrong `occurrence`); the 28th is a name the reader completed beyond the text (cr-0141 «هشيم بن بشير»).

Labelled stored chains in the agreed set: **(a)** 104, **(b)** 48, **(c)** 76 chains (70 reports), **(d)** 2. Reports: a-only 100, b-only 46, c-only 70, d-only 2, a+c 3, b+c 1, a+b 1.

**Reading effort.** I read in this pass 81 agreed reports (all of (b) and (d) that are not identical to v1, all of (c) that are not identical to v1, every report with an inherited link) and the 30 random
disagreements (seed 20261123, of 56). The other **142** agreed reports have non-derived routes equal to the agreed reading I read in v1 and no inherited link: their v1 verdict is carried (`carry.py`).
So every agreed report has a read verdict, none is imputed (v1 had 29 unread (c) reports; v2 has none).

**Holds** (`holds.py` on both outputs, plus the readers' `needs_ruling`; `cannot_read_without_previous_report` is a hold by itself). Right = right + representation-only + label-wrong; the 4 reports both readers declined
(cr-0052, 0153, 0201, 0235) are abstentions, kept in the agreed count and out of the right-rates.

| stage | reports | share of 279 | right (Wilson 95%) | wrong or undecided |
|---|---|---|---|---|
| agreed, before holds | 223 | 80% (75-84) | **206/219 = 94% (90-96)** | 13 |
| after the tool's holds | 189 | 68% (62-73) | 180/189 = 95% (91-97) | 9 |
| after tool holds + `needs_ruling` by **either** reader (default below) | 174 | **62% (57-68)** | **167/174 = 96% (92-98)** | 7 |
| tool holds + `needs_ruling` by **both** | 184 | 66% (60-71) | 176/184 = 96% (92-98) | 8 |
| tool holds + `needs_ruling` by A only (what the scorer's hold file uses) | 180 | 65% | 172/180 = 96% (91-98) | 8 |

Wrong or undecided before holds (13): cr-0008, 0027, 0033, 0133, 0136, 0143, 0144, 0157, 0177, 0183, 0193, 0197, 0202.

## 2. v1 beside v2 (same 279 reports)

v1 "read" excludes the unread (c) reports, which biases that column up; "imputed" gives them the right-rate of the 40 I read (29/40). v1 "applied" = agreed and not gated by the back-reference opening (v1's only hold);
v2 "applied" = agreed and not held by tool holds or either reader's flag.

| group (reports) | agreed v1 | agreed v2 | right of agreed, v1 read / imputed | right of agreed, **v2** (all read) | applied v1: yield, right | applied v2: yield, right |
|---|---|---|---|---|---|---|
| ALL (279) | 219 = 78% (73-83) | 223 = 80% (75-84) | 168/190 = 88% (83-92) / 86% (81-90) | **206/219 = 94% (90-96)** | 172 = 62%, 156/172 = 91% (85-94) | 174 = 62% (57-68), **167/174 = 96% (92-98)** |
| Sunni (133) | 113 = 85% (78-90) | 109 = 82% (75-88) | 86/97 = 89% (81-94) / 87% (79-92) | 103/109 = 94% (89-97) | 97 = 73%, 86/97 = 89% | 95 = 71% (63-78), 92/95 = 97% (91-99) |
| six-book (114) | 95 = 83% (75-89) | 91 = 80% (72-86) | 71/80 = 89% (80-94) / 86% (78-92) | 86/91 = 95% (88-98) | 80 = 70%, 71/80 = 89% | 78 = 68% (59-76), 76/78 = 97% (91-99) |
| Pure Canon (19) | 18 = 95% (75-99) | 18 = 95% (75-99) | 15/17 = 88% (66-97) | 17/18 = 94% (74-99) | 17 = 89%, 15/17 | 17 = 89% (69-97), 16/17 = 94% (73-99) |
| Imami (131) | 92 = 70% (62-77) | 101 = 77% (69-83) | 72/80 = 90% (81-95) / 88% (80-93) | 90/97 = 93% (86-96) | 62 = 47%, 60/62 = 97% (89-99) | 67 = 51% (43-60), 63/67 = 94% (86-98) |
| al-Kafi (28) | 13 = 46% (30-64) | 27 = 96% (82-99) | 7/7 / 85% (58-96) | 24/26 = 92% (76-98) | 7 = 25%, 7/7 | 16 = 57% (39-73), 15/16 = 94% (72-99) |
| al-Faqih (20) | 13 = 65% (43-82) | 18 = 90% (70-97) | 10/10 / 92% (67-99) | 18/18 = 100% (82-100) | 10 = 50%, 10/10 | 11 = 55% (34-74), 11/11 = 100% (74-100) |
| other Imami (83) | 66 = 80% (70-87) | 56 = 67% (57-77) | 55/63 = 87% (77-93) / 86% (76-93) | 48/53 = 91% (80-96) | 45 = 54%, 43/45 = 96% (85-99) | 40 = 48% (38-59), 37/40 = 92% (80-97) |
| al-Rabiʿ (10) | 9 = 90% (60-98) | 9 = 90% (60-98) | 5/8 = 62% (31-86) | 9/9 = 100% (70-100) | 8 = 80%, 5/8 | 8 = 80% (49-94), 8/8 = 100% (68-100) |
| Zayd (5) | 5 = 100% | 4 = 80% (38-96) | 5/5 | 4/4 = 100% (51-100) | 5 = 100%, 5/5 | 4 = 80%, 4/4 |

Agreement moved little overall (78% to 80%) but moved by work: al-Kafi 46% to 96% and al-Faqih 65% to 90% (the offset failures are gone), other Imami 80% to 67% (12 of the 19 reports with an invalid output are other-Imami
reports, Persian or vocalised Thaqalayn spelling, and `cannot_read` took 3).

## 3. Expected error if auto-applied, against the stored chains

Reader error among applied readings at the stored defect mix p: `p*e_def + (1-p)*e_cor` (e_cor = wrong where the stored chain was labelled correct, e_def = wrong where it was defective), range from the Wilson bounds.
**Net** = what the archive would hold after applying only agreed-and-not-held readings and leaving the rest as stored: `y*reader_error + (1-y)*p`.
Stored rates are yours (checked by rule, out of sample).

| tradition | stored | v1 reader error / net | **v2 reader error among applied** | **v2 net (range)** | verdict v2 | verdict v1 |
|---|---|---|---|---|---|---|
| Sunni | 8.3% | 5.3% / 5.7% | 3.1% (0.8-11.0) | **4.6% (3.0-10.2)** | not shown (point estimate better, upper bound 10.2 > 8.3) | not shown |
| Sunni six-book | 10.6% | 3.7% / 4.8% | 2.1% (0.4-11.1) | **4.8% (3.6-10.9)** | not shown (upper bound 10.9 is 0.3 above 10.6) | not shown |
| Imami | 4.0% | 8.1% / 6.9% ungated; 0.8% / 2.5% gated (post hoc) | 5.4% (1.8-15.2) | **4.7% (2.9-9.8)** | **not shown** (point estimate equal) | **worse** ungated |
| al-Kafi | 0 of 70 | 0% / 0% (n=3 correct, 4 defective) | 0% (0-22.8); 0/13 wrong where stored correct | 0.0% (0-13.0) | not shown (cannot beat 0; no regression seen) | not shown |
| al-Faqih | 20% | 0% / 7% (n=10) | 0% (0-38.1) | 9.0% (9.0-30.0) | not shown (point estimate better) | not shown |
| al-Rabiʿ | 5.0% | 39.7% / 36% | 0% (0-44.1), n=8 | 1.0% (1.0-36.3) | not shown (point estimate better) | **worse** |
| Pure Canon | no figure | 14% where stored correct | 1/14 wrong where stored correct, 0/3 defective | n/a | not shown | not shown |
| Zayd | no figure | 0/5 | 0/4 | n/a | not shown | not shown |

Plainly: **v2 is not worse than the stored chains anywhere it was measured, and it is not shown better anywhere**; the point estimates are better for Sunni, al-Faqih and al-Rabiʿ, equal for Imami and al-Kafi.
v2 repaired the two v1 "worse" cases (Imami inherited chains, al-Rabiʿ «بلغني»), but from 3 to 8 reports of the defective stratum per work cannot show it.
Before holds, overall: reader wrong where the stored chain is right 6/145 = 4% (2-9), where it is defective 7/74 = 9% (5-18) (v1: 6% and 29%).
The 40 agreed reports in the defective stratum that are not held are exactly where an auto-apply would fix something: they are 40 of 74.

## 4. What v2 fixed and what it broke (reports agreed in both pilots, verdict read in both)

| | count | reports |
|---|---|---|
| fixed (v1 wrong or undecided, v2 right) | **12** | cr-0015 (undecided in v1; settled by the ruling that a described action is not a link), cr-0013, 0039, 0079 «بلغني» as an unnamed link; cr-0048 «بإسناده يرفعه إلى»; cr-0102 «أخبرني من سمع»; cr-0108, 0117, 0213 second isnad as a group; cr-0053, 0255 speaker / Imam named in the text; cr-0126 inherited chain |
| same, right | 142 | |
| same, wrong | 3 | cr-0008, cr-0193 (inherited chain not taken although previous reports were supplied), cr-0027 (undecided) |
| broke, reader | **2** | cr-0133 (shared tail «سمعت أبا هريرة» dropped from route one), cr-0136 (the isnad of an appended poem written as a route) |
| broke, tool | 2 | cr-0183, cr-0197 (compiler head written twice, see 4.3) |
| now abstains by design | 3 | cr-0153, 0201, 0235 (`needs_previous_report`; v1 read them text-only: right, wrong, right) |

Changes in who agrees: **35 newly agreed** reports (30 right, 2 representation-only, 5 wrong: cr-0033, 0143, 0144, 0157, 0177) and **33 that lost agreement** (v1 agreed; v2 not): 14 right, 6 wrong,
7 unread, 4 representation-only, 2 label-wrong. Most losses are an invalid output or a surface spelling difference (cr-0233, 0006, 0151), not a changed reading.
22 reports that v1 left unread are now read: 20 right, 1 wrong (cr-0202), 1 abstention.

**4.1 Inherited chains.** 25 reports open with a back reference. 15 carried a previous report, 4 were flagged `needs_previous_report`, **6 arrived with none and no flag: cr-0019, 0084, 0121, 0143, 0164, 0168**
(and cr-0151 had a previous report with no names). The hold `back_reference_without_previous_report` fired on all six (checked on A or B) and `cannot_read_without_previous_report` on the four flagged:
the two readers answered `cannot_read` on all four, in agreement, so **no back-reference report without a previous report can be applied** (v1 gave a text-only reading to 6 such reports).
**Did the previous report help?** Where inheritance was needed and a chain was available, 2 of 4 agreed readings used it (cr-0126: six names written as `inherited`, quote «حدثنا الحسن بن إبراهيم بن ناتانه … عن عبد الله بن بكير»; cr-0194 «وعنه (ع)» takes «أبي عبد الله»),
2 did not: **cr-0193** (prev1 carries the chain «حدثنا محمد بن أحمد بن الحسين … علي …», the readers wrote only «بهذا الإسناد»; no hold fired) and **cr-0008** (prev1 and prev2 are «وبهذا الإسناد», the names stand in prev3; both readers ignored it; caught only by B's flag).
A cheap hold would catch both: a reading made only of back_reference links for a text that opens with a back reference (`back_reference_only_reading`).

**4.2 Imam / source in text.** 25 agreed readings contain an `imam_in_text` link: 22 right, 1 representation-only, 2 wrong only because of the doubled compiler head. In the agreed set it is **not over-applied**.
Over-application lives in the disagreements: cr-0264 «ونحن عند سعيد بن المسيب» (B adds سعيد as a link, A leaves him out and flags it; he is the place of hearing, so A is right and B wrong); cr-0147 (B adds «الصعب بن جثامة» to every route
from a remark about two versions); cr-0099 (A adds «أمير المؤمنين» after the relation links «أبيه > جده», possibly the same man twice). The rule is also under-applied once: **cr-0177** (عثمان speaks the saying; neither reader adds him, no flag).
cr-0138 (Abu Bakr inside al-Baraʾ's account) is in the excluded set; A added him, B did not.

**4.3 Compiler head duplicated.** `expand.py` skips the head only when the compiler's short name stands inside a surface. It misses the text's longer spellings: **cr-0183** («الحسين بن سعيد الأهوازي» head plus the text's «الحسين بن سعيد») and **cr-0197**
(«الصدوق» head plus «أبو جعفر محمد بن علي … ابن بابويه القمي»). Both readings are otherwise right; applied as expanded they would write the compiler twice. Fix in the tool (compare against the compiler's known aliases, or the first link of the chain). I score them wrong because the reading as applied is wrong.

**4.4 `needs_ruling`.** Set by A on 29 and by B on 21 of the valid outputs (both on 12; either on 38 reports). Among the **19 agreed reports where either flagged (6 both)**: I judge **9 real** ambiguities
(cr-0008, 0047, 0091, 0111, 0144, 0158, 0187, 0190, 0280) and **10 on settled cases** (the Imam who answers or is asked: cr-0060, 0069, 0134, 0095; a title inside the chain: 0122; an Imam after «عن»: 0192; an explainer who is not a link: 0026;
a variant wording: 0131; «ابنى محمد»: 0132; the answer that settles «من»: 0202). cr-0060 and 0069 were flagged by B only. The flags do not track the errors: **3 of the 13 agreed wrong readings were flagged** (cr-0008, 0144, 0202), 10 were not
(cr-0027, 0033, 0133, 0136, 0143, 0157, 0177, 0183, 0193, 0197); the wrong rate is 3/19 = 16% flagged against 10/200 = 5% unflagged.

**Which hold rule.** Over the 189 reports the tool's holds leave, each flag rule removes: **either** 15 (13 right, 2 wrong), **both** 5 (4 right, 1 wrong), **A only** 9 (8 right, 1 wrong). That is about 6.5 correct readings lost per wrong one caught for either, 4 for both.
"Readings differ" is not a rule for the agreed set (they do not differ); it is what disagreement already does.

**4.5 Second isnads and unnamed gaps.** Second isnad as a group: 3 v1-wrong reports fixed (cr-0108, 0117, 0213) and present in cr-0026, 0102, 0190, 0260; over-applied twice: cr-0136 (a poem's isnad «وأنشدني أبو الفرج البرقي الداودي قال: أنشدني شيخ») and, in a disagreement, cr-0220
(an informant inside a story). `unnamed` gaps: 5 v1-wrong reports fixed (the «بلغني» reports cr-0013, 0039, 0079; cr-0048; cr-0102) and present in cr-0195 and 0181 «أحدهما»; one over-application: cr-0202 (the unnamed «من» is named by the answer «ابن عباس»; both readers keep both).

## 5. What is still wrong

**5a. Agreed, not held, wrong or undecided (7 of 174):** 

| class | n | examples (text; reading) | fix |
|---|---|---|---|
| shared tail written once after a branch is left off a route | 2 | cr-0133 «ح وأنبأنا حميد بن مسعدة، عن سفيان بن حبيب، عن الأوزاعي، قال حدثنا أبو كثير، قال سمعت أبا هريرة»: route one ends «أبو كثير». cr-0157 «ومحمد بن إسماعيل … عن صفوان بن يحيى وابن أبي عمير عن معاوية بن عمار»: route one ends «ابن أبي عمير» | prompt wording (shared tail after the LAST «ح» belongs to every branch) + hold `divergent_route_ends` |
| speaker of the saying not added | 1 | cr-0177 «فقال إن رسول الله صلى الله عليه وسلم قال»: عثمان speaks; reading ends «هانئا، مولى عثمان»; no flag | prompt example |
| isnad of an appended poem/anecdote read as a route | 1 | cr-0136 «وأنشدني أبو الفرج البرقي الداودي قال: أنشدني شيخ كان منقطعا … ومنتظر للموت» | prompt: a second isnad counts only if it carries the same saying |
| inherited chain not taken though the previous report was supplied | 1 | cr-0193 | prompt: «if prev1 opens with the same words, read prev2, prev3»; hold `back_reference_only_reading` |
| compiler head written twice (tool) | 1 | cr-0183 | tool alias check |
| undecided: Ibn ʿUmar speaks a legal opinion inside a scene | 1 | cr-0027 «فقال عبد الله ابن عمر ليس لها صداق» | owner ruling (cr-0015, «كان لا يقرأ في الصلاة», is settled by the ruling that a described action is not a link) |

Held and wrong (6, caught): cr-0008 (flag B), 0033 (hold `drops_stored_name`; the reading adds a restated «الزهري > حميد» as a third route), 0143 (back reference, no previous report), 0144 (flags; both readers keep «المعتمر» and «معتمر بن سليمان» as two links),
0197 (hold fired on stored junk «هب ابن وهب»), 0202 (flags).

**Holds that fire on correct readings.** `drops_stored_name` fires on 23 agreed reports and 20 are right: the "dropped" stored name is a junk link in a defective stored chain («كسب النائحة», «محرم قتل ثعلبا», «تابع/», «أخرى»); 19 of those 20 stand in
labelled-defective chains, so the hold queues exactly the corrections the pipeline exists for. Restrict it to a stored name that stands in the chain region (before the reading's matn start) and is a plausible name (not a matn clause, no verb), or drop it.
`reading_empty_stored_has_links` (8) fires on 4 abstentions and 4 correct empty readings (cr-0064, 0149, 0171: no chain in the text).
`nested_jami` / `nested_semicolon` fired once, on a correct reading (cr-0210).

**5b. Disagreements, random 30 of 56** (all read; `cases.md` section C):

| class | n | examples (both readings) | right | fix |
|---|---|---|---|---|
| tool: surface not found (spelling of the text, case ending, spacing, wrong `occurrence`) | 9 | cr-0031 text «على بن محمد», both wrote «علي»: both invalid. cr-0070 B «أبو محمد» for the text's «أبي محمد». cr-0019 «و بهذا الإسناد» (space) | A in 3, B in 1, both (invalid) in 5 | tool: fold ى/ي/ی, kunya case, spaces; ignore an `occurrence` with one match |
| surface scope (nisba, «الكاتب», «العدل», attached «و», «بهذا الحديث») | 6 | cr-0163 A «…الشجاعي الكاتب», B «…الشجاعي». cr-0151 A «وبهذا الإسناد», B «بهذا الإسناد» | both in 5, A in 1 | tool: fold in `canonical()` |
| shared tail missed by one pass | 4 | cr-0011 A «مسدد > يحيى», B «مسدد > يحيى > عبيد الله > نافع > ابن عمر». cr-0100 B's first route stops at «عمرو بن الحارث» | B 2, A 1, partial 1 | prompt wording; hold `divergent_route_ends` |
| parallel pair misparsed | 3 | cr-0083 B puts «أبو علي الأشعري» at the head of the second route. cr-0208 A crosses «علي بن ابراهيم > محمد بن اسماعيل» | A 1, B 2 | prompt example for «A عن B و C عن D جميعا عن E» |
| speaker or Imam omitted by one pass | 2 | cr-0051 «أن علي ابن أبي طالب قال»: A adds, B not. cr-0084 «قال أمير المؤمنين عليه السلام: أنا الراعي» (held anyway) | A in 2 | prompt example |
| extra route from a remark, anecdote or variant | 2 | cr-0147 B adds «الصعب بن جثامة» to all routes. cr-0220 B adds «…الحميري > أبوعلي > ابا محمد» | A in 2 | prompt: variants and stories inside the report are not routes |
| comment isnad at the boundary of rule 4 | 1 | cr-0205 «وقد روى شيبان عن يحيى بن أبي كثير مثل هذا»: B writes a route, A not | B by rule 4 | prompt: say whether a partial route counts |
| narrative-embedded chain | 1 | cr-0010 A ends «نبيه > عثمان بن عفان», B inserts «أبان بن عثمان»; both omit «أن عمر بن عبيد الله» | B closer | not fixable cleanly |
| doubt between two readings | 1 | cr-0137 «مجاهد أو عمن حدثه عن مجاهد»: A two routes, B one | A | prompt: write both |
| nested isnads | 1 | cr-0032 | neither | not fixable by a reader |

Disagreement is now mostly tool and scope noise (15 of 30), which the tool can remove; 7 of the 30 are real tail or parsing differences.

## 6. Recommendation

Rule used: apply = agreed, valid, no tool hold, no `needs_ruling` from either reader (62% of reports). Evidence is thin per work; "now" means "first limited run, with a review sample", not the corpus.

| tradition / work | decision | reason (numbers above) |
|---|---|---|
| Sunni six-book: Bukhari, Muslim, Abu Dawud, Tirmidhi, Nasa'i, Ibn Majah | **auto-apply with a named extra hold**: `divergent_route_ends` and a second-isnad marker after the matn | applied 76/78 = 97% right; the two wrong are a dropped shared tail and an omitted speaker; stored 10.6%, v2 net 4.8% (3.6-10.9) |
| al-Faqih | **auto-apply with the same hold**, then re-measure | 18/18 right before holds, 11/11 applied; stored 20%; the sample is 20 reports |
| other Imami (Khisal, Amali, Tawhid, Maani, Kamal, Ghayba, Thawab, Fadail, Sifat, Mumin, Zuhd, Ziyarat, Uyun, Mujam) | **auto-apply only where the text does not open with a back reference and the previous report was used**; add `back_reference_only_reading` and the compiler-alias fix first | 37/40 applied; the three wrong are cr-0136, 0183, 0193; only 4 defective-stratum readings are applied, so the fixes are barely tested |
| al-Kafi | **not yet** | stored 0 of 70: nothing to gain, and 0/13 regressions is a bound of 0-23% |
| Pure Canon (Ahmad, al-Darimi, al-Muwatta) | **not yet** | the stored chain is the source's field; the reader adds matn-named speakers (cr-0051, 0140) and the passes split on cr-0146; the ruling "a described action is not a link" helps (cr-0015) but cr-0027 is open |
| al-Rabiʿ | **not yet** (n=9) | all the v1 errors (the «بلغني» gap) are fixed, which is the evidence that the prompt works; no defective report to prove it |
| Zayd | **not yet** (n=4) | fixed shape, nothing to correct |
| every report that opens with a back reference and has no usable previous report | **hold** (6 of 25 arrived without one) | holds already fire |

**Prompt wording still needed.**
1. Shared tail: «a name written once after the LAST «ح» (or after «قالا»/«جميعا») is the tail of every branch, including a branch that ended earlier; do not end a branch where the text stops repeating names» (cr-0133, 0157; 4 of the 30 disagreements).
2. A speaker named inside the report: add the example «فقال إن رسول الله ص قال» after a named person (cr-0177, 0051) and the counter-example «ونحن عند سعيد بن المسيب» (place of hearing; cr-0264).
3. A second isnad counts when it carries the SAME saying; an isnad of a poem, an anecdote or a variant remark does not (cr-0136, 0220, 0147); say how a partial remark «وقد روى شيبان عن …» is treated (cr-0205, 0280).
4. Previous reports: «if prev1 begins with the same back reference, continue to prev2 and prev3 until names appear; write them as inherited» (cr-0008, 0193).
5. The same man written twice in a chain is one link (cr-0144, 0085); «من» identified by the answer «ابن عباس» is one link (cr-0202).
6. `needs_ruling`: not for the Imam who is asked or who answers, not for a title inside the chain, not for a variant wording (10 of 19 agreed flags).

**Tool changes.** Fold ى/ي/ی, kunya case (أبو/أبي/أبا), spaces and a stray `occurrence` before declaring a surface missing (27 of 28 invalid outputs); compiler alias check (cr-0183, 0197); `canonical()` folds nisba/«الكاتب»/attached «و»/«بهذا الحديث» (11 of 30 disagreements);
restrict or drop `drops_stored_name`; add `divergent_route_ends` (fires on 11 agreed reports: 4 wrong, 7 right; 5 of them are not already held, containing 3 of the 4 wrong) and `back_reference_only_reading` (cr-0008, 0193).

**Flags: either, both or readings differ.** Use **neither as a hold by itself**: the flags catch 3 of 13 wrong readings and queue 16 right ones; "either" costs 13 right readings for 2 wrong (6.5:1), "both" 4 for 1. If one must be chosen, "both" (4:1)
and send A-only/B-only flags to the review sample. Readings that differ are never applied.

**Fresh labelled sample before the corpus run.** Draw at random from the live population, not enriched for defects, then keep only what is applied (agreed and not held). To show a reader error at the work's stored mix below 5% with a Wilson upper bound
needs **n = 73 applied readings with no error, 110 with one, 142 with two, 173 with three** (3%: 125 / 185 / 239 / 290). Sunni six-book works need about 150 applied reports per work to separate 5% from the stored 10.6%; al-Faqih, al-Kafi and the largest Imami works 150 each
(at a 62% apply rate that is about 240 drawn per work); smaller works 100. Label them by two readers, with the previous report in the packet, and keep the back-reference reports as their own stratum. The post hoc holds (`divergent_route_ends`, `back_reference_only_reading`) must be tested on this sample, not on this pilot.

## 7. What I could not judge

- 142 agreed reports carry their v1 verdict (identical routes, read in v1); cr-0015 was re-judged under the new ruling.
- The 26 non-agreed reports outside my 30; the outputs that are invalid are judged only through the other pass.
- Speaker or subject where the text does not settle it: cr-0027 stays `cannot_tell`; cr-0099 (a relation link and a named Imam that may be one man) and cr-0137 (a doubt between two readings) were not decided.
- Nested «؛» and «جميعا» structures (cr-0032, 0065) and the embedded chain of cr-0010.
- Stored-defect rates per work are the ones you gave; the pilot's stored chains are not the live uncertain population.
- Single Arabic reader (a model, not a scholar); verdicts on boundary cases (a poem's isnad, a comment isnad, a duplicate link) are judgements and are marked as such in `cases.md`.

## Files

`agreed_set.tsv` (all 284 reports; state, classes, verdict, tag, holds, flags, v1 verdict, quote), `cases.md` (read cases, disagreements, changes), `verdicts_v2.py` (hand verdicts), `build_v2.py` (expansion, agreement, classes, holds),
`carry.py` (which verdicts carry over), `numbers_v2.py` (tables, `numbers_v2.json`), `dump.py`, `flags_list.py`, `build_cases_v2.py`, `common_v2.py`; derived JSON: `states_v2.json`, `carry_v2.json`, `dis_sample_v2.json`.
Run from `chain-reader/` with `python -X utf8`: `build_v2.py`, `carry.py`, `numbers_v2.py`, `build_cases_v2.py`.
