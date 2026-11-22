# v3_3/: design notes

Operating instructions and numbers: `README.md`; holds: `HOLDS.md`; lists for the fix pipeline: `APPLY_LISTS.md`. Code carries one-line docs and points here. Nothing here runs a model or writes a database.
`v3_2/` and earlier, `tranches/*/outputs`, judge folders, `reviews/ai/` and `chain-fixes/` are read-only from here. v3.3 changes only holds, triage and submission: `expand_v3_2`, `validate_v3_2`, `norm_v3_2` and the v3.2 prompt files are imported from `v3_2/` (a `sys.path` entry), so there is no second copy to drift. Module names are distinct (`holds_v3_3`, `triage_v3_3`, `to_submission_v3_3`) so v3.2 and v3.3 import side by side. Python writes use `newline="\n"`.

## holds
- Every change answers a judged case of tranche 02 (`HOLDS.md`). A hold is kept narrow enough that no judged-right reading of the judge's sample is caught, except the al-Faqih route statements, which are held on purpose until the owner rules (the judge counted them right under the standing ruling).
- `route_ends_inside_another_route` keeps v3.1's three exemptions (a route ending in a back reference, a later isnad written after the saying, an abbreviated route) because without them it holds tranche 01's four judged-right two-isnad readings (dd8d9b, 0c66ee, 610c03, 31cf87). The price is two readings the judge's plain rule caught (1061e3, 883658), both held by other holds.
- «X» matches «X بن Y» (restated short form) only when the two routes do NOT end at that same name: otherwise every shared Companion written «عبد الله» in one route and «عبد الله بن مرة» in another would fire (a2c20f).
- The far-inheritance narrowing needs EVERY report between the two numbers to be in the packet and to be a pass-through (no written chain, no speaker, opens with a back reference). An unknown report is not a pass-through: b36519's reports #1067-#1070 are not in its packet, so it stays held. In 5505a6's packet every report #215-#221 is listed (all «وبإسناده / وبهذا الإسناد»); in b36519's #1067-#1070 are not, so the rule cannot tell what stood between.
- The faqih statement is matched on the folded opening of the text (`FAQIH_ROUTE_STATEMENT`, Imami works only) and is independent of the reading: it also tags (`tags` in `triage.tsv`) reports that are not agreed.
- Patterns run on the folded text (`fold_v3`: alif maqsura becomes ya, hamza carriers fold), so write «علي», not «على», in a pattern.

## variant switch
v3.2's `--variant-notes-supported` lifted `has_variant_group` in the triage. The judge showed the lift is wrong by default (90% right, 3 of 30 groups were genuine routes), so in v3.3 the flag only records that the pipeline carries notes, and the release is the separate `--release-variant-readings` (needs the first flag; `triage()` raises otherwise). The fix engine has its own flag with the same name (`chain_fix_engine.py` line 517): outside this folder, see `README.md` section 7.

## submission
`to_submission_v3_3.py` imports the envelope helpers from `to_submission_v3_2` and differs in the triage it calls, the release flag, `run.tool_version: "v3_3"` and the agreement string. The prompt files are v3_2's (the prompt did not change).

## evaluate
`evaluate_v3_3.py` reads the three v3.3 triages and the judges' verdicts; "right" is R or RO, undecided counts as not right; weighted intervals are Wilson on the effective n (`v3_2/eval_lib_v3_2.py`). Sample status is stated per figure: tranche 02 is in-sample for the v3.3 changes, tranche 01 and batch 001 are out of sample for them (tranche 01 is in-sample for the v3.2 holds). The batch lists map the fix store's fix ids to reading ids through the stored submissions.

## deferred
- A «ح»-before-the-short-route rule for `route_at_most_half_the_longest` (would keep 6d7565, 2c5437, cb35a4 held and release 1552aa; four readings): trigger, the owner's word or another released case.
- `imami_pronoun_asker_no_imam` (1 hit): not asked.
- The engine registration of `v3_3` and an engine-side release flag: `chain-fixes/` is the pipeline owner's.
- A judge draw from the v3.3 eligible set: the draw script reads `triage-v3_2`, and drawing from the v3.2-eligible set is what lets the judge test the new holds out of sample.

## pipeline correction (owner, 2026-11-22)
The fix pipeline runs v3.3 with `route_at_most_half_the_longest` taken back to v3.2's un-narrowed rule (`holds_v3_3_pipeline.py`, a patch module beside the tool, not an edit of `holds_v3_3.py`): the narrowing released 6d7565 (judged wrong) and 2c5437, cb35a4 (read as its class); 1552aa (right) is held again. Test: `tests/test_pipeline_correction.py`. The «ح» rule of §deferred would release 1552aa without the other three.
