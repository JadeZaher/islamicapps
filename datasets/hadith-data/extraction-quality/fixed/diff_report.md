# Fixed parse vs production: diff report

Generated 2026-11-21T23:23:56.566410+00:00 by `build_fixed.py` from `datasets/parse_openiti.py` (fixed). Files only: `parsed_hadiths.fixed.json` is a new file; no live path, database or commit was touched.

## Counts

| | rabi | zayd | rida |
|---|---|---|---|
| records before (production) | 1004 | 698 | 35 |
| records after (fixed) | 1005 | 691 | 205 |
| production `source_record_id`s preserved exactly | 1004 | 690 | 34 |
| text unchanged (byte for byte) | 906 | 66 | 1 |
| text changed | 98 | 624 | 33 |
| new ids from splits (`#2`, `#3`...) | 0 | 1 | 171 |
| production records that were split | 0 | 1 | 32 |
| records that absorbed another old record (fragment merge or page-break continuation) | 0 | 8 | 1 |
| records that received a carried chain-opener prefix | 0 | 2 | 0 |
| high-confidence sanad/matn splits | 746 | 638 | 147 |
| low-confidence splits (`sanad_ar` = `matn_ar` = null) | 259 | 53 | 58 |
| continuation chains with `sanad_inherits_from` | 27 | 0 | 204 |
| records with `footnotes` | 1 | 0 | 0 |
| records with `commentary` | 142 | 0 | 0 |
| commentary strings | 148 | 0 | 0 |
| verbatim strings checked | 2594 | 1962 | 499 |

Newly recovered (ids that were not in production and are not split children): rabi: rabi_0881; zayd: none; rida: none

Verbatim check: every `text_ar`, `sanad_ar`, `matn_ar`, footnote and commentary string is a substring of the source after the pipeline's normalisation (NFKC, controls, page and milestone markers, footnote markers) plus the marker strip (`=`, leading `V`, lone `*`), blocks joined by one space. Failures: rabi: 0; zayd: 0; rida: 0.

## How the text of preserved records changed

| change | rabi | zayd | rida |
|---|---|---|---|
| extended | 1 | 10 | 1 |
| extended_both_sides | 0 | 1 | 0 |
| markup_only | 0 | 605 | 0 |
| other | 6 | 4 | 0 |
| prefix_added | 0 | 1 | 0 |
| tail_removed | 91 | 3 | 32 |
| unchanged | 906 | 66 | 1 |

`tail_removed` = the production text starts with the new text (footnote block, commentary, heading or the later reports of a split were cut off); `markup_only` = only `=`/`V`/`*` markers differ; `extended` = text added (merged fragment, restored orphan line); `prefix_added` = a chain opener carried over from the previous report; `extended_both_sides` / `other` = both.

## Ids that disappear, and why

- **rabi**: none
- **zayd**: `zayd_0009|9|V01P065` (absorbed into zayd_0008), `zayd_0045|45|V01P091` (absorbed into zayd_0044), `zayd_0047|47|V01P092` (absorbed into zayd_0046), `zayd_0140|140|V01P151` (absorbed into zayd_0139), `zayd_0308|308|V01P242` (absorbed into zayd_0307), `zayd_0430|430|V01P301` (absorbed into zayd_0429), `zayd_0469|469|V01P318` (absorbed into zayd_0468), `zayd_0610|610|V01P381` (absorbed into zayd_0609)
- **rida**: `rida_0002|2|V01P440` (absorbed into rida_0001)
- **zayd_0118** (`الثياب للصلاة:`, a `~~` line after a bab heading) is a chapter title tail, not a report; it is already absent from production (the replay saw it, the production load did not), and every later zayd id is unchanged.

## Text no longer attached to any record

- **rabi**: 13 blocks: line 41 (22 chars), line 4772 (40 chars), line 4774 (38 chars), line 5151 (59 chars), line 5951 (66 chars), line 6582 (24 chars), line 6584 (53 chars), line 6588 (257 chars), line 6593 (748 chars), line 6607 (211 chars), line 6611 (588 chars), line 6634 (50 chars), line 6636 (66 chars)
- **zayd**: 1 blocks: line 24 (80 chars, preamble_or_introduction)
- **rida**: 1 blocks: line 5337 (80 chars, preamble_or_introduction)

