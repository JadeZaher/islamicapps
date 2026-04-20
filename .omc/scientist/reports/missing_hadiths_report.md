# Missing Hadith Numbers Analysis Report
Generated: 2026-03-23

## Executive Summary

The parsed_hadiths.json contains 791 entries out of 1005 expected. This analysis identified 214 missing hadith numbers and cross-referenced them against raw OCR text from 266 PDF pages. Of these: **66 are parseable** (clear OCR marker present, parser failed), **91 are possibly parseable** (numeral present but context ambiguous), and **57 are genuinely absent** from OCR.

## Data Overview

- Dataset: parsed_hadiths.json + raw_ocr_pages.json
- Expected range: 1-1005 (1005 total hadiths)
- Parsed hadiths: 791
- Missing hadiths: 214
- OCR pages: 266 PDF pages

## Part-by-Part Summary

| Part | Range | Missing | Parseable | Possibly Parseable | Absent |
|------|-------|---------|-----------|-------------------|--------|
| Part 1 | 1-391 | 137 | 45 | 70 | 22 |
| Part 2 | 392-742 | 68 | 19 | 19 | 30 |
| Part 3 | 743-882 | 3 | 0 | 1 | 2 |
| Part 4 | 883-1005 | 6 | 2 | 1 | 3 |
| Total | 1-1005 | 214 | 66 | 91 | 57 |

## Complete Missing Numbers by Part

### Part 1 (1-391)

