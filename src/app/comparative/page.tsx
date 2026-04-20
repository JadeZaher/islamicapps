import { getAllParallels, getAllTraditions, getComparativeStats } from '@/app/actions/comparative-actions';
import { ComparativeClient } from './client';

export default async function ComparativePage() {
    const [parallelsResult, traditions, stats] = await Promise.all([
        getAllParallels({ pageSize: 50 }),
        getAllTraditions(),
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
