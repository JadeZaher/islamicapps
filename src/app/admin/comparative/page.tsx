export const dynamic = 'force-dynamic';

import { getAllTraditions, getAllSourceTexts, getAllParallels, getAllMotifTags } from '@/app/actions/comparative-actions';
import { getAllNarrators } from '@/app/actions/graph-actions';
import { ComparativeManagerClient } from './client';

export default async function ComparativeAdminPage() {
    const [traditions, sourceTexts, parallelsResult, motifTags, narratorsResult] = await Promise.all([
        getAllTraditions(),
        getAllSourceTexts(),
        getAllParallels({ pageSize: 50 }),
        getAllMotifTags(),
        getAllNarrators({ pageSize: 100 }),
    ]);

    return (
        <ComparativeManagerClient
            traditions={traditions}
            sourceTexts={sourceTexts}
            parallels={parallelsResult.items}
            motifTags={motifTags}
            narrators={narratorsResult.items}
        />
    );
}
