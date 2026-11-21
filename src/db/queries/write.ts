/** Curation write envelope: transaction, lock timeout, load guard, audit row (rules 4 and 10, section 10.2). */
import 'server-only';
import { sql, type SQL } from 'drizzle-orm';
import { db } from '@/db/client';
import { curationAudit } from '@/db/schema';

export type CurationErrorCode = 'not_found' | 'refused' | 'invalid' | 'conflict' | 'load_in_progress' | 'unauthorized';

/** A refusal the caller can show; `code` is stable, `message` is reader-facing and never contains SQL. */
export class CurationError extends Error {
  constructor(
    readonly code: CurationErrorCode,
    message: string,
  ) {
    super(message);
    this.name = 'CurationError';
  }
}

export type Transaction = Parameters<Parameters<typeof db.transaction>[0]>[0];

const ACTOR_PATTERN = /^(curator|system):[^\s:][^:]*$/;

/** Postgres constraint violations mapped to reader-facing refusals. */
function translateDatabaseError(error: unknown): unknown {
  if (error instanceof CurationError) return error;
  // drizzle wraps driver errors in DrizzleQueryError; the Postgres fields live on `cause`.
  const source = ((error as { cause?: unknown } | null)?.cause ?? error) as { code?: string; constraint_name?: string } | null;
  const code = source?.code;
  const constraint = source?.constraint_name ?? '';
  if (code === '23514') return new CurationError('invalid', `The change breaks a data rule (${constraint || 'check constraint'}).`);
  if (code === '23505') return new CurationError('conflict', `A live record with the same key already exists (${constraint || 'unique'}).`);
  if (code === '23503') return new CurationError('invalid', `A referenced record does not exist (${constraint || 'foreign key'}).`);
  if (code === '55P03') return new CurationError('load_in_progress', 'The record is locked by another change; try again shortly.');
  return error;
}

/**
 * Runs a curated write in one transaction with `lock_timeout = 3s`, refusing while a dataset load is running.
 * Writes never retry (rule 10).
 */
export async function curationWrite<T>(actor: string, write: (tx: Transaction) => Promise<T>): Promise<T> {
  if (!ACTOR_PATTERN.test(actor)) throw new CurationError('unauthorized', 'A named curator is required.');
  try {
    return await db.transaction(async (tx) => {
      await tx.execute(sql`set local lock_timeout = '3s'`);
      const loading = await tx.execute(sql`select 1 from dataset_versions where load_status = 'loading' limit 1`);
      if (loading.length > 0) throw new CurationError('load_in_progress', 'Data load in progress, try again later.');
      return write(tx);
    });
  } catch (error) {
    throw translateDatabaseError(error);
  }
}

/** Appends the audit row for one change, inside the caller's transaction. */
export async function audit(
  tx: Transaction,
  entry: { actor: string; action: string; entityType: string; entityId: string; before?: unknown; after?: unknown },
): Promise<void> {
  await tx.insert(curationAudit).values({
    actor: entry.actor,
    action: entry.action,
    entityType: entry.entityType,
    entityId: entry.entityId,
    before: entry.before ?? null,
    after: entry.after ?? null,
  });
}

/** Raw statement inside a transaction, rows as plain objects. */
export async function txRows<Row extends Record<string, unknown>>(tx: Transaction, query: SQL): Promise<Row[]> {
  return Array.from(await tx.execute<Row>(query)) as unknown as Row[];
}

/** Locks and returns one live row as JSON, or throws not_found. `table` is a trusted identifier. */
export async function lockLiveRow(tx: Transaction, table: string, id: string, label: string): Promise<Record<string, unknown>> {
  const [row] = await txRows<{ image: Record<string, unknown> }>(
    tx,
    sql`select to_jsonb(r) as image from ${sql.identifier(table)} r where r.id = ${id} and r.retired_at is null for update`,
  );
  if (!row) throw new CurationError('not_found', `${label} not found.`);
  return row.image;
}

/** Builds a partial `set` object from an allowlist: absent keys are skipped, sent keys keep their value or null (rule 5). */
export function allowlistedPatch<Patch extends Record<string, unknown>, Column extends string>(
  patch: Patch,
  columns: Record<keyof Patch & string, Column>,
): Partial<Record<Column, unknown>> {
  const set: Partial<Record<Column, unknown>> = {};
  for (const key of Object.keys(columns) as Array<keyof Patch & string>) {
    if (Object.prototype.hasOwnProperty.call(patch, key)) set[columns[key]] = patch[key] ?? null;
  }
  return set;
}

/** Generates a curation entity ID. */
export function newId(): string {
  return crypto.randomUUID();
}
