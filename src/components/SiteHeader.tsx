'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Search } from 'lucide-react';

const NAV_LINKS = [
  { href: '/hadith', label: 'Hadith' },
  { href: '/narrator', label: 'Narrators' },
  { href: '/comparative', label: 'Comparative' },
] as const;

/** Public top bar; the admin area renders its own chrome, so it is hidden there. */
export function SiteHeader() {
  const pathname = usePathname();
  if (pathname.startsWith('/admin')) return null;

  return (
    <header className="border-b border-slate-800 bg-slate-950">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-6 gap-y-3 px-6 py-3">
        <Link
          href="/"
          className="rounded-sm text-sm font-semibold tracking-tight text-slate-100 outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
        >
          Shura wa Istehsan
        </Link>

        <nav aria-label="Main" className="flex items-center gap-1">
          {NAV_LINKS.map(({ href, label }) => {
            const isActive = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                aria-current={isActive ? 'page' : undefined}
                className={`rounded-md px-3 py-1.5 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-emerald-400 ${
                  isActive
                    ? 'bg-slate-800 text-white'
                    : 'text-slate-400 hover:bg-slate-900 hover:text-slate-100'
                }`}
              >
                {label}
              </Link>
            );
          })}
        </nav>

        <form action="/hadith" role="search" className="relative ml-auto w-full sm:w-64">
          <Search
            aria-hidden="true"
            className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-slate-500"
          />
          <input
            type="search"
            name="q"
            aria-label="Search hadith"
            placeholder="Search hadith"
            className="h-8 w-full rounded-md border border-slate-700 bg-slate-900 pl-8 pr-3 text-sm text-slate-100 placeholder:text-slate-500 outline-none focus-visible:border-emerald-500 focus-visible:ring-2 focus-visible:ring-emerald-500/40"
          />
        </form>
      </div>
    </header>
  );
}
