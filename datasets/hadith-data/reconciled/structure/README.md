# structure (report numbering, volume, book, chapter, source order, edition locators)

Sidecars keyed by the stable report id (`record_id`; `hadith_id` = `hadith:` + `record_id`, the production `hadiths.id`).
Nothing existing is modified, nothing here is a release input, every row is `review_state: unreviewed`. Load
specification for the schema owner: `LOAD_SPEC.md`.

## Build (repository root, about 3 minutes, deterministic: two builds gave identical output bytes)

```
python -B datasets/hadith-data/reconciled/structure/build_structure_sidecars.py --production-dump <csv>
cd datasets/hadith-data/reconciled/structure && python -B -m unittest test_structure_logic     # 23 tests
```

`<csv>` is the read-only production dump (SELECT only; connection string never printed):
`\copy (select h.id, h.record_id, c.source_work_id, h.collection_id, h.hadith_no, h.volume, h.chapter_no, h.chapter_title,
h.category, h.url, h.page_ref, h.provider_hadith_id, h.source_record_id, b.number as book_number, b.volume as book_volume,
b.provider_file_id, (h.retired_at is not null) as retired from hadiths h join collections c on c.id=h.collection_id left join
books b on b.id=h.book_id order by h.id) to 'prod_hadiths.csv' csv header`. Without it the "before" columns are omitted.
Cross-check done 2026-11-21: all 99,283 production rows equal the corpus on `hadith_no`, `volume`, `chapter_no`, `url`,
`page_ref` (0 differences, 0 missing). Inputs are opened read-only; nothing from a downloaded directory is executed.

## Files

| File | Rows | Contents |
| --- | ---: | --- |
| `report_structure.jsonl.gz`, `report_structure_flat.csv.gz` | 99,283 | one row per report: `source_order`, volume, book, chapter, number, scheme, reference key/text/uniqueness, section (Ahmad), edition locator, `loaded_*` values where the source disagrees with what is loaded, flags |
| `reference_provenance.jsonl.gz` | 568,069 | one record per emitted reference field (and per external claim): the checkable source shape, see Citation standard |
| `provenance_validation.json` | | pass counts by work, by source code, by field group; every input file with its SHA-256; registry codes used |
| `structure_nodes.jsonl.gz` | 8,857 | distinct volumes, books (kitab) and chapters (bab) per work with titles, for the `books` / `chapters` tables |
| `external_locator_claims.jsonl.gz` | 84,271 | hadith-kg and Riwayat locators for matched reports (number, page, chapter, edition as hadith-kg names it), labelled as that dataset's claim |
| `structure_disagreements.jsonl.gz` | 69,925 | the claims that differ from ours |
| `numbering_audit.json`, `numbering_audit.csv.gz` | 34 works | the audit below plus the measured evidence behind each Thaqalayn scheme |
| `structure.manifest.json` | | input and code SHA-256, output hashes and counts |

Inputs (SHA-256): corpus `development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz` `feeeb38d…003a17`;
`all_hadiths_clean.csv.gz` `5d0919b3…dfef`; `archive/datasets.7z` `2822d053…df378`, member `all_hadiths_clean.csv`
`a6800edb…50db15`; `pure_canon.jsonl` `0cb5ec01…550ac`; `Hadith-Pure-Canon-Authentica.xlsx` `2189b0a5…cca0`;
`jamic_sahih_ibadiyya.txt` `074e0b13…8b08`; `musnad_zaydiyya_052.mARkdown` `d5aa2db2…e5919ae0235`;
`external_report_crosswalk.jsonl.gz` `9b63c459…ffc76`; `hadith-kg.db` `d5280843…15a6`; Riwayat `hadith_master.db`
`278e674e…61133b` (hashed here, equals its README); the 33 Thaqalayn `v2_books/*.json` hashes are in
`provenance_validation.json` (full 64-digit values everywhere). Code: `structure_logic.py`, `structure_provenance.py`,
`build_structure_sidecars.py`.

## Citation standard (owner, 2026-11-21)

