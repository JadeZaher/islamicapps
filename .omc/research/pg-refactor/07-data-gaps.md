---
type: research
date: 2026-11-21
intent: Data-gap closing plan for the Postgres/Drizzle refactor. Covers the ranked gaps, narrator identity resolution workflow, translation, grading, biography/citation, a critique of the release gate, and jobs that can start now.
branch: refactor/postgres-drizzle @ af2f90b
mode: read-only investigation. The only computation was two read-only Python passes over all_hadiths_unified.csv.gz, using scratchpad scripts that printed to stdout and wrote no files.
---

# 07 — Data-gap closing plan

## Where the numbers come from

| Fact | Source |
| --- | --- |
| Corpus is 99,283 rows: Sunni 64,356, Imami 33,225, Ibadi 1,004, Zaydi 698 | `datasets/hadith-data/DATA_QUALITY_REPORT.md:36-42` |
| Strict candidate has 204 complete `chain_indx` rows and 99,079 without | `DATA_QUALITY_REPORT.md:12-14,42` |
| Audit: 84,781 rows have an extracted chain, 14,500 have none, 2 hit the extraction limit, 527 fully resolve. 437,476 surfaces were attempted and 387,359 are unresolved (88.5%) | `sanad_resolution_audit.json` `.metrics`; `DATA_QUALITY_REPORT.md:84-94` |
| Translation backlog is 12,841 rows. 0 rows are `human_verified`/`source_verified` | `DATA_QUALITY_REPORT.md:111-158` |
| `evidence_curation.json` contains 0 claims and 0 citations | `DATA_QUALITY_REPORT.md:283-295` |
| 352,315 of 399,064 assessment nodes are placeholders (88.28%) | `DATA_QUALITY_REPORT.md:317-320` |
| 84.21% of the 24,326 narrators have no Hijri birth or death year | `DATA_QUALITY_REPORT.md:352-359` |
| **New, computed for this report:** 58,028 distinct normalized unresolved surfaces, a full coverage curve, a category split, and a review-unit count | scratchpad `surface_curve.py` and `ctx.py`; they reuse `regen.build_narrator_index` / `resolve_narrator` / `narrator_normalize` and `extract_isnad_branches` exactly as `audit_narrator_resolution.py:288-363` does, so the totals reconcile with the audit: 84,781 rows and 387,359 occurrences |
| **New:** Sunni `grade_value` is the single token `ثابت` on all 29,915 graded rows. Imami `gradings_full` is populated on 14,902 rows | read-only scan of `all_hadiths_unified.csv.gz` |

---

## (a) Ranked gap table

| # | Gap | Size | Why it matters to a reader | Current blocker |
| --- | --- | --- | --- | --- |
| 1 | **Narrator identity, which drives chain completeness** | 387,359 of 437,476 surface occurrences are unresolved (88.5%), across 58,028 distinct normalized surfaces. Only 527 of 84,781 extracted rows resolve fully. The candidate has 99,079 rows without `chain_indx`. | Without identity there are no narrator pages, no "who transmitted this", no teacher/student navigation, no cross-tradition shared-narrator view, and no isnad grading context. This is the archive's distinguishing feature. | (i) Exact-only resolver policy (`AGENTS.md:175-179`, `regen_unified_csvs.py:2327-2334`). (ii) The registry has no common-name (shuhra) or kunya alias column. Example: `أبي هريرة` with 4,494 occurrences misses because the registry name is `أبو هريرة - عبد الرحمن بن صخر الدوسي` (scholar 13). (iii) **Imami rijal are essentially absent from `all_rawis.csv`.** The probes `ابن أبي عمير`, `الفضل بن شاذان`, `الحسين بن سعيد` and `صفوان بن يحيى` return 0 candidates, and `علي بن إبراهيم` returns 2 unrelated ones. Imami accounts for 161,298 unresolved occurrences. (iv) The atomic whole-row rule (`extract_isnad_unified.py:395-439`; `regen_unified_csvs.py:883-908`). |
| 2 | **Translation review state** | 0 of 99,283 rows are publishable. The backlog is 12,841 rows: 853 missing, 11,953 Arabic leakage, 10 placeholder, 1 short, 14 equal to Arabic, 2 collisions, 8 missing Arabic. About 5,000 machine candidates are unreviewed: r7 prefix 1,439, r8 suffix 3,564, local 21. | A reader cannot tell which English is the published Sunnah.com/Thaqalayn text, which is machine output, and which is reviewed. Mistranslated doctrine is a real harm, e.g. `لا نورث` reversed into "we do not inherit" (`DATA_QUALITY_REPORT.md:259-262`). | Review capacity. r8 is quality-paused on 2 fidelity defects. Rights are pending for sunnah.com and Pure Canon (`datasets/sources/README.md:12-14`). The 853 K6 blanks have no local source. |
| 3 | **Biography and citations** | 0 claims and 0 citations in `evidence_curation.json`. 20,484 narrators (84.21%) have no Hijri endpoint. 38 birth/death pairs are inverted. The 21 seed biographies cite no edition or page. | A narrator page that shows an uncited "d. 150 AH" is the precise failure this archive exists to avoid. | No sourced biographical corpus is ingested. `all_rawis.csv` has no license or row citations (`datasets/sources/narrator-lexicon.md:8-14`). No review lane exists. |
| 4 | **Grading and assessment** | 88.28% of assessment nodes are placeholders. **All 29,915 Sunni "substantive" grades are the literal `ثابت`** (Ahmad 23,529, Darimi 2,477, Shafi'i 2,054, Muwatta 1,855), which looks like a collection-level label, not a per-hadith ruling. K6 (34,441 rows) has no grade. Ibadi and Zaydi have none. Imami has 14,902 rows with cited Majlisi/Behbudi/Mohseni gradings (Kafi 13,981, Mu'jam 428, Faqih 390, …). | Calling a placeholder or a collection label a grade misleads readers. The Imami gradings are real, cited evidence that is underused. | No grading provenance model. Sunnah.com grade rights (Albani/Darussalam) are unclear. |
| 5 | **Rows with no extracted chain** | 14,500 rows: Sunni 12,229, Imami 2,228, Ibadi 38, Zaydi 5. | Some of these have no isnad by nature. Nahj al-Balagha (2,260 rows) is sermons and letters. Some Muwatta and Musnad rows are mursal or have abbreviated chains. Others are extraction misses. | No per-row "isnad absent in source" disposition separates real absence from extractor misses. |
| 6 | **Source text and rights** | 8 rows missing Arabic. Zaydi re-parse yields 699 rows against 698 checked in. One Thaqalayn ID is unavailable. Licenses are `unstated` for sunnah.com, Pure Canon and the OpenITI derivatives (`datasets/sources/README.md`). K6 `source` labels carry stray padding, e.g. `" Sahih Muslim "`. | Publishing without rights clearance risks takedown. Missing Arabic cannot be translated. | Rights correspondence (`curation_dispositions.jsonl`: `rights_status: pending_written_permission`). |
| 7 | **Source-work and compiler metadata** | 32 sources, none with an author, dates or locator (`DATA_QUALITY_REPORT.md:310-311`). | Readers cannot judge a collection's date or authority. | No evidence curation has been done. This is small and quick to close. |
| 8 | **Historical events and epochs** | 54 uncited events, 32 locations, no epochs. A seeder `Egypt` mapping fails (`DATA_QUALITY_REPORT.md:374-388`). | The lifetime-context feature would show unsourced history. | Same as #3. |

