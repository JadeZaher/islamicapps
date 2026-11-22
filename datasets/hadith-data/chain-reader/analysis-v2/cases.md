# Read cases (v2 pilot)

Verdicts: **right**, **rep** (representation only), **wrong**, **label_wrong**, **cannot_tell**, **abstain** (both readers answered cannot_read_without_previous_report). Markers in readings: [M] imam_in_text, [I] inherited, [U] unnamed, [R] relation, [B] back_reference; the compiler head the tool adds is not shown.
`fix`: i prompt wording, ii packet/context, iii tool or hold, iv not fixable by a reader.

## A. Agreed reports read in this pass (82)

### cr-0007  sunni six-book / muslim  label=defective  ->  **right** (plain)
- text: «وحدثناه أبو بكر، وأبو كريب وابن نمير عن عبد الله بن نمير، ح وحدثناه عمرو الناقد، حدثنا وكيع، كلهم عن هشام»
- reading (both passes): علي بن حجر > علي > هشام > [B]بهذا الإسناد || أبو كريب > أبو أسامة > هشام > [B]بهذا الإسناد  (+4 routes)
- needs_ruling A/B: False/False; holds: []
- why: Six routes from four ح groups to هشام; «بهذا الإسناد» kept as a back_reference at the end.

### cr-0013  al-rabi / musnad-rabi  label=correct  ->  **right** (balagha_gap_fixed)
- text: «قال: بلغني عن أبي هريرة قال»
- reading (both passes): أبو عبيدة > جابر بن زيد > [U]بلغني > أبي هريرة
- needs_ruling A/B: False/False; holds: []
- why: v1 wrong: «بلغني» is now an unnamed link between جابر بن زيد and أبي هريرة.

### cr-0015  pure canon / muwatta  label=correct  ->  **right** (scene_subject_per_ruling)
- text: «مالك, نافع ⏎ ⏎ أن عبد الله ابن عمر كان لا يقرأ في الصلاة على الجنازة»
- reading (both passes): مالك > نافع
- needs_ruling A/B: False/False; holds: []
- why: Ibn ʿUmar's practice is described; he does not speak the report (ruling: a person whose action is described is not a link); v1 cannot_tell.

### cr-0016  pure canon / muwatta  label=defective  ->  **right** (plain)
- text: «يحيى, مالك, ابن شهاب, سعيد ابن المسيب, أبي هريرة | يحيى, مالك, ابن شهاب, عن أبي سلمة ابن عبد الرحمن, أبي هريرة»
- reading (both passes): يحيى > مالك > ابن شهاب > سعيد ابن المسيب > أبي هريرة || يحيى > مالك > ابن شهاب > أبي سلمة ابن عبد الرحمن > أبي هريرة
- needs_ruling A/B: False/False; holds: []
- why: Two field routes; the stray «عن» is not part of the name.

### cr-0021  sunni six-book / tirmidhi  label=defective  ->  **right** (unnamed_link)
- text: «حدثنا محمد بن يحيى، وغير، واحد، قالوا حدثنا أبو عاصم، عن وهب أبي خالد، قال حدثتني أم حبيبة بنت العرباض، وهو ابن سارية عن أبيها»
- reading (both passes): محمد بن يحيى > أبو عاصم > وهب أبي خالد > أم حبيبة بنت العرباض > [R]أبيها || [U]غير، واحد > أبو عاصم > وهب أبي خالد > أم حبيبة بنت العرباض > [R]أبيها
- needs_ruling A/B: False/False; holds: []
- why: Unnamed «غير واحد» is a parallel head; «أبيها» is a bare relation link; the gloss «وهو ابن سارية» is left out.

### cr-0024  al-kafi / al-kafi  label=defective  ->  **right** (imam_speaker)
- text: «عن عذافر قال سمعت أبا عبد الله (عليه السلام) وقد سئل عن كسب النائحة»
- reading (both passes): علي بن إبراهيم > [R]أبيه > ابن أبي عمير > الحسن بن عطية > عذافر > [M]أبا عبد الله
- needs_ruling A/B: False/False; holds: ['drops_stored_name']
- why: Imam heard from: last link (imam_in_text). Hold drops_stored_name is a false hold: the stored name is the matn phrase «كسب النائحة».

### cr-0026  sunni six-book / bukhari  label=defective  ->  **right** (second_route)
- text: «حدثنا موسى، حدثنا معتمر، وقال، لم يبتئر. وقال خليفة حدثنا معتمر»
- reading (both passes): موسى > معتمر || خليفة > معتمر
- needs_ruling A/B: False/True; holds: ['needs_ruling']
- why: Second route «خليفة > معتمر» as a group (rule 4); stored false link dropped.

### cr-0028  al-kafi / al-kafi  label=correct  ->  **right** (plain)
- text: «1- عدة من أصحابنا عن أحمد بن محمد عن ابن فضال عن مثنى عن زرارة عن أبي عبد الله»
- reading (both passes): [U]عدة من أصحابنا > أحمد بن محمد > ابن فضال > مثنى > زرارة > أبي عبد الله
- needs_ruling A/B: False/False; holds: []
- why: Unnamed «عدة من أصحابنا» head, Imam inside the chain stays a narrator.

### cr-0033  sunni six-book / muslim  label=defective  ->  **wrong** (spurious_route)  fix: i
- text: «قال الزهري ألا أحدثك بحديثين عجيبين قال الزهري أخبرني حميد بن عبد الرحمن»
- reading (both passes): محمد بن رافع > عبد الرزاق > معمر > الزهري > حميد بن عبد الرحمن > أبي هريرة || عبد بن حميد > عبد الرزاق > معمر > الزهري > حميد بن عبد الرحمن > أبي هريرة  (+1 routes)
- needs_ruling A/B: False/False; holds: ['drops_stored_name']
- why: Third route «الزهري > حميد > أبي هريرة» is the same man restated inside the chain, not another route; both passes add it.

### cr-0039  al-rabi / musnad-rabi  label=correct  ->  **right** (balagha_gap_fixed)
- text: «أبو عبيدة قال: بلغني عن جابر بن عبد الله»
- reading (both passes): أبو عبيدة > [U]بلغني > جابر بن عبد الله
- needs_ruling A/B: False/False; holds: []
- why: v1 wrong: «بلغني» now an unnamed link after أبو عبيدة.

### cr-0045  al-kafi / al-kafi  label=correct  ->  **right** (plain)
- text: «أبو علي الأشعري عن محمد بن عبد الجبار و أبو العباس الرزاز عن أيوب بن نوح و حميد بن زياد عن ابن سماعة و محمد بن إسماعيل عن الفضل بن شاذان جميعا عن صفوان»
- reading (both passes): أبو علي الأشعري > محمد بن عبد الجبار > صفوان > أبي خالد القماط > [M]أبي عبد الله || أبو العباس الرزاز > أيوب بن نوح > صفوان > أبي خالد القماط > [M]أبي عبد الله  (+2 routes)
- needs_ruling A/B: False/False; holds: []
- why: Four routes, Imam added («قلت لأبي عبد الله»).

### cr-0046  al-kafi / al-kafi  label=correct  ->  **right** (plain)
- text: «8- علي بن إبراهيم عن أبيه عن ابن أبي عمير عن حماد عن الحلبي عن أبي عبد الله (عليه السلام) قال سئل»
- reading (both passes): علي بن إبراهيم > [R]أبيه > ابن أبي عمير > حماد > الحلبي > أبي عبد الله
- needs_ruling A/B: False/False; holds: []
- why: Imam inside the chain: narrator.

