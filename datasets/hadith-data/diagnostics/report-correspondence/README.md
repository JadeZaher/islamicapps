# report-correspondence (diagnostic only, unreviewed candidates)

Which reports carry the same matn in more than one tradition or work? This job links **reports**, never narrators or
chains: each copy keeps its own sanad, tradition and source. A textual overlap is evidence that two reports
correspond. It is not a ruling that they are the same hadith, and it says nothing about authenticity or about who
narrated from whom. Every row is `basis: textual_overlap`, `review_state: unreviewed`.

Nothing here writes a dataset, registry, manifest or database. Standard library only, no network, deterministic.

## Commands (repository root)

```
python -B datasets/hadith-data/diagnostics/report-correspondence/build_report_correspondence.py   # about 5.5 minutes
python -B datasets/hadith-data/diagnostics/report-correspondence/measure_lsh_recall.py            # about 1.5 minutes, after the build
cd datasets/hadith-data/diagnostics/report-correspondence && python -B -m unittest test_correspondence_logic
```

Peak memory sampled at 706 MB. Two full builds with `PYTHONHASHSEED=1` and `PYTHONHASHSEED=987` gave byte-identical
outputs (every CSV, JSONL and `summary.json`); `run_log.json` alone carries the wall-clock time.

## Inputs (SHA-256)

| Input | SHA-256 |
| --- | --- |
| `datasets/hadith-data/development/incomplete-curation/all_hadiths_unified.incomplete.csv.gz` (the 37-column file the Postgres exporter loads; has `record_id`) | `feeeb38dae008bed993fab7ccdf6fc7399e985296d5a0c36b59534327e003a17` |
| `datasets/hadith-data/reconciled/pure_canon_chain.jsonl.gz` | `5b335f0e81853c65ca05761ea188abf3772256a86897afbc8a3c43396371bb19` |
| `datasets/hadith-data/reconciled/no_chain_in_source.jsonl.gz` | `59b98699b696002998df43bcd5d0626d69a4aa46caf443d12ce8400f384c15c5` |
| `datasets/hadith-data/neo4j_export/source_work_registry.json` | `8dfda404ca64d217cad7d366a1941d59009220a47705eb4ccca08d4bc2cbe2ba` |
| `datasets/hadith-data/regen_unified_csvs.py` (normalizer, imported) | `310fbf58885b53700a17698c1ffcd3231f24a55ba7ea8e8c1c08b64864e78147` |
| `datasets/hadith-data/extract_isnad_unified.py` (sanad/matn boundary, imported) | `56ea1ae0968d1cddfa4d0dcdd630e8145e897a1b82413cb3c271cf8023708212` |
| `datasets/classify_attribution.py` (`_norm`, imported through the normalizer) | `c9060f141cf19795f64c911885dc805c6e80c717b0aaf6322b7c4542875a76f9` |

`output/summary.json` repeats these hashes and adds the code hashes and git HEAD.

Report ids are the loader's: `hadith:<record_id>` (`neo4j_export/export_bundle.py`, `pg_export/export_postgres.py`).

## Files

| File | Role |
| --- | --- |
| `correspondence_logic.py` | Pure logic: comparison text, shingles, MinHash, LSH bands, exact scores, classes, clusters |
| `matn_isolation.py` | One row to its matn, using the sidecars, the matn column and the canonical extractor boundary |
| `build_report_correspondence.py` | The job |
| `measure_lsh_recall.py` | Exact all-pairs scoring for a fixed sample of reports, to measure what LSH misses |
| `test_correspondence_logic.py` | Table-driven tests on real corpus texts, including pairs that must not match |

## Matn isolation

Correspondence is judged on the matn only. A shared isnad formula would otherwise create matches between different
reports: the test `test_isolating_the_matn_removes_a_chain_driven_match` shows two Kafi reports with the same chain
(`علي بن إبراهيم عن أبيه عن ابن أبي عمير ...`) that the classifier keeps on their whole texts and drops on their
matns (Jaccard under 0.1).

Precedence for each row:

1. `source_text_is_matn_only`: Pure Canon rows in `reconciled/pure_canon_chain.jsonl.gz` (Ahmad, Darimi, Muwatta';
   the source ships the chain separately). `text_ar` is used after its SHA-256 matches the sidecar.
