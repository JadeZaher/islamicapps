'use server';
/** Curated historical-event writes. Each: requireCurator(), zod, one query call. */
import * as history from '@/db/queries/history';
import { requireCurator } from '@/lib/auth/require-curator';
import { historicalEventCreateSchema, historicalEventPatchSchema, idSchema } from './schemas';

export async function createHistoricalEvent(input: unknown): Promise<string> {
  const actor = await requireCurator();
  return history.createHistoricalEvent(actor, historicalEventCreateSchema.parse(input));
}

export async function updateHistoricalEvent(id: unknown, patch: unknown): Promise<void> {
  const actor = await requireCurator();
  await history.updateHistoricalEvent(actor, idSchema.parse(id), historicalEventPatchSchema.parse(patch));
}

/** Retires the event (nothing is hard-deleted). */
export async function deleteHistoricalEvent(id: unknown): Promise<void> {
  const actor = await requireCurator();
  await history.retireHistoricalEvent(actor, idSchema.parse(id));
}
