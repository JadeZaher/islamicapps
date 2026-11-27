/** Multi-axis timelines and cultural-contact grid tables (0025): tracks, place snapshots, narrator residences/affiliations, and cited external-tradition parallels. */
import { sql } from 'drizzle-orm';
import { check, index, integer, jsonb, pgTable, text, unique } from 'drizzle-orm/pg-core';
import { pipelineBookkeeping, pipelineBookkeepingForeignKeys, restrictForeignKey } from './columns';
import { hadiths } from './corpus';
import { evidenceReviewStateEnum } from './enums';
import { citations } from './evidence';
import { locations } from './history';
import { narrators } from './narrators';

/** A thematic timeline track for grouping historical, political, technological, intellectual, or demographic events. */
export const timelineTracks = pgTable(
  'timeline_tracks',
  {
    id: text('id').primaryKey(),
    slug: text('slug').notNull(),
    title: text('title').notNull(),
    category: text('category').notNull(),
    scope: text('scope').notNull(),
    description: text('description'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    unique('timeline_tracks_slug_key').on(table.slug),
    check(
      'timeline_tracks_category_check',
      sql`${table.category} in ('political', 'world_event', 'technological', 'intellectual_movement', 'demographic_shift', 'legal_theological', 'trade_pilgrimage', 'social_gender_norms', 'myths_literature_art', 'food_agriculture_ecology', 'economic_tensions')`,
    ),
    check('timeline_tracks_scope_check', sql`${table.scope} in ('global', 'regional', 'city')`),
    index('timeline_tracks_category_idx').on(table.category),
    ...pipelineBookkeepingForeignKeys('timeline_tracks', table),
  ],
);

/** Time-sliced demographic, political, religious, and ethnographic profile of a location. */
export const placeSnapshots = pgTable(
  'place_snapshots',
  {
    id: text('id').primaryKey(),
    locationId: text('location_id').notNull(),
    yearMin: integer('year_min'),
    yearMax: integer('year_max'),
    precision: text('precision'),
    polityOrRuler: text('polity_or_ruler'),
    dominantSchools: text('dominant_schools').array().notNull().default(sql`'{}'::text[]`),
    religiousCommunities: jsonb('religious_communities').notNull().default(sql`'{}'::jsonb`),
    languages: text('languages').array().notNull().default(sql`'{}'::text[]`),
    ethnographicNotes: text('ethnographic_notes'),
    socialNorms: jsonb('social_norms'),
    materialCulture: jsonb('material_culture'),
    citationId: text('citation_id').notNull(),
    reviewState: evidenceReviewStateEnum('review_state').notNull().default('candidate_only'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('place_snapshots_location_id_fk', table.locationId, locations.id),
    restrictForeignKey('place_snapshots_citation_id_fk', table.citationId, citations.id),
    check(
      'place_snapshots_year_range_check',
      sql`${table.yearMin} is null or ${table.yearMax} is null or ${table.yearMax} >= ${table.yearMin}`,
    ),
    check(
      'place_snapshots_religious_communities_check',
      sql`jsonb_typeof(${table.religiousCommunities}) = 'object'`,
    ),
    index('place_snapshots_location_id_idx').on(table.locationId),
    index('place_snapshots_year_range_idx').on(table.yearMin, table.yearMax),
    index('place_snapshots_location_year_range_idx').on(table.locationId, table.yearMin, table.yearMax),
    index('place_snapshots_citation_id_idx').on(table.citationId),
    index('place_snapshots_review_state_idx').on(table.reviewState),
    ...pipelineBookkeepingForeignKeys('place_snapshots', table),
  ],
);

/** Attested residence, study, teaching, office, or rihla visit of a narrator at a location over a time range. */
export const narratorResidences = pgTable(
  'narrator_residences',
  {
    id: text('id').primaryKey(),
    narratorId: text('narrator_id').notNull(),
    locationId: text('location_id').notNull(),
    yearMin: integer('year_min'),
    yearMax: integer('year_max'),
    precision: text('precision'),
    role: text('role').notNull(),
    citationId: text('citation_id').notNull(),
    reviewState: evidenceReviewStateEnum('review_state').notNull().default('candidate_only'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('narrator_residences_narrator_id_fk', table.narratorId, narrators.id),
    restrictForeignKey('narrator_residences_location_id_fk', table.locationId, locations.id),
    restrictForeignKey('narrator_residences_citation_id_fk', table.citationId, citations.id),
    check(
      'narrator_residences_year_range_check',
      sql`${table.yearMin} is null or ${table.yearMax} is null or ${table.yearMax} >= ${table.yearMin}`,
    ),
    check(
      'narrator_residences_role_check',
      sql`${table.role} in ('born', 'studied', 'taught', 'qadi', 'governor', 'rihla_visit', 'died')`,
    ),
    index('narrator_residences_narrator_id_idx').on(table.narratorId),
    index('narrator_residences_location_id_idx').on(table.locationId),
    index('narrator_residences_year_range_idx').on(table.yearMin, table.yearMax),
    index('narrator_residences_citation_id_idx').on(table.citationId),
    index('narrator_residences_review_state_idx').on(table.reviewState),
    ...pipelineBookkeepingForeignKeys('narrator_residences', table),
  ],
);

/** Attested social, tribal, scholarly, political, or professional affiliation of a narrator. */
export const narratorAffiliations = pgTable(
  'narrator_affiliations',
  {
    id: text('id').primaryKey(),
    narratorId: text('narrator_id').notNull(),
    kind: text('kind').notNull(),
    label: text('label').notNull(),
    note: text('note'),
    citationId: text('citation_id').notNull(),
    reviewState: evidenceReviewStateEnum('review_state').notNull().default('candidate_only'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('narrator_affiliations_narrator_id_fk', table.narratorId, narrators.id),
    restrictForeignKey('narrator_affiliations_citation_id_fk', table.citationId, citations.id),
    check(
      'narrator_affiliations_kind_check',
      sql`${table.kind} in ('tribe', 'mawla_of', 'legal_school', 'theological_tendency', 'political_faction', 'convert_background', 'profession')`,
    ),
    index('narrator_affiliations_narrator_id_idx').on(table.narratorId),
    index('narrator_affiliations_kind_idx').on(table.kind),
    index('narrator_affiliations_citation_id_idx').on(table.citationId),
    index('narrator_affiliations_review_state_idx').on(table.reviewState),
    ...pipelineBookkeepingForeignKeys('narrator_affiliations', table),
  ],
);

/** Cited scholarly observation of an external-tradition parallel or Isra'iliyyat motif for a hadith. */
export const externalTraditionParallels = pgTable(
  'external_tradition_parallels',
  {
    id: text('id').primaryKey(),
    hadithId: text('hadith_id').notNull(),
    traditionSource: text('tradition_source').notNull(),
    relationType: text('relation_type').notNull(),
    sourceWork: text('source_work').notNull(),
    locator: text('locator'),
    note: text('note'),
    citationId: text('citation_id').notNull(),
    reviewState: evidenceReviewStateEnum('review_state').notNull().default('candidate_only'),
    ...pipelineBookkeeping(),
  },
  (table) => [
    restrictForeignKey('external_tradition_parallels_hadith_id_fk', table.hadithId, hadiths.id),
    restrictForeignKey('external_tradition_parallels_citation_id_fk', table.citationId, citations.id),
    check(
      'external_tradition_parallels_tradition_source_check',
      sql`${table.traditionSource} in ('biblical', 'midrash_talmud', 'syriac_christian', 'sasanian_andarz', 'pre_islamic_poetry', 'ancient_near_eastern_myth', 'arabian_folklore', 'greco_roman', 'poetry_adab', 'other')`,
    ),
    check(
      'external_tradition_parallels_relation_type_check',
      sql`${table.relationType} in ('direct_quote', 'structural_parallel', 'shared_motif', 'polemical_response')`,
    ),
    index('external_tradition_parallels_hadith_id_idx').on(table.hadithId),
    index('external_tradition_parallels_tradition_source_idx').on(table.traditionSource),
    index('external_tradition_parallels_citation_id_idx').on(table.citationId),
    index('external_tradition_parallels_review_state_idx').on(table.reviewState),
    ...pipelineBookkeepingForeignKeys('external_tradition_parallels', table),
  ],
);
