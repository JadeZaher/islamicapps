'use server';
/** Section 9.3 curation actions: publication status, rights, identity decisions, absences, network refresh. */
import * as curation from '@/db/queries/curation';
import { requireCurator } from '@/lib/auth/require-curator';
import { chainAbsenceSchema, collectionRightsSchema, curationStatusSchema, idSchema, surfaceDecisionSchema } from './schemas';

/** `published` needs a live, reviewed citation. */
export async function setBioStatus(narratorId: unknown, status: unknown): Promise<void> {
  const actor = await requireCurator();
  await curation.setBioStatus(actor, idSchema.parse(narratorId), curationStatusSchema.parse(status));
}

/** `published` needs a tradition and a live, reviewed citation. */
export async function setVerdictStatus(assessmentId: unknown, status: unknown): Promise<void> {
  const actor = await requireCurator();
  await curation.setVerdictStatus(actor, idSchema.parse(assessmentId), curationStatusSchema.parse(status));
}

/** Owner-only in practice: records a work's rights status and English policy. */
export async function setCollectionRights(collectionId: unknown, input: unknown): Promise<void> {
  const actor = await requireCurator();
  await curation.setCollectionRights(actor, idSchema.parse(collectionId), collectionRightsSchema.parse(input));
}

/** Records an identity decision; the reviewer is stamped from the session, never from input. */
export async function decideSurfaceUnit(input: unknown): Promise<curation.DecisionResult> {
  const actor = await requireCurator();
  return curation.decideSurfaceUnit(actor, surfaceDecisionSchema.parse(input));
}

export async function retireSurfaceDecision(decisionId: unknown): Promise<curation.DecisionResult> {
  const actor = await requireCurator();
  return curation.retireSurfaceDecision(actor, idSchema.parse(decisionId));
}

export async function recordChainAbsence(input: unknown): Promise<{ id: string; refreshed: number }> {
  const actor = await requireCurator();
  return curation.recordChainAbsence(actor, chainAbsenceSchema.parse(input));
}

export async function refreshNetwork(): Promise<{ refreshed: boolean }> {
  const actor = await requireCurator();
  return curation.refreshNetwork(actor);
}
