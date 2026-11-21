# src/db/queries — the only place SQL lives

Design: `docs/architecture/data-architecture.md` sections 3, 7, 8, 9, 10.2, 11.3. Files under `src/app/**` may import
these modules but never `drizzle-orm`, `postgres`, `@/db/client` or `@/db/schema` (lint, `eslint.config.mjs`).

## Layout

| File | What |
| --- | --- |
| `sql-helpers.ts` | `clampPage`, `paginated`, `escapeLike`, `withReadRetry`, `resolveTraditionCode`, `COUNT_CAP` |
| `contracts.ts` | Read contracts (section 9.4). Types only, safe for client components |
| `mappers.ts` | One mapper per entity; snake_case keys and the legacy aliases the UI reads |
| `hadith.ts` | Public browse, search, detail (public views only) |
| `isnad.ts` | Mention-keyed chain graph from `public_chain_links` |
| `narrator.ts`, `assessment.ts` | Narrator list/search/detail/network/typeahead; verdict and grade fragments |
| `history.ts`, `location.ts`, `commentary.ts`, `comparative.ts` | Reads and curated writes per area |
| `curation.ts` | Section 9.3 writes: bio and verdict status, rights, surface decisions, absences, network refresh |
| `write.ts` | `curationWrite` envelope and `audit` |
| `*-review.ts` | Reviewer-mode reads of base tables; importable only from `/admin` and curation actions (rule 9, linted) |
| `health.ts` | `select 1` under a timeout |
| `enums.ts` | Enum value lists for zod in actions |

## Rules as implemented

- **One round trip per page section.** List reads are one statement that returns `{counted, items}`: a
  `not materialized` CTE of matching IDs feeds both a capped count (`limit COUNT_CAP + 1`) and the ordered page,
  and `json_agg` builds the rows, so a page past the end still reports its total. Nested data (verdicts, grades,
  links, motif tags) is a correlated `json_agg` subquery, never a join that multiplies rows.
- **One ordering contract** for hadith lists: `collection_sort_key, hadith_no_int nulls last, id`.
- **Search** (section 7.3) is a `union` of index-driven ID sets: trigram `ilike` on `chapter_title_folded` and
  `category_folded` (term folded in SQL with `lower(unaccent())`, the loader's folding), `websearch_to_tsquery`
  on English, and `text_ar_normalized ilike` with the term through the TypeScript `norm()` when it contains
  Arabic. Trigram branches need 3 characters. Public search reads `public_hadiths` / `public_translations`;
  reviewer search the live base tables, through the same builder (`HadithRelations`).
- **Verdicts are public** only when `published`, tradition-scoped and citing a live reviewed citation
  (`REVIEWED_CITATION`). The lexicon (dates, bio) is never returned on public pages (question 4).
- **Writes** run in `curationWrite(actor, ...)`: one transaction, `lock_timeout 3s`, refused while any
  `dataset_versions.load_status = 'loading'`, constraint violations mapped to `CurationError` codes, never retried.
  Every write appends `curation_audit` with before/after images in the same transaction. Updates go through
  `allowlistedPatch` (absent key = untouched, sent `null` = cleared). "Delete" retires the row and its live link
  rows; retiring a faith, source text or location is refused while live rows reference it.
- **Publication gates:** commentary `published` needs a live reviewed citation (no owner commentary policy is
  recorded, question 10); parallel `published` needs its hadith in `public_hadiths`, and a new manual parallel
  starts `published` only when that holds; bio/verdict `published` need the citation (and a tradition).
- **Chain nodes** are keyed by mention ID. Narrator name and verdict are filled only on verified links; an
  unidentified position carries only its surface. No chain-health score is computed (no computed grade).

## Tests

`__tests__/flows.test.ts` builds the real migration stream into a private schema (`query_fixture`) of the
development database (`fixture-database.ts`, refusing production), loads real rows copied from the 2026-11-21
bundle (`fixtures/corpus.json`: 14 hadiths across the four traditions, 53 mentions, 12 narrators, two Majlisi
grades, one Phase-0 verdict), and sets `DATABASE_URL`'s `search_path` to it so the app client runs unchanged.
`__tests__/http-gate.test.ts` drives the proxy, sign-in and actions over HTTP against `next start`.

```
npx tsx --conditions=react-server src/db/queries/__tests__/flows.test.ts
npx next build && npx tsx --conditions=react-server src/db/queries/__tests__/http-gate.test.ts
```

`--conditions=react-server` lets `server-only` load outside Next.js.
