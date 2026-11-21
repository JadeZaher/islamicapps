# assessments (consolidated, attributed gradings and narrator verdicts)

Every report grading and narrator verdict on disk that can be attributed to a named scholar, compiler or printed work,
consolidated into load-ready rows. One row is one **perspective**: one scholar's (or one work's) words about one report
or one narrator, kept verbatim, with one complete citation. Nothing is computed or aggregated, no two scholars' rulings
are merged, competing verdicts sit side by side, and every row is `review_state: candidate_only`.

Written only into this directory. The external SQLite files are opened `mode=ro&immutable=1`; nothing from a download
directory is executed. No database, network or npm. Deterministic: a second build gives byte-identical `.gz` files.

## Commands (repository root; about 1 minute in all)

```
python -B datasets/hadith-data/assessments/build_assessments.py      # rows, summary, exclusions, overstatements, manifest
python -B datasets/hadith-data/assessments/build_review_sample.py    # Tirmidhi 785 dispositions, 150-row worksheet
python -B datasets/hadith-data/assessments/validate_citations.py     # pre-load citation check (exit 1 on any failure)
cd datasets/hadith-data/assessments && python -B -m unittest test_assessment_logic
```

## Inputs

SHA-256 of every input and code file is in `manifest.json` (`inputs_sha256`, `code_sha256`). The main ones:

| Input | SHA-256 (prefix) |
| --- | --- |
| projection `2026.11.21.3` `canonical/hadiths.csv` (= production dataset version `e2430eae…`) | `2afcb9e4b246` |
| projection `canonical/hadith_assessments.csv` (the loaded Imami rulings) | `913aa025ce8b` |
| `diagnostics/grading-recovery/pure_canon_closing_statement_candidates.jsonl` (workbook column L) | `5423440b4f01` |
| `archive/sheikahmad-pure-canon/pure_canon.jsonl` (column B matn and C chain, for the join) | `0cb5ec01959b` |
| `diagnostics/biography-verification/rijal_entries_taqrib.jsonl.gz`, `lexicon_rijal_links.jsonl.gz` | `a0606d1a73b8`, `56cad0c9d003` |
| OpenITI Tahdhib al-Kamal, Rijal al-Najashi, Rijal al-Tusi, al-Fihrist | `f4f26e71dd9c`, `a34bc95dbf6a`, `955b2b7114a5`, `1c4975a18ca0` |
| rijal lane `datasets/hadith-data/rijal/output/` (entry ids, passages, statements, works; read only) | in `manifest.json` |
| `reconciled/external_narrator_lexicon_links.jsonl.gz`, `hadith_kg_narrators.jsonl.gz` | `2772ffb4f8b1`, `ee220cdaf630` |
| hadith-kg `hadith-kg.db` (rev. 8ae7e3d5), Riwayat `hadith_master.db` (v1) | `d528084321e7`, `278e674ee72a` |
| `diagnostics/biography-recovery/narrator_assessment_candidates.jsonl` (lexicon labels) | `7358595959d4` |

## Licences of the outputs

Each row names its source short reference (`src/lib/sources/registry.ts`) and licence in `citation.source`.
- Rows from OpenITI rijal texts (`RIJ`): **CC BY-NC-SA 4.0**, non-commercial, share alike, attribution to OpenITI
  release 2025.1.9 and the edition named in `citation.edition`.
- hadith-kg rows (`HKG`): **CC BY 4.0**, credit "hadith-kg by emadjumaah, revision 8ae7e3d5", with this project's change
  stated (statements filtered and re-keyed; not reviewed). Each row is that dataset's record of the critic's statement:
  credit both the critic and hadith-kg.
- Thaqalayn rulings (`THQ`): CC BY 4.0. sunnah.com (`SUN`), Pure Canon (`NMC`), narrator lexicon (`MSD`): by the
  owner's permission (2026-11-21).

## Files

