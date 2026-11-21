'use client';

import { useRouter, useSearchParams } from 'next/navigation';
import { Button } from '@/components/ui/button';

interface PaginationControlsProps {
    page: number;
    totalPages: number;
    total: number;
    pageSize: number;
    onPageChange?: (page: number) => void;
}

export function PaginationControls({ page, totalPages, total, pageSize, onPageChange }: PaginationControlsProps) {
    const router = useRouter();
    const searchParams = useSearchParams();

    if (totalPages <= 1) return null;

    const start = (page - 1) * pageSize + 1;
    const end = Math.min(page * pageSize, total);

    const goToPage = (p: number) => {
        if (onPageChange) {
            onPageChange(p);
            return;
        }
        // Default: preserve all existing searchParams, just update page
        const params = new URLSearchParams(searchParams.toString());
        params.set('page', String(p));
        router.push(`?${params.toString()}`);
    };

    return (
        <nav aria-label="Pagination" className="flex flex-wrap items-center justify-between gap-4 mt-6">
            <p className="text-sm tabular-nums text-ink-muted">
                {start}–{end} of {total.toLocaleString()}
            </p>
            <div className="flex items-center gap-2">
                <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => goToPage(page - 1)}
                    aria-label="Previous page"
                >
                    Previous
                </Button>
                <span className="text-sm tabular-nums text-ink-muted px-2" aria-current="page" aria-label={`Page ${page} of ${totalPages}`}>
                    {page} / {totalPages}
                </span>
                <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => goToPage(page + 1)}
                    aria-label="Next page"
                >
                    Next
                </Button>
            </div>
        </nav>
    );
}