### cr-0047  al-kafi / al-kafi  label=defective  ->  **right** (plain)
- text: «عن زرعة بن محمد عن سماعة وعن المفضل بن عمر عن أبي عبد الله»
- reading (both passes): [U]عدة من أصحابنا > أحمد بن محمد > الحسين بن سعيد > علي بن الصلت > زرعة بن محمد > سماعة > أبي عبد الله || [U]عدة من أصحابنا > أحمد بن محمد > الحسين بن سعيد > علي بن الصلت > زرعة بن محمد > المفضل بن عمر > أبي عبد الله
- needs_ruling A/B: True/False; holds: ['needs_ruling']
- why: «سماعة» and «المفضل بن عمر» as two alternatives of one level; a mild real ambiguity (flag by A).

### cr-0048  other imami / al-khisal  label=defective  ->  **right** (irsal_gap_fixed)
- text: «عن محمد بن عيسى بإسناده يرفعه إلى أبي جعفر عليه السلام»
- reading (both passes): [R]أبي > محمد بن يحيى العطار > محمد بن أحمد بن يحيى > محمد بن عيسى > [U]بإسناده يرفعه إلى > أبي جعفر || [R]أبي > أحمد بن إدريس > محمد بن أحمد بن يحيى > محمد بن عيسى > [U]بإسناده يرفعه إلى > أبي جعفر  (+2 routes)
- needs_ruling A/B: False/False; holds: []
- why: v1 wrong: now «محمد بن عيسى > [unnamed] بإسناده يرفعه إلى > أبي جعفر».

### cr-0049  al-kafi / al-kafi  label=correct  ->  **rep** (relation_word)
- text: «عن علي بن جعفر عن أخيه أبي الحسن ( عليه السلام ) قال سألته»
- reading (both passes): محمد بن يحيى > العمركي بن علي > علي بن جعفر > أبي الحسن
- needs_ruling A/B: False/False; holds: []
- why: Stored «أخيه أبي الحسن»; reader «أبي الحسن» (name alone, rule 7).

### cr-0052  al-kafi / al-kafi  label=defective  ->  **abstain** (cannot_read)
- text: «8 عنه عن عدة من أصحابنا رفعوه إلى أبي عبد الله (عليه السلام)»
- reading (both passes): 
- needs_ruling A/B: False/False; holds: ['back_reference_without_previous_report', 'cannot_read_without_previous_report', 'reading_empty_stored_has_links']
- why: Both passes answered cannot_read_without_previous_report; held three ways.

### cr-0053  sunni six-book / tirmidhi  label=defective  ->  **right** (speaker_fixed)
- text: «أما إني سمعت رسول الله صلى الله عليه وسلم يقول»
- reading (both passes): أحمد بن منيع > قران بن تمام الأسدي > سعيد بن عبيد الطائي > علي بن ربيعة الأسدي > المغيرة بن شعبة || أحمد بن منيع > مروان بن معاوية > سعيد بن عبيد الطائي > علي بن ربيعة الأسدي > المغيرة بن شعبة  (+1 routes)
- needs_ruling A/B: False/False; holds: []
- why: v1 wrong: المغيرة، who speaks the saying, is now the last link.

### cr-0056  al-kafi / al-kafi  label=correct  ->  **right** (imam_speaker)
- text: «قال سمعت أبا عبد الله (عليه السلام) يقول»
- reading (both passes): محمد بن يحيى > أحمد بن محمد > علي بن الحكم > معاوية بن وهب > [M]أبا عبد الله
- needs_ruling A/B: False/False; holds: []
- why: Imam heard from: last link.

### cr-0060  other imami / kitab-al-ghayba-numani  label=correct  ->  **right** (imam_asked_flag_unneeded)
- text: «قال: قالت لأبي جعفر: إذا مضى الإمام القائم … قال: بالهدى والإطراق»
- reading (both passes): محمد بن همام > الحسن بن محمد بن جمهور > [R]أبيه > سليمان بن سماعة > أبي الجارود > [M]أبي جعفر || محمد بن الحسن بن محمد بن جمهور > الحسن بن محمد بن جمهور > [R]أبيه > سليمان بن سماعة > أبي الجارود > [M]أبي جعفر
- needs_ruling A/B: False/True; holds: ['needs_ruling']
- why: The Imam who is addressed and answers is the last link (settled); run B flagged needs_ruling anyway.

### cr-0062  al-kafi / al-kafi  label=defective  ->  **right** (plain)
- text: «علي عن أبي عبد الله بن صالح وأحمد بن النضر عن القنبري رجل من ولد قنبر الكبير مولى أبي الحسن الرضا»
- reading (both passes): علي > أبي عبد الله بن صالح > القنبري || علي > أحمد بن النضر > القنبري
- needs_ruling A/B: False/False; holds: ['drops_stored_name']
- why: Two routes from the head «علي»; the gloss after القنبري is left out. Hold drops_stored_name fires on the stored fragment «رجل من».

### cr-0063  al-kafi / al-kafi  label=correct  ->  **right** (plain)
- text: «عدة من أصحابنا عن أحمد بن محمد بن خالد عن عثمان بن عيسى عن رجل عن أبي عبد الله»
- reading (both passes): [U]عدة من أصحابنا > أحمد بن محمد بن خالد > عثمان بن عيسى > [U]رجل > أبي عبد الله
- needs_ruling A/B: False/False; holds: []
- why: Two unnamed links.

### cr-0064  al-rabi / musnad-rabi  label=defective  ->  **right** (no_chain)
- text: «وسئل النبيء صلى الله عليه وسلم يوما عن الإيمان وكان متقنعا بردائه»
- reading (both passes): 
- needs_ruling A/B: False/False; holds: ['reading_empty_stored_has_links']
- why: No chain: both readers return none; the stored link «الإيمان» is a word. Hold reading_empty_stored_has_links fires (false).

### cr-0066  sunni six-book / bukhari  label=defective  ->  **right** (speaker)
- text: «قال كان أبو نهيك رجلا أكولا فقال له ابن عمر إن رسول الله صلى الله عليه وسلم قال»
- reading (both passes): علي بن عبد الله > سفيان > عمرو > ابن عمر
- needs_ruling A/B: False/False; holds: []
- why: ابن عمر speaks the saying: last link.

### cr-0067  al-kafi / al-kafi  label=correct  ->  **right** (plain)
- text: «عن محمد بن الحسين وأحمد بن محمد عن ابن محبوب عن محمد بن الفضيل»
- reading (both passes): محمد بن يحيى > محمد بن الحسين > ابن محبوب > محمد بن الفضيل > أبي حمزة الثمالي > ابي جعفر || محمد بن يحيى > أحمد بن محمد > ابن محبوب > محمد بن الفضيل > أبي حمزة الثمالي > ابي جعفر
- needs_ruling A/B: False/False; holds: []
- why: Two parallel routes.

### cr-0069  other imami / kitab-al-ghayba-numani  label=defective  ->  **right** (imam_asked_flag_unneeded)
- text: «وصفت لأبي عبد الله رجلا … فقال: إن مات هذا مات ميتة جاهلية»
- reading (both passes): أحمد بن محمد بن سعيد > يحيى بن زكريا بن شيبان > علي بن سيف بن عميرة > [R]أبيه > حمران بن أعين > [M]أبي عبد الله
- needs_ruling A/B: False/True; holds: ['needs_ruling']
- why: Imam who answers: last link; run B flagged needs_ruling on this settled case.

### cr-0075  al-kafi / al-kafi  label=defective  ->  **right** (parallel_imams_fixed)
- text: «عن الحلبي و زرارة و محمد بن مسلم و حمران بن أعين عن أبي جعفر و أبي عبد الله ( عليه السلام ) قالا»
- reading (both passes): أبو علي الأشعري > محمد بن حسان > محمد بن علي > أبي جميلة > الحلبي > أبي جعفر || أبو علي الأشعري > محمد بن حسان > محمد بن علي > أبي جميلة > الحلبي > أبي عبد الله  (+6 routes)
- needs_ruling A/B: False/False; holds: []
- why: Eight routes, each ending in one of the two Imams (v1: neither pass right).

