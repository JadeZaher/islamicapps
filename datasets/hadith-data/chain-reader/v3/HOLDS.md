---
type: reference
---
# v3 holds: why a reading is queued, not applied

`holds_v3.compute_holds(reading, output, text, context, stored_surfaces, other_output)` returns `[{"code", "detail"}]`. A hold never changes or discards a reading; the decide step queues the report with its codes.
Agreement is `expand_v3.canonical()` equality (link keys: spelling folded, attached «و», trailing epithet and nisba, «بهذا الحديث» dropped). Hits below are on the second pilot's 247 reports agreed under v3
(`rescore_v3.json`), right = right + representation-only; **they were tuned on this pilot (two refinements, below) and must be judged again on batch 001**.

| code | fires when | pilot hits (right / wrong / not judged) | note |
|---|---|---|---|
| ~~`drops_stored_name`~~ | removed | v2: 23 agreed hits, 20 right, 3 wrong (cr-0033, 0197, 0202) | it queued corrections (19 of the 20 right hits sit in labelled-defective chains); the judge's finding 5a. cr-0197 is now a tool fix, cr-0202 is caught by both flags; **cr-0033 is applied again and is wrong** |
| `routes_end_at_different_links` | the routes of one report, not counting `variant` groups and a later group that begins more than 60 letters after the first isnad, end at different last links (a trailing «بهذا الإسناد» is not counted) | 4: 1 / 3 / 0 (cr-0133, 0143, 0157 wrong; cr-0180 right) | routes that share everything but the last link are one level of alternatives and count once («عن أبي جعفر وأبي عبد الله», «\|» routes, two Imams named). Before that refinement: 8 hits, 5 right, 3 wrong |
| `back_reference_only` | every link of every route is a back reference; or the text OPENS with a back reference (not «بهذا الإسناد» later in the chain), a previous report with a written chain was supplied, and no route has an `inherited` link | 4: 1 / 2 / 1 (cr-0008, 0193 wrong; cr-0151 is right only by the disagreement sample's representation verdict) | a Sunni chain with its own names that closes with «بهذا الإسناد» is not held (cr-0091, 0254) |
| `second_isnad_not_same_saying` | a later group begins after the saying (more than 60 letters after the first isnad) and the 70 letters before it hold a poem or story cue (انشد، شعر، قصيد، بيت، ابيات، الراجز، حكي) | 1: 0 / 1 / 0 (cr-0136) | cue words only; **an anecdote or a remark about versions without such a word is not detected** (cr-0147's remark, cr-0220's story): not built beyond the poem |
| `back_reference_without_previous_report` | the text opens with a back reference (or says «بهذا الإسناد» in its first 160 letters) and no previous report with `has_written_chain` was supplied | 15: 9 / 1 / 5 abstentions | v2 held 6. Nine more fire on the second pilot only because its packets are v2's (three reports back, no walk-back); batch packets walk back up to 12 |
| `cannot_read_without_previous_report` | the reader answered that status | 4 abstentions | by design |
| `needs_ruling` | **both** readers set `needs_ruling` | not an agreed-set hit in the table above (cr-0139, 0144, 0202 are held by it) | one reader's flag goes to the review sample (`triage_v3.py`: `review_sample.txt`), not to a hold: the judge's finding 4.4 (either 13 right lost per 2 wrong; both 4 per 1) |
| `too_many_routes` | more than 8 routes after expansion | 0 | the tool refuses above 400 |
| `nested_jami`, `nested_semicolon` | two or more «جميعا» / «؛» in the chain region | 1 right (cr-0210), both | unchanged |
| `reading_empty_stored_has_links` | the reading has no link and the stored chain has | 8: 4 / 0 / 4 abstentions | unchanged; needs `--reports` |

Not built: a second-isnad marker after the matn when the reading has one group (the deferred hold of v2; v3 asks the reader for second isnads in rule 4 and measures first); detection of an anecdote or version
remark as a second isnad (needs a tell other than a cue word); detection of a speaker omitted from the last link (cr-0177) or a place of hearing taken as a link (cr-0264 B), which are reading errors the tool cannot see.

Flag state: `holds_v3.ruling_flag_state(a, b)` returns `both`, `a_only`, `b_only` or `None`.
