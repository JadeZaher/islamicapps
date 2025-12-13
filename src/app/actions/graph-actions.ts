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

  const queries = [
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

  const queries = [
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
