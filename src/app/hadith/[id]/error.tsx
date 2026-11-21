'use client';

import { useEffect, useRef } from 'react';
import Link from 'next/link';

const WAKE_RETRY_MS = 2000;

export default function HadithError({
    error,
    reset,
}: {
    error: Error & { digest?: string };
    reset: () => void;
}) {
    const retried = useRef(false);

    useEffect(() => {
        console.error('Hadith page failed', error.digest ?? error);
        if (retried.current) return;
        // One silent retry covers a cold database wake-up.
        const timer = setTimeout(() => {
            retried.current = true;
            reset();
        }, WAKE_RETRY_MS);
        return () => clearTimeout(timer);
    }, [error, reset]);

    return (
        <main className="min-h-screen bg-slate-950 flex items-center justify-center p-8 text-white">
            <div className="max-w-md w-full text-center space-y-5" role="alert">
                <h1 className="text-2xl font-bold">Couldn&apos;t load this hadith</h1>
                <div className="flex items-center justify-center gap-4">
                    <button
                        type="button"
                        onClick={() => reset()}
                        className="rounded-md bg-cyan-700 px-5 py-2 text-sm font-medium hover:bg-cyan-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-300"
                    >
                        Try again
                    </button>
                    <Link href="/" className="text-sm text-slate-300 hover:text-white underline-offset-4 hover:underline">
                        Home
                    </Link>
                </div>
            </div>
        </main>
    );
}