### cr-0077  al-kafi / al-kafi  label=correct  ->  **right** (imam_speaker)
- text: «قال سمعت أبا عبد الله (عليه السلام) يقول»
- reading (both passes): علي بن إبراهيم > [R]أبيه > محسن بن أحمد > أبان > مسمع بن عبد الملك > [M]أبا عبد الله
- needs_ruling A/B: False/False; holds: []
- why: Imam heard from.

### cr-0078  al-rabi / musnad-rabi  label=defective  ->  **right** (balagha_gap)
- text: «قال الربيع: بلغني عن جويبر عن الضحاك عن ابن عباس»
- reading (both passes): [U]بلغني > جويبر > الضحاك > ابن عباس
- needs_ruling A/B: False/False; holds: []
- why: Reader writes the compiler's own «بلغني» as an unnamed head link: consistent with the work's balagha convention (the gap is real).

### cr-0079  al-rabi / musnad-rabi  label=defective  ->  **right** (balagha_gap_fixed)
- text: «أبو عبيدة قال: بلغني عن ابن عمر يروي عن رسول الله»
- reading (both passes): أبو عبيدة > [U]بلغني > ابن عمر
- needs_ruling A/B: False/False; holds: []
- why: v1 wrong: «بلغني» now unnamed.

### cr-0088  sunni six-book / tirmidhi  label=defective  ->  **right** (speaker)
- text: «قلنا لابن عباس أرأيت قول الله عز وجل»
- reading (both passes): عبد الله بن عبد الرحمن > صاعد الحراني > زهير > قابوس بن أبي ظبيان > [R]أباه > ابن عباس
- needs_ruling A/B: False/False; holds: []
- why: «قلنا لـ X»: link (rule 5).

### cr-0093  al-kafi / al-kafi  label=correct  ->  **right** (imam_asked)
- text: «قال قلت لأبي عبد الله (عليه السلام) إن رجلا أوصى إلي بشيء»
- reading (both passes): محمد بن يحيى > محمد بن أحمد > محمد بن عيسى > محمد بن سليمان > الحسين بن عمر > [M]أبي عبد الله
- needs_ruling A/B: False/False; holds: []
- why: Imam addressed and answering.

### cr-0094  al-kafi / al-kafi  label=correct  ->  **right** (imam_asked)
- text: «قال سألت الرضا (عليه السلام) عن الرجل يلمس فرج جاريته»
- reading (both passes): [U]عدة من أصحابنا > أحمد بن محمد > إسماعيل بن سعد الأشعري > [M]الرضا
- needs_ruling A/B: False/False; holds: []
- why: Imam asked.

### cr-0095  other imami / sifat-al-shia  label=correct  ->  **rep** (flag_unneeded)
- text: «عن عبد الله بن موسى بن جعفر ع قال : سألته عن الملكين»
- reading (both passes): [R]أبي > سعد بن عبد الله > علي الناسخ بن السائح > عبد الله بن موسى بن جعفر
- needs_ruling A/B: False/True; holds: ['needs_ruling']
- why: The last link already answers; run B flagged needs_ruling on a settled case. Stored differs only by the honorific.

### cr-0101  sunni six-book / nasai  label=defective  ->  **right** (plain)
- text: «عن حبيب، مولى عروة عن بدية، - وكان الليث يقول ندبة - مولاة ميمونة عن ميمونة قالت»
- reading (both passes): الحارث بن مسكين > ابن وهب > يونس > ابن شهاب > حبيب، مولى عروة > بدية > ميمونة || الحارث بن مسكين > ابن وهب > الليث > ابن شهاب > حبيب، مولى عروة > بدية > ميمونة
- needs_ruling A/B: False/False; holds: []
- why: Two routes (يونس / الليث), ميمونة added (speaker).

### cr-0102  sunni six-book / abudawud  label=defective  ->  **right** (unnamed_and_second_isnad)
- text: «فقال أخبرني من سمع رسول الله … قال أبو داود ورواه ابن المبارك عن محمد بن يسار عن سليم بن مطير»
- reading (both passes): أحمد بن أبي الحواري > سليم بن مطير > مطير > [U]أخبرني من سمع || ابن المبارك > محمد بن يسار > سليم بن مطير
- needs_ruling A/B: False/False; holds: ['drops_stored_name']
- why: Unnamed informant as last link; appended isnad as a second group (rule 4). drops_stored_name is a false hold (stored junk «ادي القرى»).

### cr-0104  al-kafi / al-kafi  label=defective  ->  **right** (unnamed_link)
- text: «11 غير واحد من أصحابنا عن أحمد بن أبي عبد الله عن غير واحد عن أبي جميلة»
- reading (both passes): [U]غير واحد من أصحابنا > أحمد بن أبي عبد الله > [U]غير واحد > أبي جميلة > أبي عبد الله
- needs_ruling A/B: False/False; holds: ['drops_stored_name']
- why: Two unnamed links.

### cr-0105  al-faqih / man-la-yahduruhu-al-faqih  label=correct  ->  **right** (plain)
- text: «و روى عمار الساباطي عن أبي عبد الله عليه السلام»
- reading (both passes): عمار الساباطي > أبي عبد الله
- needs_ruling A/B: False/False; holds: []
- why: Imam after «عن» is a narrator; previous report irrelevant.

### cr-0108  sunni six-book / bukhari  label=defective  ->  **right** (second_isnad_fixed)
- text: «وحدثنا آدم حدثنا شعبة حدثنا أبو إسحاق الهمداني عن البراء بن عازب»
- reading (both passes): سعيد بن الربيع > شعبة > أبي إسحاق > البراء بن عازب || محمد بن عرعرة > شعبة > أبي إسحاق > البراء بن عازب  (+1 routes)
- needs_ruling A/B: False/False; holds: []
- why: v1 wrong: third route added.

### cr-0111  other imami / kamil-al-ziyarat  label=correct  ->  **right** (alternative_flag_real)
- text: «عن سعيد بن يسار أو غيره قال سمعت أبا عبد الله»
- reading (both passes): محمد بن جعفر الرزاز القرشي الكوفي > محمد بن الحسين بن أبي الخطاب > محمد بن سنان > سعيد بن يسار > [M]أبا عبد الله || محمد بن جعفر الرزاز القرشي الكوفي > محمد بن الحسين بن أبي الخطاب > محمد بن سنان > [U]أو غيره > [M]أبا عبد الله  (+2 routes)
- needs_ruling A/B: False/True; holds: ['needs_ruling']
- why: «أو غيره» as an unnamed alternative; second isnad after the bracket as its own group. A real ambiguity, flagged by B.

### cr-0113  sunni six-book / bukhari  label=correct  ->  **right** (plain)
- text: «حدثنا عبدان، عن أبي حمزة، عن الأعمش، عن شقيق، عن عبد الله، قال قسم النبي»
- reading (both passes): عبدان > أبي حمزة > الأعمش > شقيق > عبد الله
- needs_ruling A/B: False/False; holds: []
- why: Plain.

### cr-0114  sunni six-book / nasai  label=defective  ->  **right** (plain)
- text: «عن حبيب، مولى عروة عن بدية … عن ميمونة قالت»
- reading (both passes): الحارث بن مسكين > ابن وهب > يونس > ابن شهاب > حبيب، مولى عروة > بدية > ميمونة || الحارث بن مسكين > ابن وهب > الليث > ابن شهاب > حبيب، مولى عروة > بدية > ميمونة
- needs_ruling A/B: False/False; holds: []
- why: As cr-0101.

### cr-0117  sunni six-book / muslim  label=defective  ->  **right** (second_isnad_fixed)
- text: «وحدثنيه زهير بن حرب، حدثنا عبد الصمد بن عبد الوارث، حدثنا همام»
- reading (both passes): أبو بكر بن أبي شيبة > يزيد بن هارون > همام > إسحاق، بن عبد الله بن أبي طلحة > أنس بن مالك || زهير بن حرب > عبد الصمد بن عبد الوارث > همام > إسحاق بن عبد الله بن أبي طلحة > أنس بن مالك
- needs_ruling A/B: False/False; holds: []
- why: v1 wrong: second route after the matn is now a group.

