import { getAllCommentaries, getAllHadiths, getAllNarrators } from '@/app/actions/graph-actions';
import { CommentariesManagerClient } from './client';

interface PageProps {
    searchParams: Promise<{ page?: string; type?: string }>;
}

export default async function CommentariesManagerPage({ searchParams }: PageProps) {
    const params = await searchParams;
    const page = parseInt(params.page || '1', 10);
    const type = params.type || '';

    const [commentariesResult, hadithsResult, narratorsResult] = await Promise.all([
        getAllCommentaries({ page }),
        getAllHadiths({ pageSize: 100 }),
        getAllNarrators({ pageSize: 100 }),
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
