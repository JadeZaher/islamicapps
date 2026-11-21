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
| `isnad.ts` | Mention-keyed chain graph from `public_chain_links`; `chainNodesJson` (shared by the family read) and `REVIEW_CHAIN_RELATIONS` |
| `correspondence.ts` | `getReportFamily`: a report, every telling the display rule links to it, and all their chains, in one statement |
| `correspondence-review.ts` | Curator family preview, review queue, one pair with both texts and its decision history |
| `correspondence-decisions.ts` | `decideCorrespondence`: confirm / reject / uncertain, retire-and-supersede, audit row |
| `family-graph.ts` | Pure, client-safe: the combined transmission graph (merge rule, layered layout, compact mode) and the summary counts |
| `narrator.ts`, `assessment.ts` | Narrator list/search/detail/network/typeahead; verdict and grade fragments |
| `narrator-sources.ts` | An external record or the Imam register's record, link candidates, and the paged chain positions naming a narrator |
| `identity-groups.ts` | Pure, client-safe: candidates grouped by person key, `mentionIdentity`, basis order |
| `history.ts`, `location.ts`, `commentary.ts`, `comparative.ts` | Reads and curated writes per area |
| `curation.ts` | Section 9.3 writes: bio and verdict status, rights, surface decisions, absences, network refresh |
| `write.ts` | `curationWrite` envelope and `audit` |
| `*-review.ts` | Reviewer-mode reads of base tables; importable only from `/admin` and curation actions (rule 9, linted) |
| `health.ts` | `select 1` under a timeout |
| `dataset.ts` | `getPreviewNotice`: is the current version a non-release served under owner approval |
| `hadith-export-review.ts` | Curator CSV export batches (live base tables); only `/api/export/hadiths` imports it |
| `enums.ts` | Enum value lists for zod in actions |
| `visibility.ts` | `ReadVisibility` and `hadithRelationsFor` / `verdictModeFor`: the one public-vs-curator-preview switch |
| `browse.ts` | Works by tradition, work and book outlines, reports in source order, a report's context (trail, previous/next) |
| `dataset-version.ts` | Current dataset version stamp; `isIndexable` (crawl policy) |
| `sources.ts` | Counts per source for `/sources` (works, reports, identity claims, narrators); no text |

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
  (`REVIEWED_CITATION`). The lexicon's prose bio is never returned on public pages; its dates and places are (see
  §Lexicon on public narrator pages).
- **Writes** run in `curationWrite(actor, ...)`: one transaction, `lock_timeout 3s`, refused while any
  `dataset_versions.load_status = 'loading'`, constraint violations mapped to `CurationError` codes, never retried.
  Every write appends `curation_audit` with before/after images in the same transaction. Updates go through
  `allowlistedPatch` (absent key = untouched, sent `null` = cleared). "Delete" retires the row and its live link
  rows; retiring a faith, source text or location is refused while live rows reference it.
- **Publication gates:** commentary `published` needs a live reviewed citation (no owner commentary policy is
  recorded, question 10); parallel `published` needs its hadith in `public_hadiths`, and a new manual parallel
  starts `published` only when that holds; bio/verdict `published` need the citation (and a tradition).