### cr-0119  al-faqih / man-la-yahduruhu-al-faqih  label=correct  ->  **right** (imam_asked)
- text: «قال : قلت لأبي عبد الله عليه السلام إنه ذكر لنا»
- reading (both passes): معاوية بن وهب > [M]أبي عبد الله
- needs_ruling A/B: False/False; holds: []
- why: Imam addressed.

### cr-0122  other imami / kitab-al-ghayba-numani  label=defective  ->  **right** (flag_unneeded)
- text: «عن أبي صادق، عن أمير المؤمنين أنه قال: ملك بني العباس»
- reading (both passes): محمد بن همام > أحمد بن مابنداذ > أحمد بن هلال > الحسن بن علي بن فضال > سفيان بن إبراهيم الجريري > [R]أبيه > أبي صادق > أمير المؤمنين
- needs_ruling A/B: True/False; holds: ['needs_ruling']
- why: Imam inside the chain after «عن»: narrator (settled); A flagged needs_ruling.

### cr-0124  al-faqih / man-la-yahduruhu-al-faqih  label=defective  ->  **right** (imam_asked)
- text: «عن أبي بصير فقال : سألت أبا عبد الله عليه السلام»
- reading (both passes): البزنطي > علي بن أبي حمزة > أبي بصير > [M]أبا عبد الله
- needs_ruling A/B: False/False; holds: ['drops_stored_name']
- why: Imam asked; stored junk merged.

### cr-0125  sunni six-book / muslim  label=correct  ->  **right** (plain)
- text: «عن الزهري، عن أبي، سلمة عن جابر، ح»
- reading (both passes): عبد بن حميد > عبد الرزاق > معمر > الزهري > أبي، سلمة > جابر
- needs_ruling A/B: False/False; holds: []
- why: Truncated text.

### cr-0126  other imami / al-amali-saduq  label=correct  ->  **right** (inherited_fixed)
- text: «15 - وبهذا الاسناد، قال: قال الصادق جعفر بن محمد (عليهما السلام)»
- reading (both passes): [I]الحسن بن إبراهيم بن ناتانه > [I]علي بن إبراهيم > [I]أبيه > [I]محمد بن أبي عمير > [I]أبي زياد النهدي > [I]عبد الله بن بكير > [M]الصادق جعفر بن محمد
- needs_ruling A/B: False/False; holds: []
- why: v1 wrong: the six names of prev1 are written as inherited, then the Imam named here (imam_in_text). Previous chain_text: «حدثنا الحسن بن إبراهيم بن ناتانه … عن عبد الله بن بكير،».

### cr-0129  other imami / kitab-al-ghayba-numani  label=correct  ->  **right** (imam_scene_speaker)
- text: «كنت عند أبي عبد الله في بيته … فقال: ما يبكيك يا عمرو»
- reading (both passes): أبو سليمان > إبراهيم بن إسحاق > عبد الله بن حماد > عمرو بن شمر > [M]أبي عبد الله
- needs_ruling A/B: False/False; holds: []
- why: The Imam answers and speaks the saying.

### cr-0131  sunni six-book / muslim  label=defective  ->  **right** (plain)
- text: «وحدثنيه عبيد الله بن عمر القواريري، حدثنا خالد … حدثنا هشام، بهذا الإسناد»
- reading (both passes): محمد بن المثنى > يحيى بن سعيد > هشام > ابن أبي كثير > أبي سلمة > معيقيب || عبيد الله بن عمر القواريري > خالد > هشام > [B]بهذا الإسناد  (+1 routes)
- needs_ruling A/B: True/False; holds: ['drops_stored_name', 'needs_ruling']
- why: Three routes; the second ends with a back_reference, not expanded.

### cr-0133  sunni six-book / nasai  label=correct  ->  **wrong** (shared_tail_missed)  fix: i
- text: «ح وأنبأنا حميد بن مسعدة، عن سفيان بن حبيب، عن الأوزاعي، قال حدثنا أبو كثير، قال سمعت أبا هريرة»
- reading (both passes): سويد بن نصر > عبد الله > الأوزاعي > أبو كثير || حميد بن مسعدة > سفيان بن حبيب > الأوزاعي > أبو كثير > أبا هريرة
- needs_ruling A/B: False/False; holds: []
- why: Route one stops at «أبو كثير»; the text writes «أبا هريرة» once, after the second branch, for both. v1 had it right (regression).

### cr-0134  al-faqih / man-la-yahduruhu-al-faqih  label=defective  ->  **right** (asker_not_link)
- text: «و سأل سليمان بن جعفر الجعفري العبد الصالح موسى بن جعفر عليهما السلام: عن الرجل»
- reading (both passes): [M]موسى بن جعفر
- needs_ruling A/B: True/True; holds: ['needs_ruling']
- why: Single link: the Imam who is asked (owner ruling; v1 had asker plus Imam). Both readers flagged needs_ruling although the prompt's rule 5 settles it.

### cr-0136  other imami / al-amali-mufid  label=correct  ->  **wrong** (poem_isnad_as_route)  fix: i
- text: «وأنشدني أبو الفرج البرقي الداودي قال: أنشدني شيخ كان منقطعا إلى الله تعالى ببيت المقدس: ومنتظر للموت»
- reading (both passes): أبو حفص عمر بن محمد المعروف بابن الزيات > علي بن مهرويه القزويني > داود بن سليمان الغازي > الرضا علي بن موسى > موسى بن جعفر > جعفر بن محمد > محمد بن علي > علي بن الحسين > الحسين بن علي > [M]أمير المؤمنين || أبو الفرج البرقي الداودي > [U]شيخ
- needs_ruling A/B: False/False; holds: []
- why: Second route «أبو الفرج البرقي > شيخ» is the isnad of a poem appended to the report, not of the saying (v1 right).

### cr-0143  al-kafi / al-kafi  label=defective  ->  **wrong** (concatenated_reports)  fix: iv
- text: «عن علي بن أبي حمزة و محمد بن يحيى عن أحمد بن محمد عن علي بن الحكم عن علي بن أبي حمزة عن أبي بصير مثله .حميد بن زياد عن ابن سماعة»
- reading (both passes): [B]عنه > عبد الله بن جبلة > علي بن أبي حمزة > أحمد بن محمد > علي بن الحكم > علي بن أبي حمزة > أبي بصير || [B]عنه > عبد الله بن جبلة > محمد بن يحيى > أحمد بن محمد > علي بن الحكم > علي بن أبي حمزة > أبي بصير  (+1 routes)
- needs_ruling A/B: False/False; holds: ['back_reference_without_previous_report']
- why: Two isnads run together: the reading crosses «علي بن أبي حمزة» into the second isnad. Held: back_reference_without_previous_report.

### cr-0144  sunni six-book / muslim  label=defective  ->  **wrong** (duplicate_link)  fix: i
- text: «كلاهما عن المعتمر، قال ابن حبيب حدثنا معتمر بن سليمان»
- reading (both passes): يحيى بن حبيب > المعتمر > معتمر بن سليمان > [R]أبي > أبو نضرة > جابر بن عبد الله || محمد بن عبد الأعلى > المعتمر > معتمر بن سليمان > [R]أبي > أبو نضرة > جابر بن عبد الله
- needs_ruling A/B: True/True; holds: ['needs_ruling']
- why: The same man written twice (المعتمر, معتمر بن سليمان) is kept as two links by both passes.

### cr-0146  pure canon / muwatta  label=correct  ->  **right** (scene_subject)
- text: «رأى سالم ابن عبد الله يخرج من أنفه الدم حتى تختضب أصابعه»
- reading (both passes): مالك
- needs_ruling A/B: False/False; holds: []
- why: Salim is the subject of what was seen, not the speaker: not a link (owner ruling); v1 disagreement.

