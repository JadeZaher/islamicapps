---
type: runbook
---
# Full run of the chain reader v3.1: how to run a tranche and hand the result on

__TRANCHE_COUNT__ tranches of whole packets (__REPORTS__ reports, packets of 20), each a stratified mirror of the population (reports with an `uncertain` chain in the six Sunni books, al-Faqih and the other Imami works except al-Kafi; batch 001's 500 are out except the __REREAD__ reports of `v3_1/batch-001/reread_under_v3_1.txt`, which are in tranche 01).
Nothing here has been run. Each tranche is its own folder `tranches/tranche-NN/`: `packets/` (what a reader gets), `private/` (id_map.json, sample.json, reports.jsonl: **never give a reader anything under `private/`**), `jobs.json`, `manifest.json`, `outputs/pass-a|pass-b/` (empty).
Prompt: `v3_1/prompt-v3_1.md`, version 3.1.0, sha256 `__PROMPT_SHA__`. Check before a run (from `chain-reader/`):
`python -B -X utf8 -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" v3_1/prompt-v3_1.md`

## 0. Before the first tranche (the pipeline owner; outside `chain-reader/`)

Done 2026-11-22 (batch 001 applied through it; `reviews/ai/AGENTS.md` §Chain fixes, `conductor/RUNBOOK.md` "First model-read fixes applied (batch 001)"): prompt v3.1 is registered (`READER_PROMPTS.v3_1`);
the engine reads v3.1 readings with the `_v3_1` modules (`run.tool_version`, default the prompt's own tool); `chain-fix-submit` reads `shura-chain-no-chain-envelope/1` (the apply retires the stored chain, the page says no chain is
written) and keeps each fix's `inherited_from` on the submission (an inherited name is written as a mention repeating the earlier report's written mention, held when that report's chain is not rule-checked).
Inherited readings must be submitted with `--database production` (the earlier reports are read there). A report that also has a rule-checked chain is held (`stored_chain_checked_by_rule`) until the owner rules.

## 1. Readers (an orchestrator: a Conduction mission, or agents launched by hand)

`tranches/tranche-NN/jobs.json` lists the jobs: `jobs[]` of `{job_id, pass, packets, packet_files, output_dir, output_files, run_file, run_id, expected_files, input_chars, instruction}`. Give each job's `instruction` to ONE fresh agent as the whole task, nothing else; the model tier is
fixed for the whole run (`__MODEL__`, the tier of batch 001), pass A and pass B use the same tier and different agents. A job is done when `expected_files` files named in `output_files` stand in `output_dir` and the agent appended its line to `run_file`:
`run_id=<job_id> | packets=<P1>,<P2> | model=<model id> | start=<UTC start> | end=<UTC end> | files=<n>`. Pass B pairs the packets shifted by one so no agent reads the same pair twice. Do not show a pass the other pass's outputs.
Several agents append to the same RUN.txt: append, never rewrite (the converter finds a packet's run from the `packets=` list). A job that wrote fewer files than expected is run again whole (a new run id); outputs are not edited by hand.

## 2. Commands for tranche NN (from `datasets/hadith-data/chain-reader/`; Python as `python -B -X utf8`)

```
T=tranches/tranche-NN
# validate each pass (exit 1 and one line per missing, unparsable or invalid output; an invalid output counts as invalid, no retries inside the measurement)
python -B -X utf8 v3_1/validate_v3_1.py --packets $T/packets --outputs $T/outputs/pass-a
python -B -X utf8 v3_1/validate_v3_1.py --packets $T/packets --outputs $T/outputs/pass-b
# triage: expand, agree, holds, eligible (triage.tsv, readings/, eligible.txt, no_chain.txt, review_sample.txt, summary.json)
python -B -X utf8 v3_1/triage_v3_1.py --packets $T/packets --pass-a $T/outputs/pass-a --pass-b $T/outputs/pass-b --out $T/triage --reports $T/private/reports.jsonl
# envelopes: packet-NNN.envelope.json (readings with links, inherited ones carry inherited_from), packet-NNN.no_chain.envelope.json (agreed empty readings), not_submitted.tsv (with the reason)
python -B -X utf8 v3_1/to_submission_v3_1.py --packets $T/packets --reports $T/private/reports.jsonl --pass-a $T/outputs/pass-a --pass-b $T/outputs/pass-b --out $T/submissions --batch tNN
```

From the repository root, once section 0 is done (add `--check-only` to see what would be recorded; nothing is written then):

```
for f in datasets/hadith-data/chain-reader/tranches/tranche-NN/submissions/packet-*.envelope.json; do
  npx tsx reviews/ai/tools/chain-fix-submit.ts --envelope "$f" --reports datasets/hadith-data/chain-reader/tranches/tranche-NN/private/reports.jsonl
done
npx tsx reviews/ai/tools/chain-fix-decide.ts          # pairs the two passes' submissions, applies the auto-apply rule, rewrites the overrides and the queue; idempotent
```

The judge's sample (100 eligible readings, stratified by group, seed 20261200 + the tranche number), from `chain-reader/`:

```
python -B -X utf8 tranches/draw_judge_sample.py --tranche NN          # writes $T/judge/{sample.tsv, draw.json, dump.jsonl}
```

## 3. The gate between tranches

Read the 100 (right / wrong / undecided, with the Arabic quote; `analysis-batch-001/` is the model) before the next tranche's `chain-fix-submit` records anything. Stop on any reading that breaks a correct stored chain, or when the right-rate of the sample falls under 95%.
Batch 001's measured rate was __RATE__ among the judged eligible readings under the v3.1 tool (`v3_1/batch-001/RETRIAGE.md`). Report per tranche: valid, agreed, eligible (chain / no chain), holds by code, and the judge's table.
Tranche 01 also carries the __REREAD__ reports batch 001 re-reads; `eligible_to_apply.txt` of batch 001 (__ELIGIBLE_TO_APPLY__ readings) can be applied now, independently (`v3_1/batch-001/`).

## 4. The tranches

__TABLE__

Sizes, characters per job and the token estimate: `tranches/sizing.json`. Counts per work and the context coverage of each tranche: `tranches/tranche-NN/manifest.json`.
