/** Reading in order: works by tradition, books, chapters, reports in source order, a report's place in its work. */
import 'server-only';
import { sql, type SQL } from 'drizzle-orm';
import { bookHeading, idNamespace, reportNumber, reportReference, type IdNamespace, type ReferenceFields } from '@/lib/citation/reference';
import { text } from './mappers';
import { clampPage, HADITH_TRADITION_CODES, oneRow, paginated, rows, type HadithTraditionCode, type PageRequest, type Paginated } from './sql-helpers';
import { hadithRelationsFor, type ReadVisibility } from './visibility';

/**
 * Source order of a report within its work, on alias `h` (see AGENTS.md §Source order). Comparable as a bigint[]
 * plus `id collate "C"` as the tie-break. The one place the order is defined; swap for a loaded column when one exists.
 */
const SOURCE_ORDER = sql`(case
  when h.id like 'hadith:k6:%' and h.source_record_id ~ '^[0-9]+$'
    then array[h.source_record_id::bigint]
  when h.source_record_id ~ '^provider-file:[0-9]+[|]hadith:[0-9]+$'
    then (regexp_match(h.source_record_id, '^provider-file:([0-9]+)[|]hadith:([0-9]+)$'))::bigint[]
  when h.id like 'hadith:openiti:%' and h.provider_hadith_id ~ '_[0-9]+[a-z]?$'
    then array[(regexp_match(h.provider_hadith_id, '_([0-9]+)[a-z]?$'))[1]::bigint,
               case when h.provider_hadith_id ~ '[a-z]$' then 1 else 0 end]
  else array[coalesce(h.hadith_no_int::bigint, 9223372036854775807::bigint)]
end)`;

/** The report's own number as text, on alias `h`: Thaqalayn's from its URL (category/chapter/hadith), else hadith_no. */
const NUMBER_KEY = sql`(case
  when h.id like 'hadith:thaqalayn:%' then substring(h.url from '/hadith/[0-9]+/([0-9]+/[0-9]+/[0-9]+)/?$')
  when btrim(h.hadith_no) ~ '^0*[1-9][0-9]*$' then ltrim(btrim(h.hadith_no), '0')
end)`;

/** Reports per browse page. */
export const BROWSE_PAGE_SIZE = 50;
const EXCERPT_CHARACTERS = 320;

export interface WorkSummary {
  slug: string;
  name: string;
  sourceWorkId: string;
  tradition: HadithTraditionCode;
  reportCount: number;
  bookCount: number;
  chapterCount: number;
}

export interface TraditionWorks {
  tradition: HadithTraditionCode;
  works: WorkSummary[];
}

/** What structure this copy of a work really carries; drives the honest notes on browse pages. */
export interface WorkStructure {
  namespace: IdNamespace;
  reports: number;
  withBook: number;
  withChapter: number;
  /** Reports with a positive number of their own (Thaqalayn: from the provider URL). */
  withNumber: number;
  distinctNumbers: number;
}

export interface BookSummary {
  number: string;
  label: string;
  title: string | null;
  reportCount: number;
  chapterCount: number;
}

export interface ChapterSummary {
  key: string;
  number: string | null;
  name: string | null;
  /** The kitab the chapter sits in, when the source names one distinct from the chapter. */
  category: string | null;
  reportCount: number;
}

export interface WorkHeader {
  slug: string;
  name: string;
  sourceWorkId: string;
  tradition: HadithTraditionCode;
  sourceSlug: string;
  sourceName: string;
}

export interface WorkOutline {
  work: WorkHeader;
  structure: WorkStructure;
  books: BookSummary[];
  reportsWithoutBook: number;
}

export interface BookOutline {
  work: WorkHeader;
  namespace: IdNamespace;
  book: BookSummary;
  chapters: ChapterSummary[];
  reportsWithoutChapter: number;
}

export interface ReportListItem {
  id: string;
  number: string | null;
  reference: string;
  chapterName: string | null;
  arabicExcerpt: string | null;
  englishExcerpt: string | null;
}

export interface ReportNeighbour {
  id: string;
  reference: string;
}

