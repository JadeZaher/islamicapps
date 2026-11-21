# Vector Embedding Pipeline & Semantic Search

## Problem

The hadith corpus (99K texts in Arabic + English) currently supports only keyword search and graph traversal. There is no semantic search capability — users can't find hadiths by meaning, detect similar hadiths across traditions, or cluster hadiths by topic.

## Goal

Build a vector embedding pipeline that:
1. Generates embeddings for all hadith texts (Arabic + English separately)
2. Stores embeddings directly in Neo4j using native vector indexes
3. Enables semantic search across the corpus
4. Enables cross-tradition hadith similarity detection
5. Provides a foundation for future automated grading (matn analysis)

## Architecture

```
Hadith.text_arabic_normalized -> CAMeLBERT-CA -> 768-dim -> Hadith.embedding_ar
Hadith.text_english           -> BGE-M3       -> 1024-dim -> Hadith.embedding_en
```

Use Neo4j native vector indexes (HNSW) for similarity search. No external vector store needed at current scale (~99K documents).

## Embedding Models

| Property | Model | Dimensions | Why |
|---|---|---|---|
| embedding_ar | CAMeLBERT-CA | 768 | Trained on classical Arabic corpus |
| embedding_en | BGE-M3 | 1024 | Best multilingual, supports Arabic-English cross-lingual |

Alternative: If local GPU unavailable, fall back to OpenAI text-embedding-3-small (1536-dim) for both languages.

## Key Use Cases

1. **Semantic search**: "Find hadiths about patience in hardship" -> vector similarity
2. **Matn variant detection**: Find same hadith across different collections with different wording
3. **Cross-tradition matching**: Find semantically similar hadiths in Sunni vs Shia collections
4. **Topic clustering**: Auto-cluster hadiths by semantic topic without manual tagging
5. **Isra'iliyyat detection**: Embed Biblical/Talmudic texts -> find similar hadiths
6. **Anomaly detection**: Hadiths far from their topic cluster = candidates for scholarly review

## Constraints

- Skip hadiths where `embedding_skip = true` (set by text cleanup track)
- Embedding generation is compute-intensive; batch processing with progress tracking
- Neo4j vector index requires Neo4j 5.11+ (verify version)
- Keep embeddings as node properties, not separate nodes (simpler, faster)

## Success Criteria

- >95% of hadiths have both Arabic and English embeddings
- Vector index created and queryable
- Semantic search returns relevant results (manual spot-check of 20 queries)
- Cross-tradition similarity query returns meaningful pairs