Rabi's unassigned blocks are volume front/back matter, empty or orphaned titles, and the unnumbered closing «حديث الشفاعة» (lines 6582-6632) that the old parser glued onto the last numbered report; they are kept in `parsed_hadiths.fixed.json` under `unassigned_blocks`.

## Source reports the audit listed as missed

| work | item | now in output |
|---|---|---|
| rabi | numbered_report_dropped_whole | now_in_output x 1 |
| rabi | orphan_line_dropped_inside_record | now_in_output x 8 |
| rabi | rabi_comment_not_loaded_to_production | now_in_output x 140 |
| zayd | shorter_than_10_chars_kept_as_prefix_of_next | still_absent x 1 |
| zayd | unrecognised_line | now_in_output x 1 |

## Audit checks re-run on the fixed parse (records flagged, before -> after)

| flag | rabi | zayd | rida |
|---|---|---|---|
| commentary_misattributed | 138 -> 0 | 0 -> 0 | 0 -> 0 |
| commentary_tail | 181 -> 111 | 0 -> 0 | 0 -> 0 |
| footnote_leak | 3 -> 0 | 0 -> 0 | 0 -> 0 |
| fragment_only_chain | 0 -> 0 | 3 -> 0 | 0 -> 1 |
| markup_leak | 4 -> 0 | 613 -> 0 | 1 -> 0 |
| merged_records | 9 -> 0 | 4 -> 0 | 32 -> 0 |
| merged_records_audit_rule_only | 0 -> 0 | 0 -> 6 | 0 -> 0 |
| multiple_sayings | 0 -> 0 | 18 -> 17 | 0 -> 0 |
| sanad_latin_not_arabic_span | 843 -> 0 | 678 -> 0 | 9 -> 0 |
| sanad_matn_split_wrong | 891 -> 0 | 654 -> 0 | 35 -> 0 |
| truncated | 7 -> 0 | 3 -> 0 | 2 -> 0 |
| records | 1004 -> 1005 | 698 -> 691 | 35 -> 205 |
| clean (no defect flag) | 37 -> 1005 | 7 -> 691 | 0 -> 204 |
| text-level clean | 914 -> 1005 | 78 -> 691 | 2 -> 204 |

Rules are the audit's (`deterministic_checks.py`: `split_chain_matn`, `RE_ZAYD_OPENER`, `RE_ORDINAL_HEADING`, the gloss heuristic) applied to the fixed records' `text_ar` / `sanad_ar` / `matn_ar`; `commentary_misattributed` and the dropped-source-line `truncated` kind cannot occur any more (comments are attached to their own record; orphan lines are text). `sanad_latin_not_arabic_span` now counts Latin in `sanad_ar` (the Latin `sanad` list is the resolver's, not the parser's). Remaining flags, by id, are in `checks_before_after.json` (`after.<work>.flagged`).

- **rabi** remaining (first 12 ids per flag): commentary_tail: rabi_0002, rabi_0009, rabi_0010, rabi_0015, rabi_0016, rabi_0021, rabi_0026, rabi_0028, rabi_0045, rabi_0052, rabi_0063, rabi_0080
- **zayd** remaining (first 12 ids per flag): merged_records_audit_rule_only: zayd_0001, zayd_0002, zayd_0023, zayd_0046, zayd_0307, zayd_0429; multiple_sayings: zayd_0001, zayd_0014, zayd_0027, zayd_0203, zayd_0204, zayd_0217, zayd_0239, zayd_0255, zayd_0285, zayd_0314, zayd_0347, zayd_0353
- **rida** remaining (first 12 ids per flag): fragment_only_chain: rida_0007#4

## 12 before / after examples

### rabi_0001

**Before** (production)

