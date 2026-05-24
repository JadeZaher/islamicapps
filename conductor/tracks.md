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
