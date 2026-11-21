---
type: track-spec
title: Query port and action switch
tags: [query-port-and-action-switch_20261121, planned]
resource: ./metadata.json
---

# Query port and action switch

Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) section 12 step 6; section 3 (layout and rules); section 7
(search); section 8 (query patterns); section 9 (action coverage, new curation
actions, changed read contracts); section 11.3 (public views); section 13.3
(ports).

Folds in: archived
[comparative_ingestion_20260322](../../archive/2026-11-21-neo4j-era/tracks/comparative_ingestion_20260322/spec.md)
(the research route and `commit-parallel.ts` replace its discovery and ingest
scripts; AI parallels default to `proposed`, Q6) and phase 5 of
[uniform_isnad_extraction_20260609](../../archive/2026-11-21-neo4j-era/tracks/uniform_isnad_extraction_20260609/plan.md)
(multi-branch chains become mention-keyed nodes with `chain_id` and `branch`).

## Goal

The app runs end to end against Postgres.

## Scope

Query modules area by area (hadith, isnad, narrator, history, commentary,
comparative), then each server action switched to call them; the section 9.3
curation actions; `/api/health`; `force-dynamic` on database pages; read
retry; the ESLint `no-restricted-imports` rule (section 3.2 rule 1); the
section 13.3 ports (research route, `commit-parallel.ts`, `find-parallels`,
ER ingest as decisions, `audit-graph` as `db:audit`); test ports (DB-free
release-gate test, Arabic parity test, replacement for the source-text test
at `regen-full-load-hardening.test.ts:644-645`); the section 9.4 UI
co-changes.

## Out of scope

Removing Neo4j code (neo4j-retirement-sweep); production cutover.

## Acceptance checks

- Every action in sections 9.1 and 9.2 is answered by a query module.
- Lint fails if any file under `src/app/**` imports `drizzle-orm`,
  `postgres`, `@/db/client` or `@/db/schema`.
- Public pages read only `public_*` views.
- With Neo4j variables unset, these flows work against the database: hadith
  detail, narrator detail, search, admin edit as a curator, comparative
  publish, health check.

## Open owner questions (section 14)

Q3, Q4, Q5, Q6, Q7, Q10, Q11, Q13 shape what the read contracts expose.
