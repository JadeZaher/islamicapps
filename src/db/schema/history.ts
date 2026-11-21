/** History tables (section 5.9): locations, events, narrator links, epochs, and the published-events and published-epochs views. */
import { sql } from 'drizzle-orm';
import {
  boolean,
  check,
  doublePrecision,
  index,
  integer,
  jsonb,
  pgTable,
  pgView,
  text,
  timestamp,
  uniqueIndex,
} from 'drizzle-orm/pg-core';
import { curationBookkeeping, isLive, linkBookkeeping, restrictForeignKey } from './columns';
import { eventCategoryEnum, eventVerificationEnum, hadithTraditionEnum, locationRelationEnum, recordOriginEnum } from './enums';
import { citations } from './evidence';
import { narrators } from './narrators';

/** A place, seeded or curated. */
export const locations = pgTable(
  'locations',
  {
    id: text('id').primaryKey(),
    name: text('name').notNull(),
    nameArabic: text('name_arabic'),
    modernCountry: text('modern_country'),
    region: text('region'),
    description: text('description'),
    latitude: doublePrecision('latitude'),
    longitude: doublePrecision('longitude'),
    verificationStatus: eventVerificationEnum('verification_status').notNull().default('unverified'),
    origin: recordOriginEnum('origin').notNull(),
    ...curationBookkeeping(),
  },
  (table) => [
    check('locations_latitude_check', sql`${table.latitude} between -90 and 90`),
    check('locations_longitude_check', sql`${table.longitude} between -180 and 180`),
  ],
);

/** Columns of historical_events, shared with the published_historical_events view declaration. */
function historicalEventColumns() {
  return {
    id: text('id').primaryKey(),
    title: text('title').notNull(),
    titleArabic: text('title_arabic'),
    description: text('description'),
    significance: text('significance'),
    startYearHijri: integer('start_year_hijri'),
    endYearHijri: integer('end_year_hijri'),
    startYearGregorian: integer('start_year_gregorian'),
    endYearGregorian: integer('end_year_gregorian'),
    category: eventCategoryEnum('category'),
    locationName: text('location_name'),
    locationId: text('location_id'),
    verificationStatus: eventVerificationEnum('verification_status').notNull().default('unverified'),
    publicationReady: boolean('publication_ready').notNull().default(false),
    citationSource: text('citation_source'),
    citationLocator: text('citation_locator'),
    citationUrl: text('citation_url'),
    citationRetrievedAt: timestamp('citation_retrieved_at', { withTimezone: true }),
    citationId: text('citation_id'),
    origin: recordOriginEnum('origin').notNull(),
    ...curationBookkeeping(),
  };
}

/** A historical event; the publish gate is a check constraint here and a view on read. */
export const historicalEvents = pgTable('historical_events', historicalEventColumns(), (table) => [
  restrictForeignKey('historical_events_location_id_fk', table.locationId, locations.id),
  restrictForeignKey('historical_events_citation_id_fk', table.citationId, citations.id),
  check(
    'historical_events_year_order_check',
    sql`${table.startYearHijri} is null or ${table.endYearHijri} is null or ${table.endYearHijri} >= ${table.startYearHijri}`,
  ),
  check(
    'historical_events_publication_gate_check',
    sql`not ${table.publicationReady} or (${table.verificationStatus} in ('human_verified', 'source_verified') and nullif(trim(${table.citationSource}), '') is not null and (nullif(trim(${table.citationLocator}), '') is not null or nullif(trim(${table.citationUrl}), '') is not null))`,
  ),
  index('historical_events_year_range_idx').on(table.startYearHijri, table.endYearHijri),
  index('historical_events_category_idx').on(table.category),
  index('historical_events_published_start_idx')
    .on(table.startYearHijri)
    .where(sql`${table.publicationReady}`),
]);

/** Link: a narrator's involvement in an event. */
export const narratorEvents = pgTable(
  'narrator_events',
  {
    ...linkBookkeeping(),
    narratorId: text('narrator_id').notNull(),
    eventId: text('event_id').notNull(),
    role: text('role').notNull().default('Participant'),
  },
  (table) => [
    restrictForeignKey('narrator_events_narrator_id_fk', table.narratorId, narrators.id),
    restrictForeignKey('narrator_events_event_id_fk', table.eventId, historicalEvents.id),
    uniqueIndex('narrator_events_live_key')
      .on(table.narratorId, table.eventId, table.role)
      .where(isLive(table.retiredAt)),
    index('narrator_events_event_id_idx').on(table.eventId),
  ],
);

