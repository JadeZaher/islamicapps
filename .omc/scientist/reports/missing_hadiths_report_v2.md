# Missing Hadith Numbers Analysis Report
Generated: 2026-03-23

## Executive Summary

The parsed_hadiths.json contains **791 entries** out of **1005 expected** hadiths (Musnad al-Rabi ibn Habib). This analysis identified **214 missing hadith numbers** and cross-referenced them against raw OCR text from 266 PDF pages. Of the missing hadiths:

- **62 are parseable** - The OCR contains the hadith text with a clear marker; the parser failed to extract them
- **90 are possibly parseable** - The Arabic numeral appears in OCR but context is ambiguous (chapter headers, etc.)
- **62 are absent** - The Arabic numeral does not appear as a hadith entry in the OCR at all

Part 1 (hadiths 1-391) accounts for the majority of missing content (137 of 214 = 64%).

## Data Overview

| Field | Value |
|-------|-------|
| Expected hadiths | 1-1005 (1005 total) |
| Parsed hadiths | 791 |
| Missing hadiths | 214 |
| OCR pages | 266 PDF pages |
| OCR file | raw_ocr_pages.json (513 KB) |

## Part-by-Part Summary

| Part | Range | Missing | Parseable | Possibly Parseable | Absent |
|------|-------|---------|-----------|-------------------|--------|
| Part 1 (1-391) | 1-391 | 137 | 42 | 70 | 25 |
| Part 2 (392-742) | 392-742 | 68 | 18 | 18 | 32 |
| Part 3 (743-882) | 743-882 | 3 | 0 | 1 | 2 |
| Part 4 (883-1005) | 883-1005 | 6 | 2 | 1 | 3 |
| **TOTAL** | 1-1005 | **214** | **62** | **90** | **62** |

## Complete List of Missing Hadith Numbers by Part

### Legend
- **parseable**: OCR has clear hadith marker (N _ or _ N or )N( + text) - parser missed it
- **possibly parseable**: Arabic numeral present but context ambiguous - needs manual review
- **absent**: Arabic numeral not found as hadith entry in OCR - page may be image-only or OCR failed

### Part 1 (1-391)

