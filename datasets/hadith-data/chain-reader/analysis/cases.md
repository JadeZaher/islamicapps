# Read cases

Every case below was read against the Arabic text (diacritics stripped for reading; quotes are from the text). Verdicts: **right**, **rep** (representation only: same links, differs in a gloss, honorific, verb, relation word, orthography, back-reference link or a noise word in the stored surface), **wrong**, **label_wrong** (reader right, human label wrong), **cannot_tell**.
`fix`: i prompt rule, ii context from sources, iii deterministic post-processing, iv not fixable by a reader.

## Class (d): labelled defective, reader reproduces the stored chain (5 reports, all read)

### cr-0091  sunni six-book / muslim  ->  **right** (stored_junk_dropped)
- text: «حدثنا قتادة، بهذا الإسناد نحو حديث عفان وقال عون بن عتبة»
- stored: [defective/false_split] إسحاق بن إبراهيم > عبد الصمد بن عبد الوارث > همام > قتادة || [unlabelled] إسحاق بن إبراهيم > عبد الصمد بن عبد الوارث > همام > عون بن عتبة
- reader (both passes): إسحاق بن إبراهيم > عبد الصمد بن عبد الوارث > همام > قتادة || محمد بن المثنى > عبد الصمد بن عبد الوارث > همام > قتادة
- why: Label note says the defect is the extra routes «همام > عون بن عتبة»; reader drops them (the text only says «وقال عون بن عتبة») and keeps the two routes to قتادة.

### cr-0117  sunni six-book / muslim  ->  **wrong** (second_isnad_after_matn)  fix: i
- text: «وحدثنيه زهير بن حرب، حدثنا عبد الصمد بن عبد الوارث، حدثنا همام»
- stored: [correct/missing_route] أبو بكر بن أبي شيبة > يزيد بن هارون > همام > إسحاق بن عبد الله بن أبي طلحة > أنس بن مالك
- reader (both passes): أبو بكر بن أبي شيبة > يزيد بن هارون > همام > إسحاق بن عبد الله بن أبي طلحة > أنس بن مالك
- why: The second isnad after the first matn is a real route (label missing_route); excluded by prompt rule 9, so the reader returns one route.

### cr-0147  sunni six-book / muslim  ->  **right** (stored_junk_dropped)
- text: «كلهم عن الزهري، بهذا الإسناد أهديت له حمار وحش . كما قال مالك»
- stored: [defective/non_narrator] يحيى بن يحيى > الليث بن سعد > الزهري || [unlabelled] محمد بن رمح > الليث بن سعد > الزهري
- reader (both passes): يحيى بن يحيى > الليث بن سعد > الزهري || محمد بن رمح > الليث بن سعد > الزهري  (+3 more routes)
- why: Reader's five routes match the three ح-groups ending «كلهم عن الزهري»; the junk stored chain «…> حش كما» is dropped.

### cr-0213  sunni six-book / tirmidhi  ->  **wrong** (second_isnad_after_matn)  fix: i
- text: «قال محمد بن رافع وأخبرنا محمد بن بشر أخبرنا علي بن نزار عن نزار عن عكرمة»
- stored: [correct/missing_route] محمد بن رافع > محمد بن بشر > سلام بن أبي عمرة > عكرمة > ابن عباس
- reader (both passes): محمد بن رافع > محمد بن بشر > سلام بن أبي عمرة > عكرمة > ابن عباس
- why: Second isnad written right after the first, before «نحوه»; no matn between, so it is a route; reader returned only the first.

### cr-0238  al-faqih / man-la-yahduruhu-al-faqih  ->  **right** (stored_junk_dropped)
- text: «و سأل موسى بن بكر أبا الحسن موسى بن جعفر عليهما السلام: عن الرجل يقوم في الصف وحده»
- stored: [correct/non_narrator_name] موسى بن بكر > أبا الحسن موسى بن جعفر || [unlabelled] موسى بن بكر > أبا الحسن موسى بن جعفر > حده
- reader (both passes): موسى بن بكر > أبا الحسن موسى بن جعفر
- why: Reader's two links match the correct stored chain; the junk link «حده» (matn word «وحده») is not added.

## Class (b): labelled correct, reader differs (57 reports, all read)

### cr-0001  sunni six-book / muslim  ->  **right** (artifact_clitic)
- text: «حدثنا عبيد الله بن عمر القواريري، وأحمد بن عبدة»
- stored: [unlabelled] عبيد الله بن عمر القواريري > سفيان بن عيينة > ابن أبي نجيح > مجاهد > قزعة > أبي سعيد الخدري || [correct] أحمد بن عبدة > سفيان بن عيينة > ابن أبي نجيح > مجاهد > قزعة > أبي سعيد الخدري
- reader (both passes): عبيد الله بن عمر القواريري > سفيان بن عيينة > ابن أبي نجيح > مجاهد > قزعة > أبي سعيد الخدري || أحمد بن عبدة > سفيان بن عيينة > ابن أبي نجيح > مجاهد > قزعة > أبي سعيد الخدري
- why: Stored name «أحمد بن عبدة» is written «وأحمد» (و attached); score.py drops it as 'not in text', so the reduced stored chain lacks it. The reader's two routes are the text's two routes.

### cr-0008  other imami / uyun-akhbar-al-rida  ->  **wrong** (inherited_chain)  fix: ii
- text: «349 - وبهذا الإسناد قال: قال رسول الله صلى الله عليه وآله: التائب من الذنب»
- stored: [correct] محمد بن أحمد بن الحسين بن يوسف البغدادي > على بن عنبسة > دارم بن قبيصة > على بن موسى الرضا > أبيه > آبائه > علي بن أبي طالب
- reader (both passes): 
- why: Text holds no name; stored (correct) chain is the full chain completed from the previous report. The reader can only return a back reference; applied, it would erase a correct chain.

### cr-0013  al-rabi / musnad-rabi  ->  **wrong** (balagha_gap)  fix: i
- text: «أبو عبيدة عن جابر بن زيد قال: بلغني عن أبي هريرة قال»
- stored: [correct] أبو عبيدة > جابر بن زيد > بلغني > أبي هريرة
- reader (both passes): أبو عبيدة > جابر بن زيد > أبي هريرة
- why: «بلغني» marks an unnamed intermediary; the stored (correct) chain keeps it as an anonymous link, the reader drops it. The prompt has no rule for it.

### cr-0014  other imami / kitab-al-zuhd  ->  **right** (artifact_clitic)
- text: «عن محمد بن أبي حمزة وحسين بن عثمان عن إسحاق بن عمار»
- stored: [unlabelled] ابن أبي عمير > محمد بن أبي حمزة > إسحاق بن عمار > أبي عبد الله || [correct] ابن أبي عمير > حسين بن عثمان > إسحاق بن عمار > أبي عبد الله
- reader (both passes): ابن أبي عمير > محمد بن أبي حمزة > إسحاق بن عمار > أبي عبد الله || ابن أبي عمير > حسين بن عثمان > إسحاق بن عمار > أبي عبد الله
- why: Same artifact («وحسين»); reader gives both parallel routes.

### cr-0022  pure canon / darimi  ->  **rep** (gloss_dropped)
- text: «علي هو ابن مسهر, هشام هو ابن عروة»
- stored: [correct] محمد ابن عيينة > علي هو ابن مسهر > هشام هو ابن عروة > محمد ابن عبد الرحمن ابن نوفل
- reader (both passes): محمد ابن عيينة > علي > هشام > محمد ابن عبد الرحمن ابن نوفل
- why: Stored keeps the source field's gloss «هو ابن …»; reader leaves it out (prompt rule 1). Same four links.

### cr-0023  other imami / kitab-al-ghayba-numani  ->  **right** (artifact_clitic)
- text: «محمد بن الحسين بن أبي الخطاب ومحمد بن عيسى وعبد الله بن عامر القصباني جميعا»
- stored: [unlabelled] محمد بن همام > جعفر بن محمد بن مالك > محمد بن الحسين بن أبي الخطاب > عبد الرحمن بن أبي نجران > الخشاب > معروف بن خربوذ > أبي جعفر || [unlabelled] محمد بن همام > جعفر بن محمد بن مالك > محمد بن عيسى > عبد الرحمن بن أبي نجران > الخشاب > معروف بن خربوذ > أبي جعفر
- reader (both passes): محمد بن همام > جعفر بن محمد بن مالك > محمد بن الحسين بن أبي الخطاب > عبد الرحمن بن أبي نجران > الخشاب > معروف بن خربوذ > أبي جعفر || محمد بن همام > جعفر بن محمد بن مالك > محمد بن عيسى > عبد الرحمن بن أبي نجران > الخشاب > معروف بن خربوذ > أبي جعفر  (+4 more routes)
- why: Same artifact («وعبد الله بن عامر»); 2x3 routes = stored 6.

### cr-0030  pure canon / darimi  ->  **rep** (gloss_dropped)
- text: «عطاء قاله محمد, يحيى ابن سعيد القطان»
- stored: [unlabelled] محمد ابن عيسى > هشيم > مغيرة > إبراهيم > الحسن > عطاء قاله محمد > يحيى ابن سعيد القطان > عثمان ابن الأسود || [unlabelled] محمد ابن عيسى > هشيم > مغيرة > إبراهيم > عبد الملك > عطاء قاله محمد > يحيى ابن سعيد القطان > عثمان ابن الأسود
- reader (both passes): محمد ابن عيسى > هشيم > مغيرة > إبراهيم > الحسن > عطاء > يحيى ابن سعيد القطان > عثمان ابن الأسود || محمد ابن عيسى > هشيم > مغيرة > إبراهيم > عبد الملك > عطاء > يحيى ابن سعيد القطان > عثمان ابن الأسود  (+2 more routes)
- why: Stored link «عطاء قاله محمد»; reader «عطاء». Four parallel routes otherwise identical.

### cr-0039  al-rabi / musnad-rabi  ->  **wrong** (balagha_gap)  fix: i
- text: «أبو عبيدة قال: بلغني عن جابر بن عبد الله قال سمعت رسول الله»
- stored: [correct] أبو عبيدة > بلغني > جابر بن عبد الله
- reader (both passes): أبو عبيدة > جابر بن عبد الله
- why: Same as cr-0013.

### cr-0041  other imami / mujam-al-ahadith-al-mutabara  ->  **right** (artifact_clitic)
- text: «عن الحلبي وزرارة، عن أبي عبد الله»
- stored: [unlabelled] أبي > سعد > ابن عيسى > ابن فضال > الحلبي > أبي عبد الله || [correct] أبي > سعد > ابن عيسى > ابن فضال > زرارة > أبي عبد الله
- reader (both passes): أبي > سعد > ابن عيسى > ابن فضال > الحلبي > أبي عبد الله || أبي > سعد > ابن عيسى > ابن فضال > زرارة > أبي عبد الله
- why: Same artifact («وزرارة»).

### cr-0042  pure canon / ahmad  ->  **rep** (gloss_dropped)
- text: «ليث يعني ابن سعد, بكير ابن عبد الله ابن الأشج»
- stored: [correct] هاشم ابن القاسم > ليث يعني ابن سعد > بكير ابن عبد الله ابن الأشج > سليمان ابن يسار > أبي هريرة
- reader (both passes): هاشم ابن القاسم > ليث > بكير ابن عبد الله ابن الأشج > سليمان ابن يسار > أبي هريرة
- why: Gloss «يعني ابن سعد» dropped by reader.

