'use server';

import { runQuery, runWrite, runTransaction } from '@/lib/db/neo4j';
import { getTraditionFilterValues } from '@/lib/constants/traditions';
import { getSourceFilterValues } from '@/lib/constants/sources';
import { randomUUID } from 'crypto';
import { type PaginationParams, type PaginatedResult, toSkipLimit, paginate } from '@/lib/pagination';

// ============ HELPERS ============

/** Filter object keys to only allowed property names, preventing Cypher injection via dynamic SET. */
function safeKeys<T extends Record<string, unknown>>(data: T, allowed: readonly string[]): Partial<T> {
  const out: Record<string, unknown> = {};
  for (const key of Object.keys(data)) {
    if (allowed.includes(key)) out[key] = data[key];
  }
  return out as Partial<T>;
}

function buildSetClause(alias: string, data: Record<string, unknown>): string {
  return Object.keys(data).map((key) => {
    if (!/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(key)) {
      throw new Error(`Invalid property key: ${key}`);
    }
    return `${alias}.${key} = $${key}`;
  }).join(', ');
}

// ============ TYPES ============

export interface HistoricalEventData {
  title: string;
  title_arabic?: string;
  description: string;
  /** Legacy start-year aliases retained while historical records migrate. */
  year_hijri?: number;
  year_gregorian?: number;
  start_year_hijri?: number;
  start_year_gregorian?: number;
  end_year_hijri?: number;
  end_year_gregorian?: number;
  category: string;
  significance?: string;
  location_name?: string;
  verification_status?: 'unverified' | 'unverified_seed' | 'human_verified' | 'source_verified';
  publication_ready?: boolean;
  citation_source?: string;
  citation_locator?: string;
  citation_url?: string;
  citation_retrieved_at?: string;
}

export interface CommentaryData {
  source_work: string;
  author: string;
  text: string;
  text_arabic?: string;
  type: string;
  reference?: string;
  hadith_id?: string;
  narrator_id?: string;
}

export interface LocationData {
  name: string;
  name_arabic?: string;
  modern_country?: string;
  region?: string;
  latitude?: number;
  longitude?: number;
  description?: string;
}

export type LegacyNarratorReliability = 'THIQA' | 'SADUQ' | 'DAIF' | 'MAJHUL' | 'KADHAB';

interface Neo4jEntity {
  properties: Record<string, unknown>;
}

export interface HadithDetails extends Record<string, unknown> {
  id: string;
  title?: string | null;
  primary_topic?: string | null;
  chapter?: string;
  category?: string;
  source?: string;
  tradition?: string;
  text_english?: string | null;
  text_arabic?: string | null;
}

export interface HistoricalEvent extends HistoricalEventData, Record<string, unknown> {
  id: string;
}

export interface Commentary extends CommentaryData, Record<string, unknown> {
  id: string;
  hadith?: HadithDetails | null;
  narrator?: NarratorDetails | null;
}

export interface Location extends LocationData, Record<string, unknown> {
  id: string;
}

export interface NarratorDetails extends Record<string, unknown> {
  id: string;
  name_english: string;
  name_arabic: string;
  reliability?: LegacyNarratorReliability;
  tabaqah: string;
  birth_year_hijri?: number;
  birth_year_gregorian?: number;
  death_year_hijri?: number;
  death_year_gregorian?: number;
  birth_date_hijri?: number;
  birth_date_gregorian?: number;
  birth_date_source_text?: string;
  birth_date_provenance?: string;
  birth_date_review_status?: string;
  death_date_hijri?: number;
  death_date_gregorian?: number;
  death_date_source_text?: string;
  death_date_provenance?: string;
  death_date_review_status?: string;
  bio?: string;
  biographical_narrative?: string;
  geographic_region?: string;
  is_prophet?: boolean;
  is_companion?: boolean;
  name_arabic_clean?: string;
  name_english_clean?: string;
  kunya?: string;
  nasab?: string;
  nisba?: string;
  bio_summary?: string;
  bio_tadil?: string;
  bio_jarh?: string;
  reliability_consensus?: string;
  reliability_disagreement?: boolean;
  critic_quote_count?: number;
  bio_provenance?: string;
}

export interface NarratorHadithSummary extends Record<string, unknown> {
  id: string;
  title: string;
  primary_topic?: string;
  display_grade?: string;
}

export interface EnhancedNarratorDetails extends NarratorDetails {
  other_hadiths: NarratorHadithSummary[];
  locations: Array<Record<string, unknown>>;
  teacher_student_network: {
    teachers: Array<Record<string, unknown>>;
    students: Array<Record<string, unknown>>;
  };
}

// ============ READ HELPERS ============

function optionalString(value: unknown): string | undefined {
  return typeof value === 'string' && value.trim() ? value : undefined;
}

function optionalNumber(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined;
}

function optionalBoolean(value: unknown): boolean | undefined {
  return typeof value === 'boolean' ? value : undefined;
}

function legacyReliability(value: unknown): LegacyNarratorReliability | undefined {
  const normalized = optionalString(value)?.toUpperCase();
  return normalized === 'THIQA' || normalized === 'SADUQ' || normalized === 'DAIF' ||
    normalized === 'MAJHUL' || normalized === 'KADHAB'
    ? normalized
    : undefined;
}

