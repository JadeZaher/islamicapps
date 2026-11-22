---
type: pilot
---
# Chain reader pilot (model-based isnad reader)

Rule-based chain extraction has plateaued (`../chain-audit/round4/README.md`: about 1 in 10 stored Sunni chains still wrong).
This directory holds the materials to test the alternative: a language model reads each report's Arabic and returns its
routes, mechanically validated, then fanned out over the corpus. **Nothing here runs a model, writes to the database or
changes the product.** Design notes and rationale: `AGENTS.md`.

## Files

| Path | What |
|---|---|
| `prompt.md` | The reader prompt (front matter `version`), built by `tools/make_prompt.py` from `tools/prompt_body.md` plus 8 worked examples (`examples/examples.json`) |
| `validate.py` | Mechanical acceptance of one output; `--repair` re-finds offsets from surfaces. Tests: `tests/test_validate.py` |
| `score.py`, `norm.py` | Pilot scorer (Wilson 95% tables, `disagreements.tsv`) and the comparison forms. Tests: `tests/test_score.py` on `tests/fixtures/` |
| `pilot/reports.jsonl` | One row per report: id, tradition, work, the text the reader sees, stored chains with the human verdict per chain, report-level verdicts |
| `pilot/packets/packet-NN.jsonl` | Blind packets of 25 (`{"id","text"}` only). `pilot/pilot_summary.json`: counts and exclusions |
| `sizing.json` | Corpus sizing (below), measured read-only on production |
| `tools/` | `fetch_labelled.cjs` (read-only snapshot of the labelled reports), `build_pilot.py`, `make_prompt.py`, `sizing.cjs`, `hash_prompt.py`, `http_reader.py` (stub) |

## Prompt

`prompt.md` version **1.0.0**, SHA-256 of its exact bytes (LF endings; `.gitattributes` pins them):

`2ae9a0e923aa3450cd0c8655ce1f4f6d9ec1cc430bd576bb3706e3d1d949da14`

`python tools/hash_prompt.py --check` fails if this line and the file disagree. Change the prompt, bump `version`, rebuild
(`tools/make_prompt.py`), re-record the hash here, and treat every earlier output as belonging to the old hash. About 19,000
characters (the examples are fully diacritized Arabic): estimate 8-10k input tokens per call, to be measured with the chosen model's tokenizer.
Output: `{"id", "routes": [{"links": [{"surface","start","end","kind"}], "shared_tail_from"}], "matn_start", "notes"}`;
kinds `narrator | unnamed | back_reference | relation`. Offsets are Python string indices (UTF-16 and code points agree for Arabic).

## What the pilot measures, and the numbers it produces

The set (`pilot/reports.jsonl`): **284 reports, 105 labelled defective, 179 labelled correct** (see the per-work table).
The reader never sees the stored chain, the verdict, the work name or any label; the packet order is a deterministic md5 shuffle.

| Question | Number from `score.md` | Proposed go (adjust before running) |
|---|---|---|
| Can it follow the output contract? | share passing `validate.py` as given, and after offset repair | repaired >= 97%; strict >= 90% (otherwise the harness must re-find offsets) |
| Does it keep what is right? | labelled-correct chains reproduced exactly (surface sequence, diacritic/whitespace/punctuation-insensitive), `loose` beside it | exact >= 93%, Wilson lower bound >= 88% (the stored chains are right for these, so every miss is a false alarm; real prevalence of defects is about 10%) |
| Does it move where the rules are wrong? | labelled-defective items where the reader differs from the stored chain; share containing the lost name (12 reports only) | differs >= 70% **and** a human reading of `disagreements.tsv` finds the reader right in >= 70% of them |
| Is it stable? | two independent runs on the same packets: exact same routes per report | >= 90% |
| Who is it good at? | the same rows per work, with intervals | no work with a lower bound far below the total (small works are wide: read them, do not gate on them) |

Intervals at this size: roughly +-5 points on the 179 correct (at 90%), +-9 on the 105 defective (at 70%), +-20 and wider per work (Muslim 23/23 and
Kafi 14/14 are the only works above 10 per arm).
`disagreements.tsv` is the real product of the pilot: every labelled-correct mismatch, every defective item the reader
reproduced, every invalid output and every run-to-run difference, with the stored routes, the reader's routes and the text head.

### Pilot composition (reports; defective / correct)

Defective: every report with a hand-read defect whose label is current (round 4: 39) or confirmed (round 2/3 with a quoted stored
surface still in the chain: 31), plus 35 older unconfirmed ones (newest round first) up to a cap of 105; 81 more defective
candidates were left out. Correct: as many per work as defective, at least 5 (fewer where fewer exist), freshest labels first (round 4: 124 reports).

