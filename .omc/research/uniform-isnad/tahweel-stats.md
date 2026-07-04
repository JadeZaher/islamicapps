# Taḥwīl-occurrence audit

Generated: 2026-06-11T11:43:52.561654Z  
Source: `datasets/hadith-data/all_hadiths_unified.csv`  
Detector regex: `(?:^|[\s،.])ح\s+و?(?:حدثنا|حدثني|أخبرنا|أخبرني|أنبأنا|أنبأني|ثنا|نا)`  
Total rows scanned: 99,283

Columns:
- **rows** total rows from that source
- **w/ text_ar** rows where `text_ar` is non-empty
- **0br** no ح splitter (single chain)
- **1br** 1 ح splitter (2 chains)
- **2br** 2 ح splitters (3 chains)
- **3br** 3 ح splitters (4 chains)
- **4+** 4 or more ح splitters
- **multi%** percentage of `w/ text_ar` rows that have at least one ح

| Source | rows | w/ text_ar | 0br | 1br | 2br | 3br | 4+ | multi% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Musnad Ahmad | 23,529 | 23,529 | 23,529 | 0 | 0 | 0 | 0 | 0.0% |
| Al-Kāfi | 14,245 | 14,245 | 14,245 | 0 | 0 | 0 | 0 | 0.0% |
| Sahih Muslim | 7,596 | 7,590 | 6,513 | 818 | 164 | 52 | 49 | 14.3% |
| Sahih Bukhari | 7,370 | 7,370 | 7,335 | 35 | 0 | 0 | 0 | 0.5% |
| Man Lā Yaḥḍuruh al-Faqīh | 6,382 | 6,382 | 6,382 | 0 | 0 | 0 | 0 | 0.0% |
| Sunan an-Nasa'i | 5,774 | 5,774 | 5,638 | 136 | 0 | 0 | 0 | 2.4% |
| Sunan Abi Da'ud | 5,260 | 5,260 | 4,990 | 251 | 14 | 3 | 2 | 5.1% |
| Sunan Ibn Majah | 4,227 | 4,227 | 4,012 | 204 | 11 | 0 | 0 | 5.1% |
| Jami' al-Tirmidhi | 4,214 | 4,212 | 4,185 | 27 | 1 | 1 | 0 | 0.7% |
| Sunan al-Darimi | 2,477 | 2,477 | 2,477 | 0 | 0 | 0 | 0 | 0.0% |
| Nahj al-Balāgha | 2,260 | 2,260 | 2,260 | 0 | 0 | 0 | 0 | 0.0% |
| Musnad al-Shafi'i | 2,054 | 2,054 | 2,054 | 0 | 0 | 0 | 0 | 0.0% |
| Muwatta' Malik | 1,855 | 1,855 | 1,855 | 0 | 0 | 0 | 0 | 0.0% |
| Al-Amālī | 1,469 | 1,469 | 1,469 | 0 | 0 | 0 | 0 | 0.0% |
| Al-Khiṣāl | 1,282 | 1,282 | 1,282 | 0 | 0 | 0 | 0 | 0.0% |
| Kitāb al-Ghayba | 1,242 | 1,242 | 1,242 | 0 | 0 | 0 | 0 | 0.0% |
| Thawāb al-Aʿmāl wa ʿiqāb al-Aʿmāl | 1,106 | 1,106 | 1,106 | 0 | 0 | 0 | 0 | 0.0% |
| al-Jami al-Sahih (Musnad al-Rabi ibn Habib) | 1,004 | 1,004 | 1,004 | 0 | 0 | 0 | 0 | 0.0% |
| ʿUyūn akhbār al-Riḍā | 954 | 954 | 954 | 0 | 0 | 0 | 0 | 0.0% |
| Maʿānī al-ʾAkhbār | 829 | 829 | 829 | 0 | 0 | 0 | 0 | 0.0% |
| Kāmil al-Ziyārāt | 750 | 750 | 750 | 0 | 0 | 0 | 0 | 0.0% |
| Musnad al-Imam Zayd ibn Ali | 698 | 698 | 698 | 0 | 0 | 0 | 0 | 0.0% |
| Kamāl al-Dīn wa Tamām al-Niʿma | 659 | 659 | 659 | 0 | 0 | 0 | 0 | 0.0% |
| Al-Tawḥīd | 575 | 575 | 575 | 0 | 0 | 0 | 0 | 0.0% |
| Muʿjam al-Aḥādīth al-Muʿtabara | 555 | 555 | 555 | 0 | 0 | 0 | 0 | 0.0% |
| Kitāb al-Zuhd | 290 | 290 | 290 | 0 | 0 | 0 | 0 | 0.0% |
| Kitāb al-Ḍuʿafāʾ | 226 | 226 | 226 | 0 | 0 | 0 | 0 | 0.0% |
| Kitāb al-Muʾmin | 201 | 201 | 201 | 0 | 0 | 0 | 0 | 0.0% |
| Ṣifāt al-Shīʿa | 71 | 71 | 71 | 0 | 0 | 0 | 0 | 0.0% |
| Risālat al-Ḥuqūq | 49 | 49 | 49 | 0 | 0 | 0 | 0 | 0.0% |
| Faḍaʾil al-Shīʿa | 45 | 45 | 45 | 0 | 0 | 0 | 0 | 0.0% |
| Sahifat al-Imam Ali al-Rida | 35 | 35 | 35 | 0 | 0 | 0 | 0 | 0.0% |
| **TOTAL** | **99,283** | **99,275** | **97,515** | **1,471** | **190** | **56** | **51** | **1.8%** |

## Headline numbers

- Rows requiring multi-branch extractor: **1,768** (1.8% of rows with text_ar)
- Maximum branches per hadith observed: **5** (4+ class indicates rare high-branching cases — Q2 in spec)

## Decisions this audit feeds

- **T-1.1 algorithm complexity**: if 2br+ is < 1% of corpus, optimize the algorithm for 1br as the common case and treat 2+ as edge cases.
- **T-1.3 convergence detection**: 1br rows are the calibration set for T-0.3.
- **Phase 5 UI rendering**: the per-source multi% tells us which source pages need the multi-chain renderer up front (high-multi% sources) vs. which can defer it (low-multi% sources).