function withNarratorDateAliases(props: Record<string, unknown>): NarratorDetails {
  const birthHijri = optionalNumber(props.birth_date_hijri) ?? optionalNumber(props.birth_year_hijri);
  const birthGregorian = optionalNumber(props.birth_date_gregorian) ?? optionalNumber(props.birth_year_gregorian);
  const deathHijri = optionalNumber(props.death_date_hijri) ?? optionalNumber(props.death_year_hijri);
  const deathGregorian = optionalNumber(props.death_date_gregorian) ?? optionalNumber(props.death_year_gregorian);
  return {
    ...props,
    id: optionalString(props.id) ?? '',
    name_english: optionalString(props.name_english) ?? optionalString(props.name) ?? '',
    name_arabic: optionalString(props.name_arabic) ?? '',
    reliability: legacyReliability(props.reliability),
    tabaqah: optionalString(props.tabaqah) ?? '',
    birth_date_hijri: optionalNumber(props.birth_date_hijri),
    birth_date_gregorian: optionalNumber(props.birth_date_gregorian),
    birth_date_source_text: optionalString(props.birth_date_source_text),
    birth_date_provenance: optionalString(props.birth_date_provenance),
    birth_date_review_status: optionalString(props.birth_date_review_status),
    death_date_hijri: optionalNumber(props.death_date_hijri),
    death_date_gregorian: optionalNumber(props.death_date_gregorian),
    death_date_source_text: optionalString(props.death_date_source_text),
    death_date_provenance: optionalString(props.death_date_provenance),
    death_date_review_status: optionalString(props.death_date_review_status),
    birth_year_hijri: birthHijri,
    birth_year_gregorian: birthGregorian,
    death_year_hijri: deathHijri,
    death_year_gregorian: deathGregorian,
    bio: optionalString(props.bio),
    biographical_narrative: optionalString(props.biographical_narrative),
    geographic_region: optionalString(props.geographic_region),
    is_prophet: optionalBoolean(props.is_prophet),
    is_companion: optionalBoolean(props.is_companion),
    name_arabic_clean: optionalString(props.name_arabic_clean),
    name_english_clean: optionalString(props.name_english_clean),
    kunya: optionalString(props.kunya),
    nasab: optionalString(props.nasab),
    nisba: optionalString(props.nisba),
    bio_summary: optionalString(props.bio_summary),
    bio_tadil: optionalString(props.bio_tadil),
    bio_jarh: optionalString(props.bio_jarh),
    reliability_consensus: optionalString(props.reliability_consensus),
    reliability_disagreement: optionalBoolean(props.reliability_disagreement),
    critic_quote_count: optionalNumber(props.critic_quote_count),
    bio_provenance: optionalString(props.bio_provenance),
  };
}

export async function getNarratorById(id: string): Promise<NarratorDetails | null> {
  const result = await runQuery<{ n: Neo4jEntity }>(`
    MATCH (n:Narrator {id: $id})
    RETURN n
  `, { id });
  const props = result[0]?.n.properties as Record<string, unknown> | undefined;
  return props ? withNarratorDateAliases(props) : null;
}

export async function getAllNarrators(
  pagination?: PaginationParams,
): Promise<PaginatedResult<NarratorDetails>> {
  const { skip, limit, page, pageSize } = toSkipLimit(pagination);
  const [countResult, result] = await Promise.all([
    runQuery<{ total: number }>(`MATCH (n:Narrator) WHERE n.is_prophet IS NULL OR n.is_prophet = false RETURN count(n) as total`),
    runQuery(`
      MATCH (n:Narrator)
      WHERE n.is_prophet IS NULL OR n.is_prophet = false
      RETURN n
      ORDER BY coalesce(n.name_english, n.name)
      SKIP $skip LIMIT $limit
    `, { skip, limit }),
  ]);
  return paginate(
    result.map((r) => withNarratorDateAliases(r.n.properties)),
    countResult[0]?.total ?? 0,
    page,
    pageSize,
  );
}

// --- HADITH ---
export async function getHadithById(id: string) {
  // v2 schema: Hadith is the single source of text/sanad fields; no MatnVariation
  // intermediary. Chains attach directly via (h)-[:HAS_CHAIN]->(:Chain).
  // We still optional-match MatnVariation so any legacy v1 nodes that survived
  // a partial migration won't break the page.
  const result = await runQuery(`
    MATCH (h:Hadith {id: $id})
    OPTIONAL MATCH (h)-[:HAS_VARIATION]->(m:MatnVariation)
    RETURN h, collect(DISTINCT m) as legacy_variations
  `, { id });

  if (result.length === 0) return null;

  const props = result[0].h.properties as Record<string, unknown>;
  const legacyVariations = (result[0].legacy_variations as Array<{ properties: Record<string, unknown> } | null>) ?? [];

  // Backward-compatible aliases so existing UI bindings keep rendering.
  // v2 schema is authoritative; the v1 names are mirrored for the read layer only.
  const text_en = optionalString(props.text_en) ?? optionalString(props.text_english);
  const text_ar = optionalString(props.text_ar) ?? optionalString(props.text_arabic);
  const chapter = optionalString(props.chapter);
  const category = optionalString(props.category);
  const canonicalSanad = optionalString(props.sanad) ??
    optionalString(props.isnad_arabic) ??
    optionalString(props.chain_text_arabic);

  // Build a "variations" array for legacy UI bindings: if no MatnVariation
  // children exist, synthesise one from the Hadith's own matn fields so the
  // detail page renders matn text.
  let variations: Array<Record<string, unknown>>;
  if (legacyVariations.length > 0) {
    variations = legacyVariations
      .filter((v): v is { properties: Record<string, unknown> } => v !== null)
      .map((v) => v.properties);
  } else {
    const synthesized: Record<string, unknown> = {
      id: `${props.id}::synthesized`,
      // Prefer matn_* (the canonical narrative text in v2), fall back to text_*
      text_arabic: optionalString(props.matn_ar) ?? text_ar ?? null,
      text_english: optionalString(props.matn_en) ?? text_en ?? null,
      source: 'hadith_node',
    };
    variations = [synthesized];
  }

  return {
    ...props,
    // v1 aliases for legacy UI bindings
    title: optionalString(props.title) ?? chapter ?? category ?? null,
    primary_topic: optionalString(props.primary_topic) ?? category ?? null,
    text_english: text_en ?? null,
    text_arabic: text_ar ?? null,
    // v2 fields the UI should start reading directly
    sanad: canonicalSanad ?? null,
    isnad_arabic: optionalString(props.isnad_arabic) ?? canonicalSanad ?? null,
    chain_text_arabic: optionalString(props.chain_text_arabic) ?? canonicalSanad ?? null,
    matn_ar: optionalString(props.matn_ar) ?? null,
    matn_en: optionalString(props.matn_en) ?? null,
    variations,
  };
}

