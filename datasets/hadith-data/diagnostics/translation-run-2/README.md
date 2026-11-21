---
type: diagnostic
status: candidate_only_unreviewed
---

# translation-run-2 (2026-11-21): gap-fill English for reports with no creditable public English

**Status: partial. The run stopped at 7,046 of 31,090 reports because the OpenRouter account ran out of credits (see "Blocked").**
Everything here and in `machine_translation_candidates/` is a review-only candidate. No database write, no canonical file, no `src/` or `drizzle/` change.
Runner: `translate_gap_fill.py` (reuses `../../generate_hy_mt2_candidates.py`: sentence splitting, transport with backoff, `screen-v2`, budget, locked journal). Tests: `test_translate_gap_fill.py`.

## Gap

A "creditable public English" is an English text on a public report whose model or translator can be named on the page. Query (read-only, production, 2026-11-21): public reports with no `translations` row, or a row that is not `quality_status = complete`, or whose Arabic hash differs: **43,914 of 99,273** (public English before: 55,359).

By what the report has today:

| Existing English | Reports |
| --- | ---: |
| No `translations` row: Sunni 30,768 (Musnad Ahmad 23,529, Darimi 2,477, Shafi'i 2,054, Muwatta' 1,855, Tirmidhi 186, Muslim 354, Bukhari 177, Ibn Majah 128, Nasa'i 8), Ibadi 1,004, Zaydi 698, Sahifat al-Rida 35 | 32,505 |
| Row failing QA: arabic_leakage 11,399, placeholder 8, suspiciously_short 1, same_as_arabic 1 | 11,409 |

The 29,915 Sunni reports from Musnad Ahmad, Muwatta', Darimi and al-Shafi'i whose master English has no recorded model have no `translations` row in production, so nothing creditable is shown for them today.

By how this work covers them:

| Coverage | Reports |
| --- | ---: |
| Earlier mechanical glyph candidates (source English with honorific ligatures replaced; no model; credited to the source): `honorific_glyph_substitution_candidates_2026-11-21.jsonl` | 10,662 |
| Earlier accepted hy-mt2 rows (pinned model; reused, not re-translated): the 2026-11-21 pilot (rescreened), `batch_no_usable_english`, `batch_names_terms` | 2,141 |
| Earlier skipped (a sentence over 5,500 characters) | 15 |
| To translate in this run (31,090 plannable, 6 skipped here) | 31,096 |

Before and after by tradition and work (after = public English + glyph candidates + accepted hy-mt2 candidates, assuming they are loaded; `run_summary.json` has the per-state breakdown). Works with no gap are omitted.

| Tradition | Work | Public reports | Public English before | Gap | Creditable English after | Still without |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Ibadi | al-Jami al-Sahih (Musnad al-Rabi ibn Habib) | 1,004 | 0 | 1,004 | 1,001 | 3 |
| Imami | 'Uyun Akhbar al-Rida | 953 | 949 | 4 | 950 | 3 |
| Imami | Al-Amali (Saduq) | 1,082 | 1,081 | 1 | 1,082 | 0 |
| Imami | Al-Kafi | 14,245 | 14,185 | 60 | 14,234 | 11 |
| Imami | Al-Khisal | 1,282 | 1,278 | 4 | 1,282 | 0 |
| Imami | Kamal al-Din | 659 | 635 | 24 | 655 | 4 |
| Imami | Kitab al-Du'afa | 226 | 136 | 90 | 226 | 0 |
| Imami | Kitab al-Ghayba (Nu'mani) | 467 | 466 | 1 | 467 | 0 |
| Imami | Kitab al-Ghayba (Tusi) | 774 | 773 | 1 | 773 | 1 |
| Imami | Kitab al-Mu'min | 201 | 199 | 2 | 201 | 0 |
| Imami | Ma'ani al-Akhbar | 829 | 825 | 4 | 828 | 1 |
| Imami | Man La Yahduruhu al-Faqih | 6,382 | 6,346 | 36 | 6,381 | 1 |
| Imami | Mu'jam al-Ahadith al-Mu'tabara | 555 | 29 | 526 | 554 | 1 |
| Imami | Nahj al-Balagha | 2,260 | 2,259 | 1 | 2,259 | 1 |
| Imami | Sahifat al-Imam Ali al-Rida | 35 | 0 | 35 | 34 | 1 |
| Imami | Thawab al-A'mal | 1,106 | 1,105 | 1 | 1,106 | 0 |
| Sunni | Jami' al-Tirmidhi | 4,212 | 2,359 | 1,853 | 4,212 | 0 |
| Sunni | Musnad Ahmad | 23,529 | 0 | 23,529 | 4,509 | 19,020 |
| Sunni | Musnad al-Shafi'i | 2,054 | 0 | 2,054 | 804 | 1,250 |
| Sunni | Muwatta' Malik | 1,855 | 0 | 1,855 | 189 | 1,666 |
| Sunni | Sahih Bukhari | 7,370 | 7,193 | 177 | 7,370 | 0 |
| Sunni | Sahih Muslim | 7,590 | 7,236 | 354 | 7,590 | 0 |
| Sunni | Sunan Abi Da'ud | 5,260 | 1,105 | 4,155 | 5,260 | 0 |
| Sunni | Sunan Ibn Majah | 4,227 | 1,115 | 3,112 | 4,227 | 0 |
| Sunni | Sunan al-Darimi | 2,477 | 0 | 2,477 | 354 | 2,123 |
| Sunni | Sunan an-Nasa'i | 5,774 | 3,918 | 1,856 | 5,774 | 0 |
| Zaydi | Musnad al-Imam Zayd ibn Ali | 698 | 0 | 698 | 693 | 5 |
| **All** | | 99,273 | 55,359 | 43,914 | 75,182 | 24,091 |

Of the 24,091 still without: 24,044 not yet translated (489 of them failed with HTTP 402; 6 are Imami, the rest Sunni), 26 failed the screen, 15 skipped by the earlier run and 6 skipped by this one. Reproduce: `translate_gap_fill.py snapshot`, then `gap` and `summary`. `gap_before.json` and `gap_before_manifest.csv.gz` (record id, work, Arabic hash, existing English status, coverage) are the gap as found.

## Terminology prompt (a pin change, not a model change)

`translation_model.json` gained `prompt_terminology` (`hy-mt2-terminology-en-prompt-v2`, 94 terms: honorific and isnad formulas, the commonest Companion, Imam, Zaydi and Ibadi names, common legal terms, in the glossary transliteration scheme of `src/lib/glossary/terms.ts`). It uses the model card's Terminology template ("Reference the following translations: {ar} translates to {en} ..."). Per request only the entries whose Arabic occurs in the text are sent (diacritics and alef variants ignored, longest match wins, at most 14, in order of appearance); a source with no match gets the base prompt. The base prompt stays in `prompt` and is the fallback; the model is unchanged. Two guards beyond `screen-v2` (a repeated reference list; any macron or dot mark in the English) reject an output, and the row is retried once with the base prompt.

Paired pilot: the same 60 rows (stratified by tradition, Sunni split over its four gap works, three length bands, two long rows forced in), one sample each at temperature 0.7, base prompt against terminology prompt (`pilot_comparison.json`). Two of the 60 sources are non-linguistic (a single letter, a row of asterisks), so 58 were compared.

| Measure over the pilot outputs | Base prompt | Terminology draft 1 | Terminology revision 2 (used) |
| --- | ---: | ---: | ---: |
| Honorific in one parenthetical form | 56 | 147 | 137 |
| Honorific in comma or dash forms | 111 | 11 | 31 |
| "God" instead of "Allah" | 4 | 1 | 1 |
| Glossary mark ʿ in names | 0 | 94 | 64 |
| Rows with macron or dot transliteration | 0 | 2 | 1 (now rejected by the guard) |
| "O the Messenger of Allah" (wrong vocative) | 0 | 7 | 0 |
| Screen rejects | 2 (the junk sources) | 2 (same) | 1 (the guard) |

Reading (the lane agent, 36 pairs against the Arabic): meaning-level errors 5 with the base prompt (pc_62947 "two women" for two things; pc_90728 "forbade him"; zayd_0415 "she inherited"; pc_2141 "I read it" for the command "Read"; pc_43469 the names "Har and Abd" for a free man and a slave) against 3 plus 2 minor with draft 1. The draft 1 error on pc_73910 (a dropped negation) is sampling noise: that row had no terminology match, so both runs sent the identical prompt and gave different meanings. Verdict: the terminology prompt is **kept**. It is clearly more consistent (formulas, names, "Allah", the ʿ scheme) and not worse on meaning. Costs seen: draft 1 wrote "O the Messenger of Allah" (fixed by vocative entries), occasional macron transliteration (guarded), and where the Arabic omits the Prophet's name it renders a bare "(peace and blessings be upon him) said". Revision 3 (the quoted Zaydi sigla `" ع م "`, `" ص "`, `(ص)`, `(ع)`) was added during the run; 18 accepted rows need the redo pass below. The sigla expansions follow the base run's reading and are unverified.

## Batch (gap-fill run 2)

The gap is Sunni 41,422, Imami 790, Zaydi 698, Ibadi 1,004; 31,090 reports (4.64 million Arabic characters) were plannable. Concurrency 8, then 16 (1.0 attempts per call, no 429), then 32 (the account ran dry there). Reports were taken in record-id order (`openiti:` Ibadi, Imami, Zaydi, then `pure-canon:` Sunni, then `thaqalayn:`), so the Ibadi, Zaydi and Sahifat al-Rida sets are complete and the four Sunni works are partial.

| | Reports |
| --- | ---: |
| Selected for translation | 31,090 |
| Attempted with a response | 7,046 |
| Accepted by the screen | 7,020 |
| Failed the screen | 26 (diacritic_transliteration 16 after a base-prompt retry, repetition_loop 7, length_ratio_too_long 3) |
| Transport error HTTP 402 (insufficient credits), to retry | 489 |
| Not yet attempted | 23,555 |
| Skipped, listed in `..._skipped.jsonl` | 6 (5 sources with fewer than 3 Arabic letters, 1 source of 43,117 characters with a sentence over 5,500) |
| Fell back from the terminology to the base prompt | 269 rows (accepted: 4,699 terminology, 2,321 base) |
| Split at sentence boundaries | 7 rows |

Cost and tokens (provider `usage.cost`): run 2 journal 0.26817 USD and 1,657,921 tokens (1,084,178 prompt, 573,743 completion); three pilots 0.01711 USD and 98,019 tokens; this lane 0.28528 USD and 1,755,940 tokens. Cap 20 USD, never approached (cumulative with the first run: 0.40369 USD). Projected total for all 31,090 reports about 1.2 USD.

## Reading of 58 outputs

Stratified random draw from the 7,020 accepted run-2 outputs (seed 7): Musnad Ahmad 14, Shafi'i 8, Muwatta' 6, Darimi 8, Ibadi 8, Zaydi 8, Sahifat al-Rida 8, each spread over short (under 150 characters), middle and long (600 or more). One reader (this lane's agent) compared each with its Arabic. **7 of 58 (12 percent) had a meaning-level error: about 1 in 8, in line with the first pilot's 1 in 7.** Four of the seven read a common noun as a proper name:

- `pure-canon:pc_23210` (Ahmad, 43 characters): the imperative "aslim" (accept Islam) rendered as the name "Aslam".
- `pure-canon:pc_16560` (Ahmad): "al-fatima" (the one who weans) rendered as "Fatima".
- `pure-canon:pc_2312` (Shafi'i): "a'bud" (his slaves) rendered as a person, "ʿAbud".
- `pure-canon:pc_18348` (Ahmad): "al-ʿaraq" (sweat) rendered as a place, "the Arq".
- `openiti:imami:rida_0019` (Sahifat al-Rida): "adhdhana fi udhn" (called the adhan in the ear) rendered as "gave permission".
- `openiti:ibadi:rabi_0203` (Ibadi): "wa hiya khalatuhu" (his maternal aunt) rendered "paternal aunt".
- `pure-canon:pc_10613` (Muwatta', 34 characters): "idha massa al-khitan al-khitan" (the two circumcised parts meet) rendered as one male touching another.

Minor or stylistic, not counted: the subject shifted from "I asked" to "He asked" (`pc_23095`); a bare "And (peace and blessings be upon him) said" where the Arabic omits the Prophet's name (Ibadi `rabi_0777`, `rabi_0767`); "then all is well" supplied where the Arabic leaves the apodosis out (`pc_11823`); a literal "the sky seized them" for rain overtaking; name spellings still vary outside the term list (ʿAbdullah Ibn ʿAbbas, Ibn Abbas, Sa'd, Ya'la). Rows that fell back to the base prompt lose the ʿ scheme. Short chainless sentences and sources whose common nouns look like names are the weak spot, as in the first pilot. The other 51 had no error I could find; that is not a verification.

## Review first, and the 200-row worksheet

`review_first_PARTIAL_2026-11-21.csv`: 1,606 of the 7,020 run-2 outputs scored 3 or more on weighted flags (screen error 5; length-ratio outlier 3; numbers differ 3; honorific mismatch 2.5; very short source under 40 letters 2; negation possibly dropped 2; low length ratio 2; rare name spelling 2; very long source 1.5; short chainless 1; `translate_gap_fill.py flags`). Tier A (score 4.5 or more) is 107 rows; start there. Evidence the ranking helps, from the 58-row reading: 10 of 58 were flagged and 3 of the 7 errors were among them (30 percent of flagged rows against 8 percent of unflagged rows had an error). Untranslated Arabic cannot occur in an accepted row (any Arabic script is a screen failure). It is a ranking aid, not a measurement.

`review_worksheet_200_PARTIAL_2026-11-21.csv`: 200 stratified random run-2 outputs (proportional to each work, at least 4 per work, a third drawn from texts over 600 characters) with the Arabic and blank judgement fields (meaning correct y/n/partial, error type, severity, notes, reviewer, date). **It was drawn from the partial set; regenerate it after the run completes** (`sample`, seed 20261121) so it covers all of Musnad Ahmad, Darimi, Shafi'i and Muwatta'.

## Files

| File | Rows |
| --- | ---: |
| `machine_translation_candidates/openrouter_hy_mt2_30b_a3b_gapfill_terminology_v2_2026-11-21.jsonl` (journal) | 7,535 events |
| `machine_translation_candidates/..._gapfill_terminology_v2_2026-11-21_skipped.jsonl` | 6 |
| `machine_translation_candidates/..._gapfill_load_ready_2026-11-21.jsonl` (earlier accepted 2,141 + run 2 accepted 7,020) | 9,161 |
| `pilot_v1_base.jsonl`, `pilot_v2_draft1_terminology.jsonl`, `pilot_v2_terminology.jsonl` | 60, 60, 58 |
| `pilot_comparison.json`, `run_summary.json`, `gap_before.json`, `gap_before_manifest.csv.gz` | |
| `review_first_PARTIAL_2026-11-21.csv` | 1,606 |
| `review_worksheet_200_PARTIAL_2026-11-21.csv` | 200 |

Journal events carry: record id, Arabic SHA-256, `text_en`, `translation_source` (`hy-mt2-openrouter-v1`), `translation_model` (`tencent/hy-mt2-30b-a3b`), `prompt_version`, `terminology_terms_sent`, `translation_review_status: machine_unreviewed`, `candidate_only`, `validation_status` and `validation_errors` (the QA result), `model_cost_usd`, `model_usage`, `created_at` (the timestamp passed on the command line), split offsets, response ids and finish reasons.

## Blocked: OpenRouter credits

At about 7,000 reports every call began to return HTTP 402 ("Insufficient credits", `limit_source: openrouter_credits`). `GET /api/v1/credits` showed total credits 484 and usage 484.21; the key's own limit showed 47.97 USD remaining, so the account balance, not the key, is empty (this lane spent 0.29 USD of it; other work on the account may have used the rest). The process was stopped, the 489 failed calls are recorded as `http_402` events, and no other key or provider was tried. **The owner needs to add credit (about 1.5 USD covers the rest), then resume:**

```
cd datasets/hadith-data/diagnostics/translation-run-2
python translate_gap_fill.py snapshot --output <scratch>/gap_prod.csv          # read-only SELECT on production
python translate_gap_fill.py run --snapshot <scratch>/gap_prod.csv --timestamp <UTC ISO> --run-label gapfill-run-2 \
  --output ../../machine_translation_candidates/openrouter_hy_mt2_30b_a3b_gapfill_terminology_v2_2026-11-21.jsonl --concurrency 16
# redo the 18 rows whose Zaydi sigla now have entries (new label, same journal; the later event wins)
python translate_gap_fill.py run <same arguments> --run-label gapfill-run-2-sigla-redo --redo-term '" ع م "' --redo-term '" ص "' --redo-term '(ص)' --redo-term '(ع)'
python translate_gap_fill.py finalize --snapshot <csv> --journal <journal> --output ../../machine_translation_candidates/openrouter_hy_mt2_30b_a3b_gapfill_load_ready_2026-11-21.jsonl
python translate_gap_fill.py summary  --snapshot <csv> --journal <journal> --public-totals <file> --output run_summary.json --timestamp <ISO>
python translate_gap_fill.py flags    --snapshot <csv> --ready <load_ready> --output review_first_2026-11-21.csv
python translate_gap_fill.py sample   --snapshot <csv> --ready <load_ready> --output review_worksheet_200_2026-11-21.csv
```

`--public-totals` is a text file of `tradition|work|count` lines (`PUBLIC_TOTALS_QUERY` in the script). The run is resumable and idempotent: finished reports are skipped by record id and Arabic hash, and `--retry-rejected` re-sends screen failures. `model_registry.json` and `docs/models.md` state the partial counts; update them from `run_summary.json` after the resume.

## Load specification (for the schema owner; this lane edits nothing under `src/`, `drizzle/`, the projection or the loader)

Goal: public pages show "Unreviewed machine translation (tencent/hy-mt2-30b-a3b)" for these reports under the existing per-work English policy.

**What already works.** `collection_rights.english_policy = source_provided_and_machine_allowed` is set on all 34 works (production, 2026-11-21). `public_translations` (`drizzle/core/0009`) admits `state = machine_unreviewed` under that policy when `quality_status = complete` and `arabic_sha256` equals the report's. `englishLabel` and `englishReference` in `src/lib/sources/report-credit.ts` print "Unreviewed machine translation (<model>)" and a "Machine translation (<model>), not reviewed" credit when `state = machine_unreviewed` and `model` is set. So the load only has to write correct `translations` rows.

**Input.** `machine_translation_candidates/openrouter_hy_mt2_30b_a3b_gapfill_load_ready_2026-11-21.jsonl` (regenerate with `finalize` after the resume), one row per report. Bind by `record_id` plus `arabic_sha256`; drop and count any row whose hash differs from the loaded `hadiths.arabic_sha256`.

**Row to write** (`translations`):

| Column | Value |
| --- | --- |
| `id` | `translation:<record_id>:en` (existing convention, for example `translation:k6:22047:en`) |
| `hadith_id` | `hadith:<record_id>` |
| `language` | `en` |
| `text` | candidate `text_en`, as is |
| `state` | `machine_unreviewed` |
| `quality_status` | `complete` |
| `review_state_raw` | `machine_unreviewed` |
| `source` | candidate `translation_source` (`hy-mt2-openrouter-v1`) |
| `model` | candidate `translation_model` (`tencent/hy-mt2-30b-a3b`) |
| `translator` | NULL |
| `provenance_source` | `machine_translation_candidates/<origin_journal>:<prompt_version>` |
| `source_record_id` | the report's own `source_record_id` |
| `arabic_sha256` | candidate `arabic_sha256` |
| bookkeeping | the loading dataset version in `first_seen_` and `changed_in_dataset_version_id` |

**Precedence when both a source-provided and a machine version exist (source first).**
1. A report that already has a complete, hash-bound `human_verified`, `source_verified` or `source_provided` row keeps it; no machine row. By construction none of the 43,914 gap reports has one, but the loader must enforce it so a later source recovery is never overwritten.
2. A report whose existing row fails QA and has a mechanical glyph candidate (10,662 reports) gets that candidate as `state = source_provided`, `quality_status = complete`, `source` and `translator` unchanged, `review_state_raw = mechanical_substitution`, no `model`. It is the source's English with honorific ligatures replaced; credit stays with the source.
3. Otherwise the machine candidate above.

**Insert or update.** `translations` is unique on `(hadith_id, language)`, retired rows included, so a report that already has a failing row (728 of the 9,161 load-ready rows) must be UPDATED in place, not inserted beside it: replace `text`, `state`, `quality_status`, `source`, `model`, `review_state_raw`, `provenance_source`, set `changed_in_dataset_version_id`, and keep the replaced text's hash and `quality_status` in the audit table so nothing is lost. The alternative is an additive migration that makes the unique index partial (`WHERE retired_at IS NULL`) and retires the failing row. The other 8,433 rows are plain inserts. One transaction per load, as the loader already does.

**Check to change.** `src/db/load/verify-data.ts` check "no candidate-only rows in canonical tables" counts every `translations` row with `state = machine_unreviewed`, so it fails on this load. Narrow it to `machine_unreviewed` rows without a `model`, or whose work's policy does not allow machine English. The `public_translations` check in the same file already accepts the new state. `pg_export/export_postgres.py` routes `machine_unreviewed` English to `candidates/translation_candidates.csv`, which the loader does not read: either extend the projection to read the load-ready file, or add a small overlay load that reads it directly; no re-export of the master is needed.

**Related defects seen.** Five public reports have no Arabic letters in `text_ar` (`pure-canon:pc_68632`, `pc_71292`, `pc_71297`, `thaqalayn:6f1d2a5882cc525cd9cf62e4`, `thaqalayn:c0fe57e835501d8060b566b1`); they cannot be translated and should be `quality_excluded`. Sixteen reports (the 15 earlier plus `thaqalayn:940c80ddfe49bbf0ff76b712`) have one sentence over 5,500 characters and stay without English until split by hand.

**Counts (current load-ready file; partial, the final counts follow the resume).** Machine candidates by tradition and work:

| Tradition | Work | Rows | Insert | Update |
| --- | --- | ---: | ---: | ---: |
| Ibadi | al-Jami al-Sahih (Musnad al-Rabi ibn Habib) | 1,001 | 1,001 | 0 |
| Imami | Al-Amali (Saduq) | 1 | 0 | 1 |
| Imami | Al-Kafi | 46 | 0 | 46 |
| Imami | Al-Khisal | 1 | 0 | 1 |
| Imami | Kamal al-Din | 20 | 0 | 20 |
| Imami | Kitab al-Du'afa | 90 | 0 | 90 |
| Imami | Kitab al-Ghayba (Nu'mani) | 1 | 0 | 1 |
| Imami | Ma'ani al-Akhbar | 3 | 0 | 3 |
| Imami | Man La Yahduruhu al-Faqih | 35 | 0 | 35 |
| Imami | Mu'jam al-Ahadith al-Mu'tabara | 525 | 0 | 525 |
| Imami | Sahifat al-Imam Ali al-Rida | 34 | 34 | 0 |
| Imami | Thawab al-A'mal | 1 | 0 | 1 |
| Sunni | Jami' al-Tirmidhi | 187 | 186 | 1 |
| Sunni | Musnad Ahmad | 4,508 | 4,508 | 0 |
| Sunni | Musnad al-Shafi'i | 804 | 804 | 0 |
| Sunni | Muwatta' Malik | 189 | 189 | 0 |
| Sunni | Sahih Bukhari | 177 | 177 | 0 |
| Sunni | Sahih Muslim | 354 | 354 | 0 |
| Sunni | Sunan Ibn Majah | 132 | 128 | 4 |
| Sunni | Sunan al-Darimi | 354 | 354 | 0 |
| Sunni | Sunan an-Nasa'i | 8 | 8 | 0 |
| Zaydi | Musnad al-Imam Zayd ibn Ali | 690 | 690 | 0 |
| | **All** | **9,161** | **8,433** | **728** |

Mechanical glyph rows (source English, no model): Sunan Abi Da'ud 4,155, Sunan Ibn Majah 2,980, Sunan an-Nasa'i 1,848, Jami' al-Tirmidhi 1,666, Imami 9, Zaydi 3, Musnad Ahmad 1: 10,662 in all.