The order puts first the gaps a reader would notice and that block the most rows. #1 dominates: even with translation solved, the current gate still publishes 0 rows because of chains.

---

## (b) Narrator identity resolution: tiered workflow

### b.0 Measured shape of the gap (computed 2026-11-21, read-only)

**Occurrence coverage.** This is the share of unresolved occurrences covered if the top-N distinct normalized surfaces were each given a decision.

| Top N surfaces | Occurrences covered | % of 387,359 |
| ---: | ---: | ---: |
| 10 | 53,498 | 13.8 |
| 50 | 111,984 | 28.9 |
| 100 | 145,552 | 37.6 |
| 250 | 193,784 | 50.0 |
| 500 | 227,986 | 58.9 |
| 1,000 | 259,064 | 66.9 |
| 2,000 | 284,584 | 73.5 |
| 5,000 | 312,288 | 80.6 |
| 10,000 | 330,875 | 85.4 |
| 20,000 | 349,331 | 90.2 |

The long tail is heavy. There are 58,028 distinct surfaces: 40,010 are singletons, 3,125 occur 10 or more times, and 862 occur 50 or more times.

**Row-level curve under the atomic rule.** A row completes only when every surface in it is resolved. Treat this as an upper bound: it assumes each reviewed surface resolves in every context.

| Top N reviewed | Rows fully resolvable | Sunni | Imami | Ibadi | Zaydi |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 (today) | 527 | 341 | 176 | 6 | 4 |
| 100 | 5,601 | | | | |
| 500 | 16,896 | 8,589 | 7,098 | 700 | 509 |
| 1,000 | 24,005 | | | | |
| 2,000 | 31,397 | 17,472 | 12,647 | 744 | 534 |
| 5,000 | 40,384 | 23,064 | 15,962 | 806 | 552 |
| 10,000 | 47,174 | | | | |
| 20,000 | 55,921 | | | | |
| all 58,028 | 84,781 | 52,126 | 30,996 | 966 | 693 |

Ibadi and Zaydi saturate quickly: the top 500 surfaces already cover more than 70% of their rows. These two are the cheapest traditions to complete.

**Surface categories.** These are heuristic buckets over normalized surfaces.