export async function getAllHadiths(
  pagination?: PaginationParams,
): Promise<PaginatedResult<HadithDetails>> {
  const { skip, limit, page, pageSize } = toSkipLimit(pagination);
  const [countResult, result] = await Promise.all([
    runQuery<{ total: number }>(`MATCH (h:Hadith) RETURN count(h) as total`),
    runQuery(`
      MATCH (h:Hadith)
      RETURN h
      ORDER BY h.source, toInteger(h.hadith_no)
      SKIP $skip LIMIT $limit
    `, { skip, limit }),
  ]);
  return paginate(result.map((r) => r.h.properties), countResult[0]?.total ?? 0, page, pageSize);
}

// --- GRAPH QUERIES ---
export async function getFullChainGraph(hadithId: string) {
  // v2 schema: direct (h)-[:HAS_CHAIN]->(:Chain)-[:INCLUDES]->(:Narrator) traversal.
  // Transmission edges between narrators are :NARRATED_FROM (with confidence +
  // temporal_plausibility + extraction_method + source). The legacy v1 path
  // (HAS_VARIATION → MatnVariation → TRANSMITTED_VIA → Chain) remains a
  // read-only fallback. Legacy :HEARD_FROM edges are global rather than
  // chain-scoped, so they are deliberately not used to infer chain order.
  //
  // Order nodes by chain position (the :INCLUDES.position property). Cypher's
  // `collect()` and `RETURN DISTINCT n` do NOT preserve insertion order, so
  // without an explicit ORDER BY the narrators come back scrambled and the
  // isnad renders in the wrong sequence on the page.
  const params = { hadithId };
  const [directNodes, directEdges] = await Promise.all([
    runQuery<{ n: Neo4jEntity }>(`
      MATCH (h:Hadith {id: $hadithId})-[:HAS_CHAIN]->(c:Chain)-[i:INCLUDES]->(n:Narrator)
      RETURN DISTINCT coalesce(c.id, c.pipeline_key, toString(id(c))) AS chainId,
             c.chain_index AS chainIndex, i.position AS position, n
      ORDER BY coalesce(c.chain_index, 0), chainId, position, n.id
    `, params),
    runQuery(`
      MATCH (h:Hadith {id: $hadithId})-[:HAS_CHAIN]->(c:Chain)-[i1:INCLUDES]->(n1:Narrator)
      MATCH (n1)-[r:NARRATED_FROM]->(n2:Narrator)
      MATCH (c)-[i2:INCLUDES]->(n2)
      WHERE i1.position IS NULL OR i2.position IS NULL OR i2.position = i1.position + 1
      RETURN DISTINCT coalesce(c.id, c.pipeline_key, toString(id(c))) AS chainId,
             c.chain_index AS chainIndex, i1.position AS sourcePosition,
             i2.position AS targetPosition, n1, r, n2
      ORDER BY coalesce(c.chain_index, 0), chainId, sourcePosition
    `, params),
  ]);

  let schema: 'v2' | 'legacy' = 'v2';
  let nodeRows = directNodes;
  let edgeRows = directEdges;

  if (directNodes.length === 0) {
    schema = 'legacy';
    nodeRows = await runQuery(`
      MATCH (h:Hadith {id: $hadithId})-[:HAS_VARIATION]->(:MatnVariation)
            -[:TRANSMITTED_VIA]->(c:Chain)-[i:INCLUDES]->(n:Narrator)
      RETURN DISTINCT coalesce(c.id, c.pipeline_key, toString(id(c))) AS chainId,
             c.chain_index AS chainIndex, i.position AS position, n
      ORDER BY coalesce(c.chain_index, 0), chainId, position, n.id
    `, params);
    edgeRows = [];
  }

  return {
    nodes: nodeRows.map((row) => ({
      ...row.n.properties,
      chain_id: String(row.chainId),
      chain_index: typeof row.chainIndex === 'number' ? row.chainIndex : null,
      position: typeof row.position === 'number' ? row.position : null,
      chain_position: typeof row.position === 'number' ? row.position : null,
      chain_schema: schema,
    })),
    edges: edgeRows.map((row) => ({
      source: row.n1.properties.id,
      target: row.n2.properties.id,
      type: schema === 'v2' ? 'NARRATED_FROM' : 'HEARD_FROM',
      chain_id: String(row.chainId),
      chain_index: typeof row.chainIndex === 'number' ? row.chainIndex : null,
      source_position: typeof row.sourcePosition === 'number' ? row.sourcePosition : null,
      target_position: typeof row.targetPosition === 'number' ? row.targetPosition : null,
      // v2: status now comes from temporal_plausibility ('plausible'|'impossible'|'unknown').
      // Fall back to legacy r.status if a partial-migration edge still carries it.
      status: row.r.properties.temporal_plausibility ?? row.r.properties.status ?? null,
      confidence: row.r.properties.confidence ?? null,
      extraction_method: row.r.properties.extraction_method ?? null,
      chain_schema: schema,
    })),
  };
}

