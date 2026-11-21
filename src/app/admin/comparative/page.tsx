export const dynamic = 'force-dynamic';

import { listMotifTags, listReligiousTraditions, listSourceTexts } from '@/db/queries/comparative';
import { listParallelsForReview } from '@/db/queries/comparative-review';
import { listNarratorsForReview } from '@/db/queries/narrator-review';
import { ComparativeManagerClient } from './client';

export default async function ComparativeAdminPage() {
    const [traditions, sourceTexts, parallelsResult, motifTags, narratorsResult] = await Promise.all([
        listReligiousTraditions(),
        listSourceTexts(),
        listParallelsForReview({ pageSize: 50 }),
        listMotifTags(),
        listNarratorsForReview('', {}, { pageSize: 100 }),
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
