---
type: track-spec
title: Neo4j retirement sweep
tags: [neo4j-retirement-sweep_20261121, planned]
resource: ./metadata.json
---

# Neo4j retirement sweep

Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) section 12 step 10; section 13.2 (delete at cutover);
section 13.5 (stale documentation).

## Goal

No `neo4j-driver` import remains, and no document describes Neo4j as the
store.

## Scope

- Every section 13.2 row, as `git mv` into `src/scripts/archive/`.
- Rewrite the section 13.5 documents: `CONTRIBUTING.md`,
  `.agent/rules/app-goal.md`, the `AGENTS.md` files under `src/lib/db`,
  `src/scripts/lib/regen` and `src/scripts/__tests__`,
  `src/scripts/ops/README.md`, the `neo4j_export` docs (reword as a source
  format), and `conductor/product-guidelines.md` and
  `conductor/code_styleguides/typescript.md`, which the 2026-11-21 conductor
  reset left untouched.
- The conductor tracks are already marked superseded by that reset (see
  `conductor/archive/2026-11-21-neo4j-era/README.md`).

## Out of scope

Railway resources (removed in railway-cutover phase 5). Data files under
`datasets/` (never removed).

## Acceptance checks

- `grep -r neo4j-driver src package.json` finds nothing outside
  `src/scripts/archive/`.
- Build, lint and type-check pass once at the end.

## Open owner questions (section 14)

Q7 and the never-delete rule: archive, never hard delete, unless the owner says so.
