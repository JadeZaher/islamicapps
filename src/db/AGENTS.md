# src/db — PostgreSQL + Drizzle data layer

Design source of truth: `docs/architecture/data-architecture.md` (sections 3, 4, 5, 7, 11). This file holds
the rationale that code comments point to, plus every decision taken while implementing step 4.
`src/lib/db/AGENTS.md` describes the outgoing Neo4j layer; its still-valid invariants are carried over below.

## Layout

| Path | What |
| --- | --- |
| `schema/enums.ts` | All 35 enums of section 5.2 |
| `schema/columns.ts` | Pipeline, curation and link bookkeeping column groups; `restrictForeignKey`; `isLive` |
| `schema/operations.ts` | `dataset_versions`, `curation_audit` |
| `schema/corpus.ts` | traditions, sources, collections, collection_rights, books, chapters, hadiths, translations; `public_hadiths`, `public_translations` view declarations |
| `schema/narrators.ts` | narrators, narrator_lexicon_profiles, narrator_aliases, narrator_teachers |
| `schema/evidence.ts` | bibliographic_works, editions, citations |
| `schema/isnad.ts` | chains, chain_mentions, chain_absence_dispositions, narrator_surface_decisions; `narrator_lifespans`, `narrator_transmissions`, `public_chain_links` declarations |
| `schema/assessments.ts` | hadith_assessments, narrator_assessments, narrator_bios |
| `schema/history.ts` | locations, historical_events, narrator_events, narrator_locations; `published_historical_events` declaration |
| `schema/commentary.ts` | commentaries, commentary_hadiths, commentary_narrators |
| `schema/comparative.ts` | religious_traditions, schools_of_thought, source_texts, cross_parallels, motif_tags, four link tables, parallel_research_runs |
| `client.ts` | The app's only client (server-only, lazy, globalThis-cached, max 5) |
| `connection-options.ts` | `DATABASE_URL` check and TLS rule, shared by client, migrator and verify |
| `migrate.ts` | Programmatic migrator (`npm run db:migrate`); the pre-deploy command bundles it to `migrate.mjs` |
| `verify.ts` | Catalog verification (`npm run db:verify`); exits 1 on any mismatch |
| `advisory-locks.ts` | Fixed advisory-lock keys |
| `ops/indexes-heavy.sql` | Concurrent heavy index builds, run by an operator after a load. Never a migration |
| `../../drizzle/core/` | The single migration stream (generated plus hand-written SQL) |

## Ownership and the reload contract

Every table has one owner class (section 4.1). Pipeline tables carry `first_seen_/changed_in_/retired_in_dataset_version_id`,
`updated_at`, `retired_at`; a reload upserts by stable ID and retires by anti-join, never deletes. Curation
entity tables carry `created_/updated_/retired_ at/by`; curation link tables carry an identity `id`,
`created_at/by`, `retired_at/by` and a partial unique index on the linked pair `where retired_at is null`.
Nothing is hard-deleted (owner rule); every foreign key is `on delete restrict`, so an accidental delete
fails loudly instead of cascading.

Derived columns on pipeline tables (`chain_mentions.narrator_id/resolution/link_kind/decision_id`,
`hadiths.source_text_status/chain_status/grading_status`, `chains.verified_link_count`) are written only by
the loader and by the SQL functions. Facet defaults are the worst state, so a freshly inserted row is never
shown as better than it is.

## Verified link (one predicate, three places)

A mention is a verified link when `resolution in ('exact_registry','human_verified','derived_relation_verified')`
and `narrator_id` points at a live narrator. The same predicate is written in `public_chain_links`
(`drizzle/core/0003_views.sql`) and twice in `refresh_publication_facets` (`0004_functions.sql`). If the
owner approves `source_index` (question 1) or `mention_exact` transmissions (question 11), change all of them
in one migration. `narrator_transmissions` keeps its own stricter basis rule from section 5.5.

## Migrations

- One stream, `drizzle/core`, applied by `src/db/migrate.ts`: `lock_timeout 5s`, `statement_timeout 60s`,
  the data-write advisory lock, three retries on lock timeout. The drizzle 0.45.4 migrator runs all pending
  migrations in ONE transaction (verified in `pg-core/dialect.js`), so `create index concurrently` can never be
  a migration: heavy indexes live in `ops/indexes-heavy.sql`.
