---
type: implementation-plan
title: Containment and access control plan
tags: [containment-and-access-control_20261121, planned]
resource: ./spec.md
---

# Implementation plan: Containment and access control

Track: `containment-and-access-control_20261121`. Spec: [./spec.md](./spec.md). Design steps: 0.5, 1.

## Phase 0 — Containment (step 0.5)

- [ ] Inspect `NODE_CSV_URLS` and `RELATION_CSV_URLS` for embedded credentials.
- [ ] Rotate `OPENROUTER_KEY`; remove the line from `.env`.

Done when: no stray credentials remain in the service variables, recorded with dates (design section 10.3).

## Phase 1 — Inventory

- [x] Write the mutation inventory with `file:line` for every writing action and route.
- [x] Reconcile design section 10 counts with it; list differences.

Done when: the inventory is checked in and section 10 differences are listed.

## Phase 2 — Auth core

- [x] `src/lib/auth/session.ts` (Web Crypto HMAC cookie) and `require-curator.ts`.
- [x] Sign-in page and server action; throttling and rate limit in `src/proxy.ts`.
- [x] `src/lib/auth/AGENTS.md`: revocation procedure (section 10.1).

Done when: local flow tests show anonymous requests refused and a signed-in curator allowed.

## Phase 3 — Gate current writes

- [x] `requireCurator()` first in every inventoried action; zod input.
- [x] Allowlists in the three comparative update actions.

Done when: every inventory row is marked gated.

## Phase 4 — Production verification

- [ ] After build-fix deploys: probe every inventory row anonymously on the production URL.

Done when: section 12 step 1 done-when holds on the production URL.
