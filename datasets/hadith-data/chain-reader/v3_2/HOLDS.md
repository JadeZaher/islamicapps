---
type: reference
---
# v3.2 holds: why a reading is queued, not applied

`holds_v3_2.compute_holds(reading, output, text, context, stored_surfaces, other_output)` returns `[{"code", "detail"}]`; `triage_v3_2` unites the two readings' codes, adds `bracketed_insertion_differs`, and drops `has_variant_group` when `--variant-notes-supported` is passed. A hold never changes a reading.
Every v3.1 hold is unchanged (`../v3_1/HOLDS.md`), including `routes_end_at_different_links` **with its exemptions**: the broad pre-v3.1 behaviour is not reinstated (it caught 4 judged-right readings in the read sample: dd8d9b, 0c66ee, 610c03, 31cf87; they stay eligible, a test pins it).

**Every v3.2 hold was designed from tranche 01's judge sample (`../tranches/tranche-01/judge/analysis/`) and is measured on that same sample: the figures below are IN-SAMPLE.** Tranche 02 is the out-of-sample test (README section 7). "Eligible under v3.1" counts the 747 eligible readings of tranche 01 (732 with links, 15 "no chain"); "agreed" counts the 863 readings both passes agree on under v3.2.

## New holds

| code | fires when | tranche 01: hits on agreed / of them eligible under v3.1 | judged caught: wrong / **right** / undecided | batch 001: among the 394 | why (the judge's finding) |
|---|---|---|---|---|---|
| `has_variant_group` | a reading carries a `variant: true` remark (kept in `variant_remarks`, never a route) and the fix pipeline cannot carry notes yet; lifted by `--variant-notes-supported` | 49 / 23 (27 carried one: 4 of those now disagree because one pass wrote the group as a route and the other as a variant) | **3 / 0 / 0** (30fa50, c93705, e3f7d5) | 4: 88802d (judged right), 244c94, ca3dad, ef706c (not judged) | README section 8 of the judge: three of the seven wrong readings are one mechanism, a variant group stored as a chain |
| `variant_only_reading` | every group is a variant remark: nothing is left to store (otherwise the empty route list would read as "no chain") | 0 / 0 | 0 / 0 / 0 | 0 | a guard the new expansion needs; not lifted by the flag |
| `route_at_most_half_the_longest` | two or more routes, the longest with 4 links or more, the shortest at most half as long (the judge's `h_short_route`; compiler head not counted, an inherited link is) | 6 / 2 | **1 / 0 / 0** (6d7565) | 3: 2c5437, bb2042, cb35a4 (not judged; see "Batch 001" in README: all three read like the 6d7565 class) | a shared head or tail dropped from a later route (case 6d7565) |
| `first_links_split_by_comma` | two routes identical except the first link, the two first links adjacent in the text with only a comma between them (no «و») | 1 / 1 | **1 / 0 / 0** (05c2d0) | 0 | a kunya and a name («أبو الطاهر، أحمد بن عمرو بن سرح») read as two men |
| `semicolon_in_multi_route_isnad` | «؛» inside the isnad (the text up to `matn_start`) of a reading with 2 or more routes | 2 / 1 | **1 / 0 / 0** (eb2b15) | 3: 0c320a, 3fe523, 9f0528, **all judged right** | co-transmitters grouped after «؛» lose their shared tail (case eb2b15) |
| `imami_single_narrator_without_source` | an Imami work; one route; one link besides the compiler; that link is a `narrator` that is not an Imam by name (laqab or the five kunyas of `IMAM_KUNYAS`); nothing inherited | 3 / 2 | **0 / 0 / 2** (07d717, f14c39) | 2: a6d33f, dbf175, **both judged right** | «و قال الحلبي: و سألته», «في رواية جميل أنه قال»: the Imam is left out (cases 07d717, f14c39) |
| `inherited_from_far_report` | an `inherited` link whose previous report is more than 3 back: the difference of the two report numbers when both are plain numbers (b36519: 1071 against 1066, though the packet calls it `prev1`), else the ref's index | 1 / 1 | **0 / 0 / 1** (b36519) | 0 | an Imam inherited from five reports back with nothing in the text to confirm it |
| `needs_ruling_prophet_no_transmitter` | an empty reading whose text opens with the Prophet speaking or acting: `PROPHET_OPENING` («وقال صلى الله عليه وآله», «ونهى صلى الله عليه وآله», «وصلى رسول الله», «كما روي عن النبي»); every work alike | 2 / 1 | **0 / 0 / 1** (cf634a) | 3: a2dfb1, b8346e, dadc56, **all judged right as "no chain"** | unruled; the judge found it applied in one group and held in another (case cf634a); now held everywhere |
| `empty_reading_unsettled_opening` (opener added) | v3.1's hold, with «و مع قوله عليه السلام» (`QUOTED_SAYING`: «مع قوله / قول» then an Imam's or the Prophet's blessing) an implicit-speaker opener of an empty reading; it does NOT inherit from the earlier report (no packet change) | 2 / 1 | **0 / 0 / 1** (2973ea) | 0 | case 2973ea |
| `bracketed_insertion_differs` (triage) | the two passes agree only because a link inside «[ ... ]» is left out of `canonical()`, and they wrote it differently | 1 / 0 | 0 / 0 / 0 (54c186 was not eligible) | 0 | the judge: the pass that writes the editor's insertion is the right one in both cases (54c186, dfff83); the tool compares without it and will not apply a reading that depends on it |

Judged caught, all new holds together: 11 readings (4 `W` + the 3 variants + eb2b15 ... ): 6 wrong (30fa50, c93705, e3f7d5, 05c2d0, 6d7565, eb2b15) and 5 undecided (07d717, f14c39, b36519, cf634a, 2973ea); **0 of 190 judged-right readings caught**. Not caught: 0706da (wrong, the one asked answers) and a20cb6 (undecided, a narrated encounter).
**Costs to look at in batch 001** (a second sample, which the holds were not tuned on): 3 `semicolon_in_multi_route_isnad`, 2 `imami_single_narrator_without_source`, 1 variant and the 3 Prophet "no chain" readings, all judged right, would be held: 9 of the 394 (2.3%), none wrong. Two of those holds are broader than the case that taught them; the owner may narrow them (README section 5).

## Why not more

- The Imam exemption of `imami_single_narrator_without_source` (a narrator whose surface is an Imam's laqab or one of the kunyas) matters for 2 of the 15 single-link Imami readings eligible in tranche 01 and batch 001 (5d4df1 «الصادق», 3fe91b «أبي عبد الله»); the others are `inherited` or `imam_in_text`, which the hold never touches.
- `route_at_most_half_the_longest` counts the judge's links (a back reference at the end counts), so its 2 eligible hits in tranche 01 are the judge's 2.
- `0706da` (the asked who answers is dropped) has no cue a regex can use (`قلت لX` hit 12 tranche readings, 1 wrong): the prompt example is its only guard.
- A narrower `imami_single_narrator_without_source` (only when the text after the link has «سألته» or «أنه قال») would spare a6d33f and dbf175 and keep 07d717 and f14c39; it is a one-line change and is left out because the owner asked for the broad form.