### cr-0149  al-faqih / man-la-yahduruhu-al-faqih  label=defective  ->  **right** (no_chain)
- text: «5813 - الدال على الخير كفاعله»
- reading (both passes): 
- needs_ruling A/B: False/False; holds: ['reading_empty_stored_has_links']
- why: Advice only; no chain. Hold reading_empty_stored_has_links fires (false).

### cr-0153  other imami / thawab-al-amal  label=defective  ->  **abstain** (cannot_read)
- text: «و بهذا الإسناد قال قال علی ع أیها الناس»
- reading (both passes): 
- needs_ruling A/B: False/False; holds: ['back_reference_without_previous_report', 'cannot_read_without_previous_report', 'reading_empty_stored_has_links']
- why: cannot_read_without_previous_report by both.

### cr-0156  other imami / fadail-al-shia  label=defective  ->  **right** (plain)
- text: «أبي رحمه الله، قال: حدثني سعد بن عبد الله قال: حدثنى عباد بن سليمان»
- reading (both passes): [R]أبي > سعد بن عبد الله > عباد بن سليمان > محمد بن سليمان > [R]أبيه > أبان بن تغلب > أبى عبد الله
- needs_ruling A/B: False/False; holds: []
- why: Imam inside chain: narrator.

### cr-0157  al-kafi / al-kafi  label=defective  ->  **wrong** (shared_tail_missed)  fix: i
- text: «عن أبيه عن ابن أبي عمير ومحمد بن إسماعيل عن الفضل بن شاذان عن صفوان بن يحيى وابن أبي عمير عن معاوية بن عمار»
- reading (both passes): علي بن إبراهيم > [R]أبيه > ابن أبي عمير || محمد بن إسماعيل > الفضل بن شاذان > صفوان بن يحيى > معاوية بن عمار > أبي عبد الله  (+1 routes)
- needs_ruling A/B: False/False; holds: []
- why: First route stops at «ابن أبي عمير»: the tail «معاوية بن عمار > أبي عبد الله» is written once for both (v1: B right, A wrong; now both wrong).

### cr-0171  al-faqih / man-la-yahduruhu-al-faqih  label=defective  ->  **right** (no_chain)
- text: «3286 - و في خبر آخر : "أنه لا تقبل شهادة الولد على والده "»
- reading (both passes): 
- needs_ruling A/B: False/False; holds: ['reading_empty_stored_has_links']
- why: No chain; hold false.

### cr-0173  sunni six-book / muslim  label=defective  ->  **right** (speaker)
- text: «أنه نظر إلى عبد الله بن عمر كيف يحكي رسول الله صلى الله عليه وسلم قال " يأخذ الله»
- reading (both passes): سعيد بن منصور > يعقوب > أبو حازم > عبيد الله بن مقسم > عبد الله بن عمر
- needs_ruling A/B: False/False; holds: []
- why: ابن عمر speaks the saying: last link.

### cr-0177  sunni six-book / tirmidhi  label=defective  ->  **wrong** (speaker_omitted)  fix: i
- text: «فقال إن رسول الله صلى الله عليه وسلم قال " إن القبر أول منازل الآخرة»
- reading (both passes): هناد > يحيى بن معين > هشام بن يوسف > عبد الله بن بحير > هانئا، مولى عثمان
- needs_ruling A/B: False/False; holds: []
- why: عثمان speaks the saying to those who asked; reading ends at «هانئا، مولى عثمان» and does not flag it (v1 cannot_tell).

### cr-0181  al-kafi / al-kafi  label=defective  ->  **right** (unnamed_link)
- text: «عن زرارة عن أحدهما (عليهما السلام) في محرمين»
- reading (both passes): أحمد بن محمد > الحسن بن محبوب > شهاب > زرارة > [U]أحدهما
- needs_ruling A/B: False/False; holds: ['drops_stored_name']
- why: «أحدهما» as an unnamed link. drops_stored_name false hold (stored junk).

### cr-0182  al-faqih / man-la-yahduruhu-al-faqih  label=defective  ->  **right** (imam_single)
- text: «و قال أبو جعفر عليه السلام : «البر و الصدقة ينفيان الفقر»
- reading (both passes): [M]أبو جعفر
- needs_ruling A/B: False/False; holds: ['drops_stored_name']
- why: Single-link route: the Imam who speaks.

### cr-0187  sunni six-book / abudawud  label=defective  ->  **right** (parallel_narrators_fixed)
- text: «حدثني إياس بن الحارث بن المعيقيب، وجده، من قبل أمه أبو ذباب عن جده»
- reading (both passes): ابن المثنى > سهل بن حماد أبو عتاب > أبو مكين، نوح بن ربيعة > إياس بن الحارث بن المعيقيب > [R]جده || ابن المثنى > سهل بن حماد أبو عتاب > أبو مكين، نوح بن ربيعة > أبو ذباب > [R]جده  (+4 routes)
- needs_ruling A/B: True/False; holds: ['needs_ruling']
- why: Two parallel narrators (إياس, أبو ذباب) from «جده» (v1: both passes wrong). A flagged needs_ruling on the three heads (unneeded).

### cr-0190  other imami / mujam-al-ahadith-al-mutabara  label=correct  ->  **right** (second_isnad)
- text: «قال الكليني (رحمه الله): وحدثني شيخ من أصحابنا - ذهب عني اسمه - أن أبا عمرو سأل أحمد بن إسحاق»
- reading (both passes): محمد بن عبدالله > عبدالله بن جعفر الحميري || محمد بن يحيى > عبدالله بن جعفر الحميري  (+1 routes)
- needs_ruling A/B: True/True; holds: ['needs_ruling']
- why: Third route «الكليني > [unnamed] شيخ من أصحابنا» is a real second isnad written in the report (the compiler named in the text).

### cr-0194  other imami / kitab-al-mumin  label=correct  ->  **right** (inherited)
- text: «91 - وعنه (ع) قال لكل شئ شئ يستريح إليه»
- reading (both passes): [I]أبي عبد الله
- needs_ruling A/B: False/False; holds: ['drops_stored_name']
- why: «عنه» takes the Imam of prev1 («وعن أبي عبد الله (ع) قال …»), written as inherited.

### cr-0195  other imami / fadail-al-shia  label=correct  ->  **right** (unnamed_and_imam)
- text: «حدثني سعد بن عبد الله بإسناد يرفعه، عن منصور الصيقل، قال: كنت عند أبي عبد الله عليه السلام في فسطاطه بمنى، فنظر إلى الناس فقال»
- reading (both passes): [R]أبى > سعد بن عبد الله > [U]بإسناد يرفعه > منصور الصيقل > [M]أبي عبد الله
- needs_ruling A/B: False/False; holds: []
- why: Unnamed gap «بإسناد يرفعه» and the Imam who speaks (v1 disagreement).

### cr-0201  other imami / kamal-al-din  label=correct  ->  **abstain** (cannot_read)
- text: «و بهذا الإسناد قال قال علي بن الحسين سيد العابدين ع»
- reading (both passes): 
- needs_ruling A/B: False/False; holds: ['back_reference_without_previous_report', 'cannot_read_without_previous_report', 'reading_empty_stored_has_links']
- why: cannot_read_without_previous_report by both.

### cr-0202  sunni six-book / bukhari  label=defective  ->  **wrong** (extra_unnamed_link)  fix: i
- text: «قال أخبرني من، شهد النبي صلى الله عليه وسلم … قلت من حدثك قال ابن عباس»
- reading (both passes): مسلم > شعبة > الشيباني > الشعبي > [U]أخبرني من > ابن عباس
- needs_ruling A/B: True/True; holds: ['drops_stored_name', 'needs_ruling']
- why: The unnamed «من» is identified by the answer «ابن عباس»: one link, not an unnamed link plus ابن عباس. Both flagged needs_ruling (real ambiguity, and the flag caught it).

