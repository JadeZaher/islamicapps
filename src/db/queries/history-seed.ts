/**
 * Idempotent seed writes for curation-owned history rows (locations, historical events, epochs). A seed row is
 * created as `unverified_seed`, never publication-ready, and refreshed only while it is still an untouched seed:
 * once a curator reviews, publishes or retires it, the seed leaves it alone. Every change is audited.
 * See src/db/queries/AGENTS.md §Time and place and src/db/AGENTS.md ("The history seed may refresh ...").
 */
import 'server-only';
import { sql } from 'drizzle-orm';
import { audit, curationWrite, txRows, type Transaction } from './write';

export type SeedTable = 'locations' | 'historical_events' | 'epochs';

const ENTITY_TYPE: Record<SeedTable, string> = {
  locations: 'location',
  historical_events: 'historical_event',
  epochs: 'epoch',
};

/** Seed content by column name. Arrays and objects are written as jsonb. */
export type SeedContent = Record<string, string | number | boolean | null | unknown[] | Record<string, unknown>>;

export interface SeedRow {
  id: string;
  content: SeedContent;
}

export interface SeedOutcome {
  created: string[];
  refreshed: string[];
  unchanged: string[];
  /** Rows a curator has reviewed, published or retired since seeding; their content is not touched. */
  keptCurated: Array<{ id: string; reason: string }>;
}

/** JSON with object keys sorted, so jsonb (which reorders keys) compares equal to the seed value. */
function canonical(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>).sort(([left], [right]) => left.localeCompare(right));
    return `{${entries.map(([key, inner]) => `${JSON.stringify(key)}:${canonical(inner)}`).join(',')}}`;
  }
  return JSON.stringify(value ?? null);
}

function parameter(value: SeedContent[string]) {
  return value !== null && typeof value === 'object' ? sql`${JSON.stringify(value)}::jsonb` : sql`${value}`;
}

/** Why the seed must not touch an existing row, or null when it is still an untouched seed. */
function curatedReason(existing: Record<string, unknown>): string | null {
  if (existing.retired_at) return 'retired by a curator';
  if (existing.verification_status !== 'unverified_seed') return `reviewed (${String(existing.verification_status)})`;
  if (existing.publication_ready === true) return 'marked publication-ready';
  return null;
}

async function seedOne(tx: Transaction, table: SeedTable, actor: string, row: SeedRow, outcome: SeedOutcome): Promise<void> {
  const [existingRow] = await txRows<{ image: Record<string, unknown> }>(
    tx,
    sql`select to_jsonb(r) as image from ${sql.identifier(table)} r where r.id = ${row.id} for update`,
  );
  const existing = existingRow?.image;
  const columns = Object.keys(row.content);

  if (!existing) {
    const allColumns = ['id', ...columns, 'verification_status', 'origin', 'created_by', 'updated_by'];
    const values = [sql`${row.id}`, ...columns.map((column) => parameter(row.content[column])), sql`'unverified_seed'`, sql`'seed'`, sql`${actor}`, sql`${actor}`];
    const [created] = await txRows<{ image: Record<string, unknown> }>(
      tx,
      sql`insert into ${sql.identifier(table)} (${sql.join(allColumns.map((column) => sql.identifier(column)), sql`, `)})
          values (${sql.join(values, sql`, `)}) returning to_jsonb(${sql.identifier(table)}) as image`,
    );
    await audit(tx, { actor, action: 'seed_create', entityType: ENTITY_TYPE[table], entityId: row.id, after: created.image });
    outcome.created.push(row.id);
    return;
  }

  const reason = curatedReason(existing);
  if (reason) {
    outcome.keptCurated.push({ id: row.id, reason });
    return;
  }
  const changed = columns.filter((column) => canonical(existing[column]) !== canonical(row.content[column]));
  if (changed.length === 0) {
    outcome.unchanged.push(row.id);
    return;
  }
  const assignments = changed.map((column) => sql`${sql.identifier(column)} = ${parameter(row.content[column])}`);
  const [after] = await txRows<{ image: Record<string, unknown> }>(
    tx,
    sql`update ${sql.identifier(table)} set ${sql.join(assignments, sql`, `)}, updated_at = now(), updated_by = ${actor}
        where id = ${row.id} and verification_status = 'unverified_seed' and retired_at is null
          ${table === 'locations' ? sql`` : sql`and not publication_ready`}
        returning to_jsonb(${sql.identifier(table)}) as image`,
  );
  await audit(tx, { actor, action: 'seed_refresh', entityType: ENTITY_TYPE[table], entityId: row.id, before: existing, after: after.image });
  outcome.refreshed.push(row.id);
}

/** Seeds one table in one transaction. `locations` has no publication flag: only status and retirement guard it. */
export async function seedHistoryRows(actor: string, table: SeedTable, rows: SeedRow[]): Promise<SeedOutcome> {
  const outcome: SeedOutcome = { created: [], refreshed: [], unchanged: [], keptCurated: [] };
  await curationWrite(actor, async (tx) => {
    for (const row of rows) await seedOne(tx, table, actor, row, outcome);
  });
  return outcome;
}
