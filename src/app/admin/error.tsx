'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function AdminError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
    useEffect(() => {
        console.error('Admin route error', error.digest);
    }, [error]);

    return (
        <div role="alert" className="mx-auto max-w-md py-24 text-center">
            <h1 className="text-2xl font-semibold text-white">Couldn&apos;t load this page</h1>
            <div className="mt-6 flex justify-center gap-3">
                <Button onClick={reset} className="bg-emerald-600 hover:bg-emerald-700">
                    Try again
                </Button>
                <Button asChild variant="outline" className="border-slate-600 text-slate-300">
                    <Link href="/admin/hadith">Back to admin</Link>
                </Button>
            </div>
        </div>
    );
}
