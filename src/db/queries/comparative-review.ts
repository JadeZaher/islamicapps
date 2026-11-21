/** Reviewer-mode parallels: every live parallel, any status, on any live hadith. Curator callers only. */
import 'server-only';
import { sql } from 'drizzle-orm';
import { pageParallels } from './comparative';
import type { Paginated, ParallelRecord } from './contracts';
import type { PageRequest } from './sql-helpers';

export async function listParallelsForReview(request?: PageRequest): Promise<Paginated<ParallelRecord>> {
  return pageParallels(sql`hadiths`, sql`p.retired_at is null and h.retired_at is null`, sql`p.hadith_excerpt_en`, request);
}
