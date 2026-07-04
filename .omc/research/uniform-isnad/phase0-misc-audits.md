# Phase 0 misc audits (T-0.2 / T-0.3 / T-0.4)

Generated: 2026-06-11T11:46:10.244243Z

## T-0.2 — Lone ح false-positive risk

Found 10 sample rows where a lone ح appears in text_ar but is NOT 
preceded by transmission-verb context (the taḥwīl detector correctly skipped them). 
Each row's lone-ح count, source, hadith_no, and a 200-char snippet:

| Source | hadith_no | lone_ح count | first 200 chars |
|---|---|---:|---|
| Sahih Bukhari | 89 | 1 | `حدثنا أبو اليمان، أخبرنا شعيب، عن الزهري، ح قال أبو عبد الله وقال ابن وهب أخبرنا يونس، عن ابن شهاب، عن عبيد الله بن عبد الله بن أبي ثور، عن عبد الله بن عباس، عن عمر، قال كنت أنا وجار، لي من الأنصار في` |
| Sahih Bukhari | 214 | 1 | `حدثنا محمد بن يوسف، قال حدثنا سفيان، عن عمرو بن عامر، قال سمعت أنسا، ح قال وحدثنا مسدد، قال حدثنا يحيى، عن سفيان، قال حدثني عمرو بن عامر، عن أنس، قال كان النبي صلى الله عليه وسلم يتوضأ عند كل صلاة‏.‏ ` |
| Sahih Bukhari | 240 | 1 | `حدثنا عبدان، قال أخبرني أبي، عن شعبة، عن أبي إسحاق، عن عمرو بن ميمون، عن عبد الله، قال بينا رسول الله صلى الله عليه وسلم ساجد ح قال وحدثني أحمد بن عثمان قال حدثنا شريح بن مسلمة قال حدثنا إبراهيم بن يو` |
| Sahih Bukhari | 335 | 1 | `حدثنا محمد بن سنان، قال حدثنا هشيم، ح قال وحدثني سعيد بن النضر، قال أخبرنا هشيم، قال أخبرنا سيار، قال حدثنا يزيد  هو ابن صهيب الفقير  قال أخبرنا جابر بن عبد الله، أن النبي صلى الله عليه وسلم قال ‏"‏ أ` |
| Sahih Bukhari | 1479 | 1 | `حدثنا أبو اليمان، أخبرنا شعيب، عن الزهري، ح وقال الليث حدثني عبد الرحمن بن خالد، عن ابن شهاب، عن عبيد الله بن عبد الله بن عتبة بن مسعود، أن أبا هريرة  رضى الله عنه  قال قال أبو بكر  رضى الله عنه  والل` |
| Sahih Bukhari | 3218 | 1 | `حدثنا أبو نعيم، حدثنا عمر بن ذر، ح قال حدثني يحيى بن جعفر، حدثنا وكيع، عن عمر بن ذر، عن أبيه، عن سعيد بن جبير، عن ابن عباس  رضى الله عنهما  قال قال رسول الله صلى الله عليه وسلم لجبريل ‏"‏ ألا تزورنا أ` |
| Sahih Bukhari | 3544 | 1 | `حدثنا أبو نعيم، حدثنا سفيان، عن سعد، ح قال يعقوب بن إبراهيم حدثنا أبي، عن أبيه، قال حدثني عبد الرحمن بن هرمز الأعرج، عن أبي هريرة  رضى الله عنه  قال رسول الله صلى الله عليه وسلم ‏"‏ قريش والأنصار وجهي` |
| Sahih Bukhari | 4638 | 1 | `حدثنا إبراهيم بن موسى، أخبرنا هشام، أن ابن جريج، أخبرهم ح، وحدثني إسحاق، أخبرنا عبد الرزاق، أخبرنا ابن جريج، أخبرني عبد الكريم، أن مقسما، مولى عبد الله بن الحارث أخبره أن ابن عباس  رضى الله عنهما  أخب` |
| Sahih Bukhari | 5008 | 1 | `حدثنا عبد الله بن محمد، حدثنا عبد الرزاق، أخبرنا معمر، عن الزهري، ح وقال الليث حدثني عقيل، قال محمد أخبرني عروة، عن عائشة  رضى الله عنها‏.‏ أول ما بدئ به رسول الله صلى الله عليه وسلم الرؤيا الصادقة جا` |
| Sahih Bukhari | 5921 | 1 | `حدثنا أبو اليمان، أخبرنا شعيب، عن الزهري، أخبرني أنس بن مالك، ح وقال الليث حدثني يونس، عن ابن شهاب، قال أخبرني أنس بن مالك  رضى الله عنه  قال أرسل النبي صلى الله عليه وسلم إلى الأنصار، وجمعهم في قبة م` |

Interpretation: if these snippets show lone ح as part of an Arabic word, in the matn, 
or in narrative text (NOT as an isnad splitter), the detector is correctly conservative. 
If any sample shows what looks like a real taḥwīl splitter that the detector missed, 
we need to broaden the regex.

## T-0.3 — Convergence-narrator calibration (Sahih Muslim 1-ح subset)

Examined: **50** 1-ح rows from Sahih Muslim
Rows with detectable token overlap between pre-ح and post-ح segments: **15**
Rows with NO overlap (need no-stitch fallback per FR-1.1 step 3 last bullet): **35**
Median overlapping-token count in overlap rows: **1**

