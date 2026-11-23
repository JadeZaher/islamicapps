---
type: results
---
# review-applied-b001: reviewer v1.1.0 over the 348 applied readings, re-recorded under the tolerant quote rule (2026-11-22)

Per-item records: `outcomes.tsv` (real ids and opaque ids), `summary.json`, `requeue.txt`, `reviews.jsonl` (the review recorded for each item, quotes in the text's own characters). The old records (`../outputs/`, `../private/`) are untouched. No model was run, nothing applied, reverted or relabelled, no database touched.

## The quote rule

A quote is valid when it is a substring of the text (or of the context item it names), or when it is one after folding out ONLY Arabic vowel marks (U+064B-0652, U+0670), Qur'anic annotation marks, tatweel, and normalising whitespace. Letters match exactly (no hamza/alef/ya folding). A quote valid only after the fold is stored as the text's own characters and its review carries `quote_refolded: n`.

Recovery: of the 73 items recorded invalid, 73 now have a valid review (72 from pass 1, 1 only from the re-queue) and 0 stay invalid. 75 items (101 quotes) in the final records were recorded through the refold.

## Pass 1 against the re-queue

Rule: the pass-1 review is the record when it is valid (written first, independently); the re-queue's review is used only when pass 1 has none. 74 items have a valid review in both; decisions agree on 69 (93%); 73 if `no_chain` and `confirm_reading` on an agreed-empty reading (the same verdict: no chain) are counted equal. By pair (pass 1 -> re-queue): confirm_reading -> confirm_reading: 59; confirm_with_correction -> confirm_reading: 1; confirm_with_correction -> confirm_with_correction: 1; no_chain -> confirm_reading: 4; no_chain -> no_chain: 8; refer_to_human -> refer_to_human: 1. Items where both wrote a correction: 1, of which 1 wrote the same routes.

## Decisions (valid reviews)

| | six Sunni books (184) | al-Faqih (91) | other Imami (73) | all (348) |
|---|---|---|---|---|
| confirm_reading | 177 | 62 | 63 | 302 |
| no_chain (on an applied "no chain" reading) | 0 | 27 | 3 | 30 |
| confirm_with_correction (substantive; none equals the reading) | 6 | 1 | 6 | 13 |
| confirm_with_correction equal to the reading (counted as a confirmation) | 0 | 0 | 0 | 0 |
| refer_to_human | 1 | 1 | 1 | 3 |
| prefer_reader_*, keep_stored | 0 | 0 | 0 | 0 |
| no valid review | 0 | 0 | 0 | 0 |

## Pipeline actions (`review_rules_v1_1.outcome`)

| | six Sunni books (184) | al-Faqih (91) | other Imami (73) | all (348) |
|---|---|---|---|---|
| label_ai_reviewed: label AI reviewed (the applied reading stays) | 177 | 89 | 66 | 332 |
| apply_correction: replace with the twice-agreed correction | 5 | 0 | 5 | 10 |
| label_disputed: label disputed (the applied reading stays) | 2 | 2 | 2 | 6 |

## Second reviews of the substantive corrections

13 readings have a substantive correction (or `no_chain` against routes): 10 second reviews wrote the same corrected routes, 1 wrote something else (confirm_with_correction: 1; ids: b1-cae8ac), 2 have no second review yet.

Awaiting a second review (packets built, not run: `../second-pass-refolded/jobs-pass-2.json`): b1-fea4e5 (al-Faqih), b1-2958ef (other Imami). Until it runs, the action for each is `label_disputed` (the applied reading stays).

## Share of applied readings the reviewer finds wrong (all valid reviews)

Confirmed wrong = a second review wrote the same correction (the pipeline would replace or revert it). Alleged wrong = the first review wrote a substantive correction, a `no_chain` against routes or `keep_stored`, confirmed or not. Referrals are in neither. Wilson 95% interval.

| group | confirmed wrong: k / valid | share | Wilson 95% | alleged wrong: k / valid | share | Wilson 95% |
|---|---|---|---|---|---|---|
| six Sunni books | 5 / 184 | 2.7% | 1.2% to 6.2% | 6 / 184 | 3.3% | 1.5% to 6.9% |
| al-Faqih | 0 / 91 | 0.0% | 0.0% to 4.1% | 1 / 91 | 1.1% | 0.2% to 6.0% |
| other Imami | 5 / 73 | 6.8% | 3.0% to 15.1% | 6 / 73 | 8.2% | 3.8% to 16.8% |
| all Imami | 5 / 164 | 3.0% | 1.3% to 6.9% | 7 / 164 | 4.3% | 2.1% to 8.5% |
| all | 10 / 348 | 2.9% | 1.6% to 5.2% | 13 / 348 | 3.7% | 2.2% to 6.3% |

Caveats: one model family reviewed model readers; this is a reviewer-on-readers measurement, not a human audit. Group sizes are 184 / 91 / 73, so the Imami intervals are wide.

## Referrals

1. b1-21210d (six Sunni books): format: connecting chain after the names: the whole route is al-Tirmidhi, Ali b. Hujr, Ali b. Mushir, al-A'mash, Abu Salih, then Abu Hurayra or Abu Sa'id (two routes); «حدثنا بذلك» joins the compiler to the isnad stated first.
2. b1-aa8754 (al-Faqih): a first-person narrative with an unnamed speaker or implicit transmission: «قال: وسألت» continues an earlier report's chain that is not in the packet
3. b1-d6b7d1 (other Imami): Whether the editor's bracketed «[عن زائدة]» between Zakariyya and Zadhan is a link of the chain; the readers leave it out, the stored chain keeps it.
