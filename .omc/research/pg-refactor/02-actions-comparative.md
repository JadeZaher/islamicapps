# Comparative actions + pipeline catalog
Date: 2026-11-21. Intent: inventory every Neo4j touchpoint in the comparative domain so the Postgres/Drizzle schema and port can cover it. Read-only investigation.

Files: A = src/app/actions/comparative-actions.ts (571 lines, 'use server'). Neo4j client: runQuery, runWrite, runTransaction from '@/lib/db/neo4j'.

## 0. Key findings
- The "discovery -> review -> commit" flow is NOT implemented as the older conductor track described. Reality: there is NO review/staging step. processHadith calls you.com then commits straight to Neo4j (src/lib/comparative/pipeline.ts:141). src/scripts/types/parallel-candidate.ts (staging JSON with PENDING/APPROVED/REJECTED/COMMITTED) is an orphaned contract from conductor/tracks/comparative_ingestion_20260322 (plan.md:18-70, which assumed OpenAI + Sefaria + Bible API). Nothing imports it.
- ingest-approved-parallels.ts DOES NOT EXIST (only mentioned at src/scripts/archive/README.md:88 as "kept"; not found in src/scripts or archive). The closest file, src/scripts/ingest-er-approved.ts, is the unrelated narrator entity-resolution HITL ingest (:NameMention -[:RESOLVES_TO]-> :Narrator from er-staging.jsonl). Not comparative.
- POST /api/comparative/research has NO caller in src (no fetch to it). conductor/tech-stack.md:55 documents it as the single allowed API route. No auth check in the route or in src/app/admin/layout.tsx. Anyone who can reach the URL can spend you.com credits.
- Property-name drift on Hadith: route.ts uses h.text_en / h.chapter / h.category (matches graph-actions.ts:895,957); find-parallels.ts:79-84 uses h.title / h.text_english / h.primary_topic (legacy v1 names, likely returns 0 rows on the v2 graph; stale script). Hadith columns needed in PG: id, chapter, category, text_en, created_at.
- route.ts:72 and :102 use `(h.chapter ?? h.category)` which is not valid Cypher (needs coalesce()), and pass plain JS numbers for SKIP/LIMIT (find-parallels wraps them in neo4j.int). The route is probably broken today. Port it, do not preserve it.
- All mutators have no authz and no revalidate; the admin UI calls them from a client component.
- updateTradition / updateSourceText / updateParallel interpolate object KEYS from caller data into Cypher (SET t.${k}). In Drizzle this becomes a typed column allowlist.
- delete* use DETACH DELETE (removes edges only). Deleting a tradition leaves cross_parallels orphaned in Neo4j, which then vanish from reads because FROM_TRADITION is a required MATCH. In PG choose FK behaviour deliberately (recommend RESTRICT on source_texts/traditions that have parallels).
- Proposed schema in docs/architecture/data-architecture.md:186-200 lacks columns this code needs; see section 6.

## 1. Neo4j schema used by this domain
Labels: ReligiousTradition, SourceText, MotifTag, CrossCulturalParallel (plus existing Hadith, Narrator, Chain, Location).
Relationships:
- (SourceText)-[:BELONGS_TO]->(ReligiousTradition)
- (Hadith)-[:HAS_PARALLEL]->(CrossCulturalParallel)
- (CrossCulturalParallel)-[:PARALLELS]->(SourceText)
- (CrossCulturalParallel)-[:FROM_TRADITION]->(ReligiousTradition)
- (CrossCulturalParallel | Hadith)-[:TAGGED_WITH]->(MotifTag)
- (Narrator)-[:TRANSMITTER_OF_TRADITION]->(ReligiousTradition)
- (Location)-[:HEARTLAND_OF]->(ReligiousTradition)
- read-only traversal: (Hadith)-[:HAS_CHAIN]->(Chain)-[:INCLUDES]->(Narrator)

Constraints (src/lib/db/schema.ts:86-92): unique ReligiousTradition.id and .name; SourceText.id; MotifTag.id and .name. Indexes (schema.ts:186-188): SourceText.tradition_name, SourceText.canonical_reference, MotifTag.category. pipeline_key convention: src/lib/db/neo4j-helpers.ts:33,190. SourceText.canonical_reference is the MERGE key but only indexed, not unique.

