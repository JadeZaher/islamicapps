---
id: narrator-lexicon
name: Local controlled narrator vocabulary
kind: lexicon
url: https://www.kaggle.com/datasets/fahd09/hadith-narrators
retrieved: 2026-07-20

license: unstated
license_url: https://muslimscholars.info/
license_notes: |
  The 24,326-row local asset does not retain row-level upstream citations or a
  documented license. Treat it as an unresolved provenance asset, not an
  authoritative biographical edition.
  2026-11-21 rights review: upstream identified. The file is the Kaggle dataset
  fahd09/hadith-narrators (2018-08-20, same 9,267,851 bytes), whose uploader
  "scraped" muslimscholars.info and labelled the upload CC0. muslimscholars.info
  states "All contents copyright of Arees Institute, registered in the United
  States". The uploader's CC0 cannot waive Arees Institute's rights. Public
  display of lexicon fields: permission_needed (Arees Institute). Previously
  url/license_url pointed at this project's own repository.

traditions:
  - cross-tradition
collections:
  - "Controlled rawi vocabulary"
coverage_rows: 24326

paths:
  - datasets/narrator-data/all_rawis.csv
  - src/scripts/seed-narrator-bios-phase0.ts

bibtex: |
  @misc{islamicapps-narrator-lexicon-2026,
    title  = {IslamicApps Local Narrator Vocabulary},
    author = {{IslamicApps contributors}},
    year   = {2026},
    url    = {https://github.com/atooz/islamicapps},
    note   = {Unresolved upstream provenance; audited 2026-07-20}
  }
---

# Local controlled narrator vocabulary

## What we use

`all_rawis.csv` provides 24,326 unique narrator identities, relationship lists,
and sparse date/place assertions for chain resolution. It is a working identity
index, not yet a citation-authentic biography corpus.

## How we acquired it

The current repository does not preserve a reproducible acquisition record for
the CSV. A separate manual phase-0 seed contains 21 narrative summaries.

## What we changed

- Resolve chain surface forms conservatively to `scholar_indx`.
- Keep ambiguous or unresolved forms in a gap asset.
- Do not infer missing dates or biographies.

## Known limits

The CSV has no citation, edition, page, narrative biography, Arabic-name,
geographic-region, or tabaqah fields. Only 374 rows have both plausible Hijri
endpoints before plausibility review, and 38 of those reverse birth/death order.
The 21 manual summaries cite general reference works in code comments but lack
record-level edition/page citations. Most narrator biographies and all
source-authentic citations remain outstanding.

## License & attribution requirements

Upstream provenance and license must be reconstructed before external release.
Every future biographical claim should cite work, author/editor, edition,
volume/page, passage or stable URL, retrieval date, and uncertainty.

## Correction 2026-11-21: where it came from

Evidence: `docs/rights/evidence/kaggle-fahd09-hadith-narrators-2026-11-21.txt`,
`muslimscholars-home-2026-11-21.txt`, `local-copy-identity-2026-11-21.md`.

- `all_rawis.csv` was first committed in `2696de8` (2026-03-22) and is
  unchanged: 9,267,851 bytes, SHA-256
  `d87c3af64d48b3cd585294ab5f6381536a51ff95a72a6707a7426ea483bf6c11`, the exact
  size of `all_rawis.csv` in Kaggle `fahd09/hadith-narrators` (version 1).
- Kaggle: "I only scraped this database [muslimscholars.info] with a Python
  script plus very minimal cleanup." The K6 snapshot's `chain_indx` points
  into this file because both come from the same uploader.
- muslimscholars.info (Arees Institute, United States) asserts copyright in all
  its contents. Facts (names, relations, dates) are generally free in the US;
  the database's selection, the `grade` column, biographies and book lists may
  not be. Keep lexicon fields off public pages until Arees Institute agrees
  (request F in `docs/rights/rights-register.md`).

## Related

- Rights register: `docs/rights/rights-register.md`
- Kaggle dataset: https://www.kaggle.com/datasets/fahd09/hadith-narrators
- Canonical identity input: `datasets/narrator-data/all_rawis.csv`
