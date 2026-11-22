---
type: adjudication
---
# Pilot 001: reviewer against judge, adjudicated by reading the Arabic

**Who decided.** One model reader (`claude-opus-5-5`), reading each item's Arabic `text` by hand, made every verdict here. That is the same model family as the reviewer and the readers, so a blind spot all three share would pass unseen. No person checked these verdicts. No model was run, no database was touched, and nothing outside `adjudication/` was written. No narrator is identified. Every claim rests on a quote from the item's text. `adjudicate.py` refuses to run if a quote is not an exact substring of that text.

**Rulings applied:** the owner's rulings listed in the task, including the third round of 2026-11-22: the narrated-encounter rule (9) and the two-sayings rule (10). The judge worked before ruling 9 existed. Its `cases.md` marks narrated encounters "unruled", for example t02-09169c: «narrated encounter where the Imam speaks (unruled; both passes flagged)».

| file | what |
|---|---|
| `items.tsv` | one row per item (81). Columns: opaque id and report id; packet, set and status; the judge's verdict; the reviewer's decision, the review's own validity and its uncertainty; whether judge and reviewer agree; the adjudicated `actual` and `my_verdict`; `correction_check` and `referral_check`; the quote; a note |
| `numbers.json` | every rate below, with Wilson 95% intervals |
| `adjudicate.py` | the verdict table (by hand) joined to key, packets and outputs. It validates each review on its own, checks quotes and computes the rates |
| `compare_corrections.py` | expands each corrected reading with `v3_4/expand_v3_4` and compares its routes with the readers'. That is how a correction is classed as representation only |
| `dump_items.py` | prints items for reading (`--only`, `--packet`) |

Run all three from `chain-reader/` with `python -B -X utf8 reviewer/pilot-001/adjudication/<script>`.

## 1. Coverage

- **Read in full: 55 of 81.**
  - All 16 items where the reviewer and the judge disagree: 12 the judge called right and the reviewer did not confirm, plus the 4 the judge could not tell.
  - All 16 the judge called wrong, including the 2 in packet 04.
  - A random 15 of the 41 scored items both call right (seed 20261122).
  - The 8 packet-04 items both call right.
- **Not adjudicated: 26** items both call right. I spot-read their text and routes only, and they are counted as `assumed_right`. One representation note: in cr1-d685c3 the last link's surface is «صاحب», cut from «حدثنا صاحب، هذه الدار».
- **Packet 04.** Each review was validated on its own (`validate_review`), so 9 of its 10 reviews are valid. Only cr1-750b73's corrected reading is invalid, with the error `order: g0l2i0 'عكرمة بن عمار' occurs only before the previous level`.

## 2. Adjudicated rates

The adjudicated truth for the 81 items:

| actual | count | what it means |
|---|---|---|
| wrong | 26 | the 16 the judge called wrong, the 4 it could not tell, and 6 it called right |
| right | 52 | 26 read in full, plus the 26 assumed right |
| unruled | 3 | al-Faqih route statements: the structure is right, but whether to store them at all is the owner's open question |

| reviewer | k / n | rate | Wilson 95% |
|---|---|---|---|
| **actually wrong: caught** (any non-confirmation) | 26 / 26 | 100% | 87.1–100% |
| actually wrong: confirmed (missed) | 0 / 26 | 0% | 0–12.9% |
| how it caught them | 19 corrected, 7 referred | | |
| **actually right: confirmed** | 49 / 52 | 94.2% | 84.4–98.0% |
| actually right: corrected substantively (harmful if applied) | 0 / 52 | 0% | 0–6.9% |
| actually right: corrected cosmetically (same routes) | 3 / 52 | 5.8% | 2.0–15.6% |
| actually right: referred | 0 / 52 | 0% | 0–6.9% |
| unruled: referred | 3 / 3 | | |
| **corrected readings that are right** (valid ones) | 21 / 21 | 100% | 84.5–100% |
| corrected readings right in substance (including the invalid one) | 22 / 22 | 100% | 85.1–100% |
| corrections that are substantive and right | 18 / 21 | 85.7% | 65.4–95.0% (the other 3 are cosmetic) |
| referrals justified | 10 / 10 | | |
| both-right re-read: actually right | 23 / 23 | 100% | 85.7–100% |
| **judge: wrong verdict** (decided items, unruled excluded) | 6 / 74 | 8.1% | 3.8–16.6% |
| judge cannot-tell items that are decidable under today's rulings | 4 / 4 | | |