- text_ar: قال أبو عمرو الربيع بن حبيب بن عمرو البصري: حدثني أبو عبيدة مسلم بن أبي كريمة التميمي عن جابر بن زيد الأزدي عن عبد الله بن عباس عن النبيء صلى الله عليه وسلم قال: «نية المؤمن خير من عمله».
- matn_ar: قال: «نية المؤمن خير من عمله».
- sanad: al-Rabi ibn Habib, Abu Ubayda Muslim ibn Abi Karima, Jabir ibn Zayd al-Azdi

**After** (`rabi_0001`, page_ref ``, page_start ``, lines 49-51)

- text_ar: قال أبو عمرو الربيع بن حبيب بن عمرو البصري: حدثني أبو عبيدة مسلم بن أبي كريمة التميمي عن جابر بن زيد الأزدي عن عبد الله بن عباس عن النبيء صلى الله عليه وسلم قال: «نية المؤمن خير من عمله».
- sanad_ar: قال أبو عمرو الربيع بن حبيب بن عمرو البصري: حدثني أبو عبيدة مسلم بن أبي كريمة التميمي عن جابر بن زيد الأزدي عن عبد الله بن عباس عن النبيء صلى الله عليه وسلم قال:
- matn_ar: «نية المؤمن خير من عمله».  (split_confidence `high`, kind `chain_and_matn`)

### rabi_0001b

**Before** (production)

- text_ar: وبهذا السند في رواية أخرى عنه عليه السلام قال: «الأعمال بالنيات ولكل امرئ ما نوى».
- matn_ar: قال: «الأعمال بالنيات ولكل امرئ ما نوى».
- sanad: (empty)

**After** (`rabi_0001b`, page_ref ``, page_start ``, lines 53-54)

- text_ar: وبهذا السند في رواية أخرى عنه عليه السلام قال: «الأعمال بالنيات ولكل امرئ ما نوى».
- sanad_ar: وبهذا السند في رواية أخرى عنه عليه السلام قال:
- matn_ar: «الأعمال بالنيات ولكل امرئ ما نوى».  (split_confidence `high`, kind `continuation_chain`)
- sanad_inherits_from: `rabi_0001`

### rabi_0140

**Before** (production)

- text_ar: أبو عبيدة عن جابر بن زيد قال: بلغني عن رسول الله صلى الله عليه وسلم قال: «أمرني حبيبي جبريل عليه السلام أن أغسل فنيكتي وعنفقتي وعنقفتي عند الجنابة». وسرته وكل ما بطن من ج … ة السفلى، والرفغان: ما بين الذكر والفخذين، والمأبضان: ما تحت الركبتين، والمسربة هي: التي فصلت الصدر إلى السرة.
- matn_ar: قال: «أمرني حبيبي جبريل عليه السلام أن أغسل فنيكتي وعنفقتي وعنقفتي عند الجنابة». وسرته وكل ما بطن من جسده. __________ *  … ان: ما تحت الركبتين، والمسربة هي: التي فصلت الصدر إلى السرة.
- sanad: Abu Ubayda Muslim ibn Abi Karima, Jabir ibn Zayd al-Azdi

**After** (`rabi_0140`, page_ref `V01P039`, page_start `V01P038`, lines 910-931)

- text_ar: أبو عبيدة عن جابر بن زيد قال: بلغني عن رسول الله صلى الله عليه وسلم قال: «أمرني حبيبي جبريل عليه السلام أن أغسل فنيكتي وعنفقتي وعنقفتي عند الجنابة».
- sanad_ar: أبو عبيدة عن جابر بن زيد قال: بلغني عن رسول الله صلى الله عليه وسلم قال:
- matn_ar: «أمرني حبيبي جبريل عليه السلام أن أغسل فنيكتي وعنفقتي وعنقفتي عند الجنابة».  (split_confidence `high`, kind `chain_and_matn`)
- commentary [rabi_comment]: قال الربيع: قال أبو عبيدة: وعليه مع ذلك غسل رفغيه ومأبضيه ومسربته وسرته وكل ما بطن من جسده.
- commentary [rabi_comment]: قال الربيع: الفنيكة هي: المسربة التي في وسط الشارب، والعنفقة هي: المسربة التي في الرقبة من خلف قفا الرأس، والعنقفة هي: الشعيرات المنحازة من اللحية تحت … ان: ما تحت الركبتين، والمسربة هي: التي فصلت الصدر إلى السرة.

