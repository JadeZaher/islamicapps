import Link from 'next/link';

interface PageLinksProps {
  basePath: string;
  page: number;
  totalPages: number;
  /** Current query params other than `page`; empty values are dropped. */
  params?: Record<string, string | undefined>;
}

// DESIGN.md §Buttons: secondary (1px ink border, fills with ink on hover); a disabled end shows a rule border.
const linkClass =
  'inline-flex h-10 items-center border border-ink px-4 text-sm font-semibold text-ink no-underline transition-colors duration-[var(--motion-fast)] hover:bg-ink hover:text-paper';
const disabledClass = 'inline-flex h-10 items-center border border-rule px-4 text-sm font-semibold text-ink-muted';

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
    <nav aria-label="Pagination" className="mt-8 flex items-center justify-between gap-4">
      {page > 1 ? (
        <Link href={hrefFor(page - 1)} rel="prev" aria-label="Previous page" className={linkClass}>
          Previous
        </Link>
      ) : (
        <span aria-hidden="true" className={disabledClass}>Previous</span>
      )}
      <span aria-current="page" className="text-sm tabular-nums text-ink-muted">
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