| No. | Arabic | Assessment | OCR Location |
|-----|--------|------------|--------------|
| 14 | ١٤ | parseable | pdf:14(bk:9), pdf:45(bk:40) |
| 16 | ١٦ | possibly parseable | not found |
| 17 | ١٧ | possibly parseable | not found |
| 19 | ١٩ | possibly parseable | not found |
| 21 | ٢١ | parseable | pdf:34(bk:29), pdf:61(bk:56) |
| 22 | ٢٢ | possibly parseable | not found |
| 23 | ٢٣ | parseable | pdf:114(bk:109) |
| 25 | ٢٥ | parseable | pdf:254(bk:249) |
| 26 | ٢٦ | possibly parseable | not found |
| 27 | ٢٧ | possibly parseable | not found |
| 28 | ٢٨ | possibly parseable | not found |
| 29 | ٢٩ | parseable | pdf:18(bk:13) |
| 30 | ٣٠ | parseable | pdf:18(bk:13), pdf:82(bk:77) |
| 31 | ٣١ | parseable | pdf:17(bk:12), pdf:23(bk:18) |
| 32 | ٣٢ | parseable | pdf:19(bk:14), pdf:86(bk:81) |
| 41 | ٤١ | possibly parseable | not found |
| 42 | ٤٢ | parseable | pdf:120(bk:115) |
| 44 | ٤٤ | parseable | pdf:22(bk:17) |
| 45 | ٤٥ | possibly parseable | not found |
| 46 | ٤٦ | parseable | pdf:126(bk:121) |
| 47 | ٤٧ | parseable | pdf:127(bk:122) |
| 48 | ٤٨ | parseable | pdf:130(bk:125) |
| 49 | ٤٩ | parseable | pdf:133(bk:128) |
| 50 | ٥٠ | possibly parseable | pdf:136(bk:131) |
| 51 | ٥١ | parseable | pdf:24(bk:19), pdf:138(bk:133) |
| 52 | ٥٢ | parseable | pdf:24(bk:19) |
| 53 | ٥٣ | parseable | pdf:24(bk:19) |
| 54 | ٥٤ | parseable | pdf:147(bk:142), pdf:149(bk:144) |
| 55 | ٥٥ | parseable | pdf:149(bk:144) |
| 56 | ٥٦ | parseable | pdf:151(bk:146) |
| 57 | ٥٧ | possibly parseable | not found |
| 60 | ٦٠ | possibly parseable | pdf:161(bk:156) |
| 62 | ٦٢ | possibly parseable | not found |
| 81 | ٨١ | possibly parseable | not found |
| 82 | ٨٢ | possibly parseable | not found |
| 83 | ٨٣ | possibly parseable | pdf:32(bk:27) |
| 84 | ٨٤ | parseable | pdf:32(bk:27) |
| 85 | ٨٥ | possibly parseable | not found |
| 86 | ٨٦ | parseable | pdf:33(bk:28) |
| 87 | ٨٧ | parseable | pdf:33(bk:28) |
| 88 | ٨٨ | parseable | pdf:33(bk:28) |
| 89 | ٨٩ | parseable | pdf:33(bk:28) |
| 90 | ٩٠ | possibly parseable | not found |
| 91 | ٩١ | possibly parseable | pdf:274(bk:269) |
| 92 | ٩٢ | parseable | pdf:34(bk:29) |
| 93 | ٩٣ | possibly parseable | pdf:193(bk:188) |
| 94 | ٩٤ | parseable | pdf:264(bk:259) |
| 95 | ٩٥ | absent | not found |
| 96 | ٩٦ | possibly parseable | not found |
| 97 | ٩٧ | possibly parseable | not found |
| 98 | ٩٨ | parseable | pdf:35(bk:30), pdf:135(bk:130) |
| 99 | ٩٩ | absent | not found |
| 100 | ١٠٠ | possibly parseable | not found |
| 101 | ١٠١ | absent | not found |
| 102 | ١٠٢ | parseable | pdf:36(bk:31) |
| 103 | ١٠٣ | parseable | pdf:36(bk:31) |
| 104 | ١٠٤ | possibly parseable | not found |
| 105 | ١٠٥ | absent | not found |
| 107 | ١٠٧ | possibly parseable | not found |
| 108 | ١٠٨ | possibly parseable | not found |
| 109 | ١٠٩ | absent | not found |
| 110 | ١١٠ | possibly parseable | not found |
| 111 | ١١١ | absent | not found |
| 114 | ١١٤ | possibly parseable | not found |
| 115 | ١١٥ | absent | not found |
| 124 | ١٢٤ | possibly parseable | not found |
| 125 | ١٢٥ | parseable | pdf:40(bk:35) |
| 126 | ١٢٦ | possibly parseable | not found |
| 127 | ١٢٧ | possibly parseable | not found |
| 128 | ١٢٨ | possibly parseable | not found |
| 149 | ١٤٩ | possibly parseable | not found |
| 200 | ٢٠٠ | absent | not found |
| 206 | ٢٠٦ | absent | not found |
| 207 | ٢٠٧ | possibly parseable | not found |
| 208 | ٢٠٨ | parseable | pdf:60(bk:55) |
| 210 | ٢١٠ | absent | not found |
| 211 | ٢١١ | possibly parseable | not found |
| 212 | ٢١٢ | possibly parseable | not found |
| 213 | ٢١٣ | possibly parseable | not found |
| 214 | ٢١٤ | possibly parseable | not found |
| 215 | ٢١٥ | parseable | pdf:62(bk:57) |
| 216 | ٢١٦ | possibly parseable | not found |
| 217 | ٢١٧ | parseable | pdf:62(bk:57) |
| 218 | ٢١٨ | possibly parseable | not found |
| 219 | ٢١٩ | possibly parseable | not found |
| 220 | ٢٢٠ | parseable | pdf:63(bk:58) |
| 221 | ٢٢١ | possibly parseable | pdf:16(bk:11) |
| 222 | ٢٢٢ | parseable | pdf:64(bk:59) |
| 223 | ٢٢٣ | possibly parseable | not found |
| 224 | ٢٢٤ | possibly parseable | not found |
| 225 | ٢٢٥ | possibly parseable | not found |
| 226 | ٢٢٦ | possibly parseable | pdf:65(bk:60) |
| 227 | ٢٢٧ | possibly parseable | not found |
| 228 | ٢٢٨ | possibly parseable | pdf:65(bk:60) |
| 232 | ٢٣٢ | possibly parseable | not found |
| 234 | ٢٣٤ | parseable | pdf:66(bk:61) |
| 237 | ٢٣٧ | possibly parseable | pdf:67(bk:62) |
| 238 | ٢٣٨ | possibly parseable | not found |
| 239 | ٢٣٩ | possibly parseable | not found |
| 242 | ٢٤٢ | possibly parseable | not found |
| 243 | ٢٤٣ | possibly parseable | not found |
| 244 | ٢٤٤ | absent | not found |
| 245 | ٢٤٥ | absent | not found |
| 248 | ٢٤٨ | possibly parseable | not found |
| 249 | ٢٤٩ | possibly parseable | not found |
| 250 | ٢٥٠ | absent | not found |
| 255 | ٢٥٥ | possibly parseable | not found |
| 268 | ٢٦٨ | possibly parseable | not found |
| 269 | ٢٦٩ | possibly parseable | not found |
| 282 | ٢٨٢ | absent | not found |
| 283 | ٢٨٣ | possibly parseable | not found |
| 284 | ٢٨٤ | parseable | pdf:79(bk:74) |
| 286 | ٢٨٦ | parseable | pdf:80(bk:75) |
| 287 | ٢٨٧ | absent | not found |
| 288 | ٢٨٨ | possibly parseable | not found |
| 290 | ٢٩٠ | possibly parseable | not found |
| 321 | ٣٢١ | parseable | pdf:86(bk:81) |
| 322 | ٣٢٢ | possibly parseable | not found |
| 326 | ٣٢٦ | parseable | pdf:87(bk:82) |
| 328 | ٣٢٨ | possibly parseable | pdf:88(bk:83) |
| 329 | ٣٢٩ | parseable | pdf:88(bk:83) |
| 332 | ٣٣٢ | absent | not found |
| 333 | ٣٣٣ | possibly parseable | pdf:89(bk:84) |
| 334 | ٣٣٤ | possibly parseable | not found |
| 337 | ٣٣٧ | possibly parseable | pdf:90(bk:85) |
| 343 | ٣٤٣ | absent | not found |
| 345 | ٣٤٥ | absent | not found |
| 348 | ٣٤٨ | parseable | pdf:92(bk:87) |
| 363 | ٣٦٣ | parseable | pdf:96(bk:91) |
| 366 | ٣٦٦ | possibly parseable | not found |
| 370 | ٣٧٠ | absent | not found |
| 374 | ٣٧٤ | absent | not found |
| 375 | ٣٧٥ | absent | not found |
| 377 | ٣٧٧ | possibly parseable | pdf:99(bk:94) |
| 379 | ٣٧٩ | parseable | pdf:99(bk:94) |
| 381 | ٣٨١ | absent | not found |
| 383 | ٣٨٣ | possibly parseable | pdf:100(bk:95) |

