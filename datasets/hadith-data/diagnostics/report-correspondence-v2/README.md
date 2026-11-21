# report-correspondence-v2 (diagnostic only, unreviewed candidates)

Version 2 of the report-correspondence job (`../report-correspondence/`, method `report-correspondence-v1`). Same task, same
pair ids, same columns, same unit (a **report**, never a narrator or chain); `basis` is still `textual_overlap` and every
row is `review_state: unreviewed`. It fixes the four known defects of v1 and adds three classes. Nothing here writes a
dataset, registry, manifest or database. Standard library only, no network, deterministic. v1 code is imported
(`correspondence_logic`, `matn_isolation`, `build_report_correspondence`, `diagnostic_common`), the grading-recovery
compiler rules are imported (`mine_grading_sources`, `extract_tirmidhi_compiler_statements`), nothing is copied.

## Commands (repository root)

```
python -B datasets/hadith-data/diagnostics/report-correspondence-v2/build_report_correspondence_v2.py   # 8.3 minutes
python -B datasets/hadith-data/diagnostics/report-correspondence-v2/measure_recall_v2.py                 # 3 minutes, after the build
cd datasets/hadith-data/diagnostics/report-correspondence-v2 && python -B -m unittest test_correspondence_logic_v2
```

`--out NAME` on the build writes to `NAME/` instead of `output/` (used for the determinism check). Two full builds with
`PYTHONHASHSEED=1` and `PYTHONHASHSEED=987` (run concurrently) gave **byte-identical** pairs CSV and JSONL, cluster
members, formula inventories, review worksheet, `summary.json`, `transition_v1_to_v2.json` and `cluster_comparison.json`
(`cmp`); `run_log.json` alone carries the wall-clock time. Build plus recall measurement stayed under 12 minutes on a
machine shared with other jobs. Peak memory was not measured (v1 sampled 706 MB; v2 holds two shingle sets per report and a
128 MB count array, so expect about 1.5 to 2 GB). `output-run2/` is the second determinism run and can be deleted.

## Inputs (SHA-256)

The v1 inputs are unchanged (corpus `feeeb38d...3a`, `pure_canon_chain.jsonl.gz` `5b335f0e...71`,
`no_chain_in_source.jsonl.gz` `59b98699...15`, registry `8dfda404...ba`, normalizer `310fbf58...64`, extractor `56ea1ae0...12`,
`classify_attribution.py` `c9060f14...76`; full table in `../report-correspondence/README.md`). New:

| Input | SHA-256 |
| --- | --- |
| `datasets/sources/external/quran-tanzil/quran-simple-clean.txt` | `228df2a717671aeb9d2ff573002bd28d6b3f973f4bc7153554e3a81663d67610` |
| `diagnostics/grading-recovery/mine_grading_sources.py` (speaker phrases per work, imported) | `bf58b1db771cfc8b16026847be3e117e2b3f1e062897549418d3faeab9a582d0` |
| `diagnostics/extract_tirmidhi_compiler_statements.py` (Tirmidhi statement rule, imported) | `f933f027b6fa390fb987b2d15ad77023fa196350e52c0b6e5c61dfe4ecc16d76` |

`output/summary.json` repeats all hashes and adds the code hashes.

## Files

| File | Role |
| --- | --- |
| `correspondence_logic_v2.py` | Pure logic: compiler cut, formula grams and flags, residual text, content-word hash, the v2 verdict |
| `build_report_correspondence_v2.py` | The job (reading, inventory, candidates, scoring, clusters, outputs, v1 comparison, worksheet) |
| `measure_recall_v2.py` | Exact all-pairs scoring of 450 sampled reports under the v2 rules; recall with and without the new signature |
| `test_correspondence_logic_v2.py` | Table-driven tests on real corpus texts, including pairs that must not match |

## Method (what changed from v1)

