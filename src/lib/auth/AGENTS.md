# src/lib/auth — named-curator access (data-architecture.md section 10)

| File | What |
| --- | --- |
| `session.ts` | Cookie `curator_session` = `base64url({n: name, e: expiry}).base64url(HMAC-SHA256)`, Web Crypto only (used by `src/proxy.ts`) |
| `passphrases.ts` | scrypt hashes (`scrypt$N$r$p$salt$key`, base64url), constant-time verify, dummy hash for unknown names |
| `throttle.ts` | In-memory sliding windows on `globalThis`: 5 sign-in attempts per address and 20 per curator name per 15 min; 30 anonymous reads per address per minute; `clientIp` |
| `throttled-response.ts` | Blocked sign-in answer: browsers 303 to `/sign-in?error=throttled`, others 429 |
| `require-curator.ts` | `requireCurator()` returns `curator:<name>` or throws `UnauthorizedError` |
| `hash-passphrase.ts` | Operator CLI: passphrase on stdin, hash on stdout |

## Environment (owner sets these on the Railway `islamicapps` service)

- `CURATOR_PASSPHRASES` — JSON `{"<name>": "<scrypt hash>"}`. Absent or malformed: nobody can sign in.
- `ADMIN_SESSION_SECRET` — at least 32 characters of randomness. Shorter or absent: sessions fail closed.

- `CLIENT_IP_HEADER` (optional) — edge header that carries the client address; default `x-real-ip`.

Create a hash: `npm run --silent auth:hash` with the passphrase on stdin. Full owner steps: `conductor/tracks/containment-and-access-control_20261121/railway-env-setup.md`.

## Model

- Reads are public. `/admin/**` and `/api/export/**` need a session in `src/proxy.ts` (GET redirects to
  `/sign-in`, anything else is 401). The proxy alone is not enough: server actions are POST endpoints reachable
  from any page, so every curation action's first line is `await requireCurator()`.
- A session is valid only while its name is still a key of `CURATOR_PASSPHRASES`, checked on every request.
- Cookie: httpOnly, Secure, SameSite=Strict, 12 hours, path `/`.
- Sign-in is a plain form posting to `/api/auth/sign-in` (route handler); return targets are limited to `/admin…`.
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
