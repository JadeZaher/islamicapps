/** Commentary tables (section 5.10): commentaries and their hadith and narrator links. */
import { index, pgTable, text, uniqueIndex } from 'drizzle-orm/pg-core';
import { curationBookkeeping, isLive, linkBookkeeping, restrictForeignKey } from './columns';
import { hadiths } from './corpus';
import { curationStatusEnum, recordOriginEnum } from './enums';
import { citations } from './evidence';
import { narrators } from './narrators';

/** A curated commentary; public pages show `published` only. */
export const commentaries = pgTable(
  'commentaries',
  {
    id: text('id').primaryKey(),
    type: text('type'),
    text: text('text').notNull(),
    textArabic: text('text_arabic'),
    author: text('author'),
    sourceWork: text('source_work'),
    reference: text('reference'),
    citationId: text('citation_id'),
    status: curationStatusEnum('status').notNull().default('proposed'),
    origin: recordOriginEnum('origin').notNull(),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('commentaries_citation_id_fk', table.citationId, citations.id),
    index('commentaries_created_at_idx').on(table.createdAt.desc()),
  ],
);

/** Link: commentary on a hadith, bound to the Arabic it was written against. */
export const commentaryHadiths = pgTable(
  'commentary_hadiths',
  {
    ...linkBookkeeping(),
    commentaryId: text('commentary_id').notNull(),
    hadithId: text('hadith_id').notNull(),
    boundArabicSha256: text('bound_arabic_sha256').notNull(),
  },
  (table) => [
    restrictForeignKey('commentary_hadiths_commentary_id_fk', table.commentaryId, commentaries.id),
    restrictForeignKey('commentary_hadiths_hadith_id_fk', table.hadithId, hadiths.id),
    uniqueIndex('commentary_hadiths_live_key').on(table.commentaryId, table.hadithId).where(isLive(table.retiredAt)),
    index('commentary_hadiths_hadith_id_idx').on(table.hadithId),
  ],
);

/** Link: commentary about a narrator. */
export const commentaryNarrators = pgTable(
  'commentary_narrators',
  {
    ...linkBookkeeping(),
    commentaryId: text('commentary_id').notNull(),
    narratorId: text('narrator_id').notNull(),
  },
  (table) => [
    restrictForeignKey('commentary_narrators_commentary_id_fk', table.commentaryId, commentaries.id),
    restrictForeignKey('commentary_narrators_narrator_id_fk', table.narratorId, narrators.id),
    uniqueIndex('commentary_narrators_live_key')
      .on(table.commentaryId, table.narratorId)
      .where(isLive(table.retiredAt)),
    index('commentary_narrators_narrator_id_idx').on(table.narratorId),
  ],
);