| work | defective | correct |
|---|---|---|
| sunni:muslim | 23 | 23 |
| sunni:bukhari | 10 | 10 |
| sunni:abudawud | 8 | 8 |
| sunni:tirmidhi | 8 | 8 |
| sunni:ibnmajah | 5 | 5 |
| sunni:nasai | 4 | 5 |
| sunni:ahmad | 2 | 5 |
| sunni:darimi | 1 | 5 |
| sunni:muwatta | 1 | 5 |
| imami:al-kafi | 14 | 14 |
| imami:man-la-yahduruhu-al-faqih | 10 | 10 |
| imami:thawab-al-amal | 2 | 5 |
| imami:al-khisal | 2 | 5 |
| imami:kitab-al-ghayba-numani | 2 | 5 |
| imami:kitab-al-ghayba-tusi | 2 | 5 |
| imami:al-amali-saduq | 1 | 5 |
| imami:al-tawhid-saduq | 1 | 5 |
| imami:kamil-al-ziyarat | 1 | 4 |
| imami:fadail-al-shia | 1 | 2 |
| imami:kitab-al-mumin | 1 | 3 |
| imami:uyun-akhbar-al-rida | 1 | 5 |
| imami:al-amali-mufid, kamal-al-din, maani-al-akhbar, mujam-al-ahadith-al-mutabara | 0 | 5 each |
| imami:sifat-al-shia | 0 | 4 |
| imami:kitab-al-zuhd | 0 | 3 |
| ibadi:musnad-rabi | 5 | 5 |
| zaydi:musnad-zayd | 0 | 5 |
| imami:sahifat-al-imam-ali-al-rida | 0 | 0 |
| **total** | **105** | **179** |

By tradition: Sunni 62 / 74, Imami 38 / 95, Ibadi 5 / 5, Zaydi 0 / 5.

### What makes the scoring weaker than it sounds

1. **Old labels describe old chains.** Round 2 and 3 verdicts were read before the later builder commits (`cc91b0e` ... `83c5e2f`); only
   round 4 was read on the current builder. Each label carries `label_state`: `current` (round 4), `confirmed` (a quoted stored surface still
   stored), `unconfirmed` (older, nothing confirms it still holds), `older` (an older "correct", not re-read). `stale_fixed` ones were dropped
   (round 3 re-judged them fixed) and 35 labelled chains that are no longer live were dropped. `score.md` shows the defective rate with
   and without the unconfirmed ones. A reader that "reproduces the stored chain" on an unconfirmed defect may simply be right.
2. **Most defect notes say what is wrong with the stored chain, not what the right reading is.** Only 12 of the 105 defective reports have a note
   from which a lost name could be taken mechanically (Arabic name followed by "missing / not stored / lost"). For the rest, "reader differs"
   proves only that the reader disagrees, not that it is right: the human read of `disagreements.tsv` is the measure. `expected_names` is a regex
   extraction, not a hand-checked field.
3. **Stored chains hold names the text lacks.** 61 of 270 labelled chains (about 1 in 4 labelled items) have a stored name that is not in the
   report's text (mostly «و بهذا الإسناد» reports whose chain was completed from the previous report; Thaqalayn). A reader cannot see
   those names, so `score.py` compares on the names the text has and says how many items were reduced that way. The audit judged such chains as
   whole chains.
4. **The audits accept surfaces the prompt forbids.** Stored surfaces sometimes keep a gloss («عبد الله بن يزيد - مولى المنبعث», «عفان المعنى») or a
   verb prefix; the prompt asks for names only. `loose` equality (one surface a contiguous word run of the other) separates this noise from real
   differences; the exact figure is still the headline.
5. **Judgment items.** A Companion named only inside the matn as the source (rounds 3 and 4 "companion_in_matn_judgment") is a link by the prompt's
   rule 2; the audit counted it as a defect only as a judgment call. Pure Canon (Ahmad, Darimi, Muwatta) chains were judged against the
   source's own `sanad` field, so "correct" there means "agrees with the field".
6. **What the set cannot test.** Continuations that inherit a parent's chain (Sahifat al-Rida 100 of its labelled reports, al-Rabi' 30) are excluded:
   the chain is not in the continuation's text; they need the parent's text in the input, a design decision for later. Rida therefore has no pilot
   reports and Zayd no defective one. Second isnads written after the matn cannot be routes here (they would lie in the matn), so that defect class
   (3 of the 7 round-4 report-level defects) is only a note. 3 labelled reports over 6,000 characters were left out.
