export const dynamic = 'force-dynamic';

import type { Metadata } from 'next';
import { HADITH_TRADITIONS, TraditionMark } from '@/components/marks';
import Link from 'next/link';
import { searchVisibleHadiths } from '@/db/queries/hadith';
import { requestVisibility } from '@/lib/auth/visibility';
import { hadithPath } from '@/lib/hadith-address';
import { ArabicText } from '@/components/ArabicText';
import { EmptyState } from '@/components/EmptyState';
import { BilingualTitle } from '@/components/NarratorName';
import { PageLinks } from '@/components/PageLinks';
import { TraditionBadge } from '@/components/badges';
import { Button } from '@/components/ui/button';
import { HADITH_TRADITION_OPTIONS } from '@/lib/constants/traditions';

// "All" first, then alphabetical: no tradition is listed as the default (DESIGN.md §Principles).
const TRADITION_FILTERS = [...HADITH_TRADITION_OPTIONS].sort((a, b) => (a.value === '' ? -1 : b.value === '' ? 1 : a.value.localeCompare(b.value)));

export const metadata: Metadata = { title: 'Hadith' };

interface PageProps {
  searchParams: Promise<{ page?: string; q?: string; tradition?: string }>;
}

const EXCERPT_LENGTH = 220;

function excerpt(text: string | null | undefined): string {
  const flat = (text ?? '').replace(/\s+/g, ' ').trim();
  return flat.length > EXCERPT_LENGTH ? `${flat.slice(0, EXCERPT_LENGTH).trimEnd()}...` : flat;
}

/** Tradition mark inside a filter chip; "All traditions" has none. */
function ChipMark({ value }: { value: string }) {
  const known = HADITH_TRADITIONS.find((name) => name === value);
  return known ? <TraditionMark tradition={known} decorative /> : null;
}

export default async function HadithIndexPage({ searchParams }: PageProps) {
  const params = await searchParams;
  const page = Math.max(1, Number(params.page) || 1);
  const q = params.q?.trim() ?? '';
  const tradition = params.tradition ?? '';

  // Public views (or curator preview); an unknown tradition value gives an empty page, never an error.
  const result = await searchVisibleHadiths(q, { tradition: tradition || undefined }, { page }, await requestVisibility());
  const hadiths = result.items;

  const traditionHref = (value: string) => {
    const search = new URLSearchParams();
    if (q) search.set('q', q);
    if (value) search.set('tradition', value);
    const query = search.toString();
    return query ? `/hadith?${query}` : '/hadith';
  };

  return (
    <main className="wrap pb-12">
      <h1 className="page-header type-h1">Hadith</h1>

      <form action="/hadith" role="search" className="mt-8 flex max-w-[var(--measure-reading)] gap-2">
        {tradition && <input type="hidden" name="tradition" value={tradition} />}
        <input
          type="search"
          name="q"
          defaultValue={q}
          aria-label="Search hadith"
          placeholder="Search by chapter, topic or text"
          dir="auto"
          className="h-10 w-full border border-control bg-surface px-3 text-base text-ink placeholder:text-ink-muted focus-visible:border-focus focus-visible:outline-offset-0"
        />
        <Button type="submit">
          Search
        </Button>
      </form>

      <nav aria-label="Filter by tradition" className="mt-4 flex flex-wrap gap-2">
        {TRADITION_FILTERS.map((option) => {
          const isActive = option.value === tradition;
          return (
            <Link
              key={option.value || 'all'}
              href={traditionHref(option.value)}
              aria-current={isActive ? 'true' : undefined}
              className={`inline-flex min-h-10 items-center gap-2 border px-3 text-sm no-underline transition-colors duration-[var(--motion-fast)] ${
                isActive ? 'border-ink text-ink shadow-[inset_0_0_0_1px_var(--color-ink)]' : 'border-control text-ink-muted hover:text-ink'
              }`}
            >
              <ChipMark value={option.value} />
              {option.value || option.label}
            </Link>
          );
        })}
      </nav>

      <p className="mt-6 type-small tabular-nums text-ink-muted" aria-live="polite">
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
        <ul className="mt-3 border-t border-rule-strong">
          {hadiths.map((hadith) => {
            const english = excerpt((hadith.text_english as string | null) ?? null);
            const arabic = excerpt((hadith.text_arabic as string | null) ?? null);
            const reference = [hadith.source, hadith.hadith_no ? `#${String(hadith.hadith_no)}` : '']
              .filter(Boolean)
              .join(' ');
            return (
              <li key={hadith.id}>
                <Link
                  href={hadithPath(hadith.id)}
                  className="group block border-b border-rule py-4 no-underline transition-colors duration-[var(--motion-fast)] hover:bg-sunken"
                >
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1 type-small text-ink-muted">
                    <span className="font-semibold text-ink underline decoration-rule decoration-1 underline-offset-[0.2em] group-hover:decoration-accent">{reference || 'Hadith'}</span>
                    {hadith.tradition && <TraditionBadge tradition={hadith.tradition} />}
                  </div>
                  {hadith.title && (
                    <p className="mt-1 font-medium text-ink">
                      <BilingualTitle text={String(hadith.title)} />
                    </p>
                  )}
                  {english ? (
                    <p className="mt-1 max-w-[var(--measure-wide)] type-small text-ink-muted">{english}</p>
                  ) : (
                    arabic && (
                      <ArabicText as="p" variant="inline" className="mt-1 max-w-[var(--measure-reading)] text-ink">
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
