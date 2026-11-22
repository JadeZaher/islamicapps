---
type: design
---

# Chain fixes: model readers submit, agree, apply, and wait for final review

Rule-based chain extraction has plateaued (`datasets/hadith-data/chain-audit/round4/README.md`: about 8% of Sunni chains marked
`checked_by_rule` are still wrong out of sample; two thirds of `uncertain` chains are right). The chain reader
(`datasets/hadith-data/chain-reader/`) reads one report's Arabic and returns its routes. This note is everything after that:
submission, the store, the agreement rule, the database write, final review, reversal and reload replay.

Built (2026-11-22): the store, four CLIs, the Python engine and replay helper, tests. Drafted, not run: the migration, Drizzle
declarations, the database apply/revert and the load invariants (`src/db/ops/pending/`), because another lane owned the schema.

## The pieces

| Piece | Where | Writes |
| --- | --- | --- |
| Reader prompt (unchanged, referenced by hash) | `datasets/hadith-data/chain-reader/prompt.md` | nothing |
| Agent instructions | `reviews/ai/prompts/chain-fix-submission.md` | nothing |
| Engine: the reader's validator, comparison with the stored chain, planned rows | `datasets/hadith-data/chain-fixes/chain_fix_engine.py` | nothing |
| `submit`, `decide`, `review`, `status` | `reviews/ai/tools/chain-fix-*.ts` | the store |
| Store (append-only) | `reviews/ai/records/chain-fixes/` | |
| Overrides the projection replays | `datasets/hadith-data/chain-fixes/accepted_overrides.jsonl.gz` (written by decide/review) | |
| Replay helper for the projection | `datasets/hadith-data/chain-fixes/replay.py` | nothing |
| Database mirror, apply, revert (draft) | `src/db/ops/pending/chain-fix*.{sql,ts}` | the database |

Every Arabic rule (validation, folding, comparison, mark stripping, normalization, review-unit ids) runs in one Python module,
which imports the reader's `validate.py`/`norm.py`/`score.py` and the projection's `name_normalize`, so the submit tool, the
database apply and the projection replay cannot drift apart. The TypeScript CLIs own provenance, the store, concurrency and the
rules about readers and reviewers, like the other `reviews/ai/tools/`. A CLI calls the engine once per invocation.

## What a reader submits

An envelope (`shura-chain-fix-envelope/1`) per reader run: the run (`model_id`, `provider_runtime`, `run_id`, UTC `started_at`
and `finished_at`, the `prompt_sha256` it ran under, and `view`: `text_only` or `text_and_stored_chain`), the packet it read,
and one entry per report: the reader's JSON exactly as the prompt defines it, a one-sentence `reason`, `evidence` quotes and an
optional `external_citation` (`url` or `edition_locator`, plus the exact `quote`).

`submit` refuses the whole envelope, one line per problem, when any of these fail:
- the reader's own validator (`validate.py`, unchanged): surfaces equal `text[start:end]`, order, no overlap, nothing at or after
  `matn_start`, the kind vocabulary, real shared tails. Offsets that are only miscounted are re-found from the surfaces
  (`repair_offsets`, as `score.py` does) and the record says so; a surface not in the text is never repaired;
- every evidence quote is an exact substring; a reader who saw the stored chain must also quote around every change (each added
  or changed link inside a quote, each removed name inside a quote);
- the prompt hash is the current `prompt.md`'s (a reading under an older prompt is re-run, not recorded);
- the text: the packet's text must be the report's current text (`--reports`, or production read-only with `--database
  production`), else "stale text";
- a `text_only` reading must come from a packet that shows only `{id, text}`;
- the report's stored chain must not repeat names from an earlier report (`inherited_from_mention_id`): the reader cannot see
  them.

