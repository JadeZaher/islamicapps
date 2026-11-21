# /collections — reading the corpus in order

`/collections` (works by tradition: Ibadi, Imami, Sunni, Zaydi, alphabetical, none first) → `/collections/<work slug>`
(books or volumes with counts; a single volume's chapters inline; or the reports, when the copy has no books) →
`/<book number>` (chapters grouped by kitab, or reports; `?view=all` reads the whole book) → `/<chapter key>`
(reports, 50 a page). Data: `src/db/queries/browse.ts`; visibility from `requestVisibility()`.

## What the data really carries (development load, 2026-11-21)

| Tradition | Reports | Book | Chapter | Own number |
| --- | ---: | ---: | ---: | --- |
| Sunni, six books (K6) | 34,441 | all (kitab) | none | sunnah.com numbers; 31 are `0` |
| Sunni, Pure Canon (Ahmad, Muwatta', Darimi, Shafi'i) | 29,915 | none | none | Ahmad repeats numbers; Shafi'i has none |
| Imami (Thaqalayn, 21 works; Rida via OpenITI) | 33,225 | all (volume) | all | from the provider URL only |
| Zaydi (OpenITI) | 698 | all | all | yes |
| Ibadi (OpenITI) | 1,004 | all | all | yes |

Where a level is missing the page says so (`structure.ts`) and lists by the work's own numbering; nothing is invented.
Why chapters are missing for the Sunni works: `neo4j_export/export_bundle.py` `_structure_nodes` builds only a Book for
`sunnah-com` rows (from the CSV's `chapter_no`/`chapter`, which in K6 are the kitab) and nothing for Pure Canon (it
refuses any structure field there). The K6 input carries no bab field at all.
