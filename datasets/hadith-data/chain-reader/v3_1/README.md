---
type: pilot
---
# Chain reader v3.1: prompt, tool, packet builder and the tranches of the full run

Version 3.1 encodes the owner's rulings of 2026-11-22 (after the judge read batch 001: `../analysis-batch-001/`) and prepares the full run. No model was run, nothing was written to a database, nothing outside `v3_1/` and `tranches/` was edited (`v3/`, `analysis-*/`, `context/` are imported read-only).
Design reasons: `AGENTS.md`; holds: `HOLDS.md`; the numbers: `batch-001/RETRIAGE.md`; the run: `../tranches/RUN.md`.

## 1. What changed from v3

| | change | where |
|---|---|---|
| Prompt | **3.1.0**, sha256 `fca49673fea34c55531f3764b7cae1c3cdeaf890b8d0cf5c7dd90c2e132860fd`, 27,173 letters (v3: 27,328). Rule 5: the asker is a link, one rule for «سأل / سئل / كتب / شكا», the pronoun case; Previous reports: «وقال عليه السلام», an asker with a pronoun and a bare «وعن X» take the Imam or the chain from the earlier report (`supplies: chain / speaker`); rule 10: «و روي: «أن ...»» is `[]` ("no isnad"); rule 11: `needs_ruling` for the eight unruled cases and no others. Examples: real batch-001 reports 4cbe02, 05f29e, 38f586, 2c405e (v3's 2, 6, 7 dropped for length) | `tools/chain_body_v3_1.md`, `tools/make_prompt_v3_1.py`, `prompt-v3_1.md`, `prompt-v3_1.json` |
| Packets | the walk-back also serves Imami asker-with-pronoun, «وقال عليه السلام» and bare «وعن» openings and stops at a report that writes its chain or names its speaker; the private reports file lists each previous report's hadith id | `backref_lib_v3_1.cjs`, `build_context_v3_1.cjs` |
| Tool | folds: a joined name («بنجعفر»), «للرضا», case-ending alif, dual nisba, an Imam's laqab, a closing «في هذا الإسناد» | `norm_v3_1.py`, `expand_v3_1.py` |
| Holds | empty readings applicable as "no chain by reading" unless a transmission word and a name stand before the saying or the text opens as an asker / inherited speaker; `asker_not_a_link`; `routes_end_at_different_links` exempts an abbreviated route and independent isnads; widened back-reference openings | `holds_v3_1.py`, `HOLDS.md` |
| Triage / submission | `applies: chain \| no_chain`; inherited readings submitted with the previous report's id; a `no_chain` envelope | `triage_v3_1.py`, `to_submission_v3_1.py` |
| Full run | 10 tranches of 49 packets, jobs per tranche, runbook, judge draw | `../tranches/` |

## 2. Batch 001 re-triaged with the v3.1 tool (existing outputs, no model)

| | v3 | v3.1 |
|---|---|---|
| valid outputs A / B | 493 / 493 | 497 / 497 (newly valid in a pass: ab0a95, b50f75, c44673, d8f54e, 6e0cb4) |
| agreed | 450 | 457 (7 newly agreed: 1b65ce, 83044c, ab0a95, b43223, c44673, d8f54e, de6e12) |
| eligible | 370 | 402 = 366 with links + **36 "no chain by reading"** |

Right-rate among the eligible chain readings the judge read (right + representation-only; the 4 undecided count as not right):

| tool and rulings | judged | right | wrong | undecided | right (Wilson 95%) | weighted by group share |
|---|---|---|---|---|---|---|
| v3 as the judge scored it (asker not a link) | 244 | 239 | 1 | 4 | 98.0% (95-99) | 98.6% |
| v3 outputs applied under the new rulings (no tool change) | 244 | 231 | 9 | 4 | 94.7% (91-97) | 96.3% |
| **v3.1 tool, new rulings** | 241 | **237** | **0** | 4 | **98.3% (96-99)** | 98.9% |

The asker ruling makes 12 eligible v3 readings wrong (9 the judge read, 3 unread of the same shape «و سأل X Y»); 4cbe02 (the writer of the question kept) turns right. The v3.1 row has 9 fewer (held by `asker_not_a_link`) and 6 more readings the tool now lets through that the judge had read outside sample.tsv
(1b65ce, b43223, d8f54e, de6e12: both readers right; 21210d, 3c59ef: the routes-end release); 4 undecided stay (550aae, 941f93, b2ad9c, cb13de). Per group: six Sunni books 90/90, al-Faqih 70/71, other Imami 77/80.
**Empty readings:** 36 of the judge's 57 are applicable now (33 «clear» + 3 Prophet; the judge found all 36 right as "no chain"); the other 21 stay held (asker 10, inherited speaker 7, «روي عن الأئمة» 1, first-person narrative 1, first-person asker 1, a pronoun asker without a name 1).
**Lists:** `batch-001/eligible_to_apply.txt` **394** readings (agreed, unheld, outside every ruling; 36 "no chain"; 6 eligible readings the judge found undecided or turning on an unruled point are withheld), `batch-001/reread_under_v3_1.txt` **39** reports (asker 32, inherited speaker 6, bare «وعن» 1: they go into tranche 01).
**Limits:** the readings are v3's; the new prompt has not been run. The empty-reading and `routes_end` detectors were tuned on these same cases. 125 of the 366 eligible readings were not read by the judge. Verdicts are one model's, not blind (`../analysis-batch-001/README.md` section 8).

## 3. Tranches of the full run (`../tranches/`)

Population: the 13,843 live reports with an `uncertain` chain; the three judged groups are 10,245 (six Sunni books 7,830, al-Faqih 771, other Imami except al-Kafi 1,644). Without batch 001's 500 and with its 39 re-read reports: **9,784** (7,580 / 658 / 1,546).
**10 tranches** (9 x 980, 1 x 964 reports), 49 packets of 20 each (490 in all), stratified by work (each tranche within one report per work of its proportional share), ids `tNN-xxxxxx` unique across tranches. **50 jobs per tranche** (25 per pass: pairs of packets, pass B shifted by one), 500 jobs.
Characters per job (instruction + prompt + two packets): mean 134,147, from 38,157 (a single packet) to 183,503. Packets 35.6 MB in all. Expected load, two passes: **67.1 M characters in, about 22.4 to 26.8 M tokens in and 4.1 to 4.9 M tokens out** (2.5 to 3 characters per token; the output is 624 letters per report, measured on batch 001's pass A).
Previous reports: 242 reports need one, 205 find one (58 by a named speaker), 37 do not (held). The dataset version was read before the population draw and after the last packet: unchanged (`tranches/manifest.json`).

## 4. Tests (from `datasets/hadith-data/chain-reader/`)

```
python -B -X utf8 -m unittest discover -s v3_1/tests -p "test_*.py"                     # 45 tests: v3's pilot-case table on the v3.1 tool, batch-001 rulings (typos, scope folds, routes-end, asker, empties, submission), prompt, tranches
node --test v3_1/tests/test_backref_lib_v3_1.cjs v3_1/tests/test_build_context_v3_1.cjs  # 9 tests: openings equal Python's, the widened walk, budgets
python -B -X utf8 v3_1/tools/make_prompt_v3_1.py                                         # rebuilds the prompt: 8 examples validated, 21 quoted fragments, 8 pilot readings
python -B -X utf8 v3_1/batch-001/retriage_batch001.py                                    # section 2
python -B -X utf8 tranches/build_tranches.py [--plan-only]                              # section 3 (read-only on production; rebuilds if the dataset version changes during the build)
```
`v3/tests` still pass (24). The v3 `rescore_v3.py` was not re-run under v3.1; the ported pilot table (`tests/test_tool_v3_1.py`) is the check.

## 5. Not built
- The fix pipeline cannot take v3.1 yet (prompt registration, the engine modules, the no-chain envelope): `AGENTS.md` section submission, `../tranches/RUN.md` section 0.
- A hold for the unruled cases (no cue); the 95cd8f fold; a reader-typo repair («أبي طالب» for «بيطالب»); the unfound evidence quote of a `fixes` item still invalidates an output (the judge's f18a2e).
- No run of the new prompt; no judged measurement of any v3.1 reading.
