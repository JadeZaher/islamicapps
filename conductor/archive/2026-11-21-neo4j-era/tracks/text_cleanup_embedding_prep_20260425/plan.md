# Text Cleanup & Embedding Preparation — Implementation Plan

## Phase 1: OCR Artifact Cleanup (3 tasks)

### Task 1.1: Identify and categorize OCR artifacts
- Query all 7,302 Arabic texts with numeric sequences
- Sample 50 to categorize: page numbers, footnote refs, corrupted chars, verse numbers
- Determine which are genuine (verse refs) vs noise

### Task 1.2: Build Arabic text cleaner
- Script: `src/scripts/clean-arabic-text.ts`
- Strip: isolated numeric runs, page markers, footnote indicators
- Preserve: Quran verse references (may need pattern: surah:ayah format)
- Backup original to text_arabic_raw before modifying

### Task 1.3: Apply OCR cleanup
- Run cleaner in batches against Neo4j
- Log changes count per source collection (Zaydi likely highest)

## Phase 2: AI Translation Refusal Repair (3 tasks)

### Task 2.1: Extract all 484 refusal texts
- Query hadiths where text_english CONTAINS 'I cannot' OR 'I can't' OR 'I'm unable'
- Export as JSONL with hadith_id + text_arabic for re-translation

### Task 2.2: Re-translate via Ollama
- Use existing translation pipeline (datasets/translate_ollama_generic.py)
- Target: translate all 484 Arabic texts to English
- Fallback prompt: focus on faithful academic translation, not content filtering

### Task 2.3: Merge re-translations back to Neo4j
- Backup text_english_raw before overwriting
- Update text_english with new translations
- Verify no new refusals in output

## Phase 3: Short Text Triage (2 tasks)

### Task 3.1: Categorize short texts
- Query 922 hadiths with Arabic text <20 chars
- Categorize: fragment, chapter heading, cross-reference, legitimate short hadith
- Determine: which should be flagged `embedding_skip = true`

### Task 3.2: Flag non-embeddable texts
- SET `embedding_skip = true` on texts too short or fragmentary for meaningful embedding
- These will be excluded from the vector index but remain in the graph

## Phase 4: Text Normalization Pipeline (2 tasks)

### Task 4.1: Create Arabic normalization function
- Reuse/extend normalizeAr from link-sanad-chains.ts
- Normalize: harakat removal, alif variants, ta marbuta, alif maqsura
- Store normalized version as `text_arabic_normalized` (used for embedding, original preserved)

### Task 4.2: Batch normalize all Arabic texts
- Script: `src/scripts/normalize-hadith-text.ts`
- Process all 98,801 hadiths with Arabic text
- Store normalized version for embedding pipeline to consume

## Phase 5: Verification (1 task)

### Task 5.1: Re-run text quality checks
- Run data-readiness-audit.ts text section
- Verify: OCR artifacts <500, refusals = 0, short texts flagged
- Document final counts
