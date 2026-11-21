/** Every Postgres enum in data-architecture.md section 5.2. See src/db/AGENTS.md §Enums. */
import { pgEnum } from 'drizzle-orm/pg-core';

export const hadithTraditionEnum = pgEnum('hadith_tradition', ['Sunni', 'Imami', 'Zaydi', 'Ibadi']);

export const gradeSchemeEnum = pgEnum('grade_scheme', [
  'sunni_7tier',
  'imami_4tier',
  'zaydi_3tier',
  'ibadi_2tier',
  'unspecified',
]);

export const releaseClassEnum = pgEnum('release_class', ['release', 'non_release']);

export const loadStatusEnum = pgEnum('load_status', ['loading', 'complete', 'failed']);

export const rightsStatusEnum = pgEnum('rights_status', ['cleared', 'pending', 'restricted']);

export const englishPolicyEnum = pgEnum('english_policy', ['reviewed_only', 'source_provided_allowed']);

export const narrationLevelEnum = pgEnum('narration_level', ['marfu', 'imam', 'mawquf', 'maqtu', 'unknown']);

export const sourceTextStatusEnum = pgEnum('source_text_status', [
  'present_locator_bound',
  'present',
  'missing',
]);

export const chainStatusEnum = pgEnum('chain_status', [
  'complete',
  'partial',
  'unresolved',
  'absent_in_source',
  'extraction_failed',
]);

export const gradingStatusEnum = pgEnum('grading_status', [
  'cited_assessments',
  'compiler_criterion',
  'none_recorded',
]);

export const translationStateEnum = pgEnum('translation_state', [
  'human_verified',
  'source_verified',
  'source_provided',
  'machine_unreviewed',
  'unknown_provenance',
]);

export const narratorAuthorityEnum = pgEnum('narrator_authority', ['rawi', 'imami_rijal']);

export const tabaqahClassEnum = pgEnum('tabaqah_class', [
  'PROPHET',
  'SAHABA',
  'TABIUN',
  'ATBA_TABIUN',
  'ATBA_ATBA',
  'LATER_SCHOLAR',
]);

export const linkKindEnum = pgEnum('link_kind', [
  'unclassified',
  'person',
  'derived_relation',
  'collective',
  'anonymous',
  'not_a_narrator',
]);

export const mentionResolutionEnum = pgEnum('mention_resolution', [
  'unresolved',
  'exact_registry',
  'source_index',
  'human_verified',
  'derived_relation_verified',
  'undecidable',
]);

export const resolutionBasisEnum = pgEnum('resolution_basis', [
  'report_atomic',
  'mention_exact',
  'source_index',
  'human_decision',
]);

export const surfaceDecisionKindEnum = pgEnum('surface_decision_kind', [
  'same_as',
  'derived_relation',
  'collective',
  'anonymous',
  'not_a_narrator',
  'undecidable',
]);

export const decisionScopeEnum = pgEnum('decision_scope', [
  'teacher_context',
  'teacher_and_student_context',
  'mention',
]);

export const assessmentKindEnum = pgEnum('assessment_kind', [
  'cited_ruling',
  'compiler_criterion',
  'compiler_statement',
  'collection_label',
]);

export const gradeCanonicalEnum = pgEnum('grade_canonical', [
  'sahih',
  'hasan',
  'muwaththaq',
  'da_if',
  'majhul',
  'mursal',
  'mawdu',
  'mu_tabar',
  'mukhtalaf',
  'ungraded',
]);

export const narratorVerdictEnum = pgEnum('narrator_verdict', [
  'thiqa',
  'thiqa_thabt',
  'saduq',
  'la_basa_bihi',
  'majhul',
  'daif',
  'matruk',
  'kadhab',
  'mukhtalaf_fihi',
  'not_applicable',
]);

export const narratorAssessmentKindEnum = pgEnum('narrator_assessment_kind', [
  'critic_ruling',
  'consensus_summary',
]);

export const curationStatusEnum = pgEnum('curation_status', ['proposed', 'verified', 'published']);

export const evidenceReviewStateEnum = pgEnum('evidence_review_state', [
  'candidate_only',
  'lexicon_unverified',
  'source_provided',
  'source_verified',
  'human_verified',
]);

export const eventVerificationEnum = pgEnum('event_verification', [
  'unverified',
  'unverified_seed',
  'human_verified',
  'source_verified',
]);

export const eventCategoryEnum = pgEnum('event_category', [
  'PROPHETIC_ERA',
  'RASHIDUN',
  'UMAYYAD',
  'ABBASID',
  'SCHOLARLY',
  'MILITARY',
  'POLITICAL',
  'SOCIAL',
  'RELIGIOUS',
  'SCIENTIFIC',
  'CULTURAL',
  'ECONOMIC',
]);

export const locationRelationEnum = pgEnum('location_relation', ['born', 'died', 'resided']);

export const calendarEnum = pgEnum('calendar', ['hijri', 'gregorian']);

export const parallelTypeEnum = pgEnum('parallel_type', [
  'CONDEMNATION',
  'CULTURAL_BLEED',
  'SHARED_SOURCE',
  'DIRECT_BORROWING',
  'APOLOGETIC',
  'DISPUTED',
]);

export const israIliyyatStatusEnum = pgEnum('isra_iliyyat_status', [
  'MUWAFIQ',
  'MUKHALIF',
  'MASKUT_ANHU',
  'NONE',
]);

export const confidenceLevelEnum = pgEnum('confidence_level', ['HIGH', 'MEDIUM', 'LOW']);

export const motifCategoryEnum = pgEnum('motif_category', [
  'ESCHATOLOGY',
  'CREATION',
  'PROPHETIC_STORIES',
  'LEGAL',
  'WISDOM',
  'PERSIAN_INFLUENCE',
  'COSMOLOGY',
]);

export const schoolCategoryEnum = pgEnum('school_category', [
  'SUNNI_THEOLOGICAL',
  'SHIA_THEOLOGICAL',
  'IBADI_THEOLOGICAL',
  'SUNNI_MADHHAB',
  'SHIA_MADHHAB',
]);

export const recordOriginEnum = pgEnum('record_origin', ['manual', 'seed', 'ai_research', 'neo4j_migration']);