7. **Prevalence.** 37% of the pilot is defective, about 10% of the real corpus is. Read the correct-chain figures as the false-alarm rate to expect.
8. **Production moves.** `pilot/reports.jsonl` is a snapshot (`snapshot_at` on every row, 2026-11-22T14:07Z) taken while another job is loading
   production. Re-run `tools/fetch_labelled.cjs` and `tools/build_pilot.py build` after it finishes if the stored routes matter; labelled chain ids that
   disappear are dropped automatically.
9. **Offsets.** Models count characters badly. Strict validation may fail on a correct reading; use the repaired column for the reading, strict for the harness decision.
10. **Prompt examples are out of the set.** The 8 reports used as worked examples are excluded from the pilot; a different set of examples changes the hash and needs a rebuild.

## Running a reader

Use a fresh context per packet and nothing but the two inputs; do not give the reader `pilot/reports.jsonl`, `pilot_summary.json`,
the audit directory or earlier outputs.

**(a) As an agent.** Copy `prompt.md` and one packet (`pilot/packets/packet-NN.jsonl`) alone into an empty directory. Instructions to the agent:
"Your instructions are in `prompt.md`. Read `packet-NN.jsonl`: each line is one report. For every line, answer exactly as the prompt
defines, and write the answer, verbatim and only the JSON, to `outputs/<run>/<id>.json` (the line's `id`, e.g. `cr-0007.json`). Do not read any other file."
Record the exact model id the runtime reports, the UTC time before and after, and the prompt hash, next to `outputs/<run>/` (e.g. `outputs/<run>/RUN.txt`). Do it twice
with a different run name for the agreement figure. Then `python validate.py --reports pilot/reports.jsonl --outputs outputs/<run> --repair`
lists what fails.

**(b) Through an HTTP chat API.** `tools/http_reader.py` builds the payloads and is a stub: it implements no request. Per report the payload is
the contents of `prompt.md` as the system message and `{"id": ..., "text": ...}` as the user message; nothing else (no project name,
path, label, stored chain or other metadata; the ids are opaque). The key is read at run time from `CHAIN_READER_API_KEY`, never from a file or argument, and is not printed.
`python tools/http_reader.py --packet pilot/packets/packet-01.jsonl --out-dir outputs/<run> --dry-run` checks the payload shape without a key.
Fill in `send()` for the chosen provider, temperature 0, reply saved verbatim.

**Scoring.**
```
python score.py --reports pilot/reports.jsonl --outputs outputs/run-a --outputs-b outputs/run-b --out outputs/run-a/score
```
writes `score.md` (a go/no-go block, then one row per work and tradition with Wilson 95% intervals) and `disagreements.tsv`.

**Tests.** `python -m unittest discover -s tests -p "test_*.py"` from this directory (validator rules, scorer on the fixture, pilot-set invariants).
**Rebuild.** `python tools/build_pilot.py ids --out ids.json`; `node --env-file=.env.local datasets/hadith-data/chain-reader/tools/fetch_labelled.cjs ids.json fetched.json`;
`python tools/make_prompt.py --fetched fetched.json`; `python tools/build_pilot.py build --fetched fetched.json --out-dir pilot`; `python tools/hash_prompt.py`.

## Corpus sizing (live rows, `retired_at is null`)

Measured 2026-11-22T14:19Z with `tools/sizing.cjs` (read-only) while production was being loaded: earlier audit counts of uncertain chains
(Sunni 20,441, Imami 12,881 in round 4) have already fallen (now 17,975 and 4,627), so re-measure before costing. "Chars" is what the reader would see: `text_ar`, plus the
separate chain field for Ahmad, al-Darimi and the Muwatta. "Uncertain" = at least one live chain with `structure_status = 'uncertain'`.

| tradition | reports | chains | reports with a chain | reports with an uncertain chain | chars of those reports | chars of all reports |
|---|---|---|---|---|---|---|
| **sunni** | 64,356 | 76,262 | 61,970 | 10,359 | 3,708,060 | 17,764,182 |
| **imami** | 33,395 | 33,229 | 28,652 | 3,439 | 3,404,918 | 18,958,627 |
| **ibadi** | 1,005 | 841 | 832 | 40 | 10,547 | 225,925 |
| **zaydi** | 691 | 667 | 667 | 5 | 3,382 | 190,313 |
| **all** | 99,447 | 110,999 | 92,121 | 13,843 | 7,126,907 | 37,139,047 |

| work | reports | chains | reports with a chain | uncertain reports | chars (uncertain) | chars (all) |
|---|---|---|---|---|---|---|
| sunni:ahmad | 23,529 | 26,274 | 23,336 | 2,173 | 605,848 | 4,712,490 |
| sunni:muslim | 7,596 | 13,272 | 7,529 | 2,849 | 1,006,910 | 2,512,008 |
| sunni:bukhari | 7,370 | 8,049 | 7,345 | 1,295 | 577,042 | 2,717,818 |
| sunni:nasai | 5,774 | 6,837 | 5,768 | 1,191 | 417,533 | 1,759,784 |
| sunni:abudawud | 5,260 | 6,669 | 5,258 | 1,285 | 509,053 | 1,722,942 |
| sunni:tirmidhi | 4,214 | 5,128 | 4,209 | 619 | 316,957 | 1,890,073 |
| sunni:ibnmajah | 4,227 | 5,504 | 4,225 | 591 | 201,569 | 1,185,756 |
| sunni:darimi | 2,477 | 2,645 | 2,475 | 291 | 55,707 | 441,994 |
| sunni:muwatta | 1,855 | 1,884 | 1,825 | 65 | 17,441 | 407,541 |
| sunni:shafii (no chain in source) | 2,054 | 0 | 0 | 0 | 0 | 413,776 |
| imami:al-kafi | 14,245 | 16,600 | 14,211 | 1,024 | 1,031,671 | 8,082,810 |
| imami:man-la-yahduruhu-al-faqih | 6,382 | 4,891 | 4,566 | 771 | 350,046 | 2,597,197 |
| imami:nahj-al-balagha (no isnad by design) | 2,260 | 0 | 0 | 0 | 0 | 648,789 |
| imami:al-khisal | 1,282 | 1,515 | 1,259 | 222 | 167,575 | 794,060 |
| imami:thawab-al-amal | 1,106 | 1,132 | 1,095 | 138 | 80,584 | 605,261 |
| imami:al-amali-saduq | 1,082 | 1,175 | 1,036 | 145 | 189,577 | 897,397 |
| imami:uyun-akhbar-al-rida | 954 | 1,102 | 946 | 160 | 444,269 | 1,255,082 |
| imami:maani-al-akhbar | 829 | 985 | 805 | 131 | 99,442 | 456,451 |
| imami:kitab-al-ghayba-tusi | 774 | 741 | 599 | 147 | 95,658 | 391,175 |
| imami:kamil-al-ziyarat | 750 | 895 | 740 | 182 | 215,680 | 638,100 |
| imami:kamal-al-din | 659 | 887 | 628 | 139 | 339,594 | 958,362 |
| imami:al-tawhid-saduq | 575 | 724 | 571 | 83 | 182,039 | 513,525 |
| imami:mujam-al-ahadith-al-mutabara | 555 | 730 | 547 | 63 | 32,280 | 220,172 |
| imami:kitab-al-ghayba-numani | 468 | 616 | 466 | 112 | 90,612 | 289,410 |
| imami:al-amali-mufid | 387 | 408 | 385 | 59 | 49,536 | 294,038 |
| imami:kitab-al-zuhd | 290 | 306 | 287 | 18 | 8,948 | 93,712 |
| imami:kitab-al-duafa | 226 | 0 | 0 | 0 | 0 | 30,143 |
| imami:sahifat-al-imam-ali-al-rida | 205 | 205 | 205 | 3 | 3,029 | 42,130 |
| imami:kitab-al-mumin | 201 | 198 | 191 | 19 | 4,225 | 48,943 |
| imami:sifat-al-shia | 71 | 74 | 71 | 5 | 3,107 | 56,291 |
| imami:risalat-al-huquq | 49 | 0 | 0 | 0 | 0 | 12,110 |
| imami:fadail-al-shia | 45 | 45 | 44 | 18 | 17,046 | 33,469 |
| ibadi:musnad-rabi | 1,005 | 841 | 832 | 40 | 10,547 | 225,925 |
| zaydi:musnad-zayd | 691 | 667 | 667 | 5 | 3,382 | 190,313 |

253 reports (al-Rabi' 49, Sahifat al-Rida 204) inherit their chain from a parent report and need the parent's text in the input.

**Cost, to be re-checked with the model's tokenizer.** The 13,843 uncertain reports are 7.1M characters of input, about 3M tokens at roughly 2.3
characters per token; the whole corpus is 37.1M characters, about 16M tokens. Add the prompt (8-10k tokens) once per call: 13,843 single-report calls
would cost about 120M prompt tokens uncached, 550 calls of 25 reports (the packet size) about 5M. Output is JSON of roughly 25 tokens per link: assume
300-600 tokens per report, 4-8M tokens for the uncertain set. The longest uncertain report is 55,003 characters (Uyun akhbar al-Rida); 18 works have an
uncertain report over 5,000 characters, so a length cap or a split rule is needed before fan-out.
