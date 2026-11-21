export const dynamic = 'force-dynamic';

import { getComparativeStats, listPublicParallels, listReligiousTraditions } from '@/db/queries/comparative';
import { ComparativeClient } from './client';

export default async function ComparativePage() {
    // Published parallels on public hadiths only (section 9.2).
    const [parallelsResult, traditions, stats] = await Promise.all([
        listPublicParallels({ pageSize: 50 }),
        listReligiousTraditions(),
        getComparativeStats(),
    ]);

    return (
        <ComparativeClient
            initialParallels={parallelsResult.items}
            traditions={traditions}
            stats={stats}
        />
    );
}
