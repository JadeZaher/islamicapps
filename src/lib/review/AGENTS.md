# src/lib/review — the review model's shared code

Design and rationale: `docs/review/README.md`. Schema proposal: `docs/review/schema-proposal.ts`.

| File | What |
| --- | --- |
| `procedures.ts` | The registry of every AI review: rule procedures (by kind of claim) and specialist reviewers. The single source for `/method`, `docs/review/ai-review.md` and the coverage test |
| `generate-doc.ts` | Renders `docs/review/ai-review.md` (`--check` fails on drift). Never edit that file by hand |
| `claim-key.ts` | Claim kinds, the key grammar per kind, content hashes, review fields |
| `summary.ts` | The display summary of one claim's reviews (counts by stance; "Reviewers differ"; stale reviews listed, not counted) |
| `citation-standard.ts` | The one citation standard as code (`docs/review/citations.md` is its prose) |
| `perspectives.ts` | Row kinds, aspects and grouping of the perspectives matrix |

## Claim keys

A key names what is asserted, never the row that proposed it: `identity|<mention>|<narrator>`, not a candidate id.
So a review survives a new method version, a second source proposing the same identity, or a reload that retires
and re-emits a candidate. The same reasoning already keys `report_correspondence_decisions` on the pair. Hadith ids
may contain `|` (OpenITI), so each kind's pattern names its parts. Correspondence pairs are in byte order, matching
the database's `collate "C"` check.

## Summary

One view per reviewer (a superseded or retired review is history), counted only when bound to the claim's current
content hash. No percentage, weight or net score; "verified" and "confirmed" never appear in a label (the test checks).

## Coverage test

`__tests__/review.test.ts` discovers the review-bearing enums at run time: a new basis, class or state fails until
`procedures.ts` covers it or `NOT_AI_REVIEWED` gives the reason. It also checks prompt hashes against
`reviews/ai/specialists.json` and the generated doc against the data.

Run: `npx tsx src/lib/review/__tests__/review.test.ts`.
