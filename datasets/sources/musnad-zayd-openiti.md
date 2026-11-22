---
id: musnad-zayd-openiti
name: Musnad al-Imam Zayd ibn Ali via OpenITI
kind: corpus
url: https://github.com/OpenITI/RELEASE/tree/master/data/0122ZaydIbnCali/0122ZaydIbnCali.Musnad
retrieved: 2026-07-20

license: CC-BY-NC-SA-4.0
license_url: https://zenodo.org/records/17767721
license_notes: |
  Corrected 2026-11-21 (was "unstated"): OpenITI release 2025.1.9 is
  CC BY-NC-SA 4.0 (Zenodo record 17767721). Per-text metadata names the printed
  edition OCLC 745191363 and annotation for SHARIAsource; paratext removed in
  the 2023 OpenITI Clean operation. See docs/rights/rights-register.md §3.
  Pin an OpenITI release and preserve the full text URI and digest.

traditions:
  - zaydi
collections:
  - "Musnad al-Imam Zayd ibn Ali"
coverage_rows: 698

paths:
  - datasets/hadith-data/zaydi-hadith/PROVENANCE.json
  - datasets/hadith-data/zaydi-hadith/parsed_hadiths.json

bibtex: |
  @misc{musnad-zayd-openiti-2026,
    title  = {Musnad al-Imam Zayd ibn Ali, OpenITI transcription},
    author = {{OpenITI contributors}},
    year   = {2026},
    url    = {https://github.com/OpenITI/RELEASE},
    note   = {OpenITI URI 0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1; retrieved 2026-07-20}
  }
---

# Musnad al-Imam Zayd ibn Ali via OpenITI

## What we use

The OpenITI mARkdown transcription is the Arabic source for the Zaydi Musnad.
The project-generated English is a separate derivative and must retain its
model, prompt, and review status.

## How we acquired it

The OpenITI text is parsed by `datasets/parse_openiti.py` into
`zaydi-hadith/parsed_hadiths.json`; `PROVENANCE.json` records the local source
locator.

## What we changed

- Removed OpenITI structure markers while retaining page references.
- Separated record boundaries and normalized fields into the unified schema.
- Kept Arabic source text distinct from machine-produced English.

## Known limits

The checked-in parse (corrected 2026-11-21) has 691 rows; the earlier parse had 698; rerunning the current parser against the
exact official Git blob `2c97cb75946922ea45e348ef10f1f94ee10bb1c7`
produces 699. The missing row must be reconciled before publication. Existing
English has no row-level human-review evidence.

## License & attribution requirements

Cite OpenITI and preserve the full OpenITI URI, pinned blob/release, and local
transformation provenance. Recheck the individual text license before external
redistribution.

## Related

- Parent registry: [[openiti]]
