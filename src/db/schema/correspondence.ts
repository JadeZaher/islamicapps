/** Report correspondences: machine candidates, cluster members, reviewer decisions. See src/db/AGENTS.md §Report correspondences. */
import { sql } from 'drizzle-orm';
import {
  boolean,
  check,
  index,
  integer,
  pgTable,
  pgView,
  primaryKey,
  real,
  text,
  timestamp,
  unique,
  uniqueIndex,
  type AnyPgColumn,
} from 'drizzle-orm/pg-core';
import {
  curationBookkeeping,
  isLive,
  pipelineBookkeeping,
  pipelineBookkeepingForeignKeys,
  restrictForeignKey,
} from './columns';
import { hadiths } from './corpus';
import {
  reportCorrespondenceBasisEnum,
  reportCorrespondenceClassEnum,
  reportCorrespondenceDecisionEnum,
  reportCorrespondenceReviewedRelationEnum,
  reportCorrespondenceScopeEnum,
} from './enums';
import { citations } from './evidence';

/** Pair order is byte order (`collate "C"`), the projection's order; the database collation would ignore punctuation. */
function orderedPairCheck(name: string, left: AnyPgColumn, right: AnyPgColumn) {
  return check(name, sql`${left} collate "C" < ${right} collate "C"`);
}

/** One unordered report pair per method version, scored on the two matns (pipeline-owned, replaced per load). */
export const reportCorrespondenceCandidates = pgTable(
  'report_correspondence_candidates',
  {
    id: text('id').primaryKey(),
    hadithIdA: text('hadith_id_a').notNull(),
    hadithIdB: text('hadith_id_b').notNull(),
    /** The Arabic the scores were computed on; the projection drops a pair whose text has since changed. */
    arabicSha256A: text('arabic_sha256_a').notNull(),
    arabicSha256B: text('arabic_sha256_b').notNull(),
    relationClass: reportCorrespondenceClassEnum('relation_class').notNull(),
    jaccard: real('jaccard').notNull(),
    containment: real('containment').notNull(),
    globalContainment: real('global_containment').notNull(),
    lengthRatio: real('length_ratio').notNull(),
    sharedShingles: integer('shared_shingles').notNull(),
    shinglesA: integer('shingles_a').notNull(),
    shinglesB: integer('shingles_b').notNull(),
    wordsA: integer('words_a').notNull(),
    wordsB: integer('words_b').notNull(),
    scoreBand: text('score_band').notNull(),
    scope: reportCorrespondenceScopeEnum('scope').notNull(),
    matnSplitA: text('matn_split_a').notNull(),
    matnSplitB: text('matn_split_b').notNull(),
    clusterId: text('cluster_id').notNull(),
    basis: reportCorrespondenceBasisEnum('basis').notNull(),
    methodVersion: text('method_version').notNull(),
    ...pipelineBookkeeping(),
  },
  (table) => [
    unique('report_correspondence_candidates_pair_method_key').on(table.hadithIdA, table.hadithIdB, table.methodVersion),
    restrictForeignKey('report_correspondence_candidates_hadith_id_a_fk', table.hadithIdA, hadiths.id),
    restrictForeignKey('report_correspondence_candidates_hadith_id_b_fk', table.hadithIdB, hadiths.id),
    orderedPairCheck('report_correspondence_candidates_pair_order_check', table.hadithIdA, table.hadithIdB),
    check(
      'report_correspondence_candidates_scores_check',
      sql`${table.jaccard} between 0 and 1 and ${table.containment} between 0 and 1 and ${table.globalContainment} between 0 and 1`,
    ),
    index('report_correspondence_candidates_hadith_id_b_idx').on(table.hadithIdB),
    index('report_correspondence_candidates_cluster_id_idx').on(table.clusterId),
    ...pipelineBookkeepingForeignKeys('report_corr_candidates', table),
  ],
);

/** Star-cluster membership per method version (pipeline-owned): every paired report sits in exactly one cluster. */
export const reportCorrespondenceClusterMembers = pgTable(
  'report_correspondence_cluster_members',
  {
    methodVersion: text('method_version').notNull(),
    hadithId: text('hadith_id').notNull(),
    clusterId: text('cluster_id').notNull(),
    starCentreHadithId: text('star_centre_hadith_id').notNull(),
    isStarCentre: boolean('is_star_centre').notNull(),
    ...pipelineBookkeeping(),
  },
  (table) => [
    primaryKey({ name: 'report_correspondence_cluster_members_pkey', columns: [table.methodVersion, table.hadithId] }),
    restrictForeignKey('report_correspondence_cluster_members_hadith_id_fk', table.hadithId, hadiths.id),
    restrictForeignKey(
      'report_correspondence_cluster_members_star_centre_hadith_id_fk',
      table.starCentreHadithId,
      hadiths.id,
    ),
    check(
      'report_correspondence_cluster_members_centre_check',
      sql`${table.isStarCentre} = (${table.hadithId} = ${table.starCentreHadithId})`,
    ),
    index('report_correspondence_cluster_members_hadith_id_idx').on(table.hadithId),
    index('report_correspondence_cluster_members_cluster_id_idx').on(table.clusterId),
    ...pipelineBookkeepingForeignKeys('report_corr_cluster_members', table),
  ],
);

