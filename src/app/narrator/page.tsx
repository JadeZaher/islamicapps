export const dynamic = 'force-dynamic';

import type { Metadata } from 'next';
import Link from 'next/link';
import { listNarrators } from '@/db/queries/narrator';
import { EmptyState } from '@/components/EmptyState';
import { NarratorName } from '@/components/NarratorName';
import { PageLinks } from '@/components/PageLinks';
import { Button } from '@/components/ui/button';

export const metadata: Metadata = { title: 'Narrators' };

interface PageProps {
  searchParams: Promise<{ page?: string; q?: string }>;
}

export default async function NarratorIndexPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page) || 1);
  const q = params.q?.trim() ?? '';

  // Browse and search share one paginated query with a capped count (section 7.3).
  const result = await listNarrators(q, {}, { page });
  const count = `${result.total.toLocaleString()}${result.totalCapped ? '+' : ''}`;

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 text-slate-100">
      <h1 className="text-3xl font-semibold">Narrators</h1>

      <form action="/narrator" role="search" className="mt-6 flex gap-2">
        <input
          type="search"
          name="q"
          defaultValue={q}
          aria-label="Search narrators"
          placeholder="Search by name, English or Arabic"
          className="h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus-visible:border-emerald-500 focus-visible:ring-2 focus-visible:ring-emerald-500/40"
        />
        <Button type="submit" className="h-10 bg-emerald-600 text-white hover:bg-emerald-500">
          Search
        </Button>
      </form>

      <p className="mt-6 text-sm text-slate-400" aria-live="polite">
        {q
          ? `${count} ${result.total === 1 && !result.totalCapped ? 'match' : 'matches'}`
          : `${count} narrators`}
      </p>

      {result.items.length === 0 ? (
        <EmptyState
          className="mt-4"
          title="No narrators found"
          description="Try a different spelling or the Arabic name."
          action={
            q && (
              <Button asChild variant="outline" size="sm">
                <Link href="/narrator">Clear search</Link>
              </Button>
            )
          }
        />
      ) : (
        <ul className="-mx-3 mt-3 divide-y divide-slate-800 border-y border-slate-800">
          {result.items.map((narrator) => {
            const id = String(narrator.id);
            return (
              <li key={id}>
                <Link
                  href={`/narrator/${encodeURIComponent(id)}`}
                  className="block px-3 py-3 outline-none transition-colors hover:bg-slate-900 focus-visible:bg-slate-900 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-400"
                >
                  <NarratorName
                    english={narrator.name_english as string | undefined}
                    arabic={narrator.name_arabic as string | undefined}
                    latinClassName="font-medium text-slate-100"
                    arabicClassName="text-lg leading-relaxed text-slate-400"
                  />
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      <PageLinks basePath="/narrator" page={result.page} totalPages={result.totalPages} />
    </main>
  );
}
