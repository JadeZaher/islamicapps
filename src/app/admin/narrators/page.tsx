export const dynamic = 'force-dynamic';

import { listNarratorsForReview } from '@/db/queries/narrator-review';
import { parsePageParam } from '@/lib/pagination';
import { NarratorsClient } from './client';

interface PageProps {
    searchParams: Promise<{ page?: string; q?: string; reliability?: string; verdict?: string; tradition?: string; tabaqah?: string }>;
}

/** Legacy v1 reliability codes in bookmarked URLs, mapped onto the verdict enum (rule 8). */
const LEGACY_RELIABILITY: Record<string, string> = {
    THIQA: 'thiqa',
    SADUQ: 'saduq',
    DAIF: 'daif',
    MAJHUL: 'majhul',
    KADHAB: 'kadhab',
};

export default async function NarratorsPage({ searchParams }: PageProps) {
    const params = await searchParams;
    const page = parsePageParam(params.page);
    const q = params.q || '';
    const verdict = params.verdict || (params.reliability ? LEGACY_RELIABILITY[params.reliability.toUpperCase()] ?? params.reliability : '');

    // Reviewer mode: verdicts of every status; one paginated query with a real count (no fake pagination).
    const result = await listNarratorsForReview(
        q,
        { verdict: verdict || undefined, tradition: params.tradition || undefined, tabaqah: params.tabaqah || undefined },
        { page },
    );

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
