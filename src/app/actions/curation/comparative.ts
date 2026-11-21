'use server';
/** Curated comparative-study writes (section 9.2). Each: requireCurator(), zod, one query call. */
import * as comparative from '@/db/queries/comparative';
import { requireCurator } from '@/lib/auth/require-curator';
import {
  crossParallelCreateSchema,
  curationStatusSchema,
  idSchema,
  motifTagCreateSchema,
  parallelPatchSchema,
  religiousTraditionCreateSchema,
  religiousTraditionPatchSchema,
  sourceTextCreateSchema,
  sourceTextPatchSchema,
} from './schemas';

export async function createReligiousTradition(input: unknown): Promise<string> {
  const actor = await requireCurator();
  return comparative.createReligiousTradition(actor, religiousTraditionCreateSchema.parse(input));
}

export async function updateTradition(id: unknown, patch: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.updateReligiousTradition(actor, idSchema.parse(id), religiousTraditionPatchSchema.parse(patch));
}

/** Retires the faith; refused while live parallels or source texts reference it. */
export async function deleteTradition(id: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.retireReligiousTradition(actor, idSchema.parse(id));
}

/** Creates a source text in its faith (`tradition_id`, or `tradition_name` for legacy callers). */
export async function createSourceText(input: unknown): Promise<string> {
  const actor = await requireCurator();
  const { tradition_id: traditionId, ...rest } = sourceTextCreateSchema.parse(input);
  return comparative.createSourceText(actor, { ...rest, religious_tradition_id: traditionId });
}

/** Compatibility for the Neo4j-era two-step create: moves the source text to the given faith. */
export async function linkSourceTextToTradition(sourceTextId: unknown, traditionId: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.updateSourceText(actor, idSchema.parse(sourceTextId), { religious_tradition_id: idSchema.parse(traditionId) });
}

export async function updateSourceText(id: unknown, patch: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.updateSourceText(actor, idSchema.parse(id), sourceTextPatchSchema.parse(patch));
}

export async function deleteSourceText(id: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.retireSourceText(actor, idSchema.parse(id));
}

export async function createMotifTag(input: unknown): Promise<string> {
  const actor = await requireCurator();
  return comparative.createMotifTag(actor, motifTagCreateSchema.parse(input));
}

export async function deleteMotifTag(id: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.retireMotifTag(actor, idSchema.parse(id));
}

export async function tagHadith(hadithId: unknown, motifTagId: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.tagHadith(actor, idSchema.parse(hadithId), idSchema.parse(motifTagId));
}

/** Retires the tag link. */
export async function untagHadith(hadithId: unknown, motifTagId: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.untagHadith(actor, idSchema.parse(hadithId), idSchema.parse(motifTagId));
}

export async function tagParallel(parallelId: unknown, motifTagId: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.tagParallel(actor, idSchema.parse(parallelId), idSchema.parse(motifTagId));
}

export async function createCrossParallel(input: unknown): Promise<string> {
  const actor = await requireCurator();
  return comparative.createCrossParallel(actor, crossParallelCreateSchema.parse(input));
}

/** Typed allowlist update; `status` changes only through publishParallel. */
export async function updateParallel(id: unknown, patch: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.updateParallel(actor, idSchema.parse(id), parallelPatchSchema.parse(patch));
}

export async function deleteParallel(id: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.retireParallel(actor, idSchema.parse(id));
}

/** `published` requires the hadith to be in public_hadiths. */
export async function publishParallel(id: unknown, status: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.publishParallel(actor, idSchema.parse(id), curationStatusSchema.parse(status));
}

export async function linkNarratorToTradition(narratorId: unknown, traditionId: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.linkNarratorToTradition(actor, idSchema.parse(narratorId), idSchema.parse(traditionId));
}

export async function unlinkNarratorFromTradition(narratorId: unknown, traditionId: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.unlinkNarratorFromTradition(actor, idSchema.parse(narratorId), idSchema.parse(traditionId));
}

export async function linkLocationToTradition(locationId: unknown, traditionId: unknown): Promise<void> {
  const actor = await requireCurator();
  await comparative.linkLocationToTradition(actor, idSchema.parse(locationId), idSchema.parse(traditionId));
}
