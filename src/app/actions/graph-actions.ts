'use server';

import { runQuery, runWrite, runTransaction } from '@/lib/db/neo4j';
import { randomUUID } from 'crypto';

// ============ TYPES ============

export interface ScholarVerdictData {
  grade: 'SAHIH' | 'HASAN' | 'DAIF' | 'MAWDU';
  reasoning: string;
  confidenceLevel: 'HIGH' | 'MEDIUM' | 'LOW';
  citedNarratorIds?: string[]; // For CITES_DEFECT relationships
}

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

// ============ DUAL GRADING SYSTEM ============

/**
 * Adds a scholar verdict to a Hadith
 * Automatically updates the display_grade after creation
 */
export async function addScholarVerdict(
  scholarId: string,
  hadithId: string,
  verdictData: ScholarVerdictData
): Promise<string> {
  const verdictId = randomUUID();
  const dateAssessed = new Date().toISOString();

  const queries: Array<{ query: string; params?: Record<string, any> }> = [
    {
      query: `
        CREATE (v:ScholarVerdict {
          id: $id,
          grade: $grade,
          reasoning: $reasoning,
          date_assessed: $dateAssessed,
          confidence_level: $confidenceLevel
        })
      `,
      params: {
        id: verdictId,
        grade: verdictData.grade,
        reasoning: verdictData.reasoning,
        dateAssessed,
        confidenceLevel: verdictData.confidenceLevel,
      },
    },
    {
      query: `
        MATCH (s:Scholar {id: $scholarId})
        MATCH (v:ScholarVerdict {id: $verdictId})
        MATCH (h:Hadith {id: $hadithId})
        CREATE (s)-[:ISSUED]->(v)
        CREATE (v)-[:GRADES]->(h)
      `,
      params: { scholarId, verdictId, hadithId },
    },
  ];

  // Add CITES_DEFECT relationships if provided
  if (verdictData.citedNarratorIds && verdictData.citedNarratorIds.length > 0) {
    for (const narratorId of verdictData.citedNarratorIds) {
      queries.push({
        query: `
          MATCH (v:ScholarVerdict {id: $verdictId})
          MATCH (n:Narrator {id: $narratorId})
          CREATE (v)-[:CITES_DEFECT {
            type: 'Weakness in chain',
            explanation: 'Referenced in verdict reasoning'
          }]->(n)
        `,
        params: { verdictId, narratorId },
      });
    }
  }

  await runTransaction(queries);

  // Update the display grade
  await updateDisplayGrade(hadithId);

  return verdictId;
}

/**
 * Updates the display_grade based on scholar verdicts
 * Priority: Highest authority_rank scholar verdict > auto_calculated_grade
 */
export async function updateDisplayGrade(hadithId: string): Promise<void> {
  const result = await runQuery<{ grade: string; rank: number }>(`
    MATCH (h:Hadith {id: $hadithId})
    OPTIONAL MATCH (v:ScholarVerdict)-[:GRADES]->(h)
    OPTIONAL MATCH (s:Scholar)-[:ISSUED]->(v)
    WITH h, v, s
    ORDER BY s.authority_rank DESC
    LIMIT 1
    RETURN 
      COALESCE(v.grade, h.auto_calculated_grade, 'UNGRADED') as grade,
      COALESCE(s.authority_rank, 0) as rank
  `, { hadithId });

  if (result.length > 0) {
    const displayGrade = result[0].grade;
    await runWrite(`
      MATCH (h:Hadith {id: $hadithId})
      SET h.display_grade = $displayGrade
    `, { hadithId, displayGrade });
  }
}

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

  // Update display grade (will use this if no scholar verdicts exist)
  await updateDisplayGrade(hadithId);

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

export async function getAllNarrators() {
  const result = await runQuery(`
    MATCH (n:Narrator)
    WHERE n.is_prophet IS NULL OR n.is_prophet = false
    RETURN n
    ORDER BY n.name_english
  `);
  return result.map((r) => r.n.properties);
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
  const result = await runQuery(`
    MATCH (h:Hadith {id: $id})
    OPTIONAL MATCH (h)-[:HAS_VARIATION]->(m:MatnVariation)
    OPTIONAL MATCH (v:ScholarVerdict)-[:GRADES]->(h)
    OPTIONAL MATCH (s:Scholar)-[:ISSUED]->(v)
    RETURN h, collect(DISTINCT m) as variations, 
           collect(DISTINCT {verdict: v, scholar: s}) as verdicts
  `, { id });

  if (result.length === 0) return null;

  return {
    ...result[0].h.properties,
    variations: result[0].variations.map((v: any) => v.properties),
    verdicts: result[0].verdicts
      .filter((v: any) => v.verdict)
      .map((v: any) => ({
        ...v.verdict.properties,
        scholar: v.scholar.properties,
      })),
  };
}

export async function getAllHadiths() {
  const result = await runQuery(`
    MATCH (h:Hadith)
    RETURN h
    ORDER BY h.title
  `);
  return result.map((r) => r.h.properties);
}

// --- SCHOLAR ---
export async function createScholar(data: {
  name: string;
  era: string;
  school: string;
  authority_rank: number;
}): Promise<string> {
  const id = randomUUID();
  await runWrite(`
    CREATE (s:Scholar {
      id: $id,
      name: $name,
      era: $era,
      school: $school,
      authority_rank: $authority_rank
    })
  `, { id, ...data });
  return id;
}

export async function getScholars() {
  const result = await runQuery(`
    MATCH (s:Scholar)
    RETURN s
    ORDER BY s.authority_rank DESC
  `);
  return result.map((r) => r.s.properties);
}