/**
 * A reviewer's decision on a report pair (curation-owned, untouched by reloads). Keyed on the pair, not the candidate,
 * so it survives a new method version; bound to the Arabic the reviewer saw. Retire-and-supersede, never delete.
 */
export const reportCorrespondenceDecisions = pgTable(
  'report_correspondence_decisions',
  {
    id: text('id').primaryKey().default(sql`gen_random_uuid()::text`),
    hadithIdA: text('hadith_id_a').notNull(),
    hadithIdB: text('hadith_id_b').notNull(),
    boundArabicSha256A: text('bound_arabic_sha256_a').notNull(),
    boundArabicSha256B: text('bound_arabic_sha256_b').notNull(),
    decision: reportCorrespondenceDecisionEnum('decision').notNull(),
    reviewedRelation: reportCorrespondenceReviewedRelationEnum('reviewed_relation'),
    note: text('note'),
    citationId: text('citation_id'),
    decidedBy: text('decided_by').notNull(),
    decidedAt: timestamp('decided_at', { withTimezone: true }).notNull().defaultNow(),
    supersedesDecisionId: text('supersedes_decision_id'),
    ...curationBookkeeping(),
  },
  (table) => [
    restrictForeignKey('report_correspondence_decisions_hadith_id_a_fk', table.hadithIdA, hadiths.id),
    restrictForeignKey('report_correspondence_decisions_hadith_id_b_fk', table.hadithIdB, hadiths.id),
    restrictForeignKey('report_correspondence_decisions_citation_id_fk', table.citationId, citations.id),
    restrictForeignKey(
      'report_correspondence_decisions_supersedes_decision_id_fk',
      table.supersedesDecisionId,
      table.id,
    ),
    orderedPairCheck('report_correspondence_decisions_pair_order_check', table.hadithIdA, table.hadithIdB),
    // A confirmation says the two texts carry one report or passage; the other three readings say they do not.
    check(
      'report_correspondence_decisions_confirmed_relation_check',
      sql`${table.decision} <> 'confirmed' or ${table.reviewedRelation} is null
          or ${table.reviewedRelation} in ('same_wording', 'same_report_variant_wording', 'partial_overlap')`,
    ),
    check(
      'report_correspondence_decisions_retired_check',
      sql`num_nonnulls(${table.retiredAt}, ${table.retiredBy}) in (0, 2)`,
    ),
    uniqueIndex('report_correspondence_decisions_live_pair_key')
      .on(table.hadithIdA, table.hadithIdB)
      .where(isLive(table.retiredAt)),
    index('report_correspondence_decisions_hadith_id_b_idx').on(table.hadithIdB),
  ],
);

/** The display rule, one row per unordered pair (hand-written SQL, drizzle/core/0007). */
export const reportCorrespondenceShownPairs = pgView('report_correspondence_shown_pairs', {
  hadithIdA: text('hadith_id_a').notNull(),
  hadithIdB: text('hadith_id_b').notNull(),
  candidateId: text('candidate_id'),
  relationClass: reportCorrespondenceClassEnum('relation_class'),
  jaccard: real('jaccard'),
  containment: real('containment'),
  scope: reportCorrespondenceScopeEnum('scope'),
  decisionId: text('decision_id'),
  decision: reportCorrespondenceDecisionEnum('decision'),
  reviewedRelation: reportCorrespondenceReviewedRelationEnum('reviewed_relation'),
}).existing();

/** Columns of the two directional correspondence views (hand-written SQL, drizzle/core/0007). */
function correspondenceViewColumns() {
  return {
    hadithId: text('hadith_id').notNull(),
    correspondingHadithId: text('corresponding_hadith_id').notNull(),
    candidateId: text('candidate_id'),
    relationClass: reportCorrespondenceClassEnum('relation_class'),
    jaccard: real('jaccard'),
    containment: real('containment'),
    scope: reportCorrespondenceScopeEnum('scope'),
    decisionId: text('decision_id'),
    decision: reportCorrespondenceDecisionEnum('decision'),
    reviewedRelation: reportCorrespondenceReviewedRelationEnum('reviewed_relation'),
    confirmed: boolean('confirmed').notNull(),
  };
}

/** Display rule over live reports, either publication state: shown pairs, both directions. Reviewer reads use it. */
export const reportCorrespondenceDisplay = pgView('report_correspondence_display', correspondenceViewColumns()).existing();

/** Public view: the display rule restricted to pairs whose two reports are both public. */
export const publicReportCorrespondences = pgView('public_report_correspondences', correspondenceViewColumns()).existing();
