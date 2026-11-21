# biography-verification (diagnostic only)

Rechecks the narrator lexicon's life dates, generation markers and places against authoritative rijal texts
(Ibn Hajar's *Taqrib al-Tahdhib*, al-Mizzi's *Tahdhib al-Kamal*) and the hadith-kg narrator table, and profiles the
two newly fetched open datasets (hadith-kg, Riwayat). Every output row is **unreviewed** and carries its evidence.
A link between a lexicon row and a rijal entry is a **candidate link, not an identification**. Verdicts are
attributed to the critic and work they come from, within the Sunni tradition. Competing values are kept as
separate rows; ranges and qualifiers are kept as written. Nothing here changes a canonical asset.

## Licence of these outputs

- Files derived from the OpenITI texts (`rijal_entries_*`, `lexicon_rijal_links*`, `lexicon_source_comparisons*`,
  `cited_biographical_assertion_candidates*`, `citation_candidates*`, `taqrib_verdict_candidates*`,
  `spot_check_worksheet_100.csv`, `verification_summary.json`, `works_and_editions.json`,
  `imami_authority_inputs.json`) are **CC BY-NC-SA 4.0**: attribution to OpenITI (release 2025.1.9, Zenodo
  10.5281/zenodo.17767721) and the edition named in each OpenITI header, **non-commercial use only**, derivatives
  under the same licence.
- Rows derived from hadith-kg additionally carry **CC BY 4.0** attribution: "hadith-kg by emadjumaah,
  https://huggingface.co/datasets/emadjumaah/hadith-kg (revision 8ae7e3d5), CC BY 4.0".