**Sensitivity check.** If only the right readings I read in full are counted, the reviewer confirms 23 of 26 (88.5%), and the other 3 are cosmetic corrections. Counting a correction with the same routes as a confirmation (section 5.1) gives 26 of 26.

**Against the README's proposed gate.**
- Catch rule: the reviewer catches 16 of 16 judge-wrong items (14 scored plus 2 in packet 04) and 26 of 26 adjudicated wrong. It passes.
- Confirm rule: it confirms 49 of 61 judge-right items (80%), which fails the 90% bar. Measured against the adjudicated truth it confirms 49 of 52 (94%), or 52 of 52 with cosmetic corrections counted. It passes.

## 3. Reviewer against judge (the 16 disagreements, plus packet 04)

There are 16 disagreements: 12 items the judge called right, plus the 4 it could not tell. **The reviewer is right on 10, both are acceptable (representation only) on 3, and 3 are unruled. The judge is right on none, and neither is right on none.** In packet 04 all 10 agree with the judge.

### 3.1 Judge right, reviewer referred (7)

| id | my verdict | the reading's problem (quote) |
|---|---|---|
| cr1-d695ec | reviewer_right | A second saying is relayed by the man who speaks inside the encounter: «فنظرت فإذا عمر قال إني قد رأيتك جئت آنفا قال». Under rulings 9 and 10 it needs its own chain, and both readers leave him out. The join of «ح وحدثني أبو عثمان، عن جبير بن نفير» is also genuinely open, because no speaker is written. |
| cr1-5415bf | reviewer_right | The man who speaks inside the narrator's encounter («ونحن مع أمير المؤمنين علي بصفين … قال: قد بلغتماني») is not the last link (ruling 9). «وذكر أبان أنه سمعه أيضا عن عمر بن أبي سلمة» is a real route-or-remark ambiguity. |
| cr1-37ccb6 | reviewer_right | The chain continues by another isnad: «بمثل حديث مالك بن أنس بإسناده عن نافع». The readers stop at the last name with no back-reference link, and the earlier report is not in the packet. |
| cr1-b567d7 | reviewer_right | The man who speaks in the scene is missing as last link: «قبل عمر بن الخطاب الحجر ثم قال أم والله لقد علمت». «أنحدثه» is an implicit, unnamed transmitter, which is unruled. |
| cr1-2fc4ff, cr1-1d4e8b, cr1-efd81b | unruled | Each is al-Faqih's route statement with no saying: «و ما كان فيه عن … فقد رويته». The structure is right. The non-clearable hold `needs_ruling_faqih_route_statement` keeps them held whatever the reviewer says. |

### 3.2 Judge right, reviewer corrected (5)

| id | my verdict | quote |
|---|---|---|
| cr1-80cd84 | reviewer_right, substantive | «قال ابن عيسى لم يذكر أمية أحد إلا معتمر»: only one of the three routes has that link. The judge's own caveat says so, and the judge marked the same kind of statement in cr1-b61479 («إلا الضحاك وابن عجلان فإنهما زادا») as reshaping routes. |
| cr1-23cc42 | reviewer_right, substantive (medium) | «وقال عثمان والحسن بن علي عن محمد بن عباد بن جعفر»: two named co-transmitters of this chain gave another name at one link. Putting «وغيرهم» on the written chain is a default the text does not state. |
| cr1-593d35 | both_acceptable | Only where the back-reference link «في هذا الإسناد» sits changes. `compare_corrections`: `same_routes=True`. |
| cr1-cd74d5 | both_acceptable | Only the variant group changes: in «أمر عبد الله بن عمرو» the man commanded is not a link of the remark. Routes are identical. |
| cr1-e87ace | both_acceptable | Only the last link's kind changes, `imam_in_text` to `narrator` («عمن سمع أبا عبد الله الصادق (عليه السلام) يقول»). Routes are identical. |

### 3.3 Judge could not tell (4)

All four readings are wrong, and the reviewer is right on all four.

