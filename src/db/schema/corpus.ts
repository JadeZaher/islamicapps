/** Corpus tables (section 5.3): traditions, sources, collections, rights, books, chapters, hadiths, translations. */
import { sql } from 'drizzle-orm';
import {
  boolean,
  check,
  customType,
  index,
  integer,
  jsonb,
  pgTable,
  pgView,
  text,
  unique,
} from 'drizzle-orm/pg-core';
import {
  curationBookkeeping,
  pipelineBookkeeping,
  pipelineBookkeepingForeignKeys,
  restrictForeignKey,
} from './columns';
import {
  chainStatusEnum,
  englishPolicyEnum,
  gradeSchemeEnum,
  gradingStatusEnum,
  hadithTraditionEnum,
  narrationLevelEnum,
  rightsStatusEnum,
  sourceTextStatusEnum,
  translationStateEnum,
} from './enums';
import { bibliographicWorks } from './evidence';

/** Postgres `tsvector`; read only through generated columns. */
const tsvector = customType<{ data: string }>({
  dataType: () => 'tsvector',
});

/** The closed set of four hadith traditions. */
export const traditions = pgTable(
  'traditions',
  {
    id: text('id').primaryKey(),
    code: hadithTraditionEnum('code').notNull(),
    nameArabic: text('name_arabic'),
    normalizedName: text('normalized_name').notNull(),
    gradeScheme: gradeSchemeEnum('grade_scheme').notNull(),
    ...pipelineBookkeeping(),
  },
  (table) => [unique('traditions_code_key').on(table.code), ...pipelineBookkeepingForeignKeys('traditions', table)],
);

/** Upstream provider a row came from. */
export const sources = pgTable(
  'sources',
  {
    id: text('id').primaryKey(),
    slug: text('slug').notNull(),
    name: text('name').notNull(),
    releaseState: text('release_state').notNull(),
    ...pipelineBookkeeping(),
  },
  (table) => [unique('sources_slug_key').on(table.slug), ...pipelineBookkeepingForeignKeys('sources', table)],
);

/** One row per source work (the Neo4j `Source` node). Carries no rights. */
export const collections = pgTable(
  'collections',
  {
    id: text('id').primaryKey(),
    sourceWorkId: text('source_work_id').notNull(),
    slug: text('slug').notNull(),
    name: text('name').notNull(),
    nameArabic: text('name_arabic'),
    sortKey: integer('sort_key').notNull(),
    traditionId: text('tradition_id').notNull(),
    sourceId: text('source_id').notNull(),
    compilerName: text('compiler_name'),
    bibliographicWorkId: text('bibliographic_work_id'),
    registryVersion: text('registry_version').notNull(),
    ...pipelineBookkeeping(),
  },
  (table) => [
    unique('collections_source_work_id_key').on(table.sourceWorkId),
    unique('collections_slug_key').on(table.slug),
    unique('collections_name_key').on(table.name),
    unique('collections_sort_key_key').on(table.sortKey),
    restrictForeignKey('collections_tradition_id_fk', table.traditionId, traditions.id),
    restrictForeignKey('collections_source_id_fk', table.sourceId, sources.id),
    restrictForeignKey('collections_bibliographic_work_id_fk', table.bibliographicWorkId, bibliographicWorks.id),
    index('collections_tradition_id_idx').on(table.traditionId),
    ...pipelineBookkeepingForeignKeys('collections', table),
  ],
);

/** The owner's per-work publication decision (curation); a reload never touches it. */
export const collectionRights = pgTable(
  'collection_rights',
  {
    collectionId: text('collection_id').primaryKey(),
    rightsStatus: rightsStatusEnum('rights_status').notNull().default('pending'),
    englishPolicy: englishPolicyEnum('english_policy').notNull().default('reviewed_only'),
    rightsNote: text('rights_note'),
    citation: text('citation'),
    ...curationBookkeeping(),
  },
  (table) => [restrictForeignKey('collection_rights_collection_id_fk', table.collectionId, collections.id)],
);

