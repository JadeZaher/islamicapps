/** Assessments and biography (sections 5.6, 5.7): hadith grades, narrator verdicts, curated bios. */
import { sql } from 'drizzle-orm';
import { boolean, check, index, integer, pgTable, text, unique } from 'drizzle-orm/pg-core';
import {
  curationBookkeeping,
  pipelineBookkeeping,
  pipelineBookkeepingForeignKeys,
  restrictForeignKey,
} from './columns';
import { hadiths, traditions } from './corpus';
import {
  assessmentKindEnum,
  curationStatusEnum,
  evidenceReviewStateEnum,
  gradeCanonicalEnum,
  gradeSchemeEnum,
  narratorAssessmentKindEnum,
  narratorVerdictEnum,
  tabaqahClassEnum,
} from './enums';
import { citations } from './evidence';
import { narrators } from './narrators';

/** Tradition-scoped, multi-valued, cited hadith grades. No placeholder rows. */
export const hadithAssessments = pgTable(
  'hadith_assessments',
  {
    id: text('id').primaryKey(),
    hadithId: text('hadith_id').notNull(),
    traditionId: text('tradition_id').notNull(),
    gradeScheme: gradeSchemeEnum('grade_scheme').notNull(),
    ordinal: integer('ordinal').notNull(),
    kind: assessmentKindEnum('kind').notNull(),
    grader: text('grader'),
    gradeRaw: text('grade_raw').notNull(),
    gradeCanonical: gradeCanonicalEnum('grade_canonical'),
    gradeDetail: text('grade_detail'),
    citationRaw: text('citation_raw'),
    citedWork: text('cited_work'),
    citedVolume: text('cited_volume'),
    citedPage: text('cited_page'),
    citationId: text('citation_id'),
    sourceField: text('source_field').notNull(),
    reviewState: evidenceReviewStateEnum('review_state').notNull(),
    ...pipelineBookkeeping(),
  },
  (table) => [
    unique('hadith_assessments_natural_key').on(table.hadithId, table.traditionId, table.sourceField, table.ordinal),
    restrictForeignKey('hadith_assessments_hadith_id_fk', table.hadithId, hadiths.id),
    restrictForeignKey('hadith_assessments_tradition_id_fk', table.traditionId, traditions.id),
    restrictForeignKey('hadith_assessments_citation_id_fk', table.citationId, citations.id),
    index('hadith_assessments_hadith_id_idx').on(table.hadithId),
    index('hadith_assessments_tradition_grade_idx').on(table.traditionId, table.gradeCanonical),
    ...pipelineBookkeepingForeignKeys('hadith_assessments', table),
  ],
);

/** A curated verdict on a narrator; always tradition-scoped before it can publish. */
export const narratorAssessments = pgTable(
  'narrator_assessments',
  {
    id: text('id').primaryKey(),
    narratorId: text('narrator_id').notNull(),
    traditionId: text('tradition_id'),
    kind: narratorAssessmentKindEnum('kind').notNull(),
    verdict: narratorVerdictEnum('verdict').notNull(),
    critic: text('critic'),
    quoteAr: text('quote_ar'),
    quoteEn: text('quote_en'),
    tadilText: text('tadil_text'),
    jarhText: text('jarh_text'),
    isCompanion: boolean('is_companion'),
    disagreement: boolean('disagreement').notNull().default(false),
    criticQuoteCount: integer('critic_quote_count'),
    provenance: text('provenance').notNull(),
    citationId: text('citation_id'),
    status: curationStatusEnum('status').notNull().default('proposed'),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('narrator_assessments_narrator_id_fk', table.narratorId, narrators.id),
    restrictForeignKey('narrator_assessments_tradition_id_fk', table.traditionId, traditions.id),
    restrictForeignKey('narrator_assessments_citation_id_fk', table.citationId, citations.id),
    check(
      'narrator_assessments_published_tradition_check',
      sql`${table.status} <> 'published' or ${table.traditionId} is not null`,
    ),
    check(
      'narrator_assessments_published_citation_check',
      sql`${table.status} <> 'published' or ${table.citationId} is not null`,
    ),
    index('narrator_assessments_narrator_tradition_idx').on(table.narratorId, table.traditionId),
  ],
);

/** Curated, descriptive biography fields; evaluative text lives in narrator_assessments. */
export const narratorBios = pgTable(
  'narrator_bios',
  {
    narratorId: text('narrator_id').primaryKey(),
    isProphet: boolean('is_prophet').notNull().default(false),
    tabaqahClass: tabaqahClassEnum('tabaqah_class'),
    nameEnClean: text('name_en_clean'),
    nameArClean: text('name_ar_clean'),
    kunya: text('kunya'),
    nasab: text('nasab'),
    nisba: text('nisba'),
    geographicRegion: text('geographic_region'),
    deathYearHijri: integer('death_year_hijri'),
    deathYearGregorian: integer('death_year_gregorian'),
    bioSummary: text('bio_summary'),
    provenance: text('provenance').notNull(),
    citationId: text('citation_id'),
    status: curationStatusEnum('status').notNull().default('proposed'),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('narrator_bios_narrator_id_fk', table.narratorId, narrators.id),
    restrictForeignKey('narrator_bios_citation_id_fk', table.citationId, citations.id),
    check('narrator_bios_published_citation_check', sql`${table.status} <> 'published' or ${table.citationId} is not null`),
  ],
);