### rabi_0335

**Before** (production)

- text_ar: أبو عبيدة عن جابر بن زيد قال: بلغني عن رسول الله صلى الله عليه وسلم قال للسعاة: «لا تأخذوا من أرباب الماشية سخلة ولا ربى ولا أكولة ولا فحلا ولا شارفة ولا ذات هزال ولا ذات عوار». ولدها، والأكولة شاة اللحم، وهي السمينة.
- matn_ar: للسعاة: «لا تأخذوا من أرباب الماشية سخلة ولا ربى ولا أكولة ولا فحلا ولا شارفة ولا ذات هزال ولا ذات عوار». ولدها، والأكولة شاة اللحم، وهي السمينة.
- sanad: Abu Ubayda Muslim ibn Abi Karima, Jabir ibn Zayd al-Azdi

**After** (`rabi_0335`, page_ref `V01P085`, page_start `V01P084`, lines 2130-2139)

- text_ar: أبو عبيدة عن جابر بن زيد قال: بلغني عن رسول الله صلى الله عليه وسلم قال للسعاة: «لا تأخذوا من أرباب الماشية سخلة ولا ربى ولا أكولة ولا فحلا ولا شارفة ولا ذات هزال ولا ذات عوار».
- sanad_ar: null
- matn_ar: null  (split_confidence `low`, kind `chain_and_matn`)
- commentary [rabi_comment]: قال الربيع: السخلة التي تتبع أمها وهي ترضع عليها، والربى التي تربي ولدها، والأكولة شاة اللحم، وهي السمينة.

### rabi_0880

**Before** (production)

- text_ar: قال الربيع بن حبيب: بلغني عن ابن مسعود والضحاك بن مزاحم أنهما قالا: {استوى على العرش} أي استوى عليه وعلى الأشياء كلها فخضعت ودانت ، وقد تقول العرب: استوت لفلان دنياه، أي  … . ومن أين جاز له أن يتأول قوله: {استوى على العرش} على ما يعقل ولم يجز أن يتأول قوله: {وهو معهم} على ما يعقل ؟.
- matn_ar: {الرحمن على العرش استوى} ما قال عبد الله بن العباس وابن عمر والحسن ومجاهد: إنه ارتفع ذكره وثناؤه ومجده وعظمته تعالى عما  … على ما يعقل ولم يجز أن يتأول قوله: {وهو معهم} على ما يعقل ؟.
- sanad: al-Rabi ibn Habib

**After** (`rabi_0880`, page_ref `V01P246`, page_start `V01P242`, lines 5832-5905)

- text_ar: قال الربيع بن حبيب: بلغني عن ابن مسعود والضحاك بن مزاحم أنهما قالا: {استوى على العرش} أي استوى عليه وعلى الأشياء كلها فخضعت ودانت ، وقد تقول العرب: استوت لفلان دنياه، أي  … ياه على ما يريد، واستوى بشر على العراق والحجاز، واستوى فلان على مال فلان يريدون أنه احتوى عليه وحازه ونحو ذلك.
- sanad_ar: null
- matn_ar: null  (split_confidence `low`, kind `unsplit`)
- commentary [arranger_note]: تنبيه فإن سأل المسترشد عن تفسير الآيات المتشابهات والدلالة على معانيها من قول الله عز وجل: {الرحمن على العرش استوى} وقوله: {وجآء ربك والملك صفا صفا}،  … على ما يعقل ولم يجز أن يتأول قوله: {وهو معهم} على ما يعقل ؟.

### rabi_0881

**Before**: not in production (dropped by the old parser).

**After** (`rabi_0881`, page_ref `V01P247`, page_start `V01P247`, lines 5909-5932)

