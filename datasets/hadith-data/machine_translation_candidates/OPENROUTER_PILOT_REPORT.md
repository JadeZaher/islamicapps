# OpenRouter rejection pilot — 2026-07-22 UTC

The pilot used `google/gemini-2.5-flash` through OpenRouter with prompt
`hadith-machine-translation-v2`. It selected 14 deterministic backlog rows
covering every translation rejection class, all four traditions, both identity
collisions, and the 55,003-character maximum input. The run used a dedicated
artifact/checkpoint and a `$2` checkpoint ceiling; no canonical dataset,
override, review state, or publication manifest was changed.

## Accounting and mechanical results

- 14 attempted; 13 mechanically accepted; one correctly rejected.
- 48,242 prompt tokens; 22,282 completion tokens; 70,524 total tokens.
- Provider-reported cost: `$0.0701776`.
- All 14 responses reported provider `Google`, requested model
  `google/gemini-2.5-flash`, and finish reason `stop`.
- Zero transport errors, budget blocks, stale/lost claims, Arabic leakage,
  prompt/meta leakage, or declared uncertainty.
- The rejected Imami row contained only `* * * * *`; it was copied unchanged
  and rejected as `copied_input` / `wrong_language`. It is not a hadith and
  should be reclassified before another run.

## Independent content review

Of the 13 mechanically accepted translations, independent Arabic/English QA
classified eight as pass, four as concern, and one as fail.

The confirmed failure is the 30,498-character Al-Kafi row
`thaqalayn:84ab939fb34eb368e9e1e07c`. Its English silently omits the complete
passage forbidding pressure on an insolvent Muslim and promising divine shade
to one who grants respite, then resumes cleanly afterward. The Arabic contains
17 warning anchors (`إياكم`); the English contains only 16 corresponding
“beware” clauses. Transport and schema checks could not detect this semantic
skip, and the model declared no uncertainty.

The 55,003-character `ʿUyun akhbar al-Rida` row begins and ends correctly,
retains both isnads and its final attribution, and preserves all 96 sampled
question/answer anchors in order. That is strong structural evidence, not a
complete scholarly review; the output is also frequently wooden and
over-literal.

The remaining concerns were source/content specific:

- one Ibadi source explicitly abbreviates itself with an ellipsis and “the
  hadith”;
- one Zaydi Arabic source is cut off at `ولم`, and the model correctly did not
  invent a completion;
- one Zaydi rendering flattens `الموطئون أكتافاً` to “humble,” losing the
  idiom's approachable/easygoing sense; and
- both giant Imami master rows have implausible `attributed_to=Prophet Muhammad
  (qudsi)` metadata that must be corrected independently of translation.

Both Ibadi collision rows were translated as distinct reports with their
separate isnads and subject matter preserved.

## Decision

Do not start the full 12,833-row paid queue. Before another scale test:

1. prefilter/reclassify nonlinguistic and incomplete Arabic source rows;
2. add chunking or source-anchor coverage checks for long inputs;
3. correct the two giant Imami attribution fields; and
4. run a larger stratified pilot with several long records and qualified Arabic
   review.

Every artifact remains `candidate_only` and `machine_unreviewed`. Mechanical
acceptance is not evidence of complete or publication-ready translation.
