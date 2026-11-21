---
type: implementation-plan
title: Railway cutover and observation plan
tags: [railway-cutover_20261121, in-progress]
resource: ./spec.md
---

# Implementation plan: Railway cutover and observation

Track: `railway-cutover_20261121`. Spec: [./spec.md](./spec.md). Design steps: 8, 9.

## Phase 0 — Database checks

- [x] Verify version 18, extensions, private host in `DATABASE_URL` (2026-11-21: PostgreSQL 18.6; `vector`, `pg_trgm`, `unaccent`; the app's `DATABASE_URL` uses the private host and database `railway`). Serverless not checked from the CLI.
- [~] Apply `railway-tuning.sql` (done 2026-11-21 with `src/db/ops/apply-tuning.ts`, reloaded); restart (session lead); `db:verify`.

Done when: the database matches section 2.4 settings.

## Phase 1 — Backups and restore

- [ ] Enable daily, weekly and monthly backups.
- [ ] Rehearse both restore procedures in a throwaway environment.

Done when: a restore has been performed and timed.

## Phase 2 — Deploy with migrator

- [~] Health check added to `railway.json` (`/api/health`, 120 s, restart on failure). `migrate.mjs` and `preDeployCommand` deferred: migrations run by hand for now (see log).
- [ ] Set Pre-deploy Timeout to 300 s; deploy.

Done when: a deploy runs migrations and passes the health check.

## Phase 3 — Load window

- [~] Bundle loaded into production over the public proxy (2026-11-21, version `e2430eae…`). Curation export not loaded (Neo4j export lane). Public Access still on: turn it off when no further load is planned.
- [x] Record `collection_rights` decisions with the owner: all 34 works cleared, `source_provided_and_machine_allowed` (`npm run db:record-rights`, 2026-11-21).

Done when: production `db:verify` passes after the load.

## Phase 4 — Observe

- [ ] External uptime probe on `/api/health`; measure billed memory.

Done when: 7 idle days without probe failures; section 1.4 updated.

## Phase 5 — Retire Neo4j (step 9)

- [ ] Final Neo4j volume dump; owner approval; remove service, volume and the nine variables.

Done when: owner approval is recorded.

## Phase 6 — Remove after the first release (preview approval and notice)

The development snapshot is public as a preview under owner approval, with a notice. Once a release dataset version is
current the notice hides itself; then remove the rest (same list as `conductor/RUNBOOK.md`, "Remove after the first release").

- [ ] Revoke the approval: `npx tsx src/scripts/db/approve-preview.ts --revoke --by <owner> --reason "first release is current"`.
- [ ] Delete `src/components/PreviewNotice.tsx`, `src/components/PreviewNoticeBar.tsx`, the mount in `src/app/layout.tsx`, and `getPreviewNotice` (`src/db/queries/dataset.ts`).
- [ ] Delete the glossary `preview` entry (`/glossary#preview`) if no longer wanted.
- [ ] Delete `src/scripts/db/approve-preview.ts` and the "preview notice" flow in `http-gate.test.ts` if no more previews are wanted.

Done when: no `PreviewNotice` or `approve-preview` reference remains, and no `dataset_versions` row carries `public_override_by` on a current release.

## Log

- **2026-11-21, go-live pass.** Development first, then production: migration `0009` (English policy), rights for all 34
  works, preview approval for version `e2430eae…`, production loaded from the identical projection (`prod-load-2.log`; the first attempt, `prod-load-1.log`, stalled in the network refresh on a database with no statistics, was cancelled and rolled back cleanly, and the loader now analyzes changed tables inside the load transaction),
  heavy indexes, history seed and the 21 biographies, data invariants on both. Server tuning applied with `ALTER
  SYSTEM` (restart pending). `SITE_URL` and `NEXT_TELEMETRY_DISABLED` set on the service with `--skip-deploys`.
- **Migrations stay manual (decision).** A pre-deploy migrate would need `migrate.mjs` bundled into the standalone image
  (the runtime has no `tsx`); the migrator already takes the data-write advisory lock with a 5 s lock timeout and three
  retries, so a pre-deploy run during a load would fail the deploy rather than migrate mid-load. Until the bundle exists
  the operator runs `npm run db:migrate` against production before merging a change that adds a migration; `0009` is
  already applied.
- **Deferred:** restricted roles (`roles.sql`, `app_rw`, `MIGRATOR_DATABASE_URL`), backups and the restore rehearsal,
  the uptime probe, `railway.json` to the new config format before 2026-12-01.
