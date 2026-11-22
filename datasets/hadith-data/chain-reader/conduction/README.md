---
type: runbook
---
# chain-reader on Conduction

Runs reader jobs (one fresh Haiku `claude-haiku-5-5` agent per job, the instruction of `v3/batch-001/RUN.md` section 1) as a Conduction factory: one wave, one agent per job, at most 12 at once.

## Run a tranche
Jobs file: list of `{job_id, pass, packets, prompt_file, output_dir, run_txt, run_id, expected_files, instruction}` (`jobs-test.json` is the example; the tranche builder emits the same shape). Run from the repository root.
```
# 1. build the factory (creates the output dirs, writes factory-<slug>.json next to this file)
python -X utf8 datasets/hadith-data/chain-reader/conduction/make_mission.py <jobs.json> --slug <tranche-slug> [--concurrency 12] [--max-turns 150]
# 2. dashboard on :8000 (see Dashboard), then launch and wait (polls every 20 s, 40 min bound)
python -X utf8 datasets/hadith-data/chain-reader/conduction/run_tranche.py --factory datasets/hadith-data/chain-reader/conduction/factory-<tranche-slug>.json [--base http://127.0.0.1:8000]
# 3. measure with RUN.md section 3 on the jobs' output dirs
```
`run_tranche.py` exits 0 only when the factory completed (gate passed).

## What the mission does
- Agent `read-<pass>-<job_id>`: `sdk: claude`, `model: claude-haiku-5-5`, tools `Read, Write, Bash`, `owns` = its expected files.
- Brief = `instruction` plus a short harness note: Conduction's claim ledger refuses a Write on an unclaimed file and claims are per exact path (no directory claim), so the worker calls `graph_claim` once with its expected paths. RUN.txt is appended by Bash (claims cover only Write/Edit), so concurrent jobs of one pass append to the same RUN.txt.
- Wave gate (`check_tranche.py`): every expected file exists and parses as JSON, and every `run_id` has a RUN.txt line. The reading is not judged there; `validate_v3.py` and `triage_v3.py` do that.
- Concurrency: `max_concurrency` of the wave (default 12; the generator refuses more). `max_turns` 150 (a job used about 50).

## Dashboard
`conduction.ps1` failed on this machine (see `C:\Users\atooz\Programming\conduction\NOTES-chain-reader-mission-2026-11-22.md`): the recorded port 8001 is held by an old Conduction (PID 129412, since 2026-11-14) and the launcher then died on a locked log. Start a server directly:
```
$env:CONDUCTION_PORT="8000"; $env:CONDUCTION_SCHEDULER="0"
Start-Process "C:\Program Files\Python312\python.exe" -ArgumentList "-X","utf8","app.py" -WorkingDirectory C:\Users\atooz\Programming\conduction -WindowStyle Hidden -PassThru
```
Stop it with `Stop-Process -Id <that PID>`. The run shows at http://127.0.0.1:8000/factory and /runs (factory run `<slug>-<epoch>`, wave run `<slug>-<epoch>-readers`). Run state is files under `<repo>/.agentgraph/`, so the launching server and the dashboard server may be different processes.

## Monitor and resume
- Files: `ls <output_dir> | wc -l`; transcripts `<repo>/.agentgraph/runs/<factory-run>-readers/transcripts/<agent>.md` (every tool call as a `**-> Tool**` line); state `<repo>/.agentgraph/factory-runs/<id>/state.json`.
- Stop: `POST /api/factory/runs/<id>/interrupt`. Resume: `run_tranche.py --resume <factory_run_id>` (`/api/factory/runs/<id>/resume`). Resume was NOT exercised.

## Verified (2026-11-22, packets 001-004, 4 jobs, outputs `v3/batch-001/conduction-test/pass-a|b`)
All 4 jobs ran, gate passed, 160 files plus 2 RUN.txt files, every RUN.txt line says `model=claude-haiku-5-5` (also `model:` in the transcripts), 4 concurrent, 8 min wall clock (launch 17:32:14Z, done 17:40:14Z; job latencies 394-467 s, 48-52 turns), cost reported by Conduction USD 1.90 (0.41 to 0.54 per job); no token counts.
Same 80 reports, hand run vs Conduction: valid a 77 vs 78, valid b 79 vs 78; agreed 73 vs 72; eligible 64 vs 63. Conduction pass-a equals hand-run pass-a on 69 of 77 jointly valid reports (cond-b vs hand-b 74/78; hand-a vs hand-b 73/77; cond-a vs cond-b 72/78), the spread of two hand-run passes.
Tool audit from the transcripts: the only Reads are `prompt-v3.md` and the job's own two packets, Writes only to the job's output files, Bash only `date -u` and the RUN.txt `echo >>`, plus `ToolSearch` and `graph_claim`. Nothing touched `private/`, other passes, the database or the web.

## Limits
- Read paths and Bash commands are not restricted by Conduction (only claims for Write/Edit and a destructive-command filter): "read nothing else" is the brief's rule, checked afterwards by listing every tool-call line of each transcript.
- The reader instruction is verbatim except the appended harness note (claim step).
- Cost, not tokens, is reported. Only 4 concurrent agents were exercised, not 12.
