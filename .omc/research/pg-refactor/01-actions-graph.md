# 01 - Catalog of graph-actions.ts + neo4j-helpers + pagination + attribution
Date: 2026-11-21. Intent: per-action Cypher / return-shape / UI-consumer / relational-needs catalog for the Neo4j -> Postgres/Drizzle refactor. Read-only investigation.
Paths relative to repo root. GA = src/app/actions/graph-actions.ts (1126 lines, 30 exported async actions plus exported types).
Table names follow docs/architecture/data-architecture.md ("proposed"); `*` marks gaps vs that doc.

## 0. Cross-cutting findings (read first)

1. v2 graph property drift (loader truth: src/scripts/lib/regen/load-narrators.ts:28-43, assessment.ts:13 "G-1 ABSOLUTE: never write reliability/grade scalar", batch-loaders.ts:29):
   - `Narrator.reliability` is REMOVED by G-1 (assessment.ts:228 `REMOVE n.reliability`). GA reads it in withNarratorDateAliases (GA:193), searchNarrators filter (GA:437), `collect(teacher {.reliability})` (GA:882), exportHadiths (GA:1057,1105). UI readers: ReliabilityBadge narrator/[id]/page.tsx:73, admin/narrators/client.tsx:55,96, IsnadGraph/NarratorSidebar/IsnadChain (n.reliability), and chainHealthScore hadith/[id]/page.tsx:59 (always 0 in v2; page has a TODO). The /admin/narrators reliability filter returns 0 rows on v2 data.
   - `Hadith.display_grade`, `auto_calculated_grade`, `transmission_type` are absent in v2 (grades live on :Assessment via HAS_ASSESSMENT). UI reads them: hadith/[id]/client-page.tsx:28,72,113-114 (shows "Ungraded"), narrator other_hadiths display_grade (narrator client-page.tsx:529), types.ts:26-28.
   - `Source.compiler` (getSourceStats GA:938) does not exist; loader writes `compiler_name` (batch-loaders.ts:179).
   - `Chain.chain_index`: loader sets it; export bundle names it `branch` (neo4j_export/contract.py:154-157, HAS_CHAIN branch:int). Chain id fallback `coalesce(c.id, c.pipeline_key, toString(id(c)))` (GA:356) uses Neo4j internal `id()`; PG equivalent is just chains.id.
   - NARRATED_FROM edge props read: temporal_plausibility, status, confidence, extraction_method (GA:407-409). Loader writes confidence/extraction_method/source (G-2, batch-loaders.ts:30). Bundle contract (contract.py:345-355) is chain-scoped (chain_id, hadith_id, from_position, to_position, sanad_confidence, extraction_method) with NO temporal_plausibility and no numeric confidence. Proposed PG derives transmissions from chain_mentions so these are null. UI reads only `e.status` (IsnadGraph/NarratorSidebar): low impact.
   - `IN_SCHOOL`/`SchoolOfThought` (exportHadiths 'school', GA:1068) is legacy: mode-fullregen.ts:152-170 migrates it to FROM_TRADITION->ReligiousTradition and leaves old edges. v2 truth: `Hadith.tradition` scalar.
   - `title`, `primary_topic`, `text_english`, `text_arabic` are v1 aliases synthesized in the action layer (GA:309-312, 892-896, 986-989), not stored.
   - Export-bundle Hadith header (contract.py:82-93) has NO text_en/chapter/category/hadith_id/school/volume/chapter_no (Translation/Chapter/Book nodes instead). The live graph (loader: load-hadith.ts, batch-loaders.ts) does carry h.text_en, chapter, category, volume, school on Hadith. Proposed PG `hadiths` has no `category`, no text_en, no chapter text (chapter_id FK, translations table). Gap: `category` is read by every list/search action as title fallback and filter (GA:309,957,965,1030).
   - Narrator bundle header (contract.py:98-100) is identity only; live graph narrators get name_english/name_arabic/tabaqah/geographic_region/birth+death dates from load-narrators.ts. Proposed `narrators` lacks tabaqah, geographic_region, birth/death years (hijri+gregorian), date source_text/provenance/review_status, bio, kunya/nasab/nisba, bio_summary/tadil/jarh, reliability_consensus/disagreement, critic_quote_count, bio_provenance (would sit in narrator_profiles.raw_profile jsonb). UI binds all of them (narrator/[id]/client-page.tsx:95-103, 214-384).
   - No action filters `tombstoned`/retired rows (grep count 0 in GA). Loader tombstones (assessment.ts:198). PG equivalent `retired_at is null` must be applied on every pipeline-table read.
