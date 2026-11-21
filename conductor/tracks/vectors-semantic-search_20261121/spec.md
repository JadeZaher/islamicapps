---
type: track-spec
title: Vectors and semantic search
tags: [vectors-semantic-search_20261121, planned]
resource: ./metadata.json
---

# Vectors and semantic search

Design: [../../../docs/architecture/data-architecture.md](../../../docs/architecture/data-architecture.md) section 12 step 11; section 5.13 (vector table); section
7.4 (vector table design, bit pre-filter); section 1.3 (when to flip to HNSW);
section 1.4 (memory).

Retargets archived
[vector_embedding_pipeline_20260425](../../archive/2026-11-21-neo4j-era/tracks/vector_embedding_pipeline_20260425/spec.md)
from Neo4j vector indexes to pgvector (design 13.5), and the Arabic
normalization part of
[text_cleanup_embedding_prep_20260425](../../archive/2026-11-21-neo4j-era/tracks/text_cleanup_embedding_prep_20260425/spec.md)
(the project's Arabic `norm()` now exists; OCR and refusal artifacts moved to
translation-recovery).

## Goal

"Similar hadiths" ships on pgvector with recorded benchmarks.

## Scope

Benchmark with the filtered query; the core migration creating
`hadith_embeddings` (`vector` is already enabled on the Railway database, so
the "fail closed" check passes); offline embedding; the similar-hadiths
feature; `hadith_embeddings.is_public` maintained by `setCollectionRights`;
the vector-readiness check ported from `data-readiness-audit.ts`.

## Out of scope

An approximate (HNSW) index at launch; free-text semantic search unless Q8
picks a query embedder; cross-tradition analytics.

## Acceptance checks

- Benchmarks of the filtered query recorded (latency, recall against exact).
- Memory added by the hot set measured against section 1.4.
- Similar hadiths shows only public rows.

## Open owner questions (section 14)

- Q8: embedding model and request-time query embedding. Blocks this track.
