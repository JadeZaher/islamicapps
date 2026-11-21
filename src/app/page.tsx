import Link from 'next/link';
import { Search } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { HADITH_TRADITION_OPTIONS } from '@/lib/constants/traditions';

const TRADITION_LINKS = HADITH_TRADITION_OPTIONS.filter((option) => option.value);

const linkClass =
  'rounded-md border border-slate-800 px-4 py-3 text-sm text-slate-200 outline-none transition-colors hover:border-emerald-500/50 hover:bg-slate-900 focus-visible:ring-2 focus-visible:ring-emerald-400';

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-[70vh] max-w-2xl flex-col justify-center px-6 py-16 text-slate-100">
      <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">Shura wa Istehsan</h1>
      <p className="mt-3 text-lg text-slate-400">
        Hadith and narrators across the Sunni, Imami, Zaydi and Ibadi traditions.
      </p>

      <form action="/hadith" role="search" className="mt-8 flex gap-2">
        <div className="relative w-full">
          <Search
            aria-hidden="true"
            className="pointer-events-none absolute left-3 top-1/2 size-5 -translate-y-1/2 text-slate-500"
          />
          <input
            type="search"
            name="q"
            aria-label="Search hadith"
            placeholder="Search hadith by chapter, topic or text"
            className="h-12 w-full rounded-lg border border-slate-700 bg-slate-900 pl-10 pr-3 text-base text-slate-100 placeholder:text-slate-500 outline-none focus-visible:border-emerald-500 focus-visible:ring-2 focus-visible:ring-emerald-500/40"
          />
        </div>
        <Button type="submit" size="lg" className="h-12 bg-emerald-600 px-6 text-white hover:bg-emerald-500">
          Search
        </Button>
      </form>

      <nav aria-label="Browse by tradition" className="mt-10">
        <h2 className="text-sm font-medium text-slate-400">Browse by tradition</h2>
        <ul className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          {TRADITION_LINKS.map((option) => (
            <li key={option.value}>
              <Link href={`/hadith?tradition=${encodeURIComponent(option.value)}`} className={`block ${linkClass}`}>
                {option.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <nav aria-label="More" className="mt-6 flex gap-2">
        <Link href="/narrator" className={`flex-1 text-center ${linkClass}`}>
          Narrators
        </Link>
        <Link href="/comparative" className={`flex-1 text-center ${linkClass}`}>
          Comparative studies
        </Link>
      </nav>
    </main>
  );
}