| File | Rows | What |
| --- | ---: | --- |
| `hadith_assessments.jsonl.gz` | 18,486 | Report gradings, one per perspective (kinds below) |
| `compiler_criterion_links.jsonl.gz` | 14,966 | Bukhari 7,370 and Muslim 7,596 reports linked to their compiler's criterion: its own basis, never a verdict |
| `hadith_assessments_held_back.jsonl.gz` | 4,475 | Every statement not emitted, with its reason |
| `pure_canon_column_l_joins.jsonl.gz` | 4,286 | How each column-L row of the six books was (or was not) joined to a K6 report |
| `tirmidhi_785_dispositions.jsonl.gz` | 785 | Final disposition of each statement the earlier pass held back |
| `narrator_assessments.jsonl.gz` | 114,841 | Narrator verdict perspectives (kinds below) |
| `narrator_assessments_held_back.jsonl.gz` | 1,007 | Statements whose critic or subject cannot be fixed |
| `taxonomy_overstatements.json` | 341 terms / 2,246 rows | Loaded Imami canonical values that state more than the grader did |
| `external_exclusions.json` | | What hadith-kg and Riwayat carry that looks like grading, and why none of it is taken |
| `summary.json` | | All counts: rows by kind and scholar, coverage before and after, citations, aspects |
| `sample_60_judged.csv` | 60 | Stratified sample read against the Arabic, with judgement and status after the fixes it caused |
| `review_worksheet_150.csv` | 150 | Random cited rows with blank reviewer columns |
| `manifest.json` | | Input, code and output hashes |

## Report gradings (`hadith_assessments.jsonl.gz`)

| `basis_kind` | Grader | Rows |
| --- | --- | ---: |
| `cited_ruling_in_commentary` (already loaded; ids unchanged) | al-Majlisi 13,866; al-Mohseni 822; al-Behbudi 232; al-Najafi 102 | 15,022 |
| `compiler_statement_in_report_text` | al-Tirmidhi 3,328; al-Nasa'i 39; Abu Dawud 21; Ibn Majah 2; Muslim 1 | 3,391 |
| `compiler_statement_in_closing_column` (Pure Canon column L, joined) | al-Tirmidhi | 70 |
| `ruling_quoted_by_compiler` | al-Bukhari, as quoted by al-Tirmidhi | 3 |

**How a compiler statement is recognised** (`assessment_logic.classify_report_statement`): the sentence must grade a
report as its grammatical subject (`هذا حديث …`, `إسناده …`, `حديث فلان حديث …`); the speaker must be the compiler
(`قال` + his kunya, or, in the Jami' of al-Tirmidhi only, an unmarked statement with no other speaker since the report
ended); `حديث فلان` must name a word that occurs in this report (whole words; `عمر` never matches `عمرو`); `الحسن`,
`والصحيح ما روى` and `وهم` as "and they" are not grades. `grade_raw` is the verbatim clause (`هذا حديث حسن صحيح`);
`citation.passage_ar` is the exact span `text_ar[start:end]`.

**Pure Canon column L.** Rows of the four loaded Pure Canon works join by `pc_*` id. Six-book rows join to K6 only when
the Pure Canon matn (blessing formulas removed, letters only, at least 40 letters; else its opening and closing 60
letters) occurs in exactly one K6 report of the same work, is itself unique in that work, and the Pure Canon chain's
names (transmission words dropped, `ابن` as `بن`) are contained in the K6 chain or agree in their opening. 2,316 joined,
112 held because the chain differs, 977 too short, 839 no K6 match, 42 not unique. A closing statement that
repeats an in-text statement of the same compiler is recorded as `corroborated_by` on that row (939), not as a new row;
a statement that follows a further `حدثنا` in the closing text belongs to the next report and is held (46).

