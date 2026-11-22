"""Hand verdicts for every read case (see README.md). Written after reading each report's Arabic against the agreed reading.

Verdict codes: right | rep (representation only) | wrong | label_wrong (reader right, human label wrong) | cannot_tell.
Fix codes for wrong/cannot_tell: i prompt rule | ii context from sources | iii deterministic post-processing | iv not fixable by a reader.
Entry: id -> (verdict, tag, fix, quote, why). A report the reader agreed on, that I read, and that is not listed here is 'right'
with tag plain_match: the reader's routes equal the stored chains and I re-read them against the text.
"""

V = {}


def add(i, verdict, tag, quote, why, fix=""):
    V[i] = (verdict, tag, fix, quote, why)


# ---- class (b): labelled correct, reader differs from the stored chain ---------------------------------------------
add("cr-0001", "right", "artifact_clitic", "حدثنا عبيد الله بن عمر القواريري، وأحمد بن عبدة", "Stored name «أحمد بن عبدة» is written «وأحمد» (و attached); score.py drops it as 'not in text', so the reduced stored chain lacks it. The reader's two routes are the text's two routes.")
add("cr-0014", "right", "artifact_clitic", "عن محمد بن أبي حمزة وحسين بن عثمان عن إسحاق بن عمار", "Same artifact («وحسين»); reader gives both parallel routes.")
add("cr-0023", "right", "artifact_clitic", "محمد بن الحسين بن أبي الخطاب ومحمد بن عيسى وعبد الله بن عامر القصباني جميعا", "Same artifact («وعبد الله بن عامر»); 2x3 routes = stored 6.")
add("cr-0041", "right", "artifact_clitic", "عن الحلبي وزرارة، عن أبي عبد الله", "Same artifact («وزرارة»).")
add("cr-0086", "right", "artifact_clitic", "حدثنا يحيى بن يحيى، وإسحاق بن إبراهيم، - واللفظ ليحيى - قالا", "Same artifact («وإسحاق»); gloss correctly left out.")
add("cr-0132", "right", "artifact_clitic", "عن ابن شهاب، عن الحسن، وعبد الله، ابنى محمد عن أبيهما", "Same artifact («وأسامة»); 3x2 routes; «عبد الله» for the stored «عبد الله ابنى محمد» is the name alone.")
add("cr-0145", "right", "artifact_clitic", "حدثنا محمد بن يحيى العطار وأحمد بن إدريس جميعا", "Same artifact («وأحمد بن إدريس»); the blessing «رحمهما الله» correctly left out.")
add("cr-0155", "right", "artifact_clitic", "حدثني محمد بن رافع، وعبد بن حميد", "Same artifact («وعبد بن حميد»).")
add("cr-0165", "right", "artifact_clitic", "أبو بكر بن أبي شيبة، وعمرو الناقد، وزهير بن حرب، قالوا حدثنا وكيع", "Same artifact («وعمرو الناقد»).")
add("cr-0204", "right", "artifact_clitic", "حدثنا أبو بكر بن أبي شيبة، وأبو كريب قالا حدثنا وكيع", "Same artifact («وأبو كريب»).")
add("cr-0208", "right", "artifact_clitic", "علي بن ابراهيم عن أبيه ومحمد بن اسماعيل عن الفضل ابن شاذان جميعا عن حماد", "Same artifact («ومحمد بن اسماعيل»).")
add("cr-0244", "right", "artifact_clitic", "سعيد بن منصور، وأبو الربيع العتكي، وقتيبة بن سعيد، قالوا حدثنا حماد", "Same artifact («وأبو الربيع»); gloss «- وهو ابن زيد -» left out.")
add("cr-0265", "right", "artifact_clitic", "حدثنا سعد بن عبد الله، وعبد الله بن جعفر الحميري جميعا", "Same artifact («وعبد الله»).")
add("cr-0022", "rep", "gloss_dropped", "علي هو ابن مسهر, هشام هو ابن عروة", "Stored keeps the source field's gloss «هو ابن …»; reader leaves it out (prompt rule 1). Same four links.")
add("cr-0030", "rep", "gloss_dropped", "عطاء قاله محمد, يحيى ابن سعيد القطان", "Stored link «عطاء قاله محمد»; reader «عطاء». Four parallel routes otherwise identical.")
add("cr-0042", "rep", "gloss_dropped", "ليث يعني ابن سعد, بكير ابن عبد الله ابن الأشج", "Gloss «يعني ابن سعد» dropped by reader.")
add("cr-0096", "rep", "gloss_dropped", "سعيد يعني المقبري, أبي عبيدة", "Gloss «يعني المقبري» dropped by reader.")
add("cr-0043", "rep", "prefix_noise", "168 - وعن أبي عبد الله عليه السلام قال", "Stored surface keeps the connective «وعن»; reader «أبي عبد الله». The report continues the previous one but the single link is the same.")
add("cr-0192", "rep", "prefix_noise", "172 - وعن أبي عبد الله عليه السلام قال", "Same as cr-0043.")
add("cr-0194", "rep", "backref_honorific", "91 - وعنه (ع) قال لكل شئ شئ يستريح إليه", "Formula-only chain: stored «وعنه ع», reader «وعنه»; honorific only.")
add("cr-0151", "rep", "backref_link", "7 - وبهذا الإسناد قال: قال رسول الله", "Stored chain is the lone back reference «وبهذا الإسناد»; the reader gives the same back_reference link, which score.py drops, so its route is empty. No name in the text.")
add("cr-0168", "rep", "backref_link", "43 - وبالإسناد الأول عن علي بن مهزيار، عن واصل بن سليمان", "Stored keeps «وبالإسناد الأول» as first link; reader has it as back_reference (dropped by score.py). Names identical.")
add("cr-0190", "rep", "orthography", "محمد بن عبدالله ومحمد بن يحيى جميعا، عن عبدالله بن جعفر الحميري", "Stored «عبد الله», text/reader «عبدالله» (no space); also artifact_clitic. Same two routes.")
add("cr-0220", "rep", "orthography", "محمد بن عبدالله ومحمد بن يحيى جميعا، عن عبدالله بن جعفر الحميري", "Same as cr-0190.")
add("cr-0196", "rep", "gloss_in_stored", "عن ابن عباس ( ما كذب الفؤاد ما رأى ) قال رآه بقلبه", "Stored last link carries the quoted verse; reader «ابن عباس». Three routes incl. «وابن أبي رزمة، وأبو نعيم» correct.")
add("cr-0200", "rep", "prefix_noise", "عن الحسين بن علي بن بنت إلياس الخزاز عن الرضا ع قال", "Honorific «ع» in the stored surface only.")
add("cr-0230", "rep", "prefix_noise", "حدثنا محمد بن علي ماجيلويه رحمه الله عن أبي عبد الله ع قال", "Honorific only.")
add("cr-0261", "rep", "prefix_noise", "أبي رحمه الله قال حدثنا سعد بن عبد الله عن الحارثي عن أبي عبد الله ع قال", "Honorific only.")
add("cr-0203", "rep", "relation_word", "عن أبيه، عن جده يعلى بن مرة قال: سمعت رسول الله", "Stored «جده يعلى بن مرة», reader «يعلى بن مرة» (prompt rule 1: relation word before a name gives the name alone).")
add("cr-0218", "rep", "relation_word", "عن أنس بن مالك، عن خالته أم حرام بنت ملحان، قالت", "Stored «خالته أم حرام…», reader «أم حرام بنت ملحان».")
add("cr-0240", "rep", "relation_word", "عن حميد بن عبد الرحمن، عن أمه أم كلثوم بنت عقبة، قالت سمعت رسول الله", "Stored «أمه أم كلثوم…», reader name alone.")
add("cr-0247", "rep", "relation_word", "عن علي بن جعفر عن أخيه موسى بن جعفر عليه السلام قال", "Stored «أخيه موسى بن جعفر», reader «موسى بن جعفر»; plus artifact_clitic («وأبي قتادة»).")
add("cr-0280", "rep", "relation_word", "حدثني أبي موسى بن جعفر قال: حدثني أبي جعفر ابن محمد", "Stored «أبي موسى بن جعفر», reader «موسى بن جعفر»; all ten links the same persons in the same order.")
add("cr-0215", "rep", "name_scope", "عن مالك بن أنس، عن  أبي نعيم، وهب بن كيسان أن جابر بن عبد الله", "Stored 'correct' chain has only the kunya «أبي نعيم» (another stored chain «هب بن كيسان»); text writes kunya then name; reader gives one link «أبي نعيم وهب بن كيسان».")
add("cr-0267", "rep", "noise_in_stored", "وقال علي بن محمد و محمد بن علي عليه السلام: «من قال بالجسم", "Stored link «محمد بن علي من» carries the first matn word; reader «محمد بن علي»; two single-link routes by prompt rule 3.")
add("cr-0268", "rep", "noise_in_stored", "عن أبي هريرة، - رضى الله عنه - رواية قال", "Stored «أبي هريرة - - رواية»; reader «أبي هريرة».")
add("cr-0284", "rep", "bracket_variant", "عن يونس بن عبد الله [عبد الرحمن] عن قدامة بن ملك [مالك]", "Editor's bracketed variants left out by reader; co-transmitters «أبي و علي بن الحسين و محمد بن الحسن» split into three routes (stored merged two of them in an unlabelled chain).")
add("cr-0051", "right", "source_in_matn", "مالك ⏎ ⏎ أن علي ابن أبي طالب قال لا يقطع الصلاة شيء", "Reader adds «علي ابن أبي طالب», named as the speaker of the saying (prompt rule 2). Differs from the source's own sanad field (the Pure Canon label convention).")
add("cr-0084", "right", "imam_named", "عن أبي عبد الله عليه السلام قال: قال أمير المؤمنين عليه السلام: أنا الراعي", "Imam named after the chain as the source of the saying = last link (owner ruling); stored lacks him and keeps «وبهذا الاسناد» as a link.")
add("cr-0136", "right", "imam_named", "قال: قال أمير المؤمنين عليه السلام: لو رأى العبد أجله", "Reader adds the Imam named after the chain; relation words «أبي» dropped (rule 1).")
add("cr-0176", "right", "imam_named", "عن الحسن بن صدقه قال قال أبو الحسن الأول ع قیلوا", "Imam named after the chain is the last link; stored stops at الحسن بن صدقه.")
add("cr-0224", "right", "imam_named", "خرجت إلينا ألواح من أبي الحسن عليه السلام", "Imam named as the source of the tablets; added by reader.")
add("cr-0229", "right", "imam_named", "عن الاصبغ بن نباتة قال: كان أمير المؤمنين عليه السلام يقول", "Imam added; plus artifact_clitic («وأحمد بن إدريس»).")
add("cr-0233", "right", "imam_named", "120 - وبهذا الإسناد قال: قال على بن أبي طالب عليه السلام: إنه لو رأى العبد", "Stored is the lone back reference; the reader adds the Imam named as the speaker.")
add("cr-0273", "right", "imam_named", "قال : قلت لأبي عبد الله عليه السلام شجرة أصلها في الحل", "«قلت لـ X» is a link (prompt rule 5); stored stops at معاوية بن عمار.")
add("cr-0167", "right", "source_in_matn", "لما بويع عثمان سمعت المقداد بن الأسود الكندي رحمه الله يقول", "«سمعت X» names the source (prompt rule 5); stored lacks him.")
add("cr-0283", "right", "source_in_matn", "عن خالد بن عمير العدوي، قال خطبنا عتبة بن غزوان فحمد الله", "Companion who addressed them is the source of the saying; reader adds him (rule 2).")
add("cr-0163", "label_wrong", "stored_missing_link", "حدثني أبو الحسين محمد بن علي الشجاعي الكاتب قال: أخبرنا أبو عبد الله محمد بن إبراهيم المعروف بابن أبي زينب النعماني الكاتب قال: أخبرنا محمد بن عثمان", "Stored chain skips the link «أبو عبد الله محمد بن إبراهيم …النعماني الكاتب» that the text writes; labelled 'correct' (note: «chain matches the text»). Reader right.")
add("cr-0234", "label_wrong", "stored_merged_routes", "عن أبي عبد الله عليه السلام؛ ومحمد بن الحسين عن إبراهيم بن أبي يحيى المدني عن أبي هارون العبدي", "The ';' starts a second isnad; the stored 'correct' chain runs «أبي عبد الله > إبراهيم بن أبي يحيى» across it. Reader writes two routes. Judgement call on how the two isnads relate; the join the stored chain makes is not in the text.")
add("cr-0008", "wrong", "inherited_chain", "349 - وبهذا الإسناد قال: قال رسول الله صلى الله عليه وآله: التائب من الذنب", "Text holds no name; stored (correct) chain is the full chain completed from the previous report. The reader can only return a back reference; applied, it would erase a correct chain.", "ii")
add("cr-0126", "wrong", "inherited_chain", "15 - وبهذا الاسناد، قال: قال الصادق جعفر بن محمد (عليهما السلام): ما من قدم سعت إلى الجمعة", "Stored six-name chain comes from the previous report; the reader sees only the Imam named here. Applying it would replace six links by one.", "ii")
add("cr-0164", "wrong", "inherited_chain", "و بهذا الإسناد عن الحارث بن المغيرة عن أبي عبد الله عليه السلام", "Stored chains hold the inherited names before «الحارث بن المغيرة»; reader returns only what the text shows.", "ii")
add("cr-0193", "wrong", "inherited_chain", "330 - بهذا الإسناد عن النبي صلى الله عليه وآلهقال: من كف غضبه", "Text has no name; stored is an eleven-name inherited chain.", "ii")
add("cr-0201", "wrong", "inherited_chain", "و بهذا الإسناد قال قال علي بن الحسين سيد العابدين ع القائم منا", "Stored chain (inherited) is eight names; reader returns the Imam named here only.", "ii")
add("cr-0013", "wrong", "balagha_gap", "أبو عبيدة عن جابر بن زيد قال: بلغني عن أبي هريرة قال", "«بلغني» marks an unnamed intermediary; the stored (correct) chain keeps it as an anonymous link, the reader drops it. The prompt has no rule for it.", "i")
add("cr-0039", "wrong", "balagha_gap", "أبو عبيدة قال: بلغني عن جابر بن عبد الله قال سمعت رسول الله", "Same as cr-0013.", "i")
add("cr-0266", "wrong", "second_isnad_after_matn", "رواه سعيد عن مالك. وقال عمر بن حمزة سمعت سالما سمعت ابن عمر … وقال أبو اليمان أخبرنا شعيب، عن الزهري", "Main chain right («عمي القاسم» -> «القاسم بن يحيى» is rep) but the appended routes the label requires are excluded by prompt rule 9. Same outcome as stored; the label calls the report defective.", "i")
# ---- class (d) -----------------------------------------------------------------------------------------------------
add("cr-0091", "right", "stored_junk_dropped", "حدثنا قتادة، بهذا الإسناد نحو حديث عفان وقال عون بن عتبة", "Label note says the defect is the extra routes «همام > عون بن عتبة»; reader drops them (the text only says «وقال عون بن عتبة») and keeps the two routes to قتادة.")
add("cr-0117", "wrong", "second_isnad_after_matn", "وحدثنيه زهير بن حرب، حدثنا عبد الصمد بن عبد الوارث، حدثنا همام", "The second isnad after the first matn is a real route (label missing_route); excluded by prompt rule 9, so the reader returns one route.", "i")
add("cr-0147", "right", "stored_junk_dropped", "كلهم عن الزهري، بهذا الإسناد أهديت له حمار وحش . كما قال مالك", "Reader's five routes match the three ح-groups ending «كلهم عن الزهري»; the junk stored chain «…> حش كما» is dropped.")
add("cr-0213", "wrong", "second_isnad_after_matn", "قال محمد بن رافع وأخبرنا محمد بن بشر أخبرنا علي بن نزار عن نزار عن عكرمة", "Second isnad written right after the first, before «نحوه»; no matn between, so it is a route; reader returned only the first.", "i")
add("cr-0238", "right", "stored_junk_dropped", "و سأل موسى بن بكر أبا الحسن موسى بن جعفر عليهما السلام: عن الرجل يقوم في الصف وحده", "Reader's two links match the correct stored chain; the junk link «حده» (matn word «وحده») is not added.")
# ---- class (c): the 40 read ----------------------------------------------------------------------------------------
add("cr-0010", "wrong", "source_dropped", "حدثني نبيه بن وهب، أن عمر بن عبيد الله بن معمر، رمدت عينه … فنهاه أبان بن عثمان … وحدث عن عثمان بن عفان", "Reader stops at «نبيه بن وهب»: loses عمر بن عبيد الله (rule 5 «أن X»), أبان بن عثمان and عثمان بن عفان. Worse than stored, which at least ends at عثمان.", "i")
add("cr-0020", "wrong", "second_isnad_after_matn", "حدثنا بذلك هناد وقتيبة قالا حدثنا وكيع عن ثابت بن أبي صفية", "Reader's «وكيع > ثابت > أبي جعفر > جابر» is much better than stored, but the heads «هناد وقتيبة» are written after the saying and are missing.", "i")
add("cr-0026", "right", "stored_junk_dropped", "حدثنا موسى، حدثنا معتمر، وقال، لم يبتئر. وقال خليفة حدثنا معتمر", "Label: false link (stored «موسى > خليفة > معتمر»). Reader gives «موسى > معتمر». «وقال خليفة …» is a separate appended route (note-only by rule 9).")
add("cr-0048", "wrong", "irsal_gap", "عن محمد بن عيسى بإسناده يرفعه إلى أبي جعفر عليه السلام", "Reader cleans the name but writes «محمد بن عيسى > أبي جعفر» as if direct; the label wants the name plus an anonymous gap for «بإسناده يرفعه».", "i")
add("cr-0053", "wrong", "source_in_matn_missed", "فجاء المغيرة بن شعبة فصعد المنبر … أما إني سمعت رسول الله صلى الله عليه وسلم يقول", "المغيرة is the Companion source of the saying (rule 2); the reader kept the three routes but did not add him.", "i")
add("cr-0078", "right", "plain_new_chain", "قال الربيع: بلغني عن جويبر عن الضحاك عن ابن عباس", "Stored had no chain; reader reads «جويبر > الضحاك > ابن عباس» (compiler «الربيع» not a link, his own «بلغني» not a link).")
add("cr-0079", "wrong", "balagha_gap", "أبو عبيدة قال: بلغني عن ابن عمر يروي عن رسول الله", "Reader drops both the verb «يروي» (right) and the anonymous «بلغني» link the work's convention keeps (cr-0013).", "i")
add("cr-0089", "right", "stored_junk_dropped", "5- وفي رواية أخرى عن أبي عبد الله (عليه السلام)", "Stored link «أخرى» is a word; reader «أبي عبد الله».")
add("cr-0090", "wrong", "over_applied_rule_5", "قال سأل شباك إبراهيم فحدثنا عن علقمة، عن عبد الله", "Reader applies «سأل X Y = two links» and makes شباك a transmitter between مغيرة and إبراهيم; he is the asker, the chain goes مغيرة > إبراهيم > علقمة.", "i")
add("cr-0097", "right", "stored_junk_dropped", "تابع/, روح, عبد الصمد, همام, قتادة", "«تابع/» is a source-field label, not a name; reader drops it.")
add("cr-0098", "right", "stored_junk_dropped", "ومنهم محصن بن غسان بن ظالم الزبيدي،عاش مائتي سنة وستا وخمسين سنة", "A biography line with no chain; reader returns no route; stored had two junk chains.")
add("cr-0102", "wrong", "unnamed_gap", "فقال أخبرني من سمع رسول الله صلى الله عليه وسلم في حجة الوداع", "Reader: «أحمد > سليم > مطير» (good, drops junk) but the anonymous informant «من سمع رسول الله» is an unnamed link it omits.", "i")
add("cr-0106", "right", "stored_junk_dropped", "عن عمران بن حصين، أنه سأل رسول الله صلى الله عليه وسلم عن الرجل يصلي قاعدا", "Stored last link «الرجل يصلي قاعدا» is the question; reader ends at عمران.")
add("cr-0108", "wrong", "second_isnad_after_matn", "وحدثنا آدم حدثنا شعبة حدثنا أبو إسحاق الهمداني عن البراء بن عازب", "Second isnad (label missing_route) comes before the saying; reader returned only the two routes of the first.", "i")
add("cr-0120", "right", "source_in_matn", "قال: سئل أسامة بن زيد: كيف كان رسول الله صلى الله عليه وسلم يسير", "The answerer is the source (rule 2); reader adds «أسامة بن زيد». Label calls it a judgment.")
add("cr-0127", "right", "stored_junk_dropped", "كلاهما عن حماد بن زيد، - قال أبو الربيع حدثنا حماد، - حدثنا أيوب", "The repeated «حماد» is one man mentioned twice; reader gives one link, two routes.")
add("cr-0140", "right", "source_in_matn", "سمعت جدي عبيدة ابن عمرو الكلابي يقول رأيت رسول الله", "«سمعت X» names the source (rule 5); reader adds it, drops the clause «سمعته أنا من».")
add("cr-0141", "wrong", "complex_tahwil", "جميعا عن أبي معشر، ح وحدثنا أبو بكر بن أبي شيبة", "Five ح-groups with «جميعا عن أبي معشر» shared by some: reader drops «أبي معشر» from the first route and splits «عبدة بن سليمان … ابن أبي عروبة» into two routes, instead of one chain.", "iv")
add("cr-0153", "right", "inherited_backref_only", "و بهذا الإسناد قال قال علی ع أیها الناس", "Stored: back reference plus a junk matn phrase; reader: the Imam named. Nothing stored is lost.")
add("cr-0158", "right", "unnamed_link", "حدثنا عبد بن حميد، وغير واحد، - المعنى واحد قالوا", "Reader: one route from «عبد بن حميد», one from the unnamed «غير واحد»; gloss left out; stored «احد» junk.")
add("cr-0169", "right", "imam_named", "عن أبي الصباح الكناني عن أبي عبد الله (عليه السلام) في قول الله", "Stored last link is matn words; reader the Imam.")
add("cr-0172", "right", "stored_junk_dropped", "أبو النعمان انا حماد ابن يزيد, ثابت", "Two names and a verb in one stored link; reader splits.")
add("cr-0179", "right", "unnamed_link", "علي بن أسباط عمن روى في الجلالات قال", "Reader: «علي بن أسباط > عمن روى» (unnamed link), stored merged them.")
add("cr-0184", "right", "source_in_matn", "عن أبي قلابة، أن أبا المليح، حدثه قال كنا مع بريدة", "Reader adds بريدة, who is the Companion source.")
add("cr-0189", "right", "source_in_matn", "أخبرنا عمرو، - يعني ابن الحارث - أن ابن شهاب، حدثه عن أبي إدريس", "«أن X حدثه» (rule 5): reader adds ابن شهاب; junk tail dropped.")
add("cr-0197", "right", "compiler_named", "حدثنا الشيخ الجليل أبو جعفر محمد بن علي بن الحسين بن موسى ابن بابويه القمي (رضي الله عنه)، قال: حدثنا أبي", "The compiler is named in the text; under the owner ruling (compiler heads the chain) the reader's first link is right; stored dropped him and mangled «وهب ابن وهب». Also adds «أم سلمة».")
add("cr-0207", "right", "stored_junk_dropped", "عن ابن عباس  رضى الله عنهما – {ولكل جعلنا موالي} قال ورثة", "Stored link is the verse; reader ابن عباس.")
add("cr-0217", "right", "stored_junk_dropped", "عن نافع، عن ابن عمر، رواية قال", "«رواية» is not part of the name.")
add("cr-0227", "wrong", "inherited_chain", "20 - وبهذا الإسناد قال: قال رسول الله صلى الله عليه وآله وسلم: إن الله عز وجل عمودا", "Text has no name; stored holds four inherited chains (one with a junk link). Reader would return nothing.", "ii")
add("cr-0241", "right", "stored_junk_dropped", "عن ابن أبي عمير عن بعض أصحابنا عن أحدهما (عليهما السلام) في الرجل يحدث", "Reader reproduces the correct chain and drops the junk second chain.")
add("cr-0242", "right", "stored_junk_dropped", "قال أبو الحسن القطان حدثناه خازم بن يحيى، حدثنا عبد الملك بن شيبان", "Two persons and a verb merged in stored; reader splits.")
add("cr-0248", "right", "stored_missing_link", "حدثنا يزيد بن خالد، وقتيبة، أن الليث بن سعد، حدثهم عن بكير", "«أن X حدثهم»: reader adds الليث بن سعد to both routes.")
add("cr-0251", "right", "stored_missing_link", "أخبرنا ابن جريج، قال عمرو بن دينار قال ابن عباس", "Reader adds عمرو بن دينار and ابن عباس.")
add("cr-0252", "right", "stored_missing_link", "قال قرأت على عبد الله بن عمر { الله الذي خلقكم من ضعف }", "Reader adds عبد الله بن عمر.")
add("cr-0253", "right", "stored_missing_link", "حدثنا محمد بن كثير، ح وحدثنا مسلم بن إبراهيم، حدثنا همام، عن قتادة", "The shared tail is given to both routes; stored had the lone «محمد بن كثير».")
add("cr-0255", "wrong", "imam_missed", "كنت أنا و يونس بن ظبيان و المفضل بن عمر و أبو سلمة السراج جلوسا عند أبي عبد الله (ع) و كان المتكلم يونس", "The Imam is the source of the saying and is named after the chain; reader's routes end at «الحسين بن ثوير بن أبي فاختة» (the three heads «أبي، علي بن الحسين، محمد بن الحسن» are right).", "i")
add("cr-0263", "right", "stored_junk_dropped", "و روى أبان عن بكير و الحلبي عن أحدهما عليهما السلام", "Two co-transmitters merged in stored; reader writes two routes.")
add("cr-0271", "right", "stored_missing_link", "حدثنا يحيى بن يحيى، قال قرأت على مالك عن نافع، عن زيد بن عبد الله", "Stored kept only the first name; reader the full chain.")
add("cr-0278", "right", "stored_missing_link", "قال سمعت مسروقا، والأسود، قالا نشهد على عائشة أنها قالت", "Reader: two routes ending at عائشة.")
add("cr-0279", "rep", "prefix_noise", "138 - وعن أبي عبد الله عليه السلام قال: قال رسول الله", "Stored «وعن أبي عبد الله», reader «أبي عبد الله»; continuation of the previous report (inherited chain not in this text).")
# ---- 'a' reports where reading them turned up a call to make -----------------------------------------------------
add("cr-0237", "cannot_tell", "subject_vs_source", "أن عمر بن الخطاب، رأى حلة سيراء عند باب المسجد فقال يا رسول الله", "Bukhari report of an event of عمر; whether he is a link (source of the story) or only its subject is a judgment; stored and both readers omit him.", "i")
add("cr-0015", "cannot_tell", "subject_vs_source", "مالك, نافع ⏎ ⏎ أن عبد الله ابن عمر كان لا يقرأ في الصلاة على الجنازة", "Pure Canon: the field has two names; the practice is Ibn ʿUmar's; reader (like the field) omits him, but cr-0051 shows the reader adds a named speaker. Policy needed.", "i")
add("cr-0027", "cannot_tell", "subject_vs_source", "أن ابنة عبيد الله ابن عمر … فقال عبد الله ابن عمر ليس لها صداق", "Same as cr-0015.", "i")
add("cr-0138", "wrong", "source_in_matn_missed", "قال أبو بكر مررنا براع وقد عطش رسول الله صلى الله عليه وسلم", "Abu Bakr narrates the story in the first person; he is the source (rule 2); reader ends at البراء.", "i")
add("cr-0258", "wrong", "source_in_matn_missed", "أتوا حذيفة، فقالوا … فقال: سمعت رسول الله (صلى الله عليه وآله) يقول", "The speaker of the Prophet's saying is a source link (rule 2); reader ends at بلال بن يحيى العبسي.", "i")

