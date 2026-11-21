/** Per-request cached reads shared by the report-context components (layout-mounted). */
import 'server-only';
import { cache } from 'react';
import { getReportContext } from '@/db/queries/browse';
import { getCurrentDatasetVersion } from '@/db/queries/dataset-version';
import { requestVisibility } from '@/lib/auth/visibility';

export const loadReportContext = cache(async (id: string) => getReportContext(id, await requestVisibility()));

export const loadDatasetVersion = cache(() =>
  getCurrentDatasetVersion().catch((error: unknown) => {
    console.error('Dataset version lookup failed', error instanceof Error ? error.message : error);
    return null;
  }),
);