### Part 2 (392-742)

| No. | Arabic | Assessment | OCR Location |
|-----|--------|------------|--------------|
| 392 | ٣٩٢ | absent | not found |
| 393 | ٣٩٣ | absent | not found |
| 394 | ٣٩٤ | absent | not found |
| 400 | ٤٠٠ | absent | not found |
| 401 | ٤٠١ | possibly parseable | not found |
| 404 | ٤٠٤ | possibly parseable | not found |
| 405 | ٤٠٥ | possibly parseable | not found |
| 409 | ٤٠٩ | absent | not found |
| 411 | ٤١١ | absent | not found |
| 432 | ٤٣٢ | absent | not found |
| 444 | ٤٤٤ | parseable | pdf:120(bk:115) |
| 461 | ٤٦١ | parseable | pdf:124(bk:119) |
| 462 | ٤٦٢ | parseable | pdf:124(bk:119) |
| 466 | ٤٦٦ | absent | not found |
| 478 | ٤٧٨ | parseable | pdf:130(bk:125) |
| 481 | ٤٨١ | absent | not found |
| 504 | ٥٠٤ | absent | not found |
| 505 | ٥٠٥ | parseable | pdf:136(bk:131) |
| 506 | ٥٠٦ | absent | not found |
| 509 | ٥٠٩ | parseable | pdf:137(bk:132) |
| 510 | ٥١٠ | absent | not found |
| 519 | ٥١٩ | parseable | pdf:140(bk:135) |
| 520 | ٥٢٠ | parseable | pdf:140(bk:135) |
| 521 | ٥٢١ | possibly parseable | not found |
| 522 | ٥٢٢ | parseable | pdf:140(bk:135) |
| 523 | ٥٢٣ | possibly parseable | not found |
| 539 | ٥٣٩ | absent | not found |
| 542 | ٥٤٢ | absent | not found |
| 549 | ٥٤٩ | absent | not found |
| 550 | ٥٥٠ | absent | not found |
| 551 | ٥٥١ | absent | not found |
| 552 | ٥٥٢ | parseable | pdf:149(bk:144) |
| 576 | ٥٧٦ | possibly parseable | pdf:154(bk:149) |
| 577 | ٥٧٧ | parseable | pdf:154(bk:149) |
| 606 | ٦٠٦ | absent | not found |
| 611 | ٦١١ | parseable | pdf:162(bk:157) |
| 615 | ٦١٥ | absent | not found |
| 636 | ٦٣٦ | possibly parseable | not found |
| 638 | ٦٣٨ | absent | not found |
| 640 | ٦٤٠ | absent | not found |
| 641 | ٦٤١ | possibly parseable | not found |
| 642 | ٦٤٢ | possibly parseable | pdf:170(bk:165) |
| 644 | ٦٤٤ | absent | not found |
| 646 | ٦٤٦ | absent | not found |
| 668 | ٦٦٨ | possibly parseable | not found |
| 669 | ٦٦٩ | absent | not found |
| 670 | ٦٧٠ | possibly parseable | not found |
| 682 | ٦٨٢ | absent | not found |
| 683 | ٦٨٣ | parseable | pdf:180(bk:175) |
| 684 | ٦٨٤ | possibly parseable | not found |
| 685 | ٦٨٥ | parseable | pdf:180(bk:175) |
| 686 | ٦٨٦ | possibly parseable | not found |
| 687 | ٦٨٧ | parseable | pdf:180(bk:175) |
| 692 | ٦٩٢ | absent | not found |
| 702 | ٧٠٢ | parseable | pdf:183(bk:178) |
| 704 | ٧٠٤ | absent | not found |
| 705 | ٧٠٥ | parseable | pdf:184(bk:179) |
| 706 | ٧٠٦ | possibly parseable | not found |
| 707 | ٧٠٧ | parseable | pdf:184(bk:179) |
| 710 | ٧١٠ | absent | not found |
| 713 | ٧١٣ | possibly parseable | pdf:186(bk:181) |
| 715 | ٧١٥ | absent | not found |
| 718 | ٧١٨ | possibly parseable | not found |
| 722 | ٧٢٢ | absent | not found |
| 724 | ٧٢٤ | possibly parseable | not found |
| 726 | ٧٢٦ | possibly parseable | not found |
| 727 | ٧٢٧ | parseable | pdf:188(bk:183) |
| 728 | ٧٢٨ | possibly parseable | not found |

