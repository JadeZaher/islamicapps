import Link from 'next/link';

export interface Crumb {
  label: string;
  href?: string;
}

/** Breadcrumb trail; the last crumb is the current page and is not a link. DESIGN.md §Page header. */
export function Breadcrumbs({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="type-small text-ink-muted">
      <ol className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        {items.map((item, index) => {
          const last = index === items.length - 1;
          return (
            <li key={`${index}:${item.label}`} className="flex items-baseline gap-x-2">
              {item.href && !last ? (
                <Link href={item.href} className="archive-link text-ink-muted">
                  {item.label}
                </Link>
              ) : (
                <span aria-current={last ? 'page' : undefined} className={last ? 'text-ink' : undefined}>
                  {item.label}
                </span>
              )}
              {!last && (
                <span aria-hidden="true" className="text-ink-faint">
                  /
                </span>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
