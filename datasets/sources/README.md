# Sources

One file per upstream data source. Each file carries a BibTeX-style front-matter block plus a prose body — see [`_TEMPLATE.md`](./_TEMPLATE.md).

The canonical, machine-readable list is whatever currently lives in this directory; the table below is a human-friendly index. The generated [`datasets/CREDITS.md`](../CREDITS.md) is derived from this directory by [`scripts/build-credits.ts`](../../scripts/build-credits.ts) — **do not hand-edit the generated file.**

## Index

| Slug | Source | Traditions | Kind | License | Status |
| --- | --- | --- | --- | --- | --- |
| [openiti](./openiti.md) | Open Islamicate Texts Initiative | cross-tradition | meta-source | CC-BY-NC-SA-4.0 | ✅ documented |
| `thaqalayn-api` | Thaqalayn API V2 | shia-imami | api | unstated | ⏳ pending |
| `sunnah-com` | sunnah.com canonical-six export | sunni | scraped-site | unstated | ⏳ pending |
| `sheikahmad-pure-canon` | Pure Canon Authentica (NabiMuhammad.com / SheikhAhmad) | sunni | dataset | unstated | ⏳ pending |
| `musnad-zayd-openiti` | Musnad al-Imam Zayd ibn Ali (via OpenITI) | zaydi | corpus | inherits OpenITI | ⏳ pending |
| `jami-sahih-rabi-openiti` | Jami' al-Sahih (Musnad al-Rabi, Ibadi) via OpenITI | ibadi | corpus | inherits OpenITI | ⏳ pending |
| `musnad-rida-openiti` | Musnad al-Imam Ali al-Rida (Zaydi appendix) via OpenITI | zaydi | corpus | inherits OpenITI | ⏳ pending |
| `narrator-lexicon` | Controlled rawi vocabulary (Ibn Hajar / al-Mizzī / al-Khūʾī etc.) | cross-tradition | lexicon | unstated | ⏳ pending |

> Status legend: ✅ documented · ⏳ pending · ⚠️ needs review (license unclear, data updated upstream, scope change).

## Adding a new source

1. Copy [`_TEMPLATE.md`](./_TEMPLATE.md) to `datasets/sources/<your-slug>.md`.
2. Fill in the front-matter — every required field must be present (see template comments).
3. Write the prose sections. Be concrete about *what we changed* and *known limits* — those are the parts other researchers will cite back.
4. Add a row to the index table above.
5. Re-run `npm run build:credits` and commit the regenerated `datasets/CREDITS.md`.

## Why the BibTeX field is required

Two reasons:

- It is the single thing an external researcher needs to cite our use of a source in a paper or post. Lifting one BibTeX entry is friction-free; reconstructing one from prose is not.
- The credits generator parses it directly, so a single source of truth feeds both human and machine consumers (footer credits, MCP discovery manifest, `CREDITS.md`, future about-page).

If the upstream source has no canonical citation form (a sufficiently common case for living digital projects), invent one using the `@misc{...}` form with the project name, year, URL, and a `Retrieved YYYY-MM-DD` note. Document the invention in `license_notes`.
