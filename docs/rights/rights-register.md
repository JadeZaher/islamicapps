---
type: rights-register
status: proposal-awaiting-owner-approval
prepared: 2026-11-21
scope: the 34 source works of source_work_registry.json (registry 2026.07.23), the narrator lexicon, and the six OpenITI rijal texts
---

# Rights register

**What this is.** The evidence, per source work, for what the archive may publish, and a proposed status for
each component. It is assembled for the owner's decision. **It is not legal advice.** Copyright in editions,
translations and databases depends on the country and on facts not visible from here; where an answer turns on
either, the status is `unclear`, not a guess. Nothing in this file has been recorded in any database.

Evidence files sit in [`evidence/`](./evidence/), one per fetched page, each headed with its URL, retrieval
time (2026-11-21 UTC) and purpose. Local file identities are proven in
[`evidence/local-copy-identity-2026-11-21.md`](./evidence/local-copy-identity-2026-11-21.md).

Status words: `clear` (permitted, no conditions beyond citation) · `clear_with_conditions` (permitted under the
conditions listed) · `unclear` (terms silent, contradictory or jurisdiction-dependent; what is missing is said) ·
`not_permitted` (current terms or third-party copyright rule it out) · `permission_needed` (ask; whom, and a
draft, below) · `n/a` (we hold no such component).

## The four findings that change what can be published

1. **The six books did not come from sunnah.com, and their English is not ours to publish.** Our K6 file is
   byte-for-byte the size of the 2018 Kaggle upload `fahd09/hadith-dataset` (41,069,994 bytes), which says it
   was "scraped from http://qaalarasulallah.com/" and labels itself CC0. Spot checks show the text is
   sunnah.com's, word for word. The uploader's CC0 cannot license other people's translations: the English is
   Muhsin Khan, Abdul Hamid Siddiqui, Ahmad Hasan and Darussalam's published translations, and sunnah.com's
   own policy says "We do not permit … mass reproduction of entire books or collections on other websites."
2. **Thaqalayn now licenses its library under CC BY 4.0, but only the rights it holds.** Its Terms of Use
   (updated 2026-10-01) license "public library content, including translations" under CC BY 4.0, including
   commercially, and then say "This grant covers the rights held by Stichting Thaqalayn." Its About page says
   "We use already available translations." So the Imami Arabic can go public with attribution. Whether each
   English translation is Thaqalayn's to license is the one question to ask Thaqalayn.
3. **OpenITI is CC BY-NC-SA 4.0, so the Zaydi, Ibadi and Rida works can go public non-commercially.** The
   project cards said "unstated"; the Zenodo record of release 2025.1.9 states `cc-by-nc-sa-4.0`. Everything
   derived from those texts, including our machine translations and chain tables, must carry the same licence.
4. **The schema's per-work gate cannot hold "Arabic cleared, provider English not cleared".** With
   `english_policy = reviewed_only`, any provider English row that a reviewer later marks `source_verified` or
   `human_verified` becomes public, whoever owns it. Until the schema can say "no provider English" for a work,
   a process rule must stop reviewers from verifying English whose rights are not cleared (see
   [untangling-plan.md](./untangling-plan.md) step 2).