| Category | Occurrences | Distinct | Resolution path |
| --- | ---: | ---: | --- |
| ism + nasab (`X بن Y`) | 163,047 | 19,736 | Registry match after alias/nisba handling, then context |
| single ism or laqab (`سفيان`, `الزهري`, `مالك`) | 69,935 | 2,885 | Context only (teacher/student plus tabaqah) |
| other multi-token | 58,503 | 29,865 | Mixed. Includes reordered names (`الحميدي عبد الله بن الزبير`) and residual noise |
| kunya only (`أبي عبد الله`, `أبي جعفر`, `أبي بصير`) | 41,586 | 1,738 | Context only. In Imami chains `أبي عبد الله`/`أبي جعفر` at chain end with an Imam marker are the Imams |
| relational or fragment (`أبيه`, `أبي`, `جده`, `عنه`, `و`) | 23,320 | 78 | **Never a registry identity.** Derive from the neighbour (father/grandfather of the resolved previous narrator) as a candidate. `عنه` is an anaphor back to an earlier chain. `و` is an extractor artefact |
| `ابن X` nasab only (`ابن عباس`, `ابن شهاب`, `ابن أبي عمير`) | 21,375 | 538 | Registry alias plus context |
| collective or anonymous (`عدة من أصحابنا`, `بعض أصحابنا`, `رجل`) | 9,593 | 3,188 | **Never a single identity.** Model as an anonymous or collective link. For al-Kafi's `عدة`, al-Kulayni's own stated membership is a cited, tradition-internal claim |

Taken together, **32,913 occurrences (8.5%) can never become one registry ID.** Under the atomic rule, every row containing `أبيه` (14,101 occurrences) or `عدة من أصحابنا` (3,139) stays incomplete forever unless the chain model can represent a derived or collective link. This is a schema requirement as well as a curation requirement.

**Candidate availability.** For the top 2,000 surfaces, these are the existing prefix/kunya `blocked_index` candidates from `narrator_resolution_candidates`, `regen_unified_csvs.py:2337-2352`.

| Candidates | Distinct surfaces | Occurrences |
| --- | ---: | ---: |
| 0 | 771 | 100,461 |
| 1 | 402 | 37,440 |
| 2–5 | 457 | 53,542 |
| more than 5 | 370 | 93,141 |

The 0-candidate share is dominated by Imami names that are missing from the registry. Prefix blocking is weak: `سفيان` has 60 candidates and `محمد بن يحيى` has 26.

**Review units.** Identity depends on context. "Next" below is the teacher: the following surface in source order.

| Top N surfaces | Distinct (surface, teacher-surface) contexts | Contexts covering ≥80% of each surface's occurrences | (surface, source-work) units |
| ---: | ---: | ---: | ---: |
| 100 | 14,824 | 2,479 | 1,215 |
| 500 | 32,544 | 9,139 | 4,657 |
| 2,000 | 50,073 | 18,940 | 12,150 |

**Realistic budget.** About 2,500 context-keyed decisions cover roughly 80% of the occurrences of the top 100 surfaces. About 9,000 cover the top 500. That reaches roughly 45–55% of all unresolved occurrences. This is an estimate: the top 500 cover 58.9% of occurrences, and the 80% context cut takes that to about 47%.

### b.1 Tier 0: exact-match improvements that are safe

None of these infer identity. Each makes the existing exact rule see text the registry already contains. Each needs a regression fixture, and T0-b, T0-c and T0-d need a one-line amendment to `AGENTS.md:175-179`, because that file lists the permitted normalizations exhaustively.

| ID | Change | Why it is safe | Where |
| --- | --- | --- | --- |
| T0-a | Keep the 7 Unicode-normalization equivalences | Already machine-audited (`narrator_alias_candidates.json`) | n/a |
| T0-b | **Registry-declared alias segments.** Split the registry Arabic name on ` - `, `،` and `/`, and index each segment under the existing uniqueness rule (`build_narrator_index` drops anything with 2 or more IDs). Example: `أبو هريرة - عبد الرحمن بن صخر الدوسي` yields `أبو هريرة` | The registry itself asserts that the segment names this person. No external inference is added. Uniqueness is still enforced. | `_extract_arabic_name` at `regen_unified_csvs.py:2207-2229`; `_add` at `2276-2288` |
| T0-c | **Grammatical case folding of the kunya head.** Fold `أبي`/`أبا` to `أبو` only when at least one name token follows, then do the exact lookup | Nominative, genitive and accusative forms of the same lexeme. A bare `أبي` ("my father") is excluded by the token-count guard. | `narrator_normalize` at `regen_unified_csvs.py:2196-2204` (lookup side only) |
| T0-d | Strip a trailing honorific or formula that the extractor leaves on a surface: `رضي الله عنه`, `عليه السلام`, `ص`. Use the same token-bounded rule the extractor uses | Display formulae, not name tokens | `extract_isnad_unified.py:45` `_HONORIFIC_RE` |
| T0-e | Measure first: run T0-b to T0-d in a diagnostic-only resolver and report the delta before any policy change | Evidence before policy | Job J2 |

**Do not do these at Tier 0:** reorder-tolerant matching, nisba stripping, kunya-only matching, or 4-character prefix matching. Each can join two different people, so each belongs in Tier 1 as a candidate.

### b.2 Tier 1: candidate generation and ranking (never asserts identity)

The **review unit** is `(normalized surface, teacher-context, source_work_id)`, with the student-context as a secondary key. Classical rijal disambiguation works the same way: `سفيان` narrating from `الزهري` in a Bukhari chain is a different question from `سفيان` narrating from `منصور`.

**Candidate retrieval.** Take the union of these channels, cap the set at 25, and record each candidate's provenance channel:

