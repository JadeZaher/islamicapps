/** Per-request cached narrator read, shared by the layout's existence check, generateMetadata and the page. */
import 'server-only';
import { cache } from 'react';
import { getVisibleNarrator } from '@/db/queries/narrator';
import { requestVisibility } from '@/lib/auth/visibility';

/** Public reads, or curator-preview reads for a signed-in curator under PRIVATE_PREVIEW (resolved from the session). */
export const loadNarrator = cache(async (id: string) => getVisibleNarrator(decodeURIComponent(id), await requestVisibility()));