# ---- reports agreed only when offsets are ignored (not in the validated agreed set): 12 read -----------------------
LENIENT_ONLY = {
    "cr-0139": ("cannot_tell", "complex_tahwil", "كل هؤلاء عن الأعمش، عن أبي سفيان، عن جابر، . زاد عمرو في روايته عن عمار، وأبو كريب في روايته عن أبي معاوية، فقالا عن أم مبشر", "Reader gives the base chain (five routes ending جابر); the text adds per-route variants «عن أم مبشر» whose placement I cannot settle."),
    "cr-0036": ("rep", "prefix_noise", "عن جعفر بن محمد عن أبيه عن آبائه ع قال", "Honorific only."),
    "cr-0045": ("right", "imam_named", "قال قلت لأبي عبد الله ( عليه السلام ) رجل يعرف رأيه مرة", "Four parallel routes joined by «جميعا عن صفوان»; Imam added."),
    "cr-0055": ("rep", "prefix_noise", "عن سوره بن كليب عن أبي عبد الله ع قال", "Honorific only."),
    "cr-0060": ("right", "imam_named", "عن أبي الجارود قال: قالت لأبي جعفر", "Imam added; two routes for «محمد بن همام ومحمد بن الحسن بن محمد بن جمهور، جميعا»."),
    "cr-0067": ("right", "plain_match", "عن محمد بن الحسين وأحمد بن محمد عن ابن محبوب", "Two parallel routes; Imam last."),
    "cr-0083": ("right", "plain_match", "قال سمعت أبا عبد الله ( عليه السلام ) يقول", "Two routes, Imam last."),
    "cr-0095": ("rep", "prefix_noise", "عن عبد الله بن موسى بن جعفر ع قال", "Honorific only."),
    "cr-0119": ("right", "imam_named", "قال : قلت لأبي عبد الله عليه السلام إنه ذكر لنا", "«قلت لـ X» link."),
    "cr-0124": ("right", "stored_junk_dropped", "عن أبي بصير فقال : سألت أبا عبد الله عليه السلام عن محرم قتل ثعلبا", "Stored merged matn words into the links; reader reads البزنطي > علي بن أبي حمزة > أبي بصير > أبا عبد الله."),
    "cr-0134": ("right", "stored_junk_dropped", "و سأل سليمان بن جعفر الجعفري العبد الصالح موسى بن جعفر", "Asker and Imam as two links (rule 5)."),
    "cr-0210": ("right", "plain_match", "عن القاسم بن يحيى عن جده الحسن بن راشد. و رويته عن محمد بن علي ماجيلويه", "Two isnads kept apart; first has three parallel co-transmitters."),
}
