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

**Key files:**
- `datasets/hadith-data/extract_classical_for_translation.py` (NEW)
- `datasets/hadith-data/classical_collections_translated.jsonl` (output)
- `datasets/translate_ollama_generic.py` (existing translation pipeline)

---

## [ ] Track: Import Classical Musnad & Sunan Collections [import_musnad_ahmad_20260418]

**Type:** Feature
**Status:** Planned
**Created:** 2026-04-18
**Priority:** P1
**Dependencies:** fix_hadith_data_integrity_20260418, translate_classical_collections_20260418

Extract 4 classical collections (Ahmad ~23.5k, Darimi ~2.5k, Shafi'i ~2k, Muwatta ~1.9k) from `pure_canon.jsonl` into a clean CSV, map sanad to existing narrator IDs, merge translations, then import via existing pipeline. Shafi'i imports as matn-only (no isnads in source data — see `shafii-research.md`). Anthologies deferred to separate scholarly analysis track.

**Phases:**
1. Data Extraction & CSV Generation — Python script (5 tasks)
2. Source Registry & Import Updates — TypeScript (3 tasks)
3. Import Execution & Verification (4 tasks)

**Key files:**
- `datasets/hadith-data/extract_classical_musnad.py` (NEW)
- `datasets/hadith-data/hadith_classical_musnad.csv` (output)
- `src/lib/constants/sources.ts` (add `tier` field)
- `shafii-research.md` (Shafi'i isnad sourcing research)

---

## [ ] Track: Automated Cross-Cultural Parallel Ingestion Pipeline [comparative_ingestion_20260322]

**Type:** Feature
**Status:** Planned
**Created:** 2026-03-22

Discovery script (GPT-4o + Sefaria + Bible API) -> JSON staging file -> human review UI at `/admin/comparative/review` -> idempotent ingestion script that commits approved candidates to Neo4j as `CrossCulturalParallel` nodes.

**Phases:**
1. Discovery Script and Staging Schema (`npm run db:find-parallels`)
2. Human Review UI (`/admin/comparative/review`)
3. Ingestion Script (`npm run db:ingest-parallels`)
4. Documentation and Environment Setup

**Required:** `OPENAI_API_KEY`
**Optional:** `BIBLE_API_KEY`, `SEFARIA_API_KEY`
**New dep:** `npm install openai`