2. `no_chain_in_source`: `reconciled/no_chain_in_source.jsonl.gz` (Shafi'i, Nahj al-Balagha), same hash check.
3. `matn_column`: the dataset's `matn_ar`, accepted only when its letters occur inside `text_ar` and it does not start
   where the text starts with a chain (three or more transmission links in its first 25 words).
4. `extractor_boundary`: `extract_isnad_unified._split_on_tahweel` then `_matn_start` on the last segment, the
   extractor's own cut (no second extractor).
5. `whole_text_no_reliable_boundary` (flagged): the extractor found no matn start, or one so late that under 40
   letters remain after a chain of over 85 % of the text. The whole last segment is compared, but only when its
   first 25 words hold fewer than three transmission links (`_LINK_RE`); otherwise the row has no usable matn.

Two defects in the `matn_ar` column surfaced and are routed around, not repaired:

- **Misattached matns.** 1,597 Sunni K6 rows (Muslim 625, Tirmidhi 596, Ibn Majah 245, Nasa'i 80, Bukhari 47, Abu
  Da'ud 4) carry a `matn_ar` that is not in their own text: the `sunni_isnad.jsonl` fill joins on
  `(source, hadith_no)`, which is duplicated, so a neighbouring report's matn was attached. Using the column blindly
  would have created false cross-report matches.
- **Chain left in.** 12,617 K6 `matn_ar` values start where the text starts and still carry the isnad (Muslim 3,287,
  Nasa'i 2,540, Abu Da'ud 2,346, Bukhari 1,753, Ibn Majah 1,446, Tirmidhi 1,245). These fall back to the extractor.

OpenITI `matn_ar` (Zaydi, Ibadi, Sahifat al-Rida) is cut a few letters late (`ال:` for `قال:`); harmless for
comparison. Per-work counts are in `output/matn_isolation_coverage.csv`. `output/matn_isolation_flags.csv` lists
every row whose split is flagged or unusable, whose matn column was rejected, or whose matn comes from a no-chain
sidecar (24,103 rows).

| Tradition | Reports | Reliable split | Flagged split (whole text) | No usable matn | Under 8 words | Matched |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Sunni | 64,356 | 62,311 | 25 | 2,020 | 6,375 | 55,961 |
| Imami | 33,225 | 27,680 | 4,321 | 1,224 | 1,165 | 30,836 |
| Zaydi | 698 | 698 | 0 | 0 | 2 | 696 |
| Ibadi | 1,004 | 1,004 | 0 | 0 | 55 | 949 |

Where the flagged and unusable rows sit: Man La Yahduruhu al-Faqih (2,892 flagged: its reports mostly open with
`وسأل ...` or `قال الصادق ...` and no isnad, so the whole text is the matn plus a short attribution), Kitab al-Ghayba
(Tusi) 325 (theological prose), Kitab al-Du'afa 217 (rijal entries, not reports), 'Uyun 191, Kitab al-Mu'min 145. The
2,020 unusable Sunni rows are mostly Muslim's referential reports (`بهذا الإسناد مثله`, 948 in Muslim), which have no
wording of their own: 633 of Muslim's 948 carry `مثله`, `نحوه`, `بمعناه` or `بهذا الإسناد`. The rest, and Al-Kafi's
561, are texts where the extractor finds no matn start, typically a matn opening `في رجل ...`, `في قول الله ...` or
`أنه كان ...` straight after the chain.

Normalization is for comparison only and never stored: `regen.narrator_normalize` (NFKC, format controls,
vocalization, tatweel, alef and ya variants: `classify_attribution._norm`), `fold_persian_urdu_letter_variants`,
`fold_punctuation_and_whitespace`, `strip_blessing_formulas`; plus, in `correspondence_logic.py`, the formulas
`عز وجل`, `تبارك وتعالى`, `جل جلاله`, `صلوات الله عليه`, `عليه الصلاة والسلام`, `كرم الله وجهه`, `عجل الله فرجه`, the
abbreviation tokens `ع`, `ص`, `ع م`, `عج`, `ره`, `رض`, `صلعم`, and any non-Arabic letters (`<br>` in Thaqalayn). The
conjunction and spacing differences (`و لكن` / `ولكن`) vanish because shingles are taken over letters with spaces
removed.

## Method

Near-duplicate detection in four steps (Broder, "On the resemblance and containment of documents", 1997):

1. **Shingles.** Overlapping 5-letter shingles of the comparison text, spaces removed. Each shingle is an exact
   40-bit integer (one byte per letter), mixed with the SplitMix64 finalizer to 32 bits.
2. **MinHash signatures.** One-permutation hashing (Li, Owen, Zhang, NIPS 2012) with rotation densification
   (Shrivastava and Li, ICML 2014): 128 bins, two independent salts per window. Shingles found in more than 0.5 % of
   matched reports (442 of 88,442) are left out of signatures only, so formula letters such as `رسولالله` do not create
   candidates.
3. **LSH banding** (Leskovec, Rajaraman, Ullman, *Mining of Massive Datasets*, ch. 3.4): 42 bands of 3 rows per
   signature, 84 band tables in all. A band's rows are spread across the signature (bins j, j+42, j+84) because
   densified neighbouring bins copy each other; with contiguous rows the first trial produced 18 million candidates
   that were almost all noise. Long reports are signed as overlapping 16-word windows (stride 8) so a short report
   inside a long one can collide with the window that holds it. A bucket of more than 60 reports is a formula
   bucket and emits no pairs (69 buckets, 1,397 reports).
4. **Exact scoring** of every candidate on the full shingle sets: Jaccard, and containment (shared shingles over the
   shorter text's shingles). When one text is over 1.25 times the other, containment is **local**: the best share
   of the shorter text's shingles inside one window 1.25 times its length in the longer text (sliding maximum over
   prefix sums). Without this, a short report's letter 5-grams are found scattered through any 3,000-word text and a
   global containment of 0.6 meant nothing (first trial: Ibn Majah's `من فطر صائما ...` "contained" in an Amali
   chapter with Jaccard 0.004).

### Short reports

A matn under 8 comparison words is not matched at all (7,597 reports, 7.6 %). Short sayings such as `اليمين على
المدعى عليه` (4 words) or `من كنت مولاه فعلي مولاه` alone (4 words) match each other by accident as easily as by
transmission, so they are excluded rather than shown with false confidence. A partial overlap also needs at least
15 words on the shorter side. Musnad Ahmad (3,363), Musnad al-Shafi'i (443), Sunan al-Darimi (367) and Bukhari (361)
lose the most.

### Classes

| Class | Rule | Meaning |
| --- | --- | --- |
| `same_wording` | Jaccard >= 0.80 | Near-identical text |
| `same_report_variant_wording` | Jaccard >= 0.25 and containment >= 0.40 | The same report told with differences |
| `partial_overlap` | containment >= 0.60, shorter side >= 15 words | One contains a passage of the other |
| (dropped) | anything weaker | |

`score_band` is the Jaccard decile for the first two classes and the containment decile for partial overlaps.

### Clusters

Pairs are grouped in two guarded phases (`correspondence_logic.build_clusters`):

1. **Chaining guard: star clustering** (Aslam, Pelekhov, Rus, JGAA 8(1), 2004) over strong edges (same wording and
   variant). Centres are taken by degree, then id; every member is directly linked to its centre. Plain connected
   components produced a 3,688-report cluster at Jaccard 0.25; stars cap the largest at 61.
2. **Compound guard.** A `partial_overlap` edge merges two stars only one to one: the container star contains no
   other star and the contained star lies in no other star. A long compound report holding passages of several
   reports, or one passage held by two unrelated long reports, never joins them. 862 compound container stars and
   716 multiply contained stars were held apart (3,529 partial edges blocked, 1,215 merged).

The cluster id is `report-cluster:` plus the first 20 hex digits of SHA-256 over the sorted member ids: deterministic
and content-addressed (it changes when membership changes). Pairs between clusters stay in the pair file.

## Headline numbers

135,825 pairs: 6,750 `same_wording`, 112,864 `same_report_variant_wording`, 16,211 `partial_overlap`.

| Scope | Pairs | same wording | variant | partial |
| --- | ---: | ---: | ---: | ---: |
| Across traditions | 8,728 | 109 | 6,525 | 2,094 |
| One tradition, different works (corroborating versions) | 93,145 | 4,592 | 77,336 | 11,217 |
| Same work (repetitions) | 33,952 | 2,049 | 29,003 | 2,900 |

Reports with a counterpart in another tradition: **7,107** (Sunni 5,286, Imami 1,225, Ibadi 478, Zaydi 118). As a
share of matched reports: Ibadi 50 %, Zaydi 17 %, Imami 4.0 %, Sunni 9.4 %.

Tradition-pair matrix (pairs; strong classes in brackets):

| | Imami | Zaydi | Ibadi |
| --- | ---: | ---: | ---: |
| **Sunni** | 4,439 (2,861) | 435 (279) | 3,607 (3,314) |
| **Imami** | | 128 (90) | 113 (86) |
| **Zaydi** | | | 6 (4) |

17,536 clusters: 16,627 within one tradition, 839 spanning 2, 66 spanning 3, 4 spanning all 4 traditions
(Sunni+Imami 413, Sunni+Ibadi 361, Sunni+Imami+Ibadi 38, Imami+Zaydi 31, Sunni+Imami+Zaydi 26, Sunni+Zaydi 25).

Score bands (all scopes):

| Band | Pairs | Band | Pairs |
| --- | ---: | --- | ---: |
| variant J 0.2-0.3 | 26,022 | partial C 0.6-0.7 | 7,728 |
| variant J 0.3-0.4 | 35,327 | partial C 0.7-0.8 | 3,959 |
| variant J 0.4-0.5 | 21,142 | partial C 0.8-0.9 | 2,190 |
| variant J 0.5-0.6 | 14,244 | partial C 0.9-1.0 | 2,334 |
| variant J 0.6-0.7 | 9,557 | same J 0.8-0.9 | 3,803 |
| variant J 0.7-0.8 | 6,572 | same J 0.9-1.0 | 2,947 |

## Precision: one reader's reading of the 150-pair sample

All 150 worksheet pairs were read by the job's author (not a reviewer; the worksheet's judgement fields are blank).
"Real" means the two texts plainly carry the same report or the same quoted passage; "borderline" means a shared
legal ruling or formula with a different speaker or occasion.

| Stratum | Read | Real | Borderline | Not a correspondence |
| --- | ---: | ---: | ---: | ---: |
| partial C 0.6-0.7 | 14 | 9 | 2 | 3 |
| partial C 0.7-0.8 | 14 | 12 | 2 | 0 |
| partial C 0.8-0.9 | 14 | 12 | 1 | 1 |
| partial C 0.9-1.0 | 12 | 11 | 1 | 0 |
| variant J 0.2-0.3 | 12 | 8 | 3 | 1 |
| variant J 0.3-0.4 | 12 | 8 | 3 | 1 |
| variant J 0.4-0.5 | 12 | 11 | 0 | 1 |
| variant J 0.5-0.6 | 12 | 12 | 0 | 0 |
| variant J 0.6-0.7 | 12 | 10 | 2 | 0 |
| variant J 0.7-0.8 | 12 | 12 | 0 | 0 |
| same J 0.8-1.0 | 24 | 24 | 0 | 0 |

The false positives share one shape: a common formula carries the overlap (the shahada, the tahlil `لا إله إلا الله
وحده لا شريك له`, a Quran verse, the frame `ثلاثة لا يكلمهم الله ...` with different triads, `ما رأيت أحدا أكثر ...`).
A suggested display threshold: `same_wording`; variant at Jaccard >= 0.4; partial at containment >= 0.7. The lower
bands are reviewer material.

Examples (comparison is on the matn shown; ids are loader ids):

1. **Clear, Sunni / Imami, same wording (J 0.95).** Sunan Abi Da'ud 4873 `hadith:k6:19825`: `من كان له وجهان في الدنيا
   كان له يوم القيامة لسانان من نار` / Al-Khisal `hadith:thaqalayn:e4c7d3b25369713d76eb9a54`: the same words.
2. **Clear, Sunni / Imami, variant (J 0.74).** Musnad Ahmad `hadith:pure-canon:pc_73535`: `لا حسد إلا على اثنتين رجل
   آتاه الله القرآن ... ورجل آتاه الله مالا ...` / Al-Khisal `hadith:thaqalayn:52082747757d55b14c7970b8`: `لا حسد إلا في
   اثنتين رجل آتاه الله مالا ... ورجل آتاه الله القرآن ...` (the two halves in the other order).
3. **Clear, Zaydi / Imami, partial (C 0.92).** Musnad Zayd 613 `hadith:openiti:zaydi:zayd_0613|613|V01P382`: `يحمل هذا
   العلم من كل خلف عدوله ينفون عنه تحريف الغالين وانتحال المبطلين وتأويل الجاهلين` / Ma'ani al-Akhbar
   `hadith:thaqalayn:ac5af7210a58861b0fcf63a9`, where al-Sadiq quotes it inside a longer report.
4. **Borderline, Ibadi / Zaydi (J 0.27).** Musnad al-Rabi' 542: `قال رسول الله ... الرجل أحق بامرأته ما لم تغتسل من
   الحيضة الثالثة` / Musnad Zayd 474: `عن علي قال: الرجل أحق برجعة امرأته ما لم تغتسل من آخر حيضة`. The same ruling,
   attributed to the Prophet in one and to Ali in the other: a textual correspondence, not one report.
5. **False positive, Sunni / Imami (J 0.26).** Sunan Ibn Majah 2980 `hadith:k6:33185`: `ثلاثة لا يكلمهم الله ... رجل
   على فضل ماء ...` / Al-Kafi `hadith:thaqalayn:e532c2d8d54f19057995a200`: `ثلاثة لا يكلمهم الله ... شيخ زان وملك جبار
   ومقل مختال`. Same frame, different three.
6. **False positive, partial (C 0.63).** Musnad Ahmad `hadith:pure-canon:pc_29780` (the Jibril hadith) / Al-Kafi
   `hadith:thaqalayn:466e90b70a62c5cf0454e4da`: `إقامة المرأة أن تكبر وتشهد أن لا إله إلا الله وأن محمدا عبده
   ورسوله`. Only the shahada is shared.

## Recall of the candidate step

`measure_lsh_recall.py` scores 450 reports (300 random, 50 from each non-Sunni tradition) exactly against every
matched report and checks which kept pairs LSH found (`output/lsh_recall.json`). Recall: same wording 100 %; variant
J >= 0.5 98-100 %, 0.4-0.5 92 %, 0.3-0.4 75 %, 0.2-0.3 53 %; partial 85 %; across traditions 83 %; all 77 %. What is
missed sits in the bands with the lowest precision.

## Famous reports (search by distinctive phrase in the isolated matns; nothing forced)

| Phrase | Carriers | Linked across traditions |
| --- | --- | --- |
| `من كذب علي متعمدا فليتبوأ مقعده من النار` | Sunni 28, Imami 3, Ibadi 2 | Sunni-Imami, Sunni-Ibadi (e.g. Bukhari `hadith:k6:1250` with Musnad al-Rabi' 738) |
| `من كنت مولاه فعلي مولاه` | Sunni 12, Imami 29 | Sunni-Imami (e.g. Sahifat al-Rida 13 with Musnad Ahmad `pc_25530`) |
| `إني تارك فيكم الثقلين` | Sunni 4, Imami 14 | Sunni-Imami (Ahmad `pc_17898` with several Imami copies) |
| `بمنزلة هارون من موسى` | Sunni 21, Imami 29 | Sunni-Imami |
| `بني الإسلام على خمس` | Sunni 11, Imami 11 | Sunni-Imami |
| `طلب العلم فريضة على كل مسلم` | Sunni 1, Imami 4 | Sunni-Imami (Ibn Majah `hadith:k6:30443` with two Imami copies) |
| `لا ضرر ولا ضرار` | Sunni 5, Imami 6 | **Not found.** The Sunni copies are the 4-word saying alone (under the minimum); the Imami copies embed it in the Samura ibn Jundab story |
| `اليمين على المدعى عليه` | Sunni 19, Imami 6 | **Not found.** Short, and the tellings differ (`البينة على المدعي واليمين على من أنكر`) |
| `إنما الأعمال بالنيات`, `الحلال بين والحرام بين`, `الدين النصيحة`, `حتى يحب لأخيه ما يحب لنفسه` | Sunni only | Not in another tradition's matns in this corpus |
| `أنا مدينة العلم وعلي بابها`, `كمثل سفينة نوح`, `من مات ولم يعرف إمام زمانه` | Imami only | Not in another tradition's matns in this corpus |

## Outputs (`output/`, git-ignored; rebuild with the commands)

| File | Rows |
| --- | ---: |
| `report_correspondence_pairs.csv` / `.jsonl` | 135,825 each |
| `report_correspondence_cluster_members.csv` | 54,769 |
| `matn_isolation_coverage.csv` | 34 works |
| `matn_isolation_flags.csv` | 24,103 |
| `review_worksheet_150.csv` | 150 (blank judgement fields; `shared_passage_in_longer_text` shows where the overlap sits) |
| `lsh_recall.json`, `summary.json`, `run_log.json` | |

## Proposed Postgres tables

The runbook's one-writer rule splits machine output from human decisions, as `translation_candidates` and
`narrator_surface_decisions` already do (design §4.3).

**`report_correspondence_candidates`** (candidate stream: loader-owned, replaced per load, reviewer mode only)

| Column | Type | Notes |
| --- | --- | --- |
| `id` | text PK | `report-pair:` + first 20 hex of SHA-256(`hadith_id_a` 0x1F `hadith_id_b`) |
| `hadith_id_a`, `hadith_id_b` | text not null, FK `hadiths` | Unordered pair stored as `check (hadith_id_a < hadith_id_b)`; unique with `method_version` |
| `arabic_sha256_a`, `arabic_sha256_b` | text not null | The Arabic the scores were computed on; `db:verify` lists pairs whose text changed |
| `relation_class` | text not null | `same_wording`, `same_report_variant_wording`, `partial_overlap` |
| `jaccard`, `containment`, `global_containment`, `length_ratio` | real not null | |
| `shared_shingles`, `shingles_a`, `shingles_b`, `words_a`, `words_b` | integer not null | |
| `score_band`, `scope`, `matn_split_a`, `matn_split_b` | text not null | |
| `cluster_id` | text not null | Index; joins `report_correspondence_cluster_members` |
| `basis` | text not null | `textual_overlap` |
| `method_version`, `dataset_version_id` | text not null | FK `dataset_versions` |

Indexes: unique (`hadith_id_a`, `hadith_id_b`, `method_version`); (`hadith_id_b`); (`cluster_id`).

**`report_correspondence_cluster_members`**: (`method_version`, `hadith_id`) PK, `cluster_id`, `star_centre`.

**`report_correspondence_decisions`** (curation: app-owned, untouched by reloads)

| Column | Type | Notes |
| --- | --- | --- |
| `id` | text PK | |
| `hadith_id_a`, `hadith_id_b` | text not null, FK | Same ordering check. Keyed on the pair, not the candidate id, so a decision survives a new method version |
| `bound_arabic_sha256_a`, `bound_arabic_sha256_b` | text not null | A decision whose Arabic has changed is re-queued, never silently reapplied |
| `decision` | text not null | `confirmed`, `rejected`, `uncertain` |
| `reviewed_relation` | text null | The reviewer's class: the three machine classes plus `same_ruling_different_attribution`, `shared_formula_only`, `shared_quran_quotation` |
| `note` | text null | |
| `citation_id` | text null, FK `citations` | When the reviewer relies on a takhrij work |
| `decided_by`, `decided_at` | text, timestamptz not null | |
| `supersedes_decision_id`, `retired_at` | null | No deletes: a revised decision supersedes and retires the old row |

Unique (`hadith_id_a`, `hadith_id_b`) where `retired_at is null`. The reader-facing link shows `confirmed` pairs, and
optionally unreviewed candidates above the display threshold with a "machine-found, unreviewed" marker; `rejected`
pairs are never shown.

## Next steps to raise recall

- **Embedding pass for paraphrased tellings.** Letter shingles need shared wording. A sentence-embedding model over
  matns (for example BGE-M3, already named in the project's research notes) would find tellings with the same
  content in different words; its candidates would need their own basis label (`semantic_similarity`) and their own
  precision reading.
- **Short sayings.** Admit 4 to 7-word matns only as `same_wording` with Jaccard >= 0.9 and a rarity condition (no
  stop shingle carries the match).
- **Tirmidhi's compiler statements** (`قال أبو عيسى ...`, `وفي الباب عن ...`) inflate the Tirmidhi side and turn some
  variants into partials. A boundary from `diagnostics/extract_tirmidhi_compiler_statements.py` would fix it.
- **Formula filter.** Flag overlaps carried by the shahada, tahlil, talbiya or a Quran verse (the main false-positive
  shape) instead of dropping them.
- **The 4,321 flagged Imami rows and the 948 referential Muslim reports.** A better boundary for `في قول الله ...` and
  `في رجل ...` openings would move rows from the flagged to the reliable split; referential reports (`مثله`, `نحوه`)
  could inherit the matn of the report they point to, as a separate labelled relation.
- **Recall at Jaccard 0.2-0.4** rises with more band tables (a third salt) at the cost of runtime.
