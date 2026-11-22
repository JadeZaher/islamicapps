---
type: integration
---
# What the fix-pipeline owner must add for the AI reviewer (and the v3.4 saying label)

Nothing below is built: these are the integrator's files (`reviews/ai/`, `src/`, `drizzle/`, `datasets/hadith-data/chain-fixes/`). Each item names the file and the reason. The semantics to
implement are `review_rules.py` (vocabulary, clearable holds, `outcome()`) and `README.md` §2; import or mirror them, do not re-derive.

## 1. Register the reviewer as a specialist

| file | add | why |
|---|---|---|
| `src/lib/review/procedures.ts` | a `Specialist` after `CHAIN_READER_SPECIALIST`: id `chain-reviewer`, version `1.0.0`, claimKinds `['chain_structure']`, title "Chain reviewer (AI first pass of final review)", prompt `datasets/hadith-data/chain-reader/reviewer/prompt-reviewer-v1.md`, packet lines (report Arabic and context, both readers' readings and notes, the tool's holds in plain words, the stored chain), recommendedModel `claude-opus-5-5`, modelReason "close reading of the Arabic against two model readings; must out-read the readers it reviews", notThisModel `['claude-haiku-5-5 (the readers it reviews)']`, `measured: null`, `unmeasured: 'Pilot built (reviewer/pilot-001, 81 tranche-02 reports judged by an independent reader); not run.'` | `/method` and the registry are generated from this list (`build-specialist-registry.ts`) |
| `reviews/ai/specialists.json` | regenerate: `npx tsx reviews/ai/tools/build-specialist-registry.ts` | the registry records prompt hash `46606e81…` and later every run |
| `reviews/ai/tools/specialist-lib.ts` (or the registry builder's prompt list) | accept a prompt path outside `reviews/ai/prompts/` (the chain reader's already is) | the reviewer prompt lives beside its tools, as the reader's does |

## 2. `chain-fix-review --ai`: record the reviewer's runs

