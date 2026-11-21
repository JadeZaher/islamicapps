/** Comparative-study tables (section 5.11): faiths, schools, source texts, parallels, motifs. */
import {
  index,
  integer,
  pgTable,
  text,
  uniqueIndex,
} from 'drizzle-orm/pg-core';
import { sql } from 'drizzle-orm';
import { curationBookkeeping, isLive, linkBookkeeping, restrictForeignKey } from './columns';
import { hadiths, traditions, translations } from './corpus';
import {
  confidenceLevelEnum,
  curationStatusEnum,
  israIliyyatStatusEnum,
  motifCategoryEnum,
  parallelTypeEnum,
  recordOriginEnum,
  schoolCategoryEnum,
} from './enums';
import { locations } from './history';
import { narrators } from './narrators';

/** The open set of faiths used for comparison (distinct from the four hadith traditions). */
export const religiousTraditions = pgTable(
  'religious_traditions',
  {
    id: text('id').primaryKey(),
    name: text('name').notNull(),
    nameArabic: text('name_arabic'),
    description: text('description'),
    geographicOrigin: text('geographic_origin'),
    geographicHeartlands: text('geographic_heartlands').array().notNull().default(sql`'{}'::text[]`),
    researchFaithCode: text('research_faith_code'),
    ...curationBookkeeping(),
  },
  (table) => [
    uniqueIndex('religious_traditions_live_name_key').on(table.name).where(isLive(table.retiredAt)),
    uniqueIndex('religious_traditions_live_research_faith_code_key')
      .on(table.researchFaithCode)
      .where(isLive(table.retiredAt)),
  ],
);

/** Seeded taxonomy of schools of thought. */
export const schoolsOfThought = pgTable(
  'schools_of_thought',
  {
    id: text('id').primaryKey(),
    name: text('name').notNull(),
    nameArabic: text('name_arabic'),
    founder: text('founder'),
    description: text('description'),
    category: schoolCategoryEnum('category').notNull(),
    foundedCenturyHijri: integer('founded_century_hijri'),
    parentSchoolId: text('parent_school_id'),
    religiousTraditionId: text('religious_tradition_id'),
    traditionId: text('tradition_id'),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('schools_of_thought_parent_school_id_fk', table.parentSchoolId, table.id),
    restrictForeignKey(
      'schools_of_thought_religious_tradition_id_fk',
      table.religiousTraditionId,
      religiousTraditions.id,
    ),
    restrictForeignKey('schools_of_thought_tradition_id_fk', table.traditionId, traditions.id),
    uniqueIndex('schools_of_thought_live_name_key').on(table.name).where(isLive(table.retiredAt)),
  ],
);

/** A text from another tradition that a parallel cites. */
export const sourceTexts = pgTable(
  'source_texts',
  {
    id: text('id').primaryKey(),
    religiousTraditionId: text('religious_tradition_id').notNull(),
    title: text('title').notNull(),
    titleOriginal: text('title_original'),
    author: text('author'),
    approximateDateCe: text('approximate_date_ce'),
    description: text('description'),
    canonicalReference: text('canonical_reference'),
    origin: recordOriginEnum('origin').notNull(),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('source_texts_religious_tradition_id_fk', table.religiousTraditionId, religiousTraditions.id),
    uniqueIndex('source_texts_live_canonical_reference_key')
      .on(table.canonicalReference)
      .where(isLive(table.retiredAt)),
    index('source_texts_religious_tradition_id_idx').on(table.religiousTraditionId),
  ],
);

/** A cross-tradition parallel to a hadith; `status` is the review gate. */
export const crossParallels = pgTable(
  'cross_parallels',
  {
    id: text('id').primaryKey(),
    pipelineKey: text('pipeline_key'),
    hadithId: text('hadith_id').notNull(),
    boundArabicSha256: text('bound_arabic_sha256').notNull(),
    sourceTextId: text('source_text_id').notNull(),
    religiousTraditionId: text('religious_tradition_id').notNull(),
    parallelType: parallelTypeEnum('parallel_type').notNull(),
    israIliyyatStatus: israIliyyatStatusEnum('isra_iliyyat_status').notNull().default('NONE'),
    confidenceLevel: confidenceLevelEnum('confidence_level').notNull().default('MEDIUM'),
    hadithExcerptEn: text('hadith_excerpt_en'),
    sourceTranslationId: text('source_translation_id'),
    sourceTextOriginal: text('source_text_original'),
    sourceTextEn: text('source_text_en'),
    scholarlyAnalysis: text('scholarly_analysis'),
    origin: recordOriginEnum('origin').notNull(),
    status: curationStatusEnum('status').notNull(),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('cross_parallels_hadith_id_fk', table.hadithId, hadiths.id),
    restrictForeignKey('cross_parallels_source_text_id_fk', table.sourceTextId, sourceTexts.id),
    restrictForeignKey('cross_parallels_religious_tradition_id_fk', table.religiousTraditionId, religiousTraditions.id),
    restrictForeignKey('cross_parallels_source_translation_id_fk', table.sourceTranslationId, translations.id),
    uniqueIndex('cross_parallels_live_pipeline_key_key').on(table.pipelineKey).where(isLive(table.retiredAt)),
    index('cross_parallels_hadith_id_idx').on(table.hadithId),
    index('cross_parallels_tradition_type_idx').on(table.religiousTraditionId, table.parallelType),
    index('cross_parallels_created_at_idx').on(table.createdAt.desc()),
  ],
);

