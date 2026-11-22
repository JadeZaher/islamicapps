<!-- Generated from datasets/hadith-data/model_registry.json by datasets/hadith-data/render_model_docs.py. Do not edit. -->

# Models used in this project

Which model did which work in this project. One entry per (model, kind of work). Built from recorded evidence only; docs/models.md is generated from this file by render_model_docs.py.

As of 2026-11-22. Source of truth: `datasets/hadith-data/model_registry.json` (schema `model_registry.schema.json`).

## Pinned translator

Arabic to English machine translation uses `tencent/hy-mt2-30b-a3b` on openrouter, pinned by the owner on 2026-11-21.
Configuration: `datasets/hadith-data/translation_model.json` (prompt `hy-mt2-default-en-prompt-v1`, temperature 0.7, context 8,192 tokens, completion limit 4,096, QA screen `screen-v2`).
Changing this file is a reviewed edit: update model_registry.json and regenerate docs/models.md in the same change.

What its output may and may not be used for:

- May: Candidate text for a curator to review against the Arabic and the source edition.
- May: Public display only for a report with no source-provided English, labelled 'Unreviewed machine translation' with this model id and credited to SWI (public_translations, migration 0018); source-provided English is always shown instead where it exists.
- May not: Writing to canonical CSV/GZIP, translation_overrides.jsonl or any release input without a hash-bound human review (release accepts only human_verified or source_verified).
- May not: Presenting the mechanical screen as evidence that the translation is faithful: it checks shape (refusal, Arabic leakage, Latin ratio, loops, truncation), not meaning.
- May not: Publishing as reviewed English, or attributing the wording to any scholar or source.
- Review state: machine_unreviewed; no human review of any hy-mt2 output is recorded. Published under the label 'Unreviewed machine translation (tencent/hy-mt2-30b-a3b)' for reports with no source English, state machine_unreviewed in translations (0018). 33,307 reports carry a draft (2,025 from the first run under prompt v1, 31,282 from gap-fill run 2: 20,056 terminology prompt, 11,226 base prompt after fallback or no matching term); 113 reports stay without English (91 failed the screen twice, 22 not translatable: sources with no Arabic letters or a sentence over 5,500 characters). Spend: US$0.40369 up to 2026-11-21 and US$0.7767 on 2026-11-22 (journal usage.cost; 4,876,971 tokens that day), about US$1.18 and 7.36 million tokens in all. Reading of 40 random outputs on 2026-11-22 (10 per tradition, one reader): 5 with a meaning-level error (see quality_findings).

## Summary

