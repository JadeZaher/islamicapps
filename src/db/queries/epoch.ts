/** Epochs (eras): admin list and curated edits. Raw SQL: the table ships with a pending migration (src/db/ops/pending/). */
import 'server-only';
import { sql } from 'drizzle-orm';
import { oneRow } from './sql-helpers';
import { epochsAvailable } from './timeline';
import { audit, CurationError, curationWrite, lockLiveRow, txRows } from './write';

export interface EpochRecord {
  id: string;
  name: string;
  name_arabic: string | null;
  alternate_names: Array<{ name: string; name_arabic?: string; used_by: string }>;
  parent_epoch_id: string | null;
  tradition_context: string | null;
  start_year_hijri: number | null;
  start_year_hijri_latest: number | null;
  end_year_hijri: number | null;
  end_year_hijri_latest: number | null;
  boundary_note: string | null;
  overview: string | null;
  verification_status: string;
  publication_ready: boolean;
  citation_id: string | null;
  origin: string;
}

export interface EpochPatch {
  name?: string;
  name_arabic?: string | null;
  start_year_hijri?: number | null;
  start_year_hijri_latest?: number | null;
  end_year_hijri?: number | null;
  end_year_hijri_latest?: number | null;
  boundary_note?: string | null;
  overview?: string | null;
  verification_status?: 'unverified' | 'unverified_seed' | 'human_verified' | 'source_verified';
  publication_ready?: boolean;
  citation_id?: string | null;
}

/** Allowlist: patch keys are column names, so only these may be written. */
const EPOCH_COLUMNS: ReadonlyArray<keyof EpochPatch> = [
  'name', 'name_arabic', 'start_year_hijri', 'start_year_hijri_latest', 'end_year_hijri', 'end_year_hijri_latest',
  'boundary_note', 'overview', 'verification_status', 'publication_ready', 'citation_id',
];

/** Every live epoch, shared periods first, parents before their sub-periods. `available` is false before the migration. */
export async function listEpochs(): Promise<{ available: boolean; items: EpochRecord[] }> {
  if (!(await epochsAvailable())) return { available: false, items: [] };
  const row = await oneRow<{ items: EpochRecord[] }>(sql`
    select coalesce(json_agg(to_jsonb(e) order by e.tradition_context nulls first, coalesce(p.start_year_hijri, e.start_year_hijri),
                             e.parent_epoch_id nulls first, e.start_year_hijri, e.id), '[]'::json) as items
    from epochs e left join epochs p on p.id = e.parent_epoch_id
    where e.retired_at is null`);
  return { available: true, items: row?.items ?? [] };
}

export async function updateEpoch(actor: string, id: string, patch: EpochPatch): Promise<void> {
  const keys = EPOCH_COLUMNS.filter((key) => Object.prototype.hasOwnProperty.call(patch, key));
  if (keys.length === 0) return;
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'epochs', id, 'Epoch');
    const assignments = keys.map((key) => sql`${sql.identifier(key)} = ${patch[key] ?? null}`);
    const [after] = await txRows<{ image: Record<string, unknown> }>(
      tx,
      sql`update epochs set ${sql.join(assignments, sql`, `)}, updated_at = now(), updated_by = ${actor}
          where id = ${id} returning to_jsonb(epochs) as image`,
    );
    await audit(tx, { actor, action: 'update', entityType: 'epoch', entityId: id, before, after: after.image });
  });
}

export async function retireEpoch(actor: string, id: string): Promise<void> {
  await curationWrite(actor, async (tx) => {
    const before = await lockLiveRow(tx, 'epochs', id, 'Epoch');
    const children = await txRows(tx, sql`select 1 from epochs where parent_epoch_id = ${id} and retired_at is null limit 1`);
    if (children.length > 0) throw new CurationError('refused', 'Retire its sub-periods first.');
    await txRows(tx, sql`update epochs set retired_at = now(), retired_by = ${actor}, updated_at = now(), updated_by = ${actor} where id = ${id}`);
    await audit(tx, { actor, action: 'retire', entityType: 'epoch', entityId: id, before });
  });
}
