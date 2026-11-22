---
type: runbook
---
# Batch 001: how to run the readers and hand the result on

500 reports in 25 packets of 20 (`packets/`, manifest `packets/manifest.json`), drawn at random from the live uncertain population (`draw.json`: seed 20261122, exclusions, strata).
Packets carry opaque ids (`b1-xxxxxx`); the map to hadith ids is `private/id_map.json`. **Never give a reader anything under `private/`.** Nothing here has been run.

Prompt: `v3/prompt-v3.md`, version 3.0.0, sha256 `a5a223b6acfc0b0d25260624bf527284f40a57576ba422f5e821e15dd0827764` (also `v3/prompt-v3.json`). Check before a run:
`python -B -X utf8 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" v3/prompt-v3.md` (from `chain-reader/`).

## 1. The instruction to give each reader agent

One fresh agent per two packets (40 reports); 13 agents per pass, 26 for both passes. Fill the four placeholders and give the text below as the whole task, nothing else.
Placeholders: `{P1}`, `{P2}` the packet numbers (`001`, `002`), `{PASS}` `a` or `b`, `{RUNID}` a unique id of letters, digits, `.`, `-`, `_` (for example `b1-a-001-002`).
Use a fresh context and a model tier fixed for the whole batch (the pilot used `claude-haiku-5-5`); both passes use the same tier, different agents.

```
You are a chain reader. Your instructions are the file
  c:\Users\atooz\Programming\experiments\islamicapps\datasets\hadith-data\chain-reader\v3\prompt-v3.md
(version 3.0.0, sha256 a5a223b6acfc0b0d25260624bf527284f40a57576ba422f5e821e15dd0827764). Read all of it before you start.

Your input is two packet files, JSON lines, each line {"id", "text", "context"}:
  c:\Users\atooz\Programming\experiments\islamicapps\datasets\hadith-data\chain-reader\v3\batch-001\packets\packet-{P1}.jsonl
  c:\Users\atooz\Programming\experiments\islamicapps\datasets\hadith-data\chain-reader\v3\batch-001\packets\packet-{P2}.jsonl

For EVERY line write one file named after that line's id:
  c:\Users\atooz\Programming\experiments\islamicapps\datasets\hadith-data\chain-reader\v3\batch-001\outputs\pass-{PASS}\<id>.json
holding exactly the JSON object the prompt describes for that report: no markdown fence, no commentary, no other keys. Read each report yourself, from its text and its context;
do not write a program that produces the readings. Never skip an id: a report you cannot read still gets its file (status, groups and notes as the prompt says).

Read nothing else: not the other pass's outputs, nothing under the batch's private folder, no other packet, no database, no web. Do not edit any packet or any file but your own outputs.

When every file is written, append ONE line to
  c:\Users\atooz\Programming\experiments\islamicapps\datasets\hadith-data\chain-reader\v3\batch-001\outputs\pass-{PASS}\RUN.txt
exactly in this form (UTC times like 2026-11-23T09:00:00Z; the model id is the exact id your runtime reports; take the start time before you read the first packet):
  run_id={RUNID} | packets={P1},{P2} | model=<model id> | start=<UTC start> | end=<UTC end> | files=<number of files you wrote>
Then answer with the number of files only.
```

Pass B uses the same text with `{PASS}` = `b`. Shift the pairing in pass B by one packet (`001` alone, then `002,003`, `004,005` ...) so no agent reads the same pair of packets twice;
any grouping works: the converter finds a packet's run from the `packets=` list of its RUN line.

## 2. Layout

```
v3/batch-001/
  packets/            packet-001.jsonl .. packet-025.jsonl, manifest.json      what the readers get
  outputs/pass-a/     <id>.json x 500, RUN.txt (one line per agent run)       pass A
  outputs/pass-b/     <id>.json x 500, RUN.txt                                pass B (never shown pass A)
  triage/             triage.tsv, readings/<id>.json, eligible.txt, review_sample.txt, summary.json     (written by triage_v3.py)
  submissions/        packet-NNN.envelope.json, not_submitted.tsv                                    (written by to_submission.py)
  private/            id_map.json, sample.json, reports.jsonl, population.jsonl                       never given to a reader
```

## 3. Commands (from `datasets/hadith-data/chain-reader/`; Python as `python -B -X utf8`)

```
# 1. validate each pass (exit 1 and one line per missing, unparsable or invalid output; no retries inside the measurement: an invalid output counts as invalid)
python -B -X utf8 v3/validate_v3.py --packets v3/batch-001/packets --outputs v3/batch-001/outputs/pass-a
python -B -X utf8 v3/validate_v3.py --packets v3/batch-001/packets --outputs v3/batch-001/outputs/pass-b

# 2. expand (levels to routes with offsets, compiler head, same-man merge), agree (canonical equal), compute holds, list the eligible reports: one command, one row per report
python -B -X utf8 v3/triage_v3.py --packets v3/batch-001/packets --pass-a v3/batch-001/outputs/pass-a --pass-b v3/batch-001/outputs/pass-b --out v3/batch-001/triage --reports v3/batch-001/private/reports.jsonl
#    triage.tsv: valid_a valid_b agree flag holds eligible problems; readings/<id>.json: the expanded agreed reading; eligible.txt = agreed, status read, no hold;
#    a needs_ruling flag from ONE reader goes to review_sample.txt, from both it is the hold `needs_ruling`.

# 3. hand the agreed-and-unheld readings to the fix pipeline (envelopes per packet; reports that cannot be submitted are listed with the reason)
python -B -X utf8 v3/to_submission.py --packets v3/batch-001/packets --reports v3/batch-001/private/reports.jsonl --pass-a v3/batch-001/outputs/pass-a --pass-b v3/batch-001/outputs/pass-b --out v3/batch-001/submissions
# from the repository root:
npx tsx reviews/ai/tools/chain-fix-submit.ts --envelope datasets/hadith-data/chain-reader/v3/batch-001/submissions/packet-001.envelope.json --reports datasets/hadith-data/chain-reader/v3/batch-001/private/reports.jsonl --check-only
```

Step 3 will say `FAIL` until the pipeline owner extends the submit tool; the three things it pins (`v3/AGENTS.md` section submission): the prompt hash is `chain-reader/prompt.md`'s (the envelope carries v3's),
`run.view` must be `text_only` or `text_and_stored_chain` (the envelope says `text_and_context`, because the readers saw the context), and a `text_only` view demands a blind packet. Do not edit the envelope to pass.

## 4. Measuring (what the batch is for)

The judge reads every eligible reading of the six-book stratum and of al-Faqih, and a random 100 of the other Imami (README section 5), against the Arabic, and records right / wrong / undecided with the quote.
Rates are per stratum with Wilson bounds; the post hoc holds (`routes_end_at_different_links`, `back_reference_only`, `second_isnad_not_same_saying`) are judged here for the first time out of sample:
count their hits and how many of those readings were right. Back-reference reports (`opening` in `private/id_map.json`) are their own stratum.
