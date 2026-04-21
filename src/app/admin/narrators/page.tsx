import { getAllNarrators, searchNarrators } from '@/app/actions/graph-actions';
import { NarratorsClient } from './client';

interface PageProps {
    searchParams: Promise<{ page?: string; q?: string; reliability?: string; tabaqah?: string }>;
}

export default async function NarratorsPage({ searchParams }: PageProps) {
    const params = await searchParams;
    const page = parseInt(params.page || '1', 10);
    const q = params.q || '';
    const reliability = params.reliability || '';
    const tabaqah = params.tabaqah || '';

    const hasFilters = q || reliability || tabaqah;

    let result;
    if (hasFilters) {
        const narrators = await searchNarrators(q, {
            reliability: reliability || undefined,
            tabaqah: tabaqah || undefined,
        });
        result = {
            items: narrators,
            page: 1,
            totalPages: 1,
            total: narrators.length,
            pageSize: 50,
        };
    } else {
        result = await getAllNarrators({ page });
    }

    return (
        <NarratorsClient
            narrators={result.items}
            pagination={{
                page: result.page,
                totalPages: result.totalPages,
                total: result.total,
                pageSize: result.pageSize,
            }}
        />
    );
}
