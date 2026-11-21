export const dynamic = 'force-dynamic';

import type { Metadata } from 'next';
import Link from 'next/link';
import { searchPublicHadiths } from '@/db/queries/hadith';
import { ArabicText } from '@/components/ArabicText';
import { EmptyState } from '@/components/EmptyState';
import { BilingualTitle } from '@/components/NarratorName';
import { PageLinks } from '@/components/PageLinks';
import { TraditionBadge } from '@/components/badges';
import { Button } from '@/components/ui/button';
import { HADITH_TRADITION_OPTIONS } from '@/lib/constants/traditions';

export const metadata: Metadata = { title: 'Hadith' };

interface PageProps {
  searchParams: Promise<{ page?: string; q?: string; tradition?: string }>;
}

const EXCERPT_LENGTH = 220;

function excerpt(text: string | null | undefined): string {
  const flat = (text ?? '').replace(/\s+/g, ' ').trim();
  return flat.length > EXCERPT_LENGTH ? `${flat.slice(0, EXCERPT_LENGTH).trimEnd()}...` : flat;
}

export default async function HadithIndexPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page) || 1);
  const q = params.q?.trim() ?? '';
  const tradition = params.tradition ?? '';

  // Public views only; an unknown tradition value gives an empty page, never an error.
  const result = await searchPublicHadiths(q, { tradition: tradition || undefined }, { page });
  const hadiths = result.items;

  const traditionHref = (value: string) => {
    const search = new URLSearchParams();
    if (q) search.set('q', q);
    if (value) search.set('tradition', value);
    const query = search.toString();
    return query ? `/hadith?${query}` : '/hadith';
  };

  return (
    <main className="mx-auto max-w-4xl px-6 py-10 text-slate-100">
      <h1 className="text-3xl font-semibold">Hadith</h1>

      <form action="/hadith" role="search" className="mt-6 flex gap-2">
        {tradition && <input type="hidden" name="tradition" value={tradition} />}
        <input
          type="search"
          name="q"
          defaultValue={q}
          aria-label="Search hadith"
          placeholder="Search by chapter, topic or text"
          className="h-10 w-full rounded-md border border-slate-700 bg-slate-900 px-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus-visible:border-emerald-500 focus-visible:ring-2 focus-visible:ring-emerald-500/40"
        />
        <Button type="submit" className="h-10 bg-emerald-600 text-white hover:bg-emerald-500">
          Search
        </Button>
      </form>

      <nav aria-label="Filter by tradition" className="mt-4 flex flex-wrap gap-2">
        {HADITH_TRADITION_OPTIONS.map((option) => {
          const isActive = option.value === tradition;
          return (
            <Link
              key={option.value || 'all'}
              href={traditionHref(option.value)}
              aria-current={isActive ? 'true' : undefined}
              className={`rounded-full border px-3 py-1 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-emerald-400 ${
                isActive
                  ? 'border-emerald-500/60 bg-emerald-500/15 text-emerald-200'
                  : 'border-slate-700 text-slate-400 hover:text-slate-100'
              }`}
            >
              {option.value || option.label}
            </Link>
          );
        })}
      </nav>

      <p className="mt-6 text-sm text-slate-400" aria-live="polite">
        {result.total.toLocaleString()}
        {result.totalCapped ? '+' : ''} {result.total === 1 && !result.totalCapped ? 'hadith' : 'hadiths'}
      </p>

      {hadiths.length === 0 ? (
        <EmptyState
          className="mt-4"
          title={q || tradition ? 'No hadith found' : 'No published hadith yet.'}
          description={q || tradition ? 'Try a different search or tradition.' : undefined}
          action={
            (q || tradition) && (
              <Button asChild variant="outline" size="sm">
                <Link href="/hadith">Clear filters</Link>
              </Button>
            )
          }
        />
      ) : (
        <ul className="-mx-3 mt-3 divide-y divide-slate-800 border-y border-slate-800">
          {hadiths.map((hadith) => {
            const english = excerpt((hadith.text_english as string | null) ?? null);
            const arabic = excerpt((hadith.text_arabic as string | null) ?? null);
            const reference = [hadith.source, hadith.hadith_no ? `#${String(hadith.hadith_no)}` : '']
              .filter(Boolean)
              .join(' ');
            return (
              <li key={hadith.id}>
                <Link
                  href={`/hadith/${encodeURIComponent(hadith.id)}`}
                  className="block px-3 py-4 outline-none transition-colors hover:bg-slate-900 focus-visible:bg-slate-900 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-emerald-400"
                >
                  <div className="flex flex-wrap items-center gap-2 text-sm text-slate-400">
                    <span>{reference || 'Hadith'}</span>
                    {hadith.tradition && <TraditionBadge tradition={hadith.tradition} />}
                  </div>
                  {hadith.title && (
                    <p className="mt-1 font-medium text-slate-100">
                      <BilingualTitle text={String(hadith.title)} />
                    </p>
                  )}
                  {english ? (
                    <p className="mt-1 text-sm leading-relaxed text-slate-300">{english}</p>
                  ) : (
                    arabic && (
                      <ArabicText as="p" className="mt-1 text-lg text-slate-300">
                        {arabic}
                      </ArabicText>
                    )
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      )}

      <PageLinks
        basePath="/hadith"
        page={result.page}
        totalPages={result.totalPages}
        params={{ q, tradition }}
      />
    </main>
  );
}
