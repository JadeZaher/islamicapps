# v3_2/: design notes

Operating instructions and numbers: `README.md`; holds: `HOLDS.md`; folds: `FOLDS.md`; the run: `../tranches/RUN.md` (names the v3.1 modules; `README.md` section 7 has the v3.2 equivalents). Code carries one-line docs and points here. Nothing in this directory runs a model or writes a database.
`v3/`, `v3_1/`, `analysis-*/`, `context/`, `pilot/`, `outputs/` and `tranches/` are read-only from here; module names are distinct (`expand_v3_2`, `holds_v3_2`, `validate_v3_2`, `norm_v3_2`, `triage_v3_2`, `to_submission_v3_2`) so v3.1 and v3.2 import side by side. Python writes use `newline="\n"`.
The packet builder (`../v3_1/backref_lib_v3_1.cjs`, `build_context_v3_1.cjs`) is NOT copied: the packets of every tranche are unchanged, and the new opener is Python-only (below).

## variant
A `variant: true` group is a remark that another version names a different transmitter («بمثل حديث سليمان بن بلال», «أرسله ابن عون», «وقد روى شيبان ... مثل هذا»). It is not a route of this saying, so it never enters `routes`, never takes part in agreement, and is never stored as a chain (v3.1 stored it: 3 of tranche 01's 7 wrong readings).
`expand` keeps it in `variant_remarks` (`surfaces`, and the sentence of the remark: from the last full stop or line break before its first name to the next one after its last, at most 160 letters each way). `matn_start` is computed from the real routes only, so a remark after the saying no longer pushes the chain region into the matn.
Two guards: `has_variant_group` holds a reading with a remark until the pipeline carries notes (the flag lifts it, in `triage` only, so the summary still counts it); `variant_only_reading` holds a reading with no real route, which would otherwise look like an empty reading ("no chain") and be applied as one, and the flag does not lift it.
The two passes may disagree about whether a group is a variant (one writes a route, the other a remark): the non-variant routes then differ and the report is not agreed (5 reports of tranche 01).

## folds
`link_key` folds a patron («X مولى Y»), a title («أم / أمير المؤمنين» + a name), a companion after a kunya and «امرأة أبيه»; `readings_agree` pairs routes that differ in ONE slot by a restated short form («X» for «X بن Y»). Each is bounded by what the 11 equivalent readings of the judge's 40 show, with negative tests; the list is `FOLDS.md`.
Bracketed insertions «[ ... ]» are links (the judge: the pass that writes them is right) that `canonical()` leaves out so that the two passes compare; a reading whose passes wrote them differently is agreed but held (`bracketed_insertion_differs`), never applied, because the applied reading is pass A's and may lack the link.
Not folded on purpose: anything that could make two different men equal without a same-slot neighbour check.

## holds
The three shape holds copy the judge's own definitions (`proposed_holds.py`: `h_short_route`, `h_kunya_pair`, `h_semicolon_in_chain`) with two changes: the comma hold reads the gap between the two first links by offsets (only whitespace and a comma) instead of a 12-letter regex, and the semicolon hold reads the original text up to `matn_start` (the judge sliced the diacritic-stripped text with an offset of the original). Their hit counts equal the judge's on tranche 01 (2, 1, 1).
`inherited_from_far_report` measures the gap by report NUMBERS (the packet's previous reports are the nearest report that writes its chain or names its speaker, not the nearest report: b36519's `prev1` is five reports back), falling back to the ref's index only when a number is missing.
`imami_single_narrator_without_source` exempts an Imam by name (laqab, or the kunyas of `IMAM_KUNYAS`) and every other link kind (`inherited`, `imam_in_text`, `unnamed`, `back_reference`, `relation`): they are what the v3.1 rulings produce on purpose.
The Prophet rule is applied to EMPTY readings only, from the opening of the text (`PROPHET_OPENING`), and not to a scene where he merely appears («فقصتها حفصة على النبي ...»): the unruled case is the Prophet as the speaker of a report with no transmitter. It is a work-independent hold (the judge found cf634a applied in a Maani al-Akhbar group while the same shape in al-Faqih was held by the readers' flags).
«و مع قوله عليه السلام» is `QUOTED_SAYING`: an implicit-speaker opener for the empty-reading hold only. It is not in `INHERITING`, because the packet builder does not give it a previous report (it would only add `back_reference_without_previous_report` to a report the builder cannot help).

## validity
A missing `fixes` key is `[]` (`with_default_fixes`, applied in `validate_chain` and in `triage`, so the stored `reader_output_v3` carries it). Every other shape rule is unchanged.

## submission
`to_submission_v3_2.py` is v3.1's with: `--reader-prompt v3|v3_1|v3_2` (the prompt the outputs were read under; `run.tool_version` is `v3_2`), `--variant-notes-supported`, the variant remark carried as `fixes[].variant_remarks` and a line in `output.notes`, `agreement` naming `readings_agree`. The pipeline owner's side (`reviews/ai/`) is untouched; an envelope with a variant remark is only produced once the flag is passed.

## prompt
`tools/chain_body_v3_2.md` (v3.1's body, three one-line additions) + v1's tradition conventions + examples, built by `tools/make_prompt_v3_2.py`, which fails the build when an example does not validate against its text, a quoted fragment is not in its pilot report, a pilot reading does not expand as its rule says, or the prompt is longer than v3.1's (27,173 letters). `tools/build_example_packets_v3_2.py` builds `examples/example-packets.jsonl` (v3.1's four batch-001 packets plus four tranche-01 reports shortened at a stated phrase).
It is a draft: no model has run it and nothing is applied under it.

## deferred
- The tranche-02 draw and the out-of-sample figures for every v3.2 hold: trigger, tranche 02 read and triaged.
- Narrowing `imami_single_narrator_without_source` and `semicolon_in_multi_route_isnad` (each caught right readings of batch 001): trigger, tranche 02's hits.
- Trimming the epithet from the applied surface: trigger, the first tranche applied with v3.2.
- The 0706da class (the one asked answers) has only the prompt example.

## triage
`triage_v3_2.triage` is v3.1's with: outputs normalised by `with_default_fixes`; agreement by `readings_agree`; the extra code `bracketed_insertion_differs`; `--variant-notes-supported` removing `has_variant_group` (listed in `suppressed`); a `variant_group` flag and `variant_remarks_agree` per report (the remarks are compared separately and never block agreement); `triage.tsv` gains a `variant_group` column, `summary.json` the variant counts.
