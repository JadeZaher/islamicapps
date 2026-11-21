/** Anti-join merge by stable id (section 4.3 step 6): guarded upsert, retire-not-delete, derived-column refresh. */
import type { LoaderSql } from './connection';
import { stagingTableName } from './copy';
import { quoteIdentifier, type PipelineTableSpec } from './tables';

export interface MergeResult {
  table: string;
  staged: number;
  inserted: number;
  updated: number;
  derivedUpdated: number;
  retired: number;
  /** Live-before minus staged, counted before the retire statement; must equal `retired` (section 11.4). */
  expectedRetired: number;
}

/** Columns the loader computes during the merge rather than reading from the CSV. */
const COMPUTED_COLUMNS: Record<string, Record<string, string>> = {
  narrators: { name_en_folded: 'lower(unaccent(s."name_en"))' },
};

function keyMatch(spec: PipelineTableSpec, left: string, right: string): string {
  return spec.key.map((column) => `${right}.${quoteIdentifier(column)} = ${left}.${quoteIdentifier(column)}`).join(' and ');
}

/** Merges one table from its staging copy. `versionId` is the dataset version doing the load. */
export async function mergeTable(
  sql: LoaderSql,
  spec: PipelineTableSpec,
  header: string[],
  staged: number,
  versionId: string,
): Promise<MergeResult> {
  const table = quoteIdentifier(spec.name);
  const staging = stagingTableName(spec.name);
  const computed = COMPUTED_COLUMNS[spec.name] ?? {};
  const contentColumns = [
    ...header.filter((column) => !spec.key.includes(column) && !spec.derivedFromStaging.includes(column)),
    ...Object.keys(computed),
  ].map(quoteIdentifier);
  const insertColumns = [...header, ...Object.keys(computed), 'first_seen_dataset_version_id', 'changed_in_dataset_version_id']
    .map(quoteIdentifier)
    .join(', ');
  const selectExpressions = [...header.map((column) => `s.${quoteIdentifier(column)}`), ...Object.values(computed), '$1', '$1'].join(', ');
  const assignments = [
    ...contentColumns.map((column) => `${column} = excluded.${column}`),
    'changed_in_dataset_version_id = excluded.changed_in_dataset_version_id',
    'updated_at = now()',
    'retired_at = null',
    'retired_in_dataset_version_id = null',
  ].join(', ');
  const current = [...contentColumns.map((column) => `t.${column}`), 't.retired_at'].join(', ');
  const incoming = [...contentColumns.map((column) => `excluded.${column}`), 'null::timestamptz'].join(', ');

  const [{ expected_retired: expectedRetired }] = await sql.unsafe<{ expected_retired: number }[]>(
    `select count(*)::int as expected_retired from ${table} t
     where t.retired_at is null and not exists (select 1 from ${staging} s where ${keyMatch(spec, 't', 's')})`,
  );

  // Unchanged rows are not touched at all: no new tuple, no WAL, no index entries.
  const [{ inserted, updated }] = await sql.unsafe<{ inserted: number; updated: number }[]>(
    `with merged as (
       insert into ${table} as t (${insertColumns})
       select ${selectExpressions} from ${staging} s
       on conflict (${spec.key.map(quoteIdentifier).join(', ')}) do update set ${assignments}
       where (${current}) is distinct from (${incoming})
       returning (xmax = 0) as inserted
     )
     select count(*) filter (where inserted)::int as inserted, count(*) filter (where not inserted)::int as updated from merged`,
    [versionId],
  );

  let derivedUpdated = 0;
  if (spec.derivedFromStaging.length > 0) {
    // Automatic resolutions from staging, never over a row a human decision owns (decision_id set).
    const derived = spec.derivedFromStaging.map(quoteIdentifier);
    const rows = await sql.unsafe(
      `update ${table} t set (${derived.join(', ')}) = (${derived.map((column) => `s.${column}`).join(', ')}),
              changed_in_dataset_version_id = $1, updated_at = now()
       from ${staging} s
       where ${keyMatch(spec, 't', 's')} and t.decision_id is null
         and (${derived.map((column) => `t.${column}`).join(', ')}) is distinct from (${derived.map((column) => `s.${column}`).join(', ')})`,
      [versionId],
    );
    derivedUpdated = rows.count;
  }

  const retiredRows = await sql.unsafe(
    `update ${table} t set retired_at = now(), retired_in_dataset_version_id = $1
     where t.retired_at is null and not exists (select 1 from ${staging} s where ${keyMatch(spec, 't', 's')})`,
    [versionId],
  );

  return { table: spec.name, staged, inserted, updated, derivedUpdated, retired: retiredRows.count, expectedRetired };
}

/** Mentions whose id is unchanged but whose normalized surface changed (section 4.2); reported, not fatal. */
export async function countSurfaceChangedUnderSameId(sql: LoaderSql): Promise<number> {
  const [{ changed }] = await sql.unsafe<{ changed: number }[]>(
    `select count(*)::int as changed from chain_mentions m join ${stagingTableName('chain_mentions')} s on s.id = m.id
     where m.surface_normalized is distinct from s.surface_normalized`,
  );
  return changed;
}
