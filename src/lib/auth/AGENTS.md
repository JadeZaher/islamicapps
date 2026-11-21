# src/lib/auth — named-curator access (data-architecture.md section 10)

| File | What |
| --- | --- |
| `session.ts` | Cookie `curator_session` = `base64url({n: name, e: expiry}).base64url(HMAC-SHA256)`, Web Crypto only (used by `src/proxy.ts`) |
| `passphrases.ts` | scrypt hashes (`scrypt$N$r$p$salt$key`, base64url), constant-time verify, dummy hash for unknown names |
| `throttle.ts` | In-memory sliding windows on `globalThis`: 5 sign-in attempts per address and 20 per curator name per 15 min; 30 anonymous reads per address per minute; `clientIp` |
| `throttled-response.ts` | Blocked sign-in answer: browsers 303 to `/sign-in?error=throttled`, others 429 |
| `require-curator.ts` | `requireCurator()` returns `curator:<name>` or throws `UnauthorizedError` |
| `hash-passphrase.ts` | Operator CLI: passphrase on stdin, hash on stdout |
| `switches.ts` | `AUTH_ENABLED` and `PRIVATE_PREVIEW`, resolved in one place; auth surfaces; preview-open paths; `safeReturnPath` (edge-safe) |
| `visibility.ts` | `requestVisibility()` / `visibilityForSessionToken()`: the only producer of curator read visibility |

## Switches

Both are read at request time (never baked in at build) and accept only the value `1`; defaults are off.

- **`AUTH_ENABLED`** (owner decision 2026-11-21: off; the pipeline is the only writer). Off: `src/proxy.ts` answers 404
  for `/sign-in`, `/api/auth/*`, `/admin/**`, `/api/export/**` before reading any cookie; the sign-in, sign-out and
  export route handlers, the sign-in page and the admin layout check it again; `requireCurator()` throws
  `UnauthorizedError('Curation is not enabled on this deployment.')`, which `attempt()` turns into the usual
  `{ ok: false, message }`. No public page links to sign-in or admin. On: everything below applies unchanged.
- **`PRIVATE_PREVIEW`** implies auth. The proxy requires a session for every route except `/sign-in`,
  `/api/auth/sign-in`, `/api/auth/sign-out`, `/api/health`, `/robots.txt` and top-level `public/` files (GET/HEAD
  303 to `/sign-in?next=…`, anything else 401), and sets `X-Robots-Tag: noindex, nofollow` on every response. Sign-in
  may then return to any same-site path (`safeReturnPath`; otherwise only `/admin…`). Fail closed: without a 32+
  character `ADMIN_SESSION_SECRET` and at least one curator, `src/instrumentation.ts` exits at start-up and the proxy
  answers 503.

### Read visibility

`ReadVisibility` (`src/db/queries/visibility.ts`) is `'public'` or a branded `CuratorVisibility` that only
`visibilityForSessionToken` mints, and only when `PRIVATE_PREVIEW=1` and the cookie verifies for a still-configured
curator. Anonymous, forged, expired, revoked, or switch off: public. Pages call `requestVisibility()` (React-cached per
request) and pass the result to the query layer, which picks public views or live base tables in one function
(`hadithRelationsFor`). Tested in `src/db/queries/__tests__/browse-flows.test.ts` ("visibility") and over HTTP in
`switches-http.test.ts`.

## Environment (owner sets these on the Railway `islamicapps` service)

- `AUTH_ENABLED`, `PRIVATE_PREVIEW` — see Switches. Steps: `conductor/tracks/containment-and-access-control_20261121/railway-env-setup.md` §0.

- `CURATOR_PASSPHRASES` — JSON `{"<name>": "<scrypt hash>"}`. Absent or malformed: nobody can sign in.
- `ADMIN_SESSION_SECRET` — at least 32 characters of randomness. Shorter or absent: sessions fail closed.

- `CLIENT_IP_HEADER` (optional) — edge header that carries the client address; default `x-real-ip`.

Create a hash: `npm run --silent auth:hash` with the passphrase on stdin. Full owner steps: `conductor/tracks/containment-and-access-control_20261121/railway-env-setup.md`.

## Model

- With `AUTH_ENABLED=1`: reads are public. `/admin/**` and `/api/export/**` need a session in `src/proxy.ts` (GET redirects to
  `/sign-in`, anything else is 401). The proxy alone is not enough: server actions are POST endpoints reachable
  from any page, so every curation action's first line is `await requireCurator()`.
- A session is valid only while its name is still a key of `CURATOR_PASSPHRASES`, checked on every request.
- Cookie: httpOnly, Secure, SameSite=Strict, 12 hours, path `/`.
- Sign-in is a plain form posting to `/api/auth/sign-in` (route handler); return targets are limited to `/admin…`
  (any same-site path under private preview).
- Throttling and the read limit are per instance and reset on restart (accepted in section 7.3).

## Throttling

- **Reserve, then judge.** `reserveSignInAttempt(ip)` checks and counts in one synchronous step; the sign-in route calls it
  before its first await, and `reserveSignInName` right after the form parse, still before the scrypt comparison. Concurrent
  requests therefore cannot all pass a stale check. Only a correct passphrase releases (`confirmSignIn`: frees the address
  slot, clears the name). The proxy's `isSignInBlocked` is a read-only early answer.
- **Per name.** 20 per 15 min, lower-cased, across addresses, so one name cannot be brute-forced from many addresses. The
  window slides and blocked attempts are not counted, so a lock-out lasts at most 15 minutes after the attacker stops; an
  attacker who keeps sending 20 attempts per window can still keep one name from signing in. Open sessions are unaffected.
  Raise `SIGN_IN_NAME_LIMIT` rather than lower it if that bites.
- **Client address.** Never the left-most `X-Forwarded-For` hop (the client sets it). `clientIp` uses the edge header named by
  `CLIENT_IP_HEADER` (default `x-real-ip`), else the right-most `X-Forwarded-For` hop, and ignores values that are not an
  address. Railway's behaviour is recorded, with its verification status, in the track log.

## Revocation

- One curator: remove the name from `CURATOR_PASSPHRASES` and redeploy; their open session stops working at once.
- Everyone: rotate `ADMIN_SESSION_SECRET`; every session ends.
