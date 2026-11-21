/** zod input schemas for curation actions. Enum values are mapped to canonical values here (rule 8). */
import { z } from 'zod';
import {
  CONFIDENCE_LEVELS,
  CURATION_STATUSES,
  DECISION_SCOPES,
  ENGLISH_POLICIES,
  EVENT_CATEGORIES,
  EVENT_VERIFICATION_STATES,
  ISRA_ILIYYAT_STATUSES,
  MOTIF_CATEGORIES,
  PARALLEL_TYPES,
  RIGHTS_STATUSES,
  SURFACE_DECISION_KINDS,
} from '@/db/queries/enums';

export const idSchema = z.string().trim().min(1).max(200);

/** Absent stays absent; blank becomes null (a clear); text is trimmed. */
const optionalText = (max = 20_000) =>
  z.preprocess((value) => (typeof value === 'string' && value.trim() === '' ? null : value), z.string().trim().max(max).nullable()).optional();

/** Absent stays absent; blank becomes null; numeric strings become numbers. */
const optionalNumber = (schema: z.ZodNumber) =>
  z
    .preprocess((value) => {
      if (value === '' || value === null) return null;
      if (typeof value === 'string') return Number(value);
      return value;
    }, schema.nullable())
    .optional();

const year = () => optionalNumber(z.number().int().min(-5000).max(5000));

/** Upper-cases category input so legacy title-case values (`Political`) map onto the enum. */
const eventCategory = z.preprocess(
  (value) => (typeof value === 'string' ? (value.trim() === '' ? null : value.trim().toUpperCase().replace(/[\s-]+/g, '_')) : value),
  z.enum(EVENT_CATEGORIES).nullable(),
);

const eventFields = {
  title: z.string().trim().min(1).max(500),
  title_arabic: optionalText(500),
  description: optionalText(),
  significance: optionalText(),
  start_year_hijri: year(),
  end_year_hijri: year(),
  start_year_gregorian: year(),
  end_year_gregorian: year(),
  /** Legacy aliases of the start years. */
  year_hijri: year(),
  year_gregorian: year(),
  category: eventCategory.optional(),
  location_name: optionalText(500),
  verification_status: z.enum(EVENT_VERIFICATION_STATES).optional(),
  publication_ready: z.boolean().optional(),
  citation_source: optionalText(1000),
  citation_locator: optionalText(1000),
  citation_url: optionalText(2000),
  citation_retrieved_at: z
    .preprocess((value) => (value === '' ? null : value), z.coerce.date().nullable())
    .optional(),
};

/** Folds `year_hijri` / `year_gregorian` into the canonical start years, only where the caller sent them. */
function foldEventAliases<T extends { year_hijri?: number | null; year_gregorian?: number | null; start_year_hijri?: number | null; start_year_gregorian?: number | null }>(
  value: T,
) {
  const { year_hijri: yearHijri, year_gregorian: yearGregorian, ...rest } = value;
  const folded: Omit<T, 'year_hijri' | 'year_gregorian'> & { start_year_hijri?: number | null; start_year_gregorian?: number | null } = rest;
  if (folded.start_year_hijri === undefined && yearHijri !== undefined) folded.start_year_hijri = yearHijri;
  if (folded.start_year_gregorian === undefined && yearGregorian !== undefined) folded.start_year_gregorian = yearGregorian;
  return folded;
}

export const historicalEventCreateSchema = z.object(eventFields).transform(foldEventAliases);
export const historicalEventPatchSchema = z.object(eventFields).partial().transform(foldEventAliases);

const coordinate = (limit: number) => optionalNumber(z.number().min(-limit).max(limit));

const locationFields = {
  name: z.string().trim().min(1).max(300),
  name_arabic: optionalText(300),
  modern_country: optionalText(200),
  region: optionalText(200),
  description: optionalText(),
  latitude: coordinate(90),
  longitude: coordinate(180),
};

export const locationCreateSchema = z.object(locationFields);
export const locationPatchSchema = z.object(locationFields).partial();

const commentaryFields = {
  text: z.string().trim().min(1).max(50_000),
  text_arabic: optionalText(50_000),
  author: optionalText(300),
  source_work: optionalText(500),
  type: optionalText(100),
  reference: optionalText(1000),
};

export const commentaryCreateSchema = z.object({
  ...commentaryFields,
  hadith_id: optionalText(200),
  narrator_id: optionalText(200),
});