- text_ar: وأما ما سألت عنه من قول الحواريين لعيسى صلوات الله عليه: {هل يستطيع ربك أن ينزل علينا مائدة من السماء} وذكرت أن ذلك يدل على أن الله في السماء دون الأرض، فدل ذلك على أنه ل … م ناقة عشراء من صخرة يدل على أنه هناك دون ما سواه لكن الله بمنه وفضله يدبر الأمر من حيث يشاء بلا زوال وانتقال.
- sanad_ar: 
- matn_ar: وأما ما سألت عنه من قول الحواريين لعيسى صلوات الله عليه: {هل يستطيع ربك أن ينزل علينا مائدة من السماء} وذكرت أن ذلك يدل  … لكن الله بمنه وفضله يدبر الأمر من حيث يشاء بلا زوال وانتقال.  (split_confidence `high`, kind `no_chain`)

### rabi_0225

**Before** (production)

- text_ar: أبو عبيدة عن جابر بن زيد عن أبي هريرة قال: انصرف رسول الله صلى الله عليه وسلم من صلاة جهر فيها بالقراءة فقال: «هل قرأ معي أحد منكم آنفا؟» قالوا: بلى يا رسول الله. فقال رس … لقرآن؟!». فانتهى الناس عن القراءة خلف رسول الله صلى الله عليه وسلم فيما جهر به من الصلاة. __________ * خ: هذه.
- matn_ar: قال: «هل قرأ معي أحد منكم آنفا؟» قالوا: بلى يا رسول الله. فقال رسول الله صلى الله عليه وسلم: «مالي أنازع في القرآن؟!». ف … ى الله عليه وسلم فيما جهر به من الصلاة. __________ * خ: هذه.
- sanad: Abu Ubayda Muslim ibn Abi Karima, Jabir ibn Zayd al-Azdi, Abu Hurayra

**After** (`rabi_0225`, page_ref `V01P060`, page_start `V01P059`, lines 1468-1481)

- text_ar: أبو عبيدة عن جابر بن زيد عن أبي هريرة قال: انصرف رسول الله صلى الله عليه وسلم من صلاة جهر فيها بالقراءة فقال: «هل قرأ معي أحد منكم آنفا؟» قالوا: بلى يا رسول الله. فقال رس … سلم: «مالي أنازع في القرآن؟!». فانتهى الناس عن القراءة خلف رسول الله صلى الله عليه وسلم فيما جهر به من الصلاة.
- sanad_ar: أبو عبيدة عن جابر بن زيد عن أبي هريرة قال:
- matn_ar: انصرف رسول الله صلى الله عليه وسلم من صلاة جهر فيها بالقراءة فقال: «هل قرأ معي أحد منكم آنفا؟» قالوا: بلى يا رسول الله.  … راءة خلف رسول الله صلى الله عليه وسلم فيما جهر به من الصلاة.  (split_confidence `high`, kind `chain_and_matn`)
- footnotes: ['خ: هذه.']
- commentary [rabi_comment]: قال الربيع: قال أبو عبيدة: إلا بفاتحة الكتاب فإنها تقرأ مع كل إمام وغيره.

### zayd_0026

**Before** (production)

- text_ar: Vسألت زيدا بن علي عليه السلام عن الوضوء مرة مرة فقال جائز والثلاث أفضل.
- matn_ar: السلام عن الوضوء مرة مرة فقال جائز والثلاث أفضل.
- sanad: (empty)

**After** (`zayd_0026`, page_ref `V01P077`, page_start `V01P077`, lines 290-291)

- text_ar: سألت زيدا بن علي عليه السلام عن الوضوء مرة مرة فقال جائز والثلاث أفضل.
- sanad_ar: 
- matn_ar: سألت زيدا بن علي عليه السلام عن الوضوء مرة مرة فقال جائز والثلاث أفضل.  (split_confidence `high`, kind `no_chain`)

### zayd_0007

**Before** (production)

