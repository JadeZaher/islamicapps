# Hadith corpus and Neo4j import research — 2026-07-20

## Executive finding

The active unified CSV has 99,283 rows and 68,515 rows with some English text (69.0098%). The archived unified snapshot contains 29,888 translations that can be recovered into the active rows by exact Arabic-text matching, raising projected English coverage to 98,403 / 99,283 (99.1136%). The remaining 880 gaps are 853 rows in the six Sunnah.com collections and 27 rows in Musnad al-Shafi'i.

"Complete translation" must mean more than a non-empty English cell. Each translation should retain the source URL or snapshot, source edition/reference, translator or generation method, model/prompt/version when machine-generated, retrieval date, and human-review state. OpenITI's upstream texts are Arabic-only, and the current unified format loses Thaqalayn's named translator metadata.

## Active corpus profile

Source of truth inspected: `datasets/hadith-data/all_hadiths_unified.csv`.

| Tradition | Rows | Arabic present | English present (`text_en` or `matn_en`) | English missing |
| --- | ---: | ---: | ---: | ---: |
| Sunni | 64,356 | 64,348 | 33,588 | 30,768 |
| Imami | 33,225 | 33,225 | 33,225 | 0 |
| Ibadi | 1,004 | 1,004 | 1,004 | 0 |
| Zaydi | 698 | 698 | 698 | 0 |
| **Total** | **99,283** | **99,275** | **68,515** | **30,768** |

The four archived workbooks each contain 97,550 data rows, so none is row-authoritative relative to the 99,283-row CSV. They remain valuable as translation-recovery assets.

## Translation recovery already available locally

Archive inspected: `datasets/hadith-data/archive/unified-snapshots/unified_hadith_consolidated.csv`.

| Active source | Active untranslated | Exact Arabic matches to translated archive rows | Still missing after recovery |
| --- | ---: | ---: | ---: |
| Musnad Ahmad | 23,529 | 23,529 | 0 |
| Sunan al-Darimi | 2,477 | 2,477 | 0 |
| Muwatta' Malik | 1,855 | 1,855 | 0 |
| Musnad al-Shafi'i | 2,054 | 2,027 | 27 |
| **Total** | **29,915** | **29,888** | **27** |

Do not recover these by `source + hadith_number`: archive numbering is non-unique or blank for important sources. Use `source + normalized exact Arabic hash`, detect duplicate hashes, and retain the archive row/snapshot as lineage. The archive contains one extra Darimi and one extra Muwatta row; they should be reconciled, not silently appended.

The remaining six-collection gaps are Bukhari 177, Muslim 354, Tirmidhi 186, Nasa'i 8, Ibn Majah 128, and Abu Dawud 0 (853 total). These should be source-recovered against the cited Sunnah.com edition/reference and Arabic text, with generated translation only as an explicitly labeled fallback.

## Authoritative-source checks

### Sunnah.com collections

The official collection pages expose collection-specific counts/ranges that do not map 1:1 to this dataset's row numbering. Examples: Bukhari advertises more than 7,500 narrations with repetitions and its page range reaches 7,563; Muslim advertises roughly 7,500 with repetitions while its main reference numbering reaches 3,033; Tirmidhi describes roughly 4,400 with repetitions while its displayed reference range reaches 3,956. Abu Dawud reaches 5,274, Nasa'i 5,758, and Ibn Majah 4,341. Therefore a bare integer `hadith_no` is not a cross-edition identity.

Primary pages:

- https://sunnah.com/bukhari
- https://sunnah.com/muslim
- https://sunnah.com/abudawud
- https://sunnah.com/tirmidhi
- https://sunnah.com/nasai
- https://sunnah.com/ibnmajah

The pages are bilingual source surfaces; Bukhari credits Dr. Muhammad Muhsin Khan and Muslim credits Abdul Hamid Siddiqui. Preserve translator, collection edition, book/chapter, displayed reference, and source URL. Do not use row-count equality as completeness proof.

### Thaqalayn API / Imami corpus

The project README states that `ThaqalaynData` is outdated and no longer maintained. Its static manifest advertises 33,190 rows; the live official `/api/v2/allbooks` manifest advertises 33,191. The sole row-count delta is `Kitab-al-Ghayba-Numani` (static max 468, live max 469). The live manifest also fills a previously blank translator for `Kamal-al-Din-wa-Tamam-al-Nima-Saduq` (`Sayyid Athar Husain S. H. Rizvi`). The active dataset's 33,190 Thaqalayn rows therefore match the stale static snapshot and are one row behind the live manifest.

