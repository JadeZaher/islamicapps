---
id: openiti
name: Open Islamicate Texts Initiative (OpenITI)
kind: meta-source
url: https://openiti.org
retrieved: 2026-06-16

license: CC-BY-NC-SA-4.0
license_url: https://zenodo.org/records/17767721
license_notes: |
  Corrected 2026-11-21 (was "unstated"): the Zenodo record of OpenITI release
  2025.1.9 (DOI 10.5281/zenodo.17767721, concept DOI 10.5281/zenodo.3082463)
  declares cc-by-nc-sa-4.0. The GitHub repositories carry no LICENSE file, so
  cite the Zenodo release, not repository master. Conditions: attribution to
  OpenITI and the upstream library, non-commercial use, share-alike for
  adaptations (including our parsed text, chain tables and machine
  translations). See docs/rights/rights-register.md section 3.
  Earlier note, kept for the record:
  OpenITI is an umbrella corpus assembled from many upstream community
  libraries (Maktaba Shamila al-Zaydiyya, al-Ibadiyya, etc.). The corpus
  as a whole does not publish a single SPDX-identified license; individual
  texts inherit whatever license their upstream library applied. In
  practice the corpus is treated as openly redistributable for academic
  and non-commercial use with attribution. **Treat as "share-alike with
  attribution" until upstream clarifies, and re-verify per text before
  any commercial republication.**

traditions:
  - cross-tradition
  - zaydi
  - ibadi
  - sunni
  - shia-imami
collections:
  - "Musnad al-Imam Zayd ibn Ali (0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1)"
  - "Jami' al-Sahih / Musnad al-Rabi (0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1)"
  - "Sahifat al-Imam Ali al-Rida (Imami-family appendix in the same source file as Musnad Zayd)"
coverage_rows: 1738

paths:
  - datasets/parse_openiti.py
  - datasets/hadith-data/openiti-sources/
  - datasets/hadith-data/zaydi-hadith/
  - datasets/hadith-data/ibadi-hadith/
  - datasets/hadith-data/rida-hadith/