2. Dead exported actions (no caller outside GA): getNarratorById (internal use only GA:631,856), linkNarratorToEvent, getTimelineForNarrator, getCommentariesForHadith, linkNarratorToLocation, getSourceStats. Unused param: getNarratorNetwork `depth` (GA:914). UI dead-ends: `locations` from getEnhancedNarratorDetails and its `teacher_student_network` are not bound by narrator/[id]/client-page.tsx (props lines 95-150) while page.tsx:26-27 calls both it and getNarratorNetwork. Ignored admin params: commentaries `type` (admin/commentaries/page.tsx:12,29 only filterType), locations `q` (admin/locations/page.tsx:12), narrators geographic_region never sent.
3. Neo4j-only mechanics: `neo4j.int` in pagination.ts:27-28; `datetime()` created_at (GA:491,674,792); `DETACH DELETE` (GA:554,772,817) -> FK ON DELETE CASCADE; MERGE with property in rel pattern (GA:623 `INVOLVED_IN {role}`) -> unique(narrator_id,event_id,role); dynamic rel type via template (GA:844) -> `relation` enum column; whole-node `...props` spreads (UI types use index signatures so sparse rows are fine but keep snake_case keys).
4. N+1/unbounded summary: getAllCommentaries row multiplication; getEnhancedNarratorDetails teacher x student cartesian and unbounded lists; getNarratorNetwork unbounded; getFullChainGraph spreads full narrator bags per chain row; commentaries admin page pulls 100 full hadith + 100 full narrator rows for dropdowns; exportHadiths LIMIT 10000 with up to 3 OPTIONAL MATCH cartesian collects. No true N+1 (every action is a fixed number of queries; some awaits are sequential rather than parallel: getEnhancedNarratorDetails 4, getTimelineForNarrator 3, getNarratorNetwork 2).
5. Tests that read GA source as text will break on rewrite: src/scripts/__tests__/regen-full-load-hardening.test.ts:644 (`graphSource`) and :645 (narrator page source).
6. No session/authz check inside any GA write action (admin create/update/delete). Verify middleware protects /admin before relying on it.

## 1. Shared helpers inside GA (non-exported)
- `safeKeys(data, allowed)` GA:12 + `buildSetClause(alias,data)` GA:20: allowlist + identifier regex for dynamic `SET e.k = $k`. Drizzle: `.set(pick(data, allowed))`. Allowlists: HISTORICAL_EVENT_KEYS GA:557, COMMENTARY_KEYS GA:762, LOCATION_KEYS GA:820.
- `optionalString/Number/Boolean`, `legacyReliability`, `withNarratorDateAliases` GA:163-227: normalizers; mirrors `birth_date_*` into `birth_year_*` (UI reads `*_year_*` plus `*_date_source_text/provenance/review_status`); `name_english` falls back to `name`; reliability coerced to THIQA|SADUQ|DAIF|MAJHUL|KADHAB else undefined. Output type NarratorDetails GA:106-143.

## 2. Actions (30). `Paginated<T>` = `{items, total, page, pageSize, totalPages}` (pagination.ts:12-18)

### 2.1 getNarratorById(id) - READ, no external caller - GA:229
Cypher `MATCH (n:Narrator {id:$id}) RETURN n`. Returns NarratorDetails|null. PG: narrators by id (PK/unique) plus profile columns (see 0.1).

### 2.2 getAllNarrators(pagination?) - READ - GA:238
- Cypher: count `MATCH (n:Narrator) WHERE n.is_prophet IS NULL OR n.is_prophet=false RETURN count(n)`; page `... RETURN n ORDER BY coalesce(n.name_english, n.name) SKIP $skip LIMIT $limit` (2 parallel queries).
- Returns Paginated<NarratorDetails>. Callers: admin/narrators/page.tsx:33 (25/page -> NarratorsClient: id,name_english,name_arabic,tabaqah,reliability,geographic_region,death_year_hijri); admin/commentaries/page.tsx:18 and admin/comparative/page.tsx:13 (`pageSize:100` dropdowns: id,name_english,tabaqah).
- PG: `narrators where coalesce(is_prophet,false)=false order by coalesce(name_en,name) limit/offset`; expression index on that coalesce (24k rows, sort is cheap anyway). Flags: dropdowns pull 100 full rows for 3 columns; only first 100 narrators selectable as commentary subject via dropdown (typeahead covers rest).

