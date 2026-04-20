import { getAllHadiths, searchHadiths } from '@/app/actions/graph-actions';
import { HadithManagerClient } from './client';

interface PageProps {
    searchParams: Promise<{ page?: string; q?: string; source?: string; grade?: string }>;
}

export default async function HadithManagerPage({ searchParams }: PageProps) {
    const params = await searchParams;
    const page = parseInt(params.page || '1', 10);
    const q = params.q || '';
    const source = params.source || '';
    const grade = params.grade || '';

    const hasFilters = q || source || grade;
    const result = hasFilters
        ? await searchHadiths(q, { source: source || undefined, grade: grade || undefined }, { page })
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
