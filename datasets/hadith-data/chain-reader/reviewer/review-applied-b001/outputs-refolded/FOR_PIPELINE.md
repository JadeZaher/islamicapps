---
type: handoff
---
# review-applied-b001: what the pipeline owner ingests

File: `datasets/hadith-data/chain-reader/reviewer/review-applied-b001/outputs-refolded/outcomes.tsv` (UTF-8, tab separated, one header line, one row per applied reading, 348 rows). Supporting file, same folder: `reviews.jsonl` (one JSON line per reading: the recorded review with quotes in the text's own characters, and the second review where one exists).

Columns: `opaque` (the reviewer's packet id, `cr1-xxxxxx`), `id` (the reading id, `b1-xxxxxx`, as in `reviews/ai/records/chain-fixes/submissions/*.jsonl` `reading.id`: look the fix up there), `status` (`applied`), `holds`, `not_clearable`, `valid`, `decision` (the reviewer's), `effective` (after rule (a): a correction equal to the reading is a confirmation), **`outcome`** (what the pipeline does), `action_class`, `second_pass` (a second review is required), `second_run` (`True` the second review wrote the same routes, `False` it did not, empty none yet), `uncertainty`, `question`, `problem`, `quote_refolded` (how many of the review's quotes were recorded through the vowel-mark fold; 0 for none).

## Counts by `outcome`

| outcome | readings | what to do | label |
|---|---|---|---|
| `label_ai_reviewed` | 332 | label AI reviewed (the applied reading stays) | Read by model; AI reviewed (claude-opus-5-5), <date>; awaiting human review |
| `apply_correction` | 10 | replace with the twice-agreed correction | Corrected by AI review (claude-opus-5-5, 2 runs), <date>; awaiting human review |
| `label_disputed` | 6 | label disputed (the applied reading stays) | Read by model; disputed by AI review (claude-opus-5-5), <date>; awaiting second review |

Total 348. `<date>` is the date the pipeline records the review. Each `apply_correction` replaces the applied reading with the corrected routes of `reviews.jsonl` (`second_review` agrees with `review`); the side-by-side list is `replacements.md`. A `label_disputed` reading STAYS applied and is labelled: 3 are referrals to a human, 1 had a second review that wrote a different correction, 2 wait for a second review in `../second-pass-refolded/` (packets and `jobs-pass-2.json`, not run): b1-fea4e5, b1-2958ef. A human decision on a reading always wins over these outcomes (`human_decides`).

Nothing in this folder was applied. Re-run `python -B -X utf8 reviewer/rerecord_refolded.py` (from chain-reader/) after the second pass is run into `second-pass-refolded/outputs/pass-2/`; it re-reads every output and rewrites these files.