Decision feedback:
- If overlap rate > 95%: stitch is the dominant case; no-stitch fallback rare and OK.
- If overlap rate < 80%: stitch detection needs more robust token matching (perhaps trigram or LCS).
- Observed: **30.0%** overlap rate.

No-overlap sample rows (Hadith # + first 5 segs each side):

- Muslim #31: pre=['محمد بن أبي عمر المكي', 'سفيان']; post=['ح و', 'أبو بكر بن خلاد الباهلي - واللفظ له -', 'سمعت سفيان بن عيينة', 'مسعر', 'سمعت سعد بن إبراهيم يقول لا يحدث']
- Muslim #135: pre=['أحمد بن عبدة الضبي', 'عبد العزيز - ي', 'ي الدراوردي -', 'العلاء']; post=['ح و', 'أمية بن بسطام - واللفظ له -', 'يزيد بن زريع', 'روح', 'العلاء بن عبد الرحمن بن يعقوب']
- Muslim #137: pre=['و', 'أبو بكر بن أبي شيبة', 'وكيع']; post=['ح و', 'محمد بن المثنى', 'عبد الرحمن - ي', 'ي ابن مهدي -', 'ا جميعا']
- Muslim #140: pre=['و', 'أبو بكر بن أبي شيبة', 'أبو خالد الأحمر']; post=['ح و', 'ه زهير بن حرب', 'يزيد بن هارون كلاهما', 'أبي مالك', 'أبيه أنه سمع النبي يقول من وحد الله ثم ذكر بمثله']
- Muslim #142: pre=['و', 'إسحاق بن إبراهيم وعبد بن حميد', 'ا', 'عبد الرزاق', 'معمر']; post=['ح و', 'حسن الحلواني وعبد بن حميد', 'ا', 'يعقوب - وهو ابن إبراهيم بن سعد -', 'أبي']

## T-0.4 — Thaqalayn arabicText probe

Sampled: 1,449 rows across v2_books JSONs (cap 1,000)
With classical isnad grammar (حدثنا/أخبرنا/أنبأنا/عَن): **1,412** (97.4%)

Sample rows:

- **Al-Kāfi #2** diacritized=True norm-strips-diacritics=True
  - ` 1ـ أَخْبَرَنَا أَبُو جَعْفَرٍ مُحَمَّدُ بْنُ يَعْقُوبَ قَالَ حَدَّثَنِي عِدَّةٌ مِنْ أَصْحَابِنَا مِنْهُمْ مُحَمَّدُ بْنُ يَحْيَى الْعَطَّارُ عَنْ أَحْمَدَ بْنِ مُحَمَّدٍ عَنِ الْحَسَنِ بْنِ مَحْبُوب`

- **Al-Kāfi #3** diacritized=True norm-strips-diacritics=True
  - ` 2ـ عَلِيُّ بْنُ مُحَمَّدٍ عَنْ سَهْلِ بْنِ زِيَادٍ عَنْ عَمْرِو بْنِ عُثْمَانَ عَنْ مُفَضَّلِ بْنِ صَالِحٍ عَنْ سَعْدِ بْنِ طَرِيفٍ عَنِ الاصْبَغِ بْنِ نُبَاتَةَ عَنْ علي (عَلَيْهِ السَّلام) قَالَ هَ`

- **Al-Kāfi #4** diacritized=True norm-strips-diacritics=True
  - ` 3ـ أَحْمَدُ بْنُ إِدْرِيسَ عَنْ مُحَمَّدِ بْنِ عَبْدِ الْجَبَّارِ عَنْ بَعْضِ أَصْحَابِنَا رَفَعَهُ إِلَى أَبِي عَبْدِ الله (عَلَيْهِ السَّلام) قَالَ قُلْتُ لَهُ مَا الْعَقْلُ قَالَ مَا عُبِدَ بِهِ ا`

- **Al-Kāfi #5** diacritized=True norm-strips-diacritics=True
  - ` 4ـ مُحَمَّدُ بْنُ يَحْيَى عَنْ أَحْمَدَ بْنِ مُحَمَّدِ بْنِ عِيسَى عَنِ ابْنِ فَضَّالٍ عَنِ الْحَسَنِ بْنِ الْجَهْمِ قَالَ سَمِعْتُ الرِّضَا (عَلَيْهِ السَّلام) يَقُولُ صَدِيقُ كُلِّ امْرِئٍ عَقْلُهُ`

- **Al-Kāfi #6** diacritized=True norm-strips-diacritics=True
  - ` 5ـ وَعَنْهُ عَنْ أَحْمَدَ بْنِ مُحَمَّدٍ عَنِ ابْنِ فَضَّالٍ عَنِ الْحَسَنِ بْنِ الْجَهْمِ قَالَ قُلْتُ لابِي الْحَسَنِ (عَلَيْهِ السَّلام) إِنَّ عِنْدَنَا قَوْماً لَهُمْ مَحَبَّةٌ وَلَيْسَتْ لَهُمْ `

Decision feedback:
- If `pct_with_grammar` > 80% → `arabicText` is the right priority-1 source for Imami extraction (FR-3.2).
- If `norm-strips-diacritics-correctly` is True across samples → existing `_norm` handles Thaqalayn diacritization; no separate normalisation pass needed.