### cr-0210  al-faqih / man-la-yahduruhu-al-faqih  label=defective  ->  **right** (plain)
- text: «عن سعد بن عبد الله؛ و أحمد بن محمد بن عيسى؛ و إبراهيم بن هاشم جميعا عن القاسم بن يحيى عن جده الحسن بن راشد»
- reading (both passes): [R]أبي > سعد بن عبد الله > القاسم بن يحيى > الحسن بن راشد || [R]أبي > أحمد بن محمد بن عيسى > القاسم بن يحيى > الحسن بن راشد  (+2 routes)
- needs_ruling A/B: False/False; holds: ['nested_jami', 'nested_semicolon']
- why: Four routes. Holds nested_jami + nested_semicolon fire on a correct reading (false).

### cr-0213  sunni six-book / tirmidhi  label=defective  ->  **right** (second_isnad_fixed)
- text: «قال محمد بن رافع وأخبرنا محمد بن بشر أخبرنا علي بن نزار عن نزار عن عكرمة»
- reading (both passes): محمد بن رافع > محمد بن بشر > سلام بن أبي عمرة > عكرمة > ابن عباس || محمد بن رافع > محمد بن بشر > علي بن نزار > نزار > عكرمة > ابن عباس
- needs_ruling A/B: False/False; holds: []
- why: v1 wrong: second route now present.

### cr-0214  sunni six-book / muslim  label=correct  ->  **right** (plain)
- text: «كلهم عن يحيى بن أبي كثير، بهذا الإسناد نحوه»
- reading (both passes): يحيى بن بشر الحريري > معاوية > يحيى بن أبي كثير > [B]بهذا الإسناد || ابن المثنى > أبو عامر > هشام > يحيى بن أبي كثير > [B]بهذا الإسناد  (+3 routes)
- needs_ruling A/B: False/False; holds: []
- why: Five routes with back_reference.

### cr-0235  other imami / kitab-al-ghayba-tusi  label=correct  ->  **abstain** (cannot_read)
- text: «s131- وبهذا الإسناد عن ابن عباس في قوله»
- reading (both passes): 
- needs_ruling A/B: False/False; holds: ['back_reference_without_previous_report', 'cannot_read_without_previous_report', 'reading_empty_stored_has_links']
- why: cannot_read_without_previous_report by both.

### cr-0238  al-faqih / man-la-yahduruhu-al-faqih  label=defective  ->  **right** (asker_not_link)
- text: «و سأل موسى بن بكر أبا الحسن موسى بن جعفر عليهما السلام: عن الرجل يقوم في الصف وحده»
- reading (both passes): [M]أبا الحسن موسى بن جعفر
- needs_ruling A/B: False/False; holds: ['drops_stored_name']
- why: Single link: the Imam asked (owner ruling).

### cr-0243  sunni six-book / nasai  label=defective  ->  **right** (plain)
- text: «أخبرني أبي وأم عبد الملك بن أبي محذورة، عن أبي محذورة»
- reading (both passes): إبراهيم بن الحسن > حجاج > ابن جريج > عثمان بن السائب > [R]أبي > أبي محذورة || إبراهيم بن الحسن > حجاج > ابن جريج > عثمان بن السائب > أم عبد الملك بن أبي محذورة > أبي محذورة
- needs_ruling A/B: False/False; holds: []
- why: Two routes: a bare «أبي» relation and the mother.

### cr-0255  other imami / kamil-al-ziyarat  label=defective  ->  **right** (imam_scene_speaker_fixed)
- text: «جلوسا عند أبي عبد الله (ع) و كان المتكلم يونس … قال إذا حضرتهم و ذكرتنا فقل»
- reading (both passes): [R]أبي > سعد بن عبد الله > أحمد بن محمد بن عيسى > القاسم بن يحيى > الحسن بن راشد > الحسين بن ثوير بن أبي فاختة > [M]أبي عبد الله || علي بن الحسين > سعد بن عبد الله > أحمد بن محمد بن عيسى > القاسم بن يحيى > الحسن بن راشد > الحسين بن ثوير بن أبي فاختة > [M]أبي عبد الله  (+1 routes)
- needs_ruling A/B: False/False; holds: []
- why: v1 wrong: the Imam who speaks is now the last link; the three heads right.

### cr-0260  sunni six-book / bukhari  label=defective  ->  **right** (plain)
- text: «قال سفيان وزاد فيه أبو الزناد عن الأعرج عن أبي هريرة»
- reading (both passes): علي بن عبد الله > سفيان > الزهري > سعيد بن المسيب > أبي هريرة || سفيان > أبو الزناد > الأعرج > أبي هريرة
- needs_ruling A/B: False/False; holds: []
- why: Appended route as its own group.

### cr-0262  sunni six-book / ibnmajah  label=defective  ->  **right** (speaker)
- text: «فسمعته يقول بينا نحن مع رسول الله»
- reading (both passes): أبو كريب > أبو معاوية > الأعمش > زيد بن وهب > عبد الرحمن بن عبد رب الكعبة > عبد الله بن عمرو بن العاص || أبو كريب > عبد الرحمن المحاربي > الأعمش > زيد بن وهب > عبد الرحمن بن عبد رب الكعبة > عبد الله بن عمرو بن العاص  (+1 routes)
- needs_ruling A/B: False/False; holds: []
- why: The Companion heard from is the last link.

### cr-0272  al-kafi / al-kafi  label=defective  ->  **right** (plain)
- text: «عن حماد بن عيسى عن بعض أصحابنا عن أبي عبد الله (عليه السلام) أنه سئل عن التيمم»
- reading (both passes): علي بن إبراهيم > [R]أبيه > حماد بن عيسى > [U]بعض أصحابنا > أبي عبد الله
- needs_ruling A/B: False/False; holds: ['drops_stored_name']
- why: Plain; hold false (stored junk).

### cr-0280  other imami / al-khisal  label=correct  ->  **right** (second_isnad_comment)
- text: «وقد روى هذا الحديث عن أبي الصلت الهروي عبدالسلام بن صالح، عن علي ابن موسى الرضا باسناد مثله»
- reading (both passes): حمزة بن محمد بن أحمد العلوي > أبوالحسن علي بن محمد البزاز > أبوأحمد داود بن سليمان الغازي > علي ابن موسى الرضا > موسى بن جعفر > جعفر ابن محمد > محمد بن علي الباقر > علي بن الحسين > الحسين بن علي > أمير المؤمنين || أبي الصلت الهروي عبدالسلام بن صالح > علي ابن موسى الرضا > [B]باسناد مثله
- needs_ruling A/B: True/True; holds: ['needs_ruling']
- why: Second group from the appended «ورواه X عن Y» (rule 4). Both readers flagged needs_ruling although the ten-link chain is settled.

### cr-0282  sunni six-book / bukhari  label=defective  ->  **right** (plain)
- text: «عن ابن عباس، رضى الله عنهما في قوله {اللات والعزى}»
- reading (both passes): مسلم > أبو الأشهب > أبو الجوزاء > ابن عباس
- needs_ruling A/B: False/False; holds: []
- why: Stored junk dropped.

## B. Agreed reports whose verdict is carried from v1 (142)

Their expanded non-derived routes equal the agreed reading I read in v1 and no inherited link is involved, so v1's verdict and quote stand (`../analysis/cases.md`, `../analysis/agreed_set.tsv`). The compiler head and the imam_in_text links were re-checked in this pass: two of them write the compiler twice (see the README). Ids:

