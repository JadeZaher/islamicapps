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

## 2026-11-21 (later) — follow-up: review findings, refusals, export, preview

- Sign-in throttle: the client address is no longer the left-most `X-Forwarded-For` hop (client-settable). It is the edge
  header named by `CLIENT_IP_HEADER` (default `x-real-ip`), else the RIGHT-most `X-Forwarded-For` hop. Failures are also
  throttled per curator name (20 per 15 min, case-insensitive, across addresses; a correct sign-in clears the name).
- Race fixed: `/api/auth/sign-in` reserves its address slot synchronously before any await (and the name slot right after
  the form parse, still before the scrypt comparison); only a correct passphrase releases them.
- Railway client-IP source: NOT verified against current Railway documentation. The Railway docs MCP tools
  (`mcp__railway__search-docs`, `fetch-docs`) were not available to this agent and outbound HTTP from the sandbox timed
  out (`docs.railway.com`, no connection after 20 s). The default (`x-real-ip`, then right-most `X-Forwarded-For`) rests
  on recalled behaviour: Railway's edge sets `X-Real-IP` and appends the connecting address to `X-Forwarded-For`.
  Before relying on it, read https://docs.railway.com/networking/public-networking (specs and limits), or request
  `/api/health` through the public domain with `X-Real-IP: 1.2.3.4` and `X-Forwarded-For: 5.6.7.8` and log what the app
  receives; if the edge does not overwrite `X-Real-IP`, set `CLIENT_IP_HEADER=x-forwarded-for`.
- Blocked sign-in: browser form posts (`Accept: text/html`) are redirected 303 to `/sign-in?error=throttled`; other
  callers get 429 with `Retry-After`.
- Curation actions return `{ ok: true, data } | { ok: false, message, fieldErrors? }` for expected refusals; admin
  clients unwrap through `unwrapAction`. Unexpected failures still throw.
- `/api/export/hadiths`: curator-only streaming CSV (`src/db/queries/hadith-export-review.ts`); the admin hadith page no
  longer imports `graph-actions`. No page or client imports `graph-actions` or `comparative-actions` (files kept for the
  retirement track).
- Preview approval: `src/scripts/db/approve-preview.ts`, `getPreviewNotice`, `<PreviewNotice />` in the root layout.
  Removal checklist: `conductor/RUNBOOK.md`, "Remove after the first release".
- Owner environment setup: `railway-env-setup.md` in this folder.