export const commentaryPatchSchema = z.object({ ...commentaryFields, citation_id: optionalText(200) }).partial();

export const curationStatusSchema = z.enum(CURATION_STATUSES);

export const religiousTraditionCreateSchema = z.object({
  name: z.string().trim().min(1).max(200),
  name_arabic: optionalText(200),
  description: optionalText(),
  geographic_origin: optionalText(300),
  geographic_heartlands: z.array(z.string().trim().min(1).max(200)).max(50).optional(),
});
export const religiousTraditionPatchSchema = religiousTraditionCreateSchema.partial();

const sourceTextFields = {
  title: z.string().trim().min(1).max(500),
  title_original: optionalText(500),
  author: optionalText(300),
  approximate_date_ce: optionalText(100),
  canonical_reference: optionalText(300),
  description: optionalText(),
};

/** Create takes the faith directly (`tradition_id`), or `tradition_name` from legacy callers. */
export const sourceTextCreateSchema = z
  .object({ ...sourceTextFields, tradition_id: optionalText(200), tradition_name: optionalText(200) })
  .refine((value) => Boolean(value.tradition_id || value.tradition_name), { message: 'Choose a tradition.' });

export const sourceTextPatchSchema = z
  .object({ ...sourceTextFields, tradition_id: idSchema })
  .partial()
  .transform(({ tradition_id: traditionId, ...rest }) => (traditionId ? { ...rest, religious_tradition_id: traditionId } : rest));

export const motifTagCreateSchema = z.object({
  name: z.string().trim().min(1).max(200),
  category: z.enum(MOTIF_CATEGORIES),
  description: optionalText(),
});

export const motifCategorySchema = z.enum(MOTIF_CATEGORIES);

const parallelPatchFields = {
  parallel_type: z.enum(PARALLEL_TYPES),
  isra_iliyyat_status: z.enum(ISRA_ILIYYAT_STATUSES),
  confidence_level: z.enum(CONFIDENCE_LEVELS),
  hadith_excerpt_en: optionalText(),
  source_text_original: optionalText(),
  source_text_en: optionalText(),
  scholarly_analysis: optionalText(),
};

export const crossParallelCreateSchema = z.object({
  hadith_id: idSchema,
  source_text_id: idSchema,
  tradition_id: idSchema,
  ...parallelPatchFields,
  isra_iliyyat_status: parallelPatchFields.isra_iliyyat_status.optional(),
  confidence_level: parallelPatchFields.confidence_level.optional(),
  motif_tag_ids: z.array(idSchema).max(50).optional(),
});

/** Typed allowlist for updateParallel; unknown keys are stripped, never interpolated. */
export const parallelPatchSchema = z.object(parallelPatchFields).partial();

export const parallelFiltersSchema = z
  .object({
    tradition_id: idSchema.optional(),
    parallel_type: z.enum(PARALLEL_TYPES).optional(),
    isra_iliyyat_status: z.enum(ISRA_ILIYYAT_STATUSES).optional(),
    motif_category: z.enum(MOTIF_CATEGORIES).optional(),
    confidence_level: z.enum(CONFIDENCE_LEVELS).optional(),
  })
  .optional();

export const collectionRightsSchema = z.object({
  rights_status: z.enum(RIGHTS_STATUSES),
  english_policy: z.enum(ENGLISH_POLICIES),
  rights_note: optionalText(5000),
  citation: optionalText(2000),
});

export const surfaceDecisionSchema = z.object({
  scope: z.enum(DECISION_SCOPES),
  unit_id: idSchema,
  decision_kind: z.enum(SURFACE_DECISION_KINDS),
  target_narrator_id: optionalText(200),
  derived_relation: optionalText(200),
  citation_id: optionalText(200),
  cited_basis_note: optionalText(5000),
  attributed_scholar: optionalText(300),
  notes: optionalText(5000),
});

export const chainAbsenceSchema = z
  .object({
    collection_id: optionalText(200),
    hadith_id: optionalText(200),
    reason: z.string().trim().min(1).max(5000),
    citation_id: optionalText(200),
  })
  .refine((value) => Boolean(value.collection_id) !== Boolean(value.hadith_id), {
    message: 'Give exactly one of a collection or a hadith.',
  });

export const searchTermSchema = z.string().max(200).default('');
