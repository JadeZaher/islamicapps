/** Isnad tables and derived views (section 5.5). See src/db/AGENTS.md §Isnad. */
import { sql } from 'drizzle-orm';
import {
  boolean,
  check,
  index,
  integer,
  pgMaterializedView,
  pgTable,
  pgView,
  real,
  text,
  timestamp,
  unique,
  uniqueIndex,
} from 'drizzle-orm/pg-core';
import {
  curationBookkeeping,
  isLive,
  pipelineBookkeeping,
  pipelineBookkeepingForeignKeys,
  restrictForeignKey,
} from './columns';
import { collections, hadiths } from './corpus';
import {
  decisionScopeEnum,
  linkKindEnum,
  mentionCandidateBasisEnum,
  mentionResolutionEnum,
  resolutionBasisEnum,
  surfaceDecisionKindEnum,
} from './enums';
import { citations } from './evidence';
import { narrators } from './narrators';

/** One row per branch (tahwil) of a report. */
export const chains = pgTable(
  'chains',
  {
    id: text('id').primaryKey(),
    hadithId: text('hadith_id').notNull(),
    branch: integer('branch').notNull(),
    length: integer('length').notNull(),
    resolved: boolean('resolved').notNull(),
    verifiedLinkCount: integer('verified_link_count').notNull().default(0),
    extractionMethod: text('extraction_method').notNull(),
    confidence: real('confidence'),
    sanadConfidence: text('sanad_confidence'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    unique('chains_hadith_id_branch_key').on(table.hadithId, table.branch),
    restrictForeignKey('chains_hadith_id_fk', table.hadithId, hadiths.id),
    ...pipelineBookkeepingForeignKeys('chains', table),
  ],
);

/** A name as written at one position of one branch; position 0 is the collector. */
export const chainMentions = pgTable(
  'chain_mentions',
  {
    id: text('id').primaryKey(),
    chainId: text('chain_id').notNull(),
    hadithId: text('hadith_id').notNull(),
    position: integer('position').notNull(),
    surfaceAr: text('surface_ar').notNull(),
    surfaceNormalized: text('surface_normalized').notNull(),
    teacherContextNormalized: text('teacher_context_normalized'),
    studentContextNormalized: text('student_context_normalized'),
    reviewUnitId: text('review_unit_id').notNull(),
    reviewUnitFineId: text('review_unit_fine_id').notNull(),
    linkKind: linkKindEnum('link_kind').notNull().default('unclassified'),
    resolution: mentionResolutionEnum('resolution').notNull().default('unresolved'),
    resolutionBasis: resolutionBasisEnum('resolution_basis'),
    narratorId: text('narrator_id'),
    decisionId: text('decision_id'),
    confidence: real('confidence'),
    extractionMethod: text('extraction_method'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    unique('chain_mentions_chain_id_position_key').on(table.chainId, table.position),
    restrictForeignKey('chain_mentions_chain_id_fk', table.chainId, chains.id),
    restrictForeignKey('chain_mentions_hadith_id_fk', table.hadithId, hadiths.id),
    restrictForeignKey('chain_mentions_narrator_id_fk', table.narratorId, narrators.id),
    restrictForeignKey('chain_mentions_decision_id_fk', table.decisionId, narratorSurfaceDecisions.id),
    check(
      'chain_mentions_resolved_confidence_check',
      sql`${table.narratorId} is null or ${table.confidence} is not null`,
    ),
    index('chain_mentions_narrator_id_idx').on(table.narratorId).where(sql`${table.narratorId} is not null`),
    index('chain_mentions_hadith_id_idx').on(table.hadithId),
    index('chain_mentions_review_unit_id_idx').on(table.reviewUnitId),
    index('chain_mentions_review_unit_fine_id_idx').on(table.reviewUnitFineId),
    index('chain_mentions_surface_normalized_idx').on(table.surfaceNormalized),
    ...pipelineBookkeepingForeignKeys('chain_mentions', table),
  ],
);

/**
 * Every automatic identity candidate for a mention, each with its basis; disagreeing candidates are all kept.
 * Pipeline-owned. `reviewer_decision` is never stored here (check): it is read from the decision in the public view.
 * See src/db/AGENTS.md §Identity candidates.
 */
export const chainMentionCandidates = pgTable(
  'chain_mention_candidates',
  {
    id: text('id').primaryKey(),
    mentionId: text('mention_id').notNull(),
    hadithId: text('hadith_id').notNull(),
    narratorId: text('narrator_id').notNull(),
    basis: mentionCandidateBasisEnum('basis').notNull(),
    /** Resolver tier, or the source index's agreement class against the Arabic. */
    detail: text('detail'),
    /** 0-based position in the source's own narrator index (source bases only). */
    sourcePosition: integer('source_position'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    unique('chain_mention_candidates_mention_narrator_basis_key').on(table.mentionId, table.narratorId, table.basis),
    restrictForeignKey('chain_mention_candidates_mention_id_fk', table.mentionId, chainMentions.id),
    restrictForeignKey('chain_mention_candidates_hadith_id_fk', table.hadithId, hadiths.id),
    restrictForeignKey('chain_mention_candidates_narrator_id_fk', table.narratorId, narrators.id),
    check('chain_mention_candidates_pipeline_basis_check', sql`${table.basis} <> 'reviewer_decision'`),
    check(
      'chain_mention_candidates_source_position_check',
      sql`(${table.basis} in ('source_index', 'source_index_confirmed_by_text')) = (${table.sourcePosition} is not null)`,
    ),
    index('chain_mention_candidates_hadith_id_idx').on(table.hadithId),
    index('chain_mention_candidates_narrator_id_idx').on(table.narratorId),
    ...pipelineBookkeepingForeignKeys('chain_mention_candidates', table),
  ],
);

/** Curated record that a report, or a whole work, has no isnad by nature. */
export const chainAbsenceDispositions = pgTable(
  'chain_absence_dispositions',
  {
    id: text('id').primaryKey(),
    collectionId: text('collection_id'),
    hadithId: text('hadith_id'),
    reason: text('reason').notNull(),
    citationId: text('citation_id'),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('chain_absence_dispositions_collection_id_fk', table.collectionId, collections.id),
    restrictForeignKey('chain_absence_dispositions_hadith_id_fk', table.hadithId, hadiths.id),
    restrictForeignKey('chain_absence_dispositions_citation_id_fk', table.citationId, citations.id),
    check(
      'chain_absence_dispositions_one_target_check',
      sql`num_nonnulls(${table.collectionId}, ${table.hadithId}) = 1`,
    ),
  ],
);

/** A human identity decision for one review unit, replayed onto matching mentions after every load. */
export const narratorSurfaceDecisions = pgTable(
  'narrator_surface_decisions',
  {
    id: text('id').primaryKey().default(sql`gen_random_uuid()::text`),
    scope: decisionScopeEnum('scope').notNull(),
    unitId: text('unit_id').notNull(),
    surfaceNormalized: text('surface_normalized').notNull(),
    teacherContextNormalized: text('teacher_context_normalized'),
    studentContextNormalized: text('student_context_normalized'),
    collectionId: text('collection_id').notNull(),
    decisionKind: surfaceDecisionKindEnum('decision_kind').notNull(),
    targetNarratorId: text('target_narrator_id'),
    derivedRelation: text('derived_relation'),
    analyticsExcluded: boolean('analytics_excluded').notNull().default(false),
    citationId: text('citation_id'),
    citedBasisNote: text('cited_basis_note'),
    reviewer: text('reviewer').notNull(),
    attributedScholar: text('attributed_scholar'),
    reviewedAt: timestamp('reviewed_at', { withTimezone: true }).notNull(),
    notes: text('notes'),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('narrator_surface_decisions_collection_id_fk', table.collectionId, collections.id),
    restrictForeignKey('narrator_surface_decisions_target_narrator_id_fk', table.targetNarratorId, narrators.id),
    restrictForeignKey('narrator_surface_decisions_citation_id_fk', table.citationId, citations.id),
    check(
      'narrator_surface_decisions_derived_scope_check',
      sql`${table.decisionKind} <> 'derived_relation' or ${table.scope} in ('teacher_and_student_context', 'mention')`,
    ),
    check(
      'narrator_surface_decisions_target_check',
      sql`(${table.decisionKind} in ('same_as', 'derived_relation')) = (${table.targetNarratorId} is not null)`,
    ),
    uniqueIndex('narrator_surface_decisions_live_unit_key')
      .on(table.scope, table.unitId)
      .where(isLive(table.retiredAt)),
    index('narrator_surface_decisions_target_narrator_id_idx').on(table.targetNarratorId),
  ],
);

/** Derived view: lifespan ranges per narrator (hand-written SQL, drizzle/core/0003). */
export const narratorLifespans = pgView('narrator_lifespans', {
  narratorId: text('narrator_id').notNull(),
  birthMin: integer('birth_min'),
  birthMax: integer('birth_max'),
  deathMin: integer('death_min'),
  deathMax: integer('death_max'),
  claimCount: integer('claim_count').notNull(),
  disputed: boolean('disputed').notNull(),
  basis: text('basis').notNull(),
}).existing();

/** Derived materialized view: consecutive verified links only (hand-written SQL, drizzle/core/0003). */
export const narratorTransmissions = pgMaterializedView('narrator_transmissions', {
  studentId: text('student_id').notNull(),
  teacherId: text('teacher_id').notNull(),
  hadithCount: integer('hadith_count').notNull(),
  occurrenceCount: integer('occurrence_count').notNull(),
  confidence: real('confidence'),
  extractionMethods: text('extraction_methods').array().notNull(),
  temporalPlausibility: text('temporal_plausibility').notNull(),
  temporalReason: text('temporal_reason'),
}).existing();

/** Public view: mentions of public hadiths; `narrator_id` only where the mention is a verified link. */
export const publicChainLinks = pgView('public_chain_links', {
  id: text('id').notNull(),
  chainId: text('chain_id').notNull(),
  hadithId: text('hadith_id').notNull(),
  branch: integer('branch').notNull(),
  position: integer('position').notNull(),
  surfaceAr: text('surface_ar').notNull(),
  linkKind: linkKindEnum('link_kind').notNull(),
  resolution: mentionResolutionEnum('resolution').notNull(),
  isLink: boolean('is_link').notNull(),
  narratorId: text('narrator_id'),
  confidence: real('confidence'),
}).existing();

/** Public view: every identity candidate of a public mention with its basis (hand-written SQL, drizzle/core/0006). */
export const publicChainMentionCandidates = pgView('public_chain_mention_candidates', {
  mentionId: text('mention_id').notNull(),
  chainId: text('chain_id').notNull(),
  hadithId: text('hadith_id').notNull(),
  narratorId: text('narrator_id').notNull(),
  basis: mentionCandidateBasisEnum('basis').notNull(),
  detail: text('detail'),
  /** True only for the bases that may set a verified link: confirmed source index, reviewer decision. */
  verifiedBasis: boolean('verified_basis').notNull(),
}).existing();
