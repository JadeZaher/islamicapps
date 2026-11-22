# chain-fixes: model readings of chains, replayed by the projection

Design, states, the auto-apply rule and the integration checklist: `docs/review/chain-fix-pipeline.md`. Tools that write here:
`reviews/ai/tools/chain-fix-decide.ts` and `chain-fix-review.ts` (never by hand).

| File | What |
| --- | --- |
| `chain_fix_engine.py` | Every Arabic rule of the pipeline: the reader's validator, the comparison with the stored chain, the planned rows. Called once per CLI invocation over stdin/stdout JSON |
| `replay.py` | What the projection imports to replay accepted fixes (binding check, branches in the exporter's shape, mention-id map for external claims) |
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
- `origins` carry each kept name's origin from the branch it came from, so the K6 source-index claim and an edition
  identification follow it (the Sunni builder's mechanism); a new name has none.
- A rejected fix leaves this file in the same call that records the rejection, so the next load restores the rule-built chain
  even before the database revert runs.

## reader formats (0019/0020)

`run_item` takes `reader_format` `v1` (routes with offsets), `v2` (`context/expand.py`, `validate_v2.py`, `holds.py`), `v3`
(`v3/expand_v3.py`, `validate_v3.py`, `holds_v3.py`; the output is `reader_output_v3`) or `text` (proposals only). v2/v3 readings are
turned into the v1 shape for comparison (`v1_from_v2`): derived links (compiler head, inherited names) are dropped from the routes and
returned in `derived_links` with kind and origin; an Imam named in the text stays a written link. Every format returns `holds` and
`proposals` (the reader's other findings). A v3 reading that takes inherited names gets the hold `inherited_links_not_applied`.