cr-0001, cr-0003, cr-0004, cr-0005, cr-0008, cr-0009, cr-0012, cr-0014, cr-0015, cr-0017, cr-0018, cr-0022, cr-0023, cr-0025, cr-0027, cr-0030, cr-0034, cr-0035, cr-0038, cr-0040, cr-0041, cr-0042, cr-0043, cr-0044, cr-0050, cr-0054, cr-0061, cr-0072, cr-0073, cr-0074, cr-0076, cr-0080, cr-0081, cr-0086, cr-0087, cr-0089, cr-0091, cr-0092, cr-0096, cr-0097, cr-0098, cr-0103, cr-0106, cr-0107, cr-0109, cr-0110, cr-0112, cr-0115, cr-0116, cr-0118, cr-0120, cr-0121, cr-0123, cr-0127, cr-0130, cr-0132, cr-0140, cr-0142, cr-0145, cr-0148, cr-0150, cr-0152, cr-0154, cr-0155, cr-0158, cr-0159, cr-0161, cr-0162, cr-0165, cr-0169, cr-0172, cr-0174, cr-0175, cr-0179, cr-0183, cr-0184, cr-0185, cr-0186, cr-0188, cr-0189, cr-0191, cr-0192, cr-0193, cr-0196, cr-0197, cr-0198, cr-0199, cr-0203, cr-0204, cr-0207, cr-0209, cr-0212, cr-0215, cr-0216, cr-0217, cr-0218, cr-0221, cr-0222, cr-0223, cr-0224, cr-0225, cr-0226, cr-0228, cr-0229, cr-0230, cr-0231, cr-0232, cr-0236, cr-0240, cr-0241, cr-0242, cr-0244, cr-0245, cr-0246, cr-0247, cr-0248, cr-0249, cr-0250, cr-0251, cr-0252, cr-0254, cr-0256, cr-0257, cr-0259, cr-0261, cr-0263, cr-0265, cr-0267, cr-0268, cr-0269, cr-0270, cr-0271, cr-0273, cr-0274, cr-0275, cr-0276, cr-0277, cr-0278, cr-0279, cr-0281, cr-0283, cr-0284

### Carried reports with a derived-link duplicate (tool)

- cr-0183: الحسين بن سعيد > محمد بن سنان > عمار بن مروان > [M]أبا عبد الله
- cr-0197: أبو جعفر محمد بن علي بن الحسين بن موسى ابن بابويه القمي > [R]أبي > سعد بن عبد الله > أحمد بن أبي عبد الله البرقي > محمد بن خالد > أبي البختري وهب ابن وهب > الصادق جعفر بن محمد > [R]أبيه > [R]آبائه > أم سلمة

## C. Disagreements: random 30 of 56 (seed 20261123), all read

### cr-0006  sunni six-book / abudawud  ->  class **tool_orthography_invalid**, right: **A**  fix: iii
- text: «حدثنا محمد بن سليمان الأنباري، حدثنا وكيع، عن سفيان»
- difference: B invalid: asked for occurrence 2 of «وكيع», which stands once. A right.

### cr-0010  sunni six-book / muslim  ->  class **narrative_embedded**, right: **B closer**  fix: i
- text: «فنهاه أبان بن عثمان … وحدث عن عثمان بن عفان»
- difference: A ends «نبيه > عثمان بن عفان»; B «نبيه > أبان بن عثمان > عثمان بن عفان». Both omit «أن عمر بن عبيد الله».

### cr-0011  sunni six-book / abudawud  ->  class **shared_tail_missed**, right: **B**  fix: i
- text: «حدثنا مسدد، حدثنا يحيى، ح وحدثنا عثمان بن أبي شيبة، عن ابن نمير، عن عبيد الله، عن نافع»
- difference: A stops the first route at «يحيى»; B gives it the tail.

### cr-0019  other imami / kamal-al-din  ->  class **tool_orthography_invalid**, right: **A (held)**  fix: iii
- text: «و بهذا الإسناد عن يونس بن عبد الرحمن»
- difference: B invalid: «وبهذا الإسناد» not found because the text writes «و بهذا» with a space.

### cr-0020  sunni six-book / tirmidhi  ->  class **shared_tail_missed**, right: **neither**  fix: i
- text: «حدثنا بذلك هناد وقتيبة قالا حدثنا وكيع عن ثابت بن أبي صفية»
- difference: A invalid (order); B: route one complete, routes «هناد > وكيع > ثابت» and «قتيبة > …» stop before «أبي جعفر > جابر».

### cr-0031  other imami / uyun-akhbar-al-rida  ->  class **tool_orthography_invalid**, right: **both (invalid)**  fix: iii
- text: «عن أبيه على بن محمد، عن أبيه محمد بن على»
- difference: Both invalid: the text writes «على» (alef maqsura), the readers «علي».

### cr-0032  al-faqih / man-la-yahduruhu-al-faqih  ->  class **nested_multi_isnad**, right: **neither**  fix: iv
- text: «عن أيوب بن نوح؛ و إبراهيم بن هاشم جميعا عن صفوان بن يحيى؛ و ابن أبي عمير جميعا عن محمد بن حمران»
- difference: A and B both break the second isnad into fragments and differ in the third route.

### cr-0036  other imami / thawab-al-amal  ->  class **tool_orthography_invalid**, right: **B**  fix: iii
- text: «أبی رحمه الله قال حدثنی أحمد بن إدریس»
- difference: A invalid: the text uses Persian yeh (ی), A wrote «أبي».

### cr-0051  pure canon / muwatta  ->  class **speaker_omitted**, right: **A**  fix: i
- text: «أن علي ابن أبي طالب قال لا يقطع الصلاة شيء»
- difference: A adds the speaker of the saying; B keeps the field's single name.

### cr-0055  other imami / thawab-al-amal  ->  class **tool_orthography_invalid**, right: **both (invalid)**  fix: iii
- text: «حدثنی محمد بن الحسن قال حدثنی محمد بن یحیی»
- difference: Both invalid: Persian yeh in the text.

### cr-0070  other imami / maani-al-akhbar  ->  class **tool_orthography_invalid**, right: **A**  fix: iii
- text: «عن أبي محمد عبد الله بن محمد الغفاري»
- difference: B invalid: wrote «أبو محمد» where the text has the genitive «أبي محمد».

### cr-0071  sunni six-book / abudawud  ->  class **tool_orthography_invalid**, right: **both (invalid)**  fix: iii
- text: «حدثنا موسى بن على، ح»
- difference: Both invalid: «علي» for the text's «على».

### cr-0083  al-kafi / al-kafi  ->  class **parallel_pair_misparse**, right: **A**  fix: i
- text: «أبو علي الأشعري عن محمد بن عبد الجبار و محمد بن يحيى عن أحمد بن محمد جميعا عن ابن فضال»
- difference: B makes «أبو علي الأشعري» the head of the second route too (أبو علي > محمد بن يحيى > أحمد بن محمد).

### cr-0084  other imami / fadail-al-shia  ->  class **speaker_omitted**, right: **A (held)**  fix: i
- text: «عن أبي عبد الله عليه السلام قال: قال أمير المؤمنين عليه السلام: أنا الراعي»
- difference: A adds the speaker of the saying (imam_in_text), B omits him. Held: back reference without previous report.

### cr-0100  sunni six-book / muslim  ->  class **shared_tail_missed**, right: **A**  fix: i
- text: «أن أبا النضر، حدثه عن سليمان بن يسار، عن عائشة»
- difference: B's first route stops at «عمرو بن الحارث»; A applies the tail to both.

### cr-0137  al-rabi / musnad-rabi  ->  class **doubt_alternative**, right: **A**  fix: i
- text: «عن مجاهد أو عمن حدثه عن مجاهد - شك في ذلك أبو غانم -»
- difference: A gives both readings as two routes, B only the first. Both flagged needs_ruling on the title «الإمام», which the prompt settles.

### cr-0141  sunni six-book / muslim  ->  class **tool_orthography_invalid**, right: **neither (invalid)**  fix: iii
- text: «ح وحدثنا أبو بكر بن أبي شيبة، حدثنا هشيم، عن مغيرة»
- difference: A wrote «هشيم بن بشير» (a name completed beyond the text); B wrote «أبو معشر» for the text's «أبي معشر».

