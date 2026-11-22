"""Hand verdicts for the v2 agreed reports that were read in this pass (81), and for the 30 random disagreements.

Agreed reports whose non-derived routes equal v1's agreed reading and carry no inherited link keep the verdict I gave v1 (carry_v2.json): 142.
Codes: right | rep | wrong | label_wrong | cannot_tell | abstain (the readers answered cannot_read_without_previous_report: no reading to judge).
Entry: id -> (verdict, tag, fix, quote, why). fix: i prompt wording, ii packet/context, iii tool/hold, iv not fixable by a reader.
"""

V2 = {}


def add(i, verdict, tag, quote, why, fix=""):
    V2[i] = (verdict, tag, fix, quote, why)


# ---- chunk 1 ---------------------------------------------------------------------------------------------------------------
add("cr-0007", "right", "plain", "وحدثناه أبو بكر، وأبو كريب وابن نمير عن عبد الله بن نمير، ح وحدثناه عمرو الناقد، حدثنا وكيع، كلهم عن هشام", "Six routes from four ح groups to هشام; «بهذا الإسناد» kept as a back_reference at the end.")
add("cr-0013", "right", "balagha_gap_fixed", "قال: بلغني عن أبي هريرة قال", "v1 wrong: «بلغني» is now an unnamed link between جابر بن زيد and أبي هريرة.")
add("cr-0016", "right", "plain", "يحيى, مالك, ابن شهاب, سعيد ابن المسيب, أبي هريرة | يحيى, مالك, ابن شهاب, عن أبي سلمة ابن عبد الرحمن, أبي هريرة", "Two field routes; the stray «عن» is not part of the name.")
add("cr-0021", "right", "unnamed_link", "حدثنا محمد بن يحيى، وغير، واحد، قالوا حدثنا أبو عاصم، عن وهب أبي خالد، قال حدثتني أم حبيبة بنت العرباض، وهو ابن سارية عن أبيها", "Unnamed «غير واحد» is a parallel head; «أبيها» is a bare relation link; the gloss «وهو ابن سارية» is left out.")
add("cr-0024", "right", "imam_speaker", "عن عذافر قال سمعت أبا عبد الله (عليه السلام) وقد سئل عن كسب النائحة", "Imam heard from: last link (imam_in_text). Hold drops_stored_name is a false hold: the stored name is the matn phrase «كسب النائحة».")
add("cr-0026", "right", "second_route", "حدثنا موسى، حدثنا معتمر، وقال، لم يبتئر. وقال خليفة حدثنا معتمر", "Second route «خليفة > معتمر» as a group (rule 4); stored false link dropped.")
add("cr-0028", "right", "plain", "1- عدة من أصحابنا عن أحمد بن محمد عن ابن فضال عن مثنى عن زرارة عن أبي عبد الله", "Unnamed «عدة من أصحابنا» head, Imam inside the chain stays a narrator.")
add("cr-0033", "wrong", "spurious_route", "قال الزهري ألا أحدثك بحديثين عجيبين قال الزهري أخبرني حميد بن عبد الرحمن", "Third route «الزهري > حميد > أبي هريرة» is the same man restated inside the chain, not another route; both passes add it.", "i")
add("cr-0039", "right", "balagha_gap_fixed", "أبو عبيدة قال: بلغني عن جابر بن عبد الله", "v1 wrong: «بلغني» now an unnamed link after أبو عبيدة.")
add("cr-0045", "right", "plain", "أبو علي الأشعري عن محمد بن عبد الجبار و أبو العباس الرزاز عن أيوب بن نوح و حميد بن زياد عن ابن سماعة و محمد بن إسماعيل عن الفضل بن شاذان جميعا عن صفوان", "Four routes, Imam added («قلت لأبي عبد الله»).")
add("cr-0046", "right", "plain", "8- علي بن إبراهيم عن أبيه عن ابن أبي عمير عن حماد عن الحلبي عن أبي عبد الله (عليه السلام) قال سئل", "Imam inside the chain: narrator.")
add("cr-0047", "right", "plain", "عن زرعة بن محمد عن سماعة وعن المفضل بن عمر عن أبي عبد الله", "«سماعة» and «المفضل بن عمر» as two alternatives of one level; a mild real ambiguity (flag by A).")
add("cr-0048", "right", "irsal_gap_fixed", "عن محمد بن عيسى بإسناده يرفعه إلى أبي جعفر عليه السلام", "v1 wrong: now «محمد بن عيسى > [unnamed] بإسناده يرفعه إلى > أبي جعفر».")
add("cr-0049", "rep", "relation_word", "عن علي بن جعفر عن أخيه أبي الحسن ( عليه السلام ) قال سألته", "Stored «أخيه أبي الحسن»; reader «أبي الحسن» (name alone, rule 7).")
add("cr-0052", "abstain", "cannot_read", "8 عنه عن عدة من أصحابنا رفعوه إلى أبي عبد الله (عليه السلام)", "Both passes answered cannot_read_without_previous_report; held three ways.")
add("cr-0053", "right", "speaker_fixed", "أما إني سمعت رسول الله صلى الله عليه وسلم يقول", "v1 wrong: المغيرة، who speaks the saying, is now the last link.")
add("cr-0056", "right", "imam_speaker", "قال سمعت أبا عبد الله (عليه السلام) يقول", "Imam heard from: last link.")
add("cr-0060", "right", "imam_asked_flag_unneeded", "قال: قالت لأبي جعفر: إذا مضى الإمام القائم … قال: بالهدى والإطراق", "The Imam who is addressed and answers is the last link (settled); run B flagged needs_ruling anyway.")
add("cr-0062", "right", "plain", "علي عن أبي عبد الله بن صالح وأحمد بن النضر عن القنبري رجل من ولد قنبر الكبير مولى أبي الحسن الرضا", "Two routes from the head «علي»; the gloss after القنبري is left out. Hold drops_stored_name fires on the stored fragment «رجل من».")
add("cr-0063", "right", "plain", "عدة من أصحابنا عن أحمد بن محمد بن خالد عن عثمان بن عيسى عن رجل عن أبي عبد الله", "Two unnamed links.")
add("cr-0064", "right", "no_chain", "وسئل النبيء صلى الله عليه وسلم يوما عن الإيمان وكان متقنعا بردائه", "No chain: both readers return none; the stored link «الإيمان» is a word. Hold reading_empty_stored_has_links fires (false).")
add("cr-0066", "right", "speaker", "قال كان أبو نهيك رجلا أكولا فقال له ابن عمر إن رسول الله صلى الله عليه وسلم قال", "ابن عمر speaks the saying: last link.")
add("cr-0067", "right", "plain", "عن محمد بن الحسين وأحمد بن محمد عن ابن محبوب عن محمد بن الفضيل", "Two parallel routes.")
add("cr-0069", "right", "imam_asked_flag_unneeded", "وصفت لأبي عبد الله رجلا … فقال: إن مات هذا مات ميتة جاهلية", "Imam who answers: last link; run B flagged needs_ruling on this settled case.")
add("cr-0075", "right", "parallel_imams_fixed", "عن الحلبي و زرارة و محمد بن مسلم و حمران بن أعين عن أبي جعفر و أبي عبد الله ( عليه السلام ) قالا", "Eight routes, each ending in one of the two Imams (v1: neither pass right).")
add("cr-0077", "right", "imam_speaker", "قال سمعت أبا عبد الله (عليه السلام) يقول", "Imam heard from.")
add("cr-0078", "right", "balagha_gap", "قال الربيع: بلغني عن جويبر عن الضحاك عن ابن عباس", "Reader writes the compiler's own «بلغني» as an unnamed head link: consistent with the work's balagha convention (the gap is real).")
add("cr-0079", "right", "balagha_gap_fixed", "أبو عبيدة قال: بلغني عن ابن عمر يروي عن رسول الله", "v1 wrong: «بلغني» now unnamed.")
# ---- chunk 2 ---------------------------------------------------------------------------------------------------------------
add("cr-0088", "right", "speaker", "قلنا لابن عباس أرأيت قول الله عز وجل", "«قلنا لـ X»: link (rule 5).")
add("cr-0093", "right", "imam_asked", "قال قلت لأبي عبد الله (عليه السلام) إن رجلا أوصى إلي بشيء", "Imam addressed and answering.")
add("cr-0094", "right", "imam_asked", "قال سألت الرضا (عليه السلام) عن الرجل يلمس فرج جاريته", "Imam asked.")
add("cr-0095", "rep", "flag_unneeded", "عن عبد الله بن موسى بن جعفر ع قال : سألته عن الملكين", "The last link already answers; run B flagged needs_ruling on a settled case. Stored differs only by the honorific.")
add("cr-0101", "right", "plain", "عن حبيب، مولى عروة عن بدية، - وكان الليث يقول ندبة - مولاة ميمونة عن ميمونة قالت", "Two routes (يونس / الليث), ميمونة added (speaker).")
add("cr-0102", "right", "unnamed_and_second_isnad", "فقال أخبرني من سمع رسول الله … قال أبو داود ورواه ابن المبارك عن محمد بن يسار عن سليم بن مطير", "Unnamed informant as last link; appended isnad as a second group (rule 4). drops_stored_name is a false hold (stored junk «ادي القرى»).")
add("cr-0104", "right", "unnamed_link", "11 غير واحد من أصحابنا عن أحمد بن أبي عبد الله عن غير واحد عن أبي جميلة", "Two unnamed links.")
add("cr-0105", "right", "plain", "و روى عمار الساباطي عن أبي عبد الله عليه السلام", "Imam after «عن» is a narrator; previous report irrelevant.")
add("cr-0108", "right", "second_isnad_fixed", "وحدثنا آدم حدثنا شعبة حدثنا أبو إسحاق الهمداني عن البراء بن عازب", "v1 wrong: third route added.")
add("cr-0111", "right", "alternative_flag_real", "عن سعيد بن يسار أو غيره قال سمعت أبا عبد الله", "«أو غيره» as an unnamed alternative; second isnad after the bracket as its own group. A real ambiguity, flagged by B.")
add("cr-0113", "right", "plain", "حدثنا عبدان، عن أبي حمزة، عن الأعمش، عن شقيق، عن عبد الله، قال قسم النبي", "Plain.")
add("cr-0114", "right", "plain", "عن حبيب، مولى عروة عن بدية … عن ميمونة قالت", "As cr-0101.")
add("cr-0117", "right", "second_isnad_fixed", "وحدثنيه زهير بن حرب، حدثنا عبد الصمد بن عبد الوارث، حدثنا همام", "v1 wrong: second route after the matn is now a group.")
add("cr-0119", "right", "imam_asked", "قال : قلت لأبي عبد الله عليه السلام إنه ذكر لنا", "Imam addressed.")
add("cr-0122", "right", "flag_unneeded", "عن أبي صادق، عن أمير المؤمنين أنه قال: ملك بني العباس", "Imam inside the chain after «عن»: narrator (settled); A flagged needs_ruling.")
add("cr-0124", "right", "imam_asked", "عن أبي بصير فقال : سألت أبا عبد الله عليه السلام", "Imam asked; stored junk merged.")
add("cr-0125", "right", "plain", "عن الزهري، عن أبي، سلمة عن جابر، ح", "Truncated text.")
add("cr-0126", "right", "inherited_fixed", "15 - وبهذا الاسناد، قال: قال الصادق جعفر بن محمد (عليهما السلام)", "v1 wrong: the six names of prev1 are written as inherited, then the Imam named here (imam_in_text). Previous chain_text: «حدثنا الحسن بن إبراهيم بن ناتانه … عن عبد الله بن بكير،».")
add("cr-0129", "right", "imam_scene_speaker", "كنت عند أبي عبد الله في بيته … فقال: ما يبكيك يا عمرو", "The Imam answers and speaks the saying.")
add("cr-0131", "right", "plain", "وحدثنيه عبيد الله بن عمر القواريري، حدثنا خالد … حدثنا هشام، بهذا الإسناد", "Three routes; the second ends with a back_reference, not expanded.")
add("cr-0133", "wrong", "shared_tail_missed", "ح وأنبأنا حميد بن مسعدة، عن سفيان بن حبيب، عن الأوزاعي، قال حدثنا أبو كثير، قال سمعت أبا هريرة", "Route one stops at «أبو كثير»; the text writes «أبا هريرة» once, after the second branch, for both. v1 had it right (regression).", "i")
add("cr-0134", "right", "asker_not_link", "و سأل سليمان بن جعفر الجعفري العبد الصالح موسى بن جعفر عليهما السلام: عن الرجل", "Single link: the Imam who is asked (owner ruling; v1 had asker plus Imam). Both readers flagged needs_ruling although the prompt's rule 5 settles it.")
add("cr-0136", "wrong", "poem_isnad_as_route", "وأنشدني أبو الفرج البرقي الداودي قال: أنشدني شيخ كان منقطعا إلى الله تعالى ببيت المقدس: ومنتظر للموت", "Second route «أبو الفرج البرقي > شيخ» is the isnad of a poem appended to the report, not of the saying (v1 right).", "i")
add("cr-0143", "wrong", "concatenated_reports", "عن علي بن أبي حمزة و محمد بن يحيى عن أحمد بن محمد عن علي بن الحكم عن علي بن أبي حمزة عن أبي بصير مثله .حميد بن زياد عن ابن سماعة", "Two isnads run together: the reading crosses «علي بن أبي حمزة» into the second isnad. Held: back_reference_without_previous_report.", "iv")
add("cr-0144", "wrong", "duplicate_link", "كلاهما عن المعتمر، قال ابن حبيب حدثنا معتمر بن سليمان", "The same man written twice (المعتمر, معتمر بن سليمان) is kept as two links by both passes.", "i")
add("cr-0146", "right", "scene_subject", "رأى سالم ابن عبد الله يخرج من أنفه الدم حتى تختضب أصابعه", "Salim is the subject of what was seen, not the speaker: not a link (owner ruling); v1 disagreement.")
add("cr-0149", "right", "no_chain", "5813 - الدال على الخير كفاعله", "Advice only; no chain. Hold reading_empty_stored_has_links fires (false).")
add("cr-0153", "abstain", "cannot_read", "و بهذا الإسناد قال قال علی ع أیها الناس", "cannot_read_without_previous_report by both.")
# ---- chunk 3 ---------------------------------------------------------------------------------------------------------------
add("cr-0156", "right", "plain", "أبي رحمه الله، قال: حدثني سعد بن عبد الله قال: حدثنى عباد بن سليمان", "Imam inside chain: narrator.")
add("cr-0157", "wrong", "shared_tail_missed", "عن أبيه عن ابن أبي عمير ومحمد بن إسماعيل عن الفضل بن شاذان عن صفوان بن يحيى وابن أبي عمير عن معاوية بن عمار", "First route stops at «ابن أبي عمير»: the tail «معاوية بن عمار > أبي عبد الله» is written once for both (v1: B right, A wrong; now both wrong).", "i")
add("cr-0171", "right", "no_chain", "3286 - و في خبر آخر : \"أنه لا تقبل شهادة الولد على والده \"", "No chain; hold false.")
add("cr-0173", "right", "speaker", "أنه نظر إلى عبد الله بن عمر كيف يحكي رسول الله صلى الله عليه وسلم قال \" يأخذ الله", "ابن عمر speaks the saying: last link.")
add("cr-0177", "wrong", "speaker_omitted", "فقال إن رسول الله صلى الله عليه وسلم قال \" إن القبر أول منازل الآخرة", "عثمان speaks the saying to those who asked; reading ends at «هانئا، مولى عثمان» and does not flag it (v1 cannot_tell).", "i")
add("cr-0181", "right", "unnamed_link", "عن زرارة عن أحدهما (عليهما السلام) في محرمين", "«أحدهما» as an unnamed link. drops_stored_name false hold (stored junk).")
add("cr-0182", "right", "imam_single", "و قال أبو جعفر عليه السلام : «البر و الصدقة ينفيان الفقر", "Single-link route: the Imam who speaks.")
add("cr-0187", "right", "parallel_narrators_fixed", "حدثني إياس بن الحارث بن المعيقيب، وجده، من قبل أمه أبو ذباب عن جده", "Two parallel narrators (إياس, أبو ذباب) from «جده» (v1: both passes wrong). A flagged needs_ruling on the three heads (unneeded).")
add("cr-0190", "right", "second_isnad", "قال الكليني (رحمه الله): وحدثني شيخ من أصحابنا - ذهب عني اسمه - أن أبا عمرو سأل أحمد بن إسحاق", "Third route «الكليني > [unnamed] شيخ من أصحابنا» is a real second isnad written in the report (the compiler named in the text).")
add("cr-0194", "right", "inherited", "91 - وعنه (ع) قال لكل شئ شئ يستريح إليه", "«عنه» takes the Imam of prev1 («وعن أبي عبد الله (ع) قال …»), written as inherited.")
add("cr-0195", "right", "unnamed_and_imam", "حدثني سعد بن عبد الله بإسناد يرفعه، عن منصور الصيقل، قال: كنت عند أبي عبد الله عليه السلام في فسطاطه بمنى، فنظر إلى الناس فقال", "Unnamed gap «بإسناد يرفعه» and the Imam who speaks (v1 disagreement).")
add("cr-0201", "abstain", "cannot_read", "و بهذا الإسناد قال قال علي بن الحسين سيد العابدين ع", "cannot_read_without_previous_report by both.")
add("cr-0202", "wrong", "extra_unnamed_link", "قال أخبرني من، شهد النبي صلى الله عليه وسلم … قلت من حدثك قال ابن عباس", "The unnamed «من» is identified by the answer «ابن عباس»: one link, not an unnamed link plus ابن عباس. Both flagged needs_ruling (real ambiguity, and the flag caught it).", "i")
add("cr-0210", "right", "plain", "عن سعد بن عبد الله؛ و أحمد بن محمد بن عيسى؛ و إبراهيم بن هاشم جميعا عن القاسم بن يحيى عن جده الحسن بن راشد", "Four routes. Holds nested_jami + nested_semicolon fire on a correct reading (false).")
add("cr-0213", "right", "second_isnad_fixed", "قال محمد بن رافع وأخبرنا محمد بن بشر أخبرنا علي بن نزار عن نزار عن عكرمة", "v1 wrong: second route now present.")
add("cr-0214", "right", "plain", "كلهم عن يحيى بن أبي كثير، بهذا الإسناد نحوه", "Five routes with back_reference.")
add("cr-0235", "abstain", "cannot_read", "s131- وبهذا الإسناد عن ابن عباس في قوله", "cannot_read_without_previous_report by both.")
add("cr-0238", "right", "asker_not_link", "و سأل موسى بن بكر أبا الحسن موسى بن جعفر عليهما السلام: عن الرجل يقوم في الصف وحده", "Single link: the Imam asked (owner ruling).")
add("cr-0243", "right", "plain", "أخبرني أبي وأم عبد الملك بن أبي محذورة، عن أبي محذورة", "Two routes: a bare «أبي» relation and the mother.")
add("cr-0255", "right", "imam_scene_speaker_fixed", "جلوسا عند أبي عبد الله (ع) و كان المتكلم يونس … قال إذا حضرتهم و ذكرتنا فقل", "v1 wrong: the Imam who speaks is now the last link; the three heads right.")
add("cr-0260", "right", "plain", "قال سفيان وزاد فيه أبو الزناد عن الأعرج عن أبي هريرة", "Appended route as its own group.")
add("cr-0262", "right", "speaker", "فسمعته يقول بينا نحن مع رسول الله", "The Companion heard from is the last link.")
add("cr-0272", "right", "plain", "عن حماد بن عيسى عن بعض أصحابنا عن أبي عبد الله (عليه السلام) أنه سئل عن التيمم", "Plain; hold false (stored junk).")
add("cr-0280", "right", "second_isnad_comment", "وقد روى هذا الحديث عن أبي الصلت الهروي عبدالسلام بن صالح، عن علي ابن موسى الرضا باسناد مثله", "Second group from the appended «ورواه X عن Y» (rule 4). Both readers flagged needs_ruling although the ten-link chain is settled.")
add("cr-0282", "right", "plain", "عن ابن عباس، رضى الله عنهما في قوله {اللات والعزى}", "Stored junk dropped.")

