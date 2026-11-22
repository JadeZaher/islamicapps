---
type: pilot
---
# Chain reader v3: tool, prompt, packet builder and the first corpus batch

The second pilot's judge (`../analysis-v2/README.md`) left a work list; this directory does it. No model was run, nothing was written to the database, nothing outside `v3/` was edited (`context/`, `analysis*/`, `pilot/`, `outputs/` are imported read-only).
Design reasons: `AGENTS.md`; holds: `HOLDS.md`; the run: `batch-001/RUN.md`. Tests: section 8.

## 1. What changed from v2, and why

| change | judge's finding | where |
|---|---|---|
| Surfaces found after a spelling fold (ى/ي/ی, ک, hamza carriers, kunya case, a space after «و», tatweel, diacritics), returned in the text's own characters; a stray `occurrence` is ignored; the text is matched **as written first**, folded second | 27 of 28 invalid outputs were spelling (5b, section 1) | `expand_v3.py` |
| `canonical()` folds attached «و», trailing epithet and nisba («…الشجاعي الكاتب»), «بهذا الحديث» | 11 of the 30 disagreements were scope noise (5b) | `norm_v3.link_key`, `expand_v3.canonical` |
| Compiler alias check (first written link, spellings per work, Musnad Zayd = Abu Khalid al-Wasiti) | cr-0183, cr-0197 wrote the compiler twice (4.3) | `work_profiles_v3.json`, `expand_v3.compiler_written` |
| The same man written twice in succession is one link | cr-0144, 0085 (5a) | `norm_v3.same_man`, `expand_v3.collapse_repeats` |
| Hold `drops_stored_name` **removed** | fired on 23 agreed readings, 20 right; it queues exactly the corrections (5a) | `holds_v3.py` |
| Hold `routes_end_at_different_links` | cr-0133, 0157 (shared tail dropped); 4 of 30 disagreements (5a, 5b, 6) | `holds_v3.py` |
| Hold `back_reference_only` | cr-0008, 0193 (inherited chain not taken) (4.1) | `holds_v3.py` |
| Hold `second_isnad_not_same_saying`, **poem cue only** | cr-0136 (5a) | `holds_v3.py` |
| `needs_ruling` holds only when BOTH readers set it; one reader's flag goes to a review sample | flags caught 3 of 13 wrong; either costs 13 right per 2 wrong, both 4 per 1 (4.4) | `holds_v3.ruling_flag_state`, `triage_v3.py` |
| Prompt v3: (a) tail after the last «ح» belongs to every branch; (b) last link = whose words are relayed, place/scene/commentator are not links; (c) second isnad only for the same saying, `variant` group; (d) walk back to the previous report with names, inherited names MUST be taken; (e) same man once; (f) `needs_ruling` not for the Imam asked or answering, a title, a variant; (g) an unnamed «من» the text then names | 6 wording items of section 6, cr-0133, 0157, 0177, 0264, 0136, 0147, 0220, 0205, 0008, 0193, 0144, 0202 | `prompt-v3.md` (27,328 characters; v2: 29,837) |
| Previous report found in **book order** and walked back (12), every intermediate carried, named chain not elided, own size cap | six reports "arrived with no previous report and no flag"; cr-0151, 0008, 0193 (4.1) | `backref_lib.cjs`, `build_context_v3.cjs` |
| Output: a group may carry `"variant": true` | cr-0205, 0280 (5b) | `expand_v3.py` |

