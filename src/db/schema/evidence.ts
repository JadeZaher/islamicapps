/** Evidence tables (section 5.8) shipped at launch: bibliographic works, editions, citations. */
import { integer, pgTable, text, timestamp } from 'drizzle-orm/pg-core';
import { pipelineBookkeeping, pipelineBookkeepingForeignKeys, restrictForeignKey } from './columns';
import { traditions } from './corpus';
import { evidenceReviewStateEnum, rightsStatusEnum } from './enums';
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
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('citations_work_id_fk', table.workId, bibliographicWorks.id),
    restrictForeignKey('citations_edition_id_fk', table.editionId, editions.id),
    ...pipelineBookkeepingForeignKeys('citations', table),
  ],
);
