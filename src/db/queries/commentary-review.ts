/** Reviewer-mode commentary reads (base tables, every status). Curator callers only. */
import 'server-only';
import { sql } from 'drizzle-orm';
import { commentaryObject } from './commentary';
import type { CommentaryRecord, Paginated } from './contracts';
import { mapCommentary } from './mappers';
import { clampPage, oneRow, paginated, type PageRequest } from './sql-helpers';

/** Admin list, newest first; every status. Pages commentaries first, then attaches links (section 8). */
export async function listCommentaries(request?: PageRequest, type?: string): Promise<Paginated<CommentaryRecord>> {
  const window = clampPage(request, Number.MAX_SAFE_INTEGER);
  const where = type ? sql`c.retired_at is null and c.type = ${type}` : sql`c.retired_at is null`;
  const row = await oneRow<{ total: number; items: Record<string, unknown>[] }>(sql`
    select (select count(*)::int from commentaries c where ${where}) as total,
           coalesce((select jsonb_agg(${commentaryObject(sql`hadiths`)} order by c.created_at desc, c.id)
                     from (select * from commentaries c where ${where}
                           order by c.created_at desc, c.id limit ${window.limit} offset ${window.offset}) c), '[]'::jsonb) as items
  `);
  return paginated((row?.items ?? []).map(mapCommentary), row?.total ?? 0, window);
}