Every reference field a row emits has a record in `reference_provenance.jsonl.gz` with the same keys: `claim_by`
(`project_source_file` or `external_dataset`), `kind` (`source_value` or `derived`, derived ones carry `derivation`),
`source_code` / `source_name` / `licence` (from `src/lib/sources/registry.ts`, read by `structure_provenance.load_registry`),
`source_file`, `source_sha256` (must be the hash of an input file), `source_version` (required for external),
`source_record_id` (provider id, line, pc id, external id), `source_field` (field or markup), `edition` (as the source
names it, required for every `edition_*` field). `validate_record` is the gate: a field whose record fails is set to
null and the row flagged `withdrawn_unsourced:<group>`. Codes used: THQ (Thaqalayn, CC BY 4.0), OITI (OpenITI, CC BY-NC-SA
4.0), SUN (K6 / sunnah.com, owner permission), NMC (Pure Canon, owner permission), HKG (hadith-kg, CC BY 4.0), RWY
(Riwayat, CC0 layer). No new code is needed: project-computed values (ranks, Ahmad sections) are `derived` and cite the
source field they come from.

Result: **568,069 of 568,069 records pass; 84,271 of 84,271 external claims pass.** By source: THQ 227,255, SUN 103,221,
NMC 108,763, OITI 11,303, HKG 66,512, RWY 51,015. By field group: source_order 99,283, number 124,045, book 69,291, chapter
34,886, volume 34,925 (+2 withdrawn), hadith_in_chapter 33,190, section 47,119, edition 7,803, external 117,527. Withdrawn
because the source could not be checked: 14 Zaydi chapter titles (not found as a heading line) and 2 Ibadi volumes (no page
marker yet). **Zaydi and Rida numbers are not emitted at all**: the OpenITI text numbers no hadith (the loaded 1..699 is the
parser's sequence), so those 733 reports stay on the stable id. Ibadi kitab numbers and Zaydi/Rida book and chapter
numbers are likewise not emitted (the source gives titles only). By work the pass counts are in `provenance_validation.json`.

## Per-work table

"Stored unique" = reports whose loaded `hadith_no` is unique in the work. "Site today" = reports whose `reference.ts`
string is unique and is a real reference (not the record-id fallback). "After" = reports whose emitted `reference_key`
is unique in the work. Book/chapter = reports with a kitab level / a source bab. Page / edition = local page markers /
edition text. kg page = reports with a hadith-kg page claim (separate file).

| Work | Reports | Scheme | Stored unique | Site today | After | Sharing | No ref | Book / bab | Page / edition | kg page |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |
| musnad-rabi | 1,004 | continuous_work | 1,000 | 1,002 | 1,002 | 2 | 0 | 927 / 992 | 1,001 / 1,004 | 407 |
| al-amali-mufid | 387 | unit_in_book | 31 | 387 | 387 | 0 | 0 | 387 / 387 | 0 / 0 | 0 |
| al-amali-saduq | 1,082 | per_chapter | 6 | 1,082 | 1,082 | 0 | 0 | 1,082 / 1,082 | 0 / 0 | 0 |
| al-kafi | 14,245 | per_chapter | 358 | 14,245 | 14,245 | 0 | 0 | 14,245 / 14,245 | 0 / 0 | 0 |
| al-khisal | 1,282 | per_chapter | 81 | 1,282 | 1,282 | 0 | 0 | 1,282 / 1,282 | 0 / 0 | 0 |
| al-tawhid-saduq | 575 | per_chapter | 12 | 575 | 575 | 0 | 0 | 575 / 575 | 0 / 0 | 0 |
| fadail-al-shia | 45 | per_chapter | 45 | 45 | 45 | 0 | 0 | 45 / 45 | 0 / 0 | 0 |
| kamal-al-din | 659 | per_chapter | 9 | 609 | 625 | 18 | 0 | 659 / 659 | 0 / 0 | 0 |
| kamil-al-ziyarat | 750 | per_chapter | 11 | 750 | 750 | 0 | 0 | 750 / 750 | 0 / 0 | 0 |
| kitab-al-duafa | 226 | per_chapter | 31 | 226 | 226 | 0 | 0 | 226 / 226 | 0 / 0 | 0 |
| kitab-al-ghayba-numani | 468 | per_chapter | 0 | 468 | 468 | 0 | 0 | 468 / 468 | 0 / 0 | 0 |
| kitab-al-ghayba-tusi | 774 | continuous_work | 6 | 774 | 774 | 0 | 0 | 774 / 774 | 0 / 0 | 0 |
| kitab-al-mumin | 201 | continuous_work | 0 | 201 | 201 | 0 | 0 | 201 / 201 | 0 / 0 | 0 |
| kitab-al-zuhd | 290 | per_chapter | 0 | 290 | 290 | 0 | 0 | 290 / 290 | 0 / 0 | 0 |
| maani-al-akhbar | 829 | per_chapter | 322 | 829 | 829 | 0 | 0 | 829 / 829 | 0 / 0 | 0 |
| man-la-yahduruhu-al-faqih | 6,382 | continuous_work | 209 | 6,220 | 6,376 | 4 | 0 | 6,382 / 6,382 | 0 / 0 | 0 |
| mujam-al-ahadith-al-mutabara | 555 | per_chapter | 65 | 555 | 555 | 0 | 0 | 555 / 555 | 0 / 0 | 0 |
| nahj-al-balagha | 2,260 | unit_in_book | 183 | 2,260 | 2,260 | 0 | 0 | 2,260 / 2,260 | 0 / 0 | 0 |
| risalat-al-huquq | 49 | per_chapter | 1 | 49 | 49 | 0 | 0 | 49 / 49 | 0 / 0 | 0 |
| sahifat-al-imam-ali-al-rida | 35 | None | 35 | 35 | 0 | 0 | 35 | 35 / 35 | 35 / 35 | 0 |
| sifat-al-shia | 71 | per_chapter | 71 | 71 | 71 | 0 | 0 | 71 / 71 | 0 / 0 | 0 |
| thawab-al-amal | 1,106 | per_chapter | 272 | 1,106 | 1,106 | 0 | 0 | 1,106 / 1,106 | 0 / 0 | 0 |
| uyun-akhbar-al-rida | 954 | per_chapter | 4 | 954 | 954 | 0 | 0 | 954 / 954 | 0 / 0 | 0 |
| abudawud | 5,260 | continuous_work | 5,255 | 5,255 | 5,255 | 0 | 5 | 5,260 / 0 | 0 / 0 | 3,714 |
| ahmad | 23,529 | per_section | 1,261 | 1,251 | 22,900 | 165 | 464 | 0 / 0 | 0 / 0 | 6,675 |
| bukhari | 7,370 | continuous_work | 7,273 | 7,335 | 7,335 | 35 | 0 | 7,370 / 0 | 0 / 0 | 5,451 |
| darimi | 2,477 | continuous_work | 2,475 | 2,475 | 2,475 | 2 | 0 | 0 / 0 | 0 / 2,477 | 633 |
| ibnmajah | 4,227 | continuous_work | 3,739 | 4,221 | 4,221 | 6 | 0 | 4,227 / 0 | 0 / 0 | 3,575 |
| muslim | 7,596 | continuous_work | 6,643 | 7,057 | 7,057 | 513 | 26 | 7,596 / 0 | 0 / 0 | 4,305 |
| muwatta | 1,855 | continuous_work | 1,855 | 1,790 | 1,855 | 0 | 0 | 0 / 0 | 0 / 1,855 | 405 |
| nasai | 5,774 | continuous_work | 5,678 | 5,696 | 5,702 | 6 | 66 | 5,774 / 0 | 0 / 0 | 5,301 |
| shafii | 2,054 | continuous_work | 0 | 0 | 0 | 0 | 2,054 | 0 / 0 | 0 / 0 | 228 |
| tirmidhi | 4,214 | continuous_work | 3,029 | 4,078 | 4,088 | 121 | 5 | 4,214 / 0 | 0 / 0 | 2,500 |
| musnad-zayd | 698 | None | 698 | 698 | 0 | 0 | 698 | 698 / 669 | 698 / 698 | 62 |

Sources of each column: Thaqalayn rows from `v2_books/<n>.json` (`volume`; `categoryId`+`category`; `chapterInCategoryId`+`chapter`;
URL last segment; leading numeral of `arabicText`/`englishText`; `id` for order). K6 from the original CSV in
`archive/datasets.7z` (`chapter_no`/`chapter` = kitab, `hadith_no`, row position). Pure Canon from `pure_canon.jsonl` and
workbook columns E, F, M, N. Ibadi from the OpenITI text (`# n)`, `# [n] باب`, `# كتاب`, `PageV`); Zaydi/Rida headings and
page markers from the OpenITI text.

## Findings

**Thaqalayn (33,225 reports).** Verified: the loaded `hadith_no` is `chapterInCategoryId` for 33,225 of 33,225 reports.
Al-Kafi: 14,245 rows, 9,278 distinct URLs, 14,245 distinct (volume, URL); 10,889 of the 11,034 reports whose Arabic opens with
a numeral disagree with the stored number. The brief's "every Al-Amali reports number 1" does not hold for the stored number
(Mufid 42 of 387, Saduq 7 of 1,082 are 1); it holds for the URL's last segment in Mufid (387 of 387), because in that work the
provider's `chapterInCategoryId` is the hadith's number inside its assembly (Saduq's last segment is 1 for 97 reports, one per
assembly start). The provider path (volume, book=`categoryId`, chapter=`chapterInCategoryId`, URL segment) is unique for
all but 22 reports (Faqih 4 after resolving 156 collisions by the printed number; Kamal al-Din 18). The provider's number
semantics differ per work, so each work's scheme was fixed from measured evidence (`numbering_audit.json`
`_thaqalayn_measured_evidence`: coverage and uniqueness of URL segment, `chapterInCategoryId` and both printed numerals in
the scopes work/volume/book/chapter): `per_chapter` (default); `unit_in_book` for Nahj al-Balagha (sermon/letter/saying
number = `chapterInCategoryId`, rows sharing it are fragments) and Amali Mufid; `continuous_work` for Faqih (Arabic
numeral, 92 % coverage, 99 % unique), Mu'min (95 %) and Ghayba of Tusi (64 % only; the others are absent, not guessed).
Provider text carries no printed edition or page: no edition locator for any Imami work except Rida.

