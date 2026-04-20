import { getAllHistoricalEvents } from '@/app/actions/graph-actions';
import { EventsManagerClient } from './client';

interface PageProps {
    searchParams: Promise<{ page?: string; category?: string }>;
}

export default async function EventsManagerPage({ searchParams }: PageProps) {
    const params = await searchParams;
    const page = parseInt(params.page || '1', 10);
    const category = params.category || '';

    const result = await getAllHistoricalEvents(
        category ? { category } : undefined,
        { page }
    );

    return (
        <EventsManagerClient
            events={result.items}
            pagination={{
                page: result.page,
                totalPages: result.totalPages,
                total: result.total,
                pageSize: result.pageSize,
            }}
        />
    );
}
