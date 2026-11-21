---
type: track-log
track: containment-and-access-control_20261121
---

# Log

## 2026-11-21 — app data layer lane

- Phase 0 (containment of `NODE_CSV_URLS`, `RELATION_CSV_URLS`, `OPENROUTER_KEY`) not done: it needs Railway
  variable access and a key rotation by the owner; no secret was read.
- Phase 1: `mutation-inventory.md` — 29 writing Neo4j actions confirmed, three injectable updates confirmed.
- Phase 2: `src/lib/auth/` (session, passphrases, throttle, require-curator, hash CLI, AGENTS.md with revocation),
  `src/proxy.ts`, `/sign-in` page, `/api/auth/sign-in` and `/api/auth/sign-out` route handlers.
- Phase 3: `requireCurator()` first in all 29 Neo4j writes plus `exportHadiths`; key allowlists in
  `updateTradition`, `updateSourceText`, `updateParallel`; every new curation action gated and zod-validated.
- Flow tests: `src/db/queries/__tests__/flows.test.ts` (session forge/expiry/revocation),
  `http-gate.test.ts` (proxy redirect and 401, anonymous action writes nothing, sixth sign-in is 429, cookie flags).
- Phase 4 (production probe) waits for build-fix to deploy.