Node properties:
- ReligiousTradition: id(uuid), name, name_arabic, description, geographic_heartlands string[], created_at
- SourceText: id, title, title_original, tradition_name (denormalised copy), author, approximate_date_ce (string), canonical_reference, description, created_at
- MotifTag: id, name, category, description, created_at
- CrossCulturalParallel: id, pipeline_key (commit path only), parallel_type, isra_iliyyat_status, confidence_level, hadith_excerpt_en, source_text_original, source_text_en, scholarly_analysis (markdown with citations, can be several KB), created_at, updated_at (commit path only)

Enums (A:9-28): ParallelType {CONDEMNATION, CULTURAL_BLEED, SHARED_SOURCE, DIRECT_BORROWING, APOLOGETIC, DISPUTED}; IsraIliyyatStatus {MUWAFIQ, MUKHALIF, MASKUT_ANHU, NONE}; ConfidenceLevel {HIGH, MEDIUM, LOW}; MotifCategory {ESCHATOLOGY, CREATION, PROPHETIC_STORIES, LEGAL, WISDOM, PERSIAN_INFLUENCE, COSMOLOGY}. you-research-client also admits parallel_type 'NONE'; pipeline.ts:119 only skips when parallel_exists === 'NO', so a PARTIAL answer with type NONE can be persisted as 'NONE' (violates the ParallelType enum; guard or allow).

## 2. Server actions in comparative-actions.ts (every export async function)
Callers legend: ADMIN = src/app/admin/comparative/client.tsx (client component); ADMINPAGE = src/app/admin/comparative/page.tsx; PUB = src/app/comparative/client.tsx or page.tsx; HADITH = src/app/hadith/[id]/page.tsx; NARR = src/app/narrator/[id]/page.tsx; none = no caller found in src.

### Traditions
- createReligiousTradition(data) :110. WRITE. CREATE (t:ReligiousTradition {id, name, name_arabic, description, geographic_heartlands, created_at}). Returns string uuid. Caller ADMIN:51. Relational: INSERT religious_traditions (name UNIQUE).
- getAllTraditions() :131. READ. MATCH (t) OPTIONAL MATCH (s:SourceText)-[:BELONGS_TO]->(t) OPTIONAL MATCH (n:Narrator)-[:TRANSMITTER_OF_TRADITION]->(t) RETURN t, count(DISTINCT s) source_count, count(DISTINCT n) narrator_count ORDER BY t.name. Returns ReligiousTradition[] ({...props, source_count, narrator_count}). Callers ADMINPAGE, PUB page. Relational: SELECT with two counts (source_texts.religious_tradition_id, narrator_religious_traditions), cast ::int.
- updateTradition(id, data) :154. WRITE. MATCH (t {id}) SET t.<dynamic keys> skipping undefined. void. Callers none. Relational: UPDATE with column allowlist.
- deleteTradition(id) :150. WRITE. MATCH (t {id}) DETACH DELETE t. void. Caller ADMIN:62. Relational: DELETE; cascade narrator_religious_traditions and location_religious_traditions; RESTRICT if source_texts/cross_parallels reference it.

### Source texts
- createSourceText(data) :169. WRITE. CREATE (s:SourceText {id, title, title_original, tradition_name, author, approximate_date_ce, canonical_reference, description, created_at}), no edge. Returns uuid. Caller ADMIN:185. Relational: INSERT source_texts.
- linkSourceTextToTradition(sourceTextId, traditionId) :196. WRITE. MERGE (s)-[:BELONGS_TO]->(t). void. Caller ADMIN:187 (immediately after create). Relational: source_texts.religious_tradition_id FK (single-valued in practice; Neo4j would allow many).
- getAllSourceTexts({tradition_name?}) :204. READ. MATCH (s) OPTIONAL MATCH (s)-[:BELONGS_TO]->(t) [WHERE s.tradition_name = $] RETURN s, t ORDER BY s.tradition_name, s.title. Returns SourceText[] ({...s, tradition: t or null}). Caller ADMINPAGE (no filter). Relational: source_texts LEFT JOIN religious_traditions; tradition_name filter becomes a join on name.
- updateSourceText(id, data) :226. WRITE. SET s.<dynamic keys>. Callers none.
- deleteSourceText(id) :222. WRITE. DETACH DELETE. Caller ADMIN. Decide FK vs cross_parallels.

