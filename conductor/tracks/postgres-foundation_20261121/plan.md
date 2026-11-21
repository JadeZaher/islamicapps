---
type: implementation-plan
title: Postgres foundation: Drizzle schema, client, migrations plan
tags: [postgres-foundation_20261121, in_progress]
resource: ./spec.md
---

# Implementation plan: Postgres foundation: Drizzle schema, client, migrations

Track: `postgres-foundation_20261121`. Spec: [./spec.md](./spec.md). Design steps: 4.

## Phase 0 — Environment

- [ ] Connect with `.env.local`; record server version and `pg_available_extensions`.
- [ ] Write `src/db/ops/roles.sql` (section 2.9); apply as the template superuser.
- [ ] Decide with the owner where the `_test` database lives.

Done when: `schema_owner` and `app_rw` exist on the Railway database and the version is recorded.

## Phase 1 — Schema files

- [ ] `enums.ts`, `columns.ts` (sections 5.1, 5.2).
- [ ] Corpus, narrators, isnad, assessments, biography, evidence, history, commentary, comparative, audit (sections 5.3 to 5.12).
- [ ] `candidates.ts` and `vector.ts` written but not migrated (section 5.14).

Done when: `drizzle-kit generate` produces `drizzle/core` for exactly the launch tables.

## Phase 2 — Hand-written migrations

- [ ] Extensions (idempotent), public views (section 11.3), materialized view and functions.
- [ ] Partial unique indexes on curation tables (section 3.2 rule 6).

Done when: every object named in sections 5 and 11.3 for launch is created by a migration.

## Phase 3 — Client and migrator

- [ ] `src/db/client.ts` per section 3.3.
- [ ] `src/db/migrate.ts` per section 2.6.
- [ ] `src/db/AGENTS.md` invariants.

Done when: `db:migrate` runs cleanly as `schema_owner` (section 12 step 4 done-when).

## Phase 4 — Verify

- [ ] Re-run `db:migrate` (no-op); count tables and views; test `app_rw` grants.

Done when: acceptance checks in the spec pass.