| Hadith No. | Arabic Numeral | Assessment | OCR Location (pdf_page, book_page) |
|-----------|---------------|------------|-----------------------------------|
| 14 | ١٤ | parseable | pdf:14 bk:9 | pdf:45 bk:40 |
| 16 | ١٦ | absent | not found |
| 17 | ١٧ | possibly parseable | pdf:121 bk:116 | pdf:174 bk:169 |
| 19 | ١٩ | parseable | pdf:16 bk:11 | pdf:123 bk:118 |
| 21 | ٢١ | parseable | pdf:16 bk:11 | pdf:34 bk:29 |
| 22 | ٢٢ | possibly parseable | pdf:224 bk:219 |
| 23 | ٢٣ | possibly parseable | pdf:16 bk:11 | pdf:114 bk:109 |
| 25 | ٢٥ | parseable | pdf:254 bk:249 |
| 26 | ٢٦ | possibly parseable | pdf:265 bk:260 |
| 27 | ٢٧ | possibly parseable | pdf:17 bk:12 | pdf:31 bk:26 |
| 28 | ٢٨ | possibly parseable | pdf:32 bk:27 |
| 29 | ٢٩ | parseable | pdf:18 bk:13 | pdf:33 bk:28 |
| 30 | ٣٠ | parseable | pdf:18 bk:13 | pdf:82 bk:77 |
| 31 | ٣١ | possibly parseable | pdf:17 bk:12 | pdf:23 bk:18 |
| 32 | ٣٢ | parseable | pdf:19 bk:14 | pdf:86 bk:81 |
| 41 | ٤١ | possibly parseable | pdf:45 bk:40 |
| 42 | ٤٢ | possibly parseable | pdf:46 bk:41 | pdf:120 bk:115 |
| 44 | ٤٤ | parseable | pdf:22 bk:17 | pdf:48 bk:43 |
| 45 | ٤٥ | possibly parseable | pdf:49 bk:44 |
| 46 | ٤٦ | parseable | pdf:50 bk:45 | pdf:126 bk:121 |
| 47 | ٤٧ | possibly parseable | pdf:51 bk:46 |
| 48 | ٤٨ | parseable | pdf:52 bk:47 | pdf:130 bk:125 |
| 49 | ٤٩ | parseable | pdf:53 bk:48 | pdf:133 bk:128 |
| 50 | ٥٠ | possibly parseable | pdf:136 bk:131 |
| 51 | ٥١ | parseable | pdf:24 bk:19 | pdf:138 bk:133 |
| 52 | ٥٢ | parseable | pdf:24 bk:19 | pdf:156 bk:151 |
| 53 | ٥٣ | parseable | pdf:24 bk:19 |
| 54 | ٥٤ | parseable | pdf:24 bk:19 | pdf:58 bk:53 |
| 55 | ٥٥ | parseable | pdf:149 bk:144 |
| 56 | ٥٦ | parseable | pdf:25 bk:20 | pdf:151 bk:146 |
| 57 | ٥٧ | possibly parseable | pdf:161 bk:156 |
| 60 | ٦٠ | possibly parseable | pdf:26 bk:21 | pdf:161 bk:156 |
| 62 | ٦٢ | possibly parseable | pdf:26 bk:21 |
| 81 | ٨١ | absent | not found |
| 82 | ٨٢ | absent | not found |
| 83 | ٨٣ | possibly parseable | pdf:32 bk:27 |
| 84 | ٨٤ | parseable | pdf:32 bk:27 |
| 85 | ٨٥ | possibly parseable | pdf:89 bk:84 |
| 86 | ٨٦ | parseable | pdf:33 bk:28 | pdf:90 bk:85 |
| 87 | ٨٧ | parseable | pdf:33 bk:28 |
| 88 | ٨٨ | parseable | pdf:33 bk:28 | pdf:192 bk:187 |
| 89 | ٨٩ | parseable | pdf:33 bk:28 | pdf:93 bk:88 |
| 90 | ٩٠ | possibly parseable | pdf:34 bk:29 |
| 91 | ٩١ | possibly parseable | pdf:274 bk:269 |
| 92 | ٩٢ | parseable | pdf:34 bk:29 | pdf:96 bk:91 |
| 93 | ٩٣ | possibly parseable | pdf:34 bk:29 | pdf:193 bk:188 |
| 94 | ٩٤ | parseable | pdf:98 bk:93 | pdf:264 bk:259 |
| 95 | ٩٥ | absent | not found |
| 96 | ٩٦ | possibly parseable | pdf:35 bk:30 | pdf:100 bk:95 |
| 97 | ٩٧ | possibly parseable | pdf:101 bk:96 |
| 98 | ٩٨ | parseable | pdf:35 bk:30 | pdf:102 bk:97 |
| 99 | ٩٩ | absent | not found |
| 100 | ١٠٠ | possibly parseable | pdf:35 bk:30 |
| 101 | ١٠١ | absent | not found |
| 102 | ١٠٢ | parseable | pdf:36 bk:31 |
| 103 | ١٠٣ | parseable | pdf:36 bk:31 |
| 104 | ١٠٤ | possibly parseable | pdf:36 bk:31 |
| 105 | ١٠٥ | absent | not found |
| 107 | ١٠٧ | possibly parseable | pdf:37 bk:32 |
| 108 | ١٠٨ | possibly parseable | pdf:37 bk:32 |
| 109 | ١٠٩ | absent | not found |
| 110 | ١١٠ | possibly parseable | pdf:37 bk:32 |
| 111 | ١١١ | absent | not found |
| 114 | ١١٤ | possibly parseable | pdf:38 bk:33 | pdf:118 bk:113 |
| 115 | ١١٥ | absent | not found |
| 124 | ١٢٤ | possibly parseable | pdf:40 bk:35 | pdf:128 bk:123 |
| 125 | ١٢٥ | parseable | pdf:40 bk:35 | pdf:129 bk:124 |
| 126 | ١٢٦ | possibly parseable | pdf:130 bk:125 |
| 127 | ١٢٧ | possibly parseable | pdf:131 bk:126 |
| 128 | ١٢٨ | possibly parseable | pdf:40 bk:35 | pdf:132 bk:127 |
| 149 | ١٤٩ | possibly parseable | pdf:153 bk:148 |
| 200 | ٢٠٠ | absent | not found |
| 206 | ٢٠٦ | absent | not found |
| 207 | ٢٠٧ | possibly parseable | pdf:211 bk:206 |
| 208 | ٢٠٨ | parseable | pdf:60 bk:55 | pdf:212 bk:207 |
| 210 | ٢١٠ | absent | not found |
| 211 | ٢١١ | possibly parseable | pdf:61 bk:56 |
| 212 | ٢١٢ | possibly parseable | pdf:61 bk:56 | pdf:216 bk:211 |
| 213 | ٢١٣ | possibly parseable | pdf:62 bk:57 | pdf:217 bk:212 |
| 214 | ٢١٤ | possibly parseable | pdf:218 bk:213 |
| 215 | ٢١٥ | parseable | pdf:62 bk:57 |
| 216 | ٢١٦ | possibly parseable | pdf:62 bk:57 | pdf:220 bk:215 |
| 217 | ٢١٧ | parseable | pdf:62 bk:57 | pdf:221 bk:216 |
| 218 | ٢١٨ | possibly parseable | pdf:62 bk:57 | pdf:222 bk:217 |
| 219 | ٢١٩ | possibly parseable | pdf:63 bk:58 | pdf:223 bk:218 |
| 220 | ٢٢٠ | parseable | pdf:63 bk:58 |
| 221 | ٢٢١ | possibly parseable | pdf:16 bk:11 | pdf:225 bk:220 |
| 222 | ٢٢٢ | parseable | pdf:64 bk:59 | pdf:226 bk:221 |
| 223 | ٢٢٣ | possibly parseable | pdf:64 bk:59 | pdf:227 bk:222 |
| 224 | ٢٢٤ | possibly parseable | pdf:64 bk:59 | pdf:228 bk:223 |
| 225 | ٢٢٥ | possibly parseable | pdf:64 bk:59 | pdf:229 bk:224 |
| 226 | ٢٢٦ | possibly parseable | pdf:65 bk:60 | pdf:230 bk:225 |
| 227 | ٢٢٧ | possibly parseable | pdf:65 bk:60 | pdf:231 bk:226 |
| 228 | ٢٢٨ | possibly parseable | pdf:65 bk:60 | pdf:232 bk:227 |
| 232 | ٢٣٢ | possibly parseable | pdf:66 bk:61 | pdf:236 bk:231 |
| 234 | ٢٣٤ | parseable | pdf:66 bk:61 | pdf:238 bk:233 |
| 237 | ٢٣٧ | possibly parseable | pdf:67 bk:62 | pdf:241 bk:236 |
| 238 | ٢٣٨ | possibly parseable | pdf:242 bk:237 |
| 239 | ٢٣٩ | possibly parseable | pdf:243 bk:238 |
| 242 | ٢٤٢ | possibly parseable | pdf:68 bk:63 | pdf:246 bk:241 |
| 243 | ٢٤٣ | possibly parseable | pdf:247 bk:242 |
| 244 | ٢٤٤ | absent | not found |
| 245 | ٢٤٥ | absent | not found |
| 248 | ٢٤٨ | possibly parseable | pdf:70 bk:65 | pdf:252 bk:247 |
| 249 | ٢٤٩ | possibly parseable | pdf:253 bk:248 |
| 250 | ٢٥٠ | absent | not found |
| 255 | ٢٥٥ | possibly parseable | pdf:259 bk:254 |
| 268 | ٢٦٨ | possibly parseable | pdf:272 bk:267 |
| 269 | ٢٦٩ | possibly parseable | pdf:273 bk:268 |
| 282 | ٢٨٢ | absent | not found |
| 283 | ٢٨٣ | possibly parseable | pdf:79 bk:74 |
| 284 | ٢٨٤ | parseable | pdf:79 bk:74 |
| 286 | ٢٨٦ | parseable | pdf:80 bk:75 |
| 287 | ٢٨٧ | absent | not found |
| 288 | ٢٨٨ | possibly parseable | pdf:80 bk:75 |
| 290 | ٢٩٠ | possibly parseable | pdf:81 bk:76 |
| 321 | ٣٢١ | parseable | pdf:86 bk:81 |
| 322 | ٣٢٢ | possibly parseable | pdf:86 bk:81 |
| 326 | ٣٢٦ | parseable | pdf:87 bk:82 |
| 328 | ٣٢٨ | possibly parseable | pdf:88 bk:83 |
| 329 | ٣٢٩ | parseable | pdf:88 bk:83 |
| 332 | ٣٣٢ | absent | not found |
| 333 | ٣٣٣ | possibly parseable | pdf:89 bk:84 |
| 334 | ٣٣٤ | possibly parseable | pdf:89 bk:84 |
| 337 | ٣٣٧ | possibly parseable | pdf:90 bk:85 |
| 343 | ٣٤٣ | absent | not found |
| 345 | ٣٤٥ | absent | not found |
| 348 | ٣٤٨ | parseable | pdf:92 bk:87 |
| 363 | ٣٦٣ | parseable | pdf:96 bk:91 |
| 366 | ٣٦٦ | possibly parseable | pdf:97 bk:92 |
| 370 | ٣٧٠ | absent | not found |
| 374 | ٣٧٤ | absent | not found |
| 375 | ٣٧٥ | absent | not found |
| 377 | ٣٧٧ | possibly parseable | pdf:99 bk:94 |
| 379 | ٣٧٩ | parseable | pdf:99 bk:94 |
| 381 | ٣٨١ | absent | not found |
| 383 | ٣٨٣ | possibly parseable | pdf:100 bk:95 |

