---
type: diagnostic
---
# fixed/ — the corrected OpenITI parse (rabi, zayd, rida)

Output of the parser fix for the defects in `../README.md`. Nothing here is wired into a live path: `parsed_hadiths.fixed.json` is a new file,
the live `parsed_hadiths.json` files, the unified CSVs and every database are untouched. `LOAD_STEPS.md` says what the session lead runs to adopt it.

```
python -I -X utf8 datasets/hadith-data/extraction-quality/fixed/build_fixed.py     # rebuilds everything in this directory
python -X utf8 -m pytest datasets/test_parse_openiti.py -q                          # flow tests on the real sources
```

| File | What |
|---|---|
| `parsed_hadiths.fixed.json` | `works.{rabi,zayd,rida}` = the three parse results (same shape as `parsed_hadiths.json` plus the new fields below) |
| `diff_report.md` / `diff_summary.json` | counts, id changes, the audit's checks before/after, 12 before/after examples, limits |
| `checks_before_after.json` | the audit's flag counts (before from `../output/summary.json`, after from `check_fixed.py`) with the flagged ids |
| `LOAD_STEPS.md` | the commands, files and schema changes to get this into production; what a changed `arabic_sha256` invalidates |
| `check_fixed.py`, `build_fixed.py` | the audit rules re-run on the fixed records; the build and report |

## Model of the parser (`datasets/parse_openiti.py`)

- **Blocks.** `read_blocks` turns the file into blocks: a `#` paragraph or `###` heading plus its `~~` lines and its *orphan* lines (a line with
  neither prefix, e.g. ` PageV01P006 ما قال ...`, which the old parser dropped). A numbered header behind a page marker (` PageV01P247 881) ...`)
  opens a block of its own. A `~~` line after a heading belongs to the heading («الطاهرين:», zayd_0118/0149/0196).
- **Rabi record** = a numbered header block and the paragraphs that follow until the next header, `[N] باب`, juz line or a stand-alone title paragraph
  (`كتاب ...`, `ما جاء ...`; those set `kitab` / `section`). After the report starts to end, everything is not text: `__________` and `(N) *` blocks
  → `footnotes` (note-number-only blocks are counted in `footnote_markers_without_text`); a paragraph that opens «قال الربيع» → `commentary` kind
  `rabi_comment`, continued over a page break while the comment is unfinished (`is_terminal`); «تنبيه» and all after it up to the next header → one
  `arranger_note`; an inline «... ». قال الربيع: ...» → `gloss`; any other paragraph after a comment → `note`. Paragraphs that open «قال جابر» and the
  arranger's prose are left in `text_ar` (not in the brief; see the limits in `diff_report.md`).
- **Zayd / rida** keep the old record boundaries (a `#` paragraph whose first 30 characters hold a transmission verb, rida also «وباسناده» and
  `الباب ...`) so ids stay stable, with one correction: a verb at the top of a *page-break* paragraph whose previous report is cut mid-sentence is a
  continuation, not a trigger (`_page_break_decision`). Inside a boundary-defined chunk: zayd «و= حدثني ...» after a full stop starts a second report;
  rida splits at each «وباسناده» and at each inline «الباب <ordinal> في ...» (the heading becomes `bab`, not a report). Then chain-only fragments, and
  records that end inside a chain, merge into the next adjacent report (`merge_chain_fragments`) unless a glued opener «(حدثني) أبو خالد قال:» can be
  moved to the next report as its prefix (`prefix_from_id`). A next report that itself opens «وباسناده ...» is never the body of a fragment.
- **Edition markers** (`strip_edition_markers`): zayd `=` / `و=`, a leading Latin `V`, lone `*` are not text. Page markers, milestones and `(N)` / `(¬N)`
  footnote markers go through the pipeline's existing `normalize_arabic` / `strip_footnote_markers`.
- **Verbatim contract.** Haystack = every block's cleaned text, joined by one space (`build_haystack`). `text_ar`, `sanad_ar`, `matn_ar`, each footnote and
  each commentary string must be a whitespace-collapsed substring of it; `parse_*()['verification']` lists failures (zero today; the tests assert it).
- **sanad_ar / matn_ar** (`sanad_matn_fields`, from the audit's `split_chain_matn`): the sanad runs through the reporting verb («قال:», «أنه قال:») and a
  following «قال رسول الله ...»; the matn is the rest. A continuation phrase («وبهذا السند», «وباسناده», «ومن طريقه») gives `sanad_inherits_from` = the id of the
  previous report in the work. Not confident (no clear closing verb, matn would open with another reporting verb) → both null, `split_confidence: "low"`.
  `split_kind`: `chain_and_matn`, `continuation_chain`, `no_chain` (sanad `""`), `unsplit`, `chain_only`.

## Adopted 2026-11-21 (the load session)

`LOAD_STEPS.md` was followed (production, incomplete-curation build). One correction to the parser: Sahifat al-Rida's
`tradition` is `Imami` again (`parse_openiti.py` had `Zaydi`, so `record_id` would have become `openiti:zaydi:rida_*` and all 35
ids retired; production has always held it as `openiti:imami:rida_*`). `parsed_hadiths.fixed.json` still says `Zaydi` for
`works.rida`: the live `rida-hadith/parsed_hadiths.json` equals it except that field. Rebuild this directory with
`build_fixed.py` before using it as a reference again. The structure fields load as `hadiths.sanad_ar`, `sanad_inherits_from`,
`split_confidence` and `source_notes` (`src/db/AGENTS.md` §OpenITI extraction fields).

## Id anchoring (why the parser replays the old segmentation)

Production ids are `<work>_<counter>` for zayd/rida and `rabi_<number>` for rabi; `record_id = openiti:<tradition>:<id>|<hadith_no>|<page_ref>` and `page_ref` is
the page marker last seen when the *old* parser flushed the record (the page of the next report's start). To keep every `record_id` of a surviving report,
`legacy_spans()` replays the old record boundaries (validated: it reproduces all 1,737 production `source_record_id`s, plus `zayd_0118`, byte for byte; a test
pins this). A new report maps to the legacy record containing its start line: the first keeps the id, later ones get `#2`, `#3` and the parent's `hadith_no`
/ `page_ref`; legacy records swallowed by a merge or a page-break continuation are listed in `absorbed_ids`. Rabi ids come from the printed number; a number the
old parser lost (881) has no legacy record and uses its own `page_start`. If the old segmentation is ever retired, so is this guarantee: record_ids would then change.
`page_start` is the true page of the report's first paragraph.
