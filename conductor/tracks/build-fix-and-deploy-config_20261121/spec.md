---
type: track-spec
title: Build fix and deploy config
tags: [build-fix-and-deploy-config_20261121, in_progress]
resource: ./metadata.json
---

# Build fix and deploy config

Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) section 12 step 2, section 13.1, section 2.6 (build rules only).
Research: [../../../.omc/research/pg-refactor/09-scripts-fate.md](../../../.omc/research/pg-refactor/09-scripts-fate.md) sections 4, 6 and 8.

## Goal

`next build` succeeds inside the Docker image and a Railway deploy of the app
goes live again. The last good deploy was 2026-07-22; the 2026-08-18 image
build failed with no diagnosis.

## Scope

- Get the real build log of the failed deploy before changing anything.
- Exclude `src/scripts` from `tsconfig.json`; add `tsconfig.scripts.json` for
  operator scripts (section 2.6).
- Fix the Dockerfile port (09-scripts-fate section 6; design 2.2 `PORT`):
  stop setting `ENV PORT 3000`, and make the Railway domain target port
  (pinned to 8080 today) match or auto-detect.
- Add `railway.json`, field names checked against Railway's current schema
  (section 2.6). Ship it **without** `preDeployCommand` and without the
  `/api/health` health check; railway-cutover adds both once they exist.
- Delete-now inventory (section 13.1) as `git mv` into `src/scripts/archive/`.
  Re-verify each row first: at `af2f90b` most rows are already gone from the
  tree. Still present: `src/components/NarratorCard.tsx` (ui-polish lane C
  owns it), the `db:ingest-parallels` script and the `react-force-graph-2d`
  dependency in `package.json` (join file).

## Out of scope

- The pre-deploy migrator and `migrate.mjs` bundling (railway-cutover).
- `/api/health`, `force-dynamic` page markers (query-port-and-action-switch).
- UI dead code (ui-polish). Anything under `src/db/` (postgres-foundation).

## Acceptance checks

- `docker build` completes locally with `next build` inside the image.
- A Railway deploy shows Active and serves the home page; the deploy log is
  saved under the track folder.
- `tsc -p tsconfig.scripts.json --noEmit` runs; its errors are recorded, not
  required to be zero.
- Every section 13.1 row is marked moved, already gone, or handed to its owner.

## Open owner questions

None from section 14 block this track. Deploying to production is an owner
action: confirm which branch and environment before the deploy in phase 3.
