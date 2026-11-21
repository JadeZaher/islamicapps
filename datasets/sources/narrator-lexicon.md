---
id: narrator-lexicon
name: Local controlled narrator vocabulary
kind: lexicon
url: https://github.com/atooz/islamicapps
retrieved: 2026-07-20

license: unstated
license_url: https://github.com/atooz/islamicapps
license_notes: |
  The 24,326-row local asset does not retain row-level upstream citations or a
  documented license. Treat it as an unresolved provenance asset, not an
  authoritative biographical edition.

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

## Related

- Canonical identity input: `datasets/narrator-data/all_rawis.csv`
