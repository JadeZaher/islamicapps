# src/db — PostgreSQL + Drizzle data layer

Design source of truth: `docs/architecture/data-architecture.md` (sections 3, 4, 5, 7, 11). This file holds
the rationale that code comments point to, plus every decision taken while implementing step 4.
`src/lib/db/AGENTS.md` describes the outgoing Neo4j layer; its still-valid invariants are carried over below.

## Layout

| Path | What |
| --- | --- |
| `schema/enums.ts` | The 35 enums of section 5.2, the two identity-candidate enums (0006) and the five correspondence enums (0007) |
| `schema/columns.ts` | Pipeline, curation and link bookkeeping column groups; `restrictForeignKey`; `isLive` |
| `schema/operations.ts` | `dataset_versions`, `curation_audit` |
| `schema/corpus.ts` | traditions, sources, collections, collection_rights, books, chapters, hadiths, translations; `public_hadiths`, `public_translations` view declarations |
| `schema/narrators.ts` | narrators, narrator_lexicon_profiles, narrator_aliases, narrator_teachers |
| `schema/evidence.ts` | bibliographic_works, editions, citations |
| `schema/isnad.ts` | chains, chain_mentions, chain_mention_candidates, chain_absence_dispositions, narrator_surface_decisions; `narrator_lifespans`, `narrator_transmissions`, `public_chain_links`, `public_chain_mention_candidates` declarations |
| `schema/assessments.ts` | hadith_assessments, narrator_assessments, narrator_bios |
| `schema/history.ts` | locations, historical_events, narrator_events, narrator_locations; `published_historical_events` declaration |
| `schema/commentary.ts` | commentaries, commentary_hadiths, commentary_narrators |
| `schema/comparative.ts` | religious_traditions, schools_of_thought, source_texts, cross_parallels, motif_tags, four link tables |
| `schema/correspondence.ts` | report_correspondence_candidates, report_correspondence_cluster_members, report_correspondence_decisions; `report_correspondence_shown_pairs`, `report_correspondence_display`, `public_report_correspondences` declarations |
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

## Standing identity (one predicate, three places)

Naming (owner, 2026-11-21): the automatic top tier is **machine-reviewed**, never "verified"; a sample found about 5%
of it wrong where two people share a name. "Verified" is reserved for a reviewer's decision. Enum values and column
names (`verified_link_count`, `verified_basis`, `human_verified`) are unchanged; every reader-facing label and doc uses the
new words, and the teacher-student network built from this tier is machine-reviewed.

Since `0006`: a mention has a standing identity (what the code calls a verified link) when `resolution in ('source_index','human_verified','derived_relation_verified')`
and `narrator_id` points at a live narrator. `exact_registry` is no longer in the list: a name match is a candidate,
never a link. The predicate is written in `public_chain_links` and twice in `refresh_publication_facets` (all three
redefined in `0006_mention_identity_candidates.sql`); `db:verify` fails if the view still names `exact_registry`.
`narrator_transmissions` keeps a stricter rule: both neighbours `resolution_basis = 'source_index'`, or both
`human_decision` (mixed pairs are not counted; owner question below).

## Identity candidates (owner decisions 2026-11-21)

Where the name matcher and the K6 source index both identify a narrator they disagree on 24-49% of matches, so one
`narrator_id` per name misrepresents the data. Decisions: (a) show every identity for a name with its source, both
when they disagree; (b) kunya-only lexicon entries may match, marked; (c) sanads stay per tradition, so automatic
name matches are emitted only for Sunni reports; (d) placeholder lexicon rows are never a target, except kunya-only
rows through (b).

- **`chain_mention_candidates`** (pipeline, written only by the loader): one row per (mention, narrator, basis),
  unique on that triple, with `detail` (resolver tier or K6 agreement class) and `source_position` (set exactly for
  the two source bases, check). Bases: `name_exact` (resolver tier 0), `name_spelling_fold` (tiers 1-2),
  `name_kunya_only` (`kunya_only_candidate` in `regen_unified_csvs.py`), `source_index` (the K6 source's own index
  at a position the Arabic corroborates, in a report whose agreement class is not full), and
  `source_index_confirmed_by_text` (the sidecar's report-level basis `source_index_corroborated_by_text`: full
  agreement, or every source id aligned). `reviewer_decision` is never stored (check): one writer per table, so the
  public view reads it from `narrator_surface_decisions` through `chain_mentions.decision_id`.
- **What sets `chain_mentions.narrator_id`** (the verified identity, meaning unchanged from section 5.5): the loader
  writes it only for a mention with a `source_index_confirmed_by_text` candidate that no other candidate contradicts
  (`resolution = 'source_index'`, `resolution_basis = 'source_index'`, `extraction_method =
  'source_index_confirmed_by_text'`, confidence 1.0); a reviewer decision writes the rest. A name match, a kunya-only
  match and an unconfirmed source index never do. A confirmed but contested mention stays `unresolved` with both
  candidates shown (`verified_narrator` in `export_postgres.py`). **A kunya-only candidate never contests** (owner,
  2026-11-21): it is a label shown beside the other candidates and ignored when deciding whether the identity stands
  and in every analysis; 1,328 mentions gained their machine-reviewed identity with this rule.
