import Link from 'next/link';
import { Button } from '@/components/ui/button';

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-[50vh] max-w-md flex-col items-center justify-center gap-4 px-6 text-center text-slate-100">
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <p className="text-sm text-slate-400">This page doesn&apos;t exist or was moved.</p>
      <Button asChild className="bg-emerald-600 text-white hover:bg-emerald-500">
        <Link href="/hadith">Browse hadith</Link>
      </Button>
    </main>
  );
}