**The 785 held back earlier** (`tirmidhi_785_dispositions.jsonl.gz`): 677 promoted (al-Tirmidhi 672, al-Bukhari as
quoted 3, two that contain al-Tirmidhi's own clause before he quotes al-Bukhari), 108 held: 30 comparative
(`أصح شيء في هذا الباب`, not a grade), 65 with no report-subject grading clause, 8 grading a different named report,
5 another authority speaking.

## Narrator verdicts (`narrator_assessments.jsonl.gz`)

| `basis_kind` | Source | Rows | Attached to a lexicon narrator |
| --- | --- | ---: | ---: |
| `rijal_entry_verdict` | Ibn Hajar, *Taqrib* (span from the first maratib term) | 7,448 | 5,166 rows |
| `companion_status_in_rijal_entry` | Ibn Hajar, *Taqrib* | 751 | |
| `critic_quoted_in_rijal_work` | critics as quoted by al-Mizzi, *Tahdhib al-Kamal* | 11,950 | |
| `listed_in_work` | Ibn Hibban's *al-Thiqat*, as reported by al-Mizzi | 2,318 | 7,333 Mizzi rows in all |
| `rijal_entry_verdict` | al-Najashi 694; al-Tusi, *Rijal* 336, *al-Fihrist* 131 | 1,161 | none (no Imami narrator authority is loaded) |
| `dataset_record_of_critic_statement` | hadith-kg `aqwal`, 803 named critics | 59,979 | 8,469 rows (all hadith-kg kinds) |
| `listed_in_work` / `companion_status_statement` | hadith-kg | 10,880 / 3,309 | |
| `narrator_lexicon_source_not_stated` | the lexicon's `[ ع - ثقة ]` cells | 17,045 | all; `citation_status: not_yet_cited` |

**Al-Mizzi's critics.** `قال X: …` gives critic X; `قال X، عن Y: …` gives critic Y quoted through X (`reporter_ar`);
`سألت أبي عنه فقال` resolves the father only through a fixed table (Ibn Abi Hatim → Abu Hatim; 'Abd Allah or Salih b.
Ahmad → Ahmad); `قال يحيى بن معين، وأبو زرعة، والنسائي: ثقة` gives one row per named critic
(`shared_statement_named_critics`); `في موضع آخر` repeats the previous critic. Held: a question about someone else
(685), a relational critic not in the table (279), a subject that may be a relative (27). The opening twelve words must
hold a jarh/ta'dil term; death dates and narrative are not verdicts. Top critics: Ibn Hibban 2,336, Abu Hatim 2,016,
al-Nasa'i 2,008, Ibn Ma'in 1,967, Abu Zur'a 691, Ahmad 578, al-'Ijli 456, Abu Dawud 421.

**Al-Najashi and al-Tusi** (read from OpenITI through `rijal_sources`, mapped to the rijal lane's `rijal_entry:` ids;
17,812 rows match a rijal-lane statement id in `rijal_lane_statement_ids`): a clause holding one of their
terms (`ثقة`, `ثقة ثقة`, `ضعيف`, `واقفي`, `غال`, `عامي`, `وجه في أصحابنا` …) in the author's own voice. Held when quoted
(`قال أبو العباس`, `ذكره الكشي وقال`) or when the clause's subject is a relative (`وأخوه الحسن … ثقة`); the Imams' speech
in quotation marks is ignored.

**hadith-kg `aqwal` (127,863).** Excluded: 11,660 attributed to `تعليق` (editorial commentary, not a critic), 41,823
mentions with no verdict (`ذكره في تاريخ دمشق`, `… ولم يذكر فيه جرحا ولا تعديلا`), 212 `سكت عنه`. The book is named in the
statement itself for some (`قال في التقريب` 7,385); otherwise hadith-kg does not say which of the critic's works, and
`citation.work.title_note` says so. Al-Najashi, al-Tusi and al-Kashshi in hadith-kg's critic register are `imami`; every
other critic defaults to `sunni` (`tradition_basis` says so; for the owner to confirm). Linked to our narrators only
through `external_narrator_lexicon_links` (1,194 hadith-kg links); otherwise attached to `narrator:hadith-kg:<id>`.

## Canonical terms: never flattened

`grade_canonical` / `verdict_canonical` is set only when the whole term, minus its subject, is one term the glossary's
scheme for that tradition names: Imami `صحيح حسن موثق ضعيف مجهول مرسل معتبر مختلف فيه` and `ضعيف على المشهور`; a
Sunni compiler's bare `صحيح حسن ضعيف مرسل موضوع`; narrators `ثقة، ثقة ثبت، صدوق، لا بأس به، ليس به بأس، مجهول، ضعيف،
متروك، كذاب`. Everything else (`حسن صحيح`, `صدوق يهم`, `مقبول`, `ثقة في نفسه`, `مجهول الحال`) keeps its words with a
null canonical. **Overstatements in the loaded Imami rows** (`taxonomy_overstatements.json`, 2,246 rows, for the owner):
every `… كالصحيح` loaded as sahih (739: `حسن كالصحيح` 411, `موثق كالصحيح` 156, `مجهول كالصحيح` 118 …); `مرفوع` as mursal
(268); `حسن أو موثق` and other alternatives loaded as the stronger one (236); `مرسل كالموثق` and `كالموثق` as muwaththaq;
`صحيح على الظاهر` as sahih (63); compounds with `معتبر` incl. `ضعيف على المشهور معتبر عند ي` as mu'tabar (79). This build
proposes null for each, with the reason.

## Excluded as machine-computed (`external_exclusions.json`)

- hadith-kg report and chain grades: `hadiths.matn` (715,790), `sanads.matn` and `sanads.hukum` (577,024),
  `sanads.max_rank`, meaning-group and taraf labels, `rawis.rank`. **How told apart:** none names a grader; all
  577,024 `hukum` values are in a few templated frames (`إسناد ضعيف فيه X وهو ضعيف الحديث`, 0 name a scholar or use
  `صححه`/`حسنه`); and the chain label follows the weakest narrator's rank (contingency in the file: rank 3 → `صحيح`
  120,972 of 131,625; rank 10 → `شديد الضعف` 33,913 of 35,636), i.e. it is computed from ranks.
- Riwayat: no report grading and no critic statement in any table; narrator `tradition`, `madhhab`, `tabaqa` and the
  identification confidences are the corpus's own labels or model output. Nothing taken.
- So no report grading from either dataset reaches the crosswalked reports.

## Coverage

Reports with at least one attributed grading (collection labels and criterion links not counted):

| Tradition (reports) | Before (production) | After |
| --- | ---: | ---: |
| Imami (33,225) | 14,787 (al-Kafi 13,869, Faqih 387, Mu'jam 428 …) | 14,787 (unchanged; canonical corrections proposed) |
| Sunni (64,356) | 0 | 3,375: Tirmidhi 3,312 of 4,214, Nasa'i 39, Abu Dawud 21, Ibn Majah 2, Muslim 1 |
| Ibadi (1,004) | 0 | 0 |
| Zaydi (698) | 0 | 0 |

158 reports carry rulings from two or more graders that differ in wording (Imami 233 and Sunni 3 reports have two or
more graders). Production before: 44,937 `hadith_assessments` rows (15,022 Imami rulings, 29,915 Pure Canon `ثابت`
collection labels; measured by SELECT on 2026-11-21).

Narrators (24,326 lexicon narrators loaded): before, 0 with an attributed verdict (the 20 production rows have no critic).
After, **5,589** with at least one named critic, 2,751 with two or more critics, **726 where named critics' mapped terms
differ** (the disagreement is the content), 11,677 more with only a lexicon label (not yet cited). Further perspectives
attach to a rijal entry or an external narrator only: hadith-kg 65,699 rows, Mizzi 6,935, Taqrib 3,033, Najashi 694,
Tusi 467.

**Ibadi and Zaydi.** Their texts hold no grading: al-Rabi''s `قال الربيع` glosses words, `قال جابر` and Zayd b. 'Ali's
statements are legal or doctrinal, and no sentence grades a report. hadith-kg's critics speak about 88 narrators in
hadith-kg's Musnad al-Rabi' chains (498 statements) and 8 in Musnad Zayd (52): these are Sunni critics' verdicts and
are labelled so, never as Ibadi or Zaydi. **What would be needed:** for Ibadi, Nur al-Din al-Salimi's *Sharh al-Jami'
al-Sahih* (commentary with his judgements) and Ibadi biographical works (al-Darjini's *Tabaqat al-Masha'ikh*, al-Shammakhi's
*Siyar*); for Zaydi, al-Siyaghi's *al-Rawd al-Nadir* on Musnad Zayd, Ibrahim b. al-Qasim's *Tabaqat al-Zaydiyya* and
al-Jundari's *Tarajim al-Rijal*, each as a cited text (OpenITI or a permitted edition) parsed like the rijal works here.
For Sunni beyond al-Tirmidhi: the 35,487 Pure Canon rows labelled `ألباني` (and 9,276 `تليدي`) are a scholar's selection,
but the workbook does not name which of his books; once named and permitted they would become per-work criterion
links, not individual verdicts.

## Citations (owner rule: one rigorous shape everywhere)

Every row carries `citation` = `work` {author, title, tradition; `quoted_in` for a critic quoted inside another work},
`edition` (as the source names it), `locator` (volume, page, entry or hadith number; or dataset, version and record id),
`passage_ar` (verbatim) with `char_span` where it comes from a stored text (`hadiths.text_ar`, or the rijal lane's entry
`passage_ar`), `source` {code, licence} from the registry, and `text_sha256` of the text read; plus `citation_status`
`cited` / `not_yet_cited` with `citation_missing`. `validate_citations.py` checks every row and re-verifies each
in-text span against the report Arabic and its hash.

| Kind | Cited | Not yet cited (reason) |
| --- | ---: | ---: |
| Report gradings (all four kinds) | 18,486 | 0 |
| Compiler criterion links | 0 | 14,966 (the compiler's stated conditions are not stored from a reviewed edition) |
| Narrator perspectives from rijal works and hadith-kg | 97,796 | 0 |
| Narrator lexicon labels | 0 | 17,045 (the lexicon does not say whose verdict or which work) |

## Perspective matrix (owner, 2026-11-21) and aspects

Each row has `perspective_id` (compatible with the rijal lane: `perspective:<work>` and
`perspective:<work>:quoted:<critic>`; `perspective:hadith_kg:critic:<alem id>`; for reports
`perspective:<grader>:<basis_kind>`), and for narrators `aspect`, using the rijal lane's keys **`verdict_term`,
`reliability_qualifier`, `doctrinal_or_other_note`, `generation_or_imam`**, with `aspect_detail` listing what the words
themselves speak to: `reliability`, `precision_memory`, `doctrine`, `specific_defect`, `companion_status`, or
`not_distinguished`. Example: Taqrib `صدوق يهم ورمي بالإرجاء` → `verdict_term` [reliability, precision_memory, doctrine].

## Load spec (for the schema owner; nothing here edits `src/` or `drizzle/`)

**`hadith_assessments`** (pipeline table). Columns map directly: `id`, `hadith_id`, `tradition_id`, `grade_scheme`,
`ordinal`, `kind`, `grader`, `grade_raw`, `grade_canonical`, `cited_work`, `cited_volume`, `cited_page`,
`citation_raw`, `source_field`, `review_state` (`candidate_only`). Ids: `assessment:<record_id>:<tradition>:<source_field>:<NN>`
(`source_field` `text_ar`, `pure_canon_column_l`, `gradings_full`, `collection_membership`), so the natural key
(hadith, tradition, source_field, ordinal) stays unique. Add:
- enum `assessment_kind`: keep `cited_ruling` for `ruling_quoted_by_compiler` but add column `as_quoted_by text`;
  add column `basis_kind text` (or an enum: `cited_ruling_in_commentary`, `compiler_statement_in_report_text`,
  `compiler_statement_in_closing_column`, `ruling_quoted_by_compiler`, `compiler_criterion`);
- `statement_ar text`, `char_start int`, `char_end int`, `arabic_sha256 text` (load check: `substring(text_ar from
  char_start + 1 for char_end - char_start) = statement_ar` and the hash equals `hadiths.arabic_sha256`, else refuse);
- `citation jsonb`, `citation_status text check in ('cited','not_yet_cited')`, `source_code text`, `perspective_id text`,
  `corroborated_by jsonb`.
- For the 15,022 loaded Imami rows: update only `grade_canonical` where `taxonomy_overstatements.json` proposes null, and
  only after the owner approves that list. Criterion links load as `kind = compiler_criterion`, `grade_canonical` null,
  and must never count toward `grading_status = cited_assessments`.
- Note: the loader's key (hadith, tradition, grader) in `batch-loaders.ts` would merge two rulings by one grader on one
  report; key by `id` instead.

**`narrator_assessments`** (today curation-owned with `narrator_id not null` and a `narrator_verdict` enum). These rows
are pipeline rows, so either a new pipeline table `narrator_assessment_candidates` or relax the current one. Needed:
- `narrator_id` nullable, plus `subject_ref text not null` (`rijal_entry:<work>:<n>`, `narrator:hadith-kg:<id>`,
  `lexicon:<scholar_indx>`) and `link_basis`;
- `critic` (display), `critic_ar`, `critic_key`, `as_quoted_by`, `reporter_ar`, `tradition_id`, `tradition_basis`;
- `verdict_raw text not null` (verbatim; Taqrib and Najashi spans are letter-folded, with the verbatim in
  `citation.passage_ar`), `verdict_canonical narrator_verdict null` (the current enum works; `mukhtalaf_fihi` and
  `not_applicable` are never produced here), `basis_kind` (`rijal_entry_verdict`, `critic_quoted_in_rijal_work`,
  `dataset_record_of_critic_statement`, `listed_in_work`, `companion_status_in_rijal_entry`, `companion_status_statement`,
  `narrator_lexicon_source_not_stated`), `aspect`, `aspect_detail text[]`, `perspective_id`;
- `citation jsonb`, `citation_status`, `source_code`; a check that `citation_status = 'cited'` before `published`.
- Overlap with the rijal lane: both lanes read the same rijal works. Load one row per perspective: these rows carry the
  rijal lane's `rijal_entry:` id and matching `rijal_lane_statement_ids`; prefer these where they resolve the critic
  more finely (al-Mizzi's quoted critics), and do not load both for the same statement id.

**Presentation.** Report page: assessments grouped by tradition (Ibadi, Imami, Sunni, Zaydi, alphabetical, no default),
one line per perspective: grader (or "al-Bukhari, as quoted by al-Tirmidhi"), the Arabic term, the canonical term only
when set, the locator, and the source reference; a compiler's criterion shown apart from rulings. Narrator page: a matrix
with one row per perspective (critic and work; "as quoted by al-Mizzi"; "hadith-kg's record of Abu Hatim"), grouped by
tradition the same way, columns the aspect keys, cells the verbatim words. Never a consensus, count or computed verdict;
where critics differ, show both. Lexicon labels sit last, marked "narrator lexicon, source not stated".

## Sample read (60 rows, `sample_60_judged.csv`)

Read against the Arabic (term matches the passage; right scholar; right report or narrator): **52 right, 7 doubtful,
1 wrong.** Reports 24 / 5 / 1; narrators 28 / 2 / 0. The wrong row and three doubtful ones were Pure Canon closing
statements that followed a second chain (pc_28711: `وحديث عبادة حديث حسن` was this report's grade, but the row took
the next report's `هذا حديث حسن غريب`); one doubtful came from `عمر` matching inside `عمرو`. Both were fixed and the four
rows are now held; the file records each row's status after the fixes. Remaining doubts: al-Nasa'i's `هذا خطأ` correcting a
name in the chain (kept, canonical null), a Mizzi critic written only `يحيى`, and hadith-kg crediting al-Duri where
the judgement is usually Ibn Ma'in's as transmitted by al-Duri. The narrator-lexicon labels are correctly not cited.

## Tests

`test_assessment_logic.py` (22 table-driven tests on real passages): compiler-voice and named-subject decisions,
non-gradings that must not be emitted (`الحسن` as a name, `وهم` as "and they", Abu Dawud's narrator remark, a transmitter
speaking), the closing-column cut, Imami non-rulings and every flagged overstatement, al-Mizzi critic resolution and held
cases, al-Najashi/al-Tusi voice and relative subjects, hadith-kg statement kinds and the editorial label, aspects.
