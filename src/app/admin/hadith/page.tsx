export const dynamic = 'force-dynamic';

import { getAllHadiths, searchHadiths } from '@/app/actions/graph-actions';
import { parsePageParam } from '@/lib/pagination';
import { HadithManagerClient } from './client';

interface PageProps {
    searchParams: Promise<{ page?: string; q?: string; source?: string; tradition?: string; school?: string }>;
}

export default async function HadithManagerPage({ searchParams }: PageProps) {
    const params = await searchParams;
    const page = parsePageParam(params.page);
    const q = params.q || '';
    const source = params.source || '';
    // `school` remains a read-only URL alias for bookmarked legacy filters.
    const tradition = params.tradition || params.school || '';

    const hasFilters = q || source || tradition;
    const result = hasFilters
        ? await searchHadiths(q, { source: source || undefined, tradition: tradition || undefined }, { page })
        : await getAllHadiths({ page });

    return (
        <HadithManagerClient
            hadiths={result.items}
            pagination={{
                page: result.page,
                totalPages: result.totalPages,
                total: result.total,
                pageSize: result.pageSize,
            }}
        />
    );
}