### cr-0043  other imami / kitab-al-mumin  ->  **rep** (prefix_noise)
- text: «168 - وعن أبي عبد الله عليه السلام قال»
- stored: [correct/surface_prefix] وعن أبي عبد الله
- reader (both passes): أبي عبد الله
- why: Stored surface keeps the connective «وعن»; reader «أبي عبد الله». The report continues the previous one but the single link is the same.

### cr-0051  pure canon / muwatta  ->  **right** (source_in_matn)
- text: «مالك ⏎ ⏎ أن علي ابن أبي طالب قال لا يقطع الصلاة شيء»
- stored: [correct] مالك
- reader (both passes): مالك > علي ابن أبي طالب
- why: Reader adds «علي ابن أبي طالب», named as the speaker of the saying (prompt rule 2). Differs from the source's own sanad field (the Pure Canon label convention).

### cr-0084  other imami / fadail-al-shia  ->  **right** (imam_named)
- text: «عن أبي عبد الله عليه السلام قال: قال أمير المؤمنين عليه السلام: أنا الراعي»
- stored: [correct] وبهذا الاسناد > سليمان الديلمي > أبي بصير > أبي عبد الله
- reader (both passes): سليمان الديلمي > أبي بصير > أبي عبد الله > أمير المؤمنين
- why: Imam named after the chain as the source of the saying = last link (owner ruling); stored lacks him and keeps «وبهذا الاسناد» as a link.

### cr-0086  sunni six-book / muslim  ->  **right** (artifact_clitic)
- text: «حدثنا يحيى بن يحيى، وإسحاق بن إبراهيم، - واللفظ ليحيى - قالا»
- stored: [unlabelled] يحيى بن يحيى > جرير > منصور > سالم > كريب > ابن عباس || [correct] إسحاق بن إبراهيم > جرير > منصور > سالم > كريب > ابن عباس
- reader (both passes): يحيى بن يحيى > جرير > منصور > سالم > كريب > ابن عباس || إسحاق بن إبراهيم > جرير > منصور > سالم > كريب > ابن عباس
- why: Same artifact («وإسحاق»); gloss correctly left out.

### cr-0096  pure canon / ahmad  ->  **rep** (gloss_dropped)
- text: «سعيد يعني المقبري, أبي عبيدة»
- stored: [correct] هاشم > ليث > سعيد يعني المقبري > أبي عبيدة > سعيد ابن يسار > أبا هريرة
- reader (both passes): هاشم > ليث > سعيد > أبي عبيدة > سعيد ابن يسار > أبا هريرة
- why: Gloss «يعني المقبري» dropped by reader.

### cr-0126  other imami / al-amali-saduq  ->  **wrong** (inherited_chain)  fix: ii
- text: «15 - وبهذا الاسناد، قال: قال الصادق جعفر بن محمد (عليهما السلام): ما من قدم سعت إلى الجمعة»
- stored: [correct] الحسن بن إبراهيم بن ناتانه > علي بن إبراهيم > أبيه > محمد بن أبي عمير > أبي زياد النهدي > عبد الله بن بكير
- reader (both passes): الصادق جعفر بن محمد
- why: Stored six-name chain comes from the previous report; the reader sees only the Imam named here. Applying it would replace six links by one.

### cr-0132  sunni six-book / nasai  ->  **right** (artifact_clitic)
- text: «عن ابن شهاب، عن الحسن، وعبد الله، ابنى محمد عن أبيهما»
- stored: [unlabelled] سليمان بن داود > عبد الله بن وهب > يونس > ابن شهاب > الحسن > أبيهما > علي بن أبي طالب || [unlabelled] سليمان بن داود > عبد الله بن وهب > يونس > ابن شهاب > عبد الله ابنى محمد > أبيهما > علي بن أبي طالب
- reader (both passes): سليمان بن داود > عبد الله بن وهب > يونس > ابن شهاب > الحسن > أبيهما > علي بن أبي طالب || سليمان بن داود > عبد الله بن وهب > مالك > ابن شهاب > الحسن > أبيهما > علي بن أبي طالب  (+4 more routes)
- why: Same artifact («وأسامة»); 3x2 routes; «عبد الله» for the stored «عبد الله ابنى محمد» is the name alone.

### cr-0136  other imami / al-amali-mufid  ->  **right** (imam_named)
- text: «قال: قال أمير المؤمنين عليه السلام: لو رأى العبد أجله»
- stored: [correct] أبو حفص عمر بن محمد المعروف بابن الزيات > علي بن مهرويه القزويني > داود بن سليمان الغازي > الرضا علي بن موسى > أبي موسى بن جعفر > أبي جعفر بن محمد > أبي محمد بن علي > أبي علي بن الحسين > أبي الحسين بن علي
- reader (both passes): أبو حفص عمر بن محمد المعروف بابن الزيات > علي بن مهرويه القزويني > داود بن سليمان الغازي > الرضا علي بن موسى > موسى بن جعفر > جعفر بن محمد > محمد بن علي > علي بن الحسين > الحسين بن علي > أمير المؤمنين
- why: Reader adds the Imam named after the chain; relation words «أبي» dropped (rule 1).

### cr-0145  other imami / al-tawhid-saduq  ->  **right** (artifact_clitic)
- text: «حدثنا محمد بن يحيى العطار وأحمد بن إدريس جميعا»
- stored: [unlabelled] أبي > محمد بن يحيى العطار > محمد بن أحمد بن يحيى بن عمران الأشعري > علي بن إسماعيل > حماد بن عيسى > حريز > زرارة > أبي جعفر || [correct] أبي > أحمد بن إدريس > محمد بن أحمد بن يحيى بن عمران الأشعري > علي بن إسماعيل > حماد بن عيسى > حريز > زرارة > أبي جعفر
- reader (both passes): أبي > محمد بن يحيى العطار > محمد بن أحمد بن يحيى بن عمران الأشعري > علي بن إسماعيل > حماد بن عيسى > حريز > زرارة > أبي جعفر || أبي > أحمد بن إدريس > محمد بن أحمد بن يحيى بن عمران الأشعري > علي بن إسماعيل > حماد بن عيسى > حريز > زرارة > أبي جعفر  (+2 more routes)
- why: Same artifact («وأحمد بن إدريس»); the blessing «رحمهما الله» correctly left out.

### cr-0151  other imami / uyun-akhbar-al-rida  ->  **rep** (backref_link)
- text: «7 - وبهذا الإسناد قال: قال رسول الله»
- stored: [correct] وبهذا الإسناد
- reader (both passes): 
- why: Stored chain is the lone back reference «وبهذا الإسناد»; the reader gives the same back_reference link, which score.py drops, so its route is empty. No name in the text.

### cr-0155  sunni six-book / muslim  ->  **right** (artifact_clitic)
- text: «حدثني محمد بن رافع، وعبد بن حميد»
- stored: [unlabelled] محمد بن رافع > عبد الرزاق > معمر > الزهري > سالم > ابن عمر || [correct] عبد بن حميد > عبد الرزاق > معمر > الزهري > سالم > ابن عمر
- reader (both passes): محمد بن رافع > عبد الرزاق > معمر > الزهري > سالم > ابن عمر || عبد بن حميد > عبد الرزاق > معمر > الزهري > سالم > ابن عمر
- why: Same artifact («وعبد بن حميد»).

### cr-0163  other imami / kitab-al-ghayba-tusi  ->  **label_wrong** (stored_missing_link)
- text: «حدثني أبو الحسين محمد بن علي الشجاعي الكاتب قال: أخبرنا أبو عبد الله محمد بن إبراهيم المعروف بابن أبي زينب النعماني الكاتب قال: أخبرنا محمد بن عثمان»
- stored: [correct] به أبو عبد الله أحمد بن عبدون المعروف بابن الحاشر > أبو الحسين محمد بن علي الشجاعي الكاتب > محمد بن عثمان بن علان الذهبي البغدادي بدمشق > أبو بكر بن أبي خيثمة > علي بن الجعد > زهير بن معاوية > زياد بن خيثمة > الأسود بن سعيد الهمداني > جابر بن سمرة
- reader (both passes): أبو عبد الله أحمد بن عبدون المعروف بابن الحاشر > أبو الحسين محمد بن علي الشجاعي الكاتب > أبو عبد الله محمد بن إبراهيم المعروف بابن أبي زينب النعماني الكاتب > محمد بن عثمان بن علان الذهبي البغدادي > أبو بكر بن أبي خيثمة > علي بن الجعد > زهير بن معاوية > زياد بن خيثمة > الأسود بن سعيد الهمداني > جابر بن سمرة
- why: Stored chain skips the link «أبو عبد الله محمد بن إبراهيم …النعماني الكاتب» that the text writes; labelled 'correct' (note: «chain matches the text»). Reader right.

### cr-0164  other imami / kamal-al-din  ->  **wrong** (inherited_chain)  fix: ii
- text: «و بهذا الإسناد عن الحارث بن المغيرة عن أبي عبد الله عليه السلام»
- stored: [unlabelled] أبي > سعد بن عبد الله > محمد بن عيسى بن عبيد > يونس بن عبد الرحمن > الحارث بن المغيرة > أبي عبد الله || [correct] أبي > عبد الله بن جعفر الحميري > محمد بن عيسى بن عبيد > يونس بن عبد الرحمن > الحارث بن المغيرة > أبي عبد الله
- reader (both passes): الحارث بن المغيرة > أبي عبد الله
- why: Stored chains hold the inherited names before «الحارث بن المغيرة»; reader returns only what the text shows.

### cr-0165  sunni six-book / muslim  ->  **right** (artifact_clitic)
- text: «أبو بكر بن أبي شيبة، وعمرو الناقد، وزهير بن حرب، قالوا حدثنا وكيع»
- stored: [unlabelled] أبو بكر بن أبي شيبة > وكيع > سفيان > إسماعيل بن أمية > محمد بن يحيى بن حبان > يحيى بن عمارة > أبي سعيد الخدري || [correct] عمرو الناقد > وكيع > سفيان > إسماعيل بن أمية > محمد بن يحيى بن حبان > يحيى بن عمارة > أبي سعيد الخدري
- reader (both passes): أبو بكر بن أبي شيبة > وكيع > سفيان > إسماعيل بن أمية > محمد بن يحيى بن حبان > يحيى بن عمارة > أبي سعيد الخدري || عمرو الناقد > وكيع > سفيان > إسماعيل بن أمية > محمد بن يحيى بن حبان > يحيى بن عمارة > أبي سعيد الخدري  (+1 more routes)
- why: Same artifact («وعمرو الناقد»).

### cr-0167  other imami / al-amali-mufid  ->  **right** (source_in_matn)
- text: «لما بويع عثمان سمعت المقداد بن الأسود الكندي رحمه الله يقول»
- stored: [correct] أبو الحسن علي بن محمد الكاتب > الحسن بن علي الزعفراني > إبراهيم بن محمد الثقفي > محمد بن علي > الحسين بن سفيان > أبيه > لوط بن يحيى > عبد الرحمن بن جندب > أبيه
- reader (both passes): أبو الحسن علي بن محمد الكاتب > الحسن بن علي الزعفراني > إبراهيم بن محمد الثقفي > محمد بن علي > الحسين بن سفيان > أبيه > لوط بن يحيى > عبد الرحمن بن جندب > أبيه > المقداد بن الأسود الكندي
- why: «سمعت X» names the source (prompt rule 5); stored lacks him.

