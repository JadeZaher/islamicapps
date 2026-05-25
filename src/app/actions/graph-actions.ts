'use server';

import { runQuery, runWrite, runTransaction } from '@/lib/db/neo4j';
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

export interface NarratorData {
  name_arabic: string;
  name_english: string;
  reliability: 'THIQA' | 'SADUQ' | 'DAIF' | 'MAJHUL' | 'KADHAB';
  tabaqah: 'PROPHET' | 'SAHABA' | 'TABI_UN' | 'TABI_TABI_IN';
  bio: string;
  birth_year_hijri?: number;
  death_year_hijri?: number;
  geographic_region?: string;
}

export interface HadithData {
  title: string;
  primary_topic: string;
}

export interface HistoricalEventData {
  title: string;
  title_arabic?: string;
  description: string;
  year_hijri?: number;
  year_gregorian?: number;
  category: string;
  significance?: string;
  location_name?: string;
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
  modern_country?: string;
  region?: string;
  latitude?: number;
  longitude?: number;
}

// ============ GRADING SYSTEM ============

/**
 * Calculates auto_calculated_grade based on chain analysis
 * Logic:
 * - If any narrator is KADHAB (liar) → MAWDU
 * - If any narrator is DAIF and chain has gaps → DAIF
 * - If all narrators are THIQA and chain is connected → SAHIH
 * - If all narrators are THIQA or SADUQ → HASAN
 */
export async function calculateAutoGrade(hadithId: string): Promise<string> {
  // Get all narrators from all chains of this Hadith
  const narrators = await runQuery<{ reliability: string; connected: boolean }>(`
    MATCH (h:Hadith {id: $hadithId})-[:HAS_VARIATION]->(m:MatnVariation)
          -[:TRANSMITTED_VIA]->(c:Chain)-[:INCLUDES]->(n:Narrator)
    MATCH (n)-[r:HEARD_FROM]->()
    RETURN DISTINCT n.reliability as reliability, r.status as connected
  `, { hadithId });

  let grade = 'SAHIH';

  // Check for KADHAB (fabricators)
  if (narrators.some((n) => n.reliability === 'KADHAB')) {
    grade = 'MAWDU';
  }
  // Check for DAIF with broken chains
  else if (
    narrators.some((n) => n.reliability === 'DAIF') ||
    narrators.some((n) => !n.connected)
  ) {
    grade = 'DAIF';
  }
  // All THIQA → SAHIH
  else if (narrators.every((n) => n.reliability === 'THIQA')) {
    grade = 'SAHIH';
  }
  // Mix of THIQA and SADUQ → HASAN
  else if (narrators.every((n) => n.reliability === 'THIQA' || n.reliability === 'SADUQ')) {
    grade = 'HASAN';
  }
  // Default to DAIF if conditions unclear
  else {
    grade = 'DAIF';
  }

  // Store the auto-calculated grade
  await runWrite(`
    MATCH (h:Hadith {id: $hadithId})
    SET h.auto_calculated_grade = $grade
  `, { hadithId, grade });

  // Set display_grade to match auto-calculated
  await runWrite(`
    MATCH (h:Hadith {id: $hadithId})
    SET h.display_grade = $grade
  `, { hadithId, grade });

  return grade;
}

/**
 * Calculates transmission_type based on chain counts per generation
 * - MUTAWATIR: ≥10 chains per Tabaqah layer
 * - MASHHUR: 3-9 chains
 * - AZIZ: 2 chains
 * - GHARIB: 1 chain
 */
export async function calculateTransmissionType(hadithId: string): Promise<string> {
  const result = await runQuery<{ chainCount: number }>(`
    MATCH (h:Hadith {id: $hadithId})-[:HAS_VARIATION]->(m:MatnVariation)
          -[:TRANSMITTED_VIA]->(c:Chain)
    RETURN count(DISTINCT c) as chainCount
  `, { hadithId });

  const chainCount = result[0]?.chainCount || 0;

  let transmissionType = 'GHARIB';
  if (chainCount >= 10) {
    transmissionType = 'MUTAWATIR';
  } else if (chainCount >= 3) {
    transmissionType = 'MASHHUR';
  } else if (chainCount === 2) {
    transmissionType = 'AZIZ';
  }

  await runWrite(`
    MATCH (h:Hadith {id: $hadithId})
    SET h.transmission_type = $transmissionType
  `, { hadithId, transmissionType });

  return transmissionType;
}

