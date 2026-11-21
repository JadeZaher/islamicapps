---
type: plan
status: recommendation for the owner, 2026-11-21
---

# AI specialist review: models, sampling, pilot

## Volumes (production, 2026-11-21, SELECT only)

| Claim kind | Rows today | Shown to readers | Notes |
| --- | ---: | ---: | --- |
| Identity candidates | 212,921 | 85,277 standing (AI-reviewed by rule) | plus hadith-kg, Riwayat and Imam-kunya bases now in the schema enum, not yet loaded |
| Report correspondences | 135,825 pairs | 66,666 pairs | v2 method in progress |
| Translations | 66,776 source-provided | all | 9,161 machine rows load-ready (translation-run-2); source English is the source's, not reviewed here |
| Gradings | 15,022 cited rulings + 29,915 collection labels | the 15,022 | labels are never grades |
| Narrator verdicts, bios | 20 + 21 | unpublished | hand-written, Sunni |
| History | 182 date claims, 54 events, 38 eras | 0 | history lane output, not loaded |
| Qur'an citations | 11,080 | 0 | not loaded |
| Cited biographical candidates | 17,893 | 0 | from Taqrib and Tahdhib |

## What a rule decides, and is never model-reviewed

A rule is exact, so a model adds nothing and costs something: hash binding; the collection-label exclusion; the
non-ruling exclusion; kunya-only as a label; placeholder rows never a target; the year-in-passage check for history;
exact letter matching of a Qur'an span (a model may review whether a match is a *quotation*, not whether the letters
match); numbering parse flags. These stay "checked by rule".

## Model per specialist

| Specialist | Default | Hard slice (strongest) | Why | Must not be |
| --- | --- | --- | --- | --- |
| isnad-identity | `claude-opus-5-5` | `claude-fable-5-2` for contested names, the Imams' kunyas, and rule-vs-specialist disagreements | rijal reasoning over classical Arabic; homonyms are where errors live | Riwayat's automatic-linking claims used Claude labels: review those with a non-Claude model or record the overlap |
| correspondence | `claude-opus-5-5` | `claude-fable-5-2` for cross-tradition pairs a reviewer disagreed with | close reading; volume is handled by sampling, not a weaker model | |
| translation | `claude-opus-5-5` | | independent of the translators | `tencent/hy-mt2-30b-a3b` (the pinned translator); `google/gemini-2.5-flash` for its own candidates |
| grading-attribution | `claude-opus-5-5` | `claude-fable-5-2` for any contradicted attribution | attribution errors are consequential; passages are short | |
| history-claim | `claude-fable-5-2` | | 182 claims: the strongest model costs little | |
| rijal-link | `claude-opus-5-5` | `claude-fable-5-2` for contested entries | homonym resolution | |

Independence: a reviewer is never the model that produced the claim. The rule procedures were written with Claude
coding assistance, but their output is deterministic code, not a model's judgement; a specialist review is still a
separate, fresh context that never sees that code or its scores.

Cost is taken from provider usage records per run (no price is assumed here). Order of size: an identity packet item
is about 1,500 input tokens and 300 output; a correspondence pair about 1,200 and 250.

## Sampling: never claim a review no reviewer saw

- **Everything** where the volume is small: history (182), narrator verdicts (20), bios (21), the Imam-kunya
  convention entries (one item per convention, plus 20 mentions per kunya), grading attributions that a rule or a
  person contradicts.
- **Stratified samples** where it is large: identity by tradition x basis x contested; correspondence by class x
  score band x scope; translation by work x length band; gradings by grader x term.
- Draws are deterministic: first N per stratum by `sha256(seed || claim id)`, seed and strata recorded in
  `batch.json`. A rerun with the same seed draws the same items.
- **What the label says.** "AI specialist review" appears only on a claim a specialist actually reviewed (a record
  exists for its claim key and current content hash). Every other claim shows only its rule label. The specialist's
  measured agreement per stratum is published on `/method`, so the sample speaks for the procedure, not for unseen
  items.

## Pilot (ready to run)

| | isnad-identity | correspondence |
| --- | --- | --- |
| Packets | `reviews/ai/packets/isnad-identity/pilot-1/packet-01.json` to `packet-05.json` | `reviews/ai/packets/correspondence/pilot-1/packet-01.json` to `packet-06.json` |
| Items | 33 mentions, 46 candidate claims | 33 pairs |
| Strata | gold 5, uncontested AI-reviewed 8, contested 8, name match only 8, Imam kunya 4 | gold 5, same wording 5, variant shown 5, variant below display 5, partial shown 5, partial below display 5, cross-tradition shown 2, the owner-brief example 1 |
| Known answers | 5 (source-identity README examples: Qays b. Abi Gharaza is not Qays b. Abi Hazim; Abu Dawud inside a chain is not the compiler; Abu al-Yaman is al-Hakam b. Nafi; Ghundar is Muhammad b. Jaʿfar; Abu Dawud 4168's Yahya is al-Qattan) | 5 (report-correspondence README examples 1, 2, 3, 5, 6: three real, two formula-only) |
| Model | `claude-opus-5-5`, one fresh subagent per packet | same |

Run each packet per `reviews/ai/README.md` §Isolation, then `record-specialist-run.ts`.

**Trust the specialist if:** all known answers agree (5 of 5 per specialist); every output validates first time
or after one format retry; on the uncontested identity stratum it supports at least 7 of 8 and every exception
cites a passage; on the contested stratum it uses `contested` or `insufficient_evidence` rather than picking a side
without a quoted reason; for correspondence it reads the two below-display bands with a visibly lower `supports`
rate than the shown bands (the one-reader precision was about 2 in 3 below the threshold, 45 of 48 above).

**Distrust it if:** it misses a known answer with low uncertainty; it quotes text not in the packet (the recorder
rejects this; count the rejections); it supports every candidate of a contested mention; or a second run on the same
packet disagrees on more than 1 in 5 items. Then revise the prompt (new version, new hash) and redraw a fresh seed,
never re-score the same packets with the new prompt.

After the pilot, a person reads every item where the specialist and the rule disagree. That reading, not the
specialist's own output, is the specialist's measured agreement on `/method`.
