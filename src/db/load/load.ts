/** Bulk load of a verified projection (section 4.3). One session: advisory lock, COPY to staging, one merge transaction. */
import { execFileSync } from 'node:child_process';
import { DATA_WRITE_LOCK_KEY } from '../advisory-locks';
import { headerMismatches, readCatalog } from './catalog';
import type { LoaderSql } from './connection';
import { dropStaging, stageTable } from './copy';
import { verifyProjection, type VerifiedProjection } from './manifest';
import { countSurfaceChangedUnderSameId, mergeTable, type MergeResult } from './merge';
import { PIPELINE_TABLES, quoteIdentifier } from './tables';
import { failedChecks, formatChecks, runDataChecks, type DataCheckReport } from './verify-data';

export interface LoadOptions {
  projectionDirectory: string;
  loadPurpose: string;
  loadedBy: string;
  minimumLiveHadiths?: number;
  log?: (message: string) => void;
}

export interface LoadResult {
  versionId: string;
  /** `reload`: the version was already current and complete; the load must change nothing. */
  mode: 'new' | 'resume' | 'reload';
  merge: MergeResult[];
  facetRowsChanged: number;
  rowsChanged: number;
  networkRefreshed: boolean;
  checks: DataCheckReport;
  databaseBytes: { before: number; after: number };
  timingsMs: Record<string, number>;
}

class LoadAbort extends Error {}

function gitHead(): string | null {
  try {
    return execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  } catch {
    return null;
  }
}

async function databaseBytes(sql: LoaderSql): Promise<number> {
  const [{ bytes }] = await sql.unsafe<{ bytes: string }[]>('select pg_database_size(current_database())::text as bytes');
  return Number(bytes);
}

/** Inserts or re-arms the dataset_versions row; returns how this load relates to it. */
async function prepareVersion(sql: LoaderSql, projection: VerifiedProjection, options: LoadOptions): Promise<LoadResult['mode']> {
  const { manifest } = projection;
  const versionId = manifest.content_sha256;
  const [existing] = await sql.unsafe<{ load_status: string; is_current: boolean }[]>(
    'select load_status::text, is_current from dataset_versions where id = $1',
    [versionId],
  );
  if (existing?.load_status === 'complete' && existing.is_current) return 'reload';
  if (existing) {
    await sql.unsafe(`update dataset_versions set load_status = 'loading', completed_at = null where id = $1`, [versionId]);
    return 'resume';
  }
  await sql.unsafe(
    `insert into dataset_versions (
       id, source_bundle_sha256, input_dataset_sha256, rawis_sha256, legacy_master_sha256, curation_manifest_sha256,
       extractor_version, extractor_sha256, bundle_version, bundle_schema_version, source_release_state, release_class,
       non_release_reason, load_purpose, load_status, is_current, version_label, expected_record_count,
       attribution_disclaimer, loaded_by, git_head)
     values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, 'loading', false, $15, $16, $17, $18, $19)`,
    [
      versionId,
      manifest.source_bundle.content_sha256,
      manifest.inputs.input_dataset_sha256,
      manifest.inputs.rawis_sha256,
      manifest.inputs.legacy_master.sha256,
      manifest.inputs.curation_manifest_sha256,
      manifest.inputs.extractor.version,
      manifest.inputs.extractor.sha256,
      manifest.source_bundle.bundle_version,
      manifest.source_bundle.bundle_schema_version,
      manifest.source_bundle.source_release_state,
      manifest.release.release_class,
      manifest.release.non_release_reason,
      options.loadPurpose,
      `projection ${manifest.projection_version}${manifest.options.source_index ? ` +candidates(${manifest.options.source_index})` : ''}`,
      manifest.source_bundle.expected_record_count,
      manifest.release.attribution_disclaimer,
      options.loadedBy,
      gitHead(),
    ],
  );
  return 'new';
}

