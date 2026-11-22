---
type: reference
---
# v3.3 apply lists, for the fix-pipeline owner

Ids are the opaque ids of the tranches (`t01-xxxxxx`, `t02-xxxxxx`) and batch 001 (`b1-xxxxxx`). Nothing here was applied, submitted or written to a database. Judges' verdicts are one model's, not blind; an unjudged reading in a list is eligible by the tool only.

## Tranche 01 and tranche 02: `eligible_v3_3.txt` and `withheld_by_judge.txt`

| tranche | read under | eligible under v3.3 | **apply list `eligible_v3_3.txt`** | of them "no chain" (`no_chain.txt`) | withheld by the judge (`withheld_by_judge.txt`) |
|---|---|---|---|---|---|
| 01 `tranches/tranche-01/triage-v3_3/` | prompt v3.1, tool v3.3 | 733 = 720 chain + 13 no chain | **730** = 717 chain + 13 no chain | 13 | **3**: 0706da W, 6d7565 W, a20cb6 CT |
| 02 `tranches/tranche-02/triage-v3_3/` | prompt v3.2, tool v3.3 | 700 = 689 chain + 11 no chain | **695** = 684 chain + 11 no chain | 11 | **5**: 553df1 W, 0dfb7f CT, 3cacbd CT, fe8248 CT, fecbb4 CT |

`eligible_v3_3.txt` = the triage's eligible readings (both passes valid, equal routes, status read, no v3.3 hold) minus every reading a judge marked wrong (W) or cannot-tell (CT). `withheld_by_judge.txt` lines: `id`, `wrong|cannot tell`, where the verdict is from, `chain|no_chain`. The triage's own full list is `eligible.txt` beside them (v3.3 triage, nothing withheld); the no-chain subset of the apply list is `no_chain.txt` (all 13 and 11 are in the apply lists: the judge read all 11 of tranche 02 as right).
Why each is withheld: 0706da the one asked who answers is dropped (no cue a regex can use); 6d7565 a short route's head dropped (**eligible only because v3.3 narrowed `route_at_most_half_the_longest`**: v3.2 held it); a20cb6, 0dfb7f, 3cacbd, fe8248 narrated encounters or a first-person «سألته» with the Imam a pronoun (the owner's questions); fecbb4 a second saying with its own transmitter; 553df1 a restated name written as two links.
Coverage: the judge read 201 of tranche 01's eligible readings and 244 of tranche 02's (a random sample, plus its hold and scan reads), so about 440 and 450 readings of the lists are unjudged; their expected right-rate is the weighted figure of `README.md` section 2 (98.1% on the judged v3.3 readings of each tranche, lower bound 94.2% and 95.4%).
`released_vs_v3_2.txt` lists the readings eligible under v3.3 and not under v3.2 (tranche 02: 1552aa R, 5505a6 R, 89130e R; tranche 01: 479600 unjudged, 6d7565 W): **the fix engine recomputes holds with the tool named in the envelope**; with `tool_version` `v3_2` it holds these again, with `v3_3` it needs registering first (`README.md` section 7).
Held by v3.3 and not in the lists, pending the owner: the al-Faqih route statements (`faqih_route_statements.tsv`: tranche 02 6 eligible under v3.2, tranche 01 2), every `has_variant_group` reading (77 and 49), and the `needs_ruling` ones.

## Batch 001: against the 348 applied and the 46 held (`v3_3/batch-001/`)

Mapping: the fix store's queue (`reviews/ai/records/chain-fixes/queue.json`, 348 `awaiting_final_review`, 46 `held`) through the stored submissions' reading ids.

**v3.3 would hold 12 of the 348 applied** (`would_hold_of_applied.tsv`), all by `needs_ruling_faqih_route_statement` (al-Faqih «و ما كان فيه عن X فقد رويته عن ...»): `b1-170d33`, `b1-1bea49`, `b1-26d360`, `b1-297cae`, `b1-520cad`, `b1-60b019`, `b1-703a20`, `b1-928814`, `b1-a05d58`, `b1-a735be`, `b1-d752cd`, `b1-fffeb4`. Eleven were judged right by the first judge (d752cd was not judged), so this is an owner decision about a class, not a defect found: if the owner rules the statements are isnads, nothing changes; if not, these 12 come off. mutaba'a, route-ends-inside and the narrowed holds hit none of the 348.

**v3.3 would release, tool side, 2 of the 46 held** (`would_release_of_held.tsv`, column `tool_side_holds_in_queue` against `v3_3_eligible`): `b1-2c5437` and `b1-cb35a4` (held by `route_at_most_half_the_longest`; the narrowing frees them). **Both look wrong** (the v3.2 README read them as the 6d7565 class: the second route drops its shared head, «قال دلهم وحدثنيه أيضا الأسود», «قال وأخبرني ابن طاوس»); not judged. Do not release them on the strength of v3.3. The other tool-held readings stay held under v3.3: variant (244c94, ca3dad, ef706c, 88802d), semicolon (0c320a, 3fe523, 9f0528; now also faqih statements), Prophet "no chain" (a2dfb1, b8346e, dadc56), single narrator (a6d33f, dbf175, also `stored_chain_checked_by_rule`), bb2042 (half-route, last links differ).
The other 31 of the 46 are held by pipeline codes only (`stored_chain_checked_by_rule` 27, `cited_by_later_report` 2 + 1 with the former, `inherited_source_chain_uncertain` 1); v3.3 does not touch them (`would_release_of_held.tsv`, column `pipeline_holds_that_remain`). So 15 of the 46 are tool-held (4 variant, 3 half-route, 3 semicolon, 3 Prophet, 2 single narrator): 2 released, 13 stay.