- Order: `0000_extensions` (pg_trgm, unaccent; idempotent) -> `0001_core_schema` (generated) ->
  `0002_table_storage` (fillfactor 90) -> `0003_views` -> `0004_functions`.
- Hand-written migrations are created with `npx drizzle-kit generate --custom --name=<name>` so the journal
  and snapshot stay consistent; views are declared in TypeScript with `.existing()` so drizzle-kit ignores them.
- Expand only (section 2.6). Views written as `select h.*` freeze their column list at creation: adding a
  column to `hadiths` or `translations` needs the dependent public views recreated in the same migration.
  `narrator_transmissions` depends on `narrator_lifespans`; redefining lifespans means drop and recreate the
  materialized view (and its two indexes) in that migration.
- `pgvector` is installed on the Railway database but is created by the step 11 migration, not here.

## Locks

`DATA_WRITE_LOCK_KEY = 4741100001` (migrator and loader, session-level). `NETWORK_REFRESH_LOCK_KEY = 4741100002`
(`refresh_network`, transaction-level). `refresh_network()` takes the data-write key **shared** with
`try`: another session's load or migration makes it return false, while the loader's own session (which holds
the key exclusively) can still call it. The literals are duplicated in `0004_functions.sql`.

## Client

`getDatabase()` creates the postgres.js pool on first use, never at import (so `next build` never connects),
and caches it on `globalThis` so dev hot reload does not multiply pools. `db` is a Proxy over it. Options per
section 3.3: `max 5`, `idle_timeout 20`, `connect_timeout 5`, prepared statements on (no transaction pooler).
On SIGTERM it ends the pool with a 5 s timeout and exits only when no other SIGTERM listener (Next.js) exists.
Scripts (`migrate.ts`, `verify.ts`) never import `client.ts`: `server-only` throws outside the react-server
condition.

## Carried over from src/lib/db/AGENTS.md (still valid)

- Narrator and event scalar fields are compatibility projections, not publication evidence. No loader may treat a
  provenance tag, a raw date string or an unverified seed marker as a citation.
- The historical publish gate (`publication_ready`, `human_verified`/`source_verified`, nonblank
  `citation_source`, nonblank `citation_locator` or `citation_url`) is now enforced twice: the
  `historical_events_publication_gate_check` constraint on write and `published_historical_events` on read.
- The history seed may refresh an event's content only while it is `unverified_seed` and not
  `publication_ready`. A changed seed definition for a reviewed or published event needs a new review.
- Competing evidence is never collapsed: separate assertion rows, lifespans as ranges. A cited unknown or open
  range is valid; an exact year is never invented.
- Narrator-by-event overlap is computed at read time on `narrator_lifespans` x `published_historical_events`;
  no overlap rows are stored. Only direct involvement (`narrator_events`) is persisted.
- Stable unique keys for people, works, editions, citations, assertions, events and epochs (section 4.2).

## Decisions made during implementation (step 4)

Where the doc was ambiguous or contradicted the orchestrator brief, the stricter reading was chosen.

1. **Layout.** Schema files are flat in `src/db/schema/<domain>.ts` (orchestrator brief) instead of the doc's
   `schema/core/`; migrations stay in `drizzle/core` (doc). `narrator_bios` lives in `assessments.ts`,
   `parallel_research_runs` in `comparative.ts`, `dataset_versions` and `curation_audit` in `operations.ts`.
2. **Only the 41 launch tables are declared.** The doc says schema files for the 7 later tables exist from
   step 4, but declaring them would make drizzle-kit migrate them. Each later table (`translation_candidates`,
   `resolution_review_units`, `narrator_same_as`, `biographical_assertions`, `temporal_assertions`, `epochs`,
   `hadith_embeddings`) is declared together with its migration. No launch table has a foreign key into them.
3. **All 35 enums are created,** including `calendar`, which only later tables use (harmless, expand-only).
4. **Explicit constraint names** (`<table>_<column>_fk`, `_key`, `_check`, `_idx`): drizzle's default FK names
   exceed Postgres's 63-byte limit and would be truncated silently.