### cr-0168  other imami / al-amali-mufid  ->  **rep** (backref_link)
- text: «43 - وبالإسناد الأول عن علي بن مهزيار، عن واصل بن سليمان»
- stored: [correct] وبالإسناد الأول > علي بن مهزيار > واصل بن سليمان > ابن سنان > أبا عبد الله
- reader (both passes): علي بن مهزيار > واصل بن سليمان > ابن سنان > أبا عبد الله
- why: Stored keeps «وبالإسناد الأول» as first link; reader has it as back_reference (dropped by score.py). Names identical.

### cr-0176  other imami / thawab-al-amal  ->  **right** (imam_named)
- text: «عن الحسن بن صدقه قال قال أبو الحسن الأول ع قیلوا»
- stored: [correct] أحمد بن محمد > أبیه > محمد بن أحمد > عبد الله الرازی > منصور بن العباس > عمرو بن سعید > الحسن بن صدقه
- reader (both passes): أحمد بن محمد > أبیه > محمد بن أحمد > عبد الله الرازی > منصور بن العباس > عمرو بن سعید > الحسن بن صدقه > أبو الحسن الأول
- why: Imam named after the chain is the last link; stored stops at الحسن بن صدقه.

### cr-0190  other imami / mujam-al-ahadith-al-mutabara  ->  **rep** (orthography)
- text: «محمد بن عبدالله ومحمد بن يحيى جميعا، عن عبدالله بن جعفر الحميري»
- stored: [correct] محمد بن عبد الله > عبد الله بن جعفر الحميري || [unlabelled] محمد بن يحيى > عبد الله بن جعفر الحميري
- reader (both passes): محمد بن عبدالله > عبدالله بن جعفر الحميري || محمد بن يحيى > عبدالله بن جعفر الحميري
- why: Stored «عبد الله», text/reader «عبدالله» (no space); also artifact_clitic. Same two routes.

### cr-0192  other imami / kitab-al-mumin  ->  **rep** (prefix_noise)
- text: «172 - وعن أبي عبد الله عليه السلام قال»
- stored: [correct/surface_prefix] وعن أبي عبد الله
- reader (both passes): أبي عبد الله
- why: Same as cr-0043.

### cr-0193  other imami / uyun-akhbar-al-rida  ->  **wrong** (inherited_chain)  fix: ii
- text: «330 - بهذا الإسناد عن النبي صلى الله عليه وآلهقال: من كف غضبه»
- stored: [unlabelled] محمد بن أحمد بن الحسين بن يوسفالبغدادي > على بن عنبسة > فاطمة بنت على بن موسى > أبي عليا يحدث > أبيه > جعفر بن محمد > أبيه > أبيهما على بن الحسين > أبيه > أبي طالب || [correct] محمد بن أحمد بن الحسين بن يوسفالبغدادي > على بن عنبسة > فاطمة بنت على بن موسى > أبي عليا يحدث > أبيه > جعفر بن محمد > أبيه > أبيهما على بن الحسين > عمه > أبي طالب
- reader (both passes): 
- why: Text has no name; stored is an eleven-name inherited chain.

### cr-0194  other imami / kitab-al-mumin  ->  **rep** (backref_honorific)
- text: «91 - وعنه (ع) قال لكل شئ شئ يستريح إليه»
- stored: [correct] وعنه ع
- reader (both passes): وعنه
- why: Formula-only chain: stored «وعنه ع», reader «وعنه»; honorific only.

### cr-0196  sunni six-book / tirmidhi  ->  **rep** (gloss_in_stored)
- text: «عن ابن عباس ( ما كذب الفؤاد ما رأى ) قال رآه بقلبه»
- stored: [unlabelled] عبد بن حميد > عبد الرزاق > إسرائيل > سماك > عكرمة > ابن عباس ما كذب الفؤاد ما رأى || [correct] عبد بن حميد > ابن أبي رزمة > إسرائيل > سماك > عكرمة > ابن عباس ما كذب الفؤاد ما رأى
- reader (both passes): عبد بن حميد > عبد الرزاق > إسرائيل > سماك > عكرمة > ابن عباس || عبد بن حميد > ابن أبي رزمة > إسرائيل > سماك > عكرمة > ابن عباس  (+1 more routes)
- why: Stored last link carries the quoted verse; reader «ابن عباس». Three routes incl. «وابن أبي رزمة، وأبو نعيم» correct.

### cr-0200  other imami / thawab-al-amal  ->  **rep** (prefix_noise)
- text: «عن الحسين بن علي بن بنت إلياس الخزاز عن الرضا ع قال»
- stored: [correct] محمد بن الحسن > محمد بن الحسن الصفار > محمد بن عیسی > الحسین بن علی بن بنت إلیاس الخزاز > الرضا ع
- reader (both passes): محمد بن الحسن > محمد بن الحسن الصفار > محمد بن عیسی > الحسین بن علی بن بنت إلیاس الخزاز > الرضا
- why: Honorific «ع» in the stored surface only.

### cr-0201  other imami / kamal-al-din  ->  **wrong** (inherited_chain)  fix: ii
- text: «و بهذا الإسناد قال قال علي بن الحسين سيد العابدين ع القائم منا»
- stored: [unlabelled] علي بن أحمد الدقاق > محمد بن أبي عبد الله الكوفي > موسى بن عمران النخعي > عمه الحسين بن يزيد > حمزة بن حمران > أبيه حمران بن أعين > سعيد بن جبير > سيد العابدين علي بن الحسين || [correct] محمد بن أحمد الشيباني > محمد بن أبي عبد الله الكوفي > موسى بن عمران النخعي > عمه الحسين بن يزيد > حمزة بن حمران > أبيه حمران بن أعين > سعيد بن جبير > سيد العابدين علي بن الحسين
- reader (both passes): علي بن الحسين سيد العابدين
- why: Stored chain (inherited) is eight names; reader returns the Imam named here only.

### cr-0203  other imami / al-amali-mufid  ->  **rep** (relation_word)
- text: «عن أبيه، عن جده يعلى بن مرة قال: سمعت رسول الله»
- stored: [correct] محمد بن عمران المرزباني > أبو بكر أحمد بن محمد بن عيسى المكي > عبد الله بن أحمد بن حنبل > عبد الرحمن بن صالح > محمد بن سعد الأنصاري > عمر بن عبد الله ابن يعلى بن مرة > أبيه > جده يعلى بن مرة
- reader (both passes): محمد بن عمران المرزباني > أبو بكر أحمد بن محمد بن عيسى المكي > عبد الله بن أحمد بن حنبل > عبد الرحمن بن صالح > محمد بن سعد الأنصاري > عمر بن عبد الله ابن يعلى بن مرة > أبيه > يعلى بن مرة
- why: Stored «جده يعلى بن مرة», reader «يعلى بن مرة» (prompt rule 1: relation word before a name gives the name alone).

### cr-0204  sunni six-book / muslim  ->  **right** (artifact_clitic)
- text: «حدثنا أبو بكر بن أبي شيبة، وأبو كريب قالا حدثنا وكيع»
- stored: [unlabelled] أبو بكر بن أبي شيبة > وكيع > سفيان > سلمة بن كهيل > كريب > ابن عباس || [correct] أبو كريب > وكيع > سفيان > سلمة بن كهيل > كريب > ابن عباس
- reader (both passes): أبو بكر بن أبي شيبة > وكيع > سفيان > سلمة بن كهيل > كريب > ابن عباس || أبو كريب > وكيع > سفيان > سلمة بن كهيل > كريب > ابن عباس
- why: Same artifact («وأبو كريب»).

### cr-0208  other imami / mujam-al-ahadith-al-mutabara  ->  **right** (artifact_clitic)
- text: «علي بن ابراهيم عن أبيه ومحمد بن اسماعيل عن الفضل ابن شاذان جميعا عن حماد»
- stored: [unlabelled] علي بن ابراهيم > أبيه > حماد بن عيسى > حريز > زرارة || [correct] محمد بن اسماعيل > الفضل ابن شاذان > حماد بن عيسى > حريز > زرارة
- reader (both passes): علي بن ابراهيم > أبيه > حماد بن عيسى > حريز > زرارة || محمد بن اسماعيل > الفضل ابن شاذان > حماد بن عيسى > حريز > زرارة
- why: Same artifact («ومحمد بن اسماعيل»).

### cr-0215  sunni six-book / muslim  ->  **rep** (name_scope)
- text: «عن مالك بن أنس، عن  أبي نعيم، وهب بن كيسان أن جابر بن عبد الله»
- stored: [correct] محمد بن حاتم > عبد الرحمن بن مهدي > مالك بن أنس > أبي نعيم > جابر بن عبد الله || [unlabelled] محمد بن حاتم > عبد الرحمن بن مهدي > مالك بن أنس > هب بن كيسان > جابر بن عبد الله
- reader (both passes): محمد بن حاتم > عبد الرحمن بن مهدي > مالك بن أنس > أبي نعيم وهب بن كيسان > جابر بن عبد الله
- why: Stored 'correct' chain has only the kunya «أبي نعيم» (another stored chain «هب بن كيسان»); text writes kunya then name; reader gives one link «أبي نعيم وهب بن كيسان».

### cr-0218  sunni six-book / bukhari  ->  **rep** (relation_word)
- text: «عن أنس بن مالك، عن خالته أم حرام بنت ملحان، قالت»
- stored: [correct] عبد الله بن يوسف > الليث > يحيى > محمد بن يحيى بن حبان > أنس بن مالك > خالته أم حرام بنت ملحان
- reader (both passes): عبد الله بن يوسف > الليث > يحيى > محمد بن يحيى بن حبان > أنس بن مالك > أم حرام بنت ملحان
- why: Stored «خالته أم حرام…», reader «أم حرام بنت ملحان».

### cr-0220  other imami / mujam-al-ahadith-al-mutabara  ->  **rep** (orthography)
- text: «محمد بن عبدالله ومحمد بن يحيى جميعا، عن عبدالله بن جعفر الحميري»
- stored: [correct] محمد بن عبد الله > عبد الله بن جعفر الحميري || [unlabelled] محمد بن يحيى > عبد الله بن جعفر الحميري
- reader (both passes): محمد بن عبدالله > عبدالله بن جعفر الحميري || محمد بن يحيى > عبدالله بن جعفر الحميري
- why: Same as cr-0190.

### cr-0224  other imami / kitab-al-ghayba-tusi  ->  **right** (imam_named)
- text: «خرجت إلينا ألواح من أبي الحسن عليه السلام»
- stored: [correct] عنه > أحمد بن مهران > محمد بن علي > محمد بن سنان > الحسين بن المختار || [unlabelled] عنه > أحمد بن مهران > محمد بن علي > علي بن الحكم > الحسين بن المختار
- reader (both passes): عنه > أحمد بن مهران > محمد بن علي > محمد بن سنان > الحسين بن المختار > أبي الحسن || عنه > أحمد بن مهران > محمد بن علي > علي بن الحكم > الحسين بن المختار > أبي الحسن
- why: Imam named as the source of the tablets; added by reader.

