export const dynamic = 'force-dynamic';

import Link from 'next/link';
import {
  listCorrespondencesForReview,
  type ReviewQueueFilters,
  type ReviewQueueScope,
  type ReviewQueueStatus,
} from '@/db/queries/correspondence-review';
import type { CorrespondenceClass } from '@/db/queries/contracts';
import { parsePageParam } from '@/lib/pagination';
import { CORRESPONDENCE_LABEL } from '@/app/hadith/[id]/components/family/labels';

interface PageProps {
  searchParams: Promise<{ page?: string; status?: string; scope?: string; class?: string; shown?: string }>;
}

const STATUS: Record<ReviewQueueStatus, string> = { unreviewed: 'Unreviewed', decided: 'Decided', all: 'All' };
const SCOPE: Record<ReviewQueueScope, string> = {
  cross_tradition: 'Across traditions',
  cross_work_same_tradition: 'Across works, one tradition',
  same_work: 'Within one work',
  all: 'All',
};
const SHOWN: Record<'all' | 'shown' | 'hidden', string> = { all: 'All', shown: 'Shown to readers', hidden: 'Below the display threshold' };
const CLASS: Record<CorrespondenceClass | 'all', string> = { all: 'All', ...(CORRESPONDENCE_LABEL as Record<CorrespondenceClass, string>) };

function pick<T extends string>(value: string | undefined, options: Record<T, string>, fallback: T): T {
  return value && value in options ? (value as T) : fallback;
}

/** Review queue of machine-found report correspondences; lowest-scoring first, since those need a reader most. */
export default async function CorrespondenceQueuePage({ searchParams }: PageProps) {
  const params = await searchParams;
  const filters: Required<ReviewQueueFilters> = {
    status: pick(params.status, STATUS, 'unreviewed'),
    scope: pick(params.scope, SCOPE, 'cross_tradition'),
    relationClass: pick(params.class, CLASS, 'all'),
    shown: pick(params.shown, SHOWN, 'all'),
  };
  const page = parsePageParam(params.page);
  const result = await listCorrespondencesForReview(filters, { page, pageSize: 50 });
  const query = (overrides: Record<string, string | number>) => {
    const next = new URLSearchParams({
      status: filters.status,
      scope: filters.scope,
      class: filters.relationClass,
      shown: filters.shown,
      page: String(page),
      ...Object.fromEntries(Object.entries(overrides).map(([key, value]) => [key, String(value)])),
    });
    return `?${next.toString()}`;
  };

  return (
    <div className="space-y-6 text-ink">
      <header>
        <h1 className="text-2xl font-semibold">Report correspondences</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Machine-found pairs of reports with shared wording, weakest overlap first. Confirm a pair only when the two texts
          carry the same report or passage; reject a shared formula, verse or ruling. Overlap is shared wording for same and
          variant wording, and the share of the shorter text for a shared passage.
        </p>
      </header>

      <form method="get" className="flex flex-wrap items-end gap-4 text-sm">
        {(
          [
            ['status', 'Status', STATUS, filters.status],
            ['scope', 'Scope', SCOPE, filters.scope],
            ['class', 'Class', CLASS, filters.relationClass],
            ['shown', 'Display', SHOWN, filters.shown],
          ] as const
        ).map(([name, label, options, value]) => (
          <label key={name} className="flex flex-col gap-1 text-ink-muted">
            {label}
            <select name={name} defaultValue={value} className="border border-rule bg-paper px-2 py-1 text-ink">
              {Object.entries(options).map(([key, text]) => (
                <option key={key} value={key}>{text}</option>
              ))}
            </select>
          </label>
        ))}
        <button type="submit" className="h-10 border border-ink px-4 text-sm font-semibold text-ink hover:bg-ink hover:text-paper">Apply</button>
      </form>

      <p className="text-sm text-ink-muted">
        {result.totalCapped ? `${result.total.toLocaleString('en')}+` : result.total.toLocaleString('en')} pairs
      </p>

      {result.items.length === 0 ? (
        <p className="text-ink-muted">No pairs match these filters.</p>
      ) : (
        <div className="overflow-x-auto" tabIndex={0} role="region" aria-label="Correspondence pairs">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-rule text-left text-ink-muted">
              <th className="py-2 pr-4 font-medium">Report A</th>
              <th className="py-2 pr-4 font-medium">Report B</th>
              <th className="py-2 pr-4 font-medium">Class</th>
              <th className="py-2 pr-4 text-right font-medium">Overlap</th>
              <th className="py-2 pr-4 font-medium">Decision</th>
              <th className="py-2 font-medium"><span className="sr-only">Open</span></th>
            </tr>
          </thead>
          <tbody>
            {result.items.map((item) => (
              <tr key={item.id} className="border-b border-rule">
                <td className="py-2 pr-4">{item.a.tradition} · {item.a.source_work} {item.a.hadith_no ?? <span className="text-ink-muted">{item.a.hadith_id.replace(/^hadith:/, '')}</span>}</td>
                <td className="py-2 pr-4">{item.b.tradition} · {item.b.source_work} {item.b.hadith_no ?? <span className="text-ink-muted">{item.b.hadith_id.replace(/^hadith:/, '')}</span>}</td>
                <td className="py-2 pr-4">{CORRESPONDENCE_LABEL[item.relation_class]}{item.shown ? '' : ' (below threshold)'}</td>
                <td className="py-2 pr-4 text-right tabular-nums" title={item.relation_class === 'partial_overlap' ? 'Share of the shorter text inside the longer' : 'Shared wording (Jaccard)'}>
                  {Math.round(item.measure * 100)}%
                </td>
                <td className="py-2 pr-4 text-ink-muted">{item.decision ?? '—'}</td>
                <td className="py-2">
                  <Link
                    href={`/admin/correspondences/review?a=${encodeURIComponent(item.a.hadith_id)}&b=${encodeURIComponent(item.b.hadith_id)}`}
                    className="text-accent underline-offset-4 hover:underline"
                  >
                    Review
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        </div>
      )}

      <nav aria-label="Pages" className="flex gap-4 text-sm">
        {page > 1 && <Link href={query({ page: page - 1 })} className="underline-offset-4 hover:underline">Previous</Link>}
        <span className="text-ink-muted">Page {result.page} of {result.totalPages}</span>
        {page < result.totalPages && <Link href={query({ page: page + 1 })} className="underline-offset-4 hover:underline">Next</Link>}
      </nav>
    </div>
  );
}
