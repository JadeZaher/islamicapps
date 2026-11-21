/** Operations tables: dataset_versions (one row per load) and curation_audit. Section 5.3, 5.12. */
import { sql } from 'drizzle-orm';
import {
  bigint,
  boolean,
  check,
  index,
  integer,
  jsonb,
  pgTable,
  text,
  timestamp,
  uniqueIndex,
} from 'drizzle-orm/pg-core';
import { loadStatusEnum, releaseClassEnum } from './enums';

/** One row per bundle load; `is_current` marks the live version. */
export const datasetVersions = pgTable(
  'dataset_versions',
  {
    id: text('id').primaryKey(),
    sourceBundleSha256: text('source_bundle_sha256').notNull(),
    inputDatasetSha256: text('input_dataset_sha256').notNull(),
    rawisSha256: text('rawis_sha256').notNull(),
    legacyMasterSha256: text('legacy_master_sha256').notNull(),
    curationManifestSha256: text('curation_manifest_sha256'),
    extractorVersion: text('extractor_version').notNull(),
    extractorSha256: text('extractor_sha256').notNull(),
    bundleVersion: text('bundle_version').notNull(),
    bundleSchemaVersion: integer('bundle_schema_version').notNull(),
    sourceReleaseState: text('source_release_state').notNull(),
    releaseClass: releaseClassEnum('release_class').notNull(),
    nonReleaseReason: text('non_release_reason'),
    publicOverrideBy: text('public_override_by'),
    publicOverrideReason: text('public_override_reason'),
    publicOverrideAt: timestamp('public_override_at', { withTimezone: true }),
    loadPurpose: text('load_purpose').notNull(),
    loadStatus: loadStatusEnum('load_status').notNull(),
    isCurrent: boolean('is_current').notNull().default(false),
    versionLabel: text('version_label'),
    expectedRecordCount: integer('expected_record_count'),
    counts: jsonb('counts').notNull().default(sql`'{}'::jsonb`),
    attributionDisclaimer: text('attribution_disclaimer').notNull(),
    loadedBy: text('loaded_by').notNull(),
    startedAt: timestamp('started_at', { withTimezone: true }).notNull().defaultNow(),
    completedAt: timestamp('completed_at', { withTimezone: true }),
    networkRefreshedAt: timestamp('network_refreshed_at', { withTimezone: true }),
    gitHead: text('git_head'),
  },
  (table) => [
    uniqueIndex('dataset_versions_is_current_key').on(table.isCurrent).where(sql`${table.isCurrent}`),
    check(
      'dataset_versions_curation_manifest_check',
      sql`${table.sourceReleaseState} <> 'development_nonrelease' or ${table.curationManifestSha256} is not null`,
    ),
    check(
      'dataset_versions_public_override_complete_check',
      sql`num_nonnulls(${table.publicOverrideBy}, ${table.publicOverrideReason}, ${table.publicOverrideAt}) in (0, 3)`,
    ),
    check(
      'dataset_versions_public_override_non_release_check',
      sql`${table.publicOverrideBy} is null or ${table.releaseClass} = 'non_release'`,
    ),
  ],
);

/** Append-only audit of every curated write, written in the same transaction as the change. */
export const curationAudit = pgTable(
  'curation_audit',
  {
    id: bigint('id', { mode: 'number' }).primaryKey().generatedAlwaysAsIdentity(),
    occurredAt: timestamp('occurred_at', { withTimezone: true }).notNull().defaultNow(),
    actor: text('actor').notNull(),
    action: text('action').notNull(),
    entityType: text('entity_type').notNull(),
    entityId: text('entity_id').notNull(),
    before: jsonb('before'),
    after: jsonb('after'),
    requestId: text('request_id'),
  },
  (table) => [
    index('curation_audit_entity_idx').on(table.entityType, table.entityId, table.occurredAt.desc()),
  ],
);
