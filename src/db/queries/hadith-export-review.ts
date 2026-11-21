/** Curator CSV export of live hadiths (reviewer mode, base tables). Consumed only by /api/export/hadiths. */
import 'server-only';
import { sql, type SQL } from 'drizzle-orm';
import { filterPredicates } from './hadith';
import { andAll, rows, withReadRetry } from './sql-helpers';

/** Selectable columns: the request key mapped to a trusted SQL expression over aliases h, t, col, tr. */
const FIELD_EXPRESSIONS: Record<string, SQL> = {
  id: sql`h.id`,
  chapter: sql`h.chapter_title`,
  category: sql`h.category`,
  source: sql`coalesce(h.source_display_label, col.name)`,
  hadith_no: sql`h.hadith_no`,
  tradition: sql`t.code`,
  text_en: sql`tr.text`,
  text_ar: sql`h.text_ar`,
  title: sql`coalesce(h.chapter_title, h.category)`,
  primary_topic: sql`h.category`,
  text_english: sql`tr.text`,
  text_arabic: sql`h.text_ar`,
};

/** Optional related-record columns: edge key to its output columns and correlated subqueries over `h`. */
const EDGE_EXPRESSIONS: Record<string, Array<[column: string, expression: SQL]>> = {
  narrators: [
    [
      'narrators',
      sql`(select string_agg(coalesce(n.name_en, n.name_ar), '; ' order by cm.position)
           from chain_mentions cm join narrators n on n.id = cm.narrator_id
           where cm.hadith_id = h.id and cm.retired_at is null and n.retired_at is null
             and cm.resolution in ('exact_registry', 'human_verified', 'derived_relation_verified'))`,
    ],
  ],
  commentaries: [
    [
      'commentaries',
      sql`(select string_agg('[' || coalesce(c.author, '') || ' - ' || coalesce(c.source_work, '') || '] ' || c.text, ' | ' order by c.created_at)
           from commentary_hadiths ch join commentaries c on c.id = ch.commentary_id
           where ch.hadith_id = h.id and ch.retired_at is null and c.retired_at is null)`,
    ],
  ],
  variations: [
    ['variation_texts_english', sql`coalesce(tr.matn_text, tr.text)`],
    ['variation_texts_arabic', sql`coalesce(h.matn_ar, h.text_ar)`],
  ],
  school: [['schools', sql`h.school`]],
};

export const EXPORT_FIELD_KEYS = Object.keys(FIELD_EXPRESSIONS);
export const EXPORT_EDGE_KEYS = Object.keys(EDGE_EXPRESSIONS);

/** Hard ceiling so one request cannot walk an unbounded table. */
export const EXPORT_ROW_LIMIT = 100_000;
const BATCH_SIZE = 500;

export interface HadithExportRequest {
  fields: string[];
  edges: string[];
  tradition?: string;
  source?: string;
}

function selectedColumns(request: HadithExportRequest): Array<[string, SQL]> {
  return [
    ...request.fields.filter((field) => field in FIELD_EXPRESSIONS).map((field): [string, SQL] => [field, FIELD_EXPRESSIONS[field]]),
    ...request.edges.flatMap((edge) => EDGE_EXPRESSIONS[edge] ?? []),
  ];
}

/** Output column names, in order, for a request (unknown keys are dropped). */
export function exportColumns(request: HadithExportRequest): string[] {
  return selectedColumns(request).map(([column]) => column);
}

/** Yields batches of rows (column name to text) in the hadith ordering contract, at most EXPORT_ROW_LIMIT rows. */
export async function* exportHadithBatches(request: HadithExportRequest): AsyncGenerator<Record<string, string>[]> {
  const predicates = filterPredicates({ tradition: request.tradition, source: request.source });
  const selected = selectedColumns(request);
  if (predicates === null || selected.length === 0) return;
  const selectList = sql.join(
    selected.map(([column, expression]) => sql`${expression} as ${sql.identifier(column)}`),
    sql`, `,
  );

  for (let offset = 0; offset < EXPORT_ROW_LIMIT; offset += BATCH_SIZE) {
    const batch = await withReadRetry(() =>
      rows<Record<string, unknown>>(sql`
        with page as (
          select h.id, h.collection_sort_key, h.hadith_no_int
          from hadiths h
          join traditions t on t.id = h.tradition_id
          join collections col on col.id = h.collection_id
          where ${andAll([sql`h.retired_at is null`, ...predicates])}
          order by h.collection_sort_key, h.hadith_no_int nulls last, h.id
          limit ${BATCH_SIZE} offset ${offset}
        )
        select ${selectList}
        from page p
        join hadiths h on h.id = p.id
        join traditions t on t.id = h.tradition_id
        join collections col on col.id = h.collection_id
        left join lateral (
          select x.text, x.matn_text from translations x
          where x.hadith_id = h.id and x.language = 'en' and x.retired_at is null
          limit 1
        ) tr on true
        order by p.collection_sort_key, p.hadith_no_int nulls last, p.id`),
    );
    if (batch.length === 0) return;
    yield batch.map((row) => Object.fromEntries(selected.map(([column]) => [column, row[column] == null ? '' : String(row[column])])));
    if (batch.length < BATCH_SIZE) return;
  }
}
