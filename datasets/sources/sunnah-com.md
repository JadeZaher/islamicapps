---
id: sunnah-com
name: Sunnah.com bilingual hadith collection
kind: api
url: https://sunnah.com/developers
retrieved: 2026-07-20

license: unstated
license_url: https://sunnah.com/about
license_notes: |
  No bulk-data license was found. Site policy forbids scraping and mass
  reproduction of entire books or collections. The official API requires an
  API key, publishes only a portion of checked data, and accepts requests for
  an offline dump although a general dump is not currently available. Obtain
  written permission for persistent local storage, normalization, display,
  redistribution, and translator attribution before bulk recovery or release.

traditions:
  - sunni
collections:
  - "Sahih al-Bukhari"
  - "Sahih Muslim"
  - "Jami' al-Tirmidhi"
  - "Sunan an-Nasa'i"
  - "Sunan Abi Dawud"
  - "Sunan Ibn Majah"
coverage_rows: 34441

paths:
  - datasets/hadith-data/all_hadiths_clean.csv.gz
  - datasets/hadith-data/all_hadiths_unified.csv.gz

bibtex: |
  @misc{sunnah-com-2026,
    title  = {Sunnah.com Hadith Collection and API},
    author = {{Sunnah.com}},
    year   = {2026},
    url    = {https://sunnah.com},
    note   = {Retrieved 2026-07-20}
  }
---

# Sunnah.com

## What we use

The six Sunni collections in the current master descend from a bilingual
Sunnah.com snapshot. Official collection pages and the official API are the
verification surface for record-level recovery. Collection-local references,
not bare integers, are required because displayed numbering differs by edition.

## How we acquired it

The repository inherited a prebuilt CSV snapshot; no reproducible acquisition
log or pinned API response accompanies it. New recovery must use the official
API or an approved offline snapshot, retain the request reference and response
digest, and match the Arabic source text before applying English.

## What we changed

- Normalized source labels and projected rows into the unified schema.
- Preserved the original row identifier as `source_record_id`.
- Added translation completeness and provenance fields.
- Made no blanket content correction to Arabic or English.

## Known limits

- 853 rows still lack English after all local recovery assets are exhausted.
- Eight rows lack Arabic and several existing English values fail structural QA.
- The legacy snapshot does not retain translator, API response, or edition
  metadata per row.
- The official API requires a key and exposes only a checked portion of the
  corpus. Its access form accepts offline-dump requests, but a general dump is
  not currently available.

## Access and reproduction conditions

- Do not scrape the website or reproduce whole books or collections from page
  HTML; the official About page expressly disallows both practices.
- Use the approved API or an explicitly granted offline snapshot only after
  confirming terms for local persistence, transformation, display, and
  redistribution.
- Retain API request references, response digests, retrieval times, language
  identifiers, and missing-record metadata so recovery remains auditable.
- API/reference mappings and local curation dispositions are provenance
  evidence only; they neither license translation text nor satisfy the local
  translation release gate.

## License & attribution requirements

The license is unstated. Retain the Sunnah.com collection URL, displayed
reference, and named translator where the source supplies one. Do not represent
the local snapshot as an independently licensed open corpus.

## Related

- Canonical consumer: `datasets/hadith-data/regen_unified_csvs.py`
- Developer/API policy: https://sunnah.com/developers
- API access request: https://github.com/sunnah-com/api/issues/new?template=request-for-api-access.md
- API specification: https://github.com/sunnah-com/api/blob/master/spec.v1.yml
- Site reproduction policy: https://sunnah.com/about