### Part 3 (743-882)

| No. | Arabic | Assessment | OCR Location |
|-----|--------|------------|--------------|
| 783 | ٧٨٣ | absent | not found |
| 784 | ٧٨٤ | possibly parseable | not found |
| 786 | ٧٨٦ | absent | not found |

### Part 4 (883-1005)

| No. | Arabic | Assessment | OCR Location |
|-----|--------|------------|--------------|
| 894 | ٨٩٤ | parseable | pdf:252(bk:247) |
| 895 | ٨٩٥ | parseable | pdf:252(bk:247) |
| 919 | ٩١٩ | possibly parseable | not found |
| 960 | ٩٦٠ | absent | not found |
| 962 | ٩٦٢ | absent | not found |
| 1000 | ١٠٠٠ | absent | not found |

## Parseable Hadiths (Full List)

These 66 hadiths have clear OCR markers and should be recoverable by an improved parser.

14, 21, 23, 25, 29, 30, 31, 32, 42, 44, 46, 47, 48, 49, 51, 52, 53, 54, 55, 56, 84, 86, 87, 88, 89, 92, 94, 98, 102, 103, 125, 208, 215, 217, 220, 222, 234, 284, 286, 321, 326, 329, 348, 363, 379, 444, 461, 462, 478, 505, 509, 519, 520, 522, 552, 577, 611, 683, 685, 687, 702, 705, 707, 727, 894, 895

