# hadith-kg (al-Jami' Hadith Knowledge Graph), SQLite

Raw, unmodified upstream file. Untrusted data: read it only as data (SQLite opened `mode=ro&immutable=1` by scripts
kept outside this directory); never execute anything from here. Nothing here is a registry, an alias list or an
identity claim, and no canonical pipeline reads it. Only this README is tracked in git (`.gitignore`
`datasets/sources/external/*/*`).

## Source

| Field | Value |
| --- | --- |
| Dataset page | https://huggingface.co/datasets/emadjumaah/hadith-kg |
| File URL | https://huggingface.co/datasets/emadjumaah/hadith-kg/resolve/8ae7e3d5be284a6b32a989cd41866343fc19501c/hadith-kg.db |
| Version | Hugging Face revision `8ae7e3d5be284a6b32a989cd41866343fc19501c` (last modified 2026-07-31T15:49:32Z) |
| Upstream build | `meta` table: "mongodump hadithdb/hadith (2017-10-12) + rawa_cat.csv", cleaned 2026-07-09 |
| Retrieved | 2026-11-21, generic client identity, unauthenticated |
| Licence | **CC BY 4.0**, re-confirmed on the source on 2026-11-21 (card YAML `license: cc-by-4.0` and API `cardData.license`), matching the earlier capture in `datasets/hadith-data/diagnostics/chain-reconciliation/research/readme-hf-emadjumaah_hadith-kg.md` (byte-identical card) |

## Files

| File | Bytes | SHA-256 | Check |
| --- | ---: | --- | --- |
| `hadith-kg.db` | 1,634,877,440 | `d528084321e715006712e0e2461809a3afc9408065a1d1af90238c8b723815a6` | equals the published Git LFS oid for this revision |
| `source-README.md` (dataset card at the revision) | 2,267 | `f9cea956e11e56223cc4f0446da0ebd7e92a610010091afcf7d5874b9b4c882a` | |
| `source-api-dataset.json` (HF API, licence and revision) | 1,509 | `2fe751988a8dc94fa90bc376810012d9d708365c864f5b73156ba8e9aae6c818` | |
| `source-api-tree.json` (HF file list with LFS oids) | 1,402 | `cba246e362c3905e1f7b68a202c1b82fabf33c98e4183198c3875f6c542aa8c6` | |

Not downloaded (not needed for the approved purpose): `hadith-app.db` (2.9 GB application copy), `athar-embedding.db`
and `matn-embedding.db` (about 240 MB each, embedding vectors).

## Required attribution (CC BY 4.0)

> hadith-kg — "الجامع — Hadith Knowledge Graph" by emadjumaah, https://huggingface.co/datasets/emadjumaah/hadith-kg
> (revision 8ae7e3d5), licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Compiled by its
> author from hadithdb (2017). Measurements and candidate rows derived from it by this project are unreviewed;
> the database itself was not changed.

Any table or display derived from this file must carry that line and say what was changed.

## Profile

Measured by `datasets/hadith-data/diagnostics/biography-verification/profile_external_datasets.py`; full numbers in
`external_dataset_profile.json` there. In short: 425 books with no tradition field (nearly all Sunni works; book 55
is *Musnad Zayd*, Zaydi, and book 56 *Musnad al-Rabi' b. Habib*, Ibadi; no Imami work), 715,790 hadiths with plain Arabic
`nass` and matn offsets, 577,024 chains (`sanads`/`sanad_rawis`, ordered from the book author up to the companion),
49,844 narrators (`rawis`: name, popular name, `tabaka` on a 1-38 scale, rank wording, raw death/birth year strings,
`iqama`, `death_place`), 127,863 critic statements (`aqwal`, 1,015 critics in `alems`). Narrator ids are internal
integers; there is no external id column, so nothing joins to `scholar_indx` except by name.
