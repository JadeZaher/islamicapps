---
id: jami-sahih-rabi-openiti
name: Jami' al-Sahih of al-Rabi ibn Habib via OpenITI
kind: corpus
url: https://github.com/OpenITI/RELEASE/tree/master/data/0170RabicIbnHabibAzdi/0170RabicIbnHabibAzdi.JamicSahih
retrieved: 2026-07-20

license: CC-BY-NC-SA-4.0
license_url: https://zenodo.org/records/17767721
license_notes: |
  Corrected 2026-11-21 (was "unstated"): OpenITI release 2025.1.9 is
  CC BY-NC-SA 4.0 (Zenodo record 17767721). The per-text metadata records no
  edition (template placeholders only); paratext removed in the 2023 OpenITI
  Clean operation. See docs/rights/rights-register.md §3.

traditions:
  - ibadi
collections:
  - "Jami' al-Sahih / Musnad al-Rabi ibn Habib"
coverage_rows: 1004

paths:
  - datasets/hadith-data/ibadi-hadith/PROVENANCE.json
  - datasets/hadith-data/ibadi-hadith/parsed_hadiths.json

bibtex: |
  @misc{jami-rabi-openiti-2026,
    title  = {Jami' al-Sahih of al-Rabi ibn Habib, OpenITI transcription},
    author = {{OpenITI contributors}},
    year   = {2026},
    url    = {https://github.com/OpenITI/RELEASE},
    note   = {OpenITI URI 0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1; retrieved 2026-07-20}
  }
---

# Jami' al-Sahih of al-Rabi ibn Habib via OpenITI

## What we use

This OpenITI transcription is the Arabic source for the 1,005-row Ibadi (1,004 before the 2026-11-21 parser correction)
collection, including commentary represented by the parser.

## How we acquired it

`datasets/parse_openiti.py` parses the mARkdown source into
`ibadi-hadith/parsed_hadiths.json` and retains page references.

## What we changed

- Parsed OpenITI book/chapter/page markers.
- Projected records into the unified schema.
- Added project-generated English as a separately attributed derivative.

## Known limits

Two local rows share upstream ID `rabi_0387` and hadith number 387 but contain
different Arabic. They also reuse one English translation, so both are blocked
for curation until compared with the pinned source blob
`cd75e85312a6204bd9aa17d888c2ae4306994b88`. Existing English lacks row-level
model/prompt/review provenance.

## License & attribution requirements

Cite OpenITI and preserve the full text URI, release/blob, and transformation
provenance. Recheck the per-text license before redistribution.

## Related

- Parent registry: [[openiti]]