/**
 * Search narrators by name with optional filters
 */
export async function searchNarrators(searchTerm: string = '', filters?: {
  reliability?: string;
  tabaqah?: string;
  geographic_region?: string;
}) {
  let query = `
    MATCH (n:Narrator)
    WHERE (n.is_prophet IS NULL OR n.is_prophet = false)
  `;

  const params: Record<string, any> = {};

  if (searchTerm) {
    query += ` AND (toLower(n.name_english) CONTAINS toLower($searchTerm) 
                   OR toLower(n.name_arabic) CONTAINS toLower($searchTerm))`;
    params.searchTerm = searchTerm;
  }

  if (filters?.reliability) {
    query += ` AND n.reliability = $reliability`;
    params.reliability = filters.reliability;
  }

  if (filters?.tabaqah) {
    query += ` AND n.tabaqah = $tabaqah`;
    params.tabaqah = filters.tabaqah;
  }

  if (filters?.geographic_region) {
    query += ` AND n.geographic_region = $geographic_region`;
    params.geographic_region = filters.geographic_region;
  }

  query += `
    RETURN n
    ORDER BY n.name_english
    LIMIT 50
  `;

  const result = await runQuery(query, params);
  return result.map((r) => r.n.properties);
}

// ============ HISTORICAL EVENTS ============

/**
 * Create a historical event node
 */
export async function createHistoricalEvent(data: HistoricalEventData): Promise<string> {
  const id = randomUUID();
  const startYearHijri = data.start_year_hijri ?? data.year_hijri ?? null;
  const startYearGregorian = data.start_year_gregorian ?? data.year_gregorian ?? null;
  await runWrite(`
    CREATE (e:HistoricalEvent {
      id: $id,
      title: $title,
      title_arabic: $title_arabic,
      description: $description,
      year_hijri: $year_hijri,
      year_gregorian: $year_gregorian,
      start_year_hijri: $start_year_hijri,
      start_year_gregorian: $start_year_gregorian,
      end_year_hijri: $end_year_hijri,
      end_year_gregorian: $end_year_gregorian,
      category: $category,
      significance: $significance,
      location_name: $location_name,
      verification_status: $verification_status,
      publication_ready: $publication_ready,
      citation_source: $citation_source,
      citation_locator: $citation_locator,
      citation_url: $citation_url,
      citation_retrieved_at: $citation_retrieved_at,
      created_at: datetime()
    })
  `, {
    id,
    title: data.title,
    title_arabic: data.title_arabic ?? null,
    description: data.description,
    year_hijri: startYearHijri,
    year_gregorian: startYearGregorian,
    start_year_hijri: startYearHijri,
    start_year_gregorian: startYearGregorian,
    end_year_hijri: data.end_year_hijri ?? null,
    end_year_gregorian: data.end_year_gregorian ?? null,
    category: data.category,
    significance: data.significance ?? null,
    location_name: data.location_name ?? null,
    verification_status: data.verification_status ?? 'unverified',
    publication_ready: data.publication_ready ?? false,
    citation_source: data.citation_source ?? null,
    citation_locator: data.citation_locator ?? null,
    citation_url: data.citation_url ?? null,
    citation_retrieved_at: data.citation_retrieved_at ?? null,
  });
  return id;
}

/**
 * Get all historical events with optional filters
 */
export async function getAllHistoricalEvents(filters?: {
  category?: string;
  yearRange?: [number, number];
}, pagination?: PaginationParams): Promise<PaginatedResult<any>> {
  const { skip, limit, page, pageSize } = toSkipLimit(pagination);
  let whereClause = '';
  const params: Record<string, any> = { skip, limit };
  const conditions: string[] = [];

  if (filters?.category) {
    conditions.push('e.category = $category');
    params.category = filters.category;
  }
  if (filters?.yearRange) {
    conditions.push(
      'coalesce(e.end_year_hijri, e.start_year_hijri, e.year_hijri) >= $minYear ' +
      'AND coalesce(e.start_year_hijri, e.year_hijri) <= $maxYear',
    );
    params.minYear = filters.yearRange[0];
    params.maxYear = filters.yearRange[1];
  }

  if (conditions.length > 0) {
    whereClause = ' WHERE ' + conditions.join(' AND ');
  }

  const [countResult, result] = await Promise.all([
    runQuery<{ total: number }>(`MATCH (e:HistoricalEvent)${whereClause} RETURN count(e) as total`, params),
    runQuery(`MATCH (e:HistoricalEvent)${whereClause} RETURN e ORDER BY coalesce(e.start_year_hijri, e.year_hijri) SKIP $skip LIMIT $limit`, params),
  ]);
  return paginate(result.map((r) => r.e.properties), countResult[0]?.total ?? 0, page, pageSize);
}

export async function deleteHistoricalEvent(eventId: string): Promise<void> {
  await runWrite(`MATCH (e:HistoricalEvent {id: $eventId}) DETACH DELETE e`, { eventId });
}