### Motif tags
- createMotifTag(data) :234. WRITE. CREATE (m:MotifTag {id, name, category, description, created_at}); uses CREATE not MERGE so a duplicate name throws on the unique constraint. Returns uuid. Caller ADMIN:546.
- getAllMotifTags(category?) :253. READ. MATCH (m:MotifTag) [WHERE m.category = $] ORDER BY m.category, m.name. Returns MotifTag[]. Caller ADMINPAGE.
- deleteMotifTag(id) :265. WRITE. DETACH DELETE. Caller ADMIN. Cascade hadith_motif_tags and parallel_motif_tags.
- tagHadith(hadithId, motifTagId) :269. WRITE. MERGE (h)-[:TAGGED_WITH]->(m). Callers none. INSERT hadith_motif_tags ON CONFLICT DO NOTHING.
- untagHadith(hadithId, motifTagId) :277. WRITE. DELETE the rel. Callers none.
- tagParallel(parallelId, motifTagId) :284. WRITE. MERGE (p)-[:TAGGED_WITH]->(m). Internal (createCrossParallel loop). INSERT parallel_motif_tags ON CONFLICT DO NOTHING.

### Cross-cultural parallels
- createCrossParallel(data) :294. WRITE. runTransaction of 4 statements: CREATE (p:CrossCulturalParallel {id, parallel_type, isra_iliyyat_status default 'NONE', confidence_level default 'MEDIUM', hadith_excerpt_en, source_text_original, source_text_en, scholarly_analysis, created_at}); MATCH Hadith CREATE (h)-[:HAS_PARALLEL]->(p); MATCH SourceText CREATE (p)-[:PARALLELS]->(s); MATCH ReligiousTradition CREATE (p)-[:FROM_TRADITION]->(t). Then, OUTSIDE the tx, one tagParallel per motif_tag_id. A MATCH on a missing id silently creates nothing, leaving an orphan p. Returns uuid. Caller ADMIN:317 (form has hadith picked via graph-actions searchHadiths). Relational: single tx INSERT cross_parallels + parallel_motif_tags; FKs remove the orphan bug.
- getParallelsForHadith(hadithId) :361. READ. MATCH (h {id})-[:HAS_PARALLEL]->(p) MATCH (p)-[:PARALLELS]->(s) MATCH (p)-[:FROM_TRADITION]->(t) OPTIONAL MATCH (p)-[:TAGGED_WITH]->(m) RETURN p, s, t, collect(DISTINCT m) ORDER BY p.created_at. Returns CrossCulturalParallel[] ({...p, source_text, tradition, motif_tags[]}). Caller HADITH:28 (wrapped in .catch(() => [])). Relational: cross_parallels JOIN source_texts JOIN religious_traditions, json_agg tags, WHERE hadith_id, ORDER BY created_at.
- deleteParallel(id) :384. WRITE. DETACH DELETE. Caller ADMIN. Cascade parallel_motif_tags.
- updateParallel(id, data) :388. WRITE. SET p.<dynamic keys> over Omit<data, hadith_id|source_text_id|tradition_id|motif_tag_ids>. Caller ADMIN. Allowlist: parallel_type, isra_iliyyat_status, confidence_level, hadith_excerpt_en, source_text_original, source_text_en, scholarly_analysis.
- searchParallels(filters?) :453. READ. MATCH (h)-[:HAS_PARALLEL]->(p), (p)-[:PARALLELS]->(s), (p)-[:FROM_TRADITION]->(t), OPTIONAL (p)-[:TAGGED_WITH]->(mt); AND-filters t.id, p.parallel_type, p.isra_iliyyat_status, p.confidence_level, mt.category; RETURN p, h{.id,.chapter,.category}, s, t, collect(DISTINCT mt) ORDER BY t.name, p.parallel_type LIMIT 100. Quirk: the motif_category filter is applied to the OPTIONAL MATCH row, so returned motif_tags only contains tags of that category. Returns CrossCulturalParallel[] with hadith{id,chapter,category}. Caller PUB client.tsx:107. Relational: filtered SELECT LIMIT 100; motif_category via EXISTS subquery (decide whether tags returned are all or filtered).
- getAllParallels(pagination?) :518. READ. Count query MATCH (h)-[:HAS_PARALLEL]->(p) RETURN count(p); page query same joins ORDER BY p.created_at DESC SKIP/LIMIT via toSkipLimit/paginate from '@/lib/pagination'. Adds v1 aliases hadith.title = chapter || category || null and hadith.primary_topic = category. Returns PaginatedResult<CrossCulturalParallel>. Callers ADMINPAGE, PUB page. Relational: SELECT + count(*) with LIMIT/OFFSET; keep alias mapping in the mapper.
- getComparativeStats() :564. READ. MATCH (p)-[:FROM_TRADITION]->(t) RETURN t.name AS tradition, p.parallel_type AS type, count(*) AS count ORDER BY tradition, type. Returns ComparativeStat[] {tradition, type, count}. Caller PUB page. Relational: GROUP BY religious_traditions.name, parallel_type; cast count to int (pg returns bigint as string).

