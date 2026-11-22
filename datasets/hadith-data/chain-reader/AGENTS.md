---
type: reference
---
# chain-reader: design notes

Operating instructions are in `README.md`; this file holds the reasons. Code carries one-line docs and points here.

## prompt
- Built, not hand-edited: `tools/prompt_body.md` + `tools/make_prompt.py`. The examples' offsets are computed from real report text and each example
  is run through `validate.py` at build time, so a prompt with a wrong example cannot be produced. Examples come from reports the audits judged
  and are excluded from the pilot (`examples/examples.json`, read by `build_pilot.py`).
- Conventions per tradition are separate short blocks because a rule that is right in one tradition is wrong in another (a trailing «بهذا الإسناد»
  adds nothing in a Sunni chain judged by the audits, «عنه» is a link in al-Kafi and al-Rabi').
- «بهذا الإسناد» is asked for as a `back_reference` link (the task's vocabulary); stored chains never carry it, so `score.py` drops it from the
  reader's route before comparing. Without that, every correct Sunni chain ending that way would count as a miss.
- Shared tail (`shared_tail_from`): links the text writes once for several routes carry identical `start`/`end` in each route. If the text repeats
  the names per route (Pure Canon's `|` field), the routes are independent and the tail is `null`.

## validate
- Accepts or rejects mechanically; it never judges the reading. `repair_offsets` exists because models miscount characters: strict pass rate
  tells the harness whether offsets can be trusted, repaired pass rate is the denominator for the reading metrics.
- A declared tail must be the same occurrence as a tail link of another route, and tail links may not overlap the route's own links: otherwise
  the exemption from text order would let any reordering through.

## score and norm
- `fold_exact`: marks, tatweel, zero-width characters out; punctuation and whitespace are one space (stored surfaces lose commas inside names).
  `fold_loose` adds hamza/ya/ta marbuta folding and is used only for containment and for the "is this name in the text" test.
- Stored chains are compared on the names the text contains (`stored_route`). A chain completed from a previous report cannot be reproduced from one report's text;
  `stored_reduced` reports how often that happened.
- Denominators: outputs valid after offset repair. Missing or invalid outputs are listed in `disagreements.tsv` and counted in the validity columns, not as misreadings.
- Labels: `label_state` is `current` (round 4), `confirmed`, `unconfirmed`, `older`; see README "weaker than it sounds". Do not merge states silently.

## pilot set
- Built from the hand-read `sample_check.csv` rows of rounds 2-4 (`judged_by = read`, verdict ok/correct/defect; pair rows and unread rows are not labels).
  A later round's label for the same chain overrides an earlier one. Round 3 population rows without a chain id are report-level labels.
- Reader text: `text_ar`; for Ahmad, al-Darimi and the Muwatta (matn only in `text_ar`) the chain field `hadiths.sanad`, a blank line, then `text_ar`
  (`text_layout = chain_field_then_matn`). OpenITI reports with `sanad_inherits_from` are excluded (the chain is the parent's).
- Ids are opaque (`cr-NNNN`) and the order is an md5 shuffle, so neither the filename nor the position in a packet reveals work or verdict.
- Do not edit `pilot/` by hand; rerun `tools/build_pilot.py`. Never write anywhere else from here.

## deferred
- Parent text for inherited chains (Rabi' continuations, Sahifat al-Rida); second isnads after the matn as routes; re-verifying round 2/3 defect labels
  on the final production load (trigger: production load finished); automatic extraction of right readings from notes beyond the 12 regex cases.
