'use server';
/** Curated history writes (events, epochs). Each: requireCurator(), zod, one query call. */
import { z } from 'zod';
import * as epoch from '@/db/queries/epoch';
import * as history from '@/db/queries/history';
import { requireCurator } from '@/lib/auth/require-curator';
import { attempt, type ActionResult } from './result';
import { historicalEventCreateSchema, historicalEventPatchSchema, idSchema } from './schemas';

const blankToNull = (value: unknown) => (typeof value === 'string' && value.trim() === '' ? null : value);
const epochYear = z.preprocess(
  (value) => (value === '' || value === null ? null : typeof value === 'string' ? Number(value) : value),
  z.number().int().min(-200).max(1500).nullable(),
);
const epochFields = {
  name: z.string().trim().min(1).max(300),
  name_arabic: z.preprocess(blankToNull, z.string().trim().max(300).nullable()),
  start_year_hijri: epochYear,
  start_year_hijri_latest: epochYear,
  end_year_hijri: epochYear,
  end_year_hijri_latest: epochYear,
  boundary_note: z.preprocess(blankToNull, z.string().trim().max(2000).nullable()),
  overview: z.preprocess(blankToNull, z.string().trim().max(5000).nullable()),
  verification_status: z.enum(['unverified', 'unverified_seed', 'human_verified', 'source_verified']),
  publication_ready: z.boolean(),
  citation_id: z.preprocess(blankToNull, z.string().trim().max(200).nullable()),
};
const epochPatchSchema = z.object(epochFields).partial();

/** Edits an epoch (review state, citation, years, wording). The publish gate is a check constraint. */
export async function updateEpoch(id: unknown, patch: unknown): Promise<ActionResult<void>> {
  return attempt(async () => {
    const actor = await requireCurator();
    await epoch.updateEpoch(actor, idSchema.parse(id), epochPatchSchema.parse(patch));
  });
}

/** Retires the epoch (nothing is hard-deleted); refused while a live sub-period points at it. */
export async function retireEpoch(id: unknown): Promise<ActionResult<void>> {
  return attempt(async () => {
    const actor = await requireCurator();
    await epoch.retireEpoch(actor, idSchema.parse(id));
  });
}

export async function createHistoricalEvent(input: unknown): Promise<ActionResult<string>> {
  return attempt(async () => {
    const actor = await requireCurator();
    return history.createHistoricalEvent(actor, historicalEventCreateSchema.parse(input));
  });
}

export async function updateHistoricalEvent(id: unknown, patch: unknown): Promise<ActionResult<void>> {
  return attempt(async () => {
    const actor = await requireCurator();
    await history.updateHistoricalEvent(actor, idSchema.parse(id), historicalEventPatchSchema.parse(patch));
  });
}

/** Retires the event (nothing is hard-deleted). */
export async function deleteHistoricalEvent(id: unknown): Promise<ActionResult<void>> {
  return attempt(async () => {
    const actor = await requireCurator();
    await history.retireHistoricalEvent(actor, idSchema.parse(id));
  });
}
