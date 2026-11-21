/** Enum value lists for input validation in actions (rule 8); actions may not import the schema directly. */
import 'server-only';
import {
  confidenceLevelEnum,
  curationStatusEnum,
  englishPolicyEnum,
  eventCategoryEnum,
  eventVerificationEnum,
  israIliyyatStatusEnum,
  locationRelationEnum,
  motifCategoryEnum,
  narratorVerdictEnum,
  parallelTypeEnum,
  rightsStatusEnum,
  surfaceDecisionKindEnum,
  decisionScopeEnum,
  tabaqahClassEnum,
} from '@/db/schema';

export const EVENT_CATEGORIES = eventCategoryEnum.enumValues;
export const EVENT_VERIFICATION_STATES = eventVerificationEnum.enumValues;
export const CURATION_STATUSES = curationStatusEnum.enumValues;
export const PARALLEL_TYPES = parallelTypeEnum.enumValues;
export const ISRA_ILIYYAT_STATUSES = israIliyyatStatusEnum.enumValues;
export const CONFIDENCE_LEVELS = confidenceLevelEnum.enumValues;
export const MOTIF_CATEGORIES = motifCategoryEnum.enumValues;
export const RIGHTS_STATUSES = rightsStatusEnum.enumValues;
export const ENGLISH_POLICIES = englishPolicyEnum.enumValues;
export const NARRATOR_VERDICTS = narratorVerdictEnum.enumValues;
export const TABAQAH_CLASSES = tabaqahClassEnum.enumValues;
export const LOCATION_RELATIONS = locationRelationEnum.enumValues;
export const SURFACE_DECISION_KINDS = surfaceDecisionKindEnum.enumValues;
export const DECISION_SCOPES = decisionScopeEnum.enumValues;

export type EventCategory = (typeof EVENT_CATEGORIES)[number];
export type EventVerification = (typeof EVENT_VERIFICATION_STATES)[number];
export type CurationStatus = (typeof CURATION_STATUSES)[number];
export type ParallelType = (typeof PARALLEL_TYPES)[number];
export type IsraIliyyatStatus = (typeof ISRA_ILIYYAT_STATUSES)[number];
export type ConfidenceLevel = (typeof CONFIDENCE_LEVELS)[number];
export type MotifCategory = (typeof MOTIF_CATEGORIES)[number];
export type RightsStatus = (typeof RIGHTS_STATUSES)[number];
export type EnglishPolicy = (typeof ENGLISH_POLICIES)[number];
export type LocationRelation = (typeof LOCATION_RELATIONS)[number];
export type SurfaceDecisionKind = (typeof SURFACE_DECISION_KINDS)[number];
export type DecisionScope = (typeof DECISION_SCOPES)[number];
