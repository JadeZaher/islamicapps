/** Per-request cached reads under the request's visibility, shared by the layout's existence check, metadata and pages. */
import 'server-only';
import { cache } from 'react';
import { getVisibleReportFamily } from '@/db/queries/correspondence';
import { getVisibleHadith } from '@/db/queries/hadith';
import { requestVisibility } from '@/lib/auth/visibility';

/** Public, or every live report for a verified curator under PRIVATE_PREVIEW (src/lib/auth/visibility.ts). */
export const loadHadith = cache(async (id: string) => getVisibleHadith(decodeURIComponent(id), await requestVisibility()));

/** The report's family under the same visibility (the chains route's metadata and page, and the hadith page section). */
export const loadFamily = cache(async (id: string) => getVisibleReportFamily(decodeURIComponent(id), await requestVisibility()));
