---
type: pilot
---
# Chain reader v3.4: the owner's third-round rulings (encounter, two sayings), the saying label, and the re-read set

Built 2026-11-22. **No model was run, nothing was written to a database, nothing outside `v3_4/` and `reviewer/` was written** (every tranche, triage, judge and earlier tool folder is
untouched; `v3_2/` and `v3_3/` modules are imported, never edited). Design reasons: `AGENTS.md`.

## 1. Prompt v3.4 (`prompt-v3_4.md`, `prompt-v3_4.json`)

sha256 **`b63fd535a8cdbdea9294704a494e110523874f846fb1c9be40d4cf26ea8ba959`**, 26,983 letters (the budget is v3.2's 27,023; the build fails above it). Built by `tools/make_prompt_v3_4.py`
from `tools/chain_body_v3_4.md` and `examples/example-packets.jsonl` (`tools/build_example_packets_v3_4.py`); every example validates against its real text and expands to the stated
routes, remarks and sayings; the 21 pilot fragments and 8 pilot readings of the v3.2 build still check; the 5 fragments the new rules quote stand in their real reports and in the prompt.

| what changed | where in the prompt |
|---|---|
| (a) **Narrated encounter**: the Imam or source who speaks inside the narrator's story is the last link («كنت عند أبي عبد الله عليه السلام في فسطاطه بمنى، فنظر إلى الناس فقال»); counter-example: one only present, addressed or described stays out («… وعنده علي ابنه، فقال: يا علي»: «علي ابنه» is no link) | rule 6 (new paragraph), owner ruling 5, example 4 (t01-a20cb6, shortened) |
| (b) **Two sayings**: both stored, each isnad its own group labelled with its saying | rule 4a, owner ruling 6, example 5 (t01-520f51) |
| **Mutabaʿa**: «تابعه قتيبة حدثنا العنقزي عن حنظلة» is a variant remark, never a second route | rule 4, example 2 (t02-1061e3, the tranche-02 judge's wrong reading) |
| `needs_ruling` narrowed to the still-unruled set: first-person narrative with an unnamed speaker or implicit transmission; the Prophet's one-sentence report with no transmitter; a cited book's author or an Imam's rescript; a source known only by a title; al-Faqih's «طرق» statements; «قضى أمير المؤمنين … في» with no transmitter; «روي عن الأئمة». Encounters, two sayings and «ورواه X عن Y فلم يرفعه» (a variant) are now named as NOT a reason | rule 11 |
| examples replaced, not appended: v3.2's 2 («بمثل حديث سليمان بن بلال»), 4 (kunya, comma, name), 5 (the one asked answers), 6 (al-Faqih «و كتب X إلى Y»), 8 (`groups: []`) dropped; their rules and quotes stay in the text (the tranche-02 judge found all four classes fixed: 15/15, 44/44, census al-Faqih 47/48) | Worked examples |

**The saying label** (output format `shura-chain-reader-output/3.4`): a group may carry
```
{"levels": [...], "saying": 2, "saying_opens": "أنها لم تكن تفعل ذلك"}
```
`saying` numbers the sayings in text order (1 = first); `saying_opens` is the first 3-8 words of that saying copied from the text (the tool accepts 2-12 and locates them like a surface,
fold-tolerant, returning the text's own characters). When any group carries it, every non-variant group does, groups of one saying name the same opening, and `shared_tail` is null
(a later saying writes the names it shares, keeping the head as in example 3). A v3.2 tool rejects a labelled output; an unlabelled v3.4 output is a v3.2 output.

## 2. Tool (`expand_v3_4.py`, `validate_v3_4.py`, `holds_v3_4.py`, `triage_v3_4.py`, `to_submission_v3_4.py`)

**Base.** `v3_3/` exists and has holds, triage and submission but no expansion or validator of its own (it imports v3_2's unchanged). So v3.4 **wraps** rather than copies: expansion and
validation are v3_2's, imported, plus the label layer; holds are v3_3's (`holds_v3_4.BASE == "v3_3"`; v3_2's if v3_3 is absent). Nothing must be re-based now; if a later v3_3 changes
`holds_v3_3.compute_holds`, v3.4 picks it up on import (the tests then show it). Re-base only `expand_v3_4.base` if a newer expansion appears.

| module | v3.4 adds |
|---|---|
| `expand_v3_4` | `saying_shape_errors`, `locate_sayings` (an opening is looked for after its saying's last link, then after its first, then anywhere, with a tool note), routes carry `saying`, remarks carry it when labelled, reading carries `sayings` [{saying, label "Chain of the first saying", opens, start, end, groups}]; `readings_agree` per saying (same saying numbers, v3.2 agreement inside each) |
| `validate_v3_4` | v3.2's validator on the output without labels, plus the label checks |
| `holds_v3_4` | the shape holds (`SHAPE_CODES`: half-route, both tail holds, comma, semicolon, nested «جميعا» / «؛») run **per saying**, every other hold on the whole reading; new `saying_route_starts_inside_another_route` (a later saying's route starting at a man interior to an earlier saying's chain: the head was dropped) and `two_sayings_not_supported` |
| `triage_v3_4` | `--sayings-supported` lifts `two_sayings_not_supported`; `saying_openings_differ` when the passes open a saying at different places; `sayings` column |
| `to_submission_v3_4` | `run.tool_version: v3_4`; a fix with two sayings carries `sayings: [{saying, label, opens, routes: [indices into output.routes]}]` and one note line per saying; `output.routes` stay plain v1 routes; `--reader-prompt v3_4` (default) or `v3_2` |

Effect on the judge's cases (`tests/judge_cases_v3_4.py`, read by hand as the prompt says): t02-023097 unlabelled trips v3.3's `route_ends_inside_another_route` (saying 1 ends at
جابر بن سمرة, who stands inside saying 2's route to «أبي»); labelled, only `two_sayings_not_supported` stands. t02-102af2's second saying runs through يونس only («زاد يونس في روايته»)
and keeps the head to بكير; written headless it is held. The three encounters (8b818b, 1cc0f4, a20cb6) end at the one who speaks and fire no hold.

## 3. The re-read set (`reread-001/`, built by `build_reread_v3_4.py`)

Covered: **batch 001, tranches 01 and 02** (each with a v3.3 triage). Not covered: tranches 03-10 (no triage when built; tranche 03 finished both passes during this build). For them:
`build_reread_v3_4.py --set reread-002 --exclude-set reread-001` once they are triaged.

| | batch 001 | tranche 01 | tranche 02 | **total** |
|---|---|---|---|---|
| reports in the set | 66 | 121 | 115 | **302** |
| `needs_ruling_both` (both readers flagged: agreed and held as needs_ruling, or differing and both flagged) | 13 | 52 | 47 | 112 |
| `flag_one_reader` | 44 | 51 | 45 | 140 |
| `encounter_shape` | 7 | 18 | 18 | 43 |
| `two_sayings_shape` | 5 | 19 | 17 | 41 |
| `judge_cannot_tell` (on these two questions) | 4 | 4 | 6 | 14 |

A report can have several reasons. Only one reason: flag one reader 125, both flagged 86, encounter shape 27, two-sayings shape 20, judge cannot tell 1.
Detection rules (folded text; the docstring of `build_reread_v3_4.py` has them verbatim): **encounter**: «كنت / كنا [جالسا / جلوسا / يوما / قاعدا] عند | مع | بين يدي», «دخلت / دخلنا على»,
«بينا / بينما أنا / نحن», «خرجت / خرجنا مع» in the first 600 letters, not followed by the Prophet within three words (he ends the chain: nothing would change), with «قال / فقال» within 300
letters after. **Two sayings**: after the furthest written link of any valid reading (+20 letters), «و / ف + حدثني / حدثنا / أخبرني / أخبرنا / حدثتني / سمعت» (optionally after «قال X»), unless
«نحوه / مثله / بمثله / بنحوه / بهذا الإسناد / بمعناه / نحو حديث / مثل حديث» follows within 200 letters (another route of the same saying). Their precision is not measured; reading the
47 shape-only hits by eye, many are already right under v3.2 (an asked man who answers, Tirmidhi's own remarks with an isnad): the re-read is the measurement.
The judges' cannot-tell ids: batch 001 b2ad9c, 941f93, dcfca3 (Q4), cb13de (Q5); tranche 01 a20cb6 (CT), 306ccd, 2a5330, 881857 (Q3/Q4 disagreements); tranche 02 3cacbd, fe8248, fecbb4,
c3900f, 3ac3df, f3cf19.

Packets: **16** (15 of 20, one of 2), lines `{"id": "r4-xxxxxx", "text", "context"}` with the source packet's text and context unchanged (a test compares every line with its source).
`jobs.json`: **17 jobs** (pass A 8: 001+002 ...; pass B 9: 001 alone, 002+003 ... 016 alone), the shape of `tranches/tranche-02/jobs-v3_2.json`; with an even packet count pass B has one job more,
stated in two extra keys of `expected` (`jobs_pass_b`, `run_txt_lines_pass_b`). Outputs go to `reread-001/outputs/pass-a|pass-b`. `manifest.json` (counts, packet hashes; no ids);
`private/id_map.json` (salt; opaque id to source, original id, source packet) and `private/reasons.tsv` (every reason and cue per report). Triage of the re-read: run `triage_v3_4.py` with
`--packets reread-001/packets` (the id map turns the result back into tranche ids).

## 4. Which prompt for which tranche

| tranche | state on 2026-11-22 | prompt |
|---|---|---|
| batch 001, 01 | read (v3, v3.1) | stay; their encounter / two-sayings reports are in `reread-001` |
| 02, 03 | read under v3.2 (03 finished both passes during this build) | stay v3.2; 02 in `reread-001`, 03 in `reread-002` after its triage |
| 04, 05, 06 | assigned to running reader workers (no output on disk when checked) | stay v3.2 if any job of the tranche has started; a tranche with no output at all when the owner decides may switch |
| **07, 08, 09, 10** | not started | **switch to v3.4**: `python -B -X utf8 v3_4/make_jobs_v3_4.py --tranche 07` (… 10) writes `tranches/tranche-NN/jobs-v3_4.json` (not written by me; it refuses a tranche with outputs unless `--force`) |

Readings of v3.4 jobs are triaged and submitted with the v3.4 modules only (`triage_v3_4.py`, `to_submission_v3_4.py --reader-prompt v3_4`). Note: tranches 04-10 have only `jobs.json` on disk,
which names prompt **v3.1**; `make_jobs_v3_4.py` converts from it (any prompt path `v3_N/prompt-v3_N.md`).

## 5. Tests (from `chain-reader/`)

```
python -B -X utf8 -m unittest discover -s v3_4/tests -p "test_*.py"      # 17 tests
python -B -X utf8 v3_4/tools/build_example_packets_v3_4.py && python -B -X utf8 v3_4/tools/make_prompt_v3_4.py
python -B -X utf8 v3_4/build_reread_v3_4.py --check
```
Flows covered: the judge's two-sayings cases (023097, 102af2, and 520f51) validate, label and expand; per-saying shape holds (023097 with and without labels); a dropped head across sayings
(102af2) is held; eight label errors (table); agreement needs the same sayings; triage holds then (with the flag) releases a labelled reading and the envelope carries `sayings` with route
indices; openings at different places held; the three encounters end at the speaker with no hold and Uthman stays out of 8b818b; the mutabaʿa is a remark; 100 real v3.2 outputs validate
identically under v3.2 and v3.4; prompt hash, budget and rules; example texts are prefixes of their reports; the jobs conversion changes only the prompt fields; every re-read line equals
its source packet's text and context and the jobs cover every report once per pass.

## 6. Not built / deferred

- The fix pipeline's side of the label (the engine re-expands `reader_output_v3` with the tool version, so `chain_fix_engine.py` must know `v3_4` and store `sayings`; the page must show
  "Chain of the first saying / second saying"): the integrator's, listed in `../reviewer/INTEGRATION.md` §6. Until then every two-saying reading is held (`two_sayings_not_supported`).
- No model has run prompt v3.4; no re-read was run; `jobs-v3_4.json` files were not written.
- The re-read set does not yet include tranches 03-06 (no triage at build time).
- Precision of the two shape detectors is unmeasured (the re-read measures it).
