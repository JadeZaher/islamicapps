---
type: track-spec
title: Railway cutover and observation
tags: [railway-cutover_20261121, planned]
resource: ./metadata.json
---

# Railway cutover

Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) section 12 steps 8 and 9; section 2 (topology, variables,
tuning, backups, restore, migrate on deploy, roles); section 1.4 (memory, to be
replaced by the measurement).

## Already done, differs from step 8

The Postgres service already exists in project `hadith-ontology`, with
`vector`, `pg_trgm` and `unaccent` enabled, and the app's `DATABASE_URL`
already points at it. Step 8's "add the template" and "point `DATABASE_URL`"
are therefore checks, not actions: confirm serverless is off, the image is
Postgres 18, and the app uses the private `.railway.internal` host. Replace
the app's `DATABASE_URL` with the `app_rw` URL and add
`MIGRATOR_DATABASE_URL` (design 2.2); today it most likely holds the template
superuser URL.

## Goal

The app serves from Postgres in production, health stays green, billed memory
is measured, and Neo4j is removed with the owner's approval.

## Scope

Tuning SQL and restart (section 2.4); `db:verify` gate; daily, weekly and
monthly backups; Pre-deploy Timeout 300 s; rehearse both restore procedures in
a throwaway environment (2.5.1); Dockerfile bundling of `migrate.mjs` and the
`railway.json` `preDeployCommand` and health check (2.6); load window with
Public Access; bundle and curation-export loads; `collection_rights` rows with
the owner; uptime probe; memory measurement. Step 9: observation period, final
Neo4j dump, removal with recorded approval.

## Out of scope

Code deletion (neo4j-retirement-sweep).

## Acceptance checks

- Health check green; billed memory recorded and section 1.4 replaced.
- The uptime probe shows no failures on idle over 7 days.
- Restore rehearsal recorded.
- Owner approval for Neo4j removal recorded.

## Open owner questions (section 14)

Q2 (rights per work), Q5 (English policy per work), Q12 (off-machine copy),
Q13 (non-release bundle in public); the 7-day observation period (section 15).