5. **Every FK is `on delete restrict`;** the doc states no other behaviour anywhere.
6. **`chain_absence_dispositions` carries curation bookkeeping.** Its table omits the line, but section 5.1 puts
   it on every curation entity table.
7. **Public override is all-or-none over three columns:** `num_nonnulls(public_override_by, public_override_reason,
   public_override_at) in (0, 3)` (the doc's check names only by and reason) and only on `non_release`.
8. **Surface decision target is an equivalence:** `target_narrator_id` is set if and only if the kind is
   `same_as` or `derived_relation` (the doc says "required for"; a collective or anonymous decision with a
   target would be incoherent, since replay assigns no narrator).
9. **`cross_parallels.status` has no column default.** The doc's default depends on `origin` (`proposed` for
   `ai_research`, `published` for `manual`), which a column default cannot express; the writer must set it.
10. **Verified link requires a live narrator** (see above). Consequence: `human_verified` mentions with link kind
    `collective`, `anonymous` or `not_a_narrator` are not links, so such a chain is `partial`, not `complete`.
11. **`narrator_lifespans` before assertions ship:** death prefers a `published` bio whose citation is live and
    reviewed (section 5.8 predicate), else the lexicon; birth comes from the lexicon only (bios have no birth
    year); `basis` is the weakest source any bound came from; one row per live narrator with at least one bound;
    `claim_count = 0`, `disputed = false`.
12. **`public_hadiths`** also requires a live collection, a live `collection_rights` row and the current version's
    `load_status = 'complete'`. **`public_chain_links`** exposes `narrator_id` and `confidence` only on verified
    links and returns every live mention, so the isnad always reads as written.
13. **`grading_status`:** `collection_label` rows are ignored (they are never a grade), so "only
    `compiler_criterion` rows" means only among displayable kinds.
14. **`source_text_status`:** "blank" Arabic means no non-whitespace character; the locator fields are
    blank-trimmed too.
15. **`text_tsv`** is `to_tsvector('english'::regconfig, text)`; the explicit cast keeps the generated column
    immutable.
16. **`refresh_network()`** skips via the shared data-write lock instead of reading `load_status`, so a stale
    `loading` row cannot block it forever and the loader can call it; it stamps `network_refreshed_at` on the
    current version. Both functions have `EXECUTE` revoked from `PUBLIC`; `roles.sql` will grant it to `app_rw`.
17. **`refresh_publication_facets(hadith_ids text[])`** is implemented now (section 11.2 is fully specified);
    `apply_decision(unit_id)` is not (see Deferred).
18. **TLS:** an explicit `sslmode` in the URL wins; otherwise the doc rule (off for `*.railway.internal`,
    `require` elsewhere).
19. **`db:migrate` runs `src/db/migrate.ts`,** not `drizzle-kit migrate`, so the lock and timeouts apply locally
    exactly as in the pre-deploy command.
20. **`maintenance_work_mem = '128MB'`** in `indexes-heavy.sql` is a chosen value; the doc gives none.
21. **`db:verify` is the catalog half** of the doc's `db:verify`. The section 11.4 data invariants and the server
    settings checks join it in step 5.
22. **Environment override:** the database is Railway PostgreSQL 18.6, used directly; the doc's local
    `pgvector:pg18` container on 5442 was not set up (orchestrator instruction).

## Deferred

- `ops/roles.sql` (`schema_owner`, `app_rw`, grants, `app_rw` timeouts) and `ops/railway-tuning.sql`. The step 4
  migrations ran as the Railway template superuser, so every object is owned by it: `roles.sql` must
  `REASSIGN OWNED` / `ALTER ... OWNER TO schema_owner` before the app switches roles.
- `apply_decision(unit_id)`: written with the loader's decision replay (step 5/6) so both share one SQL path,
  including the narrower-scope-wins rule and the position - 1 condition for `derived_relation`.
- Running `ops/indexes-heavy.sql` (after the first load).
- `src/db/load/*`, section 11.4 checks, `src/db/queries/*`, `withReadRetry`, the ESLint import rule, the
  Dockerfile `migrate.mjs` bundle and `railway.json` pre-deploy command.
- The 7 later tables (decision 2).
