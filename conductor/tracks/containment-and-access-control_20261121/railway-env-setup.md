---
type: runbook-note
track: containment-and-access-control_20261121
---

# Setting the curator environment on Railway

Two variables on the `islamicapps` service. Never paste real values into a file, chat or commit.

## 0. Switches (owner decision 2026-11-21)

| Variable | Default | Effect |
| --- | --- | --- |
| `AUTH_ENABLED` | off (unset) | Only `1` turns curator sign-in on. Off: `/sign-in`, `/api/auth/*`, `/admin/**`, `/api/export/**` answer 404, no sign-in or admin link is shown, every curation action refuses, and the session code is never reached. The deployment currently runs with it off (pipeline is the only writer) |
| `PRIVATE_PREVIEW` | off (unset) | Only `1`. Implies auth. Every route except sign-in, sign-out, `/api/health`, `/robots.txt` and static assets needs a signed-in curator; curators see all loaded data under a banner; every response is `noindex, nofollow`. Needs sections 1 and 2 below: without them the server refuses to start |
| `SITE_URL` | request host | Public origin used in citations, canonical links, robots and the sitemap, e.g. `https://example.org` |

Sections 1 to 3 matter only when `AUTH_ENABLED=1` or `PRIVATE_PREVIEW=1`.

### Running a private preview deployment

1. Create a curator hash (section 1) and a session secret (section 2); set `CURATOR_PASSPHRASES` and
   `ADMIN_SESSION_SECRET` on the service.
2. Set `PRIVATE_PREVIEW=1` (and `SITE_URL`). `AUTH_ENABLED` need not be set: preview implies it.
3. Deploy. If start-up logs `Refusing to start: PRIVATE_PREVIEW=1 needs ...`, a variable from step 1 is missing.
4. Open the site: you land on `/sign-in`; sign in and you return to the page you asked for, with the red preview strip.
5. To end the preview, unset `PRIVATE_PREVIEW` (and, if no curators should remain, `AUTH_ENABLED`).

## 1. Curator passphrases (`CURATOR_PASSPHRASES`)

Format: a JSON object `{"<curator name>": "<scrypt hash>"}`. Names are case-sensitive keys; the sign-in form must match.

Create one hash per curator (the passphrase is read from stdin; use a long random passphrase, 20+ characters):

```
# bash
printf '%s' '<passphrase>' | npm run --silent auth:hash
# PowerShell
'<passphrase>' | npm run --silent auth:hash
```

It prints one line, `scrypt$16384$8$1$<salt>$<key>`. Assemble the JSON on a single line:

```
{"<name-one>":"<hash-one>","<name-two>":"<hash-two>"}
```

Set it (bash quoting; in PowerShell or cmd use the Railway dashboard, Variables, Raw Editor, to avoid quote mangling):

```
railway variables -s islamicapps --set 'CURATOR_PASSPHRASES={"<name-one>":"<hash-one>"}'
```

Add or revoke a curator by editing the JSON and setting it again. Removing a name ends that curator's open session at
once (the name is checked on every request).

## 2. Session signing secret (`ADMIN_SESSION_SECRET`)

At least 32 characters of randomness; shorter or absent means every session fails closed.

```
node -e "console.log(require('crypto').randomBytes(48).toString('base64url'))"
railway variables -s islamicapps --set 'ADMIN_SESSION_SECRET=<paste the generated value>'
```

Rotating it ends every curator session at once.

## 3. Optional: client address header (`CLIENT_IP_HEADER`)

Only if the Railway edge does not overwrite `X-Real-IP` (see `log.md`, 2026-11-21 follow-up):

```
railway variables -s islamicapps --set 'CLIENT_IP_HEADER=x-forwarded-for'
```

## Notes

- Setting a variable redeploys the service from GitHub `main`, which is older than the running build (see
  `conductor/RUNBOOK.md`). Set these with the cutover deploy, not before.
- Confirm they exist without echoing values: `railway variables -s islamicapps --kv | cut -d= -f1`.
- Local development: both go in `.env.local` (git-ignored). The session cookie is `Secure`, so use https or a browser
  that treats `localhost` as a secure context.