**The back-reference finding that corrects the work list.** The six missed reports (cr-0019, 0084, 0121, 0143, 0164, 0168) and cr-0151 were all *detected* by v2's opening test; I ran it on them (`tests/test_tool_v3.py::BackReferenceDetection`). The lookup
failed: `hadith_no_int` and the printed number repeat inside a Thaqalayn section (23 reports of cr-0019's section share `hadith_no_int` 21), so "a report with a lower number" found nothing, and a chapter's first report has no earlier one in its chapter.
The order that works is the provider file plus the numeric provider id. With the v3 builder (a smoke build of the pilot's reports against production, 2026-11-22T16:09Z) cr-0019, 0084, 0121, 0143, 0164, 0151, 0008 and 0193 each get a previous report that writes its chain (cr-0151 after two «وبهذا الإسناد» intermediates, cr-0008 after two); cr-0168 (al-Amali al-Mufid, a run of «وبالإسناد الأول» thirty reports long) gets none within 12 and is held. Detection was still widened («وعنه», «بإسناده», «بالإسناد الأول», «بنفس الإسناد», «بالسند», leading «ح», «وعن»), and «بهذا الإسناد» inside the first 160 letters is now a *closing* back reference, not an opening.

## 2. Re-score of the second pilot's outputs under the v3 tool (no new model run)

Same 279 reports, same outputs of both passes, the judge's verdicts (`../analysis-v2/agreed_set.tsv`). `rescore_v3.py` recomputes the v2 column from the v2 modules and **asserts it equals the judge's table (223 agreed, 174 applied, 167 right)** before it computes anything else. Right = right + representation-only + label-wrong;
the 4 abstentions are out of the rates.

| tool | valid A / B | both valid | agreed | tool holds leave | flag rule | applied (yield) | right among applied | wrong or undecided applied |
|---|---|---|---|---|---|---|---|---|
| **v2** (the pilot as judged) | 266 / 264 | 260 | 223 = 80% (75-84) | 189 | either | 174 = 62% | **167/174 = 96% (92-98)** | cr-0027, 0133, 0136, 0157, 0177, 0183, 0193 |
| v2 tool, flag rule alone | | | | | both | 184 = 66% | 176/184 = 96% (92-98) | |
| v3 fold and canonical only (v2 holds) | 277 / 277 | 275 | **247 = 89% (84-92)** | 205 | either | 189 = 68% | 183/189 = 97% (93-99) | |
| v3 fold and canonical only (v2 holds) | | | | | both | 201 = 72% | 194/201 = 97% (93-98) | |
| **v3 tool** (fold + new holds) | 277 / 277 | 275 | 247 = 89% | 219 | either | 200 = 72% | 197/200 = 98% (96-99) | |
| **v3 tool, flag rule both** (the v3 rule) | 277 / 277 | 275 | 247 = 89% | 219 | both | **213 = 76% (71-81)** | **210/213 = 99% (96-100)** | cr-0027 (undecided), 0033, 0177 |

Before holds: v2 206/219 = 94% (90-96); v3 231/241 = 96% (93-98) (2 held reports unjudged). Invalid outputs: 28 (20 surface, 5 occurrence, 3 order) fall to 4 (cr-0070 B: a marker «(ي‍)» inside a name; cr-0141 A: a name completed beyond the text; two `order`).

What bought what: the fold takes agreement from 223 to 247 (24 newly agreed reports: 22 right, 2 held and unjudged: cr-0168, 0227); the new holds take 4 wrong readings out of the applied set (cr-0133, 0136, 0157, 0193) and one tool fix turns two wrong into right (cr-0183, 0197;
cr-0144 is merged into one link); the both-flag rule adds 13 applied readings (213 against 200) at no wrong one. **Any right reading lost? Yes, 3 of the 174 v2-applied:** cr-0043 and cr-0279 (al-Faqih «وعن X», representation-only) and cr-0224 (al-Kafi «عنه», right), all by
`back_reference_without_previous_report`: the pilot's v2 packets hold three previous reports and the names stand further back. cr-0224 gets its names in v3 packets (the census below); the two al-Faqih «وعن X» stay held by design (an owner call, `AGENTS.md` deferred).
**One wrong reading is newly applied: cr-0033** (the reader restates «الزهري > حميد» as a third route), which `drops_stored_name` used to hold and nothing else does.

Honest limits. (1) The judge's verdicts are the same person's as the work list, and the holds were tuned on this pilot (two refinements to `routes_end_at_different_links`: same-prefix routes count once, a later group after the saying is not compared; and `back_reference_only` skips a closing «بهذا الإسناد»;
before them: 8 hits, 5 right; after: 4 hits, 1 right, 3 wrong), so 99% is an in-sample figure; the fresh batch measures it. (2) Nine of the 24 newly agreed reports had no verdict; I read them (`extra_verdicts.tsv`, all right: cr-0002, 0068, 0082, 0085, 0128, 0139, 0176, 0178, 0200),
which is not the judge. Judge-only: 202/205 judged = 99% (96-100), with the 8 unjudged applied readings counted wrong 202/213 = 95% (91-97), counted right 210/213. (3) cr-0151's verdict comes from the disagreement sample (a representation difference), not from a reading of its inherited chain.

**Holds, hits on the agreed readings (right / wrong / abstention or unjudged).** v2's `drops_stored_name`: 23 hits, 20 right, 3 wrong (removed). v3: `routes_end_at_different_links` 4 (1 / 3 / 0: cr-0133, 0143, 0157 wrong, cr-0180 right);
`back_reference_only` 4 (1 / 2 / 1: cr-0008, 0193 wrong); `second_isnad_not_same_saying` 1 (0 / 1: cr-0136); `back_reference_without_previous_report` 15 (9 / 1 / 5; v2: 6); `needs_ruling` by both: held cr-0139, 0144, 0202 (the judge's "both" rule, 4 right per wrong).
Table-driven tests pin the named cases (cr-0133, 0157, 0193, 0008, 0183, 0197, 0136, 0177, 0264, 0147, 0202, plus 0144, 0200, 0044, 0075, 0091, 0194 as controls) in `tests/test_tool_v3.py`; cr-0177, 0264 B and 0033 are `KNOWN_MISS` rows: the tool cannot see them.

## 3. Back-reference openings across the corpus (99,447 live reports)

"Opens" = the text starts with a back reference (v3's test). v2 counted any report with «بهذا الإسناد» in its first 160 letters (733 Muslim chains that close with it, 819 in all) as well, so its detector fires on 3,479 and v3's on 2,662.
"Previous report with names" = a supplied previous report that itself writes a chain: v2's lookup (chapter pool, printed number, three reports) against v3's (book order, walk back at most 12).

| work | reports | v2 detector | **opens (v3)** | pronoun / isnad phrase / bare «عن» | with names: v2 | **v3** | none found |
|---|---:|---:|---:|---|---:|---:|---:|
| al-Kafi | 14,245 | 1,041 | 1,040 | 849 / 186 / 5 | 147 | **1,040** | 0 |
| Uyun akhbar al-Rida | 954 | 328 | 328 | 0 / 328 / 0 | 37 | 78 | 250 |
| Thawab al-amal | 1,106 | 214 | 213 | 1 / 211 / 1 | 0 | 187 | 26 |
| Sahifat al-Rida | 205 | 204 | 204 | 0 / 204 / 0 | 0 | 0 | 204 (parent report) |
| Kitab al-Mumin | 201 | 196 | 196 | 6 / 0 / 190 | 0 | 0 | 196 |
| Sunni: al-Shafi'i | 2,054 | 138 | 138 | 0 / 0 / 138 | 0 | 0 | 138 (no chain in source) |
| Kitab al-Ghayba (Tusi) | 774 | 116 | 114 | 72 / 41 / 1 | 77 | 111 | 3 |
| Kamil al-ziyarat | 750 | 80 | 79 | 48 / 29 / 2 | 0 | 79 | 0 |
| al-Amali (Saduq) | 1,082 | 54 | 52 | 0 / 52 / 0 | 47 | 52 | 0 |
| al-Amali (Mufid) | 387 | 49 | 48 | 0 / 48 / 0 | 0 | 14 | 34 |
| Kamal al-din | 659 | 47 | 46 | 0 / 46 / 0 | 25 | 46 | 0 |
| al-Tawhid | 575 | 34 | 34 | 0 / 34 / 0 | 32 | 34 | 0 |
| Maani al-akhbar | 829 | 34 | 33 | 0 / 33 / 0 | 0 | 33 | 0 |
| al-Ghayba (Numani) | 468 | 24 | 20 | 0 / 7 / 13 | 19 | 20 | 0 |
| al-Faqih | 6,382 | 8 | 7 | 0 / 0 / 7 | 1 | 6 | 1 |
| Sunni: Bukhari | 7,370 | 29 | 29 | 0 / 1 / 28 | 29 | 29 | 0 |
| Sunni: Ahmad | 23,529 | 27 | 24 | 0 / 20 / 4 | 0 | 3 | 21 (chain field) |
| Sunni: Tirmidhi / Muslim / Abu Dawud | 4,214 / 7,596 / 5,260 | 57 / 734 / 9 | 10 / 1 / 1 | | 9 / 1 / 1 | 10 / 1 / 1 | 0 |
| Fadail, Sifat, Zuhd, Mujam, Rabi', Darimi, Muwatta, Nahj (8 works) | 8,558 | 45 | 45 | | 7 | 40 | 5 |
| **all 34 works** | 99,447 | 3,479 | **2,662** | 978 / 1,278 / 406 | 432 | **1,784** | 878 |

Ibn Majah, Nasa'i, al-Khisal, Duafa, Huquq and Musnad Zayd have none. Full per-work table: `census_backref.json` (`census_backref.cjs`, re-runnable). Of the 878 without names, 559 are works where the chain is elsewhere by design (Sahifat 204, Mumin 196, Shafi'i 138, Ahmad's chain field 21);
the real gaps are Uyun (250 openings sit in runs of «وبهذا الإسناد» longer than 12), Mufid (34: «وبالإسناد الأول» runs), Thawab (26); 9 are scattered. The limit 12 was chosen from the curve: 6 gives 1,711, 12 gives 1,784, 20 gives 1,840.
al-Faqih's «وعن X» openings (406 bare «عن» in the corpus) are counted as back references and, with no chain to inherit, are held; whether they should be is the owner's call.

## 4. Batch 001 (a measured fresh sample, nothing run)

Drawn uniformly at random (seed 20261122, `draw.json`) from the **13,843 live reports with at least one `structure_status = 'uncertain'` chain** (dataset version `6df54aa3…`, read 2026-11-22T16:06Z), after removing the 380 of them that appear in any earlier sample
(2,188 distinct reports: every `chain-audit/**/sample_check.csv` and `verdicts.tsv`, the pilot's `reports.jsonl`, the prompt examples). 25 packets of 20, `batch-001/packets/` (1,602,153 bytes; context median 1,722 characters, p95 2,844, max 3,075; manifest with ids, work counts, coverage, bytes, UTC time and sha256 of sample, profiles, builder and sidecars).

| stratum | drawn | pool after exclusion | composition |
|---|---:|---:|---|
| Sunni six books | 250 | 7,612 | Muslim 90, Bukhari 42, Abu Dawud 41, Nasa'i 38, Tirmidhi 20, Ibn Majah 19 (largest remainder of the live uncertain counts) |
| al-Faqih | 150 | 748 | |
| other Imami, not al-Kafi | 100 | 1,588 | Kamil al-ziyarat 12, al-Amali (Saduq) 11, Uyun 10, Kamal al-din 10, Maani 10, al-Khisal 15, al-Amali (Mufid) 6, Tusi 6, Thawab 6, Numani 5, Tawhid 3, Mujam 3, Fadail 1, Mumin 1, Zuhd 1 |

Context coverage of the 500: source claims 448, archive flags 493, name facts 173, correspondences 156, `sources_agree` 162; previous reports 5 (5 reports open with a back reference; 2 got a previous report that writes a chain, 3 did not, none flagged `needs_previous_report`); omitted for size: name facts 104, correspondences 20, flags 7.
Ids are opaque (`b1-` + 6 hex of a salted hash; no hadith id or work key in the id), packet order is shuffled across works, the map is `private/id_map.json` with `private/sample.json`, `private/reports.jsonl` (the hidden half for the submit tool) and `private/population.jsonl`.
Reader instruction text, directory layout for two passes and the commands (validate, expand, holds, hand-over): `batch-001/RUN.md`. `to_submission.py` is exercised on the pilot's outputs in `tests/test_flow_v3.py` (submitted readings pass the submit tool's own v1 validator).

## 5. Sizing a full run over the uncertain population (`sizing_v3.py`, `sizing_v3.json`)

| | |
|---|---|
| reports | 13,843 (Sunni six books 7,830, other Sunni 2,529, al-Kafi 1,024, al-Faqih 771, other Imami 1,644, Ibadi and Zaydi 45) |
| packets of 20 | **693** |
| reader agent runs, two packets (40 reports) per agent | **347 per pass, 694 for two passes** (batch 001: 13 per pass, 26 for both) |
| characters read per pass | report text 7.13 M, context 30.46 M (measured per group in batch 001; al-Kafi, other Sunni, Ibadi and Zaydi estimated from the nearest sampled group), prompt 27,328 x 347 = 9.48 M; **47.1 M** |
| two passes | **94.1 M characters, about 31 to 38 M tokens** (2.5 to 3 characters per token for diacritised Arabic) |
| packet bytes (UTF-8) | about 44 M for all packets |

The context is 4 to 5 times the text: the cap (3,000 characters) and `--no-archive-flags` are the levers; the text-and-metadata checker pass is not included (v3 is the chain reader only).

## 6. Not built, and why

- `second_isnad_not_same_saying` detects a poem cue only (انشد، شعر، قصيد، بيت ...); an anecdote or a remark about versions (cr-0147's remark, cr-0220's story) has no tell cheap enough. Trigger: batch 001 shows misses.
- No hold for a speaker omitted from the last link (cr-0177) or a place of hearing read as a link (cr-0264 B): reading errors, only the prompt can reduce them.
- A marker inside a name and a name completed beyond the text stay invalid (two outputs).
- The text-and-metadata checker, its packets and the reconciling reader are not rebuilt; `--no-archive-flags` for pass B (the v2 ablation) is not applied.
- The fix pipeline cannot take these readings yet: its submit tool pins the v1 prompt hash and the views `text_only` / `text_and_stored_chain`, and refuses chains that repeat earlier names; `to_submission.py` writes the envelope it will take once those change (`AGENTS.md` section submission). I did not touch it.
- Readings with inherited links are not submitted (the pipeline's rule); they stay in `triage/readings/`.

## 7. Files

`prompt-v3.md` / `prompt-v3.json` (hash, build checks) / `tools/make_prompt_v3.py` / `tools/chain_body_v3.md`; `norm_v3.py`, `expand_v3.py`, `holds_v3.py`, `validate_v3.py`, `work_profiles_v3.json`; `backref_lib.cjs`, `build_context_v3.cjs`, `census_backref.cjs` / `.json`;
`draw_population.cjs`, `draw_batch.py`, `triage_v3.py`, `to_submission.py`, `sizing_v3.py` / `.json`; `rescore_v3.py` / `.json`, `extra_verdicts.tsv`; `tests/`; `batch-001/` (`RUN.md`, `draw.json`, `packets/`, `private/`).

## 8. Tests (from `datasets/hadith-data/chain-reader/`)

```
python -B -X utf8 -m unittest discover -s v3/tests -p "test_*.py"      # 24 tests: tool on real pilot cases, holds, detection, validation, converter, draw
node --test v3/tests/test_backref_lib.cjs v3/tests/test_build_context_v3.cjs   # 6 tests: JS detection equals Python's, walk-back, order key, budget rules
python -B -X utf8 v3/tools/make_prompt_v3.py                           # rebuilds the prompt: 7 examples, 21 quoted fragments, 8 full pilot readings, length <= v2
python -B -X utf8 v3/rescore_v3.py                                     # asserts the v2 baseline (223 / 174 / 167) then prints the table above
```
