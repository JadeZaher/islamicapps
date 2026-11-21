export const dynamic = 'force-dynamic';

import { EVENT_CATEGORIES, type EventCategory } from '@/db/queries/enums';
import { listHistoricalEvents } from '@/db/queries/history';
import { parsePageParam } from '@/lib/pagination';
import { EventsManagerClient } from './client';

interface PageProps {
    searchParams: Promise<{ page?: string; category?: string }>;
}

/** Maps `?category=` (including legacy title case, e.g. `Political`) onto the enum; unknown gives null (empty list). */
function canonicalCategory(value: string): EventCategory | null | undefined {
    if (!value) return undefined;
    const upper = value.trim().toUpperCase().replace(/[\s-]+/g, '_');
    return (EVENT_CATEGORIES as readonly string[]).includes(upper) ? (upper as EventCategory) : null;
}

export default async function EventsManagerPage({ searchParams }: PageProps) {
    const params = await searchParams;
    const page = parsePageParam(params.page);

    const result = await listHistoricalEvents({ category: canonicalCategory(params.category || '') }, { page });

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
