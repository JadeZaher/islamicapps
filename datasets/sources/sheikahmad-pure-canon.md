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
  2026-11-21 rights review: the provider's "Hadith Pure Canon Authentica" page
  (https://nabimuhammad.com/Prophet_Muhammad_Hadith-Canon.html) ends "© 2026
  NabiMuhammad.com — All Rights Reserved"; no licence or terms page found.
  Status: permission_needed. See docs/rights/rights-register.md section 2.

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

## Rights review 2026-11-21

Evidence: `docs/rights/evidence/nabimuhammad-hadith-canon-2026-11-21.txt`,
`local-copy-identity-2026-11-21.md`.

- Provider: NabiMuhammad.com, led by Ahmad Darwish. Its site says "All Rights
  Reserved" and offers the Green Book workbook for download; downloading is
  not a licence to republish.
- `Hadith-Pure-Canon-Authentica.xlsx`: creator "DELL", created 2026-03-29, no
  licence sheet. How it reached the project is not recorded.
- Every one of the 100,217 rows has `ruling = ثابت`, the provider's own seal,
  not a scholar's grading.
- Several rows embed edition blocks from an electronic hadith library (for
  example Darimi: Dar al-Kitab al-Arabi, Beirut 1987, ed. Zamarli and
  al-Sab' al-'Alami; Muwatta': ed. Muhammad Fu'ad 'Abd al-Baqi).
- Identity flag: the provider's 14 listed references do not include a Musnad
  al-Shafi'i; confirm what the label `شافعي` (2,054 rows) denotes.
- Open alternatives: OpenITI holds Ahmad's *Musnad*, Malik's *Muwatta'* and
  al-Shafi'i's *Musnad* (CC BY-NC-SA 4.0).

## Related

- Rights register: `docs/rights/rights-register.md`
- Provider page: https://nabimuhammad.com/Prophet_Muhammad_Hadith-Canon.html
- Canonical consumer: `datasets/hadith-data/regen_unified_csvs.py`