- `external_dataset_profile.json`, `narrator_join_*`, `report_join_*`: hadith-kg (CC BY 4.0) and Riwayat (CC0 for
  its own layer; texts inherit their sources' licences). See `datasets/sources/external/{hadith-kg,riwayat-corpus}/README.md`.

## Inputs (SHA-256, run of 2026-11-21, git HEAD `ebc18dc2`)

| Input | SHA-256 |
| --- | --- |
| `datasets/narrator-data/all_rawis.csv` (lexicon) | `d87c3af64d48b3cd585294ab5f6381536a51ff95a72a6707a7426ea483bf6c11` |
| `diagnostics/biography-recovery/biographical_assertion_candidates.jsonl` (lexicon dates/places with qualifiers) | `cca747fdc203230fd5b6b0fbe0e29d0315a8dd1f5afee494a2a2da7f3017cc0f` |
| `diagnostics/biography-recovery/narrator_assessment_candidates.jsonl` (lexicon grade labels) | `7358595959d44390e6bdc0e91fd57685c1d2fe09d0b0de443615eb3213ef6c8b` |
| OpenITI `0852IbnHajarCasqalani.TaqribTahdhib.JK000121-ara1.completed` (ed. Muhammad Awwama, Dar al-Rashid, Syria, 1406/1986) | `178d493bd150032bc64a81ed4397d7e4a828209ee690deed283c1e63cada4637` |
| OpenITI `0742Mizzi.TahdhibKamal.Shamela0003722-ara1.mARkdown` (ed. Bashar Awwad Ma'ruf, Mu'assasat al-Risala, Beirut) | `f4f26e71dd9c0c70ef09285fc0b4de8abe3fe586c0eddba19985155df175f58f` |
| OpenITI Najashi / Tusi Rijal / Tusi Fihrist | as in `datasets/sources/external/README.md` (`a34bc95d…`, `955b2b71…`, `1c4975a1…`) |
| `datasets/sources/external/hadith-kg/hadith-kg.db` | `d528084321e715006712e0e2461809a3afc9408065a1d1af90238c8b723815a6` |
| `datasets/sources/external/riwayat-corpus/hadith_master.db` | `278e674ee72ac04886059b14fe6f8e52e70797ac6c65cba08409bafc2d61133b` |
| `datasets/hadith-data/all_hadiths_unified.csv.gz` (report join) | in `external_dataset_profile.json` `header.inputs_sha256` |
| `datasets/hadith-data/regen_unified_csvs.py` (canonical name folds, imported read-only) | `310fbf58885b53700a17698c1ffcd3231f24a55ba7ea8e8c1c08b64864e78147` |

## Commands (repo root; standard library only, no network, no database server)

```
python -B datasets/hadith-data/diagnostics/biography-verification/verify_lexicon_against_rijal.py     # part B, ~30 s
python -B datasets/hadith-data/diagnostics/biography-verification/profile_external_datasets.py        # part A, ~15 min
python -B datasets/hadith-data/diagnostics/biography-verification/measure_imami_authority_inputs.py   # Imami, ~90 s
cd datasets/hadith-data/diagnostics/biography-verification && python -B -m unittest test_rijal_parsing
```

The two SQLite files are opened `mode=ro&immutable=1`; nothing from the download directories is executed.

## Modules

| File | What |
| --- | --- |
| `rijal_parsing.py` | Pure parsing: Arabic year words, death/birth clauses, tabaqa, verdict span, headword, name chain, places gazetteer |
| `rijal_sources.py` | OpenITI entry reader with page locators, canonical name key, lexicon loaders, paths |
| `verify_lexicon_against_rijal.py` | Part B: parse, link, compare, assertion candidates, worksheet, summary |
| `profile_external_datasets.py` | Part A: profiles and joins for hadith-kg and Riwayat |
| `measure_imami_authority_inputs.py` | What Najashi, Tusi and Riwayat offer for an Imami narrator authority (measurement only) |
| `test_rijal_parsing.py` | Table-driven tests on real Taqrib wordings (century rule boundary, elided tens, ages, alternatives) |

## Method (part B)

**Entries and locators.** Taqrib: 8,824 numbered entries (`### $` men, `### $$` women; the number is Awwama's
tarjama number). Tahdhib al-Kamal: 8,377 entries (Bashar Awwad's numbers). OpenITI writes `PageVxxPyyy` at the end
of each printed page, so the page of a passage is the first marker after it (`v1p413` = volume 1, page 413). Every
row keeps the passage verbatim (markup removed, characters unchanged).

**Name key.** The canonical one: `regen_unified_csvs.narrator_fold_normalize` + `strip_blessing_formulas`, then the
guarded `fold_kunya_case_forms` when `kunya_fold_allowed`, applied identically to both sides. Lexicon names come from
`_extract_arabic_name`; the 866 `registry_placeholder_reason` rows (Shykh-marked, bare one-token, kunya-only, no
Arabic) are never linked. A light letter fold (`fold_for_phrases`) is used only to find phrases such as `مات سنة`.

**Links, unique on both sides or not at all.**
- Tier A `A_full_name_key`: the lexicon key equals the entry's headword key. A Taqrib headword is the name up to the
  first verdict word, tabaqa clause or narrative word; vocalization glosses (`بفتح المثناة وسكون المعجمة`) are either
  skipped or end the headword, and both readings are indexed.
- Tier B `B_nasab_chain_plus_tokens`: the lexicon's ism-nasab chain (`X بن Y بن Z`, at least one `بن`) equals the
  entry's chain exactly, and every other lexicon token (nisba, kunya) appears in the entry's headword.
- A key held by several entries, several lexicon rows, or an entry claimed by two lexicon rows is `ambiguous`
  (candidates listed); nothing is picked. Agreement of tabaqa or death year is recorded but never used to link, so
  the agreement rates below are not circular.

**Years.** Taqrib usually omits the century. Ibn Hajar's introduction (OpenITI lines 110-115) states the rule:

> وذكرت وفاة من عرفت سنة وفاته منهم ، فإن كان من الأولى والثانية : فهم قبل المائة ، وإن كان من الثالثة إلى آخر
> الثامنة : فهم بعد المائة ، وإن كان من التاسعة إلى آخر الطبقات : فهم بعد المائتين ، ومن ندر عن ذلك بينته .

Read literally, the rule breaks at the boundaries: `عبد الله بن نمير … من كبار التاسعة مات سنة تسع وتسعين` would be
299, but he died in 199. The parser therefore picks the century whose year lies nearest the tabaqa's median death
year (medians measured on hadith-kg `rawis` with a single death year: 1: 48, 2: 77, 3: 100, 4: 121, 5: 132, 6: 136,
7: 162, 8: 188, 9: 214, 10: 241, 11: 267, 12: 292) and flags each row `century_by_author_convention` (same as the
literal rule, 2,198 alternatives) or `century_by_tabaqa_era_not_literal_rule` (158). Without a tabaqa the year stays
`century_not_stated` with its within-century value. Alternatives (`وقيل`, `أو`) are separate rows; elided parts
(`سنة إحدى أو اثنتين وعشرين` = 21 or 22; `سنة ست وتسعين وقيل سنة سبع` = 96 or 97) are inherited and flagged;
`بعد`/`قبل` give open bounds; `في حدود`, `قريبا من`, `على رأس` give circa; `بضع` gives a range; event dates (`في
خلافة عمر`) keep no year; ages (`وله`, `وقد جاوز`, `وعاش`) end the clause. Tahdhib al-Kamal statements keep the
speaker parsed from `قال X:` where present; a clause whose first word is not a date opener is flagged
`subject_may_differ` (`مات أبوه سنة …`) and excluded from comparison.

**Comparison classes** (closest pair of lexicon value and source alternative): `agree` (both exact, equal),
`consistent` (overlap where one side is a range, bound or circa), `variant_1_2_years`, `differ_3_10_years`,
`differs_by_exactly_100` (a century slip on one side), `gross_conflict` (> 10 years), `lexicon_only`, `source_only`,
`neither`, and `agree/differ_within_century_only` when the source omits the century and gives no tabaqa.

**Generation.** The lexicon's `[Nth generation]` number is compared with Ibn Hajar's tabaqa number (explicit
`من ال<ordinal>`, or a companion statement = 1).

**Places.** Lexicon place cells (English) and source places are mapped to a small gazetteer of 50 places
(`rijal_parsing.GAZETTEER`); source places are nisbas (`ال…ي`) in the headword plus explicit `نزيل/سكن X`. A nisba
is an attachment, not proof of residence, so `differ` is weak evidence; region containment (Hijaz ⊃ Medina, Makkah,
Ta'if; Iraq ⊃ Kufa, Basra, …) is labelled `consistent_by_region`, never `agree`. `الهمداني` (a Yemeni tribe),
`البخاري` and `النسائي` (compilers' nisbas in running text) are deliberately not mapped.

**Verdicts.** The span from the first of Ibn Hajar's twelve-level terms to the tabaqa clause, in folded form, with
the full verbatim passage beside it; attributed to Ibn Hajar, *Taqrib*, Sunni.

## Results (part B)

### Links (24,326 lexicon rows; 866 placeholders never linked)

| Source | Unique (tier A / B) | Ambiguous | None |
| --- | ---: | ---: | ---: |
| Taqrib al-Tahdhib | 5,404 (2,665 / 2,739) | 941 | 17,115 |
| Tahdhib al-Kamal | 4,024 (2,179 / 1,845) | 710 | 18,726 |
| Taqrib or Tahdhib (union) | 5,839 | 830 | 16,791 |
| hadith-kg `rawis` (derived database) | 7,049 (5,058 / 1,991) | 1,967 | 14,444 |

Union by lexicon generation class (unique / ambiguous / none / placeholder): companions 530 / 107 / 6,921 / 93;
followers 2,598 / 288 / 3,439 / 348; successors of followers 1,583 / 271 / 3,562 / 282; "Nth century AH" rows
1,128 / 164 / 2,858 / 141; other markers 0 / 0 / 11 / 2. Companions link least because Taqrib and Tahdhib only cover narrators of the Six Books
and the lexicon's companion names are often short forms.

### Death years

| Class | vs Taqrib | vs Tahdhib al-Kamal statements | vs hadith-kg |
| --- | ---: | ---: | ---: |
| agree | 1,171 | 522 | 813 |
| consistent (range, bound, circa) | 417 | 149 | 316 |
| variant 1-2 years | 14 | 22 | 118 |
| differ 3-10 years | 20 | 18 | 62 |
| differs by exactly 100 | 13 | 5 | 8 |
| gross conflict (> 10) | 28 | 14 | 54 |
| **agree or consistent / both have a year** | **1,588 / 1,663 (95.5%)** | **671 / 730 (91.9%)** | **1,129 / 1,371 (82.3%)** |
| within-century only (agree / differ) | 27 / 3 | 54 / 40 | |
| lexicon only / source only | 149 / 27 | 406 / 36 | 113 / 478 |

- Of the 1,588 Taqrib agreements, 289 rest on a century Ibn Hajar wrote, 1,210 on his literal rule and 89 on the
  tabaqa-era reading. 80 agreements match a later alternative (`وقيل …`), not his first.
- Tier A and tier B links agree at similar rates (A: 495 of 519 comparable, 95.4%; B: 1,093 of 1,144, 95.5%),
  which supports the tier B rule.
- Disagreements cross-checked with Tahdhib al-Kamal: of 28 gross conflicts, 6 have a Mizzi statement that also
  contradicts the lexicon and 6 have none; one variant, one 3-10-year difference and one `differs_by_exactly_100`
  have a Mizzi report equal to the lexicon value (competing reports, not lexicon errors).

### Generation, places, verdicts, birth years

- Generation vs Ibn Hajar's tabaqa: **5,128 agree / 66 differ (98.7%)**; differences are 1 tabaqa in 40 cases
  (mostly *mukhadram* men the lexicon puts in generation 1 where Ibn Hajar says `من الثانية`), 2-4 in 24, 7-8 in 2.
  Lexicon only 106, Taqrib only 91.
- Places vs Taqrib nisbas/residence: **3,195 agree, 6 consistent by region, 20 differ**; lexicon only 1,009 (Taqrib
  gives no place nisba), Taqrib only 142. Tahdhib: 2,059 / 12 / 47. hadith-kg `iqama`/`death_place`: 3,629 / 65 / 204.
- Verdicts: an Ibn Hajar verdict span for 5,163 linked narrators. Where the lexicon has a grade label, its Arabic
  term occurs in Ibn Hajar's verdict for 4,495 of 4,899 (91.8%), so the lexicon label is very likely Taqrib-derived
  (still unattributed in the lexicon).
- Birth years are rare on both sides (Taqrib 1 agreement; Tahdhib 6 agree, 5 consistent).

### What linked narrators gain

| Gain | Narrators |
| --- | ---: |
| Death year where the lexicon has none (any source) | 500 (Taqrib 20, Tahdhib 35, hadith-kg 474) |
| Birth year where the lexicon has none | 185 |
| Tabaqa number where the lexicon marker has none | 91 |
| An attributed Ibn Hajar verdict where the lexicon has no label | 264 (5,163 verdicts in total) |

## Reading: how trustworthy are the lexicon's dates and places?

- **Where it can be checked, the lexicon follows Ibn Hajar closely**: 95.5% of death years and 98.7% of generation
  numbers agree, and places almost never contradict a nisba. Only 20 linked narrators gain a death year from Taqrib,
  i.e. when Taqrib states a year, the lexicon nearly always has it. The lexicon's dates and generations were very
  likely compiled from Taqrib/Tahdhib-family sources, so agreement mostly confirms faithful transcription, not
  independent truth. Tahdhib al-Kamal, which reports several authorities, still agrees 91.9% of the time.
- **The errors are real and of identifiable kinds** (about 4.5% of comparable death years): century slips (lexicon
  123 for a ninth-tabaqa man who died 223), digit transpositions (324 for 234; 352 for 262), and one-or-two-year
  variants that are the classic competing reports (Ibn Hajar's `على الصحيح` against Mizzi's other report). Some
  conflicts are on the source side: the OpenITI Taqrib has typos (`ست عسرة` for `ست عشرة`) and at least one century
  inconsistent with the tabaqa (Makki b. Ibrahim, ninth tabaqa, `ومائة`, died 215).
- **Coverage, not accuracy, is the limit.** Only 5,839 lexicon narrators (24%) link uniquely to an authoritative
  entry; companions are mostly outside Taqrib's scope, and 16,791 rows have no exact-name entry at all.
- **Recommendation.** Dates and generation markers are reliable enough to display with a "lexicon, not yet cited"
  label, except the 61 Taqrib conflicts (gross, century or 3-10 years), which should be withheld or shown with the
  competing source value until reviewed. For linked narrators, the cited Taqrib/Tahdhib candidates should replace
  the lexicon value once reviewed. Places can be shown with the same label, but generic regions such as "Hijaz"
  (8,818 cells) carry little information.

## Files

| File | Rows | Contents |
| --- | ---: | --- |
| `rijal_entries_taqrib.jsonl.gz` | 8,824 | Taqrib entries: number, page, headwords and keys, tabaqa, verdict span, death/birth alternatives, residence phrases, nisba places, verbatim passage |
| `rijal_entries_mizzi.jsonl.gz` | 8,377 | Tahdhib al-Kamal entries: heading, keys, 6,447 death/birth clauses (1,833 entries with a full death year) with speaker, page and paragraph |
| `lexicon_rijal_links.jsonl.gz` | 72,978 | Lexicon row × source (Taqrib, Tahdhib, hadith-kg): status, tier, entry or candidate list |
| `lexicon_source_comparisons.jsonl.gz` | 16,477 | Per unique link: death year, birth year, generation, places (and verdict for Taqrib) with both values and the class |
| `cited_biographical_assertion_candidates.jsonl.gz` | 17,893 | Shaped for `biographical_assertions` (design §5.8): `narrator_id`, `predicate`, `value_text` (verbatim), `year_min`/`year_max`, `calendar`, `precision`, flags, `attributed_to`, `citation_id` + embedded citation, `quote_ar`, `review_state: candidate_only`, `reviewed: false` |
| `citation_candidates.jsonl.gz` | 13,909 | Citation rows (work, edition, entry locator, page, verbatim quote) |
| `works_and_editions.json` | 3 | Work and edition records from the OpenITI headers |
| `taqrib_verdict_candidates.jsonl.gz` | 5,163 | Ibn Hajar's verdict per linked narrator, attributed, with the lexicon label beside it |
| `spot_check_worksheet_100.csv` | 100 | Stratified sample (seed `biography-verification-v1`): lexicon value, source passage and locator, parsed value, machine comparison, blank reviewer fields |
| `verification_summary.json` | | All counts above, parse statistics, input hashes |

Assertion predicates: Taqrib death_year 2,102, tabaqah 5,285, residence 496; Tahdhib death_year 1,955, birth_year
280; hadith-kg death_year 1,849, birth_year 232, residence 5,100, death_place 594. `review_state` uses the schema
enum value `candidate_only` (the enum has no `unreviewed`); `reviewed: false` says the same in plain words.

## Part A: hadith-kg and Riwayat (`profile_external_datasets.py`)

What identifies what (full schema with row counts in `external_dataset_profile.json`):

| | hadith-kg | Riwayat |
| --- | --- | --- |
| Narrator | `rawis.id` (internal integer; 49,844 rows, 14,384 with a death year) | `narrator.id` (`N0000123`; 193,014 rows) with crosswalk `narrator_source_id` to `itq`, `chains`, `kg` (= hadith-kg `rawis.id`), `sh`, `thq`, `mids` |
| Report | `hadiths.id`; locator `books.id` + `no_inbook` (+ `page_no`); 715,790 | `hadith.id`; upstream ids in `source_ids` JSON (`kg`, `thaqalayn`); 924,787 (37,307 Shi'i) |
| Chain | `sanads.id` + ordered `sanad_rawis` (pos 0 = book author); 577,024 chains | `chain_mention` rows per (`hadith_id`, `chain_no`) ordered by `pos`; 5,677,620 mentions |

**Narrators.** Neither dataset carries a muslimscholars.info id (the origin of `scholar_indx`), so there is no
shared external id. Join = exact canonical name key (tier A only) + overlapping death year, unique on both sides.
Only 3,823 lexicon rows have a usable hijri death year, which bounds this join:

| Lexicon generation class (rows with a death year) | hadith-kg unique / ambiguous / none | Riwayat unique / ambiguous / none |
| --- | --- | --- |
| companions (787) | 51 / 0 / 734 | 125 / 6 / 654 |
| followers (962) | 220 / 0 / 734 | 431 / 19 / 504 |
| successors of followers (813) | 192 / 0 / 614 | 311 / 16 / 479 |
| "Nth century AH" (1,254) | 303 / 3 / 929 | 424 / 15 / 796 |
| total (incl. 5 other, 38 placeholders not joined) | **766 / 3 / 3,016** | **1,291 / 56 / 2,438** |

Quality: of the 644 lexicon narrators joined uniquely to both, Riwayat's own `kg` crosswalk points to the same
hadith-kg narrator in **632 and to a different one in 0** (12 have no crosswalk). The 20-row sample in the JSON shows
the same names and years on both sides. For context, name alone (no year) is unique on both sides for 5,480
lexicon rows in hadith-kg and 8,026 in Riwayat.

**Reports.** Letters-only canonical text (`narrator_normalize`, which also expands `ﷺ`); level 1 = whole text
equal; level 2 = their matn (at least 40 letters) contained in our `text_ar`, found by its last 30 letters and
verified by hash. Our corpus: 99,283 rows.

REPORT_TABLE_PLACEHOLDER

## Imami narrator authority: what the inputs offer (`measure_imami_authority_inputs.py`, measurement only)

| Work | Entries | Distinct headword keys (unique in work) | Entries with `ثقة` / `ضعيف` | Entries with a dated death |
| --- | ---: | ---: | ---: | ---: |
| al-Najashi, *Rijal* | 1,269 | 1,266 (1,265) | 532 / 44 | 22 |
| al-Tusi, *Rijal* | 6,365 | 5,856 (5,456) | 172 / 19 | 74 |
| al-Tusi, *al-Fihrist* | 910 | 884 (868) | 78 / 5 | 2 |

- Keys shared across works: 351 keys occur in two works and 28 in all three; 7,220 occur in one.
- Tusi's *Rijal* is organised by the Imam a narrator transmitted from (a tabaqa signal): companions of al-Sadiq
  3,212, of al-Baqir 466, of Ali 446, of the Prophet 430, of al-Rida 319, of al-Kazim 272, of al-Hadi 186, and 509
  who transmitted from no Imam directly.
- Najashi and Tusi give verdicts (`ثقة`, `ثقة ثقة`, `ضعيف`, `واقفي`, `غال`, `عامي`) but almost no dates: an Imami
  authority built from them would have verdicts and tabaqa, not death years.
- Riwayat Shi'i chains: 181,922 mentions, 152,163 with an asserted narrator id (134,614 of those from Thaqalayn's
  own annotation or ids on re-parsed spans), over 7,030 distinct narrators (6,024 labelled `shia`, 953
  `sunni_or_unknown`, 53 `sunni`); 649 have a death year and 806 a tabaqa; 4,174 carry a Thaqalayn crosswalk id.
  Their names equal exactly one Najashi/Tusi headword for 734 narrators (28,571 mentions), several entries for 402
  (33,351 mentions), and none for 5,894 (90,241 mentions).
- Our Imami corpus is 33,225 rows; Riwayat's Shi'i texts come from Thaqalayn as ours do (report join above).

## Not checked, and why

- Lexicon rows with no unique exact-name entry (16,791 none, 830 ambiguous): no candidate is chosen among homonyms.
- Companions outside the Six Books (most of the 6,921 unlinked companions): Taqrib and Tahdhib do not cover them;
  Ibn Hajar's *al-Isaba* or Ibn al-Athir's *Usd al-Ghaba* (OpenITI) would, and are not on disk.
- Gregorian-only lexicon dates; places outside the 50-place gazetteer; battle-site death places (Uhud, Siffin).
- Verdict spans are heuristic and folded; the verbatim passage is the evidence.
- Online sources: none were consulted; every comparison here uses texts on disk.
- Tabaqa medians come from hadith-kg (a derived database); they only choose an omitted century and every such row
  is flagged.
