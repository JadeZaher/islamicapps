/** Dataset-version state for the public preview notice. See src/db/queries/AGENTS.md §Preview approval. */
import 'server-only';
import { sql } from 'drizzle-orm';
import { oneRow } from './sql-helpers';

export interface PreviewNotice {
  versionLabel: string | null;
  approvedAt: string;
}

/**
 * Non-null only while the current, complete dataset version is non-release and served under a recorded owner
 * approval: the same predicate public_hadiths uses to open its gate (drizzle/core/0003_views.sql), so the notice
 * and the data it explains cannot drift apart. A release version becoming current turns it off by itself.
 */
export async function getPreviewNotice(): Promise<PreviewNotice | null> {
  const row = await oneRow<{ version_label: string | null; approved_at: Date | string }>(sql`
    select version_label, public_override_at as approved_at
    from dataset_versions
    where is_current and load_status = 'complete'
      and release_class = 'non_release' and public_override_by is not null
    limit 1`);
  if (!row) return null;
  return { versionLabel: row.version_label, approvedAt: new Date(row.approved_at).toISOString() };
}
