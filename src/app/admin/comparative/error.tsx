'use client';

import { useEffect } from 'react';
import { Button } from '@/components/ui/button';

export default function AdminComparativeError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error('Admin comparative page failed', error.digest);
    }, [error]);

    return (
        <div role="alert" className="flex flex-col items-start gap-4 py-12">
            <h1 className="text-2xl font-semibold text-white">Couldn&apos;t load comparative studies</h1>
            <Button onClick={reset}>Try again</Button>
        </div>
    );
}