/** Link: a narrator born in, died in or resided at a location. */
export const narratorLocations = pgTable(
  'narrator_locations',
  {
    ...linkBookkeeping(),
    narratorId: text('narrator_id').notNull(),
    locationId: text('location_id').notNull(),
    relation: locationRelationEnum('relation').notNull(),
  },
  (table) => [
    restrictForeignKey('narrator_locations_narrator_id_fk', table.narratorId, narrators.id),
    restrictForeignKey('narrator_locations_location_id_fk', table.locationId, locations.id),
    uniqueIndex('narrator_locations_live_key')
      .on(table.narratorId, table.locationId, table.relation)
      .where(isLive(table.retiredAt)),
    index('narrator_locations_location_id_idx').on(table.locationId),
  ],
);

/** View: live events that pass the publish gate, with permissive interval bounds (drizzle/core/0003). */
export const publishedHistoricalEvents = pgView('published_historical_events', {
  ...historicalEventColumns(),
  eventStart: integer('event_start').notNull(),
  eventEnd: integer('event_end').notNull(),
}).existing();

// Epochs (migration 0008, promoted from src/db/ops/pending on 2026-11-21).
/** A name a tradition or language uses for the period, beside the neutral descriptive `name`. */
export interface EpochAlternateName {
  name: string;
  name_arabic?: string;
  /** Who uses the name: a tradition code ('Sunni', 'Imami', 'Zaydi', 'Ibadi') or 'historians'. */
  used_by: string;
}

function epochColumns() {
  return {
    id: text('id').primaryKey(),
    name: text('name').notNull(),
    nameArabic: text('name_arabic'),
    alternateNames: jsonb('alternate_names').$type<EpochAlternateName[]>().notNull().default(sql`'[]'::jsonb`),
    parentEpochId: text('parent_epoch_id'),
    /** The tradition whose own reckoning frames the period; null for a period every tradition dates alike. */
    traditionContext: hadithTraditionEnum('tradition_context'),
    startYearHijri: integer('start_year_hijri'),
    /** Set only when the start is disputed: the start lies in [start_year_hijri, start_year_hijri_latest]. */
    startYearHijriLatest: integer('start_year_hijri_latest'),
    endYearHijri: integer('end_year_hijri'),
    endYearHijriLatest: integer('end_year_hijri_latest'),
    boundaryNote: text('boundary_note'),
    overview: text('overview'),
    verificationStatus: eventVerificationEnum('verification_status').notNull().default('unverified'),
    publicationReady: boolean('publication_ready').notNull().default(false),
    citationId: text('citation_id'),
    origin: recordOriginEnum('origin').notNull(),
    ...curationBookkeeping(),
  };
}

/** An era: Hijri range (a range per boundary where disputed), neutral name, labelled alternates, publish gate. */
export const epochs = pgTable('epochs', epochColumns(), (table) => [
  restrictForeignKey('epochs_parent_epoch_id_fk', table.parentEpochId, table.id),
  restrictForeignKey('epochs_citation_id_fk', table.citationId, citations.id),
  check('epochs_alternate_names_check', sql`jsonb_typeof(${table.alternateNames}) = 'array'`),
  check(
    'epochs_start_range_check',
    sql`${table.startYearHijriLatest} is null or (${table.startYearHijri} is not null and ${table.startYearHijriLatest} >= ${table.startYearHijri})`,
  ),
  check(
    'epochs_end_range_check',
    sql`${table.endYearHijriLatest} is null or (${table.endYearHijri} is not null and ${table.endYearHijriLatest} >= ${table.endYearHijri})`,
  ),
  check(
    'epochs_year_order_check',
    sql`${table.startYearHijri} is null or ${table.endYearHijri} is null or coalesce(${table.endYearHijriLatest}, ${table.endYearHijri}) >= ${table.startYearHijri}`,
  ),
  check(
    'epochs_publication_gate_check',
    sql`not ${table.publicationReady} or (${table.verificationStatus} in ('human_verified', 'source_verified') and ${table.citationId} is not null)`,
  ),
  index('epochs_year_range_idx').on(table.startYearHijri, table.endYearHijri).where(sql`${table.retiredAt} is null`),
  index('epochs_parent_epoch_id_idx').on(table.parentEpochId),
]);

/** View: live epochs that pass the publish gate and cite a live reviewed citation, with outer bounds. */
export const publishedEpochs = pgView('published_epochs', {
  ...epochColumns(),
  epochStart: integer('epoch_start').notNull(),
  epochEnd: integer('epoch_end'),
}).existing();