### Narrator and location links
- linkNarratorToTradition(narratorId, traditionId) :396. WRITE. MERGE (n:Narrator)-[:TRANSMITTER_OF_TRADITION]->(t). Caller ADMIN:69. INSERT narrator_religious_traditions ON CONFLICT DO NOTHING.
- unlinkNarratorFromTradition(narratorId, traditionId) :404. WRITE. DELETE rel. Caller ADMIN.
- getTraditionConnectionsForNarrator(narratorId) :411. READ. (a) traditions of the narrator ORDER BY t.name; (b) MATCH (n)<-[:INCLUDES]-(c:Chain)<-[:HAS_CHAIN]-(h) MATCH (h)-[:HAS_PARALLEL]->(p)-[:FROM_TRADITION]->(t) MATCH (p)-[:PARALLELS]->(s) RETURN DISTINCT h{.id,.chapter,.category}, p{.id,.parallel_type,.isra_iliyyat_status}, t{.id,.name}, s{.title,.canonical_reference} ORDER BY h.chapter, h.category LIMIT 50. Returns {traditions: ReligiousTradition props[], hadiths_with_parallels: {hadith, parallel, tradition, source_text}[]}. Caller NARR:30 (.catch to empties). Relational: join table for (a); chain_mentions(narrator_id) -> chains -> hadith -> cross_parallels joins for (b), SELECT DISTINCT LIMIT 50. Fixed-depth joins only.
- linkLocationToTradition(locationId, traditionId) :443. WRITE. MERGE (l:Location)-[:HEARTLAND_OF]->(t). Callers none. INSERT location_religious_traditions.

Exports with no caller in src: updateTradition, updateSourceText, tagHadith, untagHadith, linkLocationToTradition, and the tradition_name filter of getAllSourceTexts. Exported types: ParallelType, IsraIliyyatStatus, ConfidenceLevel, MotifCategory, ReligiousTraditionData, SourceTextData, CrossCulturalParallelData, MotifTagData, ReligiousTradition, SourceText, MotifTag, HadithParallelSummary, CrossCulturalParallel, ComparativeStat. Admin client types its props as any[] (client.tsx:35-39), so the UI consumes raw property bags: PG mapper must keep snake_case names (name_arabic, source_count, hadith_excerpt_en, isra_iliyyat_status, motif_tags, source_text, tradition, hadith) and serialise created_at to a JSON-safe value.