// ============ CRUD OPERATIONS ============

// --- NARRATOR ---
export async function createNarrator(data: NarratorData): Promise<string> {
  const id = randomUUID();
  await runWrite(`
    CREATE (n:Narrator {
      id: $id,
      name_arabic: $name_arabic,
      name_english: $name_english,
      reliability: $reliability,
      tabaqah: $tabaqah,
      bio: $bio,
      birth_year_hijri: $birth_year_hijri,
      death_year_hijri: $death_year_hijri,
      geographic_region: $geographic_region
    })
  `, { id, ...data });
  return id;
}

export async function getNarratorById(id: string) {
  const result = await runQuery(`
    MATCH (n:Narrator {id: $id})
    RETURN n
  `, { id });
  return result[0]?.n.properties || null;
}

export async function getAllNarrators(pagination?: PaginationParams): Promise<PaginatedResult<any>> {
  const { skip, limit, page, pageSize } = toSkipLimit(pagination);
  const [countResult, result] = await Promise.all([
    runQuery<{ total: number }>(`MATCH (n:Narrator) WHERE n.is_prophet IS NULL OR n.is_prophet = false RETURN count(n) as total`),
    runQuery(`
      MATCH (n:Narrator)
      WHERE n.is_prophet IS NULL OR n.is_prophet = false
      RETURN n
      ORDER BY n.name_english
      SKIP $skip LIMIT $limit
    `, { skip, limit }),
  ]);
  return paginate(result.map((r) => r.n.properties), countResult[0]?.total ?? 0, page, pageSize);
}

// --- HADITH ---
export async function createHadith(data: HadithData): Promise<string> {
  const id = randomUUID();
  await runWrite(`
    CREATE (h:Hadith {
      id: $id,
      title: $title,
      primary_topic: $primary_topic,
      auto_calculated_grade: '',
      display_grade: '',
      transmission_type: ''
    })
  `, { id, ...data });
  return id;
}

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
  const text_en = props.text_en as string | null | undefined;
  const text_ar = props.text_ar as string | null | undefined;
  const chapter = props.chapter as string | null | undefined;
  const category = props.category as string | null | undefined;

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
      text_arabic: (props.matn_ar as string) || text_ar || null,
      text_english: (props.matn_en as string) || text_en || null,
      source: 'hadith_node',
    };
    variations = [synthesized];
  }

  return {
    ...props,
    // v1 aliases for legacy UI bindings
    title: chapter || category || null,
    primary_topic: category || null,
    text_english: text_en ?? null,
    text_arabic: text_ar ?? null,
    // v2 fields the UI should start reading directly
    isnad_arabic: (props.sanad as string) ?? null,
    chain_text_arabic: (props.sanad as string) ?? null,
    matn_ar: (props.matn_ar as string) ?? null,
    matn_en: (props.matn_en as string) ?? null,
    variations,
  };
}