1. **Component-keyed blocking.** Parse the registry Arabic name into ism, nasab chain (`بن …`), kunya (`أبو …`), nisba (`ال…ي`) and laqab. Block on (ism, father-ism), (kunya, nisba) or (nasab-head) as well as the existing 4-character prefix. This replaces prefix-only blocking, under which `سفيان` has 60 candidates.
2. **Graph adjacency.** Use `teachers_inds` (13,104 of 24,326 rows filled) and `students_inds` (6,124). If the teacher-context surface is resolved, or itself has a short candidate list, keep candidates whose `teachers_inds` contains that ID. Do the same for the student side. This is the strongest signal. It costs nothing and works directly on `scholar_indx` (`.omc/research/neo4j-hadith-graph/insight_03_entity_resolution.md:18,118`).
3. **Registry-declared aliases** from T0-b, including non-unique ones, which are kept as candidates.
4. **Father/grandfather derivation** for `أبيه`/`جده`, from the previous narrator's `parents` field (Phase-4 follow-up 3, `.omc/research/uniform-isnad/phase4-kunya-gap.md`).

**Ranking features.** Store each feature separately so a reviewer sees why a candidate ranks where it does.

| Feature | Source | Use |
| --- | --- | --- |
| `name_component_score` | Weighted ism/nasab agreement (high weight), nisba (medium), kunya/laqab (low, because they collide often) | Score |
| `teacher_edge` / `student_edge` | `teachers_inds` / `students_inds` contains the neighbour candidate | Strong boost. Absence is neutral, because the lists are incomplete |
| `tabaqah_gap` | `grade` column, e.g. `[6th generation]`, `Comp.(RA)` maps to generation 1. Expect the teacher to be about 1 generation earlier. | Hard prune when the gap is 3 or more generations. Otherwise a penalty |
| `death_plausibility` | `death_date_hijri` (3,951 filled). A student cannot have died before his teacher could plausibly transmit. A teacher who died more than about 90 years before the student's death is implausible | Hard prune only when both dates are present. Never when either is missing |
| `chain_position_prior` | Position from the collector end. Imam marker (`عليه السلام`) plus terminal position plus `narration_level=imam` from `classify_attribution.py` | Settles Imami `أبي عبد الله`/`أبي جعفر`, which are context-dependent |
| `tradition_prior` | Row tradition against registry tags | Weak. **Cross-tradition matches always need human review** |
| `corpus_frequency_prior` | How often the candidate is already resolved in the same source work | Tie-break only |

**Output per unit:** a ranked list with `score`, `margin_top1_top2`, the features, a `status` of `candidate_only`, and the evidence row IDs (first 5 `record_id`s). **Nothing is written to `chain_indx`, the registry, or any canonical CSV.**

