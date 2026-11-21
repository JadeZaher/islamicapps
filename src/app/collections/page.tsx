import type { Metadata } from 'next';
import Link from 'next/link';
import { listWorksByTradition } from '@/db/queries/browse';
import { requestVisibility } from '@/lib/auth/visibility';
import { TraditionBadge } from '@/components/TraditionBadge';

export const dynamic = 'force-dynamic';

export const metadata: Metadata = { title: 'Collections' };

const number = (value: number) => value.toLocaleString('en');

/** Works grouped by tradition, the four traditions in alphabetical order; none is the default. */
export default async function CollectionsPage() {
  const traditions = await listWorksByTradition(await requestVisibility());
  const empty = traditions.every((group) => group.works.length === 0);

  return (
    <main className="archive archive-column py-[var(--archive-space-5)]">
      <h1 className="type-h1 border-b-2 border-rule-strong pb-5">Collections</h1>

      {empty ? (
        <p role="status" className="archive-rule mt-[var(--archive-space-4)] pt-[var(--archive-space-3)] text-[color:var(--archive-muted)]">
          No works are published yet.
        </p>
      ) : (
        <div className="mt-[var(--archive-space-4)] grid gap-[var(--archive-space-5)] md:grid-cols-2">
          {traditions.map((group) => (
            <section key={group.tradition} id={group.tradition.toLowerCase()} aria-labelledby={`${group.tradition}-heading`} className="scroll-mt-16">
              <h2 id={`${group.tradition}-heading`} className="archive-rule pt-3">
                <TraditionBadge tradition={group.tradition} />
              </h2>
              {group.works.length === 0 ? (
                <p className="mt-[var(--archive-space-2)] text-sm text-ink-muted">No works published.</p>
              ) : (
                <ul className="mt-[var(--archive-space-2)]">
                  {group.works.map((work) => (
                    <li key={work.slug} className="border-b border-[color:var(--archive-rule)]">
                      <Link
                        href={`/collections/${encodeURIComponent(work.slug)}`}
                        className="flex items-baseline justify-between gap-[var(--archive-space-3)] py-[var(--archive-space-2)] hover:bg-sunken"
                      >
                        <span className="font-medium">{work.name}</span>
                        <span className="shrink-0 text-sm tabular-nums text-[color:var(--archive-muted)]">{number(work.reportCount)}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>
      )}
    </main>
  );
}
