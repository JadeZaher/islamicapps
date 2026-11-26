/** Evidence tables (section 5.8): bibliographic works, editions, citations, temporal assertions. */
import { sql } from 'drizzle-orm';
import { check, index, integer, jsonb, pgTable, text, timestamp } from 'drizzle-orm/pg-core';
import { pipelineBookkeeping, pipelineBookkeepingForeignKeys, restrictForeignKey } from './columns';
import { collections, traditions } from './corpus';
import { calendarEnum, evidenceReviewStateEnum, rightsStatusEnum } from './enums';
import { narrators } from './narrators';

/** A cited work, optionally linked to its author as a narrator. */
export const bibliographicWorks = pgTable(
  'bibliographic_works',
  {
    id: text('id').primaryKey(),
    title: text('title').notNull(),
    titleAr: text('title_ar'),
    author: text('author'),
    authorNarratorId: text('author_narrator_id'),
    traditionId: text('tradition_id'),
    authorDeathYearHijri: integer('author_death_year_hijri'),
    openitiUri: text('openiti_uri'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('bibliographic_works_author_narrator_id_fk', table.authorNarratorId, narrators.id),
    restrictForeignKey('bibliographic_works_tradition_id_fk', table.traditionId, traditions.id),
    ...pipelineBookkeepingForeignKeys('bibliographic_works', table),
  ],
);

/** A printed or digital edition of a work. */
export const editions = pgTable(
  'editions',
  {
    id: text('id').primaryKey(),
    workId: text('work_id').notNull(),
    editor: text('editor'),
    publisher: text('publisher'),
    place: text('place'),
    year: text('year'),
    locatorScheme: text('locator_scheme'),
    url: text('url'),
    rightsStatus: rightsStatusEnum('rights_status').notNull(),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('editions_work_id_fk', table.workId, bibliographicWorks.id),
    ...pipelineBookkeepingForeignKeys('editions', table),
  ],
);

/** A locator into a work or edition. Counts as cited only when live and reviewed (section 5.8). */
export const citations = pgTable(
  'citations',
  {
    id: text('id').primaryKey(),
    workId: text('work_id').notNull(),
    editionId: text('edition_id'),
    volume: text('volume'),
    page: text('page'),
    locator: text('locator'),
    url: text('url'),
    quoteAr: text('quote_ar'),
    quoteEn: text('quote_en'),
    retrievedAt: timestamp('retrieved_at', { withTimezone: true }),
    reviewState: evidenceReviewStateEnum('review_state').notNull(),
    /** Character/byte span in the source file (0024: history and rijal OpenITI citations). */
    sourceSpan: jsonb('source_span'),
    /** SHA-256 of the source file that `source_span` indexes into (0024). */
    sourceSha256: text('source_sha256'),
    /** Repository-relative path to the source file (0024). */
    sourceFile: text('source_file'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('citations_work_id_fk', table.workId, bibliographicWorks.id),
    restrictForeignKey('citations_edition_id_fk', table.editionId, editions.id),
    check('citations_source_span_check', sql`${table.sourceSpan} is null or jsonb_typeof(${table.sourceSpan}) = 'object'`),
    check('citations_source_sha256_check', sql`${table.sourceSha256} is null or ${table.sourceSha256} ~ '^[0-9a-f]{64}$'`),
    check('citations_source_file_check', sql`${table.sourceFile} is null or btrim(${table.sourceFile}) <> ''`),
    ...pipelineBookkeepingForeignKeys('citations', table),
  ],
);

/**
 * Cited dating claims about an event, epoch boundary or collection (design §5.8, 0024).
 * Competing claims are separate rows; event and epoch IDs are not foreign keys because those tables are curation-owned.
 */
export const temporalAssertions = pgTable(
  'temporal_assertions',
  {
    id: text('id').primaryKey(),
    eventId: text('event_id'),
    epochId: text('epoch_id'),
    collectionId: text('collection_id'),
    boundary: text('boundary'),
    predicate: text('predicate').notNull(),
    yearMin: integer('year_min'),
    yearMax: integer('year_max'),
    calendar: calendarEnum('calendar').notNull().default('hijri'),
    precision: text('precision'),
    alternatives: integer('alternatives').array().notNull().default(sql`'{}'::integer[]`),
    monthDay: text('month_day'),
    statedAr: text('stated_ar'),
    statementEn: text('statement_en'),
    dateBasis: text('date_basis'),
    qualifier: text('qualifier'),
    reckoning: text('reckoning'),
    attributedTo: text('attributed_to'),
    perspective: jsonb('perspective'),
    flags: text('flags').array().notNull().default(sql`'{}'::text[]`),
    note: text('note'),
    citationId: text('citation_id').notNull(),
    reviewState: evidenceReviewStateEnum('review_state').notNull().default('candidate_only'),
    aiReview: jsonb('ai_review'),
    humanReviews: jsonb('human_reviews').notNull().default(sql`'[]'::jsonb`),
    supersedesAssertionId: text('supersedes_assertion_id'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('temporal_assertions_collection_id_fk', table.collectionId, collections.id),
    restrictForeignKey('temporal_assertions_citation_id_fk', table.citationId, citations.id),
    restrictForeignKey('temporal_assertions_supersedes_assertion_id_fk', table.supersedesAssertionId, table.id),
    check('temporal_assertions_subject_check', sql`num_nonnulls(${table.eventId}, ${table.epochId}, ${table.collectionId}) = 1`),
    check(
      'temporal_assertions_boundary_check',
      sql`${table.boundary} is null or (${table.epochId} is not null and ${table.boundary} in ('start', 'end'))`,
    ),
    check(
      'temporal_assertions_year_range_check',
      sql`${table.yearMin} is null or ${table.yearMax} is null or ${table.yearMax} >= ${table.yearMin}`,
    ),
    check(
      'temporal_assertions_date_basis_check',
      sql`${table.dateBasis} is null or ${table.dateBasis} in ('passage', 'section_heading')`,
    ),
    check(
      'temporal_assertions_perspective_check',
      sql`${table.perspective} is null or jsonb_typeof(${table.perspective}) = 'object'`,
    ),
    check('temporal_assertions_ai_review_check', sql`${table.aiReview} is null or jsonb_typeof(${table.aiReview}) = 'object'`),
    check('temporal_assertions_human_reviews_check', sql`jsonb_typeof(${table.humanReviews}) = 'array'`),
    index('temporal_assertions_event_id_idx').on(table.eventId),
    index('temporal_assertions_epoch_id_idx').on(table.epochId),
    index('temporal_assertions_collection_id_idx').on(table.collectionId),
    index('temporal_assertions_citation_id_idx').on(table.citationId),
    ...pipelineBookkeepingForeignKeys('temporal_assertions', table),
  ],
);