export async function getAllHadiths(pagination?: PaginationParams): Promise<PaginatedResult<any>> {
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
  // (HAS_VARIATION → MatnVariation → TRANSMITTED_VIA → Chain) and the v1 edge
  // type (:HEARD_FROM) are NOT present after the v2 fullregen.
  //
  // Order nodes by chain position (the :INCLUDES.position property). Cypher's
  // `collect()` and `RETURN DISTINCT n` do NOT preserve insertion order, so
  // without an explicit ORDER BY the narrators come back scrambled and the
  // isnad renders in the wrong sequence on the page.
  const nodes = await runQuery(`
    MATCH (h:Hadith {id: $hadithId})-[:HAS_CHAIN]->(c:Chain)-[i:INCLUDES]->(n:Narrator)
    WITH n, min(i.position) AS pos
    RETURN n, pos
    ORDER BY pos
  `, { hadithId });

  const edges = await runQuery(`
    MATCH (h:Hadith {id: $hadithId})-[:HAS_CHAIN]->(c:Chain)-[i:INCLUDES]->(n1:Narrator)
    MATCH (n1)-[r:NARRATED_FROM]->(n2:Narrator)
    WHERE (c)-[:INCLUDES]->(n2)
    RETURN DISTINCT n1, r, n2, i.position AS pos
    ORDER BY pos
  `, { hadithId });

  return {
    nodes: nodes.map((r) => ({
      ...r.n.properties,
      // Surface the position so the UI can also sort if it shuffles.
      chain_position: typeof r.pos === 'number' ? r.pos : (r.pos?.toNumber?.() ?? null),
    })),
    edges: edges.map((r) => ({
      source: r.n1.properties.id,
      target: r.n2.properties.id,
      // v2: status now comes from temporal_plausibility ('plausible'|'impossible'|'unknown').
      // Fall back to legacy r.status if a partial-migration edge still carries it.
      status: r.r.properties.temporal_plausibility ?? r.r.properties.status ?? null,
      confidence: r.r.properties.confidence ?? null,
      extraction_method: r.r.properties.extraction_method ?? null,
    })),
  };
}

