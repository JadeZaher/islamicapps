# reviewer/: design notes

Operating instructions, the decision rule and the pilot: `README.md`; the pipeline owner's work: `INTEGRATION.md`. Nothing here runs a model or writes a database.

- **One rule table in code.** `review_rules.py` holds the vocabulary, the plain words of every hold code and the clearable flag; the builder, the validator, the scorer and the README's
  tables all follow it, so the pipeline can import the same `outcome()` semantics rather than re-deriving them from prose. Unknown codes are not clearable: a new hold is safe by default.
- **Reader A is pass A, not shuffled.** The applied reading is pass A's; shuffling would make `prefer_reader_a` mean different passes in different items for no gain (the reviewer sees no
  pass name anyway). Reader outputs carry the item's opaque id, never the report id.
- **Exact quotes, not folded.** The reader validator accepts a folded quote; the reviewer's must be an exact substring (the house rule for specialists, `reviews/ai/README.md`): a reviewer that
- **Quote rule (v1.1 validator, 2026-11-22).** v1's exact-substring rule stays in `validate_review.py` (untouched); `validate_review_v1_1.py` accepts a quote that equals a substring after folding ONLY vowel marks (U+064B-0652, U+0670), Qur'anic annotation marks, tatweel, and normalising whitespace. Letters match exactly: hamza/alef/ya are different words in a quote, so the reader's `norm.fold_loose` is deliberately not reused. Why: the reviewer dropped or changed tashkil when quoting vocalised Imami text and 73 of 348 applied-set reviews were thrown away for it (198 of 722 quotes, all marks only; no quote differed in a letter). A refolded review is valid, its quote is replaced by the TEXT's own characters, and it carries `quote_refolded: n` (also a column in `outcomes.tsv`). Corrected readings need no change: the reader validator (`expand_v3_2._strict_pattern`) already ignores marks in a surface and stores the text's own characters. The re-record of the applied set is `rerecord_refolded.py` (`review-applied-b001/outputs-refolded/`); a pass-1 review wins over its re-queue's. `prompt-reviewer-v1_2.draft.md` is the unused next prompt (one line asks for exact marks).
  normalises a quote has not copied it, and its review is what a human will check first.
- **Corrections need two runs**, `prefer_reader_*` one: a preferred reading already has one independent model (the reader) agreeing with the reviewer; a correction has none.
- **`no_chain` against routes is treated as a correction** (second pass too): it retires a stored chain on the reviewer's word alone otherwise.
- **Applied readings revert on any non-confirmation** (owner): the failure that matters on an applied chain is a wrong chain shown; the stored chain is the known quantity.
- **Packets are JSON, 10 items**: the reviewer reads slowly and the packets carry both readings in full (about 100 KB each); JSON (not JSONL) follows `reviews/ai` packets.
- The pilot's sample seed (20261601) and the salt for opaque ids are fixed in code / `private/`; re-running the builder reproduces the same ids and order.