### 2.3 getHadithById(id) - READ (hadith detail hot path) - GA:261
- Cypher: `MATCH (h:Hadith {id:$id}) OPTIONAL MATCH (h)-[:HAS_VARIATION]->(m:MatnVariation) RETURN h, collect(DISTINCT m) AS legacy_variations`.
- JS shaping GA:277-320: text_en ?? text_english; text_ar ?? text_arabic; canonicalSanad = sanad ?? isnad_arabic ?? chain_text_arabic; variations = legacy MatnVariation props, else ONE synthesized `{id:"<id>::synthesized", text_arabic: matn_ar??text_ar, text_english: matn_en??text_en, source:'hadith_node'}`.
- Returns `{...props, title: title??chapter??category??null, primary_topic: primary_topic??category??null, text_english, text_arabic, sanad, isnad_arabic, chain_text_arabic, matn_ar, matn_en, variations}` = HadithNode (hadith/[id]/types.ts:17-77). Caller hadith/[id]/page.tsx:20 (`.catch -> null`). UI-read fields: id,title,primary_topic,display_grade*,auto_calculated_grade*,transmission_type*,text_english/arabic,isnad_arabic,chain_text_arabic,sanad,chapter,hadith_no,source,variations[].{source,text_*},chain_type,attributed_to,narration_level,sanad_confidence,tradition,volume,school,category,matn_*,hadith_id,chapter_no (* absent in v2).
- PG: hadiths + translations(language='en') + chapters/books join + collections/sources for `source` label. Drop MatnVariation branch (no data) but KEEP the synthesized variation with `source:'hadith_node'` because hadith/[id]/client-page.tsx:176-177 filters on it. Gaps: attributed_to, narration_level, chain_type, school, category, hadith_id, grades (see section 6). Index: PK + unique record_id.

### 2.4 getAllHadiths(pagination?) - READ - GA:323
- Cypher: count `MATCH (h:Hadith) RETURN count(h)`; page `MATCH (h:Hadith) RETURN h ORDER BY h.source, toInteger(h.hadith_no) SKIP/LIMIT`.
- Returns Paginated<HadithDetails> raw props (NO alias synthesis). Callers: admin/hadith/page.tsx:21 -> HadithManagerClient (tradition, volume, id, hadith_no, title, primary_topic, source, chapter, text_arabic/text_ar, matn_ar); admin/commentaries/page.tsx:17 (`pageSize:100`, dropdown id/title).
- INCONSISTENCY: raw props lack `title`/`primary_topic` (synthesized only in searchHadiths/getHadithById) so the unfiltered admin list shows blank title/topic, filtered list shows them. Use one shared row mapper.
- PG: `order by collection name, hadith_no_int`. `toInteger(hadith_no)` yields null for non-numeric; PG needs a safe cast or stored `hadith_no_int`. Index (collection_id, hadith_no_int).

### 2.5 getFullChainGraph(hadithId) - READ (hot path) - GA:340
- Cypher A nodes: `MATCH (h:Hadith {id:$hadithId})-[:HAS_CHAIN]->(c:Chain)-[i:INCLUDES]->(n:Narrator) RETURN DISTINCT coalesce(c.id,c.pipeline_key,toString(id(c))) AS chainId, c.chain_index AS chainIndex, i.position AS position, n ORDER BY coalesce(c.chain_index,0), chainId, position, n.id`.
- Cypher B edges: `MATCH (h)-[:HAS_CHAIN]->(c)-[i1:INCLUDES]->(n1:Narrator) MATCH (n1)-[r:NARRATED_FROM]->(n2:Narrator) MATCH (c)-[i2:INCLUDES]->(n2) WHERE i1.position IS NULL OR i2.position IS NULL OR i2.position = i1.position+1 RETURN DISTINCT chainId, chainIndex, i1.position sourcePosition, i2.position targetPosition, n1, r, n2 ORDER BY ..., sourcePosition`. A and B run in parallel.
- Fallback when A is empty (GA:376-386): legacy `(h)-[:HAS_VARIATION]->(:MatnVariation)-[:TRANSMITTED_VIA]->(c)-[i:INCLUDES]->(n)`, edges=[]; drop in PG, keep `chain_schema:'v2'`.
- Returns `{nodes, edges}` (types.ts:74-103). node = `{...narratorProps, chain_id:String, chain_index:number|null, position, chain_position (dup of position), chain_schema}`; edge = `{source:n1.id, target:n2.id, type:'NARRATED_FROM'|'HEARD_FROM', chain_id, chain_index, source_position, target_position, status: r.temporal_plausibility??r.status??null, confidence, extraction_method, chain_schema}`. Consumers: IsnadChain.tsx (chain_position, e.source/target, node.chain_id/chain_index/chain_position/chain_schema/name_arabic/name_english); IsnadGraph/NarratorSidebar (reliability, tabaqah, is_prophet, death_year_hijri, bio, birth_year_hijri, geographic_region, e.status); page.tsx:56-72 (reliability==='THIQA', tabaqah==='SAHABA'|'PROPHET', is_prophet); client-page.tsx:45-47 (name presence, chain_id).
- Semantics to preserve: position ascending runs collector -> Prophet; edge = n1 at position p NARRATED_FROM n2 at p+1; edges are chain-scoped; DISTINCT because a narrator can recur.
- PG: chains (hadith_id, branch) join chain_mentions(chain_id, position, narrator_id) join narrators. Edges = `chain_mentions a join chain_mentions b on b.chain_id=a.chain_id and b.position=a.position+1` (NARRATED_FROM not needed; strictly more correct, since Cypher B joins a GLOBAL edge then re-checks adjacency so a pair adjacent in chain X could be matched through an edge created by chain Y). narrator_id is only filled when the whole chain resolves (arch doc), same as INCLUDES today. edge extras: extraction_method <- chains.extraction_method, confidence <- chains.sanad_confidence (string, was number), status has no source unless temporal-plausibility (src/scripts/lib/regen/temporal-plausibility.ts) is persisted.
- Indexes: chains(hadith_id, branch); unique chain_mentions(chain_id, position); narrators PK. Flag: per-chain-row copy of full narrator bag (bio text) - narrow the select but the sidebar needs bio/birth/death/region/tabaqah.

