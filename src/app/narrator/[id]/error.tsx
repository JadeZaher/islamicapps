'use client';

import { useEffect } from 'react';
import Link from 'next/link';

export default function NarratorError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    useEffect(() => {
        console.error('Narrator page failed', error.digest ?? '');
    }, [error]);

    return (
        <main className="flex min-h-[60vh] items-center justify-center px-6">
            <div role="alert" className="max-w-md text-center">
                <h1 className="text-2xl font-semibold text-white">Couldn&apos;t load this narrator</h1>
                <div className="mt-6 flex items-center justify-center gap-4">
                    <button
                        type="button"
                        onClick={reset}
                        className="rounded-md bg-cyan-700 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-600 focus-visible:outline focus-visible:outline-2 focus-visible:outline-cyan-300"
                    >
                        Try again
                    </button>
                    <Link href="/" className="text-sm text-white/70 underline underline-offset-4 hover:text-white">
                        Home
                    </Link>
                </div>
            </div>
        </main>
    );
}
