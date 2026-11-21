---
type: track-spec
title: Containment and access control
tags: [containment-and-access-control_20261121, planned]
resource: ./metadata.json
---

# Containment and access control

Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) section 12 steps 0.5 and 1, section 10 (whole), section 15
(auth assumptions).

## Goal

The open research route cannot spend money, and anonymous requests cannot
reach any write on the production URL.

## Scope

- **Step 0.5, no build:** remove or rotate `YOU_API_KEY` on the `islamicapps`
  service; check you.com spend and request logs; inspect `NODE_CSV_URLS` and
  `RELATION_CSV_URLS` for embedded credentials; rotate the stray
  `OPENROUTER_KEY` and remove its line from the stale UTF-16 `.env`
  (section 10.3).
- **Step 1:** first a checked-in inventory of every mutating server action and
  route with `file:line` (the security finding `08-security-auth.md` does not
  exist), then reconcile section 10 with it. Then `src/proxy.ts` (route gate,
  sign-in throttling, per-IP read rate limit), the named-curator cookie,
  `requireCurator()` as the first line of every current mutating action, zod
  input, allowlists in the three comparative update actions, and auth plus
  caps on the research route.

## Out of scope

- The Postgres curation actions of section 9.3 and `curation_audit` rows
  (query-port-and-action-switch).
- The admin layout chrome (ui-polish lane D). The deploy itself (build-fix).

## Acceptance checks

- Containment actions recorded with dates (never secret values).
- The inventory lists every writing `'use server'` export and route handler.
- On the **production URL**: every inventoried action and route refuses an
  anonymous request; the sixth failed sign-in in 15 minutes returns 429; the
  research route rejects anonymous and over-cap calls.
- Flow tests drive the proxy gate and `requireCurator()` through the public
  seam, not mocks.

## Open owner questions (section 14)

- Q14: named curators from step 1 (design assumes yes). The owner supplies
  curator names and passphrases.
- Section 15 assumptions to confirm: `CURATOR_PASSPHRASES` and
  `ADMIN_SESSION_SECRET` as names, research effort levels `lite` and
  `standard`, 30 reads a minute per IP.
