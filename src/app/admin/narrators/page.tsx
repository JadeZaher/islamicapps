export const dynamic = 'force-dynamic';

import { getAllNarrators, searchNarrators } from '@/app/actions/graph-actions';
import { DEFAULT_PAGE_SIZE, parsePageParam } from '@/lib/pagination';
import { NarratorsClient } from './client';

interface PageProps {
    searchParams: Promise<{ page?: string; q?: string; reliability?: string; tabaqah?: string }>;
}

export default async function NarratorsPage({ searchParams }: PageProps) {
    const params = await searchParams;
    const requestedPage = parsePageParam(params.page);
    const q = params.q || '';
    const reliability = params.reliability || '';
    const tabaqah = params.tabaqah || '';

    const hasFilters = q || reliability || tabaqah;

    let result;
    if (hasFilters) {
        // searchNarrators returns every match, so paginate here instead of rendering them all.
        const narrators = await searchNarrators(q, {
            reliability: reliability || undefined,
            tabaqah: tabaqah || undefined,
        });
        const pageSize = DEFAULT_PAGE_SIZE;
        const totalPages = Math.max(1, Math.ceil(narrators.length / pageSize));
        const page = Math.min(requestedPage, totalPages);
        result = {
            items: narrators.slice((page - 1) * pageSize, page * pageSize),
            page,
            totalPages,
            total: narrators.length,
            pageSize,
        };
    } else {
        result = await getAllNarrators({ page: requestedPage });
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
