/** The current dataset version: the stamp every page shows, and the crawl policy derived from it. */
import 'server-only';
import { sql } from 'drizzle-orm';
import { oneRow, toIso } from './sql-helpers';

export interface DatasetVersionStamp {
  id: string;
  /** First 12 characters of the ID, enough to identify a version in a citation. */
  shortId: string;
  label: string | null;
  bundleVersion: string;
  releaseClass: 'release' | 'non_release';
  completedAt: string | null;
  /** Release-class, or non-release under a recorded owner approval: the public_hadiths gate. */
  publiclyServable: boolean;
}

/** The current, completely loaded version, or null (no load yet, or a load in progress). */
export async function getCurrentDatasetVersion(): Promise<DatasetVersionStamp | null> {
  const row = await oneRow<{
    id: string;
    version_label: string | null;
    bundle_version: string;
    release_class: 'release' | 'non_release';
    completed_at: unknown;
    servable: boolean;
  }>(sql`
    select id, version_label, bundle_version, release_class, completed_at,
           (release_class = 'release' or public_override_by is not null) as servable
    from dataset_versions
    where is_current and load_status = 'complete'
    limit 1`);
  if (!row) return null;
  return {
    id: row.id,
    shortId: row.id.slice(0, 12),
    label: row.version_label,
    bundleVersion: row.bundle_version,
    releaseClass: row.release_class,
    completedAt: toIso(row.completed_at),
    publiclyServable: row.servable,
  };
}

/** Search engines may index only a release; a non-release preview, no load, or private preview is noindex. */
export function isIndexable(version: DatasetVersionStamp | null, privatePreview: boolean): boolean {
  return !privatePreview && version?.releaseClass === 'release';
}