### 2.6 searchNarrators(searchTerm='', filters?{reliability,tabaqah,geographic_region}) - READ - GA:418
- Cypher (dynamic): `MATCH (n:Narrator) WHERE (n.is_prophet IS NULL OR n.is_prophet=false) [AND (toLower(n.name_english) CONTAINS toLower($t) OR toLower(n.name_arabic) CONTAINS toLower($t))] [AND n.reliability=$r] [AND n.tabaqah=$t] [AND n.geographic_region=$g] RETURN n ORDER BY n.name_english LIMIT 50`.
- Returns raw prop bags[] (not paginated, not alias-normalized). Callers: admin/narrators/page.tsx:21 (q, reliability, tabaqah; page fakes total=len, page=1, pageSize=50, so the filtered list silently caps at 50 with no paging); admin/commentaries/client.tsx:89 (debounced typeahead; id,name_english,tabaqah).
- Text matching: case-insensitive substring on English and Arabic names. PG: ILIKE '%q%' with gin(gin_trgm_ops) on name_en and name_ar (pg_trgm and unaccent exist locally); consider a normalized-Arabic column (see src/lib/attribution norm). Escape LIKE wildcards.
- Gap: `reliability` filter has no PG source (needs narrator_assessments join or derived reliability_consensus column). Ordering differs from getAllNarrators (name_english vs coalesce).

### 2.7 createHistoricalEvent(data) - WRITE - GA:466
- `CREATE (e:HistoricalEvent {id:randomUUID(), title, title_arabic, description, year_hijri, year_gregorian, start_year_hijri, start_year_gregorian, end_year_hijri, end_year_gregorian, category, significance, location_name, verification_status (default 'unverified'), publication_ready (default false), citation_source, citation_locator, citation_url, citation_retrieved_at, created_at: datetime()})`. start_year_* = start_year_* ?? year_* (nullish: 0 valid, src/app/actions/AGENTS.md "Historical context"). Returns id. Caller admin/events/client.tsx. Types HistoricalEventData GA:31-51.
- PG historical_events columns: title (doc says `name`)*, title_arabic*, description*, start/end year hijri + gregorian*, category, significance*, location_name*, verification_status enum(unverified, unverified_seed, human_verified, source_verified), publication_ready, citation_source/locator/url, citation_retrieved_at*, created_at*. Legacy year_hijri/year_gregorian alias columns can become mapper-computed, but the UI type HistoricalTimelineEvent still REQUIRES `year_hijri: number` (components/HistoricalTimeline.tsx:5-19) and admin/events/client.tsx reads year_hijri/year_gregorian.

### 2.8 getAllHistoricalEvents(filters?{category, yearRange}, pagination?) - READ - GA:520
- Cypher: `MATCH (e:HistoricalEvent) [WHERE e.category=$category AND coalesce(e.end_year_hijri,e.start_year_hijri,e.year_hijri) >= $minYear AND coalesce(e.start_year_hijri,e.year_hijri) <= $maxYear] RETURN e ORDER BY coalesce(e.start_year_hijri,e.year_hijri) SKIP/LIMIT` + count. Caller admin/events/page.tsx:15 (category only; yearRange never passed). Returns Paginated<any>; client reads id,title,title_arabic,description,significance,location_name,category,year_hijri,year_gregorian.
- PG: overlap predicate on start/end hijri; index historical_events(start_year_hijri, end_year_hijri) and (category).

### 2.9 deleteHistoricalEvent(id) - WRITE - GA:553
`DETACH DELETE` -> `delete ... where id` with narrator_events ON DELETE CASCADE. Conflicts with the "never delete data, back up instead" owner rule: schema designer should decide hard delete vs `retired_at`.

