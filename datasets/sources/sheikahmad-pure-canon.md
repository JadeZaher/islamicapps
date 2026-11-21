---
id: sheikahmad-pure-canon
name: Pure Canon Authentica dataset
kind: dataset
url: https://nabimuhammad.com
retrieved: 2026-04-14

license: unstated
license_url: https://nabimuhammad.com
license_notes: |
  Contributor spreadsheets and derived files carry no explicit license in the
  repository. Confirm redistribution terms with the contributor/source owner.

traditions:
  - sunni
collections:
  - "Musnad Ahmad"
  - "Sunan al-Darimi"
  - "Musnad al-Shafi'i"
  - "Muwatta' Malik"
coverage_rows: 29915

paths:
  - datasets/hadith-data/archive/sheikahmad-pure-canon/pure_canon.jsonl
  - datasets/hadith-data/archive/classical-pipeline/classical_canon_enhanced.csv
  - datasets/hadith-data/archive/classical-pipeline/classical_translations_clean.jsonl

bibtex: |
  @misc{sheikahmad-pure-canon-2026,
    title  = {Pure Canon Authentica Hadith Dataset},
    author = {{Sheikh Ahmad / NabiMuhammad.com contributors}},
    year   = {2026},
    url    = {https://nabimuhammad.com},
    note   = {Contributor snapshot retrieved 2026-04-14}
  }
---

# Pure Canon Authentica dataset

## What we use

Only the four named primary collections are promoted to hadith nodes. The
remaining anthology and scholar-verdict rows require a separate cited
scholarship model and are not silently appended to the canonical corpus.

## How we acquired it

Contributor Excel assets were normalized into `pure_canon.jsonl`. English
translation passes were archived separately; the unified generator joins them
by immutable `pc_*` ID and exact stripped Arabic text.

## What we changed

- Canonicalized four Arabic source labels.
- Extracted chains where the source supports them.
- Resolved narrator surface forms conservatively and retained a gap file.
- Recovered English with deterministic source-ID and Arabic-text checks.

## Known limits

Translations are machine-produced and not comprehensively human reviewed.
Earlier repeated JSONL attempts conflict; the enhanced CSV has precedence and
`classical_translations_clean.jsonl` is only a narrow fallback when the enhanced
row is blank and the immutable ID plus Arabic text agree.

## License & attribution requirements

License terms are unstated. Preserve the source asset name and record ID and
confirm redistribution rights with the contributor/source owner.

## Related

- Canonical consumer: `datasets/hadith-data/regen_unified_csvs.py`
