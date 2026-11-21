---
type: implementation-plan
title: Neo4j curation export and seed ports plan
tags: [neo4j-curation-export_20261121, planned]
resource: ./spec.md
---

# Implementation plan: Neo4j curation export and seed ports

Track: `neo4j-curation-export_20261121`. Spec: [./spec.md](./spec.md). Design steps: 7.

## Phase 0 — Dump

- [ ] Run `backup-db.ts` read-only against production Neo4j; store off-machine.

Done when: the dump's location and hash are recorded.

## Phase 1 — Seed ports

- [ ] `seed-historical-data`, `seed-narrator-bios-phase0`, `seed-taxonomy` as `src/scripts/db/seed-*.ts`.

Done when: seeds load on an empty database with actor `system:seed`.

## Phase 2 — Export and re-key

- [ ] `export-neo4j-curation.ts` covering every step 7 entity; re-key; hash binding.
- [ ] Seed diff and legacy grade diff reports.

Done when: every exported row is classified loadable, differing or unkeyable.

## Phase 3 — Load and review

- [ ] Load into the development database; owner reviews the differing rows.

Done when: section 12 step 7 done-when holds.