### Sample OCR Contexts for Parseable Hadiths

- **No. 14** (١٤) | pdf_page=14 book_page=9 | cat=clear_marker
  Context: 
- **No. 21** (٢١) | pdf_page=34 book_page=29 | cat=ambiguous
  Context: 
- **No. 23** (٢٣) | pdf_page=114 book_page=109 | cat=clear_marker
  Context: 
- **No. 25** (٢٥) | pdf_page=254 book_page=249 | cat=clear_marker
  Context: 
- **No. 29** (٢٩) | pdf_page=18 book_page=13 | cat=text_follows
  Context: 
- **No. 30** (٣٠) | pdf_page=18 book_page=13 | cat=text_follows
  Context: 
- **No. 31** (٣١) | pdf_page=17 book_page=12 | cat=ambiguous
  Context: 
- **No. 32** (٣٢) | pdf_page=19 book_page=14 | cat=clear_marker
  Context: 
- **No. 42** (٤٢) | pdf_page=120 book_page=115 | cat=clear_marker
  Context: 
- **No. 44** (٤٤) | pdf_page=22 book_page=17 | cat=clear_marker
  Context: 
- **No. 46** (٤٦) | pdf_page=126 book_page=121 | cat=clear_marker
  Context: 
- **No. 47** (٤٧) | pdf_page=127 book_page=122 | cat=clear_marker
  Context: 
- **No. 48** (٤٨) | pdf_page=130 book_page=125 | cat=clear_marker
  Context: 
- **No. 49** (٤٩) | pdf_page=133 book_page=128 | cat=clear_marker
  Context: 
- **No. 51** (٥١) | pdf_page=24 book_page=19 | cat=text_follows
  Context: 
- **No. 52** (٥٢) | pdf_page=24 book_page=19 | cat=text_follows
  Context: 
- **No. 53** (٥٣) | pdf_page=24 book_page=19 | cat=text_follows
  Context: 
- **No. 54** (٥٤) | pdf_page=147 book_page=142 | cat=ambiguous
  Context: 
- **No. 55** (٥٥) | pdf_page=149 book_page=144 | cat=clear_marker
  Context: 
- **No. 56** (٥٦) | pdf_page=151 book_page=146 | cat=clear_marker
  Context: 

## Absent Hadiths (Full List)

These 57 hadiths have no Arabic numeral found in the OCR at all.

95, 99, 101, 105, 109, 111, 115, 200, 206, 210, 244, 245, 250, 282, 287, 332, 343, 345, 370, 374, 375, 381, 392, 393, 394, 400, 409, 411, 432, 466, 481, 504, 506, 510, 539, 542, 549, 550, 551, 606, 615, 638, 640, 644, 646, 669, 682, 692, 704, 710, 715, 722, 783, 786, 960, 962, 1000

## Limitations

- Arabic OCR quality varies; digits can be misread (e.g., ٩ vs ٧, ٦ vs ١)
- Chapter header bab-numbers overlap with hadith numbers, causing ambiguity
- Possibly parseable category requires manual review
- Image-only PDF pages produce no OCR text; absent hadiths may fall on such pages
- Hadith numbers embedded mid-line without clear delimiter are harder to detect