export interface ReportContext {
  id: string;
  tradition: HadithTraditionCode;
  work: WorkHeader & { rightsCitation: string | null };
  book: (BookSummary & { name: string | null; volume: string | null }) | null;
  chapter: { key: string; number: string | null; name: string | null } | null;
  number: string | null;
  reference: string;
  url: string | null;
  /** False when another report of the work records the same provider URL (it cannot then identify this report). */
  urlUnique: boolean;
  previous: ReportNeighbour | null;
  next: ReportNeighbour | null;
  position: number;
  total: number;
  /** Provenance of the English the page shows; null when no English is shown. */
  english: { state: string | null; translator: string | null; model: string | null } | null;
}

type Row = Record<string, unknown>;

const count = (value: unknown): number => Number(value ?? 0);

function referenceFields(row: Row): ReferenceFields {
  return {
    id: String(row.id),
    hadithNo: text(row.hadith_no),
    url: text(row.url),
    volume: text(row.volume),
    pageRef: text(row.page_ref),
    bookNumber: text(row.book_number),
  };
}

/** JSON of the reference columns for alias `h` with book `b`. */
const REFERENCE_JSON = sql`'id', h.id, 'hadith_no', h.hadith_no, 'url', h.url, 'volume', h.volume,
  'page_ref', h.page_ref, 'book_number', b.number`;

function excerpt(value: unknown): string | null {
  const flat = (text(value) ?? '').replace(/\s+/g, ' ');
  if (!flat) return null;
  return flat.length > EXCERPT_CHARACTERS ? `${flat.slice(0, EXCERPT_CHARACTERS).trimEnd()}…` : flat;
}

function mapWorkHeader(work: Row): WorkHeader {
  return {
    slug: String(work.slug),
    name: String(work.name),
    sourceWorkId: String(work.source_work_id),
    tradition: work.tradition as HadithTraditionCode,
    sourceSlug: String(work.source_slug),
    sourceName: String(work.source_name),
  };
}

function mapBook(namespace: IdNamespace, book: Row): BookSummary {
  const number = String(book.number);
  const heading = bookHeading(namespace, { number, name: text(book.name), volume: text(book.volume) });
  return { number, ...heading, reportCount: count(book.reports), chapterCount: count(book.chapters) };
}

/** Work header columns for alias `col` joined to `t` (tradition) and `s` (source). */
const WORK_HEADER_JSON = sql`json_build_object('slug', col.slug, 'name', col.name, 'source_work_id', col.source_work_id,
  'tradition', t.code, 'source_slug', s.slug, 'source_name', s.name)`;

/** The four traditions in alphabetical order (none is the default), each with its visible works in registry order. */
export async function listWorksByTradition(visibility: ReadVisibility): Promise<TraditionWorks[]> {
  const relations = hadithRelationsFor(visibility);
  const found = await rows<Row>(sql`
    select t.code as tradition, col.slug, col.name, col.source_work_id,
           count(*)::int as reports, count(distinct h.book_id)::int as books, count(distinct h.chapter_id)::int as chapters
    from ${relations.hadiths} h
    join collections col on col.id = h.collection_id and col.retired_at is null
    join traditions t on t.id = col.tradition_id
    where ${relations.liveHadith}
    group by t.code, col.slug, col.name, col.source_work_id, col.sort_key
    order by col.sort_key`);
  return [...HADITH_TRADITION_CODES]
    .sort((a, b) => a.localeCompare(b))
    .map((tradition) => ({
      tradition,
      works: found
        .filter((row) => row.tradition === tradition)
        .map((row) => ({
          slug: String(row.slug),
          name: String(row.name),
          sourceWorkId: String(row.source_work_id),
          tradition,
          reportCount: count(row.reports),
          bookCount: count(row.books),
          chapterCount: count(row.chapters),
        })),
    }));
}

