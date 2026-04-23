export const dynamic = 'force-dynamic';

import { getAllLocations } from '@/app/actions/graph-actions';
import { LocationsManagerClient } from './client';

interface PageProps {
    searchParams: Promise<{ page?: string; q?: string }>;
}

export default async function LocationsManagerPage({ searchParams }: PageProps) {
    const params = await searchParams;
    const page = parseInt(params.page || '1', 10);
    const q = params.q || '';

    const result = await getAllLocations({ page });

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
