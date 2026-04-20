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
        <div className="flex items-center justify-between mt-6">
            <p className="text-sm text-slate-400">
                {start}–{end} of {total.toLocaleString()}
            </p>
            <div className="flex items-center gap-2">
                <Button
                    variant="outline"
                    size="sm"
                    disabled={page <= 1}
                    onClick={() => goToPage(page - 1)}
                    className="border-slate-600 text-slate-300 hover:bg-white/5 disabled:opacity-30"
                >
                    Previous
                </Button>
                <span className="text-sm text-slate-400 px-2">
                    {page} / {totalPages}
                </span>
                <Button
                    variant="outline"
                    size="sm"
                    disabled={page >= totalPages}
                    onClick={() => goToPage(page + 1)}
                    className="border-slate-600 text-slate-300 hover:bg-white/5 disabled:opacity-30"
                >
                    Next
                </Button>
            </div>
        </div>
    );
}
