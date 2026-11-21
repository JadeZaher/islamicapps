export const dynamic = 'force-dynamic';

import { searchHadithsForReview } from '@/db/queries/hadith-review';
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

    // Reviewer mode: every live hadith, including rows the public views hide.
    const result = await searchHadithsForReview(q, { source: source || undefined, tradition: tradition || undefined }, { page });

    return (
        <HadithManagerClient
            hadiths={result.items.map((hadith) => ({
                ...hadith,
                title: hadith.title ?? '',
                source: hadith.source,
                primary_topic: hadith.primary_topic ?? undefined,
                text_english: hadith.text_english ?? undefined,
                text_arabic: hadith.text_arabic ?? undefined,
                hadith_no: hadith.hadith_no ?? undefined,
                chapter: hadith.chapter ?? undefined,
                chapter_no: hadith.chapter_no ?? undefined,
                volume: hadith.volume ?? undefined,
                matn_ar: hadith.matn_ar ?? undefined,
                matn_en: undefined,
                text_ar: hadith.text_ar ?? undefined,
                text_en: hadith.text_en ?? undefined,
            }))}
            pagination={{
                page: result.page,
                totalPages: result.totalPages,
                total: result.total,
                pageSize: result.pageSize,
            }}
        />
    );
}