const HISTORICAL_EVENT_KEYS = [
  'title', 'title_arabic', 'description',
  'year_hijri', 'year_gregorian',
  'start_year_hijri', 'start_year_gregorian',
  'end_year_hijri', 'end_year_gregorian',
  'category', 'significance', 'location_name',
  'verification_status', 'publication_ready',
  'citation_source', 'citation_locator', 'citation_url', 'citation_retrieved_at',
] as const;

export async function updateHistoricalEvent(eventId: string, data: Partial<HistoricalEventData>): Promise<void> {
  const normalized: Partial<HistoricalEventData> = { ...data };
  if (data.start_year_hijri !== undefined) normalized.year_hijri = data.start_year_hijri;
  else if (data.year_hijri !== undefined) normalized.start_year_hijri = data.year_hijri;
  if (data.start_year_gregorian !== undefined) normalized.year_gregorian = data.start_year_gregorian;
  else if (data.year_gregorian !== undefined) normalized.start_year_gregorian = data.year_gregorian;
  const safe = safeKeys(normalized, HISTORICAL_EVENT_KEYS);
  const setClause = buildSetClause('e', safe);
  if (!setClause) return;
  await runWrite(`MATCH (e:HistoricalEvent {id: $eventId}) SET ${setClause}`, { eventId, ...safe });
}

/**
 * Get historical events during a narrator's lifetime
 *
 * The legacy seed is intentionally hidden: only explicitly publishable,
 * reviewed events with a source plus locator or stable URL may reach readers.
 */
export async function getHistoricalEventsForNarrator(narratorId: string) {
  const result = await runQuery(`
    MATCH (n:Narrator {id: $narratorId})
    WITH n,
         coalesce(n.birth_date_hijri, n.birth_year_hijri) AS birthYear,
         coalesce(n.death_date_hijri, n.death_year_hijri) AS deathYear
    MATCH (e:HistoricalEvent)
    WITH e, birthYear, deathYear,
         coalesce(e.start_year_hijri, e.year_hijri) AS eventStart,
         coalesce(e.end_year_hijri, e.start_year_hijri, e.year_hijri) AS eventEnd
    WHERE (birthYear IS NOT NULL OR deathYear IS NOT NULL)
      AND eventStart IS NOT NULL
      AND e.publication_ready = true
      AND e.verification_status IN ['human_verified', 'source_verified']
      AND trim(coalesce(e.citation_source, '')) <> ''
      AND (
        trim(coalesce(e.citation_locator, '')) <> '' OR
        trim(coalesce(e.citation_url, '')) <> ''
      )
      AND (birthYear IS NULL OR eventEnd >= birthYear)
      AND (deathYear IS NULL OR eventStart <= deathYear)
    RETURN DISTINCT e, eventStart AS sortYear
    ORDER BY sortYear
  `, { narratorId });
  return result.map((r) => r.e.properties);
}

/**
 * Link a narrator to a historical event with optional role
 */
export async function linkNarratorToEvent(
  narratorId: string,
  eventId: string,
  role?: string
): Promise<void> {
  await runWrite(`
    MATCH (n:Narrator {id: $narratorId})
    MATCH (e:HistoricalEvent {id: $eventId})
    MERGE (n)-[:INVOLVED_IN {role: $role}]->(e)
  `, { narratorId, eventId, role: role || 'Participant' });
}

/**
 * Get full timeline for a narrator (birth, contextual events, involved events, death)
 */
export async function getTimelineForNarrator(narratorId: string) {
  const narrator = await getNarratorById(narratorId);
  const contextualEvents = await getHistoricalEventsForNarrator(narratorId);

  const involvedEvents = await runQuery(`
    MATCH (n:Narrator {id: $narratorId})-[r:INVOLVED_IN]->(e:HistoricalEvent)
    WHERE e.publication_ready = true
      AND e.verification_status IN ['human_verified', 'source_verified']
      AND trim(coalesce(e.citation_source, '')) <> ''
      AND (
        trim(coalesce(e.citation_locator, '')) <> '' OR
        trim(coalesce(e.citation_url, '')) <> ''
      )
    RETURN e, r.role as role
    ORDER BY coalesce(e.start_year_hijri, e.year_hijri)
  `, { narratorId });

  return {
    narrator,
    birth_year_hijri: narrator?.birth_year_hijri,
    death_year_hijri: narrator?.death_year_hijri,
    events: involvedEvents.map((r) => ({ ...r.e.properties, role: r.role })),
    contextual_events: contextualEvents,
  };
}

// ============ COMMENTARIES ============

/**
 * Create a commentary linked to a hadith and/or narrator
 */
export async function createCommentary(data: CommentaryData): Promise<string> {
  const id = randomUUID();
  const queries: Array<{ query: string; params?: Record<string, any> }> = [
    {
      query: `
        CREATE (c:Commentary {
          id: $id,
          source_work: $source_work,
          author: $author,
          text: $text,
          text_arabic: $text_arabic,
          type: $type,
          reference: $reference,
          created_at: datetime()
        })
      `,
      params: {
        id,
        source_work: data.source_work,
        author: data.author,
        text: data.text,
        text_arabic: data.text_arabic || null,
        type: data.type,
        reference: data.reference || null,
      },
    },
  ];

  if (data.hadith_id) {
    queries.push({
      query: `
        MATCH (c:Commentary {id: $id})
        MATCH (h:Hadith {id: $hadith_id})
        CREATE (c)-[:COMMENTS_ON]->(h)
      `,
      params: { id, hadith_id: data.hadith_id },
    });
  }

  if (data.narrator_id) {
    queries.push({
      query: `
        MATCH (c:Commentary {id: $id})
        MATCH (n:Narrator {id: $narrator_id})
        CREATE (c)-[:DISCUSSES]->(n)
      `,
      params: { id, narrator_id: data.narrator_id },
    });
  }

  await runTransaction(queries);
  return id;
}