What the tool computes, never the agent: the fix kinds against the stored chain (`no_change`, `link_added`, `link_removed`,
`surface_changed`, `route_split`, `routes_merged`, `shared_tail_attached`, `chain_removed`, `chain_added`), the evidence of each
added or changed link (its exact text with offsets, labelled `computed_evidence`), the two text hashes, the stored chain it was
compared with (rows and SHA-256), and the planned rows. Comparison folds both sides the same way (`norm.fold_loose` over
`name_normalize`, the extractor's trailing «ع» dropped, «بهذا الإسناد» dropped as `score.py` does), so «أبي سعيد، الخدري» read
from the text equals the stored «أبي سعيد الخدري».

Each record is the review-record shape plus the reading: `specialist_id` `chain-reader`, prompt path, version and SHA-256,
`model_id`, `provider_runtime`, `orchestrator_run_id`, packet path, SHA-256 and item id, UTC times, `review_kind: specialist`,
`label: "AI reviewed"`.

**Binding.** A fix is bound to `arabic_sha256` (the report's `text_ar`, the hash every other projection binding uses) and to
`reader_text_sha256` (the exact string the offsets count in: for Ahmad, al-Darimi and al-Muwatta the source's chain field, a
blank line, then `text_ar`).

**Identity of a fix.** `fix_id = sha256(hadith_id, arabic_sha256, reader_text_sha256, routes_key)`; `routes_key` hashes what
would be applied (per route in text order: span and link kind). Two readers who write the same routes in another order, or
call «أبيه» `relation` versus `narrator`, have the same fix. `submission_id` adds the run and model: the same run submitting the
same reading again is a duplicate ("dup", nothing written).

## Concurrency

Many Haiku agents submit at once. Each run appends only to its own file, `submissions/<run id>.jsonl`, one whole-lines write
under an exclusive lock file (`open(..., 'wx')`; a lock older than two minutes is a crashed writer's). Two runs never share a
file. A race between two invocations of one run can at worst write a duplicate line; every reader of the store keys by
`submission_id` and keeps the first, so a duplicate changes nothing. Reviews append to `reviews/<kind>-<reviewer>.jsonl` the same
way. `decide` and `review` recompute state under one `store.lock`. Derived files (`state.json`, `queue.json`, the overrides) are
written to a temporary file and renamed.

## States and who moves a fix

| State | Meaning | Moved by | A reader of the site sees |
| --- | --- | --- | --- |
| `submitted` | one reader run so far | decide | the stored chain, unchanged |
| `disputed` | readers disagree and no reading wins by the rule | decide | unchanged; queued for a third reader or a human |
| `outvoted` | another reading of the report won by the rule | decide | unchanged |
| `accepted` | agreed and passed the auto-apply rule; in the overrides; the database apply writes it | decide | "Read by model (claude-haiku-4-5, 2 readers), 2026-11-22; awaiting final review" |
| `confirmed` | a named human confirmed it; no human rejects | review | "Verified by <reviewer>, <date>" with the note and citation |
| `rejected` | a human rejected it | review | the rule-built chain again, with its own status |
| `superseded` | a human marked it superseded, or confirmed another reading of the report | review | whichever reading stands |
| `stale` | read from an older text of the report | decide | unchanged; re-read the current text |

Separately, per fix, `database`: `not_applied`, `applied`, `reverted`, from the apply's records.

**Why `accepted` and not the brief's `agreed` then `applied`.** In the store every agreed reading passes the auto-apply rule at
once (it was validated, and both readers are bound to the same text by construction), so a separate `agreed` state would never
be observed. And "applied" is a database fact the file tools cannot know: it is the `database` field, written by the apply. Two
honest dimensions instead of one state that would claim a write that has not happened.

**Final review** (`review`). Any number of reviewers; each review is one row with the reviewer's name or handle, the date, a
note, an optional citation (URL or edition locator with the exact quote), and for an AI reviewer the model and the prompt path
and hash. The latest review per reviewer counts; every earlier one stays. Rule:
1. any human rejection: `rejected` (one human is enough to reverse; a wrong chain shown is worse than the rule-built one back);
2. else a human `superseded` naming another fix of the report: `superseded`;
3. else any human confirmation: `confirmed` (only this is ever worded "verified": status `verified_by_reviewer`);
4. a human confirmation of one reading of a disputed report settles it; the other readings become `superseded`;
5. AI reviews never move a fix; an AI that does not confirm is counted as an objection and listed for a human.

## The auto-apply rule

Per report, among current submissions (bound to the newest text) and counting each run's latest reading once: a reading is
`accepted` when
- at least **two** runs gave it, and
- at least **one** of those runs was **blind** (`view: text_only`: it saw the text and nothing else, neither the stored chain nor
  another reader), and
- it has at least **twice** the runs of every other reading together (2 against 1 settles a dispute; 1 against 1, or 3 against 2,
  does not), and no other reading ties it.

A lone reading never changes a chain. The one exception: a lone reading that equals the stored chain (`no_change`) is recorded
beside it (`effect: annotate`: a line "a model reader read the same routes"), and nothing is replaced. Two agreeing `no_change`
readings of an `uncertain` chain set its status to `read_by_model` (`set_status`), rows unchanged. A changed reading replaces the
routes (`replace_routes`) with status `read_by_model`.

**The risk.** Two readers can share a mistake: the same model under the same prompt has correlated errors (it may drop the same
Companion named in a matn, or keep the same gloss). Agreement measures consistency, not correctness. It is measured on the
labelled pilot set (`datasets/hadith-data/chain-reader/pilot/`, 284 reports labelled correct or defective by the round 2-4
re-checks): run two independent blind readers over the packets, then `python score.py --reports pilot/reports.jsonl --outputs
<run-a> --outputs-b <run-b>`, and count, per work with Wilson intervals, how often an **agreed** reading is wrong against the
labels. That figure, not the agreement rate, is what `/method` must publish for `read_by_model`. Records keep the model per run,
so the rate can be split into "same model twice" and "two models". Until it is measured: `read_by_model` chains are labelled
"awaiting final review", and they form no teacher-student pair (integration step 5), so a shared mistake reaches the page as a
labelled reading, never the narrator network.

## Identities on apply

The reader never says who a narrator is; identity stays a separate review. The engine aligns each read route with the stored
branch that shares its longest run of names (two read routes may align with one stored branch, so a split keeps the shared tail's
evidence), and per name records `kept_mention_id` (the stored mention it is, matched in sequence, so a name written twice is
matched in order) and `carry_identity`.
- **A kept name keeps its identity evidence**: every `chain_mention_candidates` row of the stored mention is copied onto the new
  mention (candidate id recomputed by the projection's formula). `source_position` is kept unchanged: it indexes the source's own
  narrator list (K6, hadith-kg, Riwayat), not our chain, so a link added before the name does not move it.
- **A kept name keeps its standing identity** (`narrator_id`, `resolution`, `resolution_basis`, `confidence`, `extraction_method`,
  `decision_id`, `identity_withheld_reason`, link kind) **only when both neighbours are unchanged**: the same stored mentions as
  before, i.e. the same fine review unit. Then every adjacent pair it forms is a pair that existed before, already checked by the
  chronology guard; no new pair can form between a carried identity and a new name (a new name is unresolved).
- **A new or changed name starts unresolved**, with no candidates and no Latin form; it is never given an identity. The next full
  load runs the normal candidate rules on it (name match for Sunni reports, Imam kunyas) and recomputes the tier; source-index
  claims follow only kept names (replay `origins`), exactly as the Sunni builder moves them.
- Latin names: a kept name keeps its Latin form unless that form came from an identity that is not carried.

## Apply, reversal, reload

**Ids.** `chains_hadith_id_branch_key` and `chain_mentions_chain_id_position_key` are unique over retired rows too, so a fix
cannot insert new rows beside retired ones at the same branch and position. A fix therefore writes the projection's own ids
(`chain:<record>:<branch>`, `mention:<record>:<branch>:<position>`), as every chain builder re-cut already does: upsert by id,
retire by anti-join within the report. The rows as they were are kept whole in `chain_fix_applications.base_rows` (every column,
via `to_jsonb`), so nothing is lost and a revert is exact.

**Apply** (`chain-fix-apply.ts`, draft): under the loader's data-write advisory lock (never during a load or migration). First it
mirrors the store into the five tables. Then per report, one transaction: lock the report; refuse when the Arabic hash differs
(stays queued) or the live chain no longer hashes to the chain the readers were compared with (re-submit) or another fix is in
the database (revert it first); snapshot the live chains, mentions and candidates; write the planned rows, carrying identity by
the rule above; retire what the fix drops; `refresh_publication_facets` for the report; record the application. Then
`refresh_network()` once for the batch, and an application line in `records/chain-fixes/applications/` so `status` shows
`database: applied`. A later human confirmation of an applied fix only changes the status to `verified_by_reviewer`.

**Revert** (`--revert <fix>` or `--revert-rejected`, which reads `queue.json`): restores `base_rows` column by column, retires what
the fix added, refreshes facets, records `reverted` (with the rows before the revert, so it can be undone). Nothing is deleted at
any step; every store file is append-only except the derived `state.json`, `queue.json` and the overrides, which are recomputed.

**Reload.** Chains are pipeline-owned and rebuilt on every load, so the applied fix lives where the projection replays it, like a
curated decision: `accepted_overrides.jsonl.gz`, one row per report, bound to `arabic_sha256` and `reader_text_sha256`. In
`export_postgres.py`, after every chain builder and before the structure gate, for each override (`replay.py`):
1. `binding_problem`: if the Arabic or the reader text changed, drop the row, count it (`chain_fixes.dropped:<reason>`) and leave
   the store to re-queue it (the next decide marks the old submissions `stale` once a reader reads the new text);
2. `replace_routes`: `replay_branches` gives branches in the exporter's own shape with the planned ids and surfaces and
   `origins` from the stored branch each kept name came from, so the K6 source-index claim and an edition identification follow
   the name; the exporter then runs every identity, chronology and Latin-name rule on them as on any chain;
3. the structure gate is not run on these branches: their status is the override's (`read_by_model` or `verified_by_reviewer`),
   and `chains.chain_fix_id` is the fix;
4. `set_status`/`annotate`: the rule-built branches stay; only the status (for `set_status`) and `chain_fix_id` are set;
5. external claims keyed by a stored mention id are moved with `mention_id_map` (kept names) or dropped and counted (others),
   because the external-identity check refuses a claim whose surface differs at its mention id.
Because apply and replay write the same ids and surfaces, the next load changes only what the projection's own rules add
(candidates for new names, Latin forms); it never undoes a fix. A rejected fix leaves the overrides at once, so the next load
restores the rule-built chain even if the revert was not run.

## Schema draft (`src/db/ops/pending/chain-fixes.pending.sql`, `chain-fixes-schema.ts`)

| Table | Key columns | Class |
| --- | --- | --- |
| `chain_fixes` | `id` (`chain-fix:<24 hex>`), `hadith_id`, `arabic_sha256`, `reader_text_sha256`, `text_layout`, `routes_key`, `fix_kinds`, `planned` | immutable |
| `chain_fix_submissions` | `id`, `fix_id`, `view`, `reading`, `base_chain_sha256`, `reason`, `evidence`, `computed_evidence`, `external_citation`, specialist, prompt path/version/SHA-256, `model_id`, `provider_runtime`, `orchestrator_run_id`, packet path/SHA-256/item, UTC times | immutable |
| `chain_fix_decisions` | `fix_id`, `state`, `effect`, `structure_status`, `runs`, `text_only_runs`, `dissenting_runs`, `models`, `why`, `decided_at`, `supersedes_decision_id`; curation bookkeeping; partial unique on live `fix_id` and on live `hadith_id` with an effect | curation (retired rows are the transitions) |
| `chain_fix_reviews` | `fix_id`, `reviewer_kind`, `reviewer`, `model_id`/`prompt_path`/`prompt_sha256` (AI only, check), `decision`, `superseded_by_fix_id`, `note`, `citation`, `reviewed_at` | append-only, one row per review |
| `chain_fix_applications` | `fix_id`, `hadith_id`, `action` (`applied`/`reverted`), `effect`, `base_rows`, `written_ids`, `dataset_version_id` | append-only |
| `chains` | `chain_fix_id` (FK), `structure_status` widened with `read_by_model`, `verified_by_reviewer` (no reasons, a fix named) | pipeline |
| `public_chain_fix_labels` (view) | per public chain: fix, state, models, runs, `decided_at`, `awaiting_final_review`, `human_confirmations` (each reviewer, date, note, citation) | |

Every FK `on delete restrict` with an explicit name; checks hold the rules the code applies (citation shape, evidence present, AI
review names its model and prompt, "verified" only for `confirmed`, agreement counts). One writer for all five tables:
`chain-fix-apply.ts`. The structure status values stay text, not an enum, as in 0017.

## Invariants (`src/db/ops/pending/chain-fixes.verify-data.sql`)

1. A live chain that names a fix reads the report's current Arabic (`chain_fixes.arabic_sha256 = hadiths.arabic_sha256`).
2. A live chain names a fix only while that fix's live decision has an effect.
3. A chain read by model (`read_by_model`, `verified_by_reviewer`) has exactly one fix across its report, whose latest application
   is `applied` and whose decision is not `rejected`.
4. The chain's status is the one its live decision gives.
5. `verified_by_reviewer` only with a named human whose latest review confirms and no human whose latest review rejects.
6. No reviewer row without a named reviewer, a note and a date; an AI review names its model and prompt (checks).
7. A rejected fix is not left applied (reported until the revert runs with the review sync).
8. An accepted changed reading has two runs, one blind, in the submission rows (not only in the counts).
9. In a rewritten chain, an identity always has its carried candidate (a new name never invents one).
10. A model-read, unverified chain forms no teacher-student pair.

## Integration status (2026-11-22)

All twelve steps below are done (migrations `0019_chain_fixes_compiler`, `0020_chain_fix_reader_v3_view`; projection `2026.11.22.12`),
with these changes from the draft, by owner decision: an agreed reading is applied as "read by model, awaiting final review"; a
`held` state (reader holds, `chain-reader/context/HOLDS.md`, `v3/HOLDS.md`) never auto-applies; model-read chains feed lists only where
`chain_fix_work_settings` allows (off for every work); readers' other findings are a file store of proposals for people; the submit tool
takes v1, v2 and v3 readings (any registered prompt; view `text_and_context`). No reading has been submitted or applied: the
overrides file is absent and every production chain has `chain_fix_id` null. Rationale: `src/db/AGENTS.md` §Chain fixes,
`reviews/ai/AGENTS.md` §Chain fixes.

**First application (2026-11-22, batch 001; `conductor/RUNBOOK.md` "First model-read fixes applied (batch 001)").** Migration
`0021_chain_fix_dispositions`: "no chain by reading" (`chain_fixes.disposition`, the page reads `public_chain_fix_dispositions`),
the reader tool version beside the prompt (`chain_fix_submissions.tool_version`), inherited readings (`inherited_from`; inherited names
are rows repeating the earlier report's written mention, held unless that chain is rule-checked), the source named in the text labelled
(`public_chain_fix_mention_kinds`). The projection replay now rewrites rows by the apply's own rule instead of re-running identity
rules on replayed branches (`datasets/hadith-data/chain-fixes/AGENTS.md` §replay), so apply and replay write the same rows.

**Variant remarks and the compiler mark per route (2026-11-22, no migration).** A reader group marked `variant: true` (a remark that another
version names another transmitter, «بمثل حديث X») is stored with the fix as `planned.variant_remarks` (the union of both passes, each marked
with the pass that wrote it), shown under the chain ("The report mentions another version: ...") and counted as no route, mention, pair or
agreement input; the submit tool's `--variant-notes-supported` lifts the `has_variant_group` hold. A fix's later routes carry their own
compiler `direct`/`indirect` mark from their opening words (`planned.chains[].compiler_link`, replay computes it for older plans).
Detail: `datasets/hadith-data/chain-fixes/AGENTS.md`, `reviews/ai/AGENTS.md`.

## Integration checklist (for the next schema owner, in order)

1. **Promote the schema.** Move the five tables and the view from `src/db/ops/pending/chain-fixes-schema.ts` into
   `src/db/schema/isnad.ts` (fix the import paths); add `chainFixId: text('chain_fix_id')` to `chains` with
   `restrictForeignKey('chains_chain_fix_id_fk', table.chainFixId, chainFixes.id)` and the widened
   `chains_structure_status_check` (body in the pending SQL); export from `src/db/schema/index.ts`. Reason: one migration stream.
2. **Migration.** `npx drizzle-kit generate --custom --name=chain_fixes` (next number after the last in `drizzle/core`), paste
   `chain-fixes.pending.sql` as the body, then check `drizzle-kit generate` reports no changes (fold its snapshot in if not, per
   `src/db/AGENTS.md` §Migrations). Append to the same migration: `public_chain_links` recreated with the latest body plus
   `c.chain_fix_id AS chain_fix_id` at the end (CREATE OR REPLACE appends).
3. **`src/db/verify.ts`.** Expected tables + 5, views + 1 (`public_chain_fix_labels`); check `chains_structure_status_check` names
   the two new values and `public_chain_links` ends with `chain_fix_id`. Reason: `db:verify` is the catalog gate.
4. **`src/db/load/verify-data.ts`.** Port the ten checks of `chain-fixes.verify-data.sql`, each as one named check (7 reported,
   not fatal). Reason: the load gate.
5. **`narrator_transmissions`.** Recreate it (with its two indexes) from the current body with the structure guard changed from
   `c.structure_status IS DISTINCT FROM 'uncertain'` to `(c.structure_status IS NULL OR c.structure_status IN ('checked_by_rule',
   'verified_by_reviewer'))`. Reason: a model-read chain awaiting review forms no pair until the agreed-reading error rate is
   measured and the owner rules; a human-verified one does. `db:verify` checks the new predicate.
6. **Loader** (`src/db/load/tables.ts`): `chains` gains the CSV column `chain_fix_id` (content, not derived). The five chain-fix
   tables are curation-class: not in the load contract, never touched by the loader, and (like correspondence decisions) they do
   not block a load. `dump-catalog.ts` then classifies `chain_fix_id` as `csv`.
7. **Projection** (`datasets/hadith-data/pg_export/export_postgres.py`): after the Sunni builder (the `sunni_chain_builder` block)
   and before the structure gate, replay `datasets/hadith-data/chain-fixes/accepted_overrides.jsonl.gz` with `replay.py`
   (`load_overrides`, `binding_problem`, `replay_branches`, `mention_id_map`) as §Reload describes: skip `chain_structure.assess`
   for replayed branches and write the override's status; write `chain_fix_id` for every chain of an override; move or drop
   external claims through `mention_id_map` before the unused-claims refusal; bind the overrides file and `replay.py` in the
   manifest by SHA-256 and count `counts.chain_fixes` (replaced, status set, annotated, dropped by reason, mentions kept/new).
   Add the `chains` column to the header. Document in `pg_export/AGENTS.md` §Chain fixes.
8. **Run the apply once by hand** on development after the load, then production:
   `npx tsx src/db/ops/pending/chain-fix-apply.ts --database production --confirm-production --dry-run`, then without
   `--dry-run`. Move `chain-fix-apply.ts` to `src/db/ops/` and add `npm run db:chain-fixes`. Its test: the loader flow-test
   pattern (`load_test_<hex>` schema with a real slice), apply then revert one report, asserting the rows equal `base_rows` after
   the revert.
9. **Chain page** (`src/app/hadith/[id]/components/chain-structure.ts` and the chain view): read `public_chain_fix_labels`; under a
   `read_by_model` chain: "Read by model (<models>), <decided_at date>; awaiting final review", linked to the fix; under
   `verified_by_reviewer`: "Verified by <reviewer>, <date>" with the note and citation; an `annotate` row: "A model reader read
   the same routes (<model>, <date>)". Never the word "verified" for anything else.
10. **`/method` and the registry.** Add `CHAIN_READER_SPECIALIST` (exported from `reviews/ai/tools/chain-fix-lib.ts`) to
    `SPECIALISTS` in `src/lib/review/procedures.ts`, adding `'chain_structure'` to `CLAIM_KINDS` in `src/lib/review/claim-key.ts`
    (key grammar `chain_structure|hadith:<id>`, field `text`); run `npx tsx reviews/ai/tools/build-specialist-registry.ts` (it
    already reads chain-reader runs from `records/chain-fixes/submissions/`). On `/method`, a `chain-fix-agreement` procedure entry:
    the rule above, the measured agreed-reading error rate per work once the pilot is run, and the failure mode (shared mistakes).
11. **Docs.** `src/db/AGENTS.md`: a §Chain fixes section (migration number, the tables, the id-reuse decision, the network guard)
    and the migration in §Migrations; `conductor/RUNBOOK.md`: the operator sequence (decide, apply, review, `--revert-rejected`).
12. **Model registry.** `datasets/hadith-data/model_registry.json`: the reader model(s) with work `chain reading (chain-fix
    submissions)` and output status `ai_reviewed, awaiting final review`; `render_model_docs.py`.

## Choices that differ from the brief

- **States.** `accepted` replaces `agreed` + `applied`, and the database write is a separate `database` field (§States).
- **Ids are reused, prior rows are kept in `base_rows`**, not retired beside new rows: the two unique keys over retired rows make
  retire-and-insert at the same branch and position impossible without relaxing them, and the loader itself rewrites re-cut
  chains in place. Revert is still exact and nothing is deleted.
- **A fifth table and an immutable `chain_fixes` entity**: reviews, decisions, submissions and `chains.chain_fix_id` all need one
  key for "this reading of this text"; `chain_fix_applications` holds the rows a revert needs.
- **No `non_name_removed` kind**: whether removed words were a name is a judgement; the tool reports `link_removed` and the
  reader's reason and quotes say why. `surface_changed` covers a trimmed or extended name (stored «زرارة بن أوفى يحدث», read
  «زرارة بن أوفى»).
- **Agreement compares what is applied** (spans and link kinds), not the reader's notes, `matn_start` or shared-tail declaration.
- **A 2-against-1 majority settles a dispute** (the brief queued disputes for "a third reader or a human"; the third reader can
  only settle it if a majority counts).
- **Model-read chains feed no teacher-student pair** until measured (integration step 5); the brief left this open.
- **Offsets are repaired** before validation when only the count is wrong (the prompt itself says the surface is the primary
  answer); the record says so.
- **The reader prompt is referenced in place**, not copied: `promptInfo` now accepts its `reader:` front-matter key, and every
  submission records the hash it ran under and is refused if the file has changed since.
