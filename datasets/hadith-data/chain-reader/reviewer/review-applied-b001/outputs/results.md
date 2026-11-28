---
type: results
---
# review-applied-b001: reviewer v1.1.0 over the 348 applied readings (2026-11-22)

Per-item records: `../private/outcomes.tsv`, `../private/summary.json`, `../private/requeue.txt`. Workers: `claude-opus-5-5` via Conduction (pass 1: 35 jobs; re-queue 1r: 8 jobs; pass 2: 2 jobs). Nothing applied, reverted or relabelled; no database touched.

## Decisions (valid reviews; 73 items have no valid review, see below)

| decision | six Sunni books (184) | al-Faqih (91) | other Imami (73) | all (348) |
|---|---|---|---|---|
| confirm_reading | 177 | 23 | 44 | 244 |
| no_chain (on an applied "no chain" reading) | 0 | 15 | 3 | 18 |
| confirm_with_correction (substantive; none equals the reading) | 6 | 0 | 5 | 11 |
| refer_to_human | 1 | 0 | 1 | 2 |
| prefer_reader_*, keep_stored | 0 | 0 | 0 | 0 |
| invalid (re-queued once, still invalid) | 0 | 53 | 20 | 73 |

All 73 invalid reviews fail one check: `quote_not_exact`. 204 of 722 quotes in the pass-1 and 1r outputs differ from the report text only in Arabic vowel marks (the reviewer wrote the quote unvocalised or re-vocalised); 3 differ otherwise. Every item with vocalised text (al-Faqih, other Imami) is hit; no Sunni item is. The one re-queue round recovered 2 of 75.

## Pipeline actions (`review_rules_v1_1.outcome`)

| action | six Sunni | al-Faqih | other Imami | all |
|---|---|---|---|---|
| label_ai_reviewed | 177 | 38 | 47 | 262 |
| label_disputed (stays applied) | 2 | 0 | 1 | 3 |
| apply_correction (replace with the twice-agreed correction) | 5 | 0 | 5 | 10 |
| requeue (no valid review; stays as it was) | 0 | 53 | 20 | 73 |

Second reviews of the 11 substantive corrections: 10 wrote the same corrected routes (5 Sunni, 5 other Imami), 1 wrote a different correction (cr1-ce3fb5, Abu Dawud), 0 confirmed the original.

## Wrong-share estimate (substantive correction confirmed by a second review; no keep_stored or differing no_chain decision occurred)

| group | k / valid reviews | share | Wilson 95% |
|---|---|---|---|
| six Sunni books | 5 / 184 | 2.7% | 1.2% to 6.2% |
| al-Faqih | 0 / 38 | 0.0% | 0.0% to 9.2% |
| other Imami | 5 / 53 | 9.4% | 4.1% to 20.3% |
| all Imami | 5 / 91 | 5.5% | 2.4% to 12.2% |
| all | 10 / 275 | 3.6% | 2.0% to 6.6% |

Caveats: one model family reviewed model readers; this is the first reviewer-on-readers measurement, not a human audit. The 73 missing reviews are all Imami and not random (al-Faqih rests on 38 of 91). Their raw, unrecorded decisions (quote check ignored): 63 confirm, 8 no_chain, 1 correction, 1 referral.

## Referrals

1. b1-21210d (Tirmidhi), format: a linking phrase «حدثنا بذلك» joins the compiler to an isnad stated first (two routes, ending Abu Hurayra or Abu Said).
2. b1-d6b7d1 (al-Khisal): whether the editor's bracketed «[عن زائدة]» between Zakariyya and Zadhan is a link; the readers omit it, the stored chain keeps it.