- text_ar: حدثني أبو خالد رحمه الله قال: سألت زيدا عليه السلام عن الغسل من الجنابة فقال: تغسل يديك ثلاثا ثم تستنجي وتتوضأ وضوءك للصلاة ثم تغسل رأسك ثلاثا ثم تفيض الماء على سائر جسدك … ل الله اصابتني جنابة فغسلت رأسي ثم جلست حتى جف رأسي أفأعيد الماء على رأسي فقال لابل يجزئك غسل رأسك عن الاعادة.
- matn_ar:  ثلاثا ثم تغسل قدميك . قال حدثني بهذا أبي عن أبيه عن جده عن علي بن أبي طالب كرم الله وجهه عن النبي صلى الله عليه وآله. و … ي أفأعيد الماء على رأسي فقال لابل يجزئك غسل رأسك عن الاعادة.
- sanad: (empty)

**After** (`zayd_0007`, page_ref `V01P064`, page_start `V01P063`, lines 137-148)

- text_ar: حدثني أبو خالد رحمه الله قال: سألت زيدا عليه السلام عن الغسل من الجنابة فقال: تغسل يديك ثلاثا ثم تستنجي وتتوضأ وضوءك للصلاة ثم تغسل رأسك ثلاثا ثم تفيض الماء على سائر جسدك … م تغسل قدميك . قال حدثني بهذا أبي عن أبيه عن جده عن علي بن أبي طالب كرم الله وجهه عن النبي صلى الله عليه وآله.
- sanad_ar: حدثني أبو خالد رحمه الله قال:
- matn_ar: سألت زيدا عليه السلام عن الغسل من الجنابة فقال: تغسل يديك ثلاثا ثم تستنجي وتتوضأ وضوءك للصلاة ثم تغسل رأسك ثلاثا ثم تفيض … ن علي بن أبي طالب كرم الله وجهه عن النبي صلى الله عليه وآله.  (split_confidence `high`, kind `chain_and_matn`)

### zayd_0022

**Before** (production)

- text_ar: حدثني زيد بن علي عن أبيه عن جده عن علي عليهم السلام قال: = قال رسول الله صلى الله عليه وآله لا تقبل صلاة الا بزكاة ولا تقبل صلاة الا بقرآن ولا تقبل صلاة الا بطهور ولا تقبل صدقة من غلول. حدثني أبو خالد قال:
- matn_ar: الله صلى الله عليه وآله لا تقبل صلاة الا بزكاة ولا تقبل صلاة الا بقرآن ولا تقبل صلاة الا بطهور ولا تقبل صدقة من غلول. حدثني أبو خالد قال:
- sanad: Zayd ibn Ali, Ali ibn al-Husayn (Zayn al-Abidin), al-Husayn ibn Ali

**After** (`zayd_0022`, page_ref `V01P073`, page_start `V01P072`, lines 246-253)

- text_ar: حدثني زيد بن علي عن أبيه عن جده عن علي عليهم السلام قال: قال رسول الله صلى الله عليه وآله لا تقبل صلاة الا بزكاة ولا تقبل صلاة الا بقرآن ولا تقبل صلاة الا بطهور ولا تقبل صدقة من غلول.
- sanad_ar: حدثني زيد بن علي عن أبيه عن جده عن علي عليهم السلام قال: قال رسول الله صلى الله عليه وآله
- matn_ar: لا تقبل صلاة الا بزكاة ولا تقبل صلاة الا بقرآن ولا تقبل صلاة الا بطهور ولا تقبل صدقة من غلول.  (split_confidence `high`, kind `chain_and_matn`)

### zayd_0429

**Before** (production)

- text_ar: حدثني أبو خالد الواسطي قال:
- matn_ar:  خالد الواسطي قال:
- sanad: (empty)

**After** (`zayd_0429`, page_ref `V01P300`, page_start `V01P300`, lines 3521-3528)

- text_ar: حدثني أبو خالد الواسطي قال: حدثني زيد بن علي عن ابيه عن جده عن علي (ع م) قال: قال رسول الله صلى الله عليه وآله تزوجوا فاني مكاثر بكم الامم.
- sanad_ar: حدثني أبو خالد الواسطي قال: حدثني زيد بن علي عن ابيه عن جده عن علي (ع م) قال: قال رسول الله صلى الله عليه وآله
- matn_ar: تزوجوا فاني مكاثر بكم الامم.  (split_confidence `high`, kind `chain_and_matn`)
- absorbed_ids: ['zayd_0430']