### 2.10 updateHistoricalEvent(id, Partial<HistoricalEventData>) - WRITE - GA:567
Syncs alias pairs (start_year_hijri<->year_hijri, same for gregorian), allowlist HISTORICAL_EVENT_KEYS, `MATCH ... SET <dynamic>`; no-op when empty. Behavioural trap: Neo4j driver serializes `undefined` as null so `{x: undefined}` clears the property; Drizzle `.set({x: undefined})` skips it. Use explicit nulls.

### 2.11 getHistoricalEventsForNarrator(narratorId) - READ (public, fail-closed gate) - GA:585
- Cypher: `MATCH (n:Narrator {id}) WITH n, coalesce(n.birth_date_hijri,n.birth_year_hijri) birthYear, coalesce(n.death_date_hijri,n.death_year_hijri) deathYear MATCH (e:HistoricalEvent) WITH e, birthYear, deathYear, coalesce(e.start_year_hijri,e.year_hijri) eventStart, coalesce(e.end_year_hijri,e.start_year_hijri,e.year_hijri) eventEnd WHERE (birthYear IS NOT NULL OR deathYear IS NOT NULL) AND eventStart IS NOT NULL AND e.publication_ready=true AND e.verification_status IN ['human_verified','source_verified'] AND trim(coalesce(e.citation_source,''))<>'' AND (trim(coalesce(e.citation_locator,''))<>'' OR trim(coalesce(e.citation_url,''))<>'') AND (birthYear IS NULL OR eventEnd >= birthYear) AND (deathYear IS NULL OR eventStart <= deathYear) RETURN DISTINCT e, eventStart AS sortYear ORDER BY sortYear`.
- Returns event prop bags[] -> HistoricalTimelineEvent[] (narrator/[id]/page.tsx:29 -> client-page.tsx:137,414). The gate is a documented public-facing correctness rule (src/app/actions/AGENTS.md, src/lib/db/AGENTS.md) and must survive verbatim; suggest a SQL view `published_historical_events`.
- PG: one query narrators x events with the gate and interval overlap computed at read time (AGENTS: no narrator-by-event overlap edges). Needs narrator birth/death hijri columns (gap). Partial index on events `where publication_ready`. Cartesian MATCH over all events is fine (tiny table).

### 2.12 linkNarratorToEvent(narratorId, eventId, role?) - WRITE, DEAD - GA:615
`MERGE (n)-[:INVOLVED_IN {role: role||'Participant'}]->(e)`. PG narrator_events(narrator_id, event_id, role) unique on all three, `on conflict do nothing`. No UI caller, so no INVOLVED_IN data is creatable via UI.

### 2.13 getTimelineForNarrator(narratorId) - READ, DEAD - GA:630
Calls getNarratorById + getHistoricalEventsForNarrator + `MATCH (n)-[r:INVOLVED_IN]->(e:HistoricalEvent) WHERE <same publish gate, no overlap> RETURN e, r.role ORDER BY coalesce(e.start_year_hijri,e.year_hijri)`. Returns `{narrator, birth_year_hijri, death_year_hijri, events:[{...e, role}], contextual_events}`. Three sequential awaits. Decide: delete, or wire involvement into the narrator page.

### 2.14 createCommentary(data) - WRITE (multi-statement txn) - GA:661
runTransaction: `CREATE (c:Commentary {id, source_work, author, text, text_arabic, type, reference, created_at})`; optional `MATCH c, MATCH (h:Hadith {id}) CREATE (c)-[:COMMENTS_ON]->(h)`; optional `MATCH c, MATCH (n:Narrator {id}) CREATE (c)-[:DISCUSSES]->(n)`. Returns id. Caller admin/commentaries/client.tsx. Behaviour change: a missing hadith/narrator id silently creates no edge in Cypher; PG FK would throw.
PG: commentaries + commentary_hadiths + commentary_narrators in one db.transaction. Doc table has `title`,`body` but code uses `text` and also `text_arabic`*, `type`*, `reference`*, created_at*. `type` union per narrator client-page.tsx:130: HADITH_COMMENTARY|NARRATOR_BIOGRAPHY|CHAIN_ANALYSIS|OTHER.

### 2.15 getAllCommentaries(pagination?) - READ - GA:715
- Cypher: count `MATCH (c:Commentary) RETURN count(c)`; page `MATCH (c) OPTIONAL MATCH (c)-[:COMMENTS_ON]->(h:Hadith) OPTIONAL MATCH (c)-[:DISCUSSES]->(n:Narrator) RETURN c,h,n ORDER BY c.created_at DESC SKIP/LIMIT`.
- Returns Paginated<{...c, hadith: h|null, narrator: n|null}>; admin/commentaries/client.tsx reads commentary.{id,type,text,text_arabic,reference,source_work,author,hadith.{id,title},narrator.{id,name_english,tabaqah}}.
- BUG (latent): two OPTIONAL MATCH give |hadiths| x |narrators| rows per commentary; SKIP/LIMIT counts rows while total counts commentaries. Only <=1 of each is creatable today. `hadith.title` is an alias absent from raw props -> blank. PG: page commentaries first, then batch-fetch links (`= any(ids)`). Indexes: commentaries(created_at desc); link-table PKs plus indexes on hadith_id and narrator_id.

