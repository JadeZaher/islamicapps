'use server';

/**
 * Scholar & ScholarVerdict graph actions — extracted from graph-actions.ts
 *
 * These functions manage the scholarly grading layer:
 *   - Scholar CRUD (modern hadith critics like al-Albani, al-Talidi, etc.)
 *   - ScholarVerdict creation + CITES_DEFECT relationships
 *   - display_grade resolution (scholar verdict > auto-calculated grade)
 *
 * Depends on: src/lib/db/neo4j.ts  (runQuery, runWrite, runTransaction)
 *
 * To re-enable, move this file back to src/app/actions/ and re-export
 * from the main graph-actions barrel, then restore the ScholarVerdict
 * UI in GradingPanel.tsx and the verdicts prop in client-page.tsx.
 */

import { runQuery, runWrite, runTransaction } from '@/lib/db/neo4j';
import { randomUUID } from 'crypto';

// ============ TYPES ============

export interface ScholarVerdictData {
  grade: 'SAHIH' | 'HASAN' | 'DAIF' | 'MAWDU';
  reasoning: string;
  confidenceLevel: 'HIGH' | 'MEDIUM' | 'LOW';
  citedNarratorIds?: string[]; // For CITES_DEFECT relationships
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

// ============ SCHOLAR CRUD ============

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

/**
 * Get all verdicts for a specific hadith with scholar details
 */
export async function getVerdictsForHadith(hadithId: string) {
  const result = await runQuery(`
    MATCH (v:ScholarVerdict)-[:GRADES]->(h:Hadith {id: $hadithId})
    MATCH (s:Scholar)-[:ISSUED]->(v)
    RETURN v, s
    ORDER BY s.authority_rank DESC
  `, { hadithId });

  return result.map((r) => ({
    ...r.v.properties,
    scholar: r.s.properties,
  }));
}