- **`narrators.placeholder_reason`** (pipeline): `registry_placeholder_reason` of the lexicon row, so the
  "never a placeholder target" rule is checkable in SQL.
- **`public_chain_mention_candidates`**: every candidate of a public mention with `basis`, `detail` and
  `verified_basis` (confirmed source index or reviewer decision). Unverified candidates appear here and nowhere in
  `public_chain_links.narrator_id` or `narrator_transmissions`.
- **Load invariants** (`load/verify-data.ts`): candidate on a live mention of the same hadith naming a live narrator;
  no placeholder target except `name_kunya_only`, which targets only `kunya_only_name` rows; no name basis on a
  non-Sunni report; an automatic `narrator_id` has its confirming candidate and no non-kunya candidate contests it.

## Report correspondences (0007; design §5.5.1)

Reports that carry the same matn in another work or tradition, from `diagnostics/report-correspondence/`. Reports are
linked, never narrators or chains. One writer per table: the loader writes candidates and cluster members; curators
write decisions.

- **Pair order is byte order.** `hadith_id_a < hadith_id_b` is checked `collate "C"`: the database collation
  (`en_US.utf8`) ignores punctuation at the first level, so it can order `hadith:k6:…` ids differently from the Python
  job. `orderPair` in `queries/correspondence-decisions.ts` orders by bytes too.
- **Hash binding, twice.** The projection drops (and counts) a pair whose Arabic hash differs from the loaded text; the
  display rule also joins both hashes, so a text changed by a later load hides the pair until it is rebuilt. A decision
  binds to the hashes the reviewer read and applies only while both still match: re-queued, never silently reapplied.
- **One display rule.** `report_correspondence_shown_pairs` (confirmed at any score; else same wording, variant at
  Jaccard >= 0.4, partial at containment >= 0.7, unless rejected). `report_correspondence_display` is both directions;
  `public_report_correspondences` adds the public gate. All three are written without CTEs: a CTE referenced twice is
  materialized whole, which would scan every pair for one report's family.
- **Decision semantics.** `confirmed` means one report or passage; a confirmation may carry only a machine class as its
  reading (check). `same_ruling_different_attribution`, `shared_formula_only`, `shared_quran_quotation` go with a
  rejection or uncertain. Revising retires the live row and points the new one at it (`supersedes_decision_id`).
- **FK names.** The two pipeline tables pass a short prefix (`report_corr_*`) to `pipelineBookkeepingForeignKeys`: the
  full table names push the generated names past Postgres's 63 bytes (decision 4 below), which `db:verify` caught.

## Migrations

- One stream, `drizzle/core`, applied by `src/db/migrate.ts`: `lock_timeout 5s`, `statement_timeout 60s`,
  the data-write advisory lock, three retries on lock timeout. The drizzle 0.45.4 migrator runs all pending
  migrations in ONE transaction (verified in `pg-core/dialect.js`), so `create index concurrently` can never be
  a migration: heavy indexes live in `ops/indexes-heavy.sql`.
- Order: `0000_extensions` (pg_trgm, unaccent; idempotent) -> `0001_core_schema` (generated) ->
  `0002_table_storage` (fillfactor 90) -> `0003_views` -> `0004_functions` -> `0005` (research feature removed) ->
  `0006_mention_identity_candidates` (generated table, enums and column, then hand-written: `public_chain_links`
  and `refresh_publication_facets` redefined, `public_chain_mention_candidates` created, `narrator_transmissions`
  dropped and recreated with its two indexes) -> `0007_report_correspondences` (generated tables and enums, then the
  three hand-written views) -> `0008_epochs` (the history lane's pending `epochs` table and `published_epochs` view,
  promoted from `ops/pending/`; idempotent). A `--custom` generate snapshots the previous schema: after promoting a
  table into `schema/`, check `drizzle-kit generate` reports no changes, and fold its snapshot into the custom one if not.
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
   `dataset_versions` and `curation_audit` in `operations.ts`.
2. **Only the 40 launch tables are declared.** The doc says schema files for the 7 later tables exist from
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

- Identity candidates: mixed transmission pairs (one confirmed source-index neighbour, one human decision); whether a
  kunya-only candidate should contest a confirmed source identity (it does now); source-index claims that name a
  placeholder row are dropped and counted in the projection manifest, not emitted; the narrator page still lists
  only reports where the narrator is a verified link.
- `ops/roles.sql` (`schema_owner`, `app_rw`, grants, `app_rw` timeouts) and `ops/railway-tuning.sql`. The step 4
  migrations ran as the Railway template superuser, so every object is owned by it: `roles.sql` must
  `REASSIGN OWNED` / `ALTER ... OWNER TO schema_owner` before the app switches roles.
- `apply_decision(unit_id)`: written with the loader's decision replay (step 5/6) so both share one SQL path,
  including the narrower-scope-wins rule and the position - 1 condition for `derived_relation`.
- Running `ops/indexes-heavy.sql` (after the first load).
- `src/db/load/*`, section 11.4 checks, `src/db/queries/*`, `withReadRetry`, the ESLint import rule, the
  Dockerfile `migrate.mjs` bundle and `railway.json` pre-deploy command.
- The 7 later tables (decision 2).