### cr-0229  other imami / al-khisal  ->  **right** (imam_named)
- text: «عن الاصبغ بن نباتة قال: كان أمير المؤمنين عليه السلام يقول»
- stored: [unlabelled] أبي > محمد بن يحيى العطار > أبوسعيد سهل بن زياد الآدمي > محمد بن الحسين بن زيد الزيات > عمرو بن عثمان الخزاز > ثابت بن دينار > سعد بن طريف الخفاف > الاصبغ بن نباتة || [correct] أبي > أحمد بن إدريس > أبوسعيد سهل بن زياد الآدمي > محمد بن الحسين بن زيد الزيات > عمرو بن عثمان الخزاز > ثابت بن دينار > سعد بن طريف الخفاف > الاصبغ بن نباتة
- reader (both passes): أبي > محمد بن يحيى العطار > أبوسعيد سهل بن زياد الآدمي > محمد بن الحسين بن زيد الزيات > عمرو بن عثمان الخزاز > ثابت بن دينار > سعد بن طريف الخفاف > الاصبغ بن نباتة > أمير المؤمنين || أبي > أحمد بن إدريس > أبوسعيد سهل بن زياد الآدمي > محمد بن الحسين بن زيد الزيات > عمرو بن عثمان الخزاز > ثابت بن دينار > سعد بن طريف الخفاف > الاصبغ بن نباتة > أمير المؤمنين
- why: Imam added; plus artifact_clitic («وأحمد بن إدريس»).

### cr-0230  other imami / sifat-al-shia  ->  **rep** (prefix_noise)
- text: «حدثنا محمد بن علي ماجيلويه رحمه الله عن أبي عبد الله ع قال»
- stored: [correct] محمد بن علي ماجيلويه > أبي عبد الله ع
- reader (both passes): محمد بن علي ماجيلويه > أبي عبد الله
- why: Honorific only.

### cr-0233  other imami / uyun-akhbar-al-rida  ->  **right** (imam_named)
- text: «120 - وبهذا الإسناد قال: قال على بن أبي طالب عليه السلام: إنه لو رأى العبد»
- stored: [correct] وبهذا الإسناد
- reader (both passes): على بن أبي طالب
- why: Stored is the lone back reference; the reader adds the Imam named as the speaker.

### cr-0234  other imami / kitab-al-ghayba-tusi  ->  **label_wrong** (stored_merged_routes)
- text: «عن أبي عبد الله عليه السلام؛ ومحمد بن الحسين عن إبراهيم بن أبي يحيى المدني عن أبي هارون العبدي»
- stored: [correct] وبهذا الإسناد > محمد بن يحيى > محمد الحسين > مسعدة بن زياد > أبي عبد الله > إبراهيم بن أبي يحيى المدني > أبي هارون العبدي > أبي سعيد الخدري || [unlabelled] وبهذا الإسناد > محمد بن يحيى > محمد الحسين > مسعدة بن زياد > محمد بن الحسين > إبراهيم بن أبي يحيى المدني > أبي هارون العبدي > أبي سعيد الخدري
- reader (both passes): محمد بن يحيى > محمد الحسين > مسعدة بن زياد > أبي عبد الله || محمد بن الحسين > إبراهيم بن أبي يحيى المدني > أبي هارون العبدي > أبي سعيد الخدري
- why: The ';' starts a second isnad; the stored 'correct' chain runs «أبي عبد الله > إبراهيم بن أبي يحيى» across it. Reader writes two routes. Judgement call on how the two isnads relate; the join the stored chain makes is not in the text.

### cr-0240  sunni six-book / tirmidhi  ->  **rep** (relation_word)
- text: «عن حميد بن عبد الرحمن، عن أمه أم كلثوم بنت عقبة، قالت سمعت رسول الله»
- stored: [correct] أحمد بن منيع > إسماعيل بن إبراهيم > معمر > الزهري > حميد بن عبد الرحمن > أمه أم كلثوم بنت عقبة
- reader (both passes): أحمد بن منيع > إسماعيل بن إبراهيم > معمر > الزهري > حميد بن عبد الرحمن > أم كلثوم بنت عقبة
- why: Stored «أمه أم كلثوم…», reader name alone.

### cr-0244  sunni six-book / muslim  ->  **right** (artifact_clitic)
- text: «سعيد بن منصور، وأبو الربيع العتكي، وقتيبة بن سعيد، قالوا حدثنا حماد»
- stored: [unlabelled] سعيد بن منصور > حماد > أيوب > أبي قلابة > أبي أسماء > ثوبان || [correct] أبو الربيع العتكي > حماد > أيوب > أبي قلابة > أبي أسماء > ثوبان
- reader (both passes): سعيد بن منصور > حماد > أيوب > أبي قلابة > أبي أسماء > ثوبان || أبو الربيع العتكي > حماد > أيوب > أبي قلابة > أبي أسماء > ثوبان  (+1 more routes)
- why: Same artifact («وأبو الربيع»); gloss «- وهو ابن زيد -» left out.

### cr-0247  other imami / kitab-al-ghayba-tusi  ->  **rep** (relation_word)
- text: «عن علي بن جعفر عن أخيه موسى بن جعفر عليه السلام قال»
- stored: [correct] سعد بن عبد الله > أحمد بن محمد بن عيسى > موسى بن قاسم البجلي > علي بن جعفر > أخيه موسى بن جعفر || [unlabelled] سعد بن عبد الله > أحمد بن محمد بن عيسى > أبي قتادة علي بن محمد بن حفص > علي بن جعفر > أخيه موسى بن جعفر
- reader (both passes): سعد بن عبد الله > أحمد بن محمد بن عيسى > موسى بن قاسم البجلي > علي بن جعفر > موسى بن جعفر || سعد بن عبد الله > أحمد بن محمد بن عيسى > أبي قتادة علي بن محمد بن حفص > علي بن جعفر > موسى بن جعفر
- why: Stored «أخيه موسى بن جعفر», reader «موسى بن جعفر»; plus artifact_clitic («وأبي قتادة»).

### cr-0261  other imami / sifat-al-shia  ->  **rep** (prefix_noise)
- text: «أبي رحمه الله قال حدثنا سعد بن عبد الله عن الحارثي عن أبي عبد الله ع قال»
- stored: [correct] أبي > سعد بن عبد الله > الحارثي > أبي عبد الله ع
- reader (both passes): أبي > سعد بن عبد الله > الحارثي > أبي عبد الله
- why: Honorific only.

### cr-0265  other imami / al-khisal  ->  **right** (artifact_clitic)
- text: «حدثنا سعد بن عبد الله، وعبد الله بن جعفر الحميري جميعا»
- stored: [correct] أبي > سعد بن عبد الله > هارون بن مسلم > مسعدة بن صدقة الربعي > جعفر بن محمد > أبيه > آبائه > علي || [correct] أبي > عبد الله بن جعفر الحميري > هارون بن مسلم > مسعدة بن صدقة الربعي > جعفر بن محمد > أبيه > آبائه > علي
- reader (both passes): أبي > سعد بن عبد الله > هارون بن مسلم > مسعدة بن صدقة الربعي > جعفر بن محمد > أبيه > آبائه > علي || أبي > عبد الله بن جعفر الحميري > هارون بن مسلم > مسعدة بن صدقة الربعي > جعفر بن محمد > أبيه > آبائه > علي
- why: Same artifact («وعبد الله»).

### cr-0266  sunni six-book / bukhari  ->  **wrong** (second_isnad_after_matn)  fix: i
- text: «رواه سعيد عن مالك. وقال عمر بن حمزة سمعت سالما سمعت ابن عمر … وقال أبو اليمان أخبرنا شعيب، عن الزهري»
- stored: [correct/missing_route_taliq] مقدم بن محمد > عمي القاسم بن يحيى > عبيد الله > نافع > ابن عمر
- reader (both passes): مقدم بن محمد > القاسم بن يحيى > عبيد الله > نافع > ابن عمر
- why: Main chain right («عمي القاسم» -> «القاسم بن يحيى» is rep) but the appended routes the label requires are excluded by prompt rule 9. Same outcome as stored; the label calls the report defective.

### cr-0267  al-faqih / man-la-yahduruhu-al-faqih  ->  **rep** (noise_in_stored)
- text: «وقال علي بن محمد و محمد بن علي عليه السلام: «من قال بالجسم»
- stored: [unlabelled] علي بن محمد || [correct] محمد بن علي من
- reader (both passes): علي بن محمد || محمد بن علي
- why: Stored link «محمد بن علي من» carries the first matn word; reader «محمد بن علي»; two single-link routes by prompt rule 3.

### cr-0268  sunni six-book / muslim  ->  **rep** (noise_in_stored)
- text: «عن أبي هريرة، - رضى الله عنه - رواية قال»
- stored: [correct] زهير بن حرب > سفيان بن عيينة > أبي الزناد > الأعرج > أبي هريرة - - رواية
- reader (both passes): زهير بن حرب > سفيان بن عيينة > أبي الزناد > الأعرج > أبي هريرة
- why: Stored «أبي هريرة - - رواية»; reader «أبي هريرة».

### cr-0273  al-faqih / man-la-yahduruhu-al-faqih  ->  **right** (imam_named)
- text: «قال : قلت لأبي عبد الله عليه السلام شجرة أصلها في الحل»
- stored: [correct] معاوية بن عمار
- reader (both passes): معاوية بن عمار > أبي عبد الله
- why: «قلت لـ X» is a link (prompt rule 5); stored stops at معاوية بن عمار.

### cr-0280  other imami / al-khisal  ->  **rep** (relation_word)
- text: «حدثني أبي موسى بن جعفر قال: حدثني أبي جعفر ابن محمد»
- stored: [correct] حمزة بن محمد بن أحمد العلوي > أبوالحسن علي بن محمد البزاز > أبوأحمد داود بن سليمان الغازي > علي ابن موسى الرضا > أبي موسى بن جعفر > أبي جعفر ابن محمد > أبي محمد بن علي الباقر > أبي علي بن الحسين > أبي الحسين بن علي > أبي أمير المؤمنين
- reader (both passes): حمزة بن محمد بن أحمد العلوي > أبوالحسن علي بن محمد البزاز > أبوأحمد داود بن سليمان الغازي > علي ابن موسى الرضا > موسى بن جعفر > جعفر ابن محمد > محمد بن علي الباقر > علي بن الحسين > الحسين بن علي > أمير المؤمنين
- why: Stored «أبي موسى بن جعفر», reader «موسى بن جعفر»; all ten links the same persons in the same order.

### cr-0283  sunni six-book / muslim  ->  **right** (source_in_matn)
- text: «عن خالد بن عمير العدوي، قال خطبنا عتبة بن غزوان فحمد الله»
- stored: [correct] شيبان بن فروخ > سليمان بن المغيرة > حميد بن هلال > خالد بن عمير العدوي
- reader (both passes): شيبان بن فروخ > سليمان بن المغيرة > حميد بن هلال > خالد بن عمير العدوي > عتبة بن غزوان
- why: Companion who addressed them is the source of the saying; reader adds him (rule 2).

