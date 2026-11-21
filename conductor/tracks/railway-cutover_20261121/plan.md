---
type: implementation-plan
title: Railway cutover and observation plan
tags: [railway-cutover_20261121, planned]
resource: ./spec.md
---

# Implementation plan: Railway cutover and observation

Track: `railway-cutover_20261121`. Spec: [./spec.md](./spec.md). Design steps: 8, 9.

## Phase 0 — Database checks

- [ ] Verify serverless off, version 18, extensions, private host in `DATABASE_URL`.
- [ ] Apply `railway-tuning.sql`; restart; `db:verify`.

Done when: the database matches section 2.4 settings.

## Phase 1 — Backups and restore

- [ ] Enable daily, weekly and monthly backups.
- [ ] Rehearse both restore procedures in a throwaway environment.

Done when: a restore has been performed and timed.

## Phase 2 — Deploy with migrator

- [ ] Bundle `migrate.mjs` in the Dockerfile; add `preDeployCommand` and the health check to `railway.json`.
- [ ] Set Pre-deploy Timeout to 300 s; deploy.

Done when: a deploy runs migrations and passes the health check.

## Phase 3 — Load window

- [ ] Public Access on; load the bundle and the curation export; Public Access off.
- [ ] Record `collection_rights` decisions with the owner.

Done when: production `db:verify` passes after the load.

## Phase 4 — Observe

- [ ] External uptime probe on `/api/health`; measure billed memory.

Done when: 7 idle days without probe failures; section 1.4 updated.

## Phase 5 — Retire Neo4j (step 9)

- [ ] Final Neo4j volume dump; owner approval; remove service, volume and the nine variables.

Done when: owner approval is recorded.
