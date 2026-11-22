"""The 25 reports on which the two passes disagree once offsets are ignored (17 with both outputs valid, 8 with an invalid output). All read.

Entry: id -> (class, who_is_right, fix, quote, what_differs). who_is_right: A | B | both | neither | cannot_tell.
Fix: i prompt rule | ii context | iii deterministic post-processing | iv not fixable by a reader.
"""

D = {
    "cr-0029": ("relation_word", "A", "i+iii", "حدثنا محمد بن علي ما جيلويه رضي الله عنه، عن عمه محمد بن أبي القاسم", "B writes «عمه» as a link before «محمد بن أبي القاسم» (one man, two links); A gives the name alone (rule 1)."),
    "cr-0031": ("relation_word", "A", "i+iii", "عن أبيه على بن محمد، عن أبيه محمد بن على، عن أبيها لرضا على بن موسى", "B keeps every «أبيه» as its own link next to the named man (17 links for 11 persons); A drops the relation word (the source's typo «أبيها لرضا» gives A «لرضا على بن موسى»)."),
    "cr-0049": ("relation_word", "A", "i+iii", "عن علي بن جعفر عن أخيه أبي الحسن ( عليه السلام ) قال", "B «أخيه > أبي الحسن» (two links), A «أبي الحسن»."),
    "cr-0057": ("relation_word", "A", "i+iii", "قال سمعت عمي، يحيى - وما أدركت رجلا منا به شبيها", "B «عمي > يحيى», A «يحيى»."),
    "cr-0085": ("surface_scope", "both", "iii", "كلهم عن سفيان، قال عمرو حدثنا سفيان بن عيينة", "One man named twice; A takes the longer mention «سفيان بن عيينة», B the first «سفيان». Both right; they differ only in which mention is the surface."),
    "cr-0144": ("surface_scope", "both", "iii", "كلاهما عن المعتمر، قال ابن حبيب حدثنا معتمر بن سليمان", "A «معتمر بن سليمان» in both routes, B «المعتمر» in the second; same man mentioned twice."),
    "cr-0101": ("surface_scope", "both", "iii", "عن حبيب، مولى عروة عن بدية", "A «حبيب», B «حبيب مولى عروة» (a mawla phrase kept or not)."),
    "cr-0114": ("surface_scope", "both", "iii", "عن حبيب، مولى عروة عن بدية، - وكان الليث يقول ندبة -", "Same as cr-0101."),
    "cr-0160": ("surface_scope", "both", "iii", "وحدثني عيسى بن حماد المصري، أخبرنا الليث", "A «عيسى بن حماد», B «عيسى بن حماد المصري» (nisba kept or not); nine routes otherwise identical."),
    "cr-0177": ("surface_scope", "cannot_tell", "iii+i", "أنه سمع هانئا، مولى عثمان قال كان عثمان إذا وقف على قبر بكى", "A «هانئا», B «هانئا مولى عثمان»; both omit عثمان, the speaker of the saying (rule 2)."),
    "cr-0178": ("surface_scope", "both", "iii", "عن أبيه، عن أمير المؤمنين علي بن أبي طالب عليه السلام قال", "A keeps the title, B «علي بن أبي طالب»."),
    "cr-0069": ("imam_in_text", "A", "i", "وصفت لأبي عبد الله رجلا يتوالى أمير المؤمنين … فقال: إن مات هذا مات ميتة جاهلية", "A adds the Imam named after the chain (owner ruling); B stops at حمران بن أعين."),
    "cr-0195": ("imam_in_text", "A", "i", "عن منصور الصيقل، قال: كنت عند أبي عبد الله عليه السلام في فسطاطه بمنى", "A adds the Imam, B omits him; both drop the unnamed gap of «بإسناد يرفعه» (see irsal_gap)."),
    "cr-0146": ("source_in_matn", "A", "i", "مالك ⏎ ⏎ رأى سالم ابن عبد الله يخرج من أنفه الدم", "A adds «سالم ابن عبد الله» (rule 5 «رأيت X»), B keeps the field's single name; policy for Pure Canon (field only vs rule 5)."),
    "cr-0058": ("shared_tail", "B", "i+iii", "حدثنا محمد بن جعفر، ح وحدثنا عبيد الله بن معاذ، حدثنا أبي قالا، جميعا حدثنا شعبة", "B carries «شعبة» as shared tail of the first two routes and writes «عبيد الله بن معاذ > أبي > شعبة»; A drops شعبة from the first two and splits the third into two routes."),
    "cr-0157": ("shared_tail", "B", "i+iii", "عن أبيه عن ابن أبي عمير ومحمد بن إسماعيل عن الفضل بن شاذان عن صفوان بن يحيى وابن أبي عمير عن معاوية بن عمار", "B continues the first route to «معاوية بن عمار > الإمام»; A ends it at «ابن أبي عمير»."),
    "cr-0170": ("shared_tail", "A", "i+iii", "حدثنا محمد بن جعفر، ح وحدثنيه يحيى بن حبيب، حدثنا خالد - قالا حدثنا شعبة، بهذا الإسناد", "A adds the shared «شعبة» to the first two routes; B leaves them at «محمد بن جعفر»."),
    "cr-0059": ("route_explosion", "A", "iii", "حدثنا أبي، ومحمد بن الحسن … ومحمد بن موسى … قالوا: حدثنا سعد بن عبد الله، وعبد الله بن جعفر، ومحمد بن يحيى العطار، قالوا: حدثنا أحمد بن محمد بن عيسى، وإبراهيم بن هاشم", "3x3x2 = 18 routes: A writes all 18, B stops after 6. B is a correct prefix (truncation), A is right."),
    "cr-0075": ("route_explosion", "neither", "iii+i", "عن الحلبي و زرارة و محمد بن مسلم و حمران بن أعين عن أبي جعفر و أبي عبد الله ( عليه السلام ) قالا", "4x2 = 8 routes. A writes four routes with the two Imams in sequence «أبي جعفر > أبي عبد الله»; B writes the parallel Imams (right) but only five of the eight."),
    "cr-0032": ("nested_multi_isnad", "neither", "iv", "عن أيوب بن نوح؛ و إبراهيم بن هاشم جميعا عن صفوان بن يحيى؛ و ابن أبي عمير جميعا عن محمد بن حمران", "Second isnad with ';' and «جميعا» at two levels; A writes four fragments, B four different ones; neither gives the full structure and the correct nesting is not decidable from punctuation alone."),
    "cr-0065": ("nested_multi_isnad", "neither", "iv", "عن أبي؛ و محمد بن الحسن … عن سعد بن عبد الله؛ و عبد الله بن جعفر الحميري جميعا عن يعقوب بن يزيد؛ و الحسن بن ظريف؛ و أيوب بن نوح", "The first isnad (12 combinations) is mostly lost by both: A keeps a fragment «أيوب بن نوح > النضر > هشام», B only the second isnad."),
    "cr-0143": ("nested_multi_isnad", "neither", "iv", "عن أبي بصير مثله .حميد بن زياد عن ابن سماعة عن وهيب بن حفص", "Two reports run together («مثله» then a new isnad); A and B segment the first part differently and both lose parts."),
    "cr-0187": ("nested_multi_isnad", "neither", "iv", "حدثني إياس بن الحارث بن المعيقيب، وجده، من قبل أمه أبو ذباب عن جده", "Both read «إياس > جده > أبو ذباب > جده» as a sequence; the text has two parallel narrators (إياس, and his maternal grandfather أبو ذباب) from «جده». A and B differ only by the clitic «وجده» vs «جده» but both are wrong."),
    "cr-0219": ("nested_multi_isnad", "neither", "iv", "عن بكر بن صالح، وحدثنا أبي ومحمد بن موسى بن المتوكل … قالوا: حدثنا على بن إبراهيم بن هاشم، عن أبيه، عن بكر بن صالح", "Two isnads converge at «بكر بن صالح» (the tail «عبد الرحمن بن سالم > أبيبصير > الإمام» is shared); A ends the first isnad at بكر, B joins the tail to four of its routes and drops «الحسن بن ظريف» into a one-route fragment."),
    "cr-0137": ("title_or_epithet", "cannot_tell", "i", "الإمام عن أبي غانم الخراساني عن حاتم بن منصور", "A has the title «الإمام» as first link, B starts at «أبي غانم»; the work's convention for this opening is not stated in the prompt."),
}
