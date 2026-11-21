import Link from 'next/link';

interface PageLinksProps {
  basePath: string;
  page: number;
  totalPages: number;
  /** Current query params other than `page`; empty values are dropped. */
  params?: Record<string, string | undefined>;
}

const linkClass =
  'rounded-md border border-slate-700 px-3 py-1.5 text-sm text-slate-200 outline-none transition-colors hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-emerald-400';
const disabledClass = 'rounded-md border border-slate-800 px-3 py-1.5 text-sm text-slate-600';

/** Server-rendered Previous / Next pager: plain links, works without JS and keeps filters. */
export function PageLinks({ basePath, page, totalPages, params = {} }: PageLinksProps) {
  if (totalPages <= 1) return null;

  const hrefFor = (target: number) => {
    const search = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value) search.set(key, value);
    }
    if (target > 1) search.set('page', String(target));
    const query = search.toString();
    return query ? `${basePath}?${query}` : basePath;
  };

  return (
    <nav aria-label="Pagination" className="mt-8 flex items-center justify-between">
      {page > 1 ? (
        <Link href={hrefFor(page - 1)} rel="prev" aria-label="Previous page" className={linkClass}>
          Previous
        </Link>
      ) : (
        <span aria-hidden="true" className={disabledClass}>Previous</span>
      )}
      <span aria-current="page" className="text-sm text-slate-400">
        Page {page} of {totalPages.toLocaleString()}
      </span>
      {page < totalPages ? (
        <Link href={hrefFor(page + 1)} rel="next" aria-label="Next page" className={linkClass}>
          Next
        </Link>
      ) : (
        <span aria-hidden="true" className={disabledClass}>Next</span>
      )}
    </nav>
  );
}
