# Thaqalayn source snapshot

## Freshness and source of truth

Use the documented live REST service at `https://www.thaqalayn-api.net/api/v2`.
The repository's `V2/ThaqalaynData` directory is an archival seed and upstream
explicitly describes it as outdated; it is not the refresh surface.

`download_thaqalayn.py` first reads the current numeric JSON files to establish
the curated, one-to-one mapping from exact API `bookId` to numeric
`provider_file_id`. A new, removed, duplicated, or reassigned `bookId` stops the
refresh for curation. Never infer this identity from URL, response order, book
title, volume label, or a newly allocated sequence number. Thaqalayn URLs are
not unique across volumes.

## Publication boundary

All 33 book arrays and `BookNames.json` are fetched and validated before any
canonical file is replaced. Files are rendered as deterministic, tab-indented
UTF-8 JSON compatible with `build_csv.py`. Publication uses per-file atomic
replacement with rollback, and `snapshot_manifest.json` is replaced last as the
snapshot commit record.

The snapshot manifest stores source and rendered hashes, ETags, actual counts,
advertised ranges, and every range discrepancy. An advertised ID is not a
record: missing IDs such as the currently advertised but unavailable Nu'mani
469 remain upstream inconsistencies and must never be synthesized.

## Content preservation

Keep the complete REST objects, including Arabic and translated text, author,
translator, volume, category/chapter identifiers, URL, source sanad/matn, and
all grading representations. Refreshing the source snapshot does not approve a
translation for publication and does not rewrite or normalize source text.