bibtex: |
  @misc{openiti,
    title        = {{OpenITI}: {Open} {Islamicate} {Texts} {Initiative}},
    author       = {{Romanov, Maxim and Miller, Matthew Thomas and Savant,
                     Sarah Bowen and Kiessling, Benjamin and others}},
    year         = {2016--present},
    howpublished = {\url{https://openiti.org}},
    note         = {Retrieved 2026-06-16. Corpus assembled from
                    Maktaba Shamila al-Zaydiyya, al-Ibadiyya, and
                    related community-typed Islamicate text libraries.}
  }
---

# Open Islamicate Texts Initiative (OpenITI)

## What we use

OpenITI is our **primary source for Zaydi and Ibadi hadith collections** — two traditions for which clean, structured text was historically the bottleneck. Specifically we ingest three OpenITI texts:

- `0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1.mARkdown` — *Musnad al-Imam Zayd ibn Ali*, the foundational Zaydi hadith collection compiled by ʿAbd al-ʿAzīz ibn Isḥāq al-Baghdādī.
- `0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1.mARkdown` — *Jamiʿ al-Ṣaḥīḥ* of al-Rabīʿ ibn Ḥabīb al-Azdī, the canonical Ibāḍī collection, including al-Rabīʿ's commentary.
- The Sahifat al-Imam ʿAlī al-Riḍā appendix, which is bundled inside the Musnad Zayd source file from page 434 onward and is parsed as a separate Imami-family collection.

We chose OpenITI for these three texts because the alternatives (PDF scans, raw HTML from miscellaneous sites) require OCR with non-trivial Arabic-script error rates. OpenITI texts are **community-proofread transcriptions** from Maktaba Shamila al-Zaydiyya and al-Ibadiyya — not OCR — so the upstream error profile is "occasional typo / footnote-marker noise" rather than "garbled Arabic characters." The trade-off, documented under [Known limits](#known-limits), is that some legacy footnote artifacts and inconsistent diacritics survive.

For the **Sunni canonical six** and the **Imami four books** we use other sources (sunnah.com, ThaqalaynAPI) because better-structured alternatives exist; OpenITI's coverage there would be redundant. For the **classical Sunni Musnad / Sunan tier** (Aḥmad, al-Dārimī, etc.) we use the SheikhAhmad "Pure Canon Authentica" dataset; OpenITI's mARkdown encoding of those works is something we could fall back to but currently don't.

## How we acquired it

Manual one-time download of the three mARkdown files into `datasets/hadith-data/openiti-sources/`. Parsing is handled by [`datasets/parse_openiti.py`](../parse_openiti.py), which converts the custom mARkdown encoding (described in that script's header comment) into the project's structured hadith JSON format.

Key parsing rules — the kind of decisions that need to be auditable downstream:

- `### |` markers become `kitab` (book) boundaries; `### ||` become `bab` (chapter) boundaries.
- `#` opens a paragraph; `~~` continues the previous line.
- The Musnad Zayd file's Rida appendix is detected via a hardcoded marker constant (`ZAYD_APPENDIX_MARKER`) and routed to `rida-hadith/` rather than `zaydi-hadith/`.
- Output is written to `parsed_hadiths.json` per collection, alongside a `PROVENANCE.json` recording the OpenITI ID, parse date, and parser version.

## What we changed

Transformations applied before the data lands in our unified pipeline:

- Stripped OpenITI structural markers (`PageVNNPNNN`, `msNNN` milestones) from the running text but preserved them in a separate `structural_markers` field for round-trippability.
- Normalized Unicode to NFC.
- Separated the Rida appendix from the Musnad Zayd file (see above).
- **No content edits to the Arabic text.** OCR-like cleanup (garbled-letter sequences, stray punctuation, footnote-number noise) is handled by a separate, opt-in pass — see [strategy: arabic-text-cleanup](../strategies/arabic-text-cleanup.md) — rather than being baked into the parser.

## Known limits

- **Footnote-marker noise.** The community-typed source preserves footnote anchors as inline numerics in some passages. Mechanical cleanup catches most but not all.
- **Diacritics inconsistency.** Some texts are fully voweled (mushakkal), some are bare; the mix is internal to the upstream library, not introduced by us.
- **License ambiguity.** See `license_notes` in the front-matter. We are conservative about downstream republication until the corpus license is clarified.
- **Zaydi LLM-translation pipeline.** 258/627 Musnad Zayd hadiths required retranslation after an LLM refused on a first pass; see [strategy: arabic-text-cleanup](../strategies/arabic-text-cleanup.md) for what's audited and what isn't.
- **One-shot snapshot.** We hold a frozen copy at `retrieved: 2026-06-16`. Upstream OpenITI continues to evolve; future re-pulls should bump the `retrieved` date and diff against the in-repo copy before merging.

## License & attribution requirements

Until OpenITI publishes a single canonical license, we treat the corpus as **share-alike with attribution**. Any downstream work that republishes Zaydi/Ibadi text traceable to OpenITI must:

- Cite the OpenITI project using the BibTeX entry in the front-matter above.
- Preserve the upstream identifier (the `0122ZaydIbnCali...` style URI) so the chain of provenance is reconstructable.
- Carry forward any attribution requirements asserted by the *individual* upstream library (Maktaba Shamila al-Zaydiyya, al-Ibadiyya) when that information is recoverable from the source file.

## Rights review 2026-11-21

Evidence: `docs/rights/evidence/openiti-zenodo-17767721-2026-11-21.txt`,
`github-repo-licences-2026-11-21.txt`, `local-copy-identity-2026-11-21.md`.

- Licence: CC BY-NC-SA 4.0, declared on the Zenodo release record, not in the
  GitHub repositories. The "share-alike with attribution" reading above was
  right in spirit; the non-commercial condition was missing.
- Our two text files are the official Git blobs `2c97cb75…` (Zayd) and
  `cd75e853…` (Rabi'), taken from `master` (local file dates 2026-05-08), not
  a tagged release. Cite release 2025.1.9 and keep the blob ids.
- `datasets/hadith-data/README.md` still says the Zaydi Arabic came from an
  Archive.org OCR; that describes the April 2026 pipeline whose English is
  still in use. The current Arabic is the OpenITI file.
- Every adaptation we publish (parsed reports, chain and narrator tables,
  machine translations) must be released CC BY-NC-SA 4.0.

## Related

- Rights register: `docs/rights/rights-register.md`
- Strategies that consume this source: [[arabic-text-cleanup]], [[uniform-tahweel-aware-isnad-extraction]]
- Other sources that this enables: [[musnad-zayd-openiti]], [[jami-sahih-rabi-openiti]], [[musnad-rida-openiti]] (these are *views* of OpenITI scoped to one collection each)
