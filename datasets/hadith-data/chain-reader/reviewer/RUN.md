---
type: runbook
---
# Running the reviewer v1.1 job sets

Everything below is built and nothing has been run. From the repository root unless a command says `(from chain-reader/)`. Prompt: `prompt-reviewer-v1_1.md`, sha256 `1136aec2c975aebd0f4b8f17cf14d6ad1410229c33b97e7d8382b8258cb735f6` (the builder re-records it in `prompt-reviewer-v1_1.json`; edit the prompt and the hash and every job's instruction change, so rebuild after any edit).

## 1. The sets

| set (folder under `reviewer/`) | readings | packets = jobs | packet characters | input characters (prompt + instruction + packet, summed over jobs) | notes |
|---|---|---|---|---|---|
| `review-applied-b001/` (A) | 348 | 35 | 2,453,253 | 2,978,743 | status `applied`; 12 carry the non-clearable al-Faqih hold |
| `review-t01/eligible/` (B) | 730 | 73 | 5,758,873 | 6,854,895 | status `pending` (cleared, on the apply list) |
| `review-t01/held/` (B) | 133 | 14 | 1,171,043 | 1,381,015 | 73 `not_clearable` (a non-clearable hold stands: the review is recorded, the reading stays held); 3 `withheld_by_earlier_check` |
| `review-t02/eligible/` (B) | 695 | 70 | 5,486,837 | 6,537,817 | status `pending` |
| `review-t02/held/` (B) | 167 | 17 | 1,556,441 | 1,811,407 | 80 `not_clearable`; 5 `withheld_by_earlier_check` |
| `review-disagreements-t02/` (C) | 107 | 11 | 1,085,467 | 1,250,841 | readers differ; 15 `not_clearable` |
| **total** | **2,180** | **220** | **17,511,914** | **20,814,718** | roughly 6 to 8 million input tokens for pass 1 |

Each folder: `packets/packet-NN.json` (10 reports, opaque ids `cr1-xxxxxx`), `jobs.json` (`shura-chain-review-jobs/1`: per job `job_id`, `packet_file`, `packet_sha256`, `output_file`, `run_file`, `run_id`, `expected_items`, `not_clearable_items`, `input_chars`, `instruction`),
`private/` (`id_map.json` opaque to original id, `manifest.json` status, holds, `not_clearable`, `blocking_codes`, `stored_equals_reading`; the applied set also `applied_ids.txt`). Workers are told never to open `private/`; check that afterwards (§3). `SETS.json` holds this table.

The applied set came from `reviews/ai/records/chain-fixes/state.json` (394 fixes; 348 with `database: applied`, 9 `reverted`, 37 `not_applied`), cross-checked equal to `queue.json` `awaiting_final_review` (348 fix ids), mapped to reading ids through `submissions/*.jsonl`. A reading counts as applied only while `database == applied`: rebuild
(`python -B -X utf8 reviewer/build_review_packets_v1_1.py --sets`, from chain-reader/) if the store moves; a test fails when it has.

Rebuild everything: `--sets`. Packet content and ids are deterministic (the salt lives in `private/id_map.json`).

## 2. Run one set through Conduction

The reader tranches use `conduction/convert_tranche_jobs.py` -> `make_mission.py` -> `run_tranche.py`. Those scripts are not edited; the reviewer has its own converter that reuses `make_mission.build_factory` and the gate `check_tranche.py`:

```
python -X utf8 -B datasets/hadith-data/chain-reader/reviewer/make_review_mission.py datasets/hadith-data/chain-reader/reviewer/review-applied-b001/jobs.json --slug rv-applied-b001 [--concurrency 6] [--max-turns 60]
# writes review-applied-b001/conduction-jobs.json and factory-rv-applied-b001.json, prints the run command:
python -X utf8 datasets/hadith-data/chain-reader/conduction/run_tranche.py --factory datasets/hadith-data/chain-reader/reviewer/review-applied-b001/factory-rv-applied-b001.json
```
Dashboard and resume: `conduction/README.md` (start `app.py` on :8000 yourself; `--resume <factory_run_id>` was not exercised). Other sets: swap the jobs path and the slug (`rv-t01-held`, `rv-t01-eligible`, `rv-t02-held`, `rv-t02-eligible`, `rv-disagreements-t02`); pass 2 and re-queue files are `jobs-pass-2.json`, `jobs-pass-1r.json` (the converter names its files after the pass).

What differs from a reader tranche, and why:

| | reader tranche | reviewer set |
|---|---|---|
| job | 2 to 3 packets, 20+ output files | **one packet, one output file** (`outputs/pass-N/packet-NN.output.json`); an Opus worker reads a ~100 KB packet in one go |
| model | `claude-haiku-5-5`, hard-coded in `make_mission.MODEL` | **`claude-opus-5-5`**, set per agent by `make_review_mission.py` (it overrides the agent after `build_factory`; the instruction also asks the worker to record the exact model id in RUN.txt) |
| concurrency / turns | 12 / 150 | **6 / 60** by default: each worker holds roughly 30k tokens of packet and writes one file |
| agent name / wave | `read-<pass>-<job>` / `readers` | `review-<pass>-<job>` / `reviewers` |
| the claim note | `graph_claim` once with the expected files | same note (`make_mission.CLAIM_ADDENDUM`, unchanged), with the ONE output path; RUN.txt is appended by Bash because claims cover only Write/Edit; concurrent jobs append to the same RUN.txt |
| gate | `check_tranche.py`: every expected file exists and parses, every `run_id=<id> ` has a RUN.txt line | the same script on `conduction-jobs.json` (same keys); it does not judge a review, validation (§3) does |
| instruction | the reader's | `build_review_packets.instruction`: prompt path, version and hash, the one packet, "no private folder, no other packet, no database", write exactly the JSON, do not write a program, append the RUN.txt line, answer with the review count |

Sanity before a launch: cost scales with the input characters above (the 6 to 8 million token estimate assumes 2.5 to 3.5 characters per token; measure it on the first job). The pilot's workers took 22 seconds to 3.5 minutes per packet. Run A (35 jobs) first, or the pilot's 81 items again under v1.1, read the dispute rate, then C, then the B held lists, then the B eligible lists (the largest, 1,425 readings, and mostly confirmations).

## 3. Validate, record, second pass, re-queue (per item)

```
python -B -X utf8 reviewer/validate_review_v1_1.py --packet reviewer/<set>/packets/packet-01.json --output reviewer/<set>/outputs/pass-1/packet-01.output.json     (from chain-reader/; --allow-out-of-order for FORMAT_GAP.md)
python -B -X utf8 reviewer/record_reviews_v1_1.py --batch <set>                          # writes <set>/private/outcomes.tsv, summary.json, requeue.txt
python -B -X utf8 reviewer/build_review_packets_v1_1.py --second-pass --batch <set>      # pass 2: new packets-pass-2/, jobs-pass-2.json for the real corrections only
python -B -X utf8 reviewer/build_review_packets_v1_1.py --requeue --batch <set> [--pass 1]   # fresh packets for items with no valid review (packets-pass-1r/, jobs-pass-1r.json; again: 1r2)
```
(`<set>` is `review-applied-b001`, `review-t01/held`, ... as above.) Validation is per item: an invalid review is recorded invalid with its first reason, the item is re-queued, the rest of the packet stands. An output with a wrong header (format, specialist, prompt version, packet id) or not JSON voids its packet: every item is re-queued.
The record step counts a re-queue round's valid review in place of the missing one and a pass-2 review as the second run; run it after each pass. After a launch, list each transcript's tool calls (`.agentgraph/runs/<factory-run>-reviewers/transcripts/`) and confirm the only Reads are the prompt and the job's own packet.
There is no judge for these sets; the checks are `summary.json` (decision and outcome counts, items by status and outcome) and a human or Opus adjudicator reading a sample: every `label_disputed`, `revert_to_stored`, `queue_for_human` of an applied reading, and a random 20 of the confirmations (the pilot's confirmed right-reading rate was 49 of 52, the rest cosmetic).

## 4. Outcomes and the pipeline's actions (`review_rules_v1_1.outcome`, written to `outcomes.tsv`)

| outcome | class | what the pipeline does | label |
|---|---|---|---|
| `apply_reading` | apply | apply the agreed reading (held or pending) | "Read by model; AI reviewed (claude-opus-5-5), date; awaiting human review" |
| `apply_reader_a` / `_b` | apply | apply that reader's reading (readers differed; the reviewer preferred it, or its correction equals it) | same |
| `apply_correction` | apply | a second independent review wrote the same routes: apply the corrected reading as a new fix (on an applied reading it replaces it, not the stored chain) | "Corrected by AI review (claude-opus-5-5, 2 runs), date; awaiting human review" |
| `apply_no_chain` | apply | as a correction, to "no chain" | "No chain is written in this report (read by model; AI reviewed ...)" |
| `label_ai_reviewed` | label | applied reading stays; label gains the AI-reviewed words | as `apply_reading` |
| `label_disputed` | label | applied reading **stays**; label it; queue the correction for pass 2 (or the referral for a human) | "Read by model; disputed by AI review (claude-opus-5-5), date; awaiting second review" |
| `queue_for_human` | queue | nothing applied; both readings and the correction(s) listed for a person | unchanged |
| `keep_held` | hold | stays held, the review recorded (a non-clearable hold, or a referral with no correction) | unchanged |
| `discard_reading` | hold | `keep_stored` on a held reading: set aside, never applied, listed | unchanged |
| `revert_to_stored` | revert | only `keep_stored` on an applied reading whose stored chain differs from it: revert and list | the stored chain's own |
| `human_decides` | human | a human decision exists: it wins over everything above | "Verified by ..." / rejected |
| `requeue` | requeue | no valid review: the item stays exactly as it was; rebuild with `--requeue` | unchanged |