/** Runs the whole load. Throws (after rolling back the merge and marking the version failed) on any refusal. */
export async function loadProjection(sql: LoaderSql, options: LoadOptions): Promise<LoadResult> {
  const log = options.log ?? (() => {});
  const timingsMs: Record<string, number> = {};
  const timed = async <T>(label: string, work: () => Promise<T>): Promise<T> => {
    const started = Date.now();
    try {
      return await work();
    } finally {
      timingsMs[label] = Date.now() - started;
    }
  };

  const projection = await timed('verify_projection', () => verifyProjection(options.projectionDirectory));
  const versionId = projection.manifest.content_sha256;
  log(`projection ${versionId} verified (${projection.files.size} tables)`);

  await sql.unsafe(`set statement_timeout = 0`);
  await sql.unsafe(`set lock_timeout = '60s'`);
  await sql.unsafe('select pg_advisory_lock($1::bigint)', [DATA_WRITE_LOCK_KEY]);
  const stagedTables: string[] = [];
  let mode: LoadResult['mode'] | undefined;
  try {
    const catalog = await readCatalog(sql);
    const headerProblems = PIPELINE_TABLES.flatMap((table) =>
      headerMismatches(catalog, table.name, projection.files.get(table.name)!.entry.header),
    );
    if (headerProblems.length > 0) throw new LoadAbort(`CSV headers do not match the live catalog:\n  - ${headerProblems.join('\n  - ')}`);

    const bytesBefore = await databaseBytes(sql);
    const csvBytes = [...projection.files.values()].reduce((sum, file) => sum + file.entry.bytes, 0);
    const volumeBytes = Number(process.env.LOAD_VOLUME_BYTES ?? 0);
    if (volumeBytes > 0 && bytesBefore + 2 * csvBytes > volumeBytes / 2) {
      throw new LoadAbort(`disk budget (section 2.8): database ${bytesBefore} B + 2 x CSV ${csvBytes} B exceeds half of ${volumeBytes} B`);
    }
    log(`database ${bytesBefore} B before load; CSV ${csvBytes} B${volumeBytes > 0 ? '' : '; LOAD_VOLUME_BYTES unset, disk-budget check skipped'}`);

    mode = await prepareVersion(sql, projection, options);
    log(`dataset version ${versionId.slice(0, 12)}: ${mode}`);

    const staged = new Map<string, number>();
    await timed('copy', async () => {
      for (const table of PIPELINE_TABLES) {
        const { absolutePath, entry } = projection.files.get(table.name)!;
        stagedTables.push(table.name);
        const rows = await stageTable(sql, table.name, entry.header, absolutePath);
        if (rows !== entry.row_count) throw new LoadAbort(`${table.name}: staged ${rows} rows, manifest says ${entry.row_count}`);
        staged.set(table.name, rows);
        log(`  copied ${table.name}: ${rows}`);
      }
    });

    const result = await sql.begin(async (transaction) => {
      const tx = transaction as unknown as LoaderSql;
      const liveDecisions = await tx.unsafe<{ n: number }[]>(
        'select count(*)::int as n from narrator_surface_decisions where retired_at is null',
      );
      if (liveDecisions[0].n > 0) {
        throw new LoadAbort(`${liveDecisions[0].n} live narrator_surface_decisions exist; decision replay (apply_decision) is not implemented yet`);
      }
      const surfaceChanged = await countSurfaceChangedUnderSameId(tx);
      const merge: MergeResult[] = [];
      await timed('merge', async () => {
        for (const table of PIPELINE_TABLES) {
          const header = projection.files.get(table.name)!.entry.header;
          const merged = await mergeTable(tx, table, header, staged.get(table.name)!, versionId);
          merge.push(merged);
          log(`  merged ${table.name}: +${merged.inserted} ~${merged.updated} derived ${merged.derivedUpdated} retired ${merged.retired}`);
        }
      });
      const [{ changed: facetRowsChanged }] = await timed('facets', () =>
        tx.unsafe<{ changed: number }[]>('select refresh_publication_facets(array(select id from hadiths)) as changed'),
      );
      const rowsChanged =
        merge.reduce((sum, entry) => sum + entry.inserted + entry.updated + entry.derivedUpdated + entry.retired, 0) + facetRowsChanged;
      if (mode === 'reload' && rowsChanged > 0) {
        throw new LoadAbort(`reload of identical content changed ${rowsChanged} rows; the projection or merge is not deterministic`);
      }

      await tx.unsafe('update dataset_versions set is_current = false where is_current and id <> $1', [versionId]);
      await tx.unsafe('update dataset_versions set is_current = true where id = $1', [versionId]);
      let networkRefreshed = false;
      if (rowsChanged > 0) {
        const [{ refreshed }] = await timed('network', () => tx.unsafe<{ refreshed: boolean }[]>('select refresh_network() as refreshed'));
        if (!refreshed) throw new LoadAbort('refresh_network() was skipped; another refresh or writer holds the lock');
        networkRefreshed = true;
      }

      const expectedLiveRows = Object.fromEntries([...projection.files].map(([table, file]) => [table, file.entry.row_count]));
      const checks = await timed('checks', () =>
        runDataChecks(tx, { expectedLiveRows, mergeResults: merge, minimumLiveHadiths: options.minimumLiveHadiths }),
      );
      const failures = failedChecks(checks);
      if (failures.length > 0) throw new LoadAbort(`section 11.4 checks failed; rolled back:\n${formatChecks(checks)}`);

      if (mode !== 'reload') {
        const counts = {
          projection: projection.manifest.counts,
          merge,
          facet_rows_changed: facetRowsChanged,
          mentions_surface_changed_under_same_id: surfaceChanged,
          ...checks.reported,
        };
        await tx.unsafe(
          `update dataset_versions set load_status = 'complete', completed_at = now(), counts = $2::jsonb where id = $1`,
          [versionId, JSON.stringify(counts)],
        );
      }
      return { merge, facetRowsChanged, rowsChanged, networkRefreshed, checks };
    });

    await dropStaging(sql, stagedTables);
    stagedTables.length = 0;
    if (result.rowsChanged > 0) {
      await timed('vacuum', async () => {
        for (const entry of result.merge) {
          if (entry.inserted + entry.updated + entry.derivedUpdated + entry.retired > 0) {
            await sql.unsafe(`vacuum (analyze) ${quoteIdentifier(entry.table)}`);
          }
        }
      });
    }
    return {
      versionId,
      mode,
      ...result,
      databaseBytes: { before: bytesBefore, after: await databaseBytes(sql) },
      timingsMs,
    };
  } catch (error) {
    if (mode === 'new' || mode === 'resume') {
      await sql
        .unsafe(`update dataset_versions set load_status = 'failed' where id = $1 and load_status = 'loading'`, [versionId])
        .catch(() => undefined);
    }
    throw error;
  } finally {
    await dropStaging(sql, stagedTables).catch(() => undefined);
    await sql.unsafe('select pg_advisory_unlock($1::bigint)', [DATA_WRITE_LOCK_KEY]).catch(() => undefined);
  }
}
