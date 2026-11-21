'use server';
/** Curated commentary writes and the publish gate (section 9.3). Each: requireCurator(), zod, one query call. */
import * as commentary from '@/db/queries/commentary';
import { requireCurator } from '@/lib/auth/require-curator';
import { commentaryCreateSchema, commentaryPatchSchema, curationStatusSchema, idSchema } from './schemas';

/** Creates a `proposed` commentary with its hadith and narrator links. */
export async function createCommentary(input: unknown): Promise<string> {
  const actor = await requireCurator();
  return commentary.createCommentary(actor, commentaryCreateSchema.parse(input));
}

export async function updateCommentary(id: unknown, patch: unknown): Promise<void> {
  const actor = await requireCurator();
  await commentary.updateCommentary(actor, idSchema.parse(id), commentaryPatchSchema.parse(patch));
}

/** Retires the commentary and its links (nothing is hard-deleted). */
export async function deleteCommentary(id: unknown): Promise<void> {
  const actor = await requireCurator();
  await commentary.retireCommentary(actor, idSchema.parse(id));
}

/** `published` requires a live, reviewed citation. */
export async function publishCommentary(id: unknown, status: unknown): Promise<void> {
  const actor = await requireCurator();
  await commentary.publishCommentary(actor, idSchema.parse(id), curationStatusSchema.parse(status));
}
