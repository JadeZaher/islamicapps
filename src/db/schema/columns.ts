/** Shared column groups (section 5.1) and the restrict-by-default foreign key helper. */
import { sql } from 'drizzle-orm';
import {
  bigint,
  foreignKey,
  text,
  timestamp,
  type AnyPgColumn,
  type PgColumn,
} from 'drizzle-orm/pg-core';
import { datasetVersions } from './operations';

/** Foreign key with an explicit name and `on delete restrict` (the section 5.1 default). */
export function restrictForeignKey(name: string, column: PgColumn, foreignColumn: AnyPgColumn) {
  return foreignKey({ name, columns: [column], foreignColumns: [foreignColumn] }).onDelete('restrict');
}

/** Pipeline bookkeeping: which loads created, changed and retired the row. */
export function pipelineBookkeeping() {
  return {
    firstSeenDatasetVersionId: text('first_seen_dataset_version_id').notNull(),
    changedInDatasetVersionId: text('changed_in_dataset_version_id').notNull(),
    updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
    retiredAt: timestamp('retired_at', { withTimezone: true }),
    retiredInDatasetVersionId: text('retired_in_dataset_version_id'),
  };
}

type PipelineBookkeepingColumns = {
  firstSeenDatasetVersionId: PgColumn;
  changedInDatasetVersionId: PgColumn;
  retiredInDatasetVersionId: PgColumn;
};

/** The three dataset_versions foreign keys every pipeline table carries. */
export function pipelineBookkeepingForeignKeys(tableName: string, table: PipelineBookkeepingColumns) {
  return [
    restrictForeignKey(
      `${tableName}_first_seen_dataset_version_id_fk`,
      table.firstSeenDatasetVersionId,
      datasetVersions.id,
    ),
    restrictForeignKey(
      `${tableName}_changed_in_dataset_version_id_fk`,
      table.changedInDatasetVersionId,
      datasetVersions.id,
    ),
    restrictForeignKey(
      `${tableName}_retired_in_dataset_version_id_fk`,
      table.retiredInDatasetVersionId,
      datasetVersions.id,
    ),
  ];
}

/** Curation entity bookkeeping: actors and soft delete. */
export function curationBookkeeping() {
  return {
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    createdBy: text('created_by').notNull(),
    updatedAt: timestamp('updated_at', { withTimezone: true }).notNull().defaultNow(),
    updatedBy: text('updated_by').notNull(),
    retiredAt: timestamp('retired_at', { withTimezone: true }),
    retiredBy: text('retired_by'),
  };
}

/** Curation link bookkeeping: identity key, creation actor and soft delete. */
export function linkBookkeeping() {
  return {
    id: bigint('id', { mode: 'number' }).primaryKey().generatedAlwaysAsIdentity(),
    createdAt: timestamp('created_at', { withTimezone: true }).notNull().defaultNow(),
    createdBy: text('created_by').notNull(),
    retiredAt: timestamp('retired_at', { withTimezone: true }),
    retiredBy: text('retired_by'),
  };
}

/** Partial-index predicate for "live" curation rows (section 3.2 rule 6). */
export function isLive(retiredAt: PgColumn) {
  return sql`${retiredAt} is null`;
}
