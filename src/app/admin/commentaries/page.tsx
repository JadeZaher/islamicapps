export const dynamic = 'force-dynamic';

import { listCommentaries } from '@/db/queries/commentary-review';
import { searchHadithsForReview } from '@/db/queries/hadith-review';
import { listNarratorsForReview } from '@/db/queries/narrator-review';
import { parsePageParam } from '@/lib/pagination';
import { CommentariesManagerClient } from './client';

interface PageProps {
    searchParams: Promise<{ page?: string; type?: string }>;
}

export default async function CommentariesManagerPage({ searchParams }: PageProps) {
    const params = await searchParams;
    const page = parsePageParam(params.page);
    const type = params.type || '';

    const [commentariesResult, hadithsResult, narratorsResult] = await Promise.all([
        listCommentaries({ page }, type || undefined),
        searchHadithsForReview('', {}, { pageSize: 100 }),
        listNarratorsForReview('', {}, { pageSize: 100 }),
    ]);

    return (
        <CommentariesManagerClient
            commentaries={commentariesResult.items}
            hadiths={hadithsResult.items}
            narrators={narratorsResult.items}
            pagination={{
                page: commentariesResult.page,
                totalPages: commentariesResult.totalPages,
                total: commentariesResult.total,
                pageSize: commentariesResult.pageSize,
            }}
            filterType={type}
        />
    );
}
