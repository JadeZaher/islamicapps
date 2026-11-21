---
id: thaqalayn-api
name: Thaqalayn API V2
kind: api
url: https://github.com/MohammedArab1/ThaqalaynAPI
retrieved: 2026-07-21

license: CC-BY-4.0
license_url: https://thaqalayn.com/terms#content-license
license_notes: |
  Corrected 2026-11-21 (was GPL-3.0, which is the ThaqalaynAPI code licence,
  https://github.com/MohammedArab1/ThaqalaynAPI/blob/main/LICENSE, and says
  nothing about the hadith content). Thaqalayn's Terms of Use (updated
  2026-10-01) license "public library content, including translations" under
  CC BY 4.0, but "This grant covers the rights held by Stichting Thaqalayn",
  and Thaqalayn says it uses already available translations. Arabic of the
  classical works: CC BY 4.0 with attribution. English: unconfirmed per
  translator. Mu'jam al-Ahadith al-Mu'tabara is a modern compilation (Muhsini,
  d. 2019). Credit Thaqalayn, author and translator, link source and licence,
  state changes. See docs/rights/rights-register.md section 4.

traditions:
  - shia-imami
collections:
  - "Thaqalayn API V2 book manifest"
coverage_rows: 33190

paths:
  - datasets/hadith-data/shia-hadith/v2_books/
  - datasets/hadith-data/shia-hadith/download_thaqalayn.py
  - datasets/hadith-data/shia-hadith/build_csv.py

bibtex: |
  @misc{thaqalayn-api-2026,
    title  = {Thaqalayn API},
    author = {{Thaqalayn API contributors}},
    year   = {2026},
    url    = {https://github.com/MohammedArab1/ThaqalaynAPI},
    note   = {Retrieved 2026-07-21}
  }
---

# Thaqalayn API V2

## What we use

The local V2 JSON snapshot supplies the Imami hadith text, chain, grading,
source URL, and English text for 33,190 active rows.

## How we acquired it

`download_thaqalayn.py` maps the exact live API `bookId` values onto the
existing curated numeric provider filenames, downloads all book arrays from the
documented live REST API into a staging directory, validates them, and publishes
the snapshot manifest last. `build_csv.py` transforms those raw source objects
into the compatibility CSV consumed by the unified generator.

## What we changed

- Flattened API JSON into the unified schema.
- Preserved source URLs and grading payloads.
- Derived durable identity from the curated provider file, exact API `bookId`,
  and upstream hadith ID; the non-unique source URL is never an identity key.
- Did not edit the supplied Arabic or English content.

## Known limits

The live `/api/v2/allbooks` ranges advertise 33,191 records, but the only
advertised delta is not retrievable: `Kitab-al-Ghayba-Numani/469` returns the
API's no-hadith error and is absent from the public hadith sitemap. The verified
ingestible delta is therefore zero, and the local 33,190-row snapshot must not
synthesize that ID.

A full staged refresh attempted on 2026-07-22 UTC also found the advertised
659-row `Kamal-al-Din-wa-Tamam-al-Nima-Saduq` bulk endpoint returning `[]`;
sampled record endpoints returned the API's no-hadith error. The all-or-nothing
refresh therefore published nothing and preserved the complete local 659-row
file. Retry freshness reconciliation after the upstream endpoint is restored.
The live manifest identifies Sayyid Athar Husain S. H. Rizvi as translator for
that work, but the blocked refresh did not partially rewrite local metadata.

The API repository's checked-in `V2/ThaqalaynData` directory is described
upstream as outdated and excludes weekly database updates. It is retained only
as an archival fallback, not used for freshness.

## License & attribution requirements

The API code repository is GPL-3.0. The underlying corpus includes scraped
source editions and named third-party translations whose independent reuse
rights are not clearly stated on the public About or Privacy pages. Preserve
the API source URL, exact work identity, translator metadata, retrieval time,
and payload hashes, and obtain clarification before public bulk redistribution.

## Rights review 2026-11-21

Evidence: `docs/rights/evidence/thaqalayn-terms-2026-11-21.txt`,
`thaqalayn-about-2026-11-21.txt`, `local-copy-identity-2026-11-21.md`.

- thaqalayn.net now redirects to thaqalayn.com. Terms of Use §2: CC BY 4.0
  for the rights Thaqalayn holds; attribution must credit Thaqalayn (Stichting
  Thaqalayn), keep author and translator notices, link source and licence,
  indicate changes, and not imply endorsement.
- The text in use is the April 2026 pull: the `v2_books` files are dated
  2026-04-19 and last changed in `acbf394` (2026-04-20). The 2026-07-22
  refresh published nothing, so `retrieved: 2026-07-21` records the last
  attempt, not the data date. The October 2026 terms postdate the pull; the
  terms in force in April were not captured.
- The translator is carried per book in `BookNames.json` and is lost in the
  unified master; the attribution the licence requires needs it on the page.
- Gradings: al-Majlisi (classical) on al-Kafi; Bihbudi (*Sahih al-Kafi*) and
  Muhsini are modern scholars, rights unclear.

## Related

- Rights register: `docs/rights/rights-register.md`
- Thaqalayn Terms of Use: https://thaqalayn.com/terms
- Live manifest: https://www.thaqalayn-api.net/api/v2/allbooks
- Public REST documentation: https://github.com/MohammedArab1/ThaqalaynAPI#endpoints
- Repository license: https://github.com/MohammedArab1/ThaqalaynAPI/blob/main/LICENSE
- Thaqalayn About: https://thaqalayn.com/about (thaqalayn.net redirects here since at least 2026-11-21)
