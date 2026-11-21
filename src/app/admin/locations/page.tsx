export const dynamic = 'force-dynamic';

import { listLocations } from '@/db/queries/location';
import { parsePageParam } from '@/lib/pagination';
import { LocationsManagerClient } from './client';

interface PageProps {
    searchParams: Promise<{ page?: string; q?: string }>;
}

export default async function LocationsManagerPage({ searchParams }: PageProps) {
    const params = await searchParams;
    const page = parsePageParam(params.page);
    const q = params.q || '';

    const result = await listLocations(q, { page });

    return (
        <LocationsManagerClient
            locations={result.items}
            pagination={{
                page: result.page,
                totalPages: result.totalPages,
                total: result.total,
                pageSize: result.pageSize,
            }}
            searchQuery={q}
        />
    );
}