## 3. Pipeline library (src/lib/comparative)
### faith-prompts.ts (202 lines), pure, no DB
- FAITHS: FaithConfig[] (:22) has 16 entries (route/CLI text says "15"): JUDAISM, CHRISTIANITY, ZOROASTRIANISM, MANICHAEISM, MANDAEISM, SABIANISM, YAZIDISM, SIKHISM, YORUBA, AKAN, IGBO, DINKA, TENGRISM, MESOPOTAMIAN, ATENISM, 'VEDIC RELIGION'. Each {id UPPERCASE, name display, primary_texts, context_block}. faith.name becomes ReligiousTradition.name on commit (e.g. "Judaism").
- getFaithById (:132), getFaithsByIds (:136), GENERIC_ASSESSMENT_TEMPLATE (:145, ends with the ---STRUCTURED ASSESSMENT--- block spec), buildResearchQuery(faith, {title, text_english, isnad?, transmission_period?}) (:186) = context_block + template.
- Option: keep the registry in code (prompt config) or seed religious_traditions with a research flag + prompt column. Commit path keys the tradition by display name.

### you-research-client.ts (221 lines), external HTTP, no DB
- callYouResearch(query, apiKey, effort) :54. POST https://api.you.com/v1/research, headers Content-Type: application/json and X-API-Key, body {input, research_effort: lite|standard|deep|exhaustive}. Reads data.output.content (markdown with [[n]] citations) and data.output.sources [{url, title, snippets}]. Throws "you.com Research API error <status>: <body>".
- parseStructuredAssessment(markdown) :111 regex-extracts the block into StructuredAssessment {parallel_exists YES|PARTIAL|NO, parallel_type, confidence, source_title, source_reference, source_quote, isra_status, motif_tags[], parsed}. Missing block -> defaults to NO. "N/A" -> empty string.
- embedSourceCitations(content, sources) :163 strips the assessment block, rewrites [[n]] to markdown links, appends a **Sources** list. Output is stored in scholarly_analysis.
- Also imported by src/scripts/archive/enrich-narrators-deep.ts:15 (archived).

### neo4j-commit.ts (225 lines), the only writer of the AI path
commitParallelToNeo4j(CommitInput): CommitResult {parallel_id, source_id, tradition_id, created} :119. Input: hadith_id, hadith_text_en, tradition_name, parallel_type, isra_status, confidence, source_title, source_reference (canonical ref and idempotency key), source_quote, scholarly_analysis, motif_tags[]. Steps, each its own runWrite (NOT atomic; 7 round trips plus 2 per tag):
1. MERGE (t:ReligiousTradition {name}) ON CREATE SET id, created_at.
2. MERGE (s:SourceText {canonical_reference}) ON CREATE SET id, title, tradition_name, description = quote, created_at; ON MATCH SET title, tradition_name. Note SourceText is unique on canonical_reference alone, not per tradition; description (the quote) is only written on create.
3. MERGE (s)-[:BELONGS_TO]->(t).
4. MERGE (p:CrossCulturalParallel {pipeline_key}) where pipeline_key = `${hadith_id}::${TRADITION_UPPER}::${source_reference}`. Sets parallel_type, isra_iliyyat_status, confidence_level, hadith_excerpt_en = full hadith English text (despite the name), source_text_original = source_reference (a citation, not original-language text), source_text_en = quote, scholarly_analysis; ON MATCH adds updated_at. The created flag `(p.created_at = p.updated_at OR p.updated_at IS NULL)` is fragile; PG equivalent: INSERT ... ON CONFLICT (pipeline_key) DO UPDATE ... RETURNING (xmax = 0) AS created.
5-7. MERGE HAS_PARALLEL, PARALLELS, FROM_TRADITION.
8. Per tag: MERGE (m:MotifTag {name}) ON CREATE SET id, category = inferMotifCategory(name) (regex heuristic :46-63, default WISDOM) then MERGE (p)-[:TAGGED_WITH]->(m).
Relational implication: UNIQUE religious_traditions.name, source_texts.canonical_reference, motif_tags.name, cross_parallels.pipeline_key; the whole commit becomes one transaction. Rename the function (it is named after Neo4j). src/lib/db/neo4j-helpers.ts:12-15,190 documents a generic merge helper that already supersedes parts of it.

