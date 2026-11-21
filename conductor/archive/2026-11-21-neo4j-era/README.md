---
type: archive-index
title: Neo4j-era tracks, archived 2026-11-21
---

# Neo4j-era tracks (archived 2026-11-21)

The project left Neo4j for PostgreSQL and Drizzle. The accepted design is
[`docs/architecture/data-architecture.md`](../../../docs/architecture/data-architecture.md);
the new tracks in [`conductor/tracks.md`](../../tracks.md) are derived from its
section 12. Every track below was written against the Neo4j graph (Cypher
loaders, `:Chain`/`:Assessment` nodes, GDS, Neo4j vector indexes), so the
whole set was moved here with `git mv` at commit `af2f90b`. Nothing was
deleted; history follows the files.

- [`tracks.md`](./tracks.md) is the old track index, unchanged.
- [`tracks/`](./tracks/) holds every old track folder, unchanged.

## Disposition (per design section 13.5)

| Old track | Disposition | Where the work lives now |
| --- | --- | --- |
| `neo4j_isnad_graph_regen_20260516` | **Superseded** (design 13.5) | Reified chains, tradition-scoped assessments and tombstones are now Postgres tables (design 5.5, 5.6). Its open items 1.13 and 2.7 are Neo4j-only and die with it |
| `gds_setup_analytics_20260425` | **Superseded** (design 13.5) | Graph analytics run offline in Python over an export of `narrator_transmissions` (design section 1). Parked until identity coverage makes analytics meaningful |
| `vector_embedding_pipeline_20260425` | **Retargeted** to pgvector (design 13.5) | `vectors-semantic-search_20261121` |
| `hadith_dataset_consolidation_20260723` | **Carried forward**; Phase 3 becomes "Postgres schema and COPY load" (design 13.5) | `bundle-to-postgres-loader_20261121`. The exporter and validator stay as the source format |
| `uniform_isnad_extraction_20260609` | **Split.** Phases 0 to 2 done (Python extractor live). Phases 3 and 6 superseded (Neo4j loader and repair mode) | Phase 4 (kunya aliases) → `narrator-identity-resolution_20261121`; phase 5 (multi-chain UI) → `query-port-and-action-switch_20261121` and `ui-polish_20261121` |
| `tier2_llm_isnad_reconciliation_20260612` | **Parked** | Revisit if job J5 (extractor-noise samples) shows branch-split errors are material |
| `tahweel_annotation_kit_20260612` | **Complete** (closed 2026-06-24; its `metadata.json` still says `planned`) | Follow-ups (gold expansion, G-1 readability, LLM draft runtime) parked with the tier-2 track |
| `narrator_enrichment_20260425` | **Retargeted** | Dedup and tradition → `narrator-identity-resolution_20261121`; dates and regions as cited claims → `evidence-and-biography-curation_20261121` |
| `grade_normalization_20260425` | **Superseded** by tradition-scoped, cited assessments | `grading-coverage_20261121` |
| `scholarly_metadata_layer_20260425` | **Retargeted** | Verdicts → `grading-coverage_20261121`; commentary → `evidence-and-biography-curation_20261121` |
| `text_cleanup_embedding_prep_20260425` | **Retargeted** | Refusal and OCR artifacts → `translation-recovery_20261121`; normalization → `vectors-semantic-search_20261121` |
| `translate_classical_collections_20260418` | **Retargeted** | `translation-recovery_20261121` (the 29,915 classical recoveries with no model identity are probably this track's output) |
| `comparative_ingestion_20260322` | **Retargeted** | Research route and `commit-parallel.ts` in `query-port-and-action-switch_20261121`; AI parallels default to `proposed` (owner question 6) |
| `data_acquisition_20260521` | **Parked**, except Wave 1 (K6 grades) → `grading-coverage_20261121` | Corpus expansion (waves 0, 2 to 6) waits until after cutover. Folder has no `metadata.json` |
| `import_musnad_ahmad_20260418` | **Superseded** | The four classical collections are already in the unified corpus; their English is `translation-recovery_20261121` |
| `fix_hadith_data_integrity_20260418` | **Complete** (Phase 4 moved out long ago) | None |
