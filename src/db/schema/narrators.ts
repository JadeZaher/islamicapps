/** Narrator tables (section 5.4): identity, lexicon profile, aliases, lexicon teacher links. Never a verdict (G-1). */
import { sql } from 'drizzle-orm';
import {
  boolean,
  check,
  index,
  integer,
  jsonb,
  pgTable,
  primaryKey,
  text,
  unique,
} from 'drizzle-orm/pg-core';
import { pipelineBookkeeping, pipelineBookkeepingForeignKeys, restrictForeignKey } from './columns';
import { evidenceReviewStateEnum, nameLatinBasisEnum, narratorAuthorityEnum, narratorPlaceholderReasonEnum } from './enums';

/** Narrator identity only: no verdict, grade or reliability column, ever (G-1). */
export const narrators = pgTable(
  'narrators',
  {
    id: text('id').primaryKey(),
    authority: narratorAuthorityEnum('authority').notNull().default('rawi'),
    authorityKey: text('authority_key').notNull(),
    scholarIndx: integer('scholar_indx'),
    name: text('name').notNull(),
    nameAr: text('name_ar'),
    nameEn: text('name_en'),
    nameArNormalized: text('name_ar_normalized'),
    nameEnFolded: text('name_en_folded'),
    /** Set when the lexicon row cannot name one person; never an automatic match target except kunya-only. */
    placeholderReason: narratorPlaceholderReasonEnum('placeholder_reason'),
    /** The name in Latin letters for a record that has no English name (external and register rows; 0010). */
    nameLatin: text('name_latin'),
    nameLatinBasis: nameLatinBasisEnum('name_latin_basis'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    unique('narrators_scholar_indx_key').on(table.scholarIndx),
    unique('narrators_authority_authority_key_key').on(table.authority, table.authorityKey),
    check('narrators_name_latin_check', sql`(${table.nameLatin} is null) = (${table.nameLatinBasis} is null)`),
    check('narrators_rawi_scholar_indx_check', sql`${table.authority} <> 'rawi' or ${table.scholarIndx} is not null`),
    index('narrators_name_ar_normalized_trgm_idx').using('gin', table.nameArNormalized.op('gin_trgm_ops')),
    index('narrators_name_en_folded_trgm_idx').using('gin', table.nameEnFolded.op('gin_trgm_ops')),
    index('narrators_display_name_idx').using('btree', sql`coalesce(${table.nameEn}, ${table.name})`),
    ...pipelineBookkeepingForeignKeys('narrators', table),
  ],
);

/** What the rawi lexicon says about a narrator; a lexicon claim, not evidence. */
export const narratorLexiconProfiles = pgTable(
  'narrator_lexicon_profiles',
  {
    narratorId: text('narrator_id').primaryKey(),
    bundleId: text('bundle_id').notNull(),
    rawProfileSha256: text('raw_profile_sha256').notNull(),
    lexiconGradeLabel: text('lexicon_grade_label'),
    bio: text('bio'),
    tabaqahRaw: text('tabaqah_raw'),
    geographicRegion: text('geographic_region'),
    birthYearHijri: integer('birth_year_hijri'),
    birthYearGregorian: integer('birth_year_gregorian'),
    birthYearHijriRaw: text('birth_year_hijri_raw'),
    birthYearGregorianRaw: text('birth_year_gregorian_raw'),
    birthSourceText: text('birth_source_text'),
    birthPlace: text('birth_place'),
    deathYearHijri: integer('death_year_hijri'),
    deathYearGregorian: integer('death_year_gregorian'),
    deathYearHijriRaw: text('death_year_hijri_raw'),
    deathYearGregorianRaw: text('death_year_gregorian_raw'),
    deathSourceText: text('death_source_text'),
    deathPlace: text('death_place'),
    deathReason: text('death_reason'),
    reviewState: evidenceReviewStateEnum('review_state').notNull().default('lexicon_unverified'),
    sourceStatus: text('source_status').notNull(),
    sourceLocator: text('source_locator'),
    /** The lexicon's descriptive fields verbatim (places of stay, family, tags, interests; 0013). */
    sourceFields: jsonb('source_fields'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    unique('narrator_lexicon_profiles_bundle_id_key').on(table.bundleId),
    check(
      'narrator_lexicon_profiles_source_fields_check',
      sql`${table.sourceFields} is null or jsonb_typeof(${table.sourceFields}) = 'object'`,
    ),
    restrictForeignKey('narrator_lexicon_profiles_narrator_id_fk', table.narratorId, narrators.id),
    ...pipelineBookkeepingForeignKeys('narrator_lexicon_profiles', table),
  ],
);

/** Name surfaces a narrator is known by. */
export const narratorAliases = pgTable(
  'narrator_aliases',
  {
    id: text('id').primaryKey(),
    narratorId: text('narrator_id').notNull(),
    surface: text('surface').notNull(),
    normalizedSurface: text('normalized_surface').notNull(),
    aliasKind: text('alias_kind').notNull(),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('narrator_aliases_narrator_id_fk', table.narratorId, narrators.id),
    index('narrator_aliases_narrator_id_idx').on(table.narratorId),
    index('narrator_aliases_normalized_surface_idx').on(table.normalizedSurface),
    ...pipelineBookkeepingForeignKeys('narrator_aliases', table),
  ],
);

/** Lexicon-declared student-to-teacher links; candidate ranking only, never transmission evidence. */
export const narratorTeachers = pgTable(
  'narrator_teachers',
  {
    studentId: text('student_id').notNull(),
    teacherId: text('teacher_id').notNull(),
    evidenceFields: text('evidence_fields').array().notNull(),
    evidenceCount: integer('evidence_count').notNull(),
    reciprocal: boolean('reciprocal').notNull(),
    reviewState: text('review_state').notNull(),
    ...pipelineBookkeeping(),
  },
  (table) => [
    primaryKey({ name: 'narrator_teachers_pkey', columns: [table.studentId, table.teacherId] }),
    restrictForeignKey('narrator_teachers_student_id_fk', table.studentId, narrators.id),
    restrictForeignKey('narrator_teachers_teacher_id_fk', table.teacherId, narrators.id),
    index('narrator_teachers_teacher_id_idx').on(table.teacherId),
    ...pipelineBookkeepingForeignKeys('narrator_teachers', table),
  ],
);

/**
 * What an external dataset (or the Imam register) records about one of its narrators, verbatim, under its licence.
 * Pipeline-owned; never a verdict (G-1): hadith-kg's rank wording stays inside `assertions` and is not displayed as one.
 * `label_reason` is set when the source's id names a label as written in chains rather than an established person.
 * See src/db/AGENTS.md §External identity.
 */
export const narratorSourceProfiles = pgTable(
  'narrator_source_profiles',
  {
    narratorId: text('narrator_id').primaryKey(),
    source: text('source').notNull(),
    assertions: jsonb('assertions').notNull(),
    licence: text('licence').notNull(),
    labelReason: text('label_reason'),
    assertedBy: text('asserted_by').notNull(),
    reviewState: text('review_state').notNull().default('source_unverified'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('narrator_source_profiles_narrator_id_fk', table.narratorId, narrators.id),
    check('narrator_source_profiles_source_check', sql`${table.source} in ('hadith_kg', 'riwayat', 'imam_register', 'work_register')`),
    check('narrator_source_profiles_review_state_check', sql`${table.reviewState} = 'source_unverified'`),
    ...pipelineBookkeepingForeignKeys('narrator_source_profiles', table),
  ],
);

/** Other datasets' ids an external narrator record carries (Riwayat's crosswalk: Thaqalayn, hadith-kg, Itqan, ...). */
export const narratorExternalIds = pgTable(
  'narrator_external_ids',
  {
    id: text('id').primaryKey(),
    narratorId: text('narrator_id').notNull(),
    namespace: text('namespace').notNull(),
    externalId: text('external_id').notNull(),
    assertedBy: text('asserted_by').notNull(),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('narrator_external_ids_narrator_id_fk', table.narratorId, narrators.id),
    index('narrator_external_ids_narrator_id_idx').on(table.narratorId),
    ...pipelineBookkeepingForeignKeys('narrator_external_ids', table),
  ],
);

/**
 * A machine-proposed link between an external narrator and a lexicon row, with its evidence. A candidate only: it is
 * shown as one, used to compare two claims at a mention, and never merges narrators (a reviewer would; G-5).
 */
export const narratorLinkCandidates = pgTable(
  'narrator_link_candidates',
  {
    id: text('id').primaryKey(),
    externalNarratorId: text('external_narrator_id').notNull(),
    rawiNarratorId: text('rawi_narrator_id').notNull(),
    basis: text('basis').notNull(),
    evidence: jsonb('evidence').notNull(),
    reviewState: text('review_state').notNull(),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('narrator_link_candidates_external_narrator_id_fk', table.externalNarratorId, narrators.id),
    restrictForeignKey('narrator_link_candidates_rawi_narrator_id_fk', table.rawiNarratorId, narrators.id),
    check('narrator_link_candidates_review_state_check', sql`${table.reviewState} = 'unreviewed'`),
    index('narrator_link_candidates_external_narrator_id_idx').on(table.externalNarratorId),
    index('narrator_link_candidates_rawi_narrator_id_idx').on(table.rawiNarratorId),
    ...pipelineBookkeepingForeignKeys('narrator_link_candidates', table),
  ],
);
