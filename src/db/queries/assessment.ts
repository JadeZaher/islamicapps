/** Grades per hadith and verdicts per narrator, tradition-scoped (sections 5.6, 11.1). SQL fragments and reads. */
import 'server-only';
import { sql, type SQL } from 'drizzle-orm';
import type { HadithAssessmentGroup, NarratorVerdict } from './contracts';
import { groupAssessments, mapVerdicts } from './mappers';
import { oneRow } from './sql-helpers';

export type VerdictMode = 'public' | 'review';

/** A citation counts only when live and reviewed (section 5.8). Alias `c`. */
export const REVIEWED_CITATION = sql`c.retired_at is null and c.review_state in ('human_verified', 'source_verified')`;

/**
 * json array of verdicts for the narrator column `narratorId`. Public: published, tradition-scoped and citing a
 * live reviewed citation. Review: every live verdict, including unscoped Phase-0 imports.
 */
export function verdictsJson(narratorId: SQL, mode: VerdictMode): SQL {
  const gate =
    mode === 'public'
      ? sql`and a.status = 'published' and a.tradition_id is not null
            and exists (select 1 from citations c where c.id = a.citation_id and ${REVIEWED_CITATION})`
      : sql``;
  return sql`coalesce((
    select json_agg(json_build_object(
             'id', a.id, 'tradition', vt.code, 'verdict', a.verdict, 'kind', a.kind, 'status', a.status,
             'critic', a.critic, 'quote_ar', a.quote_ar, 'quote_en', a.quote_en)
           order by vt.code nulls last, a.kind, a.id)
    from narrator_assessments a
    left join traditions vt on vt.id = a.tradition_id
    where a.narrator_id = ${narratorId} and a.retired_at is null ${gate}
  ), '[]'::json)`;
}

/** json array of displayable grades for the hadith column `hadithId`; `collection_label` rows never appear. */
export function hadithAssessmentsJson(hadithId: SQL): SQL {
  return sql`coalesce((
    select json_agg(json_build_object(
             'tradition', at.code, 'kind', a.kind, 'grade_raw', a.grade_raw,
             'grade_canonical', a.grade_canonical, 'grader', a.grader, 'citation_raw', a.citation_raw)
           order by at.code, a.source_field, a.ordinal)
    from hadith_assessments a
    join traditions at on at.id = a.tradition_id
    where a.hadith_id = ${hadithId} and a.retired_at is null and a.kind <> 'collection_label'
  ), '[]'::json)`;
}

/** Grades for one hadith, one group per tradition. */
export async function getHadithAssessments(hadithId: string): Promise<HadithAssessmentGroup[]> {
  const row = await oneRow<{ assessments: unknown }>(sql`select ${hadithAssessmentsJson(sql`${hadithId}`)} as assessments`);
  return groupAssessments(row?.assessments);
}

/** Verdicts for one narrator under the given mode. */
export async function getNarratorVerdicts(narratorId: string, mode: VerdictMode = 'public'): Promise<NarratorVerdict[]> {
  const row = await oneRow<{ verdicts: unknown }>(sql`select ${verdictsJson(sql`${narratorId}`, mode)} as verdicts`);
  return mapVerdicts(row?.verdicts);
}
