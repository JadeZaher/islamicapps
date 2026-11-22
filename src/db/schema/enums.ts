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

export const englishPolicyEnum = pgEnum('english_policy', [
  'reviewed_only',
  'source_provided_allowed',
  /** Source-provided and machine English, each shown with its label and credit (owner, 2026-11-21; drizzle/core/0009). */
  'source_provided_and_machine_allowed',
]);

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

/** `hadith_kg`, `riwayat`: an external dataset's own narrator record; `imam_register`: the Imams (0010, src/db/AGENTS.md §External identity). */
export const narratorAuthorityEnum = pgEnum('narrator_authority', ['rawi', 'imami_rijal', 'hadith_kg', 'riwayat', 'imam_register']);

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

/** Where an identity candidate for a mention comes from (owner decisions 2026-11-21; see src/db/AGENTS.md §Identity candidates). */
export const mentionCandidateBasisEnum = pgEnum('mention_candidate_basis', [
  'name_exact',
  'name_spelling_fold',
  'name_kunya_only',
  'source_index',
  'source_index_confirmed_by_text',
  'reviewer_decision',
  'source_hadith_kg',
  'source_hadith_kg_confirmed_by_text',
  'source_riwayat',
  'source_riwayat_confirmed_by_text',
  'imam_kunya_convention',
  'imam_kunya_candidate',
  'named_in_opening_isnad',
]);

/** How a chain mention's Latin name was obtained (0010; src/db/AGENTS.md §Latin names). Never an identification. */
export const nameLatinBasisEnum = pgEnum('name_latin_basis', [
  'provider_english',
  'identity_name',
  'transliteration_vocalized',
  'transliteration_table',
]);

/** Why a lexicon row cannot name one person (`registry_placeholder_reason` in regen_unified_csvs.py). */
export const narratorPlaceholderReasonEnum = pgEnum('narrator_placeholder_reason', [
  'unidentified_shaykh_marker',
  'no_arabic_name',
  'bare_single_token_name',
  'kunya_only_name',
  'relational_name',
  'collective_or_anonymous_name',
  'hadith_kg_stub_narrator',
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

/** How two reports' matns overlap (report-correspondence job; see src/db/AGENTS.md §Report correspondences). */
export const reportCorrespondenceClassEnum = pgEnum('report_correspondence_class', [
  'same_wording',
  'same_report_variant_wording',
  'partial_overlap',
]);

/** Where a correspondence candidate comes from. Only letter-shingle overlap exists today. */
export const reportCorrespondenceBasisEnum = pgEnum('report_correspondence_basis', ['textual_overlap']);

/** Whether the two reports sit in one work, two works of one tradition, or two traditions. */
export const reportCorrespondenceScopeEnum = pgEnum('report_correspondence_scope', [
  'same_work',
  'cross_work_same_tradition',
  'cross_tradition',
]);

/** A reviewer's decision on one report pair. */
export const reportCorrespondenceDecisionEnum = pgEnum('report_correspondence_decision', [
  'confirmed',
  'rejected',
  'uncertain',
]);

/** The reviewer's reading of the pair: the three machine classes plus three readings that are not one report. */
export const reportCorrespondenceReviewedRelationEnum = pgEnum('report_correspondence_reviewed_relation', [
  'same_wording',
  'same_report_variant_wording',
  'partial_overlap',
  'same_ruling_different_attribution',
  'shared_formula_only',
  'shared_quran_quotation',
]);
