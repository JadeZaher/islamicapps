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
    <main className="wrap pb-12">
      <h1 className="page-header type-h1">Narrators</h1>

      <form action="/narrator" role="search" className="mt-8 flex max-w-[var(--measure-reading)] gap-2">
        <input
          type="search"
          name="q"
          defaultValue={q}
          aria-label="Search narrators"
          placeholder="Search by name, English or Arabic"
          dir="auto"
          className="h-10 w-full border border-control bg-surface px-3 text-base text-ink placeholder:text-ink-muted focus-visible:border-focus focus-visible:outline-offset-0"
        />
        <Button type="submit">
          Search
        </Button>
      </form>

      <p className="mt-6 type-small tabular-nums text-ink-muted" aria-live="polite">
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
        <ul className="mt-3 border-t border-rule-strong">
          {result.items.map((narrator) => {
            const id = String(narrator.id);
            return (
              <li key={id}>
                <Link
                  href={`/narrator/${encodeURIComponent(id)}`}
                  className="group block border-b border-rule py-3 no-underline transition-colors duration-[var(--motion-fast)] hover:bg-sunken"
                >
                  <NarratorName
                    english={narrator.name_english as string | undefined}
                    arabic={narrator.name_arabic as string | undefined}
                    latinClassName="font-semibold text-ink underline decoration-rule decoration-1 underline-offset-[0.2em] group-hover:decoration-accent w-fit"
                    arabicClassName="text-ink-muted"
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