export async function getAllCommentaries(pagination?: PaginationParams): Promise<PaginatedResult<any>> {
  const { skip, limit, page, pageSize } = toSkipLimit(pagination);
  const [countResult, result] = await Promise.all([
    runQuery<{ total: number }>(`MATCH (c:Commentary) RETURN count(c) as total`),
    runQuery(`
      MATCH (c:Commentary)
      OPTIONAL MATCH (c)-[:COMMENTS_ON]->(h:Hadith)
      OPTIONAL MATCH (c)-[:DISCUSSES]->(n:Narrator)
      RETURN c, h, n
      ORDER BY c.created_at DESC
      SKIP $skip LIMIT $limit
    `, { skip, limit }),
  ]);
  return paginate(
    result.map((r) => ({
      ...r.c.properties,
      hadith: r.h?.properties || null,
      narrator: r.n?.properties || null,
    })),
    countResult[0]?.total ?? 0, page, pageSize,
  );
}

/**
 * Get all commentaries for a hadith
 */
export async function getCommentariesForHadith(hadithId: string) {
  const result = await runQuery(`
    MATCH (c:Commentary)-[:COMMENTS_ON]->(h:Hadith {id: $hadithId})
    RETURN c
    ORDER BY c.created_at DESC
  `, { hadithId });
  return result.map((r) => r.c.properties);
}

/**
 * Get all commentaries for a narrator
 */
export async function getCommentariesForNarrator(narratorId: string) {
  const result = await runQuery(`
    MATCH (c:Commentary)-[:DISCUSSES]->(n:Narrator {id: $narratorId})
    RETURN c
    ORDER BY c.created_at DESC
  `, { narratorId });
  return result.map((r) => r.c.properties);
}

const COMMENTARY_KEYS = ['source_work', 'author', 'text', 'text_arabic', 'type', 'reference'] as const;

export async function updateCommentary(commentaryId: string, data: Partial<CommentaryData>): Promise<void> {
  const safe = safeKeys(data, COMMENTARY_KEYS);
  const setClause = buildSetClause('c', safe);
  if (!setClause) return;
  await runWrite(`MATCH (c:Commentary {id: $commentaryId}) SET ${setClause}`, { commentaryId, ...safe });
}

export async function deleteCommentary(commentaryId: string): Promise<void> {
  await runWrite(`MATCH (c:Commentary {id: $commentaryId}) DETACH DELETE c`, { commentaryId });
}

// ============ LOCATIONS ============

/**
 * Create a location node
 */
export async function createLocation(data: LocationData): Promise<string> {
  const id = randomUUID();
  await runWrite(`
    CREATE (l:Location {
      id: $id,
      name: $name,
      name_arabic: $name_arabic,
      modern_country: $modern_country,
      region: $region,
      latitude: $latitude,
      longitude: $longitude,
      description: $description,
      created_at: datetime()
    })
  `, {
    id,
    name: data.name,
    name_arabic: (data as any).name_arabic || null,
    modern_country: data.modern_country || null,
    region: data.region || null,
    latitude: data.latitude || null,
    longitude: data.longitude || null,
    description: (data as any).description || null,
  });
  return id;
}

export async function getAllLocations(pagination?: PaginationParams): Promise<PaginatedResult<any>> {
  const { skip, limit, page, pageSize } = toSkipLimit(pagination);
  const [countResult, result] = await Promise.all([
    runQuery<{ total: number }>(`MATCH (l:Location) RETURN count(l) as total`),
    runQuery(`MATCH (l:Location) RETURN l ORDER BY l.name SKIP $skip LIMIT $limit`, { skip, limit }),
  ]);
  return paginate(result.map((r) => r.l.properties), countResult[0]?.total ?? 0, page, pageSize);
}

export async function deleteLocation(locationId: string): Promise<void> {
  await runWrite(`MATCH (l:Location {id: $locationId}) DETACH DELETE l`, { locationId });
}

const LOCATION_KEYS = ['name', 'name_arabic', 'modern_country', 'region', 'latitude', 'longitude', 'description'] as const;

export async function updateLocation(locationId: string, data: Partial<LocationData>): Promise<void> {
  const safe = safeKeys(data, LOCATION_KEYS);
  const setClause = buildSetClause('l', safe);
  if (!setClause) return;
  await runWrite(`MATCH (l:Location {id: $locationId}) SET ${setClause}`, { locationId, ...safe });
}

/**
 * Link a narrator to a location
 */
export async function linkNarratorToLocation(
  narratorId: string,
  locationId: string,
  relType: 'BORN_IN' | 'DIED_IN' | 'RESIDED_IN'
): Promise<void> {
  const VALID_REL_TYPES = new Set(['BORN_IN', 'DIED_IN', 'RESIDED_IN']);
  if (!VALID_REL_TYPES.has(relType) || !/^[A-Z_]+$/.test(relType)) {
    throw new Error(`Invalid relationship type: ${relType}`);
  }
  await runWrite(`
    MATCH (n:Narrator {id: $narratorId})
    MATCH (l:Location {id: $locationId})
    MERGE (n)-[:${relType}]->(l)
  `, { narratorId, locationId });
}

// ============ ENHANCED QUERIES ============

/**
 * Get enhanced narrator details with commentaries, events, locations, and teacher-student network
 */
