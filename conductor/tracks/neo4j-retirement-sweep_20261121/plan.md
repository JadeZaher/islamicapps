---
type: implementation-plan
title: Neo4j retirement sweep plan
tags: [neo4j-retirement-sweep_20261121, planned]
resource: ./spec.md
---

# Implementation plan: Neo4j retirement sweep

Track: `neo4j-retirement-sweep_20261121`. Spec: [./spec.md](./spec.md). Design steps: 10.

## Phase 1 — Mine tests

- [ ] Extract pure cases from the Neo4j-flavoured tests into table-driven tests.

Done when: every pure case has a home outside the Neo4j tests.

## Phase 2 — Archive code

- [ ] `git mv` every section 13.2 row into `src/scripts/archive/`.
- [ ] Remove `neo4j-driver` and the Neo4j scripts from `package.json` at the join.

Done when: no `neo4j-driver` import remains (section 12 step 10 done-when).

## Phase 3 — Documentation

- [ ] Rewrite every section 13.5 document.

Done when: no document names Neo4j as the store.
