'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';

/** Root route error boundary; never prints error.message (can carry query text). */
export default function RootError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('Route error', error.digest ?? '', error);
  }, [error]);

  return (
    <main role="alert" className="mx-auto flex min-h-[50vh] max-w-md flex-col items-center justify-center gap-4 px-6 text-center text-slate-100">
      <h1 className="text-2xl font-semibold">Couldn&apos;t load this page</h1>
      <p className="text-sm text-slate-400">Something went wrong on our side. Try again in a moment.</p>
      <div className="flex gap-2">
        <Button onClick={reset} className="bg-emerald-600 text-white hover:bg-emerald-500">
          Try again
        </Button>
        <Button asChild variant="ghost">
          <Link href="/">Home</Link>
        </Button>
      </div>
      {error.digest && <p className="text-xs text-slate-600">Reference {error.digest}</p>}
    </main>
  );
}