| id | decision | quote |
|---|---|---|
| cr1-c785d5 | corrected (ruling 9) | «ثُمَّ قَالَ عَلَيْهِ اَلسَّلاَمُ» |
| cr1-d1ccde | corrected (ruling 9) | «كُنْتُ يَوْماً عَلَى رَأْسِ الْمَأمُونِ، فَقالَ» |
| cr1-f890c7 | corrected (ruling 10, medium) | «وأخبرني خارجة بن زيد بن ثابت أن زيد بن ثابت لم يكن يبيع». The one whose practice is described is not a link. |
| cr1-ad25ec | referred, justified | «وَقَالَ اَلْحَلَبِيُّ لَهُ»: the one asked is a back-reference to a report that is not in the packet. |

### 3.4 The judge's errors

The judge's 6 errors: d695ec, 5415bf, b567d7, 37ccb6, 23cc42 and 80cd84. Three of them (d695ec, 5415bf, b567d7), plus two of its cannot-tells (c785d5, d1ccde), turn on ruling 9 or 10, which came after the judge. Under the rulings it actually had, the judge erred on 3 of 74 (4.1%).

## 4. Judge-wrong readings: are the corrections right?

All 16 judge-wrong readings are wrong; I agree with the judge on every one. The reviewer referred 2 of them (eedf77, a494cc, both al-Faqih route statements). In both referrals it named the structural error in its reasons: in eedf77 «و الفضل بن عامر» is made a compiler's shaykh, and in a494cc «و الحميريّ جميعا» is read as a third route.

It corrected 14:
- **10 corrected readings are right as they stand.** 723cba, 36837c, c5386a, 9c5eae, 7c8879 and 519567 join «ح» branches at the shared tail. f8eeeb («- قال ابن العلاء وقيس -»), 0ea0a3 («عن ابن أبي ذئب، والأوزاعي، -») and b61479 («إلا الضحاك وابن عجلان فإنهما زادا») add a route or link stated inside the isnad. c0e535 shares the tail after a restated name.
- **4d44fd is also right.** It joins the branches, adds the co-source from «وزاد، جعفر والليث», and adds the speaker of «قال أبو بصرة أترغب عن سنة رسول الله» under ruling 9.
- **2 are right at medium confidence.**
  - 6dfc38: the readers inherited an earlier asker as the one asked (context «وَ رُوِيَ عَنِ اَلْحَلَبِيِّ قَالَ : سَأَلْتُهُ»). The correction inherits the source named in prev1, «عَنْ أَبِي عَبْدِ اَللَّهِ».
  - 0b5d5a: «قال وحدثنا مخلد بن حسين» shows the later isnads are spoken by the first shaykh.
- **1 is right in substance but invalid in format.** For 750b73, «حدثنا بذلك إسحاق بن منصور حدثنا عبد الرحمن بن مهدي» connects the compiler to the isnad stated before it. The reader format's text-order rule cannot express that.
- **None introduces a new error.** Applying any of the 13 valid ones would be a fix. One caveat: 519567 leaves the father's closing advice («قال فقال لي أبي») aside as implicit transmission, which is unruled, and the reviewer says so.

## 5. Recommendations

### 5.1 `confirm_with_correction` on an already-applied reading

The current rule reverts the reading at once. The pilot does not support that.
- Of the 32 applied items, 3 were not confirmed. In none of the 3 would reverting have put a better chain on the page:
  - **80cd84** (correction right) and **d695ec** (referral right): the stored chain is identical to the readers' reading, so reverting changes nothing.
  - **e87ace** (cosmetic correction): reverting replaces a right reading with a stored chain that fuses the gap phrase into a name: «محمد بن حمزة عمن سمع أبا عبد الله الصادق».
  - Reverting gained something in 0 of 3 (Wilson 0–56%; the sample is tiny).
- **Recommendation:**
  - Leave the reading applied, label it "AI review disputes this reading; awaiting second review", and queue the correction for pass 2.
  - If pass 2 writes the same routes, apply the correction in place of the reading, not the stored chain.
  - Revert to stored only when a human says so, or when the stored chain's routes equal the correction's.
  - Separately, a correction whose routes equal the reading's (`readings_agree`, the check `compare_corrections.py` runs) is a confirmation with a representation note. That covers 3 of 22 corrections, all on right readings. It should never revert or queue anything.

### 5.2 Applying one reviewer's correction without a second review