### cr-0284  other imami / kamil-al-ziyarat  ->  **rep** (bracket_variant)
- text: «عن يونس بن عبد الله [عبد الرحمن] عن قدامة بن ملك [مالك]»
- stored: [correct] أبي > محمد بن يحيى العطار > حمدان بن سليمان النيسابوري > عبد الله بن محمد اليماني > منيع بن الحجاج > يونس بن عبد الله عبد الرحمن > قدامة بن ملك مالك > أبي عبد الله ع || [unlabelled] علي بن الحسين و محمد بن الحسن > محمد بن يحيى العطار > حمدان بن سليمان النيسابوري > عبد الله بن محمد اليماني > منيع بن الحجاج > يونس بن عبد الله عبد الرحمن > قدامة بن ملك مالك > أبي عبد الله ع
- reader (both passes): أبي > محمد بن يحيى العطار > حمدان بن سليمان النيسابوري > عبد الله بن محمد اليماني > منيع بن الحجاج > يونس بن عبد الله > قدامة بن ملك > أبي عبد الله || علي بن الحسين > محمد بن يحيى العطار > حمدان بن سليمان النيسابوري > عبد الله بن محمد اليماني > منيع بن الحجاج > يونس بن عبد الله > قدامة بن ملك > أبي عبد الله  (+1 more routes)
- why: Editor's bracketed variants left out by reader; co-transmitters «أبي و علي بن الحسين و محمد بن الحسن» split into three routes (stored merged two of them in an unlabelled chain).

## Class (c): labelled defective, reader differs: random 40 of 69 read (seed 20261122) plus cr-0266 (in (b) above)

### cr-0010  sunni six-book / muslim  ->  **wrong** (source_dropped)  fix: i
- text: «حدثني نبيه بن وهب، أن عمر بن عبيد الله بن معمر، رمدت عينه … فنهاه أبان بن عثمان … وحدث عن عثمان بن عفان»
- stored: [defective/missing_link] وحدثناه إسحاق بن إبراهيم الحنظلي > عبد الصمد بن عبد الوارث > أبي > أيوب بن موسى > نبيه بن وهب > عثمان بن عفان
- reader (both passes): إسحاق بن إبراهيم الحنظلي > عبد الصمد بن عبد الوارث > أبي > أيوب بن موسى > نبيه بن وهب
- why: Reader stops at «نبيه بن وهب»: loses عمر بن عبيد الله (rule 5 «أن X»), أبان بن عثمان and عثمان بن عفان. Worse than stored, which at least ends at عثمان.

### cr-0020  sunni six-book / tirmidhi  ->  **wrong** (second_isnad_after_matn)  fix: i
- text: «حدثنا بذلك هناد وقتيبة قالا حدثنا وكيع عن ثابت بن أبي صفية»
- stored: [defective/non_narrator+truncated_name] أبو عيسى > ثابت بن أبي صفية || [unlabelled] روى > ثابت بن أبي صفية
- reader (both passes): وكيع > ثابت بن أبي صفية > أبي جعفر > جابر
- why: Reader's «وكيع > ثابت > أبي جعفر > جابر» is much better than stored, but the heads «هناد وقتيبة» are written after the saying and are missing.

### cr-0026  sunni six-book / bukhari  ->  **right** (stored_junk_dropped)
- text: «حدثنا موسى، حدثنا معتمر، وقال، لم يبتئر. وقال خليفة حدثنا معتمر»
- stored: [unlabelled] موسى > معتمر || [unlabelled] موسى > خليفة > معتمر
- reader (both passes): موسى > معتمر
- why: Label: false link (stored «موسى > خليفة > معتمر»). Reader gives «موسى > معتمر». «وقال خليفة …» is a separate appended route (note-only by rule 9).

### cr-0048  other imami / al-khisal  ->  **wrong** (irsal_gap)  fix: i
- text: «عن محمد بن عيسى بإسناده يرفعه إلى أبي جعفر عليه السلام»
- stored: [unlabelled] أبي > محمد بن يحيى العطار > محمد بن أحمد بن يحيى > محمد بن عيسى بإسناده يرفعه إلى أبي جعفر || [unlabelled] أبي > أحمد بن إدريس > محمد بن أحمد بن يحيى > محمد بن عيسى بإسناده يرفعه إلى أبي جعفر
- reader (both passes): أبي > محمد بن يحيى العطار > محمد بن أحمد بن يحيى > محمد بن عيسى > أبي جعفر || أبي > أحمد بن إدريس > محمد بن أحمد بن يحيى > محمد بن عيسى > أبي جعفر  (+2 more routes)
- why: Reader cleans the name but writes «محمد بن عيسى > أبي جعفر» as if direct; the label wants the name plus an anonymous gap for «بإسناده يرفعه».

### cr-0053  sunni six-book / tirmidhi  ->  **wrong** (source_in_matn_missed)  fix: i
- text: «فجاء المغيرة بن شعبة فصعد المنبر … أما إني سمعت رسول الله صلى الله عليه وسلم يقول»
- stored: [unlabelled] أحمد بن منيع > قران بن تمام الأسدي > سعيد بن عبيد الطائي > علي بن ربيعة الأسدي || [unlabelled] أحمد بن منيع > مروان بن معاوية > سعيد بن عبيد الطائي > علي بن ربيعة الأسدي
- reader (both passes): أحمد بن منيع > قران بن تمام الأسدي > سعيد بن عبيد الطائي > علي بن ربيعة الأسدي || أحمد بن منيع > مروان بن معاوية > سعيد بن عبيد الطائي > علي بن ربيعة الأسدي  (+1 more routes)
- why: المغيرة is the Companion source of the saying (rule 2); the reader kept the three routes but did not add him.

### cr-0078  al-rabi / musnad-rabi  ->  **right** (plain_new_chain)
- text: «قال الربيع: بلغني عن جويبر عن الضحاك عن ابن عباس»
- stored: 
- reader (both passes): جويبر > الضحاك > ابن عباس
- why: Stored had no chain; reader reads «جويبر > الضحاك > ابن عباس» (compiler «الربيع» not a link, his own «بلغني» not a link).

### cr-0079  al-rabi / musnad-rabi  ->  **wrong** (balagha_gap)  fix: i
- text: «أبو عبيدة قال: بلغني عن ابن عمر يروي عن رسول الله»
- stored: [defective/name_over_extended] أبو عبيدة > بلغني > ابن عمر يروي
- reader (both passes): أبو عبيدة > ابن عمر
- why: Reader drops both the verb «يروي» (right) and the anonymous «بلغني» link the work's convention keeps (cr-0013).

### cr-0089  al-kafi / al-kafi  ->  **right** (stored_junk_dropped)
- text: «5- وفي رواية أخرى عن أبي عبد الله (عليه السلام)»
- stored: [defective/non_narrator_name] أخرى > أبي عبد الله
- reader (both passes): أبي عبد الله
- why: Stored link «أخرى» is a word; reader «أبي عبد الله».

### cr-0090  sunni six-book / muslim  ->  **wrong** (over_applied_rule_5)  fix: i
- text: «قال سأل شباك إبراهيم فحدثنا عن علقمة، عن عبد الله»
- stored: [defective/name_lost] عثمان بن أبي شيبة > جرير > مغيرة || [unlabelled] إسحاق بن إبراهيم > جرير > مغيرة
- reader (both passes): عثمان بن أبي شيبة > جرير > مغيرة > شباك > إبراهيم > علقمة > عبد الله || إسحاق بن إبراهيم > جرير > مغيرة > شباك > إبراهيم > علقمة > عبد الله
- why: Reader applies «سأل X Y = two links» and makes شباك a transmitter between مغيرة and إبراهيم; he is the asker, the chain goes مغيرة > إبراهيم > علقمة.

### cr-0097  pure canon / ahmad  ->  **right** (stored_junk_dropped)
- text: «تابع/, روح, عبد الصمد, همام, قتادة»
- stored: [defective/non_narrator_name] تابع/ > روح > عبد الصمد > همام > قتادة > عبد الرحمن مولى أم برثن > أبي هريرة
- reader (both passes): روح > عبد الصمد > همام > قتادة > عبد الرحمن مولى أم برثن > أبي هريرة
- why: «تابع/» is a source-field label, not a name; reader drops it.

### cr-0098  other imami / kitab-al-ghayba-tusi  ->  **right** (stored_junk_dropped)
- text: «ومنهم محصن بن غسان بن ظالم الزبيدي،عاش مائتي سنة وستا وخمسين سنة»
- stored: [defective/non_narrator] ومنهم محصن بن غسان بن ظالم الزبيدي عاش مائتي سنة || [unlabelled] ستا
- reader (both passes): 
- why: A biography line with no chain; reader returns no route; stored had two junk chains.

### cr-0102  sunni six-book / abudawud  ->  **wrong** (unnamed_gap)  fix: i
- text: «فقال أخبرني من سمع رسول الله صلى الله عليه وسلم في حجة الوداع»
- stored: [unlabelled] أحمد بن أبي الحواري > سليم بن مطير - شيخ من أهل > أبي مطير > دين أحدكم فدعوه || [defective/non_narrator_name] أحمد بن أبي الحواري > ادي القرى > أبي مطير > دين أحدكم فدعوه
- reader (both passes): أحمد بن أبي الحواري > سليم بن مطير > مطير
- why: Reader: «أحمد > سليم > مطير» (good, drops junk) but the anonymous informant «من سمع رسول الله» is an unnamed link it omits.

### cr-0106  sunni six-book / ibnmajah  ->  **right** (stored_junk_dropped)
- text: «عن عمران بن حصين، أنه سأل رسول الله صلى الله عليه وسلم عن الرجل يصلي قاعدا»
- stored: [defective/non_narrator] بشر بن هلال الصواف > يزيد بن زريع > حسين المعلم > عبد الله بن بريدة > عمران بن حصين > الرجل يصلي قاعدا
- reader (both passes): بشر بن هلال الصواف > يزيد بن زريع > حسين المعلم > عبد الله بن بريدة > عمران بن حصين
- why: Stored last link «الرجل يصلي قاعدا» is the question; reader ends at عمران.

### cr-0108  sunni six-book / bukhari  ->  **wrong** (second_isnad_after_matn)  fix: i
- text: «وحدثنا آدم حدثنا شعبة حدثنا أبو إسحاق الهمداني عن البراء بن عازب»
- stored: [unlabelled] سعيد بن الربيع > شعبة > أبي إسحاق > البراء بن عازب || [unlabelled] محمد بن عرعرة > شعبة > أبي إسحاق > البراء بن عازب
- reader (both passes): سعيد بن الربيع > شعبة > أبي إسحاق > البراء بن عازب || محمد بن عرعرة > شعبة > أبي إسحاق > البراء بن عازب
- why: Second isnad (label missing_route) comes before the saying; reader returned only the two routes of the first.

### cr-0120  al-rabi / musnad-rabi  ->  **right** (source_in_matn)
- text: «قال: سئل أسامة بن زيد: كيف كان رسول الله صلى الله عليه وسلم يسير»
- stored: [defective/missing_link] أبو عبيدة > جابر بن زيد
- reader (both passes): أبو عبيدة > جابر بن زيد > أسامة بن زيد
- why: The answerer is the source (rule 2); reader adds «أسامة بن زيد». Label calls it a judgment.

### cr-0127  sunni six-book / muslim  ->  **right** (stored_junk_dropped)
- text: «كلاهما عن حماد بن زيد، - قال أبو الربيع حدثنا حماد، - حدثنا أيوب»
- stored: [unlabelled] أبو الربيع الزهراني > حماد بن زيد > حماد > أيوب > أبي قلابة > أبي أسماء > ثوبان || [defective/duplicate_link] قتيبة بن سعيد > حماد بن زيد > حماد > أيوب > أبي قلابة > أبي أسماء > ثوبان
- reader (both passes): أبو الربيع الزهراني > حماد بن زيد > أيوب > أبي قلابة > أبي أسماء > ثوبان || قتيبة بن سعيد > حماد بن زيد > أيوب > أبي قلابة > أبي أسماء > ثوبان
- why: The repeated «حماد» is one man mentioned twice; reader gives one link, two routes.