### rida_0032

**Before** (production)

- text_ar: وباسناده قال: قال رسول الله صلى الله عليه وآله ان الله يبغض الرجل يدخل عليه الرجل في بيته فلا يقاتله. الباب التاسع في فضل الغزو والجهاد وباسناده قال: قال علي بن الحسين عل … ناده قال: قال رسول الله صلى الله عليه وآله رأس العقل بعد الدين التودد إلى الناس واصطناع الخير إلى كل بر وفاجر.
- matn_ar: قال: قال رسول الله صلى الله عليه وآله ان الله يبغض الرجل يدخل عليه الرجل في بيته فلا يقاتله. الباب التاسع في فضل الغزو و … قل بعد الدين التودد إلى الناس واصطناع الخير إلى كل بر وفاجر.
- sanad: (empty)

**After** (`rida_0032`, page_ref `V01P495`, page_start `V01P490`, lines 6003-6072)

- text_ar: وباسناده قال: قال رسول الله صلى الله عليه وآله ان الله يبغض الرجل يدخل عليه الرجل في بيته فلا يقاتله.
- sanad_ar: وباسناده قال: قال رسول الله صلى الله عليه وآله
- matn_ar: ان الله يبغض الرجل يدخل عليه الرجل في بيته فلا يقاتله.  (split_confidence `high`, kind `continuation_chain`)
- sanad_inherits_from: `rida_0031#24`

`rida_0032` is followed by 11 split children: `rida_0032#2`, `rida_0032#3`, `rida_0032#4`, `rida_0032#5`, `rida_0032#6`, `rida_0032#7`, `rida_0032#8`, `rida_0032#9`, `rida_0032#10`, `rida_0032#11`, `rida_0032#12`. Chapter titles inside it («الباب التاسع في فضل الغزو والجهاد» ...) are now `bab` values, not reports.

## Limits and what was not done

- Sanad/matn: `sanad_ar` / `matn_ar` are filled only when the closing «قال:» (or a colon, quote or «رسول الله» attribution after it) is clear; otherwise both are null and `split_confidence` is `low` (counts above). A matn that would open with another reporting verb («قال: قال ابن عباس ...», «وقال صلى الله عليه وسلم: ...» with no chain) is also left null rather than guessed.
- `split_chain_matn` is the audit's function with three changes: a closing «قال» followed by «حدثني ...» is a chain link, punctuation after the closing verb stays on the sanad, and «ومن طريقه» counts as a continuation phrase. A matn is never cut inside a word (asserted in the tests).
- Rabi paragraphs that open «قال جابر:» / «قال أبو عبيدة:» and the arranger's prose in volume 3 are not «قال الربيع» comments, footnotes or «تنبيه»; they stay in `text_ar` as before (the advisory `commentary_tail` rows above). Whether they are the report's own discussion is a curation call.
- Zayd `(وقال)` / `(قال)` sub-sayings inside one record are not split (advisory `multiple_sayings`, 18 records). A page-break paragraph whose verb sits after a sentence end is split there; one whose verb is mid-sentence continues the previous report.
- rida pages P444 and P445 of the source repeat the same text; `rida_0007#4` is the first copy's truncated tail «... قال: قال» (flagged `fragment_only_chain` above) and the reports are present twice. Not deduplicated: the source says it twice.
- rida_0001 still begins with the editor's explanation of the chain (the source has no break between it and the Sahifa's own chain); its `bab` is the first printed line of the paragraph «الباب الاول في الذكر ولما كانت ...». rida `bab` values come from the printed first line or the matched «الباب <ordinal> في ...» phrase.
- Split children (`#2`, ...) carry the parent's `hadith_no` and legacy `page_ref`; `page_start` is the page of the paragraph the report starts in (block granularity). Production `page_ref` (the page at the *next* report's start) is kept on purpose so `record_id` does not change.
- The Latin `sanad` list and `chain_indx` are produced downstream by `regen_unified_csvs.py` from `text_ar`; the parser does not write them.

