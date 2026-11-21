---
type: diagnostic
status: candidate_only_unreviewed
---

# translation-run (2026-11-21): glyph substitution and tencent/hy-mt2-30b-a3b candidates

Everything here and in `machine_translation_candidates/` is a review-only candidate. Nothing was written to canonical CSV/GZIP, `translation_overrides.jsonl`, manifests or the backlog. Pipeline: `../../generate_hy_mt2_candidates.py` (reuses the existing generator's `candidate_validation_errors`, `text_sha256`, file-locked fsync'd `append_jsonl`). Tests: `../../__tests__/test_hy_mt2_candidates.py`.

Source of truth for selection is the isolated full-schema master `development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz` (11,953 leakage rows, including classical rows the legacy snapshot lacks), so counts differ from `../translation/summary.json` (snapshot: 11,544).

## Files (all under `machine_translation_candidates/`)

| File | Rows | Meaning |
| --- | ---: | --- |
| `honorific_glyph_substitution_candidates_2026-11-21.jsonl` | 10,662 | Mechanical: U+FDFA to "(peace and blessings be upon him)", U+FDFB to "(may His glory be exalted)". `translation_model` null, `substitution_kind` mechanical_substitution. No API call. |
| `openrouter_hy_mt2_30b_a3b_pilot_2026-11-21.jsonl` | 60 | Stratified pilot, original screen (51 accepted, 9 rejected, all 9 `repetition_loop`, shown below to be false positives). |
| `..._pilot_2026-11-21_rescreened_screen_v2.jsonl` | 60 | Same model outputs re-screened with `screen-v2` (59 accepted, 1 rejected). Derived file; original untouched. |
| `..._batch_no_usable_english_2026-11-21.jsonl` | 1,211 | missing / placeholder / same-as-Arabic / short / fully or partially Arabic. 1,210 accepted. |
| `..._batch_names_terms_2026-11-21.jsonl` | 874 | names_or_terms_only. 872 accepted. |
| `*_skipped.jsonl` | 4 + 11 | Rows with a single sentence over 5,500 chars (no defensible sentence split); never sent. |

The pilot's 36 + 24 rows that fall in the two batch phases were not repeated; the batch journals skip them (`--skip-from`).

## Method

- Prompt: model card default English template, no system prompt: "Translate the following text into English. Note that you should only output the translated result without any additional explanation:" + Arabic. Temperature 0.7 (card recommendation for 30B-A3B). Context 8,192 tokens, max completion 4,096.
- Rows over 2,500 chars are split only at sentence ends (`.` `؟` `!`), chunks joined with a space; the split offsets are in each event (`split.offsets`).
- Provider policy `data_collection: deny`, `allow_fallbacks: false`; generic User-Agent; only Arabic text and the instruction are sent.
- Screening: generator's checks (blank, refusal, placeholder, copied input, any Arabic-script leakage, under 80 percent Latin letters, short output) plus finish_reason must be `stop`, prompt-echo, Latin/Arabic letter ratio in [1.0, 3.2] (accepted Gemini candidates span 1.5 to 2.3), and a repetition-loop guard.
- `screen-v2` was tuned after seeing the pilot: the first loop guard flagged repeated honorific phrases and sources that repeat themselves (e.g. pc_88097, whose Arabic repeats "وإن زنى وإن سرق" six times). v2 strips honorific phrases and compares English 10-gram repeats with Arabic 4-gram repeats. The ratio floor was raised from 0.5 to 1.0 after one 5,495-char Imami row came back summarised (ratio 0.72). All batch rows were screened with v2.

## Spend

Pilot $0.0089 + batch 1 $0.0568 + batch 2 $0.0528 = $0.1184 total, 729,147 tokens (provider-reported `usage.cost`). Budget cap was $15; never approached.

See `summary.json` for per-file counts, latency, and coverage of every flagged master row.
