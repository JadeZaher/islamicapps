# Vector Embedding Pipeline — Implementation Plan

## Phase 1: Embedding Model Selection & Setup (3 tasks)

### Task 1.1: Verify Neo4j version supports vector indexes
- Query: `CALL dbms.components() YIELD versions`
- Require: 5.11+ for vector indexes, 2025.10+ for native VECTOR type
- If older: plan upgrade path

### Task 1.2: Set up embedding model runtime
- Option A (preferred): Local inference with @xenova/transformers (ONNX runtime)
  - Install: `npm install @xenova/transformers`
  - Load CAMeLBERT-CA for Arabic, BGE-M3 for English
  - Test: embed a sample hadith, verify dimensions
- Option B (fallback): OpenAI API
  - Use text-embedding-3-small (1536 dims)
  - Estimate cost: ~99K texts * 2 languages * ~500 tokens avg = ~100M tokens = ~$2

### Task 1.3: Create embedding utility module
- File: `src/lib/embeddings/embed.ts`
- Functions: `embedArabic(text: string): Promise<number[]>`
- Functions: `embedEnglish(text: string): Promise<number[]>`
- Batch support: `embedBatch(texts: string[], lang: 'ar' | 'en'): Promise<number[][]>`

## Phase 2: Embedding Generation Pipeline (3 tasks)

### Task 2.1: Build batch embedding script
- Script: `src/scripts/generate-embeddings.ts`
- Process: stream hadiths from Neo4j -> embed -> write back
- Flags: `--lang ar|en|both`, `--batch-size 50`, `--skip-existing`, `--sample N`
- Progress: log every 500 hadiths with ETA

### Task 2.2: Generate Arabic embeddings
- Run: `npx tsx src/scripts/generate-embeddings.ts --lang ar`
- Target: all hadiths with text_arabic_normalized and NOT embedding_skip
- Estimated time: ~2-4 hours for 99K texts (local) or ~10 min (API)

### Task 2.3: Generate English embeddings
- Run: `npx tsx src/scripts/generate-embeddings.ts --lang en`
- Target: all hadiths with text_english and NOT embedding_skip

## Phase 3: Neo4j Vector Index Creation (2 tasks)

### Task 3.1: Create vector indexes
```cypher
CREATE VECTOR INDEX hadith_embedding_ar IF NOT EXISTS
FOR (h:Hadith) ON (h.embedding_ar)
OPTIONS { indexConfig: { `vector.dimensions`: 768, `vector.similarity_function`: 'cosine' } }

CREATE VECTOR INDEX hadith_embedding_en IF NOT EXISTS
FOR (h:Hadith) ON (h.embedding_en)
OPTIONS { indexConfig: { `vector.dimensions`: 1024, `vector.similarity_function`: 'cosine' } }
```

### Task 3.2: Verify indexes
- Check index population: `SHOW INDEXES WHERE type = 'VECTOR'`
- Test query: find 5 nearest neighbors for a sample hadith

## Phase 4: Semantic Search API (3 tasks)

### Task 4.1: Create semantic search server action
- File: `src/app/actions/semantic-search-actions.ts`
- Function: `searchHadithsBySemantic(query: string, lang: 'ar' | 'en', limit: number)`
- Embed query text -> vector search -> return hadiths with scores
- Enrich results with graph context (source, grade, tradition)

### Task 4.2: Create hybrid search (vector + graph)
- Combine: vector similarity for content + graph traversal for context
- Example: "Find sahih hadiths about prayer" = vector search "prayer" + filter grade_canonical = 'sahih'

### Task 4.3: Add semantic search to UI
- Add search mode toggle: keyword vs semantic
- Display similarity scores alongside results

## Phase 5: Cross-Tradition Similarity Analysis (2 tasks)

### Task 5.1: Build cross-tradition similarity script
- Script: `src/scripts/find-cross-tradition-similarities.ts`
- For each Sunni hadith: find top-3 most similar Shia hadiths (and vice versa)
- Store as new relationship: `(h1:Hadith)-[:SEMANTICALLY_SIMILAR {score: 0.95}]->(h2:Hadith)`
- Filter: only store if score > 0.85

### Task 5.2: Analyze similarity results
- How many cross-tradition pairs found?
- Which topics have highest cross-tradition similarity?
- Which traditions have the most unique content (lowest avg similarity to others)?

## Phase 6: Verification & Benchmarking (2 tasks)

### Task 6.1: Quality spot-check
- Manually verify 20 semantic search queries across topics
- Check: are results relevant? Do similarity scores make sense?
- Test edge cases: very short queries, Arabic-only, English-only

### Task 6.2: Performance benchmarking
- Measure: query latency for vector search (target: <100ms)
- Measure: embedding generation throughput
- Document: total embedding storage size in Neo4j