export async function getEnhancedNarratorDetails(
  narratorId: string,
): Promise<EnhancedNarratorDetails | null> {
  const narrator = await getNarratorById(narratorId);
  if (!narrator) return null;

  const hadiths = await runQuery<{ h: { properties: Record<string, unknown> } }>(`
    MATCH (n:Narrator {id: $narratorId})<-[:INCLUDES]-(c:Chain)<-[:HAS_CHAIN]-(h:Hadith)
    RETURN DISTINCT h
    ORDER BY h.chapter, h.category
    LIMIT 100
  `, { narratorId });

  const locations = await runQuery<{
    l: { properties: Record<string, unknown> };
    relationType: string;
  }>(`
    MATCH (n:Narrator {id: $narratorId})-[r]->(l:Location)
    RETURN l, type(r) as relationType
  `, { narratorId });

  const network = await runQuery<{
    teachers: Array<Record<string, unknown>>;
    students: Array<Record<string, unknown>>;
  }>(`
    MATCH (n:Narrator {id: $narratorId})
    OPTIONAL MATCH (n)-[:NARRATED_FROM]->(teacher:Narrator)
    OPTIONAL MATCH (student:Narrator)-[:NARRATED_FROM]->(n)
    RETURN
      collect(DISTINCT teacher {.id, .name_english, .name_arabic, .reliability, .tabaqah}) as teachers,
      collect(DISTINCT student {.id, .name_english, .name_arabic, .reliability, .tabaqah}) as students
  `, { narratorId });

  const other_hadiths: NarratorHadithSummary[] = hadiths.map((r) => {
    const props = r.h.properties as Record<string, unknown>;
    return {
      ...props,
      id: optionalString(props.id) ?? '',
      // v1 aliases for legacy UI
      title: optionalString(props.chapter) ?? optionalString(props.category) ?? '',
      primary_topic: optionalString(props.category),
      display_grade: optionalString(props.display_grade),
      text_english: (props.text_en as string) ?? null,
      text_arabic: (props.text_ar as string) ?? null,
    };
  });

  const details: EnhancedNarratorDetails = {
    ...narrator,
    other_hadiths,
    locations: locations.map((r) => ({ ...r.l.properties, relationship: r.relationType })),
    teacher_student_network: network[0] || { teachers: [], students: [] },
  };
  return details;
}

/**
 * Get teacher-student network for graph visualization.
 *
 * v2: direction = student -[:NARRATED_FROM]-> teacher.
 */
export async function getNarratorNetwork(narratorId: string, depth: number = 2) {
  const teachers = await runQuery(`
    MATCH (n:Narrator {id: $narratorId})-[:NARRATED_FROM]->(teacher:Narrator)
    RETURN DISTINCT teacher
  `, { narratorId });

  const students = await runQuery(`
    MATCH (student:Narrator)-[:NARRATED_FROM]->(n:Narrator {id: $narratorId})
    RETURN DISTINCT student
  `, { narratorId });

  return {
    teachers: teachers.map((r) => ({ ...r.teacher.properties, relationship: 'teacher' })),
    students: students.map((r) => ({ ...r.student.properties, relationship: 'student' })),
  };
}

/**
 * Get statistics per hadith source
 */
export async function getSourceStats() {
  const result = await runQuery(`
    MATCH (s:Source)
    OPTIONAL MATCH (h:Hadith)-[:FROM_SOURCE]->(s)
    RETURN s.name as source, s.compiler as compiler, count(h) as hadith_count
    ORDER BY hadith_count DESC
  `);
  return result;
}

/**
 * Search hadiths by text or filters
 */
export async function searchHadiths(
  searchTerm: string = '',
  filters?: { source?: string; chapter?: string; tradition?: string; school?: string },
  pagination?: PaginationParams,
): Promise<PaginatedResult<any>> {
  const { skip, limit, page, pageSize } = toSkipLimit(pagination);
  const params: Record<string, any> = { skip, limit };
  const conditions: string[] = [];

  if (searchTerm) {
    conditions.push('(toLower(h.chapter) CONTAINS toLower($searchTerm) OR toLower(h.category) CONTAINS toLower($searchTerm) OR toLower(h.text_en) CONTAINS toLower($searchTerm))');
    params.searchTerm = searchTerm;
  }
  if (filters?.source) {
    conditions.push('trim(h.source) IN $sourceValues');
    params.sourceValues = getSourceFilterValues(filters.source);
  }
  if (filters?.chapter) {
    conditions.push('h.category = $chapter');
    params.chapter = filters.chapter;
  }
  const tradition = filters?.tradition ?? filters?.school;
  if (tradition) {
    conditions.push('h.tradition IN $traditionValues');
    params.traditionValues = getTraditionFilterValues(tradition);
  }

  const whereClause = conditions.length > 0 ? ' WHERE ' + conditions.join(' AND ') : '';

  const [countResult, result] = await Promise.all([
    runQuery<{ total: number }>(`MATCH (h:Hadith)${whereClause} RETURN count(h) as total`, params),
    runQuery(`MATCH (h:Hadith)${whereClause} RETURN h ORDER BY h.source, toInteger(h.hadith_no) SKIP $skip LIMIT $limit`, params),
  ]);

  const hadiths = result.map((r) => {
    const props = r.h.properties as Record<string, unknown>;
    return {
      ...props,
      // v1 aliases for legacy UI
      title: (props.chapter as string) || (props.category as string) || null,
      primary_topic: props.category || null,
      text_english: (props.text_en as string) ?? null,
      text_arabic: (props.text_ar as string) ?? null,
    };
  });

  return paginate(hadiths, countResult[0]?.total ?? 0, page, pageSize);
}

// ============ EXPORT ============