/** A work's header, structure counts and books with report and chapter counts; null when nothing in it is visible. */
export async function getWorkOutline(slug: string, visibility: ReadVisibility): Promise<WorkOutline | null> {
  const relations = hadithRelationsFor(visibility);
  const row = await oneRow<{ outline: Row }>(sql`
    with work_rows as materialized (
      select h.id, h.book_id, h.chapter_id, ${NUMBER_KEY} as number_key, ${SOURCE_ORDER} as ord
      from ${relations.hadiths} h
      join collections col on col.id = h.collection_id
      where col.slug = ${slug} and ${relations.liveHadith}
    )
    select json_build_object(
      'work', ${WORK_HEADER_JSON},
      'sample_id', (select min(w.id) from work_rows w),
      'reports', (select count(*)::int from work_rows),
      'with_book', (select count(w.book_id)::int from work_rows w),
      'with_chapter', (select count(w.chapter_id)::int from work_rows w),
      'with_number', (select count(w.number_key)::int from work_rows w),
      'distinct_numbers', (select count(distinct w.number_key)::int from work_rows w),
      'books', coalesce((
        select json_agg(json_build_object('number', b.number, 'name', b.name, 'volume', b.volume,
                                          'reports', g.reports, 'chapters', g.chapters) order by g.first_ord)
        from (select w.book_id, count(*)::int as reports, count(distinct w.chapter_id)::int as chapters, min(w.ord) as first_ord
              from work_rows w where w.book_id is not null group by w.book_id) g
        join books b on b.id = g.book_id
      ), '[]'::json)
    ) as outline
    from collections col
    join traditions t on t.id = col.tradition_id
    join sources s on s.id = col.source_id
    where col.slug = ${slug} and col.retired_at is null`);
  const outline = row?.outline;
  if (!outline || count(outline.reports) === 0) return null;
  const namespace = idNamespace(String(outline.sample_id));
  const books = ((outline.books as Row[]) ?? []).map((book) => mapBook(namespace, book));
  return {
    work: mapWorkHeader(outline.work as Row),
    structure: {
      namespace,
      reports: count(outline.reports),
      withBook: count(outline.with_book),
      withChapter: count(outline.with_chapter),
      withNumber: count(outline.with_number),
      distinctNumbers: count(outline.distinct_numbers),
    },
    books,
    reportsWithoutBook: count(outline.reports) - count(outline.with_book),
  };
}

/** A book's chapters in source order with report counts; null when the book is unknown or has no visible report. */
export async function getBookOutline(slug: string, bookNumber: string, visibility: ReadVisibility): Promise<BookOutline | null> {
  const relations = hadithRelationsFor(visibility);
  const row = await oneRow<{ outline: Row }>(sql`
    with book_rows as materialized (
      select h.id, h.chapter_id, h.category, ${SOURCE_ORDER} as ord
      from ${relations.hadiths} h
      join collections col on col.id = h.collection_id and col.slug = ${slug}
      join books b on b.id = h.book_id and b.number = ${bookNumber}
      where ${relations.liveHadith}
    )
    select json_build_object(
      'work', ${WORK_HEADER_JSON},
      'sample_id', (select min(r.id) from book_rows r),
      'book', (select json_build_object('number', b.number, 'name', b.name, 'volume', b.volume,
                                        'reports', (select count(*)::int from book_rows),
                                        'chapters', (select count(distinct r.chapter_id)::int from book_rows r))
               from books b where b.collection_id = col.id and b.number = ${bookNumber} limit 1),
      'without_chapter', (select count(*)::int from book_rows r where r.chapter_id is null),
      'chapters', coalesce((
        select json_agg(json_build_object('id', c.id, 'number', c.number, 'name', c.name, 'category', g.category,
                                          'reports', g.reports) order by g.first_ord)
        from (select r.chapter_id, count(*)::int as reports, min(r.ord) as first_ord, min(r.category) as category
              from book_rows r where r.chapter_id is not null group by r.chapter_id) g
        join chapters c on c.id = g.chapter_id
      ), '[]'::json)
    ) as outline
    from collections col
    join traditions t on t.id = col.tradition_id
    join sources s on s.id = col.source_id
    where col.slug = ${slug} and col.retired_at is null`);
  const outline = row?.outline;
  if (!outline || !outline.book || !outline.sample_id) return null;
  const namespace = idNamespace(String(outline.sample_id));
  return {
    work: mapWorkHeader(outline.work as Row),
    namespace,
    book: mapBook(namespace, outline.book as Row),
    reportsWithoutChapter: count(outline.without_chapter),
    chapters: ((outline.chapters as Row[]) ?? []).map((chapter) => {
      const name = text(chapter.name);
      const category = text(chapter.category);
      return {
        key: String(chapter.id).replace(/^chapter:/, ''),
        number: text(chapter.number),
        name,
        category: category && category !== name ? category : null,
        reportCount: count(chapter.reports),
      };
    }),
  };
}