### 2.16 getCommentariesForHadith(hadithId) - READ, DEAD - GA:741
`MATCH (c:Commentary)-[:COMMENTS_ON]->(h:Hadith {id}) RETURN c ORDER BY c.created_at DESC`. No caller (hadith page shows no commentaries).

### 2.17 getCommentariesForNarrator(narratorId) - READ - GA:753
`MATCH (c:Commentary)-[:DISCUSSES]->(n:Narrator {id}) RETURN c ORDER BY c.created_at DESC`. Caller narrator/[id]/page.tsx:28 -> CommentarySection (components/CommentarySection.tsx:20,54; id,author,text,source_work,reference,type). No LIMIT. PG: commentary_narrators(narrator_id) join, order created_at desc.

### 2.18 updateCommentary(id, Partial<CommentaryData>) - WRITE - GA:764
Allowlist source_work, author, text, text_arabic, type, reference. Links (hadith_id/narrator_id) are NOT editable after create. No updated_at.

### 2.19 deleteCommentary(id) - WRITE - GA:771
`DETACH DELETE` -> cascade link rows.

### 2.20 createLocation(data) - WRITE - GA:780
`CREATE (l:Location {id, name, name_arabic, modern_country, region, latitude, longitude, description, created_at})`. Returns id. BUG: `data.latitude || null` / `longitude || null` (GA:800-801) convert 0 to null; use `??`. PG locations needs name, name_arabic*, modern_country*, region*, latitude/longitude double, description*, created_at* (doc lists only id, name, coordinates).

### 2.21 getAllLocations(pagination?) - READ - GA:807
Count + `MATCH (l:Location) RETURN l ORDER BY l.name SKIP/LIMIT`. Paginated<any>. Caller admin/locations/page.tsx:15 (`q` ignored). Index on name.

### 2.22 deleteLocation(id) - WRITE - GA:816
`DETACH DELETE` -> cascade narrator_locations.

### 2.23 updateLocation(id, Partial<LocationData>) - WRITE - GA:822
Allowlist name, name_arabic, modern_country, region, latitude, longitude, description.

### 2.24 linkNarratorToLocation(narratorId, locationId, relType) - WRITE, DEAD - GA:832
Validates relType in BORN_IN|DIED_IN|RESIDED_IN, then `MERGE (n)-[:<relType>]->(l)`. PG narrator_locations(narrator_id, location_id, relation born|died|resided), unique triple. No UI caller, so admin cannot attach locations.

### 2.25 getEnhancedNarratorDetails(narratorId) - READ (narrator page) - GA:853
- 4 sequential awaits: (1) getNarratorById; (2) `MATCH (n)<-[:INCLUDES]-(c:Chain)<-[:HAS_CHAIN]-(h:Hadith) RETURN DISTINCT h ORDER BY h.chapter, h.category LIMIT 100`; (3) `MATCH (n)-[r]->(l:Location) RETURN l, type(r) AS relationType` (ANY rel type); (4) `MATCH (n) OPTIONAL MATCH (n)-[:NARRATED_FROM]->(teacher) OPTIONAL MATCH (student)-[:NARRATED_FROM]->(n) RETURN collect(DISTINCT teacher {.id,.name_english,.name_arabic,.reliability,.tabaqah}) teachers, collect(DISTINCT student {...}) students` (|T| x |S| intermediate rows before DISTINCT: expensive for hub narrators).
- Returns `{...narrator, other_hadiths:[{...hadithProps, id, title: chapter??category??'', primary_topic: category, display_grade, text_english, text_arabic}], locations:[{...l, relationship}], teacher_student_network:{teachers,students}}`. UI binds only other_hadiths[{id,title,primary_topic,display_grade}] plus narrator fields (client-page.tsx:95-103,514-532).
- PG: hadiths via chain_mentions(narrator_id) -> chains -> hadiths, `distinct`, order chapter/category, LIMIT 100 (silent cap, add count). Drop locations and teacher_student_network unless the page is changed to show them. Flags: returns whole hadith rows incl. text for a link list needing id/chapter/category; for a prolific narrator the 100 are an arbitrary subset ordered by chapter text.

