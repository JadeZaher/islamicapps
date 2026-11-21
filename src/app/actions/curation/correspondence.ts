'use server';
/** Reviewer decisions on report correspondences (confirm, reject, uncertain). See src/db/AGENTS.md §Report correspondences. */
import { z } from 'zod';
import {
  CORRESPONDENCE_DECISIONS,
  CORRESPONDENCE_REVIEWED_RELATIONS,
  decideCorrespondence,
  type CorrespondenceDecisionResult,
} from '@/db/queries/correspondence-decisions';
import { requireCurator } from '@/lib/auth/require-curator';
import { attempt, type ActionResult } from './result';

const SAME_REPORT_RELATIONS = new Set(['same_wording', 'same_report_variant_wording', 'partial_overlap']);
const hadithId = z.string().trim().min(1).max(200);
const sha256 = z.string().regex(/^[0-9a-f]{64}$/, 'is not a SHA-256');

const decisionSchema = z
  .object({
    hadith_id_a: hadithId,
    hadith_id_b: hadithId,
    seen_arabic_sha256_a: sha256,
    seen_arabic_sha256_b: sha256,
    decision: z.enum(CORRESPONDENCE_DECISIONS),
    reviewed_relation: z.preprocess((value) => (value === '' ? null : value), z.enum(CORRESPONDENCE_REVIEWED_RELATIONS).nullable()).optional(),
    note: z.preprocess((value) => (typeof value === 'string' && value.trim() === '' ? null : value), z.string().trim().max(4000).nullable()).optional(),
  })
  .refine((input) => input.decision !== 'confirmed' || !input.reviewed_relation || SAME_REPORT_RELATIONS.has(input.reviewed_relation), {
    path: ['reviewed_relation'],
    message: 'A confirmation needs a same-report reading; use reject or uncertain for a shared formula, verse or ruling',
  });

/** Records the decision; the reviewer is the session actor, never an input field. */
export async function decideReportCorrespondence(input: unknown): Promise<ActionResult<CorrespondenceDecisionResult>> {
  return attempt(async () => {
    const actor = await requireCurator();
    return decideCorrespondence(actor, decisionSchema.parse(input));
  });
}
