/** Per-request cached narrator read, shared by the layout's existence check, generateMetadata and the page. */
import 'server-only';
import { cache } from 'react';
import { getNarratorDetail } from '@/db/queries/narrator';

export const loadNarrator = cache((id: string) => getNarratorDetail(decodeURIComponent(id)));
