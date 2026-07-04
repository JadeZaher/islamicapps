---
# ─── Identity ─────────────────────────────────────────
id: short-kebab-case-slug                      # required, must match filename
name: Human-readable name of the source         # required
kind: corpus | api | scraped-site | dataset | meta-source | lexicon
url: https://example.org                        # required if accessible online
retrieved: YYYY-MM-DD                           # date we last pulled / verified

# ─── License ──────────────────────────────────────────
license: CC-BY-SA-4.0 | CC-BY-NC-SA-4.0 | public-domain | unstated | other
license_url: https://creativecommons.org/...    # link to the full license text
license_notes: |                                # free-form clarifications
  E.g. "non-commercial only", "attribution must include version tag",
  "license inherited from upstream OpenITI corpus".

# ─── Scope ────────────────────────────────────────────
traditions:                                     # list any that apply
  - sunni
  - shia-imami
  - zaydi
  - ibadi
  - cross-tradition
collections:                                    # specific books / corpora covered
  - "Sahih al-Bukhari"
  - "Sahih Muslim"
coverage_rows: 0                                # approximate row count, if applicable

# ─── In-repo location ─────────────────────────────────
paths:                                          # where this source's data lives
  - datasets/hadith-data/...

# ─── Citation (academic) ──────────────────────────────
# A valid BibTeX entry. This is what gets rendered into the generated
# CREDITS.md and into any external publication that cites the project.
bibtex: |
  @misc{shortkey-YYYY,
    title  = {Source title},
    author = {{Project or Author}},
    year   = {YYYY},
    url    = {https://example.org},
    note   = {Retrieved YYYY-MM-DD}
  }
---

# {Source name}

## What we use

One short paragraph: which specific files/books/endpoints we ingest, and why
this source is the right one for that scope. Name the alternatives we
considered and rejected, briefly.

## How we acquired it

Concrete steps: which script fetched / parsed / built it, what the input
format was, what the output format is in our repo. Link the script:
`datasets/.../fetch_x.py`. If acquisition was manual (one-off download,
Excel from a contributor, etc.) say so explicitly.

## What we changed

The list of transformations we apply before the data lands in our pipeline.
This is the part that determines whether downstream researchers can trust
our copy or whether they should go upstream. Examples:

- Normalized Unicode form to NFC.
- Stripped footnote markers `[1]` through `[999]`.
- Renamed columns `arab_name` → `name_arabic`, `eng_name` → `name_english`.
- **No** content edits to Arabic text.

## Known limits

What this source does *not* cover, and any known quality issues
(OCR artifacts, missing fields, contested attributions, ambiguous grading
schemes). Anyone building on this should know.

## License & attribution requirements

Re-state the obligations from the front-matter in prose. If attribution
must take a specific form (e.g. include a version string, link back to a
canonical URL, name the original compiler), put that exact form here so
contributors can copy it.

## Related

- Strategies that consume this source: [[strategy-slug]]
- Other sources that this one depends on or supersedes: [[other-source-slug]]
