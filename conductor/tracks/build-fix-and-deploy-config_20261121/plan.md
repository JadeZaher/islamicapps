---
type: implementation-plan
title: Build fix and deploy config plan
tags: [build-fix-and-deploy-config_20261121, in_progress]
resource: ./spec.md
---

# Implementation plan: Build fix and deploy config

Track: `build-fix-and-deploy-config_20261121`. Spec: [./spec.md](./spec.md). Design steps: 2.

## Phase 0 — Diagnose

- [ ] Fetch the build log of the failed 2026-08-18 deploy from Railway and save it here.
- [ ] Reproduce the image build locally and record the first real error.

Done when: the cause of the failed build is written down with evidence (design section 2.6 names the likely cause, unconfirmed).

## Phase 1 — Build config

- [ ] Exclude `src/scripts` from `tsconfig.json`; create `tsconfig.scripts.json`.
- [ ] Fix the Dockerfile port (09-scripts-fate section 6).
- [ ] Add `railway.json` per section 2.6, minus `preDeployCommand` and the health check path.

Done when: `docker build` succeeds locally.

## Phase 2 — Delete-now inventory

- [ ] Re-check every section 13.1 row against the tree; mark each moved, already gone, or owned elsewhere.
- [ ] `git mv` any remaining script rows into `src/scripts/archive/`.
- [ ] Hand the `package.json` edits (`db:ingest-parallels`) to the join.

Done when: the section 13.1 table has a disposition per row in this plan.

## Phase 3 — Deploy

- [ ] Confirm branch and environment with the owner.
- [ ] Deploy; save the deploy log; check the live URL.

Done when: a deploy is live (section 12 step 2 done-when).