### cr-0147  sunni six-book / muslim  ->  class **variant_remark_as_link**, right: **A**  fix: i
- text: «وفي حديث الليث وصالح أن الصعب بن جثامة أخبره»
- difference: B adds «الصعب بن جثامة» to every route, though the remark covers two versions only; A keeps «بهذا الإسناد».

### cr-0151  other imami / uyun-akhbar-al-rida  ->  class **surface_scope**, right: **both**  fix: iii
- text: «7 - وبهذا الإسناد قال: قال رسول الله»
- difference: A «وبهذا الإسناد», B «بهذا الإسناد»: one back reference, differs by an attached «و». Previous report has no names.

### cr-0163  other imami / kitab-al-ghayba-tusi  ->  class **surface_scope**, right: **both**  fix: iii
- text: «أبو الحسين محمد بن علي الشجاعي الكاتب»
- difference: A keeps the final «الكاتب», B drops it.

### cr-0164  other imami / kamal-al-din  ->  class **surface_scope**, right: **both (held)**  fix: iii
- text: «و بهذا الإسناد عن الحارث بن المغيرة»
- difference: Attached «و» again; held for back reference without previous report.

### cr-0166  other imami / al-amali-saduq  ->  class **surface_scope**, right: **both**  fix: iii
- text: «أبو عبد الله محمد بن عبد الله بن محمد بن الحجاج العدل»
- difference: «العدل» kept or not.

### cr-0167  other imami / al-amali-mufid  ->  class **surface_scope**, right: **both**  fix: iii
- text: «أخبرنا أبو الحسن علي بن محمد الكاتب»
- difference: «الكاتب» kept or not.

### cr-0180  sunni six-book / tirmidhi  ->  class **surface_scope**, right: **A**  fix: iii
- text: «عن الزهري، بهذا الحديث . وروى مالك، هذا الحديث»
- difference: B writes «بهذا الحديث» (the matn) as a back_reference link; A leaves it out.

### cr-0205  sunni six-book / tirmidhi  ->  class **comment_isnad_boundary**, right: **B per rule 4**  fix: i
- text: «وقد روى شيبان عن يحيى بن أبي كثير مثل هذا»
- difference: B adds a route «شيبان > يحيى بن أبي كثير» from the compiler's remark (rule 4); A omits it. Judged consistent with cr-0280.

### cr-0208  other imami / mujam-al-ahadith-al-mutabara  ->  class **parallel_pair_misparse**, right: **B**  fix: i
- text: «علي بن ابراهيم عن أبيه ومحمد بن اسماعيل عن الفضل ابن شاذان جميعا عن حماد بن عيسى»
- difference: A crosses the two routes (علي بن ابراهيم > محمد بن اسماعيل …) and drops حماد from the first; B writes two clean routes.

### cr-0211  other imami / mujam-al-ahadith-al-mutabara  ->  class **parallel_pair_misparse**, right: **B**  fix: i
- text: «علي بن ابراهيم عن أبيه ومحمد بن اسماعيل عن الفضل ابن شاذان جميعا عن حماد بن عيسى»
- difference: Same text as cr-0208.

### cr-0220  other imami / mujam-al-ahadith-al-mutabara  ->  class **embedded_narrative_as_route**, right: **A**  fix: i
- text: «وقد أخبرني أبوعلي أحمد بن إسحاق عن أبي الحسن عليه السلام قال: سألته»
- difference: B adds a route «…الحميري > أبوعلي > ابا محمد» from a story told inside the report.

### cr-0233  other imami / uyun-akhbar-al-rida  ->  class **tool_orthography_invalid**, right: **both (invalid)**  fix: iii
- text: «قال: قال على بن أبي طالبعليه السلام»
- difference: Both invalid: «علي» for «على», and the text glues the honorific to the name.

### cr-0253  sunni six-book / abudawud  ->  class **shared_tail_missed**, right: **B**  fix: i
- text: «حدثنا محمد بن كثير، ح وحدثنا مسلم بن إبراهيم، حدثنا همام، عن قتادة»
- difference: A leaves the first route as the lone «محمد بن كثير»; B gives both the tail.

## D. Changes of verdict between the pilots

```
{
 "fixed": [
  "cr-0013",
  "cr-0015",
  "cr-0039",
  "cr-0048",
  "cr-0053",
  "cr-0079",
  "cr-0102",
  "cr-0108",
  "cr-0117",
  "cr-0126",
  "cr-0213",
  "cr-0255"
 ],
 "broke": [
  "cr-0133",
  "cr-0136",
  "cr-0153",
  "cr-0183",
  "cr-0197",
  "cr-0201",
  "cr-0235"
 ],
 "same_right": 142,
 "same_wrong": [
  "cr-0008",
  "cr-0027",
  "cr-0193"
 ],
 "newly_agreed": {
  "right": [
   "cr-0028",
   "cr-0045",
   "cr-0046",
   "cr-0047",
   "cr-0056",
   "cr-0060",
   "cr-0063",
   "cr-0066",
   "cr-0067",
   "cr-0069",
   "cr-0075",
   "cr-0077",
   "cr-0088",
   "cr-0093",
   "cr-0094",
   "cr-0101",
   "cr-0105",
   "cr-0111",
   "cr-0113",
   "cr-0114",
   "cr-0119",
   "cr-0124",
   "cr-0125",
   "cr-0129",
   "cr-0134",
   "cr-0146",
   "cr-0187",
   "cr-0195",
   "cr-0210",
   "cr-0214"
  ],
  "wrong": [
   "cr-0033",
   "cr-0143",
   "cr-0144",
   "cr-0157",
   "cr-0177"
  ],
  "rep": [
   "cr-0049",
   "cr-0095"
  ]
 },
 "lost_agreement": {
  "right": [
   "cr-0006",
   "cr-0037",
   "cr-0051",
   "cr-0084",
   "cr-0147",
   "cr-0166",
   "cr-0167",
   "cr-0176",
   "cr-0205",
   "cr-0208",
   "cr-0211",
   "cr-0233",
   "cr-0239",
   "cr-0253"
  ],
  "wrong": [
   "cr-0010",
   "cr-0020",
   "cr-0141",
   "cr-0164",
   "cr-0227",
   "cr-0266"
  ],
  "unread": [
   "cr-0011",
   "cr-0082",
   "cr-0100",
   "cr-0135",
   "cr-0180",
   "cr-0206",
   "cr-0264"
  ],
  "rep": [
   "cr-0151",
   "cr-0168",
   "cr-0200",
   "cr-0220"
  ],
  "label_wrong": [
   "cr-0163",
   "cr-0234"
  ]
 },
 "v1_unread_now": [
  [
   "cr-0007",
   "right"
  ],
  [
   "cr-0016",
   "right"
  ],
  [
   "cr-0021",
   "right"
  ],
  [
   "cr-0024",
   "right"
  ],
  [
   "cr-0052",
   "abstain"
  ],
  [
   "cr-0062",
   "right"
  ],
  [
   "cr-0064",
   "right"
  ],
  [
   "cr-0104",
   "right"
  ],
  [
   "cr-0122",
   "right"
  ],
  [
   "cr-0131",
   "right"
  ],
  [
   "cr-0149",
   "right"
  ],
  [
   "cr-0156",
   "right"
  ],
  [
   "cr-0171",
   "right"
  ],
  [
   "cr-0173",
   "right"
  ],
  [
   "cr-0181",
   "right"
  ],
  [
   "cr-0182",
   "right"
  ],
  [
   "cr-0202",
   "wrong"
  ],
  [
   "cr-0243",
   "right"
  ],
  [
   "cr-0260",
   "right"
  ],
  [
   "cr-0262",
   "right"
  ],
  [
   "cr-0272",
   "right"
  ],
  [
   "cr-0282",
   "right"
  ]
 ]
}
```