/** A thematic tag for hadiths and parallels. */
export const motifTags = pgTable(
  'motif_tags',
  {
    id: text('id').primaryKey(),
    name: text('name').notNull(),
    category: motifCategoryEnum('category').notNull(),
    description: text('description'),
    origin: recordOriginEnum('origin').notNull(),
    ...curationBookkeeping(),
  },
  (table) => [
    uniqueIndex('motif_tags_live_name_key').on(table.name).where(isLive(table.retiredAt)),
    index('motif_tags_category_idx').on(table.category),
  ],
);

/** Link: motif tag on a hadith. */
export const hadithMotifTags = pgTable(
  'hadith_motif_tags',
  {
    ...linkBookkeeping(),
    hadithId: text('hadith_id').notNull(),
    motifTagId: text('motif_tag_id').notNull(),
  },
  (table) => [
    restrictForeignKey('hadith_motif_tags_hadith_id_fk', table.hadithId, hadiths.id),
    restrictForeignKey('hadith_motif_tags_motif_tag_id_fk', table.motifTagId, motifTags.id),
    uniqueIndex('hadith_motif_tags_live_key').on(table.hadithId, table.motifTagId).where(isLive(table.retiredAt)),
    index('hadith_motif_tags_motif_tag_id_idx').on(table.motifTagId),
  ],
);

/** Link: motif tag on a parallel. */
export const parallelMotifTags = pgTable(
  'parallel_motif_tags',
  {
    ...linkBookkeeping(),
    parallelId: text('parallel_id').notNull(),
    motifTagId: text('motif_tag_id').notNull(),
  },
  (table) => [
    restrictForeignKey('parallel_motif_tags_parallel_id_fk', table.parallelId, crossParallels.id),
    restrictForeignKey('parallel_motif_tags_motif_tag_id_fk', table.motifTagId, motifTags.id),
    uniqueIndex('parallel_motif_tags_live_key').on(table.parallelId, table.motifTagId).where(isLive(table.retiredAt)),
    index('parallel_motif_tags_motif_tag_id_idx').on(table.motifTagId),
  ],
);

/** Link: a narrator associated with a religious tradition. */
export const narratorReligiousTraditions = pgTable(
  'narrator_religious_traditions',
  {
    ...linkBookkeeping(),
    narratorId: text('narrator_id').notNull(),
    religiousTraditionId: text('religious_tradition_id').notNull(),
  },
  (table) => [
    restrictForeignKey('narrator_religious_traditions_narrator_id_fk', table.narratorId, narrators.id),
    restrictForeignKey(
      'narrator_religious_traditions_religious_tradition_id_fk',
      table.religiousTraditionId,
      religiousTraditions.id,
    ),
    uniqueIndex('narrator_religious_traditions_live_key')
      .on(table.narratorId, table.religiousTraditionId)
      .where(isLive(table.retiredAt)),
    index('narrator_religious_traditions_religious_tradition_id_idx').on(table.religiousTraditionId),
  ],
);

/** Link: a location associated with a religious tradition. */
export const locationReligiousTraditions = pgTable(
  'location_religious_traditions',
  {
    ...linkBookkeeping(),
    locationId: text('location_id').notNull(),
    religiousTraditionId: text('religious_tradition_id').notNull(),
  },
  (table) => [
    restrictForeignKey('location_religious_traditions_location_id_fk', table.locationId, locations.id),
    restrictForeignKey(
      'location_religious_traditions_religious_tradition_id_fk',
      table.religiousTraditionId,
      religiousTraditions.id,
    ),
    uniqueIndex('location_religious_traditions_live_key')
      .on(table.locationId, table.religiousTraditionId)
      .where(isLive(table.retiredAt)),
    index('location_religious_traditions_religious_tradition_id_idx').on(table.religiousTraditionId),
  ],
);
