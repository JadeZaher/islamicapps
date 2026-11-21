import Link from 'next/link';
import { ArabicText } from '@/components/ArabicText';
import type { ReportListItem } from '@/db/queries/browse';
import { hadithPath } from '@/lib/hadith-address';
import { ArrowMark } from './Marks';
import './archive.css';

/** Reports in source order: reference, Arabic opening (right-aligned), English opening when shown. */
export function ReportList({ items }: { items: ReportListItem[] }) {
  return (
    <ol className="archive-rule">
      {items.map((item) => (
        <li key={item.id} className="border-b border-[color:var(--archive-rule)]">
          <Link
            href={hadithPath(item.id)}
            className="archive-focus grid gap-[var(--archive-space-2)] py-[var(--archive-space-3)] hover:bg-white/[0.03] sm:grid-cols-[10rem_1fr]"
          >
            <span className="text-sm font-medium">{item.reference}</span>
            <span className="min-w-0">
              {item.arabicExcerpt && (
                <ArabicText as="span" className="block text-end text-lg leading-loose">
                  {item.arabicExcerpt}
                </ArabicText>
              )}
              {item.englishExcerpt && (
                <span className="mt-1 block text-sm leading-relaxed text-[color:var(--archive-muted)]">{item.englishExcerpt}</span>
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
    <nav aria-label="Pages" className="mt-[var(--archive-space-4)] flex items-center justify-between text-sm">
      {page > 1 ? (
        <Link href={href(page - 1)} rel="prev" className="archive-focus flex items-center gap-2 archive-link">
          <ArrowMark direction="left" /> Previous page
        </Link>
      ) : (
        <span />
      )}
      <span className="text-[color:var(--archive-muted)]">
        Page {page.toLocaleString('en')} of {totalPages.toLocaleString('en')}
      </span>
      {page < totalPages ? (
        <Link href={href(page + 1)} rel="next" className="archive-focus flex items-center gap-2 archive-link">
          Next page <ArrowMark direction="right" />
        </Link>
      ) : (
        <span />
      )}
    </nav>
  );
}
