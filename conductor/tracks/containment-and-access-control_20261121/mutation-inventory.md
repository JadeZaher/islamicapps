---
type: inventory
title: Mutation inventory (step 1)
updated: 2026-11-21
---

# Mutation inventory

Every writing `'use server'` export and route handler, with its gate. Line numbers at the 2026-11-21 working tree.
Reconciliation with design section 10: the design's "about 29 anonymous mutating actions" is confirmed exactly
(11 in `graph-actions.ts`, 18 in `comparative-actions.ts`); the "three injectable comparative updates" are
confirmed (`updateTradition`, `updateSourceText`, `updateParallel` interpolated caller keys into Cypher SET).
Difference: `exportHadiths` (graph-actions) is a read but a scrape amplifier, so it is gated too.

## Neo4j era (unused by pages; client components still import some until the UI lane switches them)

| Action | Location | Gate |
| --- | --- | --- |
| createHistoricalEvent, deleteHistoricalEvent, updateHistoricalEvent | `src/app/actions/graph-actions.ts:490, 578, 593` | requireCurator() first |
| linkNarratorToEvent (dead) | `graph-actions.ts:642` | requireCurator() |
| createCommentary, updateCommentary, deleteCommentary | `graph-actions.ts:689, 793, 801` | requireCurator() |
| createLocation, deleteLocation, updateLocation, linkNarratorToLocation | `graph-actions.ts:811, 848, 855, 866` | requireCurator() |
| exportHadiths (read, 10,000 rows) | `graph-actions.ts:1057` | requireCurator() |
| createReligiousTradition, deleteTradition, updateTradition | `src/app/actions/comparative-actions.ts:120, 161, 166` | requireCurator(); updateTradition key allowlist |
| createSourceText, linkSourceTextToTradition, deleteSourceText, updateSourceText | `comparative-actions.ts:182, 210, 237, 242` | requireCurator(); updateSourceText key allowlist |
| createMotifTag, deleteMotifTag, tagHadith, untagHadith, tagParallel | `comparative-actions.ts:252, 284, 289, 298, 306` | requireCurator() |
| createCrossParallel, deleteParallel, updateParallel | `comparative-actions.ts:317, 408, 413` | requireCurator(); updateParallel key allowlist |
| linkNarratorToTradition, unlinkNarratorFromTradition, linkLocationToTradition | `comparative-actions.ts:423, 432, 472` | requireCurator() |

## Postgres (src/app/actions/curation/)

Every export's first line is `await requireCurator()`, then zod, then one query call; each write audits in its
transaction: `commentary.ts:8-25` (4), `comparative.ts:17-114` (19), `history.ts:7-18` (3), `location.ts:7-18` (3),
`review.ts:8-41` (7), `search.ts:10` (curator read).

## Route handlers

| Route | Location | Gate |
| --- | --- | --- |
| POST /api/auth/sign-in | `src/app/api/auth/sign-in/route.ts:25` | proxy throttle (5 failures / 15 min / IP), handler re-check |
| POST /api/auth/sign-out | `src/app/api/auth/sign-out/route.ts:7` | none needed (clears own cookie) |
| GET /api/health | `src/app/api/health/route.ts:7` | read-only |
| /admin/** (pages and action POSTs) | `src/proxy.ts` | session or 303 to /sign-in (GET) / 401 |

Public read actions (`src/app/actions/read/*`) are rate-limited per IP in `src/proxy.ts`.
