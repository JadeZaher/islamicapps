---
type: diagnostic
---
# Extraction quality of the OpenITI reports (rabi, zayd, rida)

Owner feedback: reports we extracted from OpenITI are poorly cut. This directory audits all 1,737 production records of
three works with rules (`deterministic_checks.py`) and provides a resumable cheap-model scorer (`score_with_model.py`).
Nothing outside this directory was edited, no database was written, nothing is committed.

| Work | Tradition in production | Records | Source file |
|---|---|---|---|
| `rabi` Musnad al-Rabi ibn Habib | ibadi | 1,004 | `openiti-sources/rabi/jamic_sahih_ibadiyya.txt` (OpenITI `0170RabicIbnHabibAzdi.JamicSahih.ShamIbadiyya0000155-ara1`) |
| `zayd` Musnad Zayd | zaydi | 698 | `openiti-sources/zayd/musnad_zaydiyya_052.mARkdown` (`0122ZaydIbnCali.Musnad.Zaydiyya0000052-ara1`) |
| `rida` Sahifat al-Rida | imami (the parser says "Zaydi") | 35 | same Zayd file, appendix after the line containing «مسند الإمام علي الرضا» (line 5320) |

## From source file to record

1. `datasets/parse_openiti.py` (`parse_rabi`, `parse_zayd`, `parse_rida_appendix`) reads the mARkdown line by line: `# ` starts a
   paragraph, `~~` continues it, `### |` / `### ||` are headings, `PageV01P039` and `ms137` are markers. Text is normalised by
   `normalize_arabic` (NFKC, bidi controls out, page and milestone markers out, whitespace collapsed) and `strip_footnote_markers`
   (`(1)`, `(¬1)` out), then written to `ibadi-hadith|zaydi-hadith|rida-hadith/parsed_hadiths.json`.
2. A **report boundary** is: rabi, a numbered line `# 140) ...` (a `مكرر` suffix gives the `b` id); zayd and rida, any `# ` paragraph whose first
   30 characters contain a transmission verb (`حدثني`, `وقال`, `سألت`, ...) or, rida only, starts `وباسناده`. Everything else in between is
   appended to the current record. The page-break paragraphs of the edition are therefore both the main cause of merged records and of
   cut-off ones.
3. `regen_unified_csvs.py` (`openiti_to_shia_row`) builds the row: `text_ar` = parsed text, `sanad` = the Latin narrator-name list from
   the chain resolver, `matn_ar` = the parser's `matn_ar`, `record_id = openiti:<tradition>:<id>|<hadith_no>|<page_ref>` (the page is the
   page marker last seen when the record was flushed, so it is the page of the *next* report's start).
4. `pg_export/export_postgres.py` projects the row to `hadiths` (`id = hadith:` + record_id, `arabic_sha256` of `text_ar`); `src/db/load/` loads it.

`eq_source.py` replays these three parsers with provenance (every source line is labelled with what the pipeline did with it, and every
character of every record carries its raw-file offset). **The replay reproduces all 1,737 production `text_ar` byte for byte** (it also sees
`zayd_0118` «الثياب للصلاة:», a heading kept as a record by the parser; it is absent from production, evidently removed by a later cleanup).
Production rows were read once, read-only, into `output/production_snapshot.jsonl.gz` (id, text_ar, sanad, matn_ar, hash; no secrets).

## Commands

```
python -I -X utf8 datasets/hadith-data/extraction-quality/deterministic_checks.py        # 2 s, writes output/
python -I -X utf8 datasets/hadith-data/extraction-quality/score_with_model.py --dry-run   # estimate only
python -I -X utf8 datasets/hadith-data/extraction-quality/score_with_model.py --limit 20  # live; resumable; stops on 402 or cost cap
python -I -X utf8 -m pytest datasets/hadith-data/extraction-quality/test_extraction_quality.py -q
```

Outputs (`output/`): `extraction_findings.jsonl.gz` (one row per record), `records_with_windows.jsonl.gz` (scorer input),
`missed_source_reports.jsonl.gz`, `summary.json`, `run_manifest.json` (the 402 attempt), `production_snapshot.jsonl.gz`.

## Method and flags