export async function getNarratorDetails(narratorId: string) {
  const narrator = await getNarratorById(narratorId);

  // Get other Hadiths this narrator appears in
  const hadiths = await runQuery(`
    MATCH (n:Narrator {id: $narratorId})<-[:INCLUDES]-(c:Chain)
          <-[:TRANSMITTED_VIA]-(m:MatnVariation)<-[:HAS_VARIATION]-(h:Hadith)
    RETURN DISTINCT h
    ORDER BY h.title
  `, { narratorId });

  return {
    ...narrator,
    other_hadiths: hadiths.map((r) => r.h.properties),
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

/**
 * Create a new chain with narrators
 * @param hadithId - The hadith this chain belongs to
 * @param variationId - The matn variation this chain transmits
 * @param narratorIds - Array of narrator IDs in order (oldest to youngest)
 */
export async function createChain(
  hadithId: string,
  variationId: string,
  narratorIds: string[]
): Promise<string> {
  const chainId = randomUUID();

  const queries: Array<{ query: string; params?: Record<string, any> }> = [
    {
      query: `
        CREATE (c:Chain {
          id: $id,
          is_golden_chain: false,
          created_at: datetime()
        })
      `,
      params: { id: chainId },
    },
    {
      query: `
        MATCH (m:MatnVariation {id: $variationId})
        MATCH (c:Chain {id: $chainId})
        CREATE (m)-[:TRANSMITTED_VIA]->(c)
      `,
      params: { variationId, chainId },
    },
  ];

  // Add INCLUDES relationships for all narrators
  for (const narratorId of narratorIds) {
    queries.push({
      query: `
        MATCH (c:Chain {id: $chainId})
        MATCH (n:Narrator {id: $narratorId})
        CREATE (c)-[:INCLUDES]->(n)
      `,
      params: { chainId, narratorId },
    });
  }

  // Create HEARD_FROM relationships between consecutive narrators
  for (let i = 0; i < narratorIds.length - 1; i++) {
    queries.push({
      query: `
        MATCH (student:Narrator {id: $studentId})
        MATCH (teacher:Narrator {id: $teacherId})
        MERGE (student)-[r:HEARD_FROM {
          status: 'connected',
          meeting_place: 'Unknown'
        }]->(teacher)
      `,
      params: {
        studentId: narratorIds[i],
        teacherId: narratorIds[i + 1],
      },
    });
  }

  await runTransaction(queries);

  // Recalculate grades for the hadith
  await calculateAutoGrade(hadithId);
  await calculateTransmissionType(hadithId);

  return chainId;
}

/**
 * Validate that a chain follows proper chronological order
 * Later generations cannot teach earlier generations
 */
export async function validateChainOrder(narratorIds: string[]): Promise<{
  valid: boolean;
  error?: string;
}> {
  // Fetch narrator details
  const narrators = await Promise.all(narratorIds.map((id) => getNarratorById(id)));

  const TABAQAH_ORDER = ['PROPHET', 'SAHABA', 'TABI_UN', 'TABI_TABI_IN'];

  for (let i = 0; i < narrators.length - 1; i++) {
    const student = narrators[i];
    const teacher = narrators[i + 1];

    if (!student || !teacher) {
      return { valid: false, error: 'One or more narrators not found' };
    }

    const studentLevel = TABAQAH_ORDER.indexOf(student.tabaqah);
    const teacherLevel = TABAQAH_ORDER.indexOf(teacher.tabaqah);

    // Student should be from later or same generation as teacher
    if (studentLevel < teacherLevel) {
      return {
        valid: false,
        error: `Invalid order: ${student.name_english} (${student.tabaqah}) cannot learn from ${teacher.name_english} (${teacher.tabaqah})`,
      };
    }

    // Check death/birth years if available
    if (student.birth_year_hijri && teacher.death_year_hijri) {
      if (student.birth_year_hijri > teacher.death_year_hijri) {
        return {
          valid: false,
          error: `Timeline conflict: ${student.name_english} was born after ${teacher.name_english} died`,
        };
      }
    }
  }

  return { valid: true };
}

// ============ HISTORICAL EVENTS ============

/**
 * Create a historical event node
 */
export async function createHistoricalEvent(data: HistoricalEventData): Promise<string> {
  const id = randomUUID();
  await runWrite(`
    CREATE (e:HistoricalEvent {
      id: $id,
      title: $title,
      title_arabic: $title_arabic,
      description: $description,
      year_hijri: $year_hijri,
      year_gregorian: $year_gregorian,
      category: $category,
      significance: $significance,
      location_name: $location_name,
      created_at: datetime()
    })
  `, {
    id,
    title: data.title,
    title_arabic: data.title_arabic || null,
    description: data.description,
    year_hijri: data.year_hijri || null,
    year_gregorian: data.year_gregorian || null,
    category: data.category,
    significance: data.significance || null,
    location_name: data.location_name || null,
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
    conditions.push('e.year_hijri >= $minYear AND e.year_hijri <= $maxYear');
    params.minYear = filters.yearRange[0];
    params.maxYear = filters.yearRange[1];
  }

  if (conditions.length > 0) {
    whereClause = ' WHERE ' + conditions.join(' AND ');
  }

  const [countResult, result] = await Promise.all([
    runQuery<{ total: number }>(`MATCH (e:HistoricalEvent)${whereClause} RETURN count(e) as total`, params),
    runQuery(`MATCH (e:HistoricalEvent)${whereClause} RETURN e ORDER BY e.year_hijri SKIP $skip LIMIT $limit`, params),
  ]);
  return paginate(result.map((r) => r.e.properties), countResult[0]?.total ?? 0, page, pageSize);
}

export async function deleteHistoricalEvent(eventId: string): Promise<void> {
  await runWrite(`MATCH (e:HistoricalEvent {id: $eventId}) DETACH DELETE e`, { eventId });
}

const HISTORICAL_EVENT_KEYS = ['title', 'title_arabic', 'description', 'year_hijri', 'year_gregorian', 'category', 'significance', 'location_name'] as const;

export async function updateHistoricalEvent(eventId: string, data: Partial<HistoricalEventData>): Promise<void> {
  const safe = safeKeys(data, HISTORICAL_EVENT_KEYS);
  const setClause = buildSetClause('e', safe);
  if (!setClause) return;
  await runWrite(`MATCH (e:HistoricalEvent {id: $eventId}) SET ${setClause}`, { eventId, ...safe });
}

/**
 * Get historical events during a narrator's lifetime
 */
export async function getHistoricalEventsForNarrator(narratorId: string) {
  const result = await runQuery(`
    MATCH (n:Narrator {id: $narratorId})
    MATCH (e:HistoricalEvent)
    WHERE (n.birth_year_hijri IS NULL OR e.year_hijri >= n.birth_year_hijri)
      AND (n.death_year_hijri IS NULL OR e.year_hijri <= n.death_year_hijri)
    RETURN DISTINCT e
    ORDER BY e.year_hijri
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
    RETURN e, r.role as role
    ORDER BY e.year_hijri
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
export async function getEnhancedNarratorDetails(narratorId: string) {
  const narrator = await getNarratorById(narratorId);
  if (!narrator) return null;

  const hadiths = await runQuery(`
    MATCH (n:Narrator {id: $narratorId})<-[:INCLUDES]-(c:Chain)<-[:HAS_CHAIN]-(h:Hadith)
    RETURN DISTINCT h
    ORDER BY h.chapter, h.category
    LIMIT 100
  `, { narratorId });

  const locations = await runQuery(`
    MATCH (n:Narrator {id: $narratorId})-[r]->(l:Location)
    RETURN l, type(r) as relationType
  `, { narratorId });

  const network = await runQuery(`
    MATCH (n:Narrator {id: $narratorId})
    OPTIONAL MATCH (n)-[:NARRATED_FROM]->(teacher:Narrator)
    OPTIONAL MATCH (student:Narrator)-[:NARRATED_FROM]->(n)
    RETURN
      collect(DISTINCT teacher {.id, .name_english, .name_arabic, .reliability, .tabaqah}) as teachers,
      collect(DISTINCT student {.id, .name_english, .name_arabic, .reliability, .tabaqah}) as students
  `, { narratorId });

  const other_hadiths = hadiths.map((r) => {
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

  return {
    ...narrator,
    other_hadiths,
    locations: locations.map((r) => ({ ...r.l.properties, relationship: r.relationType })),
    teacher_student_network: network[0] || { teachers: [], students: [] },
  };
}

/**
 * Get enhanced hadith details with commentaries and chain info
 */
export async function getEnhancedHadithDetails(hadithId: string) {
  const hadith = await getHadithById(hadithId);
  const commentaries = await getCommentariesForHadith(hadithId);

  const chains = await runQuery(`
    MATCH (h:Hadith {id: $hadithId})-[:HAS_VARIATION]->(m:MatnVariation)
          -[:TRANSMITTED_VIA]->(c:Chain)-[:INCLUDES]->(n:Narrator)
    RETURN DISTINCT c.id as chainId, collect(DISTINCT n {.id, .name_english, .name_arabic, .reliability, .tabaqah}) as narrators
  `, { hadithId });

  return { ...hadith, commentaries, transmission_chains: chains };
}

/**
 * Get teacher-student network for graph visualization
 */
export async function getNarratorNetwork(narratorId: string, depth: number = 2) {
  const teachers = await runQuery(`
    MATCH (n:Narrator {id: $narratorId})-[:HEARD_FROM]->(teacher:Narrator)
    RETURN DISTINCT teacher
  `, { narratorId });

  const students = await runQuery(`
    MATCH (student:Narrator)-[:HEARD_FROM]->(n:Narrator {id: $narratorId})
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
  filters?: { source?: string; grade?: string; chapter?: string; school?: string },
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
    conditions.push('h.source = $source');
    params.source = filters.source;
  }
  if (filters?.grade) {
    conditions.push('h.display_grade = $grade');
    params.grade = filters.grade;
  }
  if (filters?.chapter) {
    conditions.push('h.category = $chapter');
    params.chapter = filters.chapter;
  }
  if (filters?.school) {
    conditions.push('h.tradition = $school');
    params.school = filters.school;
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
  filters: { source?: string; grade?: string; school?: string; searchTerm?: string };
  /** Which metadata fields to include */
  fields: string[];
  /** Which related edges to include as extra columns */
  edges: string[];
}

const ALLOWED_EXPORT_FIELDS = new Set([
  'id', 'chapter', 'category', 'source', 'hadith_no',
  'text_en', 'text_ar', 'display_grade', 'transmission_type', 'tradition',
  // v1 aliases for backward compat
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
    conditions.push('h.source = $source');
    params.source = config.filters.source;
  }
  if (config.filters.grade) {
    conditions.push('h.display_grade = $grade');
    params.grade = config.filters.grade;
  }
  if (config.filters.school) {
    conditions.push('h.tradition = $school');
    params.school = config.filters.school;
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
