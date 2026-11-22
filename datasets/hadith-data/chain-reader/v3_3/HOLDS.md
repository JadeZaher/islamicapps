---
type: reference
---
# v3.3 holds: what changed from v3.2 and why

`holds_v3_3.compute_holds(reading, output, text, context, stored_surfaces, other_output)` returns `[{"code", "detail"}]`; `triage_v3_3` unites the two readings' codes. A hold never changes a reading. Every v3.2 hold not named here is unchanged (`../v3_2/HOLDS.md`).
Source of every change: the out-of-sample judgement of tranche 02 (`../tranches/tranche-02/judge-v3_2/analysis/`, README sections 4, 5, 9; `cases.md`; `hold_verdicts.tsv`). **All hit counts for tranche 02 below are IN-SAMPLE (the changes were designed on it); tranche 01 and batch 001 are out of sample for the v3.3 changes.**
Verdicts are the judge's (one model, not blind). R = judged right, W = judged wrong, CT = cannot tell.

| code | fires when | tranche 02 hits on agreed (eligible under v3.2) | judged among hits | tranche 01 hits (eligible v3.2) | batch 001 hits | the judge's finding |
|---|---|---|---|---|---|---|
| **`mutabaa_marker`** (new) | the text carries «تابعه» / «وتابعه» (also «تابعها», «تابعهم», «تابعهما», «وقد تابعه», none of which occurs in the corpus) or «وقد تابع X على» / «وتابع X على», AND the reading has more than one route | 3 (2) | W 2 (1061e3, cf6189); 888bb4 is a variant remark, held by `has_variant_group` too; **R 0** | 0 | 0 | the marked isnad is a remark about another version; both passes wrote it as a route in the two eligible hits |
| **`route_ends_inside_another_route`** (replaces `routes_end_at_different_links`) | a route's last written link stands inside another route of the same report (not at its end), the other route ends at a different link, and the route is not exempt (below) | 5 (1) | W 5 (d02f9f, facedc, 181bd0, b88276, 30b092); **R 0** | 4 (1; none judged) | 2 (0) | a shared tail was dropped from the route |
| `route_at_most_half_the_longest` (narrowed) | v3.2's condition AND the short route's last link differs from the last link of every longest route | 8 (0 new cost) | W 8 (dee88c, 56b32a, 03f4b1, 0aec9d, 80403f, facedc, 181bd0, b88276); **R 0**; released: 1552aa (R) | 5 (v3.2: 6; released 6d7565, **W**) | 4 (v3.2: 6; released 2c5437, cb35a4, both probably wrong) | 1552aa: both routes reach the Companion; see the cost in README section 4 |
| `inherited_from_far_report` (narrowed) | an inherited link from a report more than 3 back, unless every report between is in the packet, writes no chain, names no speaker and opens with a back reference | 0 (v3.2: 1; released 5505a6, R) | R 1 released | 1 (b36519, CT: still held) | 0 | 5505a6 inherits through seven «وبإسناده / وبهذا الإسناد» reports |
| **`needs_ruling_faqih_route_statement`** (new, tag `faqih_route_statement`) | an Imami report that opens «(و) (كل) ما كان فيه / في هذا الكتاب عن X فقد رويته عن ...»: the compiler states his routes to a source, with no saying | 10 (6); 13 tagged | R 8 of the 10, W 2 (0a8f48, 6da700, both also held by the semicolon hold) | 4 (2); 5 tagged | 19 (12); 20 tagged | the owner has not ruled whether this is an isnad of a saying; held with a `needs_ruling` class code until the owner rules |

Replaced and removed: `routes_end_at_different_links` (v3.1, with its exemptions). Its hits: tranche 02 8 on agreed (6 W, 2 R: 89130e, 8b0565), tranche 01 6, batch 001 4.

## route_ends_inside_another_route: definition and exemptions

A route A is checked when its last written link (back reference, compiler head and inherited links aside) has key K and some other route B, whose last link is not K (nor a restated short form of K), has K at a position before its end. «X» counts as K for «X بن Y» (`restated_short_form`: d02f9f «هشام» / «هشام بن عروة»).
Exempt, the exemptions of v3.1's broad hold carried over because they keep tranche 01's four judged-right two-isnad readings eligible (dd8d9b, 0c66ee, 610c03, 31cf87; a test pins it):
- A route that ends in a back reference («عن سهيل، بهذا الإسناد»): it states its tail (8b0565, 479600, 160be9).
- A route of a later isnad written after the saying (more than 60 folded letters after the first isnad's last name): dd8d9b, 0c66ee.
- A route the text abbreviates right after its last name («بمثله», «نحوه»).
Same last link on both routes is no hit (a2c20f: three routes end at «عبد الله», one carries «عبد الله بن مرة»; without that rule the short-form match would hold a2c20f and 01827c in tranche 02, two unjudged readings I read as right).
**Not caught that the judge's rule caught:** 1061e3 and 883658. Both are the second-isnad-after-the-saying shape that dd8d9b also has (judged right), so no rule on this structure separates them; both stay held by other holds (`mutabaa_marker`, `has_variant_group`). The judge counted 6 hits (all W); this hold has 5 (all W).

## route_at_most_half_the_longest: what the narrowing costs

Releasing a short route that ends at the same man as the longest route frees 1552aa (R, tranche 02) and three readings of the same shape that look wrong: **6d7565 (W, judged, tranche 01)**, 2c5437 and cb35a4 (batch 001, not judged; the v3.2 README read them as the 6d7565 class). All four are a short route that starts with a new head and ends where the long routes end; the only separator in the four texts is the «ح» before 1552aa's second route («ح وحدثني أبو عثمان») against «قال وحدثني» / «قال وأخبرني» before the other three (see README section 4). Not built: it is a rule found on four readings.

## Kept, as the judge advised

`has_variant_group` (see "Variant switch"), `semicolon_in_multi_route_isnad` (2 caught, 2 cost, no separating narrowing), `imami_single_narrator_without_source`, `needs_ruling` by both readers, the nested and back-reference holds.

## Variant switch

`has_variant_group` holds every reading with a variant remark. `--variant-notes-supported` no longer releases anything: it records that the pipeline carries the note (`summary.json`: `variant_notes_supported`). Release needs the separate, explicit `--release-variant-readings` (off by default; it requires `--variant-notes-supported`; without it `triage` raises). The judge: with the group removed the reading is right in 27 of 30 (90.0%, 74.4-96.5); 3 of 30 groups were genuine routes or extra links of the same saying.

## Not added (the judge rejected them)

A transmission verb after the matn (11 hits, 4 R read); a single-pass `needs_ruling` flag (25 hits, 8 R read); the restated-name regex «عن X، - قال Y حدثنا Z -» (14 hits, about 12 right); `imami_pronoun_asker_no_imam` (1 hit, CT).