### cr-0140  pure canon / ahmad  ->  **right** (source_in_matn)
- text: «سمعت جدي عبيدة ابن عمرو الكلابي يقول رأيت رسول الله»
- stored: [unlabelled] عثمان ابن محمد > سعيد ابن خثيم الهلالي > جدتي ربيعة ابنة عياض || [defective/not_a_narrator] سمعته أنا من عثمان ابن محمد ابن أبي شيبة > سعيد ابن خثيم الهلالي > جدتي ربيعة ابنة عياض
- reader (both passes): عثمان ابن محمد > سعيد ابن خثيم الهلالي > ربيعة ابنة عياض > عبيدة ابن عمرو الكلابي || عثمان ابن محمد ابن أبي شيبة > سعيد ابن خثيم الهلالي > ربيعة ابنة عياض > عبيدة ابن عمرو الكلابي
- why: «سمعت X» names the source (rule 5); reader adds it, drops the clause «سمعته أنا من».

### cr-0141  sunni six-book / muslim  ->  **wrong** (complex_tahwil)  fix: iv
- text: «جميعا عن أبي معشر، ح وحدثنا أبو بكر بن أبي شيبة»
- stored: [unlabelled] قتيبة بن سعيد > حماد > هشام بن حسان > أبي معشر > إبراهيم > الأسود > أبي معشر || [unlabelled] إسحاق بن إبراهيم > عبدة بن سليمان > ابن أبي عروبة > أبي معشر > إبراهيم > الأسود > أبي معشر
- reader (both passes): قتيبة بن سعيد > حماد > هشام بن حسان > إبراهيم > الأسود > عائشة || إسحاق بن إبراهيم > عبدة بن سليمان > أبي معشر > إبراهيم > الأسود > عائشة  (+5 more routes)
- why: Five ح-groups with «جميعا عن أبي معشر» shared by some: reader drops «أبي معشر» from the first route and splits «عبدة بن سليمان … ابن أبي عروبة» into two routes, instead of one chain.

### cr-0153  other imami / thawab-al-amal  ->  **right** (inherited_backref_only)
- text: «و بهذا الإسناد قال قال علی ع أیها الناس»
- stored: [defective/not_a_narrator] و بهذا الإسناد > منکر فعلوه إلی آخر الآیه
- reader (both passes): علی
- why: Stored: back reference plus a junk matn phrase; reader: the Imam named. Nothing stored is lost.

### cr-0158  sunni six-book / tirmidhi  ->  **right** (unnamed_link)
- text: «حدثنا عبد بن حميد، وغير واحد، - المعنى واحد قالوا»
- stored: [unlabelled] عبد بن حميد > يونس بن محمد > شيبان بن عبد الرحمن > قتادة > الحسن > أبي هريرة || [defective/ghayr_wahid_split] غير واحد - المعنى > يونس بن محمد > شيبان بن عبد الرحمن > قتادة > الحسن > أبي هريرة
- reader (both passes): عبد بن حميد > يونس بن محمد > شيبان بن عبد الرحمن > قتادة > الحسن > أبي هريرة || غير واحد > يونس بن محمد > شيبان بن عبد الرحمن > قتادة > الحسن > أبي هريرة
- why: Reader: one route from «عبد بن حميد», one from the unnamed «غير واحد»; gloss left out; stored «احد» junk.

### cr-0169  al-kafi / al-kafi  ->  **right** (imam_named)
- text: «عن أبي الصباح الكناني عن أبي عبد الله (عليه السلام) في قول الله»
- stored: [defective/non_narrator_name] أحمد بن محمد > محمد بن الفضيل > أبي الصباح الكناني > المعيشة فلا بأس
- reader (both passes): أحمد بن محمد > محمد بن الفضيل > أبي الصباح الكناني > أبي عبد الله
- why: Stored last link is matn words; reader the Imam.

### cr-0172  pure canon / darimi  ->  **right** (stored_junk_dropped)
- text: «أبو النعمان انا حماد ابن يزيد, ثابت»
- stored: [defective/merged_names] أبو النعمان انا حماد ابن يزيد > ثابت
- reader (both passes): أبو النعمان > حماد ابن يزيد > ثابت
- why: Two names and a verb in one stored link; reader splits.

### cr-0179  al-kafi / al-kafi  ->  **right** (unnamed_link)
- text: «علي بن أسباط عمن روى في الجلالات قال»
- stored: [defective/merged_names] محمد بن يحيى > أحمد بن محمد > الخشاب > علي بن أسباط عمن روى في الجلالات
- reader (both passes): محمد بن يحيى > أحمد بن محمد > الخشاب > علي بن أسباط > عمن روى
- why: Reader: «علي بن أسباط > عمن روى» (unnamed link), stored merged them.

### cr-0184  sunni six-book / bukhari  ->  **right** (source_in_matn)
- text: «عن أبي قلابة، أن أبا المليح، حدثه قال كنا مع بريدة»
- stored: [defective/missing_link] معاذ بن فضالة > هشام > يحيى هو ابن أبي كثير > أبي قلابة > أبا المليح
- reader (both passes): معاذ بن فضالة > هشام > يحيى > أبي قلابة > أبا المليح > بريدة
- why: Reader adds بريدة, who is the Companion source.

### cr-0189  sunni six-book / muslim  ->  **right** (source_in_matn)
- text: «أخبرنا عمرو، - يعني ابن الحارث - أن ابن شهاب، حدثه عن أبي إدريس»
- stored: [defective/name_lost+non_narrator] هارون بن سعيد الأيلي > ابن وهب > عمرو > أبي إدريس الخولاني > أبي ثعلبة الخشني أنالله عليه > أكل || [unlabelled] هارون بن سعيد الأيلي > ابن وهب > عمرو > أبي إدريس الخولاني > سلم نهى > أكل
- reader (both passes): هارون بن سعيد الأيلي > ابن وهب > عمرو > ابن شهاب > أبي إدريس الخولاني > أبي ثعلبة الخشني
- why: «أن X حدثه» (rule 5): reader adds ابن شهاب; junk tail dropped.

### cr-0197  other imami / al-amali-saduq  ->  **right** (compiler_named)
- text: «حدثنا الشيخ الجليل أبو جعفر محمد بن علي بن الحسين بن موسى ابن بابويه القمي (رضي الله عنه)، قال: حدثنا أبي»
- stored: [unlabelled] أبي > سعد بن عبد الله > أحمد بن أبي عبد الله البرقي > أبيه محمد بن خالد > أبي البختري > الصادق جعفر بن محمد > أبيه > آبائه || [defective/name_truncated] أبي > سعد بن عبد الله > أحمد بن أبي عبد الله البرقي > أبيه محمد بن خالد > هب ابن وهب > الصادق جعفر بن محمد > أبيه > آبائه
- reader (both passes): أبو جعفر محمد بن علي بن الحسين بن موسى ابن بابويه القمي > أبي > سعد بن عبد الله > أحمد بن أبي عبد الله البرقي > محمد بن خالد > أبي البختري وهب ابن وهب > الصادق جعفر بن محمد > أبيه > آبائه > أم سلمة
- why: The compiler is named in the text; under the owner ruling (compiler heads the chain) the reader's first link is right; stored dropped him and mangled «وهب ابن وهب». Also adds «أم سلمة».

### cr-0207  sunni six-book / bukhari  ->  **right** (stored_junk_dropped)
- text: «عن ابن عباس  رضى الله عنهما – {ولكل جعلنا موالي} قال ورثة»
- stored: [unlabelled] الصلت بن محمد > أبو أسامة > إدريس > طلحة بن مصرف > سعيد بن جبير > ابن عباس – || [defective/non_narrator_name] الصلت بن محمد > أبو أسامة > إدريس > طلحة بن مصرف > سعيد بن جبير > لكل جعلنا موالي
- reader (both passes): الصلت بن محمد > أبو أسامة > إدريس > طلحة بن مصرف > سعيد بن جبير > ابن عباس
- why: Stored link is the verse; reader ابن عباس.

### cr-0217  sunni six-book / ibnmajah  ->  **right** (stored_junk_dropped)
- text: «عن نافع، عن ابن عمر، رواية قال»
- stored: [defective/name_over_extended] عبد الله بن محمد الزهري > سفيان بن عيينة > أيوب > نافع > ابن عمر رواية
- reader (both passes): عبد الله بن محمد الزهري > سفيان بن عيينة > أيوب > نافع > ابن عمر
- why: «رواية» is not part of the name.

### cr-0227  other imami / al-tawhid-saduq  ->  **wrong** (inherited_chain)  fix: ii
- text: «20 - وبهذا الإسناد قال: قال رسول الله صلى الله عليه وآله وسلم: إن الله عز وجل عمودا»
- stored: [unlabelled] أبو منصور أحمد بن إبراهيم بن بكر الخوري بنيسابور > أبو إسحاق إبراهيم بن محمد بن هارون الخوري > جعفر بن محمد ابن زياد الفقيه الخوري > أحمد بن عبد الله الجويباري > الرضا علي بن موسى > أبيه > آبائه > علي || [defective/not_a_narrator] أبو منصور أحمد بن إبراهيم بن بكر الخوري بنيسابور > أبو إسحاق إبراهيم بن محمد بن هارون الخوري > جعفر بن محمد ابن زياد الفقيه الخوري > يقال له الهروي > الرضا علي بن موسى > أبيه > آبائه > علي
- reader (both passes): 
- why: Text has no name; stored holds four inherited chains (one with a junk link). Reader would return nothing.

### cr-0241  al-kafi / al-kafi  ->  **right** (stored_junk_dropped)
- text: «عن ابن أبي عمير عن بعض أصحابنا عن أحدهما (عليهما السلام) في الرجل يحدث»
- stored: [correct/non_narrator_name] علي بن إبراهيم > أبيه > ابن أبي عمير > بعض أصحابنا > أحدهما || [unlabelled] علي بن إبراهيم > أبيه > ابن أبي عمير > بعض أصحابنا > قد طاف بعضه
- reader (both passes): علي بن إبراهيم > أبيه > ابن أبي عمير > بعض أصحابنا > أحدهما
- why: Reader reproduces the correct chain and drops the junk second chain.

### cr-0242  sunni six-book / ibnmajah  ->  **right** (stored_junk_dropped)
- text: «قال أبو الحسن القطان حدثناه خازم بن يحيى، حدثنا عبد الملك بن شيبان»
- stored: [defective/merged_names] أبو الحسن القطان حدثناه خازم بن يحيى > عبد الملك بن شيبان > يحيى بن عثمان
- reader (both passes): أبو الحسن القطان > خازم بن يحيى > عبد الملك بن شيبان > يحيى بن عثمان
- why: Two persons and a verb merged in stored; reader splits.

### cr-0248  sunni six-book / abudawud  ->  **right** (stored_missing_link)
- text: «حدثنا يزيد بن خالد، وقتيبة، أن الليث بن سعد، حدثهم عن بكير»
- stored: [defective/missing_link] يزيد بن خالد > بكير > سليمان بن يسار > أبي هريرة || [unlabelled] قتيبة > بكير > سليمان بن يسار > أبي هريرة
- reader (both passes): يزيد بن خالد > الليث بن سعد > بكير > سليمان بن يسار > أبي هريرة || قتيبة > الليث بن سعد > بكير > سليمان بن يسار > أبي هريرة
- why: «أن X حدثهم»: reader adds الليث بن سعد to both routes.

