/**
 * Enum values in src/db/schema/enums.ts that deliberately have no glossary entry, each with its reason.
 * Every other enum value must be listed in some entry's `enumValues` (checked by __tests__/glossary.test.ts).
 */
import type { EnumValueReference } from './terms';

/** Whole enums no reader or curator sees as a word. */
export const NOT_USER_FACING_ENUMS: Readonly<Record<string, string>> = {
  grade_scheme:
    'Storage key for which tradition’s scale a grade belongs to; the tradition itself is what the app shows. The tier counts in the key names are design labels, not scholarly claims.',
  load_status: 'Loader bookkeeping for a dataset version (loading, complete, failed).',
};

/** Single values no reader or curator sees as a word. */
export const NOT_USER_FACING_VALUES: Readonly<Record<EnumValueReference, string>> = {
  'link_kind.unclassified': 'Default before a mention is classified; the reader sees the name as written.',
  'record_origin.manual': 'Provenance bookkeeping; curator-entered rows carry the curator’s name instead.',
  'record_origin.seed': 'Provenance bookkeeping for seeded rows.',
  'record_origin.neo4j_migration': 'Provenance bookkeeping for rows migrated from the earlier graph store.',
};

/** Values the app shows as ordinary English that needs no definition. */
export const PLAIN_LANGUAGE_VALUES: Readonly<Record<EnumValueReference, string>> = {
  'source_text_status.present': 'Arabic text is present.',
  'source_text_status.missing': 'Arabic text is missing; such rows are not published.',
  'narration_level.unknown': 'Shown as “Unknown”.',
  'tabaqah_class.PROPHET': 'Shown as “The Prophet”.',
  'calendar.gregorian': 'The common-era calendar.',
  'location_relation.born': 'Born.',
  'location_relation.died': 'Died.',
  'location_relation.resided': 'Resided.',
  'event_category.PROPHETIC_ERA': 'The lifetime of the Prophet.',
  'event_category.SCHOLARLY': 'Plain topic label.',
  'event_category.MILITARY': 'Plain topic label.',
  'event_category.POLITICAL': 'Plain topic label.',
  'event_category.SOCIAL': 'Plain topic label.',
  'event_category.RELIGIOUS': 'Plain topic label.',
  'event_category.SCIENTIFIC': 'Plain topic label.',
  'event_category.CULTURAL': 'Plain topic label.',
  'event_category.ECONOMIC': 'Plain topic label.',
  'motif_category.ESCHATOLOGY': 'Plain topic label (the end of time).',
  'motif_category.CREATION': 'Plain topic label.',
  'motif_category.PROPHETIC_STORIES': 'Plain topic label (stories of earlier prophets).',
  'motif_category.LEGAL': 'Plain topic label.',
  'motif_category.WISDOM': 'Plain topic label (wisdom literature).',
  'motif_category.PERSIAN_INFLUENCE': 'Plain topic label.',
  'motif_category.COSMOLOGY': 'Plain topic label.',
  'report_correspondence_scope.same_work': 'Shown as “within one work”.',
  'report_correspondence_scope.cross_work_same_tradition': 'Shown as “across works of one tradition”.',
  'report_correspondence_scope.cross_tradition': 'Shown as “across traditions”.',
};