**The Imami path is blocked by the registry, not by ranking.** For about 161k Imami occurrences the right candidate does not exist in `all_rawis.csv`. A separate Imami authority file is a prerequisite. OpenITI carries the classical rijal works (author directories seen in `.omc/research/openiti-release-data-list-2026-07-20.txt`): `0450Najashi`, `0460ShaykhTusi` (Rijal/Fihrist), `0329IbnCumarKashshi` (Ikhtiyar Ma'rifat al-Rijal), `0274AhmadBarqi`, and `0411/0414 …Ghadairi`. Build an `imami_narrator_authority` key space with stable IDs, such as `IMR:<work>:<entry>`, cited to work and entry. Link it to `scholar_indx` **only** through a human-confirmed `same_as`. Per-text OpenITI licenses are unstated (`datasets/sources/openiti.md`), so license review comes first.

### b.3 Tier 2: human review queue

**Queue file.** `datasets/hadith-data/diagnostics/narrator-resolution/review_queue.jsonl`, in Postgres later. One row per review unit:

```
unit_id (sha256 of surface|teacher_ctx|source_work_id), surface_normalized, surface_examples[≤3 raw],
teacher_ctx, student_ctx, source_work_id, tradition, occurrences, rows_unblocked_if_resolved,
candidates[{scholar_indx|authority_id, score, margin, features{...}, channel}],
evidence_record_ids[≤5], decision: null|{kind: same_as|derived_relation|collective|not_a_narrator|undecidable,
target_id, cited_basis{work, edition, locator}, reviewer, reviewed_at, review_state: human_verified}
```

**Ordering.** Sort by `rows_unblocked_if_resolved` descending, which is the marginal row gain, not raw frequency. Then sort by occurrences. Ibadi and Zaydi units float up because they finish whole traditions.

**Reviewer actions:**
- Accept a candidate. A citation is required for kunya-only, laqab-only and cross-tradition decisions.
- Mark the surface `derived_relation` (`أبيه` resolves to the father of X).
- Mark it `collective` or `anonymous`.
- Mark it `not_a_narrator`. This covers extractor noise such as `و`, and those units also feed extractor regression fixtures.
- Mark it `undecidable`. The surface is shown as written forever. That is a valid final state.

**Bulk acceptance.** Allowed only within one unit, never across units. One decision covers every occurrence that shares the same (surface, teacher-context, work).

**Invariants:**
- No decision without a reviewer and timestamp. This matches the existing `er-staging.jsonl` G-5 invariant.
- `candidate_only` rows never render as links to readers.
- Every decision is replayable: decisions key on `unit_id`, so a regenerated chain reapplies them deterministically.

**Retire the legacy queue.** `datasets/hadith-data/er-staging.jsonl` has 3,857 rows, all unreviewed, written by `src/scripts/lib/regen/entity-resolution.ts`. Its surfaces are whole English Thaqalayn sentences ("Muhammad ibn al-Hassan has narrated from Sahl ibn Ziyad…"), and every candidate carries the same score, 0.72, from a prefix-only match. Treat it as superseded evidence. Do not migrate it.

### b.4 Expected coverage

| Effort | Decisions | Unresolved occurrences addressed | Rows complete (atomic, upper bound) |
| --- | ---: | --- | ---: |
| Tier 0 only | 0 human | Unknown. Measure with job J2. Likely a few percent, concentrated in famous Sunni kunyas such as `أبي هريرة` (4,494) | from 527 to maybe a few thousand |
| Top-100 surfaces, 80% contexts | about 2,500 | about 30% | at most 5,601 |
| Top-500 surfaces, 80% contexts | about 9,100 | about 47% | at most 16,896 |
| Top-2,000 surfaces, 80% contexts | about 19,000 | about 59% | at most 31,397 |
| The tail | more than 30,000 | | |

Under the atomic rule the curve flattens hard after about 2,000 surfaces. That is the quantitative case for a per-row partial status (§f). With per-link status, every reviewed decision becomes visible immediately in every row that contains it, instead of waiting for the row's rarest surface.

---

## (c) Translation gap workflow

**State.** 86,452 rows pass the structural checks, but 0 are publishable. 33,190 rows are Thaqalayn `source_provided` and 33,588 are `source_status_unknown`. 31,652 are `machine_unreviewed`, of which 29,915 are classical recoveries with no model identity. 853 rows are missing English (K6). 11,953 rows contain Arabic leakage.

1. **Provenance-first states. Start now, with no spend.**
   - **Thaqalayn (33,190 rows).** Per-row translator attribution exists upstream (`translator` field in `shia-hadith/v2_books/*.json`, e.g. "Muhammad Sarwar"). Rights are under review (`datasets/sources/thaqalayn-api.md`). Once rights clear, these become `source_verified` by work and edition, not by row review. That is the largest single unlock.
   - **K6 sunnah.com (about 33.5k with English).** Rights are pending. The `curation_dispositions.jsonl` pattern of reference correction without storing text is the template for recording the official reference per row.
   - **Classical recoveries (29,915).** Reconstruct the acquisition log or model, or verify against the edition. Until then label them `machine_or_unknown_provenance`.
2. **Leakage triage (11,953 rows).** Classify each leakage row deterministically:
   - (i) Arabic only in transliterated names or terms inside otherwise good English. A rule-based transliteration pass could fix these, but only into a new candidate file, never in place.
   - (ii) Untranslated passages.
   - (iii) Fully Arabic.

   Run this as an offline classifier (job J7) to size each bucket before spending on (ii) and (iii).
3. **Machine candidates.** Resume r8 only after prompt and validator regressions for the `k6:17921` and `k6:18013` defects (`DATA_QUALITY_REPORT.md:259-264`). Keep the `$12` overall guardrail. Never use `--allow-full-run` without a fresh targeted pilot (`machine_translation_candidates/README.md:96-132`).
4. **Review queue (about 5,000 existing candidates).** Stratify by risk:
   - doctrinal or legal markers (inheritance, `حلال`/`حرام`, passive verbs, polysemous terms flagged in r8);
   - length above 4,000 characters (segmented);
   - Imami terminology;
   - everything else, sampled at a fixed rate with acceptance sampling.

   A reviewer authors `translation_overrides.jsonl` entries one by one, bound by hash (`AGENTS.md:84-88`). Never bulk-copy.
5. **Missing 853 K6 rows.** Recover the official text where rights allow. Otherwise generate a labeled machine candidate. Muslim (354) and Tirmidhi (186) dominate.
6. **Source defects that translation cannot fix.** The three non-Arabic sources (blank, `s`, `* * * * *`), the abbreviated Ibadi row, the truncated Zaydi row (`ولم`), and the two giant Imami rows with implausible `qudsi` attribution need reclassification dispositions (`DATA_QUALITY_REPORT.md:266-271`).

**Display rule for the refactor.** Arabic is always shown. English is shown when `source_provided` with attribution and rights clearance, or when reviewed. Machine candidates are hidden from the public by default and visible only in a reviewer mode. This is an owner decision; see §f.

---

## (d) Grading and assessment workflow

1. **Stop calling placeholders assessments.** The 352,315 `no_extant_evaluation` nodes should become **absence**: no row, plus a per-hadith `grading_status = none_recorded_in_corpus`. Do not store a placeholder entity.
2. **Sunni `ثابت` (29,915 rows).** It is uniform across Ahmad, Darimi, Shafi'i and Muwatta (`grade_source = grade_value = ثابت`). That pattern is a Pure Canon collection-inclusion label, not a muhaddith's ruling. Reclassify it as `collection_inclusion_label` with source `sheikahmad-pure-canon`, and do not show it as a grade. Verify against `datasets/sources/sheikahmad-pure-canon.md`.
3. **Imami cited gradings (14,902 rows). Start now.** `gradings_full` already carries `grader: grade (work (vol/page))`, for example `Allamah Baqir al-Majlisi: صحيح (Mirʾāt al-ʿUqūl … (1/25)) | Shaykh Baqir al-Behbudi: صحيح (Sahih al-Kafi (1/ 1))`. Parse each into structured, citation-bound assessments: `grader`, `term_ar`, `cited_work`, `volume`, `page`, `source_row_id`. Ingest as `source_provided` with review state `source_verified` once rights clear. This is the largest body of real, cited assessment evidence in the corpus.
4. **K6 (34,441 rows).** Bukhari and Muslim carry the compiler's own inclusion criterion. Record that as `compiler_criterion`, which is a fact about the collection, not a per-hadith grade. For Abu Dawud, Tirmidhi, Nasa'i and Ibn Majah, per-hadith grades (Albani, Darussalam, Tirmidhi's own) exist on sunnah.com. They are blocked on rights. Tirmidhi's in-text `حسن صحيح` statements are **in the Arabic text itself** and can be extracted as `compiler_statement` with a record-level locator and no external rights issue (job J6b).
5. **Ibadi and Zaydi.** No assessment scheme is in the corpus. Show "no assessment recorded". Do not import a Sunni or Imami grade across traditions.
6. **Model.** Assessments are tradition-scoped, multi-valued, and each one is cited. There is never one "grade" scalar per hadith.

---

## (e) Biography and citation workflow

1. **Treat `all_rawis.csv` as a lexicon, not evidence** (`datasets/sources/narrator-lexicon.md`: license unstated, no row citations). Its dates may appear as `lexicon_unverified` with a visible marker, or be hidden. They never count as a cited claim.
2. **Prioritise by reader exposure.** Rank narrators by resolved-chain frequency once Tier 2 decisions exist, and by teacher/student degree before that. Roughly the top 500 narrators cover most chain views. Biography curation follows identity resolution.
3. **Claim extraction from cited classical works.** Use one work per tradition with known editions:
   - Sunni: Ibn Hajar's *Taqrib al-Tahdhib*, *Tahdhib al-Kamal*.
   - Imami: Najashi, Tusi's *Rijal*/*Fihrist*, Kashshi.
   - Ibadi and Zaydi: tradition-specific tabaqat. Gaps here should be documented, not filled.

   Machine-assisted extraction may propose `{narrator_id, claim_type, year_min, year_max, precision, quote_location_hash}` from the OpenITI text with its milestone or page locator. Each proposal is `candidate_only` until a reviewer promotes it to `evidence_curation.json` under the existing schema (`EVIDENCE_CURATION.md`: assertion ID, citation ID, edition, volume/page, review state).
4. **Competing claims stay separate.** Link them with `supersedes_assertion_id` only after review. A cited unknown date has both years null.
5. **Quick wins.**
   - (i) **Source-work compiler claims.** 32 sources with well-known compilers and dates: about 32 cited claims close gap #7 in a day of review.
   - (ii) The 38 inverted birth/death pairs and the truncated Gregorian ranges go into a lexicon-defect report (job J8) so they are never shown.
   - (iii) The 21 Phase-0 seed bios need edition and page locators added, or they stay hidden.
6. **History and epochs.** Use the same pipeline. Seed events stay hidden until cited. The `Egypt` versus Cairo/Fustat mapping must be sourced.

---

## (f) Critique of the all-or-nothing release gate, and a per-row alternative

**What the current gate does.** A load requires `ready_for_full_load: true`. That in turn requires *every* row to pass Arabic, English-review, grade/source-work and complete `chain_indx` checks (`DATA_QUALITY_REPORT.md:401-415`; `AGENTS.md:55-68,99-104`). Inside a row, one unresolved surface empties the whole chain (`extract_isnad_unified.py:414-419`; `regen_unified_csvs.py:899-903`).

**What the gate gets right.** It never invents identity, never ships a plausible partial chain as if it were complete, never treats a nonblank cell as reviewed, and binds publication to hashes. Keep all of that.

**What is wrong with it:**
1. **It conflates "complete" with "correct".** Integrity requires that *every displayed assertion* is true and sourced. It does not require that every row has every field. A verbatim Arabic source text with its provenance is a correct publication even when no narrator is identified.
2. **It withholds the archive's primary asset.** 99,275 rows have Arabic source text, and 0 can publish, because the hardest research problem (identity for 58k surfaces, including about 33k occurrences that can never map to one ID) is a precondition for the easiest value (reading the source).
3. **It discards verified work.** The atomic chain rule throws away resolved links in a row because of one unresolved neighbour. Per-link status keeps them without implying anything about the missing link.
4. **Its incentives are perverse.** The only way to ship is to loosen identity rules or bulk-accept candidates, which is exactly the integrity failure the gate exists to prevent.
5. **The curve proves it.** Even 19,000 human decisions reach at most 31,397 complete rows (§b.4). The gate stays red for years.
6. **Placeholder grades pass while honest absence fails.** 352k placeholder nodes and 29,915 `ثابت` labels satisfy "has a grade" structurally. That is worse than an explicit "none recorded".

**Proposed per-row publication model.** Postgres columns or enums on `hadith`, `chain_link` and `assessment`:

| Facet | States, best to worst | Public rendering |
| --- | --- | --- |
| `source_text_status` | `present_verified_identity` · `present` · `missing` | `missing` rows are not published |
| `rights_status` (per source work) | `cleared` · `pending` · `restricted` | Only `cleared` works publish text or English. This is a hard per-work gate and the one corpus-level gate kept |
| `translation_state` | `human_verified` · `source_verified` · `source_provided` · `machine_unreviewed` · `none` | English is shown for the top three, with attribution. Machine output appears only in reviewer mode (owner decision) |
| `chain_status` | `complete` (every link verified) · `partial` · `unresolved` (extracted, 0 links verified) · `absent_in_source` · `extraction_failed` | Always render the isnad **as written in Arabic**. Overlay links only where verified |
| `chain_link.resolution` | `exact_registry` · `human_verified` · `derived_relation_verified` · `collective` · `undecidable` · `unresolved` | Only the first three render as narrator links. All others render the surface verbatim with a neutral "not identified" marker. **Never** show a candidate name |
| `grading_status` | `cited_assessments` · `compiler_criterion` · `none_recorded` | Never show a placeholder |
| `biography_claim.review_state` | `human_verified` · `source_verified` · (otherwise hidden) | Uncited lexicon dates are hidden or marked `unverified lexicon` (owner decision) |

**Rules that keep scholarly integrity under this model:**
- **No inference across a gap.** Teacher/student adjacency, graph analytics and narrator-page counts use only consecutive *verified* link pairs. If `A — ? — C`, no `A→C` edge exists.
- Analytics (centrality, shared-narrator cross-tradition views) carry their coverage denominator, e.g. "based on 31% of links verified". No unqualified point values (`insight_03_entity_resolution.md:193`).
- The publication manifest becomes a **snapshot of per-row states plus hashes**. The gate checks *invariants*: no unverified link rendered as a link, no uncited claim rendered, no uncleared-rights text, every override bound to its hash. It does not check completeness. Completeness becomes a tracked KPI per facet.
- The existing fail-closed regeneration, hash binding, override hash checks and `--allow-incomplete-curation` isolation stay unchanged. Only the definition of "publishable row" moves from "complete" to "every shown assertion verified".

**What the owner must decide:**
- (1) Whether machine-unreviewed English is ever public (recommended: no, reviewer mode only).
- (2) Whether lexicon dates are shown with an "unverified" badge or hidden (recommended: hidden on public pages).
- (3) Whether to accept `source_provided` Thaqalayn and Sunnah.com English after rights clearance without row review (recommended: yes, with attribution).

---

## (g) Jobs that can start now

Every job below reads canonical inputs and writes **only new files** under `datasets/hadith-data/diagnostics/<job>/`. That is the tree `audit_narrator_resolution.py:25,435-499` already sanctions for narrator diagnostics; reuse its path checks: no symlinks, no hardlinks, no input/output collisions.

None of them touch:
- canonical CSV/GZIP, `curation_*` manifests or backlog (three of these are OS-locked anyway), `translation_overrides.jsonl`, `evidence_curation.json`, `all_rawis.csv`, or `er-staging.jsonl`;
- Railway or Neo4j.

**Common inputs:**
- `datasets/hadith-data/all_hadiths_unified.csv.gz` (sha256 `f8b5cebf…c173`)
- `datasets/narrator-data/all_rawis.csv` (sha256 `d87c3af6…bc11`)
- Every output records both hashes plus the git HEAD in a header object.

| Job | Inputs (beyond common) | Output (new) | Automated? | Notes |
| --- | --- | --- | --- | --- |
| **J1 surface census** | `extract_isnad_unified.py`, `regen.narrator_normalize`, `regen.build_narrator_index` | `diagnostics/narrator-resolution/surface_census.jsonl.gz`: one row per distinct normalized surface (58,028) with occurrences by tradition and source, category, top 10 teacher and student contexts, first 5 `record_id`s, and blocked-candidate count. Plus `surface_curve.json` with the §b.0 tables | Yes, about 30 s | Supersedes the 200-row cap in `sanad_resolution_audit.json` |
| **J2 Tier-0 dry run** | J1 output | `diagnostics/narrator-resolution/tier0_delta.json`: per rule T0-b/c/d, the surfaces newly matched, any new ambiguity collisions, occurrences gained, and rows newly complete. `tier0_matches.jsonl`: surface, scholar_indx, rule, registry segment | Yes | Changes no resolver. Its output is the evidence for the `AGENTS.md` policy amendment |
| **J3 candidate ranking** | J1, `all_rawis.csv` (`teachers_inds`, `students_inds`, `grade` tabaqah, `death_date_hijri`, `parents`), `datasets/classify_attribution.py` (`narration_level`) | `diagnostics/narrator-resolution/review_queue.jsonl`: one row per review unit, schema in §b.3, `decision: null`, ranked by marginal rows unblocked. Start with the top 500 surfaces at the 80% context cut, about 9,100 units | Yes | `status: candidate_only`. No decision fields filled. Includes the `أبيه`/`جده` derived-father candidates |
| **J4 Imami rijal acquisition** | OpenITI RELEASE: `0450Najashi`, `0460ShaykhTusi`, `0329IbnCumarKashshi`, `0274AhmadBarqi` | `datasets/narrator-data/imami-rijal/<work>/<file>` with a `.meta.md` (URL, commit SHA, fetch timestamp, license as stated) | Yes (network fetch) | Fetch and hash only. Parsing entries into an authority file waits for license review |
| **J5 extractor-noise fixtures** | J1 (categories `relational_or_fragment` and `other_multi_token` singletons) | `diagnostics/extractor-noise/samples.jsonl`: 200 stratified samples with record_id and the raw Arabic span | Yes | Input for gold-set expansion. Does not modify `__tests__/fixtures` |
| **J6a Imami grading parse** | `gradings_full` column of the GZIP | `diagnostics/grading/imami_gradings_structured.jsonl`: `{record_id, grader, term_ar, cited_work, volume, page, raw}` plus `parse_failures.jsonl` | Yes | 14,902 rows. Imports nothing |
| **J6b Tirmidhi in-text rulings** | `text_ar` of Jami' al-Tirmidhi rows (4,214) | `diagnostics/grading/tirmidhi_compiler_statements.jsonl`: `{record_id, statement_ar, char_span}` | Yes | Compiler statements quoted from the source text. Regex-detected, so review is needed |
| **J6c Sunni `ثابت` provenance audit** | GZIP plus `datasets/sources/sheikahmad-pure-canon.md` and `pure_canon.jsonl` | `diagnostics/grading/pure_canon_label_audit.json`: distribution and upstream field origin | Yes | Settles §d.2 |
| **J7 translation leakage triage** | GZIP (`text_en`, `text_ar`); the backlog cannot be read (OS-locked), so recompute with `regen.translation_issue` at `regen_unified_csvs.py:270` | `diagnostics/translation/leakage_buckets.jsonl` with bucket ∈ {names_only, partial_untranslated, fully_arabic}, record_id and Arabic-letter ratio, plus `summary.json` | Yes | No API calls |
| **J7b translation review packets** | Existing accepted candidates: `machine_translation_candidates/openrouter_gemini_2_5_flash_v7_full_resilient3_2026-07-22.jsonl`, `…v8_suffix_2026-07-22.jsonl`, `local_lmstudio_candidates.jsonl` | `diagnostics/translation/review_queue.jsonl` ordered by risk stratum (§c.4), with arabic_sha256 and candidate pointers (artifact path and line). No English body is copied | Yes | Read-only over the candidate JSONLs. Never write overrides |
| **J8 lexicon defect report** | `all_rawis.csv` | `diagnostics/biography/lexicon_defects.jsonl`: inverted birth/death (38), truncated Gregorian, defaulted `death_reason`, non-numeric Hijri. Plus `narrator_priority.csv` ranked by graph degree, to be refreshed later by resolved frequency | Yes | Feeds the display rule that hides lexicon dates |
| **J9 per-row status projection** | GZIP, J1, J6a, `curation_dispositions.jsonl`, `datasets/sources/*.md` | `diagnostics/publication-status/row_status.csv.gz` with the §f facets per `record_id`, plus `summary.json` showing counts per facet and what would publish under §f | Yes | Gives the owner a concrete picture for the gate decision |

**Not automatable now:**
- every Tier-2 identity decision;
- all translation overrides;
- all evidence-curation claims;
- rights correspondence;
- resuming r8 (needs prompt and validator work plus a paid pilot approval).

---

## Schema implications for the Postgres design (cross-ref 03-graph-model)

- `chain_link(hadith_id, branch_no, position, surface_ar, surface_norm, narrator_id NULL, link_kind enum{person, derived_relation, collective, anonymous, not_a_narrator}, resolution enum{exact_registry, human_verified, derived_relation_verified, undecidable, unresolved}, decision_id NULL)`. Keep the surface for every link. **Never require `narrator_id`.**
- `narrator_surface_decision(unit_id PK, surface_norm, teacher_ctx, source_work_id, decision_kind, target_narrator_id, citation_id, reviewer, reviewed_at)`. Decisions replay onto `chain_link` by `unit_id`.
- `narrator` needs a key space or `authority` column (`rawi`, `imami_rijal`, …) plus a human-only `narrator_same_as` table for cross-authority identity.
- `assessment(hadith_id, tradition_scheme, grader, term, citation_id, kind enum{cited_ruling, compiler_criterion, compiler_statement, collection_label})`. No placeholder rows.
- `translation(hadith_id, text_en, state, source, model, arabic_sha256, rights_work_id)`, so one hadith can have several translations.
- Per-row facet status columns, or a view, from §f. The manifest records facet counts and hashes.