**3. Compiler remarks are cut before comparison.** `CompilerRules` loads the grading-recovery modules by path. For
Jami' al-Tirmidhi the cut is the earliest of every `قال أبو عيسى` and every sentence its statement extractor reports
(`هذا حديث حسن غريب`, with or without Abu 'Isa); for Abu Da'ud, Nasa'i, Muslim and Bukhari it is the first speaker phrase
that the grading-recovery map assigns to that work and that is followed by a grade term within 220 characters. 3,851
reports were cut (Tirmidhi 3,654, Abu Da'ud 122, Nasa'i 69, Muslim 6); Tirmidhi's mean compared length fell from 60 to 31
words; 160 cut reports have under 3 words left and drop out. Stored text is untouched. Known gap: Abu Da'ud remarks without
a grade term (`قال أبو داود كذا قال محمد ...`) are not cut (one such pair is in the reading, row 26).

**1. Formula inventory and residual scoring.** From the data: word 4-grams (comparison words) that occur in at least 60
reports (`FORMULA_MIN_DOCUMENTS`; 415 grams, `output/formula_inventory_4grams.csv`), plus every 5-word span that equals a
Qur'an span (`quran-simple-clean.txt`, 50,446 distinct spans). A run of flagged words is removed only when it is at least
6 words long (`FORMULA_MIN_RUN_WORDS`): short narration frames (`نهي رسول الله عن`, `فليتبوأ مقعده من النار`) are content,
and removing them erased real short reports in a first trial (see "Iterations"). The **residual** is the comparison text
without the removed runs; 10,945 reports contain one. Every candidate pair is scored twice, on the whole comparison text and
on the residual, with the v1 scorer (5-letter shingles, Jaccard, local containment). The class comes from the residual:

1. v1 thresholds on the residual (same wording J >= 0.8; variant J >= 0.25 and C >= 0.4; partial C >= 0.6 with the
   shorter side >= 15 words, residual >= 10), needing at least 3 residual words and 8 shared residual shingles;
2. otherwise a pair the v1 rules keep on the whole text **stays** a variant (residual J >= 0.15) or a partial overlap
   (residual C >= 0.45): the formula costs it its high band, not its existence;
3. otherwise, if v1 would have kept it, it is **`formula_only`**: a class of its own, not shown as a telling, kept for review.

Top inventory items (reports containing the run; `formula_inventory_top_runs.csv` has the 400 most frequent runs, 180 of
them Qur'anic): the narration frames `قال سالت ابا عبد الله عن` 547, `... عن رجل` 233, `غفر له ما تقدم من ذنبه` 137,
`وبهذا الاسناد قال قال رسول الله صلي الله عليه واله` 113, `لا حول ولا قوة الا بالله` 86, `اشهد ان لا اله الا الله` 67, the
tahlil `لا اله الا الله وحده لا شريك له له الملك وله الحمد وهو علي كل شيء قدير` 34 (as a whole run; its 4-grams occur in
many more) and `اشهد ان لا اله الا الله وحده لا شريك له` 30. Qur'an runs: `انا لله وانا اليه راجعون` 39,
`الذي لا اله الا هو` 38, `لقد كان لكم في رسول الله اسوة حسنة` 35, `غير المغضوب عليهم ولا الضالين` 29. The frame
`ثلاثة لا يكلمهم الله يوم القيامة ولا يزكيهم ولهم عذاب اليم` is caught as Qur'anic (Al 'Imran 3:77), which is how the
"three whom God will not address" pairs with different triads fall to `formula_only`.

**2. Short reports.** v1 excluded matns under 8 words. v2 prepares every report of 3 or more words and admits short ones
only by two strict rules, both on the residual, both refused for referential reports (a short matn that only points at
another, `عن النبي بمثله`: 10 tokens in `REFERENTIAL_TOKENS`):

- **`short_saying_same_wording`**: both sides under 16 words and the shorter under 8, residual Jaccard >= 0.9, at least 6
  shared shingles, length ratio >= 0.7.
- **`saying_quoted_within_longer_report`**: the shorter side is 3 to 14 words, the longer is at least twice as long and 5
  words longer, the **whole** short residual lies in one window of the longer report (local containment >= 0.95), and the
  saying is distinctive: its rarest shingle occurs in at most 60 reports (`QUOTED_MAX_ANCHOR_DOCUMENTS`). `short_side`
  names which report is the saying.

Candidates for short reports come from an inverted index over residual shingles (the two rarest shingles of the saying; a
shingle in more than 400 reports seeds nothing), not from LSH. The window LSH of v1 is unchanged for reports of 8 or more
words.

**4. Recall: the third signature.** One MinHash per report over its **rare content-word stems** (residual words, one
leading conjunction/article group stripped, words in more than 1.5 % of reports and hapax words dropped, at least 8 stems),
banded exactly as v1 (42 bands of 3 rows, one salt). It targets paraphrased tellings: wording differs, content words
survive. It added 15,140 candidate pairs (545,539 after it, 530,399 before).

**5. Clusters.** v1's star clustering with its one-to-one compound guard, unchanged, over `same_wording`,
`short_saying_same_wording`, variant and partial pairs. `saying_quoted_within_longer_report` pairs create no edge (their
reports are nodes only): a quotation is not a telling and must not merge two long reports that quote the same saying.
`formula_only` pairs add nothing. Cluster ids are the same content-addressed hash.

## Results

Reports 99,283; 95,428 with 3 or more words (v1: 88,442 with 8 or more).

### Pairs, before to after

| | v1 | v2 shown classes | v2 `formula_only` |
| --- | ---: | ---: | ---: |
| All pairs | 135,825 | 146,750 | 7,238 (total 153,988) |
| Across traditions | 8,728 | 9,152 | 1,440 |
| One tradition, different works | 93,145 | 102,384 | 3,987 |
| Same work | 33,952 | 35,214 | 1,811 |

By class (all scopes; across traditions in brackets):

| Class | v1 | v2 |
| --- | ---: | ---: |
| `same_wording` | 6,750 (109) | 6,997 (127) |
| `same_report_variant_wording` | 112,864 (6,525) | 117,563 (6,387) |
| `partial_overlap` | 16,211 (2,094) | 13,162 (1,573) |
| `short_saying_same_wording` | not matched | 820 (26) |
| `saying_quoted_within_longer_report` | not matched | 8,208 (1,039) |
| `formula_only` | not a class | 7,238 (1,440) |

What happened to the 135,825 v1 pairs (`transition_v1_to_v2.json`): 6,809 became `formula_only` (variant 4,186, partial
2,620, same wording 3; across traditions 717 + 645 + 0), 773 are no longer pairs at all (462 variants, 310 partials, 1
same wording: mostly the compiler cut, plus the stricter residual minimums), the rest kept or changed class (variant to
same wording 510, partial to variant 1,506 and so on, because the class now follows the residual). Not in v1: 8,199 quoted,
818 short, 8,528 variant, 881 partial, 81 same wording, 429 formula_only. Reports with a counterpart in another tradition
(shown classes): 7,107 in v1, 7,920 in v2 (Sunni 5,765, Imami 1,507, Ibadi 513, Zaydi 135); 5 clusters span all four
traditions (v1: 4). Tradition-pair matrix for v2 by class is in `summary.json` (`cross_tradition_matrix_by_class`).

### Precision: a fresh reading of the worksheet (178 pairs, all read by the job's author, not a reviewer)

`output/review_worksheet_150.csv` has 178 rows, not 150: the plan allots 10 pairs per variant band, 9 per partial band, 14
to same wording, 12 to short, 14 to quoted, 14 to `formula_only`. Judgement fields are blank; the reading is below. "Real"
= the two texts plainly carry the same report or the same quoted passage. "Borderline" = the wording is shared but the
shared part is a liturgical text (tashahhud, salawat, talbiya, adhan, the dua of distress `لا إله إلا الله الحليم الكريم`) or a
shared ruling/frame with a different continuation. v1's reading for the same bands is in brackets (R/B/N).

| Class and band | Read | Real | Borderline | Not a correspondence | v1 (R/B/N) |
| --- | ---: | ---: | ---: | ---: | --- |
| same wording J 0.8-1.0 | 14 | 14 | 0 | 0 | 24/0/0 |
| variant J 0.7-0.8 | 10 | 10 | 0 | 0 | 12/0/0 |
| variant J 0.6-0.7 | 10 | 10 | 0 | 0 | 10/2/0 |
| variant J 0.5-0.6 | 10 | 10 | 0 | 0 | 12/0/0 |
| variant J 0.4-0.5 | 10 | 10 | 0 | 0 | 11/0/1 |
| variant J 0.3-0.4 | 10 | 10 | 0 | 0 | 8/3/1 |
| variant J 0.2-0.3 | 10 | 9 | 0 | 1 | 8/3/1 |
| variant J 0.1-0.2 (new: kept by the rescue rule) | 10 | 5 | 5 | 0 | |
| partial C 0.9-1.0 | 9 | 8 | 1 | 0 | 11/1/0 |
| partial C 0.8-0.9 | 9 | 7 | 2 | 0 | 12/1/1 |
| partial C 0.7-0.8 | 9 | 7 | 2 | 0 | 12/2/0 |
| partial C 0.6-0.7 | 9 | 7 | 2 | 0 | 9/2/3 |
| partial C 0.5-0.6 (new, rescue rule) | 9 | 5 | 4 | 0 | |
| partial C 0.4-0.5 (new, rescue rule) | 9 | 5 | 4 | 0 | |
| `saying_quoted_within_longer_report` | 14 | 13 | 0 | 1 | |
| `short_saying_same_wording` | 12 | 11 | 0 | 1 | |
| `formula_only` (is it formula or liturgy?) | 14 | 11 correctly demoted (7 formula or frame, 4 liturgical) | 1 borderline | 2 wrongly demoted (real) | |

v1 had 7 false positives in 150 reads (the bands above plus the lower variant bands); v2 has 3 in 178 across the shown
classes (one variant, one quoted, one short), none in the partial bands. The v1 false-positive shapes are gone: the
shahada and tahlil pairs, the Qur'an-verse pairs and the `ثلاثة لا يكلمهم الله` pairs with different triads all read as
`formula_only` (rows 1 to 11). The remaining non-correspondences: a variant pair sharing only the frame `ان من اشد الناس
عذابا يوم القيامة` (المصورون / من وصف عدلا), a quoted 3-word generic phrase (`انه يؤذن بالصلاة`), a short pair of Nahj
al-Balagha chapter headings (`ومن كتاب له اليه ايضا`). The two wrongly demoted `formula_only` pairs are the Euphrates-water
report (Kamil al-Ziyarat, residual J 0.139) and Abu Sa'id ibn al-Mu'alla (`الم يقل الله يا ايها الذين امنوا استجيبوا`,
residual J 0.130): the pair is real but its overlap is half Qur'an. Counts are small (9 to 14 per cell); read them as
orders of magnitude, not as rates.

### Short reports: what they add

- `short_saying_same_wording`: 820 pairs, 26 across traditions (Sunni-Imami 25, Sunni-Ibadi 1), 717 Sunni-Sunni. Examples:
  `من قتل دون ماله فهو شهيد` (Musnad Ahmad and Man La Yahduruhu al-Faqih), `الولد للفراش وللعاهر الحجر` (Shafi'i and
  Faqih), `مطل الغني ظلم`, `اتقوا النار ولو بشق تمرة`.
- `saying_quoted_within_longer_report`: 8,208 pairs (Sunni-Sunni 6,846, Sunni-Imami 838, Imami-Imami 319, Sunni-Ibadi 142,
  Sunni-Zaydi 44, other 19). Across traditions 1,039.
- **Famous reports (carriers found in the isolated matns; pairs among carriers):**
  `لا ضرر ولا ضرار` (11 carriers: Sunni 5, Imami 6): v1 found none; v2 finds 12 cross-tradition links, all quoted (Musnad
  al-Shafi'i `hadith:pure-canon:pc_71103`, the 4-word saying, inside Al-Kafi `hadith:thaqalayn:62bf1020746c9022820d1258` and
  `...78d00595257663f5de400a64`, `...6ce8e607949132eca0d9e58a`, and Mu'jam al-Ahadith al-Mu'tabara
  `...1bfd1f5961a22415d81d98c5` in the Samura ibn Jundab story); the Sunni copies are also linked to each other (Shafi'i with Malik, short same wording).
  `اليمين على المدعى عليه` (25 carriers): v1 found none; v2 finds 34 cross-tradition links, all quoted, for example Bukhari `hadith:k6:2417` and `hadith:k6:2565` inside Faqih `hadith:thaqalayn:8ff10af1e511858453b526be`.
  The ones found before keep their links: `من كذب علي متعمدا` (Sunni-Ibadi 30 variant, Sunni-Imami 6), `من كنت مولاه فعلي
  مولاه` (Sunni-Imami 8 variant, 29 partial, 33 quoted), `إني تارك فيكم الثقلين` (19 variant or same wording, 14 quoted),
  `بمنزلة هارون من موسى` (12 variant, 31 partial, 10 quoted), `بني الإسلام على خمس` (6 variant, 2 partial; 8 pairs became
  `formula_only`), `طلب العلم فريضة` (2 variant). `إنما الأعمال بالنيات`, `أنا مدينة العلم`, `كمثل سفينة نوح` remain
  without a cross-tradition link, as in v1. Full table in `summary.json` (`famous_report_check`).

### Recall of the candidate step (`output/recall_v2.json`, 450 sampled reports, 1,255 true pairs)

Truth is every pair the v2 exact scorer would keep, for pairs touching a sampled report. v1 reported 76.8 % overall and
83.0 % across traditions on **its** truth (variant 0.2-0.3: 53 %); v2's truth is a different set (formula-only noise leaves
the hard bands), so the two are not the same experiment. The like-for-like comparison is inside v2:

| Stratum (v2 truth) | True pairs | Found, all mechanisms | Found without the content signature |
| --- | ---: | ---: | ---: |
| All pairs | 1,255 | 1,134 (90.4 %) | 1,128 (89.9 %) |
| Shown classes | 1,225 | 1,113 (90.9 %) | 1,107 (90.4 %) |
| Across traditions (shown) | 305 | 267 (87.5 %) | 264 (86.6 %) |
| Variant J 0.2-0.3 | 289 | 220 (76.1 %) | 217 (75.1 %) |
| Variant J 0.3-0.4 | 344 | 315 (91.6 %) | 312 (90.7 %) |
| Partial | 91 | 83 (91.2 %) | 83 (91.2 %) |
| Quoted saying | 57 | 55 (96.5 %) | 55 (96.5 %) |
| `formula_only` | 30 | 21 (70.0 %) | 21 (70.0 %) |

**The third signature is cheap and weak**: +6 of 1,255 pairs (+0.5 point), +3 of 289 in the 0.2-0.3 band, +3 across
traditions. Rare content words alone do not reach the paraphrases that letter shingles miss; the pairs still missed are
tellings with the same content in different words (about a quarter of the 0.2-0.3 band, 12 % of the cross-tradition
pairs). That is the case for the embedding pass below, not for more band tables.

### Clusters

20,576 clusters (v1: 17,536; more because partial-only reports and singletons of the new classes are now nodes). Largest
twenty: **64, 61, 53, 51, 51, 50, 47, 47, 43, 43, 42, 42, 41, 41, 40, 40, 39, 38, 38, 37** (v1: 61, 60, 60, 58, 55, 55, 50,
49, ...). The 61-member family of v1 is *not* a tahlil family: it is the Prophet's refuge supplication (`اللهم اني اعوذ بك
من عذاب جهنم وعذاب القبر وفتنة المحيا والممات وفتنة المسيح الدجال`) and stays whole (61, one piece) because its members
really share the supplication. The family held by the tahlil is v1's 60-member cluster (98 % of its members contain
`لا اله الا الله وحده لا شريك له`; centre `hadith:k6:1123`, Ahmad/Nasa'i/Muslim/Bukhari): it falls to **14 pieces, the
largest 10**. Two smaller tahlil clusters (17 and 14 members) fall to 8 and 6 pieces (largest 4). Of v1's largest twenty
families, 13 are essentially unchanged (90 % or more of the members in one piece, ten of them whole), two shatter (the tahlil
family above and a 48-member Imami cluster that becomes 38 pieces, largest 10) and five are trimmed to 60-87 %; details
in `cluster_comparison.json`. A family can still grow: the largest v2 cluster is 64
because the rescue rule and the new short pairs add edges.

## Iterations (so the numbers can be trusted)

The first build removed every 4-gram found in 120 or more reports and applied the residual with minimums of 5 words and 12
shingles. Reading its `formula_only` sample showed 6 of 14 demoted pairs were real: narration frames such as
`نهي رسول الله عن` and `من قام رمضان ايمانا واحتسابا` are 30 to 50 % of a short report. Changes made before the final
build: runs under 6 flagged words are not removed; the v1 class is kept when the residual still overlaps (rescue rule);
residual minimums lowered to 3 words and 8 shingles; referential reports excluded from short classes (5 of 12 sampled
short pairs and 4 of 14 quoted pairs were `عن النبي بمثله`); quoted sayings need a distinctive anchor (a 3-word generic
phrase of common words matched dozens of reports). The reading above is of the final output only.

## Spec for an embedding pass (not built; no model was downloaded and no API was called)

- **Which text.** The matn after isolation and the compiler cut, with vocalization and tatweel removed but orthography and
  word order kept (not the letter-folded comparison text), for reports with at least 8 comparison words after formula
  removal. Reports under 8 words stay with the exact short index; reports over 128 words are embedded as 64-word windows
  with 16 words overlap and compared by the best window pair.
- **Model class.** A multilingual dense retrieval encoder with Arabic support and an 8k-token window, of the BGE-M3 class
  (about 560 M parameters, 1,024 dimensions, cosine), run offline on a pinned revision; record model id, revision, licence
  and prompt format in `model_registry.json`. Same-language Arabic only; no translation step.
- **Where vectors live.** A loader-owned derived table `report_embeddings` (`hadith_id`, `model_id`, `embedded_text_sha256`,
  `window_no`, `vector halfvec(1024)`), indexed with the vector extension (VectorChord or pgvector HNSW), keyed so that a
  change of Arabic text or of the cut rule invalidates the row. Vectors are never exposed to the site.
- **Candidates.** For every report the top 20 neighbours by cosine, excluding pairs already in
  `report_correspondence_candidates`, pairs whose textual class is `formula_only`, and same-work near neighbours above the
  v2 same-wording line. Keep a pair when cosine is at or above a threshold calibrated on a 150-pair reading by cosine band
  (as done here for text bands). Score the surviving pair with the v2 exact scorer too and store those numbers.
- **Labelling.** `basis = 'semantic_similarity'`, `relation_class = 'semantic_similarity'` (a new class value, never merged
  with the three textual classes), columns `cosine`, `embedding_model_id`; it never enters star clustering and is shown, if
  at all, as "similar content, different wording" after review. Its precision needs its own reading; the expected failure
  is shared topic (ritual purity, inheritance) with different rulings.

## Load spec for the schema owner (no `src/`, `drizzle/`, projection or loader file was touched)

`report_correspondence_candidates` (columns as in `../report-correspondence/README.md`), changes:

1. **`relation_class`** gains three values: `short_saying_same_wording`, `saying_quoted_within_longer_report`,
   `formula_only`. Constraint becomes the six values (plus `semantic_similarity` later).
2. **New columns** (all nullable so v1 rows still load): `jaccard_full real`, `containment_full real`,
   `words_residual_a integer`, `words_residual_b integer`, `short_side text check in ('a','b')` (which report is the saying;
   null for other classes), `compiler_cut_a boolean`, `compiler_cut_b boolean`, `found_by text`
   (`window_lsh`, `content_lsh`, `short_index`, joined with `+`). In v2 rows `jaccard`, `containment`, `shingles_*` are the
   **residual** scores that decided the class; `words_a`/`words_b` are comparison words after the compiler cut.
3. **`cluster_id`** is empty (load as null) for 1,028 pairs, all of them `formula_only` or involving a report that sits in no
   shown pair. The page must not require it. `report_correspondence_cluster_members` is as before (59,423 rows); cluster ids
   change because membership changes.
4. **Method version.** `method_version = 'report-correspondence-v2'`. The unique key (`hadith_id_a`, `hadith_id_b`,
   `method_version`) lets v1 and v2 rows coexist; load v2 as a new stream and switch the page's active version in one config
   value, then drop v1 rows. `pair_id` is the same hash of the two ids in both versions and `arabic_sha256_a/b` are computed
   on the same `text_ar`, so **reviewer decisions, keyed on the pair with `bound_arabic_sha256`, survive unchanged**.
   Re-queue rather than reapply in two cases: a `confirmed` decision on a pair that v2 now classes `formula_only` (the
   reviewer may have been judging the formula), and any decision whose pair is absent from v2 (462 variants, 310 partials,
   1 same-wording pair of v1 disappear: they are mostly Tirmidhi pairs held by a shared compiler remark).
5. **`report_correspondence_decisions.reviewed_relation`** vocabulary gains `shared_liturgical_text` (tashahhud, salawat,
   talbiya, adhan, shared supplication wording: 15 of the 54 partial pairs read were this).

**Display rule recommended from the fresh reading** (shown with the "machine-found, unreviewed" marker unless confirmed):

| Show | Evidence in the reading | Pairs | Across traditions |
| --- | --- | ---: | ---: |
| `same_wording` | 14/14 real | 6,997 | 127 |
| `same_report_variant_wording` with `jaccard` >= 0.2 | 49 real, 1 not, of 50 | 116,207 | 6,259 |
| `partial_overlap` with `containment` >= 0.6 | 29 real, 7 borderline (liturgical), 0 not, of 36 | 12,610 | 1,489 |
| `short_saying_same_wording` | 11/12 | 820 | 26 |
| `saying_quoted_within_longer_report`, in its own section | 13/14 | 8,208 | 1,039 |

That is 144,842 pairs, 8,940 across traditions. **Reviewer screen only (never on the reading page):** `formula_only`
(7,238 pairs; 11 of 14 read were right to demote, 2 were real, so the screen is also the place to rescue them),
variant with `jaccard` < 0.2 (1,356 pairs; 5 of 10 real), partial with `containment` < 0.6 (552 pairs; 5 of 9 and 5 of 9
real, the rest liturgical). v1's suggested thresholds (variant 0.4, partial 0.7) are not needed any more: the false
positives they hid were the formula-carried ones.

**Labelling "saying quoted within a longer report".** Never a "telling" of the report and never counted in "N tellings" or a
cluster. On the saying's own page (the `short_side` report): section "Quoted within longer reports", one row per longer
report (work, number, tradition) with the matching passage highlighted. On the longer report's page: "Quotes the saying
«...»" with a link to the report that is the saying alone, if one exists in the pair set. Say "quotes" and "contains", not
"narrates" or "the same hadith"; it asserts nothing about who said it, the isnad, or authenticity. `short_saying_same_wording`
appears with the tellings but carries the marker "short saying: identical words alone are weak evidence of one
transmission". Pairs flagged `compiler_cut_*` need no label.

## Outputs (`output/`, git-ignored; rebuild with the commands)

| File | Rows |
| --- | ---: |
| `report_correspondence_pairs.csv` / `.jsonl` | 153,988 each (v1 columns, then `jaccard_full`, `containment_full`, `words_residual_a`, `words_residual_b`, `short_side`, `compiler_cut_a`, `compiler_cut_b`, `found_by`) |
| `report_correspondence_cluster_members.csv` | 59,423 |
| `formula_inventory_4grams.csv` | 415 (grams in at least 60 reports) |
| `formula_inventory_top_runs.csv` | 400 (most frequent removed runs, with kind) |
| `review_worksheet_150.csv` | 178 (blank judgement fields; compared text and removed spans shown) |
| `transition_v1_to_v2.json`, `cluster_comparison.json`, `recall_v2.json`, `summary.json`, `run_log.json` | |

## Deferred, with the trigger to revisit

- **Liturgical texts** (tashahhud, salawat, talbiya, adhan, the distress dua) are shared wording in different reports, not a
  hadith in two tellings; 15 of 54 partial pairs read were this. A liturgy inventory is hand work (curated list), not a
  frequency cut; revisit when the reviewer screen shows the volume.
- **Sub-6-word frames** such as `من كان يؤمن بالله واليوم الاخر` followed by different content still pair at variant J 0.2-0.3
  occasionally (1 in 10 in that band); they are the cost of keeping short real reports.
- **Abu Da'ud remarks without a grade term** are not cut; add a rule when the compiler-statement job gets one.
- **The 4,321 flagged Imami rows** and referential Muslim reports are unchanged from v1.
- **Embedding pass**: see the spec; trigger is the cross-tradition recall of 87 %, or a reviewer asking for paraphrase links.