# v1 cannot_tell resolved by the owner rulings given for v2: a person whose action is described is not a link
add("cr-0015", "right", "scene_subject_per_ruling", "مالك, نافع ⏎ ⏎ أن عبد الله ابن عمر كان لا يقرأ في الصلاة على الجنازة", "Ibn ʿUmar's practice is described; he does not speak the report (ruling: a person whose action is described is not a link); v1 cannot_tell.")

# ---- the 30 random disagreements -------------------------------------------------------------------------------------------------------
# id -> (class, who_is_right, fix, quote, what_differs)
DIS = {
    "cr-0006": ("tool_orthography_invalid", "A", "iii", "حدثنا محمد بن سليمان الأنباري، حدثنا وكيع، عن سفيان", "B invalid: asked for occurrence 2 of «وكيع», which stands once. A right."),
    "cr-0010": ("narrative_embedded", "B closer", "i", "فنهاه أبان بن عثمان … وحدث عن عثمان بن عفان", "A ends «نبيه > عثمان بن عفان»; B «نبيه > أبان بن عثمان > عثمان بن عفان». Both omit «أن عمر بن عبيد الله»."),
    "cr-0011": ("shared_tail_missed", "B", "i", "حدثنا مسدد، حدثنا يحيى، ح وحدثنا عثمان بن أبي شيبة، عن ابن نمير، عن عبيد الله، عن نافع", "A stops the first route at «يحيى»; B gives it the tail."),
    "cr-0019": ("tool_orthography_invalid", "A (held)", "iii", "و بهذا الإسناد عن يونس بن عبد الرحمن", "B invalid: «وبهذا الإسناد» not found because the text writes «و بهذا» with a space."),
    "cr-0020": ("shared_tail_missed", "neither", "i", "حدثنا بذلك هناد وقتيبة قالا حدثنا وكيع عن ثابت بن أبي صفية", "A invalid (order); B: route one complete, routes «هناد > وكيع > ثابت» and «قتيبة > …» stop before «أبي جعفر > جابر»."),
    "cr-0031": ("tool_orthography_invalid", "both (invalid)", "iii", "عن أبيه على بن محمد، عن أبيه محمد بن على", "Both invalid: the text writes «على» (alef maqsura), the readers «علي»."),
    "cr-0032": ("nested_multi_isnad", "neither", "iv", "عن أيوب بن نوح؛ و إبراهيم بن هاشم جميعا عن صفوان بن يحيى؛ و ابن أبي عمير جميعا عن محمد بن حمران", "A and B both break the second isnad into fragments and differ in the third route."),
    "cr-0036": ("tool_orthography_invalid", "B", "iii", "أبی رحمه الله قال حدثنی أحمد بن إدریس", "A invalid: the text uses Persian yeh (ی), A wrote «أبي»."),
    "cr-0051": ("speaker_omitted", "A", "i", "أن علي ابن أبي طالب قال لا يقطع الصلاة شيء", "A adds the speaker of the saying; B keeps the field's single name."),
    "cr-0055": ("tool_orthography_invalid", "both (invalid)", "iii", "حدثنی محمد بن الحسن قال حدثنی محمد بن یحیی", "Both invalid: Persian yeh in the text."),
    "cr-0070": ("tool_orthography_invalid", "A", "iii", "عن أبي محمد عبد الله بن محمد الغفاري", "B invalid: wrote «أبو محمد» where the text has the genitive «أبي محمد»."),
    "cr-0071": ("tool_orthography_invalid", "both (invalid)", "iii", "حدثنا موسى بن على، ح", "Both invalid: «علي» for the text's «على»."),
    "cr-0083": ("parallel_pair_misparse", "A", "i", "أبو علي الأشعري عن محمد بن عبد الجبار و محمد بن يحيى عن أحمد بن محمد جميعا عن ابن فضال", "B makes «أبو علي الأشعري» the head of the second route too (أبو علي > محمد بن يحيى > أحمد بن محمد)."),
    "cr-0084": ("speaker_omitted", "A (held)", "i", "عن أبي عبد الله عليه السلام قال: قال أمير المؤمنين عليه السلام: أنا الراعي", "A adds the speaker of the saying (imam_in_text), B omits him. Held: back reference without previous report."),
    "cr-0100": ("shared_tail_missed", "A", "i", "أن أبا النضر، حدثه عن سليمان بن يسار، عن عائشة", "B's first route stops at «عمرو بن الحارث»; A applies the tail to both."),
    "cr-0137": ("doubt_alternative", "A", "i", "عن مجاهد أو عمن حدثه عن مجاهد - شك في ذلك أبو غانم -", "A gives both readings as two routes, B only the first. Both flagged needs_ruling on the title «الإمام», which the prompt settles."),
    "cr-0141": ("tool_orthography_invalid", "neither (invalid)", "iii", "ح وحدثنا أبو بكر بن أبي شيبة، حدثنا هشيم، عن مغيرة", "A wrote «هشيم بن بشير» (a name completed beyond the text); B wrote «أبو معشر» for the text's «أبي معشر»."),
    "cr-0147": ("variant_remark_as_link", "A", "i", "وفي حديث الليث وصالح أن الصعب بن جثامة أخبره", "B adds «الصعب بن جثامة» to every route, though the remark covers two versions only; A keeps «بهذا الإسناد»."),
    "cr-0151": ("surface_scope", "both", "iii", "7 - وبهذا الإسناد قال: قال رسول الله", "A «وبهذا الإسناد», B «بهذا الإسناد»: one back reference, differs by an attached «و». Previous report has no names."),
    "cr-0163": ("surface_scope", "both", "iii", "أبو الحسين محمد بن علي الشجاعي الكاتب", "A keeps the final «الكاتب», B drops it."),
    "cr-0164": ("surface_scope", "both (held)", "iii", "و بهذا الإسناد عن الحارث بن المغيرة", "Attached «و» again; held for back reference without previous report."),
    "cr-0166": ("surface_scope", "both", "iii", "أبو عبد الله محمد بن عبد الله بن محمد بن الحجاج العدل", "«العدل» kept or not."),
    "cr-0167": ("surface_scope", "both", "iii", "أخبرنا أبو الحسن علي بن محمد الكاتب", "«الكاتب» kept or not."),
    "cr-0180": ("surface_scope", "A", "iii", "عن الزهري، بهذا الحديث . وروى مالك، هذا الحديث", "B writes «بهذا الحديث» (the matn) as a back_reference link; A leaves it out."),
    "cr-0205": ("comment_isnad_boundary", "B per rule 4", "i", "وقد روى شيبان عن يحيى بن أبي كثير مثل هذا", "B adds a route «شيبان > يحيى بن أبي كثير» from the compiler's remark (rule 4); A omits it. Judged consistent with cr-0280."),
    "cr-0208": ("parallel_pair_misparse", "B", "i", "علي بن ابراهيم عن أبيه ومحمد بن اسماعيل عن الفضل ابن شاذان جميعا عن حماد بن عيسى", "A crosses the two routes (علي بن ابراهيم > محمد بن اسماعيل …) and drops حماد from the first; B writes two clean routes."),
    "cr-0211": ("parallel_pair_misparse", "B", "i", "علي بن ابراهيم عن أبيه ومحمد بن اسماعيل عن الفضل ابن شاذان جميعا عن حماد بن عيسى", "Same text as cr-0208."),
    "cr-0220": ("embedded_narrative_as_route", "A", "i", "وقد أخبرني أبوعلي أحمد بن إسحاق عن أبي الحسن عليه السلام قال: سألته", "B adds a route «…الحميري > أبوعلي > ابا محمد» from a story told inside the report."),
    "cr-0233": ("tool_orthography_invalid", "both (invalid)", "iii", "قال: قال على بن أبي طالبعليه السلام", "Both invalid: «علي» for «على», and the text glues the honorific to the name."),
    "cr-0253": ("shared_tail_missed", "B", "i", "حدثنا محمد بن كثير، ح وحدثنا مسلم بن إبراهيم، حدثنا همام، عن قتادة", "A leaves the first route as the lone «محمد بن كثير»; B gives both the tail."),
}