### pipeline.ts (211 lines)
processHadith(hadith {id, title, text_english, primary_topic?}, {youApiKey, faithIds?, effort = 'standard', delayMs = 1500, verbose}) :85. Sequentially per faith: buildResearchQuery (truncate to 39,000 chars) -> callYouResearch -> parseStructuredAssessment -> if parallel_exists === 'NO' record skipped, else embedSourceCitations + commit (source_reference falls back to `${faith.id}_${hadith.id}`) -> sleep(delayMs) between faiths. Per-faith errors are caught and counted. Returns PipelineResult {hadith_id, hadith_title, faiths_processed, parallels_found, parallels_created, parallels_updated, errors, results: FaithResult[]}; FaithResult {faith_id, faith_name, parallel_exists, parallel_type, confidence, source_reference, source_title, isra_status, motif_tags, commit?, skipped?, error?}. Cost and latency: 1 hadith x 16 faiths = 16 API calls and at least 22.5s of sleep; the route can run 20 hadiths serially, so a single request can last many minutes (serverless timeout risk; use a worker or cron on Railway). NO results and errors are not persisted, so re-runs re-pay for them. Suggest a PG table parallel_research_runs(hadith_id, tradition_id, status, effort, assessed_at) to skip already-researched pairs.

## 4. Entry points
### POST /api/comparative/research (src/app/api/comparative/research/route.ts, 164 lines)
- Env: YOU_API_KEY (500 if missing). No auth.
- Body: {hadith_id?} for single mode, or {batch_size (max 20, default 5), offset (default 0)}; shared {faiths?: string[], effort_level (default 'standard'), delay_ms (default 1500)}.
- Reads (:70-74 single, :100-105 batch): MATCH (h:Hadith) WHERE h.text_en IS NOT NULL [AND <> ''] RETURN h.id, (h.chapter ?? h.category) AS chapter, h.category, h.text_en ORDER BY h.created_at SKIP $offset LIMIT $batchSize. Relational: SELECT id, chapter, category, text_en FROM hadiths WHERE text_en <> '' ORDER BY created_at, id OFFSET/LIMIT (keyset on id would be more stable).
- Response: {results: PipelineResult[], total_created, total_updated, total_errors, hadiths_processed, next_offset?}; 404 {error} for unknown hadith; 400 for invalid JSON; empty batch returns zero totals plus message.
- Mapping: HadithRecord {id, title: chapter || category, text_english: text_en, primary_topic: category}. isnad and transmission_period are never passed although the prompt supports them.

### Scripts
- src/scripts/find-parallels.ts (139 lines): `npm run db:find-parallels` (package.json:17). CLI: --batch-size (5) --offset (0) --faith ID (repeatable, uppercased) --effort --delay-ms. Env via loadEnv() / getRequiredEnv('YOU_API_KEY') from src/scripts/lib/env. Reads Neo4j with the STALE v1 names (h.title, h.text_english, h.primary_topic), wraps paging in neo4j.int, closes with closeDriver. Cost: batch x faiths calls (5 x 16 = 80). Port to a Drizzle query and close the pg pool on exit.
- ingest-approved-parallels.ts: absent (section 0).
- src/scripts/types/parallel-candidate.ts (93 lines): ParallelCandidate {id, hadith_id, hadith_title, hadith_text_english, suggested_tradition, suggested_parallel_type, suggested_isra_iliyyat_status, suggested_confidence_level, suggested_source_text_title, suggested_source_text_canonical_reference, suggested_source_text_en, suggested_scholarly_analysis, suggested_motif_tags[], api_source ('sefaria' | 'bible_api' | 'llm_only'), api_verified, override_parallel_type?, override_isra_iliyyat_status?, override_confidence_level?, override_scholarly_analysis?, status PENDING|APPROVED|REJECTED|COMMITTED, reviewer_notes?, generated_at, reviewed_at?, committed_at?}; CandidateOverrides; loadCandidates / saveCandidates (atomic temp-file + rename; planned path datasets/parallel-candidates.json). Unused. Opportunity: a PG parallel_candidates table with these columns provides the missing review gate (admin approves -> commit into cross_parallels). Decision for owner: keep direct-commit (current) or add the review gate.