### Part 2 (392-742)

| Hadith No. | Arabic Numeral | Assessment | OCR Location (pdf_page, book_page) |
|-----------|---------------|------------|-----------------------------------|
| 392 | ٣٩٢ | absent | not found |
| 393 | ٣٩٣ | absent | not found |
| 394 | ٣٩٤ | absent | not found |
| 400 | ٤٠٠ | absent | not found |
| 401 | ٤٠١ | possibly parseable | pdf:106 bk:101 |
| 404 | ٤٠٤ | possibly parseable | pdf:107 bk:102 |
| 405 | ٤٠٥ | possibly parseable | pdf:107 bk:102 |
| 409 | ٤٠٩ | absent | not found |
| 411 | ٤١١ | absent | not found |
| 432 | ٤٣٢ | absent | not found |
| 444 | ٤٤٤ | parseable | pdf:120 bk:115 |
| 461 | ٤٦١ | absent | not found |
| 462 | ٤٦٢ | parseable | pdf:124 bk:119 |
| 466 | ٤٦٦ | absent | not found |
| 478 | ٤٧٨ | parseable | pdf:130 bk:125 |
| 481 | ٤٨١ | absent | not found |
| 504 | ٥٠٤ | absent | not found |
| 505 | ٥٠٥ | parseable | pdf:136 bk:131 |
| 506 | ٥٠٦ | absent | not found |
| 509 | ٥٠٩ | parseable | pdf:137 bk:132 |
| 510 | ٥١٠ | absent | not found |
| 519 | ٥١٩ | parseable | pdf:140 bk:135 |
| 520 | ٥٢٠ | parseable | pdf:140 bk:135 |
| 521 | ٥٢١ | possibly parseable | pdf:140 bk:135 |
| 522 | ٥٢٢ | parseable | pdf:140 bk:135 |
| 523 | ٥٢٣ | absent | not found |
| 539 | ٥٣٩ | absent | not found |
| 542 | ٥٤٢ | absent | not found |
| 549 | ٥٤٩ | absent | not found |
| 550 | ٥٥٠ | absent | not found |
| 551 | ٥٥١ | absent | not found |
| 552 | ٥٥٢ | parseable | pdf:149 bk:144 |
| 576 | ٥٧٦ | possibly parseable | pdf:154 bk:149 |
| 577 | ٥٧٧ | parseable | pdf:154 bk:149 |
| 606 | ٦٠٦ | absent | not found |
| 611 | ٦١١ | parseable | pdf:162 bk:157 |
| 615 | ٦١٥ | absent | not found |
| 636 | ٦٣٦ | possibly parseable | pdf:168 bk:163 |
| 638 | ٦٣٨ | absent | not found |
| 640 | ٦٤٠ | absent | not found |
| 641 | ٦٤١ | possibly parseable | pdf:169 bk:164 |
| 642 | ٦٤٢ | possibly parseable | pdf:170 bk:165 |
| 644 | ٦٤٤ | absent | not found |
| 646 | ٦٤٦ | absent | not found |
| 668 | ٦٦٨ | possibly parseable | pdf:176 bk:171 |
| 669 | ٦٦٩ | absent | not found |
| 670 | ٦٧٠ | possibly parseable | pdf:176 bk:171 |
| 682 | ٦٨٢ | absent | not found |
| 683 | ٦٨٣ | parseable | pdf:180 bk:175 |
| 684 | ٦٨٤ | possibly parseable | pdf:180 bk:175 |
| 685 | ٦٨٥ | parseable | pdf:180 bk:175 |
| 686 | ٦٨٦ | possibly parseable | pdf:180 bk:175 |
| 687 | ٦٨٧ | parseable | pdf:180 bk:175 |
| 692 | ٦٩٢ | absent | not found |
| 702 | ٧٠٢ | parseable | pdf:183 bk:178 |
| 704 | ٧٠٤ | absent | not found |
| 705 | ٧٠٥ | parseable | pdf:184 bk:179 |
| 706 | ٧٠٦ | possibly parseable | pdf:184 bk:179 |
| 707 | ٧٠٧ | parseable | pdf:184 bk:179 |
| 710 | ٧١٠ | absent | not found |
| 713 | ٧١٣ | possibly parseable | pdf:186 bk:181 |
| 715 | ٧١٥ | absent | not found |
| 718 | ٧١٨ | possibly parseable | pdf:187 bk:182 |
| 722 | ٧٢٢ | absent | not found |
| 724 | ٧٢٤ | possibly parseable | pdf:188 bk:183 |
| 726 | ٧٢٦ | possibly parseable | pdf:188 bk:183 |
| 727 | ٧٢٧ | parseable | pdf:188 bk:183 |
| 728 | ٧٢٨ | possibly parseable | pdf:188 bk:183 |