**Six books.** The original K6 file has no bab, no volume, no page: `chapter` is the kitab. hadith-kg and Riwayat have **no
chapter structure either** (hadith-kg tables: books, hadiths with `no_inbook` and `page_no`, `topics` is a subject taxonomy
keyed by meaning group; Riwayat `hadith` has `book` and `number` only), so **Sunni babs recovered: 0 of 34,441, and no
heading was invented**. What they give is `page_no` and the edition hadith-kg names (for example Bukhari: دار ابن كثير ,
اليمامة, بيروت, الثالثة; page 1..2318, no volume): page claims exist for 3,714 / 5,451 / 3,575 / 4,305 / 5,301 / 2,500
reports (Abu Dawud, Bukhari, Ibn Majah, Muslim, Nasa'i, Tirmidhi), in `external_locator_claims`, never in our fields.
Numbers: K6 numbering is sunnah.com's; hadith-kg's `no_inbook` is its own sequential count (agrees with K6 for 3 of 5,451
Bukhari reports, offsets vary), so the datasets use different schemes and every difference is listed, not applied.
K6 cells: 5 + 26 zeros (Abu Dawud, Muslim) unnumbered, 66 + 5 words `Grade`/`b` (Nasa'i, Tirmidhi) unnumbered, 16 letter suffixes
(`3604b`) parsed. Reports that still share (kitab, number): Muslim 513, Tirmidhi 121, Bukhari 35, Nasa'i 6, Ibn Majah 6.

**Pure Canon.** `shelf_no` (workbook column M) is the work's own position: unique, continuous inside each work
(Muwatta 2..1889, Ahmad 1890..29390, Darimi 29392..32291, Shafi'i 112924..115216) and the only order key that reproduces
source order; alphabetical `pc_` ids do not. Muwatta and Darimi: continuous numbers, edition named by the file's header row
(Muwatta: دار إحياء التراث العربي, مراجعة محمد فؤاد عبد الباقي, مصر, 2 volumes; Darimi: دار الكتاب العربي, زمرلي والعلمي, بيروت,
1987/1407, 2 volumes). Ahmad: numbers restart per section (3,616 distinct over 23,529); the `1]` cell (463 rows) is a section
opener, not hadith 1 (next row is 1), so no number is emitted for it; `1×2` marks a second series, `8.1999999999999993` is a
spreadsheet float for 8.2; 9 workbook numbers differ from `pure_canon.jsonl` only in such float noise. Sections are derived
(961, from restarts), citable as (section, number): 22,900 unique, 165 share, 464 none. Column F names a companion, but
only 684 of 961 sections have one label on 95 % of rows, so it is carried as a label, not as the section heading.
Musnad al-Shafi'i has no number anywhere (workbook column N empty): not citable by number.

**OpenITI.** Ibadi: every report binds to its numbered source line (1,004 of 1,004; source line `# 1مكرر)` is `rabi_0001b`;
source number 387 occurs twice, so 2 reports share). Source order = line number (equals `hadith_id` order for all
1,004). Disagreements with what is loaded: **53 reports have a loaded chapter that differs from the source heading (32 by number, the rest by title); the largest run, reports 588-607, sits under the source heading `# [35] باب` (no title) but is loaded in chapter 34 with chapter 34's title**; bab numbers restart in every kitab (so a chapter alone is not a locator); 254 loaded
page refs differ from the start page (247 one page late, 5 two, 1 four, 1 before the first marker; start page by source = the marker in
force at the numbered line; both kept: `edition_page` / `loaded_edition_page`). Ibadi edition: دار الفتح للطباعة والنشر،
بيروت، ومكتبة الاستقامة، روي، مسقط, and the header asserts pagination matches the print. Zaydi / Rida: edition دار مكتبة
الحياة، بيروت، 1966; page markers are not asserted to match print and have the same one-page-late behaviour (flagged).

## Disagreements between sources (examples)

- Riwayat's Thaqalayn locator versus our provider path (hadith number always agrees; chapter differs): Amali Saduq 393 of
  415 (`thaqalayn:0029b9eb…` Riwayat chapter 15, ours 14), Sifat al-Shi'a 24 of 24 (Riwayat 35, ours 54), Fada'il 28 of 29,
  Ma'ani al-Akhbar 184 of 361 (Riwayat 253, ours 255), Mujam 157 of 438, Faqih 1,269 of 3,414 chapters and 1,318 hadith
  numbers (Riwayat's locator drops the category), al-Kafi 649 chapters, 641 hadith, 1,593 volume/book. The provider JSON is a
  snapshot of the API; Riwayat's locators come from the live site, so neither is overwritten.
- hadith-kg `no_inbook` versus our numbers: Bukhari `k6:1000` ours 1027, kg 976 (page 289); Ahmad kg 6,907+ above ours;
  Muwatta kg agrees on 35 of 405. Ibadi kg is ours + 1 from the repeat marker onward (30 of 407 equal).
- Loaded vs source (Ibadi 53 chapters, 254 page refs) above.

## Works that cannot be cited by number (the page keeps the stable id)

Musnad al-Shafi'i (2,054: no number in any source); Zaydi Musnad (698) and Sahifat al-Rida (35): the text numbers nothing;
463 Ahmad opener rows and 1 more; 31 K6 zero cells and 71 K6 word cells; 277 Ghayba Tusi and 519 Faqih reports without a
printed numeral keep only the provider path. Sharing a reference (not unique): Muslim 513, Tirmidhi 121, Ahmad 165, Kamal
al-Din 18 (the rest in the table). K6 duplicates would need sunnah.com's letter suffixes, which K6 dropped.
Totals: 95,040 of 99,283 reports have a unique reference after; before, 40,658 reports had a stored number unique in their work (and that figure counts Zaydi/Rida parser sequence numbers).

## Licences

THQ CC BY 4.0 (credit Thaqalayn); OITI CC BY-NC-SA 4.0 (derived rows carry share-alike); SUN and NMC owner permission
(2026-11-21); HKG CC BY 4.0 (credit line in `src/lib/sources/registry.ts`, a change note: locators re-keyed to our ids);
RWY CC0 for its layer. The sidecars add no text.

## Deferred

K6 to Pure Canon numbering equivalence (Pure Canon's Bukhari, Muslim and others come with named editions but need a matn
match to the K6 reports); Zaydi/Rida line binding and start-page repair (needs a hadith-paragraph parse of the OpenITI
file); sunnah.com letter suffixes (needs the network, out of scope); hadith-kg `topics` as a subject label.