/** Browsing structure: books within a collection. */
export const books = pgTable(
  'books',
  {
    id: text('id').primaryKey(),
    collectionId: text('collection_id').notNull(),
    number: text('number'),
    name: text('name'),
    volume: text('volume'),
    providerFileId: text('provider_file_id'),
    providerBookId: text('provider_book_id'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('books_collection_id_fk', table.collectionId, collections.id),
    index('books_collection_id_idx').on(table.collectionId),
    ...pipelineBookkeepingForeignKeys('books', table),
  ],
);

/** Browsing structure: chapters within a collection, optionally within a book. */
export const chapters = pgTable(
  'chapters',
  {
    id: text('id').primaryKey(),
    collectionId: text('collection_id').notNull(),
    bookId: text('book_id'),
    number: text('number'),
    categoryNumber: text('category_number'),
    name: text('name'),
    nameFolded: text('name_folded'),
    providerChapterLocator: text('provider_chapter_locator'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('chapters_collection_id_fk', table.collectionId, collections.id),
    restrictForeignKey('chapters_book_id_fk', table.bookId, books.id),
    index('chapters_collection_id_idx').on(table.collectionId),
    index('chapters_book_id_idx').on(table.bookId),
    ...pipelineBookkeepingForeignKeys('chapters', table),
  ],
);

/** Columns of hadiths, shared with the public_hadiths view declaration. */
function hadithColumns() {
  return {
    id: text('id').primaryKey(),
    recordId: text('record_id').notNull(),
    sourceRecordId: text('source_record_id'),
    providerHadithId: text('provider_hadith_id'),
    collectionId: text('collection_id').notNull(),
    collectionSortKey: integer('collection_sort_key').notNull(),
    sourceDisplayLabel: text('source_display_label'),
    traditionId: text('tradition_id').notNull(),
    bookId: text('book_id'),
    chapterId: text('chapter_id'),
    volume: text('volume'),
    chapterNo: text('chapter_no'),
    chapterTitle: text('chapter_title'),
    chapterTitleFolded: text('chapter_title_folded'),
    category: text('category'),
    categoryFolded: text('category_folded'),
    hadithNo: text('hadith_no'),
    hadithNoInt: integer('hadith_no_int').generatedAlwaysAs(
      sql`case when hadith_no ~ '^[0-9]+$' then hadith_no::integer end`,
    ),
    textAr: text('text_ar'),
    textArNormalized: text('text_ar_normalized'),
    arabicSha256: text('arabic_sha256').notNull(),
    sanad: text('sanad'),
    sanadConfidence: text('sanad_confidence'),
    matnAr: text('matn_ar'),
    sanadAr: text('sanad_ar'),
    sanadInheritsFrom: text('sanad_inherits_from'),
    splitConfidence: text('split_confidence'),
    sourceNotes: jsonb('source_notes'),
    attributedTo: text('attributed_to'),
    narrationLevel: narrationLevelEnum('narration_level'),
    chainType: text('chain_type'),
    school: text('school'),
    url: text('url'),
    pageRef: text('page_ref'),
    provenanceSource: text('provenance_source'),
    translationDisposition: text('translation_disposition'),
    qualityExcluded: boolean('quality_excluded').notNull().default(false),
    qualityExclusionReason: text('quality_exclusion_reason'),
    sourceTextStatus: sourceTextStatusEnum('source_text_status').notNull().default('missing'),
    chainStatus: chainStatusEnum('chain_status').notNull().default('extraction_failed'),
    gradingStatus: gradingStatusEnum('grading_status').notNull().default('none_recorded'),
    ...pipelineBookkeeping(),
  };
}

/** One row per report. Arabic is stored byte for byte; facet columns default to the worst state. */
export const hadiths = pgTable(
  'hadiths',
  hadithColumns(),
  (table) => [
    unique('hadiths_record_id_key').on(table.recordId),
    check('hadiths_split_confidence_check', sql`${table.splitConfidence} in ('high', 'low')`),
    check('hadiths_source_notes_check', sql`${table.sourceNotes} is null or jsonb_typeof(${table.sourceNotes}) = 'array'`),
    restrictForeignKey('hadiths_collection_id_fk', table.collectionId, collections.id),
    restrictForeignKey('hadiths_tradition_id_fk', table.traditionId, traditions.id),
    restrictForeignKey('hadiths_book_id_fk', table.bookId, books.id),
    restrictForeignKey('hadiths_chapter_id_fk', table.chapterId, chapters.id),
    index('hadiths_browse_order_idx').on(table.collectionSortKey, table.hadithNoInt, table.id),
    index('hadiths_collection_id_idx').on(table.collectionId),
    index('hadiths_tradition_id_idx').on(table.traditionId),
    index('hadiths_book_id_idx').on(table.bookId),
    index('hadiths_chapter_id_idx').on(table.chapterId),
    index('hadiths_source_display_label_idx').on(table.sourceDisplayLabel),
    index('hadiths_chapter_title_folded_trgm_idx').using('gin', table.chapterTitleFolded.op('gin_trgm_ops')),
    index('hadiths_category_folded_trgm_idx').using('gin', table.categoryFolded.op('gin_trgm_ops')),
    // hadiths_text_ar_normalized_trgm_idx is heavy: built by src/db/ops/indexes-heavy.sql, not a migration.
    ...pipelineBookkeepingForeignKeys('hadiths', table),
  ],
);

/** Columns of translations, shared with the public_translations view declaration. */
function translationColumns() {
  return {
    id: text('id').primaryKey(),
    hadithId: text('hadith_id').notNull(),
    language: text('language').notNull(),
    text: text('text').notNull(),
    textTsv: tsvector('text_tsv')
      .notNull()
      .generatedAlwaysAs(sql`to_tsvector('english'::regconfig, text)`),
    matnText: text('matn_text'),
    state: translationStateEnum('state').notNull(),
    qualityStatus: text('quality_status').notNull(),
    reviewStateRaw: text('review_state_raw'),
    source: text('source'),
    model: text('model'),
    translator: text('translator'),
    provenanceSource: text('provenance_source'),
    sourceRecordId: text('source_record_id'),
    arabicSha256: text('arabic_sha256').notNull(),
    ...pipelineBookkeeping(),
  };
}

/** The bundle's canonical English surface only; candidates never live here. */
export const translations = pgTable(
  'translations',
  translationColumns(),
  (table) => [
    unique('translations_hadith_id_language_key').on(table.hadithId, table.language),
    restrictForeignKey('translations_hadith_id_fk', table.hadithId, hadiths.id),
    index('translations_text_tsv_english_idx')
      .using('gin', table.textTsv)
      .where(sql`${table.language} = 'en'`),
    ...pipelineBookkeepingForeignKeys('translations', table),
  ],
);

/** Public view: hadiths a public page may show (section 11.3; hand-written SQL, drizzle/core/0003). */
export const publicHadiths = pgView('public_hadiths', hadithColumns()).existing();

/** Public view: reviewed, hash-bound English on public hadiths; never candidates (drizzle/core/0003). */
export const publicTranslations = pgView('public_translations', translationColumns()).existing();