Each finding row: `id`, `source_record_id`, `source_file`, `located` + `source_span` (`raw_start/raw_end` = character offsets into the decoded
UTF-8 file, `line_start/line_end`, `text_raw_start/end`; or `"not located"`), `flags` (flag, severity, evidence with excerpt and raw span),
`proposal`, `proposal_validation`, `clean`. A proposal is rebuilt from the source pieces the replay kept (so it is contiguous source) or cut from
the production text at a rule boundary; then every string is checked to be a substring of the record's source window (whitespace collapsed).

| Flag | Rule |
|---|---|
| `footnote_leak` | the record contains a `__________` line / `(1) *` footnote block that the pipeline appended (3 blocks in the whole of rabi) |
| `markup_leak` | leading `=` (zayd edition marker) or Latin `V`, a lone `*`, page/milestone residue |
| `fragment_only_chain` | the whole record is a chain with no body («حدثني أبو خالد الواسطي قال:») |
| `merged_records` | chapter heading swallowed (rabi `كتاب ...`, rida `الباب ...`), several reports (rida `وباسناده`, zayd `= حدثني زيد بن علي`), a numbered report header hidden behind a page marker |
| `commentary_tail` | text from a «قال الربيع» comment paragraph's continuation or an editorial section («تنبيه»), defect; or prose after the matn's closing quote, advisory |
| `sanad_matn_split_wrong` | stored matn starts with a reporting verb, starts mid-word, differs from the rule split, or the chain exists but `sanad` is empty; continuation chains («وبهذا السند») |
| `sanad_latin_not_arabic_span` | `sanad` is a Latin name list, not the Arabic chain |
| `truncated` | source lines the pipeline dropped (rabi: a line that begins with a page marker instead of `#`), or the record ends inside a chain |
| `missing_from_source` | the replay cannot reproduce the text (0 records) |
| advisory | `commentary_misattributed` (the pipeline attaches a «قال الربيع» paragraph to the *previous* record), `multiple_sayings` (zayd `(وقال)`, `وسألت`) |

Chain/matn rule (`split_chain_matn`): the chain ends at the first reporting verb that is not followed by another transmission verb; that verb
(`قال:`) and a following «رسول الله صلى الله عليه وسلم» attribution stay on the **sanad** side; confidence is high only when a colon, an opening
quote or the attribution follows. This is the owner's convention («the `قال:` belongs to the chain side») and is one function to change.

## Counts (records flagged, by work)

| Flag | rabi (1,004) | zayd (698) | rida (35) |
|---|---|---|---|
| footnote_leak | 3 | 0 | 0 |
| markup_leak | 4 (3 `*`, 1 page residue) | 613 (612 with a leading `=`/`V`, 3 with `*`; overlapping) | 1 (`*`) |
| fragment_only_chain | 0 | 3 | 0 |
| merged_records | 9 (heading inside) | 4 (multiple reports) | 32 (203 reports + 6 headings after splitting; rida_0032 alone holds 12 reports + 2 headings) |
| commentary_tail | 181 (72 defect, 109 advisory) | 0 | 0 |
| sanad_matn_split_wrong | 891 | 654 | 35 |
| sanad_latin_not_arabic_span | 843 | 678 | 9 |
| truncated | 7 | 3 | 2 |
| commentary_misattributed (advisory) | 138 | 0 | 0 |
| multiple_sayings (advisory) | 0 | 18 | 0 |
| missing_from_source | 0 | 0 | 0 |

Kinds inside `sanad_matn_split_wrong` (rabi/zayd/rida): matn starts with a reporting verb 523/125/33; matn starts **mid-word** 333/315/0 (the
production `matn_ar` is cut inside a word, e.g. zayd_0305 starts «كب بدنته»); matn differs from the rule split 691/624/30; chain present but no
sanad 42/5/1; continuation chain without sanad 1/0/25.

**Clean records** (no defect-severity flag at all): rabi 37, zayd 7, rida 0, **44 of 1,737**. Text-level clean (ignoring the sanad/matn
representation flags, which are systemic): rabi 914, zayd 78 (the `=` marker is on 612), rida 2.

**Proposals**: 968 + 691 + 35 records carry one; 5,386 proposed strings were checked, **5,386 are verbatim substrings of their source window,
0 fail** (`summary.json` `proposal_failures`). 698 rabi, 637 zayd and 30 rida records get an Arabic `sanad_ar`/`matn_ar` split; 188+46+4 Latin-sanad
records get none (low-confidence split: narrator speech without a colon, e.g. «وباسناده قال علي ... كنا مع النبي»). Left to the model or a curator.

