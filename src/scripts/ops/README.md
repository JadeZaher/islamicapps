# `src/scripts/ops/` — operator runbook scripts

Bash scripts that automate long-running operator workflows. Not loaded by `package.json`; invoked manually when needed.

## `post-regen-supervisor.sh` / `post-regen-supervisor-v2.sh`

**Purpose:** poll a running `db:regen --mode=fullregen` PID and, when it exits, automatically launch `db:regen --mode=test` to verify the rebuilt graph passes the guardrail suite. Writes the test log to `logs/regen-test-stdout-<ts>.log` and stamps `last-test-exit-code.txt` / `last-test-log-path.txt` for follow-up.

Usage:

```bash
./src/scripts/ops/post-regen-supervisor.sh <REGEN_PID> <REGEN_LOG_PATH>
```

Polls every 60s using `tasklist` (Windows-compatible; `kill -0` is unreliable across cmd / git-bash).

`v2` is the same flow with a longer poll interval used during the 2026-05-22 batched-loader rollout. Keep both for reproducibility of that incident's timeline; routine ops should use `post-regen-supervisor.sh`.

## When to add scripts here

Anything that:
- runs unattended for hours or days
- supervises a long-running ingest / regen / repair pass
- needs to survive harness shell timeouts

If it's a one-off probe or a TS query against Neo4j, put it under `src/scripts/` (or `src/scripts/archive/` if it's a one-off after the fact). This directory is reserved for **repeatable** operator workflows.