export interface ReportScope {
  workSlug: string;
  /** Restrict to one book (by its number within the work). */
  bookNumber?: string;
  /** Restrict to one chapter (its ID without the `chapter:` prefix). */
  chapterKey?: string;
}

export interface ReportPage extends Paginated<ReportListItem> {
  /** Name of the chapter when the scope is a chapter and it is visible. */
  chapterName: string | null;
  chapterNumber: string | null;
}

/** One page of reports in source order within a work, book or chapter (one statement, exact total). */
export async function listReportsInOrder(scope: ReportScope, request: PageRequest | undefined, visibility: ReadVisibility): Promise<ReportPage> {
  const relations = hadithRelationsFor(visibility);
  const window = clampPage({ page: request?.page, pageSize: request?.pageSize ?? BROWSE_PAGE_SIZE }, Number.MAX_SAFE_INTEGER);
  const predicates: SQL[] = [sql`col.slug = ${scope.workSlug}`, relations.liveHadith];
  if (scope.bookNumber !== undefined) {
    predicates.push(sql`h.book_id in (select bk.id from books bk where bk.collection_id = col.id and bk.number = ${scope.bookNumber})`);
  }
  if (scope.chapterKey !== undefined) predicates.push(sql`h.chapter_id = ${`chapter:${scope.chapterKey}`}`);
  const row = await oneRow<{ total: number; items: Row[]; chapter: Row | null }>(sql`
    with scoped as materialized (
      select h.id, ${SOURCE_ORDER} as ord
      from ${relations.hadiths} h
      join collections col on col.id = h.collection_id
      where ${sql.join(predicates, sql` and `)}
    ),
    page as (
      select s.id, s.ord from scoped s order by s.ord, s.id collate "C" limit ${window.limit} offset ${window.offset}
    )
    select
      (select count(*)::int from scoped) as total,
      ${scope.chapterKey !== undefined
        ? sql`(select json_build_object('name', c.name, 'number', c.number) from chapters c
               where c.id = ${`chapter:${scope.chapterKey}`} and exists (select 1 from scoped))`
        : sql`null::json`} as chapter,
      coalesce((
        select json_agg(json_build_object(${REFERENCE_JSON}, 'chapter_name', c.name,
                                          'text_ar', coalesce(h.matn_ar, h.text_ar), 'text_en', tr.text)
                        order by p.ord, p.id collate "C")
        from page p
        join ${relations.hadiths} h on h.id = p.id
        left join books b on b.id = h.book_id
        left join chapters c on c.id = h.chapter_id
        left join lateral (
          select x.text from ${relations.translations} x
          where x.hadith_id = h.id and x.language = 'en' and ${relations.liveTranslation}
          limit 1
        ) tr on true
      ), '[]'::json) as items`);
  const items = (row?.items ?? []).map((item): ReportListItem => {
    const fields = referenceFields(item);
    return {
      id: fields.id,
      number: reportNumber(fields),
      reference: reportReference(fields),
      chapterName: text(item.chapter_name),
      arabicExcerpt: excerpt(item.text_ar),
      englishExcerpt: excerpt(item.text_en),
    };
  });
  return {
    ...paginated(items, row?.total ?? 0, window),
    chapterName: text(row?.chapter?.name),
    chapterNumber: text(row?.chapter?.number),
  };
}