| file | add | why |
|---|---|---|
| `reviews/ai/tools/chain-fix-review.ts` | `--ai` already needs `--model`, `--prompt`, `--prompt-sha256`; add **`--run-id`** (the job's `run_id`), **`--packet`** + `--packet-sha256`, `--started` / `--finished` (UTC, from RUN.txt), and **`--review-decision`** with the reviewer vocabulary (`confirm_reading` … `refer_to_human`), `--question`, `--uncertainty`, and the review's `reasons` / `variant_verdicts` / `corrected_reading` as one `--review-json <file>` | an AI review must be reproducible (packet, prompt and model by hash, the time) and carry its reasons with their quotes |
| new `reviews/ai/tools/chain-review-record.ts` | read a whole `outputs/pass-N/packet-NN.output.json`, validate it exactly as `reviewer/validate_review.py` does (or shell out to it), map opaque ids to fix ids through `reviewer/<batch>/private/id_map.json` + the store, and write one review row per report | 10 reports per packet: recording them one CLI call at a time invites mistakes |
| `reviews/ai/tools/chain-fix-lib.ts` | `Review`: `reviewer_kind: 'ai'` rows gain `run_id`, `packet_sha256`, `started_at`, `finished_at`, `review_decision`, `question`, `uncertainty`, `reasons`, `variant_verdicts`, `corrected_reading`, `pass` (1 or 2); keep `decision` (`confirmed` / `rejected` / `superseded`) for humans only | the human vocabulary and the AI vocabulary must not mix: only a human `confirmed` is "verified" |
| `docs/review/schema-proposal.ts`, `drizzle/` migration | the same columns on the review table, `check (reviewer_kind = 'ai') = (review_decision is not null)`; `check (reviewer_kind = 'human' or decision is null)` | the database enforces what the files do |

## 3. State transitions (`chain-fix-decide.ts`, `chain-fix-lib.ts` `reconcile`)

Today `docs/review/chain-fix-pipeline.md` rule 5 says "AI reviews never move a fix". The owner's ruling changes that for this reviewer only; rule 5 becomes: an AI review by a registered
reviewer moves a fix only as `review_rules.outcome()` says, and any human review overrides it. New states and moves:

| from | AI review | to | apply step |
|---|---|---|---|
| held (any hold, all clearable; or `disputed`) | `confirm_reading` on an agreed reading | `accepted` with `ai_reviewed: {model, run_id, at}` | apply |
| `disputed` | `prefer_reader_a` / `_b` | that reading `accepted` (`ai_reviewed`), the other `outvoted` | apply |
| held / `disputed` | `confirm_with_correction`, pass 2 gives equal routes (`readings_agree_v3_4`) | a NEW fix from the corrected reading, `accepted` with `ai_corrected: {runs: [run1, run2]}`; the readers' fix `superseded` | apply |
| held / `disputed` | `confirm_with_correction` with one run or unequal runs | `awaiting_human` (new state; both readings and the corrections listed) | none |
| held | `no_chain` (agreed reading empty) | as `confirm_reading` | apply as no-chain |
| held | `no_chain` against routes | as `confirm_with_correction` (pass 2 must also say `no_chain`) | apply as no-chain, or none |
| held | `keep_stored` | `set_aside_by_ai` (new; listed for a human) | none |
| held | `refer_to_human` | stays held; the question stored on the fix | none |
| held with a NON-clearable hold | anything | unchanged; the review is recorded | none |
| `accepted` (applied) | `confirm_reading` | unchanged, `ai_reviewed` added | relabel only |
| `accepted` (applied) | anything else | `awaiting_human` + **revert** (`database: reverted`); a correction confirmed by pass 2 then applies as above | revert, maybe apply |
| any | a human review | the existing human rules (reject, supersede, confirm) win over any AI state | as today |

The clearable list must be the code's (`review_rules.HOLDS`); a hold code the pipeline knows and the list does not is NOT clearable. `stale` (text changed) is never cleared: re-read.

## 4. Page labels (`src/app/hadith/[id]/components/chain-structure.ts`, `public_chain_fix_labels` view)

| state | wording |
|---|---|
| applied, AI-reviewed (confirmed or preferred) | "Read by model; AI reviewed (claude-opus-5-5), <date>; awaiting human review" |
| applied correction | "Corrected by AI review (claude-opus-5-5, 2 runs), <date>; awaiting human review" |
| applied no-chain, AI-reviewed | "No chain is written in this report (read by model; AI reviewed (claude-opus-5-5), <date>; awaiting human review)" |
| two sayings (v3.4) | each route under "Chain of the first saying" / "Chain of the second saying", with the saying's opening words (`fix.sayings[].opens`) |

Never "verified" for any of these; `verified_by_reviewer` stays human-only. The view gains `ai_reviewed_at`, `ai_review_model`, `ai_corrected`.

## 5. `/method` and the model registry

| file | add | why |
|---|---|---|
| `src/lib/review/procedures.ts` (the chain-fix procedure's text) | one paragraph: what the AI reviewer does, which holds it may clear and which never, that a correction needs two runs, that an applied reading it does not confirm is reverted, that a human decision overrides it, and the pilot result once measured | `/method` publishes how a chain reached the page |
| `datasets/hadith-data/model_registry.json` | an entry `claude-opus-5-5-chain-reviewer`: model `claude-opus-5-5`, role "AI first pass of final review of model-read chains", prompt path and sha256, output status `ai_reviewed, awaiting human review`, batches; then `render_model_docs.py` | the registry records which model did which work |
| `conductor/RUNBOOK.md` | the run commands (`README.md` §3) and the gate | the runbook is the environment's pulse |

## 6. The v3.4 saying label (prompt v3.4, `v3_4/`)

| file | add | why |
|---|---|---|
| `datasets/hadith-data/chain-fixes/chain_fix_engine.py` | tool version `v3_4`: import `v3_4/expand_v3_4.py`, `holds_v3_4.py`, `validate_v3_4.py`; carry `sayings` from the envelope's fix onto the planned chains (route index to saying number, label, opening) | the engine re-expands `reader_output_v3`; a v3.2 engine rejects a labelled output |
| `reviews/ai/tools/chain-fix-submit.ts` | accept `run.tool_version: "v3_4"` and the fix key `sayings`; `--sayings-supported` mirrors the triage flag (lifts `two_sayings_not_supported`) | today an unknown key or tool version is refused |
| `chain-fix-lib.ts` types, `src/db/schema/chain-fixes.ts`, migration | `sayings` on the fix (jsonb) and `saying` (smallint, null) on each planned branch | the page shows the label per route |
| `chain-structure.ts` | §4's two-sayings wording | owner ruling (b): "Chain of the first saying / second saying" |