### 2.26 getNarratorNetwork(narratorId, depth=2) - READ - GA:914
- Two sequential queries: teachers `MATCH (n {id})-[:NARRATED_FROM]->(teacher) RETURN DISTINCT teacher`; students `MATCH (student)-[:NARRATED_FROM]->(n {id}) RETURN DISTINCT student`. `depth` ignored.
- Returns `{teachers:[{...props, relationship:'teacher'}], students:[{...props, relationship:'student'}]}`. UI (narrator client-page.tsx:116-128,435-490): id,name_english,name_arabic,relationship; links /narrator/:id. Unbounded, unsorted.
- PG: `narrator_transmissions` MV (arch doc): `where student_id=$1` / `where teacher_id=$1` join narrators; free `hadith_count` for ordering and display; add LIMIT+total. MV indexes (student_id), (teacher_id). narrator_teachers (lexicon-declared links, students_inds/teachers_inds) is a second teacher source not used today; schema designer decides union vs separate. Direction convention: student -[:NARRATED_FROM]-> teacher (GA:912).

### 2.27 getSourceStats() - READ, DEAD - GA:934
`MATCH (s:Source) OPTIONAL MATCH (h:Hadith)-[:FROM_SOURCE]->(s) RETURN s.name source, s.compiler compiler, count(h) hadith_count ORDER BY hadith_count DESC`. No caller; `s.compiler` absent (compiler_name). Proposed hadiths has collection_id not source_id. Delete or re-express over collections.

### 2.28 searchHadiths(searchTerm='', filters?{source,chapter,tradition,school}, pagination?) - READ - GA:947
- Cypher: `MATCH (h:Hadith) [WHERE (toLower(h.chapter) CONTAINS toLower($t) OR toLower(h.category) CONTAINS toLower($t) OR toLower(h.text_en) CONTAINS toLower($t)) AND trim(h.source) IN $sourceValues AND h.category = $chapter AND h.tradition IN $traditionValues] RETURN h ORDER BY h.source, toInteger(h.hadith_no) SKIP/LIMIT` + count.
- `sourceValues = getSourceFilterValues(source)` (src/lib/constants/sources.ts:344: canonical label + unique legacy aliases); `traditionValues = getTraditionFilterValues(tradition)` (src/lib/constants/traditions.ts:20); `school` is a legacy alias of `tradition`; the `chapter` filter compares against h.category (no UI passes it).
- Returns Paginated<{...h, title: chapter||category||null, primary_topic: category||null, text_english: text_en??null, text_arabic: text_ar??null}>. Callers: admin/hadith/page.tsx:20 (q, source, tradition, {page}); admin/commentaries/client.tsx:73 and admin/comparative/client.tsx:311 (typeahead, `.items`, 25 rows, term>=2 chars on comparative).
- PG: trigram GIN on translations.text (language='en'), on chapters.name and on category; Arabic via hadiths.text_ar_normalized trigram (not searched today). Source filter: collections.name = any($values) (alias lists stay in TS). Tradition: traditions.name / hadiths.tradition_id. Indexes hadiths(tradition_id), (collection_id, hadith_no_int). Today's CONTAINS has no index (full scan of 99k). Escape `%`/`_`. Semantic search (hadith_embeddings) is the planned successor.

### 2.29 exportHadiths(config: ExportConfig) - READ (admin CSV) - GA:1022
- Validates `fields` against ALLOWED_EXPORT_FIELDS (GA:1009: id, chapter, category, source, hadith_no, text_en, text_ar, tradition, title, primary_topic, text_english, text_arabic). Filters: searchTerm (same 3-field CONTAINS), source, tradition (no chapter filter).
- One Cypher: `MATCH (h:Hadith) [WHERE...] [OPTIONAL MATCH (h)-[:HAS_CHAIN]->(:Chain)-[:INCLUDES]->(n:Narrator)] [OPTIONAL MATCH (comm:Commentary)-[:COMMENTS_ON]->(h)] [OPTIONAL MATCH (h)-[:IN_SCHOOL]->(sch:SchoolOfThought)] RETURN h, collect(DISTINCT n {.name_english,.reliability}) narrators, collect(DISTINCT comm {.author,.source_work,.text}) commentaries, [] variations, collect(DISTINCT sch.name) schools ORDER BY h.source, toInteger(h.hadith_no) LIMIT 10000` (EXPORT_LIMIT GA:1016; silently truncates 99k to 10k).
- Returns `Record<string,string>[]` CSV rows: requested fields + optional `narrators` ("; "-joined), `narrator_reliability` ("name:RELIABILITY"), `commentaries` ("[author - work] text" joined " | "), `variation_texts_english/arabic` (matn_en||text_en), `schools`. Consumer admin/hadith/client.tsx:88 builds CSV client-side (BOM, quote-escape; header = keys of row 0, so edge columns missing from row 0 are dropped).
- Flags: OPTIONAL MATCH cartesian (narrators x commentaries x schools) before collect; PG use correlated array_agg subqueries. `schools` reads superseded IN_SCHOOL -> emit tradition name. `narrator_reliability` needs assessments (all 'unknown' on v2). 10k rows materialized in memory and shipped as a server-action payload; prefer a streaming route handler (cursor / COPY).

