# provenance-recovery

Edition, volume, page and URL information that the original sources carry and the unified CSV lacks. Edition strings are verbatim source text, marked unreviewed, and are not cited claims.

## Inputs (SHA-256)

| File | SHA-256 |
| --- | --- |
| `datasets/hadith-data/all_hadiths_unified.csv.gz` | `f8b5cebf8a379756f1f4703b46d94c5ca1186f9853e1b0ef7a5df0c8f84cc173` |
| `datasets/hadith-data/archive/sheikahmad-pure-canon/pure_canon.jsonl` | `0cb5ec01959b326c895a6063574955997067e8646c103863285403c3ba6550ac` |
| `datasets/hadith-data/curation_dispositions.jsonl` | `3ef63a35b7fa0b7ebade85245d980e2d2872292693145957713fd4c4e03ecba6` |
| `datasets/hadith-data/openiti-sources/rabi/jamic_sahih_ibadiyya.txt` | `074e0b137e7056feda4a6786d0ee272fa5bbb342e58589f8083303b470548b08` |
| `datasets/hadith-data/openiti-sources/zayd/musnad_zaydiyya_052.mARkdown` | `d5aa2db230c7add9ac37d938b5d5103d214ab111bcb66c62899c5d5919ae0235` |
| `datasets/hadith-data/shia-hadith/v2_books/*.json` (33 files) | listed in `provenance_summary.json` |

## Command (6 s, repository root)

```
python -B datasets/hadith-data/diagnostics/provenance-recovery/measure_provenance_recovery.py
```

## Files

| File | Rows | Contents |
| --- | ---: | --- |
| `edition_locator_candidates.jsonl.gz` | 1,737 | Every Ibadi (1,004), Zaydi (698) and Rida (35) report: `page_ref` split into printed volume and page, plus the OpenITI header publisher line and its header line number. 1,002 Ibadi reports have a header that asserts pagination matches the printed edition; 733 have an edition but no such assertion; 2 have no page marker |
| `pure_canon_edition_by_work.jsonl` | 8 | Edition text from Pure Canon header rows (publisher, reviser, place, year, volumes). Applies row-level to Darimi (2,477) and Muwatta (1,855) only |
| `thaqalayn_book_provenance.jsonl` | 33 | Provider file id, `bookId`, author, translator, record count per Thaqalayn book (fields the unified CSV does not carry) |
| `missing_arabic_recovery.jsonl` | 8 | The eight reports without Arabic: disposition, official reference, Pure Canon candidate text where one exists |
| `provenance_summary.json` | | Per-source locator fill counts and the numbers quoted in the report |

## Reading the numbers

- K6 Sunni reports (34,441) have no volume, page or URL in any local lineage file; the clean CSV, seven backups and the archived consolidated snapshot carry `chapter_no` only.
- Imami reports (33,190) already carry volume and a thaqalayn.net URL; the provider has no printed edition or page.
- Musnad Ahmad (23,529) and Musnad al-Shafi'i (2,054) have no edition text anywhere in the Pure Canon files.
- Of the eight reports without Arabic, two are not reports per `curation_dispositions.jsonl` (heading `9504`, split record `11205`); four have a Pure Canon candidate that needs verification; two have no local Arabic (`10049`, `23280`).
