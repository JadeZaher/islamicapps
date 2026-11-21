'use server';
/** Public parallel filter for the comparative page: published parallels on public hadiths, at most 100. */
import type { ParallelRecord } from '@/db/queries/contracts';
import { searchPublicParallels } from '@/db/queries/comparative';
import { parallelFiltersSchema } from '../curation/schemas';

export async function searchParallels(filters?: unknown): Promise<ParallelRecord[]> {
  return searchPublicParallels(parallelFiltersSchema.parse(filters) ?? {});
}
