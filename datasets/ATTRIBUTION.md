# Attribution

This file is the canonical entry point for credit, licensing, and provenance for the data underlying **Shura wa Istehsan**.

The platform is built on the work of many communities — classical Muslim scholars across every tradition, modern digital-humanities projects, and contemporary community-maintained corpora. We aim to credit each one explicitly, accurately, and in a form that other researchers can cite back.

## How attribution is organized

Attribution lives in two parallel registries, both colocated with the data they describe:

| Registry | Path | What it answers |
| --- | --- | --- |
| **Sources** | [`datasets/sources/`](./sources/README.md) | *Where did this data come from?* — origin, license, retrieval date, BibTeX entry, scope of coverage. One file per upstream source. |
| **Strategies** | [`datasets/strategies/`](./strategies/README.md) | *How did we transform it?* — algorithms, decisions, trade-offs, evaluation evidence, and the prior work each method builds on. One file per methodology. |

Both registries follow the same convention (see the [contribution rules](#contribution-rules) below):

1. One markdown file per source or strategy.
2. **BibTeX-style front-matter** + a prose body. The front-matter is machine-readable so a credits page and an MCP discovery manifest can be generated from it (see [`scripts/build-credits.ts`](../scripts/build-credits.ts)).
3. A short paragraph of human-readable context — *what we use it for, what we changed, what we didn't*.

## Generated credits

The canonical, always-up-to-date credits page is generated from the front-matter of every file under `datasets/sources/` and `datasets/strategies/`:

```bash
npm run build:credits
# writes datasets/CREDITS.md (do not hand-edit)
```

`datasets/CREDITS.md` is the file we link from the application footer, the GitHub README, and any external publication. **Edit the source files, not the generated output.**

## Contribution rules

If your PR ingests, transforms, or references a new data source — or introduces a new algorithm/methodology — it must include or update the corresponding registry file in the **same PR**. The checklist:

- [ ] If a new external source is ingested: add `datasets/sources/<slug>.md` using [`_TEMPLATE.md`](./sources/_TEMPLATE.md).
- [ ] If an existing source's scope or license changes: update its file's front-matter.
- [ ] If a new methodology is introduced: add `datasets/strategies/<slug>.md` using [`_TEMPLATE.md`](./strategies/_TEMPLATE.md).
- [ ] Re-run `npm run build:credits` and commit the regenerated `datasets/CREDITS.md`.

Reviewers should treat a PR that touches `datasets/` without a matching registry update the same way they'd treat a PR that adds code without tests: send it back.

## Why we go to this trouble

Three reasons, in order of practical importance:

1. **Licensing integrity.** Most of our upstream sources carry obligations (attribution, share-alike, non-commercial). A single registry makes those obligations visible, auditable, and harder to accidentally violate when the dataset is republished or fed to downstream tools.
2. **Scholarly trust.** The framing of the project ([anti-sectarian, curation-not-broadcast](../README.md)) only works if every claim is traceable to a named source. The registry is what makes "we trust this grading because…" a finishable sentence.
3. **Reproducibility.** Strategy files document not just *what* algorithm we use but *what we evaluated against* and *why we picked it* — so the next contributor (human or AI) can re-evaluate when better methods land.

## Quick links

- [Sources index](./sources/README.md)
- [Strategies index](./strategies/README.md)
- [Source template](./sources/_TEMPLATE.md)
- [Strategy template](./strategies/_TEMPLATE.md)
- [Credits generator](../scripts/build-credits.ts)