### Part 3 (743-882)

| Hadith No. | Arabic Numeral | Assessment | OCR Location (pdf_page, book_page) |
|-----------|---------------|------------|-----------------------------------|
| 783 | ٧٨٣ | absent | not found |
| 784 | ٧٨٤ | possibly parseable | pdf:202 bk:197 |
| 786 | ٧٨٦ | absent | not found |

### Part 4 (883-1005)

| Hadith No. | Arabic Numeral | Assessment | OCR Location (pdf_page, book_page) |
|-----------|---------------|------------|-----------------------------------|
| 894 | ٨٩٤ | parseable | pdf:252 bk:247 |
| 895 | ٨٩٥ | parseable | pdf:252 bk:247 |
| 919 | ٩١٩ | possibly parseable | pdf:258 bk:253 |
| 960 | ٩٦٠ | absent | not found |
| 962 | ٩٦٢ | absent | not found |
| 1000 | ١٠٠٠ | absent | not found |

## Parseable Hadiths - Full List (62 hadiths)

These 62 hadiths have clear OCR markers. An improved parser should recover them.

**Numbers:** 14, 19, 21, 25, 29, 30, 32, 44, 46, 48, 49, 51, 52, 53, 54, 55, 56, 84, 86, 87, 88, 89, 92, 94, 98, 102, 103, 125, 208, 215, 217, 220, 222, 234, 284, 286, 321, 326, 329, 348, 363, 379, 444, 462, 478, 505, 509, 519, 520, 522, 552, 577, 611, 683, 685, 687, 702, 705, 707, 727, 894, 895

