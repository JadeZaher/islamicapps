# Contributing to Shura wa Istehsan

Shura wa Istehsan is an anti-sectarian, curation-first archive of hadith and Islamic history, built by request and by invitation. If you'd like to contribute — text, code, scholarship, review, or infrastructure — this file is the entry point.

Contributions are accepted via:

- **GitHub pull requests** to this repository (code, documentation, dataset transforms, evaluation work).
- **Dataset additions or amendments** routed through the [data registry](#data-attribution-is-mandatory) below.
- **Direct request** for MCP server access for AI-driven research, at cost or free; see the project README.

We welcome contributors of every tradition and background. Tradition-specific work (Sunnī, Shīʿī, Zaydī, Ibāḍī gradings, isnād reconciliation, biographical enrichment) should be presented as **parallel coverage across traditions** — never as one tradition being the default.

---

## Data, attribution, and methodology are mandatory

This is the single rule that, if you remember nothing else from this file, please remember:

> **Any PR that ingests, transforms, or references a new data source — or introduces a new algorithm / methodology — must include or update the corresponding registry file in the same PR.**

The registries live under `datasets/`:

- [`datasets/sources/`](./datasets/sources/) — one file per upstream data source (license, BibTeX, scope, retrieval date, what we changed).
- [`datasets/strategies/`](./datasets/strategies/) — one file per algorithm / methodology / pipeline mode (problem, approach, evaluation, prior work).
- [`datasets/ATTRIBUTION.md`](./datasets/ATTRIBUTION.md) — the contributor-facing summary of the whole convention.
- [`datasets/CREDITS.md`](./datasets/CREDITS.md) — **generated**, do not hand-edit. Regenerate with `npm run build:credits`.

### Quick checklist

- [ ] New external source? → add `datasets/sources/<slug>.md` from [`_TEMPLATE.md`](./datasets/sources/_TEMPLATE.md).
- [ ] Existing source's scope or license changed? → update its front-matter.
- [ ] New methodology / algorithm / pipeline mode? → add `datasets/strategies/<slug>.md` from [`_TEMPLATE.md`](./datasets/strategies/_TEMPLATE.md).
- [ ] Existing strategy got re-evaluated? → update its `last_reviewed` and `evaluation_results`.
- [ ] Ran `npm run build:credits` and committed the regenerated `datasets/CREDITS.md`.

### What reviewers will check

A PR that touches `datasets/` without a matching registry update will be sent back, the same way a PR that adds code without tests would be. Specifically:

- Every source file must have valid BibTeX front-matter that builds via `npm run build:credits`.
- License field must be filled in (use `unstated` if genuinely unknown, plus a `license_notes` block explaining what we *do* know).
- Strategy files must name the sources they consume and the prior work they build on.
- Generated `datasets/CREDITS.md` must be in sync with the registry files.

### Why we go to this trouble

Three reasons, in priority order:

1. **Licensing integrity.** Many upstream sources carry obligations (attribution, share-alike, non-commercial). The registry makes those visible and auditable.
2. **Scholarly trust.** The project's anti-sectarian, curation-first framing only works if every claim is traceable. "We trust this grading because…" needs to be a finishable sentence.
3. **Reproducibility.** Strategy files document not just *what* algorithm we use but *what we evaluated against* and *why we picked it*, so the next contributor can re-evaluate when better methods land.

---

## Code contributions

- **Stack:** Next.js 16 + TypeScript, Neo4j for the graph, Python for dataset transforms.
- **Scripts:** new TypeScript scripts go under `src/scripts/` and (if user-facing) get an npm-script entry in `package.json` matching the existing `db:*` / `build:*` conventions.
- **Tests:** the regen pipeline has tests under `src/scripts/__tests__/`. Run with `npm run test:regen`. Dataset-transform tests live under `datasets/hadith-data/__tests__/`.
- **Data files:** never delete data files. Back up, move, or archive instead — purge from the DB only on explicit request. (See project memory.)
- **Style:** match existing patterns. No comments unless the *why* is non-obvious. No new dependencies without a reason.

## Dataset contributions

- **Backups before edits.** Existing `datasets/hadith-data/*.csv` files have a `.bak-<timestamp>` convention. Preserve it.
- **Provenance.** New per-collection data lands with a `PROVENANCE.json` recording source ID, parse date, and parser version (see `datasets/hadith-data/zaydi-hadith/PROVENANCE.json` for the shape).
- **Encoding.** Arabic text in NFC, UTF-8 everywhere. Word-boundary regex on Arabic needs `(?![ء-ي])` (JavaScript `\b` is ASCII-only). See project memory.

## How to be added as a contributor

By request or invitation. Open an issue introducing yourself and what you'd like to work on, or reach out via the project's contact channel listed in the README. We do not require any specific scholarly credential — domain knowledge, technical skill, and willingness to work within the anti-sectarian framing are what matter.
