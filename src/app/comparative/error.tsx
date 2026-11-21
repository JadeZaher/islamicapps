'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function ComparativeError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error('Comparative page failed', error.digest);
    }, [error]);

    return (
        <div role="alert" className="min-h-screen bg-slate-950 flex flex-col items-center justify-center gap-4 px-4 text-center">
            <h1 className="text-2xl font-semibold text-white">Couldn&apos;t load comparative studies</h1>
            <div className="flex items-center gap-4">
                <Button onClick={reset}>Try again</Button>
                <Link href="/" className="text-sm text-cyan-300 hover:text-cyan-200">Home</Link>
            </div>
        </div>
    );
}
