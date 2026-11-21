---
type: runbook-note
track: containment-and-access-control_20261121
---

# Setting the curator environment on Railway

Two variables on the `islamicapps` service. Never paste real values into a file, chat or commit.

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