### Sample OCR Contexts for Parseable Hadiths

| Hadith No. | Arabic | pdf_page | Pattern Type | OCR Context (truncated) |
|-----------|--------|----------|-------------|-------------------------|
| 14 | ١٤ | 14 | parseable_underscore | بغاث قال البغاث أرذلة الطير )ا( الربيع _[N] أبو عبيدة نال بلغنى أن عمر |
| 19 | ١٩ | 16 | parseable_paren | لنبى علنه تال أأطلبوا العلم ولو بالصين )[N]  ومن طريقه عن النبى عليه ا |
| 21 | ٢١ | 16 | ambiguous | لب فيه " علماً سهل الله له طريق الجنة «)[N]( أبو عبيدة عن جابر بن زيد  |
| 25 | ٢٥ | 254 | parseable_underscore | بر )٣( خ اسقاط أي )٤( خ جميل )٥و٦( خ من
[N] _ |
| 29 | ٢٩ | 18 | parseable_paren | ز وجل ومن لايعرف توحيد الله نلبس بمؤمن )[N] أبو  عبيدة عن جابر بن زيد  |
| 30 | ٣٠ | 18 | parseable_paren | كم الماء الدائم ثم يغتسل منه أو يتوضاء )[N]  أبو عبيدة قال عن رسول الل |
| 32 | ٣٢ | 19 | parseable_underscore | ب العلم لفير الله عز وجل وعلماء السوء _ [N] أبو عبيدة عن جابر بن زيد ع |
| 44 | ٤٤ | 22 | parseable_underscore |  فسحقا اباب )٧( فى الولاية   والامارة _ [N] أبو عبيدة عن جابر بن زيد ع |
| 46 | ٤٦ | 50 | ambiguous | : لى )٤( خ: فضرب )٥ نامر به أى   بالغسل
[N] |
| 48 | ٤٨ | 52 | ambiguous | لس كذا نى النهاية )٣( خ لها )٤( خ انخلف
[N] |
| 49 | ٤٩ | 53 | ambiguous | سخة القطب التصريح بعائشة  رضى الله عنها
[N] |
| 51 | ٥١ | 24 | parseable_paren |  بعسدي من النبسرة إلا الرؤيا الصالحة . )[N] أبو عبيدة عن جابر بن زيد ع |
| 52 | ٥٢ | 24 | parseable_text | لصالح جزء من ستة وأربعين جزءا من النبوة [N] أبو عبيدة عن أدركت )ا( جاب |
| 53 | ٥٣ | 24 | parseable_paren | ما سمعت هذا الحديث نما كنت أبالى بها ٠ )[N]  أبو عبيدة عن جسابر بن زيد |
| 54 | ٥٤ | 24 | ambiguous |  أنستى مسألة أو فسر رؤياً ( الحديث (٥) )[N]( أبو عبيدة من طريق ابن عمر |
| 55 | ٥٥ | 149 | parseable_underscore | راغتسلى واستثفري وصلىه أي احتش بالقطن . [N]_ ومن طريقه  أيضا عنه عليه  |
| 56 | ٥٦ | 25 | ambiguous | رسول الله يثظإتةه  أفلح )ا( إن صدق ( . )[N]( أبو عبيدة جابر زيد عن أنس |
| 84 | ٨٤ | 32 | parseable_underscore | ه السلام لأنها مساكن إخوانكم من الجن . _[N] آبو عبيدة عن جابر بن زيد ع |
| 86 | ٨٦ | 33 | parseable_paren |  نال »ا تستقبلوا القبلة ببول ولا غائطه )[N] أبو عبيدة عن جابر زيد عن أ |
| 87 | ٨٧ | 33 | parseable_text | ل وضوء »باب )١٥( في آداب الوضوء   وفرضه [N] أبو عبيدة عن جابر بن زيد ع |
| 88 | ٨٨ | 33 | parseable_text |    ثلاثا لأنه لايدري أين   باتت يده ( . [N] أبو عبيدة عن جابر بن زيد ع |
| 89 | ٨٩ | 33 | parseable_underscore | ى علنة نيل الثواب الجزيل فى ذكر الله . _[N] أبو عبيدة عن جابر بن زيد ع |
| 92 | ٩٢ | 34 | parseable_text | وء له ولا صوم إلا بالكف عن محارم الله - [N] آبو عبيدة عن جابر بن زيد ع |
| 94 | ٩٤ | 98 | ambiguous | لال عن أبى عبيدة  وعلى نسختنا مو جابر .
[N] |
| 98 | ٩٨ | 35 | parseable_text | ه   وأذنيه  . اباب )١٦( فى فضائل الوضوء [N] أبو عبيدة عن جابر بن زيد ع |

## Absent Hadiths - Full List (62 hadiths)

These 62 hadiths have no trace in the OCR data as hadith entries. They appear to be on image-only pages, pages with OCR failure, or pages missing from this PDF edition.

**Numbers:** 16, 81, 82, 95, 99, 101, 105, 109, 111, 115, 200, 206, 210, 244, 245, 250, 282, 287, 332, 343, 345, 370, 374, 375, 381, 392, 393, 394, 400, 409, 411, 432, 461, 466, 481, 504, 506, 510, 523, 539, 542, 549, 550, 551, 606, 615, 638, 640, 644, 646, 669, 682, 692, 704, 710, 715, 722, 783, 786, 960, 962, 1000

### Absent Hadiths by Part

**Part 1 (1-391)** (25 hadiths): 16(١٦), 81(٨١), 82(٨٢), 95(٩٥), 99(٩٩), 101(١٠١), 105(١٠٥), 109(١٠٩), 111(١١١), 115(١١٥), 200(٢٠٠), 206(٢٠٦), 210(٢١٠), 244(٢٤٤), 245(٢٤٥), 250(٢٥٠), 282(٢٨٢), 287(٢٨٧), 332(٣٣٢), 343(٣٤٣), 345(٣٤٥), 370(٣٧٠), 374(٣٧٤), 375(٣٧٥), 381(٣٨١)

**Part 2 (392-742)** (32 hadiths): 392(٣٩٢), 393(٣٩٣), 394(٣٩٤), 400(٤٠٠), 409(٤٠٩), 411(٤١١), 432(٤٣٢), 461(٤٦١), 466(٤٦٦), 481(٤٨١), 504(٥٠٤), 506(٥٠٦), 510(٥١٠), 523(٥٢٣), 539(٥٣٩), 542(٥٤٢), 549(٥٤٩), 550(٥٥٠), 551(٥٥١), 606(٦٠٦), 615(٦١٥), 638(٦٣٨), 640(٦٤٠), 644(٦٤٤), 646(٦٤٦), 669(٦٦٩), 682(٦٨٢), 692(٦٩٢), 704(٧٠٤), 710(٧١٠), 715(٧١٥), 722(٧٢٢)

**Part 3 (743-882)** (2 hadiths): 783(٧٨٣), 786(٧٨٦)

**Part 4 (883-1005)** (3 hadiths): 960(٩٦٠), 962(٩٦٢), 1000(١٠٠٠)

## Possibly Parseable Hadiths - Full List (90 hadiths)

These 90 hadiths need manual review. The Arabic numeral appears in the OCR but only in ambiguous contexts (chapter header numbers, page numbers, or mid-sentence fragments).

**Numbers:** 17, 22, 23, 26, 27, 28, 31, 41, 42, 45, 47, 50, 57, 60, 62, 83, 85, 90, 91, 93, 96, 97, 100, 104, 107, 108, 110, 114, 124, 126, 127, 128, 149, 207, 211, 212, 213, 214, 216, 218, 219, 221, 223, 224, 225, 226, 227, 228, 232, 237, 238, 239, 242, 243, 248, 249, 255, 268, 269, 283, 288, 290, 322, 328, 333, 334, 337, 366, 377, 383, 401, 404, 405, 521, 576, 636, 641, 642, 668, 670, 684, 686, 706, 713, 718, 724, 726, 728, 784, 919

## Recommendations for Parser Improvement

1. **Add paren-prefix pattern**: Detect  and  - OCR sometimes wraps numbers in closing parens
2. **Add text-follows pattern**: Detect Arabic numeral directly followed by  without any delimiter
3. **Handle ambiguous context**: For numbers in the 90 possibly-parseable group, use surrounding hadith numbers to infer gaps
4. **Image page detection**: The 62 absent hadiths likely correspond to PDF pages with no text layer; consider OCR re-run with higher resolution
5. **Gap analysis**: Runs of consecutive missing numbers (e.g., 392-394, 244-245) suggest entire page sections were lost

## Limitations

- Arabic OCR quality varies; some numerals may be misread (e.g., ٩/٧ confusion, ٦/١ confusion)
- Chapter Bab-numbers overlap with hadith numbers and were excluded from parseable classification
- The 90 possibly-parseable entries require human review to confirm actual hadith presence
- Image-embedded pages in the PDF produce no OCR text; these are counted as absent
- Hadith numbering in this edition may skip numbers intentionally (duplicate/variant numbering schemes)
