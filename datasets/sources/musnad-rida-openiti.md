---
id: musnad-rida-openiti
name: Sahifat al-Imam Ali al-Rida via OpenITI source appendix
kind: corpus
url: https://github.com/OpenITI/RELEASE/tree/master/data/0122ZaydIbnCali/0122ZaydIbnCali.Musnad
retrieved: 2026-07-20

license: CC-BY-NC-SA-4.0
license_url: https://zenodo.org/records/17767721
license_notes: |
  Corrected 2026-11-21 (was "unstated"): OpenITI release 2025.1.9 is
  CC BY-NC-SA 4.0 (Zenodo record 17767721). Title flag: OpenITI's reviewer note
  on the parent file says "Page 434 onwards ... is a different text; a Musnad by
  Imam Musa", while the text's own heading is "مسند الإمام علي الرضا". Settle the
  title before publication. See docs/rights/rights-register.md §3.

traditions:
  - shia-imami
collections:
  - "Sahifat al-Imam Ali al-Rida"
coverage_rows: 35

paths:
  - datasets/hadith-data/rida-hadith/PROVENANCE.json
  - datasets/hadith-data/rida-hadith/parsed_hadiths.json

bibtex: |
  @misc{rida-openiti-2026,
    title  = {Sahifat al-Imam Ali al-Rida, appendix in an OpenITI source file},
    author = {{OpenITI contributors}},
    year   = {2026},
    url    = {https://github.com/OpenITI/RELEASE},
    note   = {Parsed appendix; retrieved 2026-07-20}
  }
---

# Sahifat al-Imam Ali al-Rida via OpenITI source appendix

## What we use

The parser separates a 35-row al-Rida appendix embedded in the source file used
for Musnad Zayd. It is classified with the Imami family in the unified dataset,
not as a Zaydi collection merely because of file location.

## How we acquired it

`datasets/parse_openiti.py` detects the appendix boundary and writes
`rida-hadith/parsed_hadiths.json` with its own provenance record.

## What we changed

- Split the appendix at a documented source marker.
- Parsed record/page structure and projected it into the unified schema.
- Kept project-generated English separate from Arabic provenance.

## Known limits

The appendix shares an upstream file with another collection, so record IDs
must include collection/tradition context. English lacks row-level
model/prompt/human-review provenance.

## License & attribution requirements

Cite OpenITI, preserve the parent file locator and appendix transformation, and
recheck the individual text license before redistribution.

## Related

- Parent registry: [[openiti]]