## 3. src/lib/pagination.ts (43 lines)
- `PaginationParams{page?,pageSize?}`, `PaginatedResult<T>`, `DEFAULT_PAGE_SIZE=25`, `toSkipLimit(params)` (page>=1, pageSize clamped 1..100, returns skip/limit as `neo4j.int`), `paginate(items,total,page,pageSize)` (totalPages=ceil(total/pageSize)).
- Only Neo4j coupling: `import neo4j from 'neo4j-driver'` (:5). Drizzle: return plain numbers (`offset`,`limit`); keep the rest. Shared with src/app/actions/comparative-actions.ts:5.
- Edge: admin pages do `parseInt(params.page||'1',10)` (junk -> NaN) and `Math.max(1,NaN)=NaN`; add a finite guard. node-postgres returns `count(*)` as string: cast `::int`.

## 4. src/lib/db/neo4j-helpers.ts (200 lines) - used by NO server action
- Exports: `mergeNodeByKey({label,keyProp,keyValue,createProps,mutableProps})` (MERGE + ON CREATE/ON MATCH + `_merge_sentinel` trick for `created`), `mergeEdge({fromLabel,fromKey,toLabel,toKey,relType,props})`, `buildPipelineKey(...parts)` (pure, `::`-joined), types MergeNodeInput/MergeNodeResult/MergeEdgeInput.
- Callers (offline scripts only): src/scripts/lib/regen/load-hadith.ts:23, batch-loaders.ts:41, load-chain.ts:26, mode-diff.ts:32, src/scripts/seed-taxonomy.ts:18.
- Refactor: delete mergeNodeByKey/mergeEdge with the Neo4j loaders (PG equivalent: `insert ... on conflict (business_key) do update ... returning (xmax = 0) as created`). `buildPipelineKey` is pure; keep or replace with the arch-doc ID scheme (`hadith:<record_id>`, `narrator:rawi:<scholar_indx>`, chain = hadith record + zero-padded branch). Header cites stale src/lib/comparative/neo4j-commit.ts:162.

## 5. src/lib/attribution/classify-attribution.ts (244 lines) - pure, no DB
- Exports `norm(s)`, `classify(text_ar, sanad, tradition, source) -> {attributed_to, narration_level}`, types NarrationLevel ('marfu'|'imam'|'mawquf'|'maqtu'|'unknown'), AttributionResult. 1:1 TS port of datasets/classify_attribution.py (Arabic regex markers, Unicode word-boundary shim WB_TRAIL).
- Callers: src/scripts/lib/regen/entity-resolution.ts:27 (`norm`), src/scripts/__tests__/regen-isnad-graph.test.ts:35 (`classify`,`norm`), regen-arabic-norm-parity.test.ts:57 (`norm`). Not imported by any server action or page. No refactor change needed; `norm` can also derive `hadiths.text_ar_normalized`. Output columns attributed_to / narration_level already exist in the unified CSV (contract.py:17-26) and the UI reads them via getHadithById (types.ts:60-65), so PG `hadiths` must store them.

## 6. Consolidated table / column / index needs (`*` = not in data-architecture.md)
- narrators: id, scholar_indx, name, name_ar, name_en, is_prophet, is_companion, *tabaqah, *geographic_region, *birth/death year hijri+gregorian, *birth/death date source_text/provenance/review_status, *bio, *biographical_narrative, *bio_summary/bio_tadil/bio_jarh, *reliability_consensus/disagreement, *critic_quote_count, *bio_provenance, *kunya/nasab/nisba. Indexes: gin_trgm(name_en), gin_trgm(name_ar), (tabaqah), (geographic_region), expression coalesce(name_en,name).
- hadiths: + *category, *attributed_to, *narration_level, *chain_type, *school, *hadith_no_int, *provider hadith_id; volume/chapter via books/chapters. Indexes: (collection_id, hadith_no_int), (tradition_id), unique record_id, gin_trgm(text_ar_normalized), trigram on category and chapter name.
- translations: gin_trgm(text) where language='en'; (hadith_id, language).
- chains(hadith_id, branch); chain_mentions unique(chain_id, position), index(narrator_id).
- narrator_transmissions MV: index(student_id), index(teacher_id), hadith_count.
- hadith_assessments / narrator_assessments: needed to restore display_grade and reliability (without them UI shows "Ungraded" and chainHealthScore=0).
- historical_events (title not name; section 2.7), narrator_events (unique triple), locations (2.20), narrator_locations, commentaries (+text_arabic, type, reference, created_at), commentary_hadiths, commentary_narrators (indexes on hadith_id / narrator_id).
- Curation data (events/commentaries/locations + links) is written only by these admin actions and lives only in production Neo4j; no Python pipeline creates it (migration step 5 export).