Primary sources:

- https://github.com/MohammedArab1/ThaqalaynAPI
- https://www.thaqalayn-api.net/api/v2/allbooks

Pin a dated live API snapshot, ingest the missing row only after identity/reconciliation checks, and preserve every volume's translator field in the canonical schema.

### OpenITI / Zaydi and Ibadi sources

Running the repository's own parser against exact current official OpenITI source texts yielded 699 Zaydi Musnad rows and 1,004 Ibadi Jami' rows. The active unified CSV contains 698 and 1,004 respectively, so the Zaydi set is one row short. The Rida appendix parser yields 35 rows and the active set contains 35.

Exact official Git blobs recorded by the GitHub API:

- Zayd text: `2c97cb75946922ea45e348ef10f1f94ee10bb1c7`, 452,810 bytes.
- Rabi' text: `cd75e85312a6204bd9aa17d888c2ae4306994b88`, 481,681 bytes.

Primary source/project:

- https://github.com/OpenITI/RELEASE
- https://raw.githubusercontent.com/OpenITI/RELEASE/master/data/0122ZaydIbnCali/0122ZaydIbnCali.Musnad/0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1.mARkdown
- https://raw.githubusercontent.com/OpenITI/RELEASE/master/data/0170RabicIbnHabibAzdi/0170RabicIbnHabibAzdi.JamicSahih/0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1

OpenITI recommends citing a release/tag or Zenodo release, not a moving `master`, and describes the corpus as almost exclusively Arabic. Treat the current Zaydi, Ibadi, and Rida English fields as project-generated unless row-level evidence proves otherwise; record model/prompt/review provenance and pin the upstream release plus content digest.

## Neo4j full-load guidance from official documentation

Primary source: https://neo4j.com/docs/operations-manual/current/import/

- Use `neo4j-admin database import full` only for a non-existent/empty database and run it offline. Run `--dry-run=true` first to validate input arguments and estimate size without writing.
- Set an explicit `--max-off-heap-memory` on a constrained host. The default is 90% of currently free memory; importer page cache and other import data structures share this budget. The import does not use `server.memory.pagecache.size`.
- Keep heap modest for this corpus; Neo4j gives 2 GiB as appropriate for smaller imports. Set `HEAP_SIZE` deliberately rather than growing it at the expense of off-heap/OS headroom.
- Keep `--threads` at or below available processors. Leave `--high-parallel-io=auto` unless storage measurements justify an override.
- Measure the largest UTF-8 CSV field before import and ensure `--read-buffer-size` is at least that large (default 4,194,304 bytes). Hadith text makes this a concrete validation check.
- Avoid global `--multiline-fields=true`; Neo4j warns it can severely degrade performance. Normalize embedded line breaks or use the version-2 file-specific multiline list only for files that require it.
- Curate to zero faults and use strict bad-entry tolerance. Neo4j warns malformed/bad entries materially hurt performance; do not hide them by skipping logs during the canonical load.
- Indexes/constraints are not created by default. For the general path, bulk-import the clean data first, then create constraints and query indexes. Enterprise Edition with block format may supply a `--schema` script so supported indexes/constraints are populated as part of import.

## Provenance blockers in the repository

- `datasets/sources/README.md` only has a completed OpenITI registry; Sunnah.com, Thaqalayn, Sheikh Ahmad, Zaydi, and Ibadi entries are pending.
- `datasets/CREDITS.md` reports one data source despite the active corpus consuming several.
- `datasets/ATTRIBUTION.md` requires license, retrieval, and BibTeX metadata for every upstream source, so current assets violate the repository's own provenance contract.
- `datasets/hadith-data/README.md` contains stale/contradictory collection totals. Generate these tables from the canonical manifest rather than maintaining them manually.

## Captured evidence and filtered stashes

Every external source was captured under `.omc/research` with URL, timestamp, and intent, then filtered through `scrt` before synthesis.

- `neo4j-admin-import-2026-07-20.html` → stash `neo4j-import-official`
- `openiti-release-readme-2026-07-20.md`, exact source texts, and GitHub listing captures → stashes `openiti-release-official` and source/listing metadata files
- `thaqalayn-api-readme-2026-07-20.md`, `thaqalayn-booknames-2026-07-20.txt`, `thaqalayn-live-allbooks-2026-07-20.txt` → stashes `thaqalayn-api-official`, `thaqalayn-manifest-official`, `thaqalayn-live-manifest`
- Six `sunnah-*-2026-07-20.html` captures → stash `sunnah-k6-official`
