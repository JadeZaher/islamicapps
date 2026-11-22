# chain-fixes: model readings of chains, replayed by the projection

Design, states, the auto-apply rule and the integration checklist: `docs/review/chain-fix-pipeline.md`. Tools that write here:
`reviews/ai/tools/chain-fix-decide.ts` and `chain-fix-review.ts` (never by hand).

| File | What |
| --- | --- |
| `chain_fix_engine.py` | Every Arabic rule of the pipeline: the reader's validator, the comparison with the stored chain, the planned rows. Called once per CLI invocation over stdin/stdout JSON |
| `replay.py` | What the projection imports to replay accepted fixes (binding check, `rewrite_rows`: the apply's rule over the rule-built rows) |
| `accepted_overrides.jsonl.gz` | Derived: one row per report whose chain the projection takes from an accepted or confirmed fix. Absent means none |
| `test_chain_fix_engine.py` | Engine and replay on real pilot reports: `python -I datasets/hadith-data/chain-fixes/test_chain_fix_engine.py` |

## engine

- **Reuse, not copy.** `validate.validate` and `validate.repair_offsets`, `norm.fold_loose` and `score.ISNAD_PHRASE` come from
  `../chain-reader/` (imported, never modified); `name_normalize` and `_strip_arabic_marks` from `../extract_isnad_unified.py`, the
  projection's own forms, so a planned `surface_normalized` is what the exporter would write. `review_unit_ids` repeats the
  exporter's three-line formula (`pg_export/export_postgres.py`), checked against a live production row on 2026-11-22.
- **Repair before refusing.** A reader cannot count characters; when the strict validation fails and the repaired one passes, the
  repaired reading is used and flagged. Errors returned are always the reader's own, never the repair's.
- **Comparison key**: `fold_loose(name_normalize(surface))` after the extractor's trailing «ع» is dropped. Both sides get the same
  form, so «أبي سعيد، الخدري» equals a stored «أبي سعيد الخدري» and «وأحمد» equals «أحمد». «بهذا الإسناد» is dropped from the
  reading (stored chains never carry it) and marks the route `suspension = back_reference`.
- **Alignment**: each read route takes the stored branch sharing its longest common run of names (LCS; ties to the earlier
  branch), and names are matched in sequence inside it. Two read routes may take the same stored branch (a split keeps both
  halves' evidence). A stored name is `removed` only when no read route keeps it; an unmatched stored name whose folded words
  contain the read name, or lie inside it, is `surface_changed` (a trim or an extension), not a removal plus an addition.
- **Carry rule**: `carry_identity` is true only when the name and both its neighbours are the stored ones (same fine review unit).
  Rationale in the design note §Identities: every pair a carried identity forms existed before and passed the chronology guard.
- **Rows**: ids in the projection's scheme (`chain:<record>:<branch>`, `mention:<record>:<branch>:<position>`), routes in text
  order so the branch numbering does not depend on the order a reader wrote them; a kept name keeps the stored `surface_ar`
  (identical normalization and review units), a new name is the text span with marks stripped as the extractor strips them.
  `link_kind_if_new`: narrator and relation `unclassified`, unnamed `anonymous`, back-reference `not_a_narrator`.
- **Evidence coverage** is required only for a reader who saw the stored chain (it knows what it changes); a blind reader cannot,
  so its changes are evidenced by `computed_evidence` (the exact text of each added or changed link), labelled as computed.

## replay

- The override is bound to `arabic_sha256` (what every projection binding uses) and `reader_text_sha256` (what the offsets count
  in; Ahmad, al-Darimi, al-Muwatta read the chain field, a blank line, then `text_ar`). A broken binding drops the row and counts
  it; the store re-queues the fix when the new text is read.
- **Replay equals the apply (2026-11-22).** A replaced report keeps its rule-built branches through the whole projection (so the K6
  alignment, external claims and kunya carriers of every other report are what they were), and `rewrite_rows` then swaps its chain,
  mention and candidate rows for the fix's by `chain-fix-apply.ts` `writeRoutes`' own rule, column for column: planned ids, surfaces,
  contexts and review units; a carried name its identity and Latin form; a kept name its candidates and a Latin form not taken from
  an identity; a new name unresolved with none; an inherited name its cited mention's candidates; each chain the report's first
  rule-built chain's sanad confidence and compiler (`indirect` when the route relies elsewhere). Production rows are the last load's
  rule-built rows, so the database apply and a later export write the same rows and a load changes nothing (proved on batch 001:
  `conductor/RUNBOOK.md` "First model-read fixes applied"). The first form (re-running the identity rules on replayed branches)
  could never equal the apply. Change one side only with the other.
- A rejected fix leaves this file in the same call that records the rejection, so the next load restores the rule-built chain
  even before the database revert runs.

## reader formats (0019/0020/0021)

`run_item` takes `reader_format` `v1` (routes with offsets), `v2` (`context/expand.py`, `validate_v2.py`, `holds.py`), `v3` / `v3_1`
(the output is `reader_output_v3`) or `text` (proposals only). A v3-shaped reading is validated, expanded and held by the tool
`tool_version` names (`TOOLS`: `v3` or `v3_1`; a v3.1 reading only by `v3_1`). The format follows from the prompt the reader ran, the
tool from the envelope: batch 001 was read under prompt v3 and re-triaged by tool v3.1, and the submission stores both. v2/v3 readings
are turned into the v1 shape for comparison (`v1_from_v2`): derived links are dropped from the routes and returned in `derived_links`
with kind and origin. Every format returns `holds` and `proposals` (the reader's other findings).

- **No chain by reading**: an agreed reading with no route returns `disposition: no_chain_by_reading` and plans no chain; applying it
  retires the stored chain (`chain_fixes.disposition`, view `public_chain_fix_dispositions`). The submit tool takes it only in a
  `shura-chain-no-chain-envelope/1` and refuses an empty reading anywhere else.
- **Source named in the text** (`imam_in_text`: the Imam asked or speaking, read as the last link): a written mention whose planned
  `reader_kind` stays `imam_in_text` (`mark_named_in_text`), so the page labels it (view `public_chain_fix_mention_kinds`). The compiler
  head is never a mention (the projection derives it).
- **Variant groups** (`variant: true`: «بمثل حديث X», «زاد في حديث Y»: another version's transmitter, never a route) are not yet
  handled by `to_submission_v3_1.py` or the planned rows, which would write them as ordinary chains (tranche-01 judge, confirmed on
  batch 001: 4 of the 394 readings). Until a variant is kept as a labelled remark and agreement is computed on the other routes, a
  reading with any variant group is held (`has_variant_group`; the four batch-001 fixes by archive hold). Tool `v3_2` (`TOOLS`) keeps
  variants out of the routes and returns them as `variant_remarks` (recorded on the submission); its holds still hold the reading
  until the page shows the remark.
- **Inherited links** (`plan_inherited`): each inherited name becomes a mention repeating the cited report's written mention
  (`inherited_from_mention_id` its root, its surface). `resolve_inherited` holds instead of guessing: no earlier report given
  (`inherited_previous_report_unknown`), its chain not rule-checked or verified (`inherited_source_chain_uncertain`), a name not found
  in order in one of its branches (`inherited_name_not_in_source_chain`). Routes that open inherited come first. The v3 hold
  `inherited_links_not_applied` is lifted. Fix kinds are computed on the written links only.
