/** Per-request cached hadith read, shared by the layout's existence check, generateMetadata and the page. */
import 'server-only';
import { cache } from 'react';
import { getPublicHadith } from '@/db/queries/hadith';

export const loadHadith = cache((id: string) => getPublicHadith(decodeURIComponent(id)));
