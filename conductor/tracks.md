---
type: track-index
title: Postgres-era tracks
---

# Conductor tracks

Driven by [`docs/architecture/data-architecture.md`](../docs/architecture/data-architecture.md)
(section 12 for order, section 14 for owner questions). Listed in dependency
order. Neo4j-era tracks are in
[`archive/2026-11-21-neo4j-era/`](./archive/2026-11-21-neo4j-era/README.md).

Status: `[~]` in progress, `[ ]` planned, `[x]` done. All ids end in `_20261121`.

## Migration spine (design section 12)

| | Track | Steps | Depends on | Blocks |
| --- | --- | --- | --- | --- |
| [~] | [`build-fix-and-deploy-config`](./tracks/build-fix-and-deploy-config_20261121/spec.md) | 2 | none | containment (done-when), railway-cutover |
| [ ] | [`containment-and-access-control`](./tracks/containment-and-access-control_20261121/spec.md) | 0.5, 1 | build-fix (final done-when only) | query-port, railway-cutover |
| [~] | [`postgres-foundation`](./tracks/postgres-foundation_20261121/spec.md) | 4 | none | loader, query-port |
| [ ] | [`bundle-to-postgres-loader`](./tracks/bundle-to-postgres-loader_20261121/spec.md) | 5 | postgres-foundation | query-port, curation-export, grading-coverage |
| [ ] | [`query-port-and-action-switch`](./tracks/query-port-and-action-switch_20261121/spec.md) | 6 | foundation, loader, containment, ui-polish (phase 6 only) | railway-cutover, identity, evidence, vectors |
| [ ] | [`neo4j-curation-export`](./tracks/neo4j-curation-export_20261121/spec.md) | 7 | loader | railway-cutover, evidence |
| [ ] | [`railway-cutover`](./tracks/railway-cutover_20261121/spec.md) | 8, 9 | build-fix, containment, query-port, curation-export | retirement-sweep, vectors |
| [ ] | [`neo4j-retirement-sweep`](./tracks/neo4j-retirement-sweep_20261121/spec.md) | 10 | railway-cutover | none |
| [ ] | [`vectors-semantic-search`](./tracks/vectors-semantic-search_20261121/spec.md) | 11 | query-port, railway-cutover; owner Q8 | none |

Containment phase 0 (step 0.5: rotate `YOU_API_KEY`, check spend) needs no
build and should start now.

## Alongside the spine

| | Track | Source | Depends on | Blocks |
| --- | --- | --- | --- | --- |
| [~] | [`ui-polish`](./tracks/ui-polish_20261121/spec.md) | `06-ui-audit.md` lanes A to E | none | query-port phase 6 |
| [~] | [`data-gap-diagnostics`](./tracks/data-gap-diagnostics_20261121/spec.md) | Step 3; `07-data-gaps.md` jobs J1 to J9 | none | the four curation tracks |

## Data curation (`07-data-gaps.md` sections b to e)

| | Track | Depends on | Owner questions |
| --- | --- | --- | --- |
| [ ] | [`narrator-identity-resolution`](./tracks/narrator-identity-resolution_20261121/spec.md) | diagnostics; query-port for human decisions | Q1, Q11, Q14 |
| [ ] | [`translation-recovery`](./tracks/translation-recovery_20261121/spec.md) | diagnostics | Q2, Q3, Q5 |
| [ ] | [`grading-coverage`](./tracks/grading-coverage_20261121/spec.md) | diagnostics, loader | Q2, Q9 |
| [ ] | [`evidence-and-biography-curation`](./tracks/evidence-and-biography-curation_20261121/spec.md) | diagnostics, curation-export, query-port | Q4, Q9, Q10, Q12 |

## Running in parallel now

`build-fix-and-deploy-config`, `postgres-foundation`, `ui-polish` and
`data-gap-diagnostics` have disjoint `partitions.owns` in their
`metadata.json` (checked against the tree at `af2f90b`). `package.json` and
`package-lock.json` are owned by none of them and are edited only at the join.
Re-verify owns lists before any fan-out if HEAD has moved.

## Parked (pointers into the archive)

| Work | Archived track | Revisit when |
| --- | --- | --- |
| Tier-2 LLM isnad branch reconciliation | `tier2_llm_isnad_reconciliation_20260612` | J5 shows branch-split errors are material |
| Taḥwīl gold-set expansion and kit follow-ups | `tahweel_annotation_kit_20260612` | Same trigger as above |
| Corpus expansion (Imami, post-K6 Sunni, Zaydi, Ibadi works) | `data_acquisition_20260521` waves 0, 2 to 6 | After railway-cutover |
| Offline graph analytics (centrality, communities, common link) | `gds_setup_analytics_20260425` | Identity coverage makes results meaningful; always report the coverage denominator |
