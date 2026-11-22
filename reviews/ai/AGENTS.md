# reviews/ai — rationale for the specialist review tools

Formats and the isolation protocol: `README.md`. This file holds the why that code comments point to.

## Chain fixes

Design, states, rules and the integration checklist: `docs/review/chain-fix-pipeline.md`; Arabic rules:
`datasets/hadith-data/chain-fixes/AGENTS.md`. Agent instructions: `prompts/chain-fix-submission.md`.

- **The reader is a specialist whose prompt is not in `prompts/`.** `datasets/hadith-data/chain-reader/prompt.md` is referenced in
  place and hashed on every submission; a copy would be a second document to keep identical. `promptInfo` therefore accepts the
  `reader:` front-matter key as well as `specialist:`. `CHAIN_READER_SPECIALIST` (in `tools/chain-fix-lib.ts`) is the registry
  entry, waiting for `src/lib/review/procedures.ts`; `build-specialist-registry.ts` already reads its runs from
  `records/chain-fixes/submissions/`.
- **Store layout** (`records/chain-fixes/`): `submissions/<run id>.jsonl` (one file per reader run), `reviews/<kind>-<reviewer>.jsonl`,
  `applications/<date>.jsonl` (written by the database apply), `transitions.jsonl` (one line per state change); derived and
  recomputed: `state.json`, `queue.json`. Append-only files are never edited; nothing is deleted.
- **Concurrency**: one file per run plus an exclusive lock file per append (`withLock`); a duplicate line from a race is harmless
  because every reader keys by `submission_id`. `decide` and `review` recompute under `store.lock` and rename derived files into
  place.
- **Why the CLIs call Python**: the comparison and the planned rows must equal what the projection writes; one implementation
  (the engine) serves the CLIs, the database apply and the replay.
- **Flow test**: `npx tsx reviews/ai/tools/__tests__/chain-fix.test.ts` (private store in a temporary directory, real pilot reports).
- **Reader formats and prompts (0019/0020).** The format follows from the prompt hash the run names: every prompt in
  `READER_PROMPTS` (v1 `chain-reader/prompt.md`, v2 `context/prompt-v2.md`, v3 `v3/prompt-v3.md`, the text checker) is registered
  and hashed as it stands; any other hash is refused. v2 and v3 outputs are expanded and validated by the reader toolchain
  (`context/expand.py` + `validate_v2.py`; `v3/expand_v3.py` + `validate_v3.py`), through the engine, never re-implemented here.
- **Views.** `text_only`, `text_and_context` (v3: the text and the sources' context, never the stored chain) and
  `text_and_stored_chain`. The first two are blind for the agreement rule (`isBlindView`). A blind packet may carry `context`
  only when it holds no stored chain.
- **v3 envelopes** (`chain-reader/v3/to_submission.py`): `fixes[].reader_output_v3` is the reader's unchanged output and is what the
  engine reads; `run.second_reader` is recorded as a second submission of the same fix (`agreement_basis: canonical_equal_v3`: the
  triage found both passes canonical-equal), so the decide rule sees two independent runs.
- **Derived links** (compiler head, a name inherited from an earlier report, an Imam named in the text) are not substrings of the
  report: the v3 validator checks an inherited name against the previous report's text in the packet and the head against the
  work profile. They are stored on the submission (`derived_links`: kind, origin, span) for the page; planned rows hold only
  written links (the projection derives the compiler head itself). A reading that takes inherited names is held
  (`inherited_links_not_applied`): writing an inherited mention needs the earlier report's written mention.
- **Holds** (`held` state, codes on the fix and in `chain_fix_decisions.hold_codes`): v1/v2 readings use `context/holds.py`, v3 readings
  `v3/holds_v3.py` (no `drops_stored_name`; `needs_ruling` only when both readers set it, which the v3 triage already applies before
  an envelope is written). A held reading is never applied, whatever the agreement; it waits for a third reader or a person.
- **Proposals.** Readers' findings beyond the chain (`fixes`, `text_check`, `metadata_check`) are filed in
  `records/chain-fixes/proposals/<run>.jsonl` with both readings and their sources, the evidence and the reader's provenance;
  `chain-fix-review --proposal` records a person's decision (`proposal-reviews/`); `chain-fix-status --proposals` lists them. No tool
  applies one; there is no table for them yet (file store only this round).