- **Chain nodes** are keyed by mention ID. Every node carries its surface as written, its Latin form and basis
  (`name_latin`, `name_latin_basis`, `name_latin_narrator_id`), what set a standing identity (`standing_basis`), and all
  its identity candidates from `public_chain_mention_candidates_v2` (every basis, with `source_ref`, `origin`, `tier_basis`,
  the record's authority, placeholder and label reason, and a person key from `PERSON_KEY_SQL`), plus `identity`
  (`unidentified`, `agreed`, `differ`: differ only when one registry's records are known to name different people;
  `identity-groups.ts`). Narrator name and verdict on the node itself are filled only on a standing identity
  (machine-reviewed or verified by a reviewer) (`src/db/AGENTS.md` §External identity). No chain-health score is
  computed (no computed grade).

## Narrator sources (`narrator-sources.ts`)

`getNarratorSourceRecord` reads `narrator_source_profiles` with the record's crosswalk ids and lexicon link candidates;
verdict-like dataset fields (hadith-kg `rank`, tadlis and ikhtilat flags, Riwayat `madhhab`) are dropped in the mapper and
never reach a page. `getNarratorAppearances` pages every public chain position naming the narrator as a standing identity
or a candidate (25 a page, count capped), in source order; it reads only public views. `getExternalLinkCandidates` lists,
on a lexicon narrator's page, the external records a link candidate proposes as the same person. Teachers and students
stay `getNarratorNetwork` (`narrator_transmissions`), which now includes machine-reviewed external and Imam identities.

## Report families

- **English.** Each telling carries its public English (`public_translations`, or live rows in reviewer mode) with
  `englishAttribution` from `hadith.ts`, so the family view labels and credits it exactly like the report page.
- **One round trip.** `familyStatement` ranks the corresponding reports (reviewer-confirmed first, then same wording,
  variant, partial, then Jaccard, then id in byte order), caps them at `FAMILY_CAP` = 60 (the largest star cluster
  holds 61) and returns the tellings and every chain node with its candidates as JSON. `capped` and
  `correspondences_total` say when tellings were left out. Nothing is returned when the report itself is not visible.
- **Public and reviewer reads share the statement**, parameterised by `FamilyRelations`: public views, or live base
  tables (`REVIEW_FAMILY_RELATIONS`, `REVIEW_CHAIN_RELATIONS`). The reviewer chain relation mirrors
  `public_chain_links`' standing-identity predicate (drizzle/core/0006); keep the two in step.
- **Numbering** (audit 2026-11-21 on the development database). Thaqalayn's stored `hadith_no` is the chapter number
  on every row, so it disagrees with the number in the text (al-Kafi 10,890 of 11,035 numbered texts; Man La Yahduruhu
  5,865 of 5,866; Al-Khisal 1,266 of 1,281; 'Uyun 937 of 952; Al-Amali (Saduq) 985 of 989); the report's own number is
  the provider URL's last segment, read by `src/lib/citation/reference.ts`. Musnad Ahmad has 3,616 distinct numbers for
  23,529 rows (485 non-numeric, such as `1]`) and Musnad al-Shafi'i none: `UNCITABLE_NUMBERING_WORKS` sets
  `numbering_citable = false` and the view shows the stable record id. The projection still stores the chapter number in
  `hadith_no` (a separate column needs a migration that recreates `public_hadiths`; deferred).
- **Visibility.** `getVisibleReportFamily(id, visibility)` and `getChainGraph(id, visibility)` resolve their relations
  from the request visibility (`familyRelationsFor`, `chainRelationsFor`, hadiths through `hadithRelationsFor`); public
  is the default. `CURATOR_FAMILY_RELATIONS` serves only the /admin review screens.
- **Graph merge rule** (`family-graph.ts` `mergeKey`): a name merges only on its standing identity
  (`chain_mentions.narrator_id`, machine-reviewed or reviewer-verified). Every other name is one node per mention,
  identical text or not, so nothing merges across traditions except through such an identity. Layout: longest-path
  layers from the originator (Kahn), work nodes pinned to the bottom, barycentre ordering in four sweeps with key
  tie-breaks (deterministic; a flow asserts it). Compact mode folds runs of names only one chain passes through.

## Visibility

Every visibility-aware read takes a `ReadVisibility` and asks `hadithRelationsFor(visibility)` for its relations:
public views, or the live base tables for a curator under private preview. The curator variant is a branded type
minted only by `src/lib/auth/visibility.ts` after verifying the session (see `src/lib/auth/AGENTS.md` §Read
visibility). `getVisibleHadith`, `searchVisibleHadiths`, `getVisibleNarrator` and all of `browse.ts` use it;
`getPublicHadith` / `searchPublicHadiths` are the public shorthands. Not yet visibility-aware (other owners):
`isnad.ts` (`getChainGraph` reads `public_chain_links`), `comparative.ts`, `correspondence.ts`, so under private
preview an uncleared report shows its text but an empty chain.

## Source order

`SOURCE_ORDER` in `browse.ts` is the one definition of a report's place in its work, a `bigint[]` plus `id collate
"C"`: K6 by `source_record_id` (the K6 file's row order), Thaqalayn by (provider file, provider hadith id), OpenITI by
the parsed number then its letter suffix, Pure Canon by `hadith_no_int` (no source order exists in that copy: `pc_*`
ids are alphabetical by Arabic). It is an expression, so ordering scans the work's rows (largest: 23,529, about 0.3 s
on the development database); a loaded `source_order` column with an index on `(collection_id, source_order)` would
replace it. The list ordering contract above (`collection_sort_key, hadith_no_int`) is for search results only: it
interleaves chapters in works whose numbering restarts.

## Lexicon on public narrator pages (owner decision 2026-11-21)

`getNarratorDetail` in public mode returns the lexicon's birth and death years (Hijri, Gregorian), places, region and
`source_locator`, never `bio` or `lexicon_grade_label`. `LexiconRecord` (`src/app/narrator/[id]/components/`) labels
them "Narrator lexicon, not yet cited" (linking `/glossary#rijal`) with an `MSD` reference naming the entry. A recorded
year 0 is dropped (the Hijri count has none).

- **Held back.** `lexicon-held-back.json` (built by `src/scripts/db/build-lexicon-held-back.ts` from
  `diagnostics/biography-verification/lexicon_source_comparisons.jsonl.gz`, input hash recorded) lists the 61 death years
  Ibn Hajar's Taqrib contradicts by three years or more (gross conflict 28, exactly a century 13, 3-10 years 20). The
  mapper removes both death years for those narrators and returns `held_back` with the reason and Taqrib entry; the page
  says the year is held back until reviewed and credits `RIJ`. Reviewer mode is unchanged (everything, unlabelled).
- **Not shown, because not loaded.** Generation (tabaqa) markers: `narrator_lexicon_profiles.tabaqah_raw` is null on
  every row of projection `2026.11.21.3`. Cited (Taqrib, Tahdhib) values: candidates only, not in any table yet. The
  narrator timeline (`timeline.ts`) still draws only cited public bounds.

## Rights decisions

`recordRightsDecisions(actor, decisions)` (`curation.ts`) writes many works in ONE `curationWrite` transaction: it
refuses a work that is not loaded and a loaded work without a decision (so no partial record commits), skips a work whose
live row already says the same (no write, no audit row: a re-run is a no-op), and otherwise upserts and audits
`set_rights` per work, sharing `upsertRights` with `setCollectionRights`. The operator script is
`src/scripts/db/record-rights.ts` (`npm run db:record-rights -- --database <development|production> [--confirm-production]`),
actor `system:owner-decision`; each row's `rights_note` names the owner decision and the rights-register section, and
`citation` names the source record on `/sources`.

## Preview approval

A non-release dataset version is public only while `dataset_versions.public_override_*` is set (the gate in
`public_hadiths`). The operator script `src/scripts/db/approve-preview.ts` (`--by`, `--reason`; `--revoke`) writes the three
columns and an `approve_preview` / `revoke_preview` row in `curation_audit` (actor `system:owner`) in one transaction; it
refuses a load in progress, a release version, and a second approval, and refuses the production database unless given
both `--database production` and `--confirm-production` (`src/db/target-database.ts`). `getPreviewNotice()` reads the same
predicate, so the site-wide notice (`src/components/PreviewNotice.tsx`) turns itself off when a release version becomes
current or the approval is revoked. Temporary: see `conductor/RUNBOOK.md`, "Remove after the first release".

## Time and place

Files: `timeline.ts` (reads), `timeline-rules.ts` (pure rules, client-safe),
`timeline-contracts.ts` (types), `history-seed.ts` and `biography-seed.ts` (seed writes), `epoch.ts` (admin).

- **Visibility.** `getNarratorTimeline(id, visibility)` and `getChainFamilyTimeline(ids, visibility)` take a
  `ReadVisibility`; reports come from `hadithRelationsFor(visibility)`, chains from the public views or the live base
  tables. Public: no lexicon field; a bio only when `published` with a live reviewed citation; eras and events only from
  `published_epochs` / `published_historical_events`; places only at reviewed locations. Interval relations use only
  those public bounds, so nothing hidden leaks through an overlap. Curator (private preview only): every live row,
  each claim labelled with its `DatumBasis`.
- **Claims, not values.** Each recorded year is a `DateClaim` with its basis; lexicon and bio death years are separate
  claims, and when they differ the death range spans both and `competing` is set (Sufyan b. ʿUyayna: lexicon 196, bio
  198). A recorded 0 is listed but never drawn or compared: the Hijri count has no year 0 (121 lexicon death years are 0).
- **Life relation** (`relationToLife`), on the most permissive bounds: both bounds known means overlap with
  `[earliest birth, latest death]`; only a death year means the interval contains it (`at_death`); only a birth year,
  likewise (`at_birth`); nothing known means nothing. This is deliberately stricter than design section 5.9 (and
  `history.ts` `getHistoricalEventsForNarrator`), where a death-only narrator overlaps every earlier event. A generation
  is never turned into years. Eras use outer bounds (earliest start, latest end; null end means continuing).
- **Chronological gap rule** (`chronologicalGaps`), per consecutive pair (teacher at position p+1, student at p), only
  when both are a verified link or a single agreed candidate: (1) one's earliest recorded birth is after the other's
  latest recorded death; (2) their broad generation classes (Prophet, Companion, Follower, Follower of the Followers,
  third century, fourth century or later) differ by more than one step. The statement names each date's basis and is
  never a verdict. On the development database (2026-11-21) it flags 2,431 of 114,597 chains (1,057 where both links are
  verified) in 2,224 reports; many flags point at source-index identities that cannot be right (k6:813: Qutayba,
  b. 150, "from" Bakr al-Muzani, d. 106).
- **Seed rule** (`history-seed.ts`): insert as `unverified_seed`; refresh content only while still `unverified_seed`,
  not publication-ready and live; anything else is `keptCurated`. Canonical JSON comparison (jsonb reorders keys) keeps
  re-runs at zero writes. The admin editors move a seed row to `unverified` on save, so a curator's edit is never
  refreshed away. Bios and verdicts are insert-only (`on conflict do nothing`).
- **Epochs** ship with a pending migration (`src/db/ops/pending/`). `epochsAvailable()` checks `to_regclass('epochs')`
  (cached once present), so every read works before and after it is applied.

## Tests

`__tests__/flows.test.ts` builds the real migration stream into a private schema (`query_fixture`) of the
development database (`fixture-database.ts`, refusing production), loads real rows copied from the 2026-11-21
bundle (`fixtures/corpus.json`: 14 hadiths across the four traditions, 53 mentions, 12 narrators, two Majlisi
grades, one Phase-0 verdict), and sets `DATABASE_URL`'s `search_path` to it so the app client runs unchanged.
`__tests__/correspondence-flows.test.ts` loads `fixtures/correspondence.json` (nine real reports around Sunan Abi Da'ud
`k6:19122`: Sunni and Imami tellings and an Ibadi pair below the threshold, cut from projection `2026.11.21.3` by
`datasets/hadith-data/pg_export/slice_correspondence_fixture.py`) into its own schema and drives the family read,
curation and graph, then `/hadith/[id]/chains` over `next start` (needs a build).
`fixtures/identity-candidates.json` adds the real identity candidates and verified links for those reports from the
2026-11-21 projection (`generated_from` names it), plus Sahih Muslim `k6:10008`, whose chain has an agreeing, a
disagreeing, an unidentified and a kunya-only name.
`__tests__/http-gate.test.ts` drives the proxy, sign-in and actions over HTTP against `next start` (with `AUTH_ENABLED=1`).
`__tests__/browse-flows.test.ts` (schema `browse_fixture`): reading in order across a page boundary, previous/next at
the ends, addresses and the legacy redirect, citation with dataset version and source credit, visibility rules,
switches, and source-record coverage. `__tests__/switches-http.test.ts`: auth off (404s, no links), private preview
(redirects, noindex, curator sees unpublished rows under the banner), crawl policy, and the start-up refusal.

```
npx tsx --conditions=react-server src/db/queries/__tests__/flows.test.ts
npx next build && npx tsx --conditions=react-server src/db/queries/__tests__/http-gate.test.ts
npx tsx --conditions=react-server src/db/queries/__tests__/correspondence-flows.test.ts   # after a build
npx tsx --conditions=react-server src/db/queries/__tests__/timeline.test.ts   # schema timeline_fixture, ~2 min
```

`--conditions=react-server` lets `server-only` load outside Next.js.
