'use server';
/** Public hadith search for client components; published rows only, page size capped. */
import { z } from 'zod';
import type { HadithListItem, Paginated } from '@/db/queries/contracts';
import { searchVisibleHadiths } from '@/db/queries/hadith';
import { requestVisibility } from '@/lib/auth/visibility';
import { MAX_PAGE_SIZE } from '@/db/queries/sql-helpers';

const filtersSchema = z
  .object({
    tradition: z.string().max(50).optional(),
    school: z.string().max(50).optional(),
    source: z.string().max(200).optional(),
    chapter: z.string().max(300).optional(),
  })
  .optional();

const pageSchema = z
  .object({ page: z.number().int().min(1).optional(), pageSize: z.number().int().min(1).max(MAX_PAGE_SIZE).optional() })
  .optional();

export async function searchHadiths(term: unknown, filters?: unknown, pagination?: unknown): Promise<Paginated<HadithListItem>> {
  const parsedFilters = filtersSchema.parse(filters) ?? {};
  return searchVisibleHadiths(
    z.string().max(200).parse(term ?? ''),
    {
      tradition: parsedFilters.tradition ?? parsedFilters.school,
      source: parsedFilters.source,
      chapter: parsedFilters.chapter,
    },
    pageSchema.parse(pagination),
    await requestVisibility(),
  );
}
