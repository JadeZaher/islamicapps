/** Reviewer-mode hadith reads on the live base tables (rule 9: base tables only in *-review.ts). Curator callers only. */
import 'server-only';
import { sql } from 'drizzle-orm';
import type { HadithDetail, HadithListItem, Paginated } from './contracts';
import {
  hadithDetailStatement,
  listHadithPage,
  mapHadithDetail,
  type HadithFilters,
  type HadithRelations,
} from './hadith';
import { clampPage, oneRow, type PageRequest } from './sql-helpers';

/** Live hadiths and translations, whatever their publication facets. */
const REVIEW_RELATIONS: HadithRelations = {
  hadiths: sql`hadiths`,
  translations: sql`translations`,
  liveHadith: sql`h.retired_at is null`,
  liveTranslation: sql`x.retired_at is null`,
};

/** Admin hadith browse and search, including rows the public views hide. */
export async function searchHadithsForReview(
  term: string | undefined,
  filters: HadithFilters = {},
  request?: PageRequest,
): Promise<Paginated<HadithListItem>> {
  // Admin paging is not capped at the public page limit.
  return listHadithPage(REVIEW_RELATIONS, filters, term, clampPage(request, Number.MAX_SAFE_INTEGER));
}

/** Reviewer-mode detail: any live hadith, with its facets. */
export async function getHadithForReview(hadithId: string): Promise<HadithDetail | null> {
  const row = await oneRow<{ detail: Record<string, unknown> }>(hadithDetailStatement(REVIEW_RELATIONS, hadithId));
  return row ? mapHadithDetail(row.detail) : null;
}