export interface ExportConfig {
  filters: { source?: string; tradition?: string; school?: string; searchTerm?: string };
  /** Which metadata fields to include */
  fields: string[];
  /** Which related edges to include as extra columns */
  edges: string[];
}

// v2: grade lives on :Assessment, not on :Hadith. The CSV currently emits
// only the matn-side fields; per-tradition grade columns are deferred until
// the grading-UX redesign (see runbook addendum 2026-05-25).
const ALLOWED_EXPORT_FIELDS = new Set([
  'id', 'chapter', 'category', 'source', 'hadith_no',
  'text_en', 'text_ar', 'tradition',
  // v1 aliases for downstream CSV consumers
  'title', 'primary_topic', 'text_english', 'text_arabic',
]);

const EXPORT_LIMIT = 10000;

/**
 * Export hadiths as structured rows for CSV generation.
 * Supports configurable fields and edge data (narrators, commentaries, schools, variations).
 */
export async function exportHadiths(config: ExportConfig): Promise<Record<string, string>[]> {
  // Validate fields against allowlist
  const validFields = config.fields.filter((f) => ALLOWED_EXPORT_FIELDS.has(f));

  const params: Record<string, any> = {};
  const conditions: string[] = [];

  if (config.filters.searchTerm) {
    conditions.push('(toLower(h.chapter) CONTAINS toLower($searchTerm) OR toLower(h.category) CONTAINS toLower($searchTerm) OR toLower(h.text_en) CONTAINS toLower($searchTerm))');
    params.searchTerm = config.filters.searchTerm;
  }
  if (config.filters.source) {
    conditions.push('trim(h.source) IN $sourceValues');
    params.sourceValues = getSourceFilterValues(config.filters.source);
  }
  const tradition = config.filters.tradition ?? config.filters.school;
  if (tradition) {
    conditions.push('h.tradition IN $traditionValues');
    params.traditionValues = getTraditionFilterValues(tradition);
  }

  const whereClause = conditions.length > 0 ? ' WHERE ' + conditions.join(' AND ') : '';

  // Single query with optional edge collection — avoids N+1
  const includeNarrators = config.edges.includes('narrators');
  const includeCommentaries = config.edges.includes('commentaries');
  const includeVariations = config.edges.includes('variations');
  const includeSchool = config.edges.includes('school');

  const optionalClauses: string[] = [];
  const returnFields = ['h'];

  if (includeNarrators) {
    // v2 schema: direct (h)-[:HAS_CHAIN]->(:Chain)-[:INCLUDES]->(n:Narrator)
    optionalClauses.push('OPTIONAL MATCH (h)-[:HAS_CHAIN]->(:Chain)-[:INCLUDES]->(n:Narrator)');
    returnFields.push('collect(DISTINCT n {.name_english, .reliability}) as narrators');
  }
  if (includeCommentaries) {
    optionalClauses.push('OPTIONAL MATCH (comm:Commentary)-[:COMMENTS_ON]->(h)');
    returnFields.push('collect(DISTINCT comm {.author, .source_work, .text}) as commentaries');
  }
  if (includeVariations) {
    // v2 schema: no MatnVariation; synthesize from hadith's own matn fields
    returnFields.push('[] as variations');
  }
  if (includeSchool) {
    optionalClauses.push('OPTIONAL MATCH (h)-[:IN_SCHOOL]->(sch:SchoolOfThought)');
    returnFields.push('collect(DISTINCT sch.name) as schools');
  }

  const cypher = `MATCH (h:Hadith)${whereClause}
    ${optionalClauses.join('\n    ')}
    RETURN ${returnFields.join(', ')}
    ORDER BY h.source, toInteger(h.hadith_no)
    LIMIT ${EXPORT_LIMIT}`;

  const hadiths = await runQuery(cypher, params);

  const rows: Record<string, string>[] = [];

  for (const r of hadiths) {
    const h = r.h.properties as Record<string, unknown>;
    const row: Record<string, string> = {};

    // Map v1 aliases for export if requested
    const fieldMapping: Record<string, string | null> = {
      title: ((h.chapter as string) || (h.category as string) || null),
      primary_topic: (h.category as string) || null,
      text_english: (h.text_en as string) ?? null,
      text_arabic: (h.text_ar as string) ?? null,
    };

    for (const field of validFields) {
      const mapped = fieldMapping[field];
      if (mapped !== undefined) {
        row[field] = mapped != null ? String(mapped) : '';
      } else {
        row[field] = h[field] != null ? String(h[field]) : '';
      }
    }

    if (includeNarrators && r.narrators) {
      row['narrators'] = r.narrators.map((n: any) => n.name_english).filter(Boolean).join('; ');
      row['narrator_reliability'] = r.narrators.map((n: any) => `${n.name_english}:${n.reliability || 'unknown'}`).filter((s: string) => !s.startsWith('undefined')).join('; ');
    }

    if (includeCommentaries && r.commentaries) {
      row['commentaries'] = r.commentaries.map((c: any) => `[${c.author} - ${c.source_work}] ${c.text}`).filter((s: string) => !s.startsWith('[undefined')).join(' | ');
    }

    // v2: variations are synthesized from hadith's own matn fields
    if (includeVariations) {
      row['variation_texts_english'] = (h.matn_en as string) || (h.text_en as string) || '';
      row['variation_texts_arabic'] = (h.matn_ar as string) || (h.text_ar as string) || '';
    }

    if (includeSchool && r.schools) {
      row['schools'] = r.schools.filter(Boolean).join('; ');
    }

    rows.push(row);
  }

  return rows;
}