### cr-0251  sunni six-book / bukhari  ->  **right** (stored_missing_link)
- text: «أخبرنا ابن جريج، قال عمرو بن دينار قال ابن عباس»
- stored: [defective/missing_link] عثمان بن الهيثم > ابن جريج
- reader (both passes): عثمان بن الهيثم > ابن جريج > عمرو بن دينار > ابن عباس
- why: Reader adds عمرو بن دينار and ابن عباس.

### cr-0252  sunni six-book / abudawud  ->  **right** (stored_missing_link)
- text: «قال قرأت على عبد الله بن عمر { الله الذي خلقكم من ضعف }»
- stored: [defective/missing_link] النفيلي > زهير > فضيل بن مرزوق > عطية بن سعد العوفي
- reader (both passes): النفيلي > زهير > فضيل بن مرزوق > عطية بن سعد العوفي > عبد الله بن عمر
- why: Reader adds عبد الله بن عمر.

### cr-0253  sunni six-book / abudawud  ->  **right** (stored_missing_link)
- text: «حدثنا محمد بن كثير، ح وحدثنا مسلم بن إبراهيم، حدثنا همام، عن قتادة»
- stored: [unlabelled] محمد بن كثير || [correct/truncated_route] مسلم بن إبراهيم > همام > قتادة > أبي الصديق > ابن عمر
- reader (both passes): محمد بن كثير > همام > قتادة > أبي الصديق > ابن عمر || مسلم بن إبراهيم > همام > قتادة > أبي الصديق > ابن عمر
- why: The shared tail is given to both routes; stored had the lone «محمد بن كثير».

### cr-0255  other imami / kamil-al-ziyarat  ->  **wrong** (imam_missed)  fix: i
- text: «كنت أنا و يونس بن ظبيان و المفضل بن عمر و أبو سلمة السراج جلوسا عند أبي عبد الله (ع) و كان المتكلم يونس»
- stored: [unlabelled] أبي > سعد بن عبد الله > أحمد بن محمد بن عيسى > القاسم بن يحيى > الحسن بن راشد > الحسين بن ثوير بن أبي فاختة || [defective/merged_names] علي بن الحسين و محمد بن الحسن > سعد بن عبد الله > أحمد بن محمد بن عيسى > القاسم بن يحيى > الحسن بن راشد > الحسين بن ثوير بن أبي فاختة
- reader (both passes): أبي > سعد بن عبد الله > أحمد بن محمد بن عيسى > القاسم بن يحيى > الحسن بن راشد > الحسين بن ثوير بن أبي فاختة || علي بن الحسين > سعد بن عبد الله > أحمد بن محمد بن عيسى > القاسم بن يحيى > الحسن بن راشد > الحسين بن ثوير بن أبي فاختة  (+1 more routes)
- why: The Imam is the source of the saying and is named after the chain; reader's routes end at «الحسين بن ثوير بن أبي فاختة» (the three heads «أبي، علي بن الحسين، محمد بن الحسن» are right).

### cr-0263  al-faqih / man-la-yahduruhu-al-faqih  ->  **right** (stored_junk_dropped)
- text: «و روى أبان عن بكير و الحلبي عن أحدهما عليهما السلام»
- stored: [defective/merged_names] أبان > بكير و الحلبي > أحدهما
- reader (both passes): أبان > بكير > أحدهما || أبان > الحلبي > أحدهما
- why: Two co-transmitters merged in stored; reader writes two routes.

### cr-0271  sunni six-book / muslim  ->  **right** (stored_missing_link)
- text: «حدثنا يحيى بن يحيى، قال قرأت على مالك عن نافع، عن زيد بن عبد الله»
- stored: [defective/truncated_route] يحيى بن يحيى
- reader (both passes): يحيى بن يحيى > مالك > نافع > زيد بن عبد الله > عبد الله بن عبد الرحمن بن أبي بكر الصديق > أم سلمة
- why: Stored kept only the first name; reader the full chain.

### cr-0278  sunni six-book / nasai  ->  **right** (stored_missing_link)
- text: «قال سمعت مسروقا، والأسود، قالا نشهد على عائشة أنها قالت»
- stored: [unlabelled] إسماعيل بن مسعود > خالد بن الحارث > شعبة > أبي إسحاق > مسروقا || [defective/missing_link] إسماعيل بن مسعود > خالد بن الحارث > شعبة > أبي إسحاق > الأسود
- reader (both passes): إسماعيل بن مسعود > خالد بن الحارث > شعبة > أبي إسحاق > مسروقا > عائشة || إسماعيل بن مسعود > خالد بن الحارث > شعبة > أبي إسحاق > الأسود > عائشة
- why: Reader: two routes ending at عائشة.

### cr-0279  other imami / kitab-al-mumin  ->  **rep** (prefix_noise)
- text: «138 - وعن أبي عبد الله عليه السلام قال: قال رسول الله»
- stored: [defective/name_over_extended] وعن أبي عبد الله
- reader (both passes): أبي عبد الله
- why: Stored «وعن أبي عبد الله», reader «أبي عبد الله»; continuation of the previous report (inherited chain not in this text).

## Class (c), not read (29 reports): in the agreed set, labelled defective, reader differs; no verdict is given for them

cr-0007, cr-0011, cr-0016, cr-0021, cr-0024, cr-0052, cr-0062, cr-0064, cr-0082, cr-0100, cr-0104, cr-0122, cr-0131, cr-0135, cr-0149, cr-0156, cr-0171, cr-0173, cr-0180, cr-0181, cr-0182, cr-0202, cr-0206, cr-0243, cr-0260, cr-0262, cr-0264, cr-0272, cr-0282

## Class (a) reports read, with a call to make

### cr-0015  pure canon / muwatta  ->  **cannot_tell** (subject_vs_source)  fix: i
- text: «مالك, نافع ⏎ ⏎ أن عبد الله ابن عمر كان لا يقرأ في الصلاة على الجنازة»
- stored: [correct] مالك > نافع
- reader (both passes): مالك > نافع
- why: Pure Canon: the field has two names; the practice is Ibn ʿUmar's; reader (like the field) omits him, but cr-0051 shows the reader adds a named speaker. Policy needed.

### cr-0027  pure canon / muwatta  ->  **cannot_tell** (subject_vs_source)  fix: i
- text: «أن ابنة عبيد الله ابن عمر … فقال عبد الله ابن عمر ليس لها صداق»
- stored: [correct] مالك > نافع
- reader (both passes): مالك > نافع
- why: Same as cr-0015.

### cr-0138  sunni six-book / bukhari  ->  **wrong** (source_in_matn_missed)  fix: i
- text: «قال أبو بكر مررنا براع وقد عطش رسول الله صلى الله عليه وسلم»
- stored: [correct] محمود > النضر > شعبة > أبي إسحاق > البراء
- reader (both passes): محمود > النضر > شعبة > أبي إسحاق > البراء
- why: Abu Bakr narrates the story in the first person; he is the source (rule 2); reader ends at البراء.

### cr-0237  sunni six-book / bukhari  ->  **cannot_tell** (subject_vs_source)  fix: i
- text: «أن عمر بن الخطاب، رأى حلة سيراء عند باب المسجد فقال يا رسول الله»
- stored: [correct] عبد الله بن يوسف > مالك > نافع > عبد الله بن عمر
- reader (both passes): عبد الله بن يوسف > مالك > نافع > عبد الله بن عمر
- why: Bukhari report of an event of عمر; whether he is a link (source of the story) or only its subject is a judgment; stored and both readers omit him.

### cr-0258  other imami / al-amali-saduq  ->  **wrong** (source_in_matn_missed)  fix: i
- text: «أتوا حذيفة، فقالوا … فقال: سمعت رسول الله (صلى الله عليه وآله) يقول»
- stored: [correct] علي بن أحمد بن موسى > محمد بن أبي عبد الله الكوفي > موسى بن عمران النخعي > إبراهيم بن الحكم > عبد الله بن موسى > سعد بن أوس > بلال بن يحيى العبسي
- reader (both passes): إبراهيم بن الحكم > عبد الله بن موسى > سعد بن أوس > بلال بن يحيى العبسي
- why: The speaker of the Prophet's saying is a source link (rule 2); reader ends at بلال بن يحيى العبسي.

## Class (a) reports read and judged right with no comment (87)

Reader's routes equal the stored routes, and I re-read each against the text (the 17 whose reader routes contain more routes than the labelled chain, because the other stored chains of the report were unlabelled, included). Ids:

cr-0003, cr-0004, cr-0005, cr-0006, cr-0009, cr-0012, cr-0017, cr-0018, cr-0025, cr-0034, cr-0035, cr-0037, cr-0038, cr-0040, cr-0044, cr-0050, cr-0054, cr-0061, cr-0072, cr-0073, cr-0074, cr-0076, cr-0080, cr-0081, cr-0087, cr-0092, cr-0103, cr-0107, cr-0109, cr-0110, cr-0112, cr-0115, cr-0116, cr-0118, cr-0121, cr-0123, cr-0130, cr-0133, cr-0142, cr-0148, cr-0150, cr-0152, cr-0154, cr-0159, cr-0161, cr-0162, cr-0166, cr-0174, cr-0175, cr-0183, cr-0185, cr-0186, cr-0188, cr-0191, cr-0198, cr-0199, cr-0205, cr-0209, cr-0211, cr-0212, cr-0216, cr-0221, cr-0222, cr-0223, cr-0225, cr-0226, cr-0228, cr-0231, cr-0232, cr-0235, cr-0236, cr-0239, cr-0245, cr-0246, cr-0249, cr-0250, cr-0254, cr-0256, cr-0257, cr-0259, cr-0269, cr-0270, cr-0274, cr-0275, cr-0276, cr-0277, cr-0281

## Disagreements between the two passes: all 25 read (offsets ignored; 17 valid in both, 8 with an invalid output)

### cr-0029  other imami / al-khisal  ->  class **relation_word**, right: **A**  fix: i+iii
- text: «حدثنا محمد بن علي ما جيلويه رضي الله عنه، عن عمه محمد بن أبي القاسم»
- difference: B writes «عمه» as a link before «محمد بن أبي القاسم» (one man, two links); A gives the name alone (rule 1).