Keep the two-run rule.
- **The case for dropping it:** the corrections were right 21 of 21 (Wilson lower bound 84.5%), and the substantive ones 18 of 18 (lower bound 82.4%).
- **Why that is not enough:**
  - The interval cannot rule out roughly 1 wrong correction in 6.
  - My check is one more Claude reader, so a shared blind spot would pass both of us.
  - Four of the corrections stand on a judgement the text leaves open (6dfc38, 0b5d5a, 23cc42, f890c7, the `right_medium` cases).
- **What it costs:** a second run on 22 of 81 items (27%).
- **When to revisit:** with zero errors in a row, the Wilson lower bound reaches 95% only at n ≥ 73 corrections (n / (n + 3.84) ≥ 0.95).

### 5.3 Referral reasons

**None was unjustified (10 of 10 justified).** The judge-based scorer's "7 needless referrals" is an artifact: 4 of the 7 referred readings are wrong, and 3 are unruled. The prompt still wastes the referrals in two ways.

1. **Five of the 10 are al-Faqih route statements** (2fc4ff, 1d4e8b, efd81b, eedf77, a494cc).
   - The non-clearable hold already keeps these held, so the referral decides nothing.
   - Two of them carry a real structural correction only in prose. eedf77's question: «al-Faqih's statement of the compiler's routes («طرق») to the book of Ali b. Ja'far with no saying is unruled; if it is to be stored, the readers' reading also needs correcting (see reasons).»
   - **Prompt change:** "When the item's holds already name the unruled question, do not refer for it. Review the structure as if the owner had ruled to store it: `confirm_reading` or `confirm_with_correction`. Give the unruled question in `question` as a note." The rule table keeps such items held anyway.
2. **Three referrals bundle an error the rulings settle with a part they don't** (d695ec, 5415bf, b567d7).
   - Example, d695ec: «under ruling 9 and 10 Umar speaks a second saying inside Uqba's story and should be a last link of a second saying, which both readers left out».
   - The ruled part (ruling 9 or 10) could have gone into a `corrected_reading`.
   - **Prompt and validator change:** allow `corrected_reading` with `refer_to_human`, meaning "the reading the rulings settle; the question is the rest". It is never applied without a human.

### 5.4 Score and record per item, not per packet

Yes. Rejecting packet 04 whole lost 9 valid reviews: 8 right confirmations and 1 right correction (0b5d5a). The rejection was triggered by one corrected reading that was itself right in substance.
- **Scorer and pipeline:** validate each review with `validate_review(review, item)`, record the valid ones, and mark only the invalid item as "review invalid, stays as it was".
- **Validator:** a connection isnad written after the names it connects to («حدثنا بذلك X حدثنا Y» after «وروى Y، عن Z») needs either an allowed out-of-order level or a prompt line telling the reviewer to refer it.

## 6. What I could not decide

- **cr1-d695ec:** who speaks «ح وحدثني أبو عثمان», and so where the second branch joins. The text writes no speaker.
- **cr1-5415bf:** whether «وذكر أبان أنه سمعه أيضا عن عمر بن أبي سلمة» and «قال معمر: وذكر أبو هارون العبدي أنه سمعه أيضا» are routes of this saying or remarks, and where the first one ends.
- **cr1-b567d7:** the implicit transmitter in «أنحدثه» (unruled).
- **cr1-2fc4ff, cr1-1d4e8b, cr1-efd81b** (and eedf77, a494cc): whether al-Faqih route statements are stored at all (unruled).
- **Medium-confidence corrections:**
  - 6dfc38: the antecedent of «سأله» is taken from prev1.
  - 0b5d5a: the speaker of «وحدثنا فضيل».
  - 23cc42: where «وغيرهم» goes.
  - f890c7: the speaker of «وأخبرني».
- **cr1-519567:** whether «قال فقال لي أبي» is a second saying (implicit transmission, unruled).
- **A question for the owner, not counted against anyone:** an isnad with its own «حدثني / وحدثنا» that ends «مثله» or «بمثل حديث فلان» after the matn. Examples are c0e535's third route («عَنْ أَبِي الْحَسَنِ الثَّالِثِ مِثْلَهُ») and c75278. Readers, judge and reviewer all treat it as a route. Rule 6 lists «بمثل حديث فلان» as a remark but does not address a fully written isnad.
- **The 26 both-confirmed items not adjudicated.**
