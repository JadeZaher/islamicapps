export const dynamic = 'force-dynamic';

import type { Metadata } from 'next';
import Link from 'next/link';
import { getAllNarrators, searchNarrators } from '@/app/actions/graph-actions';
import { ArabicText } from '@/components/ArabicText';
import { ConsensusBadge } from '@/components/ConsensusBadge';
import { EmptyState } from '@/components/EmptyState';
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

  // searchNarrators is capped at 50 rows and unpaginated; browsing uses the paginated list.
  const result = q
    ? await searchNarrators(q).then((items) => ({
        items,
        total: items.length,
        page: 1,
        totalPages: 1,
      }))
    : await getAllNarrators({ page });

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
          ? `${result.total.toLocaleString()} ${result.total === 1 ? 'match' : 'matches'}${result.total >= 50 ? ' (first 50 shown)' : ''}`
          : `${result.total.toLocaleString()} narrators`}
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
        <ul className="mt-3 divide-y divide-slate-800 border-y border-slate-800">
          {result.items.map((narrator) => {
            const id = String(narrator.id);
            const verdict = (narrator.reliability_consensus as string | undefined) ?? null;
            const nameArabic = narrator.name_arabic as string | undefined;
            return (
              <li key={id}>
                <Link
                  href={`/narrator/${encodeURIComponent(id)}`}
                  className="flex items-center justify-between gap-4 px-2 py-3 outline-none transition-colors hover:bg-slate-900 focus-visible:bg-slate-900 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-400"
                >
                  <div className="min-w-0">
                    <p className="truncate font-medium text-slate-100">
                      {(narrator.name_english as string | undefined) || nameArabic}
                    </p>
                    {narrator.name_english && nameArabic && (
                      <ArabicText className="block truncate text-lg text-slate-400">{nameArabic}</ArabicText>
                    )}
                  </div>
                  <ConsensusBadge verdict={verdict} />
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
