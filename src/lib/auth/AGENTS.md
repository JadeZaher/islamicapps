# src/lib/auth — named-curator access (data-architecture.md section 10)

| File | What |
| --- | --- |
| `session.ts` | Cookie `curator_session` = `base64url({n: name, e: expiry}).base64url(HMAC-SHA256)`, Web Crypto only (used by `src/proxy.ts`) |
| `passphrases.ts` | scrypt hashes (`scrypt$N$r$p$salt$key`, base64url), constant-time verify, dummy hash for unknown names |
| `throttle.ts` | In-memory sliding windows on `globalThis`: 5 failed sign-ins per IP per 15 min; 30 anonymous reads per IP per minute |
| `require-curator.ts` | `requireCurator()` returns `curator:<name>` or throws `UnauthorizedError` |
| `hash-passphrase.ts` | Operator CLI: passphrase on stdin, hash on stdout |

## Environment (owner sets these on the Railway `islamicapps` service)

- `CURATOR_PASSPHRASES` — JSON `{"<name>": "<scrypt hash>"}`. Absent or malformed: nobody can sign in.
- `ADMIN_SESSION_SECRET` — at least 32 characters of randomness. Shorter or absent: sessions fail closed.

Create a hash: `echo -n '<passphrase>' | npx tsx src/lib/auth/hash-passphrase.ts` (proposed script `auth:hash`).

## Model

- Reads are public. `/admin/**` and `/api/export/**` need a session in `src/proxy.ts` (GET redirects to
  `/sign-in`, anything else is 401). The proxy alone is not enough: server actions are POST endpoints reachable
  from any page, so every curation action's first line is `await requireCurator()`.
- A session is valid only while its name is still a key of `CURATOR_PASSPHRASES`, checked on every request.
- Cookie: httpOnly, Secure, SameSite=Strict, 12 hours, path `/`.
- Sign-in is a plain form posting to `/api/auth/sign-in` (route handler); return targets are limited to `/admin…`.
- Throttling and the read limit are per instance and reset on restart (accepted in section 7.3).

## Revocation

- One curator: remove the name from `CURATOR_PASSPHRASES` and redeploy; their open session stops working at once.
- Everyone: rotate `ADMIN_SESSION_SECRET`; every session ends.