| Model as recorded | Kind | Work | Output | Status | Identity |
| --- | --- | --- | --- | --- | --- |
| `tencent/hy-mt2-30b-a3b` **pinned** | translation | Arabic to English candidate translations for master rows whose English fails release QA: missing, placeholder, same as Arabic, too short, fully or partly Arabic, and names-or-terms-only leakage | 60 journal events (+11 more outputs) | candidate_only | namespaced_specific |
| `google/gemini-2.5-flash` | translation | Arabic to English candidate translations for the 12,833 translation-eligible backlog rows, run as pilots (prompt identities v2 to r6), a bounded r7 prefix run and an r8 suffix run | 14 journal events (+3 more outputs) | candidate_only | namespaced_specific |
| `google/gemma-4-e4b` | translation | Arabic to English translation of the OpenITI-sourced Ibadi (Jami' al-Sahih of al-Rabi'), Zaydi (Musnad Zayd) and Sahifat al-Rida appendix reports, with a self-reported 1 to 4 confidence per row | 1,733 master rows with translation_model google/gemma-4-e4b: Ibadi 1,004, Zaydi 694, Sahifat al-Rida appendix 35 (+1 more outputs) | canonical | namespaced_specific |
| `google/gemma-4-e4b` | translation | Candidate English for K6 rows with missing English (translation:missing); one historical pilot row and 20 rows from a two-worker bounded run | 21 journal events | candidate_only | namespaced_specific |
| `manual:claude-opus-4.7` | translation | Arabic to English translation of four Zaydi reports (zayd_0045, zayd_0136, zayd_0255, zayd_0348) recorded in the Zaydi translation journal alongside the Gemma rows | 4 master rows with translation_model manual:claude-opus-4.7 | canonical | namespaced_specific |
| `llama3.1:8b` | translation | Arabic to English translation runs in April 2026: Pure Canon classical rows (54,957 rows, 54,952 translated, 5 failed), a Pure Canon run of 100,217 rows that was terminated, and the Zaydi OCR translation script | 54,957 rows processed per the log (+1 more outputs) | undetermined | insufficiently_specific |
| (none recorded) | translation | Arabic to English translation of the six classical Sunni collections (Bukhari, Muslim, Tirmidhi, Abu Dawud, Nasa'i, Ibn Majah) and related Pure Canon rows, with a refusal and failure re-translation pass | 29,915 master rows with an empty translation_model (+1 more outputs) | canonical | not_recorded |
| (none recorded) | translation | 19 historical OpenITI translation-backup candidates (15 Zaydi, 4 Ibadi) audited and rejected | 19 rejected backup candidates | rejected | not_recorded |
| `gemma-3-27b-it` | arabic_text_cleanup | LLM purification of OCR-corrupted Zaydi Arabic with a 1 to 4 confidence score | 23 lines (+1 more outputs) | superseded | insufficiently_specific |
| `gemma3:12b` | ocr_parsing | LLM-assisted parsing of OCR text of the Ibadi Musnad into hadith records (tool calling), and a translation script defaulting to the same model | not counted | superseded | insufficiently_specific |
| `Claude Fable 5.2` | coding_assistance | Co-authored application code (src/app, src/db, src/lib, src/components, src/scripts), data pipeline code and diagnostics (datasets/hadith-data), and documentation and planning files (docs, conductor, .omc) in 18 commits reachable from HEAD | 18 commits | not_applicable | namespaced_specific |
| `Claude Opus 4.7 (1M context)` | coding_assistance | Co-authored application code (src/app, src/lib, src/scripts), data pipeline code (datasets/hadith-data, datasets/archive) and track documentation (conductor, .omc) in 6 commits | 6 commits | not_applicable | namespaced_specific |
| `Claude Opus 4.6 (1M context)` | coding_assistance | Co-authored data pipeline code (datasets/hadith-data, datasets), application code (src/app, src/lib, src/components, src/scripts) and track documentation (conductor, .omc) in 2 commits | 2 commits | not_applicable | namespaced_specific |
| `qwen/qwen3.7-flash` | extraction_audit | Scored each of the 1,901 corrected OpenITI reports in production (Musnad al-Rabi 1,005, Musnad Zayd 691, Sahifat al-Rida 205) against a window of the OpenITI source, 0 to 3 for boundaries, cleanliness and sanad/matn split, with flags and verbatim-substring proposals | 1,014 verdict events (+3 more outputs) | candidate_only | namespaced_specific |
| `claude-haiku-5-5` | chain_reading | Chain reading (chain-fix submissions): read each report's Arabic and wrote its routes name by name, for the chain-fix pipeline (docs/review/chain-fix-pipeline.md) | 568 reader outputs (+4 more outputs) | applied_awaiting_final_review | namespaced_specific |
| `claude-opus-5-5` | chain_review | AI first pass of final review of model-read chains (chain-reader/reviewer, prompt 1.1.0 sha256 1136aec2c975aebd0f4b8f17cf14d6ad1410229c33b97e7d8382b8258cb735f6): reads the Arabic against both readers' readings and the tool's holds and confirms, corrects, prefers a reader, keeps the stored chain or refers to a person | 81 reviews | ai_reviewed_awaiting_human_review | namespaced_specific |

Row counts for canonical data come from the full-schema master datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz (99,283 rows, streamed; fields translation_source, translation_model, translation_review_status, translation_status). The tracked all_hadiths_unified.csv.gz has the legacy 26-column schema and carries no model fields.

## Entries

### tencent/hy-mt2-30b-a3b: translation (`hy-mt2-30b-a3b-translation`)

- Runtime: OpenRouter API (provider policy data_collection deny, allow_fallbacks false)
- Work: Arabic to English candidate translations for master rows whose English fails release QA: missing, placeholder, same as Arabic, too short, fully or partly Arabic, and names-or-terms-only leakage. Arabic only is sent; no existing English is shown to the model. Gap-fill run 2 (2026-11-21, 2026-11-22; diagnostics/translation-run-2/): the same model, with a per-request terminology block (prompt hy-mt2-terminology-en-prompt-v2, sha256 03da4f8769e0...dfc5c9, translation_model.json prompt_terminology; fallback prompt hy-mt2-default-en-prompt-v1, sha256 bfe84676c7ff...df8ed4af) over public reports with no public English. 7,046 reports were translated on 2026-11-21 before the OpenRouter account ran out of credits (HTTP 402); on 2026-11-22 the account was topped up and the run resumed: the three corrected OpenITI works first (al-Rabi, Musnad Zayd, Sahifat al-Rida, from their current text), then every other report still without public English. 33,307 of the 33,420 reports without public English now have a gated draft; the drafts are published (migration 0018) as 'Unreviewed machine translation (tencent/hy-mt2-30b-a3b)' credited to SWI.
- Dates: 2026-11-21 to 2026-11-22 (created_at in the journals (one operator-supplied timestamp per run label))
- Identity: namespaced_specific. Per event the journals record the response model: tencent/hy-mt2-30b-a3b on every one of the 25,097 responses of 2026-11-22 (provider Tencent, through OpenRouter) and on all 61 pilot chunks; the 2026-11-21 gap-fill rows carry the model but no provider.
- Status: candidate_only. machine_unreviewed; no human review of any hy-mt2 output is recorded. Published under the label 'Unreviewed machine translation (tencent/hy-mt2-30b-a3b)' for reports with no source English, state machine_unreviewed in translations (0018). 33,307 reports carry a draft (2,025 from the first run under prompt v1, 31,282 from gap-fill run 2: 20,056 terminology prompt, 11,226 base prompt after fallback or no matching term); 113 reports stay without English (91 failed the screen twice, 22 not translatable: sources with no Arabic letters or a sentence over 5,500 characters). Spend: US$0.40369 up to 2026-11-21 and US$0.7767 on 2026-11-22 (journal usage.cost; 4,876,971 tokens that day), about US$1.18 and 7.36 million tokens in all. Reading of 40 random outputs on 2026-11-22 (10 per tradition, one reader): 5 with a meaning-level error (see quality_findings).
- Inputs:
  - `datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz (text_ar of flagged rows)`
  - `production database, read-only SELECT of public reports with no complete public English (43,914 reports; Arabic text and its SHA-256), 2026-11-21; snapshot regenerated by translate_gap_fill.py snapshot`
  - `production database, read-only SELECT of public reports with no public English (33,420 reports, 4,653,191 Arabic characters to translate), 2026-11-22; only the public Arabic text and the translation instruction were sent to the API`
- Outputs:
  - `datasets/hadith-data/machine_translation_candidates/openrouter_hy_mt2_30b_a3b_pilot_2026-11-21.jsonl`: 60 journal events; stratified pilot; original screen: 51 accepted, 9 rejected (all repetition_loop, shown to be false positives)
  - `datasets/hadith-data/machine_translation_candidates/openrouter_hy_mt2_30b_a3b_pilot_2026-11-21_rescreened_screen_v2.jsonl`: 60 journal events; same model outputs re-screened with screen-v2: 59 accepted, 1 rejected; derived copy, original untouched
  - `datasets/hadith-data/machine_translation_candidates/openrouter_hy_mt2_30b_a3b_batch_no_usable_english_2026-11-21.jsonl`: 1,211 journal events; 1,210 accepted, 1 rejected (length_ratio_too_long)
  - `datasets/hadith-data/machine_translation_candidates/openrouter_hy_mt2_30b_a3b_batch_names_terms_2026-11-21.jsonl`: 874 journal events; 872 accepted, 2 rejected (length_ratio_too_short, repetition_loop)
  - `datasets/hadith-data/machine_translation_candidates/openrouter_hy_mt2_30b_a3b_batch_no_usable_english_2026-11-21_skipped.jsonl`: 4 rows never sent; a single sentence over 5,500 characters; no defensible split
  - `datasets/hadith-data/machine_translation_candidates/openrouter_hy_mt2_30b_a3b_batch_names_terms_2026-11-21_skipped.jsonl`: 11 rows never sent; same reason
  - `datasets/hadith-data/machine_translation_candidates/openrouter_hy_mt2_30b_a3b_gapfill_terminology_v2_2026-11-21_skipped.jsonl`: 6 rows never sent; five sources with fewer than three Arabic letters (for example a single letter or a row of asterisks) and one 43,117-character source with a sentence over 5,500 characters
  - `datasets/hadith-data/machine_translation_candidates/openrouter_hy_mt2_30b_a3b_gapfill_load_ready_2026-11-21.jsonl`: 9,161 load-ready candidates; superseded by machine_english_overlay.jsonl.gz (earlier partial load-ready file, 9,161 rows, kept as evidence)
  - `datasets/hadith-data/diagnostics/translation-run-2/pilot_v1_base.jsonl`: 60 journal events; 60-row paired pilot, base prompt
  - `datasets/hadith-data/diagnostics/translation-run-2/pilot_v2_terminology.jsonl`: 58 journal events; same rows, terminology prompt revision 2 (two non-linguistic sources skipped); pilot_v2_draft1_terminology.jsonl holds the 60 draft-1 events
  - `datasets/hadith-data/machine_translation_candidates/openrouter_hy_mt2_30b_a3b_gapfill_terminology_v2_2026-11-21.jsonl`: 32,629 journal events; gap-fill journal: 7,535 events of 2026-11-21 plus 25,094 of 2026-11-22 (24,900 accepted, 194 rejected by screen-v2 and the two guards); the 489 earlier HTTP 402 events were retried and superseded
  - `datasets/hadith-data/machine_translation_candidates/machine_english_overlay.jsonl.gz`: 33,307 published drafts; one gated draft per report, bound to the exact Arabic by arabic_sha256, each with response model, provider (where recorded), prompt version and sha256, finish reasons, QA result, cost and timestamp; the exporter re-gates every row and binds the file by SHA-256 in the projection manifest
- May be used for:
  - Candidate text for a curator to review against the Arabic and the source edition.
  - Public display only for a report with no source-provided English, labelled 'Unreviewed machine translation' with this model id and credited to SWI (public_translations, migration 0018); source-provided English is always shown instead where it exists.
- May not be used for:
  - Writing to canonical CSV/GZIP, translation_overrides.jsonl or any release input without a hash-bound human review (release accepts only human_verified or source_verified).
  - Presenting the mechanical screen as evidence that the translation is faithful: it checks shape (refusal, Arabic leakage, Latin ratio, loops, truncation), not meaning.
  - Publishing as reviewed English, or attributing the wording to any scholar or source.
- Quality findings:
  - The pilot's first screen rejected 9 of 60 outputs as repetition loops; all 9 were false positives (repeated honorific phrases, sources that repeat themselves). screen-v2 rejects 1 of 60. (source: datasets/hadith-data/diagnostics/translation-run/README.md, section Method; summary.json per_file.pilot and pilot_rescreened)
  - One 5,495-character Imami row came back summarised (Latin/Arabic letter ratio 0.72); the ratio floor was raised from 0.5 to 1.0. (source: datasets/hadith-data/diagnostics/translation-run/README.md, section Method)
  - No reviewer-measured meaning-error rate for hy-mt2 output exists in the repository as of 2026-11-21. The only measured rates are mechanical screen outcomes (pilot 1 of 60 rejected under screen-v2; batches 1 of 1,211 and 2 of 874) and say nothing about meaning. (source: searched datasets/hadith-data/DATA_QUALITY_REPORT.md, diagnostics/translation-run/README.md and summary.json, machine_translation_candidates/README.md, .omc/research on 2026-11-21)
  - 15 rows were never sent because one sentence exceeds 5,500 characters; 11 flagged master rows remain uncovered. (source: datasets/hadith-data/diagnostics/translation-run/summary.json, coverage_of_master_problem_rows and uncovered_record_ids)
  - Gap-fill run 2 reading of 58 outputs stratified by tradition, work and length: 7 had a meaning-level error (12 percent); four of the seven read a common noun as a proper name (the imperative 'aslim' as the name Aslam, 'al-fatima' (the weaner) as Fatima, 'a'bud' (slaves) as ʿAbud, 'al-ʿaraq' (sweat) as the place Arq), others were 'adhdhana' (call to prayer) read as 'gave permission', 'khalatuhu' (maternal aunt) as paternal aunt, and 'al-khitan' read as two males. Short chainless texts and sources with ambiguous common nouns are the weak spot, as in the first pilot. (source: datasets/hadith-data/diagnostics/translation-run-2/README.md, section Reading of 58 outputs)
  - The terminology prompt (60-row paired pilot, 58 compared) put the honorific in one parenthetical form 137 times against 56, used the glossary's ʿ scheme 64 times against 0, and 'God' 1 time against 4, with no worse meaning in a 36-pair reading; it also produced 'O the Messenger of Allah' in 7 draft-1 outputs (fixed by vocative entries) and occasional macron transliteration (guarded; the row is retried with the base prompt), and renders a bare honorific with no subject ('And (peace and blessings be upon him) said') where the Arabic omits the Prophet's name. (source: datasets/hadith-data/diagnostics/translation-run-2/pilot_comparison.json and README.md)
  - At temperature 0.7 the same prompt gave different meanings on the same source in two runs (a dropped 'not' on pc_73910), so a single sample is partly noise. (source: datasets/hadith-data/diagnostics/translation-run-2/pilot_comparison.json)
  - Run 2 stopped at 7,046 of 31,090 selected reports because the OpenRouter account balance reached zero (HTTP 402 'Insufficient credits', limit_source openrouter_credits); the key's own limit had 47.97 USD remaining. About 24,000 reports remain; the estimated remaining cost is about 1.3 USD. (source: datasets/hadith-data/diagnostics/translation-run-2/README.md, section Blocked)
  - 2026-11-22 reading of 40 random published drafts (10 each from Sunni, Imami, Zaydi, Ibadi; one reader against the Arabic): 5 had a meaning-level error: Sunni 3 (pc_47927 'give the beggar' rendered 'They rejected the liquid'; pc_631 'harvest your palm' rendered 'Come out, my grandfather ... you will believe'; pc_15571 speaker confusion), Zaydi 2 (jubar rendered 'tyrant'; 'ta'rif' rendered 'knows'), Imami 1 partial (garbled gloss), Ibadi 0. No dropped isnad and no invented text was seen. One reader's reading, not a reviewed measurement. (source: conductor/RUNBOOK.md, Machine translation publish)
  - The screen held 194 of 25,094 events of 2026-11-22 (0.8 percent): diacritic transliteration 53 first, repetition loop 23, length ratio 21, truncation 1, Arabic leakage 1; after one retry 91 reports remain held out and are never shown. (source: datasets/hadith-data/machine_translation_candidates/openrouter_hy_mt2_30b_a3b_gapfill_terminology_v2_2026-11-21.jsonl)
- Evidence:
  - `datasets/hadith-data/diagnostics/translation-run/summary.json`: per_file, total_model_cost_usd, coverage_of_master_problem_rows
  - `datasets/hadith-data/diagnostics/translation-run/README.md`: Files table, Method, Spend
  - `datasets/hadith-data/machine_translation_candidates/openrouter_hy_mt2_30b_a3b_pilot_2026-11-21.jsonl`: fields translation_model, translation_source, validation_status, chunk_results[].response_model (streamed and counted)
  - `conductor/RUNBOOK.md`: Owner decisions, third round (2026-11-21): translation model pinned
  - `.omc/research/hy-mt2-modelcard-2026-11-21.md`: Hy-MT2 Translation Task Instruction Examples; Inference and Deployment (30B-A3B parameters)
  - `datasets/hadith-data/diagnostics/translation-run-2/run_summary.json`: per_work (gap before and after by tradition and work), batch
  - `datasets/hadith-data/diagnostics/translation-run-2/README.md`: Gap, Pilot, Batch, Reading of 58 outputs, Load specification, Blocked
  - `datasets/hadith-data/translation_model.json`: prompt_terminology (the new prompt version and its 94 terms)
- Notes: Pinned by the owner on 2026-11-21; configuration in translation_model.json. Pipeline generate_hy_mt2_candidates.py; gap-fill runner diagnostics/translation-run-2/translate_gap_fill.py. The pin's prompt gained a second version, hy-mt2-terminology-en-prompt-v2 (a per-request list of glossary names and formulas, model-card Terminology format); the base prompt hy-mt2-default-en-prompt-v1 stays in 'prompt' and is the fallback. docs/models.md names only the base prompt in its pin line because render_model_docs.py reads 'prompt'. Model is unchanged.

### google/gemini-2.5-flash: translation (`gemini-2-5-flash-openrouter-translation`)

- Runtime: OpenRouter API, structured output, reasoning effort none, data_collection deny
- Work: Arabic to English candidate translations for the 12,833 translation-eligible backlog rows, run as pilots (prompt identities v2 to r6), a bounded r7 prefix run and an r8 suffix run.
- Dates: 2026-07-22 to 2026-07-23 (created_at of the first (2026-07-22T03:46:19Z) and last (2026-07-23T01:22:45Z) journal events)
- Identity: namespaced_specific. Journal events record the requested model on every event and the response model on every event that received a response (the OpenRouter client rejects a mismatch).
- Status: candidate_only. machine_unreviewed. 5,795 journal events across all Gemini journals (5,123 accepted by the mechanical screen), spend 5.061573 USD. Only the 14-row pilot, the r7 prefix sample and the r8 regression pilot received independent content review; the r8 suffix run was paused after two confirmed defects and is incomplete (4,142 of 11,310 selected rows). Superseded as the default translator by the 2026-11-21 pin.
- Inputs:
  - `datasets/hadith-data/development/incomplete-curation/curation_backlog.incomplete.csv`
  - `datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz`
- Outputs:
  - `datasets/hadith-data/machine_translation_candidates/openrouter_gemini_2_5_flash_pilot_2026-07-22.jsonl`: 14 journal events; first 14-row pilot (prompt v2); 13 accepted, 1 rejected; superseded by later prompt identities. Pilots v3, v3r3, v4, v5, v6 (6, 6, 1, 6, 6 events) are likewise superseded.
  - `datasets/hadith-data/machine_translation_candidates/openrouter_gemini_2_5_flash_v7_full_resilient3_2026-07-22.jsonl`: 1,517 journal events; r7 prefix to k6:16257: 1,439 accepted, 70 arabic_leakage, 8 model_reported_uncertainty. With the three r7 predecessor journals (91, 1, 1 events) the r7 total is 1,610 events, 1,530 accepted.
  - `datasets/hadith-data/machine_translation_candidates/openrouter_gemini_2_5_flash_v8_semantic_pilot_2026-07-22.jsonl`: 4 journal events; r8 four-row regression pilot, all accepted
  - `datasets/hadith-data/machine_translation_candidates/openrouter_gemini_2_5_flash_v8_suffix_2026-07-22.jsonl`: 4,142 journal events; r8 suffix: 3,564 accepted, 560 arabic_leakage, 18 model_reported_uncertainty; quality-paused
- May be used for:
  - Reproducing or auditing the July 2026 runs (requires --allow-unpinned-model).
  - Comparison candidate text for a curator, labelled unreviewed machine translation with this model id.
- May not be used for:
  - Canonical or release use without hash-bound human review.
  - Continuing the paused r8 run or starting new translation with this model.
- Quality findings:
  - Independent review of the 13 accepted pilot rows: 8 pass, 4 concern, 1 fail. The failure silently omitted a full warning passage from a 30,498-character Al-Kafi row; the model returned stop and declared no uncertainty. (source: datasets/hadith-data/machine_translation_candidates/OPENROUTER_PILOT_REPORT.md, section Independent content review; DATA_QUALITY_REPORT.md line 181)
  - Review of the r7 prefix found four contextual errors (k6:16093 observer and actor reversed, k6:16103 the Arabic al-itq read as freed slaves, k6:7471 a lawful/unlawful contrast flattened, k6:12234 invented running), leading to the r8 guards. (source: datasets/hadith-data/DATA_QUALITY_REPORT.md line 227)
  - The r8 suffix run was quality-paused after k6:17921 (passive la nuriths rendered active, reversing the doctrinal relation) and k6:18013 (a question rendered as 'The best thing'). (source: datasets/hadith-data/DATA_QUALITY_REPORT.md lines 252-259)
- Evidence:
  - `datasets/hadith-data/machine_translation_candidates/openrouter_gemini_2_5_flash_v8_suffix_2026-07-22.jsonl`: fields translation_model, translation_source, validation_status, model_cost_usd, created_at (streamed and counted; 12 journals)
  - `datasets/hadith-data/DATA_QUALITY_REPORT.md`: lines 181-262
  - `datasets/hadith-data/machine_translation_candidates/README.md`: OpenRouter backend; 2026-07-22 pilot outcome
  - `.omc/research/openrouter-hadith-translation-2026-07-21.md`: decision paragraph (primary generator choice)

### google/gemma-4-e4b: translation (`gemma-4-e4b-lmstudio-openiti-translation`)

- Runtime: LM Studio, local OpenAI-compatible server, via datasets/translate_hadith.py
- Work: Arabic to English translation of the OpenITI-sourced Ibadi (Jami' al-Sahih of al-Rabi'), Zaydi (Musnad Zayd) and Sahifat al-Rida appendix reports, with a self-reported 1 to 4 confidence per row.
- Dates: 2026-05-10 to 2026-05-16 (modification times of translations.jsonl and its .bak files; the rows carry no timestamps)
- Identity: namespaced_specific. No build or quantization is recorded for these rows (the July 2026 candidate run recorded gguf:gemma4:Q4_K_M; the May run did not).
- Status: canonical. machine_unreviewed. Present in the canonical master but blocked from release by the review gate; 157 of the 1,733 rows also fail the release QA.
- Inputs:
  - `datasets/hadith-data/ibadi-hadith/parsed_hadiths.json (text_ar)`
  - `datasets/hadith-data/zaydi-hadith/parsed_hadiths.json (text_ar)`
  - `datasets/hadith-data/rida-hadith/parsed_hadiths.json (text_ar)`
- Outputs:
  - `datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz`: 1,733 master rows with translation_model google/gemma-4-e4b: Ibadi 1,004, Zaydi 694, Sahifat al-Rida appendix 35; all machine_unreviewed; 1,576 translation_status complete, 143 arabic_leakage, 13 same_as_arabic, 1 placeholder
  - `datasets/hadith-data/ibadi-hadith/translations.jsonl`: 1,162 journal lines (retries and 6 error lines included); zaydi-hadith/translations.jsonl has 1,203 lines (88 error lines, 4 manual); rida-hadith/translations.jsonl has 35
- May be used for:
  - Working text for curator review in the corpus, shown as unreviewed machine translation with this model id.
- May not be used for:
  - Publication as reviewed English; the release gate accepts only human_verified or source_verified.
- Quality findings:
  - 157 of 1,733 rows fail release QA (143 Arabic leakage, 13 same as Arabic, 1 placeholder). (source: master streamed 2026-11-21: group by translation_model and translation_status)
  - 1,733 rows identify google/gemma-4-e4b and are machine_unreviewed. (source: datasets/hadith-data/DATA_QUALITY_REPORT.md line 160)
- Evidence:
  - `datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz`: columns translation_model, translation_source, translation_review_status, translation_status, tradition
  - `datasets/hadith-data/zaydi-hadith/translations.jsonl`: field model
  - `datasets/hadith-data/DATA_QUALITY_REPORT.md`: line 160

### google/gemma-4-e4b: translation (`gemma-4-e4b-lmstudio-k6-missing-candidates`)

- Runtime: LM Studio, local server at 127.0.0.1:1234, via generate_machine_translation_candidates.py (local backend)
- Work: Candidate English for K6 rows with missing English (translation:missing); one historical pilot row and 20 rows from a two-worker bounded run.
- Dates: 2026-07-21 to 2026-07-22 (created_at in local_lmstudio_candidates.jsonl)
- Identity: namespaced_specific. 20 events record google/gemma-4-e4b with version gguf:gemma4:Q4_K_M. The first event (k6:3631) records the local alias hadith-gemma-e4b-local, which is not a namespaced model id; its model_version names the GGUF file lmstudio-community/gemma-4-E4B-it-GGUF/gemma-4-E4B-it-Q4_K_M.gguf.
- Identity flag: 1 of 21 events records the alias hadith-gemma-e4b-local instead of a namespaced model id (the pilot predating the hardened run contract).
- Status: candidate_only. machine_unreviewed; no content review recorded. The k6:3631 pilot row predates the hardened identity contract and must not be promoted.
- Inputs:
  - `datasets/hadith-data/curation_backlog.csv (translation:missing rows)`
- Outputs:
  - `datasets/hadith-data/machine_translation_candidates/local_lmstudio_candidates.jsonl`: 21 journal events; all 21 accepted by the mechanical screen; all candidate_only and machine_unreviewed
- May be used for:
  - Reproducing the local pilot (requires --allow-unpinned-model).
- May not be used for:
  - Promotion of the k6:3631 row; any use as reviewed English.
- Quality findings:
  - The k6:3631 pilot row predates run-ID, response telemetry and the explicit build-version contract and must not be promoted. (source: datasets/hadith-data/machine_translation_candidates/PILOT_REPORT.md)
- Evidence:
  - `datasets/hadith-data/machine_translation_candidates/local_lmstudio_candidates.jsonl`: fields translation_model, translation_model_version, prompt_version, created_at
  - `datasets/hadith-data/machine_translation_candidates/PILOT_REPORT.md`: whole file

### manual:claude-opus-4.7: translation (`manual-claude-opus-4-7-zaydi-translation`)

- Runtime: AI coding assistant, manual interactive use
- Work: Arabic to English translation of four Zaydi reports (zayd_0045, zayd_0136, zayd_0255, zayd_0348) recorded in the Zaydi translation journal alongside the Gemma rows.
- Dates: 2026-05-16 to 2026-05-16 (modification time of zaydi-hadith/translations.jsonl; rows carry no timestamp)
- Identity: namespaced_specific. The manual: prefix marks interactive assistant output rather than an API pipeline; the interface and date are not recorded per row.
- Status: canonical. machine_unreviewed; no human review recorded.
- Inputs:
  - `datasets/hadith-data/zaydi-hadith/parsed_hadiths.json (text_ar)`
- Outputs:
  - `datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz`: 4 master rows with translation_model manual:claude-opus-4.7; all Zaydi, machine_unreviewed, translation_status complete
- May be used for:
  - Working text for curator review, labelled unreviewed machine translation with this model id.
- May not be used for:
  - Publication as reviewed English.
- Evidence:
  - `datasets/hadith-data/zaydi-hadith/translations.jsonl`: 4 lines with field model manual:claude-opus-4.7
  - `datasets/hadith-data/DATA_QUALITY_REPORT.md`: line 161 (four rows identify manual:claude-opus-4.7)

### llama3.1:8b: translation (`llama3-1-8b-ollama-translation`)

- Runtime: Ollama, local, via datasets/translate_ollama_generic.py
- Work: Arabic to English translation runs in April 2026: Pure Canon classical rows (54,957 rows, 54,952 translated, 5 failed), a Pure Canon run of 100,217 rows that was terminated, and the Zaydi OCR translation script.
- Dates: 2026-04-14 to 2026-04-17 (modification times of the two run logs)
- Identity: insufficiently_specific. An Ollama tag: no vendor namespace, no quantization or digest, and not stored on any output row. Identity is taken from run logs and shell scripts.
- Status: undetermined. machine_unreviewed. The link between these outputs and the 29,915 classical rows in the master is not recorded.
- Inputs:
  - `datasets/hadith-data/pure_canon_classical.jsonl (named in the log; no such file exists under datasets/)`
  - `datasets/hadith-data/sheikahmad/pure_canon.jsonl (100,217 rows, named in the log)`
- Outputs:
  - `datasets/hadith-data/archive/logs/translate_classical.log`: 54,957 rows processed per the log (54,952 translated, 5 failed); the output file named in the log, pure_canon_classical_en.jsonl, is not in the working tree
  - `datasets/hadith-data/archive/sheikahmad-pure-canon/pure_canon_en.jsonl`: 3,231 lines; partial output of the terminated Pure Canon run
- May be used for:
  - Historical reference only.
- May not be used for:
  - Treating any master row as llama-translated: no row records this model.
- Evidence:
  - `datasets/hadith-data/archive/logs/translate_classical.log`: lines 1-4 (Ollama is running. Model: llama3.1:8b) and the Done line
  - `datasets/hadith-data/archive/sheikahmad-pure-canon/run_translations.sh`: MODEL=llama3.1:8b
  - `datasets/hadith-data/archive/zaydi-translation-pipeline/run_zaydi_translation.sh`: --model llama3.1:8b
  - `docs/rights/untangling-plan.md`: line 78 (The April 2026 runs used llama3.1:8b and OpenRouter models)

### model not recorded: translation (`unrecorded-openrouter-llm-classical-translation`)

- Runtime: OpenRouter API (per README); model not recorded
- Work: Arabic to English translation of the six classical Sunni collections (Bukhari, Muslim, Tirmidhi, Abu Dawud, Nasa'i, Ibn Majah) and related Pure Canon rows, with a refusal and failure re-translation pass.
- Dates: 2026-04-18 to 2026-04-19 (modification times of the classical pipeline JSONL files)
- Identity: not_recorded. The pipeline README says only 'OpenRouter LLM'. The master leaves translation_model blank for all 29,915 rows, and the journals carry no model field. The pipeline's split_translation_errors.py suggests llama3.1:8b for re-translating refusals, which is a suggestion, not a record.
- Status: canonical. machine_unreviewed. The report states these still need acquisition-log or model reconstruction, or human edition verification, before provenance is complete.
- Inputs:
  - `datasets/hadith-data/archive/classical-pipeline/classical_to_translate.jsonl`
- Outputs:
  - `datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz`: 29,915 master rows with an empty translation_model (29,888 from classical_canon_enhanced.csv, 27 from classical_translations_clean.jsonl); all machine_unreviewed
  - `datasets/hadith-data/archive/classical-pipeline/classical_translations_clean.jsonl`: 27,390 lines; other files: classical_failed_retranslated.jsonl 1,037; classical_refused_retranslated.jsonl 19; classical_collections_translated.jsonl 67,233
- May be used for:
  - Working text for curator review, labelled unreviewed machine translation with model not recorded.
- May not be used for:
  - Publication as reviewed English; any claim about which model produced these rows.
- Quality findings:
  - 29,915 classical recoveries are machine_unreviewed and retain an archive source but no model identity. (source: datasets/hadith-data/DATA_QUALITY_REPORT.md line 160)
- Evidence:
  - `datasets/hadith-data/archive/classical-pipeline/README.md`: Pipeline Steps, step 2 (Translation via OpenRouter LLM)
  - `datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz`: translation_source classical_canon_enhanced.csv and classical_translations_clean.jsonl with empty translation_model

### model not recorded: translation (`unattributed-openiti-backup-candidates-rejected`)

- Runtime: not recorded
- Work: 19 historical OpenITI translation-backup candidates (15 Zaydi, 4 Ibadi) audited and rejected.
- Dates: 2026-07-20 to 2026-07-20 (date of the audit, per datasets/hadith-data/AGENTS.md)
- Identity: not_recorded. The audit does not name the model. The OpenITI translations.jsonl.*.bak files record google/gemma-4-e4b on their rows, but the report does not say the 19 rejected rows came from them, so no model is assigned.
- Status: rejected. rejected after content inspection: every complete text_en contained prompt instructions, model self-correction or missing-input commentary, or text from a different hadith.
- Inputs:
  - `OpenITI translation backups, joined to current records by immutable identity and exact Arabic`
- Outputs:
  - `datasets/hadith-data/AGENTS.md`: 19 rejected backup candidates; no override written; none enters the canonical data
- May be used for:
  - None.
- May not be used for:
  - Stripping a plausible final sentence out of the responses; any promotion to an override.
- Quality findings:
  - All 19 complete backup values contained prompt text, model self-correction, missing-input commentary or a translation of different Arabic. (source: datasets/hadith-data/AGENTS.md, Translation release gate; DATA_QUALITY_REPORT.md line 143)
- Evidence:
  - `datasets/hadith-data/AGENTS.md`: Translation release gate, paragraph beginning 'An exact identity/Arabic join'
  - `datasets/hadith-data/DATA_QUALITY_REPORT.md`: line 143

### gemma-3-27b-it: arabic text cleanup (`gemma-lmstudio-zaydi-arabic-purification`)

- Runtime: LM Studio, local (script default http://localhost:1234/v1/chat/completions)
- Work: LLM purification of OCR-corrupted Zaydi Arabic with a 1 to 4 confidence score. Arabic text work, not translation.
- Dates: 2026-04-29 to 2026-05-08 (modification times of zaydi_cleaned.jsonl (2026-04-29), zaydi_purified_old.jsonl (2026-05-03) and purify_arabic_text.py (2026-05-08))
- Identity: insufficiently_specific. Only the purification script's default (gemma-3-27b-it, no vendor namespace) and the README's 'a Gemma model' are recorded; the output rows carry no model field, so which Gemma actually ran is unknown.
- Status: superseded. unreviewed. The current Zaydi Arabic is the OpenITI transcription (community-proofread Shamela, not OCR) per zaydi-hadith/PROVENANCE.json.
- Inputs:
  - `datasets/archive/ocr-pipeline/zaydi/zaydi_for_purification.jsonl (627 hadiths)`
- Outputs:
  - `datasets/archive/ocr-pipeline/zaydi/zaydi_cleaned.jsonl`: 23 lines; README: 23 merged results so far
  - `datasets/archive/ocr-pipeline/zaydi/zaydi_purified_old.jsonl`: 627 lines; 10 carry an _error field
- May be used for:
  - Historical reference only.
- May not be used for:
  - Using the purified Arabic as source text.
- Evidence:
  - `datasets/archive/ocr-pipeline/zaydi/purify_arabic_text.py`: line 5 (Gemma), --model default gemma-3-27b-it
  - `datasets/hadith-data/README.md`: Zaydi data-quality notes, LLM purification pipeline (In progress; 23 merged results)
  - `datasets/hadith-data/zaydi-hadith/PROVENANCE.json`: notes (text is from Shamela, not OCR)

### gemma3:12b: ocr parsing (`gemma3-12b-ollama-ibadi-ocr-parse`)

- Runtime: Ollama, local
- Work: LLM-assisted parsing of OCR text of the Ibadi Musnad into hadith records (tool calling), and a translation script defaulting to the same model. The run itself is not logged.
- Dates: 2026-03-16 to 2026-04-17 (modification times of the scripts and parsed_hadiths_llm_test.json)
- Identity: insufficiently_specific. Script default only, an Ollama tag without vendor namespace; no run log or per-row model field exists for the outputs.
- Status: superseded. unreviewed. The current Ibadi Arabic is the OpenITI transcription per ibadi-hadith/PROVENANCE.json.
- Inputs:
  - `datasets/hadith-data/archive/ibadi-musnad-pipeline/raw_ocr_pages.json`
- Outputs:
  - `datasets/hadith-data/archive/ibadi-musnad-pipeline/parsed_hadiths_llm_test.json`: LLM-assisted parse variant per the pipeline README; musnad_hadiths_en.jsonl, named as the translation output, is not in the working tree
- May be used for:
  - Historical reference only.
- May not be used for:
  - Using the OCR-derived parse or translation as source or release text.
- Evidence:
  - `datasets/hadith-data/archive/ibadi-musnad-pipeline/02_parse_hadiths.py`: line 410 (model='gemma3:12b'); line 5 (Ollama + Gemma)
  - `datasets/hadith-data/archive/ibadi-musnad-pipeline/03_translate_ollama_eng_to_arabic.py`: line 116 (--model default gemma3:12b)
  - `datasets/hadith-data/archive/ibadi-musnad-pipeline/README.md`: Key Data Files

### Claude Fable 5.2: coding assistance (`claude-fable-5-2-coding-assistant`)

- Runtime: AI coding assistant (Claude Code), recorded by commit trailer
- Work: Co-authored application code (src/app, src/db, src/lib, src/components, src/scripts), data pipeline code and diagnostics (datasets/hadith-data), and documentation and planning files (docs, conductor, .omc) in 18 commits reachable from HEAD. No scholarly content is attributed to the assistant.
- Dates: 2026-11-21 to 2026-11-21 (commit dates)
- Identity: namespaced_specific. Name as written in the Co-Authored-By trailer (Claude Fable 5.2 <noreply@anthropic.com>); a trailer name is not an API model identifier.
- Status: not_applicable. commits carry the repository owner's git author identity; no separate review record per commit.
- Inputs:
  - `repository working tree and owner instructions`
- Outputs:
  - `git log HEAD (trailer Co-Authored-By: Claude Fable 5.2)`: 18 commits (34 across all refs including the pre-rewrite backup branch); includes the hy-mt2 candidate generator commit f1e6001
- Evidence:
  - `git log HEAD`: --format=%(trailers:key=Co-Authored-By,valueonly), grouped by trailer value

### Claude Opus 4.7 (1M context): coding assistance (`claude-opus-4-7-coding-assistant`)

- Runtime: AI coding assistant (Claude Code), recorded by commit trailer
- Work: Co-authored application code (src/app, src/lib, src/scripts), data pipeline code (datasets/hadith-data, datasets/archive) and track documentation (conductor, .omc) in 6 commits. No scholarly content is attributed to the assistant.
- Dates: 2026-05-24 to 2026-06-03 (commit dates)
- Identity: namespaced_specific. Name as written in the Co-Authored-By trailer; a trailer name is not an API model identifier.
- Status: not_applicable. commits carry the repository owner's git author identity; no separate review record per commit.
- Inputs:
  - `repository working tree and owner instructions`
- Outputs:
  - `git log HEAD (trailer Co-Authored-By: Claude Opus 4.7 (1M context))`: 6 commits; the same assistant family also appears as manual:claude-opus-4.7 in four Zaydi translation rows (separate entry)
- Evidence:
  - `git log HEAD`: --format=%(trailers:key=Co-Authored-By,valueonly), grouped by trailer value

### Claude Opus 4.6 (1M context): coding assistance (`claude-opus-4-6-coding-assistant`)

- Runtime: AI coding assistant (Claude Code), recorded by commit trailer
- Work: Co-authored data pipeline code (datasets/hadith-data, datasets), application code (src/app, src/lib, src/components, src/scripts) and track documentation (conductor, .omc) in 2 commits. No scholarly content is attributed to the assistant.
- Dates: 2026-04-20 to 2026-04-22 (commit dates)
- Identity: namespaced_specific. Name as written in the Co-Authored-By trailer; a trailer name is not an API model identifier.
- Status: not_applicable. commits carry the repository owner's git author identity; no separate review record per commit.
- Inputs:
  - `repository working tree and owner instructions`
- Outputs:
  - `git log HEAD (trailer Co-Authored-By: Claude Opus 4.6 (1M context))`: 2 commits
- Evidence:
  - `git log HEAD`: --format=%(trailers:key=Co-Authored-By,valueonly), grouped by trailer value

### qwen/qwen3.7-flash: extraction audit (`qwen3-7-flash-openrouter-extraction-audit`)

- Runtime: OpenRouter API (provider policy data_collection deny; temperature 0; reasoning disabled; no referer or title headers)
- Work: Scored each of the 1,901 corrected OpenITI reports in production (Musnad al-Rabi 1,005, Musnad Zayd 691, Sahifat al-Rida 205) against a window of the OpenITI source, 0 to 3 for boundaries, cleanliness and sanad/matn split, with flags and verbatim-substring proposals. Arabic only; no translation; no authenticity judgement. 1,898 reports scored, 3 failed after one retry.
- Dates: 2026-11-22 to 2026-11-22 (run manifests started_utc and finished_utc)
- Identity: namespaced_specific. Requested id as sent to OpenRouter; every verdict row records the model field the harness stored (qwen/qwen3.7-flash).
- Status: candidate_only. machine_unreviewed; verdicts are advice to a curator. Nothing in parsing, text_ar, sanad or matn was changed on the strength of a score.
- Inputs:
  - `datasets/hadith-data/extraction-quality/output/records_with_windows_corrected.jsonl.gz (production text_ar, sanad_ar, matn_ar and a source window per report, built by build_corrected_windows.py)`
  - `datasets/hadith-data/extraction-quality/prompt.md (SHA-256 5699afa9f89b637d776027921724cd431a8030e36ede31b757a0f2278bb26848)`
- Outputs:
  - `datasets/hadith-data/extraction-quality/output/model_verdicts_corrected.jsonl`: 1,014 verdict events (rabi); first process; also holds 3 zayd verdicts duplicated in the zayd file
  - `datasets/hadith-data/extraction-quality/output/model_verdicts_corrected_zayd.jsonl`: 719 verdict events (zayd)
  - `datasets/hadith-data/extraction-quality/output/model_verdicts_corrected_rida.jsonl`: 208 verdict events (rida)
  - `datasets/hadith-data/extraction-quality/output/score_summary_corrected.json`: 1 summary; score distribution and the 20 lowest-scoring reports
- May be used for:
  - Ranking reports for human review of extraction quality.
  - Candidate corrections that a curator accepts or rejects against the OpenITI source.
- May not be used for:
  - Writing any proposal into text_ar, sanad or matn_ar without a hash-bound human review.
  - Treating a score as a statement about the authenticity or grade of a report.
- Quality findings:
  - Reports with all three scores 3: 1,195 of 1,898 (63 percent). Lowest sub-score 0 for 209 reports, 1 for 101, 2 for 393. Most frequent flags: markup_leak 217, sanad_matn_split_wrong 184, merged_records 153, commentary_tail 120. The worst reports are mostly Musnad al-Rabi reports that open with the compiler's own 'qal al-Rabi' (judged commentary, not a report). (source: datasets/hadith-data/extraction-quality/output/score_summary_corrected.json)
- Evidence:
  - `datasets/hadith-data/extraction-quality/output/run_manifest_corrected_zayd.json`: whole file (run_id, model, prompt_sha256, started_utc, finished_utc, cost_usd); the rida and rabi retry manifests sit beside it

### claude-haiku-5-5: chain reading (`claude-haiku-5-5-chain-reader-pilots`)

- Runtime: Claude Code subagents, fresh context per run, two independent passes
- Work: Chain reading (chain-fix submissions): read each report's Arabic and wrote its routes name by name, for the chain-fix pipeline (docs/review/chain-fix-pipeline.md). Pilot v1 (prompt.md) and v2 (context/prompt-v2.md) over the 284 labelled pilot reports; batch 001 (500 reports drawn from chains marked uncertain) under prompt v3.0.0 (v3/prompt-v3.md, sha256 a5a223b6acfc...0827764), two blind passes with source context. Re-triaged by the v3.1 tool (v3_1/, prompt 3.1.0 sha256 fca49673fea3...2860fd registered, not yet run): 394 agreed, unheld readings eligible (358 with links, 36 'no chain by reading'); 348 stand applied to the live archive (2026-11-22) as 'Read by model (claude-haiku-5-5), awaiting final review' (258 rewritten routes, 60 stored routes confirmed, 30 'no chain is written'); 46 held (30 reports that also have a rule-checked chain, 3 whose chain later reports repeat, 4 with a variant group, 1 inherited from an uncertain chain, 11 held by the v3.2 tool on re-triage, 9 of which had been applied and were reverted). Chains read by model feed no teacher and student list.
- Dates: 2026-11-22 to 2026-11-22 (RUN.txt start and end times; applied 2026-11-22)
- Identity: namespaced_specific. The id each reader run wrote in its RUN.txt line (chain-reader/outputs/*/RUN.txt, context/outputs-v2/*/RUN.txt, v3/batch-001/outputs/pass-a|pass-b/RUN.txt).
- Status: applied_awaiting_final_review. ai_reviewed, awaiting final review: 348 batch-001 readings are applied as 'Read by model, awaiting final review'; a person's confirmation turns one into 'Verified by <name>', a rejection reverts it.
- Inputs:
  - `datasets/hadith-data/chain-reader/pilot/ (284 labelled reports)`
  - `datasets/hadith-data/chain-reader/context/pilot-v2/packets/`
  - `datasets/hadith-data/chain-reader/v3/batch-001/packets/`
- Outputs:
  - `datasets/hadith-data/chain-reader/outputs/`: 568 reader outputs (v1, two passes)
  - `datasets/hadith-data/chain-reader/context/outputs-v2/`: 568 reader outputs (v2, two passes)
  - `datasets/hadith-data/chain-reader/v3/batch-001/outputs/`: 1,000 reader outputs (v3, two passes of 500)
  - `reviews/ai/records/chain-fixes/submissions/`: 788 submissions (394 readings, two runs each); batch 001, prompt v3.0.0, tool v3_1
  - `datasets/hadith-data/chain-fixes/accepted_overrides.jsonl.gz`: 348 applied fixes replayed by the projection
- May be used for:
  - Chain-fix submissions under the agreement and hold rules (reviews/ai/tools/chain-fix-*.ts)
  - Applied readings labelled 'Read by model, awaiting final review' (and 'No chain is written in this report' for an agreed empty reading)
  - Proposals beyond the chain for a person to decide
- May not be used for:
  - Writing a chain without two agreeing independent readings and no hold
  - Feeding teacher and student lists before the work's agreed-reading error rate is measured (chain_fix_work_settings)
  - Calling a reading verified
- Quality findings:
  - Pilot v2 re-scored under the v3 tool: 213 of 279 applied, 210 right (99 percent, 96 to 100), measured on the readings the holds were tuned on (in-sample); batch 001 is the out-of-sample measurement. (source: datasets/hadith-data/chain-reader/v3/README.md)
  - Batch 001 judged by one independent model reader (not blind, not a scholar): agreed, unheld readings right in 98.6% (96.8 to 99.4, weighted) against 16.0% for the stored chains; no reading broke a correct stored chain (0 of 244). Under the v3.1 tool and the owner's rulings of 2026-11-22: 237 of 241 right, 0 wrong, 4 undecided; the 36 no-chain readings all right. (source: datasets/hadith-data/chain-reader/analysis-batch-001/README.md; datasets/hadith-data/chain-reader/v3_1/batch-001/RETRIAGE.md)
- Evidence:
  - `datasets/hadith-data/chain-reader/v3/rescore_v3.json`: whole file
  - `datasets/hadith-data/chain-reader/analysis-batch-001/numbers_b1.json`: whole file

### claude-opus-5-5: chain review (`claude-opus-5-5-chain-reviewer`)

- Runtime: Conduction workers, fresh context, one packet of 10 readings per job
- Work: AI first pass of final review of model-read chains (chain-reader/reviewer, prompt 1.1.0 sha256 1136aec2c975aebd0f4b8f17cf14d6ad1410229c33b97e7d8382b8258cb735f6): reads the Arabic against both readers' readings and the tool's holds and confirms, corrects, prefers a reader, keeps the stored chain or refers to a person. Its decision moves a fix only as review_rules_v1_1.outcome says (reviews/ai/tools/chain-review-record.ts): a confirmation labels an applied reading 'AI reviewed' or applies a held reading whose holds it may clear; a correction or referral never reverts an applied reading (labelled 'Disputed by the reviewer; awaiting second review'); a correction is applied only when a second independent review writes the same routes. Pilot (prompt 1.0.0, 81 tranche-02 readings) only; 1.1.0 not yet run.
- Dates: 2026-11-22 to 2026-11-22 (pilot-001 RUN.txt)
- Identity: namespaced_specific. The id each reviewer run writes in its RUN.txt line (chain-reader/reviewer/<set>/outputs/pass-N/RUN.txt); the recorder refuses a review whose packet has no such line.
- Status: ai_reviewed_awaiting_human_review. ai_reviewed, awaiting human review: never 'verified'; a person's decision overrides it.
- Inputs:
  - `datasets/hadith-data/chain-reader/reviewer/pilot-001/packets/`
- Outputs:
  - `datasets/hadith-data/chain-reader/reviewer/pilot-001/outputs/pass-1/`: 81 reviews (prompt 1.0.0, pilot); not recorded in the fix store
- May be used for:
  - Recording reviews per item through chain-review-record.ts
  - Labels 'AI reviewed (claude-opus-5-5), <date>' and 'Disputed by the reviewer; awaiting second review'
  - Clearing the holds review_rules_v1_1 lists as clearable
- May not be used for:
  - Clearing a hold on a point the owner has not ruled
  - Applying a correction on one review run
  - Calling a chain verified
- Quality findings:
  - Pilot re-scored under the v1.1 rule against one Opus adjudicator (55 of 81 read, not blind, not a person): 26 of 26 wrong readings caught, 52 of 52 right readings confirmed (3 by a cosmetic correction), no harmful outcome. (source: datasets/hadith-data/chain-reader/reviewer/README-v1_1.md)
- Evidence:
  - `datasets/hadith-data/chain-reader/reviewer/pilot-001/rescore_v1_1.json`: whole file

## Coverage notes

- 10 of the 36 commits reachable from HEAD carry no Co-Authored-By trailer (2025-12-12 to 2026-07-04); no AI assistant is attributed for them because none is recorded.
- Commits are counted from HEAD. The backup branch backup/main-pre-rewrite-20261121 holds pre-rewrite copies of the 2026-11-21 commits, so counting every ref gives 34 for Claude Fable 5.2 instead of 18.
- The honorific glyph substitution (10,662 rows, machine_translation_candidates/honorific_glyph_substitution_candidates_2026-11-21.jsonl) is a mechanical rule with translation_model null; it is not a model and has no entry here.
- K6 and Thaqalayn English (legacy_k6_source_export, Thaqalayn API V2) is upstream source text, not model output; the master records no translation_model for it.
