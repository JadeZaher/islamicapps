# Conductor Tracks

Tracks are listed in chronological order. Check the box when a track is complete.

---

## [x] Track: Fix Hadith Data Integrity Issues [fix_hadith_data_integrity_20260418]

**Type:** Bug
**Status:** Complete (Phases 1-3 done, Phase 4 partial — Ahmad moved to own track)
**Created:** 2026-04-18
**Priority:** P0 (Critical)

Fixed 7 of 8 data integrity issues: canonical source name registry, 3 broken filters, string sort ordering, 31 bad titles, dataset_row_id backfill, Musnad al-Rabi re-import with translations. Musnad Ahmad import moved to dedicated track.

**Completed:**
- Canonical source registry (`src/lib/constants/sources.ts`)
- UI dropdown fix, ORDER BY fix, title generation fix
- DB migration script (source names, titles, dataset_row_id backfill)
- Musnad al-Rabi re-import (853 hadiths with English translations)

---

## [ ] Track: Translate Classical Collections [translate_classical_collections_20260418]

**Type:** Chore
**Status:** Planned
**Created:** 2026-04-18
**Priority:** P1
**Blocks:** import_musnad_ahmad_20260418

Bulk-translate ~29k Arabic hadiths from 4 classical collections (Ahmad, Darimi, Shafi'i, Muwatta) using Ollama. Current coverage is only 3.6% (~1,068/29,917). Prerequisite for the classical import track.

**Phases:**
1. Extract & Prepare — filter JSONL, create translation prompt (3 tasks)
2. Run Translations — Ollama batch, ~20 hours total (4 tasks)
3. Merge & Validate — combine, filter refusals, quality check (2 tasks)

---

## [ ] Track: Import Classical Musnad & Sunan Collections [import_musnad_ahmad_20260418]

**Type:** Feature
**Status:** Planned
**Created:** 2026-04-18
**Priority:** P1
**Dependencies:** fix_hadith_data_integrity_20260418, translate_classical_collections_20260418

Extract 4 classical collections (Ahmad ~23.5k, Darimi ~2.5k, Shafi'i ~2k, Muwatta ~1.9k) from `pure_canon.jsonl` into a clean CSV, map sanad to existing narrator IDs, merge translations, then import via existing pipeline. Shafi'i imports as matn-only (no isnads in source data — see `shafii-research.md`). Anthologies deferred to separate scholarly analysis track.

---

## [ ] Track: Automated Cross-Cultural Parallel Ingestion Pipeline [comparative_ingestion_20260322]

**Type:** Feature
**Status:** Planned
**Created:** 2026-03-22

Discovery script (GPT-4o + Sefaria + Bible API) -> JSON staging file -> human review UI at `/admin/comparative/review` -> idempotent ingestion script that commits approved candidates to Neo4j as `CrossCulturalParallel` nodes.

---

## [ ] Track: Narrator Biographical Enrichment [narrator_enrichment_20260425]

**Type:** Chore
**Status:** Planned
**Created:** 2026-04-25
**Priority:** P0
**Blocks:** gds_setup_analytics_20260425, vector_embedding_pipeline_20260425

Fill critical gaps in Narrator node data identified by data readiness audit:
- name_arabic: 31.8% -> target >80%
- death_year_hijri: 15.8% -> target >50%
- geographic_region: 0.1% -> target >40%
- tradition: 0.08% -> target >95%

Also: deduplicate 16,614 empty-name narrators and 200+ "no identity" duplicates.

**Phases:**
1. Audit & Source Identification (2 tasks)
2. Arabic Name Backfill (3 tasks)
3. Death Year & Birth Year Enrichment (2 tasks)
4. Geographic Region Assignment (2 tasks)
5. Tradition Assignment & Deduplication (3 tasks)
6. Verification & Metrics (1 task)

---

## [ ] Track: Text Cleanup & Embedding Preparation [text_cleanup_embedding_prep_20260425]

**Type:** Chore
**Status:** Planned
**Created:** 2026-04-25
**Priority:** P0
**Blocks:** vector_embedding_pipeline_20260425

Clean text data for high-quality embeddings:
- 7,302 Arabic texts with OCR artifacts
- 484 English texts with AI refusal artifacts
- 922 very short Arabic texts to triage
- Arabic text normalization pipeline

**Phases:**
1. OCR Artifact Cleanup (3 tasks)
2. AI Translation Refusal Repair (3 tasks)
3. Short Text Triage (2 tasks)
4. Text Normalization Pipeline (2 tasks)
5. Verification (1 task)

---

## [ ] Track: Hadith Grade Normalization [grade_normalization_20260425]

**Type:** Chore
**Status:** Planned
**Created:** 2026-04-25
**Priority:** P1
**Blocks:** gds_setup_analytics_20260425

Normalize ~200+ distinct display_grade strings into a two-tier system:
- grade_canonical: <15 broad categories (sahih, hasan, da'if, etc.)
- grade_detail: cleaned detail grades with OCR/spacing fixes

Currently: 53,676 hadiths with empty grade, ~200 near-duplicate Arabic grade strings.

**Phases:**
1. Grade Taxonomy Design (2 tasks)
2. Mapping Script (2 tasks)
3. Apply Normalization (2 tasks)
4. Verification (1 task)

---

## [ ] Track: Neo4j GDS Setup & Initial Graph Analytics [gds_setup_analytics_20260425]

**Type:** Feature
**Status:** Planned
**Created:** 2026-04-25
**Priority:** P1
**Dependencies:** narrator_enrichment_20260425, grade_normalization_20260425

Install Neo4j GDS library and run first-wave graph analytics:
- Centrality: PageRank + Betweenness on narrator HEARD_FROM network
- Community Detection: Louvain/Leiden to discover transmission school clusters
- Path Analysis: temporal chain validation (death year consistency)
- Common Link Theory: computational test of Schacht/Juynboll's theory
- Cross-tradition comparative analytics

**Phases:**
1. GDS Library Installation & Configuration (3 tasks)
2. Centrality Analysis (3 tasks)
3. Community Detection (3 tasks)
4. Path Analysis & Chain Validation (3 tasks)
5. Common Link Theory Computational Test (2 tasks)
6. Cross-Tradition Comparative Analytics (2 tasks)
7. Results Storage & Visualization (2 tasks)

---

## [ ] Track: Vector Embedding Pipeline & Semantic Search [vector_embedding_pipeline_20260425]

**Type:** Feature
**Status:** Planned
**Created:** 2026-04-25
**Priority:** P1
**Dependencies:** text_cleanup_embedding_prep_20260425, narrator_enrichment_20260425

Generate vector embeddings for all hadith texts and enable semantic search:
- Arabic embeddings via CAMeLBERT-CA (768-dim)
- English embeddings via BGE-M3 (1024-dim)
- Neo4j native vector indexes (HNSW)
- Semantic search API + cross-tradition similarity analysis

**Phases:**
1. Embedding Model Selection & Setup (3 tasks)
2. Embedding Generation Pipeline (3 tasks)
3. Neo4j Vector Index Creation (2 tasks)
4. Semantic Search API (3 tasks)
5. Cross-Tradition Similarity Analysis (2 tasks)
6. Verification & Benchmarking (2 tasks)

---

## [ ] Track: Scholarly Metadata Layer [scholarly_metadata_layer_20260425]

**Type:** Feature
**Status:** Planned
**Created:** 2026-04-25
**Priority:** P2
**Dependencies:** narrator_enrichment_20260425, grade_normalization_20260425

Populate the scholarly opinion layer:
- Scholar nodes (10+ major hadith scholars across traditions)
- ScholarVerdict nodes (33K+ from Shia corpus, Sunni implicit grades)
- Commentary nodes (major sharh works)
- Practice nodes (fiqh derivations)

**Phases:**
1. Source Identification & Data Acquisition (2 tasks)
2. ScholarVerdict Population (3 tasks)
3. Commentary Node Population (2 tasks)
4. Practice & SchoolOfThought Linking (2 tasks)
5. Verification (1 task)

---

## [~] Track: Neo4j Isnad/Narrator Graph Regeneration Pipeline [neo4j_isnad_graph_regen_20260516]

**Type:** Feature
**Status:** Planned
**Created:** 2026-05-16
**Priority:** P0
**Depends on:** fix_hadith_data_integrity_20260418
**Blocks:** narrator_enrichment_20260425, gds_setup_analytics_20260425, grade_normalization_20260425, vector_embedding_pipeline_20260425, scholarly_metadata_layer_20260425

Upstream reified-ingestion pipeline (Phases 0–2 of `.omc/research/neo4j-hadith-graph/STRATEGIC_REPORT.md`, synthesized from 14 deep-research docs). Regenerates the 69,368-record unified dataset into Neo4j as an idempotent, provenance-tracked, reified isnad/narrator graph. Fixes two live bugs in `import-datasets.ts` (uuidv4-per-run narrator duplication; scalar `n.reliability` unified-narrator fallacy). Produces the clean resolved-identity graph the five downstream tracks consume — explicit dependency edges, no duplication.

**Phases (stop-the-line gates between each):**
0. Fix-first — idempotent stable-key MERGE, remove scalar reliability, `:DatasetVersion` pinning 69,368 (CSV-record count, not `wc -l`), measure real unknown fraction (6 tasks)
1. Reified engine-agnostic schema — tradition-scoped `:Assessment` (Sunnī/Zaydī verdicts can't collide), reified `:Chain` + fast shortcut, `:NameMention`, per-edge confidence/provenance, tombstone-not-delete; **Gate G1** (7 tasks)
2. Tiered entity resolution — `chain_indx` join (Sunni 99.6%/Imami 84%, not ML) → lexicon vs `all_rawis.csv` (24,326) → ambiguous kunya-collision core with mandatory HITL; reviewed-only `:SAME_AS`; temporal-plausibility (7 tasks)

Honors the 6 enforceable guardrails (each a tested acceptance criterion) and the honest reliability ledger — no GIGO analytic ships as a result; no algorithmic output presented as a *ḥukm*.

---

## [ ] Track: Hadith Dataset Acquisition [data_acquisition_20260521]

**Type:** Feature (data engineering)
**Status:** Planned
**Created:** 2026-05-21
**Priority:** P1
**Depends on:** —
**Blocks:** Larger / richer re-runs of `neo4j_isnad_graph_regen_20260516`, `gds_setup_analytics_20260425`

Closes two classes of corpus gaps not covered by existing tracks: (a) **34,441 Sunni K6 hadiths with zero scholar-verdict data** (sunnah.com al-Albani scrape + Bukhari/Muslim consensus grade); (b) **collection-level gaps** — missing the rest of the Imami Four Books (Tahdhib + Istibsar), the major encyclopedic Imami compilations (Bihar, Wasa'il, Mustadrak al-Wasa'il), the major post-K6 Sunni works (Bayhaqi, Ibn Hibban / Khuzayma, three Tabarani Mu'jams, Mustadrak al-Hakim, two Musannafs), and extended Zaydi / Ibadi works. Potential corpus expansion from 99,283 → ~366,000 rows. Each subtrack is independently committable and per-source-isolated; existing translation / grade-canonicalization / narrator-enrichment tracks pick up the new data automatically.

**Waves (each independently committable):**
0. Infrastructure — `db:rebuild-unified-csv` script, OpenITI fetch pattern doc, source-acquisition scaffold (4 tasks)
1. **Sunni K6 grading** (FR-1) — Bukhari/Muslim consensus + sunnah.com al-Albani scrape for the 4 sunan; 34,441 rows get grades (5 tasks, **highest leverage**)
2. **Imami extension** (FR-2) — Tahdhib + Istibsar + Bihar + Wasa'il + Mustadrak al-Wasa'il from OpenITI (~127k rows) (6 tasks)
3. **Sunni post-K6** (FR-3) — Bayhaqi, Ibn Hibban, Ibn Khuzayma, 3× Tabarani, al-Mustadrak, 2× Musannaf (~140k rows) (10 tasks)
4. **Zaydi + Ibadi** (FR-4) — al-Amali al-Khamisiyya, Amali Ahmad ibn Isa, Majmu' al-Imam Zayd, Tartib al-Jami al-Sahih (~6k rows) (6 tasks)
5. Rijal handoff + perfect-regen v2 re-run on expanded corpus (4 tasks)
6. Docs + future-acquisition audit (3 tasks)

Out-of-scope (deferred to existing tracks): English translation (translate_classical_collections_20260418), grade canonicalization (grade_normalization_20260425), narrator enrichment (narrator_enrichment_20260425).

---

## [ ] Track: Uniform Taḥwīl-Aware Isnad Extraction [uniform_isnad_extraction_20260609]

**Type:** Feature (data engineering — chain extraction quality)
**Status:** Planned
**Created:** 2026-06-09
**Priority:** P0
**Depends on:** `neo4j_isnad_graph_regen_20260516`
**Blocks:** `narrator_enrichment_20260425`, `gds_setup_analytics_20260425`, `vector_embedding_pipeline_20260425`

Replaces the three divergent `chain_indx` writers in `regen_unified_csvs.py` (W1/Fix A K6 sidecar path, W2/Fix B Thaqalayn English splitter, W3/Fix C OpenITI Arabic extractor) with **one taḥwīl-aware extractor** running uniformly across every tradition's `text_ar`. Emits **one `:Chain` node per ح-branch**, each extended through the shared post-convergence segment back to the Companion / Imam / Prophet. Closes the bug surfaced 2026-06-09 by the Tirmidhi #1 case where the chain stops at سماك بن حرب and never reaches Ibn ʿUmar.

**Apply mode: differential repair, NOT drop-and-recreate** (spec §1.1). Introduces new `--mode=repair` in `regen-isnad-graph.ts` that diffs each hadith's CSV-derived chains against live Neo4j and surgically repairs only what changed. Forbidden: any global `MATCH ()-[r:INCLUDES]->() DELETE r` pattern. Hand-curated edges (`r.source NOT STARTS WITH 'dv-'`) are preserved through the pass. Repair wall time ~3–5 days unattended — the trade-off the user explicitly accepted for non-destructive correctness.

**Phases (each independently committable):**
0. Audit — ح-occurrence stats, false-positive risk on quoted-matn ح, `arabicText` diacritization probe (5 tasks)
1. Extractor — `extract_isnad_branches`, convergence detection, post-convergence stitching, ≥12 unit tests, smoke test on Tirmidhi #1 (8 tasks)
2. Integration — single `_compute_chain_indx` replaces W1/W2/W3 paths, `arabicText` for Imami, archive obsolete English splitter (7 tasks)
3. CSV format — `|`-delimiter for multi-branch `chain_indx`, TS `parseIndices` and `buildTier1Resolution` updated (5 tasks)
4. Resolver enrichment (FR-5) — kunya alias indexing in `build_narrator_index` (4 tasks; ambiguous-kunya disambiguator deferred to own track)
5. UI — chain-grouped `getFullChainGraphGrouped`, `IsnadChain` renders N rows with taḥwīl separator, convergence narrator badge (4 tasks)
6a. Build `mode-repair.ts` — diff function, surgical Cypher, soft-tombstone, dry-run, resume + checkpoint, pre-snapshot backup, forbidden-pattern test (10 tasks)
6b. Run repair — backup CSV, rebuild, full dry-run inspection, abort-on-mass-deletion check, detached live run, daily check-in, acceptance + injected-human-edge G-7 test (10 tasks)
7. Closeout (4 tasks)

Seven enforceable guardrails (each a test): (G-1) Tirmidhi #1 has 2 `:Chain` nodes; (G-2) convergence narrators in both chains; (G-3) shared post-convergence segment in both; (G-4) superset of old `chain_indx` narrators; (G-5) UI renders N separate chains; (G-6) per-tradition coverage floors (K6 4.5–6.5 avg, Al-Kāfī ≥80%, Musnad Zayd ≥70%); **(G-7) non-destructive repair — injected human edges survive, zero hadiths lose all `:HAS_CHAIN` edges during repair**.

Honors the existing reified `:Chain` schema and the multi-isnad-aware `loadChainForRow` from `neo4j_isnad_graph_regen_20260516` — does not duplicate them. The TS loader already supports multi-branch via `NarratorResolutionResult[]`; this track wires the Python side to feed it correctly.

---

## [ ] Track: Tier-2 LLM Second-Opinion Pass for Taḥwīl-Aware Isnad Extraction [tier2_llm_isnad_reconciliation_20260612]

**Type:** Feature (data engineering — chain extraction coverage uplift)
**Status:** Planned
**Created:** 2026-06-12
**Priority:** P0
**Depends on:** `uniform_isnad_extraction_20260609` (Phases 1 + 2 — Tier-1 extractor + `_compute_chain_indx` wired into the CSV builder)
**Blocks:** `uniform_isnad_extraction_20260609` Phase 6b re-run on K6 multi-branch (otherwise repair locks in the Tier-1-only floor)
**Parallel-safe with:** `uniform_isnad_extraction_20260609` Phases 4 (resolver) + 5 (UI), `narrator_enrichment_20260425`, `gds_setup_analytics_20260425`
**Research basis:** `.omc/research/uniform-isnad/research-session/report.md` (5-stage scientist mission, 2026-06-12)

Adds a Tier-2 LLM reconciliation phase on top of candidate C (LCS-suffix Tier-1) from the parent track. Fires ONLY on Tier-1 output that fails specific suspicion checks (single-narrator branches when ح present, branch-count != ح-count+1, no convergence detected in multi-branch row, low resolver-rate). Calls Claude Sonnet 4.6 with schema-validated JSON output via Anthropic SDK `tool_use`. Strict hallucination guard: every emitted narrator must resolve to `scholar_indx` in `all_rawis.csv` or be tombstoned as `NameMention` for the existing er-staging HITL flow. Reconciliation NEVER silently overwrites Tier-1 — every divergence is logged.

Justified by the research mission's conclusion that guaranteed coverage on taḥwīl-aware extraction is **provably unreachable** (classical literature itself underspecifies ح semantics; ~5–15% of taḥwīl hadiths are genuinely ambiguous in source). The honest architecture is a three-tier hybrid (rule + LLM + HITL); this track implements Tier-2.

**Cost envelope:** Claude Sonnet 4.6 at $3/MTok in + $15/MTok out. Per row ~$0.0045 (~500 in + 200 out). Full K6 multi-branch corpus (1,768 rows): ~$8 worst case, $2–3 with the suspicion filter. Full 99k corpus: ~$450 worst case, $15–25 realistic. **Hard ceiling: $50/run** — aborts mid-pass and falls back to Tier-1 if exceeded.

**Phases (each independently committable):**
0. Audit + scaffolding — calibrate suspicion thresholds against `tahweel-gold.jsonl`, hand-author `tahweel-gold-disagreements.jsonl`, confirm Anthropic model ID + er-staging schema (6 tasks)
1. Suspicion detector + cost tracker — `is_suspicious`, `add_cost` / `check_ceiling`, ≥10 unit tests (4 tasks)
2. Prompt + LLM client — `extract_branches_v1.md` with Jade sign-off, `LLMClient` Protocol, `MockLLMClient`, `AnthropicClient` with tool_use, 3-attempt retry, response cache, one live smoke call (9 tasks)
3. Hallucination guard + reconciler — `guard_branches` + NameMention emission, `reconcile_tier1_tier2` covering all 6 FR-4.2 disagreement codes (5 tasks)
4. Pipeline integration — `_compute_chain_indx_with_tier2`, `name_mention_indx` sidecar column, `DISABLE_TIER2` passthrough, `--dry-run-tier2`, audit log + cost-ceiling incident file (8 tasks)
5. Guardrail tests — G-1 through G-5 + G-7 automated; G-6 deferred to live run (7 tasks)
6. Dry-run validation pass over the K6 multi-branch subset (5 tasks)
7. Live K6 pass (1,768 rows, ~5 min wall time, monitored cost) (5 tasks)
8. Coverage measurement + G-6 acceptance (diagnose-script delta + Jaccard re-eval) (5 tasks)
9. Closeout (5 tasks)

Seven enforceable guardrails (each a test): (G-1) suspicion detector triggers on ≥1 mishandled gold fixture; (G-2) hallucination guard tombstones planted phantom narrator; (G-3) cost ceiling aborts mid-pass at $0.05 cap; (G-4) `DISABLE_TIER2=1` produces bit-identical Tier-1-only CSV; (G-5) every FR-4.2 disagreement type produces its event code in the audit log; (G-6) K6 multi-branch avg narrators per chain moves into [4.8, 6.8] from [4.5, 6.5], Jaccard p25 from 0.625 toward 0.75; (G-7) cached re-run makes zero LLM calls and produces byte-identical audit log.

Out of scope: switching extractor primary from rule-based to LLM-based; fine-tuning a custom Arabic NER model; multi-vendor LLM support (Claude only); expanding the gold set beyond the 5 fixtures; chain-of-thought / self-consistency / ensembling re-prompting strategies. All filed as follow-up track candidates.

---

## [x] Track: Taḥwīl Annotation Instruction Kit [tahweel_annotation_kit_20260612]

**Closed:** 2026-06-24 — 36/36 tests PASS; G-2/G-3/G-4/G-5 fully passed, G-1 readability + G-6 human-annotation pass deferred per Risk-D/E. Guide (6,658 words, 9 sections) + 4 tools + 4 G-N test files shipped. Gold backfilled with `kit_version: "1.0.0"` + per-row metadata. Follow-ups filed: `tahweel_gold_expansion_2026q3`, `tahweel_kit_g1_readability_check`, `tahweel_llm_draft_runtime`. See `conductor/tracks/tahweel_annotation_kit_20260612/verification.md`.

**Type:** Feature (documentation + tooling)
**Status:** Closed
**Created:** 2026-06-12
**Priority:** P1
**Depends on:** — (parallel-safe with `uniform_isnad_extraction_20260609` and `tier2_llm_isnad_reconciliation_20260612`)
**Blocks:** — (enables tighter G-1/G-2/G-3 acceptance in both extraction tracks once gold set grows from 5 → 30+ fixtures)

Builds an annotation instruction kit + SOP so the taḥwīl gold-set expansion (used as ground truth by both extraction tracks) becomes a tractable workflow rather than a heroic one-off Jade-only effort. Currently 5 fixtures exist; the kit makes 30+ tractable and 100+ achievable with multiple annotators. The deliverable target reader is an **Islamic studies graduate student** with hadith knowledge but no Python — explicitly NOT engineers. The kit documents the seven canonical case types (single chain, classic 2-branch taḥwīl, co-transmitter heads, no-convergence parallel, surface-form drift, pronoun/elided references, 3+-branch pathological) with worked examples drawn from existing fixtures. Includes a scholarly-framing section that explicitly disavows muḥaddith authority — annotators are linguistic extractors, not making ʿadāla / ḍabṭ judgments.

**Five deliverables:**
1. `docs/annotation/taḥwīl-annotation-guide.md` — the main authority document (~6 hr drafting, the dominant work).
2. `datasets/hadith-data/__tests__/fixtures/pull_next_candidates.py` — stratified candidate puller (extends existing pull script with cross-tradition + dedup against `tahweel-gold.jsonl`).
3. `datasets/hadith-data/__tests__/fixtures/validate_annotation.py` — linter that gates entry into `tahweel-gold.jsonl`; staging-then-promote workflow.
4. `docs/annotation/calibration-test.md` + scorer — 5 redacted-gold fixtures; annotator must score ≥0.85 average Jaccard before contributing real annotations.
5. `docs/annotation/iaa-tooling.md` + `compute_iaa.py` — Krippendorff's α (chosen over Cohen's κ per TC-2 because of variable-length list-of-lists) for inter-annotator agreement when 2+ people overlap.

**Phases (each independently committable):**
0. Audit + scaffolding (case-type coverage gap analysis vs existing 5 fixtures) (4 tasks)
1. Write annotation guide — all 7 case types + decision tree + scholarly framing + quality checklist (~6 hr; dominant phase) (8 tasks)
2. Calibration test build (redact existing fixtures + scorer) (4 tasks)
3. Validator implementation + bad-annotation fixture suite for G-3 (5 tasks)
4. IAA tooling (Krippendorff's α implementation + synthetic-disagreement fixture for G-4) (4 tasks)
5. Next-candidate pull script extension (stratification + dedup) (4 tasks)
6. **Dogfood: pull 5 new candidates, Jade annotates via guide, validate, promote, re-run algo_evaluate.py** — load-bearing acceptance test (5 tasks)
7. Closeout + commit (3 tasks)

Six enforceable guardrails: (G-1) non-engineer test reader scores ≥0.85 on 2 calibration cases; (G-2) calibration scorer flags deliberately-wrong annotation; (G-3) validator catches 5 hand-crafted bad annotations; (G-4) IAA tooling shows κ≈0.7 on synthetic 30%-disagreement set; (G-5) pull script enforces source + ح-count stratification; (G-6) end-to-end dogfood — 5 new annotations pass validator and don't regress bake-off Jaccard.

**Why this track exists:** the 2026-06-12 research mission ([report.md](../../.omc/research/uniform-isnad/research-session/report.md)) concluded that guaranteed extraction coverage is provably unreachable due to scholarly ambiguity in Ibn al-Salah's two ح readings (تحويل vs الحديث). The honest path forward is a larger annotated gold set that lets us correctly calibrate where the algorithm should defer to HITL — and that requires making annotation a non-heroic workflow.
