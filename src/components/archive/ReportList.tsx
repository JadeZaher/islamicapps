import Link from 'next/link';
import { ArabicText } from '@/components/ArabicText';
import type { ReportListItem } from '@/db/queries/browse';
import { hadithPath } from '@/lib/hadith-address';
import { ArrowMark } from './Marks';

/** Reports in source order: reference, Arabic opening (right-aligned), English opening when shown. */
export function ReportList({ items }: { items: ReportListItem[] }) {
  return (
    <ol className="archive-rule">
      {items.map((item) => (
        <li key={item.id} className="border-b border-rule">
          <Link
            href={hadithPath(item.id)}
            className="group grid gap-2 py-4 no-underline transition-colors duration-[var(--motion-fast)] hover:bg-sunken sm:grid-cols-[10rem_1fr] sm:gap-6"
          >
            <span className="type-small font-semibold tabular-nums text-ink underline decoration-rule decoration-1 underline-offset-[0.2em] group-hover:decoration-accent">{item.reference}</span>
            <span className="min-w-0">
              {item.arabicExcerpt && (
                <ArabicText as="span" variant="inline" className="block text-ink">
                  {item.arabicExcerpt}
                </ArabicText>
              )}
              {item.englishExcerpt && (
                <span className="mt-1 block type-small text-ink-muted">{item.englishExcerpt}</span>
              )}
            </span>
          </Link>
        </li>
      ))}
    </ol>
  );
}

/** Plain previous/next pager for server-rendered lists; works without JavaScript. */
export function Pager({ basePath, page, totalPages, extra = {} }: { basePath: string; page: number; totalPages: number; extra?: Record<string, string> }) {
  if (totalPages <= 1) return null;
  const href = (target: number) => {
    const search = new URLSearchParams(extra);
    if (target > 1) search.set('page', String(target));
    const query = search.toString();
    return query ? `${basePath}?${query}` : basePath;
  };
  return (
    <nav aria-label="Pages" className="mt-6 flex items-center justify-between gap-4 type-small">
      {page > 1 ? (
        <Link href={href(page - 1)} rel="prev" className="archive-link flex min-h-10 items-center gap-2">
          <ArrowMark direction="left" /> Previous page
        </Link>
      ) : (
        <span />
      )}
      <span className="tabular-nums text-ink-muted">
        Page {page.toLocaleString('en')} of {totalPages.toLocaleString('en')}
      </span>
      {page < totalPages ? (
        <Link href={href(page + 1)} rel="next" className="archive-link flex min-h-10 items-center gap-2">
          Next page <ArrowMark direction="right" />
        </Link>
      ) : (
        <span />
      )}
    </nav>
  );
}
