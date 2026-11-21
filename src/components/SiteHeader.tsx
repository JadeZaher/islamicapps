'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ProductMark, SearchIcon } from '@/components/marks';

const NAV_LINKS = [
  { href: '/collections', label: 'Collections' },
  { href: '/hadith', label: 'Hadith' },
  { href: '/narrator', label: 'Narrators' },
  { href: '/comparative', label: 'Comparative' },
  { href: '/glossary', label: 'Glossary' },
] as const;

/** Public top bar (DESIGN.md §Site header); the admin area renders its own chrome, so it is hidden there. */
export function SiteHeader() {
  const pathname = usePathname();
  if (pathname.startsWith('/admin')) return null;

  return (
    <header className="border-b border-rule-strong">
      <div className="wrap flex flex-wrap items-center gap-x-8 gap-y-2 py-3">
        <Link href="/" className="inline-flex items-center gap-2 py-2 text-[0.9375rem] font-extrabold tracking-[-0.01em] text-ink no-underline">
          <ProductMark decorative />
          <span>Shura wa Istehsan</span>
        </Link>

        <nav aria-label="Main">
          <ul className="flex flex-wrap gap-x-6 gap-y-1">
            {NAV_LINKS.map(({ href, label }) => {
              const isActive = pathname === href || pathname.startsWith(`${href}/`);
              return (
                <li key={href}>
                  <Link
                    href={href}
                    aria-current={isActive ? 'page' : undefined}
                    className={`inline-block border-b-2 py-2 type-small font-medium no-underline transition-colors duration-[var(--motion-fast)] ${
                      isActive ? 'border-ink text-ink' : 'border-transparent text-ink-muted hover:text-ink'
                    }`}
                  >
                    {label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* The home page is the search; a second box there would compete with it. */}
        {pathname !== '/' && (
          <form action="/hadith" role="search" className="relative w-full sm:ms-auto sm:w-64">
            <SearchIcon decorative className="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 text-ink-muted" />
            <input
              type="search"
              name="q"
              dir="auto"
              aria-label="Search hadith"
              placeholder="Search hadith"
              className="h-10 w-full border border-control bg-surface ps-9 pe-3 type-small text-ink placeholder:text-ink-muted focus-visible:border-focus focus-visible:outline-offset-0"
            />
          </form>
        )}
      </div>
    </header>
  );
}