// --- GRAPH QUERIES ---
export async function getFullChainGraph(hadithId: string) {
  const nodes = await runQuery(`
    MATCH (h:Hadith {id: $hadithId})-[:HAS_VARIATION]->(m:MatnVariation)
          -[:TRANSMITTED_VIA]->(c:Chain)-[:INCLUDES]->(n:Narrator)
    RETURN DISTINCT n
  `, { hadithId });

  const edges = await runQuery(`
    MATCH (h:Hadith {id: $hadithId})-[:HAS_VARIATION]->(m:MatnVariation)
          -[:TRANSMITTED_VIA]->(c:Chain)-[:INCLUDES]->(n1:Narrator)
    MATCH (n1)-[r:HEARD_FROM]->(n2:Narrator)
    RETURN DISTINCT n1, r, n2
  `, { hadithId });

  return {
    nodes: nodes.map((r) => r.n.properties),
    edges: edges.map((r) => ({
      source: r.n1.properties.id,
      target: r.n2.properties.id,
      status: r.r.properties.status,
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
}) {
  let query = 'MATCH (e:HistoricalEvent)';
  const params: Record<string, any> = {};
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
    query += ' WHERE ' + conditions.join(' AND ');
  }

  query += ' RETURN e ORDER BY e.year_hijri';
  const result = await runQuery(query, params);
  return result.map((r) => r.e.properties);
}

export async function deleteHistoricalEvent(eventId: string): Promise<void> {
  await runWrite(`MATCH (e:HistoricalEvent {id: $eventId}) DETACH DELETE e`, { eventId });
}

export async function updateHistoricalEvent(eventId: string, data: Partial<HistoricalEventData>): Promise<void> {
  const setClause = Object.keys(data).map((key) => `e.${key} = $${key}`).join(', ');
  if (!setClause) return;
  await runWrite(`MATCH (e:HistoricalEvent {id: $eventId}) SET ${setClause}`, { eventId, ...data });
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

export async function getAllCommentaries() {
  const result = await runQuery(`
    MATCH (c:Commentary)
    OPTIONAL MATCH (c)-[:COMMENTS_ON]->(h:Hadith)
    OPTIONAL MATCH (c)-[:DISCUSSES]->(n:Narrator)
    RETURN c, h, n
    ORDER BY c.created_at DESC
  `);
  return result.map((r) => ({
    ...r.c.properties,
    hadith: r.h?.properties || null,
    narrator: r.n?.properties || null,
  }));
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

export async function updateCommentary(commentaryId: string, data: Partial<CommentaryData>): Promise<void> {
  const updateData = { ...data };
  delete (updateData as any).hadith_id;
  delete (updateData as any).narrator_id;

  const setClause = Object.keys(updateData).map((key) => `c.${key} = $${key}`).join(', ');
  if (!setClause) return;
  await runWrite(`MATCH (c:Commentary {id: $commentaryId}) SET ${setClause}`, { commentaryId, ...updateData });
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

export async function getAllLocations() {
  const result = await runQuery(`MATCH (l:Location) RETURN l ORDER BY l.name`);
  return result.map((r) => r.l.properties);
}

export async function deleteLocation(locationId: string): Promise<void> {
  await runWrite(`MATCH (l:Location {id: $locationId}) DETACH DELETE l`, { locationId });
}

export async function updateLocation(locationId: string, data: Partial<LocationData>): Promise<void> {
  const setClause = Object.keys(data).map((key) => `l.${key} = $${key}`).join(', ');
  if (!setClause) return;
  await runWrite(`MATCH (l:Location {id: $locationId}) SET ${setClause}`, { locationId, ...data });
}

/**
 * Link a narrator to a location
 */
export async function linkNarratorToLocation(
  narratorId: string,
  locationId: string,
  relType: 'BORN_IN' | 'DIED_IN' | 'RESIDED_IN'
): Promise<void> {
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
    MATCH (n:Narrator {id: $narratorId})<-[:INCLUDES]-(c:Chain)
          <-[:TRANSMITTED_VIA]-(m:MatnVariation)<-[:HAS_VARIATION]-(h:Hadith)
    RETURN DISTINCT h
    ORDER BY h.title
    LIMIT 100
  `, { narratorId });

  const locations = await runQuery(`
    MATCH (n:Narrator {id: $narratorId})-[r]->(l:Location)
    RETURN l, type(r) as relationType
  `, { narratorId });

  const network = await runQuery(`
    MATCH (n:Narrator {id: $narratorId})
    OPTIONAL MATCH (n)-[:HEARD_FROM]->(teacher:Narrator)
    OPTIONAL MATCH (student:Narrator)-[:HEARD_FROM]->(n)
    RETURN
      collect(DISTINCT teacher {.id, .name_english, .name_arabic, .reliability, .tabaqah}) as teachers,
      collect(DISTINCT student {.id, .name_english, .name_arabic, .reliability, .tabaqah}) as students
  `, { narratorId });

  return {
    ...narrator,
    other_hadiths: hadiths.map((r) => r.h.properties),
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
  filters?: { source?: string; grade?: string; chapter?: string }
) {
  let query = 'MATCH (h:Hadith)';
  const params: Record<string, any> = {};
  const conditions: string[] = [];

  if (searchTerm) {
    conditions.push('(toLower(h.title) CONTAINS toLower($searchTerm) OR toLower(h.primary_topic) CONTAINS toLower($searchTerm) OR toLower(h.text_english) CONTAINS toLower($searchTerm))');
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
    conditions.push('h.primary_topic = $chapter');
    params.chapter = filters.chapter;
  }

  if (conditions.length > 0) {
    query += ' WHERE ' + conditions.join(' AND ');
  }

  query += ' RETURN h ORDER BY h.title LIMIT 100';
  const result = await runQuery(query, params);
  return result.map((r) => r.h.properties);
}
