---
type: evidence
retrieved: 2026-11-21
---

# Which upstream file each local copy is

Measured on 2026-11-21 from the repository and the public APIs. No dataset was
downloaded; Kaggle file sizes come from the Kaggle metadata API
(`kaggle-fahd09-*-files-2026-11-21.txt`).

## Six books (K6) and the narrator lexicon are the two Kaggle datasets by `fahd09`

| Local file | First commit | Bytes in that commit | Kaggle file | Kaggle bytes | Kaggle licence label |
| --- | --- | ---: | --- | ---: | --- |
| `datasets/hadith-data/all_hadiths_clean.csv` | `2696de8`, 2026-03-22 "add hadith datasets" | 41,069,994 | `fahd09/hadith-dataset` → `all_hadiths_clean.csv` | 41,069,994 | CC0: Public Domain |
| `datasets/narrator-data/all_rawis.csv` | `2696de8`, 2026-03-22 | 9,267,851 | `fahd09/hadith-narrators` → `all_rawis.csv` | 9,267,851 | CC0: Public Domain |

- SHA-256 of `all_hadiths_clean.csv` as first committed: `a6800edb54d45a6e6c5228cf0342c0c72d90eca62a857bcbb5c61684e550db15`.
- SHA-256 of `all_rawis.csv` (unchanged since first commit): `d87c3af64d48b3cd585294ab5f6381536a51ff95a72a6707a7426ea483bf6c11`.
- The committed header `id,hadith_id,source,chapter_no,hadith_no,chapter,chain_indx,text_ar,text_en` and the
  `chain_indx` → `scholar_indx` link match the Kaggle description ("the chain_indx column refers to scholar_indx
  column in Hadith Narrators Dataset").
- Row count in the first commit: 34,441 (Bukhari 7,370; Muslim 7,596; Abu Dawud 5,260; Tirmidhi 4,214;
  Nasa'i 5,774; Ibn Majah 4,227), identical to the K6 rows in today's master.
- Kaggle says the hadith data was "scraped from http://qaalarasulallah.com/" and the narrators from
  "muslimscholars.info". Both uploads are version 1 of August 2018.

Byte-identical size plus identical header and linkage is strong evidence, not a hash proof: the Kaggle files
themselves were not downloaded.

## The K6 text descends from sunnah.com

The first English row of four collections in the first-committed CSV was compared with the live sunnah.com page
(`sunnah-sample-*-1-2026-11-21.txt`):

| Collection | K6 English (start) | On sunnah.com | Arabic (first 60 letters, diacritics removed) on sunnah.com |
| --- | --- | --- | --- |
| Abu Dawud 1 | "Narrated Mughirah ibn Shu'bah: When the Prophet (ﷺ) went (outside)…" | yes, verbatim | yes |
| Tirmidhi 1 | "Ibn 'Umar narrated that: the Prophet said: "Salat will not be accepted without purification…" | yes, verbatim; page grades it "Sahih (Darussalam)" | yes |
| Nasa'i 1 | "It was narrated from Abu Hurairah that the Prophet (ﷺ) said: "When any one of you wakes from sleep…" | yes, verbatim | yes |
| Ibn Majah 1 | "Abu Hurairah narrated that: The Prophet said: "Whatever I have commanded you do it…" | yes, verbatim | yes |

The K6 Arabic carries no vocalization; sunnah.com's does. Bukhari's first row is the Muhsin Khan wording that
sunnah.com credits ("The translation provided here is by Dr. M. Muhsin Khan", capture of 2026-07-20 in
`.omc/research/sunnah-bukhari-2026-07-20.html`); Muslim is credited there to Abdul Hamid Siddiqui. On the
Tirmidhi, Nasa'i and Ibn Majah pages the English reference is given as "Vol. 1, Book 1, Hadith 1", the
volume numbering of a printed multi-volume English edition.

Four samples is a spot check, not a full collation.

## OpenITI files are the official blobs

| Local file | Git blob id | OpenITI URI |
| --- | --- | --- |
| `datasets/hadith-data/openiti-sources/zayd/musnad_zaydiyya_052.mARkdown` (452,810 bytes) | `2c97cb75946922ea45e348ef10f1f94ee10bb1c7` | `0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1` |
| `datasets/hadith-data/openiti-sources/rabi/jamic_sahih_ibadiyya.txt` (481,681 bytes) | `cd75e85312a6204bd9aa17d888c2ae4306994b88` | `0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1` |

Both blob ids equal the ones the GitHub API reported for the official files on 2026-07-20
(`.omc/research/source-research-summary-2026-07-20.md`). The files were taken from repository `master`, not from
a tagged release; the CC BY-NC-SA 4.0 licence is declared on the Zenodo release record (2025.1.9).
Local file dates: 2026-05-08.

## Thaqalayn snapshot date

`datasets/hadith-data/shia-hadith/v2_books/*.json` have file dates of 2026-04-19 and were last changed in commit
`acbf394` (2026-04-20). The 2026-07-22 refresh published nothing (`datasets/sources/thaqalayn-api.md`, Known
limits), so the text in use is the April 2026 pull, served by the third-party ThaqalaynAPI (which itself pulls
from Thaqalayn with an API key issued by Thaqalayn, per its README).

## Pure Canon workbooks

- `datasets/hadith-data/sheikahmad/Hadith-Pure-Canon-Authentica.xlsx`: document properties creator "DELL",
  created 2026-03-29, modified 2026-03-31. No licence or rights sheet; sheet names `Sheet1`–`Sheet3`. Cells carry
  links to `nabimuhammad.com` pages.
- `NabiMuhammad-com_First_Green_Book_of_Sahih_Hadith.xlsx`: created by `openpyxl` 2026-04-15, modified by "DELL"
  2026-04-16. The provider's landing page offers this file for download (`nabimuhammad-hadith-canon-2026-11-21.txt`).
- `pure_canon.jsonl` (100,217 rows) labels every row `ruling = ثابت`. Source labels include `مسند حنبل` (23,529),
  `سنن الدارمي` (2,477), `شافعي` (2,054), `موطأ مالك` (1,855). Several rows embed edition blocks
  ("معلومات عن النشرة التي تم العزو إليها"), e.g. Darimi: Dar al-Kitab al-Arabi, Beirut 1987, ed. Fawwaz Ahmad
  Zamarli and Khalid al-Sab' al-'Alami; Muwatta': ed. Muhammad Fu'ad 'Abd al-Baqi. The provider's own list of
  "14 Reference Pillars" does not include a Musnad al-Shafi'i, so what `شافعي` denotes is itself unconfirmed.

## OpenITI holds open-licensed alternatives for most Sunni works

GitHub contents API, 2026-11-21: `0275AH/data/0256Bukhari/0256Bukhari.Sahih`, `0275AH/data/0261Muslim/0261Muslim.Sahih`,
`0275AH/data/0275AbuDawudSijistani/0275AbuDawudSijistani.Sunan`, `0300AH/data/0279Tirmidhi/0279Tirmidhi.Sunan`,
`0325AH/data/0303Nasai/0303Nasai.SunanSughra`, `0275AH/data/0273IbnMaja/0273IbnMaja.Sunan`,
`0250AH/data/0241IbnHanbal/0241IbnHanbal.Musnad`, `0225AH/data/0204Shafici/0204Shafici.Musnad`,
`0200AH/data/0179MalikIbnAnas/0179MalikIbnAnas.Muwatta` all exist. Darimi was not found at
`0275AH/data/0255Darimi`; its folder name was not searched further. Existence was checked; edition, completeness
and numbering of these versions were not.

## Fetches that failed

- `http://qaalarasulallah.com/` timed out twice; the Wayback Machine copy (snapshot 2026-10-02) could not be
  reached (connection refused). Its terms are unknown.
- `https://thaqalayn.net/*` now redirects (308) to `https://thaqalayn.com/*`; the `.com` pages were captured.