## 5. End-to-end flow as implemented and external needs
Automated path: operator calls POST /api/comparative/research or runs `npm run db:find-parallels` -> pick hadiths with English text -> per hadith x per faith: build prompt -> you.com Research API -> parse structured block -> if not NO, MERGE tradition/source/parallel/tags directly into the live store (created or updated, idempotent by pipeline_key). No human review.
Manual path: /admin/comparative (client.tsx) creates traditions, source texts, tags and parallels via server actions (hadith picked with graph-actions searchHadiths).
Read paths: /comparative (searchParallels, getAllParallels, getComparativeStats, getAllTraditions), hadith page (getParallelsForHadith), narrator page (getTraditionConnectionsForNarrator).
External APIs and env: you.com Research API https://api.you.com/v1/research with YOU_API_KEY (defined in .env.local line 4; it is a live secret, do not copy it into docs or the HTML brief); Neo4j env NEO4J_URL / NEO4J_USERNAME / NEO4J_PASSWORD (.env.local lines 1-3), replaced by DATABASE_URL after the refactor. No Sefaria, Bible API or OpenAI calls exist in code (only in the old conductor plan). The pipeline needs outbound HTTPS and a long request budget (maxDuration, or a worker).

## 6. Implied relational schema (delta vs docs/architecture/data-architecture.md:186-200)
Proposed tables already present: religious_traditions, source_texts, cross_parallels, motif_tags, hadith_motif_tags, parallel_motif_tags, narrator_religious_traditions, location_religious_traditions. Missing or to add:
- religious_traditions: id uuid pk, name text UNIQUE NOT NULL, name_arabic, description, geographic_heartlands text[] default '{}', created_at timestamptz.
- source_texts: ADD title NOT NULL, title_original, author, approximate_date_ce text, description (holds the English quote on the commit path; the proposal's `text` maps here), canonical_reference UNIQUE, religious_tradition_id FK. Drop tradition_name (derive by join).
- cross_parallels: proposal has hadith_id, source_text_id, parallel_type, israiliyyat_status, confidence_level. ADD religious_tradition_id FK NOT NULL (reads and stats use it), pipeline_key text UNIQUE NULL (manual rows have none), hadith_excerpt_en, source_text_original, source_text_en, scholarly_analysis text, created_at, updated_at; enums as pg enums or CHECK; defaults isra 'NONE', confidence 'MEDIUM'. Indexes: (hadith_id), (religious_tradition_id, parallel_type), created_at DESC for admin pagination. Naming: proposal says israiliyyat_status, code and UI use isra_iliyyat_status; map in the Drizzle layer.
- motif_tags: id, name UNIQUE, category (7-value enum), description, created_at.
- link tables: composite PKs, ON DELETE CASCADE on both sides.
- hadiths must expose chapter, category, text_en, created_at; chains(hadith_id) and chain_mentions(chain_id, narrator_id) are used by getTraditionConnectionsForNarrator.
- Optional new: parallel_candidates (review staging), parallel_research_runs (skip and cost control), hadith_embeddings (semantic prefilter could cut the 16-faith fan-out).
Scale: parallels are tiny (hundreds to low thousands); no memory concern.

## 7. Gaps and risks for the migration
1. route.ts Cypher `??` is invalid and SKIP/LIMIT are unwrapped JS numbers; find-parallels.ts uses stale v1 property names. Verify they are broken today, then port rather than preserve.
2. createCrossParallel tags are non-atomic; the commit path is 7+ non-atomic writes. Use one PG transaction.
3. Dynamic SET key injection in three update actions.
4. No authz on any mutator or on the paid API route.
5. Pages wrap reads in .catch(() => []), which will also mask Postgres errors.
6. Neo4j datetime and Integer serialisation differ from pg: timestamptz becomes Date, count() bigint becomes string; cast and map.
7. Orphan behaviour on delete (see section 0); prefer RESTRICT for curated data.
8. PARTIAL + parallel_type NONE can be committed as 'NONE'; add enum guard.
