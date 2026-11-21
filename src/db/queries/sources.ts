/** What each source accounts for in the loaded data: works and reports per database source, claims per basis. */
import 'server-only';
import { sql } from 'drizzle-orm';
import { rows } from './sql-helpers';

export interface LoadedWork {
  sourceSlug: string;
  sourceWorkId: string;
  slug: string;
  name: string;
  tradition: string;
  reports: number;
}

export interface SourceAccounting {
  works: LoadedWork[];
  /** Live identity candidates per basis. */
  candidatesByBasis: Record<string, number>;
  narrators: number;
}

/** Counts only (no text): every live work with its source and report count, candidate counts, narrator count. */
export async function getSourceAccounting(): Promise<SourceAccounting> {
  const [works, candidates, narrators] = await Promise.all([
    rows<Record<string, unknown>>(sql`
      select s.slug as source_slug, col.source_work_id, col.slug, col.name, t.code as tradition,
             (select count(*)::int from hadiths h where h.collection_id = col.id and h.retired_at is null) as reports
      from collections col
      join sources s on s.id = col.source_id
      join traditions t on t.id = col.tradition_id
      where col.retired_at is null
      order by col.sort_key`),
    rows<{ basis: string; total: number }>(sql`
      select basis::text as basis, count(*)::int as total from chain_mention_candidates where retired_at is null group by basis`),
    rows<{ total: number }>(sql`select count(*)::int as total from narrators where retired_at is null`),
  ]);
  return {
    works: works.map((work) => ({
      sourceSlug: String(work.source_slug),
      sourceWorkId: String(work.source_work_id),
      slug: String(work.slug),
      name: String(work.name),
      tradition: String(work.tradition),
      reports: Number(work.reports),
    })),
    candidatesByBasis: Object.fromEntries(candidates.map((row) => [row.basis, Number(row.total)])),
    narrators: Number(narrators[0]?.total ?? 0),
  };
}
