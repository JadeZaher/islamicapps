'use server';
/** Curator typeahead over every live hadith (reviewer mode), for linking commentaries and parallels. */
import type { HadithListItem, Paginated } from '@/db/queries/contracts';
import { searchHadithsForReview } from '@/db/queries/hadith-review';
import { requireCurator } from '@/lib/auth/require-curator';
import { attempt, type ActionResult } from './result';
import { searchTermSchema } from './schemas';

const TYPEAHEAD_PAGE_SIZE = 20;

export async function searchHadithsForCuration(term: unknown): Promise<ActionResult<Paginated<HadithListItem>>> {
  return attempt(async () => {
    await requireCurator();
    return searchHadithsForReview(searchTermSchema.parse(term), {}, { page: 1, pageSize: TYPEAHEAD_PAGE_SIZE });
  });
}
