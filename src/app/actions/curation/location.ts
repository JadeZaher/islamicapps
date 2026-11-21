'use server';
/** Curated location writes. Each: requireCurator(), zod, one query call. */
import * as location from '@/db/queries/location';
import { requireCurator } from '@/lib/auth/require-curator';
import { idSchema, locationCreateSchema, locationPatchSchema } from './schemas';

export async function createLocation(input: unknown): Promise<string> {
  const actor = await requireCurator();
  return location.createLocation(actor, locationCreateSchema.parse(input));
}

export async function updateLocation(id: unknown, patch: unknown): Promise<void> {
  const actor = await requireCurator();
  await location.updateLocation(actor, idSchema.parse(id), locationPatchSchema.parse(patch));
}

/** Retires the location; refused while a live event refers to it. */
export async function deleteLocation(id: unknown): Promise<void> {
  const actor = await requireCurator();
  await location.retireLocation(actor, idSchema.parse(id));
}
