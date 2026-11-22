---
type: instructions
for: chain-reader
version: 1.0.0
---

# Submitting chain fixes

You have read reports with the chain reader's instructions (`datasets/hadith-data/chain-reader/prompt.md`) and have one JSON
answer per report. This is how those answers become fixes. The tool decides what changed and whether anything is applied; you
only submit what you read.

## 1. Write one envelope for your run

```json
{"format": "shura-chain-fix-envelope/1",
 "run": {"model_id": "claude-haiku-4-5", "provider_runtime": "Claude Code subagent, fresh context",
         "run_id": "haiku-2026-11-22-a", "started_at": "2026-11-22T15:00:00Z", "finished_at": "2026-11-22T15:20:00Z",
         "prompt_sha256": "<SHA-256 of chain-reader/prompt.md, as given to you>", "view": "text_only"},
 "packet": "datasets/hadith-data/chain-reader/pilot/packets/packet-01.jsonl",
 "fixes": [{"output": <your reader JSON for one report, unchanged>,
            "reason": "One sentence: what the chain is, in your words.",
            "evidence": [{"quote": "<words copied exactly from the text>"}],
            "external_citation": null}]}
```

- `model_id`: the exact id your runtime reports. `run_id`: one id for your run, letters, digits, `.` `-` `_`; never reuse another
  run's id. Times are UTC, ending in `Z`.
- `view`: `text_only` if you saw only the report text (the usual case). `text_and_context` if your packet also carried a `context`
  block (reader v2/v3: work conventions, the sources' own claims, previous reports) but not the stored chain. `text_and_stored_chain`
  if you were shown the stored chain; then your quotes must cover every change you make.
- `prompt_sha256`: the SHA-256 of the reader prompt you ran under (v1 `chain-reader/prompt.md`, v2 `context/prompt-v2.md`, v3
  `v3/prompt-v3.md`); any other hash is refused. Reader v3 envelopes are written by `chain-reader/v3/to_submission.py`, not by hand.
- `evidence`: at least one quote per report, copied character for character (diacritics and punctuation included). Good
  quotes: the chain as written, or the words around the name you were unsure about.
- `external_citation`: only if you used a search or a printed edition. Give `{"url": "https://...", "quote": "<exact words>"}`
  or `{"edition_locator": "<work, volume, page>", "quote": "<exact words>"}`. Never cite from memory.

## 2. Submit

```
npx tsx reviews/ai/tools/chain-fix-submit.ts --envelope <your envelope.json> --reports datasets/hadith-data/chain-reader/pilot/reports.jsonl
```

Add `--check-only` to validate without recording.

## 3. Read the result

- Exit 0: every report recorded (`ok   <id> <hadith>: <kinds> -> <fix id>`), or already recorded (`dup`). You are done.
- Exit 1: **nothing** was recorded. Each `FAIL` line names the report (`fixes[N] (cr-0001)`) and what to correct, in the reader
  validator's words (`surface_mismatch: r0l1 ...`: route 0, link 1's surface is not the text at those offsets; copy it again
  from the text). Correct those entries and submit the whole envelope again. Offsets that are only miscounted are re-found for
  you; a surface that is not in the text is not.
- `stale text` or `prompt.md is now ...`: do not edit anything; tell the orchestrator. The report must be read again.

## Never

- Never edit, move or delete anything under `reviews/ai/records/chain-fixes/` or the overrides file; only the tools write them.
- Never touch the database. Never say who a narrator is: names only, as the reader prompt says.
- Never submit another run's answers as yours, or change a reader answer after the fact to make it pass.