/** A report's place in its work: tradition, work, book, chapter, its reference, and the previous and next report. */
export async function getReportContext(hadithId: string, visibility: ReadVisibility): Promise<ReportContext | null> {
  const relations = hadithRelationsFor(visibility);
  const row = await oneRow<{ context: Row }>(sql`
    with current_report as (
      select h.*, ${SOURCE_ORDER} as ord from ${relations.hadiths} h where h.id = ${hadithId} and ${relations.liveHadith}
    ),
    work_rows as materialized (
      select h.id, h.hadith_no, h.url, h.volume, h.page_ref, h.book_id, ${SOURCE_ORDER} as ord
      from ${relations.hadiths} h
      where h.collection_id = (select collection_id from current_report) and ${relations.liveHadith}
    )
    select json_build_object(
      ${REFERENCE_JSON},
      'tradition', t.code,
      'work', json_build_object('slug', col.slug, 'name', col.name, 'source_work_id', col.source_work_id,
                                'tradition', t.code, 'source_slug', s.slug, 'source_name', s.name,
                                'rights_citation', cr.citation),
      'book', case when b.id is null then null else json_build_object(
                'number', b.number, 'name', b.name, 'volume', b.volume,
                'reports', (select count(*)::int from work_rows w where w.book_id = b.id)) end,
      'chapter', case when c.id is null then null else json_build_object('id', c.id, 'number', c.number, 'name', c.name) end,
      'previous', (select json_build_object('id', w.id, 'hadith_no', w.hadith_no, 'url', w.url, 'volume', w.volume,
                                            'page_ref', w.page_ref, 'book_number', wb.number)
                   from work_rows w left join books wb on wb.id = w.book_id
                   where (w.ord, w.id collate "C") < (h.ord, h.id collate "C")
                   order by w.ord desc, w.id collate "C" desc limit 1),
      'next', (select json_build_object('id', w.id, 'hadith_no', w.hadith_no, 'url', w.url, 'volume', w.volume,
                                        'page_ref', w.page_ref, 'book_number', wb.number)
               from work_rows w left join books wb on wb.id = w.book_id
               where (w.ord, w.id collate "C") > (h.ord, h.id collate "C")
               order by w.ord, w.id collate "C" limit 1),
      'position', (select count(*)::int + 1 from work_rows w where (w.ord, w.id collate "C") < (h.ord, h.id collate "C")),
      'total', (select count(*)::int from work_rows),
      'url_unique', h.url is not null and not exists (select 1 from work_rows w where w.url = h.url and w.id <> h.id),
      'english', (select json_build_object('state', x.state, 'translator', x.translator, 'model', x.model) from ${relations.translations} x
                  where x.hadith_id = h.id and x.language = 'en' and ${relations.liveTranslation} limit 1)
    ) as context
    from current_report h
    join collections col on col.id = h.collection_id
    join traditions t on t.id = h.tradition_id
    join sources s on s.id = col.source_id
    left join collection_rights cr on cr.collection_id = col.id and cr.retired_at is null
    left join books b on b.id = h.book_id
    left join chapters c on c.id = h.chapter_id`);
  const context = row?.context;
  if (!context) return null;
  const fields = referenceFields(context);
  const namespace = idNamespace(fields.id);
  const neighbour = (value: unknown): ReportNeighbour | null => {
    if (!value) return null;
    const neighbourFields = referenceFields(value as Row);
    return { id: neighbourFields.id, reference: reportReference(neighbourFields) };
  };
  const work = context.work as Row;
  const book = context.book as Row | null;
  const chapter = context.chapter as Row | null;
  const english = context.english as Row | null;
  return {
    id: fields.id,
    tradition: context.tradition as HadithTraditionCode,
    work: { ...mapWorkHeader(work), rightsCitation: text(work.rights_citation) },
    book: book ? { ...mapBook(namespace, book), name: text(book.name), volume: text(book.volume) } : null,
    chapter: chapter
      ? { key: String(chapter.id).replace(/^chapter:/, ''), number: text(chapter.number), name: text(chapter.name) }
      : null,
    number: reportNumber(fields),
    reference: reportReference(fields),
    url: fields.url,
    urlUnique: Boolean(context.url_unique),
    previous: neighbour(context.previous),
    next: neighbour(context.next),
    position: count(context.position),
    total: count(context.total),
    english: english ? { state: text(english.state), translator: text(english.translator), model: text(english.model) } : null,
  };
}
