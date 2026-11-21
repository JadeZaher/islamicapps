# Riwayat corpus (Riwāyāt: A Corpus of Sunni and Shīʿī Hadith Transmission), SQLite

Raw upstream archive plus its unpacked database. Untrusted data: read only as data (SQLite opened
`mode=ro&immutable=1` by scripts kept outside this directory); never execute anything from here, including the
upstream repository's `tools/` scripts, which were not downloaded. Nothing here is a registry, an alias list or an
identity claim, and no canonical pipeline reads it. Only this README is tracked in git.

## Source

| Field | Value |
| --- | --- |
| Record | Zenodo https://zenodo.org/records/23630501 (DOI 10.5281/zenodo.23630501, version v1; concept DOI 10.5281/zenodo.23630500) |
| File URL | https://zenodo.org/api/records/23630501/files/hadith_master.db.xz/content |
| Version | v1, published 2026-10-25. The "latest version" API response on 2026-11-21 was byte-identical to v1 (no newer version) |
| Code and documentation | https://github.com/abdullahansara/riwayat-corpus at `993ab1ed94ee8a3946cced854e3ee3ccefbe6e57` (2026-10-25T02:04:50Z); only `docs/SOURCES.md`, `docs/SCHEMA.md` and `CITATION.cff` were captured |
| Retrieved | 2026-11-21, generic client identity, unauthenticated |
| Licence | **CC0 1.0** for the authors' own layer (parses, identifications, labels, documentation), re-confirmed on 2026-11-21 (Zenodo `license: cc-zero`; repository README "License"), matching `datasets/hadith-data/diagnostics/chain-reconciliation/research/readme-abdullahansara_riwayat-corpus.md`. **The hadith texts and source annotations inside remain under their own licences** (hadith-kg CC BY 4.0, Thaqalayn, Sanadset, SemanticHadith, MIDS, AR-Sanad/Itqan, OpenITI, Hawramani/muslimscholars, Muhaddithat; `source-docs-SOURCES.md`) |

## Files

| File | Bytes | SHA-256 | Check |
| --- | ---: | --- | --- |
| `hadith_master.db.xz` (as downloaded) | 576,781,988 | `0519e097f742b2d9262a1a6c05e7cb0d697f0bef71179c1610f9d28445dfde05` | equals the SHA-256 published in the record description and repository README; MD5 `3f215d451a6534ea648ee548cf38045e` equals Zenodo's file checksum |
| `hadith_master.db` (unpacked with Python `lzma`) | 4,719,267,840 | `278e674ee72ac04886059b14fe6f8e52e70797ac6c65cba08409bafc2d61133b` | computed locally; upstream publishes no hash of the unpacked file |
| `source-api-record-v1.json` (Zenodo API) | 5,417 | `6f1eb17a5daec745b85b58564402255dbbb5f191d320e5cb2940151818df7fe7` | |
| `source-api-record-latest.json` (Zenodo latest-version API) | 5,417 | `6f1eb17a5daec745b85b58564402255dbbb5f191d320e5cb2940151818df7fe7` | identical to v1 |
| `source-api-github-head.json` (repository HEAD commit) | 11,652 | `4cd298f5415f6d1363392613a3397e80388222f3f9eeccfd31c54a10320e71cd` | |
| `source-docs-SOURCES.md` | 296 | `81d640e6874bef90ef88355485491fc03e93477e296fdef8be7051581b3cf8bf` | |
| `source-docs-SCHEMA.md` | 3,810 | `376f96d85eac97c728cea80fbc3b67671aef95dca44ade4d024ed92970abebcc` | |
| `source-CITATION.cff` | 704 | `001587103d05bed873c812cdccbdfb4bb5b6eda23285ad15d5386e22a28380b7` | |

## Attribution

CC0 requires none for the authors' layer; the authors ask for a citation (`CITATION.cff`), and the embedded texts
carry their sources' terms. Use:

> Abdullah Ansar, "Riwāyāt: A Corpus of Sunni and Shīʿī Hadith Transmission", v1, Zenodo, 2026,
> https://doi.org/10.5281/zenodo.23630501 (CC0 1.0). Hadith texts and annotations derive from third-party datasets
> under their own licences, including hadith-kg by emadjumaah (CC BY 4.0,
> https://huggingface.co/datasets/emadjumaah/hadith-kg) and ThaqalaynData for the Shi'i texts.

Shi'i rows come from Thaqalayn (`hadith.source_ids` = `{"thaqalayn": "T:<book>:..."}`); their rights follow the
project's Thaqalayn source card, not CC0.

## Profile

Measured by `datasets/hadith-data/diagnostics/biography-verification/profile_external_datasets.py` and
`measure_imami_authority_inputs.py`; numbers in `external_dataset_profile.json` and `imami_authority_inputs.json`
there. In short: 924,787 hadiths (887,480 Sunni, 37,307 Shi'i), 5,677,620 chain mentions, 193,014 narrator records
with 708,824 name forms, and a crosswalk `narrator_source_id` to `itq` (AR-Sanad/Itqan), `chains`, `kg` (hadith-kg
`rawis.id`), `sh` (SemanticHadith `HN…`), `thq` (Thaqalayn) and `mids`. No muslimscholars.info id is present, so
nothing joins to `scholar_indx` except by name.