**Missed by the extraction** (`missed_source_reports.jsonl.gz`): rabi report **881** whole (header `881) ...` sits behind a page marker, line 5909;
748 characters, chapter [36] on the Apostles' table), 8 source lines dropped inside rabi records, 1 dropped line in zayd (line 4698),
140 «قال الربيع» comment paragraphs (kept by the parser on the previous record's `commentary` field, never loaded), the rida biographical
introduction (dropped on purpose).

## 15 worked examples

Offsets are character offsets into the source file; the proposal is a verbatim substring of the source window.

1. **rabi_0140** (lines 910-931, offsets 37002-37593). Defect: commentary continuation and editor markers leak into the report. Source: `# قال الربيع: قال أبو عبيدة: وعليه ... ~~وسرته وكل ما
   بطن من جسده.`, then `# __________`, `# (1) *`, `# (2) *`, `# (3) *` (markers whose notes were stripped from this edition), then a second `# قال الربيع: الفنيكة هي ...` paragraph.
   Production text ends «... عند الجنابة». وسرته وكل ما بطن من جسده. __________ * * * المسربة ...». Proposal `text_ar` ends «عند الجنابة».», `commentary` = the two «قال الربيع» paragraphs, no
   `footnotes` (the starred notes have no text). The trap: the `~~` line after a skipped comment paragraph is appended by the parser to the report.
2. **rabi_0225** (1468-1479). Footnote `* خ: هذه.` after `__________` leaked; separated into `footnotes`, plus a Rabi comment tail. (rabi_0121 is the same with an empty footnote: text ends «قط. __________ * *».)
3. **rabi_0335** (2130-2139). Text ends «... ذات عوار». ولدها، والأكولة شاة اللحم، وهي السمينة.»: the tail is the end of the «قال الربيع: السخلة التي تتبع أمها ...» comment, split over a page break. Proposal text stops at «ذات عوار».».
4. **rabi_0880** (5832-5905; 3,714 chars of text). Report plus an arranger's «تنبيه» section of 3,426 characters; proposal keeps the 1st part, `commentary[0]` = the «تنبيه» section.
5. **rabi_0881** (line 5909, **missing**). `PageV01P247 881) ... وأما ما سألت عنه من قول الحواريين` starts with the page marker, so no `#`; the parser dropped the header and the `~~` lines after it. Listed in `missed_source_reports`.
6. **rabi_0002** (58-65). Source line 63 ` PageV01P006 ما قال وأحيانا يتمثل لي الملك رجلا فيكلمني` (no `#`/`~~`) dropped: production reads «... وقد وعيت فأعي ما يقول»; proposal restores «... وقد وعيت ما قال وأحيانا يتمثل لي الملك رجلا فيكلمني فأعي ما يقول».
7. **rabi_0001** (49-51). `matn_ar` = «قال: «نية المؤمن خير من عمله».». Proposal `sanad_ar` = Arabic chain ending «... عن النبيء صلى الله عليه وسلم قال:», `matn_ar` = ««نية المؤمن خير من عمله».».
8. **rabi_0001b**. «وبهذا السند في رواية أخرى عنه عليه السلام قال: ...»: empty `sanad`; proposal `sanad_ar` = «وبهذا السند في رواية أخرى عنه عليه السلام قال:» (a pointer to report 1; it needs `continues_chain_of: rabi_0001` in the load).
9. **zayd_0026** (line 290). Source `# Vسألت زيدا بن علي ...`: leading Latin `V`; stored `matn_ar` begins «السلام عن الوضوء ...» (cut mid-chain). Proposal «سألت زيدا بن علي عليه السلام عن الوضوء مرة مرة فقال جائز والثلاث أفضل.».
10. **zayd_0305** (2591-2593). Leading `= `; chain without a verb («... عن علي (ع م) من اعتل ظهر عليه»); stored matn «كب بدنته بالمعروف ...» (mid-word). Proposal `sanad_ar` «حدثني زيد بن علي عن أبيه عن جده عن علي (ع م)», `matn_ar` «من اعتل ظهر عليه فليركب بدنته ...».
11. **zayd_0429** (line 3521). Record is «حدثني أبو خالد الواسطي قال:»; the page break split it from `# = حدثني زيد بن علي عن ابيه`. Proposal `merge_with_next: zayd_0430`, `merged_text_ar` = fragment + «= حدثني زيد بن علي عن ابيه ... تزوجوا فاني مكاثر بكم الامم.».
12. **zayd_0001** (32-97, 2,223 chars). 8 `(وقال)` sayings under one chain (`multiple_sayings`, advisory) and it ends «... فاغسله. (حدثني) أبو خالد قال:»: the next report's opener is glued to the tail. Proposal: cut it, `move_tail_to_next_record` = «(حدثني) أبو خالد قال:».
13. **zayd_0611** (4694-4695). Source line 4698 ` يوشك (1) ان يقدح الشك في قلبه ...` has no `#`/`~~`, dropped: production ends «... والعابد». Proposal appends «يوشك ان يقدح الشك في قلبه فإذا هو في وادي الهلكات.».
14. **rida_0032** (6003-6072, 3,966 chars). 12 reports, each starting «وباسناده», and two headings, «الباب التاسع في فضل الغزو والجهاد» and «الباب العاشر ...», inside one record. Proposal `split_into`: reports and headings; the first report keeps `rida_0032`.
15. **rida_0026** (5870-5878). 4 reports in one record, ending with the edition's lone «*»; `markup_leak` plus split. (rida_0001 is the editor's explanation plus the first half of the Sahifa's own chain «... قال حدثني ابي», continued in rida_0002: flagged `truncated`, `merge_with_next`.)

## Model scoring (`score_with_model.py`, `prompt.md`)

Prompt `prompt.md` (SHA-256 recorded in every row and in `run_manifest.json`), user message = JSON with up to `--batch-size` (default 4) records:
`extracted_text`, `extracted_sanad`, `extracted_matn`, `source_window` (the record's paragraphs plus two before and two after). The model answers
`{"verdicts":[{id, scores:{boundaries,cleanliness,sanad_matn_split} 0-3, flags, reason, proposals:{text_ar,sanad_ar,matn_ar,footnotes[],commentary[]}}]}`.
`validate_verdict` rejects bad scores/flags and **drops every proposal that is not a substring of the supplied window**, recording which
(`rejected_proposals`). Rows: `id, work, status, verdict, problems, model, prompt_sha256, run_id, run_started_utc, request_started_utc,
request_finished_utc, cost_usd_share`. Resume: records stored with `status: ok` are skipped; failed ones are retried on the next run.
Safeguards: temperature 0; `provider.data_collection = deny`; headers are only `Authorization` and `Content-Type`; key read at run time from
`C:/Users/atooz/.pi/agent/models.json` (`providers["openrouter-free"].apiKey`) and scrubbed from any stored message; cost cap `--max-cost-usd`
(default 2) checked **before** each request against a pessimistic projection; HTTP 402 stops the run immediately (exit code 2, manifest
`stopped_because: http_402_payment_required`); 429/5xx retry 3 times with backoff; 401/403 stop.

**Live attempt (once, 4 records, 2026-11-21 UTC):** HTTP 402 on the first request; stopped cleanly, no rows written, `output/run_manifest.json`
holds the record. The model id `qwen/qwen3.7-flash` and its prices (US$0.03 / 0.13 per million tokens, 1M context) are the lead's figures and
were **not** checked against OpenRouter (not reachable without credit); `reasoning.enabled=false` is sent by default, use
`--reasoning default` if the model rejects it.

## Cost

Dry run over all 1,737 records (windows 1.63 M characters + 0.47 M of extracted text; 2.2 characters per token, deliberately pessimistic; 420 output tokens per
record): **about 1.2 M input and 0.73 M output tokens = US$0.13** (7.4 K tokens per 4-record batch at most). Real Arabic tokenisation will be
cheaper on input. The default cap of US$2 is 15x the estimate. English translation of the corrected reports (not built here, no English exists
for these works): the recorded hy-mt2 spend is US$0.40369 for 9,191 reports, about US$4.4e-5 each, so about US$0.10 for the ~2,000 corrected reports.

## Load spec: how corrected text flows into the projection

1. **Fix the parser first** (`parse_openiti.py`), then regenerate `parsed_hadiths.json`: stop at a `__________` paragraph; treat the paragraphs
   and `~~` lines after a «قال الربيع» paragraph as commentary, attach it to the **current** record; accept a line that starts with a page marker
   plus text as a continuation and `PageV.. N) ...` as a report header; drop `=`/`V` markers; keep short zayd fragments as the prefix of the *next*
   record only when adjacent; split rida at `وباسناده` and `الباب <ordinal>`. Anything a rule cannot do goes through a reviewed sidecar.
2. **Reviewed sidecar** `reconciled/extraction/openiti_corrections.jsonl.gz` (same hash-bound pattern as the other reconciled sidecars), one row per accepted change:
   `record_id`, `old_arabic_sha256`, `action` (`replace` | `split` | `merge_into` | `move_tail` | `add_missing`), `text_ar`, `sanad_ar`, `matn_ar`, `source_code: "OITI"`,
   `source_file`, `raw_start/raw_end`, `evidence` (the flag evidence), `reviewer`, and the model `run_id`/`prompt_sha256` if a model contributed. Rows refuse to apply when `old_arabic_sha256` no longer matches.
3. **IDs stay stable.** `record_id` keeps `openiti:<tradition>:<parsed_id>|<hadith_no>|<page_ref>`. A split keeps the id for the first report and numbers the others
   `<record_id>#2`, `#3` (stable by position, deterministic); chapter headings are not records. A merged fragment (zayd_0429) is retired with `quality_excluded = true`,
   `quality_exclusion_reason = 'merged_into:<id>'` and the later record keeps its id and gains the prefix. The missing rabi_0881 is added as `rabi_0881|881|V01P247`.
4. **Hashes.** Any changed `text_ar` changes `arabic_sha256` (recomputed by the exporter; it refuses a mismatch). Everything bound to the old hash
   (report correspondences, assessments, reconciled chain sidecars, `commentary_hadiths.bound_arabic_sha256`, translation overrides) is rebuilt or refuses; none of these
   works has public English, so no published translation is lost. Re-run `report-correspondence` and the reconciled builders for these three works.
5. **Fields.** `hadiths.text_ar` = corrected report, `hadiths.matn_ar` = corrected matn (the `MatnIsolator` gate stays), the Arabic chain `sanad_ar` needs an owner decision:
   either replace `hadiths.sanad` (today Latin names, rendered by the app) or add a `sanad_ar` column (migration). **Footnotes and Rabi's commentary are separate credited fields, never
   inside `text_ar`:** rows in `commentaries` (`type` `editor_footnote` | `compiler_comment` | `arranger_note`, `text_arabic`, `sourceWork` the work, `reference` page/line, `origin` the pipeline's record origin),
   linked by `commentary_hadiths` with `bound_arabic_sha256` of the corrected report, source code **OITI** (OpenITI, CC BY-NC-SA, as on the other OpenITI rows). Rabi's own «قال الربيع» glosses are the
   compiler's; the «تنبيه» sections and `(1) *` notes are the arranger's/editor's, credited as such.
6. **Translations** (next step) are produced from the corrected `text_ar` and bound to its new hash, with `translation_review_status = machine_unreviewed`.

## Not done / deferred

- No model verdicts exist (HTTP 402). The registry draft (`model-registry-addition.json`) is a template with bracketed fields; nothing was written to `model_registry.json`.
- `sanad_matn_split_wrong` and `sanad_latin_not_arabic_span` are systemic (most rabi and zayd rows); they are reported but are a representation decision (see load spec 5) more than per-record damage.
- 238 low-confidence chain splits get no Arabic proposal (see above). Rida reports whose chain is only «وباسناده» are proposed as continuation chains pointing at the previous report.
- Zayd sub-sayings inside one record (`(وقال)`, `وسألت`) are advisory only; whether each is a report is a curation call.
- Gloss detection after a closing quote (rabi, 109 advisory) is a heuristic; the 72 defect-grade commentary tails are structural (source paragraph evidence).
- Offsets index the decoded file (LF); the three sources contain no CRLF.

## Corrected OpenITI reports, scored 2026-11-22

The 1,901 corrected reports now in production (rabi 1,005, zayd 691, rida 205) were scored by `qwen/qwen3.7-flash` (US$0.0995). `build_corrected_windows.py` builds the input
(`output/records_with_windows_corrected.jsonl.gz`) from a production read (`output/production_snapshot_corrected_2026-11-22.jsonl.gz`) and the OpenITI source; the three works ran as three
processes (`model_verdicts_corrected.jsonl` for rabi, `_zayd`, `_rida`; `run_manifest_corrected*.json`; one retry of failed batches each). 1,898 scored, 3 failed twice. `output/score_summary_corrected.json`:
score distribution per work and axis, flags, and the 20 lowest reports. Advice only: no parsing, text or sanad was changed on a score.