### cr-0031  other imami / uyun-akhbar-al-rida  ->  class **relation_word**, right: **A**  fix: i+iii
- text: «عن أبيه على بن محمد، عن أبيه محمد بن على، عن أبيها لرضا على بن موسى»
- difference: B keeps every «أبيه» as its own link next to the named man (17 links for 11 persons); A drops the relation word (the source's typo «أبيها لرضا» gives A «لرضا على بن موسى»).

### cr-0032  al-faqih / man-la-yahduruhu-al-faqih  ->  class **nested_multi_isnad**, right: **neither**  fix: iv
- text: «عن أيوب بن نوح؛ و إبراهيم بن هاشم جميعا عن صفوان بن يحيى؛ و ابن أبي عمير جميعا عن محمد بن حمران»
- difference: Second isnad with ';' and «جميعا» at two levels; A writes four fragments, B four different ones; neither gives the full structure and the correct nesting is not decidable from punctuation alone.

### cr-0049  al-kafi / al-kafi  ->  class **relation_word**, right: **A**  fix: i+iii
- text: «عن علي بن جعفر عن أخيه أبي الحسن ( عليه السلام ) قال»
- difference: B «أخيه > أبي الحسن» (two links), A «أبي الحسن».

### cr-0057  sunni six-book / ibnmajah  ->  class **relation_word**, right: **A**  fix: i+iii
- text: «قال سمعت عمي، يحيى - وما أدركت رجلا منا به شبيها»
- difference: B «عمي > يحيى», A «يحيى».

### cr-0058  sunni six-book / muslim  ->  class **shared_tail**, right: **B**  fix: i+iii
- text: «حدثنا محمد بن جعفر، ح وحدثنا عبيد الله بن معاذ، حدثنا أبي قالا، جميعا حدثنا شعبة»
- difference: B carries «شعبة» as shared tail of the first two routes and writes «عبيد الله بن معاذ > أبي > شعبة»; A drops شعبة from the first two and splits the third into two routes.

### cr-0059  other imami / kamal-al-din  ->  class **route_explosion**, right: **A**  fix: iii
- text: «حدثنا أبي، ومحمد بن الحسن … ومحمد بن موسى … قالوا: حدثنا سعد بن عبد الله، وعبد الله بن جعفر، ومحمد بن يحيى العطار، قالوا: حدثنا أحمد بن محمد بن عيسى، وإبراهيم بن هاشم»
- difference: 3x3x2 = 18 routes: A writes all 18, B stops after 6. B is a correct prefix (truncation), A is right.

### cr-0065  al-faqih / man-la-yahduruhu-al-faqih  ->  class **nested_multi_isnad**, right: **neither**  fix: iv
- text: «عن أبي؛ و محمد بن الحسن … عن سعد بن عبد الله؛ و عبد الله بن جعفر الحميري جميعا عن يعقوب بن يزيد؛ و الحسن بن ظريف؛ و أيوب بن نوح»
- difference: The first isnad (12 combinations) is mostly lost by both: A keeps a fragment «أيوب بن نوح > النضر > هشام», B only the second isnad.

### cr-0069  other imami / kitab-al-ghayba-numani  ->  class **imam_in_text**, right: **A**  fix: i
- text: «وصفت لأبي عبد الله رجلا يتوالى أمير المؤمنين … فقال: إن مات هذا مات ميتة جاهلية»
- difference: A adds the Imam named after the chain (owner ruling); B stops at حمران بن أعين.

### cr-0075  al-kafi / al-kafi  ->  class **route_explosion**, right: **neither**  fix: iii+i
- text: «عن الحلبي و زرارة و محمد بن مسلم و حمران بن أعين عن أبي جعفر و أبي عبد الله ( عليه السلام ) قالا»
- difference: 4x2 = 8 routes. A writes four routes with the two Imams in sequence «أبي جعفر > أبي عبد الله»; B writes the parallel Imams (right) but only five of the eight.

### cr-0085  sunni six-book / muslim  ->  class **surface_scope**, right: **both**  fix: iii
- text: «كلهم عن سفيان، قال عمرو حدثنا سفيان بن عيينة»
- difference: One man named twice; A takes the longer mention «سفيان بن عيينة», B the first «سفيان». Both right; they differ only in which mention is the surface.

### cr-0101  sunni six-book / nasai  ->  class **surface_scope**, right: **both**  fix: iii
- text: «عن حبيب، مولى عروة عن بدية»
- difference: A «حبيب», B «حبيب مولى عروة» (a mawla phrase kept or not).

### cr-0114  sunni six-book / nasai  ->  class **surface_scope**, right: **both**  fix: iii
- text: «عن حبيب، مولى عروة عن بدية، - وكان الليث يقول ندبة -»
- difference: Same as cr-0101.

### cr-0137  al-rabi / musnad-rabi  ->  class **title_or_epithet**, right: **cannot_tell**  fix: i
- text: «الإمام عن أبي غانم الخراساني عن حاتم بن منصور»
- difference: A has the title «الإمام» as first link, B starts at «أبي غانم»; the work's convention for this opening is not stated in the prompt.

### cr-0143  al-kafi / al-kafi  ->  class **nested_multi_isnad**, right: **neither**  fix: iv
- text: «عن أبي بصير مثله .حميد بن زياد عن ابن سماعة عن وهيب بن حفص»
- difference: Two reports run together («مثله» then a new isnad); A and B segment the first part differently and both lose parts.

### cr-0144  sunni six-book / muslim  ->  class **surface_scope**, right: **both**  fix: iii
- text: «كلاهما عن المعتمر، قال ابن حبيب حدثنا معتمر بن سليمان»
- difference: A «معتمر بن سليمان» in both routes, B «المعتمر» in the second; same man mentioned twice.

### cr-0146  pure canon / muwatta  ->  class **source_in_matn**, right: **A**  fix: i
- text: «مالك ⏎ ⏎ رأى سالم ابن عبد الله يخرج من أنفه الدم»
- difference: A adds «سالم ابن عبد الله» (rule 5 «رأيت X»), B keeps the field's single name; policy for Pure Canon (field only vs rule 5).

### cr-0157  al-kafi / al-kafi  ->  class **shared_tail**, right: **B**  fix: i+iii
- text: «عن أبيه عن ابن أبي عمير ومحمد بن إسماعيل عن الفضل بن شاذان عن صفوان بن يحيى وابن أبي عمير عن معاوية بن عمار»
- difference: B continues the first route to «معاوية بن عمار > الإمام»; A ends it at «ابن أبي عمير».

### cr-0160  sunni six-book / muslim  ->  class **surface_scope**, right: **both**  fix: iii
- text: «وحدثني عيسى بن حماد المصري، أخبرنا الليث»
- difference: A «عيسى بن حماد», B «عيسى بن حماد المصري» (nisba kept or not); nine routes otherwise identical.

### cr-0170  sunni six-book / muslim  ->  class **shared_tail**, right: **A**  fix: i+iii
- text: «حدثنا محمد بن جعفر، ح وحدثنيه يحيى بن حبيب، حدثنا خالد - قالا حدثنا شعبة، بهذا الإسناد»
- difference: A adds the shared «شعبة» to the first two routes; B leaves them at «محمد بن جعفر».

### cr-0177  sunni six-book / tirmidhi  ->  class **surface_scope**, right: **cannot_tell**  fix: iii+i
- text: «أنه سمع هانئا، مولى عثمان قال كان عثمان إذا وقف على قبر بكى»
- difference: A «هانئا», B «هانئا مولى عثمان»; both omit عثمان, the speaker of the saying (rule 2).

### cr-0178  other imami / al-amali-mufid  ->  class **surface_scope**, right: **both**  fix: iii
- text: «عن أبيه، عن أمير المؤمنين علي بن أبي طالب عليه السلام قال»
- difference: A keeps the title, B «علي بن أبي طالب».

### cr-0187  sunni six-book / abudawud  ->  class **nested_multi_isnad**, right: **neither**  fix: iv
- text: «حدثني إياس بن الحارث بن المعيقيب، وجده، من قبل أمه أبو ذباب عن جده»
- difference: Both read «إياس > جده > أبو ذباب > جده» as a sequence; the text has two parallel narrators (إياس, and his maternal grandfather أبو ذباب) from «جده». A and B differ only by the clitic «وجده» vs «جده» but both are wrong.

### cr-0195  other imami / fadail-al-shia  ->  class **imam_in_text**, right: **A**  fix: i
- text: «عن منصور الصيقل، قال: كنت عند أبي عبد الله عليه السلام في فسطاطه بمنى»
- difference: A adds the Imam, B omits him; both drop the unnamed gap of «بإسناد يرفعه» (see irsal_gap).

### cr-0219  other imami / uyun-akhbar-al-rida  ->  class **nested_multi_isnad**, right: **neither**  fix: iv
- text: «عن بكر بن صالح، وحدثنا أبي ومحمد بن موسى بن المتوكل … قالوا: حدثنا على بن إبراهيم بن هاشم، عن أبيه، عن بكر بن صالح»
- difference: Two isnads converge at «بكر بن صالح» (the tail «عبد الرحمن بن سالم > أبيبصير > الإمام» is shared); A ends the first isnad at بكر, B joins the tail to four of its routes and drops «الحسن بن ظريف» into a one-route fragment.

## Agreed only when offsets are ignored (36 reports; 12 read at random)

### cr-0036  other imami / thawab-al-amal  ->  **rep** (prefix_noise)
- text: «عن جعفر بن محمد عن أبيه عن آبائه ع قال»
- why: Honorific only.

### cr-0045  al-kafi / al-kafi  ->  **right** (imam_named)
- text: «قال قلت لأبي عبد الله ( عليه السلام ) رجل يعرف رأيه مرة»
- why: Four parallel routes joined by «جميعا عن صفوان»; Imam added.

### cr-0055  other imami / thawab-al-amal  ->  **rep** (prefix_noise)
- text: «عن سوره بن كليب عن أبي عبد الله ع قال»
- why: Honorific only.

### cr-0060  other imami / kitab-al-ghayba-numani  ->  **right** (imam_named)
- text: «عن أبي الجارود قال: قالت لأبي جعفر»
- why: Imam added; two routes for «محمد بن همام ومحمد بن الحسن بن محمد بن جمهور، جميعا».

### cr-0067  al-kafi / al-kafi  ->  **right** (plain_match)
- text: «عن محمد بن الحسين وأحمد بن محمد عن ابن محبوب»
- why: Two parallel routes; Imam last.

### cr-0083  al-kafi / al-kafi  ->  **right** (plain_match)
- text: «قال سمعت أبا عبد الله ( عليه السلام ) يقول»
- why: Two routes, Imam last.

### cr-0095  other imami / sifat-al-shia  ->  **rep** (prefix_noise)
- text: «عن عبد الله بن موسى بن جعفر ع قال»
- why: Honorific only.

### cr-0119  al-faqih / man-la-yahduruhu-al-faqih  ->  **right** (imam_named)
- text: «قال : قلت لأبي عبد الله عليه السلام إنه ذكر لنا»
- why: «قلت لـ X» link.

### cr-0124  al-faqih / man-la-yahduruhu-al-faqih  ->  **right** (stored_junk_dropped)
- text: «عن أبي بصير فقال : سألت أبا عبد الله عليه السلام عن محرم قتل ثعلبا»
- why: Stored merged matn words into the links; reader reads البزنطي > علي بن أبي حمزة > أبي بصير > أبا عبد الله.

### cr-0134  al-faqih / man-la-yahduruhu-al-faqih  ->  **right** (stored_junk_dropped)
- text: «و سأل سليمان بن جعفر الجعفري العبد الصالح موسى بن جعفر»
- why: Asker and Imam as two links (rule 5).

### cr-0139  sunni six-book / muslim  ->  **cannot_tell** (complex_tahwil)
- text: «كل هؤلاء عن الأعمش، عن أبي سفيان، عن جابر، . زاد عمرو في روايته عن عمار، وأبو كريب في روايته عن أبي معاوية، فقالا عن أم مبشر»
- why: Reader gives the base chain (five routes ending جابر); the text adds per-route variants «عن أم مبشر» whose placement I cannot settle.

### cr-0210  al-faqih / man-la-yahduruhu-al-faqih  ->  **right** (plain_match)
- text: «عن القاسم بن يحيى عن جده الحسن بن راشد. و رويته عن محمد بن علي ماجيلويه»
- why: Two isnads kept apart; first has three parallel co-transmitters.