Also material: *Mu'jam al-Ahadith al-Mu'tabara* is a modern work (Muhammad Asif Muhsini, d. 2019), not a
classical one; the narrator lexicon is a scrape of muslimscholars.info ("All contents copyright of Arees
Institute"); and the Pure Canon provider's site says "© 2026 NabiMuhammad.com — All Rights Reserved" while
our workbook carries no licence.

## Summary table

Rows are the counts in the active master (`all_hadiths_unified.csv.gz`, 99,283 rows). Death dates are the
conventional ones, given only to show the underlying text is pre-modern; they are not curated claims.
"Gate" is the proposed `collection_rights` row (see
[collection_rights_proposal.csv](./collection_rights_proposal.csv)).

| # | Work (`source_work_id`) | Trad. | Compiler, d. | Our copy from | Rows | Arabic | English | Gradings | Metadata | Proposed gate |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- |
| 1 | Sahih al-Bukhari (`sunni:bukhari`) | Sunni | al-Bukhari, 256/870 | Kaggle `fahd09` ← qaalarasulallah.com ← sunnah.com | 7,370 | unclear | not_permitted | n/a | unclear | pending |
| 2 | Sahih Muslim (`sunni:muslim`) | Sunni | Muslim, 261/875 | same | 7,596 | unclear | not_permitted | n/a | unclear | pending |
| 3 | Sunan Abi Dawud (`sunni:abudawud`) | Sunni | Abu Dawud, 275/889 | same | 5,260 | unclear | not_permitted | n/a | unclear | pending |
| 4 | Jami' al-Tirmidhi (`sunni:tirmidhi`) | Sunni | al-Tirmidhi, 279/892 | same | 4,214 | unclear | not_permitted | n/a | unclear | pending |
| 5 | Sunan al-Nasa'i (`sunni:nasai`) | Sunni | al-Nasa'i, 303/915 | same | 5,774 | unclear | not_permitted | n/a | unclear | pending |
| 6 | Sunan Ibn Majah (`sunni:ibnmajah`) | Sunni | Ibn Majah, 273/887 | same | 4,227 | unclear | not_permitted | n/a | unclear | pending |
| 7 | Musnad Ahmad (`sunni:ahmad`) | Sunni | Ahmad b. Hanbal, 241/855 | NabiMuhammad.com workbook | 23,529 | permission_needed | n/a (project MT candidates only) | permission_needed (provider label, not a grade) | permission_needed | pending |
| 8 | Muwatta' Malik (`sunni:muwatta`) | Sunni | Malik b. Anas, 179/795 | same | 1,855 | permission_needed | n/a (MT candidates) | permission_needed | permission_needed | pending |
| 9 | Sunan al-Darimi (`sunni:darimi`) | Sunni | al-Darimi, 255/869 | same | 2,477 | permission_needed | n/a (MT candidates) | permission_needed | permission_needed | pending |
| 10 | Musnad al-Shafi'i (`sunni:shafii`) | Sunni | al-Shafi'i, 204/820 | same (label `شافعي`, identity unconfirmed) | 2,054 | permission_needed | n/a (MT candidates) | permission_needed | permission_needed | pending |
| 11 | al-Jami' al-Sahih / Musnad al-Rabi' (`ibadi:musnad-rabi`) | Ibadi | al-Rabi' b. Habib, 2nd/8th c. | OpenITI | 1,004 | clear_with_conditions | clear_with_conditions (project MT; review gate) | n/a | clear_with_conditions | cleared, after notice is live |
| 12 | al-Kafi (`imami:al-kafi`) | Imami | al-Kulayni, 329/941 | Thaqalayn via ThaqalaynAPI | 14,245 | clear_with_conditions | unclear | Majlisi: clear_with_conditions; Behbudi: unclear | clear_with_conditions | cleared, after attribution |
| 13 | Man La Yahduruhu al-Faqih (`imami:man-la-yahduruhu-al-faqih`) | Imami | al-Saduq, 381/991 | same | 6,382 | clear_with_conditions | unclear | Muhsini (vol. 5): unclear | clear_with_conditions | cleared, after attribution |
| 14 | Nahj al-Balagha (`imami:nahj-al-balagha`) | Imami | al-Sharif al-Radi, 406/1015 | same | 2,260 | clear_with_conditions | unclear | n/a | clear_with_conditions | cleared, after attribution |
| 15 | al-Amali, Saduq (`imami:al-amali-saduq`) | Imami | al-Saduq, 381/991 | same | 1,082 | clear_with_conditions | unclear | n/a | clear_with_conditions | cleared, after attribution |
| 16 | al-Amali, Mufid (`imami:al-amali-mufid`) | Imami | al-Mufid, 413/1022 | same | 387 | clear_with_conditions | unclear | unclear (16 rows) | clear_with_conditions | cleared, after attribution |
| 17 | al-Khisal (`imami:al-khisal`) | Imami | al-Saduq | same | 1,282 | clear_with_conditions | unclear | unclear (64 rows) | clear_with_conditions | cleared, after attribution |
| 18 | Kitab al-Ghayba, Tusi (`imami:kitab-al-ghayba-tusi`) | Imami | al-Tusi, 460/1067 | same | 774 | clear_with_conditions | unclear | n/a | clear_with_conditions | cleared, after attribution |
| 19 | Kitab al-Ghayba, Nu'mani (`imami:kitab-al-ghayba-numani`) | Imami | al-Nu'mani, c. 360/971 | same | 468 | clear_with_conditions | unclear | n/a | clear_with_conditions | cleared, after attribution |
| 20 | Thawab al-A'mal (`imami:thawab-al-amal`) | Imami | al-Saduq | same | 1,106 | clear_with_conditions | unclear | n/a | clear_with_conditions | cleared, after attribution |
| 21 | 'Uyun Akhbar al-Rida (`imami:uyun-akhbar-al-rida`) | Imami | al-Saduq | same | 954 | clear_with_conditions | unclear | unclear (5 rows) | clear_with_conditions | cleared, after attribution |
| 22 | Ma'ani al-Akhbar (`imami:maani-al-akhbar`) | Imami | al-Saduq | same | 829 | clear_with_conditions | unclear | unclear (2 rows) | clear_with_conditions | cleared, after attribution |
| 23 | Kamil al-Ziyarat (`imami:kamil-al-ziyarat`) | Imami | Ibn Qulawayh, 368/978 | same | 750 | clear_with_conditions | unclear | n/a | clear_with_conditions | cleared, after attribution |
| 24 | Kamal al-Din (`imami:kamal-al-din`) | Imami | al-Saduq | same | 659 | clear_with_conditions | unclear (translator blank in our snapshot) | n/a | clear_with_conditions | cleared, after attribution |
| 25 | al-Tawhid (`imami:al-tawhid-saduq`) | Imami | al-Saduq | same | 575 | clear_with_conditions | unclear | unclear (15 rows) | clear_with_conditions | cleared, after attribution |
| 26 | Mu'jam al-Ahadith al-Mu'tabara (`imami:mujam-al-ahadith-al-mutabara`) | Imami | Muhammad Asif Muhsini, **2019** | same | 555 | permission_needed | unclear | permission_needed | permission_needed | pending |
| 27 | Kitab al-Zuhd (`imami:kitab-al-zuhd`) | Imami | al-Husayn b. Sa'id al-Ahwazi, 3rd/9th c. | same | 290 | clear_with_conditions | unclear | unclear (1 row) | clear_with_conditions | cleared, after attribution |
| 28 | Kitab al-Du'afa (`imami:kitab-al-duafa`) | Imami | Ibn al-Ghada'iri, 5th/11th c. | same | 226 | clear_with_conditions | unclear | n/a | clear_with_conditions | cleared, after attribution |
| 29 | Kitab al-Mu'min (`imami:kitab-al-mumin`) | Imami | al-Ahwazi | same | 201 | clear_with_conditions | unclear | n/a | clear_with_conditions | cleared, after attribution |
| 30 | Sifat al-Shi'a (`imami:sifat-al-shia`) | Imami | al-Saduq | same | 71 | clear_with_conditions | unclear | n/a | clear_with_conditions | cleared, after attribution |
| 31 | Fada'il al-Shi'a (`imami:fadail-al-shia`) | Imami | al-Saduq | same | 45 | clear_with_conditions | unclear | n/a | clear_with_conditions | cleared, after attribution |
| 32 | Risalat al-Huquq (`imami:risalat-al-huquq`) | Imami | attrib. Imam Zayn al-'Abidin, 95/713 | same | 49 | clear_with_conditions | permission_needed (Chittick) | n/a | clear_with_conditions | cleared, after attribution |
| 33 | Sahifat al-Imam 'Ali al-Rida (`imami:sahifat-al-imam-ali-al-rida`) | Imami | attrib. al-Rida, 203/818 | OpenITI (appendix of the Zayd file) | 35 | clear_with_conditions | clear_with_conditions (project MT; review gate) | n/a | clear_with_conditions | cleared, after notice is live |
| 34 | Musnad al-Imam Zayd (`zaydi:musnad-zayd`) | Zaydi | Zayd b. 'Ali, 122/740 (comp. 'Abd al-'Aziz b. Ishaq al-Baghdadi, 4th/10th c.) | OpenITI | 698 | clear_with_conditions | clear_with_conditions (project MT; review gate) | n/a | clear_with_conditions | cleared, after notice is live |

Not one of the 34 works but on every narrator page:

| Asset | Our copy from | Rows | Status |
| --- | --- | ---: | --- |
| Narrator lexicon (`all_rawis.csv`) | Kaggle `fahd09/hadith-narrators` ← muslimscholars.info (Arees Institute) | 24,326 | Public display of its fields: permission_needed. Internal use as a matching index: unclear |
| Six OpenITI rijal texts (`datasets/sources/external/`) | OpenITI | n/a | clear_with_conditions (CC BY-NC-SA 4.0); exclude `EDITOR`-tagged apparatus |

Counts: 23 works can be `cleared` for Arabic once attribution is displayed (20 via Thaqalayn, 3 via OpenITI);
11 stay `pending` (6 K6, 4 Pure Canon, Mu'jam). No provider English is cleared today.

## Underlying texts: what is and is not in copyright

All 34 works except one are pre-modern. Their authors died between the 2nd/8th and 5th/11th centuries, so the
works themselves are in the public domain everywhere. What can carry rights today is the modern layer on top:

- **The digital transcription.** A faithful transcription of a public-domain text is generally not an original
  work under US-style law. Some countries protect it anyway: the EU database right protects a substantial
  extraction from a database whose maker invested in it, and Germany and Italy give limited terms to scientific
  or critical editions. Which applies depends on where the maker sits and where we publish: `unclear` unless a
  provider has licensed it.
- **Editorial apparatus.** Vocalization added by a modern editor, footnotes, critical notes, the editor's
  numbering and chapter titles. Our K6 Arabic carries no vocalization; Thaqalayn's Arabic is fully vocalized;
  OpenITI's cleaned versions removed "all paratextual elements (introductions, footnotes, indices…)".
- **Translations.** Every modern English translation is its own copyright work, owned by the translator or
  publisher, for decades after the translator's death.
- **Gradings.** A one-word verdict is a fact or opinion, not usually protected on its own. A modern scholar's
  complete set of verdicts, copied from his book, may be protected as a compilation. Classical gradings (al-
  Majlisi, d. 1110/1699) are public domain as text.
- **The exception is *Mu'jam al-Ahadith al-Mu'tabara*.** It is a modern selection of narrations judged reliable
  by Muhammad Asif Muhsini (died 2019). The narrations are classical; the selection, arrangement and verdicts
  are his and are in copyright.

---

## Sources

### 1. The six books (K6): Kaggle `fahd09/hadith-dataset`, ultimately sunnah.com

**Works:** 1–6. **Rows:** 34,441 (853 lack English, 8 lack Arabic).

**Where our copy came from.** `datasets/hadith-data/all_hadiths_clean.csv`, first committed in `2696de8`
(2026-03-22), 41,069,994 bytes, SHA-256 `a6800edb…db15`. Kaggle's file `all_hadiths_clean.csv` in dataset
`fahd09/hadith-dataset` (version 1, 2018-08-22) has exactly that size and the same columns
([evidence](./evidence/kaggle-fahd09-hadith-dataset-files-2026-11-21.txt)). The Kaggle page says:

> "The data is scraped from http://qaalarasulallah.com/ … *Disclaimer: I scraped the data and I hold no
> responsibility for its accuracy or validation.*" ([evidence](./evidence/kaggle-fahd09-hadith-dataset-2026-11-21.txt))

Four spot checks show the English verbatim and the Arabic letter-for-letter on sunnah.com
([evidence](./evidence/local-copy-identity-2026-11-21.md#the-k6-text-descends-from-sunnahcom)). The project card
said "a bilingual Sunnah.com snapshot"; the content is sunnah.com's, but it reached us through two scrapes.
qaalarasulallah.com did not respond and its Wayback copy could not be reached, so its terms are unknown.

**Terms that govern it.**

- Kaggle label: "CC0: Public Domain". A CC0 dedication waives only the uploader's own rights. The uploader
  scraped the content and owned none of it, so the label licenses nothing we need.
- sunnah.com About, §8 ([evidence](./evidence/sunnah-about-2026-11-21.txt)):
  > "We do not permit the scraping of our data, nor mass reproduction of entire books or collections on other
  > websites. … If you would like a snapshot of hadith data, consider using our API. Reproducing individual
  > hadith or selections of hadith for a teaching/didactic/presentation purpose is permitted."
- sunnah.com About, §6: "The Arabic text on our website is sourced from al-eman.com and other now-defunct
  sources. For the English we use various translators."
- sunnah.com Developers ([evidence](./evidence/sunnah-developers-2026-11-21.txt)): the API "offers access to a
  portion of our data", needs a key requested through a GitHub issue, and an offline dump is "not available yet".
  The `sunnah-com/api` repository has no LICENSE file ([evidence](./evidence/github-repo-licences-2026-11-21.txt)).

**Components.**

| Component | Status | Why |
| --- | --- | --- |
| Arabic | unclear | Classical text, unvocalized in our copy, so no editor's vocalization is carried. Whether the transcription itself is protected depends on jurisdiction (database right). sunnah.com's policy objects to whole-collection reproduction; we never accepted its terms, but the text is its data. **Missing:** sunnah.com's position, or an openly licensed replacement |
| English | not_permitted | Modern published translations: Bukhari by Muhammad Muhsin Khan; Muslim by Abdul Hamid Siddiqui (credited on sunnah.com); Abu Dawud's wording matches sunnah.com's Ahmad Hasan text; Tirmidhi, Nasa'i and Ibn Majah match sunnah.com's text whose references cite a multi-volume printed English edition and whose grades are labelled "Darussalam". No translator or publisher has licensed it, and sunnah.com prohibits mass reproduction. Showing a few hadith for teaching is permitted by sunnah.com; a public archive of all of them is not |
| Gradings | n/a | Our K6 rows carry none |
| Metadata | unclear | English book and chapter titles come from the translations; numbering follows sunnah.com, which mixes its own and printed-edition schemes. Numbers as facts are not protected; the English headings travel with the translation |

**Derivative work.** Our normalization and chain extraction add nothing that changes the analysis: they are
derived from text whose status is `unclear`. Machine translation of the Arabic would avoid the translators'
copyright entirely, but inherits the Arabic's status.

**Way out.** Either (a) ask sunnah.com for written permission and an approved snapshot (request A), and ask the
translation publishers separately for English (request B); or (b) replace the K6 Arabic with OpenITI's versions
(found on 2026-11-21: Bukhari *Sahih*, Muslim *Sahih*, Abu Dawud *Sunan*, Tirmidhi *Sunan*, Nasa'i *Sunan
Sughra*, Ibn Majah *Sunan*), which are CC BY-NC-SA 4.0. (b) changes numbering and identity for 34,441 rows.

### 2. Musnad Ahmad, Muwatta', Sunan al-Darimi, "Musnad al-Shafi'i": NabiMuhammad.com Pure Canon

**Works:** 7–10. **Rows:** 29,915, Arabic only in the master; English exists only as archived project machine
translations (llama3.1:8b and OpenRouter runs, April 2026), none published.

**Where our copy came from.** `datasets/hadith-data/sheikahmad/Hadith-Pure-Canon-Authentica.xlsx` (created
2026-03-29 by "DELL", no licence sheet), normalized to `archive/sheikahmad-pure-canon/pure_canon.jsonl`
(100,217 rows). How the workbook reached the project is not recorded. Every row has `ruling = ثابت`.
Several rows embed edition blocks naming modern printed editions (Darimi: Dar al-Kitab al-Arabi, Beirut 1987,
ed. Zamarli and al-Sab' al-'Alami; Muwatta': ed. Muhammad Fu'ad 'Abd al-Baqi), so the digital text descends
from an unnamed electronic hadith library keyed to those editions
([evidence](./evidence/local-copy-identity-2026-11-21.md#pure-canon-workbooks)).

**Terms.** The provider is NabiMuhammad.com, led by Ahmad Darwish. Its "Hadith Pure Canon Authentica" page
offers the companion Green Book workbook for download and ends:

> "© 2026 NabiMuhammad.com — All Rights Reserved" ([evidence](./evidence/nabimuhammad-hadith-canon-2026-11-21.txt))

No licence, terms page or reuse permission was found ([home](./evidence/nabimuhammad-home-2026-11-21.txt),
[contact form](./evidence/nabimuhammad-contact-2026-11-21.txt)). Offering a file for download is not a licence
to republish it.

**Components.**

| Component | Status | Why |
| --- | --- | --- |
| Arabic | permission_needed | Classical texts, but the compiled digital text is the provider's and is marked All Rights Reserved. Ask NabiMuhammad.com (request C) |
| English | n/a | No provider English. Our machine candidates are derivatives of the Arabic and inherit its status |
| Gradings | permission_needed | `ثابت` is the provider's own seal on all 100,217 rows ("If it is not in this collection, it is not authentic"). It is a provider label, not a scholar's grading; the design already never shows collection labels as grades |
| Metadata | permission_needed | Book/chapter structure is the provider's |

**Identity flag (not a rights issue).** The provider lists 14 "Reference Pillars"; none is a Musnad al-Shafi'i.
Our 2,054 rows labelled `شافعي` are mapped to "Musnad al-Shafi'i" by the pipeline. Confirm what they are before
any publication.

**Way out.** Permission from NabiMuhammad.com, or replacement with OpenITI's *Musnad* of Ahmad, *Muwatta'* and
*Musnad* of al-Shafi'i (found 2026-11-21; Darimi not located by the obvious path), under CC BY-NC-SA 4.0.

### 3. Musnad Zayd, Jami' al-Sahih, Sahifat al-Rida: OpenITI

**Works:** 11, 33, 34. **Rows:** 1,004 + 35 + 698.

**Where our copy came from.** `datasets/hadith-data/openiti-sources/` (file dates 2026-05-08), parsed by
`datasets/parse_openiti.py`. The two text files are the official Git blobs `2c97cb75…` (Zayd, URI
`0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1`) and `cd75e853…` (Rabi', URI
`0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1`), taken from repository `master`, not a release tag.
The Rida rows are the appendix of the Zayd file from page 434.

**Terms.** Zenodo record 17767721, release 2025.1.9 of 2025-12-30, concept DOI 10.5281/zenodo.3082463:
`"license": {"id": "cc-by-nc-sa-4.0"}` ([evidence](./evidence/openiti-zenodo-17767721-2026-11-21.txt)). The
GitHub repositories carry no LICENSE file ([evidence](./evidence/github-repo-licences-2026-11-21.txt)). The
RELEASE README asks users to cite the specific Zenodo version
([evidence](./evidence/openiti-release-readme-2026-11-21.txt)). Per-text metadata:
Zayd is based on the printed edition OCLC 745191363, annotated for SHARIAsource; Rabi' records no edition;
both "All paratextual elements … removed … (OpenITI Clean operation, 2023)"
([Zayd](./evidence/openiti-yml-zayd-musnad-2026-11-21.txt), [Rabi'](./evidence/openiti-yml-rabi-jamic-2026-11-21.txt)).

CC BY-NC-SA 4.0 allows copying, display and adaptation **if** we (1) attribute OpenITI and keep its notices,
(2) link the licence, (3) say what we changed, (4) do not use it "primarily intended for or directed towards
commercial advantage or monetary compensation", and (5) license adaptations under the same terms.

**Components.**

| Component | Status | Conditions |
| --- | --- | --- |
| Arabic | clear_with_conditions | Attribution, licence link, change notice, non-commercial, share-alike. OpenITI can license only what it holds; the upstream Shamela-family libraries are not separately licensed (residual, low) |
| English | clear_with_conditions | It is our own machine translation, an adaptation, so it must be released under CC BY-NC-SA and labelled as machine output. Publication is still blocked by the translation release gate (`machine_unreviewed`), which is a quality rule, not a rights one. The Zaydi English was produced in April 2026 from an Archive.org OCR text, not from this OpenITI file; its alignment to this Arabic must be checked before review |
| Gradings | n/a | None |
| Metadata | clear_with_conditions | Book/chapter markers from OpenITI, same licence |

**Identity flags (not rights).** Zayd: 698 rows checked in, 699 from the official blob. Rabi': two rows share
`rabi_0387`. Rida: OpenITI's reviewer wrote "Page 434 onwards … is a different text; a Musnad by Imam Musa",
while the text's own heading is "مسند الإمام علي الرضا" and the project calls it *Sahifat*. Settle the title
before it is public.

### 4. Twenty classical Imami works plus Mu'jam: Thaqalayn, through ThaqalaynAPI

**Works:** 12–32. **Rows:** 33,190.

**Where our copy came from.** `datasets/hadith-data/shia-hadith/v2_books/*.json` (33 book files plus
`BookNames.json`), file dates 2026-04-19, last changed in `acbf394` (2026-04-20). The July 2026 refresh
published nothing, so the card's "retrieved 2026-07-21" is the last attempt, not the data's date. The files come
from ThaqalaynAPI, a third-party scraper by MohammedArab1 that reads Thaqalayn's own API with a key issued by
Thaqalayn ([README](./evidence/thaqalayn-api-readme-2026-11-21.txt)). Its GPL-3.0 licence is for its code only.
thaqalayn.net now redirects to thaqalayn.com.

**Terms.** Thaqalayn Terms of Use, "Last Updated: October 1, 2026" ([evidence](./evidence/thaqalayn-terms-2026-11-21.txt)):

> "Stichting Thaqalayn licenses its public library content, including translations, under Creative Commons
> Attribution 4.0 International (CC BY 4.0). You may copy, share, and adapt this material, including
> commercially, under the licence terms."
>
> "Credit Thaqalayn (Stichting Thaqalayn), preserve supplied author, translator, and other attribution notices,
> link to the source and licence where reasonably practicable, and indicate any changes. Do not imply
> endorsement by Thaqalayn."
>
> "This grant covers the rights held by Stichting Thaqalayn. Public-domain material remains public domain …"

And the About page ([evidence](./evidence/thaqalayn-about-2026-11-21.txt)): "We use already available
translations to make these texts available in Arabic and English side by side." Book pages show only
"Translated by <name>", with no separate rights notice. The gradings page names al-Majlisi and Bihbudi for
al-Kafi, and Hadi al-Najafi and Asif Muhsini "sporadically"
([evidence](./evidence/thaqalayn-grading-info-2026-11-21.txt)).

Our snapshot predates the October terms. CC BY attaches to the material, and the material is the same, so the
current grant is a reasonable basis; the terms in force in April 2026 were not captured.

**Translators as recorded in our snapshot** (`BookNames.json`):

| Work | Translator recorded |
| --- | --- |
| al-Kafi | Muhammad Sarwar |
| Man La Yahduruhu al-Faqih | Bab Ul Qaim Publications |
| Nahj al-Balagha | Sayed Ali Raza |
| al-Amali (Saduq) | Bilal Muhammad |
| al-Amali (Mufid) | Mulla Asgharali M M Jaffer |
| al-Khisal; 'Uyun Akhbar al-Rida | Dr. Ali Peiravi |
| Kitab al-Ghayba (Tusi) | Sayyid Athar Husain S. H. Rizvi |
| Kitab al-Ghayba (Nu'mani) | Abdullah al-Shahin |
| Thawab al-A'mal | Sayed Athar Husain Rizvi & Sayed Maqsood Athar |
| Ma'ani al-Akhbar | Basel Kadem |
| Kamil al-Ziyarat | Sayyid Mohsen Al-Husayni Al-Milani |
| Kamal al-Din | blank (the live manifest names Sayyid Athar Husain S. H. Rizvi) |
| al-Tawhid | Sayed Ali Raza Rizvi |
| Mu'jam al-Ahadith al-Mu'tabara | Ammaar Muslim |
| Kitab al-Zuhd | Shaykh Tahir Ridha Jaffer |
| Kitab al-Du'afa | Tashayyu |
| Kitab al-Mu'min | Muhajir b. Ali |
| Sifat al-Shi'a; Fada'il al-Shi'a | Badr Shahin |
| Risalat al-Huquq | William C. Chittick |

**Components.**

| Component | Status | Conditions / what is missing |
| --- | --- | --- |
| Arabic (20 classical works) | clear_with_conditions | CC BY 4.0: credit Thaqalayn, keep author and translator notices, link source and licence, state changes, no endorsement. Residual: vocalization from a modern printed edition is not Thaqalayn's to license; risk depends on jurisdiction |
| Arabic (Mu'jam) | permission_needed | Modern compilation (Muhsini, d. 2019). Thaqalayn's grant does not show that it holds his rights. Ask Thaqalayn first (request D), then the author's estate or publisher |
| English (all except Huquq) | unclear | Thaqalayn licenses translations but only those it holds rights in, and says it uses existing translations. **Missing:** which translations Thaqalayn owns or is licensed to sublicense. One question to Thaqalayn (request D) resolves all twenty |
| English (Risalat al-Huquq) | permission_needed | William C. Chittick's translation, published in his *The Psalms of Islam* (1988), from general knowledge, not verified here. Thaqalayn is unlikely to hold it. Ask Thaqalayn whom to ask, then the rights holder (request E) |
| Gradings: al-Majlisi (13,941 rows, al-Kafi) | clear_with_conditions | Classical source (*Mir'at al-'Uqul*); digitization under Thaqalayn's CC BY |
| Gradings: Bihbudi (1,966 rows, from *Sahih al-Kafi*), Muhsini (825 rows), others | unclear | Modern scholars' verdicts copied systematically from their books. Single verdicts are likely unprotected; the set may be. Include in request D |
| Metadata (book, category, chapter titles in English and Arabic) | clear_with_conditions | Thaqalayn content under CC BY 4.0 |

Attribution needs the translator for each work. The unified master drops it (source-research summary,
2026-07-20); it survives in `BookNames.json` and must be carried to the page.

### 5. Narrator lexicon: Kaggle `fahd09/hadith-narrators`, from muslimscholars.info

**Where our copy came from.** `datasets/narrator-data/all_rawis.csv`, unchanged since `2696de8` (2026-03-22),
9,267,851 bytes, SHA-256 `d87c3af6…6c11`, identical in size to Kaggle's `all_rawis.csv` in
`fahd09/hadith-narrators` (2018-08-20). Kaggle: "I only scraped this database [muslimscholars.info] with a
Python script plus very minimal cleanup", labelled "CC0: Public Domain"
([evidence](./evidence/kaggle-fahd09-hadith-narrators-2026-11-21.txt)). The project card said provenance was
unknown and pointed at our own repository.

**Terms.** muslimscholars.info carries `<META NAME="copyright" CONTENT="All contents copyright of Arees
Institute, registered in the United States">` and no licence ([evidence](./evidence/muslimscholars-home-2026-11-21.txt)).

| Component | Status | Why |
| --- | --- | --- |
| Names, relations, dates, places (facts) | unclear | Facts are generally free in the US, the Institute's base; selection and arrangement of a 24,326-person database may be protected, and the scrape copied it whole |
| `grade` column, biographies, book lists | permission_needed | Editorial content of the Arees database; ask Arees Institute (request F) |
| Use as an internal matching index | unclear | Lower exposure: not displayed. The design already hides lexicon biography on public pages (data-architecture §14 q4) |

### 6. OpenITI rijal texts (chain reconciliation inputs)

Six texts in `datasets/sources/external/` (al-Najashi; al-Tusi's *Rijal*, *Fihrist*, *Ikhtiyar*; Ibn Hajar's
*Taqrib*; al-Mizzi's *Tahdhib al-Kamal*), fetched 2026-11-21 from repository `master`; licence as section 3.
**Status: clear_with_conditions** (CC BY-NC-SA 4.0). One exception: the *Ikhtiyar* file keeps a modern editor's
introduction and endnotes, tagged `EDITOR` in OpenITI's own metadata; exclude that content from anything derived.
The owner has already accepted that material derived from these texts is non-commercial and share-alike
(RUNBOOK, decisions).

---

## What the owner needs to decide

1. **Confirm the site is, and will stay, non-commercial** in the CC sense: no advertising, paywall or sale of
   data. Donations are generally consistent with non-commercial use. This unlocks the OpenITI works, the rijal
   material, and every export that contains them.
2. **Approve clearing the 20 classical Thaqalayn works for Arabic** under CC BY 4.0, conditional on the
   attribution notice being live, with `english_policy = reviewed_only`.
3. **Approve clearing the three OpenITI works** under CC BY-NC-SA 4.0, conditional on the notice being live.
4. **Adopt the interim rule for English** (untangling-plan step 2): no reviewer marks provider English as
   verified for a work whose English rights are not cleared. Decide whether to ask for a schema value that
   expresses "no provider English" per work.
5. **Choose the route for the six books:** request permission from sunnah.com and the translation publishers,
   or rebase the Arabic on OpenITI and translate it ourselves, or both in parallel. Until then they stay
   `pending`.
6. **Choose the route for the four Pure Canon works:** permission from NabiMuhammad.com, or rebase on OpenITI.
   Record how the workbook was obtained, if the owner knows.
7. **Decide the scope of grading display:** al-Majlisi's grades with citation now; Bihbudi and Muhsini only after
   Thaqalayn answers.
8. **Narrator lexicon:** keep it internal (as designed) and ask Arees Institute, or replace public narrator data
   with the CC BY-NC-SA rijal texts over time.
9. **Send the requests below** (they go out under the owner's name; nothing has been sent).

## Requests to send

Each draft is ready to send; fill the bracketed fields. They name the project but no personal details beyond
what the owner chooses to sign with.

### A. sunnah.com: Arabic and structure of the six books

To: open an issue at https://github.com/sunnah-com/api/issues/new?template=request-for-api-access.md, or use the
Contact link on sunnah.com.

> Subject: Permission request: non-commercial scholarly archive using Arabic text of the six books
>
> Assalamu alaykum,
>
> I run Shura wa Istehsan, an open, non-commercial scholarly archive of hadith across four traditions. In 2026 we
> took an old public dataset (Kaggle "fahd09/hadith-dataset", 2018) as our starting copy of the six books. We have
> since found that its text was scraped, via qaalarasulallah.com, from sunnah.com. We have read your About page,
> §8, and we do not want to republish whole collections without your agreement.
>
> We are asking for:
> 1. Permission to display, with a link back to each hadith on sunnah.com, the Arabic text and reference numbers
>    of Sahih al-Bukhari, Sahih Muslim, Sunan Abi Dawud, Jami' al-Tirmidhi, Sunan al-Nasa'i and Sunan Ibn Majah
>    on a public non-commercial website, and to derive chain-of-narrator data from it;
> 2. If you prefer, an API key or an approved offline snapshot, so that our copy matches your checked text;
> 3. The attribution wording you would like us to display.
>
> We understand that the English translations belong to their translators and publishers. We will ask them
> separately; could you tell us which printed edition and publisher each collection's English comes from?
>
> We will not use the data commercially and will remove it on request.
>
> [Name], Shura wa Istehsan, [contact]

### B. Publishers of the K6 English translations

To: the publisher of each printed translation, once sunnah.com (or the books' imprint pages) confirm which. As
far as the evidence shows: Muhammad Muhsin Khan (Bukhari), Abdul Hamid Siddiqui (Muslim), Ahmad Hasan (Abu
Dawud), and the Darussalam English editions of Tirmidhi, Nasa'i and Ibn Majah. Publisher identities are not
verified here.

> Subject: Permission request: English translation of [collection] in a non-commercial hadith archive
>
> Dear [publisher],
>
> Shura wa Istehsan is an open, non-commercial scholarly archive that shows each hadith in Arabic with an
> English rendering, its chain of narrators, and its source. We would like to display your English translation of
> [collection], translated by [translator], alongside the Arabic, with the credit line "[translator],
> [title], [publisher], [year]. Used with permission."
>
> May we display it on a public non-commercial website? If you allow it only for a part of the text, or only with
> conditions (a link, a notice, no download), please tell us which. If you do not allow it, we will not show it.
>
> [Name], Shura wa Istehsan, [contact]

### C. NabiMuhammad.com: Pure Canon Authentica

To: the contact form at https://nabimuhammad.com/contact.php.

> Subject: Permission to use the Hadith Pure Canon Authentica data in a non-commercial archive
>
> Assalamu alaykum Shaykh Ahmad,
>
> Shura wa Istehsan is an open, non-commercial scholarly archive of hadith across four traditions. We hold a copy
> of your Hadith-Pure-Canon-Authentica workbook and would like to use the Arabic text of four collections from it:
> Musnad Ahmad, Muwatta' Malik, Sunan al-Darimi, and the collection labelled "شافعي".
>
> Your site says "All Rights Reserved", so we ask before publishing:
> 1. May we display that Arabic text on a public non-commercial website, with attribution to NabiMuhammad.com and
>    a link back, and derive chain-of-narrator data from it?
> 2. May we publish our own English machine translations of it, clearly labelled as ours?
> 3. Which work does the label "شافعي" denote, and from which printed edition?
> 4. What credit line would you like?
>
> [Name], Shura wa Istehsan, [contact]

### D. Thaqalayn: scope of the CC BY 4.0 grant

To: info@thaqalayn.com.

> Subject: Which translations and gradings does your CC BY 4.0 licence cover?
>
> Assalamu alaykum,
>
> Thank you for licensing the Thaqalayn library under CC BY 4.0 (Terms of Use, 1 October 2026). Shura wa Istehsan,
> a non-commercial scholarly archive, uses Thaqalayn's text of 21 works, obtained in April 2026 through the
> ThaqalaynAPI project, and will credit Thaqalayn, each author and each translator as your terms ask.
>
> Your terms say the grant "covers the rights held by Stichting Thaqalayn". Could you tell us:
> 1. For which books Thaqalayn holds, or may sublicense, the English translation? (We list them: al-Kafi —
>    Muhammad Sarwar; Man La Yahduruhu al-Faqih — Bab Ul Qaim Publications; Nahj al-Balagha — Sayed Ali Raza;
>    al-Amali (Saduq) — Bilal Muhammad; al-Amali (Mufid) — Mulla Asgharali M M Jaffer; al-Khisal and 'Uyun Akhbar
>    al-Rida — Dr. Ali Peiravi; Kitab al-Ghayba (Tusi) and Kamal al-Din — Sayyid Athar Husain S. H. Rizvi; Kitab
>    al-Ghayba (Nu'mani) — Abdullah al-Shahin; Thawab al-A'mal — Sayed Athar Husain Rizvi & Sayed Maqsood Athar;
>    Ma'ani al-Akhbar — Basel Kadem; Kamil al-Ziyarat — Sayyid Mohsen al-Husayni al-Milani; al-Tawhid — Sayed Ali
>    Raza Rizvi; Mu'jam al-Ahadith al-Mu'tabara — Ammaar Muslim; Kitab al-Zuhd — Shaykh Tahir Ridha Jaffer;
>    Kitab al-Du'afa — Tashayyu; Kitab al-Mu'min — Muhajir b. Ali; Sifat al-Shi'a and Fada'il al-Shi'a — Badr
>    Shahin; Risalat al-Huquq — William C. Chittick.)
> 2. Does the licence cover the Arabic text and arrangement of Shaykh Muhammad Asif Muhsini's Mu'jam al-Ahadith
>    al-Mu'tabara? If not, whom should we ask?
> 3. Does it cover the gradings of Shaykh Bihbudi and Shaykh Muhsini that you publish?
> 4. For translations it does not cover, whom should we contact?
>
> [Name], Shura wa Istehsan, [contact]

### E. Risalat al-Huquq English

To: whoever Thaqalayn names in reply to D, question 4 (expected: the publisher of *The Psalms of Islam*, or the
translator). Use draft B with: collection "Risalat al-Huquq (The Treatise on Rights)", translator "William C.
Chittick".

### F. Arees Institute: muslimscholars.info narrator database

To: the contact address on muslimscholars.info (not captured; the home page is a frameset).

> Subject: Permission request: narrator data from the Muslim Scholars Database
>
> Dear Arees Institute,
>
> Shura wa Istehsan is a non-commercial scholarly archive of hadith and their chains of narrators. We hold a copy of
> narrator records from your Muslim Scholars Database, taken from a 2018 public dataset (Kaggle
> "fahd09/hadith-narrators") whose uploader scraped your site. We would like to:
> 1. use the names, teacher/student links and dates to recognise narrators in chains; and
> 2. show some of those fields on public narrator pages, credited to your database with a link.
>
> May we? If you prefer that we use only (1), or not at all, we will follow that.
>
> [Name], Shura wa Istehsan, [contact]

## Attribution and licence notices the site must display

The site must show these on every page that displays the material (a per-hadith source line plus a site-wide
credits page), and in every export.

**Thaqalayn works (12–25, 27–32), CC BY 4.0.** Per hadith or per book page:

> Source: Thaqalayn (Stichting Thaqalayn) — [link to the hadith on thaqalayn.com]. Arabic text of *[work]* by
> [author]. Translation: [translator], where shown. CC BY 4.0 — https://creativecommons.org/licenses/by/4.0/.
> Changes: text normalized and chains of narrators extracted by Shura wa Istehsan. Thaqalayn does not endorse
> this site.

The translator credit is required whenever that work's English is shown. "Changes" must be true for the page:
say "none" where we changed nothing.

**OpenITI works (11, 33, 34) and rijal texts, CC BY-NC-SA 4.0.** Per hadith or per work page:

> Arabic text: *[work]*, OpenITI version [URI, e.g. 0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1], from OpenITI:
> a Machine-Readable Corpus of Islamicate Texts, release 2025.1.9, https://doi.org/10.5281/zenodo.17767721,
> originally from [upstream library named in the text's metadata, e.g. al-Maktaba al-Shamila al-Zaydiyya].
> Licensed CC BY-NC-SA 4.0 — https://creativecommons.org/licenses/by-nc-sa/4.0/. Changes: parsed into reports,
> page markers moved out of the text, Unicode normalized; English is a machine translation by Shura wa Istehsan,
> released under the same licence.

On narrator pages and in any narrator or chain table derived from the rijal texts:

> Narrator information derived from [al-Najashi, *Rijal* / …], OpenITI version [URI], release 2025.1.9,
> https://doi.org/10.5281/zenodo.17767721. CC BY-NC-SA 4.0. This derived material is offered under the same
> licence: non-commercial use only, with attribution, and adaptations must be shared alike.

**Consequence of BY-NC-SA.** Material derived from OpenITI texts (parsed reports, chain and narrator tables,
machine translations, embeddings published as data) is itself CC BY-NC-SA 4.0. It may never be sold, placed
behind a paywall, or used to support advertising, and anyone reusing it must keep the same licence. Pages that
show such material alongside Thaqalayn material are a collection, not one adaptation, so the Thaqalayn material
does not become NC-SA; but a single export or table that merges them must carry the stricter terms. The
database dump, if ever published, must be NC-SA as a whole if it contains any OpenITI-derived row.

**Six books and Pure Canon.** Nothing to display: they stay unpublished until a request succeeds or the text is
replaced. If sunnah.com agrees, use its wording; as a placeholder: "Arabic text courtesy of sunnah.com, [link to
the hadith]."

**Machine translations (any work).** "Machine translation by Shura wa Istehsan ([model]), not reviewed" for
reviewer mode; once reviewed, "Translated by Shura wa Istehsan from the Arabic; reviewed by [curator]."
