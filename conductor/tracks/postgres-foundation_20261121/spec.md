---
type: track-spec
title: Postgres foundation: Drizzle schema, client, migrations
tags: [postgres-foundation_20261121, in_progress]
resource: ./metadata.json
---

# Postgres foundation

Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) section 12 step 4; sections 2.6 (migration rules), 2.9
(roles), 3 (layout and rules), 5 (schema; launch tables per 5.14), 7.1
(indexes), 11.3 (public views).

## Environment (differs from design section 2.7)

A Postgres database **already exists on Railway** in project
`hadith-ontology`. Its connection string is in the app service's
`DATABASE_URL` variable and in the local `.env.local`. The extensions
`vector`, `pg_trgm` and `unaccent` are already enabled. Development targets
that database, not a local `pgvector/pgvector:pg18` container.

Consequences to handle in this track:

- `roles.sql` is applied there by the template superuser, before the first
  migration.
- The first core migration must tolerate extensions that already exist.
- The step 11 "fail closed if `vector` is missing" check is already met.
- There is no `_test` database yet; the loader's `_test` rule (section 2.7)
  needs one on the same server, or an owner decision.
- Record `select version()` and confirm the image is Postgres 18.
- The existing `DATABASE_URL` is most likely the template superuser URL.
  Design 2.2 says the app's `DATABASE_URL` is the `app_rw` role and the
  migrator uses a separate `MIGRATOR_DATABASE_URL` (`schema_owner`). Once
  `roles.sql` is applied, development uses those two; the superuser URL is
  for `roles.sql` and tuning only.

The dependencies are already in the working tree (uncommitted):
`drizzle-orm` ^0.45.4, `drizzle-kit` ^0.31.11, `postgres` ^4.1.1, `zod`,
`server-only`. Check that the `postgres` major version is the intended
postgres.js release.

## Scope

All schema files of section 3.1 under `src/db/schema/core/`; migrations only
for the 41 launch tables (section 5.14); hand-written migrations for
extensions, views, the `narrator_transmissions` materialized view,
`narrator_lifespans`, `apply_decision`, `refresh_network` and partial indexes;
`client.ts` (section 3.3); `migrate.ts` (section 2.6 rules: lock and statement
timeouts, advisory lock shared with the loader, three retries); `roles.sql`;
`src/db/AGENTS.md` carrying the invariants ported from `src/lib/db/AGENTS.md`.

## Out of scope

Loader and `indexes-heavy.sql` (bundle-to-postgres-loader); query modules;
`railway-tuning.sql` (railway-cutover); the vector table (step 11).

## Acceptance checks

- `db:migrate` applies cleanly from an empty schema as `schema_owner` on the
  Railway database; a second run is a no-op.
- 41 launch tables plus the section 11.3 views exist (count recorded).
- `app_rw` cannot `DELETE` and cannot write pipeline tables (tested).
- Importing `src/db/client.ts` opens no connection (lazy client).

## Open owner questions

- Owner confirmation that development runs against the Railway database, and
  where the `_test` database lives.
- Section 14 Q1 does not block: the `resolution` enum keeps `source_index`
  whatever the answer.
